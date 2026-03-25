"""VTREND-X4B -- E0_ema21D1 with parallel breakout trigger for early entry.

Key change from E0_ema21D1 baseline: adds a secondary breakout-based entry path that
allows early partial entry (default 40% exposure), while keeping EMA cross as
the condition for full (100%) exposure.

This preserves the defensive properties of EMA cross for full sizing, but
captures wave starts earlier via breakout detection.

State machine:
  FLAT (0%) ──breakout+D1──> BREAKOUT (40%)
  FLAT (0%) ──EMA+VDO+D1──> FULL (100%)
  BREAKOUT (40%) ──EMA+VDO──> FULL (100%)  (scale up)
  BREAKOUT (40%) ──trail/trend──> FLAT (0%)
  FULL (100%) ──trail/trend──> FLAT (0%)

Entry paths (when flat):
  Path 1 — Breakout early entry:
    close > highest_high(breakout_lookback) on H4
    AND volume > SMA(volume, vol_lookback)
    AND D1 regime OK
    => target_exposure = breakout_exposure (default 0.4)

  Path 2 — Full EMA entry (same as X0):
    ema_fast(H4) > ema_slow(H4)
    AND VDO > vdo_threshold
    AND D1 regime OK
    => target_exposure = 1.0

Scale-up (when at breakout_exposure):
  ema_fast > ema_slow AND VDO > vdo_threshold
  => target_exposure = 1.0

Exit (when long at any exposure):
  Trail stop: close < peak_price - trail_mult * ATR(14)
  Trend reversal: ema_fast < ema_slow
  => target_exposure = 0.0

Parameters (tunable — 7 total):
  slow_period        -- EMA slow period (fast = max(5, slow // 4))
  trail_mult         -- ATR multiplier for trailing stop
  vdo_threshold      -- minimum VDO for entry confirmation
  d1_ema_period      -- EMA period on D1 bars (default: 21)
  breakout_lookback  -- lookback for highest_high (default: 20)
  vol_lookback       -- lookback for volume SMA (default: 20)
  breakout_exposure  -- exposure on breakout entry (default: 0.4)

Constants (structural):
  atr_period         -- 14 (Wilder standard)
  vdo_fast           -- 12
  vdo_slow           -- 28
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "vtrend_x4b"


@dataclass
class VTrendX4BConfig:
    # Tunable (7 parameters)
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21
    breakout_lookback: int = 20
    vol_lookback: int = 20
    breakout_exposure: float = 0.4

    # Structural constants
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28


class VTrendX4BStrategy(Strategy):
    def __init__(self, config: VTrendX4BConfig | None = None) -> None:
        self._config = config or VTrendX4BConfig()
        self._c = self._config

        # Precomputed indicator arrays
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # Breakout indicators
        self._highest_high: np.ndarray | None = None
        self._vol_sma: np.ndarray | None = None

        # D1 regime filter mapped to H4 index
        self._d1_regime_ok: np.ndarray | None = None

        # Runtime state
        self._state = "FLAT"  # FLAT, BREAKOUT, FULL
        self._peak_price = 0.0

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

        # Breakout indicators
        self._highest_high = _rolling_max(high, self._c.breakout_lookback)
        self._vol_sma = _sma(volume, self._c.vol_lookback)

        # D1 regime filter
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
                self._vdo is None or self._d1_regime_ok is None or
                self._highest_high is None or self._vol_sma is None or
                i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close
        bar_high = state.bar.high

        if math.isnan(atr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s
        regime_ok = bool(self._d1_regime_ok[i])

        # Breakout detection: close breaks above previous highest high
        # AND volume confirms (above its SMA)
        hh = self._highest_high[i]
        vol_sma = self._vol_sma[i]
        breakout_ok = (not math.isnan(hh) and not math.isnan(vol_sma)
                       and price > hh
                       and state.bar.volume > vol_sma)

        if self._state == "FLAT":
            # Path 2: Full EMA entry (higher priority — check first)
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok:
                self._state = "FULL"
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="x4b_ema_entry")

            # Path 1: Breakout early entry (partial)
            if breakout_ok and regime_ok:
                self._state = "BREAKOUT"
                self._peak_price = price
                return Signal(target_exposure=self._c.breakout_exposure,
                              reason="x4b_breakout_entry")

        elif self._state == "BREAKOUT":
            self._peak_price = max(self._peak_price, price)

            # Scale up: EMA cross confirms → full exposure
            if trend_up and vdo_val > self._c.vdo_threshold:
                self._state = "FULL"
                return Signal(target_exposure=1.0, reason="x4b_scaleup")

            # Exit: trail stop
            trail_stop = self._peak_price - self._c.trail_mult * atr_val
            if price < trail_stop:
                self._state = "FLAT"
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x4b_trail_stop")

            # Exit: trend reversal
            if trend_down:
                self._state = "FLAT"
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x4b_trend_exit")

        elif self._state == "FULL":
            self._peak_price = max(self._peak_price, price)

            # Exit: trail stop
            trail_stop = self._peak_price - self._c.trail_mult * atr_val
            if price < trail_stop:
                self._state = "FLAT"
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x4b_trail_stop")

            # Exit: trend reversal
            if trend_down:
                self._state = "FLAT"
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x4b_trend_exit")

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


def _rolling_max(series: np.ndarray, window: int) -> np.ndarray:
    """Rolling max over the PREVIOUS `window` bars (no lookahead).

    out[i] = max(series[i-window : i])  (excludes current bar i).
    First `window` bars are NaN (insufficient history).
    """
    n = len(series)
    out = np.full(n, np.nan)
    for i in range(window, n):
        out[i] = np.max(series[i - window: i])
    return out


def _sma(series: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average over the PREVIOUS `window` bars (no lookahead).

    out[i] = mean(series[i-window : i])  (excludes current bar i).
    First `window` bars are NaN.
    """
    n = len(series)
    out = np.full(n, np.nan)
    cumsum = np.cumsum(series)
    for i in range(window, n):
        out[i] = (cumsum[i - 1] - (cumsum[i - window - 1] if i - window - 1 >= 0 else 0.0)) / window
    return out
