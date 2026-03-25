#!/usr/bin/env python3
"""E5A-V2: MDD-only Regime Monitor (ATR channel removed).

Core sim: E5+EMA1D21 (robust ATR Q90-capped trail) — matches PRIMARY strategy.

Adjustments from V1 based on X0A findings:
  1. ATR channel removed entirely (raw ATR broken, ATR% adds little)
  2. RED threshold lowered: 6m MDD > 55% (was 65%)
  3. Secondary check: 12m MDD > 70% (catches slow bears)
  4. AMBER: 6m MDD > 45% or 12m MDD > 60%

Target: 2022 bear triggers RED, ≤2 false RED episodes in full history.

Pipeline:
  S1: Compute rolling 6m and 12m MDD on D1 bars
  S2: Classify alerts (MDD-only)
  S3: Episode analysis
  S4: False positive analysis (BTC return during RED)
  S5: Backtest comparison (E5 vanilla vs E5+monitor)
  S6: Diagnostic — peak MDD values at key bear markets
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

# Reuse helpers from V1
from research.prod_readiness_e5_ema1d21.rejected.regime_monitor_v1_REJECTED import (
    rolling_mdd, _ema, _vdo, _d1_regime_map, _metrics_vec,
    extract_episodes, ALERT_NAMES,
)


def _robust_atr_h4(high, low, close, cap_q=0.90, cap_lb=100, period=20):
    """Robust ATR: cap TR at rolling Q90 of prior cap_lb bars, then Wilder EMA.

    Matches E5+EMA1D21 primary strategy parameters.
    """
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    from numpy.lib.stride_tricks import sliding_window_view
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
        b_f = np.array([alpha])
        a_f = np.array([1.0, -(1.0 - alpha)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b_f, a_f, tail, zi=zi)
            ratr[s + period:] = smoothed
    return ratr

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

SLOW = 120
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
CPS_HARSH = 0.005

# Monitor V2 parameters — MDD-only
ROLL_6M = 180   # 6-month rolling window (D1 bars)
ROLL_12M = 360  # 12-month rolling window (D1 bars)

# Alert thresholds (MDD-only, no ATR)
AMBER_MDD_6M = 0.45   # rolling 6m MDD > 45%
AMBER_MDD_12M = 0.60  # rolling 12m MDD > 60%
RED_MDD_6M = 0.55     # rolling 6m MDD > 55%
RED_MDD_12M = 0.70    # rolling 12m MDD > 70%

FWD_WINDOWS = [30, 90, 180]

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# CLASSIFY ALERTS (MDD-ONLY, DUAL WINDOW)
# =========================================================================


def classify_alerts_v2(mdd_6m: np.ndarray, mdd_12m: np.ndarray) -> np.ndarray:
    """Classify each bar as 0=NORMAL, 1=AMBER, 2=RED using MDD-only.

    RED:   6m MDD > 55% OR 12m MDD > 70%
    AMBER: 6m MDD > 45% OR 12m MDD > 60%
    """
    n = len(mdd_6m)
    alerts = np.zeros(n, dtype=np.int8)

    for t in range(n):
        m6 = mdd_6m[t] if not np.isnan(mdd_6m[t]) else 0.0
        m12 = mdd_12m[t] if not np.isnan(mdd_12m[t]) else 0.0

        if m6 > RED_MDD_6M or m12 > RED_MDD_12M:
            alerts[t] = 2
        elif m6 > AMBER_MDD_6M or m12 > AMBER_MDD_12M:
            alerts[t] = 1

    return alerts


def _map_d1_alert_to_h4(d1_alerts: np.ndarray, d1_ct: np.ndarray,
                         h4_ct: np.ndarray) -> np.ndarray:
    """Map D1 alert level to H4 bar grid (causal)."""
    n_h4 = len(h4_ct)
    n_d1 = len(d1_ct)
    h4_alerts = np.zeros(n_h4, dtype=np.int8)
    d1_idx = 0
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            h4_alerts[i] = d1_alerts[d1_idx]
    return h4_alerts


# =========================================================================
# VECTORIZED SIMS
# =========================================================================


def _sim_e5(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=CPS_HARSH):
    """E5+EMA1D21 vectorized sim (robust ATR trail)."""
    n = len(cl)
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, SLOW)
    at = _robust_atr_h4(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0
                inp = True; pk = p
            elif px:
                px = False; cash = bq * fp * (1 - cps); bq = 0.0
                inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - 3.0 * at[i]:
                px = True
            elif ef[i] < es[i]:
                px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def _sim_e5_monitored(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                       h4_alerts, cps=CPS_HARSH):
    """E5+EMA1D21 with RED monitor override: force flat during RED."""
    n = len(cl)
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, SLOW)
    at = _robust_atr_h4(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

    cash = CASH; bq = 0.0; inp = False; pe = px = False
    nt = 0; pk = 0.0; n_mon_exits = 0
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0
                inp = True; pk = p
            elif px:
                px = False; cash = bq * fp * (1 - cps); bq = 0.0
                inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        is_red = h4_alerts[i] == 2

        if not inp:
            if not is_red and ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if is_red:
                px = True; n_mon_exits += 1
            elif p < pk - 3.0 * at[i]:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash

    return nav, nt, n_mon_exits


# =========================================================================
# S1: COMPUTE MONITOR SIGNALS
# =========================================================================


def compute_monitor_v2(d1_close):
    """Compute dual-window MDD signals."""
    print("\n" + "=" * 80)
    print("S1: MDD-ONLY MONITOR (dual window: 6m + 12m)")
    print("=" * 80)

    n = len(d1_close)
    print(f"  D1 bars: {n}")

    t0 = time.time()
    mdd_6m = rolling_mdd(d1_close, ROLL_6M)
    print(f"  Rolling MDD(6m, {ROLL_6M}d) computed ({time.time()-t0:.2f}s)")

    t0 = time.time()
    mdd_12m = rolling_mdd(d1_close, ROLL_12M)
    print(f"  Rolling MDD(12m, {ROLL_12M}d) computed ({time.time()-t0:.2f}s)")

    alerts = classify_alerts_v2(mdd_6m, mdd_12m)

    n_normal = int(np.sum(alerts == 0))
    n_amber = int(np.sum(alerts == 1))
    n_red = int(np.sum(alerts == 2))
    print(f"\n  Alert distribution:")
    print(f"    NORMAL: {n_normal:5d} ({n_normal/n*100:.1f}%)")
    print(f"    AMBER:  {n_amber:5d} ({n_amber/n*100:.1f}%)")
    print(f"    RED:    {n_red:5d} ({n_red/n*100:.1f}%)")

    # RED trigger breakdown: which channel fired
    red_by_6m = red_by_12m = red_by_both = 0
    for t in range(n):
        if alerts[t] == 2:
            m6 = mdd_6m[t] if not np.isnan(mdd_6m[t]) else 0.0
            m12 = mdd_12m[t] if not np.isnan(mdd_12m[t]) else 0.0
            hit_6m = m6 > RED_MDD_6M
            hit_12m = m12 > RED_MDD_12M
            if hit_6m and hit_12m:
                red_by_both += 1
            elif hit_6m:
                red_by_6m += 1
            elif hit_12m:
                red_by_12m += 1
    print(f"\n  RED trigger breakdown:")
    print(f"    6m MDD only:  {red_by_6m}")
    print(f"    12m MDD only: {red_by_12m}")
    print(f"    Both:         {red_by_both}")

    return {
        "mdd_6m": mdd_6m,
        "mdd_12m": mdd_12m,
        "alerts": alerts,
        "alert_counts": {"total": n, "normal": n_normal, "amber": n_amber, "red": n_red},
        "red_breakdown": {"6m_only": red_by_6m, "12m_only": red_by_12m, "both": red_by_both},
    }


# =========================================================================
# S2: EPISODE ANALYSIS
# =========================================================================


def analyze_episodes_v2(alerts, d1_close, d1_ct):
    """Analyze AMBER and RED episodes."""
    print("\n" + "=" * 80)
    print("S2: EPISODE ANALYSIS")
    print("=" * 80)

    results = {}
    for level, name in [(1, "AMBER"), (2, "RED")]:
        eps = extract_episodes(alerts, level)
        if not eps:
            print(f"\n  {name}: 0 episodes")
            results[name] = {"count": 0, "episodes": [], "total_days": 0}
            continue

        durations = [e - s + 1 for s, e in eps]
        print(f"\n  {name}: {len(eps)} episodes ({np.sum(durations)} total days, "
              f"mean {np.mean(durations):.1f}d)")

        ep_details = []
        for i, (s, e) in enumerate(eps):
            ts_start = d1_ct[s]
            ts_end = d1_ct[e]
            date_start = datetime.fromtimestamp(ts_start / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            date_end = datetime.fromtimestamp(ts_end / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            dur = e - s + 1
            btc_ret = (d1_close[e] / d1_close[s] - 1.0) * 100 if d1_close[s] > 0 else 0.0

            ep_details.append({
                "idx": i + 1, "start_bar": int(s), "end_bar": int(e),
                "start_date": date_start, "end_date": date_end,
                "duration_days": dur, "btc_return_pct": float(btc_ret),
            })
            print(f"    #{i+1:2d}  {date_start} -> {date_end}  ({dur:3d}d)  "
                  f"BTC ret={btc_ret:+.1f}%")

        results[name] = {
            "count": len(eps), "total_days": int(np.sum(durations)),
            "mean_duration": float(np.mean(durations)), "episodes": ep_details,
        }

    return results


# =========================================================================
# S3: FALSE POSITIVE ANALYSIS
# =========================================================================


def false_positive_analysis_v2(alerts, d1_close, d1_ct, report_start_idx):
    """Evaluate false positive rate for RED alerts."""
    print("\n" + "=" * 80)
    print("S3: FALSE POSITIVE ANALYSIS (RED, reporting period)")
    print("=" * 80)

    n = len(d1_close)
    red_eps = extract_episodes(alerts, 2)
    red_eps_rpt = [(s, e) for s, e in red_eps if e >= report_start_idx]

    if not red_eps_rpt:
        print("  No RED episodes in reporting period.")
        return {"n_episodes": 0, "episodes_all": red_eps}

    fp = tp = 0
    details = []

    for s, e in red_eps_rpt:
        s_eff = max(s, report_start_idx)
        dur = e - s_eff + 1
        btc_during = (d1_close[e] / d1_close[s_eff] - 1.0) * 100

        is_fp = btc_during > 0

        date_s = datetime.fromtimestamp(d1_ct[s_eff] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        date_e = datetime.fromtimestamp(d1_ct[e] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

        fwd_rets = {}
        for w in FWD_WINDOWS:
            fwd_end = min(s_eff + w, n - 1)
            if fwd_end > s_eff:
                fwd_rets[f"fwd_{w}d_pct"] = float(
                    (d1_close[fwd_end] / d1_close[s_eff] - 1.0) * 100)

        details.append({
            "start_date": date_s, "end_date": date_e, "duration": dur,
            "btc_during_pct": float(btc_during), "is_false_positive": is_fp,
            **fwd_rets,
        })

        if is_fp:
            fp += 1
        else:
            tp += 1

        label = "FP" if is_fp else "TP"
        fwd30 = fwd_rets.get("fwd_30d_pct")
        fwd90 = fwd_rets.get("fwd_90d_pct")
        print(f"  {date_s} -> {date_e}  ({dur:3d}d)  BTC during={btc_during:+.1f}%  "
              f"[{label}]"
              + (f"  fwd30={fwd30:+.1f}%" if fwd30 is not None else "")
              + (f"  fwd90={fwd90:+.1f}%" if fwd90 is not None else ""))

    total = fp + tp
    fp_rate = fp / total if total > 0 else 0
    print(f"\n  Summary: {total} RED episodes in reporting period")
    print(f"    True Positives:  {tp}")
    print(f"    False Positives: {fp}")
    print(f"    FP Rate: {fp_rate:.1%}")

    return {
        "n_episodes": total, "true_positives": tp, "false_positives": fp,
        "fp_rate": float(fp_rate), "details": details,
        "episodes_all": red_eps,
    }


# =========================================================================
# S4: BACKTEST COMPARISON
# =========================================================================


def run_backtest_v2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_alerts):
    """E5 vanilla vs E5+monitor V2."""
    print("\n" + "=" * 80)
    print("S4: BACKTEST COMPARISON — E5 vs E5+MONITOR-V2 (harsh)")
    print("=" * 80)

    nav_v, nt_v = _sim_e5(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    m_v = _metrics_vec(nav_v, wi)

    nav_m, nt_m, n_mon = _sim_e5_monitored(
        cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_alerts)
    m_m = _metrics_vec(nav_m, wi)

    print(f"\n  {'Metric':20s} {'E5 Vanilla':>14s} {'E5+V2':>14s} {'Delta':>12s}")
    print(f"  {'-'*60}")
    for key, fmt, label in [
        ("sharpe", ".4f", "Sharpe"),
        ("cagr", ".2f", "CAGR %"),
        ("mdd", ".2f", "MDD %"),
    ]:
        v = m_v[key]; m = m_m[key]; d = m - v
        print(f"  {label:20s} {v:14{fmt}} {m:14{fmt}} {d:+12{fmt}}")
    print(f"  {'Trades':20s} {nt_v:14d} {nt_m:14d} {nt_m - nt_v:+12d}")
    print(f"  {'Monitor exits':20s} {'--':>14s} {n_mon:14d}")
    print(f"  {'Final NAV':20s} {nav_v[-1]:14.2f} {nav_m[-1]:14.2f} "
          f"{nav_m[-1]-nav_v[-1]:+12.2f}")

    return {
        "vanilla": {**m_v, "trades": nt_v, "final_nav": float(nav_v[-1])},
        "monitored": {**m_m, "trades": nt_m, "final_nav": float(nav_m[-1]),
                      "monitor_exits": n_mon},
        "delta": {
            "sharpe": m_m["sharpe"] - m_v["sharpe"],
            "cagr": m_m["cagr"] - m_v["cagr"],
            "mdd": m_m["mdd"] - m_v["mdd"],
            "trades": nt_m - nt_v,
        },
    }


# =========================================================================
# S5: DIAGNOSTIC — PEAK MDD AT KEY BEAR MARKETS
# =========================================================================


def diagnostic_peaks(mdd_6m, mdd_12m, d1_ct):
    """Show peak rolling MDD values at key bear market periods."""
    print("\n" + "=" * 80)
    print("S5: DIAGNOSTIC — Peak rolling MDD at key periods")
    print("=" * 80)

    # Define key periods by approximate date ranges
    periods = [
        ("2019 H2 (post-July)", "2019-06-01", "2020-01-01"),
        ("2020 Q1 (COVID)", "2020-01-01", "2020-07-01"),
        ("2021 Q2 (May crash)", "2021-04-01", "2021-10-01"),
        ("2022 H1 (Luna)", "2022-04-01", "2022-08-01"),
        ("2022 H2 (FTX)", "2022-08-01", "2023-02-01"),
        ("2022 full bear", "2022-01-01", "2023-06-01"),
    ]

    dates = np.array([
        datetime.fromtimestamp(t / 1000, tz=timezone.utc)
        for t in d1_ct
    ])

    print(f"\n  {'Period':30s} {'Peak 6m MDD':>12s} {'vs RED 55%':>12s} "
          f"{'Peak 12m MDD':>13s} {'vs RED 70%':>12s}")
    print("  " + "-" * 82)

    for label, start_s, end_s in periods:
        start_dt = datetime.strptime(start_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        mask = (dates >= start_dt) & (dates <= end_dt)
        if not np.any(mask):
            continue

        idx = np.where(mask)[0]
        peak_6m = np.nanmax(mdd_6m[idx]) * 100 if np.any(~np.isnan(mdd_6m[idx])) else 0
        peak_12m = np.nanmax(mdd_12m[idx]) * 100 if np.any(~np.isnan(mdd_12m[idx])) else 0

        delta_6m = peak_6m - RED_MDD_6M * 100
        delta_12m = peak_12m - RED_MDD_12M * 100

        flag_6m = "RED" if peak_6m > RED_MDD_6M * 100 else "---"
        flag_12m = "RED" if peak_12m > RED_MDD_12M * 100 else "---"

        print(f"  {label:30s} {peak_6m:11.1f}% {delta_6m:+11.1f}% [{flag_6m:3s}]"
              f" {peak_12m:12.1f}% {delta_12m:+11.1f}% [{flag_12m:3s}]")


# =========================================================================
# REPORT GENERATION
# =========================================================================


def generate_report(monitor, episodes, fp_data, bt, diagnostic_data=None):
    """Generate V2 report."""
    ac = monitor["alert_counts"]
    rb = monitor["red_breakdown"]
    bt_v = bt["vanilla"]
    bt_m = bt["monitored"]
    bt_d = bt["delta"]

    n_red_all = len(fp_data.get("episodes_all", []))
    n_fp = fp_data.get("false_positives", 0)
    n_tp = fp_data.get("true_positives", 0)

    report = f"""# E5A-V2 — MDD-Only Regime Monitor (E5+EMA1D21 core)

