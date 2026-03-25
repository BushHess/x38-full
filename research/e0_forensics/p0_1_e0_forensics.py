#!/usr/bin/env python3
"""P0.1 -- Current-engine E0 trade-level forensics."""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy, _atr, _ema, _vdo
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import Bar, SCENARIOS
from v10.research.drawdown import detect_drawdown_episodes


# ============================================================================
# CONSTANTS
# ============================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
OUTDIR = Path(__file__).resolve().parent

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
SCENARIO = "harsh"
INITIAL_CASH = 10_000.0

SLOW = 120
FAST = 30
ATR_P = 14
VDO_FAST = 12
VDO_SLOW = 28
D1_EMA = 21
TRAIL_MULT = 3.0

ER_LOOKBACK = 30
ER_CHOP = 0.25
ER_TREND = 0.45

LATE_EXIT_MFE_MIN = 2.0
LATE_EXIT_CAPTURE_MAX = 0.35
LATE_EXIT_PEAK_BARS = 4

FALSE_BREAKOUT_MAE_MIN = 1.0
FALSE_BREAKOUT_MFE_EARLY = 0.5
FALSE_BREAKOUT_MFE_FULL = 1.0
FIRST_N = 6

SLOW_REV_BARS_MIN = 12
SLOW_REV_MFE_MAX = 1.0

TRAIL_NOISE_MFE_MIN = 0.5
TRAIL_NOISE_MFE_MAX = 2.0

DD_MIN_PCT = 5.0
TOP_LOSSES = 20


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class EnrichedTrade:
    trade_id: int
    entry_ts: str
    exit_ts: str
    entry_price: float
    exit_price: float
    bars_held: int
    days_held: float
    pnl_usd: float
    return_pct: float
    exit_reason: str
    entry_reason: str
    entry_er30: float
    entry_context: str
    entry_d1_regime: str
    entry_atr: float
    entry_vdo: float
    entry_ema_spread_atr: float
    entry_price_to_slow_atr: float
    mfe_pct: float
    mae_pct: float
    mfe_r: float
    mae_r: float
    realized_r: float
    giveback_r: float
    giveback_ratio: float
    peak_time: str
    peak_to_exit_bars: int
    mae_before_mfe_first6: bool
    first_6_bar_mfe_r: float
    first_6_bar_mae_r: float
    failure_mode: str
    is_winner: bool


# ============================================================================
# HELPERS
# ============================================================================


def _ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def _efficiency_ratio(close: np.ndarray, lookback: int) -> np.ndarray:
    out = np.full(len(close), np.nan, dtype=np.float64)
    for i in range(lookback, len(close)):
        net = abs(close[i] - close[i - lookback])
        total = np.sum(np.abs(np.diff(close[i - lookback:i + 1])))
        out[i] = net / total if total > 1e-12 else 0.0
    return out


def _context_from_er(er: float) -> str:
    if not np.isfinite(er):
        return "unknown"
    if er < ER_CHOP:
        return "chop"
    if er > ER_TREND:
        return "trend"
    return "transition"


def _d1_regime_map(h4: list[Bar], d1: list[Bar]) -> np.ndarray:
    d1_close = np.array([b.close for b in d1], dtype=np.float64)
    d1_ema = _ema(d1_close, D1_EMA)
    d1_close_times = [b.close_time for b in d1]
    d1_regime = d1_close > d1_ema

    out = np.zeros(len(h4), dtype=np.bool_)
    d1_idx = -1
    for i, bar in enumerate(h4):
        while d1_idx + 1 < len(d1) and d1_close_times[d1_idx + 1] < bar.close_time:
            d1_idx += 1
        if d1_idx >= 0:
            out[i] = bool(d1_regime[d1_idx])
    return out


