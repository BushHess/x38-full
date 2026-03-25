#!/usr/bin/env python3
"""PE Study V2 — Comprehensive Deep Analysis.

Following the user's request for thorough, deep, comprehensive research:

1. PE* = BODY × max(0, zDV) — de-overlapped version (no CLV)
2. Entry window: PE only filters within K bars of EMA crossover
3. Q70 with 300-bar PE quantile window
4. Component decomposition: which component carries information?
5. VDO vs PE overlap analysis (correlation, mutual information)
6. Multi-timescale check (N=60,120,240 for PE filter)

Builds on pe_study.py v1 findings:
  - V+PE-ADD P90: best variant, P(MDD lower)=78.6% — not significant
  - PE replacing VDO: WORSE (P≈21%)
  - PE as standalone entry: catastrophic

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

# V2 additions
PE_DV_WINDOW = 120      # lookback for zDV rolling median/MAD
PE_Q_WINDOW_A = 120     # original quantile window
PE_Q_WINDOW_B = 300     # user-suggested 300-bar window


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
            op[1:] / pc, vo[1:].copy(), tb[1:].copy())


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
    np.maximum(o, l, out=o)
    np.minimum(o, h, out=o)

    return c, h, l, o, v, t


# ═══════════════════════════════════════════════════════════════════════
# Indicators
# ═══════════════════════════════════════════════════════════════════════

def _zdv(close, volume, window=PE_DV_WINDOW):
    """z-scored log dollar volume using rolling median and MAD."""
    n = len(close)
    dv = close * volume
    ln_dv = np.log(np.maximum(dv, 1.0))
    zdv = np.zeros(n, dtype=np.float64)
    if window < n:
        windows = sliding_window_view(ln_dv, window)
        medians = np.median(windows, axis=1)
        mads = np.median(np.abs(windows - medians[:, np.newaxis]), axis=1)
        scales = np.maximum(1.4826 * mads, 1e-6)
        zdv[window:] = (ln_dv[window:] - medians[:n - window]) / scales[:n - window]
    return zdv


def _pe_full(close, high, low, open_, volume, dv_window=PE_DV_WINDOW):
    """PE = max(0, CLV) × BODY × max(0, zDV)."""
    eps = 1e-10
    spread = high - low + eps
    clv = (2.0 * close - high - low) / spread
    clv_pos = np.maximum(0.0, clv)
    body = np.abs(close - open_) / spread
    zdv = _zdv(close, volume, dv_window)
    zdv_pos = np.maximum(0.0, zdv)
    pe = clv_pos * body * zdv_pos
    return pe, clv_pos, body, zdv_pos


def _pe_star(close, high, low, open_, volume, dv_window=PE_DV_WINDOW):
    """PE* = BODY × max(0, zDV) — de-overlapped, no CLV."""
    eps = 1e-10
    spread = high - low + eps
    body = np.abs(close - open_) / spread
    zdv = _zdv(close, volume, dv_window)
    zdv_pos = np.maximum(0.0, zdv)
    pe_star = body * zdv_pos
    return pe_star, body, zdv_pos


def _rolling_quantile(arr, window, q):
    """Rolling quantile of arr over window. NaN for i < window."""
    n = len(arr)
    out = np.full(n, np.nan)
    if window >= n:
        return out
    windows = sliding_window_view(arr, window)
    out[window:] = np.quantile(windows[:n - window], q, axis=1)
    return out


def _ema_crossover_mask(ef, es, window):
    """Return mask: True for bars within `window` bars of an EMA up-crossover."""
    n = len(ef)
    mask = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if ef[i] > es[i] and ef[i - 1] <= es[i - 1]:
            # Crossover at bar i: mark bars i to i+window-1
            for j in range(i, min(i + window, n)):
                mask[j] = True
    return mask


# ═══════════════════════════════════════════════════════════════════════
# Simulation core (shared)
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


def sim_filter_add(cl, ef, es, at, vd, filter_arr, filter_thr, wi, trail=TRAIL):
    """VTREND + additional filter: entry only when filter_arr > filter_thr."""
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
        thr = filter_thr[i]
        if math.isnan(thr): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and filter_arr[i] > thr:
                pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_window_filter(cl, ef, es, at, vd, filter_arr, filter_thr, cross_mask, wi, trail=TRAIL):
    """VTREND + filter only within crossover window.
    Entry: EMA cross-up AND VDO > 0 AND (not in window OR filter > thr).
    Equivalent: if in crossover window, require filter; otherwise normal VTREND.
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
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                # In crossover window → require PE filter
                if cross_mask[i]:
                    thr = filter_thr[i]
                    if not math.isnan(thr) and filter_arr[i] > thr:
                        pe_ = True
                else:
                    # Outside window → normal VTREND (already in uptrend)
                    pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_component_filter(cl, ef, es, at, vd, component_arr, thr_val, wi, trail=TRAIL):
    """VTREND + single component as absolute threshold filter."""
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
            if ef[i] > es[i] and vd[i] > VDO_THR and component_arr[i] > thr_val:
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
# Analysis 1: VDO vs PE Overlap
# ═══════════════════════════════════════════════════════════════════════

