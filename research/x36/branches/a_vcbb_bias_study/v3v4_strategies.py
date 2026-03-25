"""V3 (post-2021 favorable) and V4 (full-history winner) VTREND strategies.

V3: weakvdo_freeze_0.0065 + trail3.3_close_current_confirm2 + no_trend_exit
    + cooldown6 + time_stop30
V4: weak_f_0065 + trail2.8_close_lagged_confirm1 + no_trend_exit
    + cooldown3 + time_stop60

Both share: EMA30/120, D1 EMA21 regime, robust ATR(20), VDO(12,28).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal, Side
from v10.strategies.base import Strategy

WEAK_VDO_THR = 0.0065


# ── Indicator helpers (identical to E5+EMA21D1) ────────────────────────

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _robust_atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    cap_q: float = 0.90,
    cap_lb: int = 100,
    period: int = 20,
) -> np.ndarray:
    """Robust ATR: cap TR at rolling P90 quantile, then Wilder EMA(20)."""
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


# ── Base class for V3/V4 ──────────────────────────────────────────────

class _VTrendExtBase(Strategy):
    """Shared base for V3 and V4 strategies.

    Subclasses set class-level constants for trail/cooldown/time-stop.
    """

    # Override in subclass
    TRAIL_MULT: float = 3.0
    TRAIL_CONFIRM: int = 1
    COOLDOWN_BARS: int = 0
    TIME_STOP_BARS: int = 0
    USE_LAGGED_ATR: bool = False
    USE_ACTIVITY: bool = False

    def __init__(self) -> None:
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._ratr: np.ndarray | None = None
        self._vdo_arr: np.ndarray | None = None
        self._freshness: np.ndarray | None = None
        self._activity: np.ndarray | None = None
        self._d1_regime_ok: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_close = 0.0
        self._breach_streak = 0
        self._entry_fill_bar: int | None = None
        self._last_exit_bar: int | None = None

    # ── Precompute indicators ────────────────────────────────────────

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
            return

        cl = np.array([b.close for b in h4_bars], dtype=np.float64)
        hi = np.array([b.high for b in h4_bars], dtype=np.float64)
        lo = np.array([b.low for b in h4_bars], dtype=np.float64)
        vol = np.array([b.volume for b in h4_bars], dtype=np.float64)
        tb = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)

        if not np.any(tb > 0):
            raise RuntimeError("VDO requires taker_buy_base_vol data.")

        self._ema_fast = _ema(cl, 30)
        self._ema_slow = _ema(cl, 120)
        self._ratr = _robust_atr(hi, lo, cl)

        # Imbalance ratio base = (2*tb - vol) / vol
        irb = np.zeros(n)
        mask = vol > 0
        irb[mask] = (2.0 * tb[mask] - vol[mask]) / vol[mask]

        # VDO = EMA12(irb) - EMA28(irb)
        self._vdo_arr = _ema(irb, 12) - _ema(irb, 28)

        # Freshness = EMA28(irb)  (= vdo_slow leg)
        self._freshness = _ema(irb, 28)

        # Activity (V3 only): EMA12(quote_vol / EMA28(quote_vol))
        if self.USE_ACTIVITY:
            qv = np.array([b.quote_volume for b in h4_bars], dtype=np.float64)
            ema28_qv = _ema(qv, 28)
            surprise = np.ones(n)
            m = ema28_qv > 0
            surprise[m] = qv[m] / ema28_qv[m]
            self._activity = _ema(surprise, 12)

        # D1 regime filter
        self._d1_regime_ok = self._compute_d1_regime(h4_bars, d1_bars)

    def _compute_d1_regime(
        self, h4_bars: list, d1_bars: list,
    ) -> np.ndarray:
        n_h4 = len(h4_bars)
        regime_ok = np.zeros(n_h4, dtype=np.bool_)
        if not d1_bars:
            return regime_ok

        d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
        d1_ema = _ema(d1_close, 21)
        d1_ct = [b.close_time for b in d1_bars]
        d1_regime = d1_close > d1_ema

        d1_idx = 0
        n_d1 = len(d1_bars)
        for i in range(n_h4):
            h4_ct = h4_bars[i].close_time
            while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct:
                d1_idx += 1
            if d1_ct[d1_idx] < h4_ct:
                regime_ok[i] = d1_regime[d1_idx]
        return regime_ok

    # ── Bar-by-bar decision ──────────────────────────────────────────

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if self._ema_fast is None or i < 1:
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        price = state.bar.close

        if math.isnan(ema_f) or math.isnan(ema_s):
            return None

        if not self._in_position:
            return self._try_entry(i, price, ema_f, ema_s)
        return self._try_exit(i, price)

    def _try_entry(
        self, i: int, price: float, ema_f: float, ema_s: float,
    ) -> Signal | None:
        # Cooldown gate
        if self._last_exit_bar is not None:
            if (i + 1) <= self._last_exit_bar + self.COOLDOWN_BARS:
                return None

        trend_up = ema_f > ema_s
        regime_ok = bool(self._d1_regime_ok[i])
        if not (trend_up and regime_ok):
            return None

        vdo = self._vdo_arr[i]

        # Case A: strong positive VDO
        if vdo > WEAK_VDO_THR:
            return self._fire_entry(price)

        # Case B: weak positive VDO with support
        if 0 < vdo <= WEAK_VDO_THR:
            freshness_ok = self._freshness[i] <= 0.0
            if self.USE_ACTIVITY:
                activity_ok = (
                    self._activity is not None and self._activity[i] >= 1.0
                )
                if freshness_ok and activity_ok:
                    return self._fire_entry(price)
            else:
                if freshness_ok:
                    return self._fire_entry(price)

        return None

    def _fire_entry(self, price: float) -> Signal:
        self._in_position = True
        self._peak_close = price
        self._breach_streak = 0
        return Signal(target_exposure=1.0, reason=f"{self.name()}_entry")

    def _try_exit(self, i: int, price: float) -> Signal | None:
        # Update peak (close-anchored)
        self._peak_close = max(self._peak_close, price)

        # Determine ATR value
        if self.USE_LAGGED_ATR:
            ratr_val = self._ratr[i - 1] if i > 0 else np.nan
        else:
            ratr_val = self._ratr[i]

        if math.isnan(ratr_val):
            return None

        # Trail stop
        trail_stop = self._peak_close - self.TRAIL_MULT * ratr_val
        breach = price < trail_stop

        if breach:
            self._breach_streak += 1
        else:
            self._breach_streak = 0

        if self._breach_streak >= self.TRAIL_CONFIRM:
            return self._fire_exit(f"{self.name()}_trail_stop")

        # Time stop (no trend exit — removed per spec)
        if self.TIME_STOP_BARS > 0 and self._entry_fill_bar is not None:
            if (i + 1) == self._entry_fill_bar + self.TIME_STOP_BARS:
                return self._fire_exit(f"{self.name()}_time_stop")

        return None

    def _fire_exit(self, reason: str) -> Signal:
        self._in_position = False
        self._peak_close = 0.0
        self._breach_streak = 0
        return Signal(target_exposure=0.0, reason=reason)

    # ── Post-fill state tracking ─────────────────────────────────────

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        if fill.side == Side.BUY:
            self._entry_fill_bar = state.bar_index
            self._peak_close = fill.price  # Spec: init to fill open price
            self._breach_streak = 0
        else:
            self._last_exit_bar = state.bar_index
            self._entry_fill_bar = None


# ── Concrete strategies ──────────────────────────────────────────────

class V3Strategy(_VTrendExtBase):
    """V3: post-2021 favorable — activity+freshness, trail 3.3 confirm2,
    cooldown 6, time stop 30, current ATR."""

    TRAIL_MULT = 3.3
    TRAIL_CONFIRM = 2
    COOLDOWN_BARS = 6
    TIME_STOP_BARS = 30
    USE_LAGGED_ATR = False
    USE_ACTIVITY = True

    def name(self) -> str:
        return "v3_post2021"


class V4Strategy(_VTrendExtBase):
    """V4: full-history winner — freshness only, trail 2.8 confirm1,
    cooldown 3, time stop 60, lagged ATR."""

    TRAIL_MULT = 2.8
    TRAIL_CONFIRM = 1
    COOLDOWN_BARS = 3
    TIME_STOP_BARS = 60
    USE_LAGGED_ATR = True
    USE_ACTIVITY = False

    def name(self) -> str:
        return "v4_fullhistory"
