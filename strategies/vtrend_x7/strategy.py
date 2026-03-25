"""VTREND-X7 -- Crypto-optimised trend-following.

Long-only, binary exposure (100 % or 0 %).
Signal timeframe: H4.  Regime timeframe: D1.
D1 filter applies to ENTRY only; exit stays on H4.

Key design differences vs E5_ema21D1:
  1. D1 continuity filter (2-bar confirmation + slope)
  2. EMA crossover with ATR band (anti-whipsaw)
  3. Stretch cap (no entry after overextension)
  4. Ratchet trailing stop (never widens)
  5. Soft exit with multi-condition confirmation
  6. Cooldown after exit (2 H4 bars)
  7. VDO requires real taker data (OHLC fallback removed)

Parameters (tunable):
  slow_period         -- EMA slow period (default: 120)
  fast_period         -- EMA fast period (default: 30)
  trail_mult          -- ATR multiplier for trailing stop (default: 3.0)
  d1_ema_period       -- EMA period on D1 bars (default: 21)
  trend_entry_band    -- entry band in ATR multiples (default: 0.25)
  trend_exit_band     -- exit band in ATR multiples (default: 0.10)
  stretch_cap         -- max distance from ema_fast in ATR (default: 1.5)
  cooldown_bars       -- bars to wait after exit (default: 2)
  vdo_threshold       -- VDO threshold (default: 0.0)

Constants (structural):
  atr_period  -- 14 (Wilder standard)
  vdo_fast    -- 12
  vdo_slow    -- 28
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "vtrend_x7"


@dataclass
class VTrendX7Config:
    # Tunable (10 parameters)
    slow_period: float = 120.0
    fast_period: float = 30.0
    trail_mult: float = 3.0
    d1_ema_period: int = 21
    trend_entry_band: float = 0.25
    trend_exit_band: float = 0.10
    stretch_cap: float = 1.5
    cooldown_bars: int = 2
    vdo_threshold: float = 0.0

    # Structural constants
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28


class VTrendX7Strategy(Strategy):
    def __init__(self, config: VTrendX7Config | None = None) -> None:
        self._config = config or VTrendX7Config()
        self._c = self._config

        # Precomputed indicator arrays (H4)
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None
        self._has_taker: bool = True

        # D1 regime filter mapped to H4 index
        self._d1_regime_ok: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_close = 0.0
        self._trail_stop = 0.0
        self._bars_since_exit = 999  # large → no cooldown at start

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

        self._ema_fast = _ema(close, int(self._c.fast_period))
        self._ema_slow = _ema(close, int(self._c.slow_period))
        self._atr = _atr(high, low, close, self._c.atr_period)
        self._vdo = _vdo(close, high, low, volume, taker_buy,
                         self._c.vdo_fast, self._c.vdo_slow)
        self._has_taker = True  # enforced by _vdo() RuntimeError

        # D1 continuity regime mapped to H4 bar grid
        self._d1_regime_ok = self._compute_d1_regime(h4_bars, d1_bars)

    def _compute_d1_regime(self, h4_bars: list, d1_bars: list) -> np.ndarray:
        """D1 continuity regime: close>EMA for 2 consecutive bars + EMA rising.

        Uses only completed D1 bars -- no lookahead.
        """
        n_h4 = len(h4_bars)
        regime_ok = np.zeros(n_h4, dtype=np.bool_)

        if not d1_bars:
            return regime_ok

        d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
        d1_ema = _ema(d1_close, self._c.d1_ema_period)
        d1_close_times = [b.close_time for b in d1_bars]

        # Continuity filter: close[t]>ema[t] AND close[t-1]>ema[t-1] AND ema[t]>ema[t-3]
        n_d1 = len(d1_bars)
        d1_regime = np.zeros(n_d1, dtype=np.bool_)
        for j in range(3, n_d1):
            d1_regime[j] = (
                d1_close[j] > d1_ema[j]
                and d1_close[j - 1] > d1_ema[j - 1]
                and d1_ema[j] > d1_ema[j - 3]
            )

        # Map D1 regime to H4 bars via most-recent completed D1 bar
        d1_idx = 0
        for i in range(n_h4):
            h4_ct = h4_bars[i].close_time
            while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_ct:
                d1_idx += 1
            if d1_close_times[d1_idx] < h4_ct:
                regime_ok[i] = d1_regime[d1_idx]

        return regime_ok

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._atr is None
                or self._vdo is None or self._d1_regime_ok is None
                or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        vdo_prev = self._vdo[i - 1]
        price = state.bar.close

        if math.isnan(atr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        if not self._in_position:
            self._bars_since_exit += 1

            # --- ENTRY ---
            regime_ok = bool(self._d1_regime_ok[i])
            trend_ok = (
                ema_f > ema_s + self._c.trend_entry_band * atr_val
                and price > ema_f
            )

            flow_ok = vdo_val > self._c.vdo_threshold and vdo_val > vdo_prev

            stretch_ok = price < ema_f + self._c.stretch_cap * atr_val
            cooldown_ok = self._bars_since_exit >= self._c.cooldown_bars

            if regime_ok and trend_ok and flow_ok and stretch_ok and cooldown_ok:
                self._in_position = True
                self._peak_close = price
                self._trail_stop = price - self._c.trail_mult * atr_val
                return Signal(target_exposure=1.0, reason="x7_entry")

        else:
            # --- POSITION MANAGEMENT ---
            # Ratchet trailing stop: never widen
            self._peak_close = max(self._peak_close, price)
            trail_candidate = self._peak_close - self._c.trail_mult * atr_val
            self._trail_stop = max(self._trail_stop, trail_candidate)

            # Hard exit: trailing stop
            hard_exit = price < self._trail_stop

            # Soft exit: confirmed trend reversal
            soft_exit = False
            if i >= 2:
                vdo_prev2 = self._vdo[i - 2] if i >= 2 else 0.0
                soft_exit = (
                    ema_f < ema_s - self._c.trend_exit_band * atr_val
                    and price < ema_f
                    and vdo_val < 0
                    and vdo_prev < 0
                )

            if hard_exit:
                self._in_position = False
                self._peak_close = 0.0
                self._trail_stop = 0.0
                self._bars_since_exit = 0
                return Signal(target_exposure=0.0, reason="x7_trail_stop")

            if soft_exit:
                self._in_position = False
                self._peak_close = 0.0
                self._trail_stop = 0.0
                self._bars_since_exit = 0
                return Signal(target_exposure=0.0, reason="x7_soft_exit")

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
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if not has_taker:
        raise RuntimeError(
            "VDO requires taker_buy_base_vol data. Cannot compute VDO "
            "without real taker flow data — OHLC fallback has been removed "
            "to prevent semantic confusion (price-location != order-flow)."
        )
    n = len(close)
    taker_sell = np.maximum(volume - taker_buy, 0.0)
    vdr = np.zeros(n)
    mask = volume > 1e-12
    vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    return _ema(vdr, fast) - _ema(vdr, slow)
