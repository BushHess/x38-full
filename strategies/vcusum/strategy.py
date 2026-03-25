"""VCUSUM — Sequential Change-Point Detection strategy.

3-parameter BTC trend-following strategy using Page's CUSUM on z-scored
log returns.  Detects statistical mean shifts in the return distribution.

Entry: Upward CUSUM > threshold + VDO confirmation.
Exit:  Downward CUSUM > threshold OR ATR trailing stop.

Parameters (tunable):
  ref_window  — W: bars for z-score reference (rolling mean & std)
  threshold   — h: CUSUM alarm threshold
  trail_mult  — ATR multiplier for trailing stop

Constants (structural, not optimized):
  cusum_k     — 0.5 (allowance; optimal for detecting 1-sigma shift)
  atr_period  — 14 (Wilder standard)
  vdo_fast    — 12 (fixed)
  vdo_slow    — 28 (fixed)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy


@dataclass
class VCusumConfig:
    # Tunable (3 parameters)
    ref_window: int = 120           # W: z-score reference window (H4 bars)
    threshold: float = 4.0          # h: CUSUM alarm threshold
    trail_mult: float = 3.0         # ATR trailing stop multiplier

    # Structural constants (not tuned)
    cusum_k: float = 0.5            # Allowance parameter (delta/2 for 1σ shift)
    atr_period: int = 14
    vdo_fast: int = 12
    vdo_slow: int = 28
    vdo_threshold: float = 0.0      # VDO entry gate (0.0 = any positive flow)


class VCusumStrategy(Strategy):
    def __init__(self, config: VCusumConfig | None = None) -> None:
        self._config = config or VCusumConfig()
        self._c = self._config

        # Precomputed indicator arrays (set in on_init)
        self._cusum_up: np.ndarray | None = None
        self._cusum_dn: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return "vcusum"

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

        # Log returns → z-scores → two-sided CUSUM
        log_ret = _log_returns(close)
        z = _rolling_zscore(log_ret, self._c.ref_window)
        self._cusum_up, self._cusum_dn = _cusum(z, self._c.cusum_k)

        self._atr = _atr(high, low, close, self._c.atr_period)
        self._vdo = _vdo(close, high, low, volume, taker_buy,
                         self._c.vdo_fast, self._c.vdo_slow)

    # ── Bar-by-bar decision ───────────────────────────────────────────

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._cusum_up is None or self._cusum_dn is None or
                self._atr is None or self._vdo is None or i < 1):
            return None

        cup = self._cusum_up[i]
        cdn = self._cusum_dn[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(atr_val):
            return None

        if not self._in_position:
            # ENTRY: upward CUSUM detects positive mean shift + VDO confirms
            if cup > self._c.threshold and vdo_val > self._c.vdo_threshold:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="vcusum_entry")
        else:
            # Track peak for trailing stop
            self._peak_price = max(self._peak_price, price)

            # EXIT 1: downward CUSUM detects negative mean shift
            if cdn > self._c.threshold:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vcusum_shift_exit")

            # EXIT 2: ATR trailing stop
            trail_stop = self._peak_price - self._c.trail_mult * atr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vcusum_trail_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


# ── Vectorized indicator helpers ──────────────────────────────────────

def _log_returns(close: np.ndarray) -> np.ndarray:
    """Log returns: r[i] = log(close[i] / close[i-1]). r[0] = 0."""
    n = len(close)
    r = np.zeros(n, dtype=np.float64)
    ratio = np.full(n - 1, np.nan, dtype=np.float64)
    mask = close[:-1] > 0.0
    np.divide(close[1:], close[:-1], out=ratio, where=mask)
    np.log(ratio, out=ratio, where=np.isfinite(ratio) & (ratio > 0.0))
    r[1:] = np.where(np.isfinite(ratio), ratio, 0.0)
    return r


def _rolling_zscore(returns: np.ndarray, window: int) -> np.ndarray:
    """Z-score returns using trailing reference window.

    z[i] = (r[i] - mean(r[i-W:i])) / std(r[i-W:i])
    z[i] = 0 for i < window (no reference available).
    """
    n = len(returns)
    z = np.zeros(n, dtype=np.float64)
    for i in range(window, n):
        ref = returns[i - window:i]
        mu = np.mean(ref)
        sigma = np.std(ref, ddof=1)
        if sigma > 1e-12:
            z[i] = (returns[i] - mu) / sigma
    return z


def _cusum(z: np.ndarray, k: float) -> tuple[np.ndarray, np.ndarray]:
    """Two-sided Page's CUSUM on z-scored returns.

    cusum_up[i] = max(0, cusum_up[i-1] + z[i] - k)  → detects positive shift
    cusum_dn[i] = max(0, cusum_dn[i-1] - z[i] - k)  → detects negative shift

    Returns (cusum_up, cusum_dn).
    """
    n = len(z)
    cup = np.zeros(n, dtype=np.float64)
    cdn = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        cup[i] = max(0.0, cup[i - 1] + z[i] - k)
        cdn[i] = max(0.0, cdn[i - 1] - z[i] - k)
    return cup, cdn


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
