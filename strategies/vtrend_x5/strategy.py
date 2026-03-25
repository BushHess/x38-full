"""VTREND-X5 -- Partial profit-taking variant of E0_ema21D1 (vtrend_x0).

E0_ema21D1 base with multi-level take-profit exits to lock in gains
instead of relying solely on trailing stop.

State machine:
  FLAT       -> exposure = 0.0
  LONG_FULL  -> exposure = 1.0  (initial entry, standard 3xATR trail)
  LONG_T1    -> exposure = 0.75 (after TP1: +10%, sold 25%, breakeven floor)
  LONG_T2    -> exposure = 0.50 (after TP2: +20%, sold 50%, wider 5xATR trail)

Entry (when FLAT):
  1. D1 regime: last completed D1 close > EMA(d1_ema_period) on D1
  2. EMA crossover: ema_fast(H4) > ema_slow(H4)
  3. VDO confirmation: vdo > vdo_threshold
  => target_exposure = 1.0

Exit hierarchy (all LONG states):
  - Trailing stop hit => close remaining position
  - Trend reversal (EMA cross-down) => close remaining position

Take-profit triggers (checked before exits):
  - LONG_FULL + unrealized >= tp1_pct => sell tp1_sell_frac, move to LONG_T1
  - LONG_T1   + unrealized >= tp2_pct => sell tp2_sell_frac, move to LONG_T2

Trailing stop per state:
  - LONG_FULL: peak - trail_mult * ATR
  - LONG_T1:   max(entry_price, peak - trail_mult * ATR)  [breakeven floor]
  - LONG_T2:   peak - trail_mult_tp2 * ATR                [wider trail]

Parameters (tunable, beyond E0_ema21D1 base):
  tp1_pct            -- unrealized gain threshold for first TP (default: 0.10)
  tp2_pct            -- unrealized gain threshold for second TP (default: 0.20)
  tp1_sell_frac      -- fraction of position to sell at TP1 (default: 0.25)
  tp2_sell_frac      -- fraction of position to sell at TP2 (default: 0.25)
  trail_mult_tp2     -- ATR multiplier after TP2 (default: 5.0)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "vtrend_x5"


class X5State(str, Enum):
    FLAT = "FLAT"
    LONG_FULL = "LONG_FULL"
    LONG_T1 = "LONG_T1"
    LONG_T2 = "LONG_T2"


@dataclass
class VTrendX5Config:
    # Base E0_ema21D1 parameters
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21

    # X5 take-profit parameters
    tp1_pct: float = 0.10         # +10% unrealized gain
    tp2_pct: float = 0.20         # +20% unrealized gain
    tp1_sell_frac: float = 0.25   # sell 25% at TP1
    tp2_sell_frac: float = 0.25   # sell another 25% at TP2
    trail_mult_tp2: float = 5.0   # wider trail after TP2

    # Structural constants
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28


class VTrendX5Strategy(Strategy):
    def __init__(self, config: VTrendX5Config | None = None) -> None:
        self._config = config or VTrendX5Config()
        self._c = self._config

        # Precomputed indicator arrays
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # D1 regime filter mapped to H4 index
        self._d1_regime_ok: np.ndarray | None = None

        # Runtime state
        self._state = X5State.FLAT
        self._peak_price = 0.0
        self._entry_price = 0.0   # recorded at entry for unrealized gain calc
        self._initial_qty = 0.0   # initial position qty at full entry

    def name(self) -> str:
        return STRATEGY_ID

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
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
        self._vdo = _vdo(close, high, low, volume, taker_buy,
                         self._c.vdo_fast, self._c.vdo_slow)

        self._d1_regime_ok = self._compute_d1_regime(h4_bars, d1_bars)

    def _compute_d1_regime(self, h4_bars: list, d1_bars: list) -> np.ndarray:
        n_h4 = len(h4_bars)
        regime_ok = np.zeros(n_h4, dtype=np.bool_)

        if not d1_bars:
            return regime_ok

        d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
        d1_ema = _ema(d1_close, self._c.d1_ema_period)
        d1_close_times = [b.close_time for b in d1_bars]

        d1_regime = d1_close > d1_ema

        d1_idx = 0
        n_d1 = len(d1_bars)
        for i in range(n_h4):
            h4_ct = h4_bars[i].close_time
            while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_ct:
                d1_idx += 1
            if d1_close_times[d1_idx] < h4_ct:
                regime_ok[i] = d1_regime[d1_idx]

        return regime_ok

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._atr is None or
                self._vdo is None or self._d1_regime_ok is None or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(atr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if self._state == X5State.FLAT:
            # ENTRY: trend up AND VDO confirms AND D1 regime filter
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok:
                self._state = X5State.LONG_FULL
                self._peak_price = price
                self._entry_price = price  # approximate; updated in on_after_fill
                return Signal(target_exposure=1.0, reason="x5_entry")
        else:
            # All LONG states: update peak
            self._peak_price = max(self._peak_price, price)

            # Use entry_price_avg from portfolio (more accurate than our record)
            entry_px = state.entry_price_avg if state.entry_price_avg > 0 else self._entry_price
            unrealized = (price - entry_px) / entry_px if entry_px > 0 else 0.0

            # --- Take-profit checks (before exit checks) ---
            if self._state == X5State.LONG_FULL:
                if unrealized >= self._c.tp1_pct:
                    # TP1: sell tp1_sell_frac, transition to LONG_T1
                    self._state = X5State.LONG_T1
                    new_expo = 1.0 - self._c.tp1_sell_frac
                    return Signal(target_exposure=new_expo, reason="x5_tp1")

            elif self._state == X5State.LONG_T1:
                if unrealized >= self._c.tp2_pct:
                    # TP2: sell tp2_sell_frac more, transition to LONG_T2
                    self._state = X5State.LONG_T2
                    # Current exposure is ~(1 - tp1_sell_frac), sell another tp2_sell_frac
                    current_expo = 1.0 - self._c.tp1_sell_frac
                    new_expo = current_expo - self._c.tp2_sell_frac
                    return Signal(target_exposure=max(new_expo, 0.01), reason="x5_tp2")

            # --- Exit checks (all LONG states) ---
            trail_stop = self._compute_trail_stop(atr_val, entry_px)

            if price < trail_stop:
                reason = "x5_trail_stop"
                if self._state == X5State.LONG_T1:
                    reason = "x5_be_stop"  # breakeven stop
                self._state = X5State.FLAT
                self._peak_price = 0.0
                self._entry_price = 0.0
                return Signal(target_exposure=0.0, reason=reason)

            if trend_down:
                self._state = X5State.FLAT
                self._peak_price = 0.0
                self._entry_price = 0.0
                return Signal(target_exposure=0.0, reason="x5_trend_exit")

        return None

    def _compute_trail_stop(self, atr_val: float, entry_px: float) -> float:
        if self._state == X5State.LONG_FULL:
            return self._peak_price - self._c.trail_mult * atr_val
        elif self._state == X5State.LONG_T1:
            # Breakeven floor: stop can't go below entry price
            trail = self._peak_price - self._c.trail_mult * atr_val
            return max(entry_px, trail)
        elif self._state == X5State.LONG_T2:
            # Wider trail after TP2
            return self._peak_price - self._c.trail_mult_tp2 * atr_val
        return 0.0

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        # Update entry price from actual fill when entering from flat
        if fill.reason == "x5_entry":
            self._entry_price = fill.price
            self._peak_price = state.bar.close


# -- Vectorized indicator helpers -------------------------------------------

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
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


def _vdo(close: np.ndarray, high: np.ndarray, low: np.ndarray,
         volume: np.ndarray, taker_buy: np.ndarray,
         fast: int, slow: int) -> np.ndarray:
    """Volume Delta Oscillator: EMA(vdr, fast) - EMA(vdr, slow).

    Requires real taker_buy data.  Raises RuntimeError if taker data is
    missing or all-zero — VDO must always represent taker-imbalance,
    never an OHLC price-location proxy.
    """
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)

    if not has_taker:
        raise RuntimeError(
            "VDO requires taker_buy_base_vol data. Cannot compute VDO "
            "without real taker flow data — OHLC fallback has been removed "
            "to prevent semantic confusion (price-location != order-flow)."
        )

    taker_sell = volume - taker_buy
    vdr = np.zeros(n)
    mask = volume > 0
    vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]

    return _ema(vdr, fast) - _ema(vdr, slow)
