#!/usr/bin/env python3
"""X24 Research — Trail Arming Isolation

Isolate trail arming mechanism from X23: delay trail activation until
MFE >= k * rATR_entry. No hard stop, no state conditioning, no score model.

Tests:
  T0: Phase diagnostic (churn by MFE phase in E5 baseline)
  T1: Full-sample comparison (E5 vs E5+ARM)
  T2: k-sweep characterization (k in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
  T3: Walk-forward optimization (4 folds, preset k)
  T4: Bootstrap (500 VCBB paths)
  T5: Jackknife (leave-year-out)
  T6: PSR with DOF correction
  T7: Summary table & verdict

Gates:
  G0: T1 d_sharpe(E5+ARM, E5) > 0
  G1: T3 WFO >= 3/4, mean d > 0
  G2: T4 P(d_sharpe > 0) > 0.55
  G3: T4 median d_mdd <= +5.0 pp
  G4: T5 JK neg <= 2/6
  G5: T6 PSR > 0.95
"""

from __future__ import annotations

import csv
import datetime
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed          # noqa: E402
from v10.core.types import SCENARIOS        # noqa: E402
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb  # noqa: E402
from research.lib.dsr import benchmark_sr0  # noqa: E402

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

# Indicator parameters (frozen from E5+EMA1D21)
SLOW = 120
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
D1_EMA_P = 21

# ATR parameters
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

# Trail baseline
TRAIL = 3.0

# X24 arming parameter (PRESET, ZERO TUNED)
ARM_K = 1.5

# k-sweep (characterization only, no gate)
K_SWEEP = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# Churn
CHURN_WINDOW = 20

# Cost
CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0

# Validation
WFO_FOLDS = [
    ("2021-12-31", "2022-01-01", "2022-12-31"),
    ("2022-12-31", "2023-01-01", "2023-12-31"),
    ("2023-12-31", "2024-01-01", "2024-12-31"),
    ("2024-12-31", "2025-01-01", "2026-02-20"),
]
JK_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
N_BOOT = 500
BLKSZ = 60
SEED = 42
E0_EFFECTIVE_DOF = 4.35

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# INDICATORS (identical to X23/X18, minus standard ATR and score model)
# =========================================================================

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _robust_atr(high, low, close, cap_q=RATR_CAP_Q, cap_lb=RATR_CAP_LB,
                period=RATR_PERIOD):
    """E5 robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.nanmean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
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


def _compute_indicators(cl, hi, lo, vo, tb, slow_period=SLOW):
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    vd = _vdo(cl, hi, lo, vo, tb)
    return ef, es, vd


def _compute_ratr(hi, lo, cl):
    return _robust_atr(hi, lo, cl, RATR_CAP_Q, RATR_CAP_LB, RATR_PERIOD)


def _compute_d1_regime(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
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
# METRICS
# =========================================================================

def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "trades": nt}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 \
        if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "trades": nt}


def _metrics_window(nav, start_idx, end_idx, nt=0):
    navs = nav[start_idx:end_idx]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "trades": nt}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 \
        if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "trades": nt}


def _date_to_bar_idx(h4_ct, date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ts_ms = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    idx = np.searchsorted(h4_ct, ts_ms, side='left')
    return min(idx, len(h4_ct) - 1)


def _psr(sharpe, n_returns, sr0=0.0):
    from scipy.stats import norm
    if n_returns < 3:
        return 0.5
    se = 1.0 / math.sqrt(n_returns)
    z = (sharpe - sr0) / se if se > 1e-12 else 0.0
    return float(norm.cdf(z))


# =========================================================================
# CHURN LABELING
# =========================================================================

def _label_churn(trades, churn_window=CHURN_WINDOW):
    """Label churn for trail_stop exits: re-entry within churn_window bars."""
    entry_bars = sorted(t["entry_bar"] for t in trades)
    results = []
    for t in trades:
        if t["exit_reason"] != "trail_stop":
            continue
        eb = t["exit_bar"]
        is_churn = any(eb < e <= eb + churn_window for e in entry_bars)
        results.append({"trade": t, "is_churn": is_churn})
    return results


# =========================================================================
# SIM: E5 BASELINE (robust ATR trail)
# =========================================================================

def _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH):
    """E5 baseline: robust ATR trail, always active."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    pk = 0.0
    pk_bar = 0
    entry_bar = 0
    entry_px = 0.0
    entry_cost = 0.0
    entry_ratr = 0.0
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
                entry_ratr = ratr[i - 1]
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0
                inp = True
                pk = p
                pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret_pct = (received / entry_cost - 1.0) * 100 \
                    if entry_cost > 0 else 0.0
                mfe_at_exit = (pk - entry_px) / entry_ratr \
                    if not np.isnan(entry_ratr) and entry_ratr > 1e-12 \
                    else 0.0
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret_pct,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason,
                    "mfe_atr": mfe_at_exit,
                })
                cash = received
                bq = 0.0
                inp = False
                pk = 0.0

        nav[i] = cash + bq * p
        a_val = ratr[i]
        if np.isnan(a_val) or np.isnan(ef[i]) or np.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p >= pk:
                pk_bar = i
            ts = pk - trail_mult * a_val
            if p < ts:
                exit_reason = "trail_stop"
                px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret_pct = (received / entry_cost - 1.0) * 100 \
            if entry_cost > 0 else 0.0
        mfe_at_exit = (pk - entry_px) / entry_ratr \
            if not np.isnan(entry_ratr) and entry_ratr > 1e-12 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
            "mfe_atr": mfe_at_exit,
        })
    return nav, trades


# =========================================================================
# SIM: E5+ARM — TRAIL ARMING ISOLATION (core new code)
# =========================================================================

def _run_sim_e5_arm(cl, ef, es, vd, ratr, regime_h4, wi,
                     trail_mult=TRAIL, arm_k=ARM_K, cps=CPS_HARSH):
    """
    E5 + trail arming: trail only active after MFE >= arm_k * rATR_entry.
    No hard stop. No state conditioning. No score model.

    Returns (nav, trades, stats).
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    in_position = False
    pending_entry = False
    pending_exit = False
    peak = 0.0
    peak_bar = 0
    entry_bar = 0
    entry_px = 0.0
    entry_cost = 0.0
    entry_ratr = 0.0
    trail_armed = False
    trail_arm_bar = -1
    exit_reason = ""
    nav = np.zeros(n)
    trades = []
    stats = {
        "n_trades": 0, "n_trail_stop": 0, "n_trend_exit": 0,
        "n_end_of_data": 0, "n_arm_events": 0, "n_never_armed": 0,
    }

    for i in range(n):
        p = cl[i]

        # --- Fill pending signals ---
        if i > 0:
            fp = cl[i - 1]

            if pending_entry:
                pending_entry = False
                entry_px = fp
                entry_bar = i
                entry_ratr = ratr[i - 1]   # rATR at signal bar
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0
                in_position = True
                trail_armed = False
                trail_arm_bar = -1
                peak = p
                peak_bar = i

            elif pending_exit:
                pending_exit = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret_pct = (received / entry_cost - 1.0) * 100 \
                    if entry_cost > 0 else 0.0
                mfe_at_exit = (peak - entry_px) / entry_ratr \
                    if not np.isnan(entry_ratr) and entry_ratr > 1e-12 \
                    else 0.0
                if not trail_armed:
                    stats["n_never_armed"] += 1
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": peak, "peak_bar": peak_bar,
                    "pnl_usd": pnl, "ret_pct": ret_pct,
                    "bars_held": i - entry_bar,
                    "exit_reason": exit_reason,
                    "trail_armed": trail_armed,
                    "trail_arm_bar": trail_arm_bar,
                    "mfe_atr": mfe_at_exit,
                })
                cash = received
                bq = 0.0
                in_position = False

        # --- NAV snapshot ---
        nav[i] = cash + bq * p

        # --- Skip invalid bars ---
        a_val = ratr[i]
        if np.isnan(a_val) or np.isnan(ef[i]) or np.isnan(es[i]):
            continue

        # --- Decision logic ---
        if not in_position:
            # ENTRY (unchanged from E5)
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pending_entry = True

        else:
            # Update peak
            peak = max(peak, p)
            if p >= peak:
                peak_bar = i

            # Update MFE and trail arming
            mfe = peak - entry_px
            if not trail_armed and not np.isnan(entry_ratr) \
               and entry_ratr > 1e-12:
                if mfe >= arm_k * entry_ratr:
                    trail_armed = True
                    trail_arm_bar = i
                    stats["n_arm_events"] += 1

            # EXIT CHECK 1: Trend failure (always active)
            if ef[i] < es[i]:
                exit_reason = "trend_exit"
                pending_exit = True
                stats["n_trend_exit"] += 1
                continue

            # EXIT CHECK 2: Trail stop (only when armed)
            if trail_armed:
                trail_level = peak - trail_mult * a_val
                if p < trail_level:
                    exit_reason = "trail_stop"
                    pending_exit = True
                    stats["n_trail_stop"] += 1

    # --- Handle open position at end of data ---
    if in_position and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret_pct = (received / entry_cost - 1.0) * 100 \
            if entry_cost > 0 else 0.0
        mfe_at_exit = (peak - entry_px) / entry_ratr \
            if not np.isnan(entry_ratr) and entry_ratr > 1e-12 else 0.0
        if not trail_armed:
            stats["n_never_armed"] += 1
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": peak, "peak_bar": peak_bar,
            "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": n - 1 - entry_bar,
            "exit_reason": "end_of_data",
            "trail_armed": trail_armed,
            "trail_arm_bar": trail_arm_bar,
            "mfe_atr": mfe_at_exit,
        })
        stats["n_end_of_data"] += 1

    stats["n_trades"] = len(trades)
    return nav, trades, stats


# =========================================================================
# T0: PHASE DIAGNOSTIC (pre-flight)
# =========================================================================

def run_t0_diagnostic(trades_e5, ratr):
    """Determine whether early-phase trail stops in E5 are disproportionately churn."""
    print("\n" + "=" * 70)
    print("T0: PHASE DIAGNOSTIC")
    print("=" * 70)

    # Label churn on E5 trail stops
    churn_data = _label_churn(trades_e5)

    # For each trail stop, compute mfe_atr and classify phase
    early_trades = []  # mfe_atr < ARM_K
    late_trades = []   # mfe_atr >= ARM_K

    for item in churn_data:
        t = item["trade"]
        mfe_atr = t.get("mfe_atr", 0.0)
        if mfe_atr < ARM_K:
            early_trades.append(item)
        else:
            late_trades.append(item)

    # Report
    def _phase_stats(items, label):
        n = len(items)
        n_churn = sum(1 for x in items if x["is_churn"])
        rate = n_churn / n * 100 if n > 0 else 0.0
        avg_pnl = np.mean([x["trade"]["pnl_usd"] for x in items]) if n > 0 else 0.0
        avg_bars = np.mean([x["trade"]["bars_held"] for x in items]) if n > 0 else 0.0
        return {"label": label, "n": n, "churn": n_churn, "rate": rate,
                "avg_pnl": avg_pnl, "avg_bars": avg_bars}

    early_s = _phase_stats(early_trades, "Early")
    late_s = _phase_stats(late_trades, "Late")
    all_s = _phase_stats(churn_data, "All")

    print(f"\n  {'Phase':<8} {'N':>5} {'Churn':>6} {'Rate':>7} {'AvgPnL':>10} {'AvgBars':>8}")
    print("  " + "-" * 46)
    for s in [early_s, late_s, all_s]:
        print(f"  {s['label']:<8} {s['n']:>5} {s['churn']:>6} {s['rate']:>6.1f}% "
              f"{s['avg_pnl']:>10.2f} {s['avg_bars']:>8.1f}")

    # MFE distribution at trail exit
    all_mfe = [item["trade"].get("mfe_atr", 0.0) for item in churn_data]
    if all_mfe:
        arr = np.array(all_mfe)
        pctls = {f"Q{q}": float(np.percentile(arr, q))
                 for q in [10, 25, 50, 75, 90]}
        print(f"\n  MFE at trail exit: {pctls}")
        print(f"  ARM_K={ARM_K} would prevent {early_s['n']}/{all_s['n']} "
              f"trail stops ({early_s['n']/all_s['n']*100:.1f}%)")
    else:
        pctls = {}

    # Interpretation
    delta_rate = early_s["rate"] - late_s["rate"]
    if early_s["n"] < 5:
        interp = "TOO_FEW_EARLY"
    elif delta_rate > 10:
        interp = "SUPPORTS_H1"
    else:
        interp = "DRIFT_DRIVEN"
    print(f"  Churn rate delta (early - late): {delta_rate:+.1f}pp → {interp}")

    return {
        "early": early_s, "late": late_s, "all": all_s,
        "mfe_percentiles": pctls, "interpretation": interp,
        "delta_churn_rate": delta_rate,
    }


# =========================================================================
# T1: FULL-SAMPLE COMPARISON
# =========================================================================

def run_t1_fullsample(cl, ef, es, vd, ratr, regime_h4, wi):
    print("\n" + "=" * 70)
    print("T1: FULL-SAMPLE COMPARISON")
    print("=" * 70)

    # E5 baseline
    nav_e5, trades_e5 = _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi)
    m_e5 = _metrics(nav_e5, wi, len(trades_e5))

    # E5+ARM
    nav_arm, trades_arm, stats_arm = _run_sim_e5_arm(
        cl, ef, es, vd, ratr, regime_h4, wi, arm_k=ARM_K)
    m_arm = _metrics(nav_arm, wi, len(trades_arm))

    # Exposure
    n_reporting = len(nav_e5) - wi
    for label, trades_list, m in [("E5", trades_e5, m_e5),
                                    ("E5+ARM", trades_arm, m_arm)]:
        total_bars = sum(t["bars_held"] for t in trades_list)
        m["exposure"] = total_bars / n_reporting * 100 if n_reporting > 0 else 0.0

    d_sharpe = m_arm["sharpe"] - m_e5["sharpe"]
    g0 = d_sharpe > 0

    # Performance table
    print(f"\n  {'Strategy':<12} {'Sharpe':>8} {'CAGR%':>8} {'MDD%':>8} "
          f"{'Trades':>7} {'Exp%':>7}")
    print("  " + "-" * 52)
    for label, m in [("E5", m_e5), ("E5+ARM(1.5)", m_arm)]:
        print(f"  {label:<12} {m['sharpe']:>8.4f} {m['cagr']:>8.2f} "
              f"{m['mdd']:>8.2f} {m['trades']:>7} {m['exposure']:>7.1f}")

    print(f"\n  d_sharpe(ARM vs E5) = {d_sharpe:+.4f}")
    print(f"  G0: {'PASS' if g0 else 'FAIL'}")

    # Exit anatomy
    churn_e5 = _label_churn(trades_e5)
    churn_arm = _label_churn(trades_arm)
    n_trail_e5 = sum(1 for t in trades_e5 if t["exit_reason"] == "trail_stop")
    n_trend_e5 = sum(1 for t in trades_e5 if t["exit_reason"] == "trend_exit")
    n_trail_arm = sum(1 for t in trades_arm if t["exit_reason"] == "trail_stop")
    n_trend_arm = sum(1 for t in trades_arm if t["exit_reason"] == "trend_exit")
    churn_trail_e5 = sum(1 for x in churn_e5 if x["is_churn"])
    churn_trail_arm = sum(1 for x in churn_arm if x["is_churn"])
    cr_e5 = churn_trail_e5 / n_trail_e5 * 100 if n_trail_e5 > 0 else 0.0
    cr_arm = churn_trail_arm / n_trail_arm * 100 if n_trail_arm > 0 else 0.0

    print(f"\n  {'Strategy':<12} {'Total':>6} {'Trail':>6} {'Trend':>6} "
          f"{'NvrArm':>7} {'Ch/Tr%':>7}")
    print("  " + "-" * 50)
    print(f"  {'E5':<12} {len(trades_e5):>6} {n_trail_e5:>6} {n_trend_e5:>6} "
          f"{'  -':>7} {cr_e5:>6.1f}%")
    print(f"  {'E5+ARM(1.5)':<12} {len(trades_arm):>6} {n_trail_arm:>6} "
          f"{n_trend_arm:>6} {stats_arm['n_never_armed']:>7} {cr_arm:>6.1f}%")

    return {
        "e5": m_e5, "arm": m_arm,
        "d_sharpe": d_sharpe, "g0_pass": g0,
        "stats_arm": stats_arm,
        "nav_e5": nav_e5, "trades_e5": trades_e5,
        "nav_arm": nav_arm, "trades_arm": trades_arm,
        "churn_rate_e5": cr_e5, "churn_rate_arm": cr_arm,
        "exit_anatomy": {
            "e5": {"total": len(trades_e5), "trail": n_trail_e5,
                   "trend": n_trend_e5, "churn_trail_rate": cr_e5},
            "arm": {"total": len(trades_arm), "trail": n_trail_arm,
                    "trend": n_trend_arm, "never_armed": stats_arm["n_never_armed"],
                    "churn_trail_rate": cr_arm},
        },
    }


# =========================================================================
# T2: k-SWEEP CHARACTERIZATION
# =========================================================================

def run_t2_ksweep(cl, ef, es, vd, ratr, regime_h4, wi):
    print("\n" + "=" * 70)
    print("T2: k-SWEEP CHARACTERIZATION")
    print("=" * 70)

    # E5 baseline
    nav_e5, trades_e5 = _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi)
    m_e5 = _metrics(nav_e5, wi, len(trades_e5))
    churn_e5 = _label_churn(trades_e5)
    n_trail_e5 = sum(1 for t in trades_e5 if t["exit_reason"] == "trail_stop")
    cr_e5 = sum(1 for x in churn_e5 if x["is_churn"]) / n_trail_e5 * 100 \
        if n_trail_e5 > 0 else 0.0
    n_reporting = len(nav_e5) - wi

    results = []
    print(f"\n  {'k':<6} {'Sharpe':>8} {'CAGR%':>8} {'MDD%':>8} "
          f"{'Trades':>7} {'NvrArm%':>8} {'Ch/Tr%':>7}")
    print("  " + "-" * 58)

    for k in K_SWEEP:
        nav_k, trades_k, stats_k = _run_sim_e5_arm(
            cl, ef, es, vd, ratr, regime_h4, wi, arm_k=k)
        m_k = _metrics(nav_k, wi, len(trades_k))
        total_bars = sum(t["bars_held"] for t in trades_k)
        m_k["exposure"] = total_bars / n_reporting * 100 if n_reporting > 0 else 0.0
        churn_k = _label_churn(trades_k)
        n_trail_k = sum(1 for t in trades_k if t["exit_reason"] == "trail_stop")
        cr_k = sum(1 for x in churn_k if x["is_churn"]) / n_trail_k * 100 \
            if n_trail_k > 0 else 0.0
        nvr_pct = stats_k["n_never_armed"] / stats_k["n_trades"] * 100 \
            if stats_k["n_trades"] > 0 else 0.0

        row = {
            "k": k, "sharpe": m_k["sharpe"], "cagr": m_k["cagr"],
            "mdd": m_k["mdd"], "trades": m_k["trades"],
            "never_armed_pct": nvr_pct, "churn_trail_rate": cr_k,
            "exposure": m_k["exposure"],
            "d_sharpe": m_k["sharpe"] - m_e5["sharpe"],
        }
        results.append(row)
        print(f"  {k:<6.1f} {m_k['sharpe']:>8.4f} {m_k['cagr']:>8.2f} "
              f"{m_k['mdd']:>8.2f} {m_k['trades']:>7} {nvr_pct:>7.1f}% "
              f"{cr_k:>6.1f}%")

    # E5 reference row
    print(f"  {'E5':<6} {m_e5['sharpe']:>8.4f} {m_e5['cagr']:>8.2f} "
          f"{m_e5['mdd']:>8.2f} {m_e5['trades']:>7} {'  0.0':>8}% {cr_e5:>6.1f}%")

    # Check monotonicity
    sharpes = [r["sharpe"] for r in results]
    is_monotonic_inc = all(sharpes[i] <= sharpes[i+1]
                          for i in range(len(sharpes)-1))
    is_monotonic_dec = all(sharpes[i] >= sharpes[i+1]
                          for i in range(len(sharpes)-1))
    has_peak = not is_monotonic_inc and not is_monotonic_dec
    if has_peak:
        best_k = results[np.argmax(sharpes)]["k"]
        print(f"\n  Sharpe curve has peak at k={best_k}")
    else:
        direction = "increasing" if is_monotonic_inc else "decreasing"
        print(f"\n  Sharpe curve is monotonic {direction} — "
              "arming may be equivalent in practice to trail sweep")

    return {"sweep": results, "e5_ref": {
        "sharpe": m_e5["sharpe"], "cagr": m_e5["cagr"],
        "mdd": m_e5["mdd"], "trades": m_e5["trades"],
        "churn_trail_rate": cr_e5},
        "has_peak": has_peak}


# =========================================================================
# T3: WALK-FORWARD OPTIMIZATION (4 folds)
# =========================================================================

def run_t3_wfo(cl, ef, es, vd, ratr, regime_h4, wi, h4_ct):
    print("\n" + "=" * 70)
    print("T3: WALK-FORWARD OPTIMIZATION (4 folds)")
    print("=" * 70)

    folds_cfg = []
    for train_end_str, test_start_str, test_end_str in WFO_FOLDS:
        folds_cfg.append((
            _date_to_bar_idx(h4_ct, train_end_str),
            _date_to_bar_idx(h4_ct, test_start_str),
            _date_to_bar_idx(h4_ct, test_end_str),
        ))

    fold_results = []
    for fold_idx, (train_end, test_start, test_end) in enumerate(folds_cfg):
        # No training needed — k is preset. Just run both sims on full data.
        nav_e5, trades_e5 = _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi)
        nav_arm, trades_arm, _ = _run_sim_e5_arm(
            cl, ef, es, vd, ratr, regime_h4, wi, arm_k=ARM_K)

        # Measure on test window
        test_trades_e5 = [t for t in trades_e5
                          if test_start <= t["entry_bar"] < test_end]
        m_e5_test = _metrics_window(
            nav_e5, test_start, test_end + 1, len(test_trades_e5))

        test_trades_arm = [t for t in trades_arm
                           if test_start <= t["entry_bar"] < test_end]
        m_arm_test = _metrics_window(
            nav_arm, test_start, test_end + 1, len(test_trades_arm))

        d = m_arm_test["sharpe"] - m_e5_test["sharpe"]

        fold_results.append({
            "fold": fold_idx + 1,
            "test_start": WFO_FOLDS[fold_idx][1],
            "test_end": WFO_FOLDS[fold_idx][2],
            "e5_sharpe": m_e5_test["sharpe"],
            "arm_sharpe": m_arm_test["sharpe"],
            "d_sharpe": d,
        })
        print(f"    Fold {fold_idx + 1}: E5={m_e5_test['sharpe']:.4f}, "
              f"ARM={m_arm_test['sharpe']:.4f} (d={d:+.4f}) "
              f"{'WIN' if d > 0 else 'LOSE'}")

    # Aggregate
    wins = sum(1 for f in fold_results if f["d_sharpe"] > 0)
    win_rate = wins / len(fold_results)
    mean_d = float(np.mean([f["d_sharpe"] for f in fold_results]))
    g1 = win_rate >= 0.75 and mean_d > 0

    print(f"\n  win_rate={win_rate:.0%}, mean_d={mean_d:+.4f}, "
          f"G1: {'PASS' if g1 else 'FAIL'}")

    return {
        "folds": fold_results,
        "win_rate": win_rate,
        "mean_d": mean_d,
        "g1_pass": g1,
    }


# =========================================================================
# T4: BOOTSTRAP (500 VCBB paths)
# =========================================================================

def run_t4_bootstrap(cl, hi, lo, vo, tb, ratr, regime_h4, wi):
    print("\n" + "=" * 70)
    print(f"T4: BOOTSTRAP ({N_BOOT} paths)")
    print("=" * 70)

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

    regime_pw = regime_h4[wi:]

    d_sharpes, d_cagrs, d_mdds = [], [], []
    sharpes_arm, sharpes_e5 = [], []

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        n_b = len(bcl)
        breg = regime_pw[:n_b] if len(regime_pw) >= n_b \
            else np.ones(n_b, dtype=np.bool_)

        bef, bes, bvd = _compute_indicators(bcl, bhi, blo, bvo, btb)
        bratr = _compute_ratr(bhi, blo, bcl)

        # E5 baseline
        bnav_e5, btrades_e5 = _run_sim_e5(bcl, bef, bes, bvd, bratr, breg, 0)
        bm_e5 = _metrics(bnav_e5, 0, len(btrades_e5))

        # E5+ARM (no model training needed — just run sim)
        bnav_arm, btrades_arm, _ = _run_sim_e5_arm(
            bcl, bef, bes, bvd, bratr, breg, 0, arm_k=ARM_K)
        bm_arm = _metrics(bnav_arm, 0, len(btrades_arm))

        d_sharpes.append(bm_arm["sharpe"] - bm_e5["sharpe"])
        d_cagrs.append(bm_arm["cagr"] - bm_e5["cagr"])
        d_mdds.append(bm_arm["mdd"] - bm_e5["mdd"])
        sharpes_arm.append(bm_arm["sharpe"])
        sharpes_e5.append(bm_e5["sharpe"])

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    d_sharpes = np.array(d_sharpes)
    d_cagrs = np.array(d_cagrs)
    d_mdds = np.array(d_mdds)

    p_gt0 = float(np.mean(d_sharpes > 0))
    med_mdd = float(np.median(d_mdds))
    g2 = p_gt0 > 0.55
    g3 = med_mdd <= 5.0

    r = {
        "P_d_sharpe_gt_0": p_gt0,
        "median_d_sharpe": float(np.median(d_sharpes)),
        "mean_d_sharpe": float(np.mean(d_sharpes)),
        "d_sharpe_p5": float(np.percentile(d_sharpes, 5)),
        "d_sharpe_p95": float(np.percentile(d_sharpes, 95)),
        "P_d_mdd_le_0": float(np.mean(d_mdds <= 0)),
        "median_d_mdd": med_mdd,
        "d_mdd_p5": float(np.percentile(d_mdds, 5)),
        "d_mdd_p95": float(np.percentile(d_mdds, 95)),
        "median_sharpe_arm": float(np.median(sharpes_arm)),
        "median_sharpe_e5": float(np.median(sharpes_e5)),
        "g2_pass": g2, "g3_pass": g3,
    }
    print(f"\n  d_sharpe: median={r['median_d_sharpe']:+.4f}, "
          f"[{r['d_sharpe_p5']:+.4f}, {r['d_sharpe_p95']:+.4f}]")
    print(f"  P(d_sharpe > 0): {p_gt0:.1%}")
    print(f"  d_mdd: median={med_mdd:+.2f}pp")
    print(f"  G2: {'PASS' if g2 else 'FAIL'}, G3: {'PASS' if g3 else 'FAIL'}")
    return r, d_sharpes, d_cagrs, d_mdds


# =========================================================================
# T5: JACKKNIFE (leave-year-out)
# =========================================================================

def run_t5_jackknife(cl, ef, es, vd, ratr, regime_h4, wi, h4_ct):
    print("\n" + "=" * 70)
    print("T5: JACKKNIFE (leave-year-out)")
    print("=" * 70)

    n = len(cl)

    # Full-data sims
    nav_e5, trades_e5 = _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi)
    nav_arm, trades_arm, _ = _run_sim_e5_arm(
        cl, ef, es, vd, ratr, regime_h4, wi, arm_k=ARM_K)

    folds = []
    for yr in JK_YEARS:
        ys = _date_to_bar_idx(h4_ct, f"{yr}-01-01")
        ye = min(_date_to_bar_idx(h4_ct, f"{yr}-12-31"), n - 1)

        kept = np.concatenate(
            [np.arange(wi, ys), np.arange(ye + 1, n)]
        ) if ys > wi else np.arange(ye + 1, n)

        if len(kept) < 2:
            continue

        tr_e5_jk = [t for t in trades_e5
                     if not (ys <= t["entry_bar"] <= ye)]
        m_e5 = _metrics(nav_e5[kept], 0, len(tr_e5_jk))

        tr_arm_jk = [t for t in trades_arm
                      if not (ys <= t["entry_bar"] <= ye)]
        m_arm = _metrics(nav_arm[kept], 0, len(tr_arm_jk))

        d = m_arm["sharpe"] - m_e5["sharpe"]
        folds.append({
            "year": yr,
            "e5_sharpe": m_e5["sharpe"],
            "arm_sharpe": m_arm["sharpe"],
            "d_sharpe": d,
            "d_sharpe_negative": d < 0,
        })
        print(f"    Drop {yr}: E5={m_e5['sharpe']:.4f}, "
              f"ARM={m_arm['sharpe']:.4f}, d={d:+.4f}")

    n_neg = sum(1 for f in folds if f["d_sharpe_negative"])
    mean_d = float(np.mean([f["d_sharpe"] for f in folds])) if folds else 0.0
    g4 = n_neg <= 2
    print(f"  Negative: {n_neg}/6, mean d={mean_d:+.4f}, "
          f"G4: {'PASS' if g4 else 'FAIL'}")
    return {"folds": folds, "n_negative": n_neg, "mean_d_sharpe": mean_d,
            "g4_pass": g4}


# =========================================================================
# T6: PSR WITH DOF CORRECTION
# =========================================================================

def run_t6_psr(nav_arm, wi):
    print("\n" + "=" * 70)
    print("T6: PSR WITH DOF CORRECTION")
    print("=" * 70)

    navs = nav_arm[wi:]
    rets = navs[1:] / navs[:-1] - 1.0
    n_returns = len(rets)
    mu = np.mean(rets)
    std_ret = np.std(rets, ddof=0)
    sharpe_per_bar = mu / std_ret if std_ret > 1e-12 else 0.0
    sharpe_ann = sharpe_per_bar * ANN

    # IMPL DECISION: benchmark_sr0 requires int num_trials. Round DOF.
    num_trials = max(2, int(round(E0_EFFECTIVE_DOF)))
    sr0 = benchmark_sr0(num_trials, n_returns)
    sr0_ann = sr0 * ANN

    psr = _psr(sharpe_ann, n_returns, sr0_ann)
    g5 = psr > 0.95

    print(f"  E5+ARM Sharpe (ann): {sharpe_ann:.4f}")
    print(f"  SR0 (DOF={num_trials}): {sr0_ann:.4f}")
    print(f"  PSR: {psr:.4f}")
    print(f"  G5: {'PASS' if g5 else 'FAIL'}")
    return {"sharpe": sharpe_ann, "sr0": sr0_ann, "psr": psr,
            "n_returns": n_returns, "g5_pass": g5}


# =========================================================================
# T7: SUMMARY TABLE & VERDICT
# =========================================================================

def run_t7_summary(g0, g1, g2, g3, g4, g5,
                    t1_data, t3_data, t4_data, t5_data, t6_data):
    print("\n" + "=" * 70)
    print("T7: SUMMARY TABLE & VERDICT")
    print("=" * 70)

    gates = {
        "G0": {"test": "T1", "criterion": "d_sharpe > 0 vs E5",
                "value": t1_data["d_sharpe"], "pass": g0},
        "G1": {"test": "T3", "criterion": "WFO >= 3/4, mean d > 0",
                "value": f"wr={t3_data['win_rate']:.0%}, "
                         f"d={t3_data['mean_d']:+.4f}",
                "pass": g1},
        "G2": {"test": "T4", "criterion": "P(d_sh > 0) > 0.55",
                "value": t4_data["P_d_sharpe_gt_0"], "pass": g2},
        "G3": {"test": "T4", "criterion": "med d_mdd <= +5pp",
                "value": t4_data["median_d_mdd"], "pass": g3},
        "G4": {"test": "T5", "criterion": "JK neg <= 2/6",
                "value": t5_data["n_negative"], "pass": g4},
        "G5": {"test": "T6", "criterion": "PSR > 0.95",
                "value": t6_data["psr"], "pass": g5},
    }

    print(f"\n  {'Gate':<5} {'Test':<5} {'Criterion':<25} "
          f"{'Value':<20} {'Pass?':<6}")
    print("  " + "-" * 63)
    for name, g in gates.items():
        val_str = f"{g['value']}" if isinstance(g['value'], str) \
            else f"{g['value']:.4f}"
        print(f"  {name:<5} {g['test']:<5} {g['criterion']:<25} "
              f"{val_str:<20} {'PASS' if g['pass'] else 'FAIL':<6}")

    n_pass = sum(1 for g in gates.values() if g["pass"])
    if n_pass == 6:
        verdict = "PROMOTE"
    elif n_pass >= 4:
        verdict = "HOLD"
    else:
        verdict = "REJECT"

    print(f"\n  Gates passed: {n_pass}/6")
    print(f"  VERDICT: {verdict}")

    return {"gates": gates, "n_pass": n_pass, "verdict": verdict}


# =========================================================================
# REPORT GENERATION
# =========================================================================

def _generate_report(all_results):
    """Generate x24_report.md from all_results."""
    lines = []
    lines.append("# X24 Report: Trail Arming Isolation\n")
    lines.append(f"Generated: {datetime.datetime.utcnow().isoformat()}Z\n")

    # T0
    t0 = all_results.get("t0", {})
    lines.append("\n## T0: Phase Diagnostic\n")
    lines.append("| Phase | N | Churn | Rate | AvgPnL | AvgBars |")
    lines.append("|-------|---|-------|------|--------|---------|")
    for phase in ("early", "late", "all"):
        s = t0.get(phase, {})
        lines.append(
            f"| {s.get('label', phase)} | {s.get('n', 0)} "
            f"| {s.get('churn', 0)} | {s.get('rate', 0):.1f}% "
            f"| {s.get('avg_pnl', 0):.2f} | {s.get('avg_bars', 0):.1f} |")
    interp = t0.get("interpretation", "N/A")
    delta = t0.get("delta_churn_rate", 0)
    lines.append(f"\nChurn rate delta (early - late): {delta:+.1f}pp → {interp}")
    pctls = t0.get("mfe_percentiles", {})
    if pctls:
        lines.append(f"MFE at trail exit percentiles: {pctls}\n")

    # T1
    t1 = all_results.get("t1", {})
    lines.append("\n## T1: Full-Sample Comparison\n")
    lines.append("| Strategy | Sharpe | CAGR% | MDD% | Trades | Exposure% |")
    lines.append("|----------|--------|-------|------|--------|-----------|")
    for label_key, label_str in [("e5", "E5"), ("arm", "E5+ARM(1.5)")]:
        m = t1.get(label_key, {})
        lines.append(
            f"| {label_str} | {m.get('sharpe', 0):.4f} | {m.get('cagr', 0):.2f} "
            f"| {m.get('mdd', 0):.2f} | {m.get('trades', 0)} "
            f"| {m.get('exposure', 0):.1f} |")
    lines.append(f"\nd_sharpe(ARM vs E5) = {t1.get('d_sharpe', 0):+.4f}")
    lines.append(f"G0: **{'PASS' if t1.get('g0_pass') else 'FAIL'}**\n")

    # Exit anatomy
    ea = t1.get("exit_anatomy", {})
    lines.append("| Strategy | Total | Trail | Trend | NvrArm | Ch/Tr% |")
    lines.append("|----------|-------|-------|-------|--------|--------|")
    for label_key, label_str in [("e5", "E5"), ("arm", "E5+ARM(1.5)")]:
        r = ea.get(label_key, {})
        nvr = r.get("never_armed", "-")
        lines.append(
            f"| {label_str} | {r.get('total', 0)} | {r.get('trail', 0)} "
            f"| {r.get('trend', 0)} | {nvr} "
            f"| {r.get('churn_trail_rate', 0):.1f} |")

    # T2
    t2 = all_results.get("t2", {})
    lines.append("\n## T2: k-Sweep Characterization\n")
    lines.append("| k | Sharpe | CAGR% | MDD% | Trades | NvrArm% | Ch/Tr% | d_Sharpe |")
    lines.append("|---|--------|-------|------|--------|---------|--------|----------|")
    for row in t2.get("sweep", []):
        lines.append(
            f"| {row['k']:.1f} | {row['sharpe']:.4f} | {row['cagr']:.2f} "
            f"| {row['mdd']:.2f} | {row['trades']} "
            f"| {row['never_armed_pct']:.1f} | {row['churn_trail_rate']:.1f} "
            f"| {row['d_sharpe']:+.4f} |")
    e5_ref = t2.get("e5_ref", {})
    lines.append(
        f"| E5 | {e5_ref.get('sharpe', 0):.4f} | {e5_ref.get('cagr', 0):.2f} "
        f"| {e5_ref.get('mdd', 0):.2f} | {e5_ref.get('trades', 0)} "
        f"| 0.0 | {e5_ref.get('churn_trail_rate', 0):.1f} | - |")
    lines.append(f"\nPeak in curve: {'Yes' if t2.get('has_peak') else 'No (monotonic)'}\n")

    # T3
    t3 = all_results.get("t3", {})
    lines.append("\n## T3: Walk-Forward Optimization\n")
    lines.append("| Fold | E5 Sharpe | ARM Sharpe | d_sharpe |")
    lines.append("|------|-----------|------------|----------|")
    for f in t3.get("folds", []):
        lines.append(
            f"| {f.get('fold', 0)} | {f.get('e5_sharpe', 0):.4f} "
            f"| {f.get('arm_sharpe', 0):.4f} "
            f"| {f.get('d_sharpe', 0):+.4f} |")
    lines.append(f"\nwin_rate={t3.get('win_rate', 0):.0%}, "
                 f"mean_d={t3.get('mean_d', 0):+.4f}")
    lines.append(f"G1: **{'PASS' if t3.get('g1_pass') else 'FAIL'}**\n")

    # T4
    t4 = all_results.get("t4", {})
    lines.append("\n## T4: Bootstrap\n")
    lines.append(f"- P(d_sharpe > 0): {t4.get('P_d_sharpe_gt_0', 0):.1%}")
    lines.append(f"- Median d_sharpe: {t4.get('median_d_sharpe', 0):+.4f}")
    lines.append(f"- Median d_mdd: {t4.get('median_d_mdd', 0):+.2f}pp")
    lines.append(
        f"- G2: **{'PASS' if t4.get('g2_pass') else 'FAIL'}**, "
        f"G3: **{'PASS' if t4.get('g3_pass') else 'FAIL'}**\n")

    # T5
    t5 = all_results.get("t5", {})
    lines.append("\n## T5: Jackknife\n")
    lines.append("| Year | E5 Sharpe | ARM Sharpe | d_sharpe |")
    lines.append("|------|-----------|------------|----------|")
    for f in t5.get("folds", []):
        lines.append(
            f"| {f.get('year', 0)} | {f.get('e5_sharpe', 0):.4f} "
            f"| {f.get('arm_sharpe', 0):.4f} "
            f"| {f.get('d_sharpe', 0):+.4f} |")
    lines.append(f"\nNegative: {t5.get('n_negative', 0)}/6")
    lines.append(f"G4: **{'PASS' if t5.get('g4_pass') else 'FAIL'}**\n")

    # T6
    t6 = all_results.get("t6", {})
    lines.append("\n## T6: PSR\n")
    lines.append(f"- E5+ARM Sharpe: {t6.get('sharpe', 0):.4f}")
    lines.append(f"- SR0: {t6.get('sr0', 0):.4f}")
    lines.append(f"- PSR: {t6.get('psr', 0):.4f}")
    lines.append(f"- G5: **{'PASS' if t6.get('g5_pass') else 'FAIL'}**\n")

    # T7 Summary
    t7 = all_results.get("t7", {})
    lines.append("\n## T7: Summary\n")
    lines.append("| Gate | Test | Criterion | Value | Pass? |")
    lines.append("|------|------|-----------|-------|-------|")
    for name, g in t7.get("gates", {}).items():
        val_str = f"{g['value']}" if isinstance(g['value'], str) \
            else f"{g['value']:.4f}"
        lines.append(
            f"| {name} | {g['test']} | {g['criterion']} "
            f"| {val_str} | {'PASS' if g['pass'] else 'FAIL'} |")
    lines.append(f"\n**VERDICT: {t7.get('verdict', 'UNKNOWN')}**\n")

    return "\n".join(lines)


# =========================================================================
# SAVE
# =========================================================================

def _coerce(obj):
    """Convert numpy types to Python native for JSON serialization."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, dict):
        return {k: _coerce(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_coerce(x) for x in obj]
    return obj


def save_results(all_results, d_sharpes=None, d_cagrs=None, d_mdds=None):
    # JSON results (exclude large arrays)
    json_data = {}
    for k, v in all_results.items():
        if k in ("t1",):
            # Strip nav/trades arrays from T1 for JSON
            t1_clean = {kk: vv for kk, vv in v.items()
                        if kk not in ("nav_e5", "nav_arm", "trades_e5",
                                      "trades_arm")}
            json_data[k] = t1_clean
        else:
            json_data[k] = v

    json_data["study_id"] = "X24"
    json_data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    json_data["constants"] = {
        "ARM_K": ARM_K, "TRAIL": TRAIL,
        "COST_BPS_RT": SCENARIOS["harsh"].round_trip_bps,
    }

    with open(OUTDIR / "x24_results.json", "w") as f:
        json.dump(_coerce(json_data), f, indent=2)

    # Bootstrap CSV
    if d_sharpes is not None:
        with open(OUTDIR / "x24_bootstrap.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "d_sharpe", "d_cagr", "d_mdd"])
            for i in range(len(d_sharpes)):
                w.writerow([i, f"{d_sharpes[i]:.6f}",
                            f"{d_cagrs[i]:.6f}", f"{d_mdds[i]:.6f}"])

    # WFO CSV
    t3 = all_results.get("t3", {})
    if t3.get("folds"):
        with open(OUTDIR / "x24_wfo.csv", "w", newline="") as f:
            fields = ["fold", "e5_sharpe", "arm_sharpe", "d_sharpe"]
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in t3["folds"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                            for k, v in r.items() if k in fields})

    # Jackknife CSV
    t5 = all_results.get("t5", {})
    if t5.get("folds"):
        with open(OUTDIR / "x24_jackknife.csv", "w", newline="") as f:
            fields = list(t5["folds"][0].keys())
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in t5["folds"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                            for k, v in r.items()})

    # Report
    report = _generate_report(all_results)
    with open(OUTDIR / "x24_report.md", "w") as f:
        f.write(report)

    print(f"\n  Saved to {OUTDIR}/x24_*.{{json,csv,md}}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("X24: Trail Arming Isolation")
    print("=" * 70)

    # --- Load data ---
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars],
                  dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # --- Compute indicators ---
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    ef, es, vd = _compute_indicators(cl, hi, lo, vo, tb)
    ratr = _compute_ratr(hi, lo, cl)
    print(f"  Bars: {len(cl)} H4, warmup_idx={wi}")
    print(f"  rATR first valid: {np.argmax(~np.isnan(ratr))}")

    all_results = {}

    # --- T0: Phase diagnostic ---
    nav_e5_diag, trades_e5_diag = _run_sim_e5(cl, ef, es, vd, ratr,
                                                regime_h4, wi)
    t0_data = run_t0_diagnostic(trades_e5_diag, ratr)
    all_results["t0"] = t0_data

    # --- T1: Full-sample comparison ---
    t1_data = run_t1_fullsample(cl, ef, es, vd, ratr, regime_h4, wi)
    all_results["t1"] = t1_data
    g0 = t1_data["g0_pass"]

    # --- T2: k-sweep ---
    t2_data = run_t2_ksweep(cl, ef, es, vd, ratr, regime_h4, wi)
    all_results["t2"] = t2_data

    # --- T3: WFO ---
    t3_data = run_t3_wfo(cl, ef, es, vd, ratr, regime_h4, wi, h4_ct)
    all_results["t3"] = t3_data
    g1 = t3_data["g1_pass"]

    # --- T4: Bootstrap ---
    t4_data, d_sharpes, d_cagrs, d_mdds = run_t4_bootstrap(
        cl, hi, lo, vo, tb, ratr, regime_h4, wi)
    all_results["t4"] = t4_data
    g2 = t4_data["g2_pass"]
    g3 = t4_data["g3_pass"]

    # --- T5: Jackknife ---
    t5_data = run_t5_jackknife(cl, ef, es, vd, ratr, regime_h4, wi, h4_ct)
    all_results["t5"] = t5_data
    g4 = t5_data["g4_pass"]

    # --- T6: PSR ---
    nav_arm = t1_data["nav_arm"]
    t6_data = run_t6_psr(nav_arm, wi)
    all_results["t6"] = t6_data
    g5 = t6_data["g5_pass"]

    # --- T7: Summary & Verdict ---
    t7_data = run_t7_summary(g0, g1, g2, g3, g4, g5,
                              t1_data, t3_data, t4_data, t5_data, t6_data)
    all_results["t7"] = t7_data

    # --- Save ---
    save_results(all_results, d_sharpes, d_cagrs, d_mdds)

    elapsed = time.time() - t_start
    print(f"\n  Total time: {elapsed:.1f}s ({elapsed / 60:.1f}m)")


if __name__ == "__main__":
    main()
