"""VP1-E5exit — VP1 structure with E5 robust ATR trail exit.

Takes VP1's unique structural features:
  - Strict prevday D1 mapping (UTC date d → D1 date d-1)
  - Per-bar VDO auto path + EMA_nan_carry
  - Anomaly bar handling
  - VP1 parameters: slow=140, fast=35, trail=2.5, d1_ema=28

Replaces ONLY the exit ATR:
  - Standard Wilder ATR(20) → E5 robust ATR (quantile-capped)

This isolates the question: does RATR improve VP1's trailing stop?
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

# Reuse VP1's indicator helpers for shared logic
from strategies.vtrend_vp1.strategy import (
    _ema,
    _vdo_auto,
    _d1_prevday_regime,
)


@dataclass
class VP1E5ExitConfig:
    # VP1 tunable parameters (unchanged)
    slow_period: float = 140.0
    trail_mult: float = 2.5
    vdo_threshold: float = 0.0
    d1_ema_period: int = 28

    # VP1 structural constants
    vdo_fast: int = 12
    vdo_slow: int = 28
    warmup_days: int = 365

    # E5 robust ATR parameters (replacing standard Wilder)
    ratr_cap_q: float = 0.90
    ratr_cap_lb: int = 100
    ratr_period: int = 20


class VP1E5ExitStrategy(Strategy):
    def __init__(self, config: VP1E5ExitConfig | None = None) -> None:
        self._config = config or VP1E5ExitConfig()
        self._c = self._config

        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._ratr: np.ndarray | None = None  # robust ATR, not standard
        self._vdo: np.ndarray | None = None
        self._d1_regime_ok: np.ndarray | None = None
        self._anomaly: np.ndarray | None = None

        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return "vtrend_vp1_e5exit"

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        taker_buy = np.array(
            [b.taker_buy_base_vol for b in h4_bars], dtype=np.float64,
        )

        slow_p = int(self._c.slow_period)
        fast_p = max(5, slow_p // 4)

        self._ema_fast = _ema(close, fast_p)
        self._ema_slow = _ema(close, slow_p)

        # KEY CHANGE: E5 robust ATR instead of standard Wilder
        self._ratr = _robust_atr(
            high, low, close,
            cap_q=self._c.ratr_cap_q,
            cap_lb=self._c.ratr_cap_lb,
            period=self._c.ratr_period,
        )

        # VP1 structural features (unchanged)
        self._vdo = _vdo_auto(
            close, high, low, volume, taker_buy,
            self._c.vdo_fast, self._c.vdo_slow,
        )
        self._d1_regime_ok = _d1_prevday_regime(
            h4_bars, d1_bars, self._c.d1_ema_period,
        )
        self._anomaly = volume <= 0

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._ratr is None
                or self._vdo is None or self._d1_regime_ok is None
                or i < 1):
            return None

        if self._anomaly is not None and self._anomaly[i]:
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        ratr_val = self._ratr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(ema_f) or math.isnan(ema_s):
            return None

        if not self._in_position:
            if math.isnan(vdo_val):
                return None
            regime_ok = bool(self._d1_regime_ok[i])
            if ema_f > ema_s and vdo_val > self._c.vdo_threshold and regime_ok:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="vp1e5_entry")
        else:
            self._peak_price = max(self._peak_price, price)

            if not math.isnan(ratr_val):
                trail_stop = self._peak_price - self._c.trail_mult * ratr_val
                if price < trail_stop:
                    self._in_position = False
                    self._peak_price = 0.0
                    return Signal(target_exposure=0.0, reason="vp1e5_trailing_stop")

            if ema_f < ema_s:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vp1e5_trend_reversal")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


# -- E5 Robust ATR (copied from E5 strategy) --------------------------------

def _robust_atr(
    high: np.ndarray, low: np.ndarray, close: np.ndarray,
    cap_q: float = 0.90, cap_lb: int = 100, period: int = 20,
) -> np.ndarray:
    """Robust ATR: cap TR at rolling quantile, then Wilder EMA."""
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )

    n = len(tr)
    tr_cap = np.full(n, np.nan)

    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)

    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period

    return ratr
