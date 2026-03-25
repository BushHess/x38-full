#!/usr/bin/env python3
"""X12 Research — Why Does E5 Win If It Doesn't Fix Churn?

Central question: E5's robust ATR was designed to reduce stop-churn, but
evidence shows short/medium trailing-stop damage is still worse than E0.
Yet E5 wins on headline metrics. If churn repair fails, where does the
edge actually come from?

Independent prior (vtrend/research/x1): path-state drives 67% of edge.
X12 = replication on btc-spot-dev data (50 bps, 2019+) + extension
(churn audit, timescale robustness, bootstrap OOS).

Strategies:
  E0+EMA1D21 — standard ATR(14) trail + D1 EMA(21) regime
  E5+EMA1D21 — robust ATR(20, Q90/100) trail + D1 EMA(21) regime
  Entry logic identical. Only trail stop differs.

Tests:
  T0: Churn Audit — confirm design-intent failure
  T1: Divergence Cascade Map — census of shared vs unique trades
  T2: Matched-Trade Mechanism — per-trade trail/exit forensics
  T3: Cascade Counterfactual — decompose headline delta (mechanical vs path)
  T4: Timescale Robustness — T0+T3 across 16 slow_periods
  T5: Bootstrap Confidence — 500 VCBB paths for OOS CI

Vectorized sim only, no BacktestEngine.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed          # noqa: E402
from v10.core.types import SCENARIOS        # noqa: E402
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb  # noqa: E402

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

SLOW = 120
TRAIL = 3.0
D1_EMA_P = 21

ATR_P = 14                # E0 standard ATR period
RATR_CAP_Q = 0.90         # E5 robust ATR: Q90 cap
RATR_CAP_LB = 100         # E5 robust ATR: lookback for cap
RATR_PERIOD = 20           # E5 robust ATR: Wilder period

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

N_BOOT = 500
BLKSZ = 60
SEED = 42

CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0

CHURN_WINDOW = 20          # bars: trail_stop exit → re-entry within this = churn

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# FAST INDICATORS (vectorized)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high, low, close, period=ATR_P):
    """Standard Wilder ATR."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
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
# VECTORIZED SIMS: E0+EMA1D21 and E5+EMA1D21 with trade logging
# =========================================================================

def _sim_core(cl, hi, lo, vo, tb, regime_h4, wi,
              atr_arr, slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH):
    """Shared sim core. atr_arr = standard ATR or robust ATR array.

    Returns (nav, trades) where trades is list of dicts.
    """
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    vd = _vdo(cl, hi, lo, vo, tb)

    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    entry_px = 0.0
    entry_bar = 0
    entry_cost = 0.0
    exit_reason = ""

    nav = np.zeros(n)
    trades = []

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp
                entry_bar = i
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0
                inp = True
                pk = p
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                a_val = atr_arr[i - 1] if not math.isnan(atr_arr[i - 1]) else 0.0
                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "entry_px": entry_px,
                    "exit_px": fp,
                    "peak_px": pk,
                    "pnl_usd": pnl,
                    "ret_pct": ret,
                    "bars_held": i - entry_bar,
                    "exit_reason": exit_reason,
                    "trail_dist": trail_mult * a_val,
                })
                cash = received
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1

        nav[i] = cash + bq * p

        a_val = atr_arr[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * a_val
            if p < ts:
                exit_reason = "trail_stop"
                px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    # Close open position at end
    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        a_val = atr_arr[-1] if not math.isnan(atr_arr[-1]) else 0.0
        trades.append({
            "entry_bar": entry_bar,
            "exit_bar": n - 1,
            "entry_px": entry_px,
            "exit_px": cl[-1],
            "peak_px": pk,
            "pnl_usd": pnl,
            "ret_pct": ret,
            "bars_held": (n - 1) - entry_bar,
            "exit_reason": "eod",
            "trail_dist": trail_mult * a_val,
        })
        cash = received
        bq = 0.0
        nt += 1
        nav[-1] = cash

    return nav, trades


def sim_e0_d1(cl, hi, lo, vo, tb, regime_h4, wi,
              slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH):
    """E0+EMA1D21: standard ATR(14) trail + D1 regime."""
    at = _atr(hi, lo, cl, ATR_P)
    return _sim_core(cl, hi, lo, vo, tb, regime_h4, wi, at,
                     slow_period, trail_mult, cps)


def sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi,
              slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH):
    """E5+EMA1D21: robust ATR(20, Q90/100) trail + D1 regime."""
    ratr = _robust_atr(hi, lo, cl)
    return _sim_core(cl, hi, lo, vo, tb, regime_h4, wi, ratr,
                     slow_period, trail_mult, cps)


# =========================================================================
# TRADE MATCHING
# =========================================================================

def match_trades(e0_trades, e5_trades):
    """Match trades by entry_bar. Returns (matched, e0_only, e5_only).

    matched: list of (e0_trade, e5_trade) tuples
    e0_only: list of e0 trades with no E5 match
    e5_only: list of e5 trades with no E0 match
    """
    e0_by_entry = {t["entry_bar"]: t for t in e0_trades}
    e5_by_entry = {t["entry_bar"]: t for t in e5_trades}

    shared_bars = sorted(set(e0_by_entry) & set(e5_by_entry))
    e0_only_bars = sorted(set(e0_by_entry) - set(e5_by_entry))
    e5_only_bars = sorted(set(e5_by_entry) - set(e0_by_entry))

    matched = [(e0_by_entry[b], e5_by_entry[b]) for b in shared_bars]
    e0_only = [e0_by_entry[b] for b in e0_only_bars]
    e5_only = [e5_by_entry[b] for b in e5_only_bars]

    return matched, e0_only, e5_only


# =========================================================================
# T0: CHURN AUDIT
# =========================================================================

