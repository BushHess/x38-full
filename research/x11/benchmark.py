#!/usr/bin/env python3
"""X11 Research — Short-Side Complement for E5+EMA21D1.

Hypothesis: When the D1 EMA(21) regime filter = OFF (bearish), a simple
short signal (reverse EMA crossover + ATR trail) generates independent alpha,
increasing portfolio Sharpe without increasing correlation.

Counter-hypotheses:
  1. BTC's long-term upward drift makes shorting negative-EV on average.
  2. Bear markets are short & violent — trend-following shorts enter late,
     exit late, and eat the bounce.
  3. Cross-timescale rho=0.92 (long side) suggests diversification ceiling
     may also apply to the short side.
  4. Short costs (funding rate ~10-30 bps/day on perps) erode alpha faster
     than long costs.

Design:
  LONG side:  E5+EMA21D1 baseline (unchanged).
  SHORT side: Mirror logic during regime OFF only.
    Entry: fast_ema < slow_ema AND vdo < -VDO_THR AND regime_h4 == False
    Exit:  fast_ema > slow_ema  OR  trail stop (low + trail_mult * RATR)
    Position: short 1x notional (no leverage beyond 1x).

Cost model for shorts:
  - RT spread/slippage: same as long (configurable via cost scenarios)
  - Funding rate: FUNDING_BPS_PER_BAR applied every bar while short
    Default: 1.0 bps/4h bar ≈ 6 bps/day ≈ 21.9% annualized (conservative)

Tests:
  T0: Bear-period characterization — stats of regime-OFF windows
  T1: Short-only factorial (3 cost scenarios × with/without funding)
  T2: Timescale robustness (16 slow_periods, short-only)
  T3: Combined LONG+SHORT vs LONG-only (portfolio level)
  T4: Bootstrap VCBB (500 paths, combined vs long-only h2h)
  T5: Correlation analysis — short-side vs long-side return streams
  T6: Funding rate sensitivity sweep

Note: Uses SPOT price data to simulate shorts. This is a feasibility gate —
if no signal exists here, futures data won't help. Real implementation would
require perpetual futures (BTCUSDT.P) with actual funding rates.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import lfilter
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
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

VDO_F = 12
VDO_S = 28
VDO_THR = 0.0

# E5+EMA21D1 default params
SLOW = 120
TRAIL = 3.0
D1_EMA_P = 21

# Robust ATR params
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

N_BOOT = 500
BLKSZ = 60
SEED = 42

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}
CPS_HARSH = COST_SCENARIOS["harsh"]

# Funding rate: applied per H4 bar while short
# 1.0 bps/bar = 6 bps/day ≈ 21.9%/yr (conservative for BTC perps)
FUNDING_BPS_PER_BAR = 1.0
FUNDING_PER_BAR = FUNDING_BPS_PER_BAR / 10_000.0

# Funding sweep range (bps per 4h bar)
FUNDING_SWEEP = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# FAST INDICATORS (vectorized, identical to x10)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _robust_atr(high, low, close,
                cap_q=RATR_CAP_Q, cap_lb=RATR_CAP_LB, period=RATR_PERIOD):
    """Robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))

    n = len(tr)

    windows = sliding_window_view(tr, cap_lb)
    q_vals = np.percentile(windows, cap_q * 100, axis=1)

    tr_cap = np.full(n, np.nan)
    num = n - cap_lb
    tr_cap[cap_lb:] = np.minimum(tr[cap_lb:], q_vals[:num])

    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        alpha_w = 1.0 / period
        b_w = np.array([alpha_w])
        a_w = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi_w = np.array([(1.0 - alpha_w) * ratr[s + period - 1]])
            smoothed, _ = lfilter(b_w, a_w, tail, zi=zi_w)
            ratr[s + period:] = smoothed

    return ratr


def _vdo(close, high, low, volume, taker_buy, fast=VDO_F, slow=VDO_S):
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = np.maximum(volume - taker_buy, 0.0)
        vdr = np.zeros(n)
        mask = volume > 1e-12
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 1e-12
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": nt}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar, "trades": nt}


# =========================================================================
# D1 REGIME FILTER
# =========================================================================

