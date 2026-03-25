"""X34 A3 — VTREND with per-bar quote ratio plus adaptive threshold."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy
from research.x34.branches.c_ablation.code.common import adaptive_gate
from research.x34.branches.c_ablation.code.common import atr
from research.x34.branches.c_ablation.code.common import ema

STRATEGY_ID = "vtrend_a3"


@dataclass
class VTrendA3Config:
    slow_period: float = 120.0
    trail_mult: float = 3.0
    qvdo_fast: int = 12
    qvdo_slow: int = 28
    qvdo_k: float = 1.0
    atr_period: int = 14


class VTrendA3Strategy(Strategy):
    def __init__(self, config: VTrendA3Config | None = None) -> None:
        self._config = config or VTrendA3Config()
        self._c = self._config

        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._ratio_momentum: np.ndarray | None = None
        self._theta: np.ndarray | None = None

        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return STRATEGY_ID

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        if not h4_bars:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        taker_buy_quote = np.array([b.taker_buy_quote_vol for b in h4_bars], dtype=np.float64)
        quote_volume = np.array([b.quote_volume for b in h4_bars], dtype=np.float64)

        slow_p = int(self._c.slow_period)
        fast_p = max(5, slow_p // 4)

        self._ema_fast = ema(close, fast_p)
        self._ema_slow = ema(close, slow_p)
        self._atr = atr(high, low, close, self._c.atr_period)

        delta_quote = 2.0 * taker_buy_quote - quote_volume
        ratio_source = np.zeros_like(delta_quote)
        mask = quote_volume > 0
        ratio_source[mask] = delta_quote[mask] / quote_volume[mask]

        self._ratio_momentum, self._theta = adaptive_gate(
            ratio_source,
            fast=self._c.qvdo_fast,
            slow=self._c.qvdo_slow,
            k=self._c.qvdo_k,
        )

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (
            self._ema_fast is None
            or self._ema_slow is None
            or self._atr is None
            or self._ratio_momentum is None
            or self._theta is None
            or i < 1
        ):
            return None

        ema_fast_val = self._ema_fast[i]
        ema_slow_val = self._ema_slow[i]
        atr_val = self._atr[i]
        momentum = self._ratio_momentum[i]
        theta = self._theta[i]
        price = state.bar.close

        if (
            math.isnan(ema_fast_val)
            or math.isnan(ema_slow_val)
            or math.isnan(atr_val)
        ):
            return None

        trend_up = ema_fast_val > ema_slow_val
        trend_down = ema_fast_val < ema_slow_val

        if not self._in_position:
            if trend_up and momentum > theta:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="vtrend_a3_entry")
        else:
            self._peak_price = max(self._peak_price, price)
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