def _classify_trade(metrics: dict) -> tuple[str, bool]:
    pnl_usd = metrics["pnl_usd"]
    if pnl_usd >= 0.0:
        return "winner", True

    mfe_r = metrics["mfe_r"]
    realized_r = metrics["realized_r"]
    capture_ratio = realized_r / max(mfe_r, 1e-12) if mfe_r > 0 else -999.0

    if (
        mfe_r >= LATE_EXIT_MFE_MIN
        and capture_ratio <= LATE_EXIT_CAPTURE_MAX
        and metrics["peak_to_exit_bars"] >= LATE_EXIT_PEAK_BARS
    ):
        return "late_exit_giveback", False

    if (
        metrics["mae_before_mfe_first6"]
        and mfe_r < FALSE_BREAKOUT_MFE_FULL
    ):
        return "false_breakout", False

    if (
        metrics["exit_reason"] == "vtrend_trend_exit"
        and metrics["bars_held"] >= SLOW_REV_BARS_MIN
        and mfe_r < SLOW_REV_MFE_MAX
    ):
        return "slow_trend_reversal", False

    if (
        metrics["exit_reason"] == "vtrend_trail_stop"
        and TRAIL_NOISE_MFE_MIN <= mfe_r < TRAIL_NOISE_MFE_MAX
    ):
        return "trail_stop_noise", False

    return "other_loss", False


def _trade_rows_to_csv(rows: list[EnrichedTrade]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        out.append({
            "trade_id": r.trade_id,
            "entry_ts": r.entry_ts,
            "exit_ts": r.exit_ts,
            "entry_price": round(r.entry_price, 6),
            "exit_price": round(r.exit_price, 6),
            "bars_held": r.bars_held,
            "days_held": round(r.days_held, 3),
            "pnl_usd": round(r.pnl_usd, 2),
            "return_pct": round(r.return_pct, 4),
            "exit_reason": r.exit_reason,
            "entry_reason": r.entry_reason,
            "entry_er30": round(r.entry_er30, 6) if np.isfinite(r.entry_er30) else None,
            "entry_context": r.entry_context,
            "entry_d1_regime": r.entry_d1_regime,
            "entry_atr": round(r.entry_atr, 6),
            "entry_vdo": round(r.entry_vdo, 6),
            "entry_ema_spread_atr": round(r.entry_ema_spread_atr, 6),
            "entry_price_to_slow_atr": round(r.entry_price_to_slow_atr, 6),
            "mfe_pct": round(r.mfe_pct, 4),
            "mae_pct": round(r.mae_pct, 4),
            "mfe_r": round(r.mfe_r, 6),
            "mae_r": round(r.mae_r, 6),
            "realized_r": round(r.realized_r, 6),
            "giveback_r": round(r.giveback_r, 6),
            "giveback_ratio": round(r.giveback_ratio, 6),
            "peak_time": r.peak_time,
            "peak_to_exit_bars": r.peak_to_exit_bars,
            "mae_before_mfe_first6": r.mae_before_mfe_first6,
            "first_6_bar_mfe_r": round(r.first_6_bar_mfe_r, 6),
            "first_6_bar_mae_r": round(r.first_6_bar_mae_r, 6),
            "failure_mode": r.failure_mode,
            "is_winner": r.is_winner,
        })
    return out


# ============================================================================
# CORE
# ============================================================================


def load_context() -> tuple[DataFeed, BacktestEngine, list[Bar], list[Bar], dict[str, np.ndarray], dict[int, int]]:
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    strategy = VTrendStrategy(VTrendConfig())
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=SCENARIOS[SCENARIO],
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP,
        warmup_mode="no_trade",
    )
    result = engine.run()

    h4 = feed.h4_bars
    d1 = feed.d1_bars

    close = np.array([b.close for b in h4], dtype=np.float64)
    high = np.array([b.high for b in h4], dtype=np.float64)
    low = np.array([b.low for b in h4], dtype=np.float64)
    volume = np.array([b.volume for b in h4], dtype=np.float64)
    taker = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    open_time = np.array([b.open_time for b in h4], dtype=np.int64)

    ema_fast = _ema(close, FAST)
    ema_slow = _ema(close, SLOW)
    atr = _atr(high, low, close, ATR_P)
    vdo = _vdo(close, high, low, volume, taker, VDO_FAST, VDO_SLOW)
    er30 = _efficiency_ratio(close, ER_LOOKBACK)
    d1_regime = _d1_regime_map(h4, d1)

    arrays = {
        "close": close,
        "high": high,
        "low": low,
        "open_time": open_time,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "atr": atr,
        "vdo": vdo,
        "er30": er30,
        "d1_regime": d1_regime.astype(np.float64),
    }
    open_index = {int(ts): i for i, ts in enumerate(open_time)}
    return feed, result, h4, d1, arrays, open_index