def analyze_overlap(cl, hi, lo, op, vo, tb, wi):
    """Analyze information overlap between VDO and PE components."""
    print("\n" + "=" * 70)
    print("ANALYSIS 1: VDO vs PE OVERLAP")
    print("=" * 70)

    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    pe, clv, body, zdv = _pe_full(cl, hi, lo, op, vo)

    # Trading period only
    vd_t = vd[wi:]
    pe_t = pe[wi:]
    clv_t = clv[wi:]
    body_t = body[wi:]
    zdv_t = zdv[wi:]

    # Correlation: VDO vs each PE component
    # VDO can be NaN at start, filter valid
    valid = ~np.isnan(vd_t)
    v = vd_t[valid]

    print(f"\n  Valid bars for correlation: {valid.sum()}/{len(vd_t)}")
    print()

    for name, arr in [("PE", pe_t), ("CLV+", clv_t), ("BODY", body_t), ("zDV+", zdv_t)]:
        a = arr[valid]
        if np.std(v) > 1e-12 and np.std(a) > 1e-12:
            corr = np.corrcoef(v, a)[0, 1]
        else:
            corr = 0.0
        # Rank correlation (Spearman)
        from scipy.stats import spearmanr
        rho, p_val = spearmanr(v, a)
        print(f"  VDO vs {name:5s}: Pearson r={corr:+.4f}  Spearman ρ={rho:+.4f} (p={p_val:.4f})")

    # VDO signal agreement with PE
    vdo_pos = vd_t > 0
    pe_pos = pe_t > 0
    both_pos = vdo_pos & pe_pos
    vdo_only = vdo_pos & ~pe_pos
    pe_only = ~vdo_pos & pe_pos
    neither = ~vdo_pos & ~pe_pos

    total = len(vd_t)
    print(f"\n  Signal agreement (trading period, {total} bars):")
    print(f"    VDO>0 AND PE>0:  {both_pos.sum():5d} ({both_pos.sum()/total*100:5.1f}%)")
    print(f"    VDO>0, PE=0:     {vdo_only.sum():5d} ({vdo_only.sum()/total*100:5.1f}%)")
    print(f"    VDO=0, PE>0:     {pe_only.sum():5d} ({pe_only.sum()/total*100:5.1f}%)")
    print(f"    Both ≤ 0:        {neither.sum():5d} ({neither.sum()/total*100:5.1f}%)")

    # Information content: when VDO>0, what fraction of PE components are positive?
    vdo_up = vd_t[valid] > 0
    print(f"\n  When VDO > 0 ({vdo_up.sum()} bars):")
    for name, arr in [("CLV>0", clv_t), ("BODY>0.35", body_t), ("zDV>0", zdv_t)]:
        a = arr[valid]
        if "CLV" in name:
            frac = np.mean(a[vdo_up] > 0)
        elif "BODY" in name:
            frac = np.mean(a[vdo_up] > 0.35)
        else:
            frac = np.mean(a[vdo_up] > 0)
        print(f"    P({name} | VDO>0) = {frac*100:.1f}%")

    overlap_data = {
        "pearson_vdo_pe": round(float(np.corrcoef(vd_t[valid], pe_t[valid])[0, 1]), 4),
        "pearson_vdo_clv": round(float(np.corrcoef(vd_t[valid], clv_t[valid])[0, 1]), 4),
        "pearson_vdo_body": round(float(np.corrcoef(vd_t[valid], body_t[valid])[0, 1]), 4),
        "pearson_vdo_zdv": round(float(np.corrcoef(vd_t[valid], zdv_t[valid])[0, 1]), 4),
        "both_positive_pct": round(float(both_pos.sum() / total * 100), 2),
        "vdo_only_pct": round(float(vdo_only.sum() / total * 100), 2),
        "pe_only_pct": round(float(pe_only.sum() / total * 100), 2),
    }
    return overlap_data


