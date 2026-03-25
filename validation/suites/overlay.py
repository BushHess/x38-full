"""Overlay suite: compare candidate with overlays on vs disabled."""

from __future__ import annotations

import copy
import time
from pathlib import Path

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.wfo import generate_windows
from validation.output import write_csv, write_json
from validation.strategy_factory import build_from_config
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult
from validation.suites.common import scenario_costs

# Sentinel used by compute_objective for low-trade windows (n_trades < 10).
# The actual reject value is -1_000_000.0 (see v10/research/objective.py _REJECT).
# We use -999_999.0 so that scores <= this threshold catch the -1M sentinel
# with a 1.0 safety margin.
_OBJECTIVE_REJECT_THRESHOLD = -999_999.0

# Maps every overlay-like config field to its "disabled" value.
# Used by both _has_overlay (detection) and _make_factory_without_overlay (disabling).
_OVERLAY_DISABLE_MAP: dict[str, bool | int | float] = {
    "enable_overlay": False,
    "enable_overlay_a": False,
    "enable_overlay_b": False,
    "enable_overlay_c": False,
    "cooldown_after_emergency_dd_bars": 0,
    "overlay_peak_to_trough": 0,
    "overlay_decel": 0,
    # v2 escalating cooldown fields
    "escalating_cooldown": False,
    "short_cooldown_bars": 0,
    "long_cooldown_bars": 0,
    "escalating_lookback_bars": 0,
    "cascade_trigger_count": 0,
}


def _has_overlay(config_obj: object | None) -> bool:
    if config_obj is None:
        return False
    for flag in _OVERLAY_DISABLE_MAP:
        if hasattr(config_obj, flag):
            value = getattr(config_obj, flag)
            if isinstance(value, bool) and value:
                return True
            if isinstance(value, (int, float)) and value not in (0, 0.0):
                return True
    return False


def _make_factory_without_overlay(ctx: SuiteContext):
    live_cfg = copy.deepcopy(ctx.candidate_live_config)
    params = live_cfg.strategy.params
    config_obj = ctx.candidate_config_obj
    for flag, off_value in _OVERLAY_DISABLE_MAP.items():
        # Disable flags present on the config dataclass, not just raw YAML.
        # Catches dataclass defaults like cooldown_after_emergency_dd_bars=12
        # that are absent from the YAML but active in the strategy.
        if config_obj is not None and hasattr(config_obj, flag):
            params[flag] = off_value
        elif flag in params:
            params[flag] = off_value

    def factory():
        strategy, _ = build_from_config(live_cfg)
        return strategy

    return factory


