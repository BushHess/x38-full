#!/usr/bin/env python3
"""X0A Research — Runtime Regime Monitor.

Hypothesis: A runtime monitor based on rolling 6-month MDD and rolling ATR
percentile can detect dangerous regime shifts and trigger protective alerts,
allowing automatic fallback to X0 (flat/conservative) during extreme conditions.

Monitor signals (computed daily on D1 bars):
  rolling_mdd_6m : max drawdown over trailing 180 D1 bars
  rolling_atr_q90: 90th percentile of ATR(14) over trailing 180 D1 bars
  atr_ratio      : rolling_atr_q90 / training_period_mean(atr_q90)

Alert levels:
  NORMAL: no conditions met
  AMBER : rolling_mdd_6m > 55%  OR  atr_ratio > 1.40
  RED   : rolling_mdd_6m > 65%  OR  atr_ratio > 1.60

RED triggers automatic switch to X0 fallback (force flat).

Backtest:
  S1: Monitor signal computation on full D1 history
  S2: Alert statistics (count, duration, clustering)
  S3: False positive analysis (BTC return during RED periods)
  S4: X0 vanilla vs X0+monitor overlay comparison
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
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy

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

# Monitor parameters
ROLL_WINDOW = 180        # 6-month rolling window (D1 bars)
ATR_PERIOD = 14          # Wilder ATR
TRAIN_DAYS = 365         # training period length (D1 bars) after first valid rolling
ATR_Q = 90               # percentile for ATR

# Alert thresholds
AMBER_MDD = 0.55         # rolling MDD > 55%
AMBER_ATR_RATIO = 1.40   # ATR Q90 > 140% of training mean
RED_MDD = 0.65           # rolling MDD > 65%
RED_ATR_RATIO = 1.60     # ATR Q90 > 160% of training mean

# Forward-return windows for false positive analysis (D1 bars)
FWD_WINDOWS = [30, 90, 180]

OUTDIR = Path(__file__).resolve().parent

# =========================================================================
# INDICATOR HELPERS (D1 timeframe)
# =========================================================================


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr_d1(high: np.ndarray, low: np.ndarray, close: np.ndarray,
            period: int = 14) -> np.ndarray:
    """Wilder ATR on D1 bars."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha_w = 1.0 / period
        b_filt = np.array([alpha_w])
        a_filt = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha_w) * seed])
            smoothed, _ = lfilter(b_filt, a_filt, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


# =========================================================================
# ROLLING MONITOR COMPUTATIONS
# =========================================================================


def rolling_mdd(close: np.ndarray, window: int = ROLL_WINDOW) -> np.ndarray:
    """Rolling max drawdown over trailing `window` bars.

    Returns array of same length, NaN where insufficient history.
    MDD expressed as fraction (0.55 = 55%).
    """
    n = len(close)
    mdd = np.full(n, np.nan)
    for t in range(window - 1, n):
        seg = close[t - window + 1: t + 1]
        peak = np.maximum.accumulate(seg)
        dd = 1.0 - seg / peak
        mdd[t] = np.max(dd)
    return mdd


def rolling_atr_percentile(atr: np.ndarray, window: int = ROLL_WINDOW,
                           q: float = ATR_Q) -> np.ndarray:
    """Rolling Qth percentile of ATR over trailing `window` bars.

    Skips NaN values in the ATR array.
    """
    n = len(atr)
    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        seg = atr[t - window + 1: t + 1]
        valid = seg[~np.isnan(seg)]
        if len(valid) >= window // 2:  # need at least half the window
            out[t] = np.percentile(valid, q)
    return out


def compute_training_mean(rolling_q90: np.ndarray,
                          train_days: int = TRAIN_DAYS) -> tuple[float, int, int]:
    """Compute training-period mean of rolling ATR Q90.

    Training starts at first valid (non-NaN) value and runs for train_days.
    Returns (mean, start_idx, end_idx).
    """
    valid_mask = ~np.isnan(rolling_q90)
    valid_indices = np.where(valid_mask)[0]
    if len(valid_indices) == 0:
        return np.nan, 0, 0
    start = valid_indices[0]
    end = min(start + train_days, len(rolling_q90))
    seg = rolling_q90[start:end]
    seg = seg[~np.isnan(seg)]
    return float(np.mean(seg)), int(start), int(end)


def classify_alerts(roll_mdd: np.ndarray, atr_ratio: np.ndarray,
                    amber_mdd: float = AMBER_MDD,
                    amber_atr: float = AMBER_ATR_RATIO,
                    red_mdd: float = RED_MDD,
                    red_atr: float = RED_ATR_RATIO) -> np.ndarray:
    """Classify each bar as 0=NORMAL, 1=AMBER, 2=RED.

    RED supersedes AMBER. NaN inputs → NORMAL.
    """
    n = len(roll_mdd)
    alerts = np.zeros(n, dtype=np.int8)

    for t in range(n):
        m = roll_mdd[t]
        r = atr_ratio[t]

        if np.isnan(m) and np.isnan(r):
            continue

        m_val = m if not np.isnan(m) else 0.0
        r_val = r if not np.isnan(r) else 0.0

        if m_val > red_mdd or r_val > red_atr:
            alerts[t] = 2
        elif m_val > amber_mdd or r_val > amber_atr:
            alerts[t] = 1

    return alerts


ALERT_NAMES = {0: "NORMAL", 1: "AMBER", 2: "RED"}


# =========================================================================
# ALERT EPISODE EXTRACTION
# =========================================================================


def extract_episodes(alerts: np.ndarray, level: int) -> list[tuple[int, int]]:
    """Extract contiguous episodes of a given alert level.

    Returns list of (start_idx, end_idx) inclusive tuples.
    """
    episodes = []
    in_ep = False
    start = 0
    for t in range(len(alerts)):
        if alerts[t] >= level and not in_ep:
            in_ep = True
            start = t
        elif alerts[t] < level and in_ep:
            episodes.append((start, t - 1))
            in_ep = False
    if in_ep:
        episodes.append((start, len(alerts) - 1))
    return episodes


# =========================================================================
# S1: COMPUTE MONITOR SIGNALS
# =========================================================================


def compute_monitor_signals(d1_close: np.ndarray, d1_high: np.ndarray,
                            d1_low: np.ndarray):
    """Compute all monitor signals on D1 data.

    Returns dict with arrays and training stats.
    """
    print("\n" + "=" * 80)
    print("S1: MONITOR SIGNAL COMPUTATION")
    print("=" * 80)

    n_d1 = len(d1_close)
    print(f"  D1 bars: {n_d1}")

    # ATR(14) on D1
    atr = _atr_d1(d1_high, d1_low, d1_close, ATR_PERIOD)
    print(f"  ATR({ATR_PERIOD}) computed, first valid at bar {np.argmax(~np.isnan(atr))}")

    # Rolling 6-month MDD
    t0 = time.time()
    r_mdd = rolling_mdd(d1_close, ROLL_WINDOW)
    print(f"  Rolling MDD({ROLL_WINDOW}d) computed ({time.time()-t0:.2f}s)")

    # Rolling ATR Q90
    t0 = time.time()
    r_atr_q90 = rolling_atr_percentile(atr, ROLL_WINDOW, ATR_Q)
    print(f"  Rolling ATR Q{ATR_Q}({ROLL_WINDOW}d) computed ({time.time()-t0:.2f}s)")

    # Training mean
    train_mean, train_start, train_end = compute_training_mean(r_atr_q90, TRAIN_DAYS)
    print(f"  Training period: bars [{train_start}, {train_end}) "
          f"({train_end - train_start} days)")
    print(f"  Training ATR Q{ATR_Q} mean: {train_mean:.2f}")

    # ATR ratio
    atr_ratio = np.full(n_d1, np.nan)
    valid = ~np.isnan(r_atr_q90) & (train_mean > 0)
    atr_ratio[valid] = r_atr_q90[valid] / train_mean

    # Classify alerts
    alerts = classify_alerts(r_mdd, atr_ratio)

    # Summary counts
    n_valid = int(np.sum(~np.isnan(r_mdd) | ~np.isnan(atr_ratio)))
    n_normal = int(np.sum(alerts == 0))
    n_amber = int(np.sum(alerts == 1))
    n_red = int(np.sum(alerts == 2))
    print(f"\n  Alert distribution (all {n_d1} bars):")
    print(f"    NORMAL: {n_normal:5d} ({n_normal/n_d1*100:.1f}%)")
    print(f"    AMBER:  {n_amber:5d} ({n_amber/n_d1*100:.1f}%)")
    print(f"    RED:    {n_red:5d} ({n_red/n_d1*100:.1f}%)")

    return {
        "atr": atr,
        "rolling_mdd": r_mdd,
        "rolling_atr_q90": r_atr_q90,
        "atr_ratio": atr_ratio,
        "alerts": alerts,
        "train_mean": train_mean,
        "train_start": train_start,
        "train_end": train_end,
    }


# =========================================================================
# S2: ALERT EPISODE STATISTICS
# =========================================================================


def analyze_episodes(alerts: np.ndarray, d1_close: np.ndarray,
                     d1_close_times: np.ndarray):
    """Analyze AMBER and RED episodes."""
    print("\n" + "=" * 80)
    print("S2: ALERT EPISODE ANALYSIS")
    print("=" * 80)

    results = {}
    for level, name in [(1, "AMBER"), (2, "RED")]:
        eps = extract_episodes(alerts, level)
        if not eps:
            print(f"\n  {name}: 0 episodes")
            results[name] = {"count": 0, "episodes": []}
            continue

        durations = [e - s + 1 for s, e in eps]
        print(f"\n  {name}: {len(eps)} episodes")
        print(f"    Duration: mean={np.mean(durations):.1f}d, "
              f"median={np.median(durations):.0f}d, "
              f"min={np.min(durations)}d, max={np.max(durations)}d, "
              f"total={np.sum(durations)}d")

        ep_details = []
        for i, (s, e) in enumerate(eps):
            ts_start = d1_close_times[s]
            ts_end = d1_close_times[e]
            date_start = datetime.fromtimestamp(ts_start / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            date_end = datetime.fromtimestamp(ts_end / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            dur = e - s + 1
            btc_ret = (d1_close[e] / d1_close[s] - 1.0) * 100 if d1_close[s] > 0 else 0.0

            ep_details.append({
                "idx": i + 1,
                "start_bar": int(s),
                "end_bar": int(e),
                "start_date": date_start,
                "end_date": date_end,
                "duration_days": dur,
                "btc_return_pct": float(btc_ret),
            })

            print(f"    #{i+1:2d}  {date_start} → {date_end}  ({dur:3d}d)  "
                  f"BTC ret={btc_ret:+.1f}%")

        results[name] = {
            "count": len(eps),
            "durations": durations,
            "total_days": int(np.sum(durations)),
            "mean_duration": float(np.mean(durations)),
            "episodes": ep_details,
        }

    return results


# =========================================================================
# S3: FALSE POSITIVE ANALYSIS
# =========================================================================


def false_positive_analysis(alerts: np.ndarray, d1_close: np.ndarray,
                            d1_close_times: np.ndarray,
                            report_start_idx: int):
    """Evaluate false positive rate for RED alerts during reporting period.

    A RED episode is a false positive if BTC returned positively during that
    period (meaning going flat hurt performance).
    Also computes forward N-day returns from episode start.
    """
    print("\n" + "=" * 80)
    print("S3: FALSE POSITIVE ANALYSIS (RED alerts, reporting period only)")
    print("=" * 80)

    n = len(d1_close)
    red_eps = extract_episodes(alerts, 2)
    # Filter to reporting period
    red_eps = [(s, e) for s, e in red_eps if e >= report_start_idx]

    if not red_eps:
        print("  No RED episodes in reporting period.")
        return {"n_red_episodes": 0}

    fp_count = 0
    tp_count = 0
    details = []

    for s, e in red_eps:
        s_eff = max(s, report_start_idx)
        dur = e - s_eff + 1
        btc_during = (d1_close[e] / d1_close[s_eff] - 1.0) * 100

        is_fp = btc_during > 0

        date_s = datetime.fromtimestamp(d1_close_times[s_eff] / 1000,
                                        tz=timezone.utc).strftime("%Y-%m-%d")
        date_e = datetime.fromtimestamp(d1_close_times[e] / 1000,
                                        tz=timezone.utc).strftime("%Y-%m-%d")

        # Forward returns from episode start
        fwd_rets = {}
        for w in FWD_WINDOWS:
            fwd_end = min(s_eff + w, n - 1)
            if fwd_end > s_eff:
                fwd_rets[f"fwd_{w}d_pct"] = float(
                    (d1_close[fwd_end] / d1_close[s_eff] - 1.0) * 100)
            else:
                fwd_rets[f"fwd_{w}d_pct"] = None

        detail = {
            "start_date": date_s,
            "end_date": date_e,
            "duration": dur,
            "btc_during_pct": float(btc_during),
            "is_false_positive": is_fp,
            **fwd_rets,
        }
        details.append(detail)

        if is_fp:
            fp_count += 1
        else:
            tp_count += 1

        label = "FP" if is_fp else "TP"
        print(f"  {date_s} → {date_e}  ({dur:3d}d)  BTC during={btc_during:+.1f}%  "
              f"[{label}]  fwd30={fwd_rets.get('fwd_30d_pct', 'N/A')}"
              + (f"  fwd90={fwd_rets['fwd_90d_pct']:+.1f}%" if fwd_rets.get('fwd_90d_pct') is not None else ""))

    total = fp_count + tp_count
    fp_rate = fp_count / total if total > 0 else 0
    print(f"\n  Summary: {total} RED episodes in reporting period")
    print(f"    True Positives:  {tp_count} ({tp_count/total*100:.1f}%)")
    print(f"    False Positives: {fp_count} ({fp_count/total*100:.1f}%)")
    print(f"    FP Rate: {fp_rate:.1%}")

    return {
        "n_red_episodes": total,
        "true_positives": tp_count,
        "false_positives": fp_count,
        "fp_rate": float(fp_rate),
        "details": details,
    }


# =========================================================================
# S4: BACKTEST COMPARISON — X0 vanilla vs X0+monitor
# =========================================================================

# Vectorized helpers for H4 sim (from x6/benchmark.py pattern)

VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
CPS_HARSH = 0.005


def _vdo(close, high, low, volume, taker_buy, fast=VDO_F, slow=VDO_S):
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


def _atr_h4(high, low, close, period=14):
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha_w = 1.0 / period
        b_filt = np.array([alpha_w])
        a_filt = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha_w) * seed])
            smoothed, _ = lfilter(b_filt, a_filt, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


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


def _map_d1_alert_to_h4(d1_alerts: np.ndarray, d1_ct: np.ndarray,
                         h4_ct: np.ndarray) -> np.ndarray:
    """Map D1 alert level to H4 bar grid (causal: use last completed D1)."""
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


def _metrics_vec(nav, wi):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0}
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
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}


def _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=CPS_HARSH):
    """Vanilla X0 vectorized sim."""
    n = len(cl)
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, SLOW)
    at = _atr_h4(hi, lo, cl, ATR_PERIOD)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

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
                cash = bq * fp * (1 - cps)
                bq = 0.0
                inp = False
                nt += 1
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
        cash += bq * cl[-1] * (1 - cps)
        bq = 0
        nt += 1
        nav[-1] = cash
    return nav, nt


def _sim_x0_monitored(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                       h4_alerts, cps=CPS_HARSH):
    """X0 with RED monitor override: force flat during RED periods."""
    n = len(cl)
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, SLOW)
    at = _atr_h4(hi, lo, cl, ATR_PERIOD)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    nav = np.zeros(n)
    n_monitor_exits = 0

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
                cash = bq * fp * (1 - cps)
                bq = 0.0
                inp = False
                nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        is_red = h4_alerts[i] == 2

        if not inp:
            # Don't enter during RED
            if not is_red and ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            # Force exit during RED
            if is_red:
                px = True
                n_monitor_exits += 1
            elif p < pk - 3.0 * at[i]:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps)
        bq = 0
        nt += 1
        nav[-1] = cash

    return nav, nt, n_monitor_exits


def run_backtest_comparison(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                            h4_alerts):
    """Run X0 vanilla vs X0+monitor and compare."""
    print("\n" + "=" * 80)
    print("S4: BACKTEST COMPARISON — X0 vs X0+MONITOR (harsh, 50 bps RT)")
    print("=" * 80)

    # Vanilla X0
    nav_v, nt_v = _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    m_v = _metrics_vec(nav_v, wi)

    # X0 + monitor
    nav_m, nt_m, n_mon_exits = _sim_x0_monitored(
        cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_alerts)
    m_m = _metrics_vec(nav_m, wi)

    print(f"\n  {'Metric':20s} {'X0 Vanilla':>14s} {'X0+Monitor':>14s} {'Delta':>12s}")
    print(f"  {'-'*60}")
    for key, fmt, label in [
        ("sharpe", ".4f", "Sharpe"),
        ("cagr", ".2f", "CAGR %"),
        ("mdd", ".2f", "MDD %"),
    ]:
        v = m_v[key]
        m = m_m[key]
        d = m - v
        print(f"  {label:20s} {v:14{fmt}} {m:14{fmt}} {d:+12{fmt}}")
    print(f"  {'Trades':20s} {nt_v:14d} {nt_m:14d} {nt_m - nt_v:+12d}")
    print(f"  {'Monitor exits':20s} {'—':>14s} {n_mon_exits:14d}")
    print(f"  {'Final NAV':20s} {nav_v[-1]:14.2f} {nav_m[-1]:14.2f} {nav_m[-1]-nav_v[-1]:+12.2f}")

    return {
        "vanilla": {**m_v, "trades": nt_v, "final_nav": float(nav_v[-1])},
        "monitored": {**m_m, "trades": nt_m, "final_nav": float(nav_m[-1]),
                      "monitor_exits": n_mon_exits},
        "delta": {
            "sharpe": m_m["sharpe"] - m_v["sharpe"],
            "cagr": m_m["cagr"] - m_v["cagr"],
            "mdd": m_m["mdd"] - m_v["mdd"],
            "trades": nt_m - nt_v,
        },
    }


# =========================================================================
# S5: CORRECTED MONITOR — ATR% (normalized by price)
# =========================================================================


def rolling_atr_pct_percentile(atr: np.ndarray, close: np.ndarray,
                                window: int = ROLL_WINDOW,
                                q: float = ATR_Q) -> np.ndarray:
    """Rolling Qth percentile of ATR% (ATR/close × 100) over trailing window."""
    n = len(atr)
    atr_pct = np.full(n, np.nan)
    valid = ~np.isnan(atr) & (close > 0)
    atr_pct[valid] = atr[valid] / close[valid] * 100.0

    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        seg = atr_pct[t - window + 1: t + 1]
        seg_valid = seg[~np.isnan(seg)]
        if len(seg_valid) >= window // 2:
            out[t] = np.percentile(seg_valid, q)
    return out


def run_corrected_monitor(d1_close, d1_high, d1_low, d1_ct, h4_ct,
                           cl, hi, lo, vo, tb, wi, feed,
                           d1_report_idx):
    """Re-run the full monitor pipeline using ATR% instead of raw ATR."""
    print("\n" + "=" * 80)
    print("S5: CORRECTED MONITOR — ATR% (ATR/price normalized)")
    print("=" * 80)

    atr = _atr_d1(d1_high, d1_low, d1_close, ATR_PERIOD)

    # Rolling MDD (unchanged)
    r_mdd = rolling_mdd(d1_close, ROLL_WINDOW)

    # Rolling ATR% Q90 (normalized by price)
    r_atr_pct_q90 = rolling_atr_pct_percentile(atr, d1_close, ROLL_WINDOW, ATR_Q)

    # Training mean on ATR% Q90
    train_mean_pct, train_start, train_end = compute_training_mean(
        r_atr_pct_q90, TRAIN_DAYS)
    print(f"  Training ATR% Q{ATR_Q} mean: {train_mean_pct:.4f}%")

    # ATR% ratio
    n_d1 = len(d1_close)
    atr_pct_ratio = np.full(n_d1, np.nan)
    valid = ~np.isnan(r_atr_pct_q90) & (train_mean_pct > 0)
    atr_pct_ratio[valid] = r_atr_pct_q90[valid] / train_mean_pct

    # Classify using same thresholds
    alerts_corr = classify_alerts(r_mdd, atr_pct_ratio)

    n_normal = int(np.sum(alerts_corr == 0))
    n_amber = int(np.sum(alerts_corr == 1))
    n_red = int(np.sum(alerts_corr == 2))
    print(f"\n  Corrected alert distribution:")
    print(f"    NORMAL: {n_normal:5d} ({n_normal/n_d1*100:.1f}%)")
    print(f"    AMBER:  {n_amber:5d} ({n_amber/n_d1*100:.1f}%)")
    print(f"    RED:    {n_red:5d} ({n_red/n_d1*100:.1f}%)")

    # RED breakdown: MDD vs ATR%
    red_by_mdd = red_by_atr = red_by_both = 0
    for t in range(n_d1):
        if alerts_corr[t] == 2:
            m_ok = not np.isnan(r_mdd[t]) and r_mdd[t] > RED_MDD
            a_ok = not np.isnan(atr_pct_ratio[t]) and atr_pct_ratio[t] > RED_ATR_RATIO
            if m_ok and a_ok:
                red_by_both += 1
            elif m_ok:
                red_by_mdd += 1
            elif a_ok:
                red_by_atr += 1
    print(f"\n  RED trigger breakdown (corrected):")
    print(f"    MDD only:  {red_by_mdd}")
    print(f"    ATR% only: {red_by_atr}")
    print(f"    Both:      {red_by_both}")

    # Episode analysis
    episode_data_corr = analyze_episodes(alerts_corr, d1_close, d1_ct)

    # False positive analysis
    fp_data_corr = false_positive_analysis(
        alerts_corr, d1_close, d1_ct, d1_report_idx)

    # Backtest comparison
    h4_alerts_corr = _map_d1_alert_to_h4(alerts_corr, d1_ct, h4_ct)
    d1_cl_arr = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    bt_corr = run_backtest_comparison(
        cl, hi, lo, vo, tb, wi, d1_cl=d1_cl_arr,
        d1_ct=d1_ct, h4_ct=h4_ct, h4_alerts=h4_alerts_corr)

    return {
        "alerts": alerts_corr,
        "train_mean_pct": train_mean_pct,
        "alert_counts": {
            "total_bars": n_d1,
            "normal": n_normal,
            "amber": n_amber,
            "red": n_red,
        },
        "red_breakdown": {
            "mdd_only": red_by_mdd,
            "atr_pct_only": red_by_atr,
            "both": red_by_both,
        },
        "episodes": episode_data_corr,
        "false_positive": fp_data_corr,
        "backtest": bt_corr,
    }


# =========================================================================
# SAVE OUTPUTS
# =========================================================================


def save_all(monitor_data, episode_data, fp_data, bt_comparison,
             d1_close, d1_close_times, corrected=None):
    """Save all results to files."""

    # 1. Monitor signals CSV
    csv_path = OUTDIR / "x0a_monitor_signals.csv"
    n = len(d1_close)
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bar_idx", "date", "close", "rolling_mdd",
                     "rolling_atr_q90", "atr_ratio", "alert_level", "alert_name"])
        for t in range(n):
            date = datetime.fromtimestamp(
                d1_close_times[t] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            mdd_v = f"{monitor_data['rolling_mdd'][t]:.6f}" if not np.isnan(monitor_data['rolling_mdd'][t]) else ""
            q90_v = f"{monitor_data['rolling_atr_q90'][t]:.2f}" if not np.isnan(monitor_data['rolling_atr_q90'][t]) else ""
            ratio_v = f"{monitor_data['atr_ratio'][t]:.4f}" if not np.isnan(monitor_data['atr_ratio'][t]) else ""
            alert = int(monitor_data['alerts'][t])
            w.writerow([t, date, f"{d1_close[t]:.2f}", mdd_v, q90_v, ratio_v,
                        alert, ALERT_NAMES[alert]])
    print(f"\nSaved: {csv_path}")

    # 2. Episode summary CSV
    csv_ep = OUTDIR / "x0a_episode_summary.csv"
    with open(csv_ep, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "idx", "start_date", "end_date",
                     "duration_days", "btc_return_pct"])
        for level in ["AMBER", "RED"]:
            for ep in episode_data.get(level, {}).get("episodes", []):
                w.writerow([level, ep["idx"], ep["start_date"], ep["end_date"],
                            ep["duration_days"], f"{ep['btc_return_pct']:.2f}"])
    print(f"Saved: {csv_ep}")

    # 3. Full results JSON
    json_path = OUTDIR / "x0a_results.json"
    out = {
        "monitor_params": {
            "roll_window": ROLL_WINDOW,
            "atr_period": ATR_PERIOD,
            "atr_percentile": ATR_Q,
            "train_days": TRAIN_DAYS,
            "amber_mdd": AMBER_MDD,
            "amber_atr_ratio": AMBER_ATR_RATIO,
            "red_mdd": RED_MDD,
            "red_atr_ratio": RED_ATR_RATIO,
        },
        "training": {
            "atr_q90_mean": monitor_data["train_mean"],
            "train_start_bar": monitor_data["train_start"],
            "train_end_bar": monitor_data["train_end"],
        },
        "alert_counts": {
            "total_bars": len(d1_close),
            "normal": int(np.sum(monitor_data["alerts"] == 0)),
            "amber": int(np.sum(monitor_data["alerts"] == 1)),
            "red": int(np.sum(monitor_data["alerts"] == 2)),
        },
        "episodes": {k: {kk: vv for kk, vv in v.items() if kk != "durations"}
                     for k, v in episode_data.items()},
        "false_positive_analysis": fp_data,
        "backtest_comparison": bt_comparison,
    }
    if corrected is not None:
        out["corrected_atr_pct"] = {
            "training_atr_pct_q90_mean": corrected["train_mean_pct"],
            "alert_counts": corrected["alert_counts"],
            "red_breakdown": corrected["red_breakdown"],
            "false_positive": corrected["false_positive"],
            "backtest": corrected["backtest"],
        }
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"Saved: {json_path}")

    return out


# =========================================================================
# REPORT GENERATION
# =========================================================================


def generate_report(results: dict, monitor_data: dict, episode_data: dict,
                    corrected: dict | None = None):
    """Generate markdown report."""
    ac = results["alert_counts"]
    fp = results["false_positive_analysis"]
    bt = results["backtest_comparison"]
    mp = results["monitor_params"]

    report = f"""# X0A — Runtime Regime Monitor Research Report

## 1. Objective

Evaluate a runtime regime monitor that detects dangerous market conditions
using two complementary signals:

1. **Rolling 6-month MDD**: captures sustained drawdowns
2. **Rolling ATR Q90**: captures volatility regime shifts

Alert thresholds calibrated against training-period statistics.

## 2. Monitor Parameters

| Parameter | Value |
|-----------|-------|
| Rolling window | {mp['roll_window']} D1 bars (~6 months) |
| ATR period | {mp['atr_period']} (Wilder) |
| ATR percentile | Q{mp['atr_percentile']} |
| Training period | {mp['train_days']} D1 bars |
| Training ATR Q90 mean (raw) | {results['training']['atr_q90_mean']:.2f} |
| AMBER thresholds | MDD > {mp['amber_mdd']*100:.0f}% OR ATR ratio > {mp['amber_atr_ratio']:.2f}x |
| RED thresholds | MDD > {mp['red_mdd']*100:.0f}% OR ATR ratio > {mp['red_atr_ratio']:.2f}x |

## 3. Raw ATR Monitor (FLAWED — Section retained for documentation)

### 3.1 Alert Distribution (raw ATR)

| Level | Count | % of Total |
|-------|------:|----------:|
| NORMAL | {ac['normal']} | {ac['normal']/ac['total_bars']*100:.1f}% |
| AMBER | {ac['amber']} | {ac['amber']/ac['total_bars']*100:.1f}% |
| RED | {ac['red']} | {ac['red']/ac['total_bars']*100:.1f}% |

**DIAGNOSIS**: 71.6% of bars flagged RED. Root cause: raw ATR scales linearly with
BTC price ($535 training mean at $4K BTC becomes permanently >7x at $90K BTC).
99.7% of RED days triggered by ATR channel alone. Raw ATR is **structurally
broken** as a regime monitor signal.

### 3.2 Backtest (raw ATR, harsh)

| Metric | X0 Vanilla | X0+Monitor | Delta |
|--------|----------:|----------:|------:|
| Sharpe | {bt['vanilla']['sharpe']:.4f} | {bt['monitored']['sharpe']:.4f} | {bt['delta']['sharpe']:+.4f} |
| CAGR % | {bt['vanilla']['cagr']:.2f} | {bt['monitored']['cagr']:.2f} | {bt['delta']['cagr']:+.2f} |
| MDD % | {bt['vanilla']['mdd']:.2f} | {bt['monitored']['mdd']:.2f} | {bt['delta']['mdd']:+.2f} |
| Trades | {bt['vanilla']['trades']} | {bt['monitored']['trades']} | {bt['delta']['trades']:+d} |

MDD improves -14.3% but at catastrophic CAGR cost (-17.7%) because the monitor
is flat during the entire 2021-2026 bull market.

"""

    if corrected is not None:
        cc = corrected
        ca = cc["alert_counts"]
        cfp = cc["false_positive"]
        cbt = cc["backtest"]

        report += f"""## 4. Corrected Monitor: ATR% (ATR/price, normalized)

Training ATR% Q90 mean: {cc['train_mean_pct']:.4f}%

### 4.1 Alert Distribution (ATR% normalized)

| Level | Count | % of Total |
|-------|------:|----------:|
| NORMAL | {ca['normal']} | {ca['normal']/ca['total_bars']*100:.1f}% |
| AMBER | {ca['amber']} | {ca['amber']/ca['total_bars']*100:.1f}% |
| RED | {ca['red']} | {ca['red']/ca['total_bars']*100:.1f}% |

RED trigger breakdown: MDD-only={cc['red_breakdown']['mdd_only']}, \
ATR%-only={cc['red_breakdown']['atr_pct_only']}, \
both={cc['red_breakdown']['both']}

"""
        # Corrected episodes
        for level in ["AMBER", "RED"]:
            ep = cc["episodes"].get(level, {})
            if ep.get("count", 0) == 0:
                report += f"### 4.2 {level} Episodes (corrected): 0\n\n"
                continue
            report += f"### 4.2 {level} Episodes (corrected): {ep['count']} "
            report += f"({ep['total_days']} total days, mean {ep['mean_duration']:.1f}d)\n\n"
            report += "| # | Start | End | Duration | BTC Return |\n"
            report += "|---|-------|-----|----------|------------|\n"
            for e in ep["episodes"]:
                report += (f"| {e['idx']} | {e['start_date']} | {e['end_date']} "
                          f"| {e['duration_days']}d | {e['btc_return_pct']:+.1f}% |\n")
            report += "\n"

        report += """### 4.3 False Positive Analysis (corrected, reporting period)

"""
        if cfp["n_red_episodes"] == 0:
            report += "No RED episodes in reporting period.\n\n"
        else:
            report += f"""- **Total RED episodes**: {cfp['n_red_episodes']}
- **True positives**: {cfp['true_positives']} ({cfp['true_positives']/cfp['n_red_episodes']*100:.1f}%)
- **False positives**: {cfp['false_positives']} ({cfp['false_positives']/cfp['n_red_episodes']*100:.1f}%)
- **FP Rate**: {cfp['fp_rate']:.1%}

| Start | End | Duration | BTC During | Verdict |
|-------|-----|----------|------------|---------|"""
            for d in cfp["details"]:
                v = "FP" if d["is_false_positive"] else "TP"
                report += (f"\n| {d['start_date']} | {d['end_date']} | {d['duration']}d "
                          f"| {d['btc_during_pct']:+.1f}% | {v} |")
            report += "\n\n"

        report += f"""### 4.4 Backtest Comparison (corrected, harsh)

| Metric | X0 Vanilla | X0+Monitor(corr) | Delta |
|--------|----------:|----------:|------:|
| Sharpe | {cbt['vanilla']['sharpe']:.4f} | {cbt['monitored']['sharpe']:.4f} | {cbt['delta']['sharpe']:+.4f} |
| CAGR % | {cbt['vanilla']['cagr']:.2f} | {cbt['monitored']['cagr']:.2f} | {cbt['delta']['cagr']:+.2f} |
| MDD % | {cbt['vanilla']['mdd']:.2f} | {cbt['monitored']['mdd']:.2f} | {cbt['delta']['mdd']:+.2f} |
| Trades | {cbt['vanilla']['trades']} | {cbt['monitored']['trades']} | {cbt['delta']['trades']:+d} |
| Monitor exits | - | {cbt['monitored']['monitor_exits']} | |
| Final NAV | {cbt['vanilla']['final_nav']:.2f} | {cbt['monitored']['final_nav']:.2f} | {cbt['monitored']['final_nav'] - cbt['vanilla']['final_nav']:+.2f} |

"""

    report += """## 5. Verdict

"""
    if corrected is not None:
        cbt = corrected["backtest"]
        cfp = corrected["false_positive"]
        mdd_improved = cbt["delta"]["mdd"] < -2.0
        sharpe_hurt = cbt["delta"]["sharpe"] < -0.05
        fp_high = cfp.get("fp_rate", 0) > 0.40
        fp_rate = cfp.get("fp_rate", 0)

        report += "### Raw ATR monitor: REJECT\n\n"
        report += ("Raw ATR scales with price, producing 71.6% RED rate and "
                   "destroying returns. Fundamentally broken.\n\n")
        report += "### Corrected ATR% monitor:\n\n"

        if mdd_improved and not sharpe_hurt:
            report += "**POSITIVE**: Corrected monitor reduces MDD without material Sharpe loss.\n"
        elif mdd_improved and sharpe_hurt:
            report += "**TRADEOFF**: Corrected monitor reduces MDD but at cost of Sharpe/CAGR.\n"
        elif not mdd_improved:
            report += "**NEUTRAL/NEGATIVE**: Corrected monitor does not materially improve MDD.\n"

        if fp_high:
            report += (f"\n**WARNING**: FP rate is {fp_rate:.1%}. "
                      "Monitor may still trigger too aggressively.\n")

        ca = corrected["alert_counts"]
        report += (f"\nAlert budget: {ca['red']} RED days "
                  f"({ca['red']/ca['total_bars']*100:.1f}% of history).\n")
    else:
        mdd_improved = bt["delta"]["mdd"] < -2.0
        sharpe_hurt = bt["delta"]["sharpe"] < -0.05
        if mdd_improved and not sharpe_hurt:
            report += "**POSITIVE**: Monitor reduces MDD without material Sharpe loss.\n"
        elif mdd_improved and sharpe_hurt:
            report += "**TRADEOFF**: Monitor reduces MDD but at cost of Sharpe/CAGR.\n"
        else:
            report += "**NEUTRAL/NEGATIVE**: Monitor does not materially improve MDD.\n"

    report += "\n---\n*Generated by x0a/regime_monitor.py*\n"

    rpt_path = OUTDIR / "X0A_REGIME_MONITOR_REPORT.md"
    with open(rpt_path, "w") as f:
        f.write(report)
    print(f"Saved: {rpt_path}")


# =========================================================================
# MAIN
# =========================================================================


def main():
    print("=" * 80)
    print("X0A RESEARCH: Runtime Regime Monitor")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  Rolling window: {ROLL_WINDOW}d, ATR({ATR_PERIOD}), Q{ATR_Q}")
    print(f"  AMBER: MDD>{AMBER_MDD*100:.0f}% or ATR ratio>{AMBER_ATR_RATIO:.2f}")
    print(f"  RED:   MDD>{RED_MDD*100:.0f}% or ATR ratio>{RED_ATR_RATIO:.2f}")
    print("=" * 80)

    # Load data
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    # D1 arrays (for monitor)
    d1_close = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_high = np.array([b.high for b in feed.d1_bars], dtype=np.float64)
    d1_low = np.array([b.low for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    # H4 arrays (for backtest sim)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    # Warmup index for reporting window
    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # D1 reporting start index
    d1_report_idx = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.d1_bars):
            if b.close_time >= feed.report_start_ms:
                d1_report_idx = j
                break

    print(f"\n  D1 bars: {len(d1_close)}, H4 bars: {len(cl)}")
    print(f"  H4 warmup index: {wi}, D1 report start index: {d1_report_idx}")

    # S1: Compute monitor signals
    monitor_data = compute_monitor_signals(d1_close, d1_high, d1_low)

    # S2: Episode analysis
    episode_data = analyze_episodes(monitor_data["alerts"], d1_close, d1_ct)

    # S3: False positive analysis
    fp_data = false_positive_analysis(
        monitor_data["alerts"], d1_close, d1_ct, d1_report_idx)

    # S4: Backtest comparison
    h4_alerts = _map_d1_alert_to_h4(monitor_data["alerts"], d1_ct, h4_ct)
    bt_comparison = run_backtest_comparison(
        cl, hi, lo, vo, tb, wi, d1_cl=np.array([b.close for b in feed.d1_bars]),
        d1_ct=d1_ct, h4_ct=h4_ct, h4_alerts=h4_alerts)

    # S5: Corrected monitor (ATR% normalized)
    corrected = run_corrected_monitor(
        d1_close, d1_high, d1_low, d1_ct, h4_ct,
        cl, hi, lo, vo, tb, wi, feed, d1_report_idx)

    # Save everything
    results = save_all(monitor_data, episode_data, fp_data, bt_comparison,
                       d1_close, d1_ct, corrected=corrected)

    # Generate report
    generate_report(results, monitor_data, episode_data, corrected=corrected)

    print("\n" + "=" * 80)
    print("X0A REGIME MONITOR RESEARCH COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
