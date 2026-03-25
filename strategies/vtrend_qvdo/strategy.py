"""VTREND + Q-VDO-RH — E0 with Q-VDO-RH entry filter (Mode A).

X34 Phase 3: Replace VDO original with Q-VDO-RH as entry filter.
Exit logic unchanged (ATR trailing stop + EMA cross-down).

Parameters (tunable — preregistered from spec):
  slow_period   — EMA slow period (fast = slow // 4)
  trail_mult    — ATR trailing stop multiplier
  qvdo_fast     — Q-VDO-RH fast EMA period
  qvdo_slow     — Q-VDO-RH slow EMA period (also normalizer)
  qvdo_k        — Q-VDO-RH threshold multiplier

Constants (structural, not optimized):
  atr_period    — 14 (Wilder standard)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy
from strategies.vtrend_qvdo.q_vdo_rh import q_vdo_rh


@dataclass
class VTrendQVDOConfig:
    # E0 structure (unchanged)
    slow_period: float = 120.0
    trail_mult: float = 3.0

    # Q-VDO-RH params (preregistered from spec)
    qvdo_fast: int = 12
    qvdo_slow: int = 28
    qvdo_k: float = 1.0

    # Structural constants (not tuned)
    atr_period: int = 14


class VTrendQVDOStrategy(Strategy):
    def __init__(self, config: VTrendQVDOConfig | None = None) -> None:
        self._config = config or VTrendQVDOConfig()
        self._c = self._config

        # Precomputed indicator arrays (set in on_init)
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._qvdo_momentum: np.ndarray | None = None
        self._qvdo_theta: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return "vtrend_qvdo"

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        taker_buy_quote = np.array([b.taker_buy_quote_vol for b in h4_bars], dtype=np.float64)
        quote_volume = np.array([b.quote_volume for b in h4_bars], dtype=np.float64)

        slow_p = int(self._c.slow_period)
        fast_p = max(5, slow_p // 4)

        self._ema_fast = _ema(close, fast_p)
        self._ema_slow = _ema(close, slow_p)
        self._atr = _atr(high, low, close, self._c.atr_period)

        # Q-VDO-RH Mode A
        qvdo = q_vdo_rh(
            taker_buy_quote, quote_volume,
            fast=self._c.qvdo_fast,
            slow=self._c.qvdo_slow,
            k=self._c.qvdo_k,
        )
        self._qvdo_momentum = qvdo.momentum
        self._qvdo_theta = qvdo.theta

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._atr is None or
                self._qvdo_momentum is None or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        momentum = self._qvdo_momentum[i]
        theta = self._qvdo_theta[i]
        price = state.bar.close

        if math.isnan(atr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            # ENTRY: trend up AND Q-VDO-RH momentum > adaptive threshold
            if trend_up and momentum > theta:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="vtrend_qvdo_entry")
        else:
            # Track peak for trailing stop
            self._peak_price = max(self._peak_price, price)

            # EXIT: trailing stop OR trend reversal (unchanged from E0)
            trail_stop = self._peak_price - self._c.trail_mult * atr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtrend_trail_stop")

            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtrend_trend_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


# ── Vectorized indicator helpers (from vtrend/strategy.py, verbatim) ──

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
