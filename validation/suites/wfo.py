"""Walk-forward suite for OOS robustness testing."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any
from typing import Mapping

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.wfo import generate_windows
from validation.output import write_csv
from validation.output import write_json
from validation.output import write_text
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.common import scenario_costs
from validation.thresholds import WFO_BOOTSTRAP_CI_ALPHA
from validation.thresholds import WFO_BOOTSTRAP_N_RESAMPLES
from validation.thresholds import WFO_SMALL_SAMPLE_CUTOFF
from validation.thresholds import WFO_WILCOXON_ALPHA
from validation.thresholds import WFO_WIN_RATE_THRESHOLD

_INVALID_REASON_NONE = "none"
_LOW_TRADE_REASON_NONE = "none"


def _to_float_or_nan(value: Any) -> float:
    try:
        if value is None:
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round_or_nan(value: float, ndigits: int) -> float:
    return round(float(value), ndigits) if math.isfinite(float(value)) else math.nan


def _objective_without_reject(summary: Mapping[str, Any]) -> float:
    """Compute objective score without sentinel rejection for low trade counts."""
    n_trades = _to_float_or_nan(summary.get("trades", 0.0))
    cagr = _to_float_or_nan(summary.get("cagr_pct"))
    max_dd = _to_float_or_nan(summary.get("max_drawdown_mid_pct"))
    sharpe = _to_float_or_nan(summary.get("sharpe", 0.0))

    if not math.isfinite(n_trades):
        return math.nan
    if not math.isfinite(cagr) or not math.isfinite(max_dd) or not math.isfinite(sharpe):
        return math.nan

    raw_pf = summary.get("profit_factor", 0.0)
    if isinstance(raw_pf, str) and raw_pf.strip().lower() == "inf":
        pf = 3.0
    else:
        pf = _to_float_or_nan(raw_pf)
        if math.isinf(pf):
            pf = 3.0
    if not math.isfinite(pf):
        return math.nan

    return (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
        + min(n_trades / 50.0, 1.0) * 5.0
    )


def _window_invalid_reason(
    trade_count_candidate: int,
    trade_count_baseline: int,
    candidate_core: list[float],
    baseline_core: list[float],
) -> str:
    if trade_count_candidate <= 0 and trade_count_baseline <= 0:
        return "both_zero_trade_counts"
    if trade_count_candidate <= 0:
        return "candidate_zero_trade_count"
    if trade_count_baseline <= 0:
        return "baseline_zero_trade_count"

    candidate_non_finite = any(not math.isfinite(value) for value in candidate_core)
    baseline_non_finite = any(not math.isfinite(value) for value in baseline_core)

    if candidate_non_finite and baseline_non_finite:
        return "both_non_finite_core_metrics"
    if candidate_non_finite:
        return "candidate_non_finite_core_metrics"
    if baseline_non_finite:
        return "baseline_non_finite_core_metrics"

    return _INVALID_REASON_NONE


def _low_trade_reason(
    trade_count_candidate: int,
    trade_count_baseline: int,
    min_trades_for_power: int,
    *,
    valid_window: bool,
) -> tuple[bool, str]:
    if not valid_window:
        return False, _LOW_TRADE_REASON_NONE

    candidate_low = 0 < trade_count_candidate < min_trades_for_power
    baseline_low = 0 < trade_count_baseline < min_trades_for_power

    if candidate_low and baseline_low:
        return True, "both_below_min_trades_for_power"
    if candidate_low:
        return True, "candidate_below_min_trades_for_power"
    if baseline_low:
        return True, "baseline_below_min_trades_for_power"

    return False, _LOW_TRADE_REASON_NONE


def _evaluate_window_metrics(
    *,
    window_id: int,
    test_start: str,
    test_end: str,
    candidate_summary: Mapping[str, Any],
    baseline_summary: Mapping[str, Any],
    min_trades_for_power: int,
) -> dict[str, Any]:
    candidate_score = _objective_without_reject(candidate_summary)
    baseline_score = _objective_without_reject(baseline_summary)

    candidate_cagr = _to_float_or_nan(candidate_summary.get("cagr_pct"))
    baseline_cagr = _to_float_or_nan(baseline_summary.get("cagr_pct"))
    candidate_max_dd = _to_float_or_nan(candidate_summary.get("max_drawdown_mid_pct"))
    baseline_max_dd = _to_float_or_nan(baseline_summary.get("max_drawdown_mid_pct"))
    candidate_sharpe = _to_float_or_nan(candidate_summary.get("sharpe"))
    baseline_sharpe = _to_float_or_nan(baseline_summary.get("sharpe"))

    trade_count_candidate = _to_int(candidate_summary.get("trades", 0), default=0)
    trade_count_baseline = _to_int(baseline_summary.get("trades", 0), default=0)

    invalid_reason = _window_invalid_reason(
        trade_count_candidate=trade_count_candidate,
        trade_count_baseline=trade_count_baseline,
        candidate_core=[candidate_score, candidate_cagr, candidate_max_dd, candidate_sharpe],
        baseline_core=[baseline_score, baseline_cagr, baseline_max_dd, baseline_sharpe],
    )
    valid_window = invalid_reason == _INVALID_REASON_NONE

    low_trade_window, low_trade_reason = _low_trade_reason(
        trade_count_candidate=trade_count_candidate,
        trade_count_baseline=trade_count_baseline,
        min_trades_for_power=max(1, int(min_trades_for_power)),
        valid_window=valid_window,
    )

    delta_harsh_score = (
        candidate_score - baseline_score if valid_window else math.nan
    )
    if not math.isfinite(delta_harsh_score):
        if valid_window:
            valid_window = False
            low_trade_window = False
            low_trade_reason = _LOW_TRADE_REASON_NONE
            invalid_reason = "delta_non_finite"
        delta_harsh_score = math.nan

    row = {
        "window_id": int(window_id),
        "test_start": str(test_start),
        "test_end": str(test_end),
        "candidate_score": _round_or_nan(candidate_score, 4),
        "baseline_score": _round_or_nan(baseline_score, 4),
        "delta_harsh_score": _round_or_nan(delta_harsh_score, 4),
        "candidate_cagr_pct": _round_or_nan(candidate_cagr, 4),
        "baseline_cagr_pct": _round_or_nan(baseline_cagr, 4),
        "candidate_max_dd_pct": _round_or_nan(candidate_max_dd, 4),
        "baseline_max_dd_pct": _round_or_nan(baseline_max_dd, 4),
        "candidate_sharpe": _round_or_nan(candidate_sharpe, 6),
        "baseline_sharpe": _round_or_nan(baseline_sharpe, 6),
        "candidate_trades": int(trade_count_candidate),
        "baseline_trades": int(trade_count_baseline),
        "trade_count_candidate": int(trade_count_candidate),
        "trade_count_baseline": int(trade_count_baseline),
        "valid_window": bool(valid_window),
        "invalid_reason": str(invalid_reason),
        "low_trade_window": bool(low_trade_window),
        "low_trade_reason": str(low_trade_reason),
    }

    delta_value = _to_float_or_nan(row["delta_harsh_score"])
    if math.isnan(delta_value):
        assert row["valid_window"] is False
        assert row["invalid_reason"] != _INVALID_REASON_NONE
    else:
        assert math.isfinite(delta_value)
        assert row["invalid_reason"] == _INVALID_REASON_NONE
        assert abs(delta_value) < 100_000.0

    return row


def _aggregate_deltas(
    rows: list[dict[str, Any]],
    *,
    include_window: Callable[[dict[str, Any]], bool],
) -> dict[str, Any]:
    deltas: list[float] = []
    for row in rows:
        if not include_window(row):
            continue
        value = _to_float_or_nan(row.get("delta_harsh_score"))
        if math.isfinite(value):
            deltas.append(value)

    if not deltas:
        return {
            "n_windows": 0,
            "win_count": math.nan,
            "win_rate": math.nan,
            "mean_delta": math.nan,
            "median_delta": math.nan,
            "worst_delta": math.nan,
            "best_delta": math.nan,
        }

    n_windows = len(deltas)
    win_count = sum(1 for value in deltas if value > 0.0)
    return {
        "n_windows": int(n_windows),
        "win_count": int(win_count),
        "win_rate": round(win_count / n_windows, 6),
        "mean_delta": round(sum(deltas) / n_windows, 6),
        "median_delta": round(float(median(deltas)), 6),
        "worst_delta": round(min(deltas), 6),
        "best_delta": round(max(deltas), 6),
    }


def _compute_wilcoxon(deltas: list[float]) -> dict[str, Any]:
    """Wilcoxon signed-rank test, one-sided (greater).

    H0: median(delta) = 0.  H_a: median(delta) > 0.
    Returns p-value from exact distribution when n <= 25, else normal approx.
    With n < 6 non-zero observations, scipy raises; we return p=1.0 (insufficient).
    """
    from scipy.stats import wilcoxon as _wilcoxon

    nonzero = [d for d in deltas if d != 0.0]
    n_nonzero = len(nonzero)
    if n_nonzero < 6:
        return {
            "statistic": math.nan,
            "p_value": 1.0,
            "n_nonzero": n_nonzero,
            "sufficient": False,
        }
    try:
        stat, p = _wilcoxon(deltas, alternative="greater")
    except ValueError:
        return {
            "statistic": math.nan,
            "p_value": 1.0,
            "n_nonzero": n_nonzero,
            "sufficient": False,
        }
    return {
        "statistic": round(float(stat), 4),
        "p_value": round(float(p), 6),
        "n_nonzero": n_nonzero,
        "sufficient": True,
    }


def _compute_bootstrap_ci(
    deltas: list[float],
    n_resamples: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    """Percentile bootstrap CI on mean(delta).

    Returns CI bounds and whether CI excludes zero (lower > 0).
    Uses numpy RNG with configurable seed for reproducibility.
    """
    import numpy as np

    n = len(deltas)
    if n < 2:
        return {
            "ci_lower": math.nan,
            "ci_upper": math.nan,
            "mean_delta": math.nan,
            "excludes_zero": False,
            "n": n,
            "seed": seed,
        }

    rng = np.random.default_rng(seed=seed)
    arr = np.array(deltas, dtype=np.float64)
    boot_means = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        boot_means[i] = arr[idx].mean()

    lo = float(np.percentile(boot_means, 100 * alpha / 2))
    hi = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    mean_val = float(arr.mean())

    return {
        "ci_lower": round(lo, 4),
        "ci_upper": round(hi, 4),
        "mean_delta": round(mean_val, 4),
        "excludes_zero": bool(lo > 0.0),
        "n": n,
        "seed": seed,
    }


def _fmt_num(value: Any, ndigits: int = 4) -> str:
    num = _to_float_or_nan(value)
    if not math.isfinite(num):
        return "NaN"
    return f"{num:.{ndigits}f}"


def _build_audit_report(
    *,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    min_trades_for_power: int,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    invalid_example = next((row for row in rows if not bool(row.get("valid_window"))), None)
    low_trade_example = next(
        (
            row
            for row in rows
            if bool(row.get("valid_window")) and bool(row.get("low_trade_window"))
        ),
        None,
    )

    lines: list[str] = [
        "# WFO invalid-window audit",
        "",
        f"- Generated: {now}",
        "",
        "## Spec",
        "",
        "- `valid_window=False` when either side has zero trades or any core metric is NaN/Inf.",
        "- `low_trade_window=True` only when `valid_window=True` and trade count is in `(0, min_trades_for_power)`.",
        "- Aggregate stats use valid windows only; power stats exclude low-trade windows.",
        "- Invalid windows must carry explicit `invalid_reason`; their `delta_harsh_score` is `NaN`.",
        "",
        "## What changed",
        "",
        "- Removed sentinel-driven window deltas from WFO reporting by using non-reject objective scoring in this suite.",
        "- Added explicit per-window validity fields:",
        "  - `trade_count_baseline`, `trade_count_candidate`",
        "  - `valid_window`, `invalid_reason`",
        "  - `low_trade_window`, `low_trade_reason`",
        "- Added dual aggregation blocks in `wfo_summary.json`: `stats_all_valid` and `stats_power_only`.",
        f"- Default `min_trades_for_power` for WFO is now `{int(min_trades_for_power)}`.",
        "",
        "## Before/after example",
        "",
        "- Before (legacy sentinel path): windows with very low/zero trades could emit extreme deltas like `-1000056.8469`.",
        "- After: invalid windows are explicitly marked and excluded from aggregation.",
    ]

    if invalid_example is not None:
        lines.extend(
            [
                "",
                "| window_id | valid_window | invalid_reason | delta_harsh_score | trade_count_candidate | trade_count_baseline |",
                "|---:|---|---|---:|---:|---:|",
                (
                    f"| {int(invalid_example.get('window_id', -1))} | "
                    f"{bool(invalid_example.get('valid_window'))} | "
                    f"{invalid_example.get('invalid_reason', '')} | "
                    f"{_fmt_num(invalid_example.get('delta_harsh_score'))} | "
                    f"{int(_to_int(invalid_example.get('trade_count_candidate')))} | "
                    f"{int(_to_int(invalid_example.get('trade_count_baseline')))} |"
                ),
            ]
        )

    if low_trade_example is not None:
        lines.extend(
            [
                "",
                "| low-trade window_id | valid_window | low_trade_window | low_trade_reason | delta_harsh_score |",
                "|---:|---|---|---|---:|",
                (
                    f"| {int(low_trade_example.get('window_id', -1))} | "
                    f"{bool(low_trade_example.get('valid_window'))} | "
                    f"{bool(low_trade_example.get('low_trade_window'))} | "
                    f"{low_trade_example.get('low_trade_reason', '')} | "
                    f"{_fmt_num(low_trade_example.get('delta_harsh_score'))} |"
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Summary snapshot",
            "",
            f"- invalid_windows_count: `{int(summary.get('invalid_windows_count', 0))}`",
            f"- low_trade_windows_count: `{int(summary.get('low_trade_windows_count', 0))}`",
            f"- stats_all_valid.median_delta: `{_fmt_num(summary.get('stats_all_valid', {}).get('median_delta'))}`",
            f"- stats_all_valid.worst_delta: `{_fmt_num(summary.get('stats_all_valid', {}).get('worst_delta'))}`",
            f"- stats_power_only.median_delta: `{_fmt_num(summary.get('stats_power_only', {}).get('median_delta'))}`",
            f"- stats_power_only.worst_delta: `{_fmt_num(summary.get('stats_power_only', {}).get('worst_delta'))}`",
        ]
    )

    return "\n".join(lines) + "\n"


class WFOSuite(BaseSuite):
    def name(self) -> str:
        return "wfo"

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []
        min_trades_for_power = max(
            1,
            int(getattr(cfg, "min_trades_for_power", getattr(cfg, "low_trade_threshold", 5))),
        )

        slide_months = cfg.wfo_slide_months
        if cfg.wfo_mode == "fixed":
            slide_months = cfg.wfo_test_months

        windows = generate_windows(
            cfg.start,
            cfg.end,
            train_months=cfg.wfo_train_months,
            test_months=cfg.wfo_test_months,
            slide_months=slide_months,
        )

        if cfg.wfo_windows is not None and cfg.wfo_windows > 0 and len(windows) > cfg.wfo_windows:
            windows = windows[-cfg.wfo_windows :]

        costs = scenario_costs(ctx)
        harsh_cost = costs.get("harsh") or costs.get("base") or costs.get("smart")
        if harsh_cost is None:
            harsh_cost = SCENARIOS["base"]

        rows: list[dict[str, Any]] = []

        for wi, window in enumerate(windows):
            feed = DataFeed(
                str(ctx.data_path),
                start=window.test_start,
                end=window.test_end,
                warmup_days=cfg.warmup_days,
            )

            summaries: dict[str, Mapping[str, Any]] = {}
            for label, factory in [
                ("candidate", ctx.candidate_factory),
                ("baseline", ctx.baseline_factory),
            ]:
                engine = BacktestEngine(
                    feed=feed,
                    strategy=factory(),
                    cost=harsh_cost,
                    initial_cash=cfg.initial_cash,
                    warmup_days=cfg.warmup_days,
                )
                result = engine.run()
                summaries[label] = result.summary

            row = _evaluate_window_metrics(
                window_id=wi,
                test_start=window.test_start,
                test_end=window.test_end,
                candidate_summary=summaries["candidate"],
                baseline_summary=summaries["baseline"],
                min_trades_for_power=min_trades_for_power,
            )
            rows.append(row)

        invalid_windows_count = sum(1 for row in rows if not bool(row.get("valid_window")))
        low_trade_windows_count = sum(1 for row in rows if bool(row.get("low_trade_window")))
        valid_windows_count = len(rows) - invalid_windows_count
        power_windows_count = sum(
            1
            for row in rows
            if bool(row.get("valid_window")) and not bool(row.get("low_trade_window"))
        )

        stats_all_valid = _aggregate_deltas(
            rows,
            include_window=lambda row: bool(row.get("valid_window")),
        )
        stats_power_only = _aggregate_deltas(
            rows,
            include_window=lambda row: bool(row.get("valid_window"))
            and not bool(row.get("low_trade_window")),
        )

        # --- Statistical tests on POWER-ONLY window deltas ---
        # Authoritative inference excludes low-trade windows to match
        # stats_power_only semantics.  Low-trade windows are underpowered
        # and can dilute or inflate test statistics.
        power_deltas: list[float] = []
        for row in rows:
            if bool(row.get("valid_window")) and not bool(row.get("low_trade_window")):
                v = _to_float_or_nan(row.get("delta_harsh_score"))
                if math.isfinite(v):
                    power_deltas.append(v)

        wilcoxon_result = _compute_wilcoxon(power_deltas)
        bootstrap_ci_result = _compute_bootstrap_ci(
            power_deltas,
            n_resamples=WFO_BOOTSTRAP_N_RESAMPLES,
            alpha=WFO_BOOTSTRAP_CI_ALPHA,
            seed=cfg.seed,
        )

        warnings: list[str] = []
        if int(stats_all_valid.get("n_windows", 0)) == 0:
            warning = (
                "WFO WARNING: no valid windows after invalid-window filtering; "
                "aggregate deltas are NaN."
            )
            warnings.append(warning)
            ctx.run_warnings.append(warning)
            ctx.logger.warning(warning)

        win_count = _to_float_or_nan(stats_all_valid.get("win_count"))
        positive_delta_windows = int(win_count) if math.isfinite(win_count) else 0

        summary = {
            "mode": cfg.wfo_mode,
            "n_windows_total": int(len(rows)),
            "n_windows_valid": int(valid_windows_count),
            "n_windows_power_only": int(power_windows_count),
            "n_windows": int(stats_all_valid.get("n_windows", 0)),
            "positive_delta_windows": int(positive_delta_windows),
            "win_rate": stats_all_valid.get("win_rate", math.nan),
            "mean_delta_score": stats_all_valid.get("mean_delta", math.nan),
            "median_delta_score": stats_all_valid.get("median_delta", math.nan),
            "worst_delta_score": stats_all_valid.get("worst_delta", math.nan),
            "low_trade_windows": int(low_trade_windows_count),
            "low_trade_windows_count": int(low_trade_windows_count),
            "invalid_windows_count": int(invalid_windows_count),
            "low_trade_threshold": int(min_trades_for_power),
            "min_trades_for_power": int(min_trades_for_power),
            "stats_all_valid": stats_all_valid,
            "stats_power_only": stats_power_only,
            "wilcoxon": wilcoxon_result,
            "bootstrap_ci": bootstrap_ci_result,
            "warnings": warnings,
        }

        fieldnames = [
            "window_id",
            "test_start",
            "test_end",
            "candidate_score",
            "baseline_score",
            "delta_harsh_score",
            "candidate_cagr_pct",
            "baseline_cagr_pct",
            "candidate_max_dd_pct",
            "baseline_max_dd_pct",
            "candidate_sharpe",
            "baseline_sharpe",
            "candidate_trades",
            "baseline_trades",
            "trade_count_candidate",
            "trade_count_baseline",
            "valid_window",
            "invalid_reason",
            "low_trade_window",
            "low_trade_reason",
        ]

        csv_path = write_csv(
            rows,
            ctx.results_dir / "wfo_per_round_metrics.csv",
            fieldnames=fieldnames,
        )
        artifacts.append(csv_path)

        json_path = write_json(
            {"summary": summary, "windows": rows},
            ctx.results_dir / "wfo_summary.json",
        )
        artifacts.append(json_path)

        audit_path = write_text(
            _build_audit_report(
                rows=rows,
                summary=summary,
                min_trades_for_power=min_trades_for_power,
            ),
            ctx.reports_dir / "audit_wfo_invalid_windows.md",
        )
        artifacts.append(audit_path)

        n_windows = int(stats_all_valid.get("n_windows", 0))
        if n_windows == 0:
            status = "info"
        else:
            # --- Binding gates: Wilcoxon + Bootstrap CI ---
            wilcoxon_pass = (
                wilcoxon_result["sufficient"]
                and wilcoxon_result["p_value"] <= WFO_WILCOXON_ALPHA
            )
            bootstrap_pass = bootstrap_ci_result["excludes_zero"]
            # Pass if EITHER statistical test confirms positive OOS delta.
            # Both are valid tests of the same hypothesis (delta > 0);
            # requiring both would be overly conservative at small N.
            status = "pass" if (wilcoxon_pass or bootstrap_pass) else "fail"

            # --- Advisory: binary win-rate (no longer binding) ---
            threshold_windows = (
                max(n_windows - 1, 0)
                if n_windows <= WFO_SMALL_SAMPLE_CUTOFF
                else int((WFO_WIN_RATE_THRESHOLD * n_windows) + 0.999999)
            )
            binary_pass = positive_delta_windows >= threshold_windows
            summary["binary_win_rate_pass"] = binary_pass
            summary["binary_win_rate_advisory"] = (
                f"{positive_delta_windows}/{n_windows} "
                f"(threshold={threshold_windows}, advisory_only)"
            )

        return SuiteResult(
            name=self.name(),
            status=status,
            data={"summary": summary, "windows": rows},
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
