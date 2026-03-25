#!/usr/bin/env python3
"""VEXIT Study — Exit Mechanism & Entry Filter Factorial Analysis.

2×2 factorial design testing whether ratcheting trail and/or Donchian
entry filter improve VTREND:

  Factor A: {standard trail, ratcheting trail}
  Factor B: {EMA entry only, EMA + Donchian entry}

Variants:
  VTREND       — standard trail + EMA entry         (baseline)
  V-RATCH      — ratcheting trail + EMA entry
  VTWIN        — standard trail + EMA + Donchian entry
  V-TWIN-RATCH — ratcheting trail + EMA + Donchian entry

Ratcheting trail: once set, trail level can only go UP (never loosens
when ATR expands during volatility spikes). Addresses VTREND's main
weakness: trail loosening during crashes → large MDD.

Primary hypothesis: V-TWIN-RATCH vs VTREND (single test, α=0.05).
Secondary: factorial decomposition (exploratory).

Method: 2000 bootstrap paths, paired comparison, same seed.
Cost: harsh (50 bps round-trip).
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
CPS    = COST.per_side_bps / 10_000.0   # 0.0025

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
BLKSZ  = 60
SEED   = 42

ANN = math.sqrt(6.0 * 365.25)

# Fixed structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

VDO_THR = 0.0   # VDO > 0 required for entry

# Default timescale
SLOW = 120
FAST = max(5, SLOW // 4)  # 30

# Timescale grid (H4 bars) for robustness sweep
N_GRID = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]


# ═══════════════════════════════════════════════════════════════════════
# Data loading & bootstrap path generation
# ═══════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, wi, n


def make_ratios(cl, hi, lo, vo, tb):
    pc = cl[:-1]
    return cl[1:] / pc, hi[1:] / pc, lo[1:] / pc, vo[1:].copy(), tb[1:].copy()


def gen_path(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng):
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
    v = np.empty_like(c); t = np.empty_like(c)
    h[0] = p0 * 1.002;  l[0] = p0 * 0.998
    v[0] = vol[idx[0]];  t[0] = tb[idx[0]]
    h[1:] = c[:-1] * hr[idx];  l[1:] = c[:-1] * lr[idx]
    v[1:] = vol[idx];          t[1:] = tb[idx]
    np.maximum(h, c, out=h);   np.minimum(l, c, out=l)
    return c, h, l, v, t


# ═══════════════════════════════════════════════════════════════════════
# Donchian indicator
# ═══════════════════════════════════════════════════════════════════════

def _highest_high(high, n):
    """Rolling max of high[i-n:i]. NaN for i < n. No lookahead."""
    out = np.full(len(high), np.nan)
    if n <= 0 or n >= len(high):
        return out
    windows = sliding_window_view(high, n)
    out[n:] = np.max(windows[:len(high) - n], axis=1)
    return out


# ═══════════════════════════════════════════════════════════════════════
# Four simulation variants (separate functions for performance)
# ═══════════════════════════════════════════════════════════════════════

def sim_vtrend(cl, ef, es, at, vd, wi, trail=TRAIL):
    """VTREND baseline: standard ATR trail + EMA cross-down exit."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

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


