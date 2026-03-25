#!/usr/bin/env python3
"""VPULL — Pullback Entry Strategy Design & Full Validation.

Pullback entry: enter when price bounces off fast EMA within uptrend,
instead of entering immediately whenever trend conditions hold (VTREND).

Validation pipeline (same rigor as VTREND):
  Phase 1: Real data comparison (VPULL vs VTREND)
  Phase 2: Permutation test for pullback timing (10,000 perms)
  Phase 3: Bootstrap 2000 paths — paired at default params
  Phase 4: Timescale robustness (16 timescales × 2000 paths)
  Phase 5: Determination

Parameters: slow_period, trail_mult, vdo_threshold (same 3 as VTREND)
Structural: fast = max(5, slow // 4), ATR(14), VDO(12, 28)
Cost: harsh (50 bps RT)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ───────────────────────────────────────────────────────

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
N_PERM = 10_000

ANN = math.sqrt(6.0 * 365.25)

# Fixed structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0
SLOW   = 120
FAST   = max(5, SLOW // 4)  # 30
VDO_T  = 0.0

# Timescale grid
SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

VDO_ON  = 0.0
VDO_OFF = -1e9


# ═══════════════════════════════════════════════════════════════════
# Data loading & path generation (same as timescale_robustness.py)
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# Simulation engines
# ═══════════════════════════════════════════════════════════════════

def sim_vtrend(cl, ef, es, at, vd, wi, vdo_thr, trail=TRAIL):
    """VTREND binary sim (f=1.0). Incremental stats."""
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
            if ef[i] > es[i] and vd[i] > vdo_thr:
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


def sim_vpull(cl, ef, es, at, vd, wi, vdo_thr, trail=TRAIL):
    """VPULL binary sim (f=1.0). Pullback entry + ATR trail.

    Entry: close crosses above EMA_fast from below, while trend up + VDO confirms.
    Exit: ATR trailing stop or trend reversal.
    """
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

        # Fill pending orders at previous bar's close
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

        # Signal
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            # VPULL ENTRY: pullback completion within uptrend
            if i > 0 and ef[i] > es[i] and vd[i] > vdo_thr:
                # Previous bar below fast EMA, current bar above → pullback ended
                if cl[i] >= ef[i] and cl[i - 1] < ef[i - 1]:
                    pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
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


# ═══════════════════════════════════════════════════════════════════
# Permutation test engines (score-based, matching multiple_comparison.py)
# ═══════════════════════════════════════════════════════════════════

def _compute_score(navs, trade_pnls):
    """Compute composite score from NAV array and trade PnLs."""
    nt = len(trade_pnls)
    if len(navs) < 2 or navs[0] <= 0 or nt < 10:
        return -1_000_000.0, nt

    na = np.array(navs, dtype=np.float64)
    tr = na[-1] / na[0] - 1.0
    yrs = (len(na) - 1) / (6.0 * 365.25)
    cagr = ((1.0 + tr) ** (1.0 / yrs) - 1.0) * 100.0 if yrs > 0 and tr > -1.0 else -100.0

    pk_arr = np.maximum.accumulate(na)
    dd = (pk_arr - na) / pk_arr * 100.0
    mdd = float(dd.max())

    rets = np.diff(na) / na[:-1]
    std = float(np.std(rets, ddof=0))
    sharpe = float(np.mean(rets)) / std * ANN if std > 1e-12 else 0.0

    pnls = np.array(trade_pnls)
    gp = float(pnls[pnls > 0].sum()) if (pnls > 0).any() else 0.0
    gl = float(abs(pnls[pnls < 0].sum())) if (pnls < 0).any() else 0.0
    pf = min(gp / gl, 3.0) if gl > 0 else (3.0 if gp > 0 else 0.0)

    score = (2.5 * cagr
             - 0.60 * mdd
             + 8.0 * max(0.0, sharpe)
             + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
             + min(nt / 50.0, 1.0) * 5.0)

    return score, nt


def sim_vpull_score(cl, ef, es, at, vd, wi, vdo_thr):
    """VPULL sim → (composite_score, n_trades). For permutation test."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False

    navs = []
    trade_pnls = []
    entry_cost = 0.0

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                bq = cash / (fp * (1.0 + CPS))
                entry_cost = cash
                cash = 0.0
                inp = True
                pk = p
                pe = False
            elif px:
                proceeds = bq * fp * (1.0 - CPS)
                trade_pnls.append(proceeds - entry_cost)
                cash = proceeds
                bq = 0.0
                inp = False
                pk = 0.0
                px = False

        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if i > 0 and ef[i] > es[i] and vd[i] > vdo_thr:
                if cl[i] >= ef[i] and cl[i - 1] < ef[i - 1]:
                    pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        proceeds = bq * cl[-1] * (1.0 - CPS)
        trade_pnls.append(proceeds - entry_cost)
        cash = proceeds
        bq = 0.0
        if navs:
            navs[-1] = cash

    return _compute_score(navs, trade_pnls)


