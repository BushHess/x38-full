#!/usr/bin/env python3
"""Q8: Holdout delta at multiple cost levels.

Run vectorized sims for X0, X2, X6 on holdout period at cost levels
from 0 to 100 bps per side, and compute delta at each level.

Tests whether holdout delta can flip from negative to positive
at realistic cost levels (10-20 bps RT).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

HOLDOUT_START = "2024-09-17"

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
TRAIL = 3.0

TRAIL_TIGHT = 3.0
TRAIL_MID = 4.0
TRAIL_WIDE = 5.0
GAIN_TIER1 = 0.05
GAIN_TIER2 = 0.15

SLOW_PERIOD = 120

# Cost levels: per-side bps
# 0, 3.25 (=6.5 RT, half of smart), 6.5 (smart), 10, 12.5 (=25 RT),
# 15.5 (base), 20, 25 (harsh), 37.5, 50
CPS_LEVELS_BPS = [0, 3.25, 5, 6.5, 7.5, 10, 12.5, 15.5, 20, 25, 37.5, 50]

# =========================================================================
# INDICATORS
# =========================================================================

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    b = np.array([alpha]); a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out

def _atr(high, low, close, period=14):
    prev_cl = np.empty_like(close); prev_cl[0] = close[0]; prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        aw = 1.0 / period
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - aw) * seed])
            smoothed, _ = lfilter(np.array([aw]), np.array([1.0, -(1.0 - aw)]), tail, zi=zi)
            out[period - 1] = seed; out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out

def _vdo(close, high, low, volume, taker_buy, fast=12, slow=28):
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        vdr = np.zeros(n); mask = volume > 0
        vdr[mask] = (taker_buy[mask] - (volume[mask] - taker_buy[mask])) / volume[mask]
    else:
        spread = high - low; vdr = np.zeros(n); mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)

def _d1_regime_map(cl, d1_cl, d1_ct, h4_ct, d1_ema_period=21):
    n = len(cl)
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1_idx = 0; n_d1 = len(d1_cl)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_h4[i] = d1_regime[d1_idx]
    return regime_h4

# =========================================================================
# SIMS
# =========================================================================

def _sim(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, slow_period=120, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0; ep = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                if sid in ("X2", "X6"): ep = fp
            elif px:
                px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1; ep = 0.0
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if sid == "X0":
                if p < pk - TRAIL * at[i]: px = True
                elif ef[i] < es[i]: px = True
            elif sid == "X2":
                ug = (p - ep) / ep if ep > 0 else 0.0
                tm = TRAIL_TIGHT if ug < GAIN_TIER1 else (TRAIL_MID if ug < GAIN_TIER2 else TRAIL_WIDE)
                if p < pk - tm * at[i]: px = True
                elif ef[i] < es[i]: px = True
            elif sid == "X6":
                ug = (p - ep) / ep if ep > 0 else 0.0
                if ug < GAIN_TIER1: ts = pk - TRAIL_TIGHT * at[i]
                elif ug < GAIN_TIER2: ts = max(ep, pk - TRAIL_MID * at[i])
                else: ts = max(ep, pk - TRAIL_WIDE * at[i])
                if p < ts: px = True
                elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt

def _metrics(nav, start_idx, end_idx):
    """Compute metrics for nav[start_idx:end_idx]."""
    navs = nav[start_idx:end_idx]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs)
    mdd = np.max(1.0 - navs / peak) * 100
    # Score (simplified version of validation score)
    score = cagr * (1 + sharpe) - mdd
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "score": score,
            "total_return_pct": total_ret * 100, "final_nav": float(navs[-1])}

# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("=" * 90)
    print("Q8: HOLDOUT DELTA AT MULTIPLE COST LEVELS")
    print("=" * 90)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j; break

    # Find holdout start index
    from datetime import datetime
    ho_ms = int(datetime.strptime(HOLDOUT_START, "%Y-%m-%d").timestamp() * 1000)
    ho_idx = 0
    for j, b in enumerate(feed.h4_bars):
        if b.close_time >= ho_ms:
            ho_idx = j; break

    n_full = len(cl)
    print(f"  Full sample: {n_full} bars")
    print(f"  Warmup idx: {wi}")
    print(f"  Holdout start idx: {ho_idx}")
    print(f"  Holdout bars: {n_full - ho_idx}")
    print(f"  Holdout period: {HOLDOUT_START} → {END}")
    print()

    sids = ["X0", "X2", "X6"]

    # =====================================================================
    # SECTION A: Holdout metrics at each cost level
    # =====================================================================
    print("=" * 90)
    print("  SECTION A: HOLDOUT METRICS AT EACH COST LEVEL")
    print("=" * 90)
    print()

    holdout_results = {}
    full_results = {}

    for cps_bps in CPS_LEVELS_BPS:
        cps = cps_bps / 10_000.0
        rt_bps = cps_bps * 2
        holdout_results[rt_bps] = {}
        full_results[rt_bps] = {}

        for sid in sids:
            nav, nt = _sim(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                           slow_period=SLOW_PERIOD, cps=cps)
            # Holdout metrics
            hm = _metrics(nav, ho_idx, n_full)
            holdout_results[rt_bps][sid] = {**hm, "trades": nt}

            # Full sample metrics (post-warmup)
            fm = _metrics(nav, wi, n_full)
            full_results[rt_bps][sid] = {**fm, "trades": nt}

    # Print holdout results
    print(f"  {'RT bps':>8s} | {'X0 Shrp':>8s} {'X2 Shrp':>8s} {'X6 Shrp':>8s} | "
          f"{'δ X2-X0':>8s} {'δ X6-X0':>8s} | "
          f"{'X0 CAGR':>8s} {'X2 CAGR':>8s} {'X6 CAGR':>8s} | "
          f"{'δ X2':>8s} {'δ X6':>8s}")
    print("  " + "-" * 108)

    for rt_bps in sorted(holdout_results.keys()):
        hr = holdout_results[rt_bps]
        x0s = hr["X0"]["sharpe"]; x2s = hr["X2"]["sharpe"]; x6s = hr["X6"]["sharpe"]
        x0c = hr["X0"]["cagr"]; x2c = hr["X2"]["cagr"]; x6c = hr["X6"]["cagr"]
        print(f"  {rt_bps:8.1f} | {x0s:8.4f} {x2s:8.4f} {x6s:8.4f} | "
              f"{x2s - x0s:+8.4f} {x6s - x0s:+8.4f} | "
              f"{x0c:8.2f} {x2c:8.2f} {x6c:8.2f} | "
              f"{x2c - x0c:+8.2f} {x6c - x0c:+8.2f}")

    # =====================================================================
    # SECTION B: Full-sample metrics at each cost level
    # =====================================================================
    print()
    print("=" * 90)
    print("  SECTION B: FULL-SAMPLE METRICS AT EACH COST LEVEL")
    print("=" * 90)
    print()

    print(f"  {'RT bps':>8s} | {'X0 Shrp':>8s} {'X2 Shrp':>8s} {'X6 Shrp':>8s} | "
          f"{'δ X2-X0':>8s} {'δ X6-X0':>8s} | "
          f"{'X0 CAGR':>8s} {'X2 CAGR':>8s} {'X6 CAGR':>8s} | "
          f"{'δ X2':>8s} {'δ X6':>8s}")
    print("  " + "-" * 108)

    for rt_bps in sorted(full_results.keys()):
        fr = full_results[rt_bps]
        x0s = fr["X0"]["sharpe"]; x2s = fr["X2"]["sharpe"]; x6s = fr["X6"]["sharpe"]
        x0c = fr["X0"]["cagr"]; x2c = fr["X2"]["cagr"]; x6c = fr["X6"]["cagr"]
        print(f"  {rt_bps:8.1f} | {x0s:8.4f} {x2s:8.4f} {x6s:8.4f} | "
              f"{x2s - x0s:+8.4f} {x6s - x0s:+8.4f} | "
              f"{x0c:8.2f} {x2c:8.2f} {x6c:8.2f} | "
              f"{x2c - x0c:+8.2f} {x6c - x0c:+8.2f}")

    # =====================================================================
    # SECTION C: Score delta (holdout) — validation-style
    # =====================================================================
    print()
    print("=" * 90)
    print("  SECTION C: HOLDOUT SCORE DELTA AT EACH COST LEVEL")
    print("=" * 90)
    print()

    print(f"  {'RT bps':>8s} | {'X0 score':>10s} {'X2 score':>10s} {'X6 score':>10s} | "
          f"{'δ X2-X0':>10s} {'δ X6-X0':>10s} | {'X2 wins?':>9s} {'X6 wins?':>9s}")
    print("  " + "-" * 88)

    for rt_bps in sorted(holdout_results.keys()):
        hr = holdout_results[rt_bps]
        x0sc = hr["X0"]["score"]; x2sc = hr["X2"]["score"]; x6sc = hr["X6"]["score"]
        x2w = "YES" if x2sc > x0sc else "NO"
        x6w = "YES" if x6sc > x0sc else "NO"
        print(f"  {rt_bps:8.1f} | {x0sc:10.2f} {x2sc:10.2f} {x6sc:10.2f} | "
              f"{x2sc - x0sc:+10.2f} {x6sc - x0sc:+10.2f} | {x2w:>9s} {x6w:>9s}")

    # =====================================================================
    # SECTION D: MDD comparison in holdout
    # =====================================================================
    print()
    print("=" * 90)
    print("  SECTION D: HOLDOUT MDD AT EACH COST LEVEL")
    print("=" * 90)
    print()

    print(f"  {'RT bps':>8s} | {'X0 MDD%':>8s} {'X2 MDD%':>8s} {'X6 MDD%':>8s} | "
          f"{'X0 trades':>9s} {'X2 trades':>9s} {'X6 trades':>9s}")
    print("  " + "-" * 72)

    for rt_bps in sorted(holdout_results.keys()):
        hr = holdout_results[rt_bps]
        print(f"  {rt_bps:8.1f} | {hr['X0']['mdd']:8.2f} {hr['X2']['mdd']:8.2f} {hr['X6']['mdd']:8.2f} | "
              f"{hr['X0']['trades']:9d} {hr['X2']['trades']:9d} {hr['X6']['trades']:9d}")

    # =====================================================================
    # SECTION E: Crossover analysis
    # =====================================================================
    print()
    print("=" * 90)
    print("  SECTION E: CROSSOVER ANALYSIS")
    print("=" * 90)
    print()

    # Check if delta ever crosses zero
    for test_sid in ["X2", "X6"]:
        sharpe_deltas = []
        cagr_deltas = []
        score_deltas = []
        for rt_bps in sorted(holdout_results.keys()):
            hr = holdout_results[rt_bps]
            sharpe_deltas.append((rt_bps, hr[test_sid]["sharpe"] - hr["X0"]["sharpe"]))
            cagr_deltas.append((rt_bps, hr[test_sid]["cagr"] - hr["X0"]["cagr"]))
            score_deltas.append((rt_bps, hr[test_sid]["score"] - hr["X0"]["score"]))

        print(f"  {test_sid} vs X0 holdout:")
        # Find crossover point for each metric
        for metric_name, deltas in [("Sharpe", sharpe_deltas), ("CAGR", cagr_deltas), ("Score", score_deltas)]:
            crossed = False
            for i in range(1, len(deltas)):
                if deltas[i-1][1] * deltas[i][1] < 0:  # sign change
                    # Linear interpolation
                    rt1, d1 = deltas[i-1]
                    rt2, d2 = deltas[i]
                    cross_rt = rt1 + (rt2 - rt1) * (-d1) / (d2 - d1)
                    print(f"    {metric_name} delta crosses zero at ~{cross_rt:.1f} bps RT")
                    crossed = True
            if not crossed:
                direction = "always negative" if deltas[0][1] < 0 else "always positive"
                print(f"    {metric_name} delta: {direction} ({deltas[0][1]:+.4f} at {deltas[0][0]:.0f} bps "
                      f"to {deltas[-1][1]:+.4f} at {deltas[-1][0]:.0f} bps)")
        print()

    # Save results
    output = {
        "holdout_results": {str(k): v for k, v in holdout_results.items()},
        "full_results": {str(k): v for k, v in full_results.items()},
    }
    out_path = Path(__file__).parent / "holdout_cost_sweep_q8_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to {out_path}")
    print(f"\nTotal time: {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