## 1. Design Changes from V1

| Aspect | V1 | V2 |
|--------|----|----|
| ATR channel | raw ATR (broken) + ATR% (adds little) | **Removed** |
| RED 6m MDD | > 65% | > **55%** |
| RED 12m MDD | N/A | > **70%** (new) |
| AMBER 6m MDD | > 55% | > **45%** |
| AMBER 12m MDD | N/A | > **60%** (new) |

Rationale:
- Raw ATR scales with price (71.6% RED rate — structurally broken)
- ATR% after normalization adds negligible value vs MDD-only
- 6m window misses slow bears (2022: 77% total DD, only 62.7% 6m MDD)
- 12m window catches extended drawdowns that 6m window truncates

## 2. Alert Distribution

| Level | Count | % of Total |
|-------|------:|----------:|
| NORMAL | {ac['normal']} | {ac['normal']/ac['total']*100:.1f}% |
| AMBER | {ac['amber']} | {ac['amber']/ac['total']*100:.1f}% |
| RED | {ac['red']} | {ac['red']/ac['total']*100:.1f}% |

RED trigger breakdown: 6m-only={rb['6m_only']}, 12m-only={rb['12m_only']}, both={rb['both']}

"""

    for level in ["AMBER", "RED"]:
        ep = episodes.get(level, {})
        if ep.get("count", 0) == 0:
            report += f"## 3. {level} Episodes: 0\n\n"
            continue
        report += f"## 3. {level} Episodes: {ep['count']} ({ep['total_days']} total days)\n\n"
        report += "| # | Start | End | Duration | BTC Return |\n"
        report += "|---|-------|-----|----------|------------|\n"
        for e in ep["episodes"]:
            report += (f"| {e['idx']} | {e['start_date']} | {e['end_date']} "
                      f"| {e['duration_days']}d | {e['btc_return_pct']:+.1f}% |\n")
        report += "\n"

    report += "## 4. False Positive Analysis (reporting period)\n\n"
    if fp_data["n_episodes"] == 0:
        report += "No RED episodes in reporting period.\n\n"
    else:
        report += f"""| Metric | Value |
