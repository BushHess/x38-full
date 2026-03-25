"""Trade-level suite: exports, deterministic matching, and time-aware bootstrap."""

from __future__ import annotations

import math
import time
from datetime import UTC
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
from v10.core.types import EquitySnap
from v10.core.types import Fill
from v10.core.types import Side
from v10.research.drawdown import detect_drawdown_episodes
from v10.research.regime import classify_d1_regimes
from v10.research.wfo import generate_windows

from validation.output import write_csv
from validation.output import write_json
from validation.output import write_text
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.common import ensure_backtest
from validation.suites.common import iso_to_ms

H4_BAR_MS = 4 * 60 * 60 * 1000
BOOTSTRAP_BLOCK_LENGTHS = (42, 84, 168)
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_MIN_OBS = 20  # minimum observations for meaningful block bootstrap
SMALL_MEAN_IMPROVEMENT_THRESHOLD = 0.0002
ENTRY_RISK_ORDINAL = {
    "low_non_chop": 0,
    "medium_chop": 1,
    "high_chop_stretch": 2,
    "untagged": 3,
}


def _ms_to_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry_ts_ms(trade: object) -> int:
    if hasattr(trade, "entry_ts_ms"):
        return int(trade.entry_ts_ms)
    return int(getattr(trade, "entry_time", 0))


def _exit_ts_ms(trade: object) -> int:
    if hasattr(trade, "exit_ts_ms"):
        return int(trade.exit_ts_ms)
    return int(getattr(trade, "exit_time", 0))


def _return_pct(trade: object) -> float:
    if hasattr(trade, "return_pct"):
        return float(trade.return_pct or 0.0)
    if hasattr(trade, "pnl_pct"):
        return float(trade.pnl_pct or 0.0)
    return 0.0


def _days_held(trade: object) -> float:
    if hasattr(trade, "days_held"):
        return float(trade.days_held or 0.0)
    if hasattr(trade, "bars_held"):
        return float(trade.bars_held or 0.0) * (4.0 / 24.0)
    return 0.0


def _trade_side(trade: object) -> str:
    if hasattr(trade, "side"):
        side = str(trade.side).strip().lower()
        if side:
            return side
    return "long"


