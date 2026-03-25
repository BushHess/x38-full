#!/usr/bin/env python3
"""PE Study — Participation-Efficiency Score Integration with VTREND.

PE = max(0, CLV) × BODY × max(0, zDV)
  CLV  = (2C - H - L) / (H - L + ε)       close location value
  BODY = |C - O| / (H - L + ε)              candle decisiveness
  zDV  = (ln(DV) - median(ln(DV_hist))) / (1.4826 * MAD(ln(DV_hist)))
                                              z-scored dollar volume

PE is high only when ALL three: close near high, strong body, high volume.
Compared against rolling quantile (adaptive threshold).

Combinations tested (all at N=120):
  VTREND          — baseline: EMA cross + VDO + ATR trail + EMA exit
  V+PE-ADD        — VTREND + PE > rolling P75 (additional filter)
  V-PE/VDO        — EMA cross + PE > rolling P75 (PE replaces VDO)
  V+PE-SOFT       — VTREND + PE > 0 (any positive PE = confirmation)
  V+PE-ENTRY      — PE > rolling P75 + ATR trail + EMA exit (PE as entry)

Also tests PE quantile thresholds: P50, P75, P90.

Method: 2000 bootstrap paths, paired comparison, same seed.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ─────────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
BLKSZ  = 60
SEED   = 42

ANN = math.sqrt(6.0 * 365.25)

ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0
VDO_THR = 0.0

SLOW = 120
FAST = max(5, SLOW // 4)

PE_WINDOW = 120       # lookback for rolling median/MAD of dollar volume
PE_Q_WINDOW = 120     # lookback for rolling PE quantile
PE_QUANTILES = [0.50, 0.75, 0.90]  # thresholds to test

N_GRID = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]


# ═══════════════════════════════════════════════════════════════════════
# Data loading & bootstrap
# ═══════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    op = np.array([b.open  for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, op, vo, tb, wi, n


def make_ratios(cl, hi, lo, op, vo, tb):
    pc = cl[:-1]
    return (cl[1:] / pc, hi[1:] / pc, lo[1:] / pc,
            op[1:] / pc,   # open ratio: open[t] / close[t-1]
            vo[1:].copy(), tb[1:].copy())


def gen_path(cr, hr, lr, opr, vol, tb, n_trans, blksz, p0, rng):
    n_blk = math.ceil(n_trans / blksz)
    mx = len(cr) - blksz
    if mx <= 0:
        idx = np.arange(min(n_trans, len(cr)))
    else:
        starts = rng.integers(0, mx + 1, size=n_blk)
        idx = np.concatenate([np.arange(s, s + blksz) for s in starts])[:n_trans]

    c = np.empty(len(idx) + 1, dtype=np.float64)
    c[0] = p0
    c[1:] = p0 * np.cumprod(cr[idx])

    h = np.empty_like(c); l = np.empty_like(c)
    o = np.empty_like(c)
    v = np.empty_like(c); t = np.empty_like(c)

    h[0] = p0 * 1.002;  l[0] = p0 * 0.998;  o[0] = p0 * 0.999
    v[0] = vol[idx[0]];  t[0] = tb[idx[0]]

    h[1:] = c[:-1] * hr[idx]
    l[1:] = c[:-1] * lr[idx]
    o[1:] = c[:-1] * opr[idx]
    v[1:] = vol[idx]
    t[1:] = tb[idx]

    np.maximum(h, c, out=h)
    np.minimum(l, c, out=l)
    # Ensure open is within [low, high]
    np.maximum(o, l, out=o)
    np.minimum(o, h, out=o)

    return c, h, l, o, v, t


# ═══════════════════════════════════════════════════════════════════════
# PE Indicator (vectorized)
# ═══════════════════════════════════════════════════════════════════════

def _pe_components(close, high, low, open_, volume, window=PE_WINDOW):
    """Compute PE and its three components.

    Returns: pe, clv_pos, body, zdv_pos  (all arrays of length n)
    """
    n = len(close)
    eps = 1e-10

    spread = high - low + eps

    # CLV: close location value [-1, 1], clipped to [0, 1]
    clv = (2.0 * close - high - low) / spread
    clv_pos = np.maximum(0.0, clv)

    # BODY: candle decisiveness [0, 1]
    body = np.abs(close - open_) / spread

    # zDV: z-scored log dollar volume using rolling median and MAD
    dv = close * volume
    ln_dv = np.log(np.maximum(dv, 1.0))

    zdv = np.zeros(n, dtype=np.float64)
    if window < n:
        windows = sliding_window_view(ln_dv, window)
        # windows[i] = ln_dv[i:i+window], shape (n-window+1, window)
        # For bar i+window, the history is windows[i] = ln_dv[i:i+window]
        # So zdv[window:] uses history from [0:window], [1:window+1], ...
        medians = np.median(windows, axis=1)
        mads = np.median(np.abs(windows - medians[:, np.newaxis]), axis=1)
        scales = np.maximum(1.4826 * mads, 1e-6)
        zdv[window:] = (ln_dv[window:] - medians[:n - window]) / scales[:n - window]

    zdv_pos = np.maximum(0.0, zdv)

    # PE = product of three non-negative components
    pe = clv_pos * body * zdv_pos

    return pe, clv_pos, body, zdv_pos


def _rolling_quantile(arr, window, q):
    """Rolling quantile of arr over window. NaN for i < window."""
    n = len(arr)
    out = np.full(n, np.nan)
    if window >= n:
        return out
    windows = sliding_window_view(arr, window)
    out[window:] = np.quantile(windows[:n - window], q, axis=1)
    return out


# ═══════════════════════════════════════════════════════════════════════
# Simulation variants
# ═══════════════════════════════════════════════════════════════════════

def sim_vtrend(cl, ef, es, at, vd, wi, trail=TRAIL):
    """VTREND baseline."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe_ = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe_:
                pe_ = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; prev_nav = nav; nav_peak = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0; rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio: nav_min_ratio = ratio
            navs_end = nav
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_pe_add(cl, ef, es, at, vd, pe_arr, pe_thr, wi, trail=TRAIL):
    """V+PE-ADD: VTREND + PE > threshold (additional filter)."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe_ = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe_:
                pe_ = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; prev_nav = nav; nav_peak = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0; rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio: nav_min_ratio = ratio
            navs_end = nav
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        thr = pe_thr[i]
        if math.isnan(thr): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and pe_arr[i] > thr:
                pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_pe_replace_vdo(cl, ef, es, at, pe_arr, pe_thr, wi, trail=TRAIL):
    """V-PE/VDO: EMA cross + PE > threshold (PE replaces VDO)."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe_ = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe_:
                pe_ = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; prev_nav = nav; nav_peak = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0; rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio: nav_min_ratio = ratio
            navs_end = nav
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        thr = pe_thr[i]
        if math.isnan(thr): continue
        if not inp:
            if ef[i] > es[i] and pe_arr[i] > thr:
                pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_pe_soft(cl, ef, es, at, vd, pe_arr, wi, trail=TRAIL):
    """V+PE-SOFT: VTREND + PE > 0 (any positive PE)."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe_ = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe_:
                pe_ = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; prev_nav = nav; nav_peak = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0; rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio: nav_min_ratio = ratio
            navs_end = nav
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and pe_arr[i] > 0:
                pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_pe_entry(cl, at, pe_arr, pe_thr, ef, es, wi, trail=TRAIL):
    """V-PE-ENTRY: PE > rolling threshold as entry (no EMA cross, no VDO).
    Still uses ATR trail + EMA cross-down for exit.
    """
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe_ = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe_:
                pe_ = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; prev_nav = nav; nav_peak = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0; rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio: nav_min_ratio = ratio
            navs_end = nav
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        thr = pe_thr[i]
        if math.isnan(thr): continue
        if not inp:
            if pe_arr[i] > thr:
                pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt):
    if n_rets < 2 or navs_start <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0, "trades": 0}
    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar, "trades": nt}


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: PE Distribution & Real Data
# ═══════════════════════════════════════════════════════════════════════

def analyze_pe_distribution(cl, hi, lo, op, vo, wi):
    """Understand PE distribution on real data."""
    print("\n" + "=" * 70)
    print("PE INDICATOR DISTRIBUTION (REAL DATA)")
    print("=" * 70)

    pe, clv, body, zdv = _pe_components(cl, hi, lo, op, vo)

    # Only look at trading period
    pe_t = pe[wi:]
    clv_t = clv[wi:]
    body_t = body[wi:]
    zdv_t = zdv[wi:]

    print(f"\n  Trading bars: {len(pe_t)}")

    for name, arr in [("CLV+", clv_t), ("BODY", body_t), ("zDV+", zdv_t), ("PE", pe_t)]:
        p0 = np.mean(arr == 0) * 100
        nz = arr[arr > 0]
        if len(nz) > 0:
            p25, p50, p75, p90, p95 = np.percentile(nz, [25, 50, 75, 90, 95])
            print(f"  {name:5s}  zero={p0:5.1f}%  "
                  f"| non-zero: p25={p25:.4f} p50={p50:.4f} "
                  f"p75={p75:.4f} p90={p90:.4f} p95={p95:.4f}")
        else:
            print(f"  {name:5s}  zero={p0:5.1f}%  | all zero")

    # What fraction of bars have PE > 0?
    print(f"\n  P(PE > 0) = {np.mean(pe_t > 0) * 100:.1f}%")

    # Rolling quantile thresholds
    for q in PE_QUANTILES:
        thr = _rolling_quantile(pe, PE_Q_WINDOW, q)
        thr_t = thr[wi:]
        frac_above = np.mean(pe_t > thr_t) * 100
        print(f"  P(PE > rolling P{q*100:.0f}) = {frac_above:.1f}%")

    return pe


def run_real_data(cl, hi, lo, op, vo, tb, wi):
    """Test all combinations on real data."""
    print("\n" + "=" * 70)
    print("PHASE 1: REAL DATA COMPARISON (N=120)")
    print("=" * 70)

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    pe, _, _, _ = _pe_components(cl, hi, lo, op, vo)

    # VTREND baseline
    r_vt = sim_vtrend(cl, ef, es, at, vd, wi)

    print(f"\n  {'Variant':<25s} {'CAGR':>7s} {'MDD':>6s} {'Sharpe':>7s} "
          f"{'Calmar':>7s} {'Tr':>4s}")
    print("  " + "-" * 65)

    def pr(label, r):
        print(f"  {label:<25s} {r['cagr']:+6.1f}% {r['mdd']:5.1f}% "
              f"{r['sharpe']:+6.3f} {r['calmar']:+6.3f} {r['trades']:4d}")

    pr("VTREND (baseline)", r_vt)

    results = {"vtrend": r_vt}

    for q in PE_QUANTILES:
        q_label = f"P{q*100:.0f}"
        pe_thr = _rolling_quantile(pe, PE_Q_WINDOW, q)

        # V+PE-ADD
        r = sim_pe_add(cl, ef, es, at, vd, pe, pe_thr, wi)
        key = f"v_pe_add_{q_label}"
        results[key] = r
        pr(f"V+PE-ADD ({q_label})", r)

        # V-PE/VDO
        r = sim_pe_replace_vdo(cl, ef, es, at, pe, pe_thr, wi)
        key = f"v_pe_vdo_{q_label}"
        results[key] = r
        pr(f"V-PE/VDO ({q_label})", r)

        # V-PE-ENTRY
        r = sim_pe_entry(cl, at, pe, pe_thr, ef, es, wi)
        key = f"v_pe_entry_{q_label}"
        results[key] = r
        pr(f"V-PE-ENTRY ({q_label})", r)

    # V+PE-SOFT (PE > 0)
    r = sim_pe_soft(cl, ef, es, at, vd, pe, wi)
    results["v_pe_soft"] = r
    pr("V+PE-SOFT (PE>0)", r)

    return results


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Bootstrap Paired Comparison
# ═══════════════════════════════════════════════════════════════════════

def run_bootstrap(cl, hi, lo, op, vo, tb, wi, variants_to_test):
    """2000 paths, run specified variants on each path.

    variants_to_test: list of (name, quantile_or_None) tuples
      e.g. [("v_pe_add_P75", 0.75), ("v_pe_soft", None), ...]
    """
    print("\n" + "=" * 70)
    print(f"PHASE 2: BOOTSTRAP {N_BOOT} PATHS — {len(variants_to_test)+1} VARIANTS")
    print("=" * 70)

    cr, hr, lr, opr, vol, tbr = make_ratios(cl, hi, lo, op, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    boot = {"vtrend": {m: np.zeros(N_BOOT) for m in mkeys}}
    for name, _ in variants_to_test:
        boot[name] = {m: np.zeros(N_BOOT) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, o, v, t = gen_path(cr, hr, lr, opr, vol, tbr, n_trans, BLKSZ, p0, rng)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ef = _ema(c, FAST)
        es = _ema(c, SLOW)
        pe_arr, _, _, _ = _pe_components(c, h, l, o, v)

        # VTREND baseline
        r_vt = sim_vtrend(c, ef, es, at, vd, wi)
        for m in mkeys:
            boot["vtrend"][m][b] = r_vt[m]

        # Each variant
        for name, q in variants_to_test:
            if name == "v_pe_soft":
                r = sim_pe_soft(c, ef, es, at, vd, pe_arr, wi)
            elif name.startswith("v_pe_add"):
                pe_thr = _rolling_quantile(pe_arr, PE_Q_WINDOW, q)
                r = sim_pe_add(c, ef, es, at, vd, pe_arr, pe_thr, wi)
            elif name.startswith("v_pe_vdo"):
                pe_thr = _rolling_quantile(pe_arr, PE_Q_WINDOW, q)
                r = sim_pe_replace_vdo(c, ef, es, at, pe_arr, pe_thr, wi)
            elif name.startswith("v_pe_entry"):
                pe_thr = _rolling_quantile(pe_arr, PE_Q_WINDOW, q)
                r = sim_pe_entry(c, at, pe_arr, pe_thr, ef, es, wi)
            else:
                continue
            for m in mkeys:
                boot[name][m][b] = r[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT * (len(variants_to_test) + 1) / el:.0f} sims/sec)")

    return boot


def analyze_bootstrap(boot, variants_to_test):
    """Print distributions and paired comparisons."""
    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]

    print("\n" + "=" * 70)
    print("BOOTSTRAP DISTRIBUTIONS")
    print("=" * 70)

    for name in ["vtrend"] + [v[0] for v in variants_to_test]:
        label = name.upper().replace("_", "-")
        print(f"\n  -- {label} --")
        for m in ["cagr", "mdd", "sharpe", "calmar", "trades"]:
            a = boot[name][m]
            p5, p50, p95 = np.percentile(a, [5, 50, 95])
            extra = ""
            if m in ("cagr", "sharpe"):
                extra = f"  P(>0)={np.mean(a > 0) * 100:.1f}%"
            print(f"    {m:7s}  med={p50:+8.3f}  "
                  f"[p5={p5:+7.3f}, p95={p95:+7.3f}]{extra}")

    print("\n" + "=" * 70)
    print(f"PAIRED COMPARISONS vs VTREND (same {N_BOOT} paths)")
    print("=" * 70)
    print("  P(variant better) > 97.5% = significant at α=0.05\n")

    paired = {}
    any_sig = False

    for name, _ in variants_to_test:
        label = name.upper().replace("_", "-")
        print(f"  --- {label} vs VTREND ---")
        var_res = {}

        for m, direction in [("cagr", "higher"), ("mdd", "lower"),
                              ("sharpe", "higher"), ("calmar", "higher")]:
            if direction == "lower":
                d = boot["vtrend"][m] - boot[name][m]
            else:
                d = boot[name][m] - boot["vtrend"][m]

            p_better = float(np.mean(d > 0))
            ci = np.percentile(d, [2.5, 97.5])
            sig = " ***" if p_better > 0.975 else " *" if p_better > 0.95 else ""

            print(f"    D{m:7s}  mean={d.mean():+8.4f}  "
                  f"P({direction:6s})={p_better * 100:5.1f}%  "
                  f"95%CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]{sig}")

            var_res[m] = {
                "mean_delta": round(float(d.mean()), 6),
                "p_better": round(p_better, 4),
                "ci_lo": round(float(ci[0]), 4),
                "ci_hi": round(float(ci[1]), 4),
            }
            if p_better > 0.975:
                any_sig = True

        paired[name] = var_res
        print()

    return paired, any_sig


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("PE STUDY — PARTICIPATION-EFFICIENCY INTEGRATION WITH VTREND")
    print("=" * 70)
    print(f"  PE = max(0,CLV) × BODY × max(0,zDV)")
    print(f"  Period: {START} -> {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"  PE window: {PE_WINDOW}, quantile window: {PE_Q_WINDOW}")
    print(f"  Quantiles tested: {PE_QUANTILES}")

    print("\nLoading data...")
    cl, hi, lo, op, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "config": {
            "n_boot": N_BOOT, "block_size": BLKSZ, "seed": SEED,
            "pe_window": PE_WINDOW, "pe_q_window": PE_Q_WINDOW,
            "pe_quantiles": PE_QUANTILES,
            "trail": TRAIL, "atr_period": ATR_P,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START, "end": END, "warmup": WARMUP,
            "slow": SLOW, "fast": FAST,
        },
    }

    # ── PE distribution analysis ──
    pe_real = analyze_pe_distribution(cl, hi, lo, op, vo, wi)

    # ── Phase 1: Real data ──
    real_results = run_real_data(cl, hi, lo, op, vo, tb, wi)
    output["real_data"] = {k: v for k, v in real_results.items()}

    # ── Select promising variants for bootstrap ──
    # Pick the best PE quantile for each combination type + soft + entry
    # Always test: P75 add, P75 replace VDO, P75 entry, soft
    variants = [
        ("v_pe_add_P50", 0.50),
        ("v_pe_add_P75", 0.75),
        ("v_pe_add_P90", 0.90),
        ("v_pe_vdo_P50", 0.50),
        ("v_pe_vdo_P75", 0.75),
        ("v_pe_vdo_P90", 0.90),
        ("v_pe_soft", None),
        ("v_pe_entry_P75", 0.75),
    ]

    # ── Phase 2: Bootstrap ──
    boot = run_bootstrap(cl, hi, lo, op, vo, tb, wi, variants)

    # ── Phase 3: Analysis ──
    paired, any_sig = analyze_bootstrap(boot, variants)

    output["paired_vs_vtrend"] = paired
    output["any_significant"] = any_sig

    # Bootstrap medians
    output["bootstrap"] = {}
    for name in ["vtrend"] + [v[0] for v in variants]:
        output["bootstrap"][name] = {
            m: {
                "median": round(float(np.median(boot[name][m])), 4),
                "p5": round(float(np.percentile(boot[name][m], 5)), 4),
                "p95": round(float(np.percentile(boot[name][m], 95)), 4),
            }
            for m in ["cagr", "mdd", "sharpe", "calmar", "trades"]
        }

    # Determination
    if any_sig:
        output["determination"] = "PASS"
        output["fail_reason"] = None
    else:
        best_p = max(
            max(mr["p_better"] for mr in vr.values())
            for vr in paired.values()
        )
        output["determination"] = "FAIL"
        output["fail_reason"] = (
            f"No PE variant reaches P > 97.5% on any metric "
            f"(best: {best_p * 100:.1f}%)"
        )

    print("\n" + "=" * 70)
    print(f"DETERMINATION: {output['determination']}")
    if output["fail_reason"]:
        print(f"  {output['fail_reason']}")
    print("=" * 70)

    outfile = outdir / "pe_study.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {outfile}")
