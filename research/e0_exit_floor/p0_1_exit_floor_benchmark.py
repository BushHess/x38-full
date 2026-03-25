#!/usr/bin/env python3
"""P0.1 -- Exit-floor benchmark on top of X0_E5EXIT.

Mechanism under test:
  add a tiny structural support-floor exit to the current robust-ATR anchor.
"""

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

from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
    _ema,
    _robust_atr,
    _vdo,
)
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import Bar, Fill, MarketState, SCENARIOS, Signal
from v10.strategies.base import Strategy


DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
OUTDIR = Path(__file__).resolve().parent

START = "2019-01-01"
END = "2026-02-20"
HOLDOUT_START = "2024-01-01"
WARMUP = 365
INITIAL_CASH = 10_000.0

SLOW = 120
TRAIL = 3.0
VDO_THR = 0.0
D1_EMA = 21
ATR_P = 14
VDO_FAST = 12
VDO_SLOW = 28

RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20
EXIT_N = max(12, SLOW // 4)

ER_LOOKBACK = 30
ER_CHOP = 0.25
ER_TREND = 0.45

LATE_EXIT_MFE_MIN = 2.0
LATE_EXIT_CAPTURE_MAX = 0.35
LATE_EXIT_PEAK_BARS = 4
SLOW_REV_BARS_MIN = 12
SLOW_REV_MFE_MAX = 1.0
TRAIL_NOISE_MFE_MIN = 0.5
TRAIL_NOISE_MFE_MAX = 2.0
FIRST_N = 6


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    label: str
    factory: callable


@dataclass
class ExitFloorConfig:
    strategy_id: str
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21
    vdo_fast: int = 12
    vdo_slow: int = 28
    ratr_cap_q: float = 0.90
    ratr_cap_lb: int = 100
    ratr_period: int = 20
    exit_n: int = EXIT_N
    floor_mode: str = "none"  # none | ll | floor
    floor_atr_mult: float | None = None


@dataclass
class EnrichedTrade:
    strategy_id: str
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


def _d1_regime_map(h4: list[Bar], d1: list[Bar], d1_ema_period: int = D1_EMA) -> np.ndarray:
    regime_ok = np.zeros(len(h4), dtype=np.bool_)
    if not d1:
        return regime_ok

    d1_close = np.array([b.close for b in d1], dtype=np.float64)
    d1_ema = _ema(d1_close, d1_ema_period)
    d1_close_times = [b.close_time for b in d1]
    d1_regime = d1_close > d1_ema

    d1_idx = 0
    n_d1 = len(d1)
    for i, bar in enumerate(h4):
        h4_ct = bar.close_time
        while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_ct:
            d1_idx += 1
        if d1_close_times[d1_idx] < h4_ct:
            regime_ok[i] = d1_regime[d1_idx]
    return regime_ok


def _rolling_low_shifted(low: np.ndarray, lookback: int) -> np.ndarray:
    out = np.full(len(low), np.nan, dtype=np.float64)
    for i in range(lookback, len(low)):
        out[i] = np.min(low[i - lookback:i])
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.concatenate([[high[0]], close[:-1]])),
            np.abs(low - np.concatenate([[low[0]], close[:-1]])),
        ),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _classify_trade(metrics: dict) -> tuple[str, bool]:
    pnl_usd = metrics["pnl_usd"]
    if pnl_usd >= 0.0:
        return "winner", True

    mfe_r = metrics["mfe_r"]
    realized_r = metrics["realized_r"]
    capture_ratio = realized_r / max(mfe_r, 1e-12) if mfe_r > 0 else -999.0
    exit_reason = metrics["exit_reason"]

    if (
        mfe_r >= LATE_EXIT_MFE_MIN
        and capture_ratio <= LATE_EXIT_CAPTURE_MAX
        and metrics["peak_to_exit_bars"] >= LATE_EXIT_PEAK_BARS
    ):
        return "late_exit_giveback", False

    if metrics["mae_before_mfe_first6"] and mfe_r < SLOW_REV_MFE_MAX:
        return "false_breakout", False

    if (
        exit_reason.endswith("trend_exit")
        and metrics["bars_held"] >= SLOW_REV_BARS_MIN
        and mfe_r < SLOW_REV_MFE_MAX
    ):
        return "slow_trend_reversal", False

    if (
        ("trail_stop" in exit_reason or "floor_exit" in exit_reason)
        and TRAIL_NOISE_MFE_MIN <= mfe_r < TRAIL_NOISE_MFE_MAX
    ):
        return "trail_stop_noise", False

    return "other_loss", False