def _regime_map(d1_bars: list, regimes: list[str]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for idx, bar in enumerate(d1_bars):
        if idx < len(regimes):
            mapping[bar.close_time // 86_400_000] = str(regimes[idx])
    return mapping


def _fills_for_trade(fills: list[Fill], entry_ts_ms: int, exit_ts_ms: int) -> list[Fill]:
    return [fill for fill in fills if entry_ts_ms <= int(fill.ts_ms) <= exit_ts_ms]


def _parse_entry_risk(entry_reason: str) -> str:
    text = str(entry_reason or "")
    for part in text.split("|"):
        if part.startswith("risk="):
            value = part.split("=", 1)[1].strip()
            return value or "untagged"
    return "untagged"


def _trade_exposure_stats(
    *,
    entry_ts_ms: int,
    exit_ts_ms: int,
    equity: list[EquitySnap],
    equity_close_times: np.ndarray,
    equity_exposures: np.ndarray,
) -> tuple[float, float, float]:
    if len(equity) == 0:
        return 0.0, 0.0, 0.0

    start_idx = int(np.searchsorted(equity_close_times, entry_ts_ms, side="left"))
    end_idx = int(np.searchsorted(equity_close_times, exit_ts_ms + H4_BAR_MS, side="left"))
    if end_idx <= start_idx:
        end_idx = min(start_idx + 1, len(equity_exposures))
    window = equity_exposures[start_idx:end_idx]
    if window.size == 0:
        return 0.0, 0.0, 0.0

    exposure_at_entry = float(window[0])
    exposure_at_exit = float(window[-1])
    max_exposure = float(np.max(window))
    return exposure_at_entry, exposure_at_exit, max_exposure


def _trade_row(
    *,
    label: str,
    trade: object,
    fills: list[Fill],
    equity: list[EquitySnap],
    equity_close_times: np.ndarray,
    equity_exposures: np.ndarray,
    regime_map: dict[int, str],
) -> dict[str, Any]:
    entry_ts_ms = _entry_ts_ms(trade)
    exit_ts_ms = _exit_ts_ms(trade)
    matched_fills = _fills_for_trade(fills, entry_ts_ms, exit_ts_ms)
    fees_usd = float(sum(float(fill.fee) for fill in matched_fills))
    n_buy_fills = int(sum(1 for fill in matched_fills if fill.side == Side.BUY))
    n_sell_fills = int(sum(1 for fill in matched_fills if fill.side == Side.SELL))
    exposure_entry, exposure_exit, exposure_max = _trade_exposure_stats(
        entry_ts_ms=entry_ts_ms,
        exit_ts_ms=exit_ts_ms,
        equity=equity,
        equity_close_times=equity_close_times,
        equity_exposures=equity_exposures,
    )

    return {
        "label": label,
        "trade_id": int(getattr(trade, "trade_id", 0)),
        "side": _trade_side(trade),
        "entry_ts": _ms_to_iso(entry_ts_ms),
        "exit_ts": _ms_to_iso(exit_ts_ms),
        "entry_ts_ms": entry_ts_ms,
        "exit_ts_ms": exit_ts_ms,
        "return_pct": round(_return_pct(trade), 6),
        "pnl_usd": round(float(getattr(trade, "pnl", 0.0)), 6),
        "fees_usd": round(fees_usd, 6),
        "n_buy_fills": n_buy_fills,
        "n_sell_fills": n_sell_fills,
        "entry_reason": str(getattr(trade, "entry_reason", "")),
        "entry_risk_level": _parse_entry_risk(str(getattr(trade, "entry_reason", ""))),
        "exit_reason": str(getattr(trade, "exit_reason", "")),
        "max_exposure_during_trade": round(exposure_max, 6),
        "exposure_at_entry": round(exposure_entry, 6),
        "exposure_at_exit": round(exposure_exit, 6),
        "entry_price": round(float(getattr(trade, "entry_price", 0.0)), 6),
        "exit_price": round(float(getattr(trade, "exit_price", 0.0)), 6),
        "qty": round(float(getattr(trade, "qty", 0.0)), 8),
        "days_held": round(_days_held(trade), 6),
        "regime": regime_map.get(entry_ts_ms // 86_400_000, "UNKNOWN"),
    }


def _sort_trade_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            int(row.get("entry_ts_ms", 0)),
            int(row.get("trade_id", 0)),
        ),
    )


def _build_matched_row(
    cand: dict[str, Any],
    base: dict[str, Any],
) -> dict[str, Any]:
    """Build a matched-pair row from a candidate and baseline trade row."""
    delta_ms = abs(int(cand["entry_ts_ms"]) - int(base["entry_ts_ms"]))
    return {
        "candidate_trade_id": int(cand["trade_id"]),
        "baseline_trade_id": int(base["trade_id"]),
        "side": str(cand.get("side", "long")),
        "candidate_entry_ts": str(cand["entry_ts"]),
        "baseline_entry_ts": str(base["entry_ts"]),
        "candidate_exit_ts": str(cand["exit_ts"]),
        "baseline_exit_ts": str(base["exit_ts"]),
        "entry_ts_delta_ms": int(delta_ms),
        "entry_ts_delta_bars": round(delta_ms / H4_BAR_MS, 6),
        "candidate_return_pct": round(float(cand["return_pct"]), 6),
        "baseline_return_pct": round(float(base["return_pct"]), 6),
        "delta_return_pct": round(float(cand["return_pct"]) - float(base["return_pct"]), 6),
        "candidate_pnl_usd": round(float(cand["pnl_usd"]), 6),
        "baseline_pnl_usd": round(float(base["pnl_usd"]), 6),
        "delta_pnl": round(float(cand["pnl_usd"]) - float(base["pnl_usd"]), 6),
        "candidate_fees_usd": round(float(cand["fees_usd"]), 6),
        "baseline_fees_usd": round(float(base["fees_usd"]), 6),
        "delta_fees_usd": round(float(cand["fees_usd"]) - float(base["fees_usd"]), 6),
        "candidate_entry_reason": str(cand["entry_reason"]),
        "baseline_entry_reason": str(base["entry_reason"]),
        "candidate_entry_risk_level": str(cand.get("entry_risk_level", "untagged")),
        "baseline_entry_risk_level": str(base.get("entry_risk_level", "untagged")),
        "candidate_exit_reason": str(cand["exit_reason"]),
        "baseline_exit_reason": str(base["exit_reason"]),
        "candidate_max_exposure_during_trade": round(float(cand["max_exposure_during_trade"]), 6),
        "baseline_max_exposure_during_trade": round(float(base["max_exposure_during_trade"]), 6),
        "candidate_exposure_at_entry": round(float(cand["exposure_at_entry"]), 6),
        "baseline_exposure_at_entry": round(float(base["exposure_at_entry"]), 6),
        "candidate_exposure_at_exit": round(float(cand["exposure_at_exit"]), 6),
        "baseline_exposure_at_exit": round(float(base["exposure_at_exit"]), 6),
        "candidate_win": int(float(cand["pnl_usd"]) > 0.0),
        "baseline_win": int(float(base["pnl_usd"]) > 0.0),
    }


def _match_trades(
    candidate_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    *,
    tolerance_ms: int = H4_BAR_MS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Match candidate and baseline trades using optimal assignment.

    Uses the Hungarian algorithm (scipy.optimize.linear_sum_assignment) to
    find the assignment that maximizes match count, then minimizes total
    entry-timestamp distance among tied solutions.  Trades must share the
    same side and have entry timestamps within *tolerance_ms*.
    """
    from scipy.optimize import linear_sum_assignment as _linear_sum_assignment

    candidate_sorted = _sort_trade_rows(candidate_rows)
    baseline_sorted = _sort_trade_rows(baseline_rows)

    n_cand = len(candidate_sorted)
    n_base = len(baseline_sorted)

    if n_cand == 0:
        return [], [], list(baseline_sorted)
    if n_base == 0:
        return [], list(candidate_sorted), []

    # Build cost matrix.  Eligible pairs get their distance; ineligible pairs
    # get a penalty large enough that the algorithm will never prefer an
    # ineligible assignment over leaving a slot unmatched.
    big = float(tolerance_ms + 1) * (min(n_cand, n_base) + 1)
    cost = np.full((n_cand, n_base), big, dtype=np.float64)

    for i, cand in enumerate(candidate_sorted):
        cand_entry = int(cand.get("entry_ts_ms", 0))
        cand_side = str(cand.get("side", "long"))
        for j, base in enumerate(baseline_sorted):
            if str(base.get("side", "long")) != cand_side:
                continue
            base_entry = int(base.get("entry_ts_ms", 0))
            distance = abs(cand_entry - base_entry)
            if distance <= tolerance_ms:
                # Tiebreak: among equal distances, prefer earlier baseline
                # index (which inherits sort order by entry_ts_ms, trade_id).
                cost[i, j] = float(distance) + float(j) / (n_base + 1.0) * 0.5

    row_ind, col_ind = _linear_sum_assignment(cost)

    matched_cand_set: set[int] = set()
    matched_base_set: set[int] = set()
    matched_rows: list[dict[str, Any]] = []

    for i, j in zip(row_ind, col_ind):
        if cost[i, j] >= big:
            continue
        matched_cand_set.add(i)
        matched_base_set.add(j)
        matched_rows.append(
            _build_matched_row(candidate_sorted[i], baseline_sorted[j])
        )

    candidate_only = [c for i, c in enumerate(candidate_sorted) if i not in matched_cand_set]
    baseline_only = [b for j, b in enumerate(baseline_sorted) if j not in matched_base_set]
    return matched_rows, candidate_only, baseline_only


def _mean_or_zero(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _median_or_zero(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _total_fees_usd(rows: list[dict[str, Any]]) -> float:
    return float(sum(float(row.get("fees_usd", 0.0) or 0.0) for row in rows))


def _share_emergency_dd(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    count = sum(
        1
        for row in rows
        if str(row.get("exit_reason", "")).strip().lower() == "emergency_dd"
    )
    return float(count / max(len(rows), 1))


def _buy_fills_per_episode(
    *,
    equity: list[EquitySnap],
    fills: list[Fill],
    min_dd_pct: float = 5.0,
) -> tuple[float, int]:
    if not equity:
        return 0.0, 0
    episodes = detect_drawdown_episodes(equity, min_dd_pct=min_dd_pct)
    if not episodes:
        return 0.0, 0

    last_close = int(equity[-1].close_time)
    buy_fill_count = 0
    for episode in episodes:
        start_ms = int(episode.peak_ms)
        end_ms = int(episode.recovery_ms) if episode.recovery_ms is not None else last_close
        buy_fill_count += sum(
            1
            for fill in fills
            if fill.side == Side.BUY and start_ms <= int(fill.ts_ms) <= end_ms
        )

    return float(buy_fill_count / max(len(episodes), 1)), int(len(episodes))


def _entry_risk_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        label = str(row.get("label", ""))
        risk = str(row.get("entry_risk_level", "untagged") or "untagged")
        key = (label, risk)
        if key not in grouped:
            grouped[key] = {
                "label": label,
                "entry_risk_level": risk,
                "n_trades": 0,
                "total_pnl": 0.0,
                "win_count": 0,
            }
        bucket = grouped[key]
        bucket["n_trades"] += 1
        pnl = float(row.get("pnl_usd", 0.0) or 0.0)
        bucket["total_pnl"] += pnl
        if pnl > 0.0:
            bucket["win_count"] += 1

    totals_by_label: dict[str, int] = {}
    for row in rows:
        label = str(row.get("label", ""))
        totals_by_label[label] = totals_by_label.get(label, 0) + 1

    out: list[dict[str, Any]] = []
    for (label, risk), bucket in sorted(
        grouped.items(),
        key=lambda item: (
            str(item[0][0]),
            ENTRY_RISK_ORDINAL.get(str(item[0][1]), 99),
            str(item[0][1]),
        ),
    ):
        n_trades = int(bucket["n_trades"])
        total_pnl = float(bucket["total_pnl"])
        win_count = int(bucket["win_count"])
        total_label = int(totals_by_label.get(label, 0))
        out.append(
            {
                "label": label,
                "entry_risk_level": risk,
                "n_trades": n_trades,
                "share_trades": round(n_trades / max(total_label, 1), 6),
                "total_pnl": round(total_pnl, 6),
                "avg_pnl": round(total_pnl / max(n_trades, 1), 6),
                "win_rate": round(win_count / max(n_trades, 1), 6),
                "loss_rate": round((n_trades - win_count) / max(n_trades, 1), 6),
            }
        )
    return out


def _build_trade_level_analysis_report(
    *,
    scenario: str,
    matched_rows: list[dict[str, Any]],
    candidate_only: list[dict[str, Any]],
    baseline_only: list[dict[str, Any]],
    entry_risk_rows: list[dict[str, Any]],
) -> str:
    matched_count = len(matched_rows)
    baseline_only_count = len(baseline_only)
    candidate_only_count = len(candidate_only)

    deltas_pnl = [float(row["delta_pnl"]) for row in matched_rows]
    deltas_return = [float(row["delta_return_pct"]) for row in matched_rows]
    candidate_wins = [int(row["candidate_win"]) for row in matched_rows]
    baseline_wins = [int(row["baseline_win"]) for row in matched_rows]
    candidate_win_rate = _mean_or_zero([float(v) for v in candidate_wins])
    baseline_win_rate = _mean_or_zero([float(v) for v in baseline_wins])
    win_rate_delta = candidate_win_rate - baseline_win_rate

    lines: list[str] = [
        "# Trade-level analysis",
        "",
        f"- Scenario: `{scenario}`",
        f"- matched_count: `{matched_count}`",
        f"- baseline_only_count: `{baseline_only_count}`",
        f"- candidate_only_count: `{candidate_only_count}`",
        "",
        "## Matched trade deltas",
        "",
        f"- mean_delta_pnl: `{_mean_or_zero(deltas_pnl):.6f}`",
        f"- median_delta_pnl: `{_median_or_zero(deltas_pnl):.6f}`",
        f"- mean_delta_return_pct: `{_mean_or_zero(deltas_return):.6f}`",
        f"- median_delta_return_pct: `{_median_or_zero(deltas_return):.6f}`",
        f"- baseline_win_rate: `{baseline_win_rate:.6f}`",
        f"- candidate_win_rate: `{candidate_win_rate:.6f}`",
        f"- win_rate_delta: `{win_rate_delta:.6f}`",
        "",
    ]

    def _append_contrib_table(title: str, rows: list[dict[str, Any]]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| candidate_trade_id | baseline_trade_id | candidate_entry_ts | delta_pnl | delta_return_pct |")
        lines.append("|---:|---:|---|---:|---:|")
        for row in rows:
            lines.append(
                "| "
                f"{int(row['candidate_trade_id'])} | "
                f"{int(row['baseline_trade_id'])} | "
                f"{row['candidate_entry_ts']} | "
                f"{float(row['delta_pnl']):.6f} | "
                f"{float(row['delta_return_pct']):.6f} |"
            )
        if not rows:
            lines.append("| - | - | - | - | - |")
        lines.append("")

    top_positive = sorted(
        matched_rows,
        key=lambda row: (float(row["delta_pnl"]), int(row["candidate_trade_id"])),
        reverse=True,
    )[:10]
    top_negative = sorted(
        matched_rows,
        key=lambda row: (float(row["delta_pnl"]), int(row["candidate_trade_id"])),
    )[:10]

    _append_contrib_table("Top 10 positive contributors (delta_pnl)", top_positive)
    _append_contrib_table("Top 10 negative contributors (delta_pnl)", top_negative)

    tagged_rows = [row for row in entry_risk_rows if row.get("entry_risk_level") != "untagged"]
    if tagged_rows:
        lines.append("## Entry risk cohorts")
        lines.append("")
        lines.append("| Label | Entry risk | Trades | Share | Avg pnl | Total pnl | Win rate | Loss rate |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
        for row in entry_risk_rows:
            lines.append(
                f"| {row.get('label', '')} | "
                f"{row.get('entry_risk_level', '')} | "
                f"{int(row.get('n_trades', 0))} | "
                f"{float(row.get('share_trades', 0.0)):.6f} | "
                f"{float(row.get('avg_pnl', 0.0)):.6f} | "
                f"{float(row.get('total_pnl', 0.0)):.6f} | "
                f"{float(row.get('win_rate', 0.0)):.6f} | "
                f"{float(row.get('loss_rate', 0.0)):.6f} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def _aligned_nav_return_diff(
    candidate_equity: list[EquitySnap],
    baseline_equity: list[EquitySnap],
) -> tuple[np.ndarray, np.ndarray]:
    cand_nav = {int(point.close_time): float(point.nav_mid) for point in candidate_equity}
    base_nav = {int(point.close_time): float(point.nav_mid) for point in baseline_equity}
    common_close_times = sorted(set(cand_nav) & set(base_nav))
    if len(common_close_times) < 2:
        return np.array([], dtype=np.float64), np.array([], dtype=np.int64)

    cand_series = np.array([cand_nav[ts] for ts in common_close_times], dtype=np.float64)
    base_series = np.array([base_nav[ts] for ts in common_close_times], dtype=np.float64)
    valid_prev = (cand_series[:-1] > 0.0) & (base_series[:-1] > 0.0)
    if not np.any(valid_prev):
        return np.array([], dtype=np.float64), np.array([], dtype=np.int64)

    cand_ret = np.diff(cand_series) / cand_series[:-1]
    base_ret = np.diff(base_series) / base_series[:-1]
    diff = cand_ret - base_ret
    ts = np.array(common_close_times[1:], dtype=np.int64)

    finite_mask = np.isfinite(diff) & valid_prev
    if not np.any(finite_mask):
        return np.array([], dtype=np.float64), np.array([], dtype=np.int64)
    return diff[finite_mask], ts[finite_mask]


def _bootstrap_mean_diff_samples(
    series: np.ndarray,
    *,
    block_len: int,
    n_resamples: int,
    seed: int,
) -> np.ndarray:
    n_obs = int(series.size)
    if n_obs <= 0 or n_resamples <= 0:
        return np.array([], dtype=np.float64)

    block = max(1, int(block_len))
    n_blocks = int(math.ceil(n_obs / block))
    rng = np.random.default_rng(seed)
    means = np.empty(n_resamples, dtype=np.float64)

    for idx in range(n_resamples):
        starts = rng.integers(0, n_obs, size=n_blocks)
        indices = np.concatenate([np.arange(start, start + block) % n_obs for start in starts])[:n_obs]
        means[idx] = float(series[indices].mean())
    return means


def _bootstrap_mean_diff_summary(
    series: np.ndarray,
    *,
    block_len: int,
    n_resamples: int,
    seed: int,
) -> dict[str, Any]:
    n_obs = int(series.size)
    if n_obs <= 0:
        return {
            "mean_diff": 0.0,
            "ci95_low": 0.0,
            "ci95_high": 0.0,
            "p_gt_0": 0.5,
            "n_obs": 0,
            "block_len": int(block_len),
            "n_resamples": int(n_resamples),
            "seed": int(seed),
        }

    samples = _bootstrap_mean_diff_samples(
        series,
        block_len=block_len,
        n_resamples=n_resamples,
        seed=seed,
    )
    if samples.size == 0:
        return {
            "mean_diff": float(series.mean()),
            "ci95_low": float(series.mean()),
            "ci95_high": float(series.mean()),
            "p_gt_0": 0.5,
            "n_obs": n_obs,
            "block_len": int(block_len),
            "n_resamples": int(n_resamples),
            "seed": int(seed),
        }

    return {
        "mean_diff": float(series.mean()),
        "ci95_low": float(np.percentile(samples, 2.5)),
        "ci95_high": float(np.percentile(samples, 97.5)),
        "p_gt_0": float((samples > 0.0).mean()),
        "n_obs": n_obs,
        "block_len": int(block_len),
        "n_resamples": int(n_resamples),
        "seed": int(seed),
    }


def _bootstrap_return_diff(
    series: np.ndarray,
    *,
    seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    n_obs = int(series.size)

    # Fail-fast: too few observations for any meaningful block bootstrap.
    if n_obs < BOOTSTRAP_MIN_OBS:
        insufficient = {
            "mean_diff": float(series.mean()) if n_obs > 0 else 0.0,
            "ci95_low": 0.0,
            "ci95_high": 0.0,
            "p_gt_0": 0.5,
            "n_obs": n_obs,
            "block_len": 0,
            "n_resamples": 0,
            "seed": int(seed),
            "insufficient_data": True,
        }
        return insufficient, []

    # Cap each candidate block length at n_obs // 2 so blocks never wrap
    # around the full series (which would produce degenerate CI).
    max_block = max(1, n_obs // 2)
    effective_blocks: list[int] = []
    seen: set[int] = set()
    for bl in BOOTSTRAP_BLOCK_LENGTHS:
        capped = min(bl, max_block)
        if capped not in seen:
            seen.add(capped)
            effective_blocks.append(capped)

    block_summaries: list[dict[str, Any]] = []
    for block_len in effective_blocks:
        block_summaries.append(
            _bootstrap_mean_diff_summary(
                series,
                block_len=block_len,
                n_resamples=BOOTSTRAP_RESAMPLES,
                seed=int(seed) + int(block_len),
            )
        )

    # Select the largest effective block length.
    selected = block_summaries[-1]
    return selected, block_summaries


class TradeLevelSuite(BaseSuite):
    def name(self) -> str:
        return "trade_level"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        cfg = ctx.validation_config
        if not cfg.trade_level and not cfg.auto_trade_level:
            if cfg.suite not in {"trade", "all"}:
                return "trade-level disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        scenario = "harsh" if "harsh" in cfg.scenarios else "base"
        candidate = ensure_backtest(ctx, "candidate", scenario)
        baseline = ensure_backtest(ctx, "baseline", scenario)

        candidate_trades = list(candidate.trades or [])
        baseline_trades = list(baseline.trades or [])
        candidate_fills = list(candidate.fills or [])
        baseline_fills = list(baseline.fills or [])

        candidate_equity = list(candidate.equity or [])
        baseline_equity = list(baseline.equity or [])
        cand_close_times = np.array([int(point.close_time) for point in candidate_equity], dtype=np.int64)
        base_close_times = np.array([int(point.close_time) for point in baseline_equity], dtype=np.int64)
        cand_exposures = np.array([float(point.exposure) for point in candidate_equity], dtype=np.float64)
        base_exposures = np.array([float(point.exposure) for point in baseline_equity], dtype=np.float64)

        regimes = classify_d1_regimes(ctx.feed.d1_bars)
        regime_map = _regime_map(ctx.feed.d1_bars, regimes)

        candidate_rows = _sort_trade_rows(
            [
                _trade_row(
                    label="candidate",
                    trade=trade,
                    fills=candidate_fills,
                    equity=candidate_equity,
                    equity_close_times=cand_close_times,
                    equity_exposures=cand_exposures,
                    regime_map=regime_map,
                )
                for trade in candidate_trades
            ]
        )
        baseline_rows = _sort_trade_rows(
            [
                _trade_row(
                    label="baseline",
                    trade=trade,
                    fills=baseline_fills,
                    equity=baseline_equity,
                    equity_close_times=base_close_times,
                    equity_exposures=base_exposures,
                    regime_map=regime_map,
                )
                for trade in baseline_trades
            ]
        )

        trade_fields = [
            "trade_id",
            "side",
            "entry_ts",
            "exit_ts",
            "return_pct",
            "pnl_usd",
            "fees_usd",
            "n_buy_fills",
            "n_sell_fills",
            "entry_reason",
            "entry_risk_level",
            "exit_reason",
            "max_exposure_during_trade",
            "exposure_at_entry",
            "exposure_at_exit",
            "entry_ts_ms",
            "exit_ts_ms",
            "entry_price",
            "exit_price",
            "qty",
            "days_held",
            "regime",
            "label",
        ]
        cand_csv = write_csv(candidate_rows, ctx.results_dir / "trades_candidate.csv", trade_fields)
        base_csv = write_csv(baseline_rows, ctx.results_dir / "trades_baseline.csv", trade_fields)
        artifacts.extend([cand_csv, base_csv])

        matched_rows, candidate_only, baseline_only = _match_trades(
            candidate_rows,
            baseline_rows,
            tolerance_ms=H4_BAR_MS,
        )
        matched_fields = [
            "candidate_trade_id",
            "baseline_trade_id",
            "side",
            "candidate_entry_ts",
            "baseline_entry_ts",
            "candidate_exit_ts",
            "baseline_exit_ts",
            "entry_ts_delta_ms",
            "entry_ts_delta_bars",
            "candidate_return_pct",
            "baseline_return_pct",
            "delta_return_pct",
            "candidate_pnl_usd",
            "baseline_pnl_usd",
            "delta_pnl",
            "candidate_fees_usd",
            "baseline_fees_usd",
            "delta_fees_usd",
            "candidate_entry_reason",
            "baseline_entry_reason",
            "candidate_entry_risk_level",
            "baseline_entry_risk_level",
            "candidate_exit_reason",
            "baseline_exit_reason",
            "candidate_max_exposure_during_trade",
            "baseline_max_exposure_during_trade",
            "candidate_exposure_at_entry",
            "baseline_exposure_at_entry",
            "candidate_exposure_at_exit",
            "baseline_exposure_at_exit",
            "candidate_win",
            "baseline_win",
        ]
        matched_csv = write_csv(matched_rows, ctx.results_dir / "matched_trades.csv", matched_fields)
        artifacts.append(matched_csv)

        # Regime trade summary for both candidate and baseline.
        regime_summary: dict[tuple[str, str], dict[str, Any]] = {}
        for row in candidate_rows + baseline_rows:
            key = (str(row["label"]), str(row["regime"]))
            if key not in regime_summary:
                regime_summary[key] = {
                    "label": row["label"],
                    "regime": row["regime"],
                    "n_trades": 0,
                    "total_pnl": 0.0,
                    "win_count": 0,
                }
            record = regime_summary[key]
            record["n_trades"] += 1
            record["total_pnl"] += float(row["pnl_usd"])
            if float(row["pnl_usd"]) > 0.0:
                record["win_count"] += 1

        regime_rows: list[dict[str, Any]] = []
        for _, value in sorted(regime_summary.items()):
            n_trades = int(value["n_trades"])
            total_pnl = float(value["total_pnl"])
            win_count = int(value["win_count"])
            regime_rows.append(
                {
                    "label": value["label"],
                    "regime": value["regime"],
                    "n_trades": n_trades,
                    "total_pnl": round(total_pnl, 6),
                    "win_rate": round(win_count / max(n_trades, 1), 6),
                    "avg_pnl": round(total_pnl / max(n_trades, 1), 6),
                }
            )
        regime_csv = write_csv(
            regime_rows,
            ctx.results_dir / "regime_trade_summary.csv",
            ["label", "regime", "n_trades", "total_pnl", "win_rate", "avg_pnl"],
        )
        artifacts.append(regime_csv)

        entry_risk_rows = _entry_risk_summary_rows(candidate_rows + baseline_rows)
        if any(row["entry_risk_level"] != "untagged" for row in entry_risk_rows):
            entry_risk_csv = write_csv(
                entry_risk_rows,
                ctx.results_dir / "entry_risk_summary.csv",
                [
                    "label",
                    "entry_risk_level",
                    "n_trades",
                    "share_trades",
                    "total_pnl",
                    "avg_pnl",
                    "win_rate",
                    "loss_rate",
                ],
            )
            artifacts.append(entry_risk_csv)

        # Window-level trade counts (for WFO low-trade diagnostics).
        windows = generate_windows(
            cfg.start,
            cfg.end,
            train_months=cfg.wfo_train_months,
            test_months=cfg.wfo_test_months,
            slide_months=(cfg.wfo_test_months if cfg.wfo_mode == "fixed" else cfg.wfo_slide_months),
        )
        if cfg.wfo_windows and len(windows) > cfg.wfo_windows:
            windows = windows[-cfg.wfo_windows :]

        window_rows: list[dict[str, Any]] = []
        for idx, window in enumerate(windows):
            start_ms = iso_to_ms(window.test_start)
            end_ms = iso_to_ms(window.test_end) + 86_400_000 - 1

            cand_n = sum(
                1
                for trade in candidate_rows
                if start_ms <= int(trade["entry_ts_ms"]) <= end_ms
            )
            base_n = sum(
                1
                for trade in baseline_rows
                if start_ms <= int(trade["entry_ts_ms"]) <= end_ms
            )
            window_rows.append(
                {
                    "window_id": idx,
                    "test_start": window.test_start,
                    "test_end": window.test_end,
                    "candidate_trades": cand_n,
                    "baseline_trades": base_n,
                    "low_trade_window": int(cand_n < cfg.low_trade_threshold or base_n < cfg.low_trade_threshold),
                }
            )

        if not window_rows:
            window_rows = [
                {
                    "window_id": -1,
                    "test_start": cfg.start,
                    "test_end": cfg.end,
                    "candidate_trades": len(candidate_rows),
                    "baseline_trades": len(baseline_rows),
                    "low_trade_window": int(
                        len(candidate_rows) < cfg.low_trade_threshold
                        or len(baseline_rows) < cfg.low_trade_threshold
                    ),
                }
            ]

        window_csv = write_csv(
            window_rows,
            ctx.results_dir / "window_trade_counts.csv",
            [
                "window_id",
                "test_start",
                "test_end",
                "candidate_trades",
                "baseline_trades",
                "low_trade_window",
            ],
        )
        artifacts.append(window_csv)

        # Trade-level markdown analysis report.
        analysis_report = _build_trade_level_analysis_report(
            scenario=scenario,
            matched_rows=matched_rows,
            candidate_only=candidate_only,
            baseline_only=baseline_only,
            entry_risk_rows=entry_risk_rows,
        )
        analysis_path = write_text(analysis_report, ctx.reports_dir / "trade_level_analysis.md")
        artifacts.append(analysis_path)

        # Time-aware paired block bootstrap on aligned NAV return differences.
        return_diff, return_diff_ts = _aligned_nav_return_diff(candidate_equity, baseline_equity)
        bootstrap_primary, bootstrap_by_block = _bootstrap_return_diff(return_diff, seed=cfg.seed)
        bootstrap_path = write_json(bootstrap_primary, ctx.results_dir / "bootstrap_return_diff.json")
        artifacts.append(bootstrap_path)

        delta_pnl = [float(row["delta_pnl"]) for row in matched_rows]
        delta_return = [float(row["delta_return_pct"]) for row in matched_rows]
        candidate_win_rate = _mean_or_zero([float(row["candidate_win"]) for row in matched_rows])
        baseline_win_rate = _mean_or_zero([float(row["baseline_win"]) for row in matched_rows])
        win_rate_delta = candidate_win_rate - baseline_win_rate

        trade_level_bootstrap = {
            **bootstrap_primary,
            "ci_crosses_zero": bool(
                float(bootstrap_primary["ci95_low"]) <= 0.0 <= float(bootstrap_primary["ci95_high"])
            ),
            "small_improvement_threshold": float(SMALL_MEAN_IMPROVEMENT_THRESHOLD),
            "is_small_improvement": bool(
                abs(float(bootstrap_primary["mean_diff"])) <= SMALL_MEAN_IMPROVEMENT_THRESHOLD
            ),
            "all_blocks": bootstrap_by_block,
            "n_timestamps": int(return_diff_ts.size),
        }

        candidate_fees_total = _total_fees_usd(candidate_rows)
        baseline_fees_total = _total_fees_usd(baseline_rows)
        candidate_emergency_dd_share = _share_emergency_dd(candidate_rows)
        baseline_emergency_dd_share = _share_emergency_dd(baseline_rows)
        candidate_buy_fills_per_episode, candidate_dd_episode_count = _buy_fills_per_episode(
            equity=candidate_equity,
            fills=candidate_fills,
        )
        baseline_buy_fills_per_episode, baseline_dd_episode_count = _buy_fills_per_episode(
            equity=baseline_equity,
            fills=baseline_fills,
        )

        data = {
            "scenario": scenario,
            "candidate_trades": len(candidate_rows),
            "baseline_trades": len(baseline_rows),
            "matched_trades": len(matched_rows),
            "candidate_only_trades": len(candidate_only),
            "baseline_only_trades": len(baseline_only),
            "match_rate": round(len(matched_rows) / max(len(candidate_rows), 1), 6),
            "matched_delta_pnl_mean": round(_mean_or_zero(delta_pnl), 6),
            "matched_delta_pnl_median": round(_median_or_zero(delta_pnl), 6),
            "matched_delta_return_mean": round(_mean_or_zero(delta_return), 6),
            "matched_delta_return_median": round(_median_or_zero(delta_return), 6),
            "matched_win_rate_baseline": round(baseline_win_rate, 6),
            "matched_win_rate_candidate": round(candidate_win_rate, 6),
            "matched_win_rate_delta": round(win_rate_delta, 6),
            "matched_p_positive": (
                round(sum(1 for value in delta_pnl if value > 0.0) / max(len(delta_pnl), 1), 6)
                if delta_pnl
                else None
            ),
            # Backward-compatible fields used by decision/report fallbacks.
            "matched_block_bootstrap_ci_lower": round(float(bootstrap_primary["ci95_low"]), 6),
            "matched_block_bootstrap_ci_upper": round(float(bootstrap_primary["ci95_high"]), 6),
            "matched_block_bootstrap_p_positive": round(float(bootstrap_primary["p_gt_0"]), 6),
            "candidate_fees_usd": round(candidate_fees_total, 6),
            "baseline_fees_usd": round(baseline_fees_total, 6),
            "delta_fees_usd": round(candidate_fees_total - baseline_fees_total, 6),
            "candidate_emergency_dd_share": round(candidate_emergency_dd_share, 6),
            "baseline_emergency_dd_share": round(baseline_emergency_dd_share, 6),
            "delta_emergency_dd_share_pp": round(
                (candidate_emergency_dd_share - baseline_emergency_dd_share) * 100.0,
                6,
            ),
            "candidate_buy_fills_per_episode": round(candidate_buy_fills_per_episode, 6),
            "baseline_buy_fills_per_episode": round(baseline_buy_fills_per_episode, 6),
            "delta_buy_fills_per_episode": round(
                candidate_buy_fills_per_episode - baseline_buy_fills_per_episode,
                6,
            ),
            "candidate_dd_episode_count": int(candidate_dd_episode_count),
            "baseline_dd_episode_count": int(baseline_dd_episode_count),
            "trade_level_bootstrap": trade_level_bootstrap,
        }
        if any(row["entry_risk_level"] != "untagged" for row in entry_risk_rows):
            data["entry_risk_summary"] = entry_risk_rows

        summary_json_path = write_json(data, ctx.results_dir / "trade_level_summary.json")
        artifacts.append(summary_json_path)

        return SuiteResult(
            name=self.name(),
            status="info",
            data=data,
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
