"""Churn metrics suite for churn/latency/fee-drag diagnostics."""

from __future__ import annotations

import math
import statistics
import time
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from validation.output import write_csv
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.common import ensure_backtest

_MS_PER_DAY = 86_400_000.0
_DEFAULT_BAR_MS = 14_400_000.0
_DAYS_PER_MONTH = 365.25 / 12.0
_ISSUE_LIMIT = 50

_DEFAULT_WARNING_FEE_DRAG_PCT = 20.0
_DEFAULT_WARNING_CASCADE_LEQ3_PCT = 30.0
_DEFAULT_WARNING_CASCADE_LEQ6_PCT = 50.0

_EXIT_REASONS = [
    "emergency_dd",
    "trailing_stop",
    "fixed_stop",
    "regime_off",
    "structural_breakdown",
    "hma_breakdown",
    "peak_dd_stop",
    "mr_defensive_exit",
    "time_exit",
    "other_exit",
]

_FIELDNAMES = [
    "strategy_id",
    "scenario",
    "period_start",
    "period_end",
    "trades",
    "trades_per_month",
    "entries_per_week",
    "avg_hold_bars",
    "avg_hold_days",
    "total_fees",
    "fee_drag_pct",
    "turnover",
    "turnover_per_month",
    "share_emergency_dd",
    "share_trailing_stop",
    "share_fixed_stop",
    "share_regime_off",
    "share_structural_breakdown",
    "share_hma_breakdown",
    "share_peak_dd_stop",
    "share_mr_defensive_exit",
    "share_time_exit",
    "share_other_exit",
    "reentry_median_bars",
    "reentry_p90_bars",
    "cascade_leq1",
    "cascade_leq3",
    "cascade_leq6",
    "cascade_leq12",
    "buy_sell_ratio",
]