def run_t0_churn(e0_trades, e5_trades):
    """T0: Measure churn rate per strategy. Churn = trail_stop exit followed
    by re-entry within CHURN_WINDOW bars."""
    print("\n" + "=" * 70)
    print("T0: CHURN AUDIT")
    print("=" * 70)

    results = {}
    for label, trades in [("E0", e0_trades), ("E5", e5_trades)]:
        total = len(trades)
        trail_exits = [t for t in trades if t["exit_reason"] == "trail_stop"]
        trend_exits = [t for t in trades if t["exit_reason"] == "trend_exit"]
        n_trail = len(trail_exits)
        n_trend = len(trend_exits)

        # Check churn: trail_stop exit followed by re-entry within window
        churn_count = 0
        churn_pnl = 0.0
        non_churn_trail_pnl = 0.0

        for idx, t in enumerate(trades):
            if t["exit_reason"] != "trail_stop":
                continue
            # Look for next trade
            if idx + 1 < total:
                next_t = trades[idx + 1]
                gap = next_t["entry_bar"] - t["exit_bar"]
                if gap <= CHURN_WINDOW:
                    churn_count += 1
                    churn_pnl += t["pnl_usd"]
                else:
                    non_churn_trail_pnl += t["pnl_usd"]
            else:
                non_churn_trail_pnl += t["pnl_usd"]

        churn_rate = churn_count / n_trail if n_trail > 0 else 0.0

        # Duration buckets
        short_trades = [t for t in trades if t["bars_held"] < 20]
        medium_trades = [t for t in trades if 20 <= t["bars_held"] <= 80]
        long_trades = [t for t in trades if t["bars_held"] > 80]

        r = {
            "total_trades": total,
            "trail_stop_exits": n_trail,
            "trend_exits": n_trend,
            "churn_count": churn_count,
            "churn_rate": churn_rate,
            "churn_pnl": churn_pnl,
            "non_churn_trail_pnl": non_churn_trail_pnl,
            "short_count": len(short_trades),
            "short_pnl": sum(t["pnl_usd"] for t in short_trades),
            "short_mean_pnl": np.mean([t["pnl_usd"] for t in short_trades]) if short_trades else 0.0,
            "medium_count": len(medium_trades),
            "medium_pnl": sum(t["pnl_usd"] for t in medium_trades),
            "medium_mean_pnl": np.mean([t["pnl_usd"] for t in medium_trades]) if medium_trades else 0.0,
            "long_count": len(long_trades),
            "long_pnl": sum(t["pnl_usd"] for t in long_trades),
            "long_mean_pnl": np.mean([t["pnl_usd"] for t in long_trades]) if long_trades else 0.0,
        }
        results[label] = r

        print(f"\n  {label}:")
        print(f"    Trades: {total}  (trail_stop: {n_trail}, trend: {n_trend})")
        print(f"    Churn: {churn_count}/{n_trail} = {churn_rate:.1%}")
        print(f"    Churn PnL: ${churn_pnl:+,.0f}  Non-churn trail PnL: ${non_churn_trail_pnl:+,.0f}")
        print(f"    Short(<20): {len(short_trades)} trades, ${sum(t['pnl_usd'] for t in short_trades):+,.0f}")
        print(f"    Medium(20-80): {len(medium_trades)} trades, ${sum(t['pnl_usd'] for t in medium_trades):+,.0f}")
        print(f"    Long(>80): {len(long_trades)} trades, ${sum(t['pnl_usd'] for t in long_trades):+,.0f}")

    # Deltas
    d = {
        "d_churn_rate": results["E5"]["churn_rate"] - results["E0"]["churn_rate"],
        "d_churn_pnl": results["E5"]["churn_pnl"] - results["E0"]["churn_pnl"],
        "d_short_pnl": results["E5"]["short_pnl"] - results["E0"]["short_pnl"],
        "d_medium_pnl": results["E5"]["medium_pnl"] - results["E0"]["medium_pnl"],
        "d_long_pnl": results["E5"]["long_pnl"] - results["E0"]["long_pnl"],
    }
    results["delta"] = d

    g0 = d["d_churn_rate"] >= 0
    print(f"\n  Delta churn rate: {d['d_churn_rate']:+.4f}")
    print(f"  G0 (churn repair dead): {'YES' if g0 else 'NO'}")

    return results


# =========================================================================
# T1: DIVERGENCE CASCADE MAP
# =========================================================================