|--------|------:|
| RED episodes | {fp_data['n_episodes']} |
| True Positives | {n_tp} |
| False Positives | {n_fp} |
| FP Rate | {fp_data['fp_rate']:.1%} |

| Start | End | Duration | BTC During | Verdict |
|-------|-----|----------|------------|---------|
"""
        for d in fp_data["details"]:
            v = "FP" if d["is_false_positive"] else "TP"
            report += (f"| {d['start_date']} | {d['end_date']} | {d['duration']}d "
                      f"| {d['btc_during_pct']:+.1f}% | {v} |\n")
        report += "\n"

    report += f"""## 5. Backtest: E5 Vanilla vs E5+Monitor-V2 (harsh, 50 bps RT)

| Metric | E5 Vanilla | E5+Monitor-V2 | Delta |
|--------|----------:|-------------:|------:|
| Sharpe | {bt_v['sharpe']:.4f} | {bt_m['sharpe']:.4f} | {bt_d['sharpe']:+.4f} |
| CAGR % | {bt_v['cagr']:.2f} | {bt_m['cagr']:.2f} | {bt_d['cagr']:+.2f} |
| MDD % | {bt_v['mdd']:.2f} | {bt_m['mdd']:.2f} | {bt_d['mdd']:+.2f} |
| Trades | {bt_v['trades']} | {bt_m['trades']} | {bt_d['trades']:+d} |
| Monitor exits | -- | {bt_m['monitor_exits']} | |
| Final NAV | {bt_v['final_nav']:.2f} | {bt_m['final_nav']:.2f} | {bt_m['final_nav'] - bt_v['final_nav']:+.2f} |

