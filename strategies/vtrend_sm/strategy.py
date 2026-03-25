"""VTREND-SM — State-machine trend-following strategy.

Ported from Latch/research/vtrend_variants.py (run_vtrend_state_machine).

Entry: regime_ok AND close > rolling_high(high.shift(1), entry_n) AND optional VDO
Exit:  close < max(rolling_low(low.shift(1), exit_n), ema_slow - atr_mult * ATR)
       OR optional regime break
Sizing: target_vol / realized_vol, clipped to [0, 1], with min_weight threshold
Rebalance: only when |target - current| >= min_rebalance_weight_delta OR zero-crossing

Parameters (tunable):
  slow_period   — EMA slow period (fast = max(5, slow // 4))
  atr_mult      — ATR multiplier for exit floor
  target_vol    — annualized volatility target for position sizing
  entry_n       — rolling high lookback (auto: max(24, slow // 2))
  exit_n        — rolling low lookback (auto: max(12, slow // 4))
  slope_lookback — bars to look back for EMA slow slope confirmation
  use_vdo_filter — enable VDO entry filter (default: off)
  exit_on_regime_break — force exit when regime flips off (default: off)

Constants (structural, not optimized):
  atr_period    — 14 (Wilder standard)
  vdo_fast      — 12
  vdo_slow      — 28
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "vtrend_sm"
BARS_PER_YEAR_4H: float = 365.0 * 6.0  # 2190.0 — matches source and metrics.py
EPS: float = 1e-12


# ── Config ──────────────────────────────────────────────────────────────

@dataclass
class VTrendSMConfig:
    slow_period: int = 120
    fast_period: int | None = None       # auto: max(5, slow_period // 4)
    atr_period: int = 14
    atr_mult: float = 3.0
    entry_n: int | None = None           # auto: max(24, slow_period // 2)
    exit_n: int | None = None            # auto: max(12, slow_period // 4)
    target_vol: float = 0.15
    vol_lookback: int | None = None      # auto: slow_period
    slope_lookback: int = 6
    use_vdo_filter: bool = False
    vdo_threshold: float = 0.0
    vdo_fast: int = 12
    vdo_slow: int = 28
    exit_on_regime_break: bool = False
    min_rebalance_weight_delta: float = 0.05
    min_weight: float = 0.0

    def __post_init__(self) -> None:
        if self.slope_lookback <= 0:
            raise ValueError("slope_lookback must be > 0")

    def resolved(self) -> dict[str, Any]:
        """Return dict with all auto-derived params resolved."""
        fast_period = (
            self.fast_period
            if self.fast_period is not None
            else max(5, self.slow_period // 4)
        )
        entry_n = (
            self.entry_n
            if self.entry_n is not None
            else max(24, self.slow_period // 2)
        )
        exit_n = (
            self.exit_n
            if self.exit_n is not None
            else max(12, self.slow_period // 4)
        )
        vol_lookback = (
            self.vol_lookback
            if self.vol_lookback is not None
            else self.slow_period
        )
        return {
            **asdict(self),
            "fast_period": int(fast_period),
            "entry_n": int(entry_n),
            "exit_n": int(exit_n),
            "vol_lookback": int(vol_lookback),
        }


# ── Vectorized indicator helpers ────────────────────────────────────────

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """EMA with standard span weighting (adjust=False)."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    """Average True Range (Wilder's method)."""
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


def _rolling_high_shifted(high: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling max of high over previous `lookback` bars (excluding current).

    At index i: max(high[i-lookback], ..., high[i-1]).
    Equivalent to pandas: high.shift(1).rolling(window=lookback, min_periods=lookback).max()
    """
    n = len(high)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.max(high[i - lookback:i])
    return out


def _rolling_low_shifted(low: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling min of low over previous `lookback` bars (excluding current).

    At index i: min(low[i-lookback], ..., low[i-1]).
    Equivalent to pandas: low.shift(1).rolling(window=lookback, min_periods=lookback).min()
    """
    n = len(low)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.min(low[i - lookback:i])
    return out


def _realized_vol(close: np.ndarray, lookback: int,
                  bars_per_year: float) -> np.ndarray:
    """Annualized realized volatility from log returns.

    Rolling std(ddof=0) * sqrt(bars_per_year).
    Equivalent to pandas: log_returns.rolling(window=lookback, min_periods=lookback).std(ddof=0)
    """
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    lr = np.full(n, np.nan, dtype=np.float64)
    lr[1:] = np.log(
        np.divide(
            close[1:],
            close[:-1],
            out=np.full(n - 1, np.nan, dtype=np.float64),
            where=close[:-1] > 0.0,
        )
    )
    ann_factor = math.sqrt(bars_per_year)
    for i in range(lookback, n):
        window = lr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=0)) * ann_factor
    return out


def _clip_weight(weight: float, min_weight: float = 0.0) -> float:
    """Clip weight to [0, 1] with min_weight gate."""
    if not np.isfinite(weight):
        return 0.0
    w = min(1.0, max(0.0, float(weight)))
    if w < min_weight:
        return 0.0
    return w


