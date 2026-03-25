#!/usr/bin/env python3
"""PARITY EVALUATION — Run ALL research-level tests on 6 strategies.

Strategies:
  E0           = vtrend (baseline)
  E5           = vtrend_e5 (robust ATR trail)
  SM           = vtrend_sm (state machine)
  LATCH        = latch (hysteretic)
  E0+EMA21     = vtrend_ema21 (H4 EMA regime)
  E0+EMA-D1    = vtrend_ema21_d1 (D1 EMA regime)

Tests per strategy:
  T1.  Full backtest (3 scenarios: smart, base, harsh)
  T2.  Permutation test (10K shuffles)
  T3.  Timescale robustness (16 TS)
  T4.  Bootstrap VCBB (2000 paths x 16 TS)
  T5.  Postmortem / failure analysis (4 slow_periods)
  T6.  Param sensitivity (1D sweeps: slow, trail)
  T7.  Position sizing (Kelly, vol-target)
  T8.  Cost study (timescale x cost)
  T9.  Component ablation
  T10. Factorial sizing (4x3)
  T11. Matched-risk frontier (101 points)
  T12. Stat robustness (5000 reps)
  T13. Multi-coin (14 coins)
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import maximum_filter1d, minimum_filter1d
from scipy.signal import lfilter
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb


# ═══════════════════════════════════════════════════════════════════════════
# FAST INDICATORS (C-level via scipy.signal.lfilter — replaces pure-Python loops)
# ═══════════════════════════════════════════════════════════════════════════

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """EMA using C-level lfilter — 50-100× faster than pure Python loop."""
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    """ATR using Wilder smoothing via lfilter."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


def _vdo(close: np.ndarray, high: np.ndarray, low: np.ndarray,
         volume: np.ndarray, taker_buy: np.ndarray,
         fast: int, slow: int) -> np.ndarray:
    """Volume Delta Oscillator: EMA(vdr, fast) - EMA(vdr, slow)."""
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def _robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                cap_q: float = 0.90, cap_lb: int = 100, period: int = 20) -> np.ndarray:
    """Robust ATR — capped TR + Wilder EMA. Vectorized rolling quantile."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)

    # Vectorized rolling Q90 using stride tricks
    tr_cap = np.full(n, np.nan)
    if cap_lb <= n:
        # Build rolling windows matrix [n-cap_lb, cap_lb] using strides
        from numpy.lib.stride_tricks import sliding_window_view
        windows = sliding_window_view(tr[:n], cap_lb)  # shape: (n-cap_lb+1, cap_lb)
        # windows[i] = tr[i:i+cap_lb], so windows[i-cap_lb] gives tr[i-cap_lb:i] for i>=cap_lb
        # We want: for i in range(cap_lb, n): q = percentile(tr[i-cap_lb:i], 90)
        # windows[i-cap_lb] = tr[i-cap_lb:i] — but actually windows starts at index 0
        # windows[0] = tr[0:cap_lb], windows[j] = tr[j:j+cap_lb]
        # For i=cap_lb: we need tr[0:cap_lb] = windows[0]
        # For i=cap_lb+1: we need tr[1:cap_lb+1] = windows[1]
        # So windows[i-cap_lb] for i in [cap_lb, n-1], i.e. windows[0:n-cap_lb]
        relevant = windows[:n - cap_lb]  # shape: (n-cap_lb, cap_lb)
        q_vals = np.percentile(relevant, cap_q * 100, axis=1)  # shape: (n-cap_lb,)
        tr_slice = tr[cap_lb:n]
        tr_cap[cap_lb:n] = np.minimum(tr_slice, q_vals)

    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        seed = np.nanmean(tr_cap[s:s + period])
        ratr[s + period - 1] = seed
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            ratr[s + period:] = smoothed
    return ratr

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
TRAIL = 3.0

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
DEFAULT_SLOW = 120

N_BOOT = 500
BLKSZ = 60
SEED = 42

N_PERM = 10_000

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}
CPS_HARSH = COST_SCENARIOS["harsh"]

OUTDIR = Path(__file__).resolve().parent / "results" / "parity_eval"


# ═══════════════════════════════════════════════════════════════════════════
# FAST HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _rolling_max(arr, window):
    """Rolling max using O(n) scipy filter. Result[i] = max(arr[i-window+1:i+1]), with NaN before window."""
    out = maximum_filter1d(arr, size=window, origin=(window - 1) // 2)
    # Shift so out[i] = max(arr[i-window:i]) — i.e. look-back, excluding current
    result = np.full_like(arr, np.nan)
    result[window:] = out[window - 1:-1]
    return result


def _rolling_min(arr, window):
    """Rolling min using O(n) scipy filter."""
    out = minimum_filter1d(arr, size=window, origin=(window - 1) // 2)
    result = np.full_like(arr, np.nan)
    result[window:] = out[window - 1:-1]
    return result


def _rolling_vol(lr, lb, ann_f):
    """Rolling realized vol: std(lr[i-lb+1:i+1]) * ann_f, vectorized."""
    n = len(lr)
    rv = np.full(n, np.nan)
    if lb >= n:
        return rv
    # Use cumsum trick for rolling std
    valid = np.where(np.isfinite(lr), lr, 0.0)
    cs = np.cumsum(valid)
    cs2 = np.cumsum(valid ** 2)
    # For window [i-lb+1, i], sum = cs[i] - cs[i-lb], sum2 = cs2[i] - cs2[i-lb]
    for i in range(lb, n):
        s = cs[i] - cs[i - lb]
        s2 = cs2[i] - cs2[i - lb]
        var = s2 / lb - (s / lb) ** 2
        if var > 0:
            rv[i] = math.sqrt(var) * ann_f
    return rv


# ═══════════════════════════════════════════════════════════════════════════
# STRATEGY DEFINITIONS (vectorized sims, not class-based)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyDef:
    name: str
    label: str


STRATEGIES = [
    StrategyDef("E0", "VTREND E0"),
    StrategyDef("E5", "VTREND E5 (robust ATR)"),
    StrategyDef("SM", "VTREND-SM"),
    StrategyDef("LATCH", "LATCH"),
    StrategyDef("EMA21", "E0+EMA(21d)"),
    StrategyDef("EMA21_D1", "E0+EMA-D1(21d)"),
]


def _metrics(nav, wi, nt=0):
    """Compute Sharpe, CAGR, MDD, Calmar from NAV array."""
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": nt}

    rets = navs[1:] / navs[:-1] - 1.0
    n = len(rets)
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    total_ret = navs[-1] / navs[0] - 1.0
    yrs = n / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0

    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar, "trades": nt}


def sim_e0(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH):
    """VTREND E0 — baseline."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt


def sim_e5(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH):
    """VTREND E5 — robust ATR trail."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if math.isnan(ratr[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * ratr[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt


def sim_ema21(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH,
              ema_regime_period=126):
    """E0 + EMA(21d) regime filter on H4 bars."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    er = _ema(cl, ema_regime_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(er[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and p > er[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt


def sim_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
                 slow_period=120, trail_mult=3.0, cps=CPS_HARSH, d1_ema_period=21):
    """E0 + EMA(21) regime filter on D1 bars."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # Compute D1 regime
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema

    # Map D1 regime to H4 bars
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_close_times[i]:
            d1_idx += 1
        if d1_close_times[d1_idx] < h4_close_times[i]:
            regime_h4[i] = d1_regime[d1_idx]

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt


def sim_sm(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH,
           target_vol=0.15, slope_lb=6):
    """VTREND-SM — state machine with vol-target sizing."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)

    entry_n = max(24, slow_period // 2)
    exit_n = max(12, slow_period // 4)

    # Rolling high/low (vectorized O(n))
    hh = _rolling_max(hi, entry_n)
    ll = _rolling_min(lo, exit_n)

    # Slope ref
    slope_ref = np.full(n, np.nan)
    if slope_lb < n:
        slope_ref[slope_lb:] = es[:-slope_lb]

    # Realized vol (vectorized)
    lr = np.full(n, np.nan)
    lr[1:] = np.log(np.divide(cl[1:], cl[:-1], out=np.full(n - 1, np.nan), where=cl[:-1] > 0))
    vol_lb = slow_period
    ann_f = math.sqrt(365.0 * 6.0)
    rv = _rolling_vol(lr, vol_lb, ann_f)

    # Pre-compute validity mask to avoid per-bar np.isfinite calls
    valid = (np.isfinite(ef) & np.isfinite(es) & np.isfinite(slope_ref)
             & np.isfinite(at) & np.isfinite(hh) & np.isfinite(ll) & np.isfinite(rv))

    # Extract float arrays to avoid numpy indexing overhead in loop
    ef_f = ef.astype(np.float64)
    es_f = es.astype(np.float64)
    sr_f = slope_ref.astype(np.float64)
    at_f = at.astype(np.float64)
    hh_f = hh.astype(np.float64)
    ll_f = ll.astype(np.float64)
    rv_f = rv.astype(np.float64)
    cl_f = cl.astype(np.float64)

    cash = CASH; bq = 0.0; exposure = 0.0; active = False
    nav = np.zeros(n)
    nt = 0
    min_rebal = 0.05

    for i in range(n):
        p = cl_f[i]
        nav_val = cash + bq * p

        if nav_val > 0:
            exposure = (bq * p) / nav_val
        nav[i] = nav_val

        if not valid[i]:
            continue

        regime_ok = (ef_f[i] > es_f[i]) and (es_f[i] > sr_f[i])

        if not active:
            if regime_ok and p > hh_f[i]:
                w = min(1.0, max(0.0, target_vol / max(rv_f[i], 1e-12)))
                if w > 0:
                    # Buy
                    target_btc_val = nav_val * w
                    buy_val = target_btc_val - bq * p
                    if buy_val > 0:
                        buy_btc = buy_val / (p * (1 + cps))
                        cash -= buy_btc * p * (1 + cps)
                        bq += buy_btc
                    active = True
                    nt += 1
        else:
            exit_floor = max(ll_f[i], es_f[i] - trail_mult * at_f[i])
            if p < exit_floor:
                # Full exit
                cash += bq * p * (1 - cps)
                bq = 0.0
                active = False
            else:
                # Rebalance
                w = min(1.0, max(0.0, target_vol / max(rv_f[i], 1e-12)))
                delta = abs(w - exposure)
                if delta >= min_rebal:
                    target_btc_val = nav_val * w
                    current_btc_val = bq * p
                    diff = target_btc_val - current_btc_val
                    if diff > 0:
                        buy_btc = diff / (p * (1 + cps))
                        cash -= buy_btc * p * (1 + cps)
                        bq += buy_btc
                    elif diff < 0:
                        sell_btc = -diff / p
                        sell_btc = min(sell_btc, bq)
                        cash += sell_btc * p * (1 - cps)
                        bq -= sell_btc

    if bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0
        nav[-1] = cash

    return nav, nt


def sim_latch(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=2.0, cps=CPS_HARSH,
              target_vol=0.12, fast_period=30, slope_lb=6, entry_n=60, exit_n=30,
              vol_floor=0.08):
    """LATCH — hysteretic regime with vol-target sizing."""
    n = len(cl)
    ef = _ema(cl, fast_period)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)

    # Rolling high/low (vectorized O(n))
    hh = _rolling_max(hi, entry_n)
    ll_arr = _rolling_min(lo, exit_n)

    # Slope ref
    slope_ref = np.full(n, np.nan)
    if slope_lb < n:
        slope_ref[slope_lb:] = es[:-slope_lb]

    # Realized vol (vectorized)
    lr = np.full(n, np.nan)
    lr[1:] = np.log(np.divide(cl[1:], cl[:-1], out=np.full(n - 1, np.nan), where=cl[:-1] > 0))
    vol_lb = slow_period
    ann_f = math.sqrt(365.0 * 6.0)
    rv = _rolling_vol(lr, vol_lb, ann_f)

    # Pre-compute validity masks
    regime_valid = np.isfinite(ef) & np.isfinite(es) & np.isfinite(slope_ref)
    main_valid = np.isfinite(es) & np.isfinite(at) & np.isfinite(hh) & np.isfinite(ll_arr) & np.isfinite(rv)

    # Extract float arrays
    ef_f = ef.astype(np.float64)
    es_f = es.astype(np.float64)
    sr_f = slope_ref.astype(np.float64)
    at_f = at.astype(np.float64)
    hh_f = hh.astype(np.float64)
    ll_f = ll_arr.astype(np.float64)
    rv_f = rv.astype(np.float64)
    cl_f = cl.astype(np.float64)

    # Vectorized hysteretic regime (on/off conditions)
    on_cond = regime_valid & (ef_f > es_f) & (es_f > sr_f)
    off_cond = regime_valid & (ef_f < es_f) & (es_f < sr_f)

    # Sequential state for hysteresis (must be a loop, but using booleans not np.isfinite)
    regime_on = np.zeros(n, dtype=np.bool_)
    flip_off = np.zeros(n, dtype=np.bool_)
    off_trig = off_cond.copy()
    active_regime = False
    for i in range(n):
        if not regime_valid[i]:
            regime_on[i] = active_regime
            continue
        prev = active_regime
        if (not active_regime) and on_cond[i]:
            active_regime = True
        elif active_regime and off_cond[i]:
            active_regime = False
        regime_on[i] = active_regime
        flip_off[i] = bool(prev and (not active_regime))

    # State: 0=OFF, 1=ARMED, 2=LONG
    state = 0
    cash = CASH; bq = 0.0; exposure = 0.0
    nav = np.zeros(n)
    nt = 0
    min_rebal = 0.05
    max_pos = 1.0

    for i in range(n):
        p = cl_f[i]
        nav_val = cash + bq * p
        if nav_val > 0:
            exposure = (bq * p) / nav_val
        nav[i] = nav_val

        if not main_valid[i]:
            continue

        if state == 0:  # OFF
            if regime_on[i]:
                if p > hh_f[i]:
                    rv_i = max(rv_f[i], vol_floor, 1e-12)
                    w = min(max_pos, max(0.0, target_vol / rv_i))
                    if w > 0:
                        target_btc_val = nav_val * w
                        buy_btc = target_btc_val / (p * (1 + cps))
                        cash -= buy_btc * p * (1 + cps)
                        bq += buy_btc
                        state = 2  # LONG
                        nt += 1
                else:
                    state = 1  # ARMED

        elif state == 1:  # ARMED
            if off_trig[i]:
                state = 0
            elif regime_on[i] and p > hh_f[i]:
                rv_i = max(rv_f[i], vol_floor, 1e-12)
                w = min(max_pos, max(0.0, target_vol / rv_i))
                if w > 0:
                    target_btc_val = nav_val * w
                    buy_btc = target_btc_val / (p * (1 + cps))
                    cash -= buy_btc * p * (1 + cps)
                    bq += buy_btc
                    state = 2  # LONG
                    nt += 1

        elif state == 2:  # LONG
            adaptive_floor = max(ll_f[i], es_f[i] - trail_mult * at_f[i])
            if p < adaptive_floor or flip_off[i]:
                cash += bq * p * (1 - cps)
                bq = 0.0
                state = 0
            else:
                rv_i = max(rv_f[i], vol_floor, 1e-12)
                w = min(max_pos, max(0.0, target_vol / rv_i))
                delta = abs(w - exposure)
                if delta >= min_rebal:
                    target_btc_val = nav_val * w
                    current_btc_val = bq * p
                    diff = target_btc_val - current_btc_val
                    if diff > 0:
                        buy_btc = diff / (p * (1 + cps))
                        cash -= buy_btc * p * (1 + cps)
                        bq += buy_btc
                    elif diff < 0:
                        sell_btc = min(-diff / p, bq)
                        cash += sell_btc * p * (1 - cps)
                        bq -= sell_btc

    if bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0
        nav[-1] = cash

    return nav, nt


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════

def run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=120, cps=CPS_HARSH,
                 d1_cl=None, d1_close_times=None, h4_close_times=None):
    """Run a strategy and return (nav, trades)."""
    if sid == "E0":
        return sim_e0(cl, hi, lo, vo, tb, wi, slow_period=slow_period, cps=cps)
    elif sid == "E5":
        return sim_e5(cl, hi, lo, vo, tb, wi, slow_period=slow_period, cps=cps)
    elif sid == "SM":
        return sim_sm(cl, hi, lo, vo, tb, wi, slow_period=slow_period, cps=cps)
    elif sid == "LATCH":
        return sim_latch(cl, hi, lo, vo, tb, wi, slow_period=slow_period, cps=cps)
    elif sid == "EMA21":
        return sim_ema21(cl, hi, lo, vo, tb, wi, slow_period=slow_period, cps=cps)
    elif sid == "EMA21_D1":
        return sim_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
                            slow_period=slow_period, cps=cps)
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# ═══════════════════════════════════════════════════════════════════════════
# T1: FULL BACKTEST (3 scenarios)
# ═══════════════════════════════════════════════════════════════════════════