# ═══════════════════════════════════════════════════════════════════════
# Analysis 2: Component Decomposition (Real Data)
# ═══════════════════════════════════════════════════════════════════════

def analyze_components(cl, hi, lo, op, vo, tb, wi):
    """Test each PE component individually as VTREND filter on real data."""
    print("\n" + "=" * 70)
    print("ANALYSIS 2: COMPONENT DECOMPOSITION (REAL DATA)")
    print("=" * 70)
    print("  Each component tested as standalone filter on VTREND entry\n")

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    pe, clv, body, zdv = _pe_full(cl, hi, lo, op, vo)
    pe_star, body2, zdv2 = _pe_star(cl, hi, lo, op, vo)

    # Baseline
    r_vt = sim_vtrend(cl, ef, es, at, vd, wi)

    print(f"  {'Variant':<30s} {'CAGR':>7s} {'MDD':>6s} {'Sharpe':>7s} "
          f"{'Calmar':>7s} {'Tr':>4s}")
    print("  " + "-" * 70)

    def pr(label, r):
        print(f"  {label:<30s} {r['cagr']:+6.1f}% {r['mdd']:5.1f}% "
              f"{r['sharpe']:+6.3f} {r['calmar']:+6.3f} {r['trades']:4d}")

    pr("VTREND (baseline)", r_vt)

    results = {"vtrend": r_vt}

    # Component filters with absolute thresholds
    component_tests = [
        ("V+CLV>0.25", clv, 0.25),
        ("V+CLV>0.50", clv, 0.50),
        ("V+BODY>0.25", body, 0.25),
        ("V+BODY>0.40", body, 0.40),
        ("V+zDV>0", zdv, 0.0),
        ("V+zDV>0.5", zdv, 0.5),
        ("V+zDV>1.0", zdv, 1.0),
    ]

    for label, arr, thr in component_tests:
        r = sim_component_filter(cl, ef, es, at, vd, arr, thr, wi)
        results[label] = r
        pr(label, r)

    print()

    # PE and PE* with different quantile windows and thresholds
    pe_tests = [
        # (label, indicator_arr, q_window, quantile)
        ("V+PE Q70(120)", pe, 120, 0.70),
        ("V+PE Q70(300)", pe, 300, 0.70),
        ("V+PE Q90(120)", pe, 120, 0.90),
        ("V+PE Q90(300)", pe, 300, 0.90),
        ("V+PE* Q70(120)", pe_star, 120, 0.70),
        ("V+PE* Q70(300)", pe_star, 300, 0.70),
        ("V+PE* Q90(120)", pe_star, 120, 0.90),
        ("V+PE* Q90(300)", pe_star, 300, 0.90),
    ]

    for label, arr, qw, q in pe_tests:
        thr = _rolling_quantile(arr, qw, q)
        r = sim_filter_add(cl, ef, es, at, vd, arr, thr, wi)
        results[label] = r
        pr(label, r)

    print()

    # Entry window variants
    for win_bars in [3, 6, 12]:
        cross_mask = _ema_crossover_mask(ef, es, win_bars)
        n_cross_bars = cross_mask[wi:].sum()
        pct_cross = n_cross_bars / (len(cl) - wi) * 100

        for arr, arr_name, qw, q in [
            (pe, "PE", 300, 0.70),
            (pe_star, "PE*", 300, 0.70),
        ]:
            thr = _rolling_quantile(arr, qw, q)
            label = f"V+{arr_name} WIN({win_bars}) Q70(300)"
            r = sim_window_filter(cl, ef, es, at, vd, arr, thr, cross_mask, wi)
            results[label] = r
            pr(label, r)

    print(f"\n  Cross window coverage: {n_cross_bars} bars in window "
          f"({pct_cross:.1f}% of trading bars)")

    return results


