#!/usr/bin/env python3
"""11b — E0 vs E5: Mechanism vs Strategy-Family Decomposition.

2x2 factorial design decomposing E5 into cap and period effects:

  A0 = standard ATR(14), no cap     [baseline E0]
  A1 = standard ATR(20), no cap     [period-only effect]
  A2 = capped ATR(14), Q90 cap      [cap-only effect]
  A3 = capped ATR(20), Q90 cap      [full E5]

              | period=14 | period=20 |
  no cap      |    A0     |    A1     |
  Q90 cap     |    A2     |    A3     |

This lets us cleanly attribute:
  - A1 - A0 = period effect (14 -> 20)
  - A2 - A0 = cap effect
  - A3 - A0 = combined
  - (A3 - A2) - (A1 - A0) = interaction

Analysis:
  Part 1: Scale diagnostics (full-bar, in-trade, near-stop)
  Part 2: Mechanism comparison (scale-matched trail multipliers)
  Part 3: Family-level retuning (trail sweep 2.0–5.5 for all 4)
  Part 4: Attribution (cap vs period vs interaction)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _vdo

# ── Constants (match e5_validation.py) ──────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

ANN = math.sqrt(6.0 * 365.25)

VDO_F  = 12
VDO_S  = 28

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
TRAIL_SWEEP  = [2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75, 5.0, 5.25, 5.5]

# Robust ATR constants
CAP_Q  = 0.90
CAP_LB = 100

OUTDIR = Path(__file__).resolve().parent

VARIANTS = ["A0", "A1", "A2", "A3"]
VARIANT_DESC = {
    "A0": "ATR(14), no cap",
    "A1": "ATR(20), no cap",
    "A2": "ATR(14), Q90 cap",
    "A3": "ATR(20), Q90 cap  [= E5]",
}


# ═══════════════════════════════════════════════════════════════════
# ATR computation: 4 variants
# ═══════════════════════════════════════════════════════════════════

def compute_tr(hi, lo, cl):
    """Raw True Range array."""
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    return np.maximum(
        hi - lo,
        np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)),
    )


def compute_capped_tr(tr, cap_q=CAP_Q, cap_lb=CAP_LB):
    """Cap TR at rolling quantile. Returns capped TR (NaN before cap_lb)."""
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb : i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    return tr_cap


def wilder_ema(series, period, start_idx=0):
    """Wilder EMA starting from start_idx. NaN before convergence."""
    n = len(series)
    out = np.full(n, np.nan)
    s = start_idx
    if s + period <= n:
        # Seed: simple mean of first `period` valid values
        out[s + period - 1] = np.nanmean(series[s : s + period])
        for i in range(s + period, n):
            if not math.isnan(series[i]) and not math.isnan(out[i - 1]):
                out[i] = (out[i - 1] * (period - 1) + series[i]) / period
    return out


def compute_atr_variants(hi, lo, cl):
    """Return dict of 4 ATR variant arrays: A0, A1, A2, A3."""
    tr = compute_tr(hi, lo, cl)
    tr_cap = compute_capped_tr(tr)

    return {
        "A0": wilder_ema(tr,     14, start_idx=0),        # standard(14)
        "A1": wilder_ema(tr,     20, start_idx=0),        # standard(20)
        "A2": wilder_ema(tr_cap, 14, start_idx=CAP_LB),   # capped(14)
        "A3": wilder_ema(tr_cap, 20, start_idx=CAP_LB),   # capped(20) = E5
    }


# ═══════════════════════════════════════════════════════════════════
# Simulation engine (extended from 11_e0_e5_scale_fairness.py)
# ═══════════════════════════════════════════════════════════════════

def sim_vtrend(cl, ef, es, entry_atr, vd, wi, exit_atr, trail_mult):
    """VTREND sim with explicit entry_atr (for signal NaN gating) and
    exit_atr (for trailing stop). Returns metrics + bar-level arrays."""
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
    hold_bars_sum = 0
    entry_bar = -1

    # Track in-position mask for scale diagnostics
    in_pos_mask = np.zeros(n, dtype=bool)

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
                entry_bar = i
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1
                px = False
                if entry_bar >= 0:
                    hold_bars_sum += (i - entry_bar)
                    entry_bar = -1

        if inp:
            in_pos_mask[i] = True

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                nav_peak = nav
                prev_nav = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak:
                nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio:
                nav_min_ratio = ratio

        # Signal generation — gate on entry_atr (A0 always, per VTREND spec)
        a_val = entry_atr[i]
        ea_val = exit_atr[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if math.isnan(ea_val):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > 0.0:
                pe = True
        else:
            pk = max(pk, p)
            trail = pk - trail_mult * ea_val
            if p < trail:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        if entry_bar >= 0:
            hold_bars_sum += (len(cl) - entry_bar)
        navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "final_nav": navs_end, "avg_hold_bars": 0.0}, in_pos_mask

    tr_total = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr_total) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr_total > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100

    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    avg_hold = hold_bars_sum / nt if nt > 0 else 0.0

    return {
        "sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
        "trades": nt, "final_nav": navs_end, "avg_hold_bars": avg_hold,
    }, in_pos_mask


# ═══════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
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


# ═══════════════════════════════════════════════════════════════════
# Part 1: Scale Diagnostics
# ═══════════════════════════════════════════════════════════════════

def scale_diagnostics(atr_variants, wi, n, cl, in_pos_masks):
    """Compute ATR ratios relative to A0 on three bar populations."""
    print("\n" + "=" * 70)
    print("PART 1: SCALE DIAGNOSTICS — ATR RATIOS vs A0")
    print("=" * 70)

    a0 = atr_variants["A0"]

    # Three populations
    post_warmup = np.arange(n) >= wi
    all_valid = post_warmup & ~np.isnan(a0)

    # For in-trade: use A0's in_pos_mask (since entries are identical across variants)
    in_trade = all_valid & in_pos_masks["A0"]

    # Near-stop: bars where trail stop is within 50% of close
    # i.e., (peak - 3.0 * atr) / close > 0.50
    # Approximate: bars where atr / close < some threshold
    # Use: trail distance / close = 3.0 * atr / close < 0.10 (10% of price)
    near_stop = all_valid & ((3.0 * a0 / cl) < 0.10)

    populations = {
        "all_post_warmup": all_valid,
        "in_trade_only": in_trade,
        "near_stop_bars": near_stop,
    }

    diag = {}
    for pop_name, pop_mask in populations.items():
        diag[pop_name] = {"n_bars": int(np.sum(pop_mask))}
        for v in ["A1", "A2", "A3"]:
            av = atr_variants[v]
            # Further restrict to bars where this variant is also valid
            both_valid = pop_mask & ~np.isnan(av)
            n_valid = int(np.sum(both_valid))
            if n_valid == 0:
                diag[pop_name][v] = {"n": 0, "note": "no valid bars"}
                continue
            ratio = av[both_valid] / a0[both_valid]
            stats = {
                "n": n_valid,
                "mean": float(np.mean(ratio)),
                "median": float(np.median(ratio)),
                "std": float(np.std(ratio)),
                "p5": float(np.percentile(ratio, 5)),
                "p25": float(np.percentile(ratio, 25)),
                "p75": float(np.percentile(ratio, 75)),
                "p95": float(np.percentile(ratio, 95)),
                "pct_below_1": float(np.mean(ratio < 1.0) * 100),
            }
            diag[pop_name][v] = stats

        # Print table
        print(f"\n  Population: {pop_name} ({diag[pop_name]['n_bars']:,} bars)")
        print(f"  {'variant':>8}  {'median':>8}  {'mean':>8}  {'std':>8}  "
              f"{'p5':>8}  {'p95':>8}  {'%<1':>6}  {'n':>6}")
        print(f"  " + "-" * 75)
        for v in ["A1", "A2", "A3"]:
            s = diag[pop_name][v]
            if s.get("n", 0) == 0:
                print(f"  {v:>8}  {'n/a':>8}")
                continue
            print(f"  {v:>8}  {s['median']:8.4f}  {s['mean']:8.4f}  {s['std']:8.4f}  "
                  f"{s['p5']:8.4f}  {s['p95']:8.4f}  {s['pct_below_1']:5.1f}%  {s['n']:6d}")

    return diag


# ═══════════════════════════════════════════════════════════════════
# Part 2: Mechanism Comparison (scale-matched)
# ═══════════════════════════════════════════════════════════════════

def mechanism_comparison(cl, hi, lo, vo, tb, wi, atr_variants, in_pos_masks):
    """Scale-matched trail comparison across 16 timescales."""
    print("\n" + "=" * 70)
    print("PART 2: MECHANISM COMPARISON — SCALE-MATCHED TRAIL MULTIPLIERS")
    print("=" * 70)

    a0 = atr_variants["A0"]

    # Compute 3 types of matched multipliers for each variant
    matched = {}
    for v in ["A1", "A2", "A3"]:
        av = atr_variants[v]
        post_warmup = (np.arange(len(a0)) >= wi) & ~np.isnan(a0) & ~np.isnan(av)
        in_trade = post_warmup & in_pos_masks["A0"]

        all_ratio = av[post_warmup] / a0[post_warmup]
        trade_ratio = av[in_trade] / a0[in_trade] if np.sum(in_trade) > 0 else all_ratio

        matched[v] = {
            "median": 3.0 / float(np.median(all_ratio)),
            "mean": 3.0 / float(np.mean(all_ratio)),
            "in_trade_median": 3.0 / float(np.median(trade_ratio)),
        }
        print(f"\n  {v} ({VARIANT_DESC[v]}):")
        print(f"    Full-bar median ratio:     {np.median(all_ratio):.6f}  -> matched trail = {matched[v]['median']:.4f}")
        print(f"    Full-bar mean ratio:        {np.mean(all_ratio):.6f}  -> matched trail = {matched[v]['mean']:.4f}")
        print(f"    In-trade median ratio:      {np.median(trade_ratio):.6f}  -> matched trail = {matched[v]['in_trade_median']:.4f}")

    # Run mechanism comparison at all 16 timescales
    print(f"\n  ── Scale-matched comparison (median-matched) ──")
    print(f"  Using: A0 trail=3.0, others trail=matched_median")

    header = (f"  {'sp':>5}  "
              f"{'A0 Sh':>7}  {'A0 MDD':>7}  {'A0 #T':>5}  "
              f"{'A1 Sh':>7}  {'A1 MDD':>7}  {'A1 #T':>5}  "
              f"{'A2 Sh':>7}  {'A2 MDD':>7}  {'A2 #T':>5}  "
              f"{'A3 Sh':>7}  {'A3 MDD':>7}  {'A3 #T':>5}")
    print(f"\n{header}")
    print("  " + "-" * 110)

    mech_results = []
    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

        row = {"sp": sp, "days": sp * 4 / 24}
        for v in VARIANTS:
            tm = 3.0 if v == "A0" else matched[v]["median"]
            r, _ = sim_vtrend(cl, ef, es, atr_variants["A0"], vd, wi,
                              atr_variants[v], tm)
            row[v] = r
            row[f"{v}_trail"] = tm

        mech_results.append(row)
        print(f"  {sp:5d}  "
              f"{row['A0']['sharpe']:7.3f}  {row['A0']['mdd']:6.1f}%  {row['A0']['trades']:5d}  "
              f"{row['A1']['sharpe']:7.3f}  {row['A1']['mdd']:6.1f}%  {row['A1']['trades']:5d}  "
              f"{row['A2']['sharpe']:7.3f}  {row['A2']['mdd']:6.1f}%  {row['A2']['trades']:5d}  "
              f"{row['A3']['sharpe']:7.3f}  {row['A3']['mdd']:6.1f}%  {row['A3']['trades']:5d}")

    # Win counts
    print(f"\n  ── Win counts (median-matched) vs A0 ──")
    for v in ["A1", "A2", "A3"]:
        w_sh = sum(1 for r in mech_results if r[v]["sharpe"] > r["A0"]["sharpe"])
        w_cagr = sum(1 for r in mech_results if r[v]["cagr"] > r["A0"]["cagr"])
        w_mdd = sum(1 for r in mech_results if r[v]["mdd"] < r["A0"]["mdd"])
        w_cal = sum(1 for r in mech_results if r[v]["calmar"] > r["A0"]["calmar"])
        print(f"    {v} vs A0: Sharpe {w_sh:2d}/16  CAGR {w_cagr:2d}/16  MDD {w_mdd:2d}/16  Calmar {w_cal:2d}/16")

    # Also do mean-matched and in-trade-matched
    for match_type in ["mean", "in_trade_median"]:
        print(f"\n  ── Win counts ({match_type}-matched) vs A0 ──")
        alt_results = []
        for sp in SLOW_PERIODS:
            fp = max(5, sp // 4)
            ef = _ema(cl, fp)
            es = _ema(cl, sp)
            vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
            row = {"sp": sp}
            for v in VARIANTS:
                tm = 3.0 if v == "A0" else matched[v][match_type]
                r, _ = sim_vtrend(cl, ef, es, atr_variants["A0"], vd, wi,
                                  atr_variants[v], tm)
                row[v] = r
            alt_results.append(row)

        for v in ["A1", "A2", "A3"]:
            w_sh = sum(1 for r in alt_results if r[v]["sharpe"] > r["A0"]["sharpe"])
            w_cagr = sum(1 for r in alt_results if r[v]["cagr"] > r["A0"]["cagr"])
            w_mdd = sum(1 for r in alt_results if r[v]["mdd"] < r["A0"]["mdd"])
            w_cal = sum(1 for r in alt_results if r[v]["calmar"] > r["A0"]["calmar"])
            print(f"    {v} vs A0: Sharpe {w_sh:2d}/16  CAGR {w_cagr:2d}/16  MDD {w_mdd:2d}/16  Calmar {w_cal:2d}/16")

    return matched, mech_results


# ═══════════════════════════════════════════════════════════════════
# Part 3: Family-Level Retuning (trail sweep)
# ═══════════════════════════════════════════════════════════════════

def family_retuning(cl, hi, lo, vo, tb, wi, atr_variants):
    """Trail multiplier sweep for each family, evaluated fairly."""
    print("\n" + "=" * 70)
    print("PART 3: FAMILY-LEVEL RETUNING — TRAIL SWEEP 2.0–5.5")
    print("=" * 70)

    # For the canonical timescale sp=120
    sp = 120
    fp = max(5, sp // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, sp)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    print(f"\n  Canonical timescale: sp={sp}")

    sweep_results = {v: [] for v in VARIANTS}

    for v in VARIANTS:
        print(f"\n  ── {v}: {VARIANT_DESC[v]} ──")
        print(f"  {'trail':>6}  {'Sharpe':>7}  {'CAGR':>8}  {'MDD':>7}  {'Calmar':>7}  "
              f"{'#T':>5}  {'hold':>6}")
        print("  " + "-" * 60)

        for tm in TRAIL_SWEEP:
            r, _ = sim_vtrend(cl, ef, es, atr_variants["A0"], vd, wi,
                              atr_variants[v], tm)
            sweep_results[v].append({"trail": tm, **r})
            marker = " *" if abs(tm - 3.0) < 0.01 else ""
            print(f"  {tm:6.2f}  {r['sharpe']:7.3f}  {r['cagr']:+7.1f}%  "
                  f"{r['mdd']:6.1f}%  {r['calmar']:7.3f}  "
                  f"{r['trades']:5d}  {r['avg_hold_bars']:5.0f}b{marker}")

    # Find best trail for each family by each metric
    print(f"\n  ── Best trail per family per metric (sp=120) ──")
    for metric, higher_better in [("sharpe", True), ("cagr", True),
                                  ("mdd", False), ("calmar", True)]:
        print(f"\n  {metric.upper()}:")
        for v in VARIANTS:
            if higher_better:
                best = max(sweep_results[v], key=lambda x: x[metric])
            else:
                best = min(sweep_results[v], key=lambda x: x[metric])
            print(f"    {v}: trail={best['trail']:.2f}  "
                  f"{metric}={best[metric]:.3f}" + ("%" if metric in ("cagr", "mdd") else ""))

    # Multi-timescale family sweep: for each family, find the trail that
    # maximizes Sharpe across the MEDIAN of 16 timescales
    print(f"\n  ── Multi-timescale: median Sharpe across 16 sp ──")
    multi_ts = {v: {tm: [] for tm in TRAIL_SWEEP} for v in VARIANTS}

    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

        for v in VARIANTS:
            for tm in TRAIL_SWEEP:
                r, _ = sim_vtrend(cl, ef, es, atr_variants["A0"], vd, wi,
                                  atr_variants[v], tm)
                multi_ts[v][tm].append(r)

    family_best = {}
    for v in VARIANTS:
        print(f"\n  {v} — median Sharpe across 16 timescales:")
        best_trail = None
        best_med_sh = -999
        for tm in TRAIL_SWEEP:
            sharpes = [r["sharpe"] for r in multi_ts[v][tm]]
            med_sh = np.median(sharpes)
            cagrs = [r["cagr"] for r in multi_ts[v][tm]]
            med_cg = np.median(cagrs)
            mdds = [r["mdd"] for r in multi_ts[v][tm]]
            med_mdd = np.median(mdds)
            print(f"    trail={tm:5.2f}: medSh={med_sh:.4f}  "
                  f"medCAGR={med_cg:+.1f}%  medMDD={med_mdd:.1f}%")
            if med_sh > best_med_sh:
                best_med_sh = med_sh
                best_trail = tm

        family_best[v] = {"best_trail": best_trail, "best_median_sharpe": best_med_sh}
        print(f"    -> BEST: trail={best_trail:.2f}  medianSharpe={best_med_sh:.4f}")

    # Head-to-head at each family's best trail
    print(f"\n  ── Head-to-head at each family's best trail ──")
    print(f"  {'variant':>8}  {'best_trail':>10}  {'medSh':>7}  {'medCAGR':>8}  {'medMDD':>7}")
    print(f"  " + "-" * 50)

    for v in VARIANTS:
        bt = family_best[v]["best_trail"]
        sharpes = [r["sharpe"] for r in multi_ts[v][bt]]
        cagrs = [r["cagr"] for r in multi_ts[v][bt]]
        mdds = [r["mdd"] for r in multi_ts[v][bt]]
        family_best[v]["med_cagr"] = float(np.median(cagrs))
        family_best[v]["med_mdd"] = float(np.median(mdds))
        print(f"  {v:>8}  {bt:10.2f}  {np.median(sharpes):7.4f}  "
              f"{np.median(cagrs):+7.1f}%  {np.median(mdds):6.1f}%")

    return sweep_results, multi_ts, family_best


# ═══════════════════════════════════════════════════════════════════
# Part 4: Attribution (cap vs period vs interaction)
# ═══════════════════════════════════════════════════════════════════

def attribution(mech_results):
    """2x2 factorial attribution of Sharpe, CAGR, MDD effects."""
    print("\n" + "=" * 70)
    print("PART 4: ATTRIBUTION — CAP vs PERIOD vs INTERACTION")
    print("=" * 70)

    for metric in ["sharpe", "cagr", "mdd"]:
        sign = -1 if metric == "mdd" else 1  # for MDD, lower is better
        print(f"\n  ── {metric.upper()} ──")
        print(f"  {'sp':>5}  {'A0':>8}  {'A1':>8}  {'A2':>8}  {'A3':>8}  "
              f"{'period':>8}  {'cap':>8}  {'interact':>9}  {'combined':>9}")
        print("  " + "-" * 85)

        period_effects = []
        cap_effects = []
        interaction_effects = []

        for row in mech_results:
            sp = row["sp"]
            v0 = row["A0"][metric]
            v1 = row["A1"][metric]
            v2 = row["A2"][metric]
            v3 = row["A3"][metric]

            # All variants are at their scale-matched trail, so differences
            # isolate the mechanism effect
            period_eff = (v1 - v0) * sign
            cap_eff = (v2 - v0) * sign
            combined = (v3 - v0) * sign
            interaction = combined - period_eff - cap_eff

            period_effects.append(period_eff)
            cap_effects.append(cap_eff)
            interaction_effects.append(interaction)

            print(f"  {sp:5d}  {v0:8.3f}  {v1:8.3f}  {v2:8.3f}  {v3:8.3f}  "
                  f"{period_eff:+8.4f}  {cap_eff:+8.4f}  {interaction:+9.4f}  {combined:+9.4f}")

        pe = np.array(period_effects)
        ce = np.array(cap_effects)
        ie = np.array(interaction_effects)

        print(f"\n  Summary (positive = improvement):")
        print(f"    Period effect:      median={np.median(pe):+.4f}  mean={np.mean(pe):+.4f}  "
              f"wins={int(np.sum(pe > 0))}/16")
        print(f"    Cap effect:         median={np.median(ce):+.4f}  mean={np.mean(ce):+.4f}  "
              f"wins={int(np.sum(ce > 0))}/16")
        print(f"    Interaction:        median={np.median(ie):+.4f}  mean={np.mean(ie):+.4f}  "
              f"wins={int(np.sum(ie > 0))}/16")

    return


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()

    print("=" * 70)
    print("11b — E0 vs E5: MECHANISM vs STRATEGY-FAMILY DECOMPOSITION")
    print("=" * 70)
    print(f"\n  Variants:")
    for v in VARIANTS:
        print(f"    {v}: {VARIANT_DESC[v]}")

    print(f"\n  2x2 factorial:  period(14 vs 20) x cap(none vs Q90)")
    print(f"  Trail sweep:    {TRAIL_SWEEP[0]}–{TRAIL_SWEEP[-1]} in {len(TRAIL_SWEEP)} steps")
    print(f"  Timescales:     {len(SLOW_PERIODS)} ({SLOW_PERIODS[0]}–{SLOW_PERIODS[-1]})")

    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"\n  {n} H4 bars, warmup idx={wi}, trading={n-wi} bars")

    # Compute all 4 ATR variants
    atr_vars = compute_atr_variants(hi, lo, cl)

    # Quick sanity: verify A0 matches _atr(14) and A3 matches _robust_atr
    from strategies.vtrend.strategy import _atr
    atr_ref = _atr(hi, lo, cl, 14)
    post_w = np.arange(n) >= wi
    valid_both = post_w & ~np.isnan(atr_ref) & ~np.isnan(atr_vars["A0"])
    max_diff_a0 = np.max(np.abs(atr_ref[valid_both] - atr_vars["A0"][valid_both]))
    print(f"\n  Sanity: max |A0 - _atr(14)| = {max_diff_a0:.2e}")

    # Get in-position masks from A0 baseline (trail=3.0)
    sp_test = 120
    fp = max(5, sp_test // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, sp_test)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    in_pos_masks = {}
    for v in VARIANTS:
        _, mask = sim_vtrend(cl, ef, es, atr_vars["A0"], vd, wi,
                             atr_vars[v], 3.0)
        in_pos_masks[v] = mask

    # Part 1: Scale diagnostics
    scale_diag = scale_diagnostics(atr_vars, wi, n, cl, in_pos_masks)

    # Part 2: Mechanism comparison
    matched_mults, mech_results = mechanism_comparison(cl, hi, lo, vo, tb, wi, atr_vars, in_pos_masks)

    # Part 3: Family-level retuning
    sweep_sp120, multi_ts, family_best = family_retuning(cl, hi, lo, vo, tb, wi, atr_vars)

    # Part 4: Attribution
    attribution(mech_results)

    # ── Save ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    output = {
        "variant_definitions": VARIANT_DESC,
        "factorial_design": "period(14 vs 20) x cap(none vs Q90)",
        "scale_diagnostics": scale_diag,
        "matched_multipliers": matched_mults,
        "mechanism_comparison_median_matched": [],
        "family_best_trail": family_best,
        "sweep_sp120": {},
    }

    for row in mech_results:
        entry = {"sp": row["sp"], "days": row["days"]}
        for v in VARIANTS:
            entry[v] = {k: round(v2, 6) if isinstance(v2, float) else v2
                        for k, v2 in row[v].items()}
            entry[f"{v}_trail"] = round(row[f"{v}_trail"], 6)
        output["mechanism_comparison_median_matched"].append(entry)

    for v in VARIANTS:
        output["sweep_sp120"][v] = []
        for r in sweep_sp120[v]:
            output["sweep_sp120"][v].append(
                {k: round(v2, 6) if isinstance(v2, float) else v2
                 for k, v2 in r.items()})

    out_path = OUTDIR / "11b_e0_e5_mechanism_vs_family.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {out_path}")

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"DONE in {elapsed:.1f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
