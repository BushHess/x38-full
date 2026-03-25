#!/usr/bin/env python3
"""E0 vs E5 Scale Fairness Audit.

Question: Is E5 (robust ATR) being compared fairly to E0 (standard ATR),
or does the robust ATR have a lower scale that makes the trailing stop
mechanically tighter — confounding the comparison?

Analysis:
  1. Reconstruct bar-level ATR_standard(14) and ATR_robust(Q90,lb=100,p=20)
  2. Report the median ratio, quantiles, time-series of ratio
  3. Compute stop distances: trail_mult × ATR at each bar
  4. Report trade count / holding period differences
  5. Re-run simulations with scale-matched E5 multipliers
  6. Determine whether the current E5 verdict is confounded
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
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants (match e5_validation.py exactly) ──────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

ANN = math.sqrt(6.0 * 365.25)

ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

OUTDIR = Path(__file__).resolve().parent


# ── Robust ATR (copied from e5_validation.py) ──────────────────────

def _robust_atr(hi, lo, cl, cap_q=0.90, cap_lb=100, period=20):
    """Robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(
        hi - lo,
        np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb : i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s : s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


# ── Simulation (from e5_validation.py, parameterized trail_mult) ───

def _sim_core(cl, ef, es, at, vd, wi, exit_atr, trail_mult):
    """Core VTREND simulation with explicit trail_mult for exit."""
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

    # Track holding periods
    hold_bars_sum = 0
    entry_bar = -1

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

        a_val = at[i]
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
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0,
                "trades": nt, "final_nav": navs_end, "avg_hold_bars": 0}

    tr_total = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr_total) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr_total > -1 else -100
    mdd = (1.0 - nav_min_ratio) * 100

    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    avg_hold = hold_bars_sum / nt if nt > 0 else 0

    return {
        "sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
        "trades": nt, "final_nav": navs_end, "avg_hold_bars": avg_hold,
    }


