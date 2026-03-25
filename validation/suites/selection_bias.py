"""Selection-bias suite: deflated Sharpe and optional PBO proxy."""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.wfo import generate_windows

from validation.lib.dsr import compute_psr as _compute_psr
from validation.lib.dsr import deflated_sharpe as _deflated_sharpe
from validation.output import write_json
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.common import scenario_costs
from validation.thresholds import PSR_THRESHOLD

# Sentinel used by compute_objective for low-trade windows (n_trades < 10).
# The actual reject value is -1_000_000.0 (see v10/research/objective.py _REJECT).
# We use -999_999.0 so that scores <= this threshold catch the -1M sentinel
# with a 1.0 safety margin.  Any legitimate (non-rejected) objective score is
# vastly above this threshold, so the gap has no false-positive risk.
_OBJECTIVE_REJECT_THRESHOLD = -999_999.0

_DAYS_PER_YEAR = 365.0


def _daily_log_returns(equity) -> np.ndarray:
    """Daily log returns from equity snapshots (last snapshot per UTC day)."""
    if not equity or len(equity) < 2:
        return np.array([], dtype=float)

    daily_nav: dict[int, float] = {}
    for snap in equity:
        day = int(snap.close_time // 86_400_000)
        daily_nav[day] = float(snap.nav_mid)  # last snapshot wins = daily close

    if len(daily_nav) < 2:
        return np.array([], dtype=float)

    navs = [daily_nav[d] for d in sorted(daily_nav)]
    arr = np.array(navs, dtype=float)
    return np.diff(np.log(arr))


def _annualized_sharpe(daily_returns: np.ndarray) -> float:
    """Annualized Sharpe ratio from daily log returns."""
    if len(daily_returns) < 2:
        return 0.0
    mu = float(np.mean(daily_returns))
    sigma = float(np.std(daily_returns, ddof=0))
    if sigma < 1e-12:
        return 0.0
    return (mu / sigma) * math.sqrt(_DAYS_PER_YEAR)


class SelectionBiasSuite(BaseSuite):
    def name(self) -> str:
        return "selection_bias"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if ctx.validation_config.selection_bias == "none":
            return "selection-bias disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        method = cfg.selection_bias
        costs = scenario_costs(ctx)
        scenario = "harsh" if "harsh" in costs else next(iter(costs.keys()), "base")
        cost = costs.get(scenario, SCENARIOS["base"])

        # --- Candidate backtest ---
        cand_engine = BacktestEngine(
            feed=ctx.feed,
            strategy=ctx.candidate_factory(),
            cost=cost,
            initial_cash=cfg.initial_cash,
            warmup_days=cfg.warmup_days,
        )
        cand_result = cand_engine.run()

        # All statistics (SR, T, skew, kurt) from the SAME daily return series
        # so that PSR/DSR formulas are applied to a consistent data source.
        cand_daily = _daily_log_returns(cand_result.equity)
        t_samples = int(len(cand_daily))
        observed_sharpe = _annualized_sharpe(cand_daily)

        # --- Baseline backtest (for PSR relative ranking) ---
        base_engine = BacktestEngine(
            feed=ctx.feed,
            strategy=ctx.baseline_factory(),
            cost=cost,
            initial_cash=cfg.initial_cash,
            warmup_days=cfg.warmup_days,
        )
        base_result = base_engine.run()
        base_daily = _daily_log_returns(base_result.equity)
        baseline_sharpe = _annualized_sharpe(base_daily)

        payload: dict = {
            "requested_method": method,
            "method": method,
            "scenario": scenario,
            "sr_observed": round(observed_sharpe, 6),
            "sr_baseline": round(baseline_sharpe, 6),
            "T": t_samples,
        }

        if t_samples < 30:
            payload["method"] = "none"
            payload["risk_statement"] = (
                "CAUTION — fallback to none: insufficient daily samples for deflated Sharpe"
            )
            payload["fallback_reason"] = "insufficient_samples"
            status = "info"
        else:
            std = float(np.std(cand_daily))
            if std < 1e-12:
                skew = 0.0
                kurt = 3.0
            else:
                z = (cand_daily - np.mean(cand_daily)) / std
                skew = float(np.mean(z ** 3))
                kurt = float(np.mean(z ** 4))

            # ── DSR/PSR calling convention ──
            # All inputs (SR, T, skew, kurt) are derived from the SAME
            # daily log-return series so the PSR/DSR formulas are applied
            # to a consistent data source.  This matches the theoretical
            # contract of Bailey & López de Prado (2012, 2014).
            #
            # Daily convention differs from research/lib/dsr.py:compute_dsr()
            # which uses per-bar (H4) returns internally.
            # See Report 21, §3 (Role Matrix) — DSR is advisory only.
            dsr_results: dict[str, dict] = {}
            trial_set = [27, 54, 100, 200, 500, 700]
            all_pass = True
            for trials in trial_set:
                dsr, expected_max_sr, sr_std = _deflated_sharpe(
                    sr_observed=observed_sharpe,
                    n_trials=trials,
                    t_samples=t_samples,
                    skew=skew,
                    kurt=kurt,
                )
                passed = dsr > 0.95
                if not passed:
                    all_pass = False
                dsr_results[str(trials)] = {
                    "dsr": round(dsr, 6),
                    "expected_max_sr": round(expected_max_sr, 6),
                    "sr_std": round(sr_std, 6),
                    "pass": passed,
                }

            payload["skew"] = round(skew, 6)
            payload["kurtosis"] = round(kurt, 6)
            payload["dsr"] = dsr_results

            # ── PSR: diagnostic (no veto power) ──
            # Tests P(true SR_candidate > SR_baseline) accounting for
            # estimation uncertainty and non-normality.
            #
            # LIMITATION: PSR treats sr_benchmark as a known constant,
            # ignoring its estimation error and the covariance between
            # candidate/baseline returns.  For 2-strategy comparison this
            # is anti-conservative (underestimates total uncertainty in the
            # SR difference).  WFO Wilcoxon + Bootstrap CI provide paired
            # differential evidence separately and are the binding
            # authority for "candidate beats baseline" (wfo_robustness gate).
            #
            # PSR is reported as a DIAGNOSTIC with advisory levels:
            #   >= 0.95: strong support
            #   0.90-0.95: moderate support
            #   < 0.90: warning
            # PSR alone does NOT gate PROMOTE/HOLD.  See decision.py.
            psr_result = _compute_psr(
                sr_candidate=observed_sharpe,
                sr_benchmark=baseline_sharpe,
                n_obs=t_samples,
                skew=skew,
                kurt=kurt,
            )
            psr_value = float(psr_result.get("psr", 0.0))
            psr_pass = psr_value >= PSR_THRESHOLD
            payload["psr"] = psr_result
            payload["psr_pass"] = psr_pass

            # PBO proxy from window-level candidate-vs-baseline score deltas.
            pbo_proxy = None
            if method in {"pbo", "deflated"}:
                windows = generate_windows(
                    cfg.start,
                    cfg.end,
                    train_months=cfg.wfo_train_months,
                    test_months=cfg.wfo_test_months,
                    slide_months=(
                        cfg.wfo_test_months if cfg.wfo_mode == "fixed" else cfg.wfo_slide_months
                    ),
                )
                if cfg.wfo_windows and len(windows) > cfg.wfo_windows:
                    windows = windows[-cfg.wfo_windows :]

                deltas: list[float] = []
                rejected_windows = 0
                for window in windows:
                    feed = DataFeed(
                        str(ctx.data_path),
                        start=window.test_start,
                        end=window.test_end,
                        warmup_days=cfg.warmup_days,
                    )
                    cand = BacktestEngine(
                        feed=feed,
                        strategy=ctx.candidate_factory(),
                        cost=cost,
                        initial_cash=cfg.initial_cash,
                        warmup_days=cfg.warmup_days,
                    ).run()
                    base = BacktestEngine(
                        feed=feed,
                        strategy=ctx.baseline_factory(),
                        cost=cost,
                        initial_cash=cfg.initial_cash,
                        warmup_days=cfg.warmup_days,
                    ).run()
                    cand_score = compute_objective(cand.summary)
                    base_score = compute_objective(base.summary)
                    # Skip windows where either strategy hit the reject sentinel
                    # (n_trades < 10 → score = -1_000_000). Including these would
                    # inject ±1M deltas that corrupt the negative_delta_ratio.
                    if cand_score <= _OBJECTIVE_REJECT_THRESHOLD or base_score <= _OBJECTIVE_REJECT_THRESHOLD:
                        rejected_windows += 1
                        continue
                    deltas.append(cand_score - base_score)

                if deltas:
                    pbo_proxy = float(sum(1 for d in deltas if d < 0) / len(deltas))
                    payload["pbo_proxy"] = {
                        "n_windows": len(deltas),
                        "n_windows_rejected": rejected_windows,
                        "negative_delta_ratio": round(pbo_proxy, 6),
                    }
                elif rejected_windows > 0:
                    # All windows were rejected — cannot compute PBO
                    payload["pbo_proxy"] = {
                        "n_windows": 0,
                        "n_windows_rejected": rejected_windows,
                        "negative_delta_ratio": None,
                    }

            if method == "pbo" and pbo_proxy is None:
                payload["method"] = "none"
                payload["risk_statement"] = "CAUTION — fallback to none: PBO requires valid WFO windows"
                payload["fallback_reason"] = "no_wfo_windows_for_pbo"
                status = "info"
            else:
                # DSR absolute: advisory only (trivially passes for Sharpe >1.0)
                dsr_statement = (
                    "DSR robust across tested trials"
                    if all_pass
                    else "DSR fails for at least one trial level"
                )
                payload["dsr_advisory"] = dsr_statement

                # PSR diagnostic + PBO overfitting gate (when available).
                # PSR is reported for diagnostic purposes but does NOT gate
                # PROMOTE/HOLD.  PBO overfitting is an independent check.
                psr_level = (
                    "strong support" if psr_pass
                    else "moderate support" if psr_value >= 0.90
                    else "warning"
                )
                if method == "pbo" and pbo_proxy is not None:
                    pbo_passed = pbo_proxy <= 0.5
                    payload["risk_statement"] = (
                        f"PBO {'PASS' if pbo_passed else 'FAIL'} "
                        f"(ratio={pbo_proxy:.3f}); "
                        f"PSR={psr_value:.3f} ({psr_level}, diagnostic); "
                        f"{dsr_statement} (advisory)"
                    )
                    status = "pass" if pbo_passed else "info"
                else:
                    payload["risk_statement"] = (
                        f"PSR={psr_value:.3f} ({psr_level}, diagnostic); "
                        f"{dsr_statement} (advisory)"
                    )
                    status = "info"

        json_path = write_json(payload, ctx.results_dir / "selection_bias.json")
        artifacts.append(json_path)

        return SuiteResult(
            name=self.name(),
            status=status,
            data=payload,
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