def _trade_rows_to_csv(rows: list[EnrichedTrade]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        out.append({
            "strategy_id": r.strategy_id,
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


class X0ExitFloorStrategy(Strategy):
    def __init__(self, config: ExitFloorConfig) -> None:
        self._c = config
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._ratr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None
        self._ll_exit: np.ndarray | None = None
        self._d1_regime_ok: np.ndarray | None = None
        self._in_position = False
        self._peak_price = 0.0
        self._floor_hits = 0

    def name(self) -> str:
        return self._c.strategy_id

    def on_init(self, h4_bars: list[Bar], d1_bars: list[Bar]) -> None:
        if not h4_bars:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        taker_buy = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)

        slow_p = int(self._c.slow_period)
        fast_p = max(5, slow_p // 4)
        self._ema_fast = _ema(close, fast_p)
        self._ema_slow = _ema(close, slow_p)
        self._atr = _atr(high, low, close, ATR_P)
        self._ratr = _robust_atr(
            high,
            low,
            close,
            cap_q=self._c.ratr_cap_q,
            cap_lb=self._c.ratr_cap_lb,
            period=self._c.ratr_period,
        )
        self._vdo = _vdo(close, high, low, volume, taker_buy, self._c.vdo_fast, self._c.vdo_slow)
        self._ll_exit = _rolling_low_shifted(low, self._c.exit_n)
        self._d1_regime_ok = _d1_regime_map(h4_bars, d1_bars, self._c.d1_ema_period)

    def _floor_stop(self, i: int) -> float:
        assert self._ll_exit is not None and self._ema_slow is not None and self._ratr is not None
        ll = self._ll_exit[i]
        if self._c.floor_mode == "ll":
            return ll
        if self._c.floor_mode == "floor":
            ema_floor = self._ema_slow[i] - float(self._c.floor_atr_mult) * self._ratr[i]
            return max(ll, ema_floor)
        return math.nan

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (
            self._ema_fast is None
            or self._ema_slow is None
            or self._atr is None
            or self._ratr is None
            or self._vdo is None
            or self._ll_exit is None
            or self._d1_regime_ok is None
            or i < 1
        ):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        ratr_val = self._ratr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if any(math.isnan(x) for x in (ema_f, ema_s, ratr_val, vdo_val)):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            regime_ok = bool(self._d1_regime_ok[i])
            if regime_ok and trend_up and vdo_val > self._c.vdo_threshold:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason=f"{self._c.strategy_id}_entry")
        else:
            self._peak_price = max(self._peak_price, price)

            if self._c.floor_mode != "none":
                floor_stop = self._floor_stop(i)
                if np.isfinite(floor_stop) and price < floor_stop:
                    self._in_position = False
                    self._peak_price = 0.0
                    self._floor_hits += 1
                    return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_floor_exit")

            trail_stop = self._peak_price - self._c.trail_mult * ratr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trail_stop")

            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trend_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass

    def get_gate_stats(self) -> dict[str, int]:
        return {"floor_hits": int(self._floor_hits)}


def make_specs() -> list[StrategySpec]:
    return [
        StrategySpec(
            "X0_E5EXIT",
            "X0 + E5 exit",
            lambda: VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig()),
        ),
        StrategySpec(
            "X0E5_LL30",
            "X0_E5 + rolling low floor",
            lambda: X0ExitFloorStrategy(ExitFloorConfig(
                strategy_id="x0e5_ll30",
                floor_mode="ll",
            )),
        ),
        StrategySpec(
            "X0E5_FLOOR_SM",
            "X0_E5 + SM floor",
            lambda: X0ExitFloorStrategy(ExitFloorConfig(
                strategy_id="x0e5_floor_sm",
                floor_mode="floor",
                floor_atr_mult=3.0,
            )),
        ),
        StrategySpec(
            "X0E5_FLOOR_LATCH",
            "X0_E5 + LATCH floor",
            lambda: X0ExitFloorStrategy(ExitFloorConfig(
                strategy_id="x0e5_floor_latch",
                floor_mode="floor",
                floor_atr_mult=2.0,
            )),
        ),
    ]


def load_arrays(feed: DataFeed) -> tuple[dict[str, np.ndarray], dict[int, int]]:
    h4 = feed.h4_bars
    d1 = feed.d1_bars
    close = np.array([b.close for b in h4], dtype=np.float64)
    high = np.array([b.high for b in h4], dtype=np.float64)
    low = np.array([b.low for b in h4], dtype=np.float64)
    volume = np.array([b.volume for b in h4], dtype=np.float64)
    taker = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    open_time = np.array([b.open_time for b in h4], dtype=np.int64)

    arrays = {
        "close": close,
        "high": high,
        "low": low,
        "open_time": open_time,
        "ema_fast": _ema(close, max(5, SLOW // 4)),
        "ema_slow": _ema(close, SLOW),
        "atr": _atr(high, low, close, ATR_P),
        "vdo": _vdo(close, high, low, volume, taker, VDO_FAST, VDO_SLOW),
        "er30": _efficiency_ratio(close, ER_LOOKBACK),
        "d1_regime": _d1_regime_map(h4, d1, D1_EMA).astype(np.float64),
    }
    open_index = {int(ts): i for i, ts in enumerate(open_time)}
    return arrays, open_index


def run_backtests(specs: list[StrategySpec]) -> tuple[dict, dict]:
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    strategy_runs: dict[tuple[str, str], dict] = {}
    metrics: dict[str, dict] = {}

    for spec in specs:
        metrics[spec.strategy_id] = {}
        for scenario in ("smart", "base", "harsh"):
            strategy = spec.factory()
            engine = BacktestEngine(
                feed=feed,
                strategy=strategy,
                cost=SCENARIOS[scenario],
                initial_cash=INITIAL_CASH,
                warmup_days=WARMUP,
                warmup_mode="no_trade",
            )
            result = engine.run()
            metrics[spec.strategy_id][scenario] = dict(result.summary)
            strategy_runs[(spec.strategy_id, scenario)] = {
                "strategy": strategy,
                "result": result,
            }
    return metrics, strategy_runs


def enrich_trades(
    strategy_id: str,
    result,
    arrays: dict[str, np.ndarray],
    open_index: dict[int, int],
) -> list[EnrichedTrade]:
    close = arrays["close"]
    high = arrays["high"]
    low = arrays["low"]
    ema_fast = arrays["ema_fast"]
    ema_slow = arrays["ema_slow"]
    atr = arrays["atr"]
    vdo = arrays["vdo"]
    er30 = arrays["er30"]
    d1_regime = arrays["d1_regime"]

    rows: list[EnrichedTrade] = []
    for trade in result.trades:
        entry_idx = open_index.get(int(trade.entry_ts_ms))
        exit_idx = open_index.get(int(trade.exit_ts_ms))
        if entry_idx is None or exit_idx is None:
            continue

        signal_idx = max(0, entry_idx - 1)
        hold_end = max(entry_idx + 1, exit_idx)
        hi_slice = high[entry_idx:hold_end]
        lo_slice = low[entry_idx:hold_end]
        if len(hi_slice) == 0 or len(lo_slice) == 0:
            continue

        peak_rel = int(np.argmax(hi_slice))
        trough_rel = int(np.argmin(lo_slice))
        peak_idx = entry_idx + peak_rel
        peak_price = float(hi_slice[peak_rel])
        trough_price = float(lo_slice[trough_rel])

        entry_price = float(trade.entry_price)
        exit_price = float(trade.exit_price)
        atr_entry = float(atr[signal_idx]) if np.isfinite(atr[signal_idx]) else np.nan
        risk_unit = max(atr_entry, 1e-12)

        mfe_pct = (peak_price / entry_price - 1.0) * 100.0
        mae_pct = (trough_price / entry_price - 1.0) * 100.0
        mfe_r = (peak_price - entry_price) / risk_unit
        mae_r = (entry_price - trough_price) / risk_unit
        realized_r = (exit_price - entry_price) / risk_unit
        giveback_r = max(0.0, mfe_r - realized_r)
        giveback_ratio = giveback_r / max(mfe_r, 1e-12) if mfe_r > 0 else 0.0
        peak_to_exit_bars = max(0, exit_idx - peak_idx)

        first_end = min(entry_idx + FIRST_N, hold_end)
        first_hi = high[entry_idx:first_end]
        first_lo = low[entry_idx:first_end]
        first_peak_rel = int(np.argmax(first_hi))
        first_trough_rel = int(np.argmin(first_lo))
        first_6_mfe_r = (float(first_hi[first_peak_rel]) - entry_price) / risk_unit
        first_6_mae_r = (entry_price - float(first_lo[first_trough_rel])) / risk_unit
        mae_before_mfe_first6 = first_trough_rel <= first_peak_rel

        metrics = {
            "pnl_usd": float(trade.pnl),
            "mfe_r": float(mfe_r),
            "realized_r": float(realized_r),
            "peak_to_exit_bars": peak_to_exit_bars,
            "mae_before_mfe_first6": bool(mae_before_mfe_first6),
            "bars_held": int(exit_idx - entry_idx),
            "exit_reason": trade.exit_reason,
        }
        failure_mode, is_winner = _classify_trade(metrics)

        rows.append(EnrichedTrade(
            strategy_id=strategy_id,
            trade_id=trade.trade_id,
            entry_ts=_ts(trade.entry_ts_ms),
            exit_ts=_ts(trade.exit_ts_ms),
            entry_price=entry_price,
            exit_price=exit_price,
            bars_held=int(exit_idx - entry_idx),
            days_held=(exit_idx - entry_idx) / 6.0,
            pnl_usd=float(trade.pnl),
            return_pct=(exit_price / entry_price - 1.0) * 100.0,
            exit_reason=trade.exit_reason,
            entry_reason=trade.entry_reason,
            entry_er30=float(er30[signal_idx]),
            entry_context=_context_from_er(float(er30[signal_idx])),
            entry_d1_regime="on" if bool(d1_regime[signal_idx]) else "off",
            entry_atr=atr_entry,
            entry_vdo=float(vdo[signal_idx]),
            entry_ema_spread_atr=(float(ema_fast[signal_idx]) - float(ema_slow[signal_idx])) / risk_unit,
            entry_price_to_slow_atr=(entry_price - float(ema_slow[signal_idx])) / risk_unit,
            mfe_pct=float(mfe_pct),
            mae_pct=float(mae_pct),
            mfe_r=float(mfe_r),
            mae_r=float(mae_r),
            realized_r=float(realized_r),
            giveback_r=float(giveback_r),
            giveback_ratio=float(giveback_ratio),
            peak_time=_ts(int(trade.entry_ts_ms + peak_rel * 4 * 3600 * 1000)),
            peak_to_exit_bars=peak_to_exit_bars,
            mae_before_mfe_first6=bool(mae_before_mfe_first6),
            first_6_bar_mfe_r=float(first_6_mfe_r),
            first_6_bar_mae_r=float(first_6_mae_r),
            failure_mode=failure_mode,
            is_winner=is_winner,
        ))
    return rows


def summarize_failure_modes(rows: list[EnrichedTrade]) -> list[dict]:
    losses = [r for r in rows if not r.is_winner]
    total_loss = -sum(min(r.pnl_usd, 0.0) for r in losses)
    out: list[dict] = []
    for mode in sorted({r.failure_mode for r in rows if r.failure_mode != "winner"}):
        bucket = [r for r in rows if r.failure_mode == mode]
        if not bucket:
            continue
        loss_usd = -sum(min(r.pnl_usd, 0.0) for r in bucket)
        out.append({
            "strategy_id": bucket[0].strategy_id,
            "failure_mode": mode,
            "trades": len(bucket),
            "share_of_losing_trades_pct": (len(bucket) / len(losses) * 100.0) if losses else 0.0,
            "loss_usd": round(-loss_usd, 2),
            "share_of_total_loss_pct": (loss_usd / total_loss * 100.0) if total_loss > 0 else 0.0,
            "median_return_pct": float(np.median([r.return_pct for r in bucket])),
            "median_bars_held": float(np.median([r.bars_held for r in bucket])),
            "median_mfe_r": float(np.median([r.mfe_r for r in bucket])),
            "median_mae_r": float(np.median([r.mae_r for r in bucket])),
            "median_giveback_ratio": float(np.median([r.giveback_ratio for r in bucket])),
        })
    return out


def compute_holdout_metrics(specs: list[StrategySpec]) -> dict[str, dict]:
    feed = DataFeed(DATA, start=HOLDOUT_START, end=END, warmup_days=WARMUP)
    metrics: dict[str, dict] = {}
    for spec in specs:
        strategy = spec.factory()
        engine = BacktestEngine(
            feed=feed,
            strategy=strategy,
            cost=SCENARIOS["harsh"],
            initial_cash=INITIAL_CASH,
            warmup_days=WARMUP,
            warmup_mode="no_trade",
        )
        result = engine.run()
        metrics[spec.strategy_id] = dict(result.summary)
    return metrics


def main() -> None:
    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    specs = make_specs()
    metrics, strategy_runs = run_backtests(specs)
    holdout_metrics = compute_holdout_metrics(specs)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    arrays, open_index = load_arrays(feed)

    all_trade_rows: list[EnrichedTrade] = []
    failure_summary_rows: list[dict] = []
    gate_stats_rows: list[dict] = []

    for spec in specs:
        result = strategy_runs[(spec.strategy_id, "harsh")]["result"]
        strategy = strategy_runs[(spec.strategy_id, "harsh")]["strategy"]
        trade_rows = enrich_trades(spec.strategy_id, result, arrays, open_index)
        all_trade_rows.extend(trade_rows)
        failure_summary_rows.extend(summarize_failure_modes(trade_rows))

        if hasattr(strategy, "get_gate_stats"):
            stats = strategy.get_gate_stats()
            gate_stats_rows.append({
                "strategy_id": spec.strategy_id,
                **stats,
            })

    backtest_rows: list[dict] = []
    delta_rows: list[dict] = []
    holdout_rows: list[dict] = []
    holdout_delta_rows: list[dict] = []

    ref = metrics["X0_E5EXIT"]
    ref_hold = holdout_metrics["X0_E5EXIT"]
    for spec in specs:
        for scenario in ("smart", "base", "harsh"):
            m = metrics[spec.strategy_id][scenario]
            backtest_rows.append({
                "strategy": spec.strategy_id,
                "scenario": scenario,
                "sharpe": round(float(m["sharpe"]), 4),
                "cagr_pct": round(float(m["cagr_pct"]), 2),
                "mdd_pct": round(float(m["max_drawdown_mid_pct"]), 2),
                "calmar": round(float(m["calmar"]), 4),
                "trades": int(m["trades"]),
                "win_rate_pct": round(float(m["win_rate_pct"]), 2),
                "profit_factor": round(float(m["profit_factor"]), 4),
                "total_return_pct": round(float(m["total_return_pct"]), 2),
                "avg_exposure_pct": round(float(m["avg_exposure"]), 2),
            })
        if spec.strategy_id != "X0_E5EXIT":
            m = metrics[spec.strategy_id]["harsh"]
            delta_rows.append({
                "strategy": spec.strategy_id,
                "d_sharpe": round(float(m["sharpe"] - ref["harsh"]["sharpe"]), 4),
                "d_cagr": round(float(m["cagr_pct"] - ref["harsh"]["cagr_pct"]), 2),
                "d_mdd": round(float(m["max_drawdown_mid_pct"] - ref["harsh"]["max_drawdown_mid_pct"]), 2),
                "d_calmar": round(float(m["calmar"] - ref["harsh"]["calmar"]), 4),
                "d_trades": int(m["trades"] - ref["harsh"]["trades"]),
            })

        hm = holdout_metrics[spec.strategy_id]
        holdout_rows.append({
            "strategy": spec.strategy_id,
            "scenario": "harsh",
            "start": HOLDOUT_START,
            "end": END,
            "sharpe": round(float(hm["sharpe"]), 4),
            "cagr_pct": round(float(hm["cagr_pct"]), 2),
            "mdd_pct": round(float(hm["max_drawdown_mid_pct"]), 2),
            "calmar": round(float(hm["calmar"]), 4),
            "trades": int(hm["trades"]),
            "win_rate_pct": round(float(hm["win_rate_pct"]), 2),
            "profit_factor": round(float(hm["profit_factor"]), 4),
            "total_return_pct": round(float(hm["total_return_pct"]), 2),
            "avg_exposure_pct": round(float(hm["avg_exposure"]), 2),
        })
        if spec.strategy_id != "X0_E5EXIT":
            holdout_delta_rows.append({
                "strategy": spec.strategy_id,
                "d_sharpe": round(float(hm["sharpe"] - ref_hold["sharpe"]), 4),
                "d_cagr": round(float(hm["cagr_pct"] - ref_hold["cagr_pct"]), 2),
                "d_mdd": round(float(hm["max_drawdown_mid_pct"] - ref_hold["max_drawdown_mid_pct"]), 2),
                "d_calmar": round(float(hm["calmar"] - ref_hold["calmar"]), 4),
                "d_trades": int(hm["trades"] - ref_hold["trades"]),
            })

    trade_csv_rows = _trade_rows_to_csv(all_trade_rows)

    _write_csv(
        OUTDIR / "p0_1_backtest_table.csv",
        backtest_rows,
        list(backtest_rows[0].keys()),
    )
    _write_csv(
        OUTDIR / "p0_1_delta_table.csv",
        delta_rows,
        list(delta_rows[0].keys()),
    )
    _write_csv(
        OUTDIR / "p0_1_holdout_table.csv",
        holdout_rows,
        list(holdout_rows[0].keys()),
    )
    _write_csv(
        OUTDIR / "p0_1_holdout_delta_table.csv",
        holdout_delta_rows,
        list(holdout_delta_rows[0].keys()),
    )
    _write_csv(
        OUTDIR / "p0_1_trade_table.csv",
        trade_csv_rows,
        list(trade_csv_rows[0].keys()),
    )
    _write_csv(
        OUTDIR / "p0_1_failure_summary.csv",
        failure_summary_rows,
        list(failure_summary_rows[0].keys()),
    )
    _write_csv(
        OUTDIR / "p0_1_gate_stats.csv",
        gate_stats_rows,
        list(gate_stats_rows[0].keys()),
    )

    verdict = "KILL_EXIT_FLOOR"
    interesting = []
    for row, hold_row in zip(delta_rows, holdout_delta_rows):
        loss_modes = [
            r for r in failure_summary_rows
            if r["strategy_id"] == row["strategy"] and r["failure_mode"] in {"late_exit_giveback", "trail_stop_noise"}
        ]
        loss_share = sum(r["share_of_total_loss_pct"] for r in loss_modes)
        ref_loss_share = sum(
            r["share_of_total_loss_pct"] for r in failure_summary_rows
            if r["strategy_id"] == "X0_E5EXIT" and r["failure_mode"] in {"late_exit_giveback", "trail_stop_noise"}
        )
        if (
            (row["d_sharpe"] > 0.0 or row["d_calmar"] > 0.0)
            and row["d_mdd"] <= 0.5
            and (hold_row["d_sharpe"] > -0.03 and hold_row["d_cagr"] > -1.5)
            and loss_share < ref_loss_share
        ):
            interesting.append(row["strategy"])
    if interesting:
        verdict = "PROMOTE_TO_VALIDATION"

    results = {
        "config": {
            "data": DATA,
            "start": START,
            "end": END,
            "holdout_start": HOLDOUT_START,
            "warmup_days": WARMUP,
            "initial_cash": INITIAL_CASH,
            "slow_period": SLOW,
            "trail_mult": TRAIL,
            "d1_ema_period": D1_EMA,
            "ratr_cap_q": RATR_CAP_Q,
            "ratr_cap_lb": RATR_CAP_LB,
            "ratr_period": RATR_PERIOD,
            "exit_n": EXIT_N,
        },
        "verdict": verdict,
        "interesting_candidates": interesting,
        "runtime_seconds": round(time.time() - t0, 2),
    }
    _write_json(OUTDIR / "p0_1_results.json", results)

    lines = [
        "# P0.1 Exit-Floor Benchmark Report",
        "",
        "## Verdict",
        "",
        f"- `{verdict}`",
        "",
        "## Full Period (harsh) vs Reference",
        "",
    ]
    ref_h = ref["harsh"]
    lines.append(
        f"- `X0_E5EXIT`: Sharpe={ref_h['sharpe']:.4f}, CAGR={ref_h['cagr_pct']:.2f}%, "
        f"MDD={ref_h['max_drawdown_mid_pct']:.2f}%, Calmar={ref_h['calmar']:.4f}, Trades={ref_h['trades']}"
    )
    for row in backtest_rows:
        if row["scenario"] == "harsh" and row["strategy"] != "X0_E5EXIT":
            lines.append(
                f"- `{row['strategy']}`: Sharpe={row['sharpe']:.4f}, CAGR={row['cagr_pct']:.2f}%, "
                f"MDD={row['mdd_pct']:.2f}%, Calmar={row['calmar']:.4f}, Trades={row['trades']}"
            )

    lines.extend([
        "",
        "## Candidate Deltas vs Reference (harsh)",
        "",
    ])
    for row in delta_rows:
        hold_row = next(r for r in holdout_delta_rows if r["strategy"] == row["strategy"])
        lines.append(
            f"- `{row['strategy']}`: full dSharpe={row['d_sharpe']:+.4f}, dCAGR={row['d_cagr']:+.2f}pp, "
            f"dMDD={row['d_mdd']:+.2f}pp, dCalmar={row['d_calmar']:+.4f}; "
            f"holdout dSharpe={hold_row['d_sharpe']:+.4f}, dCAGR={hold_row['d_cagr']:+.2f}pp, "
            f"dMDD={hold_row['d_mdd']:+.2f}pp, dCalmar={hold_row['d_calmar']:+.4f}"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
    ])
    if verdict == "KILL_EXIT_FLOOR":
        lines.append("- None of the support-floor variants cleared the benchmark gate cleanly.")
        lines.append("- Current evidence does not justify continuing this exit family.")
    else:
        lines.append(f"- Survivors for Phase 2 validation: {', '.join(interesting)}")

    (OUTDIR / "P0_1_BENCHMARK_REPORT.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