_NUMERIC_FIELDS = [
    "trades",
    "trades_per_month",
    "entries_per_week",
    "avg_hold_bars",
    "avg_hold_days",
    "total_fees",
    "fee_drag_pct",
    "turnover",
    "turnover_per_month",
    "share_emergency_dd",
    "share_trailing_stop",
    "share_fixed_stop",
    "share_regime_off",
    "share_structural_breakdown",
    "share_hma_breakdown",
    "share_peak_dd_stop",
    "share_mr_defensive_exit",
    "share_time_exit",
    "share_other_exit",
    "reentry_median_bars",
    "reentry_p90_bars",
    "cascade_leq1",
    "cascade_leq3",
    "cascade_leq6",
    "cascade_leq12",
    "buy_sell_ratio",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def _round(value: float, digits: int = 6) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return round(float(value), digits)


def _entry_ts(trade: object) -> int:
    if hasattr(trade, "entry_ts_ms"):
        return int(trade.entry_ts_ms)
    return int(getattr(trade, "entry_time", 0))


def _exit_ts(trade: object) -> int:
    if hasattr(trade, "exit_ts_ms"):
        return int(trade.exit_ts_ms)
    return int(getattr(trade, "exit_time", 0))


def _days_held(trade: object) -> float:
    if hasattr(trade, "days_held"):
        return max(0.0, _safe_float(trade.days_held))
    delta_ms = max(0, _exit_ts(trade) - _entry_ts(trade))
    return float(delta_ms) / _MS_PER_DAY


def _infer_bar_ms(ctx: SuiteContext) -> float:
    h4_bars = list(getattr(ctx.feed, "h4_bars", []) or [])
    if len(h4_bars) >= 2:
        diffs = []
        for idx in range(1, len(h4_bars)):
            diff = int(h4_bars[idx].open_time) - int(h4_bars[idx - 1].open_time)
            if diff > 0:
                diffs.append(float(diff))
        if diffs:
            return float(statistics.median(diffs))
    if h4_bars:
        span = int(h4_bars[0].close_time) - int(h4_bars[0].open_time) + 1
        if span > 0:
            return float(span)
    return _DEFAULT_BAR_MS


def _period_bounds(ctx: SuiteContext) -> tuple[int, int]:
    h4_bars = list(getattr(ctx.feed, "h4_bars", []) or [])
    if not h4_bars:
        return 0, 0
    start_ms = int(getattr(ctx.feed, "report_start_ms", 0) or h4_bars[0].open_time)
    end_ms = int(h4_bars[-1].close_time)
    if end_ms < start_ms:
        start_ms = int(h4_bars[0].open_time)
    return start_ms, end_ms


def _to_iso(ms: int) -> str:
    if ms < 0:
        return ""
    dt = datetime.fromtimestamp(ms / 1000.0, tz=UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_exit_reason(reason: Any) -> str:
    text = str(reason or "").strip().lower()
    if text in _EXIT_REASONS:
        return text
    return "other_exit"


def _fee_turnover_buy_sell(
    trades: list[object],
    fills: list[object],
    summary: dict[str, Any],
) -> tuple[float, float, int, int, str]:
    if fills:
        total_fees = 0.0
        turnover = 0.0
        buy_fills = 0
        sell_fills = 0
        for fill in fills:
            total_fees += max(0.0, _safe_float(getattr(fill, "fee", 0.0)))
            turnover += max(0.0, _safe_float(getattr(fill, "notional", 0.0)))
            side = getattr(fill, "side", "")
            side_text = str(getattr(side, "value", side)).upper()
            if side_text.endswith("BUY"):
                buy_fills += 1
            elif side_text.endswith("SELL"):
                sell_fills += 1
        return total_fees, turnover, buy_fills, sell_fills, "fills"

    total_fees = max(0.0, _safe_float(summary.get("fees_total"), 0.0))
    turnover = max(0.0, _safe_float(summary.get("turnover_notional"), 0.0))
    if turnover <= 0.0:
        turnover = sum(
            max(
                0.0,
                _safe_float(getattr(trade, "qty", 0.0))
                * (
                    _safe_float(getattr(trade, "entry_price", 0.0))
                    + _safe_float(getattr(trade, "exit_price", 0.0))
                ),
            )
            for trade in trades
        )
    n_trades = len(trades)
    return total_fees, turnover, n_trades, n_trades, "trades_approx"


def _exit_reason_shares(trades: list[object]) -> tuple[dict[str, float], dict[str, int]]:
    counts = {reason: 0 for reason in _EXIT_REASONS}
    for trade in trades:
        reason = _normalize_exit_reason(getattr(trade, "exit_reason", ""))
        counts[reason] = counts.get(reason, 0) + 1

    total = len(trades)
    if total <= 0:
        return {f"share_{reason}": 0.0 for reason in _EXIT_REASONS}, counts

    shares = {
        f"share_{reason}": _round(counts.get(reason, 0) / total, 6)
        for reason in _EXIT_REASONS
    }
    return shares, counts


def _p90(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, int(math.ceil(0.9 * len(ordered))) - 1)
    return float(ordered[rank])


def _reentry_metrics(trades: list[object], bar_ms: float) -> dict[str, float]:
    entries = sorted(_entry_ts(trade) for trade in trades if _entry_ts(trade) > 0)
    emergency_exits = sorted(
        _exit_ts(trade)
        for trade in trades
        if _normalize_exit_reason(getattr(trade, "exit_reason", "")) == "emergency_dd"
    )

    n_emergency = len(emergency_exits)
    if n_emergency <= 0:
        return {
            "n_emergency_exits": 0.0,
            "reentry_median_bars": 0.0,
            "reentry_p90_bars": 0.0,
            "cascade_leq1": 0.0,
            "cascade_leq3": 0.0,
            "cascade_leq6": 0.0,
            "cascade_leq12": 0.0,
        }

    entry_idx = 0
    latencies: list[float] = []
    for exit_ts in emergency_exits:
        while entry_idx < len(entries) and entries[entry_idx] <= exit_ts:
            entry_idx += 1
        if entry_idx >= len(entries):
            continue
        delta_ms = max(0, entries[entry_idx] - exit_ts)
        if bar_ms <= 0:
            latency_bars = 0.0
        else:
            latency_bars = float(int(math.floor((delta_ms + (bar_ms * 0.5)) / bar_ms)))
        latencies.append(max(0.0, latency_bars))

    def _cascade_rate(max_bars: int) -> float:
        if n_emergency <= 0:
            return 0.0
        n_within = sum(1 for latency in latencies if latency <= max_bars)
        return _round((100.0 * n_within) / n_emergency, 6)

    return {
        "n_emergency_exits": float(n_emergency),
        "reentry_median_bars": _round(float(statistics.median(latencies)) if latencies else 0.0, 6),
        "reentry_p90_bars": _round(_p90(latencies), 6),
        "cascade_leq1": _cascade_rate(1),
        "cascade_leq3": _cascade_rate(3),
        "cascade_leq6": _cascade_rate(6),
        "cascade_leq12": _cascade_rate(12),
    }


def _row_issues(rows: list[dict[str, Any]]) -> list[str]:
    issues: list[str] = []
    if not rows:
        return ["no_rows"]

    for idx, row in enumerate(rows, start=1):
        missing = [field for field in _FIELDNAMES if field not in row]
        if missing:
            issues.append(f"row_{idx}_missing_fields:{','.join(missing)}")
        for field in _NUMERIC_FIELDS:
            value = row.get(field)
            try:
                num = float(value)
            except (TypeError, ValueError):
                issues.append(f"row_{idx}_{field}_non_numeric:{value!r}")
                continue
            if math.isnan(num) or math.isinf(num):
                issues.append(f"row_{idx}_{field}_non_finite:{value!r}")
        if len(issues) >= _ISSUE_LIMIT:
            issues.append(f"issue_limit_reached:{_ISSUE_LIMIT}")
            return issues

    return issues


def _compute_row(
    strategy_id: str,
    scenario: str,
    result: object,
    period_start_ms: int,
    period_end_ms: int,
    bar_ms: float,
    warning_fee_drag_pct: float,
    warning_cascade_leq3_pct: float,
    warning_cascade_leq6_pct: float,
) -> tuple[dict[str, Any], list[str], str]:
    trades = list(getattr(result, "trades", []) or [])
    fills = list(getattr(result, "fills", []) or [])
    summary = dict(getattr(result, "summary", {}) or {})

    n_trades = len(trades)
    span_days = max((period_end_ms - period_start_ms) / _MS_PER_DAY, 1.0)
    span_months = max(span_days / _DAYS_PER_MONTH, 1e-9)
    span_weeks = max(span_days / 7.0, 1e-9)

    hold_days = [_days_held(trade) for trade in trades]
    hold_bars = [
        max(0.0, (_exit_ts(trade) - _entry_ts(trade)) / max(bar_ms, 1.0))
        for trade in trades
    ]

    total_fees, turnover, buy_fills, sell_fills, events_source = _fee_turnover_buy_sell(trades, fills, summary)
    abs_gross_pnl = sum(abs(_safe_float(getattr(trade, "pnl", 0.0))) for trade in trades)
    fee_drag_pct = 100.0 * total_fees / abs_gross_pnl if abs_gross_pnl > 1e-12 else 0.0

    shares, reason_counts = _exit_reason_shares(trades)
    reentry = _reentry_metrics(trades, bar_ms)

    if sell_fills > 0:
        buy_sell_ratio = float(buy_fills) / float(sell_fills)
    elif buy_fills > 0:
        buy_sell_ratio = float(buy_fills)
    else:
        buy_sell_ratio = 0.0

    row = {
        "strategy_id": strategy_id,
        "scenario": scenario,
        "period_start": _to_iso(period_start_ms),
        "period_end": _to_iso(period_end_ms),
        "trades": int(n_trades),
        "trades_per_month": _round(n_trades / span_months, 6),
        "entries_per_week": _round(n_trades / span_weeks, 6),
        "avg_hold_bars": _round(float(sum(hold_bars) / max(len(hold_bars), 1)), 6),
        "avg_hold_days": _round(float(sum(hold_days) / max(len(hold_days), 1)), 6),
        "total_fees": _round(total_fees, 6),
        # Definition: total_fees / abs_gross_pnl * 100.
        "fee_drag_pct": _round(fee_drag_pct, 6),
        "turnover": _round(turnover, 6),
        "turnover_per_month": _round(turnover / span_months, 6),
        "share_emergency_dd": shares["share_emergency_dd"],
        "share_trailing_stop": shares["share_trailing_stop"],
        "share_fixed_stop": shares["share_fixed_stop"],
        "share_regime_off": shares["share_regime_off"],
        "share_structural_breakdown": shares["share_structural_breakdown"],
        "share_hma_breakdown": shares["share_hma_breakdown"],
        "share_peak_dd_stop": shares["share_peak_dd_stop"],
        "share_mr_defensive_exit": shares["share_mr_defensive_exit"],
        "share_time_exit": shares["share_time_exit"],
        "share_other_exit": shares["share_other_exit"],
        "reentry_median_bars": reentry["reentry_median_bars"],
        "reentry_p90_bars": reentry["reentry_p90_bars"],
        "cascade_leq1": reentry["cascade_leq1"],
        "cascade_leq3": reentry["cascade_leq3"],
        "cascade_leq6": reentry["cascade_leq6"],
        "cascade_leq12": reentry["cascade_leq12"],
        "buy_sell_ratio": _round(buy_sell_ratio, 6),
    }

    warnings: list[str] = []
    if row["fee_drag_pct"] >= warning_fee_drag_pct:
        warnings.append(
            f"WARNING {strategy_id}/{scenario}: fee_drag_pct={row['fee_drag_pct']:.3f} "
            f">= {warning_fee_drag_pct:.3f}"
        )
    if reason_counts.get("emergency_dd", 0) > 0 and row["cascade_leq3"] >= warning_cascade_leq3_pct:
        warnings.append(
            f"WARNING {strategy_id}/{scenario}: cascade_leq3={row['cascade_leq3']:.3f} "
            f">= {warning_cascade_leq3_pct:.3f}"
        )
    if reason_counts.get("emergency_dd", 0) > 0 and row["cascade_leq6"] >= warning_cascade_leq6_pct:
        warnings.append(
            f"WARNING {strategy_id}/{scenario}: cascade_leq6={row['cascade_leq6']:.3f} "
            f">= {warning_cascade_leq6_pct:.3f}"
        )
    return row, warnings, events_source


class ChurnMetricsSuite(BaseSuite):
    def name(self) -> str:
        return "churn_metrics"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if ctx.validation_config.churn_metrics is False:
            return "churn metrics disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        warning_fee_drag_pct = float(
            getattr(cfg, "churn_warning_fee_drag_pct", _DEFAULT_WARNING_FEE_DRAG_PCT)
        )
        warning_cascade_leq3_pct = float(
            getattr(cfg, "churn_warning_cascade_leq3_pct", _DEFAULT_WARNING_CASCADE_LEQ3_PCT)
        )
        warning_cascade_leq6_pct = float(
            getattr(cfg, "churn_warning_cascade_leq6_pct", _DEFAULT_WARNING_CASCADE_LEQ6_PCT)
        )

        scenarios = [str(item) for item in cfg.scenarios if str(item).strip()]
        if not scenarios:
            scenarios = ["base"]

        period_start_ms, period_end_ms = _period_bounds(ctx)
        bar_ms = _infer_bar_ms(ctx)

        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        event_sources: set[str] = set()

        for scenario in scenarios:
            for strategy_id in ["candidate", "baseline"]:
                result = ensure_backtest(ctx, strategy_id, scenario)
                row, row_warnings, events_source = _compute_row(
                    strategy_id=strategy_id,
                    scenario=scenario,
                    result=result,
                    period_start_ms=period_start_ms,
                    period_end_ms=period_end_ms,
                    bar_ms=bar_ms,
                    warning_fee_drag_pct=warning_fee_drag_pct,
                    warning_cascade_leq3_pct=warning_cascade_leq3_pct,
                    warning_cascade_leq6_pct=warning_cascade_leq6_pct,
                )
                rows.append(row)
                warnings.extend(row_warnings)
                event_sources.add(events_source)

        csv_path = write_csv(
            rows,
            ctx.results_dir / "churn_metrics.csv",
            fieldnames=_FIELDNAMES,
        )
        artifacts.append(csv_path)

        issues = _row_issues(rows)
        status = "pass" if not issues else "fail"
        if issues:
            warnings.append(f"WARNING churn_metrics schema/data issues detected ({len(issues)})")

        return SuiteResult(
            name=self.name(),
            status=status,
            data={
                "rows": rows,
                "row_count": len(rows),
                "fieldnames": _FIELDNAMES,
                "issues": issues,
                "warnings": warnings,
                "warning_thresholds": {
                    "fee_drag_pct": warning_fee_drag_pct,
                    "cascade_leq3": warning_cascade_leq3_pct,
                    "cascade_leq6": warning_cascade_leq6_pct,
                },
                "fee_drag_definition": "fee_drag_pct = 100 * total_fees / abs_gross_pnl",
                "abs_gross_pnl_definition": "abs_gross_pnl = sum(abs(trade.pnl))",
                "event_source": ",".join(sorted(event_sources)) if event_sources else "unknown",
                "period_start": _to_iso(period_start_ms),
                "period_end": _to_iso(period_end_ms),
            },
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
