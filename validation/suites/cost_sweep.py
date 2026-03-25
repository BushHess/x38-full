"""Cost-sweep suite for execution-cost robustness checks."""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

from v10.core.engine import BacktestEngine
from v10.core.types import CostConfig, SCENARIOS
from v10.research.objective import compute_objective
from validation.output import write_csv
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult

_MS_PER_DAY = 86_400_000
_MS_PER_YEAR = 365.25 * 24.0 * 3600.0 * 1000.0
_H4_BARS_PER_YEAR = int((24.0 / 4.0) * 365.0)
_QUICK_REPORT_YEARS = 3.0
_QUICK_MIN_H4 = 800
_QUICK_MIN_D1 = 120
_ROW_ISSUE_LIMIT = 50


class _FeedSlice:
    def __init__(self, h4_bars: list[object], d1_bars: list[object], report_start_ms: int | None):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars
        self.report_start_ms = report_start_ms


def _cost_from_round_trip_bps(round_trip_bps: float) -> CostConfig:
    base = SCENARIOS["base"]
    if round_trip_bps <= 0:
        return CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.0)

    scale = round_trip_bps / max(base.round_trip_bps, 1e-9)
    return CostConfig(
        spread_bps=base.spread_bps * scale,
        slippage_bps=base.slippage_bps * scale,
        taker_fee_pct=base.taker_fee_pct * scale,
    )


def _estimate_report_years(feed: object) -> float:
    h4 = getattr(feed, "h4_bars", [])
    if not h4:
        return 0.0
    report_start_ms = getattr(feed, "report_start_ms", None)
    if report_start_ms is None:
        report_start_ms = int(h4[0].close_time)
    last_close_ms = int(h4[-1].close_time)
    if last_close_ms <= int(report_start_ms):
        return 0.0
    return (last_close_ms - int(report_start_ms)) / _MS_PER_YEAR