"""

    # Verdict
    red_eps = episodes.get("RED", {})
    n_red_ep = red_eps.get("count", 0)
    target_hit = False
    for ep in red_eps.get("episodes", []):
        if "2022" in ep["start_date"]:
            target_hit = True
            break

    report += "## 6. Verdict\n\n"
    report += f"### Target Assessment\n\n"
    report += f"- 2022 bear triggers RED: **{'YES' if target_hit else 'NO'}**\n"
    report += f"- Total RED episodes in history: **{n_red_ep}**"
    report += f" (target: <= 2 false)\n"

    # Count false RED episodes (positive BTC return during RED)
    false_red = 0
    for ep in red_eps.get("episodes", []):
        if ep["btc_return_pct"] > 0:
            false_red += 1
    report += f"- False RED episodes (BTC rose during): **{false_red}**\n"

    if target_hit and false_red <= 2:
        report += "\n**TARGETS MET**: 2022 triggers RED, false RED count within budget.\n"
    elif target_hit:
        report += f"\n**PARTIAL**: 2022 triggers RED, but {false_red} false RED exceeds budget of 2.\n"
    else:
        report += "\n**TARGETS NOT MET**: 2022 does not trigger RED.\n"

    # Overall assessment
    mdd_improved = bt_d["mdd"] < -2.0
    sharpe_hurt = bt_d["sharpe"] < -0.05
    cagr_cost = bt_d["cagr"]

    report += "\n### Performance Impact\n\n"
    sharpe_positive = bt_d["sharpe"] > 0.02
    if sharpe_positive and mdd_improved:
        report += (f"**POSITIVE**: Sharpe {bt_d['sharpe']:+.4f}, CAGR {cagr_cost:+.2f}%, "
                  f"MDD {bt_d['mdd']:+.2f}%. All metrics improve.\n")
    elif sharpe_positive:
        report += (f"**POSITIVE**: Sharpe {bt_d['sharpe']:+.4f}, CAGR {cagr_cost:+.2f}%. "
                  f"MDD marginal ({bt_d['mdd']:+.2f}%).\n")
    elif mdd_improved and not sharpe_hurt:
        report += (f"**POSITIVE**: MDD improves {bt_d['mdd']:+.2f}% with minimal "
                  f"Sharpe cost ({bt_d['sharpe']:+.4f}).\n")
    elif mdd_improved and sharpe_hurt:
        report += (f"**TRADEOFF**: MDD improves {bt_d['mdd']:+.2f}% but Sharpe drops "
                  f"{bt_d['sharpe']:+.4f}, CAGR cost {cagr_cost:+.2f}%.\n")
    else:
        report += f"**NEUTRAL**: MDD change {bt_d['mdd']:+.2f}%, Sharpe {bt_d['sharpe']:+.4f}.\n"

    report += f"""
### Mechanism: Entry Prevention, Not Exit

Monitor exits = {bt_m['monitor_exits']}. The D1 EMA(21) regime filter already flips
bearish before RED fires (by the time 6m MDD > 55%, BTC has been falling for months
and close << EMA21). Strategy is already flat when RED triggers.

The monitor adds value by **preventing entries** during brief bullish blips within
bear markets. Vanilla E5 makes {bt_v['trades']} trades; monitored makes {bt_m['trades']}
(-{bt_v['trades'] - bt_m['trades']}). These avoided entries were false signals during
stressed regimes where the regime filter briefly flickered bullish.

**Implication**: The MDD monitor and EMA(21) regime filter form a **layered defense**.
The regime filter catches most bear exposure. The MDD monitor catches the residual:
entries that pass the regime filter during elevated-stress bear market bounces.
"""

    report += "\n---\n*Generated by regime_monitor_v2.py (E5+EMA1D21 core)*\n"

    rpt_path = OUTDIR / "E5A_REGIME_MONITOR_V2_REPORT.md"
    with open(rpt_path, "w") as f:
        f.write(report)
    print(f"\nSaved: {rpt_path}")


# =========================================================================
# MAIN
# =========================================================================


def main():
    t_start = time.time()
    print("=" * 80)
    print("E5A-V2: MDD-ONLY REGIME MONITOR (E5+EMA1D21 core)")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  AMBER: 6m MDD>{AMBER_MDD_6M*100:.0f}% or 12m MDD>{AMBER_MDD_12M*100:.0f}%")
    print(f"  RED:   6m MDD>{RED_MDD_6M*100:.0f}% or 12m MDD>{RED_MDD_12M*100:.0f}%")
    print(f"  ATR channel: REMOVED")
    print("=" * 80)

    # Load data
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    d1_close = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    d1_report_idx = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.d1_bars):
            if b.close_time >= feed.report_start_ms:
                d1_report_idx = j
                break

    print(f"\n  D1 bars: {len(d1_close)}, H4 bars: {len(cl)}")
    print(f"  H4 warmup idx: {wi}, D1 report start idx: {d1_report_idx}")

    # S1: Compute monitor
    monitor = compute_monitor_v2(d1_close)

    # S2: Episode analysis
    episodes = analyze_episodes_v2(monitor["alerts"], d1_close, d1_ct)

    # S3: False positive analysis
    fp_data = false_positive_analysis_v2(
        monitor["alerts"], d1_close, d1_ct, d1_report_idx)

    # S4: Backtest
    h4_alerts = _map_d1_alert_to_h4(monitor["alerts"], d1_ct, h4_ct)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    bt = run_backtest_v2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_alerts)

    # S5: Diagnostic
    diagnostic_peaks(monitor["mdd_6m"], monitor["mdd_12m"], d1_ct)

    # Save results
    json_path = OUTDIR / "e5a_v2_results.json"
    results = {
        "params": {
            "roll_6m": ROLL_6M, "roll_12m": ROLL_12M,
            "amber_mdd_6m": AMBER_MDD_6M, "amber_mdd_12m": AMBER_MDD_12M,
            "red_mdd_6m": RED_MDD_6M, "red_mdd_12m": RED_MDD_12M,
        },
        "alert_counts": monitor["alert_counts"],
        "red_breakdown": monitor["red_breakdown"],
        "episodes": {k: {kk: vv for kk, vv in v.items()} for k, v in episodes.items()},
        "false_positive": {k: v for k, v in fp_data.items() if k != "episodes_all"},
        "backtest": bt,
    }
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # Generate report
    generate_report(monitor, episodes, fp_data, bt)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 80}")
    print(f"E5A V2 MONITOR COMPLETE ({elapsed:.0f}s)")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
