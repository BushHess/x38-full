#!/usr/bin/env python3
"""Cost & Execution Efficiency Study.

VTREND's signal is proven optimal (8 alternatives tested, none better).
This study attacks the ONE remaining lever: execution efficiency.

Key insight: we always used "harsh" 50 bps RT. Binance VIP0 spot = 20 bps RT,
with BNB discount = 15 bps RT. The cost drag on ~30 trades/year is MASSIVE.

Phase 1: Cost Sensitivity (N=120, 9 cost levels, 2000 paths)
  → How much alpha at 0, 5, 10, 15, 20, 25, 30, 40, 50 bps?
  → What's the gross (zero-cost) Sharpe ceiling?

Phase 2: Cost-Optimal Timescale (VTREND + VTWIN)
  → Does optimal N shift with cost level?
  → At low cost, do shorter timescales (more trades) become viable?
  → Does VTWIN outperform VTREND at realistic costs?
  → Paired comparison at each (cost, N) point

Phase 3: Trade Quality Analysis (real data)
  → Individual trade PnL distribution
  → PnL vs signal strength (EMA gap, VDO magnitude) at entry
  → Trade duration distribution
  → Identify: are there systematic "bad" trades?

Phase 4: Signal Strength & Min Holding (bootstrap)
  → EMA gap filter: skip weak crossovers
  → Minimum holding period: avoid whipsaw exits
  → Delayed entry: enter 1-2 bars after signal (confirms trend)

Method: 2000 block bootstrap paths, paired comparison.
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

# Cost levels to test (round-trip bps)
COST_LEVELS = [0, 5, 10, 15, 20, 25, 30, 40, 50]

# Timescales for Phase 2
TIMESCALES = [48, 60, 72, 84, 96, 120, 144, 168, 200, 240]

# Cost levels for Phase 2 (reduced set)
COST_SWEEP = [0, 15, 30, 50]


# ═══════════════════════════════════════════════════════════════════════
# Data loading & bootstrap (same as other studies)
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

def _highest_high(high, n):
    """Rolling max of high[i-n:i] for i >= n (previous n bars, excluding current)."""
    out = np.full(len(high), np.nan)
    if n >= len(high):
        return out
    windows = sliding_window_view(high, n)
    out[n:] = np.max(windows[:len(high) - n], axis=1)
    return out


# ═══════════════════════════════════════════════════════════════════════
# Simulation functions (parameterized cost)
# ═══════════════════════════════════════════════════════════════════════

def sim_vtrend(cl, ef, es, at, vd, wi, cps, trail=TRAIL):
    """VTREND with parameterized per-side cost."""
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
                pe_ = False; bq = cash / (fp * (1.0 + cps)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - cps); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
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
        cash = bq * cl[-1] * (1.0 - cps); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_vtwin(cl, ef, es, at, vd, hh, wi, cps, trail=TRAIL):
    """VTWIN: EMA cross + Donchian breakout + VDO. Same exit as VTREND."""
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
                pe_ = False; bq = cash / (fp * (1.0 + cps)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - cps); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
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
        h_hi = hh[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(h_hi):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and p > h_hi:
                pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - cps); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_vtrend_gap(cl, ef, es, at, vd, wi, cps, min_gap, trail=TRAIL):
    """VTREND + signal strength filter: require EMA gap > min_gap at entry."""
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
                pe_ = False; bq = cash / (fp * (1.0 + cps)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - cps); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
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
            gap = (ef[i] - es[i]) / es[i]
            if gap > min_gap and vd[i] > VDO_THR:
                pe_ = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - cps); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_vtrend_minhold(cl, ef, es, at, vd, wi, cps, min_hold, trail=TRAIL):
    """VTREND + minimum holding period: ignore exits for first min_hold bars."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe_ = px = False; nt = 0; entry_bar = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe_:
                pe_ = False; bq = cash / (fp * (1.0 + cps)); cash = 0.0
                inp = True; pk = p; entry_bar = i
            elif px:
                cash = bq * fp * (1.0 - cps); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
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
            held = i - entry_bar
            if held >= min_hold:
                if p < pk - trail * a: px = True
                elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - cps); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_vtrend_detailed(cl, ef, es, at, vd, wi, cps, trail=TRAIL):
    """VTREND returning individual trade records for analysis."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe_ = px = False
    entry_bar = 0; entry_price = 0.0; entry_gap = 0.0; entry_vdo = 0.0
    trades = []

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe_:
                pe_ = False; entry_price = fp * (1.0 + cps)
                bq = cash / entry_price; cash = 0.0
                inp = True; pk = p; entry_bar = i
            elif px:
                exit_price = fp * (1.0 - cps)
                pnl_pct = (exit_price / entry_price - 1.0) * 100
                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "duration": i - entry_bar,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl_pct": pnl_pct,
                    "entry_gap": entry_gap,
                    "entry_vdo": entry_vdo,
                    "exit_reason": "trail" if cl[i-1] < pk - trail * at[i-1] else "ema_cross",
                    "in_report": entry_bar >= wi,
                })
                cash = bq * exit_price; bq = 0.0; inp = False; pk = 0.0; px = False
        if i < n:
            a = at[i]
            if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
            if not inp:
                if ef[i] > es[i] and vd[i] > VDO_THR:
                    pe_ = True
                    entry_gap = (ef[i] - es[i]) / es[i]
                    entry_vdo = vd[i]
            else:
                pk = max(pk, p)
                if p < pk - trail * a: px = True
                elif ef[i] < es[i]: px = True

    if inp and bq > 0:
        exit_price = cl[-1] * (1.0 - cps)
        pnl_pct = (exit_price / entry_price - 1.0) * 100
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "duration": n - 1 - entry_bar,
            "entry_price": entry_price, "exit_price": exit_price,
            "pnl_pct": pnl_pct, "entry_gap": entry_gap,
            "entry_vdo": entry_vdo, "exit_reason": "end",
            "in_report": entry_bar >= wi,
        })

    return trades


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
# Phase 1: Cost Sensitivity
# ═══════════════════════════════════════════════════════════════════════

def phase1_cost_sensitivity(cl, hi, lo, vo, tb, wi):
    """How much alpha at each cost level? (N=120)"""
    print("\n" + "=" * 70)
    print("PHASE 1: COST SENSITIVITY (VTREND, N=120)")
    print("=" * 70)
    print(f"  Cost levels: {COST_LEVELS} bps RT")

    cr, hr, lr, opr, vol, tbr = make_ratios(cl, hi, lo, cl, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    slow = 120
    fast = max(5, slow // 4)

    results = {}
    for cost_bps in COST_LEVELS:
        results[cost_bps] = {m: np.zeros(N_BOOT) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 500 == 0 or b == 0:
            el = time.time() - t0
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s)")

        c, h, l, o, v, t = gen_path(cr, hr, lr, opr, vol, tbr, n_trans, BLKSZ, p0, rng)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ef = _ema(c, fast)
        es = _ema(c, slow)

        for cost_bps in COST_LEVELS:
            cps = cost_bps / 20_000.0  # RT bps → per-side fraction
            r = sim_vtrend(c, ef, es, at, vd, wi, cps)
            for m in mkeys:
                results[cost_bps][m][b] = r[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s")

    # Print results
    print(f"\n  {'Cost':>6s} {'med CAGR':>10s} {'med MDD':>9s} {'med Sh':>8s} "
          f"{'med Calm':>9s} {'med Tr':>7s} {'P(CAGR>0)':>10s} {'P(Sh>0)':>8s}")
    print("  " + "-" * 75)

    summary = {}
    for cost_bps in COST_LEVELS:
        r = results[cost_bps]
        mc = np.median(r["cagr"])
        mm = np.median(r["mdd"])
        ms = np.median(r["sharpe"])
        mcl = np.median(r["calmar"])
        mt = np.median(r["trades"])
        pc = np.mean(r["cagr"] > 0) * 100
        ps = np.mean(r["sharpe"] > 0) * 100

        print(f"  {cost_bps:4d}bp {mc:+9.2f}% {mm:8.1f}% {ms:+7.3f} "
              f"{mcl:+8.3f} {mt:6.0f} {pc:9.1f}% {ps:7.1f}%")

        summary[cost_bps] = {
            "median_cagr": round(mc, 3),
            "median_mdd": round(mm, 2),
            "median_sharpe": round(ms, 4),
            "median_calmar": round(mcl, 4),
            "median_trades": round(mt, 0),
            "p_cagr_pos": round(pc, 1),
            "p_sharpe_pos": round(ps, 1),
            "p5_sharpe": round(float(np.percentile(r["sharpe"], 5)), 4),
            "p95_sharpe": round(float(np.percentile(r["sharpe"], 95)), 4),
        }

    # Cost drag analysis
    gross_sharpe = summary[0]["median_sharpe"]
    print(f"\n  Gross (zero-cost) Sharpe: {gross_sharpe:.4f}")
    print(f"\n  Cost drag (Sharpe reduction from zero-cost):")
    for cost_bps in [15, 20, 30, 50]:
        drag = gross_sharpe - summary[cost_bps]["median_sharpe"]
        print(f"    {cost_bps:3d} bps: -{drag:.4f} Sharpe "
              f"({drag/gross_sharpe*100:.1f}% of gross)")

    return summary


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Cost-Optimal Timescale (VTREND + VTWIN)
# ═══════════════════════════════════════════════════════════════════════

def phase2_cost_optimal_timescale(cl, hi, lo, vo, tb, wi):
    """Does the optimal timescale shift with cost? How does VTWIN compare?"""
    print("\n" + "=" * 70)
    print("PHASE 2: COST-OPTIMAL TIMESCALE (VTREND + VTWIN)")
    print("=" * 70)
    print(f"  Costs: {COST_SWEEP} bps RT")
    print(f"  Timescales: {TIMESCALES}")

    cr, hr, lr, opr, vol, tbr = make_ratios(cl, hi, lo, cl, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]

    # results[cost][slow]["vtrend"/"vtwin"][metric][boot_idx]
    results = {}
    for cost_bps in COST_SWEEP:
        results[cost_bps] = {}
        for slow in TIMESCALES:
            results[cost_bps][slow] = {
                "vtrend": {m: np.zeros(N_BOOT) for m in mkeys},
                "vtwin": {m: np.zeros(N_BOOT) for m in mkeys},
            }

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

        for slow in TIMESCALES:
            fast = max(5, slow // 4)
            ef = _ema(c, fast)
            es = _ema(c, slow)
            hh = _highest_high(h, slow)

            for cost_bps in COST_SWEEP:
                cps = cost_bps / 20_000.0

                r_vt = sim_vtrend(c, ef, es, at, vd, wi, cps)
                r_tw = sim_vtwin(c, ef, es, at, vd, hh, wi, cps)

                for m in mkeys:
                    results[cost_bps][slow]["vtrend"][m][b] = r_vt[m]
                    results[cost_bps][slow]["vtwin"][m][b] = r_tw[m]

    el = time.time() - t0
    total_sims = N_BOOT * len(TIMESCALES) * len(COST_SWEEP) * 2
    print(f"\n  Done: {el:.1f}s ({total_sims} sims, {total_sims/el:.0f} sims/sec)")

    # Analyze: find optimal timescale at each cost
    summary = {}
    for cost_bps in COST_SWEEP:
        print(f"\n  --- Cost: {cost_bps} bps RT ---")
        print(f"  {'N':>5s}  {'VT Sh':>7s} {'VT CAGR':>8s} {'VT MDD':>7s}  "
              f"{'TW Sh':>7s} {'TW CAGR':>8s} {'TW MDD':>7s}  "
              f"{'P(TW Sh>)':>10s} {'P(TW MDD<)':>11s}")
        print("  " + "-" * 90)

        cost_summary = {}
        best_vt_sh = -999; best_vt_n = 0
        best_tw_sh = -999; best_tw_n = 0

        for slow in TIMESCALES:
            r_vt = results[cost_bps][slow]["vtrend"]
            r_tw = results[cost_bps][slow]["vtwin"]

            vt_sh = np.median(r_vt["sharpe"])
            vt_cagr = np.median(r_vt["cagr"])
            vt_mdd = np.median(r_vt["mdd"])
            tw_sh = np.median(r_tw["sharpe"])
            tw_cagr = np.median(r_tw["cagr"])
            tw_mdd = np.median(r_tw["mdd"])

            # Paired comparison
            d_sh = r_tw["sharpe"] - r_vt["sharpe"]
            d_mdd = r_vt["mdd"] - r_tw["mdd"]
            p_sh = np.mean(d_sh > 0)
            p_mdd = np.mean(d_mdd > 0)

            sh_sig = " ***" if p_sh > 0.975 else " *" if p_sh > 0.95 else ""
            mdd_sig = " ***" if p_mdd > 0.975 else " *" if p_mdd > 0.95 else ""

            print(f"  {slow:5d}  {vt_sh:+6.3f} {vt_cagr:+7.1f}% {vt_mdd:6.1f}%  "
                  f"{tw_sh:+6.3f} {tw_cagr:+7.1f}% {tw_mdd:6.1f}%  "
                  f"{p_sh*100:9.1f}%{sh_sig} {p_mdd*100:10.1f}%{mdd_sig}")

            if vt_sh > best_vt_sh: best_vt_sh = vt_sh; best_vt_n = slow
            if tw_sh > best_tw_sh: best_tw_sh = tw_sh; best_tw_n = slow

            cost_summary[slow] = {
                "vtrend_sharpe": round(vt_sh, 4),
                "vtrend_cagr": round(vt_cagr, 3),
                "vtrend_mdd": round(vt_mdd, 2),
                "vtwin_sharpe": round(tw_sh, 4),
                "vtwin_cagr": round(tw_cagr, 3),
                "vtwin_mdd": round(tw_mdd, 2),
                "p_vtwin_sharpe_better": round(p_sh, 4),
                "p_vtwin_mdd_better": round(p_mdd, 4),
                "vtrend_trades": round(float(np.median(r_vt["trades"]))),
                "vtwin_trades": round(float(np.median(r_tw["trades"]))),
            }

        print(f"\n  Best VTREND: N={best_vt_n} (Sharpe {best_vt_sh:.4f})")
        print(f"  Best VTWIN:  N={best_tw_n} (Sharpe {best_tw_sh:.4f})")

        summary[cost_bps] = {
            "results": cost_summary,
            "best_vtrend_n": best_vt_n,
            "best_vtrend_sharpe": round(best_vt_sh, 4),
            "best_vtwin_n": best_tw_n,
            "best_vtwin_sharpe": round(best_tw_sh, 4),
        }

    return summary


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Trade Quality Analysis (real data only)
# ═══════════════════════════════════════════════════════════════════════

def phase3_trade_quality(cl, hi, lo, vo, tb, wi):
    """Analyze individual trade quality on real data."""
    print("\n" + "=" * 70)
    print("PHASE 3: TRADE QUALITY ANALYSIS (REAL DATA, N=120)")
    print("=" * 70)

    slow = 120; fast = max(5, slow // 4)
    ef = _ema(cl, fast)
    es = _ema(cl, slow)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cps = COST.per_side_bps / 10_000.0
    trades = sim_vtrend_detailed(cl, ef, es, at, vd, wi, cps)

    # Filter to reporting period
    report_trades = [t for t in trades if t["in_report"]]
    n_trades = len(report_trades)

    if n_trades == 0:
        print("  No trades in reporting period!")
        return {}

    pnls = np.array([t["pnl_pct"] for t in report_trades])
    durations = np.array([t["duration"] for t in report_trades])
    gaps = np.array([t["entry_gap"] for t in report_trades])
    vdos = np.array([t["entry_vdo"] for t in report_trades])

    winners = pnls > 0
    losers = pnls < 0

    print(f"\n  Total trades: {n_trades}")
    print(f"  Win rate: {winners.sum()}/{n_trades} ({winners.mean()*100:.1f}%)")
    print(f"  Avg winner: +{pnls[winners].mean():.2f}%")
    print(f"  Avg loser:  {pnls[losers].mean():.2f}%")
    print(f"  Best trade: +{pnls.max():.2f}%")
    print(f"  Worst trade: {pnls.min():.2f}%")
    print(f"  Profit factor: {abs(pnls[winners].sum() / pnls[losers].sum()):.2f}")

    print(f"\n  Duration (bars): mean={durations.mean():.1f}, "
          f"median={np.median(durations):.0f}, "
          f"min={durations.min()}, max={durations.max()}")

    print(f"  Winner duration: mean={durations[winners].mean():.1f}")
    print(f"  Loser duration:  mean={durations[losers].mean():.1f}")

    # Exit reason breakdown
    trail_exits = sum(1 for t in report_trades if t["exit_reason"] == "trail")
    ema_exits = sum(1 for t in report_trades if t["exit_reason"] == "ema_cross")
    end_exits = sum(1 for t in report_trades if t["exit_reason"] == "end")
    print(f"\n  Exit reasons: trail={trail_exits}, ema_cross={ema_exits}, end={end_exits}")

    # PnL vs EMA gap (signal strength)
    print(f"\n  --- PnL vs EMA Gap at Entry ---")
    gap_percentiles = [0, 25, 50, 75]
    gap_thresholds = np.percentile(gaps, gap_percentiles)
    for i in range(len(gap_thresholds)):
        if i < len(gap_thresholds) - 1:
            mask = (gaps >= gap_thresholds[i]) & (gaps < gap_thresholds[i + 1])
            label = f"P{gap_percentiles[i]}-P{gap_percentiles[i+1]}"
        else:
            mask = gaps >= gap_thresholds[i]
            label = f"P{gap_percentiles[i]}+"
        if mask.sum() > 0:
            avg_pnl = pnls[mask].mean()
            wr = winners[mask].mean() * 100
            n_t = mask.sum()
            gap_range = f"[{gap_thresholds[i]:.4f}, ...]"
            print(f"    {label:8s} gap{gap_range:>20s}: "
                  f"n={n_t:3d}, WR={wr:5.1f}%, avg={avg_pnl:+6.2f}%")

    # PnL vs duration (short trades tend to be losers?)
    print(f"\n  --- PnL vs Duration ---")
    for max_d in [3, 6, 12, 24, 48]:
        mask = durations <= max_d
        if mask.sum() > 0:
            avg_pnl = pnls[mask].mean()
            wr = winners[mask].mean() * 100
            print(f"    dur≤{max_d:3d}: n={mask.sum():3d}, WR={wr:5.1f}%, avg={avg_pnl:+6.2f}%")

    # PnL vs VDO strength
    print(f"\n  --- PnL vs VDO at Entry ---")
    vdo_percentiles = [0, 33, 67]
    vdo_thresholds = np.percentile(vdos, vdo_percentiles)
    for i in range(len(vdo_thresholds)):
        if i < len(vdo_thresholds) - 1:
            mask = (vdos >= vdo_thresholds[i]) & (vdos < vdo_thresholds[i + 1])
            label = f"P{vdo_percentiles[i]}-P{vdo_percentiles[i+1]}"
        else:
            mask = vdos >= vdo_thresholds[i]
            label = f"P{vdo_percentiles[i]}+"
        if mask.sum() > 0:
            avg_pnl = pnls[mask].mean()
            wr = winners[mask].mean() * 100
            print(f"    {label:8s} VDO: n={mask.sum():3d}, "
                  f"WR={wr:5.1f}%, avg={avg_pnl:+6.2f}%")

    summary = {
        "n_trades": n_trades,
        "win_rate": round(winners.mean() * 100, 1),
        "avg_winner_pct": round(float(pnls[winners].mean()), 2),
        "avg_loser_pct": round(float(pnls[losers].mean()), 2),
        "profit_factor": round(abs(float(pnls[winners].sum() / pnls[losers].sum())), 2),
        "avg_duration": round(float(durations.mean()), 1),
        "median_duration": int(np.median(durations)),
        "short_trades_pct": round(float((durations <= 6).mean() * 100), 1),
        "avg_gap_winners": round(float(gaps[winners].mean()), 5),
        "avg_gap_losers": round(float(gaps[losers].mean()), 5),
    }

    return summary


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Signal Strength & Min Holding (bootstrap)
# ═══════════════════════════════════════════════════════════════════════

def phase4_filters(cl, hi, lo, vo, tb, wi, target_cost=15):
    """Test signal strength filter and min holding at realistic cost."""
    print("\n" + "=" * 70)
    print(f"PHASE 4: SIGNAL FILTERS (bootstrap, cost={target_cost} bps RT)")
    print("=" * 70)

    cps = target_cost / 20_000.0
    cr, hr, lr, opr, vol, tbr = make_ratios(cl, hi, lo, cl, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    slow = 120; fast = max(5, slow // 4)
    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]

    # Variants: baseline + gap filters + min hold
    gap_thresholds = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05]
    hold_periods = [0, 6, 12, 24]

    # Initialize storage
    boot_gap = {}
    for gap in gap_thresholds:
        boot_gap[gap] = {m: np.zeros(N_BOOT) for m in mkeys}

    boot_hold = {}
    for hold in hold_periods:
        boot_hold[hold] = {m: np.zeros(N_BOOT) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 500 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, o, v, t = gen_path(cr, hr, lr, opr, vol, tbr, n_trans, BLKSZ, p0, rng)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ef = _ema(c, fast)
        es = _ema(c, slow)

        # Gap filters
        for gap in gap_thresholds:
            r = sim_vtrend_gap(c, ef, es, at, vd, wi, cps, gap)
            for m in mkeys:
                boot_gap[gap][m][b] = r[m]

        # Min hold filters
        for hold in hold_periods:
            r = sim_vtrend_minhold(c, ef, es, at, vd, wi, cps, hold)
            for m in mkeys:
                boot_hold[hold][m][b] = r[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s")

    # Analyze gap filters
    print(f"\n  --- Signal Strength (EMA Gap) Filter ---")
    print(f"  {'min_gap':>8s}  {'med Sh':>7s} {'med CAGR':>9s} {'med MDD':>8s} "
          f"{'med Tr':>7s} {'P(Sh>base)':>11s} {'P(MDD<base)':>12s}")
    print("  " + "-" * 75)

    base_sh = boot_gap[0.0]["sharpe"]
    base_mdd = boot_gap[0.0]["mdd"]

    gap_summary = {}
    for gap in gap_thresholds:
        r = boot_gap[gap]
        ms = np.median(r["sharpe"])
        mc = np.median(r["cagr"])
        mm = np.median(r["mdd"])
        mt = np.median(r["trades"])

        if gap > 0:
            p_sh = np.mean(r["sharpe"] > base_sh) * 100
            p_mdd = np.mean(r["mdd"] < base_mdd) * 100
        else:
            p_sh = 50.0; p_mdd = 50.0

        sig_sh = " ***" if p_sh > 97.5 else " *" if p_sh > 95 else ""
        sig_mdd = " ***" if p_mdd > 97.5 else " *" if p_mdd > 95 else ""

        print(f"  {gap:8.3f}  {ms:+6.3f} {mc:+8.1f}% {mm:7.1f}% "
              f"{mt:6.0f} {p_sh:10.1f}%{sig_sh} {p_mdd:11.1f}%{sig_mdd}")

        gap_summary[str(gap)] = {
            "median_sharpe": round(ms, 4),
            "median_cagr": round(mc, 3),
            "median_mdd": round(mm, 2),
            "median_trades": round(mt),
            "p_sharpe_better": round(p_sh, 1),
            "p_mdd_better": round(p_mdd, 1),
        }

    # Analyze min holding
    print(f"\n  --- Minimum Holding Period ---")
    print(f"  {'min_hold':>8s}  {'med Sh':>7s} {'med CAGR':>9s} {'med MDD':>8s} "
          f"{'med Tr':>7s} {'P(Sh>base)':>11s} {'P(MDD<base)':>12s}")
    print("  " + "-" * 75)

    base_sh_h = boot_hold[0]["sharpe"]
    base_mdd_h = boot_hold[0]["mdd"]

    hold_summary = {}
    for hold in hold_periods:
        r = boot_hold[hold]
        ms = np.median(r["sharpe"])
        mc = np.median(r["cagr"])
        mm = np.median(r["mdd"])
        mt = np.median(r["trades"])

        if hold > 0:
            p_sh = np.mean(r["sharpe"] > base_sh_h) * 100
            p_mdd = np.mean(r["mdd"] < base_mdd_h) * 100
        else:
            p_sh = 50.0; p_mdd = 50.0

        sig_sh = " ***" if p_sh > 97.5 else " *" if p_sh > 95 else ""
        sig_mdd = " ***" if p_mdd > 97.5 else " *" if p_mdd > 95 else ""

        print(f"  {hold:5d} bars  {ms:+6.3f} {mc:+8.1f}% {mm:7.1f}% "
              f"{mt:6.0f} {p_sh:10.1f}%{sig_sh} {p_mdd:11.1f}%{sig_mdd}")

        hold_summary[str(hold)] = {
            "median_sharpe": round(ms, 4),
            "median_cagr": round(mc, 3),
            "median_mdd": round(mm, 2),
            "median_trades": round(mt),
            "p_sharpe_better": round(p_sh, 1),
            "p_mdd_better": round(p_mdd, 1),
        }

    return {"gap_filter": gap_summary, "min_hold": hold_summary}


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("COST & EXECUTION EFFICIENCY STUDY")
    print("=" * 70)
    print(f"  Period: {START} -> {END}   Warmup: {WARMUP}d")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"\n  Motivation: VTREND signal is proven optimal.")
    print(f"  Question: how much alpha remains after REALISTIC costs?")
    print(f"  Binance VIP0: 20 bps RT, with BNB: ~15 bps RT")
    print(f"  Current analysis uses: 50 bps RT ('harsh')")

    print("\nLoading data...")
    cl, hi, lo, op, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "study": "cost_study",
        "config": {
            "n_boot": N_BOOT, "block_size": BLKSZ, "seed": SEED,
            "trail": TRAIL, "atr_period": ATR_P,
            "start": START, "end": END, "warmup": WARMUP,
        },
    }

    # Phase 1
    output["phase1_cost_sensitivity"] = phase1_cost_sensitivity(cl, hi, lo, vo, tb, wi)

    # Phase 2
    output["phase2_cost_optimal"] = phase2_cost_optimal_timescale(cl, hi, lo, vo, tb, wi)

    # Phase 3
    output["phase3_trade_quality"] = phase3_trade_quality(cl, hi, lo, vo, tb, wi)

    # Phase 4 (at realistic 15 bps)
    output["phase4_filters"] = phase4_filters(cl, hi, lo, vo, tb, wi, target_cost=15)

    # ── Final Summary ──
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    p1 = output["phase1_cost_sensitivity"]
    print(f"\n  Gross Sharpe (0 bps):    {p1[0]['median_sharpe']:.4f}")
    print(f"  At 15 bps (BNB):         {p1[15]['median_sharpe']:.4f}")
    print(f"  At 20 bps (VIP0):        {p1[20]['median_sharpe']:.4f}")
    print(f"  At 50 bps (harsh):       {p1[50]['median_sharpe']:.4f}")

    gross_sh = p1[0]['median_sharpe']
    harsh_sh = p1[50]['median_sharpe']
    real_sh = p1[15]['median_sharpe']
    print(f"\n  Cost drag at harsh: {(gross_sh - harsh_sh):.4f} Sharpe ({(gross_sh - harsh_sh)/gross_sh*100:.1f}%)")
    print(f"  Cost drag at 15bp: {(gross_sh - real_sh):.4f} Sharpe ({(gross_sh - real_sh)/gross_sh*100:.1f}%)")
    print(f"  Recoverable alpha: {(real_sh - harsh_sh):.4f} Sharpe (by using 15 vs 50 bps)")

    p2 = output["phase2_cost_optimal"]
    for cost_bps in COST_SWEEP:
        c = p2[cost_bps]
        print(f"\n  At {cost_bps:3d} bps: best VTREND N={c['best_vtrend_n']} (Sh={c['best_vtrend_sharpe']:.4f}), "
              f"best VTWIN N={c['best_vtwin_n']} (Sh={c['best_vtwin_sharpe']:.4f})")

    print("=" * 70)

    outfile = outdir / "cost_study.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {outfile}")