# ═══════════════════════════════════════════════════════════════════════
# Analysis 3: Bootstrap (focused on promising variants)
# ═══════════════════════════════════════════════════════════════════════

def run_bootstrap(cl, hi, lo, op, vo, tb, wi):
    """2000 bootstrap paths, test most promising PE variants."""
    print("\n" + "=" * 70)
    print("ANALYSIS 3: BOOTSTRAP 2000 PATHS — COMPREHENSIVE")
    print("=" * 70)

    # Variants to bootstrap (most promising from real data + user suggestions)
    # Each: (name, type, params)
    # type: "pe_add", "pe_star_add", "pe_window", "pe_star_window", "component"
    variant_specs = [
        # PE full with different Q windows
        ("V+PE Q90(120)", "pe_add", {"q": 0.90, "qw": 120}),
        ("V+PE Q70(300)", "pe_add", {"q": 0.70, "qw": 300}),
        ("V+PE Q90(300)", "pe_add", {"q": 0.90, "qw": 300}),
        # PE* (de-overlapped)
        ("V+PE* Q70(300)", "pe_star_add", {"q": 0.70, "qw": 300}),
        ("V+PE* Q90(120)", "pe_star_add", {"q": 0.90, "qw": 120}),
        ("V+PE* Q90(300)", "pe_star_add", {"q": 0.90, "qw": 300}),
        # Entry window (PE only near crossover)
        ("V+PE WIN(6) Q70(300)", "pe_window", {"q": 0.70, "qw": 300, "win": 6}),
        ("V+PE* WIN(6) Q70(300)", "pe_star_window", {"q": 0.70, "qw": 300, "win": 6}),
        # Individual components
        ("V+BODY>0.40", "component", {"arr_type": "body", "thr": 0.40}),
        ("V+zDV>0.5", "component", {"arr_type": "zdv", "thr": 0.5}),
    ]

    cr, hr, lr, opr, vol, tbr = make_ratios(cl, hi, lo, op, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    n_vars = len(variant_specs)
    boot = {"vtrend": {m: np.zeros(N_BOOT) for m in mkeys}}
    for name, _, _ in variant_specs:
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

        # Pre-compute all indicators for this path
        pe_arr, clv_arr, body_arr, zdv_arr = _pe_full(c, h, l, o, v)
        pe_star_arr, _, _ = _pe_star(c, h, l, o, v)

        # VTREND baseline
        r_vt = sim_vtrend(c, ef, es, at, vd, wi)
        for m in mkeys:
            boot["vtrend"][m][b] = r_vt[m]

        # Run each variant
        for name, vtype, params in variant_specs:
            if vtype == "pe_add":
                thr = _rolling_quantile(pe_arr, params["qw"], params["q"])
                r = sim_filter_add(c, ef, es, at, vd, pe_arr, thr, wi)
            elif vtype == "pe_star_add":
                thr = _rolling_quantile(pe_star_arr, params["qw"], params["q"])
                r = sim_filter_add(c, ef, es, at, vd, pe_star_arr, thr, wi)
            elif vtype == "pe_window":
                thr = _rolling_quantile(pe_arr, params["qw"], params["q"])
                cmask = _ema_crossover_mask(ef, es, params["win"])
                r = sim_window_filter(c, ef, es, at, vd, pe_arr, thr, cmask, wi)
            elif vtype == "pe_star_window":
                thr = _rolling_quantile(pe_star_arr, params["qw"], params["q"])
                cmask = _ema_crossover_mask(ef, es, params["win"])
                r = sim_window_filter(c, ef, es, at, vd, pe_star_arr, thr, cmask, wi)
            elif vtype == "component":
                if params["arr_type"] == "body":
                    comp = body_arr
                elif params["arr_type"] == "zdv":
                    comp = zdv_arr
                else:
                    continue
                r = sim_component_filter(c, ef, es, at, vd, comp, params["thr"], wi)
            else:
                continue

            for m in mkeys:
                boot[name][m][b] = r[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT * (n_vars + 1) / el:.0f} sims/sec)")

    return boot, variant_specs