def enrich_trades(result, arrays: dict[str, np.ndarray], open_index: dict[int, int]) -> list[EnrichedTrade]:
    close = arrays["close"]
    high = arrays["high"]
    low = arrays["low"]
    ema_fast = arrays["ema_fast"]
    ema_slow = arrays["ema_slow"]
    atr = arrays["atr"]
    vdo = arrays["vdo"]
    er30 = arrays["er30"]
    d1_regime = arrays["d1_regime"]
    open_time = arrays["open_time"]

    rows: list[EnrichedTrade] = []
    for t in result.trades:
        entry_idx = open_index.get(int(t.entry_ts_ms))
        exit_idx = open_index.get(int(t.exit_ts_ms))
        if entry_idx is None or exit_idx is None:
            continue

        signal_idx = max(0, entry_idx - 1)
        hold_end = max(entry_idx + 1, exit_idx)
        hi_slice = high[entry_idx:hold_end]
        lo_slice = low[entry_idx:hold_end]

        peak_rel = int(np.argmax(hi_slice))
        peak_idx = entry_idx + peak_rel
        peak_price = float(hi_slice[peak_rel])
        min_low = float(np.min(lo_slice))

        entry_price = float(t.entry_price)
        exit_price = float(t.exit_price)
        entry_atr = float(atr[signal_idx]) if np.isfinite(atr[signal_idx]) else float("nan")
        atr_denom = entry_atr if np.isfinite(entry_atr) and entry_atr > 1e-12 else 1e-12

        mfe_abs = max(0.0, peak_price - entry_price)
        mae_abs = max(0.0, entry_price - min_low)
        realized_abs = exit_price - entry_price
        giveback_r = mfe_abs / atr_denom - realized_abs / atr_denom
        giveback_ratio = giveback_r / max(mfe_abs / atr_denom, 1e-12) if mfe_abs > 0 else 0.0

        first_n = min(FIRST_N, len(hi_slice))
        first_hi = hi_slice[:first_n]
        first_lo = lo_slice[:first_n]
        first_mfe_r = max(0.0, float(np.max(first_hi) - entry_price)) / atr_denom
        first_mae_r = max(0.0, float(entry_price - np.min(first_lo))) / atr_denom

        mae_before_mfe = False
        cum_mfe = 0.0
        cum_mae = 0.0
        for j in range(first_n):
            cum_mfe = max(cum_mfe, float(first_hi[j] - entry_price))
            cum_mae = max(cum_mae, float(entry_price - first_lo[j]))
            mfe_j = cum_mfe / atr_denom
            mae_j = cum_mae / atr_denom
            if mfe_j >= FALSE_BREAKOUT_MFE_EARLY:
                break
            if mae_j >= FALSE_BREAKOUT_MAE_MIN:
                mae_before_mfe = True
                break

        metrics = {
            "pnl_usd": float(t.pnl),
            "return_pct": float(t.return_pct),
            "exit_reason": str(t.exit_reason),
            "bars_held": int(max(1, exit_idx - entry_idx)),
            "mfe_r": mfe_abs / atr_denom,
            "realized_r": realized_abs / atr_denom,
            "peak_to_exit_bars": int(max(0, (exit_idx - 1) - peak_idx)),
            "mae_before_mfe_first6": mae_before_mfe,
        }
        failure_mode, is_winner = _classify_trade(metrics)

        rows.append(
            EnrichedTrade(
                trade_id=int(t.trade_id),
                entry_ts=_ts(int(t.entry_ts_ms)),
                exit_ts=_ts(int(t.exit_ts_ms)),
                entry_price=entry_price,
                exit_price=exit_price,
                bars_held=int(max(1, exit_idx - entry_idx)),
                days_held=float(t.days_held),
                pnl_usd=float(t.pnl),
                return_pct=float(t.return_pct),
                exit_reason=str(t.exit_reason),
                entry_reason=str(t.entry_reason),
                entry_er30=float(er30[signal_idx]),
                entry_context=_context_from_er(float(er30[signal_idx])),
                entry_d1_regime="on" if d1_regime[signal_idx] > 0.5 else "off",
                entry_atr=entry_atr,
                entry_vdo=float(vdo[signal_idx]),
                entry_ema_spread_atr=float((ema_fast[signal_idx] - ema_slow[signal_idx]) / atr_denom),
                entry_price_to_slow_atr=float((entry_price - ema_slow[signal_idx]) / atr_denom),
                mfe_pct=float(mfe_abs / entry_price * 100.0) if entry_price > 0 else 0.0,
                mae_pct=float(mae_abs / entry_price * 100.0) if entry_price > 0 else 0.0,
                mfe_r=float(mfe_abs / atr_denom),
                mae_r=float(mae_abs / atr_denom),
                realized_r=float(realized_abs / atr_denom),
                giveback_r=float(giveback_r),
                giveback_ratio=float(giveback_ratio),
                peak_time=_ts(int(open_time[peak_idx])),
                peak_to_exit_bars=int(max(0, (exit_idx - 1) - peak_idx)),
                mae_before_mfe_first6=bool(mae_before_mfe),
                first_6_bar_mfe_r=float(first_mfe_r),
                first_6_bar_mae_r=float(first_mae_r),
                failure_mode=failure_mode,
                is_winner=is_winner,
            )
        )
    return rows


