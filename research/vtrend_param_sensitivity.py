#!/usr/bin/env python3
"""VTREND Parameter Sensitivity Study — From the Roots.

Re-examine ALL VTREND parameters from scratch. The "wide plateau" claim
must be verified with fine-grained sweeps, not just 16 coarse points.

Questions:
  1. slow_period: Is 120 (20d) truly on a flat plateau? Or is there finer structure?
  2. fast/slow ratio: Is 4:1 optimal? Or do 3:1, 5:1, 6:1 work better?
  3. trail_mult: Is 3.0 optimal? Fine structure in 1.0-6.0?
  4. ATR period: Is 14 (Wilder) optimal? Or 10, 20?
  5. VDO fast/slow: Are 12/28 optimal? Or is there a better MACD-like pair?
  6. Interactions: slow × trail, slow × ratio — do parameters interact?

Method:
  Phase 1: Real data 1D sweeps (each param alone, others at default)
  Phase 2: Real data 2D sweeps (slow × trail, slow × ratio)
  Phase 3: Bootstrap validation of top candidates vs default (500 paths × 16 TS)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from strategies.vtrend.strategy import _ema, _atr, _vdo
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ── Constants ─────────────────────────────────────────────────────────

DATA     = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH     = 10_000.0
CPS      = 0.0025
ANN      = math.sqrt(6.0 * 365.25)

# Defaults
DEF_SLOW  = 120
DEF_RATIO = 4      # fast = slow // ratio
DEF_TRAIL = 3.0
DEF_ATR   = 14
DEF_VDO_F = 12
DEF_VDO_S = 28
DEF_VDO_T = 0.0

N_BOOT   = 500
BLKSZ    = 60
SEED     = 42
WARMUP   = 365

START    = "2019-01-01"
END      = "2026-02-20"

SLOW_PERIODS_16 = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

OUTDIR = Path(__file__).resolve().parent / "results" / "vtrend_param_sensitivity"


# ═══════════════════════════════════════════════════════════════════════
# Data & Sim
# ═══════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars; n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i; break
    return cl, hi, lo, vo, tb, wi, n


def sim_vtrend(cl, ef, es, at, vd, wi, trail_mult, vdo_thr):
    """Generic VTREND sim with configurable trail and VDO threshold."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0; pe = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; nav_peak = nav; prev_nav = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak: nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio: nav_min_ratio = ratio
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > vdo_thr: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * a_val: px = True
            elif ef[i] < es[i]: px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": 0}
    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd,
            "calmar": calmar, "trades": nt}


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: 1D Sweeps (real data)
# ═══════════════════════════════════════════════════════════════════════

