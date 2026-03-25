#!/usr/bin/env python3
"""Q5: Bootstrap VCBB excluding holdout period.

Compare T4 bootstrap results when:
  A) Full data (2020-01 → 2026-02) — original T4
  B) Pre-holdout only (2020-01 → 2024-09-17) — holdout excluded

Tests whether 14/16 timescale wins survive without holdout contamination.
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
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

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

SLOW_PERIODS_FULL = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
SLOW_PERIODS = [30, 60, 120, 200, 360, 720]  # 6 representative TS for speed

N_BOOT = 200
BLKSZ = 60
SEED = 42

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

def _metrics(nav, wi):
    navs = nav[wi:]
    if len(navs) < 2: return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs); mdd = np.max(1.0 - navs / peak) * 100
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}

# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("=" * 80)
    print("Q5: BOOTSTRAP VCBB — FULL vs PRE-HOLDOUT COMPARISON")
    print("=" * 80)

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
    n_pre = ho_idx

    print(f"  Full sample: {n_full} bars ({(n_full - wi) / (6*365.25):.2f} years post-warmup)")
    print(f"  Pre-holdout: {n_pre} bars ({(n_pre - wi) / (6*365.25):.2f} years post-warmup)")
    print(f"  Holdout:     {n_full - n_pre} bars ({(n_full - n_pre) / (6*365.25):.2f} years)")
    print(f"  Warmup idx:  {wi}")
    print()

    # Pre-holdout arrays
    cl_pre = cl[:n_pre]; hi_pre = hi[:n_pre]; lo_pre = lo[:n_pre]
    vo_pre = vo[:n_pre]; tb_pre = tb[:n_pre]; h4_ct_pre = h4_ct[:n_pre]

    sids = ["X0", "X2", "X6"]

    for label, cl_use, hi_use, lo_use, vo_use, tb_use, h4_ct_use, n_use in [
        ("FULL (incl holdout)", cl, hi, lo, vo, tb, h4_ct, n_full),
        ("PRE-HOLDOUT (excl)", cl_pre, hi_pre, lo_pre, vo_pre, tb_pre, h4_ct_pre, n_pre),
    ]:
        print("=" * 80)
        print(f"  BOOTSTRAP: {label}")
        print(f"  Data bars: {n_use}, post-warmup: {n_use - wi}")
        print("=" * 80)

        # Compute ratios from post-warmup data
        cr, hr, lr, vol_r, tb_r = make_ratios(
            cl_use[wi:], hi_use[wi:], lo_use[wi:], vo_use[wi:], tb_use[wi:]
        )
        vcbb = precompute_vcbb(cr, BLKSZ)
        n_trans = n_use - wi - 1
        p0 = cl_use[wi]
        rng = np.random.default_rng(SEED)

        # Generate bootstrap paths
        boot_paths = []
        for _ in range(N_BOOT):
            bcl, bhi, blo, bvo, btb = gen_path_vcbb(
                cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb
            )
            boot_paths.append((
                np.concatenate([cl_use[:wi], bcl]),
                np.concatenate([hi_use[:wi], bhi]),
                np.concatenate([lo_use[:wi], blo]),
                np.concatenate([vo_use[:wi], bvo]),
                np.concatenate([tb_use[:wi], btb]),
            ))

        results = {}
        for sid in sids:
            results[sid] = {}
            t0 = time.time()
            for sp in SLOW_PERIODS:
                sharpes = []
                for b in range(N_BOOT):
                    bcl_f, bhi_f, blo_f, bvo_f, btb_f = boot_paths[b]
                    bnav, _ = _sim(sid, bcl_f, bhi_f, blo_f, bvo_f, btb_f,
                                   wi, d1_cl, d1_ct, h4_ct_use, slow_period=sp)
                    bm = _metrics(bnav, wi)
                    sharpes.append(bm["sharpe"])
                results[sid][sp] = float(np.median(sharpes))
            elapsed = time.time() - t0
            print(f"  {sid}: {elapsed:.1f}s")

        # Compare X2 vs X0 and X6 vs X0
        for test_sid in ["X2", "X6"]:
            wins = 0
            print(f"\n  {test_sid} vs X0 Sharpe median (bootstrap):")
            print(f"  {'SP':>6s}  {'X0':>10s}  {test_sid:>10s}  {'wins?':>8s}  {'delta':>10s}")
            for sp in SLOW_PERIODS:
                x0_s = results["X0"][sp]
                xt_s = results[test_sid][sp]
                w = "YES" if xt_s > x0_s else "NO"
                if xt_s > x0_s: wins += 1
                print(f"  {sp:6d}  {x0_s:10.4f}  {xt_s:10.4f}  {w:>8s}  {xt_s - x0_s:+10.4f}")
            print(f"  → {test_sid} wins: {wins}/16")
        print()

    print(f"\nTotal time: {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