def run_t1_cascade(nav_e0, nav_e5, matched, e0_only, e5_only, wi):
    """T1: Census of trade categories + cascade structure."""
    print("\n" + "=" * 70)
    print("T1: DIVERGENCE CASCADE MAP")
    print("=" * 70)

    # Classify matched trades
    same_exit = [(a, b) for a, b in matched if a["exit_bar"] == b["exit_bar"]]
    diff_exit = [(a, b) for a, b in matched if a["exit_bar"] != b["exit_bar"]]

    headline_delta = float(nav_e5[wi:].sum() - nav_e0[wi:].sum()) if len(nav_e0) > wi else 0.0
    # Use final NAV difference
    headline_nav_delta = float(nav_e5[-1] - nav_e0[-1])

    # PnL summaries
    def _pnl_stats(trades_or_pairs, pair_mode=False):
        if pair_mode:
            pnls = [b["pnl_usd"] - a["pnl_usd"] for a, b in trades_or_pairs]
        else:
            pnls = [t["pnl_usd"] for t in trades_or_pairs]
        if not pnls:
            return {"count": 0, "sum": 0.0, "mean": 0.0, "median": 0.0}
        return {
            "count": len(pnls),
            "sum": sum(pnls),
            "mean": float(np.mean(pnls)),
            "median": float(np.median(pnls)),
        }

    # Cascade analysis: track chains of unique trades between re-syncs
    # Build timeline of all trades from both strategies
    all_events = []
    for a, b in matched:
        all_events.append(("matched", a["entry_bar"], a, b))
    for t in e0_only:
        all_events.append(("e0_only", t["entry_bar"], t, None))
    for t in e5_only:
        all_events.append(("e5_only", t["entry_bar"], None, t))
    all_events.sort(key=lambda x: x[1])

    # Count cascades: seed = matched-diff-exit, cascade = unique trades until next matched
    cascades = []
    current_cascade = None
    for evt_type, _, _, _ in all_events:
        if evt_type == "matched":
            if current_cascade is not None:
                cascades.append(current_cascade)
            current_cascade = None
        else:
            if current_cascade is None:
                current_cascade = {"depth": 0, "e0_only": 0, "e5_only": 0}
            current_cascade["depth"] += 1
            if evt_type == "e0_only":
                current_cascade["e0_only"] += 1
            else:
                current_cascade["e5_only"] += 1
    if current_cascade is not None:
        cascades.append(current_cascade)

    cascade_depths = [c["depth"] for c in cascades] if cascades else [0]

    results = {
        "matched_total": len(matched),
        "matched_same_exit": _pnl_stats(same_exit, pair_mode=True),
        "matched_diff_exit": _pnl_stats(diff_exit, pair_mode=True),
        "e0_only": _pnl_stats(e0_only),
        "e5_only": _pnl_stats(e5_only),
        "headline_nav_delta": headline_nav_delta,
        "n_cascades": len(cascades),
        "cascade_depth_mean": float(np.mean(cascade_depths)),
        "cascade_depth_median": float(np.median(cascade_depths)),
        "cascade_depth_max": int(np.max(cascade_depths)),
    }

    ms = results["matched_same_exit"]
    md = results["matched_diff_exit"]
    print(f"\n  Matched total: {len(matched)} (same-exit: {ms['count']}, diff-exit: {md['count']})")
    print(f"  E0-only: {results['e0_only']['count']}  E5-only: {results['e5_only']['count']}")
    print(f"  Headline NAV delta: ${headline_nav_delta:+,.2f}")
    print(f"\n  Matched same-exit PnL delta: ${ms['sum']:+,.2f} (mean: ${ms['mean']:+,.2f})")
    print(f"  Matched diff-exit PnL delta: ${md['sum']:+,.2f} (mean: ${md['mean']:+,.2f}, median: ${md['median']:+,.2f})")
    print(f"  E0-only PnL: ${results['e0_only']['sum']:+,.2f}")
    print(f"  E5-only PnL: ${results['e5_only']['sum']:+,.2f}")
    print(f"\n  Cascades: {len(cascades)}, depth mean={np.mean(cascade_depths):.1f}, max={np.max(cascade_depths)}")

    return results


# =========================================================================
# T2: MATCHED-TRADE MECHANISM
# =========================================================================

def run_t2_mechanism(matched):
    """T2: For matched-diff-exit trades, forensic analysis."""
    print("\n" + "=" * 70)
    print("T2: MATCHED-TRADE MECHANISM")
    print("=" * 70)

    diff_exit = [(a, b) for a, b in matched if a["exit_bar"] != b["exit_bar"]]

    if not diff_exit:
        print("  No diff-exit matched trades found.")
        return {"diff_exit_count": 0}

    rows = []
    e5_first_count = 0
    e0_first_count = 0

    for e0_t, e5_t in diff_exit:
        d_pnl = e5_t["pnl_usd"] - e0_t["pnl_usd"]
        d_bars = e5_t["bars_held"] - e0_t["bars_held"]
        e5_exits_first = e5_t["exit_bar"] < e0_t["exit_bar"]
        if e5_exits_first:
            e5_first_count += 1
        else:
            e0_first_count += 1

        # Duration bucket (based on E0 holding as reference)
        bh = e0_t["bars_held"]
        if bh < 20:
            bucket = "short"
        elif bh <= 80:
            bucket = "medium"
        else:
            bucket = "long"

        # Winner/loser (based on E0 PnL as reference)
        wl = "winner" if e0_t["pnl_usd"] > 0 else "loser"

        rows.append({
            "entry_bar": e0_t["entry_bar"],
            "e0_exit_bar": e0_t["exit_bar"],
            "e5_exit_bar": e5_t["exit_bar"],
            "e0_pnl": e0_t["pnl_usd"],
            "e5_pnl": e5_t["pnl_usd"],
            "d_pnl": d_pnl,
            "e0_bars": e0_t["bars_held"],
            "e5_bars": e5_t["bars_held"],
            "d_bars": d_bars,
            "e5_exits_first": e5_exits_first,
            "e0_exit_reason": e0_t["exit_reason"],
            "e5_exit_reason": e5_t["exit_reason"],
            "e0_trail_dist": e0_t["trail_dist"],
            "e5_trail_dist": e5_t["trail_dist"],
            "duration_bucket": bucket,
            "winner_loser": wl,
        })

    pnl_deltas = [r["d_pnl"] for r in rows]
    e5_wins = sum(1 for d in pnl_deltas if d > 0)

    # Sub-bucket analysis
    buckets = {}
    for bucket_name in ["short", "medium", "long"]:
        sub = [r for r in rows if r["duration_bucket"] == bucket_name]
        if sub:
            sub_d = [r["d_pnl"] for r in sub]
            buckets[bucket_name] = {
                "count": len(sub),
                "sum_d_pnl": sum(sub_d),
                "mean_d_pnl": float(np.mean(sub_d)),
                "median_d_pnl": float(np.median(sub_d)),
            }
        else:
            buckets[bucket_name] = {"count": 0, "sum_d_pnl": 0.0, "mean_d_pnl": 0.0, "median_d_pnl": 0.0}

    wl_buckets = {}
    for wl_name in ["winner", "loser"]:
        sub = [r for r in rows if r["winner_loser"] == wl_name]
        if sub:
            sub_d = [r["d_pnl"] for r in sub]
            wl_buckets[wl_name] = {
                "count": len(sub),
                "sum_d_pnl": sum(sub_d),
                "mean_d_pnl": float(np.mean(sub_d)),
            }
        else:
            wl_buckets[wl_name] = {"count": 0, "sum_d_pnl": 0.0, "mean_d_pnl": 0.0}

    results = {
        "diff_exit_count": len(diff_exit),
        "e5_exits_first": e5_first_count,
        "e0_exits_first": e0_first_count,
        "e5_wins_pnl": e5_wins,
        "mean_d_pnl": float(np.mean(pnl_deltas)),
        "median_d_pnl": float(np.median(pnl_deltas)),
        "sum_d_pnl": sum(pnl_deltas),
        "duration_buckets": buckets,
        "winner_loser_buckets": wl_buckets,
        "detail_rows": rows,
    }

    g2 = float(np.median(pnl_deltas)) > 0

    print(f"\n  Diff-exit trades: {len(diff_exit)}")
    print(f"  E5 exits first: {e5_first_count}  E0 exits first: {e0_first_count}")
    print(f"  E5 wins PnL: {e5_wins}/{len(diff_exit)}")
    print(f"  PnL delta: mean=${np.mean(pnl_deltas):+,.2f}, median=${np.median(pnl_deltas):+,.2f}, sum=${sum(pnl_deltas):+,.2f}")
    print(f"\n  Duration buckets:")
    for bn in ["short", "medium", "long"]:
        b = buckets[bn]
        print(f"    {bn:8s}: {b['count']:3d} trades, sum=${b['sum_d_pnl']:+,.2f}, mean=${b['mean_d_pnl']:+,.2f}")
    print(f"\n  Winner/Loser buckets:")
    for wn in ["winner", "loser"]:
        b = wl_buckets[wn]
        print(f"    {wn:8s}: {b['count']:3d} trades, sum=${b['sum_d_pnl']:+,.2f}, mean=${b['mean_d_pnl']:+,.2f}")
    print(f"\n  G2 (median PnL delta > 0): {'YES' if g2 else 'NO'}")

    return results