def build_failure_summary(rows: list[EnrichedTrade]) -> list[dict]:
    losers = [r for r in rows if not r.is_winner]
    total_loss = sum(r.pnl_usd for r in losers)
    modes = ["late_exit_giveback", "false_breakout", "slow_trend_reversal", "trail_stop_noise", "other_loss"]
    out = []
    for mode in modes:
        group = [r for r in losers if r.failure_mode == mode]
        if not group:
            out.append({
                "failure_mode": mode,
                "trades": 0,
                "share_of_losing_trades_pct": 0.0,
                "loss_usd": 0.0,
                "share_of_total_loss_pct": 0.0,
                "median_return_pct": None,
                "median_bars_held": None,
                "median_mfe_r": None,
                "median_mae_r": None,
                "median_giveback_ratio": None,
            })
            continue
        loss_usd = sum(r.pnl_usd for r in group)
        out.append({
            "failure_mode": mode,
            "trades": len(group),
            "share_of_losing_trades_pct": 100.0 * len(group) / len(losers) if losers else 0.0,
            "loss_usd": loss_usd,
            "share_of_total_loss_pct": 100.0 * loss_usd / total_loss if abs(total_loss) > 1e-12 else 0.0,
            "median_return_pct": float(np.median([r.return_pct for r in group])),
            "median_bars_held": float(np.median([r.bars_held for r in group])),
            "median_mfe_r": float(np.median([r.mfe_r for r in group])),
            "median_mae_r": float(np.median([r.mae_r for r in group])),
            "median_giveback_ratio": float(np.median([r.giveback_ratio for r in group])),
        })
    return out


def build_regime_summary(rows: list[EnrichedTrade]) -> list[dict]:
    out = []
    groups = {}
    for r in rows:
        key = (r.entry_context, r.entry_d1_regime)
        groups.setdefault(key, []).append(r)

    total_loser_loss = sum(r.pnl_usd for r in rows if not r.is_winner)
    for (ctx, d1_state), group in sorted(groups.items()):
        losers = [r for r in group if not r.is_winner]
        loss_usd = sum(r.pnl_usd for r in losers)
        out.append({
            "entry_context": ctx,
            "entry_d1_regime": d1_state,
            "trades": len(group),
            "win_rate_pct": 100.0 * sum(r.is_winner for r in group) / len(group) if group else 0.0,
            "avg_return_pct": float(np.mean([r.return_pct for r in group])) if group else 0.0,
            "net_pnl_usd": float(sum(r.pnl_usd for r in group)),
            "loser_loss_usd": float(loss_usd),
            "share_of_total_loss_pct": 100.0 * loss_usd / total_loser_loss if abs(total_loser_loss) > 1e-12 else 0.0,
            "median_bars_held": float(np.median([r.bars_held for r in group])) if group else 0.0,
        })
    out.sort(key=lambda x: x["loser_loss_usd"])
    return out


