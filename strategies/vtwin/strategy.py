"""VTWIN — Twin-Confirmed Trend strategy.

2-parameter BTC trend-following strategy requiring dual confirmation:
both EMA crossover AND Donchian breakout must agree before entry.

Entry: EMA fast > slow AND close > highest_high(N) AND VDO > 0.
Exit:  ATR trailing stop OR EMA cross-down.

The Donchian confirmation filters out weak EMA crossovers that don't
lead to sustained trends (price fails to make new highs).

Parameters (tunable):
  slow_period  — N: EMA slow period AND Donchian lookback (coupled)
  trail_mult   — ATR multiplier for trailing stop

Constants (structural, not optimized):
  atr_period   — 14 (Wilder standard)
  vdo_fast     — 12 (fixed)
  vdo_slow     — 28 (fixed)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy


@dataclass
class VTwinConfig:
    # Tunable (2 parameters — fewer than VTREND's 3)
    slow_period: int = 120          # EMA slow period AND Donchian lookback
    trail_mult: float = 3.0         # ATR trailing stop multiplier

    # Structural constants (not tuned)
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28
    vdo_threshold: float = 0.0      # VDO entry gate (0.0 = any positive flow)


class VTwinStrategy(Strategy):
    def __init__(self, config: VTwinConfig | None = None) -> None:
        self._config = config or VTwinConfig()
        self._c = self._config

        # Precomputed indicator arrays (set in on_init)
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._hh: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return "vtwin"

    # ── Precompute indicators on full bar arrays ──────────────────────

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        taker_buy = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)

        slow_p = self._c.slow_period
        fast_p = max(5, slow_p // 4)

        self._ema_fast = _ema(close, fast_p)
        self._ema_slow = _ema(close, slow_p)
        self._hh = _highest_high(high, slow_p)  # Coupled: same lookback as slow EMA
        self._atr = _atr(high, low, close, self._c.atr_period)
        self._vdo = _vdo(close, high, low, volume, taker_buy,
                         self._c.vdo_fast, self._c.vdo_slow)

    # ── Bar-by-bar decision ───────────────────────────────────────────

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._ema_slow is None or
                self._hh is None or self._atr is None or
                self._vdo is None or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        hh_val = self._hh[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(atr_val) or math.isnan(ema_f) or math.isnan(ema_s) or math.isnan(hh_val):
            return None

        if not self._in_position:
            # ENTRY: EMA crossover AND Donchian breakout AND VDO confirms
            if ema_f > ema_s and price > hh_val and vdo_val > self._c.vdo_threshold:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="vtwin_entry")
        else:
            # Track peak for trailing stop
            self._peak_price = max(self._peak_price, price)

            # EXIT 1: ATR trailing stop
            trail_stop = self._peak_price - self._c.trail_mult * atr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtwin_trail_stop")

            # EXIT 2: EMA cross-down (trend reversal)
            if ema_f < ema_s:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtwin_trend_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


# ── Vectorized indicator helpers ──────────────────────────────────────

def _highest_high(high: np.ndarray, n: int) -> np.ndarray:
    """Rolling max of high[i-n:i] for each bar i.

    hh[i] = max(high[i-n], high[i-n+1], ..., high[i-1])
    Excludes bar i itself (no lookahead). NaN for i < n.
    """
    out = np.full(len(high), np.nan)
    if n <= 0 or n >= len(high):
        return out
    windows = sliding_window_view(high, n)
    out[n:] = np.max(windows[:len(high) - n], axis=1)
    return out


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