def phase1_1d_sweeps(cl, hi, lo, vo, tb, wi):
    print(f"\n{'='*90}")
    print("PHASE 1: 1D PARAMETER SWEEPS (real data)")
    print(f"{'='*90}")

    results = {}

    # ── 1A: slow_period (fine-grain, every 6 H4 bars = 1 day) ──
    print(f"\n  1A: slow_period sweep (fast = slow÷{DEF_RATIO})")
    slow_vals = list(range(18, 721, 6))  # 18 to 720 in steps of 6 (= 1 day)
    at = _atr(hi, lo, cl, DEF_ATR)
    vd = _vdo(cl, hi, lo, vo, tb, DEF_VDO_F, DEF_VDO_S)

    slow_results = []
    print(f"  {'slow':>5s}  {'days':>5s}  {'fast':>4s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  {'Trd':>4s}")
    print("  " + "-" * 55)

    for sp in slow_vals:
        fp = max(5, sp // DEF_RATIO)
        ef = _ema(cl, fp); es = _ema(cl, sp)
        r = sim_vtrend(cl, ef, es, at, vd, wi, DEF_TRAIL, DEF_VDO_T)
        slow_results.append({"slow": sp, "fast": fp, "days": round(sp * 4 / 24, 1), **r})

    # Print top-10 by Sharpe
    ranked = sorted(slow_results, key=lambda x: x["sharpe"], reverse=True)
    for r in ranked[:15]:
        print(f"  {r['slow']:5d}  {r['days']:5.1f}  {r['fast']:4d}  {r['sharpe']:+7.3f}  "
              f"{r['cagr']:+6.1f}%  {r['mdd']:5.1f}%  {r['calmar']:+7.3f}  {r['trades']:4d}")

    # Plateau analysis
    peak_sh = ranked[0]["sharpe"]
    within_5pct = [r for r in slow_results if r["sharpe"] >= peak_sh * 0.95]
    within_10pct = [r for r in slow_results if r["sharpe"] >= peak_sh * 0.90]
    within_5pct_range = (min(r["slow"] for r in within_5pct), max(r["slow"] for r in within_5pct))
    within_10pct_range = (min(r["slow"] for r in within_10pct), max(r["slow"] for r in within_10pct))

    print(f"\n  Peak Sharpe: {peak_sh:+.4f} at slow={ranked[0]['slow']} ({ranked[0]['days']}d)")
    print(f"  Within 5%:  slow={within_5pct_range[0]}-{within_5pct_range[1]} "
          f"({within_5pct_range[0]*4/24:.0f}-{within_5pct_range[1]*4/24:.0f}d, {len(within_5pct)} points)")
    print(f"  Within 10%: slow={within_10pct_range[0]}-{within_10pct_range[1]} "
          f"({within_10pct_range[0]*4/24:.0f}-{within_10pct_range[1]*4/24:.0f}d, {len(within_10pct)} points)")

    # Default comparison
    def_r = next(r for r in slow_results if r["slow"] == DEF_SLOW)
    print(f"  Default (120): {def_r['sharpe']:+.4f}  Rank: {ranked.index(def_r)+1}/{len(ranked)}")

    results["slow_period"] = {
        "all": slow_results,
        "peak": ranked[0],
        "within_5pct_range": within_5pct_range,
        "within_10pct_range": within_10pct_range,
        "default_rank": ranked.index(def_r) + 1,
    }

    # ── 1B: fast/slow ratio ──
    print(f"\n  1B: fast/slow ratio sweep (slow={DEF_SLOW})")
    ratios = [2, 3, 4, 5, 6, 8, 10, 12]
    ratio_results = []

    print(f"  {'ratio':>5s}  {'fast':>4s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  {'Trd':>4s}")
    print("  " + "-" * 50)

    for ratio in ratios:
        fp = max(5, DEF_SLOW // ratio)
        ef = _ema(cl, fp); es = _ema(cl, DEF_SLOW)
        r = sim_vtrend(cl, ef, es, at, vd, wi, DEF_TRAIL, DEF_VDO_T)
        ratio_results.append({"ratio": ratio, "fast": fp, **r})
        marker = " ← default" if ratio == DEF_RATIO else ""
        print(f"  {ratio:5d}  {fp:4d}  {r['sharpe']:+7.3f}  {r['cagr']:+6.1f}%  "
              f"{r['mdd']:5.1f}%  {r['calmar']:+7.3f}  {r['trades']:4d}{marker}")

    # Also test at other slow periods
    print(f"\n  1B-ext: ratio sweep across multiple slow periods")
    print(f"  {'slow':>5s}  {'2:1':>7s}  {'3:1':>7s}  {'4:1':>7s}  {'5:1':>7s}  {'6:1':>7s}  {'8:1':>7s}  {'best_r':>6s}")
    print("  " + "-" * 60)

    multi_ratio = {}
    for sp in [60, 84, 96, 108, 120, 144, 168, 200, 240, 300]:
        es = _ema(cl, sp)
        row = {}
        for ratio in [2, 3, 4, 5, 6, 8]:
            fp = max(5, sp // ratio)
            ef = _ema(cl, fp)
            r = sim_vtrend(cl, ef, es, at, vd, wi, DEF_TRAIL, DEF_VDO_T)
            row[ratio] = r["sharpe"]
        best_r = max(row, key=row.get)
        print(f"  {sp:5d}  {row[2]:+7.3f}  {row[3]:+7.3f}  {row[4]:+7.3f}  "
              f"{row[5]:+7.3f}  {row[6]:+7.3f}  {row[8]:+7.3f}  {best_r:6d}:1")
        multi_ratio[sp] = {"ratios": row, "best": best_r}

    results["fast_slow_ratio"] = {"at_120": ratio_results, "multi_slow": multi_ratio}

    # ── 1C: trail_mult sweep ──
    print(f"\n  1C: trail_mult sweep (slow={DEF_SLOW}, fast={DEF_SLOW//DEF_RATIO})")
    trail_vals = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0, 10.0]
    ef = _ema(cl, DEF_SLOW // DEF_RATIO); es = _ema(cl, DEF_SLOW)

    trail_results = []
    print(f"  {'trail':>5s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  {'Trd':>4s}")
    print("  " + "-" * 42)

    for tv in trail_vals:
        r = sim_vtrend(cl, ef, es, at, vd, wi, tv, DEF_VDO_T)
        trail_results.append({"trail": tv, **r})
        marker = " ← default" if tv == DEF_TRAIL else ""
        print(f"  {tv:5.1f}  {r['sharpe']:+7.3f}  {r['cagr']:+6.1f}%  {r['mdd']:5.1f}%  "
              f"{r['calmar']:+7.3f}  {r['trades']:4d}{marker}")

    # Also test trail across slow periods
    print(f"\n  1C-ext: trail_mult sweep across slow periods")
    print(f"  {'slow':>5s}  {'1.0':>7s}  {'2.0':>7s}  {'2.5':>7s}  {'3.0':>7s}  "
          f"{'3.5':>7s}  {'4.0':>7s}  {'5.0':>7s}  {'best':>5s}")
    print("  " + "-" * 65)

    multi_trail = {}
    for sp in [60, 84, 96, 108, 120, 144, 168, 200, 240, 300]:
        fp = max(5, sp // DEF_RATIO)
        ef = _ema(cl, fp); es = _ema(cl, sp)
        row = {}
        for tv in [1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
            r = sim_vtrend(cl, ef, es, at, vd, wi, tv, DEF_VDO_T)
            row[tv] = r["sharpe"]
        best_t = max(row, key=row.get)
        print(f"  {sp:5d}  {row[1.0]:+7.3f}  {row[2.0]:+7.3f}  {row[2.5]:+7.3f}  {row[3.0]:+7.3f}  "
              f"{row[3.5]:+7.3f}  {row[4.0]:+7.3f}  {row[5.0]:+7.3f}  {best_t:5.1f}")
        multi_trail[sp] = {"trails": {str(k): v for k, v in row.items()}, "best": best_t}

    results["trail_mult"] = {"at_120": trail_results, "multi_slow": multi_trail}

    # ── 1D: ATR period ──
    print(f"\n  1D: ATR period sweep")
    atr_vals = [5, 7, 10, 14, 20, 28, 40, 60]
    ef = _ema(cl, DEF_SLOW // DEF_RATIO); es = _ema(cl, DEF_SLOW)

    atr_results = []
    print(f"  {'atr_p':>5s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  {'Trd':>4s}")
    print("  " + "-" * 42)

    for ap in atr_vals:
        at_test = _atr(hi, lo, cl, ap)
        r = sim_vtrend(cl, ef, es, at_test, vd, wi, DEF_TRAIL, DEF_VDO_T)
        atr_results.append({"atr_p": ap, **r})
        marker = " ← default" if ap == DEF_ATR else ""
        print(f"  {ap:5d}  {r['sharpe']:+7.3f}  {r['cagr']:+6.1f}%  {r['mdd']:5.1f}%  "
              f"{r['calmar']:+7.3f}  {r['trades']:4d}{marker}")

    results["atr_period"] = atr_results

    # ── 1E: VDO fast/slow ──
    print(f"\n  1E: VDO fast/slow sweep")
    vdo_fast_vals = [4, 6, 8, 10, 12, 16, 20, 24]
    vdo_slow_vals = [16, 20, 24, 28, 32, 36, 40, 48, 60]
    ef = _ema(cl, DEF_SLOW // DEF_RATIO); es = _ema(cl, DEF_SLOW)

    vdo_results = []
    print(f"  {'vf':>4s}  {'vs':>4s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Trd':>4s}")
    print("  " + "-" * 40)

    best_vdo = {"sharpe": -999, "vf": 0, "vs": 0}
    for vf in vdo_fast_vals:
        for vs in vdo_slow_vals:
            if vf >= vs: continue  # fast must be < slow
            vd_test = _vdo(cl, hi, lo, vo, tb, vf, vs)
            r = sim_vtrend(cl, ef, es, at, vd_test, wi, DEF_TRAIL, DEF_VDO_T)
            vdo_results.append({"vdo_fast": vf, "vdo_slow": vs, **r})
            if r["sharpe"] > best_vdo["sharpe"]:
                best_vdo = {"sharpe": r["sharpe"], "vf": vf, "vs": vs}

    # Print top 15
    ranked_vdo = sorted(vdo_results, key=lambda x: x["sharpe"], reverse=True)
    for r in ranked_vdo[:15]:
        marker = " ← default" if r["vdo_fast"] == DEF_VDO_F and r["vdo_slow"] == DEF_VDO_S else ""
        print(f"  {r['vdo_fast']:4d}  {r['vdo_slow']:4d}  {r['sharpe']:+7.3f}  {r['cagr']:+6.1f}%  "
              f"{r['mdd']:5.1f}%  {r['trades']:4d}{marker}")

    def_vdo_r = next(r for r in vdo_results if r["vdo_fast"] == DEF_VDO_F and r["vdo_slow"] == DEF_VDO_S)
    def_vdo_rank = ranked_vdo.index(def_vdo_r) + 1
    print(f"\n  Default (12/28): Sharpe={def_vdo_r['sharpe']:+.3f}, Rank: {def_vdo_rank}/{len(ranked_vdo)}")
    print(f"  Best: {best_vdo['vf']}/{best_vdo['vs']}, Sharpe={best_vdo['sharpe']:+.3f}")

    results["vdo_params"] = {"all": vdo_results, "best": best_vdo, "default_rank": def_vdo_rank}

    # ── 1F: VDO threshold ──
    print(f"\n  1F: VDO threshold sweep")
    vdo_thr_vals = [-0.50, -0.30, -0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20, 0.30, 0.50]

    thr_results = []
    print(f"  {'thr':>6s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  {'Trd':>4s}")
    print("  " + "-" * 45)

    for thr in vdo_thr_vals:
        r = sim_vtrend(cl, ef, es, at, vd, wi, DEF_TRAIL, thr)
        thr_results.append({"vdo_thr": thr, **r})
        marker = " ← default" if thr == DEF_VDO_T else ""
        print(f"  {thr:+6.2f}  {r['sharpe']:+7.3f}  {r['cagr']:+6.1f}%  {r['mdd']:5.1f}%  "
              f"{r['calmar']:+7.3f}  {r['trades']:4d}{marker}")

    results["vdo_threshold"] = thr_results

    return results


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: 2D Sweeps (real data)
# ═══════════════════════════════════════════════════════════════════════

def phase2_2d_sweeps(cl, hi, lo, vo, tb, wi):
    print(f"\n{'='*90}")
    print("PHASE 2: 2D PARAMETER SWEEPS (real data)")
    print(f"{'='*90}")

    at = _atr(hi, lo, cl, DEF_ATR)
    vd = _vdo(cl, hi, lo, vo, tb, DEF_VDO_F, DEF_VDO_S)

    # ── 2A: slow_period × trail_mult ──
    print(f"\n  2A: slow_period × trail_mult (Sharpe heatmap)")
    slow_vals = list(range(30, 361, 6))  # 30 to 360 in steps of 6
    trail_vals = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]

    grid_st = {}  # (slow, trail) -> sharpe
    for sp in slow_vals:
        fp = max(5, sp // DEF_RATIO)
        ef = _ema(cl, fp); es = _ema(cl, sp)
        for tv in trail_vals:
            r = sim_vtrend(cl, ef, es, at, vd, wi, tv, DEF_VDO_T)
            grid_st[(sp, tv)] = r

    # Find global best
    best_st = max(grid_st, key=lambda k: grid_st[k]["sharpe"])
    print(f"  Global best: slow={best_st[0]} ({best_st[0]*4/24:.0f}d), trail={best_st[1]:.1f}")
    print(f"  Sharpe={grid_st[best_st]['sharpe']:+.4f}, CAGR={grid_st[best_st]['cagr']:+.1f}%, "
          f"MDD={grid_st[best_st]['mdd']:.1f}%")

    def_key = (DEF_SLOW, DEF_TRAIL)
    print(f"  Default (120, 3.0): Sharpe={grid_st[def_key]['sharpe']:+.4f}")
    print(f"  ΔSharpe (best - default) = {grid_st[best_st]['sharpe'] - grid_st[def_key]['sharpe']:+.4f}")

    # Print heatmap for selected trails
    print(f"\n  Sharpe heatmap (top region):")
    show_slows = list(range(60, 301, 12))
    show_trails = trail_vals
    header = f"  {'slow':>5s}  {'days':>4s}"
    for tv in show_trails:
        header += f" {tv:5.1f}"
    print(header)
    print("  " + "-" * (12 + 6 * len(show_trails)))

    for sp in show_slows:
        row = f"  {sp:5d}  {sp*4/24:4.0f}"
        for tv in show_trails:
            sh = grid_st.get((sp, tv), {}).get("sharpe", 0)
            row += f" {sh:+5.3f}"
        print(row)

    # ── 2B: slow_period × ratio ──
    print(f"\n  2B: slow_period × fast/slow ratio")
    ratio_vals = [2, 3, 4, 5, 6, 8]
    grid_sr = {}

    for sp in slow_vals:
        es = _ema(cl, sp)
        for ratio in ratio_vals:
            fp = max(5, sp // ratio)
            ef = _ema(cl, fp)
            r = sim_vtrend(cl, ef, es, at, vd, wi, DEF_TRAIL, DEF_VDO_T)
            grid_sr[(sp, ratio)] = r

    best_sr = max(grid_sr, key=lambda k: grid_sr[k]["sharpe"])
    print(f"  Global best: slow={best_sr[0]} ({best_sr[0]*4/24:.0f}d), ratio={best_sr[1]}:1 "
          f"(fast={max(5, best_sr[0]//best_sr[1])})")
    print(f"  Sharpe={grid_sr[best_sr]['sharpe']:+.4f}")

    def_key_sr = (DEF_SLOW, DEF_RATIO)
    print(f"  Default (120, 4:1): Sharpe={grid_sr[def_key_sr]['sharpe']:+.4f}")
    print(f"  ΔSharpe (best - default) = {grid_sr[best_sr]['sharpe'] - grid_sr[def_key_sr]['sharpe']:+.4f}")

    # Print heatmap
    print(f"\n  Sharpe heatmap:")
    header = f"  {'slow':>5s}  {'days':>4s}"
    for rv in ratio_vals:
        header += f"  {rv:4d}:1"
    print(header)
    print("  " + "-" * (12 + 7 * len(ratio_vals)))

    for sp in list(range(60, 301, 12)):
        row = f"  {sp:5d}  {sp*4/24:4.0f}"
        for rv in ratio_vals:
            sh = grid_sr.get((sp, rv), {}).get("sharpe", 0)
            row += f" {sh:+6.3f}"
        print(row)

    # ── Summary: top 20 configs ──
    print(f"\n  TOP 20 configurations (slow × trail, ratio=4:1):")
    all_configs = [(k, v) for k, v in grid_st.items()]
    all_configs.sort(key=lambda x: x[1]["sharpe"], reverse=True)

    print(f"  {'#':>3s}  {'slow':>5s}  {'days':>5s}  {'trail':>5s}  {'Sharpe':>7s}  "
          f"{'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  {'Trd':>4s}")
    print("  " + "-" * 60)

    top20 = []
    for idx, (k, v) in enumerate(all_configs[:20]):
        sp, tv = k
        marker = " ← DEFAULT" if sp == DEF_SLOW and tv == DEF_TRAIL else ""
        print(f"  {idx+1:3d}  {sp:5d}  {sp*4/24:5.1f}  {tv:5.1f}  {v['sharpe']:+7.3f}  "
              f"{v['cagr']:+6.1f}%  {v['mdd']:5.1f}%  {v['calmar']:+7.3f}  {v['trades']:4d}{marker}")
        top20.append({"slow": sp, "trail": tv, **v})

    return {
        "slow_trail_best": {"slow": best_st[0], "trail": best_st[1], **grid_st[best_st]},
        "slow_ratio_best": {"slow": best_sr[0], "ratio": best_sr[1], **grid_sr[best_sr]},
        "top20": top20,
    }


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Bootstrap Validation (top candidates vs default)
# ═══════════════════════════════════════════════════════════════════════

def phase3_bootstrap(cl, hi, lo, vo, tb, wi, top_configs):
    """Bootstrap 500 paths × 16 timescales for top candidates vs default."""
    print(f"\n{'='*90}")
    print(f"PHASE 3: BOOTSTRAP VALIDATION — {N_BOOT} paths × {len(SLOW_PERIODS_16)} timescales")
    print(f"{'='*90}")

    # Candidates: default + top configs that differ meaningfully
    candidates = [
        {"label": "DEFAULT", "trail": DEF_TRAIL, "ratio": DEF_RATIO,
         "atr_p": DEF_ATR, "vdo_f": DEF_VDO_F, "vdo_s": DEF_VDO_S},
    ]

    # Add top configs from Phase 2 that differ from default
    seen = set()
    seen.add((DEF_SLOW, DEF_TRAIL, DEF_RATIO))
    for cfg in top_configs[:10]:
        key = (cfg["slow"], cfg["trail"], DEF_RATIO)
        if key not in seen:
            candidates.append({
                "label": f"slow={cfg['slow']},trail={cfg['trail']}",
                "slow_override": cfg["slow"],
                "trail": cfg["trail"],
                "ratio": DEF_RATIO,
                "atr_p": DEF_ATR, "vdo_f": DEF_VDO_F, "vdo_s": DEF_VDO_S,
            })
            seen.add(key)
        if len(candidates) >= 6:
            break

    print(f"\n  Candidates:")
    for i, c in enumerate(candidates):
        print(f"    {i}: {c['label']}")

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS_16)
    n_cand = len(candidates)

    # boot_sharpe[cand_idx][boot_idx, sp_idx]
    boot_sharpe = [np.zeros((N_BOOT, n_sp)) for _ in range(n_cand)]
    boot_cagr = [np.zeros((N_BOOT, n_sp)) for _ in range(n_cand)]
    boot_mdd = [np.zeros((N_BOOT, n_sp)) for _ in range(n_cand)]

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 50 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)", flush=True)

        c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng, vcbb=vcbb_state)

        for ci, cand in enumerate(candidates):
            atr_arr = _atr(h, l, c, cand["atr_p"])
            vdo_arr = _vdo(c, h, l, v, t, cand["vdo_f"], cand["vdo_s"])

            for j, sp in enumerate(SLOW_PERIODS_16):
                # Use slow_override if present (candidate-specific slow)
                # For DEFAULT: use sp from SLOW_PERIODS_16
                # For non-default candidates: they have a FIXED slow, but we still
                # need to test across timescales to be consistent
                actual_slow = cand.get("slow_override", sp)
                fp = max(5, actual_slow // cand["ratio"])
                ef = _ema(c, fp); es = _ema(c, actual_slow)

                r = sim_vtrend(c, ef, es, atr_arr, vdo_arr, 0, cand["trail"], DEF_VDO_T)
                boot_sharpe[ci][b, j] = r["sharpe"]
                boot_cagr[ci][b, j] = r["cagr"]
                boot_mdd[ci][b, j] = r["mdd"]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({el/60:.1f} min)")

    # ── Compare each candidate vs DEFAULT ──
    print(f"\n  PAIRED COMPARISON vs DEFAULT (binomial: P>50% at how many timescales)")
    print(f"  {'Candidate':>35s}  {'Sh wins':>8s}  {'p':>10s}  {'CAGR wins':>10s}  "
          f"{'p':>10s}  {'MDD wins':>10s}  {'p':>10s}")
    print("  " + "-" * 100)

    boot_results = {}
    for ci in range(1, n_cand):
        cand = candidates[ci]
        w_sh = 0; w_cg = 0; w_md = 0

        for j in range(n_sp):
            d_sh = boot_sharpe[ci][:, j] - boot_sharpe[0][:, j]
            d_cg = boot_cagr[ci][:, j] - boot_cagr[0][:, j]
            d_md = boot_mdd[0][:, j] - boot_mdd[ci][:, j]  # positive = candidate better

            if float(np.mean(d_sh > 0)) > 0.5: w_sh += 1
            if float(np.mean(d_cg > 0)) > 0.5: w_cg += 1
            if float(np.mean(d_md > 0)) > 0.5: w_md += 1

        p_sh = binomtest(w_sh, n_sp, 0.5, alternative='greater').pvalue
        p_cg = binomtest(w_cg, n_sp, 0.5, alternative='greater').pvalue
        p_md = binomtest(w_md, n_sp, 0.5, alternative='greater').pvalue

        def verdict(p):
            return ("***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.025
                    else "~" if p < 0.05 else "")

        print(f"  {cand['label']:>35s}  {w_sh:5d}/16  {p_sh:10.6f}{verdict(p_sh):>3s}  "
              f"{w_cg:5d}/16  {p_cg:10.6f}{verdict(p_cg):>3s}  "
              f"{w_md:5d}/16  {p_md:10.6f}{verdict(p_md):>3s}")

        boot_results[cand["label"]] = {
            "sharpe": {"wins": w_sh, "p": round(p_sh, 8)},
            "cagr": {"wins": w_cg, "p": round(p_cg, 8)},
            "mdd": {"wins": w_md, "p": round(p_md, 8)},
        }

    # ── DEFAULT median stats ──
    print(f"\n  DEFAULT median stats across 16 timescales:")
    print(f"  {'sp':>5}  {'medSh':>8}  {'medCAGR':>9}  {'medMDD':>8}")
    print("  " + "-" * 35)
    for j, sp in enumerate(SLOW_PERIODS_16):
        med_sh = float(np.median(boot_sharpe[0][:, j]))
        med_cg = float(np.median(boot_cagr[0][:, j]))
        med_md = float(np.median(boot_mdd[0][:, j]))
        print(f"  {sp:5d}  {med_sh:+8.4f}  {med_cg:+8.2f}%  {med_md:7.1f}%")

    return boot_results


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("VTREND PARAMETER SENSITIVITY STUDY")
    print("=" * 90)
    print(f"  Defaults: slow={DEF_SLOW}, fast={DEF_SLOW//DEF_RATIO}, trail={DEF_TRAIL}, "
          f"ATR={DEF_ATR}, VDO={DEF_VDO_F}/{DEF_VDO_S}, VDO_thr={DEF_VDO_T}")

    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  Data: {n} H4 bars, warmup index = {wi}")

    # Phase 1
    p1 = phase1_1d_sweeps(cl, hi, lo, vo, tb, wi)

    # Phase 2
    p2 = phase2_2d_sweeps(cl, hi, lo, vo, tb, wi)

    # Phase 3: Bootstrap top candidates
    p3 = phase3_bootstrap(cl, hi, lo, vo, tb, wi, p2["top20"])

    # ── Summary ──
    print(f"\n{'='*90}")
    print("SUMMARY")
    print(f"{'='*90}")

    print(f"\n  1D Sensitivity:")
    print(f"    slow_period: peak at {p1['slow_period']['peak']['slow']} "
          f"({p1['slow_period']['peak']['days']}d), "
          f"default rank {p1['slow_period']['default_rank']}/{len(p1['slow_period']['all'])}")
    print(f"      5% plateau: {p1['slow_period']['within_5pct_range']}")
    print(f"     10% plateau: {p1['slow_period']['within_10pct_range']}")

    print(f"\n  2D Sensitivity:")
    b = p2["slow_trail_best"]
    print(f"    Best (slow×trail): slow={b['slow']} ({b['slow']*4/24:.0f}d), "
          f"trail={b['trail']}, Sharpe={b['sharpe']:+.4f}")

    print(f"\n  Bootstrap (vs DEFAULT):")
    for label, v in p3.items():
        sh_v = "***" if v["sharpe"]["p"] < 0.001 else "NS"
        print(f"    {label}: Sharpe {v['sharpe']['wins']}/16 (p={v['sharpe']['p']:.4f} {sh_v})")

    el = time.time() - t_start
    print(f"\n  Total time: {el:.0f}s ({el/60:.1f} min)")

    # Save
    OUTDIR.mkdir(parents=True, exist_ok=True)

    # Convert results for JSON (simplified)
    output = {
        "config": {
            "defaults": {"slow": DEF_SLOW, "fast": DEF_SLOW // DEF_RATIO,
                         "trail": DEF_TRAIL, "atr": DEF_ATR,
                         "vdo_f": DEF_VDO_F, "vdo_s": DEF_VDO_S, "vdo_thr": DEF_VDO_T},
            "n_boot": N_BOOT, "seed": SEED,
        },
        "phase1_slow_peak": p1["slow_period"]["peak"],
        "phase1_slow_5pct_plateau": list(p1["slow_period"]["within_5pct_range"]),
        "phase1_slow_10pct_plateau": list(p1["slow_period"]["within_10pct_range"]),
        "phase1_slow_default_rank": p1["slow_period"]["default_rank"],
        "phase1_atr": p1["atr_period"],
        "phase1_vdo_best": p1["vdo_params"]["best"],
        "phase1_vdo_default_rank": p1["vdo_params"]["default_rank"],
        "phase1_vdo_threshold": p1["vdo_threshold"],
        "phase2_best_slow_trail": p2["slow_trail_best"],
        "phase2_best_slow_ratio": p2["slow_ratio_best"],
        "phase2_top20": p2["top20"],
        "phase3_bootstrap": p3,
    }

    outfile = OUTDIR / "vtrend_param_sensitivity.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print(f"{'='*90}")