def _compute_d1_regime(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
    """Compute D1 EMA regime and map to H4 close_time grid."""
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema

    n_h4 = len(h4_ct)
    regime_h4 = np.zeros(n_h4, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_h4[i] = d1_regime[d1_idx]

    return regime_h4


# =========================================================================
# LONG-ONLY SIM (E5+EMA21D1 baseline, from x10)
# =========================================================================

def sim_long_only(cl, hi, lo, vo, tb, regime_h4, wi,
                  slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH):
    """E5+EMA21D1 long-only baseline. Returns (nav, nt, per_bar_returns)."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb)

    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0

    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1 + cps))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                px = False
                if bq > 0:
                    cash += bq * fp * (1 - cps)
                    bq = 0.0
                    inp = False
                    nt += 1

        nav[i] = cash + bq * p

        if math.isnan(ratr[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            trail_stop = pk - trail_mult * ratr[i]
            if p < trail_stop:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Close open
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps)
        bq = 0.0
        nt += 1
        nav[-1] = cash

    # Per-bar returns for correlation analysis
    bar_rets = np.zeros(n)
    bar_rets[1:] = nav[1:] / np.maximum(nav[:-1], 1e-12) - 1.0

    return nav, nt, bar_rets


# =========================================================================
# SHORT-ONLY SIM (regime OFF periods only)
# =========================================================================

def sim_short_only(cl, hi, lo, vo, tb, regime_h4, wi,
                   slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH,
                   funding_per_bar=FUNDING_PER_BAR):
    """Short-side signal during regime OFF periods.

    Entry: fast_ema < slow_ema AND vdo < -VDO_THR AND NOT regime_h4
    Exit:  fast_ema > slow_ema OR trail stop (valley + trail_mult * RATR)
           OR regime turns ON (forced exit — no shorting in bull regime)

    Short P&L per bar: qty * (entry_px - current_px) - funding
    Position: cash / entry_px (1x notional, no leverage).

    Returns (nav, nt, per_bar_returns).
    """
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb)

    cash = CASH
    sq = 0.0          # short quantity (positive = short position size)
    entry_px = 0.0    # price at which we shorted
    inp = False
    pe = px = False    # pending entry/exit
    nt = 0
    valley = 0.0      # lowest price seen (for trail stop on short)

    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]

            if pe:
                pe = False
                # Open short at previous close
                entry_px = fp
                sq = cash / (fp * (1 + cps))  # notional / price, cost on entry
                cash -= sq * fp * cps          # deduct entry cost from cash
                inp = True
                valley = p

            elif px:
                px = False
                if sq > 0:
                    # Close short: profit = sq * (entry_px - fp)
                    pnl = sq * (entry_px - fp)
                    close_cost = sq * fp * cps
                    cash += pnl - close_cost
                    sq = 0.0
                    inp = False
                    nt += 1

        # Mark-to-market: cash + unrealized short P&L
        if inp and sq > 0:
            unrealized = sq * (entry_px - p)
            nav[i] = cash + unrealized
            # Deduct funding cost per bar while in position
            funding_cost = sq * p * funding_per_bar
            cash -= funding_cost
        else:
            nav[i] = cash

        if math.isnan(ratr[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            # Short entry: bearish crossover + negative VDO + regime OFF
            if ef[i] < es[i] and vd[i] < -VDO_THR and not regime_h4[i]:
                pe = True
        else:
            valley = min(valley, p)

            # Trail stop from below: price rises above valley + trail * RATR
            trail_stop = valley + trail_mult * ratr[i]
            if p > trail_stop:
                px = True
            elif ef[i] > es[i]:
                # Trend reversal exit
                px = True
            elif regime_h4[i]:
                # Forced exit: regime turned bullish
                px = True

    # Close open short at end
    if inp and sq > 0:
        pnl = sq * (entry_px - cl[-1])
        close_cost = sq * cl[-1] * cps
        cash += pnl - close_cost
        sq = 0.0
        nt += 1
        nav[-1] = cash

    # Per-bar returns
    bar_rets = np.zeros(n)
    bar_rets[1:] = nav[1:] / np.maximum(nav[:-1], 1e-12) - 1.0

    return nav, nt, bar_rets


# =========================================================================
# COMBINED LONG+SHORT SIM (equal capital allocation)
# =========================================================================

def sim_combined(cl, hi, lo, vo, tb, regime_h4, wi,
                 slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH,
                 funding_per_bar=FUNDING_PER_BAR):
    """Run long and short independently, combine NAV curves.

    Capital split: 50/50 (each starts with CASH/2).
    Combined NAV = long_nav + short_nav (rebalanced at bar level).

    Returns (nav_combined, nt_long, nt_short, long_bar_rets, short_bar_rets).
    """
    # Scale CASH temporarily for each leg
    global CASH
    orig_cash = CASH
    CASH = orig_cash / 2.0

    nav_l, nt_l, rets_l = sim_long_only(
        cl, hi, lo, vo, tb, regime_h4, wi,
        slow_period=slow_period, trail_mult=trail_mult, cps=cps)

    nav_s, nt_s, rets_s = sim_short_only(
        cl, hi, lo, vo, tb, regime_h4, wi,
        slow_period=slow_period, trail_mult=trail_mult, cps=cps,
        funding_per_bar=funding_per_bar)

    CASH = orig_cash

    nav_combined = nav_l + nav_s

    return nav_combined, nt_l, nt_s, rets_l, rets_s


# =========================================================================
# T0: BEAR-PERIOD CHARACTERIZATION
# =========================================================================

def run_t0_bear_stats(cl, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T0: BEAR-PERIOD CHARACTERIZATION (regime OFF windows)")
    print("=" * 80)

    n = len(cl)
    regime_post_wi = regime_h4[wi:]
    cl_post_wi = cl[wi:]
    n_post = len(regime_post_wi)

    n_off = np.sum(~regime_post_wi)
    n_on = np.sum(regime_post_wi)
    pct_off = n_off / n_post * 100

    print(f"\n  Total H4 bars (post-warmup): {n_post}")
    print(f"  Regime ON  (bullish): {n_on} bars ({n_on/n_post*100:.1f}%)")
    print(f"  Regime OFF (bearish): {n_off} bars ({pct_off:.1f}%)")

    # Find contiguous OFF windows
    off_windows = []
    in_off = False
    start_idx = 0
    for i in range(n_post):
        if not regime_post_wi[i] and not in_off:
            in_off = True
            start_idx = i
        elif regime_post_wi[i] and in_off:
            in_off = False
            off_windows.append((start_idx, i - 1))
    if in_off:
        off_windows.append((start_idx, n_post - 1))

    n_windows = len(off_windows)
    window_lens = [e - s + 1 for s, e in off_windows]
    window_rets = []
    for s, e in off_windows:
        if cl_post_wi[s] > 0:
            ret = (cl_post_wi[e] / cl_post_wi[s] - 1) * 100
        else:
            ret = 0.0
        window_rets.append(ret)

    window_lens = np.array(window_lens)
    window_rets = np.array(window_rets)

    print(f"\n  Number of OFF windows: {n_windows}")
    if n_windows > 0:
        print(f"  Window length (bars): mean={np.mean(window_lens):.1f}  "
              f"median={np.median(window_lens):.1f}  "
              f"min={np.min(window_lens)}  max={np.max(window_lens)}")
        print(f"  Window return%: mean={np.mean(window_rets):.2f}  "
              f"median={np.median(window_rets):.2f}  "
              f"min={np.min(window_rets):.2f}  max={np.max(window_rets):.2f}")

        n_neg = np.sum(window_rets < 0)
        n_pos = np.sum(window_rets >= 0)
        print(f"  Windows with negative return: {n_neg}/{n_windows} ({n_neg/n_windows*100:.1f}%)")
        print(f"  Windows with positive return: {n_pos}/{n_windows} ({n_pos/n_windows*100:.1f}%)")

        # Average per-bar return during OFF periods
        off_rets = []
        for i in range(1, n_post):
            if not regime_post_wi[i]:
                off_rets.append(cl_post_wi[i] / cl_post_wi[i - 1] - 1)
        off_rets = np.array(off_rets)
        if len(off_rets) > 0:
            mu_off = np.mean(off_rets) * 100
            std_off = np.std(off_rets, ddof=0) * 100
            ann_mu = mu_off * 6 * 365.25
            print(f"\n  Per-bar return during OFF: mean={mu_off:.4f}%  "
                  f"std={std_off:.4f}%  ann_drift={ann_mu:.2f}%")
            # If annualized drift during OFF is still positive, shorting is swimming upstream
            if ann_mu > 0:
                print(f"  WARNING: Annualized drift during OFF is POSITIVE ({ann_mu:.2f}%) — "
                      "shorting faces headwind")
            else:
                print(f"  Annualized drift during OFF is NEGATIVE ({ann_mu:.2f}%) — "
                      "shorting has structural tailwind")

    results = {
        "n_bars_post_warmup": int(n_post),
        "n_off": int(n_off),
        "pct_off": float(pct_off),
        "n_windows": n_windows,
    }
    if n_windows > 0:
        results.update({
            "window_len_mean": float(np.mean(window_lens)),
            "window_len_median": float(np.median(window_lens)),
            "window_ret_mean": float(np.mean(window_rets)),
            "window_ret_median": float(np.median(window_rets)),
            "pct_negative_windows": float(n_neg / n_windows * 100),
            "off_bar_drift_ann_pct": float(ann_mu) if len(off_rets) > 0 else None,
        })

    return results


# =========================================================================
# T1: SHORT-ONLY FACTORIAL (3 cost scenarios × with/without funding)
# =========================================================================

def run_t1_short_factorial(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T1: SHORT-ONLY FACTORIAL (3 cost × 2 funding variants)")
    print("=" * 80)

    results = {}
    header = (f"{'Funding':>10s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s}")
    print(f"\n{header}")
    print("-" * len(header))

    for funding_label, fpb in [("no_fund", 0.0), ("fund_1bps", FUNDING_PER_BAR)]:
        results[funding_label] = {}
        for scenario, cps_val in COST_SCENARIOS.items():
            nav, nt, _ = sim_short_only(
                cl, hi, lo, vo, tb, regime_h4, wi,
                cps=cps_val, funding_per_bar=fpb)
            m = _metrics(nav, wi, nt)
            results[funding_label][scenario] = m
            print(f"{funding_label:>10s} {scenario:6s} {m['sharpe']:8.4f} {m['cagr']:8.2f} "
                  f"{m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:7d}")

    return results


# =========================================================================
# T2: TIMESCALE ROBUSTNESS (16 slow_periods, short-only)
# =========================================================================

def run_t2_timescale(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T2: TIMESCALE ROBUSTNESS — SHORT-ONLY (16 slow_periods)")
    print("=" * 80)

    results = {}
    header = f"{'Slow':>6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Calmar':>8s} {'Trades':>7s}"
    print(f"\n{header}")
    print("-" * len(header))

    n_positive_sharpe = 0
    for slow_p in SLOW_PERIODS:
        nav, nt, _ = sim_short_only(
            cl, hi, lo, vo, tb, regime_h4, wi,
            slow_period=slow_p)
        m = _metrics(nav, wi, nt)
        results[slow_p] = m
        if m["sharpe"] > 0:
            n_positive_sharpe += 1
        print(f"{slow_p:6d} {m['sharpe']:8.4f} {m['cagr']:8.2f} "
              f"{m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:7d}")

    print(f"\n  Positive Sharpe: {n_positive_sharpe}/16 timescales")
    print(f"  Median Sharpe: {np.median([results[sp]['sharpe'] for sp in SLOW_PERIODS]):.4f}")

    return results


# =========================================================================
# T3: COMBINED LONG+SHORT vs LONG-ONLY
# =========================================================================

def run_t3_combined(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T3: COMBINED LONG+SHORT vs LONG-ONLY")
    print("=" * 80)

    results = {}
    header = (f"{'Config':>12s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s}")
    print(f"\n{header}")
    print("-" * len(header))

    for scenario, cps_val in COST_SCENARIOS.items():
        # Long-only (full capital)
        nav_l, nt_l, _ = sim_long_only(
            cl, hi, lo, vo, tb, regime_h4, wi, cps=cps_val)
        m_l = _metrics(nav_l, wi, nt_l)
        results[f"long_{scenario}"] = m_l
        print(f"{'long':>12s} {scenario:6s} {m_l['sharpe']:8.4f} {m_l['cagr']:8.2f} "
              f"{m_l['mdd']:8.2f} {m_l['calmar']:8.4f} {m_l['trades']:7d}")

        # Combined (50/50)
        nav_c, ntl, nts, _, _ = sim_combined(
            cl, hi, lo, vo, tb, regime_h4, wi,
            cps=cps_val, funding_per_bar=FUNDING_PER_BAR)
        m_c = _metrics(nav_c, wi, ntl + nts)
        results[f"combined_{scenario}"] = m_c
        results[f"combined_{scenario}"]["nt_long"] = ntl
        results[f"combined_{scenario}"]["nt_short"] = nts
        print(f"{'combined':>12s} {scenario:6s} {m_c['sharpe']:8.4f} {m_c['cagr']:8.2f} "
              f"{m_c['mdd']:8.2f} {m_c['calmar']:8.4f} {ntl + nts:7d}")

    # Delta table
    print(f"\n  DELTA (combined - long):")
    for scenario in COST_SCENARIOS:
        l = results[f"long_{scenario}"]
        c = results[f"combined_{scenario}"]
        print(f"    {scenario:6s}  dSharpe={c['sharpe']-l['sharpe']:+.4f}  "
              f"dCAGR={c['cagr']-l['cagr']:+.2f}%  "
              f"dMDD={c['mdd']-l['mdd']:+.2f}%  "
              f"dCalmar={c['calmar']-l['calmar']:+.4f}")

    return results


# =========================================================================
# T4: BOOTSTRAP VCBB (500 paths, combined vs long-only h2h)
# =========================================================================

def run_t4_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print(f"T4: BOOTSTRAP VCBB ({N_BOOT} paths, combined vs long-only h2h)")
    print("=" * 80)

    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    print("  Generating bootstrap paths...", end=" ", flush=True)
    t0 = time.time()
    boot_paths = []
    for _ in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb,
        )
        boot_paths.append((
            np.concatenate([cl[:wi], bcl]),
            np.concatenate([hi[:wi], bhi]),
            np.concatenate([lo[:wi], blo]),
            np.concatenate([vo[:wi], bvo]),
            np.concatenate([tb[:wi], btb]),
        ))
    print(f"done ({time.time() - t0:.1f}s)")

    # Run long-only and combined on each path
    long_sharpes = np.zeros(N_BOOT)
    long_cagrs = np.zeros(N_BOOT)
    long_mdds = np.zeros(N_BOOT)
    comb_sharpes = np.zeros(N_BOOT)
    comb_cagrs = np.zeros(N_BOOT)
    comb_mdds = np.zeros(N_BOOT)

    print("  Running simulations...", flush=True)
    t0 = time.time()
    for b_idx, (bcl, bhi, blo, bvo, btb) in enumerate(boot_paths):
        # Long-only
        nav_l, nt_l, _ = sim_long_only(bcl, bhi, blo, bvo, btb, regime_h4, wi)
        m_l = _metrics(nav_l, wi, nt_l)
        long_sharpes[b_idx] = m_l["sharpe"]
        long_cagrs[b_idx] = m_l["cagr"]
        long_mdds[b_idx] = m_l["mdd"]

        # Combined
        nav_c, ntl, nts, _, _ = sim_combined(
            bcl, bhi, blo, bvo, btb, regime_h4, wi,
            funding_per_bar=FUNDING_PER_BAR)
        m_c = _metrics(nav_c, wi, ntl + nts)
        comb_sharpes[b_idx] = m_c["sharpe"]
        comb_cagrs[b_idx] = m_c["cagr"]
        comb_mdds[b_idx] = m_c["mdd"]

        if (b_idx + 1) % 100 == 0:
            print(f"    {b_idx + 1}/{N_BOOT} done ({time.time() - t0:.1f}s)", flush=True)

    elapsed = time.time() - t0
    print(f"  Simulations complete ({elapsed:.1f}s)")

    # Results
    results = {}
    for label, sharpes, cagrs, mdds in [
        ("long", long_sharpes, long_cagrs, long_mdds),
        ("combined", comb_sharpes, comb_cagrs, comb_mdds),
    ]:
        results[label] = {
            "sharpe_median": float(np.median(sharpes)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_p95": float(np.percentile(sharpes, 95)),
            "cagr_median": float(np.median(cagrs)),
            "cagr_p5": float(np.percentile(cagrs, 5)),
            "cagr_p95": float(np.percentile(cagrs, 95)),
            "mdd_median": float(np.median(mdds)),
            "mdd_p5": float(np.percentile(mdds, 5)),
            "mdd_p95": float(np.percentile(mdds, 95)),
            "p_cagr_gt0": float(np.mean(cagrs > 0)),
            "p_sharpe_gt0": float(np.mean(sharpes > 0)),
        }
        r = results[label]
        print(f"\n  {label:10s}  Sharpe={r['sharpe_median']:.4f} "
              f"[{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"CAGR={r['cagr_median']:.2f}% [{r['cagr_p5']:.2f}, {r['cagr_p95']:.2f}]  "
              f"MDD={r['mdd_median']:.2f}%  P(CAGR>0)={r['p_cagr_gt0']:.3f}")

    # Head-to-head
    d_sharpe = comb_sharpes - long_sharpes
    d_cagr = comb_cagrs - long_cagrs
    d_mdd = comb_mdds - long_mdds

    sw = np.sum(d_sharpe > 0)
    cw = np.sum(d_cagr > 0)
    mw = np.sum(d_mdd < 0)

    print(f"\n  HEAD-TO-HEAD (combined vs long-only) across {N_BOOT} paths:")
    print(f"    Sharpe wins: {sw}/{N_BOOT} ({sw/N_BOOT*100:.1f}%)")
    print(f"    CAGR wins:   {cw}/{N_BOOT} ({cw/N_BOOT*100:.1f}%)")
    print(f"    MDD wins:    {mw}/{N_BOOT} ({mw/N_BOOT*100:.1f}%)")
    print(f"    Mean dSharpe: {np.mean(d_sharpe):+.4f}")
    print(f"    Mean dCAGR:   {np.mean(d_cagr):+.2f}%")
    print(f"    Mean dMDD:    {np.mean(d_mdd):+.2f}%")

    results["h2h"] = {
        "sharpe_win_pct": float(sw / N_BOOT * 100),
        "sharpe_mean_delta": float(np.mean(d_sharpe)),
        "cagr_win_pct": float(cw / N_BOOT * 100),
        "cagr_mean_delta": float(np.mean(d_cagr)),
        "mdd_win_pct": float(mw / N_BOOT * 100),
        "mdd_mean_delta": float(np.mean(d_mdd)),
    }

    return results


# =========================================================================
# T5: CORRELATION ANALYSIS — short-side vs long-side return streams
# =========================================================================

def run_t5_correlation(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T5: CORRELATION ANALYSIS — long vs short return streams")
    print("=" * 80)

    # Get per-bar returns for both sides
    _, _, rets_l = sim_long_only(cl, hi, lo, vo, tb, regime_h4, wi)
    _, _, rets_s = sim_short_only(cl, hi, lo, vo, tb, regime_h4, wi)

    # Post-warmup only
    rl = rets_l[wi:]
    rs = rets_s[wi:]

    # Full-sample correlation
    mask = (np.abs(rl) > 1e-15) | (np.abs(rs) > 1e-15)  # at least one active
    rl_active = rl[mask]
    rs_active = rs[mask]

    if len(rl_active) > 10:
        rho_p, p_p = pearsonr(rl_active, rs_active)
        rho_s, p_s = spearmanr(rl_active, rs_active)
    else:
        rho_p = rho_s = p_p = p_s = float("nan")

    print(f"\n  Active bars (either side trading): {np.sum(mask)} / {len(rl)}")
    print(f"  Pearson rho:  {rho_p:.4f} (p={p_p:.4e})")
    print(f"  Spearman rho: {rho_s:.4f} (p={p_s:.4e})")

    # Bars where BOTH sides are active simultaneously
    both_active = (np.abs(rl) > 1e-15) & (np.abs(rs) > 1e-15)
    n_both = np.sum(both_active)
    print(f"\n  Bars where BOTH sides active: {n_both} / {len(rl)} ({n_both/len(rl)*100:.2f}%)")

    if n_both > 10:
        rho_both, p_both = pearsonr(rl[both_active], rs[both_active])
        print(f"  Correlation when both active: {rho_both:.4f} (p={p_both:.4e})")
    else:
        rho_both = float("nan")
        print(f"  Too few concurrent bars for correlation")

    # Only-long bars vs only-short bars
    only_long = (np.abs(rl) > 1e-15) & (np.abs(rs) < 1e-15)
    only_short = (np.abs(rl) < 1e-15) & (np.abs(rs) > 1e-15)
    print(f"\n  Bars only LONG active:  {np.sum(only_long)}")
    print(f"  Bars only SHORT active: {np.sum(only_short)}")
    print(f"  Bars neither active:    {np.sum(~mask)}")

    # If regime-gated properly, both shouldn't be active at same time
    # (long = regime ON, short = regime OFF). Any overlap = lag from EMA crossover.
    if n_both > 0:
        print(f"\n  NOTE: {n_both} concurrent bars exist due to signal lag "
              "(EMA crossover doesn't align exactly with regime switch)")

    # Rolling correlation (monthly blocks)
    block_size = 6 * 30  # ~30 days of H4 bars
    n_blocks = len(rl) // block_size
    rolling_rhos = []
    for b in range(n_blocks):
        s = b * block_size
        e = s + block_size
        rl_b = rl[s:e]
        rs_b = rs[s:e]
        mask_b = (np.abs(rl_b) > 1e-15) | (np.abs(rs_b) > 1e-15)
        if np.sum(mask_b) > 5:
            rho_b, _ = pearsonr(rl_b[mask_b], rs_b[mask_b])
            rolling_rhos.append(rho_b)
        else:
            rolling_rhos.append(float("nan"))

    rolling_rhos = np.array(rolling_rhos)
    valid_rhos = rolling_rhos[~np.isnan(rolling_rhos)]
    if len(valid_rhos) > 0:
        print(f"\n  Rolling monthly correlation ({len(valid_rhos)} valid blocks):")
        print(f"    Mean: {np.mean(valid_rhos):.4f}  Median: {np.median(valid_rhos):.4f}")
        print(f"    Min:  {np.min(valid_rhos):.4f}  Max: {np.max(valid_rhos):.4f}")

    results = {
        "pearson_rho": float(rho_p),
        "pearson_p": float(p_p),
        "spearman_rho": float(rho_s),
        "spearman_p": float(p_s),
        "n_both_active": int(n_both),
        "rho_both_active": float(rho_both) if not math.isnan(rho_both) else None,
        "n_only_long": int(np.sum(only_long)),
        "n_only_short": int(np.sum(only_short)),
    }
    if len(valid_rhos) > 0:
        results["rolling_rho_mean"] = float(np.mean(valid_rhos))
        results["rolling_rho_median"] = float(np.median(valid_rhos))

    return results


# =========================================================================
# T6: FUNDING RATE SENSITIVITY SWEEP
# =========================================================================

def run_t6_funding_sweep(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T6: FUNDING RATE SENSITIVITY SWEEP (short-only)")
    print("=" * 80)

    results = {}
    header = (f"{'Fund_bps':>10s} {'Fund_ann%':>10s} {'Sharpe':>8s} {'CAGR%':>8s} "
              f"{'MDD%':>8s} {'Calmar':>8s}")
    print(f"\n{header}")
    print("-" * len(header))

    for fund_bps in FUNDING_SWEEP:
        fpb = fund_bps / 10_000.0
        ann_pct = fund_bps * 6 * 365.25 / 100  # annualized percentage
        nav, nt, _ = sim_short_only(
            cl, hi, lo, vo, tb, regime_h4, wi,
            funding_per_bar=fpb)
        m = _metrics(nav, wi, nt)
        results[fund_bps] = m
        results[fund_bps]["fund_ann_pct"] = ann_pct
        print(f"{fund_bps:10.2f} {ann_pct:10.2f} {m['sharpe']:8.4f} {m['cagr']:8.2f} "
              f"{m['mdd']:8.2f} {m['calmar']:8.4f}")

    # Find breakeven funding rate (where Sharpe crosses zero)
    sharpes = [(fb, results[fb]["sharpe"]) for fb in FUNDING_SWEEP]
    breakeven = None
    for i in range(len(sharpes) - 1):
        if sharpes[i][1] > 0 and sharpes[i + 1][1] <= 0:
            # Linear interpolation
            fb1, s1 = sharpes[i]
            fb2, s2 = sharpes[i + 1]
            breakeven = fb1 + (fb2 - fb1) * s1 / (s1 - s2)
            break
    if sharpes[0][1] <= 0:
        breakeven = 0.0  # already negative at zero funding

    if breakeven is not None:
        print(f"\n  Sharpe breakeven funding rate: ~{breakeven:.2f} bps/4h bar "
              f"(~{breakeven * 6 * 365.25 / 100:.1f}% annualized)")
    else:
        print(f"\n  Sharpe remains positive across entire funding sweep range")

    results["breakeven_bps"] = breakeven

    return results


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(t0_res, t1_res, t2_res, t3_res, t4_res, t5_res, t6_res):
    out = {
        "bear_stats": t0_res,
        "short_factorial": {},
        "short_timescale": {},
        "combined_vs_long": t3_res,
        "bootstrap": t4_res,
        "correlation": t5_res,
        "funding_sweep": {},
    }

    # T1
    for fl in t1_res:
        out["short_factorial"][fl] = {}
        for sc in t1_res[fl]:
            out["short_factorial"][fl][sc] = t1_res[fl][sc]

    # T2
    for sp in SLOW_PERIODS:
        out["short_timescale"][str(sp)] = t2_res[sp]

    # T6
    for fb in FUNDING_SWEEP:
        out["funding_sweep"][str(fb)] = t6_res[fb]
    out["funding_sweep"]["breakeven_bps"] = t6_res.get("breakeven_bps")

    # JSON
    json_path = OUTDIR / "x11_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV short factorial
    csv_path = OUTDIR / "x11_short_factorial.csv"
    fields = ["funding", "scenario", "sharpe", "cagr", "mdd", "calmar", "trades"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for fl in t1_res:
            for sc in ["smart", "base", "harsh"]:
                row = {"funding": fl, "scenario": sc}
                row.update(t1_res[fl][sc])
                w.writerow(row)
    print(f"Saved: {csv_path}")

    # CSV timescale
    csv_ts = OUTDIR / "x11_timescale_table.csv"
    with open(csv_ts, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slow_period", "sharpe", "cagr", "mdd", "calmar", "trades"])
        for sp in SLOW_PERIODS:
            m = t2_res[sp]
            w.writerow([sp, f"{m['sharpe']:.4f}", f"{m['cagr']:.2f}",
                        f"{m['mdd']:.2f}", f"{m['calmar']:.4f}", m["trades"]])
    print(f"Saved: {csv_ts}")

    # CSV funding sweep
    csv_fund = OUTDIR / "x11_funding_sweep.csv"
    with open(csv_fund, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fund_bps_per_bar", "fund_ann_pct", "sharpe", "cagr", "mdd", "calmar"])
        for fb in FUNDING_SWEEP:
            m = t6_res[fb]
            w.writerow([f"{fb:.2f}", f"{m['fund_ann_pct']:.2f}",
                        f"{m['sharpe']:.4f}", f"{m['cagr']:.2f}",
                        f"{m['mdd']:.2f}", f"{m['calmar']:.4f}"])
    print(f"Saved: {csv_fund}")

    # CSV bootstrap
    csv_boot = OUTDIR / "x11_bootstrap_table.csv"
    boot_fields = ["config", "sharpe_median", "sharpe_p5", "sharpe_p95",
                   "cagr_median", "cagr_p5", "cagr_p95",
                   "mdd_median", "mdd_p5", "mdd_p95",
                   "p_cagr_gt0", "p_sharpe_gt0"]
    with open(csv_boot, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=boot_fields)
        w.writeheader()
        for label in ["long", "combined"]:
            if label in t4_res:
                row = {"config": label}
                row.update({k: t4_res[label].get(k)
                           for k in boot_fields if k != "config"})
                w.writerow(row)
    print(f"Saved: {csv_boot}")


# =========================================================================
# VERDICT LOGIC
# =========================================================================

def print_verdict(t0_res, t1_res, t2_res, t3_res, t4_res, t5_res, t6_res):
    print("\n" + "=" * 80)
    print("X11 VERDICT — SHORT-SIDE COMPLEMENT FEASIBILITY")
    print("=" * 80)

    gates = []

    # Gate 1: Does the short signal have positive Sharpe at base cost + funding?
    short_base_fund = t1_res.get("fund_1bps", {}).get("harsh", {})
    short_sharpe = short_base_fund.get("sharpe", 0)
    g1 = short_sharpe > 0
    gates.append(("G1: Short Sharpe > 0 (harsh + funding)", g1, f"{short_sharpe:.4f}"))

    # Gate 2: Timescale robustness — positive Sharpe in ≥10/16 timescales
    n_pos = sum(1 for sp in SLOW_PERIODS if t2_res.get(sp, {}).get("sharpe", 0) > 0)
    g2 = n_pos >= 10
    gates.append(("G2: Positive Sharpe >=10/16 timescales", g2, f"{n_pos}/16"))

    # Gate 3: Combined beats long-only on Sharpe (harsh cost)
    comb = t3_res.get("combined_harsh", {}).get("sharpe", 0)
    long = t3_res.get("long_harsh", {}).get("sharpe", 0)
    g3 = comb > long
    gates.append(("G3: Combined Sharpe > Long Sharpe (harsh)", g3,
                  f"{comb:.4f} vs {long:.4f}"))

    # Gate 4: Bootstrap h2h — combined wins Sharpe ≥60% of paths
    h2h = t4_res.get("h2h", {})
    sw_pct = h2h.get("sharpe_win_pct", 0)
    g4 = sw_pct >= 60
    gates.append(("G4: Bootstrap Sharpe wins >=60%", g4, f"{sw_pct:.1f}%"))

    # Gate 5: Correlation — Pearson rho < 0.3 (low dependence)
    rho = t5_res.get("pearson_rho", 1.0)
    g5 = abs(rho) < 0.3
    gates.append(("G5: |Correlation| < 0.3", g5, f"{rho:.4f}"))

    # Gate 6: Funding breakeven > 2.0 bps/bar (robust to real funding)
    be = t6_res.get("breakeven_bps")
    g6 = be is not None and be > 2.0
    gates.append(("G6: Funding breakeven > 2.0 bps/bar", g6,
                  f"{be:.2f}" if be is not None else "N/A"))

    # Print gates
    n_pass = 0
    for label, passed, value in gates:
        status = "PASS" if passed else "FAIL"
        if passed:
            n_pass += 1
        print(f"  [{status:4s}] {label}: {value}")

    # Verdict
    print(f"\n  Gates passed: {n_pass}/{len(gates)}")
    if n_pass == len(gates):
        verdict = "PROCEED"
        print(f"\n  VERDICT: {verdict}")
        print("  All gates passed. Short-side complement shows feasibility.")
        print("  Next steps: obtain futures data, build full Tier 1-3 evaluation.")
    elif n_pass >= 4:
        verdict = "MARGINAL"
        print(f"\n  VERDICT: {verdict}")
        print("  Partial evidence. Investigate failed gates before proceeding.")
    else:
        verdict = "REJECT"
        print(f"\n  VERDICT: {verdict}")
        print("  Short-side complement does not show sufficient feasibility.")
        print("  The idle exposure during regime OFF is a feature, not a bug.")

    return verdict


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 80)
    print("X11 RESEARCH — SHORT-SIDE COMPLEMENT FOR E5+EMA21D1")
    print(f"  Data: {DATA} (SPOT — feasibility gate only)")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  E5 params: slow={SLOW}, trail={TRAIL}, vdo_thr={VDO_THR}, "
          f"d1_ema={D1_EMA_P}")
    print(f"  Short: mirror EMA crossover + ATR trail, regime OFF only")
    print(f"  Funding: {FUNDING_BPS_PER_BAR} bps/4h bar "
          f"(~{FUNDING_BPS_PER_BAR * 6 * 365.25 / 100:.1f}%/yr)")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")
    print("=" * 80)

    t_start = time.time()

    # Load raw arrays
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    # Compute D1 regime mask
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct, D1_EMA_P)

    # Warmup index
    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # T0: Bear-period characterization (fast)
    t0_res = run_t0_bear_stats(cl, regime_h4, wi)

    # T1: Short-only factorial (fast)
    t1_res = run_t1_short_factorial(cl, hi, lo, vo, tb, regime_h4, wi)

    # T2: Timescale robustness (fast)
    t2_res = run_t2_timescale(cl, hi, lo, vo, tb, regime_h4, wi)

    # T6: Funding sensitivity (fast)
    t6_res = run_t6_funding_sweep(cl, hi, lo, vo, tb, regime_h4, wi)

    # T5: Correlation analysis (fast)
    t5_res = run_t5_correlation(cl, hi, lo, vo, tb, regime_h4, wi)

    # T3: Combined vs long-only (moderate)
    t3_res = run_t3_combined(cl, hi, lo, vo, tb, regime_h4, wi)

    # T4: Bootstrap (slow — run last)
    t4_res = run_t4_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi)

    # Save
    save_results(t0_res, t1_res, t2_res, t3_res, t4_res, t5_res, t6_res)

    # Verdict
    verdict = print_verdict(t0_res, t1_res, t2_res, t3_res, t4_res, t5_res, t6_res)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 80}")
    print(f"X11 BENCHMARK COMPLETE — {elapsed:.0f}s total — VERDICT: {verdict}")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