# =========================================================================
# T3: CASCADE COUNTERFACTUAL
# =========================================================================

def run_t3_decomposition(nav_e0, nav_e5, matched, e0_only, e5_only, wi):
    """T3: Decompose headline delta into matched (mechanical) vs cascade."""
    print("\n" + "=" * 70)
    print("T3: CASCADE COUNTERFACTUAL")
    print("=" * 70)

    headline_delta = float(nav_e5[-1] - nav_e0[-1])

    # PnL-based decomposition
    matched_delta = sum(b["pnl_usd"] - a["pnl_usd"] for a, b in matched)
    e5_only_pnl = sum(t["pnl_usd"] for t in e5_only)
    e0_only_pnl = sum(t["pnl_usd"] for t in e0_only)
    cascade_delta = e5_only_pnl - e0_only_pnl
    residual = headline_delta - matched_delta - cascade_delta

    # Return-based decomposition (compounding-neutral)
    matched_ret_delta = sum(b["ret_pct"] - a["ret_pct"] for a, b in matched)
    e5_only_ret = sum(t["ret_pct"] for t in e5_only)
    e0_only_ret = sum(t["ret_pct"] for t in e0_only)
    cascade_ret_delta = e5_only_ret - e0_only_ret

    denom_ret = matched_ret_delta + cascade_ret_delta
    cf_pnl = cascade_delta / headline_delta if abs(headline_delta) > 1e-6 else 0.0
    cf_ret = cascade_ret_delta / denom_ret if abs(denom_ret) > 1e-6 else 0.0

    results = {
        "headline_delta": headline_delta,
        "matched_delta": matched_delta,
        "cascade_delta": cascade_delta,
        "residual": residual,
        "e5_only_pnl": e5_only_pnl,
        "e0_only_pnl": e0_only_pnl,
        "matched_ret_delta": matched_ret_delta,
        "cascade_ret_delta": cascade_ret_delta,
        "cf_pnl": cf_pnl,
        "cf_ret": cf_ret,
    }

    g1 = cf_ret > 0.5

    print(f"\n  Headline delta (NAV): ${headline_delta:+,.2f}")
    print(f"  Matched delta (PnL): ${matched_delta:+,.2f}")
    print(f"  Cascade delta (PnL): ${cascade_delta:+,.2f}")
    print(f"    E5-only PnL: ${e5_only_pnl:+,.2f}  E0-only PnL: ${e0_only_pnl:+,.2f}")
    print(f"  Residual (compounding): ${residual:+,.2f}")
    print(f"\n  Cascade fraction (PnL): {cf_pnl:.4f}")
    print(f"  Cascade fraction (ret): {cf_ret:.4f}")
    print(f"\n  G1 (cf_ret > 0.5, path dominates): {'YES' if g1 else 'NO'}")

    return results


# =========================================================================
# T4: TIMESCALE ROBUSTNESS
# =========================================================================

def run_t4_timescale(cl, hi, lo, vo, tb, regime_h4, wi):
    """T4: Run T0 + T3 decomposition at 16 slow_periods."""
    print("\n" + "=" * 70)
    print("T4: TIMESCALE ROBUSTNESS")
    print("=" * 70)

    rows = []
    churn_directions = []
    cf_directions = []

    for sp in SLOW_PERIODS:
        nav_e0, e0_t = sim_e0_d1(cl, hi, lo, vo, tb, regime_h4, wi, slow_period=sp)
        nav_e5, e5_t = sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi, slow_period=sp)

        matched, e0_only, e5_only = match_trades(e0_t, e5_t)

        # Churn delta
        def _churn_rate(trades):
            trail_exits = [t for t in trades if t["exit_reason"] == "trail_stop"]
            n_trail = len(trail_exits)
            if n_trail == 0:
                return 0.0
            churn = 0
            for idx, t in enumerate(trades):
                if t["exit_reason"] != "trail_stop":
                    continue
                if idx + 1 < len(trades):
                    gap = trades[idx + 1]["entry_bar"] - t["exit_bar"]
                    if gap <= CHURN_WINDOW:
                        churn += 1
            return churn / n_trail

        cr_e0 = _churn_rate(e0_t)
        cr_e5 = _churn_rate(e5_t)
        d_churn = cr_e5 - cr_e0

        # Decomposition
        headline = float(nav_e5[-1] - nav_e0[-1])
        matched_d = sum(b["pnl_usd"] - a["pnl_usd"] for a, b in matched)
        e5o_pnl = sum(t["pnl_usd"] for t in e5_only)
        e0o_pnl = sum(t["pnl_usd"] for t in e0_only)
        cascade_d = e5o_pnl - e0o_pnl

        matched_ret_d = sum(b["ret_pct"] - a["ret_pct"] for a, b in matched)
        cascade_ret_d = sum(t["ret_pct"] for t in e5_only) - sum(t["ret_pct"] for t in e0_only)
        denom = matched_ret_d + cascade_ret_d
        cf = cascade_ret_d / denom if abs(denom) > 1e-6 else 0.0

        churn_directions.append(1 if d_churn >= 0 else 0)
        cf_directions.append(1 if cf > 0.5 else 0)

        diff_exit_count = sum(1 for a, b in matched if a["exit_bar"] != b["exit_bar"])

        row = {
            "slow_period": sp,
            "d_churn_rate": d_churn,
            "headline_delta": headline,
            "matched_delta": matched_d,
            "cascade_delta": cascade_d,
            "cf_ret": cf,
            "n_matched": len(matched),
            "n_diff_exit": diff_exit_count,
            "n_e0_only": len(e0_only),
            "n_e5_only": len(e5_only),
            "e0_trades": len(e0_t),
            "e5_trades": len(e5_t),
        }
        rows.append(row)

    # Print table
    print(f"\n  {'SP':>4s}  {'dChurn':>8s}  {'Headline':>10s}  {'Matched':>10s}  {'Cascade':>10s}  {'cf_ret':>7s}  {'DiffEx':>6s}  {'E0only':>6s}  {'E5only':>6s}")
    print("  " + "-" * 80)
    for r in rows:
        print(f"  {r['slow_period']:4d}  {r['d_churn_rate']:+8.4f}  ${r['headline_delta']:>9,.0f}  ${r['matched_delta']:>9,.0f}  ${r['cascade_delta']:>9,.0f}  {r['cf_ret']:7.4f}  {r['n_diff_exit']:6d}  {r['n_e0_only']:6d}  {r['n_e5_only']:6d}")

    churn_stable = sum(churn_directions)
    cf_stable = sum(cf_directions)
    g3_churn = churn_stable >= 12
    g3_cf = cf_stable >= 12
    g3 = g3_churn and g3_cf

    print(f"\n  Churn direction (d>=0): {churn_stable}/16 timescales")
    print(f"  cf_ret direction (>0.5): {cf_stable}/16 timescales")
    print(f"  G3 (both stable >=12/16): {'YES' if g3 else 'NO'}")

    return {
        "rows": rows,
        "churn_stable_count": churn_stable,
        "cf_stable_count": cf_stable,
        "g3": g3,
    }


# =========================================================================
# T5: BOOTSTRAP CONFIDENCE
# =========================================================================

def run_t5_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi):
    """T5: 500 VCBB bootstrap paths for OOS confidence."""
    print("\n" + "=" * 70)
    print("T5: BOOTSTRAP CONFIDENCE (500 VCBB paths)")
    print("=" * 70)

    # Prepare bootstrap inputs from post-warmup data
    cl_pw = cl[wi:]
    hi_pw = hi[wi:]
    lo_pw = lo[wi:]
    vo_pw = vo[wi:]
    tb_pw = tb[wi:] if tb is not None else None

    cr, hr, lr, vol_r, tb_r = make_ratios(cl_pw, hi_pw, lo_pw, vo_pw, tb_pw)
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = len(cl) - wi - 1
    p0 = cl[wi]

    rng = np.random.default_rng(SEED)

    boot_headline = np.zeros(N_BOOT)
    boot_cf_ret = np.zeros(N_BOOT)
    boot_d_churn = np.zeros(N_BOOT)

    for b_idx in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)

        # Regime from original D1 data (shared across bootstrap) — use real regime
        # For bootstrap, we run sims on synthetic H4 but with real D1 regime
        # sliced to post-warmup length
        reg_pw = regime_h4[wi:]
        n_b = len(bcl)
        if len(reg_pw) >= n_b:
            breg = reg_pw[:n_b]
        else:
            breg = np.ones(n_b, dtype=np.bool_)

        bwi = 0  # bootstrap paths are already post-warmup

        nav_e0, e0_t = sim_e0_d1(bcl, bhi, blo, bvo, btb, breg, bwi)
        nav_e5, e5_t = sim_e5_d1(bcl, bhi, blo, bvo, btb, breg, bwi)

        matched, e0_only, e5_only = match_trades(e0_t, e5_t)

        # Headline
        boot_headline[b_idx] = float(nav_e5[-1] - nav_e0[-1])

        # cf_ret
        matched_ret_d = sum(b["ret_pct"] - a["ret_pct"] for a, b in matched)
        cascade_ret_d = sum(t["ret_pct"] for t in e5_only) - sum(t["ret_pct"] for t in e0_only)
        denom = matched_ret_d + cascade_ret_d
        boot_cf_ret[b_idx] = cascade_ret_d / denom if abs(denom) > 1e-6 else 0.0

        # Churn delta
        def _cr(trades):
            trail = [t for t in trades if t["exit_reason"] == "trail_stop"]
            if not trail:
                return 0.0
            ch = 0
            for idx, t in enumerate(trades):
                if t["exit_reason"] != "trail_stop":
                    continue
                if idx + 1 < len(trades) and trades[idx + 1]["entry_bar"] - t["exit_bar"] <= CHURN_WINDOW:
                    ch += 1
            return ch / len(trail)

        boot_d_churn[b_idx] = _cr(e5_t) - _cr(e0_t)

        if (b_idx + 1) % 100 == 0:
            print(f"    ... {b_idx + 1}/{N_BOOT} paths done")

    results = {
        "headline_median": float(np.median(boot_headline)),
        "headline_p5": float(np.percentile(boot_headline, 5)),
        "headline_p95": float(np.percentile(boot_headline, 95)),
        "headline_mean": float(np.mean(boot_headline)),
        "p_headline_gt0": float(np.mean(boot_headline > 0)),
        "cf_ret_median": float(np.median(boot_cf_ret)),
        "cf_ret_p5": float(np.percentile(boot_cf_ret, 5)),
        "cf_ret_p95": float(np.percentile(boot_cf_ret, 95)),
        "p_cf_ret_gt05": float(np.mean(boot_cf_ret > 0.5)),
        "d_churn_median": float(np.median(boot_d_churn)),
        "d_churn_p5": float(np.percentile(boot_d_churn, 5)),
        "d_churn_p95": float(np.percentile(boot_d_churn, 95)),
        "p_d_churn_lt0": float(np.mean(boot_d_churn < 0)),
    }

    print(f"\n  Headline delta: median=${results['headline_median']:+,.0f}, "
          f"[{results['headline_p5']:+,.0f}, {results['headline_p95']:+,.0f}]")
    print(f"  P(headline > 0): {results['p_headline_gt0']:.1%}")
    print(f"\n  cf_ret: median={results['cf_ret_median']:.4f}, "
          f"[{results['cf_ret_p5']:.4f}, {results['cf_ret_p95']:.4f}]")
    print(f"  P(cf_ret > 0.5): {results['p_cf_ret_gt05']:.1%}")
    print(f"\n  d_churn_rate: median={results['d_churn_median']:+.4f}, "
          f"[{results['d_churn_p5']:+.4f}, {results['d_churn_p95']:+.4f}]")
    print(f"  P(d_churn < 0): {results['p_d_churn_lt0']:.1%}")

    return results


# =========================================================================
# T6: COST SWEEP — reconcile 22 bps vs 50 bps discrepancy
# =========================================================================

COST_SWEEP_BPS = [10, 15, 22, 30, 35, 40, 50, 60, 75]


def run_t6_cost_sweep(cl, hi, lo, vo, tb, regime_h4, wi):
    """T6: Run T3 decomposition at multiple cost levels to find cf_ret crossover."""
    print("\n" + "=" * 70)
    print("T6: COST SWEEP (reconcile vtrend 22bps vs x12 50bps)")
    print("=" * 70)

    rows = []

    for bps in COST_SWEEP_BPS:
        cps = bps / 2.0 / 10_000.0  # per-side cost

        nav_e0, e0_t = sim_e0_d1(cl, hi, lo, vo, tb, regime_h4, wi, cps=cps)
        nav_e5, e5_t = sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi, cps=cps)

        m_e0 = _metrics(nav_e0, wi, len(e0_t))
        m_e5 = _metrics(nav_e5, wi, len(e5_t))

        matched, e0_only, e5_only = match_trades(e0_t, e5_t)

        headline = float(nav_e5[-1] - nav_e0[-1])
        matched_d = sum(b["pnl_usd"] - a["pnl_usd"] for a, b in matched)
        cascade_d = sum(t["pnl_usd"] for t in e5_only) - sum(t["pnl_usd"] for t in e0_only)

        matched_ret_d = sum(b["ret_pct"] - a["ret_pct"] for a, b in matched)
        cascade_ret_d = sum(t["ret_pct"] for t in e5_only) - sum(t["ret_pct"] for t in e0_only)
        denom = matched_ret_d + cascade_ret_d
        cf = cascade_ret_d / denom if abs(denom) > 1e-6 else 0.0

        # Churn
        def _cr(trades):
            trail = [t for t in trades if t["exit_reason"] == "trail_stop"]
            if not trail:
                return 0.0
            ch = 0
            for idx, t in enumerate(trades):
                if t["exit_reason"] != "trail_stop":
                    continue
                if idx + 1 < len(trades) and trades[idx + 1]["entry_bar"] - t["exit_bar"] <= CHURN_WINDOW:
                    ch += 1
            return ch / len(trail)

        d_churn = _cr(e5_t) - _cr(e0_t)

        # Matched-diff-exit median
        diff_exit = [(a, b) for a, b in matched if a["exit_bar"] != b["exit_bar"]]
        med_dpnl = float(np.median([b["pnl_usd"] - a["pnl_usd"] for a, b in diff_exit])) if diff_exit else 0.0

        row = {
            "cost_bps_rt": bps,
            "e0_sharpe": m_e0["sharpe"],
            "e5_sharpe": m_e5["sharpe"],
            "d_sharpe": m_e5["sharpe"] - m_e0["sharpe"],
            "headline_delta": headline,
            "matched_delta": matched_d,
            "cascade_delta": cascade_d,
            "cf_ret": cf,
            "d_churn_rate": d_churn,
            "n_matched": len(matched),
            "n_diff_exit": len(diff_exit),
            "n_e0_only": len(e0_only),
            "n_e5_only": len(e5_only),
            "median_diff_dpnl": med_dpnl,
            "e0_trades": len(e0_t),
            "e5_trades": len(e5_t),
        }
        rows.append(row)

    # Print table
    print(f"\n  {'Cost':>5s}  {'dSharpe':>8s}  {'Headline':>10s}  {'Matched':>10s}  {'Cascade':>10s}  {'cf_ret':>7s}  {'dChurn':>8s}  {'MedDPnL':>9s}")
    print("  " + "-" * 85)
    for r in rows:
        marker = " <-- vtrend" if r["cost_bps_rt"] == 22 else (" <-- x12" if r["cost_bps_rt"] == 50 else "")
        print(f"  {r['cost_bps_rt']:5d}  {r['d_sharpe']:+8.4f}  ${r['headline_delta']:>9,.0f}  ${r['matched_delta']:>9,.0f}  ${r['cascade_delta']:>9,.0f}  {r['cf_ret']:7.4f}  {r['d_churn_rate']:+8.4f}  ${r['median_diff_dpnl']:>8,.0f}{marker}")

    # Find crossover point where cf_ret crosses 0.5
    crossover_bps = None
    for i in range(len(rows) - 1):
        if (rows[i]["cf_ret"] > 0.5) != (rows[i + 1]["cf_ret"] > 0.5):
            # Linear interpolation
            bps1, cf1 = rows[i]["cost_bps_rt"], rows[i]["cf_ret"]
            bps2, cf2 = rows[i + 1]["cost_bps_rt"], rows[i + 1]["cf_ret"]
            if abs(cf2 - cf1) > 1e-8:
                crossover_bps = bps1 + (bps2 - bps1) * (0.5 - cf1) / (cf2 - cf1)
            break

    if crossover_bps is not None:
        print(f"\n  cf_ret crossover (0.5): ~{crossover_bps:.0f} bps RT")
        print(f"  Below {crossover_bps:.0f} bps: cascade dominates (vtrend finding)")
        print(f"  Above {crossover_bps:.0f} bps: mechanical dominates (x12 finding)")
    else:
        # Check if all same direction
        all_above = all(r["cf_ret"] > 0.5 for r in rows)
        all_below = all(r["cf_ret"] <= 0.5 for r in rows)
        if all_above:
            print(f"\n  cf_ret > 0.5 at ALL cost levels — cascade always dominates")
        elif all_below:
            print(f"\n  cf_ret <= 0.5 at ALL cost levels — mechanical always dominates")
        else:
            print(f"\n  cf_ret crossover: non-monotonic, no clean crossover found")

    return {"rows": rows, "crossover_bps": crossover_bps}


# =========================================================================
# SAVE RESULTS
# =========================================================================

def save_results(t0, t1, t2, t3, t4, t5, t6):
    """Save all results to JSON + CSV files."""
    # Master JSON
    out = {
        "churn_audit": t0,
        "cascade_map": {k: v for k, v in t1.items() if k != "detail_rows"},
        "matched_mechanism": {k: v for k, v in t2.items() if k != "detail_rows"},
        "decomposition": t3,
        "timescale": {k: v for k, v in t4.items() if k != "rows"},
        "bootstrap": t5,
        "cost_sweep": {k: v for k, v in t6.items() if k != "rows"},
    }
    with open(OUTDIR / "x12_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    # T0: churn audit CSV
    with open(OUTDIR / "x12_churn_audit.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "total_trades", "trail_stop_exits", "trend_exits",
                     "churn_count", "churn_rate", "churn_pnl", "non_churn_trail_pnl",
                     "short_count", "short_pnl", "medium_count", "medium_pnl",
                     "long_count", "long_pnl"])
        for label in ["E0", "E5"]:
            r = t0[label]
            w.writerow([label, r["total_trades"], r["trail_stop_exits"], r["trend_exits"],
                        r["churn_count"], f"{r['churn_rate']:.6f}", f"{r['churn_pnl']:.2f}",
                        f"{r['non_churn_trail_pnl']:.2f}",
                        r["short_count"], f"{r['short_pnl']:.2f}",
                        r["medium_count"], f"{r['medium_pnl']:.2f}",
                        r["long_count"], f"{r['long_pnl']:.2f}"])

    # T1: cascade census CSV
    with open(OUTDIR / "x12_cascade_census.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["category", "count", "pnl_sum", "pnl_mean", "pnl_median"])
        for cat in ["matched_same_exit", "matched_diff_exit", "e0_only", "e5_only"]:
            s = t1[cat]
            w.writerow([cat, s["count"], f"{s['sum']:.2f}", f"{s['mean']:.2f}", f"{s['median']:.2f}"])

    # T2: matched mechanism CSV
    if t2.get("detail_rows"):
        with open(OUTDIR / "x12_matched_mechanism.csv", "w", newline="") as f:
            fields = ["entry_bar", "e0_exit_bar", "e5_exit_bar", "e0_pnl", "e5_pnl",
                       "d_pnl", "e0_bars", "e5_bars", "d_bars", "e5_exits_first",
                       "e0_exit_reason", "e5_exit_reason", "e0_trail_dist", "e5_trail_dist",
                       "duration_bucket", "winner_loser"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in t2["detail_rows"]:
                w.writerow({k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in row.items()})

    # T3: decomposition JSON
    with open(OUTDIR / "x12_decomposition.json", "w") as f:
        json.dump(t3, f, indent=2)

    # T4: timescale CSV
    if t4.get("rows"):
        with open(OUTDIR / "x12_timescale_table.csv", "w", newline="") as f:
            fields = ["slow_period", "d_churn_rate", "headline_delta", "matched_delta",
                       "cascade_delta", "cf_ret", "n_matched", "n_diff_exit",
                       "n_e0_only", "n_e5_only", "e0_trades", "e5_trades"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in t4["rows"]:
                out_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        out_row[k] = f"{v:.6f}" if "rate" in k or "cf" in k else f"{v:.2f}"
                    else:
                        out_row[k] = v
                w.writerow(out_row)

    # T5: bootstrap CSV
    with open(OUTDIR / "x12_bootstrap_table.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "median", "p5", "p95", "probability"])
        w.writerow(["headline_delta", f"{t5['headline_median']:.2f}",
                     f"{t5['headline_p5']:.2f}", f"{t5['headline_p95']:.2f}",
                     f"{t5['p_headline_gt0']:.6f}"])
        w.writerow(["cf_ret", f"{t5['cf_ret_median']:.6f}",
                     f"{t5['cf_ret_p5']:.6f}", f"{t5['cf_ret_p95']:.6f}",
                     f"{t5['p_cf_ret_gt05']:.6f}"])
        w.writerow(["d_churn_rate", f"{t5['d_churn_median']:.6f}",
                     f"{t5['d_churn_p5']:.6f}", f"{t5['d_churn_p95']:.6f}",
                     f"{t5['p_d_churn_lt0']:.6f}"])

    # T6: cost sweep CSV
    if t6.get("rows"):
        with open(OUTDIR / "x12_cost_sweep.csv", "w", newline="") as f:
            fields = ["cost_bps_rt", "e0_sharpe", "e5_sharpe", "d_sharpe",
                       "headline_delta", "matched_delta", "cascade_delta", "cf_ret",
                       "d_churn_rate", "n_matched", "n_diff_exit", "n_e0_only",
                       "n_e5_only", "median_diff_dpnl", "e0_trades", "e5_trades"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in t6["rows"]:
                out_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        out_row[k] = f"{v:.6f}" if "rate" in k or "cf" in k else f"{v:.4f}"
                    else:
                        out_row[k] = v
                w.writerow(out_row)

    print(f"\n  Saved to {OUTDIR}/x12_*.{{json,csv}}")


# =========================================================================
# VERDICT
# =========================================================================

def print_verdict(t0, t2, t3, t4):
    """Print verdict gates and decision matrix."""
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    g0 = t0["delta"]["d_churn_rate"] >= 0
    g1 = t3["cf_ret"] > 0.5
    g2 = t2.get("median_d_pnl", 0.0) > 0
    g3 = t4.get("g3", False)

    gates = [
        ("G0", "Churn repair dead (d_churn >= 0)", g0),
        ("G1", "Path dependence dominates (cf_ret > 0.5)", g1),
        ("G2", "Mechanical per-trade edge (median dPnL > 0)", g2),
        ("G3", "Findings stable (>=12/16 timescales)", g3),
    ]

    for gid, desc, val in gates:
        print(f"  {gid}: {desc}: {'PASS' if val else 'FAIL'}")

    # Decision matrix
    if not g3:
        verdict = "INCONCLUSIVE"
    elif not g0:
        verdict = "CHURN_REPAIRS"
    elif g0 and not g1 and g2:
        verdict = "CHURN_FAILS_BUT_TAIL_WINS"
    elif g0 and g1 and not g2:
        verdict = "CHURN_FAILS_CASCADE_ONLY"
    elif g0 and g1 and g2:
        verdict = "CHURN_FAILS_MIXED"
    else:
        verdict = "CHURN_FAILS_NO_CLEAR_EDGE"

    print(f"\n  VERDICT: {verdict}")
    return verdict


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()

    print("X12: Why Does E5 Win If It Doesn't Fix Churn?")
    print("=" * 70)

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

    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)

    print(f"  Bars: {len(cl)} H4, {len(d1_cl)} D1, warmup_idx={wi}")
    print(f"  Period: {START} to {END}, warmup={WARMUP}d")

    # Run both sims at default params
    print("\n  Running E0+EMA1D21 and E5+EMA1D21 ...")
    nav_e0, e0_trades = sim_e0_d1(cl, hi, lo, vo, tb, regime_h4, wi)
    nav_e5, e5_trades = sim_e5_d1(cl, hi, lo, vo, tb, regime_h4, wi)

    m_e0 = _metrics(nav_e0, wi, len(e0_trades))
    m_e5 = _metrics(nav_e5, wi, len(e5_trades))
    print(f"\n  E0: Sharpe={m_e0['sharpe']:.4f}, CAGR={m_e0['cagr']:.2f}%, MDD={m_e0['mdd']:.2f}%, trades={m_e0['trades']}")
    print(f"  E5: Sharpe={m_e5['sharpe']:.4f}, CAGR={m_e5['cagr']:.2f}%, MDD={m_e5['mdd']:.2f}%, trades={m_e5['trades']}")

    matched, e0_only, e5_only = match_trades(e0_trades, e5_trades)

    # T0: Churn Audit
    t0_results = run_t0_churn(e0_trades, e5_trades)

    # T1: Divergence Cascade Map
    t1_results = run_t1_cascade(nav_e0, nav_e5, matched, e0_only, e5_only, wi)

    # T2: Matched-Trade Mechanism
    t2_results = run_t2_mechanism(matched)

    # T3: Cascade Counterfactual
    t3_results = run_t3_decomposition(nav_e0, nav_e5, matched, e0_only, e5_only, wi)

    # T4: Timescale Robustness
    t4_results = run_t4_timescale(cl, hi, lo, vo, tb, regime_h4, wi)

    # T5: Bootstrap Confidence
    t5_results = run_t5_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi)

    # T6: Cost Sweep
    t6_results = run_t6_cost_sweep(cl, hi, lo, vo, tb, regime_h4, wi)

    # Save
    save_results(t0_results, t1_results, t2_results, t3_results, t4_results, t5_results, t6_results)

    # Verdict
    verdict = print_verdict(t0_results, t2_results, t3_results, t4_results)

    elapsed = time.time() - t_start
    print(f"\nX12 BENCHMARK COMPLETE — {elapsed:.0f}s — VERDICT: {verdict}")


if __name__ == "__main__":
    main()