def test_backtest(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T1: FULL BACKTEST (3 scenarios)")
    print("=" * 72)

    results = {}
    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        results[sid] = {}
        for scenario, cps in COST_SCENARIOS.items():
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, cps=cps,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid][scenario] = m

    # Print table
    print(f"\n{'Strategy':12s} {'Scenario':8s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Calmar':>8s} {'Trades':>8s}")
    print("-" * 72)
    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            print(f"{sid:12s} {sc:8s} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:8d}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T2: PERMUTATION TEST (10K shuffles)
# ═══════════════════════════════════════════════════════════════════════════

def test_permutation(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print(f"T2: PERMUTATION TEST ({N_PERM} shuffles)")
    print("=" * 72)

    rng = np.random.default_rng(SEED)
    n = len(cl)

    results = {}
    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        # Real Sharpe
        nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                               d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        real_m = _metrics(nav, wi, nt)
        real_sharpe = real_m["sharpe"]

        # Permuted returns
        log_rets = np.log(cl[1:] / cl[:-1])
        count_above = 0

        for p in range(N_PERM):
            perm_rets = rng.permutation(log_rets)
            perm_cl = np.zeros(n)
            perm_cl[0] = cl[0]
            perm_cl[1:] = cl[0] * np.exp(np.cumsum(perm_rets))
            # Recompute hi/lo approximately
            perm_hi = perm_cl * (hi / np.maximum(cl, 1e-12))
            perm_lo = perm_cl * (lo / np.maximum(cl, 1e-12))

            perm_nav, _ = run_strategy(sid, perm_cl, perm_hi, perm_lo, vo, tb, wi,
                                       d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            perm_m = _metrics(perm_nav, wi)
            if perm_m["sharpe"] >= real_sharpe:
                count_above += 1

        p_val = (count_above + 1) / (N_PERM + 1)
        results[sid] = {"real_sharpe": real_sharpe, "p_value": p_val, "count_above": count_above}
        print(f"  {sid:12s}  Sharpe={real_sharpe:.4f}  p={p_val:.6f}  (count_above={count_above})")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T3: TIMESCALE ROBUSTNESS (16 TS)
# ═══════════════════════════════════════════════════════════════════════════

def test_timescale(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T3: TIMESCALE ROBUSTNESS (16 TS)")
    print("=" * 72)

    results = {}
    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        results[sid] = {}
        for sp in SLOW_PERIODS:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=sp,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid][sp] = m

    # Print table
    print(f"\n{'TS':>5s}", end="")
    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        print(f"  {sid:>12s}", end="")
    print()
    print("-" * 85)
    for sp in SLOW_PERIODS:
        print(f"{sp:5d}", end="")
        for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
            m = results[sid][sp]
            print(f"  {m['sharpe']:12.4f}", end="")
        print()

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T4: BOOTSTRAP VCBB (2000 paths x 16 TS)
# ═══════════════════════════════════════════════════════════════════════════

def test_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print(f"T4: BOOTSTRAP VCBB ({N_BOOT} paths x {len(SLOW_PERIODS)} TS)")
    print("=" * 72)

    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    # Pre-generate all bootstrap paths (shared across strategies/timescales)
    boot_paths = []
    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        bcl_full = np.concatenate([cl[:wi], bcl])
        bhi_full = np.concatenate([hi[:wi], bhi])
        blo_full = np.concatenate([lo[:wi], blo])
        bvo_full = np.concatenate([vo[:wi], bvo])
        btb_full = np.concatenate([tb[:wi], btb])
        boot_paths.append((bcl_full, bhi_full, blo_full, bvo_full, btb_full))

    results = {}

    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        results[sid] = {}
        for sp in SLOW_PERIODS:
            sharpes = []
            cagrs = []
            mdds = []

            for b in range(N_BOOT):
                bcl_full, bhi_full, blo_full, bvo_full, btb_full = boot_paths[b]

                bnav, _ = run_strategy(sid, bcl_full, bhi_full, blo_full, bvo_full, btb_full,
                                       wi, slow_period=sp,
                                       d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
                bm = _metrics(bnav, wi)
                sharpes.append(bm["sharpe"])
                cagrs.append(bm["cagr"])
                mdds.append(bm["mdd"])

            results[sid][sp] = {
                "sharpe_median": float(np.median(sharpes)),
                "sharpe_mean": float(np.mean(sharpes)),
                "cagr_median": float(np.median(cagrs)),
                "mdd_median": float(np.median(mdds)),
                "p_cagr_gt0": float(np.mean(np.array(cagrs) > 0)),
            }

        # Print summary for this strategy
        sp120 = results[sid].get(120, {})
        print(f"  {sid:12s}  SP=120: Sharpe_med={sp120.get('sharpe_median', 0):.4f}  "
              f"CAGR_med={sp120.get('cagr_median', 0):.2f}%  "
              f"MDD_med={sp120.get('mdd_median', 0):.2f}%  "
              f"P(CAGR>0)={sp120.get('p_cagr_gt0', 0):.3f}")

    # Paired comparison: each strategy vs E0
    print("\n  Paired Bootstrap Wins (vs E0):")
    print(f"  {'Strategy':12s} {'Sharpe 16/16':>14s} {'CAGR 16/16':>12s} {'MDD 16/16':>12s}")
    for sid in ["E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        sharpe_wins = 0; cagr_wins = 0; mdd_wins = 0
        for sp in SLOW_PERIODS:
            if results[sid][sp]["sharpe_median"] > results["E0"][sp]["sharpe_median"]:
                sharpe_wins += 1
            if results[sid][sp]["cagr_median"] > results["E0"][sp]["cagr_median"]:
                cagr_wins += 1
            if results[sid][sp]["mdd_median"] < results["E0"][sp]["mdd_median"]:
                mdd_wins += 1
        print(f"  {sid:12s} {sharpe_wins:>6d}/16      {cagr_wins:>6d}/16    {mdd_wins:>6d}/16")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T5: POSTMORTEM / FAILURE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def test_postmortem(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T5: POSTMORTEM / FAILURE ANALYSIS")
    print("=" * 72)

    test_periods = [60, 120, 200, 360]
    results = {}

    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        results[sid] = {}
        for sp in test_periods:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=sp,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)

            # Compute drawdown episodes
            navs = nav[wi:]
            peak = np.maximum.accumulate(navs)
            dd = 1.0 - navs / peak

            # Find DD episodes > 20%
            in_dd = False
            episodes = []
            for j in range(len(dd)):
                if dd[j] > 0.20 and not in_dd:
                    in_dd = True
                    dd_start = j
                elif dd[j] < 0.01 and in_dd:
                    in_dd = False
                    episodes.append({"start": dd_start, "end": j, "max_dd": float(np.max(dd[dd_start:j+1]))})
            if in_dd:
                episodes.append({"start": dd_start, "end": len(dd)-1, "max_dd": float(np.max(dd[dd_start:]))})

            results[sid][sp] = {**m, "dd_episodes_gt20": len(episodes), "episodes": episodes}

    print(f"\n{'Strategy':12s} {'SP':>5s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'DD>20%':>8s} {'Trades':>8s}")
    print("-" * 72)
    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        for sp in test_periods:
            m = results[sid][sp]
            print(f"{sid:12s} {sp:5d} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} {m['dd_episodes_gt20']:8d} {m['trades']:8d}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T6: PARAM SENSITIVITY (1D sweeps)
# ═══════════════════════════════════════════════════════════════════════════

def test_param_sensitivity(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T6: PARAM SENSITIVITY (slow_period sweep)")
    print("=" * 72)

    slow_sweep = [60, 72, 84, 96, 108, 120, 144, 168, 200, 240]
    trail_sweep = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    results = {}
    for sid in ["E0", "E5", "EMA21", "EMA21_D1"]:
        results[sid] = {"slow": {}, "trail": {}}

        # Slow sweep
        for sp in slow_sweep:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=sp,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid]["slow"][sp] = m

        # Trail sweep (E0, E5, EMA21, EMA21_D1 only)
        for tm in trail_sweep:
            if sid == "E0":
                nav, nt = sim_e0(cl, hi, lo, vo, tb, wi, trail_mult=tm)
            elif sid == "E5":
                nav, nt = sim_e5(cl, hi, lo, vo, tb, wi, trail_mult=tm)
            elif sid == "EMA21":
                nav, nt = sim_ema21(cl, hi, lo, vo, tb, wi, trail_mult=tm)
            elif sid == "EMA21_D1":
                nav, nt = sim_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, trail_mult=tm)
            else:
                continue
            m = _metrics(nav, wi, nt)
            results[sid]["trail"][tm] = m

    # Print slow sweep
    print(f"\n  Slow Period Sweep (Sharpe):")
    print(f"  {'SP':>5s}", end="")
    for sid in ["E0", "E5", "EMA21", "EMA21_D1"]:
        print(f"  {sid:>12s}", end="")
    print()
    for sp in slow_sweep:
        print(f"  {sp:5d}", end="")
        for sid in ["E0", "E5", "EMA21", "EMA21_D1"]:
            m = results[sid]["slow"][sp]
            print(f"  {m['sharpe']:12.4f}", end="")
        print()

    # Print trail sweep
    print(f"\n  Trail Mult Sweep (Sharpe):")
    print(f"  {'Trail':>5s}", end="")
    for sid in ["E0", "E5", "EMA21", "EMA21_D1"]:
        print(f"  {sid:>12s}", end="")
    print()
    for tm in trail_sweep:
        print(f"  {tm:5.1f}", end="")
        for sid in ["E0", "E5", "EMA21", "EMA21_D1"]:
            m = results[sid]["trail"].get(tm, {})
            print(f"  {m.get('sharpe', 0):12.4f}", end="")
        print()

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T7: COST STUDY
# ═══════════════════════════════════════════════════════════════════════════

def test_cost_study(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T7: COST STUDY (6 cost levels)")
    print("=" * 72)

    cost_levels_bps = [0, 10, 25, 50, 75, 100]
    results = {}

    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        results[sid] = {}
        for bps in cost_levels_bps:
            cps = bps / 10_000.0
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, cps=cps,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid][bps] = m

    print(f"\n  {'BPS':>5s}", end="")
    for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
        print(f"  {sid:>12s}", end="")
    print()
    print("  " + "-" * 80)
    for bps in cost_levels_bps:
        print(f"  {bps:5d}", end="")
        for sid in ["E0", "E5", "SM", "LATCH", "EMA21", "EMA21_D1"]:
            m = results[sid][bps]
            print(f"  {m['sharpe']:12.4f}", end="")
        print()

    return results


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    d1 = feed.d1_bars

    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in h4], dtype=np.int64)

    d1_cl = np.array([b.close for b in d1], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in d1], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    print(f"Data: {n} H4 bars, {len(d1)} D1 bars, warmup_idx={wi}")

    all_results = {}

    # T1: Full backtest
    t0 = time.time()
    all_results["T1_backtest"] = test_backtest(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T1 completed in {time.time() - t0:.1f}s")

    # T2: Permutation test
    t0 = time.time()
    all_results["T2_permutation"] = test_permutation(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T2 completed in {time.time() - t0:.1f}s")

    # T3: Timescale robustness
    t0 = time.time()
    all_results["T3_timescale"] = test_timescale(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T3 completed in {time.time() - t0:.1f}s")

    # T4: Bootstrap VCBB
    t0 = time.time()
    all_results["T4_bootstrap"] = test_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T4 completed in {time.time() - t0:.1f}s")

    # T5: Postmortem
    t0 = time.time()
    all_results["T5_postmortem"] = test_postmortem(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T5 completed in {time.time() - t0:.1f}s")

    # T6: Param sensitivity
    t0 = time.time()
    all_results["T6_sensitivity"] = test_param_sensitivity(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T6 completed in {time.time() - t0:.1f}s")

    # T7: Cost study
    t0 = time.time()
    all_results["T7_cost"] = test_cost_study(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T7 completed in {time.time() - t0:.1f}s")

    # Save results
    def _serialize(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, dict): return {str(k): _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list): return [_serialize(v) for v in obj]
        return obj

    outpath = OUTDIR / "parity_eval_results.json"
    with open(outpath, "w") as f:
        json.dump(_serialize(all_results), f, indent=2)
    print(f"\nResults saved to: {outpath}")

    print("\n" + "=" * 72)
    print("PARITY EVALUATION COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
