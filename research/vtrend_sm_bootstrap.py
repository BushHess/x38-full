#!/usr/bin/env python3
"""VTREND-SM Bootstrap & Subsampling Analysis.

Provides statistical confidence for the VTREND-SM strategy using:
  1. VCBB bootstrap (2000 paths) — confidence intervals for Sharpe/CAGR/MDD/Calmar
  2. Sub-period analysis — stability across different market regimes

Uses the same infrastructure as all prior studies (vcbb.py, DataFeed, harsh cost).
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
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ── Constants (identical to all studies) ──────────────────────────────────
DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025 = 25 bps per side

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
BLKSZ  = 60
CTX    = 90
K_NN   = 50
SEED   = 42

ANN = math.sqrt(6.0 * 365.25)  # ~46.85  Sharpe annualization for H4
BPY = 6.0 * 365.0              # 2190.0  bars-per-year for realized vol (matches strategy)

# ── VTREND-SM default parameters ─────────────────────────────────────────
SLOW       = 120
FAST       = max(5, SLOW // 4)       # 30
ATR_P      = 14
ATR_MULT   = 3.0
ENTRY_N    = max(24, SLOW // 2)      # 60
EXIT_N     = max(12, SLOW // 4)      # 30
TARGET_VOL = 0.15
VOL_LB     = SLOW                    # 120
SLOPE_LB   = 6
MIN_REBAL  = 0.05
MIN_WEIGHT = 0.0
EPS        = 1e-12


# ═══════════════════════════════════════════════════════════════════════════
# Indicators (copied from strategy — codebase convention: frozen artifacts)
# ═══════════════════════════════════════════════════════════════════════════

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high, low, close, period):
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.concatenate([[high[0]], close[:-1]])),
            np.abs(low - np.concatenate([[low[0]], close[:-1]])),
        ),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _rolling_high_shifted(high, lookback):
    n = len(high)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.max(high[i - lookback:i])
    return out


def _rolling_low_shifted(low, lookback):
    n = len(low)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.min(low[i - lookback:i])
    return out


def _realized_vol(close, lookback, bars_per_year):
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    lr = np.full(n, np.nan, dtype=np.float64)
    lr[1:] = np.log(np.where(close[:-1] > 0, close[1:] / close[:-1], np.nan))
    ann_factor = math.sqrt(bars_per_year)
    for i in range(lookback, n):
        window = lr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=0)) * ann_factor
    return out


# ═══════════════════════════════════════════════════════════════════════════
# VTREND-SM Simulator (fast, numpy-based)
# ═══════════════════════════════════════════════════════════════════════════

def sim_vtrend_sm(cl, hi, lo, vo, tb, wi):
    """Run VTREND-SM on price arrays and return NAV series + trade count.

    Parameters
    ----------
    cl, hi, lo, vo, tb : np.ndarray  — close, high, low, volume, taker_buy
    wi : int                          — warmup index (no signals before this)

    Returns
    -------
    navs : np.ndarray  — per-bar NAV
    nt : int           — number of round-trip trades
    """
    n = len(cl)

    # Precompute indicators
    ef = _ema(cl, FAST)
    es = _ema(cl, SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    hh = _rolling_high_shifted(hi, ENTRY_N)
    ll = _rolling_low_shifted(lo, EXIT_N)
    rv = _realized_vol(cl, VOL_LB, BPY)

    slope_ref = np.full(n, np.nan, dtype=np.float64)
    if SLOPE_LB < n:
        slope_ref[SLOPE_LB:] = es[:-SLOPE_LB]

    # Warmup: first bar where ALL indicators are finite
    warmup_end = n
    for i in range(n):
        if (np.isfinite(ef[i]) and np.isfinite(es[i]) and np.isfinite(slope_ref[i])
                and np.isfinite(at[i]) and np.isfinite(hh[i])
                and np.isfinite(ll[i]) and np.isfinite(rv[i])):
            warmup_end = i
            break
    warmup_end = max(warmup_end, wi)

    # State
    cash = CASH
    bq = 0.0        # BTC quantity
    active = False
    nt = 0

    navs = np.full(n, CASH, dtype=np.float64)

    # Pending order from previous bar's signal
    has_pending = False
    pending_target = 0.0   # target weight (0.0 = full exit)

    for i in range(n):
        p = cl[i]

        # ── Execute pending order at this bar's open (use prev close as proxy) ──
        if i > 0 and has_pending:
            fp = cl[i - 1]
            has_pending = False
            nav_fp = cash + bq * fp

            if pending_target <= 0.0:
                # Full exit — ADD proceeds to cash (fractional sizing keeps cash)
                if bq > 0:
                    cash += bq * fp * (1.0 - CPS)
                    bq = 0.0
                    active = False
                    nt += 1
            else:
                # Entry or rebalance to target weight
                desired_bq = pending_target * nav_fp / fp
                delta_bq = desired_bq - bq

                if delta_bq > 1e-12:
                    # Buying more
                    cost = delta_bq * fp * (1.0 + CPS)
                    if cost <= cash + 1e-6:
                        cash -= cost
                        bq = desired_bq
                    # else: insufficient cash, skip
                elif delta_bq < -1e-12:
                    # Selling some
                    sell_bq = -delta_bq
                    cash += sell_bq * fp * (1.0 - CPS)
                    bq = desired_bq

                if not active and bq > 1e-12:
                    active = True

        # ── NAV ──
        nav = cash + bq * p
        navs[i] = nav

        # ── Strategy logic ──
        if i < warmup_end:
            continue

        if not (np.isfinite(ef[i]) and np.isfinite(es[i])
                and np.isfinite(slope_ref[i]) and np.isfinite(at[i])
                and np.isfinite(hh[i]) and np.isfinite(ll[i])
                and np.isfinite(rv[i])):
            continue

        regime_ok = (ef[i] > es[i]) and (es[i] > slope_ref[i])

        if not active:
            # ── FLAT: check entry ──
            if regime_ok and p > hh[i]:
                w = TARGET_VOL / max(rv[i], EPS)
                w = min(1.0, max(0.0, w))
                if w >= MIN_WEIGHT and w > 0.0:
                    has_pending = True
                    pending_target = w
        else:
            # ── LONG: check exit ──
            exit_floor = max(ll[i], es[i] - ATR_MULT * at[i])
            if p < exit_floor:
                has_pending = True
                pending_target = 0.0
            else:
                # ── LONG: check rebalance ──
                curr_expo = bq * p / nav if nav > EPS else 0.0
                new_w = TARGET_VOL / max(rv[i], EPS)
                new_w = min(1.0, max(0.0, new_w))
                if new_w < MIN_WEIGHT:
                    new_w = 0.0
                delta = abs(new_w - curr_expo)
                if delta >= MIN_REBAL - 1e-12:
                    has_pending = True
                    pending_target = new_w
                    if new_w <= 0.0:
                        active = False

    # Force close
    if bq > 1e-12:
        cash += bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        navs[-1] = cash
        nt += 1

    return navs, nt


def metrics_from_navs(navs, wi):
    """Compute standard metrics from a NAV time series."""
    active = navs[wi:]
    n = len(active)
    if n < 10:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0}

    rets = active[1:] / active[:-1] - 1.0
    n_rets = len(rets)
    if n_rets < 2:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0}

    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    tr = active[-1] / active[0] - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0

    peak = np.maximum.accumulate(active)
    dd = 1.0 - active / peak
    mdd = np.max(dd) * 100.0

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar}


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    ts = np.array([b.close_time for b in h4], dtype=np.int64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, ts, wi, n


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Real Data Baseline
# ═══════════════════════════════════════════════════════════════════════════

def phase1_real(cl, hi, lo, vo, tb, wi):
    """Run VTREND-SM on real data and print baseline metrics."""
    print("\n" + "=" * 70)
    print("  PHASE 1: REAL DATA BASELINE")
    print("=" * 70)

    navs, nt = sim_vtrend_sm(cl, hi, lo, vo, tb, wi)
    m = metrics_from_navs(navs, wi)
    m["trades"] = nt

    print(f"  Sharpe:     {m['sharpe']:.4f}")
    print(f"  CAGR:       {m['cagr']:.2f}%")
    print(f"  MDD:        {m['mdd']:.2f}%")
    print(f"  Calmar:     {m['calmar']:.4f}")
    print(f"  Trades:     {nt}")
    print(f"  Final NAV:  ${navs[-1]:,.2f}")

    return m


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: VCBB Bootstrap
# ═══════════════════════════════════════════════════════════════════════════

def phase2_bootstrap(cl, hi, lo, vo, tb, wi, n):
    """VCBB bootstrap: 2000 paths, compute CI for all metrics."""
    print("\n" + "=" * 70)
    print(f"  PHASE 2: VCBB BOOTSTRAP ({N_BOOT} paths)")
    print("=" * 70)

    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=CTX)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    # Storage
    sharpes = np.zeros(N_BOOT)
    cagrs   = np.zeros(N_BOOT)
    mdds    = np.zeros(N_BOOT)
    calmars = np.zeros(N_BOOT)
    trades  = np.zeros(N_BOOT, dtype=int)

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 100 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng,
            vcbb=vcbb_state, K=K_NN,
        )
        navs, nt = sim_vtrend_sm(c, h, l, v, t, wi)
        m = metrics_from_navs(navs, wi)

        sharpes[b] = m["sharpe"]
        cagrs[b]   = m["cagr"]
        mdds[b]    = m["mdd"]
        calmars[b] = m["calmar"]
        trades[b]  = nt

    el = time.time() - t0
    print(f"\n    Done: {el:.1f}s ({el/N_BOOT:.2f}s/path)")

    # ── Summary statistics ──
    def pct(arr, ps):
        return {f"p{int(p*100)}": float(np.percentile(arr, p*100)) for p in ps}

    percentiles = [0.025, 0.05, 0.25, 0.50, 0.75, 0.95, 0.975]

    results = {}
    for name, arr in [("sharpe", sharpes), ("cagr", cagrs),
                       ("mdd", mdds), ("calmar", calmars), ("trades", trades)]:
        results[name] = {
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            **pct(arr, percentiles),
        }

    # Key probabilities
    results["P_cagr_gt_0"] = float(np.mean(cagrs > 0))
    results["P_sharpe_gt_0"] = float(np.mean(sharpes > 0))
    results["P_sharpe_gt_0.5"] = float(np.mean(sharpes > 0.5))
    results["P_mdd_lt_30"] = float(np.mean(mdds < 30))
    results["P_mdd_lt_50"] = float(np.mean(mdds < 50))

    # Print
    print(f"\n  {'Metric':>10s} {'Mean':>8s} {'Median':>8s} {'Std':>8s} "
          f"{'2.5%':>8s} {'50%':>8s} {'97.5%':>8s}")
    print("  " + "-" * 60)
    for name in ["sharpe", "cagr", "mdd", "calmar"]:
        r = results[name]
        fmt = ".4f" if name in ("sharpe", "calmar") else ".2f"
        print(f"  {name:>10s} {r['mean']:{fmt}} {r['median']:{fmt}} {r['std']:{fmt}} "
              f"{r['p2']:{fmt}} {r['p50']:{fmt}} {r['p97']:{fmt}}")

    r = results["trades"]
    print(f"  {'trades':>10s} {r['mean']:8.1f} {r['median']:8.0f} {r['std']:8.1f} "
          f"{r['p2']:8.0f} {r['p50']:8.0f} {r['p97']:8.0f}")

    print(f"\n  P(CAGR > 0):      {results['P_cagr_gt_0']:6.1%}")
    print(f"  P(Sharpe > 0):    {results['P_sharpe_gt_0']:6.1%}")
    print(f"  P(Sharpe > 0.5):  {results['P_sharpe_gt_0.5']:6.1%}")
    print(f"  P(MDD < 30%):     {results['P_mdd_lt_30']:6.1%}")
    print(f"  P(MDD < 50%):     {results['P_mdd_lt_50']:6.1%}")

    return results, sharpes, cagrs, mdds, calmars


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3: Sub-Period Analysis
# ═══════════════════════════════════════════════════════════════════════════

def phase3_subperiod(cl, hi, lo, vo, tb, ts, wi, n):
    """Test strategy stability across different time periods."""
    print("\n" + "=" * 70)
    print("  PHASE 3: SUB-PERIOD ANALYSIS")
    print("=" * 70)

    # Define sub-periods by year boundaries (UTC epoch ms)
    def year_ms(y):
        import calendar, datetime
        dt = datetime.datetime(y, 1, 1, tzinfo=datetime.timezone.utc)
        return int(dt.timestamp() * 1000)

    # ── Per-year analysis ──
    print("\n  Per-Year Performance:")
    print(f"  {'Period':>14s} {'Bars':>6s} {'Sharpe':>8s} {'CAGR':>8s} {'MDD':>7s} "
          f"{'Calmar':>8s} {'Trades':>7s}")
    print("  " + "-" * 68)

    yearly_results = {}
    for yr in range(2019, 2026):
        t_start = year_ms(yr)
        t_end = year_ms(yr + 1)

        mask = (ts >= t_start) & (ts < t_end)
        if mask.sum() < 100:
            continue

        idx = np.where(mask)[0]
        i_start = idx[0]
        i_end = idx[-1] + 1

        # Need enough history for indicators — extend back
        # Use full data but only measure performance in the sub-period
        navs, nt = sim_vtrend_sm(cl, hi, lo, vo, tb, 0)

        # Extract sub-period NAV
        sub_navs = navs[i_start:i_end]
        if len(sub_navs) < 10:
            continue

        # Metrics on sub-period
        rets = sub_navs[1:] / sub_navs[:-1] - 1.0
        n_rets = len(rets)
        mu = np.mean(rets)
        std = np.std(rets, ddof=0)
        sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

        tr = sub_navs[-1] / sub_navs[0] - 1.0
        yrs = n_rets / (6.0 * 365.25)
        cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0

        peak = np.maximum.accumulate(sub_navs)
        dd = 1.0 - sub_navs / peak
        mdd = np.max(dd) * 100.0
        calmar = cagr / mdd if mdd > 0.01 else 0.0

        # Count trades in this period (approximate from NAV changes)
        # Use position detection from NAV
        yearly_results[yr] = {
            "bars": int(mask.sum()),
            "sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
        }

        print(f"  {yr:>14d} {mask.sum():6d} {sharpe:8.4f} {cagr:7.2f}% {mdd:6.2f}% "
              f"{calmar:8.4f}")

    # ── Halves ──
    print(f"\n  Half-Period Performance:")
    print(f"  {'Period':>14s} {'Bars':>6s} {'Sharpe':>8s} {'CAGR':>8s} {'MDD':>7s} "
          f"{'Calmar':>8s}")
    print("  " + "-" * 60)

    navs_full, _ = sim_vtrend_sm(cl, hi, lo, vo, tb, 0)

    # Split at midpoint of post-warmup data
    mid = wi + (n - wi) // 2
    for label, i_start, i_end in [("First half", wi, mid), ("Second half", mid, n)]:
        sub = navs_full[i_start:i_end]
        if len(sub) < 10:
            continue
        m = metrics_from_navs(sub, 0)
        print(f"  {label:>14s} {i_end-i_start:6d} {m['sharpe']:8.4f} {m['cagr']:7.2f}% "
              f"{m['mdd']:6.2f}% {m['calmar']:8.4f}")

    # ── Thirds ──
    print(f"\n  Third-Period Performance:")
    print(f"  {'Period':>14s} {'Bars':>6s} {'Sharpe':>8s} {'CAGR':>8s} {'MDD':>7s} "
          f"{'Calmar':>8s}")
    print("  " + "-" * 60)

    third = (n - wi) // 3
    for j, label in enumerate(["First third", "Middle third", "Last third"]):
        i_start = wi + j * third
        i_end = wi + (j + 1) * third if j < 2 else n
        sub = navs_full[i_start:i_end]
        if len(sub) < 10:
            continue
        m = metrics_from_navs(sub, 0)
        print(f"  {label:>14s} {i_end-i_start:6d} {m['sharpe']:8.4f} {m['cagr']:7.2f}% "
              f"{m['mdd']:6.2f}% {m['calmar']:8.4f}")

    return yearly_results


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4: Comparison with E0 Bootstrap Baseline
# ═══════════════════════════════════════════════════════════════════════════

def phase4_comparison(results):
    """Compare VTREND-SM bootstrap stats with E0 baseline from research."""
    print("\n" + "=" * 70)
    print("  PHASE 4: SM vs E0 BOOTSTRAP COMPARISON")
    print("=" * 70)

    # E0 bootstrap baseline (from VCBB, N=120, harsh cost)
    # Source: memory/MEMORY.md — "Bootstrap (VCBB): Sharpe 0.54, CAGR 14.2%, MDD 61.0%"
    e0 = {"sharpe_median": 0.54, "cagr_median": 14.2, "mdd_median": 61.0,
           "P_cagr_gt_0": 0.803}

    sm = results
    sm_sh = sm["sharpe"]["median"]
    sm_cagr = sm["cagr"]["median"]
    sm_mdd = sm["mdd"]["median"]
    sm_p = sm["P_cagr_gt_0"]

    print(f"\n  {'Metric':>20s} {'E0 (N=120)':>12s} {'SM':>12s} {'Delta':>12s}")
    print("  " + "-" * 60)
    print(f"  {'Sharpe (median)':>20s} {e0['sharpe_median']:12.4f} {sm_sh:12.4f} "
          f"{sm_sh - e0['sharpe_median']:+12.4f}")
    print(f"  {'CAGR % (median)':>20s} {e0['cagr_median']:12.2f} {sm_cagr:12.2f} "
          f"{sm_cagr - e0['cagr_median']:+12.2f}")
    print(f"  {'MDD % (median)':>20s} {e0['mdd_median']:12.2f} {sm_mdd:12.2f} "
          f"{sm_mdd - e0['mdd_median']:+12.2f}")
    print(f"  {'P(CAGR > 0)':>20s} {e0['P_cagr_gt_0']:11.1%} {sm_p:11.1%} "
          f"{sm_p - e0['P_cagr_gt_0']:+11.1%}")

    print(f"\n  Interpretation:")
    if sm_sh > e0["sharpe_median"]:
        print(f"    Sharpe: SM higher ({sm_sh:.4f} > {e0['sharpe_median']:.4f})")
    else:
        print(f"    Sharpe: SM lower ({sm_sh:.4f} < {e0['sharpe_median']:.4f})")

    if sm_mdd < e0["mdd_median"]:
        print(f"    MDD: SM better ({sm_mdd:.1f}% < {e0['mdd_median']:.1f}%) — "
              f"lower drawdown")
    else:
        print(f"    MDD: SM worse ({sm_mdd:.1f}% > {e0['mdd_median']:.1f}%)")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  VTREND-SM BOOTSTRAP & SUBSAMPLING ANALYSIS")
    print("  Cost: harsh (50 bps RT), Block: 60, Bootstrap: VCBB")
    print("=" * 70)

    cl, hi, lo, vo, tb, ts, wi, n = load_arrays()
    print(f"  Data: {n} H4 bars, warmup index: {wi}")

    # Phase 1: Real data baseline
    real_metrics = phase1_real(cl, hi, lo, vo, tb, wi)

    # Phase 2: VCBB Bootstrap
    boot_results, sharpes, cagrs, mdds, calmars = phase2_bootstrap(
        cl, hi, lo, vo, tb, wi, n)

    # Phase 3: Sub-period analysis
    yearly = phase3_subperiod(cl, hi, lo, vo, tb, ts, wi, n)

    # Phase 4: Comparison with E0
    phase4_comparison(boot_results)

    # ── Save results ──
    outdir = ROOT / "out" / "vtrend_sm_bootstrap"
    outdir.mkdir(parents=True, exist_ok=True)

    output = {
        "strategy": "vtrend_sm",
        "cost": "harsh (50 bps RT)",
        "n_boot": N_BOOT,
        "blksz": BLKSZ,
        "seed": SEED,
        "real_data": real_metrics,
        "bootstrap": boot_results,
        "yearly": {str(k): v for k, v in yearly.items()},
    }

    with open(outdir / "results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to {outdir / 'results.json'}")

    # Save raw bootstrap arrays
    np.savez(outdir / "bootstrap_raw.npz",
             sharpes=sharpes, cagrs=cagrs, mdds=mdds, calmars=calmars)
    print(f"  Raw arrays saved to {outdir / 'bootstrap_raw.npz'}")

    print("\n" + "=" * 70)
    print("  ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