# ── Strategy ────────────────────────────────────────────────────────────

class VTrendSMStrategy(Strategy):
    def __init__(self, config: VTrendSMConfig | None = None) -> None:
        self._config = config or VTrendSMConfig()
        self._r = self._config.resolved()

        # Precomputed indicator arrays (set in on_init)
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._ema_slow_slope_ref: np.ndarray | None = None
        self._atr_arr: np.ndarray | None = None
        self._hh_entry: np.ndarray | None = None
        self._ll_exit: np.ndarray | None = None
        self._rv: np.ndarray | None = None
        self._vdo_arr: np.ndarray | None = None

        # Runtime state
        self._active = False
        self._warmup_end: int = 0

    def name(self) -> str:
        return STRATEGY_ID

    # ── Precompute indicators on full bar arrays ────────────────────────

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        taker_buy = np.array(
            [b.taker_buy_base_vol for b in h4_bars], dtype=np.float64
        )

        r = self._r

        self._ema_fast = _ema(close, r["fast_period"])
        self._ema_slow = _ema(close, r["slow_period"])

        # EMA slow slope reference: ema_slow shifted by slope_lookback bars
        sl = r["slope_lookback"]
        self._ema_slow_slope_ref = np.full(n, np.nan, dtype=np.float64)
        if sl > 0 and sl < n:
            self._ema_slow_slope_ref[sl:] = self._ema_slow[:-sl]

        self._atr_arr = _atr(high, low, close, r["atr_period"])
        self._hh_entry = _rolling_high_shifted(high, r["entry_n"])
        self._ll_exit = _rolling_low_shifted(low, r["exit_n"])
        self._rv = _realized_vol(close, r["vol_lookback"], BARS_PER_YEAR_4H)

        if r["use_vdo_filter"]:
            self._vdo_arr = _vdo(
                close, high, low, volume, taker_buy,
                r["vdo_fast"], r["vdo_slow"],
            )

        # First index where ALL indicators are finite
        self._warmup_end = self._compute_warmup(n)

    def _compute_warmup(self, n: int) -> int:
        """Find first bar index where all indicators are valid (finite)."""
        arrays = [
            self._ema_fast, self._ema_slow, self._ema_slow_slope_ref,
            self._atr_arr, self._hh_entry, self._ll_exit, self._rv,
        ]
        if self._vdo_arr is not None:
            arrays.append(self._vdo_arr)
        for i in range(n):
            if all(np.isfinite(a[i]) for a in arrays):
                return i
        return n

    # ── Bar-by-bar decision ─────────────────────────────────────────────

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        r = self._r

        if self._ema_fast is None or i < self._warmup_end:
            return None

        close_val = state.bar.close
        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        ema_s_ref = self._ema_slow_slope_ref[i]
        atr_val = self._atr_arr[i]
        hh = self._hh_entry[i]
        ll = self._ll_exit[i]
        rv = self._rv[i]

        if not (
            np.isfinite(ema_f) and np.isfinite(ema_s)
            and np.isfinite(ema_s_ref) and np.isfinite(atr_val)
            and np.isfinite(hh) and np.isfinite(ll) and np.isfinite(rv)
        ):
            return None

        # Regime check (per-bar, no hysteresis — faithful to source)
        regime_ok = (ema_f > ema_s) and (ema_s > ema_s_ref)

        if not self._active:
            # ── FLAT: check entry ───────────────────────────────────
            breakout_ok = close_val > hh
            vdo_ok = True
            if r["use_vdo_filter"] and self._vdo_arr is not None:
                vdo_val = self._vdo_arr[i]
                if not np.isfinite(vdo_val):
                    return None
                vdo_ok = vdo_val > r["vdo_threshold"]

            if regime_ok and breakout_ok and vdo_ok:
                weight = _clip_weight(
                    r["target_vol"] / max(rv, EPS), r["min_weight"]
                )
                if weight > 0.0:
                    self._active = True
                    return Signal(
                        target_exposure=weight, reason="vtrend_sm_entry"
                    )
        else:
            # ── LONG: check exit ────────────────────────────────────
            exit_floor = max(ll, ema_s - r["atr_mult"] * atr_val)
            floor_break = close_val < exit_floor
            regime_break = r["exit_on_regime_break"] and (not regime_ok)

            if floor_break or regime_break:
                self._active = False
                reason = (
                    "vtrend_sm_floor_exit" if floor_break
                    else "vtrend_sm_regime_exit"
                )
                return Signal(target_exposure=0.0, reason=reason)

            # ── LONG: check rebalance ───────────────────────────────
            new_weight = _clip_weight(
                r["target_vol"] / max(rv, EPS), r["min_weight"]
            )
            delta = abs(new_weight - state.exposure)
            if delta >= r["min_rebalance_weight_delta"] - 1e-12:
                return Signal(
                    target_exposure=new_weight, reason="vtrend_sm_rebalance"
                )

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass
