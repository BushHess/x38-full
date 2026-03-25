#!/usr/bin/env python3
"""Timescale Robustness & VDO Contribution Test.

Q1: Is alpha from trend-following in general, or specifically slow_period=120?
Q2: Does VDO consistently add alpha across timescales?

Method:
  - 16 timescales × 2 variants (with/without VDO) × 2000 bootstrap paths
  - Same seed=42, same gen_path as all prior work
  - f=1.0 (binary) since Sharpe is invariant to sizing
  - Harsh cost (50 bps RT)

Goal: prove a *robust region* exists, not find the optimal timescale.
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

ANN = math.sqrt(6.0 * 365.25)

# Fixed VTREND structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

# Timescale grid (H4 bars)
SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

# VDO thresholds
VDO_ON  = 0.0     # standard VTREND: VDO > 0 required
VDO_OFF = -1e9    # disabled: always passes


# ═══════════════════════════════════════════════════════════════════
# Data loading & path generation
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
# Fast VTREND simulation
# ═══════════════════════════════════════════════════════════════════

def sim_fast(cl, ef, es, at, vd, wi, vdo_thr):
    """VTREND binary sim (f=1.0). Returns metrics dict.

    Parameters
    ----------
    cl : close prices
    ef, es : EMA fast/slow (pre-computed)
    at : ATR (pre-computed, may have NaN for first ATR_P-1 bars)
    vd : VDO (pre-computed)
    wi : warmup index
    vdo_thr : VDO entry threshold (0.0 = on, -1e9 = off)
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
    nav_min_ratio = 1.0  # for MDD
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

    for i in range(n):
        p = cl[i]

        # Fill pending
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
                # Incremental return
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
            if ef[i] > es[i] and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    # Metrics from incremental stats
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
# Real data analysis
# ═══════════════════════════════════════════════════════════════════

def run_real_data(cl, hi, lo, vo, tb, wi):
    """Sweep timescales on real data, with and without VDO."""
    print("\n" + "=" * 70)
    print("REAL DATA: TIMESCALE SWEEP")
    print("=" * 70)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    print(f"\n  {'slow':>5s}  {'fast':>4s}  {'days':>5s}  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sharpe':>7s} {'Calmar':>7s} {'Tr':>4s}  |  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sharpe':>7s} {'Calmar':>7s} {'Tr':>4s}")
    print(f"  {'':>5s}  {'':>4s}  {'':>5s}  "
          f"{'--- WITH VDO ---':^34s}  |  {'--- NO VDO ---':^34s}")
    print("  " + "-" * 90)

    results = {}
    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        days = sp * 4 / 24

        ef = _ema(cl, fp)
        es = _ema(cl, sp)

        r_on  = sim_fast(cl, ef, es, at, vd, wi, VDO_ON)
        r_off = sim_fast(cl, ef, es, at, vd, wi, VDO_OFF)

        results[sp] = {"with_vdo": r_on, "no_vdo": r_off}

        print(f"  {sp:5d}  {fp:4d}  {days:5.1f}  "
              f"{r_on['cagr']:+6.1f}% {r_on['mdd']:5.1f}% {r_on['sharpe']:7.3f} "
              f"{r_on['calmar']:7.3f} {r_on['trades']:4d}  |  "
              f"{r_off['cagr']:+6.1f}% {r_off['mdd']:5.1f}% {r_off['sharpe']:7.3f} "
              f"{r_off['calmar']:7.3f} {r_off['trades']:4d}")

    return results


# ═══════════════════════════════════════════════════════════════════
# Bootstrap analysis
# ═══════════════════════════════════════════════════════════════════

def run_bootstrap(cl, hi, lo, vo, tb, wi):
    """2000 bootstrap paths × 16 timescales × 2 VDO variants."""
    print("\n" + "=" * 70)
    print(f"BOOTSTRAP: {N_BOOT} PATHS × {len(SLOW_PERIODS)} TIMESCALES × 2 VDO VARIANTS")
    print("=" * 70)

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]

    # Storage: [n_boot, n_sp] for each metric and variant
    boot_on  = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_off = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        # Generate path (once per bootstrap iteration)
        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, BLKSZ, p0, rng)

        # Path-constant indicators (computed once)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        # Sweep timescales
        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            r_on  = sim_fast(c, ef, es, at, vd, wi, VDO_ON)
            r_off = sim_fast(c, ef, es, at, vd, wi, VDO_OFF)

            for m in mkeys:
                boot_on[m][b, j]  = r_on[m]
                boot_off[m][b, j] = r_off[m]

    el = time.time() - t0
    n_total = N_BOOT * n_sp * 2
    print(f"\n  Done: {el:.1f}s ({n_total} sims, {n_total / el:.0f} sims/sec)")

    return boot_on, boot_off


# ═══════════════════════════════════════════════════════════════════
# Analysis
# ═══════════════════════════════════════════════════════════════════

def analyze(boot_on, boot_off, real_results):
    """Print comprehensive analysis."""
    n_sp = len(SLOW_PERIODS)

    # ── Q1: Timescale Robustness ──────────────────────────────────

    print("\n" + "=" * 70)
    print("Q1: TIMESCALE ROBUSTNESS (EMA + ATR trail, WITH VDO)")
    print("=" * 70)

    print(f"\n  {'slow':>5s} {'days':>5s}  "
          f"{'medSh':>6s} {'p5Sh':>6s} {'p95Sh':>6s}  "
          f"{'medCAGR':>8s} {'medMDD':>7s} {'medCalm':>8s}  "
          f"{'P(C>0)':>7s} {'P(S>0)':>7s}")
    print("  " + "-" * 85)

    productive_min = None
    productive_max = None
    strong_min = None
    strong_max = None

    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        sh = boot_on["sharpe"][:, j]
        cg = boot_on["cagr"][:, j]
        md = boot_on["mdd"][:, j]
        cm = boot_on["calmar"][:, j]

        p5, med, p95 = np.percentile(sh, [5, 50, 95])
        p_cagr = np.mean(cg > 0) * 100
        p_sh   = np.mean(sh > 0) * 100

        marker = ""
        if med > 0:
            if productive_min is None:
                productive_min = sp
            productive_max = sp
            marker = " *"
        if p_cagr > 70:
            if strong_min is None:
                strong_min = sp
            strong_max = sp
            marker = " **"

        print(f"  {sp:5d} {days:5.1f}  "
              f"{med:+6.3f} {p5:+6.3f} {p95:+6.3f}  "
              f"{np.median(cg):+7.1f}% {np.median(md):6.1f}% "
              f"{np.median(cm):+7.3f}  "
              f"{p_cagr:6.1f}% {p_sh:6.1f}%{marker}")

    print("\n  Legend: * = productive (median Sharpe > 0), ** = strong (P(CAGR>0) > 70%)")

    # Width analysis
    print("\n  ROBUSTNESS WIDTH:")
    if productive_min is not None and productive_max is not None:
        width = productive_max / productive_min
        days_min = productive_min * 4 / 24
        days_max = productive_max * 4 / 24
        print(f"    Productive region: slow={productive_min}–{productive_max} "
              f"({days_min:.0f}–{days_max:.0f} days)")
        print(f"    Width ratio: {width:.1f}x")
        if width >= 3:
            print(f"    → BROAD REGION: alpha from generic trend-following")
        elif width >= 2:
            print(f"    → MODERATE region: some timescale flexibility")
        else:
            print(f"    → NARROW: parameter-specific, fragile")
    else:
        print("    No productive timescale found!")

    if strong_min is not None and strong_max is not None:
        width_s = strong_max / strong_min
        days_min_s = strong_min * 4 / 24
        days_max_s = strong_max * 4 / 24
        print(f"    Strong region:     slow={strong_min}–{strong_max} "
              f"({days_min_s:.0f}–{days_max_s:.0f} days)")
        print(f"    Width ratio: {width_s:.1f}x")

    # ── Same table for NO VDO (EMA + ATR only) ───────────────────

    print("\n" + "=" * 70)
    print("Q1b: TIMESCALE ROBUSTNESS (EMA + ATR trail, NO VDO)")
    print("=" * 70)

    print(f"\n  {'slow':>5s} {'days':>5s}  "
          f"{'medSh':>6s} {'p5Sh':>6s} {'p95Sh':>6s}  "
          f"{'medCAGR':>8s} {'medMDD':>7s} {'medCalm':>8s}  "
          f"{'P(C>0)':>7s} {'P(S>0)':>7s}")
    print("  " + "-" * 85)

    prod_nv_min = None
    prod_nv_max = None

    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        sh = boot_off["sharpe"][:, j]
        cg = boot_off["cagr"][:, j]
        md = boot_off["mdd"][:, j]
        cm = boot_off["calmar"][:, j]

        p5, med, p95 = np.percentile(sh, [5, 50, 95])
        p_cagr = np.mean(cg > 0) * 100
        p_sh   = np.mean(sh > 0) * 100

        marker = ""
        if med > 0:
            if prod_nv_min is None:
                prod_nv_min = sp
            prod_nv_max = sp
            marker = " *"

        print(f"  {sp:5d} {days:5.1f}  "
              f"{med:+6.3f} {p5:+6.3f} {p95:+6.3f}  "
              f"{np.median(cg):+7.1f}% {np.median(md):6.1f}% "
              f"{np.median(cm):+7.3f}  "
              f"{p_cagr:6.1f}% {p_sh:6.1f}%{marker}")

    if prod_nv_min is not None and prod_nv_max is not None:
        width_nv = prod_nv_max / prod_nv_min
        print(f"\n  NO-VDO productive region: slow={prod_nv_min}–{prod_nv_max} "
              f"(width {width_nv:.1f}x)")

    # ── Q2: VDO Contribution ─────────────────────────────────────

    print("\n" + "=" * 70)
    print("Q2: VDO CONTRIBUTION (paired, with VDO - no VDO)")
    print("=" * 70)

    print(f"\n  {'slow':>5s} {'days':>5s}  "
          f"{'meanΔSh':>8s} {'medΔSh':>8s}  "
          f"{'P(VDO+)':>8s}  "
          f"{'meanΔCAGR':>10s} {'meanΔMDD':>9s}")
    print("  " + "-" * 70)

    vdo_helps_count = 0

    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        d_sh = boot_on["sharpe"][:, j] - boot_off["sharpe"][:, j]
        d_cg = boot_on["cagr"][:, j]   - boot_off["cagr"][:, j]
        d_md = boot_off["mdd"][:, j]    - boot_on["mdd"][:, j]  # positive = VDO reduces MDD

        p_helps = np.mean(d_sh > 0)
        if p_helps > 0.5:
            vdo_helps_count += 1

        marker = ""
        if p_helps > 0.55:
            marker = " +"
        elif p_helps < 0.45:
            marker = " -"

        print(f"  {sp:5d} {days:5.1f}  "
              f"{d_sh.mean():+8.4f} {np.median(d_sh):+8.4f}  "
              f"{p_helps * 100:7.1f}%  "
              f"{d_cg.mean():+9.2f}% {d_md.mean():+8.2f}%{marker}")

    print(f"\n  VDO helps at {vdo_helps_count}/{n_sp} timescales (P(ΔSharpe>0) > 50%)")
    if vdo_helps_count >= n_sp * 0.75:
        print(f"  → VDO adds consistent marginal value across timescales")
    elif vdo_helps_count >= n_sp * 0.50:
        print(f"  → VDO adds value at SOME timescales, not universally")
    else:
        print(f"  → VDO does NOT consistently help — marginal/spurious")

    # ── Real vs Bootstrap Comparison ──────────────────────────────

    print("\n" + "=" * 70)
    print("REAL DATA SHARPE PERCENTILE IN BOOTSTRAP")
    print("=" * 70)
    print("  (percentile = % of bootstrap paths with lower Sharpe)\n")

    print(f"  {'slow':>5s} {'days':>5s}  "
          f"{'realSh':>7s} {'pctile':>7s}  "
          f"{'realSh_nv':>9s} {'pctile_nv':>9s}")
    print("  " + "-" * 55)

    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24
        r_on  = real_results[sp]["with_vdo"]
        r_off = real_results[sp]["no_vdo"]

        pct_on  = np.mean(boot_on["sharpe"][:, j] <= r_on["sharpe"]) * 100
        pct_off = np.mean(boot_off["sharpe"][:, j] <= r_off["sharpe"]) * 100

        flag = ""
        if pct_on > 97.5:
            flag = " !"
        elif pct_on > 95:
            flag = " ?"

        print(f"  {sp:5d} {days:5.1f}  "
              f"{r_on['sharpe']:+7.3f} {pct_on:6.1f}%  "
              f"{r_off['sharpe']:+7.3f}   {pct_off:6.1f}%{flag}")

    print("\n  Legend: ! = real > 97.5th pctile (suspect overfit), ? = > 95th")

    # ── Smoothness check ──────────────────────────────────────────

    print("\n" + "-" * 70)
    print("SMOOTHNESS: adjacent timescale Sharpe correlation")
    print("-" * 70)

    med_sharpes = [float(np.median(boot_on["sharpe"][:, j])) for j in range(n_sp)]
    if n_sp > 2:
        adj_corr = float(np.corrcoef(med_sharpes[:-1], med_sharpes[1:])[0, 1])
        print(f"  Adjacent median Sharpe correlation: r = {adj_corr:.3f}")
        if adj_corr > 0.8:
            print(f"  → SMOOTH surface (generic trend-following effect)")
        elif adj_corr > 0.5:
            print(f"  → Moderate smoothness")
        else:
            print(f"  → Erratic (parameter-sensitive, suspicious)")

    return productive_min, productive_max, strong_min, strong_max


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TIMESCALE ROBUSTNESS & VDO CONTRIBUTION TEST")
    print("=" * 70)
    print(f"  Period: {START} → {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"  Timescales: {len(SLOW_PERIODS)} ({SLOW_PERIODS[0]}–{SLOW_PERIODS[-1]} H4 bars)")
    print(f"  Total sims: {N_BOOT * len(SLOW_PERIODS) * 2:,}")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n - wi} bars")

    # Real data sweep
    real_results = run_real_data(cl, hi, lo, vo, tb, wi)

    # Bootstrap
    boot_on, boot_off = run_bootstrap(cl, hi, lo, vo, tb, wi)

    # Analysis
    p_min, p_max, s_min, s_max = analyze(boot_on, boot_off, real_results)

    # ── Save ──────────────────────────────────────────────────────

    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "config": {
            "n_boot": N_BOOT,
            "block_size": BLKSZ,
            "seed": SEED,
            "slow_periods": SLOW_PERIODS,
            "cost_rt_bps": COST.round_trip_bps,
        },
        "real_data": {},
        "bootstrap_with_vdo": {},
        "bootstrap_no_vdo": {},
        "vdo_contribution": {},
    }

    for j, sp in enumerate(SLOW_PERIODS):
        key = str(sp)

        # Real data
        output["real_data"][key] = {
            "with_vdo": {k: round(v, 4) for k, v in real_results[sp]["with_vdo"].items()},
            "no_vdo": {k: round(v, 4) for k, v in real_results[sp]["no_vdo"].items()},
        }

        # Bootstrap with VDO
        for label, store, src in [
            ("bootstrap_with_vdo", output["bootstrap_with_vdo"], boot_on),
            ("bootstrap_no_vdo",   output["bootstrap_no_vdo"],   boot_off),
        ]:
            store[key] = {}
            for m in ["cagr", "mdd", "sharpe", "calmar"]:
                a = src[m][:, j]
                p5, p50, p95 = np.percentile(a, [5, 50, 95])
                store[key][m] = {
                    "median": round(float(p50), 4),
                    "p5": round(float(p5), 4),
                    "p95": round(float(p95), 4),
                    "p_positive": round(float(np.mean(a > 0)), 4),
                }

        # VDO contribution
        d_sh = boot_on["sharpe"][:, j] - boot_off["sharpe"][:, j]
        output["vdo_contribution"][key] = {
            "mean_delta_sharpe": round(float(d_sh.mean()), 6),
            "median_delta_sharpe": round(float(np.median(d_sh)), 6),
            "p_vdo_helps": round(float(np.mean(d_sh > 0)), 4),
        }

    output["robustness"] = {
        "productive_min": p_min,
        "productive_max": p_max,
        "productive_width_ratio": round(p_max / p_min, 2) if p_min and p_max else None,
        "strong_min": s_min,
        "strong_max": s_max,
        "strong_width_ratio": round(s_max / s_min, 2) if s_min and s_max else None,
    }

    outpath = outdir / "timescale_robustness.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved → {outpath}")
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