def sim_ratch(cl, ef, es, at, vd, wi, trail=TRAIL):
    """V-RATCH: ratcheting ATR trail + EMA cross-down exit.

    Trail level can only go UP (tighten), never DOWN (loosen).
    Prevents trail from loosening when ATR expands during vol spikes.
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    tl = 0.0   # ratcheting trail level
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
                # Initialize trail at entry
                a0 = at[i]
                tl = (p - trail * a0) if not math.isnan(a0) else 0.0
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                tl = 0.0
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            new_trail = pk - trail * a_val
            tl = max(tl, new_trail)   # RATCHET: only tighten
            if p < tl:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

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


def sim_vtwin(cl, ef, es, hh, at, vd, wi, trail=TRAIL):
    """VTWIN: standard trail + EMA + Donchian entry."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        a_val = at[i]
        hh_val = hh[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(hh_val):
            continue

        if not inp:
            # Twin entry: EMA crossover AND Donchian breakout AND VDO
            if ef[i] > es[i] and p > hh_val and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

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


def sim_twin_ratch(cl, ef, es, hh, at, vd, wi, trail=TRAIL):
    """V-TWIN-RATCH: ratcheting trail + EMA + Donchian entry.

    Combines VTWIN entry filter with ratcheting exit.
    Hypothesis: both improvements stack (entry filter + exit protection).
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    tl = 0.0   # ratcheting trail level
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
                a0 = at[i]
                tl = (p - trail * a0) if not math.isnan(a0) else 0.0
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                tl = 0.0
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        a_val = at[i]
        hh_val = hh[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(hh_val):
            continue

        if not inp:
            if ef[i] > es[i] and p > hh_val and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            new_trail = pk - trail * a_val
            tl = max(tl, new_trail)   # RATCHET
            if p < tl:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

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
# Phase 1: Real Data Comparison
# ═══════════════════════════════════════════════════════════════════════

def run_real_data(cl, hi, lo, vo, tb, wi):
    """Run all 4 variants on real data at multiple timescales."""
    print("\n" + "=" * 70)
    print("PHASE 1: REAL DATA COMPARISON")
    print("=" * 70)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    print(f"\n  {'N':>5s} {'days':>5s}  "
          f"{'--- VTREND ---':^24s}  "
          f"{'--- V-RATCH ---':^24s}  "
          f"{'--- VTWIN ---':^24s}  "
          f"{'--- V-TWIN-RATCH ---':^24s}")
    print(f"  {'':>5s} {'':>5s}  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Tr':>4s}  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Tr':>4s}  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Tr':>4s}  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Tr':>4s}")
    print("  " + "-" * 120)

    results = {}
    for N in N_GRID:
        days = N * 4 / 24
        fast_p = max(5, N // 4)

        ef = _ema(cl, fast_p)
        es = _ema(cl, N)
        hh = _highest_high(hi, N)

        r_vt = sim_vtrend(cl, ef, es, at, vd, wi)
        r_ra = sim_ratch(cl, ef, es, at, vd, wi)
        r_tw = sim_vtwin(cl, ef, es, hh, at, vd, wi)
        r_tr = sim_twin_ratch(cl, ef, es, hh, at, vd, wi)

        results[N] = {"vtrend": r_vt, "v_ratch": r_ra,
                      "vtwin": r_tw, "v_twin_ratch": r_tr}

        def fmt(r):
            return (f"{r['cagr']:+6.1f}% {r['mdd']:5.1f}% "
                    f"{r['sharpe']:+5.3f} {r['trades']:4d}")

        print(f"  {N:5d} {days:5.1f}  {fmt(r_vt)}  {fmt(r_ra)}  "
              f"{fmt(r_tw)}  {fmt(r_tr)}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Bootstrap Paired Comparison
# ═══════════════════════════════════════════════════════════════════════

def run_bootstrap(cl, hi, lo, vo, tb, wi, timescales=None):
    """2000 paths, all 4 variants, paired on same paths.

    Args:
        timescales: list of N values to sweep. Default: [SLOW].
    """
    if timescales is None:
        timescales = [SLOW]

    n_ts = len(timescales)
    label = f"{len(timescales)} timescales" if n_ts > 1 else f"N={timescales[0]}"

    print("\n" + "=" * 70)
    print(f"PHASE 2: BOOTSTRAP {N_BOOT} PATHS × {label} × 4 VARIANTS")
    print("=" * 70)

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    variants = ["vtrend", "v_ratch", "vtwin", "v_twin_ratch"]

    # Shape: [variant][metric] = (N_BOOT, n_ts)
    boot = {v: {m: np.zeros((N_BOOT, n_ts)) for m in mkeys} for v in variants}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        for j, N in enumerate(timescales):
            fast_p = max(5, N // 4)
            ef = _ema(c, fast_p)
            es = _ema(c, N)
            hh = _highest_high(h, N)

            r_vt = sim_vtrend(c, ef, es, at, vd, wi)
            r_ra = sim_ratch(c, ef, es, at, vd, wi)
            r_tw = sim_vtwin(c, ef, es, hh, at, vd, wi)
            r_tr = sim_twin_ratch(c, ef, es, hh, at, vd, wi)

            for m in mkeys:
                boot["vtrend"][m][b, j] = r_vt[m]
                boot["v_ratch"][m][b, j] = r_ra[m]
                boot["vtwin"][m][b, j] = r_tw[m]
                boot["v_twin_ratch"][m][b, j] = r_tr[m]

    el = time.time() - t0
    n_total = N_BOOT * n_ts * 4
    print(f"\n  Done: {el:.1f}s ({n_total} sims, {n_total / el:.0f} sims/sec)")

    return boot, timescales


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Analysis
# ═══════════════════════════════════════════════════════════════════════

def analyze_distributions(boot, timescales):
    """Print bootstrap distributions for each variant."""
    print("\n" + "=" * 70)
    print("BOOTSTRAP DISTRIBUTIONS")
    print("=" * 70)

    # Use first timescale (or N=120 column) for summary
    j = 0
    if SLOW in timescales:
        j = timescales.index(SLOW)

    N = timescales[j]
    print(f"\n  Timescale: N={N} ({N * 4 / 24:.0f} days)")

    names = {
        "vtrend": "VTREND (baseline)",
        "v_ratch": "V-RATCH",
        "vtwin": "VTWIN",
        "v_twin_ratch": "V-TWIN-RATCH",
    }

    for v, label in names.items():
        print(f"\n  -- {label} --")
        for m in ["cagr", "mdd", "sharpe", "calmar", "trades"]:
            a = boot[v][m][:, j]
            p5, p50, p95 = np.percentile(a, [5, 50, 95])
            extra = ""
            if m == "cagr":
                extra = f"  P(>0)={np.mean(a > 0) * 100:.1f}%"
            elif m == "sharpe":
                extra = f"  P(>0)={np.mean(a > 0) * 100:.1f}%"
            print(f"    {m:7s}  med={p50:+8.3f}  "
                  f"[p5={p5:+7.3f}, p95={p95:+7.3f}]{extra}")

    return j


def analyze_paired(boot, timescales, j):
    """Paired comparison of all variants vs VTREND baseline."""
    N = timescales[j]

    print("\n" + "=" * 70)
    print(f"PAIRED COMPARISONS vs VTREND (N={N}, same {N_BOOT} paths)")
    print("=" * 70)
    print("  P(variant better) > 97.5% = significant at α=0.05 (one-sided).\n")

    comparisons = [
        ("V-RATCH", "v_ratch"),
        ("VTWIN", "vtwin"),
        ("V-TWIN-RATCH", "v_twin_ratch"),
    ]

    paired_results = {}
    any_sig = False

    for label, vkey in comparisons:
        print(f"  --- {label} vs VTREND ---")
        var_results = {}

        for m, direction in [("cagr", "higher"), ("mdd", "lower"),
                              ("sharpe", "higher"), ("calmar", "higher")]:
            if direction == "lower":
                d = boot["vtrend"][m][:, j] - boot[vkey][m][:, j]
            else:
                d = boot[vkey][m][:, j] - boot["vtrend"][m][:, j]

            p_better = float(np.mean(d > 0))
            ci = np.percentile(d, [2.5, 97.5])
            sig = " ***" if p_better > 0.975 else " *" if p_better > 0.95 else ""

            print(f"    D{m:7s}  mean={d.mean():+8.4f}  "
                  f"P({label} {direction:6s})={p_better * 100:5.1f}%  "
                  f"95%CI=[{ci[0]:+.4f}, {ci[1]:+.4f}]{sig}")

            var_results[m] = {
                "mean_delta": round(float(d.mean()), 6),
                "p_better": round(p_better, 4),
                "ci_lo": round(float(ci[0]), 4),
                "ci_hi": round(float(ci[1]), 4),
            }

            if p_better > 0.975:
                any_sig = True

        paired_results[vkey] = var_results
        print()

    return paired_results, any_sig


def analyze_factorial(boot, timescales, j):
    """Decompose 2×2 factorial: main effects and interaction."""
    N = timescales[j]

    print("\n" + "=" * 70)
    print(f"FACTORIAL DECOMPOSITION (N={N})")
    print("=" * 70)
    print("  Factor A: {standard, ratcheting} trail")
    print("  Factor B: {EMA only, EMA+Donchian} entry\n")

    for m in ["cagr", "mdd", "sharpe", "calmar"]:
        vt = boot["vtrend"][m][:, j]
        ra = boot["v_ratch"][m][:, j]
        tw = boot["vtwin"][m][:, j]
        tr = boot["v_twin_ratch"][m][:, j]

        # Main effect of ratcheting: avg(ratch variants) - avg(standard variants)
        ratch_effect = ((ra + tr) / 2) - ((vt + tw) / 2)
        # Main effect of Donchian: avg(donch variants) - avg(ema variants)
        donch_effect = ((tw + tr) / 2) - ((vt + ra) / 2)
        # Interaction: does combining them produce more than sum of parts?
        interaction = (tr - tw) - (ra - vt)

        sign = "-" if m == "mdd" else "+"
        print(f"  {m:7s}:")
        print(f"    Ratchet effect:  mean={ratch_effect.mean():+8.4f}  "
              f"P(helps)={np.mean(ratch_effect > 0 if m != 'mdd' else ratch_effect < 0) * 100:5.1f}%")
        print(f"    Donchian effect: mean={donch_effect.mean():+8.4f}  "
              f"P(helps)={np.mean(donch_effect > 0 if m != 'mdd' else donch_effect < 0) * 100:5.1f}%")
        print(f"    Interaction:     mean={interaction.mean():+8.4f}  "
              f"P(synergy)={np.mean(interaction > 0 if m != 'mdd' else interaction < 0) * 100:5.1f}%")
        print()


def analyze_timescale_robustness(boot, timescales):
    """Timescale robustness for each variant (if multiple timescales)."""
    if len(timescales) < 3:
        return

    print("\n" + "=" * 70)
    print("TIMESCALE ROBUSTNESS")
    print("=" * 70)

    names = {
        "vtrend": "VTREND",
        "v_ratch": "V-RATCH",
        "vtwin": "VTWIN",
        "v_twin_ratch": "V-TWIN-RATCH",
    }

    for v, label in names.items():
        print(f"\n  -- {label} --")
        print(f"  {'N':>5s} {'days':>5s}  "
              f"{'medSh':>6s} {'medCAGR':>8s} {'medMDD':>7s} "
              f"{'P(C>0)':>7s}")
        print("  " + "-" * 50)

        for j, N in enumerate(timescales):
            days = N * 4 / 24
            sh = boot[v]["sharpe"][:, j]
            cg = boot[v]["cagr"][:, j]
            md = boot[v]["mdd"][:, j]

            marker = ""
            if np.median(sh) > 0:
                marker = " *"
            if np.mean(cg > 0) > 0.70:
                marker = " **"

            print(f"  {N:5d} {days:5.1f}  "
                  f"{np.median(sh):+6.3f} {np.median(cg):+7.1f}% "
                  f"{np.median(md):6.1f}% {np.mean(cg > 0) * 100:6.1f}%{marker}")


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("VEXIT STUDY — EXIT & ENTRY FACTORIAL ANALYSIS")
    print("=" * 70)
    print(f"  2×2 factorial: {{standard, ratchet}} trail × {{EMA, twin}} entry")
    print(f"  Primary: V-TWIN-RATCH vs VTREND (α=0.05)")
    print(f"  Period: {START} -> {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"  Default N={SLOW} ({SLOW * 4 / 24:.0f} days)")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "config": {
            "n_boot": N_BOOT, "block_size": BLKSZ, "seed": SEED,
            "trail": TRAIL, "atr_period": ATR_P,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START, "end": END, "warmup": WARMUP,
            "default_N": SLOW,
        },
    }

    # ── Phase 1: Real data comparison ──
    real_results = run_real_data(cl, hi, lo, vo, tb, wi)

    # Print summary at default N
    r = real_results[SLOW]
    print(f"\n  SUMMARY at N={SLOW}:")
    for v, label in [("vtrend", "VTREND"), ("v_ratch", "V-RATCH"),
                      ("vtwin", "VTWIN"), ("v_twin_ratch", "V-TWIN-RATCH")]:
        rv = r[v]
        print(f"    {label:16s}: CAGR={rv['cagr']:+.1f}%  MDD={rv['mdd']:.1f}%  "
              f"Sharpe={rv['sharpe']:.3f}  Trades={rv['trades']}")

    output["real_data"] = {
        str(N): {v: res for v, res in rd.items()}
        for N, rd in real_results.items()
    }

    # ── Phase 2: Bootstrap (default N only for speed) ──
    boot, ts = run_bootstrap(cl, hi, lo, vo, tb, wi, timescales=[SLOW])

    # ── Phase 3: Analysis ──
    j = analyze_distributions(boot, ts)
    paired_results, any_sig = analyze_paired(boot, ts, j)
    analyze_factorial(boot, ts, j)

    output["bootstrap_N120"] = {}
    for v in ["vtrend", "v_ratch", "vtwin", "v_twin_ratch"]:
        output["bootstrap_N120"][v] = {
            m: {
                "median": round(float(np.median(boot[v][m][:, 0])), 4),
                "p5": round(float(np.percentile(boot[v][m][:, 0], 5)), 4),
                "p95": round(float(np.percentile(boot[v][m][:, 0], 95)), 4),
            }
            for m in ["cagr", "mdd", "sharpe", "calmar", "trades"]
        }
    output["paired_vs_vtrend"] = paired_results
    output["any_significant"] = any_sig

    # ── Phase 2b: Full timescale sweep if any variant shows promise ──
    # Run if any paired P > 90% on any metric
    run_sweep = False
    for vk, vr in paired_results.items():
        for mk, mr in vr.items():
            if mr["p_better"] > 0.90:
                run_sweep = True
                break
        if run_sweep:
            break

    if run_sweep:
        print("\n  >>> Promising signal detected. Running full timescale sweep...")
        boot_full, ts_full = run_bootstrap(cl, hi, lo, vo, tb, wi, timescales=N_GRID)
        analyze_timescale_robustness(boot_full, ts_full)

        # Paired comparison at each timescale for the best variant
        print("\n" + "=" * 70)
        print("PAIRED COMPARISON ACROSS TIMESCALES")
        print("=" * 70)

        for vk in ["v_ratch", "vtwin", "v_twin_ratch"]:
            label = {"v_ratch": "V-RATCH", "vtwin": "VTWIN",
                     "v_twin_ratch": "V-TWIN-RATCH"}[vk]
            print(f"\n  --- {label} vs VTREND ---")
            print(f"  {'N':>5s} {'days':>5s}  "
                  f"{'P(Sh+)':>7s} {'P(MDD-)':>8s} {'P(CAGR+)':>9s} "
                  f"{'P(Calm+)':>9s}")
            print("  " + "-" * 55)

            for j2, N2 in enumerate(ts_full):
                days = N2 * 4 / 24
                d_sh = boot_full[vk]["sharpe"][:, j2] - boot_full["vtrend"]["sharpe"][:, j2]
                d_md = boot_full["vtrend"]["mdd"][:, j2] - boot_full[vk]["mdd"][:, j2]
                d_cg = boot_full[vk]["cagr"][:, j2] - boot_full["vtrend"]["cagr"][:, j2]
                d_cm = boot_full[vk]["calmar"][:, j2] - boot_full["vtrend"]["calmar"][:, j2]

                p_sh = np.mean(d_sh > 0) * 100
                p_md = np.mean(d_md > 0) * 100
                p_cg = np.mean(d_cg > 0) * 100
                p_cm = np.mean(d_cm > 0) * 100

                sig = " ***" if max(p_sh, p_md, p_cg, p_cm) > 97.5 else \
                      " *" if max(p_sh, p_md, p_cg, p_cm) > 95.0 else ""

                print(f"  {N2:5d} {days:5.1f}  "
                      f"{p_sh:6.1f}% {p_md:7.1f}% {p_cg:8.1f}% "
                      f"{p_cm:8.1f}%{sig}")

        output["timescale_sweep"] = True
    else:
        print("\n  No variant shows > 90% on any metric. Skipping timescale sweep.")
        output["timescale_sweep"] = False

    # ── Determination ──
    primary_p = paired_results.get("v_twin_ratch", {}).get("mdd", {}).get("p_better", 0)
    primary_sh = paired_results.get("v_twin_ratch", {}).get("sharpe", {}).get("p_better", 0)
    passes = primary_p > 0.975 or primary_sh > 0.975

    output["determination"] = "PASS" if passes else "FAIL"
    if not passes:
        best_p = max(
            max(mr["p_better"] for mr in vr.values())
            for vr in paired_results.values()
        )
        output["fail_reason"] = (
            f"No variant reaches P > 97.5% on any metric "
            f"(best: {best_p * 100:.1f}%)"
        )
    else:
        output["fail_reason"] = None

    print("\n" + "=" * 70)
    print(f"DETERMINATION: {output['determination']}")
    if output["fail_reason"]:
        print(f"  {output['fail_reason']}")
    print("=" * 70)

    outfile = outdir / "vexit_study.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {outfile}")
