"""LATCH — Hysteretic trend-following strategy with 3-state machine.

Ported from Latch/research/Latch/ package (run_latch).

Entry: regime_on (hysteretic) AND close > hh_entry (breakout)
Exit:  close < max(ll_exit, ema_slow - atr_mult * ATR) OR regime_flip_off
Sizing: target_vol / max(rv, vol_floor, EPS), clipped to [0, max_pos]
Rebalance: only when |target - current| >= min_rebalance_weight_delta OR zero-crossing

State machine:
  OFF   -> ARMED  (regime ON, no breakout)
  OFF   -> LONG   (regime ON AND breakout)
  ARMED -> OFF    (regime OFF trigger)
  ARMED -> LONG   (breakout while regime ON)
  LONG  -> OFF    (floor break OR regime flip OFF)

Parameters (13 core):
  slow_period, fast_period, slope_lookback, entry_n, exit_n
  atr_period, atr_mult
  vol_lookback, target_vol, vol_floor
  max_pos, min_weight, min_rebalance_weight_delta

Optional VDO overlay (15 fields, default mode="none"):
  vdo_mode, vdo_z_lookback, vdo_fast, vdo_slow
  4 z-score thresholds, 4 size_mod multipliers, 2 throttle multipliers
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Any

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "latch"
BARS_PER_YEAR_4H: float = 365.0 * 6.0  # 2190.0 — matches source
EPS: float = 1e-12


# ── State enum ─────────────────────────────────────────────────────────

class _LatchState(IntEnum):
    OFF = 0
    ARMED = 1
    LONG = 2


# ── Config ──────────────────────────────────────────────────────────────

@dataclass
class LatchConfig:
    # Core parameters (13)
    slow_period: int = 120
    fast_period: int = 30
    slope_lookback: int = 6
    entry_n: int = 60
    exit_n: int = 30
    atr_period: int = 14
    atr_mult: float = 2.0
    vol_lookback: int = 120
    target_vol: float = 0.12
    vol_floor: float = 0.08
    max_pos: float = 1.0
    min_weight: float = 0.0
    min_rebalance_weight_delta: float = 0.05

    # VDO overlay (15 fields, default: off)
    vdo_mode: str = "none"
    vdo_z_lookback: int = 120
    vdo_fast: int = 12
    vdo_slow: int = 28
    vdo_strong_pos_z: float = 1.0
    vdo_neutral_z: float = 0.0
    vdo_mild_neg_z: float = -0.5
    vdo_strong_neg_z: float = -1.0
    vdo_size_mult_strong_pos: float = 1.00
    vdo_size_mult_neutral: float = 0.80
    vdo_size_mult_mild_neg: float = 0.55
    vdo_size_mult_strong_neg: float = 0.25
    vdo_throttle_mult_mild_neg: float = 0.75
    vdo_throttle_mult_strong_neg: float = 0.50

    def __post_init__(self) -> None:
        if self.slow_period <= 1:
            raise ValueError("slow_period must be > 1")
        if self.fast_period <= 1:
            raise ValueError("fast_period must be > 1")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be < slow_period")
        if self.slope_lookback <= 0:
            raise ValueError("slope_lookback must be > 0")
        if self.entry_n <= 0 or self.exit_n <= 0:
            raise ValueError("entry_n and exit_n must be > 0")
        if self.atr_period <= 0:
            raise ValueError("atr_period must be > 0")
        if self.atr_mult <= 0.0:
            raise ValueError("atr_mult must be > 0")
        if self.vol_lookback <= 1:
            raise ValueError("vol_lookback must be > 1")
        if self.target_vol <= 0.0:
            raise ValueError("target_vol must be > 0")
        if self.vol_floor <= 0.0:
            raise ValueError("vol_floor must be > 0")
        if not (0.0 < self.max_pos <= 1.0):
            raise ValueError("max_pos must be in (0, 1]")
        if self.min_weight < 0.0:
            raise ValueError("min_weight must be >= 0")
        if self.min_rebalance_weight_delta < 0.0:
            raise ValueError("min_rebalance_weight_delta must be >= 0")

    def resolved(self) -> dict[str, Any]:
        """Return dict with all params (no auto-derivation in LATCH)."""
        return asdict(self)


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


def _rolling_high_shifted(high: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling max of high over previous `lookback` bars (excluding current).

    At index i: max(high[i-lookback], ..., high[i-1]).
    """
    n = len(high)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.max(high[i - lookback:i])
    return out


def _rolling_low_shifted(low: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling min of low over previous `lookback` bars (excluding current).

    At index i: min(low[i-lookback], ..., low[i-1]).
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


def _clip_weight(weight: float, max_pos: float, min_weight: float = 0.0) -> float:
    """Clip weight to [0, max_pos] with min_weight gate."""
    if not np.isfinite(weight):
        return 0.0
    w = min(max_pos, max(0.0, float(weight)))
    if w < min_weight:
        return 0.0
    return w


# ── Hysteretic regime ──────────────────────────────────────────────────

def _compute_hysteretic_regime(
    ema_fast: np.ndarray,
    ema_slow: np.ndarray,
    slope_ref: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute hysteretic regime with memory.

    ON trigger:  fast > slow AND slow > slope_ref
    OFF trigger: fast < slow AND slow < slope_ref
    Neither → hold previous state (hysteresis).

    Returns (regime_on, off_trigger, flip_off).
    """
    n = len(ema_fast)
    regime_on = np.zeros(n, dtype=np.bool_)
    off_trigger = np.zeros(n, dtype=np.bool_)
    flip_off = np.zeros(n, dtype=np.bool_)

    active = False
    for i in range(n):
        fi = ema_fast[i]
        si = ema_slow[i]
        ri = slope_ref[i]

        if not (np.isfinite(fi) and np.isfinite(si) and np.isfinite(ri)):
            regime_on[i] = active
            continue

        on = bool((fi > si) and (si > ri))
        off = bool((fi < si) and (si < ri))
        off_trigger[i] = off

        prev = active
        if (not active) and on:
            active = True
        elif active and off:
            active = False

        regime_on[i] = active
        flip_off[i] = bool(prev and (not active))

    return regime_on, off_trigger, flip_off


# ── VDO overlay helpers ────────────────────────────────────────────────

def _rolling_zscore(arr: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling z-score: (x - rolling_mean) / max(rolling_std, EPS)."""
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback - 1, n):
        window = arr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            mean = float(np.mean(window))
            std = float(np.std(window, ddof=0))
            out[i] = (arr[i] - mean) / max(std, EPS)
    return out


def _apply_vdo_overlay(base_weight: float, vdo_z: float,
                       r: dict[str, Any]) -> float:
    """Apply VDO overlay to base weight.

    Modes:
      size_mod: 4-tier z-score interpolation → multiplier
      throttle: 2-tier z-score reduction
      ranker: passthrough
    """
    mode = r["vdo_mode"]
    if mode == "none":
        return base_weight

    z = float(vdo_z)

    if mode == "size_mod":
        if not np.isfinite(z):
            mult = r["vdo_size_mult_neutral"]
        elif z >= r["vdo_strong_pos_z"]:
            mult = r["vdo_size_mult_strong_pos"]
        elif z >= r["vdo_neutral_z"]:
            mult = r["vdo_size_mult_neutral"]
        elif z >= r["vdo_mild_neg_z"]:
            mult = r["vdo_size_mult_mild_neg"]
        elif z <= r["vdo_strong_neg_z"]:
            mult = r["vdo_size_mult_strong_neg"]
        else:
            # Between mild-negative and strong-negative: blend smoothly
            span = max(r["vdo_mild_neg_z"] - r["vdo_strong_neg_z"], EPS)
            frac = (z - r["vdo_strong_neg_z"]) / span
            mult = (r["vdo_size_mult_strong_neg"]
                    + frac * (r["vdo_size_mult_mild_neg"]
                              - r["vdo_size_mult_strong_neg"]))
        return base_weight * float(mult)

    if mode == "throttle":
        if not np.isfinite(z):
            mult = 1.0
        elif z <= r["vdo_strong_neg_z"]:
            mult = r["vdo_throttle_mult_strong_neg"]
        elif z <= r["vdo_mild_neg_z"]:
            mult = r["vdo_throttle_mult_mild_neg"]
        else:
            mult = 1.0
        return base_weight * float(mult)

    # ranker: passthrough
    return base_weight


# ── Strategy ────────────────────────────────────────────────────────────

class LatchStrategy(Strategy):
    def __init__(self, config: LatchConfig | None = None) -> None:
        self._config = config or LatchConfig()
        self._r = self._config.resolved()

        # Precomputed indicator arrays (set in on_init)
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._slope_ref: np.ndarray | None = None
        self._atr_arr: np.ndarray | None = None
        self._hh_entry: np.ndarray | None = None
        self._ll_exit: np.ndarray | None = None
        self._rv: np.ndarray | None = None

        # Precomputed hysteretic regime arrays
        self._regime_on: np.ndarray | None = None
        self._regime_off_trigger: np.ndarray | None = None
        self._regime_flip_off: np.ndarray | None = None

        # VDO overlay (optional)
        self._vdo_arr: np.ndarray | None = None
        self._vdo_z: np.ndarray | None = None

        # Runtime state
        self._state = _LatchState.OFF
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

        # Slope reference: ema_slow shifted by slope_lookback bars
        sl = r["slope_lookback"]
        self._slope_ref = np.full(n, np.nan, dtype=np.float64)
        if 0 < sl < n:
            self._slope_ref[sl:] = self._ema_slow[:-sl]

        self._atr_arr = _atr(high, low, close, r["atr_period"])
        self._hh_entry = _rolling_high_shifted(high, r["entry_n"])
        self._ll_exit = _rolling_low_shifted(low, r["exit_n"])
        self._rv = _realized_vol(close, r["vol_lookback"], BARS_PER_YEAR_4H)

        # Hysteretic regime (precomputed on full arrays)
        (self._regime_on,
         self._regime_off_trigger,
         self._regime_flip_off) = _compute_hysteretic_regime(
            self._ema_fast, self._ema_slow, self._slope_ref
        )

        # VDO overlay (optional)
        if r["vdo_mode"] in ("size_mod", "throttle"):
            self._vdo_arr = _vdo(
                close, high, low, volume, taker_buy,
                r["vdo_fast"], r["vdo_slow"],
            )
            self._vdo_z = _rolling_zscore(self._vdo_arr, r["vdo_z_lookback"])

        # First index where ALL core indicators are finite
        self._warmup_end = self._compute_warmup(n)

    def _compute_warmup(self, n: int) -> int:
        """Find first bar index where all core indicators are valid."""
        arrays = [
            self._ema_fast, self._ema_slow, self._slope_ref,
            self._atr_arr, self._hh_entry, self._ll_exit, self._rv,
        ]
        for i in range(n):
            if all(np.isfinite(a[i]) for a in arrays):
                return i
        return n

    def _compute_weight(self, rv_val: float, bar_idx: int) -> float:
        """Compute position weight with optional VDO overlay."""
        r = self._r
        rv_i = max(rv_val, r["vol_floor"], EPS)
        raw_weight = r["target_vol"] / rv_i
        weight = _clip_weight(raw_weight, r["max_pos"], r["min_weight"])

        if r["vdo_mode"] != "none" and self._vdo_z is not None:
            vdo_z_val = self._vdo_z[bar_idx]
            weight = _apply_vdo_overlay(weight, vdo_z_val, r)
            weight = _clip_weight(weight, r["max_pos"], r["min_weight"])

        return weight

    # ── Bar-by-bar decision ─────────────────────────────────────────────

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        r = self._r

        if self._ema_fast is None or i < self._warmup_end:
            return None

        close_val = state.bar.close

        # Read precomputed regime arrays
        regime_on = bool(self._regime_on[i])
        off_trigger = bool(self._regime_off_trigger[i])
        flip_off = bool(self._regime_flip_off[i])

        # Read precomputed indicators
        ema_s = self._ema_slow[i]
        atr_val = self._atr_arr[i]
        hh = self._hh_entry[i]
        ll = self._ll_exit[i]
        rv_val = self._rv[i]

        # NaN guard
        if not (
            np.isfinite(ema_s) and np.isfinite(atr_val)
            and np.isfinite(hh) and np.isfinite(ll) and np.isfinite(rv_val)
        ):
            return None

        if self._state == _LatchState.OFF:
            if regime_on:
                breakout_ok = close_val > hh
                if breakout_ok:
                    weight = self._compute_weight(rv_val, i)
                    if weight > 0.0:
                        self._state = _LatchState.LONG
                        return Signal(
                            target_exposure=weight, reason="latch_entry"
                        )
                else:
                    self._state = _LatchState.ARMED

        elif self._state == _LatchState.ARMED:
            if off_trigger:
                self._state = _LatchState.OFF
            elif regime_on and (close_val > hh):
                weight = self._compute_weight(rv_val, i)
                if weight > 0.0:
                    self._state = _LatchState.LONG
                    return Signal(
                        target_exposure=weight, reason="latch_entry"
                    )

        elif self._state == _LatchState.LONG:
            # Exit check BEFORE rebalance
            adaptive_floor = max(ll, ema_s - r["atr_mult"] * atr_val)
            floor_break = close_val < adaptive_floor

            if floor_break or flip_off:
                self._state = _LatchState.OFF
                reason = (
                    "latch_floor_exit" if floor_break
                    else "latch_regime_exit"
                )
                return Signal(target_exposure=0.0, reason=reason)

            # Rebalance check
            weight = self._compute_weight(rv_val, i)
            delta = abs(weight - state.exposure)
            if delta >= r["min_rebalance_weight_delta"] - 1e-12:
                return Signal(
                    target_exposure=weight, reason="latch_rebalance"
                )

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass
