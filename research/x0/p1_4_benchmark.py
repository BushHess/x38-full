#!/usr/bin/env python3
"""P1.4 — Full benchmark + bootstrap for X0 Phase 1 vs 4 baselines.

Strategies compared:
  1. E0          = vtrend (baseline)
  2. E0+EMA21    = vtrend_ema21_d1 (D1 regime filter)
  3. E5          = vtrend_e5 (robust ATR trail)
  4. E5+EMA21    = vtrend_e5_ema21_d1 (robust ATR + D1 regime)
  5. X0          = vtrend_x0 (Phase 1 — behavioral clone of E0+EMA21)

Evaluation pipeline:
  T1. Full backtest (3 cost scenarios: smart, base, harsh)
  T2. Bootstrap VCBB (500 paths, default slow=120, block=60)

Follows canonical parity_eval.py patterns.
"""

from __future__ import annotations

import csv
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
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb


# =========================================================================
# CONSTANTS (matching parity_eval.py canonical settings)
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
TRAIL = 3.0
SLOW = 120

N_BOOT = 500
BLKSZ = 60
SEED = 42

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["E0", "E0_EMA21", "E5", "E5_EMA21", "X0"]
STRATEGY_LABELS = {
    "E0": "VTrend E0",
    "E0_EMA21": "E0+EMA21(D1)",
    "E5": "VTrend E5",
    "E5_EMA21": "E5+EMA21(D1)",
    "X0": "X0 Phase 1",
}


# =========================================================================
# FAST INDICATORS (C-level via scipy.signal.lfilter)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


def _vdo(close: np.ndarray, high: np.ndarray, low: np.ndarray,
         volume: np.ndarray, taker_buy: np.ndarray,
         fast: int, slow: int) -> np.ndarray:
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


def _robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                cap_q: float = 0.90, cap_lb: int = 100, period: int = 20) -> np.ndarray:
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    if cap_lb <= n:
        from numpy.lib.stride_tricks import sliding_window_view
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
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            ratr[s + period:] = smoothed
    return ratr


def _d1_regime_map(cl, d1_cl, d1_close_times, h4_close_times, d1_ema_period=21):
    n = len(cl)
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_close_times[i]:
            d1_idx += 1
        if d1_close_times[d1_idx] < h4_close_times[i]:
            regime_h4[i] = d1_regime[d1_idx]
    return regime_h4


# =========================================================================
# METRICS
# =========================================================================

def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "total_return": 0.0, "win_rate": 0.0,
                "profit_factor": 0.0, "avg_exposure": 0.0}
    rets = navs[1:] / navs[:-1] - 1.0
    n = len(rets)
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    total_ret = navs[-1] / navs[0] - 1.0
    yrs = n / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0

    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    # Exposure: fraction of bars where NAV != cash (in-market)
    # Approximate: bars where return != 0 (simplification for vectorized sim)
    in_market = np.sum(np.abs(rets) > 1e-10) / n * 100 if n > 0 else 0.0

    return {
        "sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
        "trades": nt, "total_return": total_ret * 100,
        "avg_exposure": in_market,
    }


# =========================================================================
# STRATEGY SIMS (vectorized, matching parity_eval.py canonical pattern)
# =========================================================================

def sim_e0(cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
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
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                    slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
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
            if p < pk - trail_mult * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def sim_e5(cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * ratr[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                    slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
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
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * ratr[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


# X0 is identical to E0_EMA21 (by design — Phase 1 parity)
sim_x0 = sim_e0_ema21_d1


def run_strategy(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                 slow_period=SLOW, cps=0.005):
    kw = dict(slow_period=slow_period, cps=cps)
    if sid == "E0":
        return sim_e0(cl, hi, lo, vo, tb, wi, **kw)
    elif sid == "E0_EMA21":
        return sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "E5":
        return sim_e5(cl, hi, lo, vo, tb, wi, **kw)
    elif sid == "E5_EMA21":
        return sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "X0":
        return sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# =========================================================================
# T1: FULL BACKTEST (3 cost scenarios)
# =========================================================================

def run_backtests(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST (3 cost scenarios)")
    print("=" * 80)

    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for scenario, cps in COST_SCENARIOS.items():
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
            m = _metrics(nav, wi, nt)
            results[sid][scenario] = m

    # Print table
    header = f"{'Strategy':14s} {'Scenario':8s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Calmar':>8s} {'Trades':>7s} {'TotRet%':>9s}"
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            print(f"{sid:14s} {sc:8s} {m['sharpe']:8.4f} {m['cagr']:8.2f} "
                  f"{m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:7d} {m['total_return']:9.2f}")

    return results


# =========================================================================
# T2: BOOTSTRAP VCBB
# =========================================================================

def run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print(f"T2: BOOTSTRAP VCBB ({N_BOOT} paths, slow={SLOW}, block={BLKSZ})")
    print("=" * 80)

    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    # Pre-generate all bootstrap paths (shared across strategies)
    print("  Generating bootstrap paths...", end=" ", flush=True)
    t0 = time.time()
    boot_paths = []
    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        bcl_full = np.concatenate([cl[:wi], bcl])
        bhi_full = np.concatenate([hi[:wi], bhi])
        blo_full = np.concatenate([lo[:wi], blo])
        bvo_full = np.concatenate([vo[:wi], bvo])
        btb_full = np.concatenate([tb[:wi], btb])
        boot_paths.append((bcl_full, bhi_full, blo_full, bvo_full, btb_full))
    print(f"done ({time.time() - t0:.1f}s)")

    results = {}
    for sid in STRATEGY_IDS:
        sharpes = []
        cagrs = []
        mdds = []

        t0 = time.time()
        for b in range(N_BOOT):
            bcl, bhi, blo, bvo, btb = boot_paths[b]
            bnav, _ = run_strategy(sid, bcl, bhi, blo, bvo, btb, wi,
                                   d1_cl, d1_ct, h4_ct)
            bm = _metrics(bnav, wi)
            sharpes.append(bm["sharpe"])
            cagrs.append(bm["cagr"])
            mdds.append(bm["mdd"])

        sharpes = np.array(sharpes)
        cagrs = np.array(cagrs)
        mdds = np.array(mdds)

        results[sid] = {
            "sharpe_median": float(np.median(sharpes)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_p95": float(np.percentile(sharpes, 95)),
            "sharpe_mean": float(np.mean(sharpes)),
            "cagr_median": float(np.median(cagrs)),
            "cagr_p5": float(np.percentile(cagrs, 5)),
            "cagr_p95": float(np.percentile(cagrs, 95)),
            "mdd_median": float(np.median(mdds)),
            "mdd_p5": float(np.percentile(mdds, 5)),
            "mdd_p95": float(np.percentile(mdds, 95)),
            "p_cagr_gt0": float(np.mean(cagrs > 0)),
            "p_sharpe_gt0": float(np.mean(sharpes > 0)),
        }

        r = results[sid]
        elapsed = time.time() - t0
        print(f"  {sid:14s}  Sharpe={r['sharpe_median']:.4f} [{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"CAGR={r['cagr_median']:.2f}% [{r['cagr_p5']:.2f}, {r['cagr_p95']:.2f}]  "
              f"MDD={r['mdd_median']:.2f}% [{r['mdd_p5']:.2f}, {r['mdd_p95']:.2f}]  "
              f"P(CAGR>0)={r['p_cagr_gt0']:.3f}  ({elapsed:.1f}s)")

    return results


# =========================================================================
# OUTPUT
# =========================================================================

def save_results(bt_results, boot_results):
    outdir = OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)

    # JSON
    payload = {
        "settings": {
            "data": DATA, "start": START, "end": END, "warmup": WARMUP,
            "slow_period": SLOW, "trail_mult": TRAIL, "cash": CASH,
            "n_boot": N_BOOT, "blksz": BLKSZ, "seed": SEED,
        },
        "backtest": bt_results,
        "bootstrap": boot_results,
    }
    with open(outdir / "p1_4_results.json", "w") as f:
        json.dump(payload, f, indent=2, default=str)

    # CSV — backtest table
    with open(outdir / "p1_4_backtest_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy", "scenario", "sharpe", "cagr_pct", "mdd_pct",
                         "calmar", "trades", "total_return_pct", "avg_exposure_pct"])
        for sid in STRATEGY_IDS:
            for sc in ["smart", "base", "harsh"]:
                m = bt_results[sid][sc]
                writer.writerow([sid, sc,
                                 f"{m['sharpe']:.4f}", f"{m['cagr']:.2f}", f"{m['mdd']:.2f}",
                                 f"{m['calmar']:.4f}", m['trades'],
                                 f"{m['total_return']:.2f}", f"{m['avg_exposure']:.2f}"])

    # CSV — bootstrap table
    with open(outdir / "p1_4_bootstrap_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy",
                         "sharpe_med", "sharpe_p5", "sharpe_p95",
                         "cagr_med", "cagr_p5", "cagr_p95",
                         "mdd_med", "mdd_p5", "mdd_p95",
                         "p_cagr_gt0", "p_sharpe_gt0"])
        for sid in STRATEGY_IDS:
            r = boot_results[sid]
            writer.writerow([sid,
                             f"{r['sharpe_median']:.4f}", f"{r['sharpe_p5']:.4f}", f"{r['sharpe_p95']:.4f}",
                             f"{r['cagr_median']:.2f}", f"{r['cagr_p5']:.2f}", f"{r['cagr_p95']:.2f}",
                             f"{r['mdd_median']:.2f}", f"{r['mdd_p5']:.2f}", f"{r['mdd_p95']:.2f}",
                             f"{r['p_cagr_gt0']:.3f}", f"{r['p_sharpe_gt0']:.3f}"])

    print(f"\nResults saved to {outdir}/")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()

    print("P1.4 — X0 Phase 1 Full Benchmark")
    print("=" * 80)

    # Load data
    print("Loading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    d1 = feed.d1_bars
    print(f"  H4: {len(h4)} bars, D1: {len(d1)} bars")

    # Extract numpy arrays
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in h4], dtype=np.int64)

    d1_cl = np.array([b.close for b in d1], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in d1], dtype=np.int64)

    # Warmup index
    wi = 0
    if feed.report_start_ms is not None:
        for j, bar in enumerate(h4):
            if bar.close_time >= feed.report_start_ms:
                wi = j
                break
    print(f"  Warmup index: {wi} (reporting from bar {wi} onwards)")

    # T1: Full backtests
    bt_results = run_backtests(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Verify X0 == E0_EMA21 parity
    print("\n  X0 vs E0_EMA21 parity check:")
    for sc in ["smart", "base", "harsh"]:
        x0_m = bt_results["X0"][sc]
        e0e_m = bt_results["E0_EMA21"][sc]
        match = all(
            abs(x0_m[k] - e0e_m[k]) < 1e-10
            for k in ["sharpe", "cagr", "mdd", "calmar"]
        ) and x0_m["trades"] == e0e_m["trades"]
        status = "BIT-IDENTICAL" if match else "DIFFERS"
        print(f"    {sc}: {status}")

    # T2: Bootstrap
    boot_results = run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Verify X0 == E0_EMA21 in bootstrap
    print("\n  X0 vs E0_EMA21 bootstrap parity:")
    x0_b = boot_results["X0"]
    e0e_b = boot_results["E0_EMA21"]
    all_match = True
    for k in x0_b:
        if abs(x0_b[k] - e0e_b[k]) > 1e-10:
            all_match = False
            break
    print(f"    {'BIT-IDENTICAL' if all_match else 'DIFFERS'}")

    # Save
    save_results(bt_results, boot_results)

    # Rankings
    print("\n" + "=" * 80)
    print("RANKINGS (harsh scenario)")
    print("=" * 80)
    harsh = {sid: bt_results[sid]["harsh"] for sid in STRATEGY_IDS}

    for metric, key, reverse in [
        ("Sharpe", "sharpe", True),
        ("CAGR%", "cagr", True),
        ("MDD%", "mdd", False),
    ]:
        ranked = sorted(STRATEGY_IDS, key=lambda s: harsh[s][key], reverse=reverse)
        print(f"\n  By {metric}:")
        for rank, sid in enumerate(ranked, 1):
            print(f"    {rank}. {sid:14s} = {harsh[sid][key]:.4f}")

    elapsed = time.time() - t_start
    print(f"\nTotal time: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
