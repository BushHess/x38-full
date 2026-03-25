#!/usr/bin/env python3
"""P0.1 -- Entry hygiene benchmark on X0/X0_E5EXIT families.

Mechanism under test:
  tighten X0-style entries only inside chop, using a tiny set of locked gates
  motivated by e0_forensics. No parameter sweep.
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

from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy
from strategies.vtrend_x0.strategy import (
    VTrendX0Config,
    VTrendX0Strategy,
    _atr,
    _ema,
    _vdo,
)
from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
    _robust_atr,
)
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import Bar, Fill, MarketState, SCENARIOS, Signal
from v10.strategies.base import Strategy


# ============================================================================
# CONSTANTS
# ============================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
OUTDIR = Path(__file__).resolve().parent

START = "2019-01-01"
END = "2026-02-20"
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


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    label: str
    family_reference: str | None
    factory: callable


@dataclass
class EntryGateConfig:
    strategy_id: str
    use_robust_exit: bool = False
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28
    ratr_cap_q: float = 0.90
    ratr_cap_lb: int = 100
    ratr_period: int = 20
    er_lookback: int = 30
    chop_er_threshold: float = 0.25
    chop_min_vdo: float | None = None
    chop_max_price_to_slow_atr: float | None = None
    combo_min_vdo: float | None = None
    combo_price_to_slow_atr: float | None = None


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

    if (
        metrics["mae_before_mfe_first6"]
        and mfe_r < SLOW_REV_MFE_MAX
    ):
        return "false_breakout", False

    if (
        exit_reason.endswith("trend_exit")
        and metrics["bars_held"] >= SLOW_REV_BARS_MIN
        and mfe_r < SLOW_REV_MFE_MAX
    ):
        return "slow_trend_reversal", False

    if (
        exit_reason.endswith("trail_stop")
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


# ============================================================================
# STRATEGY
# ============================================================================


class X0EntryHygieneStrategy(Strategy):
    def __init__(self, config: EntryGateConfig) -> None:
        self._c = config
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._ratr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None
        self._er30: np.ndarray | None = None
        self._d1_regime_ok: np.ndarray | None = None
        self._in_position = False
        self._peak_price = 0.0
        self._gate_counts = {"blocked_chop_vdo": 0, "blocked_chop_stretch": 0, "blocked_chop_combo": 0}

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
        self._atr = _atr(high, low, close, self._c.atr_period)
        if self._c.use_robust_exit:
            self._ratr = _robust_atr(
                high,
                low,
                close,
                cap_q=self._c.ratr_cap_q,
                cap_lb=self._c.ratr_cap_lb,
                period=self._c.ratr_period,
            )
        self._vdo = _vdo(close, high, low, volume, taker_buy, self._c.vdo_fast, self._c.vdo_slow)
        self._er30 = _efficiency_ratio(close, self._c.er_lookback)
        self._d1_regime_ok = _d1_regime_map(h4_bars, d1_bars, self._c.d1_ema_period)

    def _entry_allowed(self, i: int, price: float, vdo_val: float) -> bool:
        assert self._er30 is not None and self._atr is not None and self._ema_slow is not None
        er = self._er30[i]
        atr_val = self._atr[i]
        if not np.isfinite(er) or not np.isfinite(atr_val) or atr_val <= 1e-12:
            return False

        if er >= self._c.chop_er_threshold:
            return True

        price_to_slow_atr = (price - self._ema_slow[i]) / atr_val

        if self._c.chop_min_vdo is not None and vdo_val < self._c.chop_min_vdo:
            self._gate_counts["blocked_chop_vdo"] += 1
            return False

        if (
            self._c.chop_max_price_to_slow_atr is not None
            and price_to_slow_atr > self._c.chop_max_price_to_slow_atr
        ):
            self._gate_counts["blocked_chop_stretch"] += 1
            return False

        if (
            self._c.combo_min_vdo is not None
            and self._c.combo_price_to_slow_atr is not None
            and price_to_slow_atr > self._c.combo_price_to_slow_atr
            and vdo_val < self._c.combo_min_vdo
        ):
            self._gate_counts["blocked_chop_combo"] += 1
            return False

        return True

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (
            self._ema_fast is None
            or self._ema_slow is None
            or self._atr is None
            or self._vdo is None
            or self._d1_regime_ok is None
            or i < 1
        ):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        exit_atr = self._ratr[i] if self._c.use_robust_exit and self._ratr is not None else atr_val
        price = state.bar.close

        if any(math.isnan(x) for x in (ema_f, ema_s, atr_val, vdo_val, exit_atr)):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            regime_ok = bool(self._d1_regime_ok[i])
            if regime_ok and trend_up and vdo_val > self._c.vdo_threshold and self._entry_allowed(i, price, vdo_val):
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason=f"{self._c.strategy_id}_entry")
        else:
            self._peak_price = max(self._peak_price, price)
            trail_stop = self._peak_price - self._c.trail_mult * exit_atr
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
        return dict(self._gate_counts)


# ============================================================================
# CORE
# ============================================================================


def make_specs() -> list[StrategySpec]:
    return [
        StrategySpec("E0", "VTrend E0", None, lambda: VTrendStrategy(VTrendConfig())),
        StrategySpec("X0", "X0", "X0", lambda: VTrendX0Strategy(VTrendX0Config())),
        StrategySpec(
            "X0_E5EXIT",
            "X0 + E5 exit",
            "X0_E5EXIT",
            lambda: VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig()),
        ),
        StrategySpec(
            "X0_CHOP_VDO2",
            "X0 + chop VDO>=0.002",
            "X0",
            lambda: X0EntryHygieneStrategy(EntryGateConfig(
                strategy_id="x0_chop_vdo2",
                chop_min_vdo=0.002,
            )),
        ),
        StrategySpec(
            "X0_CHOP_STRETCH18",
            "X0 + chop stretch<=1.8 ATR",
            "X0",
            lambda: X0EntryHygieneStrategy(EntryGateConfig(
                strategy_id="x0_chop_stretch18",
                chop_max_price_to_slow_atr=1.8,
            )),
        ),
        StrategySpec(
            "X0_CHOP_COMBO",
            "X0 + chop combo",
            "X0",
            lambda: X0EntryHygieneStrategy(EntryGateConfig(
                strategy_id="x0_chop_combo",
                combo_price_to_slow_atr=1.6,
                combo_min_vdo=0.003,
            )),
        ),
        StrategySpec(
            "X0E5_CHOP_VDO2",
            "X0_E5 + chop VDO>=0.002",
            "X0_E5EXIT",
            lambda: X0EntryHygieneStrategy(EntryGateConfig(
                strategy_id="x0e5_chop_vdo2",
                use_robust_exit=True,
                chop_min_vdo=0.002,
            )),
        ),
        StrategySpec(
            "X0E5_CHOP_STRETCH18",
            "X0_E5 + chop stretch<=1.8 ATR",
            "X0_E5EXIT",
            lambda: X0EntryHygieneStrategy(EntryGateConfig(
                strategy_id="x0e5_chop_stretch18",
                use_robust_exit=True,
                chop_max_price_to_slow_atr=1.8,
            )),
        ),
        StrategySpec(
            "X0E5_CHOP_COMBO",
            "X0_E5 + chop combo",
            "X0_E5EXIT",
            lambda: X0EntryHygieneStrategy(EntryGateConfig(
                strategy_id="x0e5_chop_combo",
                use_robust_exit=True,
                combo_price_to_slow_atr=1.6,
                combo_min_vdo=0.003,
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
            summary = dict(result.summary)
            metrics[spec.strategy_id][scenario] = summary
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
            days_held=float(trade.days_held),
            pnl_usd=float(trade.pnl),
            return_pct=float(trade.return_pct),
            exit_reason=trade.exit_reason,
            entry_reason=trade.entry_reason,
            entry_er30=float(er30[signal_idx]),
            entry_context=_context_from_er(float(er30[signal_idx])),
            entry_d1_regime="on" if bool(d1_regime[signal_idx]) else "off",
            entry_atr=atr_entry,
            entry_vdo=float(vdo[signal_idx]),
            entry_ema_spread_atr=float((ema_fast[signal_idx] - ema_slow[signal_idx]) / risk_unit),
            entry_price_to_slow_atr=float((close[signal_idx] - ema_slow[signal_idx]) / risk_unit),
            mfe_pct=float(mfe_pct),
            mae_pct=float(mae_pct),
            mfe_r=float(mfe_r),
            mae_r=float(mae_r),
            realized_r=float(realized_r),
            giveback_r=float(giveback_r),
            giveback_ratio=float(giveback_ratio),
            peak_time=_ts(int(arrays["open_time"][peak_idx])),
            peak_to_exit_bars=peak_to_exit_bars,
            mae_before_mfe_first6=bool(mae_before_mfe_first6),
            first_6_bar_mfe_r=float(first_6_mfe_r),
            first_6_bar_mae_r=float(first_6_mae_r),
            failure_mode=failure_mode,
            is_winner=is_winner,
        ))

    return rows


def build_failure_summary(rows: list[EnrichedTrade]) -> list[dict]:
    out: list[dict] = []
    strategies = sorted({r.strategy_id for r in rows})
    for strategy_id in strategies:
        subset = [r for r in rows if r.strategy_id == strategy_id]
        total_loss = abs(sum(r.pnl_usd for r in subset if r.pnl_usd < 0.0))
        by_mode = sorted({r.failure_mode for r in subset})
        for failure_mode in by_mode:
            group = [r for r in subset if r.failure_mode == failure_mode]
            loser_loss = abs(sum(r.pnl_usd for r in group if r.pnl_usd < 0.0))
            out.append({
                "strategy_id": strategy_id,
                "failure_mode": failure_mode,
                "trades": len(group),
                "losers": sum(1 for r in group if not r.is_winner),
                "winners": sum(1 for r in group if r.is_winner),
                "net_pnl_usd": round(sum(r.pnl_usd for r in group), 2),
                "loser_loss_usd": round(-loser_loss, 2),
                "share_of_strategy_loss_pct": round((loser_loss / total_loss * 100.0) if total_loss > 0 else 0.0, 4),
                "median_mfe_r": round(float(np.median([r.mfe_r for r in group])), 6),
                "median_first6_mae_r": round(float(np.median([r.first_6_bar_mae_r for r in group])), 6),
            })
    return out


def build_failure_delta(rows: list[EnrichedTrade]) -> list[dict]:
    out: list[dict] = []
    by_strategy = {sid: [r for r in rows if r.strategy_id == sid] for sid in sorted({r.strategy_id for r in rows})}
    refs = {
        "X0_CHOP_VDO2": "X0",
        "X0_CHOP_STRETCH18": "X0",
        "X0_CHOP_COMBO": "X0",
        "X0E5_CHOP_VDO2": "X0_E5EXIT",
        "X0E5_CHOP_STRETCH18": "X0_E5EXIT",
        "X0E5_CHOP_COMBO": "X0_E5EXIT",
    }
    for sid, ref in refs.items():
        cur = by_strategy.get(sid, [])
        base = by_strategy.get(ref, [])
        if not cur or not base:
            continue
        cur_total_loss = abs(sum(r.pnl_usd for r in cur if r.pnl_usd < 0))
        base_total_loss = abs(sum(r.pnl_usd for r in base if r.pnl_usd < 0))

        def loss_abs(group: list[EnrichedTrade], failure_mode: str) -> float:
            return abs(sum(r.pnl_usd for r in group if r.failure_mode == failure_mode and r.pnl_usd < 0.0))

        def loss_share(loss: float, total_loss: float) -> float:
            return (loss / total_loss * 100.0) if total_loss > 0 else 0.0

        cur_fb_loss = loss_abs(cur, "false_breakout")
        cur_tsn_loss = loss_abs(cur, "trail_stop_noise")
        base_fb_loss = loss_abs(base, "false_breakout")
        base_tsn_loss = loss_abs(base, "trail_stop_noise")

        cur_fb = loss_share(cur_fb_loss, cur_total_loss)
        cur_tsn = loss_share(cur_tsn_loss, cur_total_loss)
        base_fb = loss_share(base_fb_loss, base_total_loss)
        base_tsn = loss_share(base_tsn_loss, base_total_loss)

        out.append({
            "strategy_id": sid,
            "reference": ref,
            "false_breakout_loss_usd": round(-cur_fb_loss, 2),
            "trail_stop_noise_loss_usd": round(-cur_tsn_loss, 2),
            "combined_loss_usd": round(-(cur_fb_loss + cur_tsn_loss), 2),
            "false_breakout_share_pct": round(cur_fb, 4),
            "trail_stop_noise_share_pct": round(cur_tsn, 4),
            "combined_share_pct": round(cur_fb + cur_tsn, 4),
            "d_false_breakout_loss_usd": round(base_fb_loss - cur_fb_loss, 2),
            "d_trail_stop_noise_loss_usd": round(base_tsn_loss - cur_tsn_loss, 2),
            "d_combined_loss_usd": round((base_fb_loss + base_tsn_loss) - (cur_fb_loss + cur_tsn_loss), 2),
            "d_false_breakout_share_pct": round(cur_fb - base_fb, 4),
            "d_trail_stop_noise_share_pct": round(cur_tsn - base_tsn, 4),
            "d_combined_share_pct": round((cur_fb + cur_tsn) - (base_fb + base_tsn), 4),
            "d_net_pnl_usd": round(sum(r.pnl_usd for r in cur) - sum(r.pnl_usd for r in base), 2),
            "d_trades": len(cur) - len(base),
        })
    return out


def build_gate_stats(specs: list[StrategySpec], runs: dict[tuple[str, str], dict]) -> list[dict]:
    rows: list[dict] = []
    for spec in specs:
        run = runs.get((spec.strategy_id, "harsh"))
        if run is None:
            continue
        strategy = run["strategy"]
        getter = getattr(strategy, "get_gate_stats", None)
        if not callable(getter):
            continue
        stats = getter()
        stats["strategy_id"] = spec.strategy_id
        rows.append(stats)
    return rows


def build_delta_table(specs: list[StrategySpec], metrics: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for spec in specs:
        ref_id = spec.family_reference
        for scenario in ("smart", "base", "harsh"):
            cur = metrics[spec.strategy_id][scenario]
            ref = metrics[ref_id][scenario] if ref_id is not None else cur
            rows.append({
                "strategy_id": spec.strategy_id,
                "reference": ref_id or spec.strategy_id,
                "scenario": scenario,
                "d_sharpe": round(cur["sharpe"] - ref["sharpe"], 4),
                "d_cagr_pct": round(cur["cagr_pct"] - ref["cagr_pct"], 2),
                "d_mdd_pct": round(cur["max_drawdown_mid_pct"] - ref["max_drawdown_mid_pct"], 2),
                "d_calmar": round((cur["calmar"] or 0.0) - (ref["calmar"] or 0.0), 4),
                "d_trades": int(cur["trades"] - ref["trades"]),
                "d_winrate_pct": round(cur["win_rate_pct"] - ref["win_rate_pct"], 2),
                "d_profit_factor": round(float(cur["profit_factor"]) - float(ref["profit_factor"]), 4),
            })
    return rows


def build_backtest_table(specs: list[StrategySpec], metrics: dict[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for spec in specs:
        for scenario in ("smart", "base", "harsh"):
            m = metrics[spec.strategy_id][scenario]
            rows.append({
                "strategy_id": spec.strategy_id,
                "label": spec.label,
                "reference": spec.family_reference or spec.strategy_id,
                "scenario": scenario,
                "sharpe": m["sharpe"],
                "cagr_pct": m["cagr_pct"],
                "mdd_pct": m["max_drawdown_mid_pct"],
                "calmar": m["calmar"],
                "trades": m["trades"],
                "win_rate_pct": m["win_rate_pct"],
                "profit_factor": m["profit_factor"],
                "avg_exposure": m["avg_exposure"],
                "total_return_pct": m["total_return_pct"],
            })
    return rows


def build_report(
    specs: list[StrategySpec],
    metrics: dict[str, dict],
    failure_delta: list[dict],
    gate_stats: list[dict],
    elapsed: float,
) -> str:
    harsh_rows = [row for row in build_backtest_table(specs, metrics) if row["scenario"] == "harsh"]
    harsh_by_id = {row["strategy_id"]: row for row in harsh_rows}
    fail_by_id = {row["strategy_id"]: row for row in failure_delta}
    gate_by_id = {row["strategy_id"]: row for row in gate_stats}

    candidate_ids = [s.strategy_id for s in specs if s.strategy_id not in {"E0", "X0", "X0_E5EXIT"}]
    winners: list[str] = []
    for strategy_id in candidate_ids:
        row = harsh_by_id[strategy_id]
        fail = fail_by_id.get(strategy_id)
        if fail is None:
            continue
        if row["reference"] == strategy_id:
            continue
        if (
            ((row["calmar"] - harsh_by_id[row["reference"]]["calmar"]) >= 0.10 or
             (row["sharpe"] - harsh_by_id[row["reference"]]["sharpe"]) >= 0.05)
            and row["mdd_pct"] <= harsh_by_id[row["reference"]]["mdd_pct"] + 0.5
            and fail["d_false_breakout_loss_usd"] > 0.0
        ):
            winners.append(strategy_id)

    verdict = "PROMOTE_TO_PHASE_2" if winners else "KILL_ENTRY_HYGIENE"

    lines = [
        "# P0.1 Entry Hygiene Report",
        "",
        "## Scope",
        "",
        "- Baselines: `E0`, `X0`, `X0_E5EXIT`",
        "- Candidates: `X0_CHOP_VDO2`, `X0_CHOP_STRETCH18`, `X0_CHOP_COMBO`,",
        "  `X0E5_CHOP_VDO2`, `X0E5_CHOP_STRETCH18`, `X0E5_CHOP_COMBO`",
        f"- Period: `{START}` to `{END}`",
        "",
        "## Verdict",
        "",
        f"- `{verdict}`",
        f"- Elapsed: `{elapsed:.2f}s`",
        "",
        "## Harsh Backtest Snapshot",
        "",
    ]

    for strategy_id in ("E0", "X0", "X0_E5EXIT", *candidate_ids):
        row = harsh_by_id[strategy_id]
        lines.append(
            f"- `{strategy_id}`: Sharpe={row['sharpe']:.4f}, CAGR={row['cagr_pct']:.2f}%, "
            f"MDD={row['mdd_pct']:.2f}%, Calmar={row['calmar']:.4f}, Trades={row['trades']}"
        )

    lines.extend(["", "## Candidate Deltas vs Family Reference", ""])
    for strategy_id in candidate_ids:
        row = harsh_by_id[strategy_id]
        ref = harsh_by_id[row["reference"]]
        fail = fail_by_id.get(strategy_id)
        gate = gate_by_id.get(strategy_id)
        lines.append(
            f"- `{strategy_id}` vs `{row['reference']}`: "
            f"dSharpe={row['sharpe'] - ref['sharpe']:+.4f}, "
            f"dCAGR={row['cagr_pct'] - ref['cagr_pct']:+.2f}pp, "
            f"dMDD={row['mdd_pct'] - ref['mdd_pct']:+.2f}pp, "
            f"dCalmar={row['calmar'] - ref['calmar']:+.4f}"
        )
        if fail is not None:
            lines.append(
                f"  false_breakout loss delta: {fail['d_false_breakout_loss_usd']:+.2f} USD; "
                f"trail_stop_noise loss delta: {fail['d_trail_stop_noise_loss_usd']:+.2f} USD"
            )
        if gate is not None:
            blocked_total = gate.get("blocked_chop_vdo", 0) + gate.get("blocked_chop_stretch", 0) + gate.get("blocked_chop_combo", 0)
            lines.append(f"  blocked entries in harsh: {blocked_total}")

    lines.extend(["", "## Interpretation", ""])
    if winners:
        lines.append(f"- Candidates clearing the branch gate: {', '.join(f'`{w}`' for w in winners)}")
        lines.append("- Next step should test the surviving gate with matched-trade attribution against the family reference.")
    else:
        lines.append("- No candidate delivered a clean family-level improvement on harsh while also reducing combined failure share.")
        lines.append("- Entry hygiene remains plausible as a mechanism, but the tested low-DOF gates are not strong enough to promote.")
        lines.append("- The next branch should move to a different mechanism, likely exit geometry or give-back control.")

    return "\n".join(lines) + "\n"


def save_artifacts(
    specs: list[StrategySpec],
    metrics: dict[str, dict],
    trade_rows: list[EnrichedTrade],
    failure_summary: list[dict],
    failure_delta: list[dict],
    gate_stats: list[dict],
    elapsed: float,
) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    backtest_table = build_backtest_table(specs, metrics)
    delta_table = build_delta_table(specs, metrics)
    report = build_report(specs, metrics, failure_delta, gate_stats, elapsed)

    payload = {
        "settings": {
            "data": DATA,
            "start": START,
            "end": END,
            "warmup_days": WARMUP,
            "initial_cash": INITIAL_CASH,
            "locked_thresholds": {
                "er_chop": ER_CHOP,
                "x0_chop_vdo2": 0.002,
                "x0_chop_stretch18": 1.8,
                "x0_chop_combo_price_to_slow_atr": 1.6,
                "x0_chop_combo_vdo": 0.003,
            },
        },
        "backtest": metrics,
        "elapsed_seconds": elapsed,
    }
    _write_json(OUTDIR / "p0_1_results.json", payload)

    _write_csv(
        OUTDIR / "p0_1_backtest_table.csv",
        backtest_table,
        [
            "strategy_id", "label", "reference", "scenario", "sharpe", "cagr_pct",
            "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor",
            "avg_exposure", "total_return_pct",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_delta_table.csv",
        delta_table,
        [
            "strategy_id", "reference", "scenario", "d_sharpe", "d_cagr_pct",
            "d_mdd_pct", "d_calmar", "d_trades", "d_winrate_pct", "d_profit_factor",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_trade_table.csv",
        _trade_rows_to_csv(trade_rows),
        list(_trade_rows_to_csv(trade_rows)[0].keys()) if trade_rows else [],
    )
    _write_csv(
        OUTDIR / "p0_1_failure_summary.csv",
        failure_summary,
        [
            "strategy_id", "failure_mode", "trades", "losers", "winners",
            "net_pnl_usd", "loser_loss_usd", "share_of_strategy_loss_pct",
            "median_mfe_r", "median_first6_mae_r",
        ],
    )
    _write_csv(
        OUTDIR / "p0_1_failure_delta_table.csv",
        failure_delta,
        [
            "strategy_id", "reference", "false_breakout_loss_usd",
            "trail_stop_noise_loss_usd", "combined_loss_usd",
            "false_breakout_share_pct", "trail_stop_noise_share_pct", "combined_share_pct",
            "d_false_breakout_loss_usd", "d_trail_stop_noise_loss_usd", "d_combined_loss_usd",
            "d_false_breakout_share_pct", "d_trail_stop_noise_share_pct",
            "d_combined_share_pct", "d_net_pnl_usd", "d_trades",
        ],
    )
    if gate_stats:
        _write_csv(
            OUTDIR / "p0_1_gate_stats.csv",
            gate_stats,
            ["blocked_chop_vdo", "blocked_chop_stretch", "blocked_chop_combo", "strategy_id"],
        )
    (OUTDIR / "P0_1_INITIAL_REPORT.md").write_text(report)


def main() -> None:
    t0 = time.time()
    specs = make_specs()
    metrics, strategy_runs = run_backtests(specs)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    arrays, open_index = load_arrays(feed)

    trade_rows: list[EnrichedTrade] = []
    for spec in specs:
        harsh_result = strategy_runs[(spec.strategy_id, "harsh")]["result"]
        trade_rows.extend(enrich_trades(spec.strategy_id, harsh_result, arrays, open_index))

    failure_summary = build_failure_summary(trade_rows)
    failure_delta = build_failure_delta(trade_rows)
    gate_stats = build_gate_stats(specs, strategy_runs)
    elapsed = time.time() - t0

    save_artifacts(specs, metrics, trade_rows, failure_summary, failure_delta, gate_stats, elapsed)
    print(f"Saved entry hygiene artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