def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    ts_ms = np.array([b.close_time for b in h4], dtype=np.int64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, ts_ms, wi, n


def main():
    print("=" * 70)
    print("E0 vs E5 SCALE FAIRNESS AUDIT")
    print("=" * 70)

    cl, hi, lo, vo, tb, ts_ms, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n-wi} bars")

    # ── Part 1: Bar-level ATR comparison ────────────────────────────
    print("\n" + "=" * 70)
    print("PART 1: ATR SCALE COMPARISON (bar-level)")
    print("=" * 70)

    atr_std = _atr(hi, lo, cl, ATR_P)
    atr_rob = _robust_atr(hi, lo, cl)

    # Find valid range where both are non-NaN
    valid = ~np.isnan(atr_std) & ~np.isnan(atr_rob)
    valid_post_warmup = valid & (np.arange(n) >= wi)

    atr_s_v = atr_std[valid_post_warmup]
    atr_r_v = atr_rob[valid_post_warmup]

    ratio = atr_r_v / atr_s_v

    print(f"\n  ATR_standard: Wilder EMA(TR, period={ATR_P})")
    print(f"  ATR_robust:   Wilder EMA(min(TR, Q90(100)), period=20)")
    print(f"  Valid post-warmup bars: {len(ratio):,}")

    print(f"\n  ── Ratio ATR_robust / ATR_standard ──")
    print(f"  Mean:     {np.mean(ratio):.6f}")
    print(f"  Median:   {np.median(ratio):.6f}")
    print(f"  Std:      {np.std(ratio):.6f}")
    print(f"  Min:      {np.min(ratio):.6f}")
    print(f"  Max:      {np.max(ratio):.6f}")
    print(f"  P5:       {np.percentile(ratio, 5):.6f}")
    print(f"  P25:      {np.percentile(ratio, 25):.6f}")
    print(f"  P75:      {np.percentile(ratio, 75):.6f}")
    print(f"  P95:      {np.percentile(ratio, 95):.6f}")
    pct_below_1 = np.mean(ratio < 1.0) * 100
    print(f"  Pct < 1:  {pct_below_1:.1f}%")

    # Stop distance comparison
    stop_e0 = TRAIL * atr_s_v
    stop_e5 = TRAIL * atr_r_v
    stop_ratio = stop_e5 / stop_e0  # same as ratio since trail_mult is identical

    print(f"\n  ── Stop distance (trail_mult × ATR) ──")
    print(f"  E0 mean stop:  {np.mean(stop_e0):.2f} USD")
    print(f"  E5 mean stop:  {np.mean(stop_e5):.2f} USD")
    print(f"  E5/E0 ratio:   {np.mean(stop_e5)/np.mean(stop_e0):.6f}")

    # Percent difference in ATR values
    pct_diff = (atr_r_v - atr_s_v) / atr_s_v * 100
    print(f"\n  ── ATR percent difference ((rob-std)/std × 100) ──")
    print(f"  Mean:     {np.mean(pct_diff):+.2f}%")
    print(f"  Median:   {np.median(pct_diff):+.2f}%")
    print(f"  P5:       {np.percentile(pct_diff, 5):+.2f}%")
    print(f"  P95:      {np.percentile(pct_diff, 95):+.2f}%")

    # Time-varying ratio: compute per-year
    from datetime import datetime, timezone
    print(f"\n  ── Ratio by calendar year ──")
    years = {}
    for i in range(n):
        if not valid_post_warmup[i]:
            continue
        dt = datetime.fromtimestamp(ts_ms[i] / 1000, tz=timezone.utc)
        yr = dt.year
        if yr not in years:
            years[yr] = []
        years[yr].append(atr_rob[i] / atr_std[i])

    year_ratios = {}
    for yr in sorted(years.keys()):
        arr = np.array(years[yr])
        med = np.median(arr)
        year_ratios[yr] = {"median": med, "mean": float(np.mean(arr)),
                           "p25": float(np.percentile(arr, 25)),
                           "p75": float(np.percentile(arr, 75)),
                           "n": len(arr)}
        print(f"    {yr}: median={med:.4f}  mean={np.mean(arr):.4f}  "
              f"p25={np.percentile(arr, 25):.4f}  p75={np.percentile(arr, 75):.4f}  "
              f"n={len(arr)}")

    # ── Part 2: Scale-matched multiplier ────────────────────────────
    print("\n" + "=" * 70)
    print("PART 2: SCALE-MATCHED TRAIL MULTIPLIER")
    print("=" * 70)

    # To make E5's stop distance equal to E0's on average:
    # trail_e5_matched = trail_e0 × (ATR_std / ATR_rob) = 3.0 × (1 / median_ratio)
    median_ratio = float(np.median(ratio))
    mean_ratio = float(np.mean(ratio))

    matched_mult_median = TRAIL / median_ratio
    matched_mult_mean = TRAIL / mean_ratio

    print(f"\n  Current E5 trail_mult: {TRAIL:.1f}")
    print(f"  Median ratio rATR/ATR: {median_ratio:.6f}")
    print(f"  Mean ratio rATR/ATR:   {mean_ratio:.6f}")
    print(f"  Scale-matched mult (median): {matched_mult_median:.4f}")
    print(f"  Scale-matched mult (mean):   {matched_mult_mean:.4f}")
    print(f"\n  Interpretation: E5 at trail=3.0 is equivalent to E0 at "
          f"trail={3.0 * median_ratio:.4f}")
    print(f"  E5's stop is {(1 - median_ratio)*100:.1f}% tighter than E0 at same multiplier")

    # ── Part 3: Simulations across timescales ───────────────────────
    print("\n" + "=" * 70)
    print("PART 3: SIMULATION — E0 vs E5(3.0) vs E5(scale-matched)")
    print("=" * 70)

    # Use a range of matched multipliers for sensitivity
    matched_mults = [matched_mult_median, matched_mult_mean]
    matched_labels = [f"E5_m({matched_mult_median:.2f})", f"E5_m({matched_mult_mean:.2f})"]

    results_table = []

    # Also sweep a few explicit multipliers for completeness
    test_mults = [TRAIL, matched_mult_median, matched_mult_mean]
    test_labels = ["E5(3.0)", f"E5({matched_mult_median:.2f})", f"E5({matched_mult_mean:.2f})"]

    header = (f"  {'sp':>5}  {'days':>5}  "
              f"{'E0 Sh':>7}  {'E0 CAGR':>8}  {'E0 MDD':>7}  {'E0 #T':>5}  {'E0 hold':>7}  "
              f"{'E5 Sh':>7}  {'E5 CAGR':>8}  {'E5 MDD':>7}  {'E5 #T':>5}  {'E5 hold':>7}  "
              f"{'E5m Sh':>7}  {'E5m CAGR':>8}  {'E5m MDD':>7}  {'E5m #T':>5}  {'E5m hold':>7}")
    print(f"\n  E5m = scale-matched at trail={matched_mult_median:.2f}")
    print(header)
    print("  " + "-" * 150)

    per_ts_results = []

    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        days = sp * 4 / 24

        ef = _ema(cl, fp)
        es = _ema(cl, sp)
        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ratr = _robust_atr(hi, lo, cl)

        # E0: standard ATR, trail=3.0
        r_e0 = _sim_core(cl, ef, es, at, vd, wi, at, TRAIL)
        # E5: robust ATR, trail=3.0 (original)
        r_e5 = _sim_core(cl, ef, es, at, vd, wi, ratr, TRAIL)
        # E5_matched: robust ATR, trail=scale-matched (median)
        r_e5m = _sim_core(cl, ef, es, at, vd, wi, ratr, matched_mult_median)

        per_ts_results.append({
            "sp": sp, "days": days,
            "e0": r_e0, "e5": r_e5, "e5_matched": r_e5m,
        })

        print(f"  {sp:5d}  {days:5.0f}  "
              f"{r_e0['sharpe']:7.3f}  {r_e0['cagr']:+7.1f}%  {r_e0['mdd']:6.1f}%  {r_e0['trades']:5d}  {r_e0['avg_hold_bars']:6.0f}b  "
              f"{r_e5['sharpe']:7.3f}  {r_e5['cagr']:+7.1f}%  {r_e5['mdd']:6.1f}%  {r_e5['trades']:5d}  {r_e5['avg_hold_bars']:6.0f}b  "
              f"{r_e5m['sharpe']:7.3f}  {r_e5m['cagr']:+7.1f}%  {r_e5m['mdd']:6.1f}%  {r_e5m['trades']:5d}  {r_e5m['avg_hold_bars']:6.0f}b")

    # ── Part 4: Win counts ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PART 4: WIN COUNTS (real data)")
    print("=" * 70)

    for label, key_a, key_b in [
        ("E5(3.0) vs E0", "e5", "e0"),
        ("E5(matched) vs E0", "e5_matched", "e0"),
        ("E5(matched) vs E5(3.0)", "e5_matched", "e5"),
    ]:
        win_sh = sum(1 for r in per_ts_results if r[key_a]["sharpe"] > r[key_b]["sharpe"])
        win_cagr = sum(1 for r in per_ts_results if r[key_a]["cagr"] > r[key_b]["cagr"])
        win_mdd = sum(1 for r in per_ts_results if r[key_a]["mdd"] < r[key_b]["mdd"])
        win_calmar = sum(1 for r in per_ts_results if r[key_a]["calmar"] > r[key_b]["calmar"])
        win_nav = sum(1 for r in per_ts_results if r[key_a]["final_nav"] > r[key_b]["final_nav"])
        print(f"\n  {label}:")
        print(f"    Sharpe: {win_sh:2d}/16   CAGR: {win_cagr:2d}/16   "
              f"MDD: {win_mdd:2d}/16   Calmar: {win_calmar:2d}/16   NAV: {win_nav:2d}/16")

    # ── Part 5: Trade count and holding period analysis ─────────────
    print("\n" + "=" * 70)
    print("PART 5: TRADE COUNT AND HOLDING PERIOD ANALYSIS")
    print("=" * 70)

    for r in per_ts_results:
        sp = r["sp"]
        e0_t = r["e0"]["trades"]
        e5_t = r["e5"]["trades"]
        e5m_t = r["e5_matched"]["trades"]
        e0_h = r["e0"]["avg_hold_bars"]
        e5_h = r["e5"]["avg_hold_bars"]
        e5m_h = r["e5_matched"]["avg_hold_bars"]
        td_pct = (e5_t - e0_t) / e0_t * 100 if e0_t > 0 else 0
        tdm_pct = (e5m_t - e0_t) / e0_t * 100 if e0_t > 0 else 0
        print(f"  sp={sp:4d}: E0={e0_t:3d}t/{e0_h:.0f}b  "
              f"E5={e5_t:3d}t/{e5_h:.0f}b ({td_pct:+.1f}%)  "
              f"E5m={e5m_t:3d}t/{e5m_h:.0f}b ({tdm_pct:+.1f}%)")

    # ── Part 6: Sensitivity — sweep of multipliers ──────────────────
    print("\n" + "=" * 70)
    print("PART 6: E5 TRAIL MULTIPLIER SENSITIVITY SWEEP")
    print("=" * 70)

    test_trail_mults = [2.5, 3.0, matched_mult_median, matched_mult_mean, 3.5, 4.0, 4.5, 5.0]
    sp_test = 120  # canonical timescale

    fp = max(5, sp_test // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, sp_test)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    ratr = _robust_atr(hi, lo, cl)

    r_e0_ref = _sim_core(cl, ef, es, at, vd, wi, at, TRAIL)
    print(f"\n  Canonical: sp={sp_test}, E0 baseline: "
          f"Sharpe={r_e0_ref['sharpe']:.3f}  CAGR={r_e0_ref['cagr']:.1f}%  "
          f"MDD={r_e0_ref['mdd']:.1f}%  trades={r_e0_ref['trades']}")

    print(f"\n  {'trail':>6}  {'Sharpe':>7}  {'CAGR':>8}  {'MDD':>7}  {'#T':>5}  {'hold':>7}  "
          f"{'ΔSh':>7}  {'ΔCAGR':>8}  {'ΔMDD':>7}  note")
    print("  " + "-" * 90)

    sensitivity_results = []
    for tm in test_trail_mults:
        r = _sim_core(cl, ef, es, at, vd, wi, ratr, tm)
        dsh = r["sharpe"] - r_e0_ref["sharpe"]
        dcg = r["cagr"] - r_e0_ref["cagr"]
        dmdd = r_e0_ref["mdd"] - r["mdd"]  # positive = E5 better
        note = ""
        if abs(tm - matched_mult_median) < 0.01:
            note = "<- matched(median)"
        elif abs(tm - matched_mult_mean) < 0.01:
            note = "<- matched(mean)"
        elif abs(tm - TRAIL) < 0.01:
            note = "<- original"
        print(f"  {tm:6.2f}  {r['sharpe']:7.3f}  {r['cagr']:+7.1f}%  "
              f"{r['mdd']:6.1f}%  {r['trades']:5d}  {r['avg_hold_bars']:6.0f}b  "
              f"{dsh:+7.3f}  {dcg:+7.1f}%  {dmdd:+6.1f}%  {note}")
        sensitivity_results.append({
            "trail_mult": round(tm, 4), "sharpe": r["sharpe"],
            "cagr": r["cagr"], "mdd": r["mdd"],
            "trades": r["trades"], "avg_hold_bars": r["avg_hold_bars"],
            "d_sharpe_vs_e0": dsh, "d_cagr_vs_e0": dcg,
            "d_mdd_vs_e0": dmdd,
        })

    # ── Part 7: Crossover analysis — find trail_mult where E5=E0 ───
    print("\n" + "=" * 70)
    print("PART 7: CROSSOVER ANALYSIS (sp=120)")
    print("=" * 70)

    # Fine sweep to find where E5 Sharpe crosses E0 Sharpe
    fine_mults = np.arange(2.0, 6.01, 0.1)
    e5_sharpes = []
    e5_cagrs = []
    e5_mdds = []

    for tm in fine_mults:
        r = _sim_core(cl, ef, es, at, vd, wi, ratr, tm)
        e5_sharpes.append(r["sharpe"])
        e5_cagrs.append(r["cagr"])
        e5_mdds.append(r["mdd"])

    e5_sharpes = np.array(e5_sharpes)
    e5_cagrs = np.array(e5_cagrs)
    e5_mdds = np.array(e5_mdds)

    sh_ref = r_e0_ref["sharpe"]
    cagr_ref = r_e0_ref["cagr"]
    mdd_ref = r_e0_ref["mdd"]

    # Find crossover points
    sh_diff = e5_sharpes - sh_ref
    for i in range(1, len(sh_diff)):
        if sh_diff[i-1] >= 0 and sh_diff[i] < 0:
            # interpolate
            x = fine_mults[i-1] + (0 - sh_diff[i-1]) / (sh_diff[i] - sh_diff[i-1]) * 0.1
            print(f"  Sharpe crossover (E5=E0): trail ≈ {x:.2f}")
        elif sh_diff[i-1] < 0 and sh_diff[i] >= 0:
            x = fine_mults[i-1] + (0 - sh_diff[i-1]) / (sh_diff[i] - sh_diff[i-1]) * 0.1
            print(f"  Sharpe crossover (E5=E0): trail ≈ {x:.2f}")

    cagr_diff = e5_cagrs - cagr_ref
    for i in range(1, len(cagr_diff)):
        if cagr_diff[i-1] >= 0 and cagr_diff[i] < 0:
            x = fine_mults[i-1] + (0 - cagr_diff[i-1]) / (cagr_diff[i] - cagr_diff[i-1]) * 0.1
            print(f"  CAGR crossover (E5=E0):   trail ≈ {x:.2f}")
        elif cagr_diff[i-1] < 0 and cagr_diff[i] >= 0:
            x = fine_mults[i-1] + (0 - cagr_diff[i-1]) / (cagr_diff[i] - cagr_diff[i-1]) * 0.1
            print(f"  CAGR crossover (E5=E0):   trail ≈ {x:.2f}")

    mdd_diff = e5_mdds - mdd_ref
    for i in range(1, len(mdd_diff)):
        if mdd_diff[i-1] <= 0 and mdd_diff[i] > 0:
            x = fine_mults[i-1] + (0 - mdd_diff[i-1]) / (mdd_diff[i] - mdd_diff[i-1]) * 0.1
            print(f"  MDD crossover (E5=E0):    trail ≈ {x:.2f}")
        elif mdd_diff[i-1] > 0 and mdd_diff[i] <= 0:
            x = fine_mults[i-1] + (0 - mdd_diff[i-1]) / (mdd_diff[i] - mdd_diff[i-1]) * 0.1
            print(f"  MDD crossover (E5=E0):    trail ≈ {x:.2f}")

    # Find where E5 matches E0 trade count
    print(f"\n  E0 trade count at sp=120: {r_e0_ref['trades']}")
    for tm in fine_mults:
        r = _sim_core(cl, ef, es, at, vd, wi, ratr, tm)
        if abs(r["trades"] - r_e0_ref["trades"]) <= 2:
            print(f"  E5 matches E0 trade count ≈ trail={tm:.1f} "
                  f"({r['trades']} trades, Sh={r['sharpe']:.3f}, "
                  f"CAGR={r['cagr']:.1f}%, MDD={r['mdd']:.1f}%)")

    # ── Save results ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    output = {
        "atr_scale_comparison": {
            "n_valid_bars": int(len(ratio)),
            "ratio_robust_over_standard": {
                "mean": float(np.mean(ratio)),
                "median": float(np.median(ratio)),
                "std": float(np.std(ratio)),
                "min": float(np.min(ratio)),
                "max": float(np.max(ratio)),
                "p5": float(np.percentile(ratio, 5)),
                "p25": float(np.percentile(ratio, 25)),
                "p75": float(np.percentile(ratio, 75)),
                "p95": float(np.percentile(ratio, 95)),
                "pct_below_1": float(pct_below_1),
            },
            "by_year": {str(k): v for k, v in year_ratios.items()},
        },
        "scale_matched_multiplier": {
            "from_median": round(matched_mult_median, 6),
            "from_mean": round(matched_mult_mean, 6),
            "e5_effective_e0_trail": round(TRAIL * median_ratio, 6),
            "tighter_pct": round((1 - median_ratio) * 100, 2),
        },
        "per_timescale": [],
        "win_counts": {},
        "sensitivity_sp120": sensitivity_results,
    }

    for r in per_ts_results:
        output["per_timescale"].append({
            "sp": r["sp"], "days": r["days"],
            "e0": {k: round(v, 6) if isinstance(v, float) else v
                   for k, v in r["e0"].items()},
            "e5_original": {k: round(v, 6) if isinstance(v, float) else v
                            for k, v in r["e5"].items()},
            "e5_matched": {k: round(v, 6) if isinstance(v, float) else v
                           for k, v in r["e5_matched"].items()},
        })

    for label, key_a, key_b in [
        ("e5_vs_e0", "e5", "e0"),
        ("e5_matched_vs_e0", "e5_matched", "e0"),
    ]:
        output["win_counts"][label] = {
            "sharpe": sum(1 for r in per_ts_results if r[key_a]["sharpe"] > r[key_b]["sharpe"]),
            "cagr": sum(1 for r in per_ts_results if r[key_a]["cagr"] > r[key_b]["cagr"]),
            "mdd": sum(1 for r in per_ts_results if r[key_a]["mdd"] < r[key_b]["mdd"]),
            "calmar": sum(1 for r in per_ts_results if r[key_a]["calmar"] > r[key_b]["calmar"]),
            "nav": sum(1 for r in per_ts_results if r[key_a]["final_nav"] > r[key_b]["final_nav"]),
        }

    out_path = OUTDIR / "11_e0_e5_scale_fairness.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {out_path}")

    print(f"\n{'='*70}")
    print("DONE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