class OverlaySuite(BaseSuite):
    def name(self) -> str:
        return "overlay"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        cfg = ctx.validation_config
        if not cfg.overlay_test and cfg.suite not in {"overlay", "all"}:
            return "overlay-test disabled"
        if not _has_overlay(ctx.candidate_config_obj):
            return "candidate has no overlay-like parameters enabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        costs = scenario_costs(ctx)
        scenario = "harsh" if "harsh" in costs else next(iter(costs.keys()), "base")
        cost = costs.get(scenario, SCENARIOS["base"])

        no_overlay_factory = _make_factory_without_overlay(ctx)

        full: dict[str, dict] = {}
        for label, factory in [
            ("with_overlay", ctx.candidate_factory),
            ("without_overlay", no_overlay_factory),
        ]:
            result = BacktestEngine(
                feed=ctx.feed,
                strategy=factory(),
                cost=cost,
                initial_cash=cfg.initial_cash,
                warmup_days=cfg.warmup_days,
            ).run()
            score = compute_objective(result.summary)
            full[label] = {
                "score": round(float(score), 6),
                "rejected": score <= _OBJECTIVE_REJECT_THRESHOLD,
                "cagr_pct": round(float(result.summary.get("cagr_pct", 0.0)), 6),
                "max_drawdown_mid_pct": round(
                    float(result.summary.get("max_drawdown_mid_pct", 0.0)),
                    6,
                ),
                "sharpe": round(float(result.summary.get("sharpe") or 0.0), 6),
                "trades": int(result.summary.get("trades", 0)),
            }

        # Guard full-period delta against reject sentinel.
        either_full_rejected = (
            full["with_overlay"].get("rejected")
            or full["without_overlay"].get("rejected")
        )
        if either_full_rejected:
            full["delta_score"] = None
            full["delta_mdd"] = None
            full["full_period_rejected"] = True
        else:
            full["delta_score"] = round(
                full["with_overlay"]["score"] - full["without_overlay"]["score"],
                6,
            )
            full["delta_mdd"] = round(
                full["with_overlay"]["max_drawdown_mid_pct"] - full["without_overlay"]["max_drawdown_mid_pct"],
                6,
            )
            full["full_period_rejected"] = False

        windows = generate_windows(
            cfg.start,
            cfg.end,
            train_months=cfg.wfo_train_months,
            test_months=cfg.wfo_test_months,
            slide_months=(cfg.wfo_test_months if cfg.wfo_mode == "fixed" else cfg.wfo_slide_months),
        )
        if cfg.wfo_windows and len(windows) > cfg.wfo_windows:
            windows = windows[-cfg.wfo_windows :]

        wfo_rows: list[dict] = []
        rejected_window_count = 0
        for idx, window in enumerate(windows):
            feed = DataFeed(
                str(ctx.data_path),
                start=window.test_start,
                end=window.test_end,
                warmup_days=cfg.warmup_days,
            )
            row: dict = {
                "window_id": idx,
                "test_start": window.test_start,
                "test_end": window.test_end,
            }

            for label, factory in [
                ("with_overlay", ctx.candidate_factory),
                ("without_overlay", no_overlay_factory),
            ]:
                result = BacktestEngine(
                    feed=feed,
                    strategy=factory(),
                    cost=cost,
                    initial_cash=cfg.initial_cash,
                    warmup_days=cfg.warmup_days,
                ).run()
                score = compute_objective(result.summary)
                row[f"{label}_score"] = round(float(score), 6)
                row[f"{label}_mdd"] = round(float(result.summary.get("max_drawdown_mid_pct", 0.0)), 6)

            # Skip windows where either side hit the reject sentinel
            # (n_trades < 10 → score = -1_000_000). Including these would
            # inject ±1M deltas that corrupt the win_rate.
            either_rejected = (
                row["with_overlay_score"] <= _OBJECTIVE_REJECT_THRESHOLD
                or row["without_overlay_score"] <= _OBJECTIVE_REJECT_THRESHOLD
            )
            row["rejected"] = either_rejected
            if either_rejected:
                rejected_window_count += 1
                row["delta_score"] = 0.0
                row["delta_mdd"] = 0.0
            else:
                row["delta_score"] = round(row["with_overlay_score"] - row["without_overlay_score"], 6)
                row["delta_mdd"] = round(row["with_overlay_mdd"] - row["without_overlay_mdd"], 6)
            wfo_rows.append(row)

        wfo_csv = write_csv(
            wfo_rows,
            ctx.results_dir / "overlay_wfo.csv",
            [
                "window_id",
                "test_start",
                "test_end",
                "with_overlay_score",
                "without_overlay_score",
                "delta_score",
                "with_overlay_mdd",
                "without_overlay_mdd",
                "delta_mdd",
                "rejected",
            ],
        )
        artifacts.append(wfo_csv)

        payload = {
            "scenario": scenario,
            "full_period": full,
            "wfo_windows": wfo_rows,
            "wfo_rejected_windows": rejected_window_count,
        }
        # Win rate computed on valid (non-rejected) windows only.
        valid_rows = [row for row in wfo_rows if not row.get("rejected")]
        if valid_rows:
            wins = sum(1 for row in valid_rows if float(row["delta_score"]) > 0)
            payload["wfo_overlay_win_rate"] = round(wins / len(valid_rows), 6)
            payload["wfo_overlay_valid_windows"] = len(valid_rows)

        json_path = write_json(payload, ctx.results_dir / "overlay_comparison.json")
        artifacts.append(json_path)

        return SuiteResult(
            name=self.name(),
            status="info",
            data=payload,
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
