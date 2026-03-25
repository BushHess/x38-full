"""VTREND-X6 -- Adaptive trail + breakeven floor (X2 + X5 hybrid).

Combines two proven components:
  1. X2 adaptive trailing stop: widen trail as unrealized gain grows
  2. X5 breakeven floor: once gain reaches a threshold, stop can't go
     below entry price

Key difference from X5: NO partial selling. Exposure stays binary (0/1).
This preserves the CAGR upside that X5 sacrificed.

Trailing stop logic (per bar, when in position):
  unrealized_gain = (close - entry_price) / entry_price

  if unrealized_gain < gain_tier1 (5%):
      trail_stop = peak - trail_tight * ATR       (3×ATR, standard)
  elif unrealized_gain < gain_tier2 (15%):
      trail_stop = max(entry_price, peak - trail_mid * ATR)
                                                   (4×ATR + BE floor)
  else:
      trail_stop = max(entry_price, peak - trail_wide * ATR)
                                                   (5×ATR + BE floor)

The breakeven floor activates once unrealized gain >= gain_tier1 (5%).
Below 5% gain, there is no BE floor (fresh trades need room to breathe).

Entry logic: identical to E0_ema21D1 baseline.
Exit: adaptive trail stop OR EMA cross-down.

Parameters (tunable -- 7 total, same as X2):
  slow_period      -- EMA slow period (fast = max(5, slow // 4))
  trail_tight      -- ATR mult when gain < gain_tier1 (default 3.0)
  trail_mid        -- ATR mult when gain_tier1 <= gain < gain_tier2 (4.0)
  trail_wide       -- ATR mult when gain >= gain_tier2 (default 5.0)
  gain_tier1       -- threshold tight -> mid (default 0.05)
  gain_tier2       -- threshold mid -> wide (default 0.15)
  vdo_threshold    -- minimum VDO for entry (default 0.0)
  d1_ema_period    -- EMA period on D1 bars (default 21)

Constants (structural):
  atr_period       -- 14 (Wilder standard)
  vdo_fast         -- 12
  vdo_slow         -- 28
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "vtrend_x6"


@dataclass
class VTrendX6Config:
    # Tunable (7 parameters — same count as X2)
    slow_period: float = 120.0
    trail_tight: float = 3.0     # gain < gain_tier1
    trail_mid: float = 4.0       # gain_tier1 <= gain < gain_tier2
    trail_wide: float = 5.0      # gain >= gain_tier2
    gain_tier1: float = 0.05     # 5%
    gain_tier2: float = 0.15     # 15%
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21

    # Structural constants
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28


class VTrendX6Strategy(Strategy):
    def __init__(self, config: VTrendX6Config | None = None) -> None:
        self._config = config or VTrendX6Config()
        self._c = self._config

        # Precomputed indicator arrays
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # D1 regime filter mapped to H4 index
        self._d1_regime_ok: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_price = 0.0
        self._entry_price = 0.0

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

    def _compute_trail_stop(self, price: float, atr_val: float) -> float:
        """Adaptive trail stop with breakeven floor above tier1."""
        if self._entry_price <= 0:
            return self._peak_price - self._c.trail_tight * atr_val

        unrealized = (price - self._entry_price) / self._entry_price

        if unrealized < self._c.gain_tier1:
            # Tight trail, no BE floor (fresh trade needs room)
            return self._peak_price - self._c.trail_tight * atr_val
        elif unrealized < self._c.gain_tier2:
            # Mid trail + BE floor
            trail = self._peak_price - self._c.trail_mid * atr_val
            return max(self._entry_price, trail)
        else:
            # Wide trail + BE floor
            trail = self._peak_price - self._c.trail_wide * atr_val
            return max(self._entry_price, trail)

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

        if not self._in_position:
            # ENTRY: identical to E0_ema21D1
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok:
                self._in_position = True
                self._peak_price = price
                self._entry_price = price
                return Signal(target_exposure=1.0, reason="x6_entry")
        else:
            self._peak_price = max(self._peak_price, price)

            # Use portfolio entry_price_avg if available (more accurate)
            entry_px = state.entry_price_avg if state.entry_price_avg > 0 else self._entry_price

            # EXIT: adaptive trail stop with BE floor OR trend reversal
            trail_stop = self._compute_trail_stop(price, atr_val)
            if price < trail_stop:
                # Determine exit reason for analysis
                unrealized = (price - entry_px) / entry_px if entry_px > 0 else 0.0
                if unrealized >= self._c.gain_tier1:
                    reason = "x6_be_stop"  # breakeven floor was active
                else:
                    reason = "x6_trail_stop"
                self._in_position = False
                self._peak_price = 0.0
                self._entry_price = 0.0
                return Signal(target_exposure=0.0, reason=reason)

            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                self._entry_price = 0.0
                return Signal(target_exposure=0.0, reason="x6_trend_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        if fill.reason == "x6_entry":
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