def sim_vtrend_score(cl, ef, es, at, vd, wi, vdo_thr):
    """VTREND sim → (composite_score, n_trades). For permutation test."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False

    navs = []
    trade_pnls = []
    entry_cost = 0.0

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                bq = cash / (fp * (1.0 + CPS))
                entry_cost = cash
                cash = 0.0
                inp = True
                pk = p
                pe = False
            elif px:
                proceeds = bq * fp * (1.0 - CPS)
                trade_pnls.append(proceeds - entry_cost)
                cash = proceeds
                bq = 0.0
                inp = False
                pk = 0.0
                px = False

        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        proceeds = bq * cl[-1] * (1.0 - CPS)
        trade_pnls.append(proceeds - entry_cost)
        cash = proceeds
        bq = 0.0
        if navs:
            navs[-1] = cash

    return _compute_score(navs, trade_pnls)


def sim_random_skip(cl, ef, es, at, vd, wi, vdo_thr, skip_rate, seed):
    """VTREND with random skip at entry — null distribution for pullback test.

    At each bar where VTREND would enter (trend up + VDO confirms),
    skip with probability skip_rate. This matches the average trade
    reduction caused by the pullback filter.
    """
    rng = np.random.RandomState(seed)
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False

    navs = []
    trade_pnls = []
    entry_cost = 0.0

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                bq = cash / (fp * (1.0 + CPS))
                entry_cost = cash
                cash = 0.0
                inp = True
                pk = p
                pe = False
            elif px:
                proceeds = bq * fp * (1.0 - CPS)
                trade_pnls.append(proceeds - entry_cost)
                cash = proceeds
                bq = 0.0
                inp = False
                pk = 0.0
                px = False

        nav = cash + bq * p
        if i >= wi:
            navs.append(nav)

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > vdo_thr:
                if rng.random() < skip_rate:
                    continue   # random skip (instead of pullback filter)
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        proceeds = bq * cl[-1] * (1.0 - CPS)
        trade_pnls.append(proceeds - entry_cost)
        cash = proceeds
        bq = 0.0
        if navs:
            navs[-1] = cash

    return _compute_score(navs, trade_pnls)


# ═══════════════════════════════════════════════════════════════════
# Phase 1: Real data comparison
# ═══════════════════════════════════════════════════════════════════

def run_real_data(cl, hi, lo, vo, tb, wi):
    """VPULL vs VTREND on real data across all timescales."""
    print("\n" + "=" * 70)
    print("PHASE 1: REAL DATA — VPULL vs VTREND")
    print("=" * 70)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    print(f"\n  {'slow':>5s}  {'fast':>4s}  │ {'':^30s} │ {'':^30s}")
    print(f"  {'':>5s}  {'':>4s}  │ {'--- VPULL ---':^30s} │ {'--- VTREND ---':^30s}")
    print(f"  {'':>5s}  {'':>4s}  │ {'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Cm':>6s} {'Tr':>4s}"
          f" │ {'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Cm':>6s} {'Tr':>4s}")
    print("  " + "-" * 76)

    results = {}
    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)

        rv = sim_vpull(cl, ef, es, at, vd, wi, VDO_ON)
        rt = sim_vtrend(cl, ef, es, at, vd, wi, VDO_ON)

        results[sp] = {"vpull": rv, "vtrend": rt}

        print(f"  {sp:5d}  {fp:4d}  │ "
              f"{rv['cagr']:+6.1f}% {rv['mdd']:5.1f}% {rv['sharpe']:5.3f} "
              f"{rv['calmar']:5.3f} {rv['trades']:4d} │ "
              f"{rt['cagr']:+6.1f}% {rt['mdd']:5.1f}% {rt['sharpe']:5.3f} "
              f"{rt['calmar']:5.3f} {rt['trades']:4d}")

    # Highlight default params
    rv = results[SLOW]["vpull"]
    rt = results[SLOW]["vtrend"]
    print(f"\n  Default (slow={SLOW}):")
    print(f"    VPULL:  CAGR={rv['cagr']:+.1f}%  MDD={rv['mdd']:.1f}%  "
          f"Sharpe={rv['sharpe']:.3f}  Trades={rv['trades']}")
    print(f"    VTREND: CAGR={rt['cagr']:+.1f}%  MDD={rt['mdd']:.1f}%  "
          f"Sharpe={rt['sharpe']:.3f}  Trades={rt['trades']}")

    return results


# ═══════════════════════════════════════════════════════════════════
# Phase 2: Permutation test for pullback timing
# ═══════════════════════════════════════════════════════════════════

def run_permutation(cl, hi, lo, vo, tb, wi):
    """Test if pullback-to-EMA timing beats random entry within trend."""
    print("\n" + "=" * 70)
    print(f"PHASE 2: PERMUTATION TEST — PULLBACK TIMING ({N_PERM:,} perms)")
    print("=" * 70)

    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # Real VPULL score
    real_score, real_trades = sim_vpull_score(cl, ef, es, at, vd, wi, VDO_T)
    print(f"\n  VPULL real score: {real_score:.2f}  (trades: {real_trades})")

    # VTREND score (enters on every eligible bar)
    vt_score, vt_trades = sim_vtrend_score(cl, ef, es, at, vd, wi, VDO_T)
    print(f"  VTREND real score: {vt_score:.2f}  (trades: {vt_trades})")

    # Calibrate skip rate
    skip_rate = 1.0 - real_trades / vt_trades if vt_trades > 0 else 0.5
    print(f"  Skip rate: {skip_rate:.4f}  (VPULL skips {skip_rate*100:.1f}% of VTREND entries)")

    # Null distribution: random skip at calibrated rate
    print(f"\n  Running {N_PERM:,} null simulations...")
    null_scores = np.empty(N_PERM)
    null_trades = np.empty(N_PERM)
    t0 = time.time()

    for i in range(N_PERM):
        if (i + 1) % 2000 == 0:
            el = time.time() - t0
            rate = (i + 1) / el if el > 0 else 1
            eta = (N_PERM - i - 1) / rate
            print(f"    {i+1:6d}/{N_PERM}  ({el:.0f}s, ~{eta:.0f}s left)")

        s, nt = sim_random_skip(cl, ef, es, at, vd, wi, VDO_T, skip_rate, seed=i)
        null_scores[i] = s
        null_trades[i] = nt

    el = time.time() - t0
    print(f"  Done: {el:.1f}s")

    # P-value
    p_val = float(np.mean(null_scores >= real_score))
    null_med = float(np.median(null_scores))
    null_mean = float(np.mean(null_scores))

    print(f"\n  Results:")
    print(f"    Real VPULL score:   {real_score:+.2f}")
    print(f"    Null median score:  {null_med:+.2f}")
    print(f"    Null mean score:    {null_mean:+.2f}")
    print(f"    P-value:            {p_val:.4f}")
    print(f"    Null trades (med):  {np.median(null_trades):.0f}")

    if p_val < 0.003125:
        print(f"    → SIGNIFICANT (p < Bonferroni threshold 0.003125)")
    elif p_val < 0.05:
        print(f"    → Marginal (p < 0.05 but fails Bonferroni)")
    else:
        print(f"    → NOT SIGNIFICANT (p ≥ 0.05)")

    return {
        "real_score": real_score,
        "real_trades": real_trades,
        "vtrend_score": vt_score,
        "vtrend_trades": vt_trades,
        "skip_rate": skip_rate,
        "p_value": p_val,
        "null_median": null_med,
        "null_mean": null_mean,
        "null_p5": float(np.percentile(null_scores, 5)),
        "null_p95": float(np.percentile(null_scores, 95)),
    }


# ═══════════════════════════════════════════════════════════════════
# Phase 3: Bootstrap 2000 paths — paired at default params
# ═══════════════════════════════════════════════════════════════════

def run_bootstrap_paired(cl, hi, lo, vo, tb, wi):
    """Bootstrap 2000 paths, VPULL and VTREND paired on same paths."""
    print("\n" + "=" * 70)
    print(f"PHASE 3: BOOTSTRAP {N_BOOT} PATHS — PAIRED (slow={SLOW})")
    print("=" * 70)

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    vpull_boot = {m: np.zeros(N_BOOT) for m in mkeys}
    vtrend_boot = {m: np.zeros(N_BOOT) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 500 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)

        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ef = _ema(c, FAST)
        es = _ema(c, SLOW)

        rv = sim_vpull(c, ef, es, at, vd, wi, VDO_T)
        rt = sim_vtrend(c, ef, es, at, vd, wi, VDO_T)

        for m in mkeys:
            vpull_boot[m][b] = rv[m]
            vtrend_boot[m][b] = rt[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT * 2} sims)")

    return vpull_boot, vtrend_boot


def analyze_bootstrap(vpull_boot, vtrend_boot, real_results):
    """Print bootstrap and paired comparison results."""
    print("\n" + "-" * 70)
    print("BOOTSTRAP RESULTS (with VDO, default params)")
    print("-" * 70)

    for label, boot in [("VPULL", vpull_boot), ("VTREND", vtrend_boot)]:
        print(f"\n  {label}:")
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = boot[m]
            p5, med, p95 = np.percentile(a, [5, 50, 95])
            p_pos = np.mean(a > 0) * 100
            print(f"    {m:>7s}: median={med:+7.3f}  [p5={p5:+7.3f}, p95={p95:+7.3f}]  P>0={p_pos:.1f}%")
        print(f"    trades: median={np.median(boot['trades']):.0f}")

    # Paired comparison
    print("\n" + "-" * 70)
    print("PAIRED COMPARISON: VPULL vs VTREND (same paths)")
    print("-" * 70)

    for m in ["cagr", "mdd", "sharpe", "calmar"]:
        if m == "mdd":
            # For MDD, lower is better → VPULL wins if VPULL MDD < VTREND MDD
            d = vtrend_boot[m] - vpull_boot[m]   # positive = VPULL better
            p_wins = np.mean(vpull_boot[m] < vtrend_boot[m]) * 100
            direction = "VPULL lower MDD"
        else:
            d = vpull_boot[m] - vtrend_boot[m]   # positive = VPULL better
            p_wins = np.mean(vpull_boot[m] > vtrend_boot[m]) * 100
            direction = "VPULL higher"

        mean_d = np.mean(d)
        ci_lo, ci_hi = np.percentile(d, [2.5, 97.5])

        sig = ""
        if ci_lo > 0:
            sig = " ** VPULL SIGNIFICANTLY BETTER"
        elif ci_hi < 0:
            sig = " ** VTREND SIGNIFICANTLY BETTER"

        print(f"\n  Δ{m}: mean={mean_d:+.4f}  95%CI=[{ci_lo:+.4f}, {ci_hi:+.4f}]"
              f"  P({direction})={p_wins:.1f}%{sig}")

    # Percentile of real data in bootstrap
    print("\n" + "-" * 70)
    print("REAL DATA PERCENTILE IN BOOTSTRAP")
    print("-" * 70)

    rv = real_results[SLOW]["vpull"]
    rt = real_results[SLOW]["vtrend"]

    for label, real_r, boot in [("VPULL", rv, vpull_boot), ("VTREND", rt, vtrend_boot)]:
        pct_sh = np.mean(boot["sharpe"] <= real_r["sharpe"]) * 100
        pct_cg = np.mean(boot["cagr"] <= real_r["cagr"]) * 100
        flag = " !" if pct_sh > 97.5 else (" ?" if pct_sh > 95 else "")
        print(f"  {label}: Sharpe={real_r['sharpe']:.3f} → {pct_sh:.1f}th pctile{flag}  "
              f"  CAGR={real_r['cagr']:+.1f}% → {pct_cg:.1f}th pctile")


# ═══════════════════════════════════════════════════════════════════
# Phase 4: Timescale robustness
# ═══════════════════════════════════════════════════════════════════

def run_timescale_robustness(cl, hi, lo, vo, tb, wi):
    """16 timescales × 2000 paths × 4 variants (VPULL/VTREND × VDO on/off)."""
    print("\n" + "=" * 70)
    print(f"PHASE 4: TIMESCALE ROBUSTNESS ({N_BOOT} paths × {len(SLOW_PERIODS)} timescales × 4 variants)")
    print("=" * 70)

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]

    # Storage: [n_boot, n_sp] for each metric × 4 variants
    vp_on  = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}   # VPULL + VDO
    vp_off = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}   # VPULL - VDO
    vt_on  = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}   # VTREND + VDO
    vt_off = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}   # VTREND - VDO

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)

        # Path-constant indicators
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            r1 = sim_vpull(c, ef, es, at, vd, wi, VDO_ON)
            r2 = sim_vpull(c, ef, es, at, vd, wi, VDO_OFF)
            r3 = sim_vtrend(c, ef, es, at, vd, wi, VDO_ON)
            r4 = sim_vtrend(c, ef, es, at, vd, wi, VDO_OFF)

            for m in mkeys:
                vp_on[m][b, j]  = r1[m]
                vp_off[m][b, j] = r2[m]
                vt_on[m][b, j]  = r3[m]
                vt_off[m][b, j] = r4[m]

    el = time.time() - t0
    n_total = N_BOOT * n_sp * 4
    print(f"\n  Done: {el:.1f}s ({n_total:,} sims, {n_total / el:.0f} sims/sec)")

    return vp_on, vp_off, vt_on, vt_off


def analyze_timescale(vp_on, vp_off, vt_on, vt_off, real_results):
    """Comprehensive timescale analysis."""
    n_sp = len(SLOW_PERIODS)

    # ── VPULL Robustness ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VPULL TIMESCALE ROBUSTNESS (with VDO)")
    print("=" * 70)

    print(f"\n  {'slow':>5s} {'days':>5s}  "
          f"{'medSh':>6s} {'p5Sh':>6s} {'p95Sh':>6s}  "
          f"{'medCAGR':>8s} {'medMDD':>7s}  "
          f"{'P(C>0)':>7s} {'P(S>0)':>7s}")
    print("  " + "-" * 75)

    vp_prod_min = vp_prod_max = vp_strong_min = vp_strong_max = None

    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        sh = vp_on["sharpe"][:, j]
        cg = vp_on["cagr"][:, j]

        p5, med, p95 = np.percentile(sh, [5, 50, 95])
        p_cagr = np.mean(cg > 0) * 100
        p_sh   = np.mean(sh > 0) * 100

        marker = ""
        if med > 0:
            if vp_prod_min is None: vp_prod_min = sp
            vp_prod_max = sp
            marker = " *"
        if p_cagr > 70:
            if vp_strong_min is None: vp_strong_min = sp
            vp_strong_max = sp
            marker = " **"

        print(f"  {sp:5d} {days:5.1f}  "
              f"{med:+6.3f} {p5:+6.3f} {p95:+6.3f}  "
              f"{np.median(cg):+7.1f}% {np.median(vp_on['mdd'][:, j]):6.1f}%  "
              f"{p_cagr:6.1f}% {p_sh:6.1f}%{marker}")

    print("\n  Legend: * = productive (median Sharpe > 0), ** = strong (P(CAGR>0) > 70%)")

    # Width
    print("\n  VPULL ROBUSTNESS WIDTH:")
    if vp_prod_min and vp_prod_max:
        w = vp_prod_max / vp_prod_min
        print(f"    Productive: slow={vp_prod_min}–{vp_prod_max} (width {w:.1f}x)")
    if vp_strong_min and vp_strong_max:
        ws = vp_strong_max / vp_strong_min
        print(f"    Strong:     slow={vp_strong_min}–{vp_strong_max} (width {ws:.1f}x)")

    # ── VTREND Robustness (for comparison) ───────────────────────
    print("\n" + "=" * 70)
    print("VTREND TIMESCALE ROBUSTNESS (with VDO, for comparison)")
    print("=" * 70)

    print(f"\n  {'slow':>5s} {'days':>5s}  "
          f"{'medSh':>6s} {'p5Sh':>6s} {'p95Sh':>6s}  "
          f"{'medCAGR':>8s} {'medMDD':>7s}  "
          f"{'P(C>0)':>7s} {'P(S>0)':>7s}")
    print("  " + "-" * 75)

    vt_prod_min = vt_prod_max = vt_strong_min = vt_strong_max = None

    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        sh = vt_on["sharpe"][:, j]
        cg = vt_on["cagr"][:, j]

        p5, med, p95 = np.percentile(sh, [5, 50, 95])
        p_cagr = np.mean(cg > 0) * 100
        p_sh   = np.mean(sh > 0) * 100

        marker = ""
        if med > 0:
            if vt_prod_min is None: vt_prod_min = sp
            vt_prod_max = sp
            marker = " *"
        if p_cagr > 70:
            if vt_strong_min is None: vt_strong_min = sp
            vt_strong_max = sp
            marker = " **"

        print(f"  {sp:5d} {days:5.1f}  "
              f"{med:+6.3f} {p5:+6.3f} {p95:+6.3f}  "
              f"{np.median(cg):+7.1f}% {np.median(vt_on['mdd'][:, j]):6.1f}%  "
              f"{p_cagr:6.1f}% {p_sh:6.1f}%{marker}")

    # ── Paired VPULL vs VTREND at each timescale ─────────────────
    print("\n" + "=" * 70)
    print("PAIRED: VPULL vs VTREND AT EACH TIMESCALE (with VDO)")
    print("=" * 70)

    print(f"\n  {'slow':>5s} {'days':>5s}  "
          f"{'vpMedSh':>8s} {'vtMedSh':>8s} {'meanΔSh':>8s}  "
          f"{'P(VP>VT)':>9s}")
    print("  " + "-" * 55)

    vp_wins_count = 0
    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        vp_sh = vp_on["sharpe"][:, j]
        vt_sh = vt_on["sharpe"][:, j]
        d_sh = vp_sh - vt_sh

        p_wins = np.mean(vp_sh > vt_sh) * 100
        if p_wins > 50:
            vp_wins_count += 1

        marker = ""
        if p_wins > 97.5:
            marker = " **"
        elif p_wins > 55:
            marker = " +"
        elif p_wins < 45:
            marker = " -"
        elif p_wins < 2.5:
            marker = " --"

        print(f"  {sp:5d} {days:5.1f}  "
              f"{np.median(vp_sh):+8.4f} {np.median(vt_sh):+8.4f} "
              f"{d_sh.mean():+8.4f}  "
              f"{p_wins:8.1f}%{marker}")

    print(f"\n  VPULL wins at {vp_wins_count}/{n_sp} timescales (P > 50%)")

    # ── VDO contribution for VPULL ───────────────────────────────
    print("\n" + "=" * 70)
    print("VDO CONTRIBUTION FOR VPULL (paired, with - without)")
    print("=" * 70)

    print(f"\n  {'slow':>5s} {'days':>5s}  "
          f"{'meanΔSh':>8s} {'medΔSh':>8s}  "
          f"{'P(VDO+)':>8s}  "
          f"{'meanΔCAGR':>10s} {'meanΔMDD':>9s}")
    print("  " + "-" * 65)

    vdo_helps = 0
    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        d_sh = vp_on["sharpe"][:, j] - vp_off["sharpe"][:, j]
        d_cg = vp_on["cagr"][:, j]   - vp_off["cagr"][:, j]
        d_md = vp_off["mdd"][:, j]   - vp_on["mdd"][:, j]   # positive = VDO reduces MDD

        p_helps = np.mean(d_sh > 0)
        if p_helps > 0.5:
            vdo_helps += 1

        marker = " +" if p_helps > 0.55 else (" -" if p_helps < 0.45 else "")

        print(f"  {sp:5d} {days:5.1f}  "
              f"{d_sh.mean():+8.4f} {np.median(d_sh):+8.4f}  "
              f"{p_helps * 100:7.1f}%  "
              f"{d_cg.mean():+9.2f}% {d_md.mean():+8.2f}%{marker}")

    print(f"\n  VDO helps VPULL at {vdo_helps}/{n_sp} timescales")

    # ── Smoothness ───────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("SMOOTHNESS: adjacent timescale Sharpe correlation")
    print("-" * 70)

    vp_meds = [float(np.median(vp_on["sharpe"][:, j])) for j in range(n_sp)]
    vt_meds = [float(np.median(vt_on["sharpe"][:, j])) for j in range(n_sp)]

    if n_sp > 2:
        vp_corr = float(np.corrcoef(vp_meds[:-1], vp_meds[1:])[0, 1])
        vt_corr = float(np.corrcoef(vt_meds[:-1], vt_meds[1:])[0, 1])
        print(f"  VPULL  adjacent correlation: r = {vp_corr:.3f}")
        print(f"  VTREND adjacent correlation: r = {vt_corr:.3f}")

    return (vp_prod_min, vp_prod_max, vp_strong_min, vp_strong_max,
            vt_prod_min, vt_prod_max, vt_strong_min, vt_strong_max,
            vp_wins_count)


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("VPULL: PULLBACK ENTRY STRATEGY — FULL VALIDATION")
    print("=" * 70)
    print(f"  Period: {START} → {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Defaults: slow={SLOW}, fast={FAST}, trail={TRAIL}, vdo={VDO_T}")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"  Permutation: {N_PERM:,} perms")
    print(f"  Timescales: {len(SLOW_PERIODS)} ({SLOW_PERIODS[0]}–{SLOW_PERIODS[-1]} H4 bars)")

    print("\n  VPULL entry: close crosses above EMA(fast) from below,")
    print("               while EMA(fast) > EMA(slow) and VDO > threshold")
    print("  Exit: ATR trailing stop or trend reversal")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    # Phase 1: Real data
    real_results = run_real_data(cl, hi, lo, vo, tb, wi)

    # Phase 2: Permutation test
    perm_results = run_permutation(cl, hi, lo, vo, tb, wi)

    # Phase 3: Bootstrap paired
    vpull_boot, vtrend_boot = run_bootstrap_paired(cl, hi, lo, vo, tb, wi)
    analyze_bootstrap(vpull_boot, vtrend_boot, real_results)

    # Phase 4: Timescale robustness
    vp_on, vp_off, vt_on, vt_off = run_timescale_robustness(cl, hi, lo, vo, tb, wi)
    ts_result = analyze_timescale(vp_on, vp_off, vt_on, vt_off, real_results)
    (vp_pmin, vp_pmax, vp_smin, vp_smax,
     vt_pmin, vt_pmax, vt_smin, vt_smax,
     vp_wins) = ts_result

    # ── Phase 5: Final Determination ─────────────────────────────
    print("\n" + "=" * 70)
    print("PHASE 5: DETERMINATION")
    print("=" * 70)

    print(f"\n  Permutation p-value: {perm_results['p_value']:.4f}")
    if perm_results['p_value'] < 0.003125:
        print(f"  → Pullback timing is GENUINE (survives Bonferroni)")
    elif perm_results['p_value'] < 0.05:
        print(f"  → Pullback timing is MARGINAL (p < 0.05, fails Bonferroni)")
    else:
        print(f"  → Pullback timing is NOT SIGNIFICANT")

    # Paired bootstrap summary
    d_sh = vpull_boot["sharpe"] - vtrend_boot["sharpe"]
    ci_lo, ci_hi = np.percentile(d_sh, [2.5, 97.5])
    p_vp_wins = np.mean(d_sh > 0) * 100

    print(f"\n  Paired bootstrap (slow={SLOW}):")
    print(f"    ΔSharpe: mean={d_sh.mean():+.4f}  95%CI=[{ci_lo:+.4f}, {ci_hi:+.4f}]")
    print(f"    P(VPULL > VTREND): {p_vp_wins:.1f}%")

    if ci_lo > 0:
        print(f"    → VPULL significantly better than VTREND")
    elif ci_hi < 0:
        print(f"    → VTREND significantly better than VPULL")
    else:
        print(f"    → No significant difference")

    print(f"\n  Timescale robustness:")
    if vp_pmin and vp_pmax:
        print(f"    VPULL productive: slow={vp_pmin}–{vp_pmax} (width {vp_pmax/vp_pmin:.1f}x)")
    if vp_smin and vp_smax:
        print(f"    VPULL strong:     slow={vp_smin}–{vp_smax} (width {vp_smax/vp_smin:.1f}x)")
    print(f"    VPULL wins at {vp_wins}/{len(SLOW_PERIODS)} timescales")

    # ── Save ──────────────────────────────────────────────────────

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "config": {
            "n_boot": N_BOOT,
            "n_perm": N_PERM,
            "block_size": BLKSZ,
            "seed": SEED,
            "slow": SLOW,
            "fast": FAST,
            "trail": TRAIL,
            "vdo_threshold": VDO_T,
            "cost_rt_bps": COST.round_trip_bps,
        },
        "real_data": {str(sp): {k: {mk: round(mv, 4) for mk, mv in v.items()}
                                for k, v in r.items()}
                      for sp, r in real_results.items()},
        "permutation_test": {k: round(v, 6) if isinstance(v, float) else v
                             for k, v in perm_results.items()},
        "bootstrap_paired": {
            "vpull": {},
            "vtrend": {},
            "paired": {},
        },
        "timescale_robustness": {},
    }

    # Bootstrap summary
    for label, boot in [("vpull", vpull_boot), ("vtrend", vtrend_boot)]:
        for m in ["cagr", "mdd", "sharpe", "calmar"]:
            a = boot[m]
            p5, p50, p95 = np.percentile(a, [5, 50, 95])
            output["bootstrap_paired"][label][m] = {
                "median": round(float(p50), 4),
                "p5": round(float(p5), 4),
                "p95": round(float(p95), 4),
                "p_positive": round(float(np.mean(a > 0)), 4),
            }

    # Paired delta
    for m in ["cagr", "mdd", "sharpe", "calmar"]:
        d = vpull_boot[m] - vtrend_boot[m]
        ci_lo, ci_hi = np.percentile(d, [2.5, 97.5])
        output["bootstrap_paired"]["paired"][m] = {
            "mean_delta": round(float(d.mean()), 6),
            "median_delta": round(float(np.median(d)), 6),
            "ci_lo": round(float(ci_lo), 6),
            "ci_hi": round(float(ci_hi), 6),
            "p_vpull_better": round(float(np.mean(d > 0) if m != "mdd"
                                         else np.mean(d < 0)), 4),
        }

    # Timescale summary
    for j, sp in enumerate(SLOW_PERIODS):
        key = str(sp)
        output["timescale_robustness"][key] = {
            "vpull_with_vdo": {},
            "vpull_no_vdo": {},
            "vtrend_with_vdo": {},
            "paired_delta_sharpe": {},
        }
        for label, src in [
            ("vpull_with_vdo", vp_on),
            ("vpull_no_vdo", vp_off),
            ("vtrend_with_vdo", vt_on),
        ]:
            for m in ["cagr", "mdd", "sharpe", "calmar"]:
                a = src[m][:, j]
                p5, p50, p95 = np.percentile(a, [5, 50, 95])
                output["timescale_robustness"][key][label][m] = {
                    "median": round(float(p50), 4),
                    "p5": round(float(p5), 4),
                    "p95": round(float(p95), 4),
                    "p_positive": round(float(np.mean(a > 0)), 4),
                }

        d_sh = vp_on["sharpe"][:, j] - vt_on["sharpe"][:, j]
        output["timescale_robustness"][key]["paired_delta_sharpe"] = {
            "mean": round(float(d_sh.mean()), 6),
            "p_vpull_better": round(float(np.mean(d_sh > 0)), 4),
        }

    outpath = outdir / "pullback_strategy.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved → {outpath}")
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