def build_episode_tables(result, rows: list[EnrichedTrade]) -> tuple[list[dict], list[dict]]:
    episodes = detect_drawdown_episodes(result.equity or [], min_dd_pct=DD_MIN_PCT)
    ep_rows: list[dict] = []
    map_rows: list[dict] = []

    total_dd = sum(ep.drawdown_pct for ep in episodes) if episodes else 0.0
    for ep_id, ep in enumerate(episodes, 1):
        ep_end = ep.recovery_ms if ep.recovery_ms is not None else ep.trough_ms
        overlaps = []
        for r in rows:
            entry_ms = int(datetime.strptime(r.entry_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)
            exit_ms = int(datetime.strptime(r.exit_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)
            if entry_ms <= ep_end and exit_ms >= ep.peak_ms:
                overlaps.append(r)

        losers = [r for r in overlaps if not r.is_winner]
        mode_counts = {}
        for r in losers:
            mode_counts[r.failure_mode] = mode_counts.get(r.failure_mode, 0) + 1
        top_mode = max(mode_counts, key=mode_counts.get) if mode_counts else "none"

        ep_rows.append({
            "episode_id": ep_id,
            "peak_date": _ts(int(ep.peak_ms)),
            "trough_date": _ts(int(ep.trough_ms)),
            "recovery_date": _ts(int(ep.recovery_ms)) if ep.recovery_ms is not None else None,
            "drawdown_pct": float(ep.drawdown_pct),
            "bars_to_trough": int(ep.bars_to_trough),
            "bars_to_recovery": int(ep.bars_to_recovery) if ep.bars_to_recovery is not None else None,
            "overlap_trades": len(overlaps),
            "overlap_losers": len(losers),
            "overlap_net_pnl_usd": float(sum(r.pnl_usd for r in overlaps)),
            "overlap_loser_pnl_usd": float(sum(r.pnl_usd for r in losers)),
            "top_failure_mode": top_mode,
            "share_of_total_drawdown_mass_pct": 100.0 * ep.drawdown_pct / total_dd if total_dd > 0 else 0.0,
        })

        for r in overlaps:
            map_rows.append({
                "episode_id": ep_id,
                "trade_id": r.trade_id,
                "entry_ts": r.entry_ts,
                "exit_ts": r.exit_ts,
                "pnl_usd": round(r.pnl_usd, 2),
                "return_pct": round(r.return_pct, 4),
                "failure_mode": r.failure_mode,
                "exit_reason": r.exit_reason,
                "entry_context": r.entry_context,
                "entry_d1_regime": r.entry_d1_regime,
                "is_winner": r.is_winner,
            })

    ep_rows.sort(key=lambda x: -x["drawdown_pct"])
    map_rows.sort(key=lambda x: (x["episode_id"], x["trade_id"]))
    return ep_rows, map_rows


def build_report(result, rows: list[EnrichedTrade], failure_rows: list[dict], regime_rows: list[dict], episode_rows: list[dict]) -> str:
    winners = [r for r in rows if r.is_winner]
    losers = [r for r in rows if not r.is_winner]
    primary_failure = min(failure_rows, key=lambda x: x["loss_usd"]) if failure_rows else None
    worst_context = min(regime_rows, key=lambda x: x["loser_loss_usd"]) if regime_rows else None
    top_episode = episode_rows[0] if episode_rows else None

    suggestions = []
    if primary_failure and primary_failure["failure_mode"] == "late_exit_giveback":
        suggestions.append("Next branch should target exit geometry and peak give-back control.")
    if primary_failure and primary_failure["failure_mode"] == "false_breakout":
        suggestions.append("Next branch should target entry hygiene, especially against early adverse excursion.")
    if worst_context and worst_context["entry_context"] == "chop":
        suggestions.append("Chop-sensitive entry gating deserves explicit testing.")
    if not suggestions:
        suggestions.append("No single dominant mode found; keep next branch low-DOF and mechanism-specific.")

    lines = [
        "# P0.1 E0 Initial Forensics Report",
        "",
        "## Scope",
        "",
        f"- Strategy: `vtrend` default",
        f"- Scenario: `{SCENARIO}`",
        f"- Period: `{START}` to `{END}`",
        "",
        "## Executive Summary",
        "",
        f"- Trades: `{len(rows)}`",
        f"- Winners / losers: `{len(winners)}` / `{len(losers)}`",
        f"- Win rate: `{(100.0 * len(winners) / len(rows)):.1f}%`" if rows else "- Win rate: n/a",
        f"- Sharpe: `{result.summary.get('sharpe', 0.0):.4f}`",
        f"- CAGR: `{result.summary.get('cagr_pct', 0.0):.2f}%`",
        f"- Max drawdown: `{result.summary.get('max_drawdown_mid_pct', 0.0):.2f}%`",
        f"- Primary losing mode: `{primary_failure['failure_mode']}` with `{primary_failure['share_of_total_loss_pct']:.1f}%` of total loss" if primary_failure else "- Primary losing mode: n/a",
        f"- Worst entry context: `{worst_context['entry_context']} + D1 {worst_context['entry_d1_regime']}` with `{worst_context['share_of_total_loss_pct']:.1f}%` of total loss" if worst_context else "- Worst entry context: n/a",
        f"- Largest drawdown episode: `{top_episode['drawdown_pct']:.2f}%` starting `{top_episode['peak_date']}`" if top_episode else "- Largest drawdown episode: n/a",
        "",
        "## Next Mechanism Hypotheses",
        "",
    ]
    for item in suggestions:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Failure Mode Table",
        "",
    ]
    for row in failure_rows:
        lines.append(
            f"- `{row['failure_mode']}`: trades={row['trades']}, loss_share={row['share_of_total_loss_pct']:.1f}%, median_MFE_R={row['median_mfe_r']}"
        )

    lines += [
        "",
        "## Regime Table",
        "",
    ]
    top_regime = sorted(regime_rows, key=lambda x: x["loser_loss_usd"])[:4]
    for row in top_regime:
        lines.append(
            f"- `{row['entry_context']} + D1 {row['entry_d1_regime']}`: trades={row['trades']}, win_rate={row['win_rate_pct']:.1f}%, loss_share={row['share_of_total_loss_pct']:.1f}%"
        )

    lines += [
        "",
        "## Drawdown Episodes",
        "",
    ]
    for row in episode_rows[:5]:
        lines.append(
            f"- Episode `{row['episode_id']}`: dd={row['drawdown_pct']:.2f}%, overlap_trades={row['overlap_trades']}, top_failure_mode={row['top_failure_mode']}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    t0 = time.time()
    print("=" * 80)
    print("P0.1 E0 FORENSICS")
    print("=" * 80)

    print("\nRunning current-engine E0 backtest...")
    feed, result, h4, d1, arrays, open_index = load_context()
    print(f"  Trades: {len(result.trades)}")
    print(f"  Sharpe: {result.summary.get('sharpe', 0.0):.4f}")
    print(f"  CAGR:   {result.summary.get('cagr_pct', 0.0):.2f}%")
    print(f"  MDD:    {result.summary.get('max_drawdown_mid_pct', 0.0):.2f}%")

    print("\nEnriching trade table...")
    rows = enrich_trades(result, arrays, open_index)

    print("Building failure summaries...")
    failure_rows = build_failure_summary(rows)
    regime_rows = build_regime_summary(rows)
    episode_rows, episode_map_rows = build_episode_tables(result, rows)

    top_losses = sorted((r for r in rows if not r.is_winner), key=lambda x: x.pnl_usd)[:TOP_LOSSES]

    primary_failure = min(failure_rows, key=lambda x: x["loss_usd"]) if failure_rows else None
    worst_context = min(regime_rows, key=lambda x: x["loser_loss_usd"]) if regime_rows else None
    top_episode = episode_rows[0] if episode_rows else None

    results = {
        "settings": {
            "data": DATA,
            "start": START,
            "end": END,
            "warmup_days": WARMUP,
            "scenario": SCENARIO,
        },
        "backtest": {
            "trades": len(result.trades),
            "sharpe": float(result.summary.get("sharpe", 0.0)),
            "cagr_pct": float(result.summary.get("cagr_pct", 0.0)),
            "max_drawdown_mid_pct": float(result.summary.get("max_drawdown_mid_pct", 0.0)),
            "win_rate_pct": float(result.summary.get("win_rate_pct", 0.0)),
            "profit_factor": float(result.summary.get("profit_factor", 0.0)),
            "avg_exposure": float(result.summary.get("avg_exposure", 0.0)),
        },
        "summary": {
            "primary_failure_mode": primary_failure["failure_mode"] if primary_failure else None,
            "primary_failure_loss_share_pct": primary_failure["share_of_total_loss_pct"] if primary_failure else None,
            "worst_entry_context": worst_context,
            "largest_drawdown_episode": top_episode,
            "drawdown_episode_count": len(episode_rows),
        },
        "elapsed_seconds": time.time() - t0,
    }

    _write_csv(
        OUTDIR / "p0_1_trade_table.csv",
        _trade_rows_to_csv(rows),
        [
            "trade_id", "entry_ts", "exit_ts", "entry_price", "exit_price", "bars_held", "days_held",
            "pnl_usd", "return_pct", "exit_reason", "entry_reason", "entry_er30", "entry_context",
            "entry_d1_regime", "entry_atr", "entry_vdo", "entry_ema_spread_atr", "entry_price_to_slow_atr",
            "mfe_pct", "mae_pct", "mfe_r", "mae_r", "realized_r", "giveback_r", "giveback_ratio",
            "peak_time", "peak_to_exit_bars", "mae_before_mfe_first6", "first_6_bar_mfe_r",
            "first_6_bar_mae_r", "failure_mode", "is_winner",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_failure_summary.csv",
        failure_rows,
        [
            "failure_mode", "trades", "share_of_losing_trades_pct", "loss_usd",
            "share_of_total_loss_pct", "median_return_pct", "median_bars_held",
            "median_mfe_r", "median_mae_r", "median_giveback_ratio",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_regime_summary.csv",
        regime_rows,
        [
            "entry_context", "entry_d1_regime", "trades", "win_rate_pct", "avg_return_pct",
            "net_pnl_usd", "loser_loss_usd", "share_of_total_loss_pct", "median_bars_held",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_episode_table.csv",
        episode_rows,
        [
            "episode_id", "peak_date", "trough_date", "recovery_date", "drawdown_pct",
            "bars_to_trough", "bars_to_recovery", "overlap_trades", "overlap_losers",
            "overlap_net_pnl_usd", "overlap_loser_pnl_usd", "top_failure_mode",
            "share_of_total_drawdown_mass_pct",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_episode_trade_map.csv",
        episode_map_rows,
        [
            "episode_id", "trade_id", "entry_ts", "exit_ts", "pnl_usd", "return_pct", "failure_mode",
            "exit_reason", "entry_context", "entry_d1_regime", "is_winner",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_top_losses.csv",
        _trade_rows_to_csv(top_losses),
        [
            "trade_id", "entry_ts", "exit_ts", "entry_price", "exit_price", "bars_held", "days_held",
            "pnl_usd", "return_pct", "exit_reason", "entry_reason", "entry_er30", "entry_context",
            "entry_d1_regime", "entry_atr", "entry_vdo", "entry_ema_spread_atr", "entry_price_to_slow_atr",
            "mfe_pct", "mae_pct", "mfe_r", "mae_r", "realized_r", "giveback_r", "giveback_ratio",
            "peak_time", "peak_to_exit_bars", "mae_before_mfe_first6", "first_6_bar_mfe_r",
            "first_6_bar_mae_r", "failure_mode", "is_winner",
        ],
    )
    _write_json(OUTDIR / "p0_1_results.json", results)

    report = build_report(result, rows, failure_rows, regime_rows, episode_rows)
    (OUTDIR / "P0_1_INITIAL_REPORT.md").write_text(report)

    print("\nPrimary failure mode:", results["summary"]["primary_failure_mode"])
    print("Artifacts written to", OUTDIR)
    print(f"Elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
