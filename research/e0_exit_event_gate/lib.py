from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from research.e0_exit_floor.p0_1_exit_floor_benchmark import ExitFloorConfig, X0ExitFloorStrategy
from v10.core.types import Fill, MarketState, Signal


@dataclass
class EventGateConfig(ExitFloorConfig):
    gate_mode: str = "below_slow"  # below_slow | peak_age_ge_3
    peak_age_bars: int = 3


class EventGatedFloorStrategy(X0ExitFloorStrategy):
    def __init__(self, config: EventGateConfig) -> None:
        super().__init__(config)
        self._gc = config
        self._peak_idx: int | None = None
        self._gate_counts = {
            "floor_hits_total": 0,
            "floor_hits_armed": 0,
            "floor_hits_blocked": 0,
        }

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
                self._peak_idx = i
                return Signal(target_exposure=1.0, reason=f"{self._c.strategy_id}_entry")
            return None

        if price >= self._peak_price:
            self._peak_price = price
            self._peak_idx = i

        floor_stop = self._floor_stop(i) if self._c.floor_mode != "none" else math.nan
        if np.isfinite(floor_stop) and price < floor_stop:
            self._gate_counts["floor_hits_total"] += 1
            if self._allow_floor_exit(i, price, ema_s):
                self._in_position = False
                self._peak_price = 0.0
                self._peak_idx = None
                self._gate_counts["floor_hits_armed"] += 1
                return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_floor_exit")
            self._gate_counts["floor_hits_blocked"] += 1

        trail_stop = self._peak_price - self._c.trail_mult * ratr_val
        if price < trail_stop:
            self._in_position = False
            self._peak_price = 0.0
            self._peak_idx = None
            return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trail_stop")

        if trend_down:
            self._in_position = False
            self._peak_price = 0.0
            self._peak_idx = None
            return Signal(target_exposure=0.0, reason=f"{self._c.strategy_id}_trend_exit")

        return None

    def _allow_floor_exit(self, i: int, price: float, ema_s: float) -> bool:
        if self._gc.gate_mode == "below_slow":
            return price <= ema_s
        if self._gc.gate_mode == "peak_age_ge_3":
            peak_idx = self._peak_idx if self._peak_idx is not None else i
            return (i - peak_idx) >= self._gc.peak_age_bars
        raise ValueError(f"unknown gate_mode: {self._gc.gate_mode}")

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass

    def get_gate_stats(self) -> dict[str, int]:
        return dict(self._gate_counts)
