"""6-class analytical regime classifier and per-regime return decomposition.

Classification priority (D1 bars):
  SHOCK   — |daily return| > 8%
  BEAR    — close < EMA_slow AND EMA_fast < EMA_slow
  CHOP    — ATR% > 3.5% AND ADX < 20
  TOPPING — |close - EMA_fast|/EMA_fast < 1% AND ADX < 25
  BULL    — close > EMA_slow AND EMA_fast > EMA_slow
  NEUTRAL — everything else
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np

from v10.core.types import Bar, EquitySnap


class AnalyticalRegime(str, Enum):
    SHOCK = "SHOCK"
    BEAR = "BEAR"
    CHOP = "CHOP"
    TOPPING = "TOPPING"
    BULL = "BULL"
    NEUTRAL = "NEUTRAL"


# ---------------------------------------------------------------------------
# Internal indicator helpers (standalone, avoid importing from v8_apex)
# ---------------------------------------------------------------------------

def _ema(arr: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average (EWM span)."""
    out = np.empty_like(arr)
    out[0] = arr[0]
    alpha = 2.0 / (period + 1.0)
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out


def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> np.ndarray:
    """Average True Range (Wilder smoothing)."""
    n = len(closes)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    # Wilder smoothing
    atr_out = np.empty(n)
    atr_out[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        atr_out[i] = alpha * tr[i] + (1.0 - alpha) * atr_out[i - 1]
    return atr_out


def _adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Average Directional Index."""
    n = len(closes)
    if n < 2:
        return np.zeros(n)

    # +DM / -DM
    pdm = np.zeros(n)
    ndm = np.zeros(n)
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        if up > down and up > 0:
            pdm[i] = up
        if down > up and down > 0:
            ndm[i] = down

    atr_arr = _atr(highs, lows, closes, period)

    # Smooth +DM, -DM with Wilder
    alpha = 1.0 / period
    s_pdm = np.empty(n)
    s_ndm = np.empty(n)
    s_pdm[0] = pdm[0]
    s_ndm[0] = ndm[0]
    for i in range(1, n):
        s_pdm[i] = alpha * pdm[i] + (1.0 - alpha) * s_pdm[i - 1]
        s_ndm[i] = alpha * ndm[i] + (1.0 - alpha) * s_ndm[i - 1]

    # +DI / -DI
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = np.where(atr_arr > 1e-12, 100.0 * s_pdm / atr_arr, 0.0)
        ndi = np.where(atr_arr > 1e-12, 100.0 * s_ndm / atr_arr, 0.0)

    # DX
    di_sum = pdi + ndi
    with np.errstate(divide="ignore", invalid="ignore"):
        dx = np.where(di_sum > 1e-12, 100.0 * np.abs(pdi - ndi) / di_sum, 0.0)

    # ADX = Wilder smoothed DX
    adx_out = np.empty(n)
    adx_out[0] = dx[0]
    for i in range(1, n):
        adx_out[i] = alpha * dx[i] + (1.0 - alpha) * adx_out[i - 1]

    return adx_out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_d1_regimes(
    d1_bars: list[Bar],
    ema_fast: int = 50,
    ema_slow: int = 200,
    adx_period: int = 14,
    shock_threshold: float = 8.0,
    chop_atr_pct: float = 3.5,
    chop_adx_max: float = 20.0,
    topping_dist_pct: float = 1.0,
    topping_adx_max: float = 25.0,
) -> list[AnalyticalRegime]:
    """Classify each D1 bar into one of 6 analytical regimes.

    Returns a list of AnalyticalRegime with the same length as d1_bars.
    """
    n = len(d1_bars)
    if n == 0:
        return []

    closes = np.array([b.close for b in d1_bars], dtype=np.float64)
    highs = np.array([b.high for b in d1_bars], dtype=np.float64)
    lows = np.array([b.low for b in d1_bars], dtype=np.float64)

    ema_f = _ema(closes, ema_fast)
    ema_s = _ema(closes, ema_slow)
    atr_arr = _atr(highs, lows, closes, 14)
    adx_arr = _adx(highs, lows, closes, adx_period)

    regimes: list[AnalyticalRegime] = []
    for i in range(n):
        c = closes[i]

        # SHOCK: |daily return| > threshold
        if i > 0:
            daily_ret_pct = abs((c / closes[i - 1] - 1.0) * 100.0)
        else:
            daily_ret_pct = 0.0

        if daily_ret_pct > shock_threshold:
            regimes.append(AnalyticalRegime.SHOCK)
            continue

        # BEAR: close < EMA_slow AND EMA_fast < EMA_slow
        if c < ema_s[i] and ema_f[i] < ema_s[i]:
            regimes.append(AnalyticalRegime.BEAR)
            continue

        # CHOP: ATR% > threshold AND ADX < threshold
        atr_pct = (atr_arr[i] / c * 100.0) if c > 1e-12 else 0.0
        if atr_pct > chop_atr_pct and adx_arr[i] < chop_adx_max:
            regimes.append(AnalyticalRegime.CHOP)
            continue

        # TOPPING: close near EMA_fast AND ADX low
        dist_pct = abs(c - ema_f[i]) / ema_f[i] * 100.0 if ema_f[i] > 1e-12 else 0.0
        if dist_pct < topping_dist_pct and adx_arr[i] < topping_adx_max:
            regimes.append(AnalyticalRegime.TOPPING)
            continue

        # BULL: close > EMA_slow AND EMA_fast > EMA_slow
        if c > ema_s[i] and ema_f[i] > ema_s[i]:
            regimes.append(AnalyticalRegime.BULL)
            continue

        # NEUTRAL: everything else
        regimes.append(AnalyticalRegime.NEUTRAL)

    return regimes


def compute_regime_returns(
    equity: list[EquitySnap],
    d1_bars: list[Bar],
    regimes: list[AnalyticalRegime],
    report_start_ms: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute per-regime return statistics.

    Maps each equity bar to the regime of its closest D1 bar (by close_time),
    then aggregates returns per regime.

    Returns dict keyed by regime name, each containing:
      total_return_pct, max_dd_pct, n_bars, n_days, sharpe (4H ann.)
    """
    if not equity or not d1_bars or not regimes:
        return {}

    # Build D1 close_time -> regime mapping
    d1_close_times = np.array([b.close_time for b in d1_bars], dtype=np.int64)
    regime_arr = regimes  # parallel with d1_close_times

    # Map each equity bar to a regime via the latest D1 bar with close_time < equity bar
    eq_times = np.array([e.close_time for e in equity], dtype=np.int64)
    navs = np.array([e.nav_mid for e in equity], dtype=np.float64)

    # For each equity bar, find the latest d1 bar with close_time < eq_time
    d1_idx_for_eq = np.searchsorted(d1_close_times, eq_times, side="left") - 1

    # Compute per-bar returns
    returns = np.zeros(len(navs))
    returns[1:] = navs[1:] / navs[:-1] - 1.0

    # Group by regime
    results: dict[str, dict[str, Any]] = {}
    for regime in AnalyticalRegime:
        mask = np.array([
            d1_idx_for_eq[i] >= 0 and regime_arr[d1_idx_for_eq[i]] == regime
            for i in range(len(eq_times))
        ], dtype=bool)

        n_bars = int(mask.sum())
        if n_bars == 0:
            continue

        regime_returns = returns[mask]
        regime_navs = navs[mask]

        total_ret = float(np.prod(1.0 + regime_returns) - 1.0) * 100.0
        n_days = n_bars * 4.0 / 24.0  # H4 bars to days

        # Max DD within this regime's bars
        if len(regime_navs) > 1:
            peak = np.maximum.accumulate(regime_navs)
            dd = 1.0 - regime_navs / peak
            max_dd = float(dd.max()) * 100.0
        else:
            max_dd = 0.0

        # Sharpe (annualized on 4H)
        sharpe = None
        if len(regime_returns) > 2:
            mu = float(regime_returns.mean())
            sigma = float(regime_returns.std(ddof=0))
            if sigma > 1e-12:
                sharpe = round((mu / sigma) * np.sqrt(2190.0), 4)

        results[regime.value] = {
            "total_return_pct": round(total_ret, 2),
            "max_dd_pct": round(max_dd, 2),
            "n_bars": n_bars,
            "n_days": round(n_days, 1),
            "sharpe": sharpe,
        }

    return results