def analyze_bootstrap(boot, variant_specs):
    """Print distributions and paired comparisons."""
    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    all_names = ["vtrend"] + [v[0] for v in variant_specs]

    print("\n" + "=" * 70)
    print("BOOTSTRAP DISTRIBUTIONS")
    print("=" * 70)

    for name in all_names:
        label = name
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
    best_p = 0.0
    best_name = ""
    best_metric = ""

    for name, _, _ in variant_specs:
        label = name
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
            if p_better > best_p:
                best_p = p_better
                best_name = name
                best_metric = m

        paired[name] = var_res
        print()

    any_sig = best_p > 0.975
    return paired, any_sig, best_p, best_name, best_metric


# ═══════════════════════════════════════════════════════════════════════
# Analysis 4: Multi-timescale PE check
# ═══════════════════════════════════════════════════════════════════════

def analyze_multi_timescale(cl, hi, lo, op, vo, tb, wi):
    """Test if PE filter helps at multiple EMA timescales (not just N=120)."""
    print("\n" + "=" * 70)
    print("ANALYSIS 4: PE FILTER ACROSS EMA TIMESCALES (REAL DATA)")
    print("=" * 70)
    print("  Does PE help consistently, or only at specific N?\n")

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    pe, _, _, _ = _pe_full(cl, hi, lo, op, vo)
    pe_star, _, _ = _pe_star(cl, hi, lo, op, vo)

    pe_thr_90_120 = _rolling_quantile(pe, 120, 0.90)
    pe_star_thr_70_300 = _rolling_quantile(pe_star, 300, 0.70)

    timescales = [60, 84, 120, 168, 240, 360]

    print(f"  {'N':>4s}  {'VTREND Sh':>10s}  {'V+PE(90/120) Sh':>16s}  {'ΔSh':>6s}  "
          f"{'V+PE*(70/300) Sh':>17s}  {'ΔSh':>6s}")
    print("  " + "-" * 75)

    ts_results = {}
    pe_helps = 0
    pe_star_helps = 0

    for slow in timescales:
        fast = max(5, slow // 4)
        ef = _ema(cl, fast)
        es = _ema(cl, slow)

        r_vt = sim_vtrend(cl, ef, es, at, vd, wi)
        r_pe = sim_filter_add(cl, ef, es, at, vd, pe, pe_thr_90_120, wi)
        r_pe_star = sim_filter_add(cl, ef, es, at, vd, pe_star, pe_star_thr_70_300, wi)

        d_pe = r_pe["sharpe"] - r_vt["sharpe"]
        d_pe_star = r_pe_star["sharpe"] - r_vt["sharpe"]

        if d_pe > 0: pe_helps += 1
        if d_pe_star > 0: pe_star_helps += 1

        print(f"  {slow:4d}  {r_vt['sharpe']:+10.3f}  {r_pe['sharpe']:+16.3f}  "
              f"{d_pe:+6.3f}  {r_pe_star['sharpe']:+17.3f}  {d_pe_star:+6.3f}")

        ts_results[slow] = {
            "vtrend_sharpe": round(r_vt["sharpe"], 4),
            "pe_sharpe": round(r_pe["sharpe"], 4),
            "pe_star_sharpe": round(r_pe_star["sharpe"], 4),
        }

    n_ts = len(timescales)
    print(f"\n  PE helps at {pe_helps}/{n_ts} timescales")
    print(f"  PE* helps at {pe_star_helps}/{n_ts} timescales")

    return ts_results, pe_helps, pe_star_helps, n_ts


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("PE STUDY V2 — COMPREHENSIVE DEEP ANALYSIS")
    print("=" * 70)
    print(f"  Period: {START} -> {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print()
    print("  Tests:")
    print("    1. VDO vs PE overlap analysis")
    print("    2. Component decomposition (CLV, BODY, zDV)")
    print("    3. PE* = BODY × max(0,zDV) — de-overlapped")
    print("    4. Entry window (PE only near EMA crossover)")
    print("    5. Q70 with 300-bar quantile window")
    print("    6. Multi-timescale consistency check")
    print("    7. Full 2000-path bootstrap on all promising variants")

    print("\nLoading data...")
    cl, hi, lo, op, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "study": "pe_study_v2",
        "config": {
            "n_boot": N_BOOT, "block_size": BLKSZ, "seed": SEED,
            "pe_dv_window": PE_DV_WINDOW,
            "trail": TRAIL, "atr_period": ATR_P,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START, "end": END, "warmup": WARMUP,
            "slow": SLOW, "fast": FAST,
        },
    }

    # ── Analysis 1: Overlap ──
    overlap = analyze_overlap(cl, hi, lo, op, vo, tb, wi)
    output["overlap_analysis"] = overlap

    # ── Analysis 2: Component decomposition ──
    comp_results = analyze_components(cl, hi, lo, op, vo, tb, wi)
    output["component_real_data"] = {k: v for k, v in comp_results.items()}

    # ── Analysis 4: Multi-timescale ──
    ts_results, pe_helps, pe_star_helps, n_ts = analyze_multi_timescale(
        cl, hi, lo, op, vo, tb, wi
    )
    output["multi_timescale"] = {
        "results": ts_results,
        "pe_helps_count": pe_helps,
        "pe_star_helps_count": pe_star_helps,
        "n_timescales": n_ts,
    }

    # ── Analysis 3: Bootstrap ──
    boot, variant_specs = run_bootstrap(cl, hi, lo, op, vo, tb, wi)
    paired, any_sig, best_p, best_name, best_metric = analyze_bootstrap(boot, variant_specs)

    output["paired_vs_vtrend"] = paired
    output["any_significant"] = any_sig

    # Bootstrap medians
    output["bootstrap"] = {}
    all_names = ["vtrend"] + [v[0] for v in variant_specs]
    for name in all_names:
        output["bootstrap"][name] = {
            m: {
                "median": round(float(np.median(boot[name][m])), 4),
                "p5": round(float(np.percentile(boot[name][m], 5)), 4),
                "p95": round(float(np.percentile(boot[name][m], 95)), 4),
            }
            for m in ["cagr", "mdd", "sharpe", "calmar", "trades"]
        }

    # ── Final Determination ──
    if any_sig:
        output["determination"] = "PASS"
        output["fail_reason"] = None
    else:
        output["determination"] = "FAIL"
        output["fail_reason"] = (
            f"No PE/PE* variant reaches P > 97.5% on any metric. "
            f"Best: {best_name} {best_metric} P={best_p*100:.1f}%"
        )

    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"\n  V1 best: V+PE-ADD P90, P(MDD lower)=78.6%")
    print(f"  V2 best: {best_name}, {best_metric} P={best_p*100:.1f}%")
    print(f"\n  PE helps at {pe_helps}/{n_ts} timescales (real data)")
    print(f"  PE* helps at {pe_star_helps}/{n_ts} timescales (real data)")
    print(f"\n  VDO-PE Pearson correlation: {overlap['pearson_vdo_pe']:.4f}")
    print(f"  VDO-CLV Pearson correlation: {overlap['pearson_vdo_clv']:.4f}")

    print(f"\n  DETERMINATION: {output['determination']}")
    if output["fail_reason"]:
        print(f"  {output['fail_reason']}")
    print("=" * 70)

    outfile = outdir / "pe_study_v2.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {outfile}")
