#!/usr/bin/env python3
"""Q4 Research: Holdout period bootstrap — Sharpe difference CI for X0 vs X2 vs X6.

Runs 1000 block-bootstrap resamples on holdout bar-level returns.
Reports: Sharpe CI per strategy, pairwise Sharpe diff CI, win rate.
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

HOLDOUT_START_DATE = "2024-09-17"

SLOW = 120
TRAIL_FIXED = 3.0
TRAIL_TIGHT = 3.0
TRAIL_MID = 4.0
TRAIL_WIDE = 5.0
GAIN_TIER1 = 0.05
GAIN_TIER2 = 0.15

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0

N_BOOT = 1000
BLOCK_SIZES = [21, 42, 84]  # ~3.5d, ~7d, ~14d in H4 bars
SEED = 2026

# =========================================================================
# INDICATORS (copied from benchmark.py for self-containment)
# =========================================================================

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out

def _atr(high, low, close, period=14):
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha_w = 1.0 / period
        b_arr = np.array([alpha_w])
        a_arr = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha_w) * seed])
            smoothed, _ = lfilter(b_arr, a_arr, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out

def _vdo(close, high, low, volume, taker_buy, fast=12, slow=28):
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)

def _d1_regime_map(cl, d1_cl, d1_ct, h4_ct, d1_ema_period=21):
    n = len(cl)
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_h4[i] = d1_regime[d1_idx]
    return regime_h4

# =========================================================================
# VECTORIZED SIMS
# =========================================================================

def _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    n = len(cl)
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL_FIXED * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt

def _sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    n = len(cl)
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0; ep = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p; ep = fp
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1; ep = 0.0
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            ug = (p - ep) / ep if ep > 0 else 0.0
            if ug < GAIN_TIER1: tm = TRAIL_TIGHT
            elif ug < GAIN_TIER2: tm = TRAIL_MID
            else: tm = TRAIL_WIDE
            if p < pk - tm * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt

def _sim_x6(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    n = len(cl)
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0; ep = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p; ep = fp
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1; ep = 0.0
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            ug = (p - ep) / ep if ep > 0 else 0.0
            if ug < GAIN_TIER1:
                trail_stop = pk - TRAIL_TIGHT * at[i]
            elif ug < GAIN_TIER2:
                trail_stop = max(ep, pk - TRAIL_MID * at[i])
            else:
                trail_stop = max(ep, pk - TRAIL_WIDE * at[i])
            if p < trail_stop: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt

# =========================================================================
# BOOTSTRAP ON HOLDOUT BAR RETURNS
# =========================================================================

def compute_sharpe(returns):
    """Annualized Sharpe from H4 bar returns, ddof=0."""
    if len(returns) < 2:
        return 0.0
    mu = np.mean(returns)
    std = np.std(returns, ddof=0)
    return (mu / std * ANN) if std > 1e-12 else 0.0


def block_bootstrap_sharpe(returns_dict, n_boot, block_size, rng):
    """Circular block bootstrap on bar-level returns.

    returns_dict: {strategy_id: np.array of bar returns}
    Returns: {strategy_id: np.array of bootstrapped Sharpes}
    """
    n = len(next(iter(returns_dict.values())))
    results = {sid: np.zeros(n_boot) for sid in returns_dict}

    for b in range(n_boot):
        # Generate block start indices
        n_blocks = (n + block_size - 1) // block_size
        starts = rng.integers(0, n, size=n_blocks)

        # Build resampled index array (circular)
        idx = np.concatenate([np.arange(s, s + block_size) % n for s in starts])[:n]

        for sid, rets in returns_dict.items():
            results[sid][b] = compute_sharpe(rets[idx])

    return results


def main():
    t_start = time.time()
    print("=" * 80)
    print("Q4: HOLDOUT BOOTSTRAP — Sharpe Difference CI (X0 vs X2 vs X6)")
    print(f"  Holdout: {HOLDOUT_START_DATE} → {END}")
    print(f"  Bootstrap: {N_BOOT} paths, block sizes: {BLOCK_SIZES}")
    print(f"  Cost: harsh (50 bps RT)")
    print("=" * 80)

    # Load data
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
                wi = j
                break

    # Find holdout start bar index
    from datetime import datetime
    holdout_start_ms = int(datetime.strptime(HOLDOUT_START_DATE, "%Y-%m-%d").timestamp() * 1000)
    ho_idx = 0
    for j, b in enumerate(feed.h4_bars):
        if b.close_time >= holdout_start_ms:
            ho_idx = j
            break

    n_bars_total = len(cl)
    n_bars_holdout = n_bars_total - ho_idx
    print(f"\n  Total H4 bars: {n_bars_total}")
    print(f"  Holdout starts at bar {ho_idx} ({HOLDOUT_START_DATE})")
    print(f"  Holdout bars: {n_bars_holdout} ({n_bars_holdout/6/365.25:.2f} years)")

    # Run full sims (need full history for indicator warmup)
    cps_harsh = 0.005  # 50 bps RT = 25 bps per side

    sims = {}
    for sid, sim_fn in [("X0", _sim_x0), ("X2", _sim_x2), ("X6", _sim_x6)]:
        t0 = time.time()
        nav, nt = sim_fn(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps_harsh)
        elapsed = time.time() - t0

        # Compute holdout metrics
        ho_nav = nav[ho_idx:]
        ho_rets = np.diff(ho_nav) / ho_nav[:-1]
        ho_sharpe = compute_sharpe(ho_rets)

        # CAGR
        total_ret = ho_nav[-1] / ho_nav[0] - 1.0
        yrs = len(ho_rets) / (6.0 * 365.25)
        cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0

        # MDD
        peak = np.maximum.accumulate(ho_nav)
        mdd = np.max(1.0 - ho_nav / peak) * 100

        sims[sid] = {
            "nav": nav, "ho_nav": ho_nav, "ho_rets": ho_rets,
            "sharpe": ho_sharpe, "cagr": cagr, "mdd": mdd, "trades": nt
        }

        print(f"\n  {sid}: Sharpe={ho_sharpe:.4f}  CAGR={cagr:.2f}%  MDD={mdd:.2f}%  "
              f"trades_total={nt}  ({elapsed:.2f}s)")

    # Print Sharpe differences (point estimates)
    print(f"\n  Point estimates (holdout, harsh):")
    for a, b in [("X2", "X0"), ("X6", "X0"), ("X6", "X2")]:
        d = sims[a]["sharpe"] - sims[b]["sharpe"]
        print(f"    {a} - {b}: dSharpe = {d:+.4f}")

    # Bootstrap on holdout bar returns
    returns_dict = {sid: sims[sid]["ho_rets"] for sid in ["X0", "X2", "X6"]}
    rng = np.random.default_rng(SEED)

    all_results = {}

    for blk in BLOCK_SIZES:
        print(f"\n{'='*80}")
        print(f"  BLOCK SIZE = {blk} bars (~{blk/6:.1f} days)")
        print(f"{'='*80}")

        boot_sharpes = block_bootstrap_sharpe(returns_dict, N_BOOT, blk, rng)

        # Per-strategy CI
        print(f"\n  Per-strategy Sharpe distribution ({N_BOOT} paths):")
        for sid in ["X0", "X2", "X6"]:
            s = boot_sharpes[sid]
            print(f"    {sid}: median={np.median(s):.4f}  "
                  f"mean={np.mean(s):.4f}  "
                  f"95% CI=[{np.percentile(s,2.5):.4f}, {np.percentile(s,97.5):.4f}]  "
                  f"90% CI=[{np.percentile(s,5):.4f}, {np.percentile(s,95):.4f}]")

        # Pairwise comparisons
        print(f"\n  Pairwise Sharpe difference:")
        pairs = [("X2", "X0"), ("X6", "X0"), ("X6", "X2")]
        for a, b in pairs:
            diff = boot_sharpes[a] - boot_sharpes[b]
            win_pct = np.mean(diff > 0) * 100
            print(f"    {a} - {b}:")
            print(f"      mean_delta = {np.mean(diff):+.4f}")
            print(f"      median_delta = {np.median(diff):+.4f}")
            print(f"      95% CI = [{np.percentile(diff,2.5):+.4f}, {np.percentile(diff,97.5):+.4f}]")
            print(f"      90% CI = [{np.percentile(diff,5):+.4f}, {np.percentile(diff,95):+.4f}]")
            print(f"      P({a} > {b}) = {win_pct:.1f}%  ({int(np.sum(diff > 0))}/{N_BOOT})")
            ci_crosses_zero = np.percentile(diff, 2.5) < 0 < np.percentile(diff, 97.5)
            print(f"      95% CI crosses zero: {'YES' if ci_crosses_zero else 'NO'}")

        all_results[f"block_{blk}"] = {
            "block_size": blk,
            "block_days": round(blk / 6, 1),
            "n_boot": N_BOOT,
            "per_strategy": {},
            "pairwise": {},
        }
        for sid in ["X0", "X2", "X6"]:
            s = boot_sharpes[sid]
            all_results[f"block_{blk}"]["per_strategy"][sid] = {
                "mean": float(np.mean(s)),
                "median": float(np.median(s)),
                "ci95": [float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))],
                "ci90": [float(np.percentile(s, 5)), float(np.percentile(s, 95))],
                "p_gt_0": float(np.mean(s > 0)),
            }
        for a, b in pairs:
            diff = boot_sharpes[a] - boot_sharpes[b]
            all_results[f"block_{blk}"]["pairwise"][f"{a}_vs_{b}"] = {
                "mean_delta": float(np.mean(diff)),
                "median_delta": float(np.median(diff)),
                "ci95": [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))],
                "ci90": [float(np.percentile(diff, 5)), float(np.percentile(diff, 95))],
                "p_a_wins": float(np.mean(diff > 0)),
                "ci95_crosses_zero": bool(np.percentile(diff, 2.5) < 0 < np.percentile(diff, 97.5)),
            }

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY: HOLDOUT BOOTSTRAP RESULTS")
    print(f"{'='*80}")
    print(f"\n  Point estimates (holdout, harsh):")
    print(f"    X0 Sharpe: {sims['X0']['sharpe']:.4f}")
    print(f"    X2 Sharpe: {sims['X2']['sharpe']:.4f}")
    print(f"    X6 Sharpe: {sims['X6']['sharpe']:.4f}")
    print(f"\n  P(X0 > X2) across block sizes:")
    for blk in BLOCK_SIZES:
        p = 1 - all_results[f"block_{blk}"]["pairwise"]["X2_vs_X0"]["p_a_wins"]
        print(f"    block={blk}: {p*100:.1f}%")
    print(f"\n  P(X0 > X6) across block sizes:")
    for blk in BLOCK_SIZES:
        p = 1 - all_results[f"block_{blk}"]["pairwise"]["X6_vs_X0"]["p_a_wins"]
        print(f"    block={blk}: {p*100:.1f}%")

    # Save
    out_path = Path(__file__).resolve().parent / "holdout_bootstrap_q4_results.json"
    all_results["point_estimates"] = {
        sid: {"sharpe": sims[sid]["sharpe"], "cagr": sims[sid]["cagr"], "mdd": sims[sid]["mdd"]}
        for sid in ["X0", "X2", "X6"]
    }
    all_results["holdout_bars"] = n_bars_holdout
    all_results["holdout_years"] = round(n_bars_holdout / (6 * 365.25), 2)

    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Saved: {out_path}")

    print(f"\n  Total time: {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