def _make_quick_feed(ctx: SuiteContext) -> tuple[object, str, dict[str, Any]]:
    full_feed = ctx.feed
    total_h4 = len(full_feed.h4_bars)
    target_report_h4 = max(int(_QUICK_REPORT_YEARS * _H4_BARS_PER_YEAR), _QUICK_MIN_H4)
    if total_h4 <= target_report_h4:
        return full_feed, "full_fallback", {
            "quick_target_years": _QUICK_REPORT_YEARS,
            "reason": "insufficient_h4_for_quick_subset",
        }

    report_h4 = min(target_report_h4, max(_QUICK_MIN_H4, total_h4 // 2))
    report_start_ms = int(full_feed.h4_bars[-report_h4].open_time)
    warmup_ms = int(ctx.validation_config.warmup_days) * _MS_PER_DAY
    load_start_ms = report_start_ms - warmup_ms

    h4 = [bar for bar in full_feed.h4_bars if int(bar.open_time) >= load_start_ms]
    d1 = [bar for bar in full_feed.d1_bars if int(bar.open_time) >= (load_start_ms - 30 * _MS_PER_DAY)]

    if len(h4) < _QUICK_MIN_H4 or len(d1) < _QUICK_MIN_D1:
        return full_feed, "full_fallback", {
            "quick_target_years": _QUICK_REPORT_YEARS,
            "reason": "insufficient_h4_or_d1_after_slice",
        }

    sliced = _FeedSlice(h4_bars=h4, d1_bars=d1, report_start_ms=report_start_ms)
    return sliced, "quick", {
        "quick_target_years": _QUICK_REPORT_YEARS,
        "report_h4_bars": report_h4,
        "slice_h4_bars": len(h4),
        "slice_d1_bars": len(d1),
        "report_years_estimated": round(_estimate_report_years(sliced), 4),
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _validate_rows(rows: list[dict[str, Any]], bps_values: list[float], strategy_ids: list[str]) -> list[str]:
    issues: list[str] = []
    expected_rows = len(bps_values) * len(strategy_ids)
    if len(rows) != expected_rows:
        issues.append(f"row_count_mismatch: expected={expected_rows}, got={len(rows)}")

    seen_pairs = {(float(row.get("bps", -1)), str(row.get("strategy_id", ""))) for row in rows}
    for bps in bps_values:
        for strategy_id in strategy_ids:
            if (float(bps), strategy_id) not in seen_pairs:
                issues.append(f"missing_pair: bps={bps}, strategy_id={strategy_id}")

    numeric_fields = ["bps", "final_nav", "CAGR", "MDD", "turnover", "total_fees", "score_primary"]
    for idx, row in enumerate(rows, start=1):
        for field in numeric_fields:
            if not _is_finite_number(row.get(field)):
                issues.append(f"row_{idx}_{field}_non_numeric: {row.get(field)!r}")

        trades_raw = row.get("trades")
        try:
            trades_int = int(trades_raw)
        except (TypeError, ValueError):
            issues.append(f"row_{idx}_trades_non_int: {trades_raw!r}")
            trades_int = 0
        if trades_int < 0:
            issues.append(f"row_{idx}_trades_negative: {trades_int}")
        row["trades"] = trades_int

        if _is_finite_number(row.get("turnover")) and float(row["turnover"]) < 0:
            issues.append(f"row_{idx}_turnover_negative: {row['turnover']}")
        if _is_finite_number(row.get("total_fees")) and float(row["total_fees"]) < 0:
            issues.append(f"row_{idx}_total_fees_negative: {row['total_fees']}")

        if len(issues) >= _ROW_ISSUE_LIMIT:
            issues.append(f"issue_limit_reached:{_ROW_ISSUE_LIMIT}")
            return issues

    return issues


class CostSweepSuite(BaseSuite):
    def name(self) -> str:
        return "cost_sweep"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if not ctx.validation_config.cost_sweep_bps:
            return "cost sweep bps list is empty"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        artifacts: list[Path] = []
        cfg = ctx.validation_config

        feed = ctx.feed
        mode_used = "full"
        mode_meta: dict[str, Any] = {}
        if cfg.cost_sweep_mode == "quick":
            feed, mode_used, mode_meta = _make_quick_feed(ctx)

        bps_values = sorted({float(x) for x in cfg.cost_sweep_bps})
        rows: list[dict] = []
        strategy_specs = [
            ("candidate", ctx.candidate_factory),
            ("baseline", ctx.baseline_factory),
        ]

        for bps in bps_values:
            cost = _cost_from_round_trip_bps(bps)
            for strategy_id, factory in strategy_specs:
                ctx.logger.info("  cost_sweep: %s @ %.2f bps (%s)", strategy_id, bps, mode_used)
                engine = BacktestEngine(
                    feed=feed,
                    strategy=factory(),
                    cost=cost,
                    initial_cash=cfg.initial_cash,
                    warmup_days=cfg.warmup_days,
                )
                result = engine.run()
                summary = dict(result.summary)
                score_primary = float(compute_objective(summary))
                rows.append(
                    {
                        "bps": round(float(bps), 6),
                        "strategy_id": strategy_id,
                        "final_nav": round(_to_float(summary.get("final_nav_mid")), 6),
                        "CAGR": round(_to_float(summary.get("cagr_pct")), 6),
                        "MDD": round(_to_float(summary.get("max_drawdown_mid_pct")), 6),
                        "trades": int(summary.get("trades", 0) or 0),
                        # Turnover uses annualized normalization from summary.
                        "turnover": round(_to_float(summary.get("turnover_per_year")), 6),
                        "total_fees": round(_to_float(summary.get("fees_total")), 6),
                        "score_primary": round(score_primary, 6),
                    }
                )

        strategy_ids = [item[0] for item in strategy_specs]
        issues = _validate_rows(rows, bps_values, strategy_ids)
        expected_rows = len(bps_values) * len(strategy_ids)

        csv_path = write_csv(
            rows,
            ctx.results_dir / "cost_sweep.csv",
            fieldnames=[
                "bps",
                "strategy_id",
                "final_nav",
                "CAGR",
                "MDD",
                "trades",
                "turnover",
                "total_fees",
                "score_primary",
            ],
        )
        artifacts.append(csv_path)

        status = "pass" if not issues else "fail"
        return SuiteResult(
            name=self.name(),
            status=status,
            data={
                "mode_requested": cfg.cost_sweep_mode,
                "mode_used": mode_used,
                "mode_meta": mode_meta,
                "cost_bps": bps_values,
                "strategy_ids": strategy_ids,
                "rows": rows,
                "n_rows": len(rows),
                "expected_rows": expected_rows,
                "metrics_consistent": not issues,
                "issues": issues,
                "score_primary_note": (
                    "score_primary = compute_objective(summary), cost-dependent; "
                    "returns -1_000_000 when trades < 10."
                ),
                "turnover_note": "turnover = turnover_per_year from backtest summary",
                "report_years_estimated": round(_estimate_report_years(feed), 4),
            },
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
