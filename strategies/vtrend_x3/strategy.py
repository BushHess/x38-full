"""VTREND-X3 -- Graduated exposure variant of E0_ema21D1.

Instead of binary 0%/100% exposure, uses 3 tiers based on conviction:

  Tier 1 (core):     expo_core     (40%) -- EMA cross + D1 regime only
  Tier 2 (moderate): expo_moderate (70%) -- + VDO > vdo_threshold
  Tier 3 (full):     expo_full    (100%) -- + VDO > vdo_strong

Entry (when flat):
  1. D1 regime: last completed D1 close > EMA(d1_ema_period) on D1
  2. EMA crossover: ema_fast(H4) > ema_slow(H4)
  => Enter at tier determined by current VDO level (no VDO gate)

While positioned:
  - Exposure adjusts dynamically as VDO strengthens/weakens
  - Trail stop: close tactical portion, keep core (40%)
  - EMA cross-down: full exit to 0%

After trail stop (CORE_ONLY state):
  - Locked at core exposure (40%)
  - Only exits on EMA cross-down
  - No re-escalation, no trail stop

Parameters (tunable -- 8 total):
  slow_period       -- EMA slow period (fast = max(5, slow // 4))
  trail_mult        -- ATR multiplier for trailing stop
  vdo_threshold     -- VDO threshold for tier 2 (moderate)
  vdo_strong        -- VDO threshold for tier 3 (full)
  d1_ema_period     -- EMA period on D1 bars (default: 21)
  expo_core         -- tier 1 exposure (default: 0.40)
  expo_moderate     -- tier 2 exposure (default: 0.70)
  expo_full         -- tier 3 exposure (default: 1.00)

Constants (structural):
  atr_period        -- 14 (Wilder standard)
  vdo_fast          -- 12
  vdo_slow          -- 28
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "vtrend_x3"

# States
_FLAT = 0
_POSITIONED = 1   # exposure adjusts dynamically with VDO
_CORE_ONLY = 2    # after trail stop, locked at core until EMA reversal


@dataclass
class VTrendX3Config:
    # Tunable (8 parameters)
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0      # tier 2 gate
    vdo_strong: float = 0.02        # tier 3 gate
    d1_ema_period: int = 21
    expo_core: float = 0.40         # tier 1
    expo_moderate: float = 0.70     # tier 2
    expo_full: float = 1.00         # tier 3

    # Structural constants
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28


class VTrendX3Strategy(Strategy):
    def __init__(self, config: VTrendX3Config | None = None) -> None:
        self._config = config or VTrendX3Config()
        self._c = self._config

        # Precomputed indicator arrays
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # D1 regime filter mapped to H4 index
        self._d1_regime_ok: np.ndarray | None = None

        # Runtime state
        self._state = _FLAT
        self._peak_price = 0.0
        self._current_expo = 0.0

    def name(self) -> str:
        return STRATEGY_ID

    def _compute_target_expo(self, vdo_val: float) -> float:
        """Determine target exposure tier from current VDO level."""
        if vdo_val > self._c.vdo_strong:
            return self._c.expo_full
        elif vdo_val > self._c.vdo_threshold:
            return self._c.expo_moderate
        else:
            return self._c.expo_core

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
        """Compute D1 EMA regime and map to H4 bar indices."""
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

        if self._state == _FLAT:
            # ENTRY: EMA cross up + D1 regime (VDO determines tier, not gate)
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and regime_ok:
                target = self._compute_target_expo(vdo_val)
                self._state = _POSITIONED
                self._peak_price = price
                self._current_expo = target
                return Signal(target_exposure=target, reason="x3_entry")

        elif self._state == _POSITIONED:
            self._peak_price = max(self._peak_price, price)

            # EXIT check 1: trailing stop → reduce to core
            trail_stop = self._peak_price - self._c.trail_mult * atr_val
            if price < trail_stop:
                self._state = _CORE_ONLY
                self._peak_price = 0.0
                self._current_expo = self._c.expo_core
                return Signal(target_exposure=self._c.expo_core,
                              reason="x3_trail_to_core")

            # EXIT check 2: EMA cross-down → full exit
            if trend_down:
                self._state = _FLAT
                self._peak_price = 0.0
                self._current_expo = 0.0
                return Signal(target_exposure=0.0, reason="x3_trend_exit")

            # REBALANCE: adjust exposure based on current VDO
            new_target = self._compute_target_expo(vdo_val)
            if new_target != self._current_expo:
                self._current_expo = new_target
                return Signal(target_exposure=new_target, reason="x3_rebalance")

        elif self._state == _CORE_ONLY:
            # Only exit on EMA cross-down; no trail, no rebalance
            if trend_down:
                self._state = _FLAT
                self._peak_price = 0.0
                self._current_expo = 0.0
                return Signal(target_exposure=0.0, reason="x3_core_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


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
