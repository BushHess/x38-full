#!/usr/bin/env python3
"""Q9: Direct head-to-head comparison — E5+EMA1D21 vs X0 vs X2 vs X6.

Same data, same holdout, same cost levels, same metrics.
All strategies run in one script for apples-to-apples comparison.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
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

# X2/X6 adaptive trail
TRAIL_TIGHT = 3.0
TRAIL_MID = 4.0
TRAIL_WIDE = 5.0
GAIN_TIER1 = 0.05
GAIN_TIER2 = 0.15

# E5 robust ATR
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
CPS_LEVELS_BPS = [0, 6.5, 15.5, 25]  # per side: 0, smart, base, harsh

# WFO windows (24m train, 6m test, rolling)
WFO_WINDOWS = [
    ("2022-01-01", "2022-07-01"),
    ("2022-07-01", "2023-01-01"),
    ("2023-01-01", "2023-07-01"),
    ("2023-07-01", "2024-01-01"),
    ("2024-01-01", "2024-07-01"),
    ("2024-07-01", "2025-01-01"),
    ("2025-01-01", "2025-07-01"),
    ("2025-07-01", "2026-01-01"),
]

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

def _robust_atr(high, low, close, cap_q=RATR_CAP_Q, cap_lb=RATR_CAP_LB, period=RATR_PERIOD):
    prev_cl = np.empty_like(close); prev_cl[0] = close[0]; prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    if cap_lb <= n:
        windows = sliding_window_view(tr[:n], cap_lb)
        relevant = windows[:n - cap_lb]
        q_vals = np.percentile(relevant, cap_q * 100, axis=1)
        tr_slice = tr[cap_lb:n]
        tr_cap[cap_lb:n] = np.minimum(tr_slice, q_vals)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        seed = np.nanmean(tr_cap[s:s + period])
        ratr[s + period - 1] = seed
        alpha = 1.0 / period
        b_coeff = np.array([alpha])
        a_coeff = np.array([1.0, -(1.0 - alpha)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b_coeff, a_coeff, tail, zi=zi)
            ratr[s + period:] = smoothed
    return ratr

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
# SIMS — all 5 strategies
# =========================================================================

def _sim(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, slow_period=120, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)

    # ATR selection
    if sid in ("E5_EMA21", ):
        at = _robust_atr(hi, lo, cl)
    else:
        at = _atr(hi, lo, cl, ATR_P)

    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # D1 regime: all strategies except E0 use it
    has_regime = sid != "E0"
    if has_regime:
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
            regime_ok = regime_h4[i] if has_regime else True
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_ok: pe = True
        else:
            pk = max(pk, p)
            if sid in ("E0", "X0", "E5_EMA21"):
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

def _metrics(nav, start_idx, end_idx=None):
    if end_idx is None: end_idx = len(nav)
    navs = nav[start_idx:end_idx]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "trades": 0}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs)
    mdd = np.max(1.0 - navs / peak) * 100
    score = cagr * (1 + sharpe) - mdd
    pf = 0.0
    gains = rets[rets > 0]; losses = rets[rets < 0]
    if len(losses) > 0 and np.sum(np.abs(losses)) > 0:
        pf = np.sum(gains) / np.sum(np.abs(losses))
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "score": score,
            "profit_factor": pf, "final_nav": float(navs[-1])}

# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("=" * 100)
    print("Q9: DIRECT HEAD-TO-HEAD — E0, X0, E5+EMA21, X2, X6")
    print("=" * 100)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)
    h4_ts = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j; break

    from datetime import datetime
    ho_ms = int(datetime.strptime(HOLDOUT_START, "%Y-%m-%d").timestamp() * 1000)
    ho_idx = 0
    for j, b in enumerate(feed.h4_bars):
        if b.close_time >= ho_ms:
            ho_idx = j; break

    n_full = len(cl)
    print(f"  Bars: {n_full}, warmup_idx: {wi}, holdout_idx: {ho_idx}")
    print(f"  Post-warmup: {n_full - wi} bars ({(n_full-wi)/(6*365.25):.2f} years)")
    print(f"  Holdout: {n_full - ho_idx} bars ({(n_full-ho_idx)/(6*365.25):.2f} years)")
    print()

    sids = ["E0", "X0", "E5_EMA21", "X2", "X6"]
    labels = {"E0": "E0", "X0": "X0(EMA21-D1)", "E5_EMA21": "E5+EMA21D1",
              "X2": "X2", "X6": "X6"}

    def ts_to_idx(ts_str):
        ms = int(datetime.strptime(ts_str, "%Y-%m-%d").timestamp() * 1000)
        for j in range(len(h4_ts)):
            if h4_ts[j] >= ms:
                return j
        return len(h4_ts)

    # =====================================================================
    # SECTION 1: Full-sample + Holdout at 4 cost levels
    # =====================================================================
    print("=" * 100)
    print("  SECTION 1: FULL-SAMPLE + HOLDOUT (SP=120)")
    print("=" * 100)

    for cps_bps in CPS_LEVELS_BPS:
        cps = cps_bps / 10_000.0
        rt_bps = cps_bps * 2
        scenario = {0: "zero", 6.5: "smart", 15.5: "base", 25: "harsh"}.get(cps_bps, f"{rt_bps:.0f}bps")

        print(f"\n  --- {scenario} ({rt_bps:.0f} bps RT) ---")
        print(f"  {'Strategy':<16s} | {'Full Shrp':>9s} {'Full CAGR':>9s} {'Full MDD':>8s} {'Trades':>6s} | "
              f"{'HO Shrp':>8s} {'HO CAGR':>8s} {'HO MDD':>7s} {'HO Score':>8s}")
        print("  " + "-" * 100)

        for sid in sids:
            nav, nt = _sim(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
            fm = _metrics(nav, wi)
            hm = _metrics(nav, ho_idx)
            print(f"  {labels[sid]:<16s} | {fm['sharpe']:9.4f} {fm['cagr']:8.2f}% {fm['mdd']:7.2f}% {nt:6d} | "
                  f"{hm['sharpe']:8.4f} {hm['cagr']:7.2f}% {hm['mdd']:6.2f}% {hm['score']:8.2f}")

    # =====================================================================
    # SECTION 2: Timescale robustness (harsh cost)
    # =====================================================================
    print()
    print("=" * 100)
    print("  SECTION 2: TIMESCALE ROBUSTNESS (harsh, 50 bps RT)")
    print("=" * 100)
    print()

    cps_harsh = 25 / 10_000.0
    ts_results = {sid: {} for sid in sids}

    for sp in SLOW_PERIODS:
        for sid in sids:
            nav, nt = _sim(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                           slow_period=sp, cps=cps_harsh)
            fm = _metrics(nav, wi)
            ts_results[sid][sp] = fm

    # Print Sharpe comparison
    header = f"  {'SP':>6s}"
    for sid in sids:
        header += f" {labels[sid]:>13s}"
    print(header)
    print("  " + "-" * (6 + 14 * len(sids)))
    for sp in SLOW_PERIODS:
        row = f"  {sp:6d}"
        for sid in sids:
            row += f" {ts_results[sid][sp]['sharpe']:13.4f}"
        print(row)

    # H2H wins
    print()
    print("  Head-to-head Sharpe wins across 16 TS:")
    for a in sids[1:]:
        for b in [sids[0]] + [s for s in sids[1:] if s != a]:
            wins = sum(1 for sp in SLOW_PERIODS if ts_results[a][sp]["sharpe"] > ts_results[b][sp]["sharpe"])
            print(f"    {labels[a]:>13s} vs {labels[b]:<13s}: {wins}/16")

    # =====================================================================
    # SECTION 3: WFO (8 windows, harsh cost)
    # =====================================================================
    print()
    print("=" * 100)
    print("  SECTION 3: WFO (8 windows, harsh cost)")
    print("=" * 100)
    print()

    wfo_results = {sid: [] for sid in sids}
    print(f"  {'Win':>4s} {'Period':<27s}", end="")
    for sid in sids:
        print(f" {labels[sid]:>13s}", end="")
    print()
    print("  " + "-" * (33 + 14 * len(sids)))

    for w_idx, (w_start, w_end) in enumerate(WFO_WINDOWS):
        si = ts_to_idx(w_start)
        ei = ts_to_idx(w_end)
        row = f"  W{w_idx:<3d} {w_start} → {w_end}  "
        for sid in sids:
            nav, nt = _sim(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps_harsh)
            wm = _metrics(nav, si, ei)
            wfo_results[sid].append(wm)
            row += f" {wm['score']:13.2f}"
        print(row)

    # WFO deltas vs E0
    print()
    print("  WFO delta vs E0:")
    print(f"  {'Win':>4s}", end="")
    for sid in sids[1:]:
        print(f" {labels[sid]:>13s}", end="")
    print()
    print("  " + "-" * (6 + 14 * (len(sids) - 1)))
    for w_idx in range(len(WFO_WINDOWS)):
        row = f"  W{w_idx:<3d}"
        for sid in sids[1:]:
            delta = wfo_results[sid][w_idx]["score"] - wfo_results["E0"][w_idx]["score"]
            row += f" {delta:+13.2f}"
        print(row)

    # Win rates
    print()
    print("  WFO win rate (delta > 0 vs E0):")
    for sid in sids[1:]:
        wins = sum(1 for i in range(len(WFO_WINDOWS))
                   if wfo_results[sid][i]["score"] > wfo_results["E0"][i]["score"])
        print(f"    {labels[sid]:>13s}: {wins}/8 ({wins/8*100:.1f}%)")

    # Direct H2H: E5_EMA21 vs X0, X2, X6
    print()
    print("  WFO win rate (direct H2H):")
    for a, b in [("E5_EMA21", "X0"), ("E5_EMA21", "X2"), ("X0", "X2")]:
        wins = sum(1 for i in range(len(WFO_WINDOWS))
                   if wfo_results[a][i]["score"] > wfo_results[b][i]["score"])
        print(f"    {labels[a]:>13s} vs {labels[b]:<13s}: {wins}/8")

    # =====================================================================
    # SECTION 4: Holdout at harsh — direct comparison
    # =====================================================================
    print()
    print("=" * 100)
    print("  SECTION 4: HOLDOUT DIRECT H2H (harsh)")
    print("=" * 100)
    print()

    print(f"  {'Metric':<20s}", end="")
    for sid in sids:
        print(f" {labels[sid]:>13s}", end="")
    print()
    print("  " + "-" * (20 + 14 * len(sids)))

    holdout_metrics = {}
    for sid in sids:
        nav, nt = _sim(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps_harsh)
        hm = _metrics(nav, ho_idx)
        hm["trades"] = nt  # full-sample trades (holdout is subset)
        holdout_metrics[sid] = hm

    for metric in ["sharpe", "cagr", "mdd", "score", "profit_factor"]:
        row = f"  {metric:<20s}"
        vals = [holdout_metrics[sid][metric] for sid in sids]
        best = max(vals) if metric != "mdd" else min(vals)
        for sid in sids:
            v = holdout_metrics[sid][metric]
            marker = " *" if abs(v - best) < 1e-6 else "  "
            if metric in ("cagr", "mdd"):
                row += f" {v:12.2f}%"
            else:
                row += f" {v:13.4f}"
        print(row)

    # Pairwise deltas
    print()
    print("  Holdout Sharpe deltas (row - col):")
    header = f"  {'':>13s}"
    for sid in sids:
        header += f" {labels[sid]:>13s}"
    print(header)
    for sid_a in sids:
        row = f"  {labels[sid_a]:>13s}"
        for sid_b in sids:
            d = holdout_metrics[sid_a]["sharpe"] - holdout_metrics[sid_b]["sharpe"]
            row += f" {d:+13.4f}"
        print(row)

    print(f"\n  Total time: {time.time() - t_start:.1f}s")

    # Save
    out = {
        "holdout_metrics": holdout_metrics,
        "ts_results": {sid: {str(sp): v for sp, v in d.items()} for sid, d in ts_results.items()},
        "wfo_results": {sid: d for sid, d in wfo_results.items()},
    }
    out_path = Path(__file__).parent / "direct_compare_q9_results.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"  Saved to {out_path}")


if __name__ == "__main__":
    main()
