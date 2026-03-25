#!/usr/bin/env python3
"""X14 Research — Trail-Stop Churn Filter: Design & Validation

Central question: Can we capture X13's churn-prediction signal with a
simple filter that strictly improves E0+EMA1D21 — and survives proper
OOS validation?

Designs (tested in order of complexity, fixed-sequence FWER):
  A: Entry-signal gate (0 new params)
  B: EMA-ratio threshold (1 new param)
  C: EMA-ratio + D1-regime dual threshold (2 new params)
  D: Walk-forward logistic model (model-based)

Tests:
  T0: Full-sample screening (all designs)
  T1: Walk-forward validation (4 expanding folds)
  T2: Bootstrap validation (500 VCBB paths)
  T3: Jackknife leave-year-out (6 folds)
  T4: DOF correction / PSR
  T5: Comprehensive comparison table

Gates (all must pass for PROMOTE):
  G0: T0 d_sharpe > 0
  G1: T1 win_rate >= 3/4
  G2: T2 P(d_sharpe > 0) > 0.60
  G3: T2 median d_mdd <= +5.0 pp
  G4: T3 d_sharpe < 0 in <= 2/6 years
  G5: T4 PSR > 0.95
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
from scipy.optimize import minimize as sp_minimize

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
ATR_P = 14

# E5 robust ATR constants (for T5 comparison)
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0

CHURN_WINDOW = 20

# Design B grid
TAU_GRID_B = [1.000, 1.005, 1.010, 1.015, 1.020, 1.025, 1.030, 1.035, 1.040, 1.050, 1.060, 1.080]

# Design C grid
TAU_EMA_GRID_C = [1.00, 1.01, 1.02, 1.03, 1.04, 1.05]
TAU_D1_GRID_C = [0.00, 0.01, 0.02, 0.03, 0.04, 0.05]

# Design D
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]

# WFO fold boundaries (train_end, test_start, test_end)
# Expanding window: train always starts at wi
WFO_FOLDS = [
    ("2021-12-31", "2022-01-01", "2022-12-31"),
    ("2022-12-31", "2023-01-01", "2023-12-31"),
    ("2023-12-31", "2024-01-01", "2024-12-31"),
    ("2024-12-31", "2025-01-01", "2026-02-20"),
]

# Jackknife years
JK_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

# Bootstrap
N_BOOT = 500
BLKSZ = 60
SEED = 42

# PSR / DOF
E0_EFFECTIVE_DOF = 4.35  # Nyholt M_eff from prod_readiness study

FEATURE_NAMES = [
    "ema_ratio", "bars_held", "atr_pctl", "bar_range_atr",
    "dd_from_peak", "bars_since_peak", "close_position",
    "vdo_at_exit", "d1_regime_str", "trail_tightness",
]

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# FAST INDICATORS (vectorized, identical to X12/X13)
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
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "trades": nt}
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
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "trades": nt}


def _metrics_window(nav, start_idx, end_idx, nt=0):
    """Compute metrics for a sub-window [start_idx, end_idx)."""
    navs = nav[start_idx:end_idx]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "trades": nt}
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
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "trades": nt}


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


def _compute_d1_regime_str(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
    """Compute (D1_close - D1_EMA) / D1_close mapped to H4 bars."""
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_str = np.where(d1_cl > 1e-12, (d1_cl - d1_ema) / d1_cl, 0.0)
    n_h4 = len(h4_ct)
    str_h4 = np.zeros(n_h4)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            str_h4[i] = d1_str[d1_idx]
    return str_h4


def _compute_indicators(cl, hi, lo, vo, tb, slow_period=SLOW):
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    vd = _vdo(cl, hi, lo, vo, tb)
    at = _atr(hi, lo, cl, ATR_P)
    return ef, es, vd, at


def _date_to_bar_idx(h4_ct, date_str):
    """Convert date string to H4 bar index using close_time.
    Returns first bar whose close_time is on or after date_str (00:00 UTC).
    """
    import datetime
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ts_ms = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    idx = np.searchsorted(h4_ct, ts_ms, side='left')
    return min(idx, len(h4_ct) - 1)


# =========================================================================
# SIM CORE — E0+EMA1D21 with optional suppress mask
# =========================================================================

def _run_sim(cl, ef, es, vd, at, regime_h4, wi,
             trail_mult=TRAIL, cps=CPS_HARSH,
             suppress_mask=None, atr_arr=None):
    """E0+EMA1D21 sim with precomputed indicators.

    suppress_mask: boolean array (n,). If True at bar i, trail stop is
    suppressed (position stays open). EMA cross-down exit unaffected.

    atr_arr: override ATR array (for E5 comparison using robust ATR).

    Returns (nav, trades, trail_stats) where trail_stats = dict with
    n_trail_triggered, n_trail_suppressed, n_trail_allowed.
    """
    n = len(cl)
    if atr_arr is not None:
        at_use = atr_arr
    else:
        at_use = at

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

    n_trail_triggered = 0
    n_trail_suppressed = 0

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
                a_val = at_use[i - 1] if not math.isnan(at_use[i - 1]) else 0.0
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
                })
                cash = received
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1

        nav[i] = cash + bq * p

        a_val = at_use[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * a_val
            if p < ts:
                n_trail_triggered += 1
                # Check suppress mask
                if suppress_mask is not None and suppress_mask[i]:
                    n_trail_suppressed += 1
                    # Stay in position — trail continues
                else:
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
        })
        cash = received
        bq = 0.0
        nt += 1
        nav[-1] = cash

    trail_stats = {
        "n_trail_triggered": n_trail_triggered,
        "n_trail_suppressed": n_trail_suppressed,
        "n_trail_allowed": n_trail_triggered - n_trail_suppressed,
    }

    return nav, trades, trail_stats


def _run_sim_oracle(cl, ef, es, vd, at, regime_h4, wi,
                    trail_mult=TRAIL, cps=CPS_HARSH,
                    churn_window=CHURN_WINDOW):
    """Oracle sim: suppress trail stop if entry signal fires within churn_window."""
    n = len(cl)
    entry_sig = np.zeros(n, dtype=np.bool_)
    for j in range(n):
        if not (math.isnan(ef[j]) or math.isnan(es[j]) or math.isnan(at[j])):
            entry_sig[j] = ef[j] > es[j] and vd[j] > VDO_THR and regime_h4[j]

    # Build oracle suppress mask: at bar i, suppress if any entry_sig in (i, i+churn_window]
    suppress = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        end = min(i + 1 + churn_window, n)
        if end > i + 1 and np.any(entry_sig[i + 1:end]):
            suppress[i] = True

    return _run_sim(cl, ef, es, vd, at, regime_h4, wi, trail_mult, cps,
                    suppress_mask=suppress)


# =========================================================================
# FILTER MASK BUILDERS
# =========================================================================

def _mask_design_a(ef, es, vd, regime_h4):
    """Design A: suppress trail stop when entry signal is active (0 params)."""
    n = len(ef)
    mask = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        mask[i] = ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]
    return mask


def _mask_design_b(ef, es, tau):
    """Design B: suppress trail stop when ema_ratio > tau (1 param)."""
    n = len(ef)
    mask = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or abs(es[i]) < 1e-12:
            continue
        mask[i] = ef[i] / es[i] > tau
    return mask


def _mask_design_c(ef, es, d1_str_h4, tau_ema, tau_d1):
    """Design C: suppress when ema_ratio > tau_ema AND d1_regime_str > tau_d1."""
    n = len(ef)
    mask = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or abs(es[i]) < 1e-12:
            continue
        mask[i] = (ef[i] / es[i] > tau_ema) and (d1_str_h4[i] > tau_d1)
    return mask


def _mask_design_d(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                   regime_h4, wi, train_end_idx,
                   trail_mult=TRAIL, cps=CPS_HARSH):
    """Design D: logistic model trained on train data, applied to full data.

    Returns mask for the FULL array (but model only trained on [wi, train_end_idx)).
    """
    n = len(cl)

    # Step 1: Run E0 sim on training portion to get trail stop exits + features
    nav_train, trades_train, _ = _run_sim(
        cl[:train_end_idx], ef[:train_end_idx], es[:train_end_idx],
        vd[:train_end_idx], at[:train_end_idx], regime_h4[:train_end_idx],
        wi, trail_mult, cps)

    # Label churn
    churn_labels = _label_churn(trades_train)
    if len(churn_labels) < 10:
        return np.zeros(n, dtype=np.bool_)

    # Extract features
    X_tr, y_tr = _extract_features_from_labels(
        trades_train, churn_labels, cl[:train_end_idx], hi[:train_end_idx],
        lo[:train_end_idx], at[:train_end_idx], ef[:train_end_idx],
        es[:train_end_idx], vd[:train_end_idx], d1_str_h4[:train_end_idx],
        trail_mult)

    if len(y_tr) < 10 or len(np.unique(y_tr)) < 2:
        return np.zeros(n, dtype=np.bool_)

    # Standardize and select C
    X_s, mu, std = _standardize(X_tr)
    best_c = 1.0
    best_auc = 0.0
    for c_val in C_VALUES:
        auc_c = _kfold_auc(X_s, y_tr, C=c_val, k=5)
        if auc_c > best_auc:
            best_auc = auc_c
            best_c = c_val

    # Fit model
    w = _fit_logistic_l2(X_s, y_tr, C=best_c)

    # Build mask: at each bar, compute features and predict
    # For efficiency, precompute ema_ratio and d1_str across all bars
    mask = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at[i]):
            continue
        if abs(es[i]) < 1e-12 or at[i] < 1e-12 or cl[i] < 1e-12:
            continue

        # Build 10-feature vector at bar i (same as X13 features)
        f1 = ef[i] / es[i]  # ema_ratio
        f2 = 0.0  # bars_held — unknown at suppression time, use 0
        # atr_pctl
        atr_start = max(0, i - 99)
        atr_window = at[atr_start:i + 1]
        valid_atr = atr_window[~np.isnan(atr_window)]
        f3 = float(np.sum(valid_atr <= at[i])) / len(valid_atr) if len(valid_atr) > 1 else 0.5
        # bar_range_atr
        f4 = (hi[i] - lo[i]) / at[i]
        # dd_from_peak — unknown without trade context, use 0
        f5 = 0.0
        # bars_since_peak — unknown, use 0
        f6 = 0.0
        # close_position
        bar_w = hi[i] - lo[i]
        f7 = (cl[i] - lo[i]) / bar_w if bar_w > 1e-12 else 0.5
        # vdo_at_exit
        f8 = float(vd[i])
        # d1_regime_str
        f9 = float(d1_str_h4[i])
        # trail_tightness
        f10 = TRAIL * at[i] / cl[i]

        feat = np.array([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10])
        feat_s = (feat - mu) / std
        z = np.dot(np.append(feat_s, 1.0), w)
        prob = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
        mask[i] = prob > 0.5  # P(churn) > 0.5 → suppress

    return mask


# =========================================================================
# CHURN LABELING (from X13)
# =========================================================================

def _label_churn(trades, churn_window=CHURN_WINDOW):
    """Label each trail stop exit as churn (1) or true reversal (0)."""
    entry_bars = sorted(t["entry_bar"] for t in trades)
    results = []
    for idx, t in enumerate(trades):
        if t["exit_reason"] != "trail_stop":
            continue
        eb = t["exit_bar"]
        is_churn = any(eb < e <= eb + churn_window for e in entry_bars)
        results.append((idx, 1 if is_churn else 0))
    return results


def _extract_features_from_labels(trades, churn_labels, cl, hi, lo, at, ef, es, vd,
                                  d1_str_h4, trail_mult=TRAIL):
    """Extract features at each trail stop exit given pre-computed labels."""
    n = len(cl)
    features = []
    labels = []

    for trade_idx, label in churn_labels:
        t = trades[trade_idx]
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n:
            continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue

        f1 = ef[sb] / es[sb] if abs(es[sb]) > 1e-12 else 1.0
        f2 = float(t["bars_held"])

        atr_start = max(0, sb - 99)
        atr_window = at[atr_start:sb + 1]
        valid_atr = atr_window[~np.isnan(atr_window)]
        f3 = float(np.sum(valid_atr <= at[sb])) / len(valid_atr) if len(valid_atr) > 1 else 0.5

        f4 = (hi[sb] - lo[sb]) / at[sb] if at[sb] > 1e-12 else 1.0

        peak_px = t["peak_px"]
        f5 = (peak_px - cl[sb]) / peak_px if peak_px > 1e-12 else 0.0

        eb = t["entry_bar"]
        trade_closes = cl[eb:t["exit_bar"]]
        if len(trade_closes) > 0:
            peak_bar = eb + int(np.argmax(trade_closes))
            f6 = float(sb - peak_bar)
        else:
            f6 = 0.0

        bar_w = hi[sb] - lo[sb]
        f7 = (cl[sb] - lo[sb]) / bar_w if bar_w > 1e-12 else 0.5
        f8 = float(vd[sb])
        f9 = float(d1_str_h4[sb])
        f10 = trail_mult * at[sb] / cl[sb] if cl[sb] > 1e-12 else 0.0

        features.append([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10])
        labels.append(label)

    return np.array(features) if features else np.empty((0, 10)), np.array(labels, dtype=int)


# =========================================================================
# STATISTICAL UTILITIES (from X13)
# =========================================================================

def _fit_logistic_l2(X, y, C=1.0, max_iter=100):
    """Fit L2-regularized logistic regression via Newton-Raphson."""
    n, d = X.shape
    Xa = np.column_stack([X, np.ones(n)])
    w = np.zeros(d + 1)

    for _ in range(max_iter):
        z = Xa @ w
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
        err = p - y
        reg = np.zeros(d + 1)
        reg[:d] = w[:d] / C
        grad = Xa.T @ err / n + reg
        S = p * (1 - p) + 1e-12
        H = (Xa.T * S) @ Xa / n
        H_reg = np.zeros((d + 1, d + 1))
        np.fill_diagonal(H_reg[:d, :d], 1.0 / C)
        H += H_reg
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            break
        w -= step
        if np.max(np.abs(step)) < 1e-8:
            break

    return w


def _kfold_auc(X, y, C=1.0, k=5, rng=None):
    """K-fold CV AUC."""
    n = X.shape[0]
    if rng is None:
        idx = np.arange(n)
    else:
        idx = rng.permutation(n)
    preds = np.zeros(n)
    fold_size = n // k
    for fold in range(k):
        start = fold * fold_size
        end = start + fold_size if fold < k - 1 else n
        test_mask = np.zeros(n, dtype=bool)
        test_mask[idx[start:end]] = True
        train_mask = ~test_mask
        X_tr, y_tr = X[train_mask], y[train_mask]
        X_te = X[test_mask]
        if len(np.unique(y_tr)) < 2:
            preds[test_mask] = np.mean(y_tr)
            continue
        w = _fit_logistic_l2(X_tr, y_tr, C)
        z = np.column_stack([X_te, np.ones(X_te.shape[0])]) @ w
        preds[test_mask] = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
    return _roc_auc(y, preds)


def _roc_auc(y_true, y_score):
    """AUC via concordance."""
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    comp = pos[:, None] > neg[None, :]
    ties = pos[:, None] == neg[None, :]
    return float((np.sum(comp) + 0.5 * np.sum(ties)) / (len(pos) * len(neg)))


def _standardize(X):
    """Standardize to zero mean, unit variance."""
    mu = np.mean(X, axis=0)
    std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


def _psr(sharpe, n_returns, sr0=0.0):
    """Probabilistic Sharpe Ratio (Bailey & López de Prado, 2014).

    Returns probability that the true Sharpe > sr0, given observed Sharpe
    and n returns. Assumes IID returns (conservative).
    """
    from scipy.stats import norm
    if n_returns < 3:
        return 0.5
    se = 1.0 / math.sqrt(n_returns)
    z = (sharpe - sr0) / se if se > 1e-12 else 0.0
    return float(norm.cdf(z))


# =========================================================================
# T0: FULL-SAMPLE SCREENING
# =========================================================================

def run_t0_screening(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct):
    """T0: Full-sample screening — all designs."""
    print("\n" + "=" * 70)
    print("T0: FULL-SAMPLE SCREENING")
    print("=" * 70)

    # E0 baseline
    nav_e0, trades_e0, ts_e0 = _run_sim(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))
    print(f"\n  E0 baseline: Sharpe={m_e0['sharpe']:.4f}, CAGR={m_e0['cagr']:.2f}%, "
          f"MDD={m_e0['mdd']:.2f}%, trades={m_e0['trades']}")

    rows = []

    # --- Design A ---
    mask_a = _mask_design_a(ef, es, vd, regime_h4)
    nav_a, trades_a, ts_a = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                     suppress_mask=mask_a)
    m_a = _metrics(nav_a, wi, len(trades_a))
    d_a = m_a["sharpe"] - m_e0["sharpe"]
    avg_hold_a = float(np.mean([t["bars_held"] for t in trades_a])) if trades_a else 0.0
    trail_exits_a = sum(1 for t in trades_a if t["exit_reason"] == "trail_stop")

    rows.append({
        "design": "A", "params": "none", "sharpe": m_a["sharpe"],
        "cagr": m_a["cagr"], "mdd": m_a["mdd"], "trades": m_a["trades"],
        "avg_hold": avg_hold_a, "trail_exits": trail_exits_a,
        "n_trail_triggered": ts_a["n_trail_triggered"],
        "n_trail_suppressed": ts_a["n_trail_suppressed"],
        "d_sharpe": d_a, "d_cagr": m_a["cagr"] - m_e0["cagr"],
        "d_mdd": m_a["mdd"] - m_e0["mdd"], "g0_pass": d_a > 0,
    })
    print(f"\n  Design A: Sharpe={m_a['sharpe']:.4f}, d={d_a:+.4f}, trades={m_a['trades']}, "
          f"trail_supp={ts_a['n_trail_suppressed']}/{ts_a['n_trail_triggered']}, "
          f"G0={'PASS' if d_a > 0 else 'FAIL'}")

    # --- Design B: sweep tau grid ---
    best_b = {"sharpe": -999, "tau": None}
    b_rows = []
    for tau in TAU_GRID_B:
        mask_b = _mask_design_b(ef, es, tau)
        nav_b, trades_b, ts_b = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                         suppress_mask=mask_b)
        m_b = _metrics(nav_b, wi, len(trades_b))
        d_b = m_b["sharpe"] - m_e0["sharpe"]
        trail_exits_b = sum(1 for t in trades_b if t["exit_reason"] == "trail_stop")
        avg_hold_b = float(np.mean([t["bars_held"] for t in trades_b])) if trades_b else 0.0
        b_rows.append({
            "tau": tau, "sharpe": m_b["sharpe"], "d_sharpe": d_b,
            "trades": m_b["trades"], "cagr": m_b["cagr"], "mdd": m_b["mdd"],
            "trail_exits": trail_exits_b,
            "n_trail_suppressed": ts_b["n_trail_suppressed"],
            "n_trail_triggered": ts_b["n_trail_triggered"],
            "avg_hold": avg_hold_b,
        })
        if m_b["sharpe"] > best_b["sharpe"]:
            best_b = {"sharpe": m_b["sharpe"], "tau": tau, "d_sharpe": d_b,
                      "cagr": m_b["cagr"], "mdd": m_b["mdd"], "trades": m_b["trades"],
                      "avg_hold": avg_hold_b, "trail_exits": trail_exits_b,
                      "ts": ts_b}

    d_b_best = best_b["d_sharpe"]
    rows.append({
        "design": "B", "params": f"tau={best_b['tau']}", "sharpe": best_b["sharpe"],
        "cagr": best_b["cagr"], "mdd": best_b["mdd"], "trades": best_b["trades"],
        "avg_hold": best_b["avg_hold"], "trail_exits": best_b["trail_exits"],
        "n_trail_triggered": best_b["ts"]["n_trail_triggered"],
        "n_trail_suppressed": best_b["ts"]["n_trail_suppressed"],
        "d_sharpe": d_b_best, "d_cagr": best_b["cagr"] - m_e0["cagr"],
        "d_mdd": best_b["mdd"] - m_e0["mdd"], "g0_pass": d_b_best > 0,
    })
    print(f"  Design B: best tau={best_b['tau']}, Sharpe={best_b['sharpe']:.4f}, d={d_b_best:+.4f}, "
          f"trades={best_b['trades']}, G0={'PASS' if d_b_best > 0 else 'FAIL'}")

    # --- Design C: sweep tau_ema x tau_d1 grid ---
    best_c = {"sharpe": -999, "tau_ema": None, "tau_d1": None}
    c_rows = []
    for tau_ema in TAU_EMA_GRID_C:
        for tau_d1 in TAU_D1_GRID_C:
            mask_c = _mask_design_c(ef, es, d1_str_h4, tau_ema, tau_d1)
            nav_c, trades_c, ts_c = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                             suppress_mask=mask_c)
            m_c = _metrics(nav_c, wi, len(trades_c))
            d_c = m_c["sharpe"] - m_e0["sharpe"]
            trail_exits_c = sum(1 for t in trades_c if t["exit_reason"] == "trail_stop")
            avg_hold_c = float(np.mean([t["bars_held"] for t in trades_c])) if trades_c else 0.0
            c_rows.append({
                "tau_ema": tau_ema, "tau_d1": tau_d1,
                "sharpe": m_c["sharpe"], "d_sharpe": d_c,
                "trades": m_c["trades"], "cagr": m_c["cagr"], "mdd": m_c["mdd"],
            })
            if m_c["sharpe"] > best_c["sharpe"]:
                best_c = {"sharpe": m_c["sharpe"], "tau_ema": tau_ema, "tau_d1": tau_d1,
                          "d_sharpe": d_c, "cagr": m_c["cagr"], "mdd": m_c["mdd"],
                          "trades": m_c["trades"], "avg_hold": avg_hold_c,
                          "trail_exits": trail_exits_c, "ts": ts_c}

    d_c_best = best_c["d_sharpe"]
    rows.append({
        "design": "C", "params": f"tau_ema={best_c['tau_ema']},tau_d1={best_c['tau_d1']}",
        "sharpe": best_c["sharpe"], "cagr": best_c["cagr"], "mdd": best_c["mdd"],
        "trades": best_c["trades"], "avg_hold": best_c["avg_hold"],
        "trail_exits": best_c["trail_exits"],
        "n_trail_triggered": best_c["ts"]["n_trail_triggered"],
        "n_trail_suppressed": best_c["ts"]["n_trail_suppressed"],
        "d_sharpe": d_c_best, "d_cagr": best_c["cagr"] - m_e0["cagr"],
        "d_mdd": best_c["mdd"] - m_e0["mdd"], "g0_pass": d_c_best > 0,
    })
    print(f"  Design C: best tau_ema={best_c['tau_ema']}, tau_d1={best_c['tau_d1']}, "
          f"Sharpe={best_c['sharpe']:.4f}, d={d_c_best:+.4f}, "
          f"trades={best_c['trades']}, G0={'PASS' if d_c_best > 0 else 'FAIL'}")

    # --- Design D (full-sample = same as train on all data, test on all data) ---
    mask_d = _mask_design_d(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                            regime_h4, wi, len(cl))
    nav_d, trades_d, ts_d = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                     suppress_mask=mask_d)
    m_d = _metrics(nav_d, wi, len(trades_d))
    d_d = m_d["sharpe"] - m_e0["sharpe"]
    avg_hold_d = float(np.mean([t["bars_held"] for t in trades_d])) if trades_d else 0.0
    trail_exits_d = sum(1 for t in trades_d if t["exit_reason"] == "trail_stop")

    rows.append({
        "design": "D", "params": "logistic", "sharpe": m_d["sharpe"],
        "cagr": m_d["cagr"], "mdd": m_d["mdd"], "trades": m_d["trades"],
        "avg_hold": avg_hold_d, "trail_exits": trail_exits_d,
        "n_trail_triggered": ts_d["n_trail_triggered"],
        "n_trail_suppressed": ts_d["n_trail_suppressed"],
        "d_sharpe": d_d, "d_cagr": m_d["cagr"] - m_e0["cagr"],
        "d_mdd": m_d["mdd"] - m_e0["mdd"], "g0_pass": d_d > 0,
    })
    print(f"  Design D: Sharpe={m_d['sharpe']:.4f}, d={d_d:+.4f}, trades={m_d['trades']}, "
          f"G0={'PASS' if d_d > 0 else 'FAIL'}")

    # Summary
    passing = [r for r in rows if r["g0_pass"]]
    print(f"\n  T0 Summary: {len(passing)}/4 designs pass G0 screen")

    return {
        "e0_baseline": m_e0,
        "rows": rows,
        "design_b_sweep": b_rows,
        "design_c_sweep": c_rows,
        "best_b_tau": best_b["tau"],
        "best_c_tau_ema": best_c["tau_ema"],
        "best_c_tau_d1": best_c["tau_d1"],
    }


# =========================================================================
# T1: WALK-FORWARD VALIDATION
# =========================================================================

def run_t1_wfo(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct,
               t0_results):
    """T1: Walk-forward validation for designs passing T0."""
    print("\n" + "=" * 70)
    print("T1: WALK-FORWARD VALIDATION")
    print("=" * 70)

    # Determine which designs passed T0
    passing = [r["design"] for r in t0_results["rows"] if r["g0_pass"]]
    if not passing:
        print("  No designs passed T0 → skip T1")
        return {"results": {}, "passing": []}

    print(f"  Designs to validate: {passing}")

    # Precompute fold boundaries
    folds = []
    for train_end_str, test_start_str, test_end_str in WFO_FOLDS:
        train_end = _date_to_bar_idx(h4_ct, train_end_str)
        test_start = _date_to_bar_idx(h4_ct, test_start_str)
        test_end = _date_to_bar_idx(h4_ct, test_end_str)
        folds.append((train_end, test_start, test_end))
        print(f"  Fold: train=[{wi}..{train_end}], test=[{test_start}..{test_end}]")

    results = {}

    for design in passing:
        print(f"\n  --- Design {design} WFO ---")
        fold_results = []

        for fold_idx, (train_end, test_start, test_end) in enumerate(folds):
            # Run E0 on test window
            nav_e0, trades_e0, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi)
            test_trades_e0 = [t for t in trades_e0
                              if test_start <= t["entry_bar"] < test_end]
            m_e0_test = _metrics_window(nav_e0, test_start, test_end + 1,
                                        len(test_trades_e0))

            # Build filter mask
            if design == "A":
                mask = _mask_design_a(ef, es, vd, regime_h4)
                fold_param = "none"
            elif design == "B":
                # Train: sweep tau on [wi, train_end]
                best_tau = TAU_GRID_B[0]
                best_train_sharpe = -999
                for tau in TAU_GRID_B:
                    mask_b = _mask_design_b(ef, es, tau)
                    nav_b, _, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                           suppress_mask=mask_b)
                    m_train = _metrics_window(nav_b, wi, train_end + 1)
                    if m_train["sharpe"] > best_train_sharpe:
                        best_train_sharpe = m_train["sharpe"]
                        best_tau = tau
                mask = _mask_design_b(ef, es, best_tau)
                fold_param = f"tau={best_tau}"
            elif design == "C":
                best_tau_ema = TAU_EMA_GRID_C[0]
                best_tau_d1 = TAU_D1_GRID_C[0]
                best_train_sharpe = -999
                for tau_ema in TAU_EMA_GRID_C:
                    for tau_d1 in TAU_D1_GRID_C:
                        mask_c = _mask_design_c(ef, es, d1_str_h4, tau_ema, tau_d1)
                        nav_c, _, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                               suppress_mask=mask_c)
                        m_train = _metrics_window(nav_c, wi, train_end + 1)
                        if m_train["sharpe"] > best_train_sharpe:
                            best_train_sharpe = m_train["sharpe"]
                            best_tau_ema = tau_ema
                            best_tau_d1 = tau_d1
                mask = _mask_design_c(ef, es, d1_str_h4, best_tau_ema, best_tau_d1)
                fold_param = f"tau_ema={best_tau_ema},tau_d1={best_tau_d1}"
            elif design == "D":
                mask = _mask_design_d(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                                      regime_h4, wi, train_end + 1)
                fold_param = "logistic"
            else:
                continue

            # Run filtered sim on full data, extract test window metrics
            nav_f, trades_f, ts_f = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                             suppress_mask=mask)
            test_trades_f = [t for t in trades_f
                             if test_start <= t["entry_bar"] < test_end]
            m_f_test = _metrics_window(nav_f, test_start, test_end + 1,
                                       len(test_trades_f))

            d_sharpe = m_f_test["sharpe"] - m_e0_test["sharpe"]
            win = d_sharpe > 0

            fold_results.append({
                "fold": fold_idx + 1,
                "param": fold_param,
                "e0_sharpe_test": m_e0_test["sharpe"],
                "filter_sharpe_test": m_f_test["sharpe"],
                "d_sharpe": d_sharpe,
                "win": win,
                "e0_trades_test": len(test_trades_e0),
                "filter_trades_test": len(test_trades_f),
            })

            print(f"    Fold {fold_idx+1}: param={fold_param}, "
                  f"E0={m_e0_test['sharpe']:.4f}, Filt={m_f_test['sharpe']:.4f}, "
                  f"d={d_sharpe:+.4f} {'WIN' if win else 'LOSE'}")

        win_rate = sum(1 for f in fold_results if f["win"]) / len(fold_results)
        mean_d = float(np.mean([f["d_sharpe"] for f in fold_results]))
        g1_pass = win_rate >= 0.75 and mean_d > 0

        results[design] = {
            "folds": fold_results,
            "win_rate": win_rate,
            "mean_d_sharpe": mean_d,
            "g1_pass": g1_pass,
        }

        print(f"    Design {design}: win_rate={win_rate:.0%}, mean_d={mean_d:+.4f}, "
              f"G1={'PASS' if g1_pass else 'FAIL'}")

    t1_passing = [d for d, r in results.items() if r["g1_pass"]]
    print(f"\n  T1 Summary: passing designs = {t1_passing}")

    return {"results": results, "passing": t1_passing}


# =========================================================================
# T2: BOOTSTRAP VALIDATION
# =========================================================================

def run_t2_bootstrap(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4,
                     d1_str_h4, wi, h4_ct, design, params,
                     t0_results):
    """T2: 500 VCBB bootstrap paths for the winning design."""
    print("\n" + "=" * 70)
    print(f"T2: BOOTSTRAP VALIDATION (design={design}, {N_BOOT} paths)")
    print("=" * 70)

    # Prepare bootstrap inputs
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

    # Shared D1 data (same for all paths — bootstrap only resamples H4)
    regime_pw = regime_h4[wi:]
    d1_str_pw = d1_str_h4[wi:]

    d_sharpes = []
    d_cagrs = []
    d_mdds = []

    for b_idx in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)

        n_b = len(bcl)
        breg = regime_pw[:n_b] if len(regime_pw) >= n_b else np.ones(n_b, dtype=np.bool_)
        bd1_str = d1_str_pw[:n_b] if len(d1_str_pw) >= n_b else np.zeros(n_b)

        bwi = 0
        bef, bes, bvd, bat = _compute_indicators(bcl, bhi, blo, bvo, btb)

        # E0 baseline
        bnav_e0, btrades_e0, _ = _run_sim(bcl, bef, bes, bvd, bat, breg, bwi)
        bm_e0 = _metrics(bnav_e0, bwi, len(btrades_e0))

        # Build filter mask for bootstrap path
        if design == "A":
            bmask = _mask_design_a(bef, bes, bvd, breg)
        elif design == "B":
            tau = params.get("tau", t0_results["best_b_tau"])
            bmask = _mask_design_b(bef, bes, tau)
        elif design == "C":
            tau_ema = params.get("tau_ema", t0_results["best_c_tau_ema"])
            tau_d1 = params.get("tau_d1", t0_results["best_c_tau_d1"])
            bmask = _mask_design_c(bef, bes, bd1_str, tau_ema, tau_d1)
        else:
            # Design D: train on first 60% of bootstrap path
            train_end_b = int(n_b * 0.6)
            bmask = _mask_design_d(bcl, bhi, blo, bef, bes, bvd, bat, bd1_str,
                                   breg, bwi, train_end_b)

        # Filtered sim
        bnav_f, btrades_f, _ = _run_sim(bcl, bef, bes, bvd, bat, breg, bwi,
                                        suppress_mask=bmask)
        bm_f = _metrics(bnav_f, bwi, len(btrades_f))

        d_sharpes.append(bm_f["sharpe"] - bm_e0["sharpe"])
        d_cagrs.append(bm_f["cagr"] - bm_e0["cagr"])
        d_mdds.append(bm_f["mdd"] - bm_e0["mdd"])

        if (b_idx + 1) % 100 == 0:
            print(f"    ... {b_idx + 1}/{N_BOOT} paths done")

    d_sharpes = np.array(d_sharpes)
    d_cagrs = np.array(d_cagrs)
    d_mdds = np.array(d_mdds)

    p_dsharpe_gt0 = float(np.mean(d_sharpes > 0))
    p_dmdd_lt0 = float(np.mean(d_mdds < 0))
    med_d_sharpe = float(np.median(d_sharpes))
    med_d_mdd = float(np.median(d_mdds))

    g2_pass = p_dsharpe_gt0 > 0.60
    g3_pass = med_d_mdd <= 5.0

    results = {
        "design": design,
        "d_sharpe_median": med_d_sharpe,
        "d_sharpe_p5": float(np.percentile(d_sharpes, 5)),
        "d_sharpe_p95": float(np.percentile(d_sharpes, 95)),
        "d_sharpe_mean": float(np.mean(d_sharpes)),
        "p_d_sharpe_gt0": p_dsharpe_gt0,
        "d_cagr_median": float(np.median(d_cagrs)),
        "d_cagr_p5": float(np.percentile(d_cagrs, 5)),
        "d_cagr_p95": float(np.percentile(d_cagrs, 95)),
        "d_mdd_median": med_d_mdd,
        "d_mdd_p5": float(np.percentile(d_mdds, 5)),
        "d_mdd_p95": float(np.percentile(d_mdds, 95)),
        "p_d_mdd_lt0": p_dmdd_lt0,
        "g2_pass": g2_pass,
        "g3_pass": g3_pass,
    }

    print(f"\n  d_sharpe: median={med_d_sharpe:+.4f}, "
          f"[{results['d_sharpe_p5']:+.4f}, {results['d_sharpe_p95']:+.4f}]")
    print(f"  P(d_sharpe > 0): {p_dsharpe_gt0:.1%}")
    print(f"  d_mdd: median={med_d_mdd:+.2f}pp, "
          f"[{results['d_mdd_p5']:+.2f}, {results['d_mdd_p95']:+.2f}]")
    print(f"  P(d_mdd < 0): {p_dmdd_lt0:.1%}")
    print(f"  G2 (P(d_sharpe>0) > 60%): {'PASS' if g2_pass else 'FAIL'}")
    print(f"  G3 (median d_mdd <= +5pp): {'PASS' if g3_pass else 'FAIL'}")

    return results, d_sharpes, d_cagrs, d_mdds


# =========================================================================
# T3: JACKKNIFE LEAVE-YEAR-OUT
# =========================================================================

def run_t3_jackknife(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                     wi, h4_ct, design, params, t0_results):
    """T3: Leave-year-out jackknife (6 folds)."""
    print("\n" + "=" * 70)
    print(f"T3: JACKKNIFE LEAVE-YEAR-OUT (design={design})")
    print("=" * 70)

    import datetime
    n = len(cl)

    # Get year boundaries
    year_ranges = []
    for yr in JK_YEARS:
        start_str = f"{yr}-01-01"
        end_str = f"{yr}-12-31"
        s_idx = _date_to_bar_idx(h4_ct, start_str)
        e_idx = _date_to_bar_idx(h4_ct, end_str)
        year_ranges.append((yr, s_idx, min(e_idx, n - 1)))

    fold_results = []

    for yr, yr_start, yr_end in year_ranges:
        # Build mask to EXCLUDE this year's bars
        include = np.ones(n, dtype=np.bool_)
        include[yr_start:yr_end + 1] = False

        # For jackknife, we run on all data but skip the excluded year's bars
        # Simpler approach: build a condensed price array excluding the year
        idx_keep = np.where(include)[0]
        cl_jk = cl[idx_keep]
        hi_jk = hi[idx_keep] if hi is not None else None
        lo_jk = lo[idx_keep] if lo is not None else None

        # Recompute indicators on reduced data
        # Need vol arrays too
        # Actually, let's just use the approach of running the full sim
        # but with a "skip year" mask. The simplest correct approach is
        # to re-run on the concatenated data without the excluded year.
        # But that changes bar indices. Instead, mask the excluded year
        # with NaN for close (sim will not trade during NaN periods).
        cl_jk = cl.copy()
        cl_jk[yr_start:yr_end + 1] = np.nan

        # This doesn't work cleanly with our sim. Alternative: run full sim
        # with suppress_mask that also forces exits during excluded year.
        # Actually simplest: just compute metrics excluding the dropped year.
        # Run sim normally, then compute metrics on bars OUTSIDE the dropped year.

        # E0 baseline: run full sim, compute metrics excluding dropped year
        nav_e0, trades_e0, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi)
        # Filter to trades NOT in the dropped year
        trades_e0_jk = [t for t in trades_e0
                        if not (yr_start <= t["entry_bar"] <= yr_end)]
        # Metrics on remaining bars
        # Use nav values at kept indices
        kept_indices = np.concatenate([
            np.arange(wi, yr_start),
            np.arange(yr_end + 1, n)
        ]) if yr_start > wi else np.arange(yr_end + 1, n)
        if len(kept_indices) < 2:
            fold_results.append({"year": yr, "d_sharpe": 0.0, "e0_sharpe": 0.0,
                                 "filter_sharpe": 0.0, "d_sharpe_negative": False})
            continue
        nav_e0_kept = nav_e0[kept_indices]
        m_e0_jk = _metrics(nav_e0_kept, 0, len(trades_e0_jk))

        # Build filter mask
        if design == "A":
            mask = _mask_design_a(ef, es, vd, regime_h4)
        elif design == "B":
            tau = params.get("tau", t0_results["best_b_tau"])
            mask = _mask_design_b(ef, es, tau)
        elif design == "C":
            tau_ema = params.get("tau_ema", t0_results["best_c_tau_ema"])
            tau_d1 = params.get("tau_d1", t0_results["best_c_tau_d1"])
            mask = _mask_design_c(ef, es, d1_str_h4, tau_ema, tau_d1)
        elif design == "D":
            # Train on all data excluding this year
            mask = _mask_design_d(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                                  regime_h4, wi, n)
        else:
            continue

        # Filtered sim
        nav_f, trades_f, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                      suppress_mask=mask)
        trades_f_jk = [t for t in trades_f
                       if not (yr_start <= t["entry_bar"] <= yr_end)]
        nav_f_kept = nav_f[kept_indices]
        m_f_jk = _metrics(nav_f_kept, 0, len(trades_f_jk))

        d_sharpe = m_f_jk["sharpe"] - m_e0_jk["sharpe"]

        fold_results.append({
            "year": yr,
            "e0_sharpe": m_e0_jk["sharpe"],
            "filter_sharpe": m_f_jk["sharpe"],
            "d_sharpe": d_sharpe,
            "d_sharpe_negative": d_sharpe < 0,
        })

        print(f"    Drop {yr}: E0={m_e0_jk['sharpe']:.4f}, Filt={m_f_jk['sharpe']:.4f}, "
              f"d={d_sharpe:+.4f}")

    n_negative = sum(1 for f in fold_results if f["d_sharpe_negative"])
    mean_d = float(np.mean([f["d_sharpe"] for f in fold_results]))
    se_d = float(np.std([f["d_sharpe"] for f in fold_results], ddof=1) /
                 math.sqrt(len(fold_results))) if len(fold_results) > 1 else 0.0

    g4_pass = n_negative <= 2

    results = {
        "design": design,
        "folds": fold_results,
        "n_negative": n_negative,
        "mean_d_sharpe": mean_d,
        "se_d_sharpe": se_d,
        "g4_pass": g4_pass,
    }

    print(f"\n  Negative folds: {n_negative}/6")
    print(f"  Mean d_sharpe: {mean_d:+.4f} ± {se_d:.4f}")
    print(f"  G4 (≤ 2 negative): {'PASS' if g4_pass else 'FAIL'}")

    return results


# =========================================================================
# T4: DOF CORRECTION / PSR
# =========================================================================

def run_t4_psr(cl, hi, lo, ef, es, vd, at, regime_h4, wi, design, params,
               d1_str_h4, t0_results):
    """T4: PSR with DOF correction."""
    print("\n" + "=" * 70)
    print(f"T4: DOF CORRECTION / PSR (design={design})")
    print("=" * 70)

    # E0 baseline
    nav_e0, trades_e0, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))
    navs_e0 = nav_e0[wi:]
    n_returns = len(navs_e0) - 1

    # DOF penalty per design
    dof_penalty = {"A": 0, "B": 1, "C": 2, "D": 10}
    extra_dof = dof_penalty.get(design, 0)
    effective_dof = E0_EFFECTIVE_DOF + extra_dof

    # Compute E0 PSR
    psr_e0 = _psr(m_e0["sharpe"], n_returns)

    # Build filter mask
    if design == "A":
        mask = _mask_design_a(ef, es, vd, regime_h4)
    elif design == "B":
        tau = params.get("tau", t0_results["best_b_tau"])
        mask = _mask_design_b(ef, es, tau)
    elif design == "C":
        tau_ema = params.get("tau_ema", t0_results["best_c_tau_ema"])
        tau_d1 = params.get("tau_d1", t0_results["best_c_tau_d1"])
        mask = _mask_design_c(ef, es, d1_str_h4, tau_ema, tau_d1)
    elif design == "D":
        mask = _mask_design_d(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                              regime_h4, wi, len(cl))
    else:
        return {}

    nav_f, trades_f, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                  suppress_mask=mask)
    m_f = _metrics(nav_f, wi, len(trades_f))

    # PSR with DOF correction: reduce effective sample size
    # Nyholt correction: n_eff = n / M_eff
    n_eff = max(3, int(n_returns / (effective_dof / E0_EFFECTIVE_DOF)))
    psr_f = _psr(m_f["sharpe"], n_eff)

    g5_pass = psr_f > 0.95

    results = {
        "design": design,
        "e0_sharpe": m_e0["sharpe"],
        "filter_sharpe": m_f["sharpe"],
        "e0_psr": psr_e0,
        "filter_psr": psr_f,
        "effective_dof": effective_dof,
        "extra_dof": extra_dof,
        "n_returns": n_returns,
        "n_eff": n_eff,
        "g5_pass": g5_pass,
    }

    print(f"  E0: Sharpe={m_e0['sharpe']:.4f}, PSR={psr_e0:.4f}")
    print(f"  Filter: Sharpe={m_f['sharpe']:.4f}, PSR(DOF-corrected)={psr_f:.4f}")
    print(f"  DOF: base={E0_EFFECTIVE_DOF:.2f} + {extra_dof} = {effective_dof:.2f}")
    print(f"  n_returns={n_returns}, n_eff={n_eff}")
    print(f"  G5 (PSR > 0.95): {'PASS' if g5_pass else 'FAIL'}")

    return results


# =========================================================================
# T5: COMPREHENSIVE COMPARISON
# =========================================================================

def run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                      wi, h4_ct, design, params, t0_results,
                      t1_results, t2_results, t4_results):
    """T5: Side-by-side comparison table."""
    print("\n" + "=" * 70)
    print("T5: COMPREHENSIVE COMPARISON")
    print("=" * 70)

    # E0
    nav_e0, trades_e0, ts_e0 = _run_sim(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))
    avg_hold_e0 = float(np.mean([t["bars_held"] for t in trades_e0])) if trades_e0 else 0.0
    trail_exits_e0 = sum(1 for t in trades_e0 if t["exit_reason"] == "trail_stop")

    # E5 (robust ATR)
    rat = _robust_atr(hi, lo, cl)
    nav_e5, trades_e5, ts_e5 = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                        atr_arr=rat)
    m_e5 = _metrics(nav_e5, wi, len(trades_e5))
    avg_hold_e5 = float(np.mean([t["bars_held"] for t in trades_e5])) if trades_e5 else 0.0
    trail_exits_e5 = sum(1 for t in trades_e5 if t["exit_reason"] == "trail_stop")

    # Oracle
    nav_or, trades_or, ts_or = _run_sim_oracle(cl, ef, es, vd, at, regime_h4, wi)
    m_or = _metrics(nav_or, wi, len(trades_or))
    avg_hold_or = float(np.mean([t["bars_held"] for t in trades_or])) if trades_or else 0.0
    trail_exits_or = sum(1 for t in trades_or if t["exit_reason"] == "trail_stop")

    # Filtered
    if design == "A":
        mask = _mask_design_a(ef, es, vd, regime_h4)
    elif design == "B":
        tau = params.get("tau", t0_results["best_b_tau"])
        mask = _mask_design_b(ef, es, tau)
    elif design == "C":
        tau_ema = params.get("tau_ema", t0_results["best_c_tau_ema"])
        tau_d1 = params.get("tau_d1", t0_results["best_c_tau_d1"])
        mask = _mask_design_c(ef, es, d1_str_h4, tau_ema, tau_d1)
    elif design == "D":
        mask = _mask_design_d(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                              regime_h4, wi, len(cl))
    else:
        mask = np.zeros(len(cl), dtype=np.bool_)

    nav_f, trades_f, ts_f = _run_sim(cl, ef, es, vd, at, regime_h4, wi,
                                     suppress_mask=mask)
    m_f = _metrics(nav_f, wi, len(trades_f))
    avg_hold_f = float(np.mean([t["bars_held"] for t in trades_f])) if trades_f else 0.0
    trail_exits_f = sum(1 for t in trades_f if t["exit_reason"] == "trail_stop")

    # WFO win rate
    wfo_wr = t1_results["results"].get(design, {}).get("win_rate", None) if t1_results else None
    # Bootstrap
    boot_p = t2_results.get("p_d_sharpe_gt0", None) if t2_results else None
    # PSR
    psr_f = t4_results.get("filter_psr", None) if t4_results else None
    psr_e0 = t4_results.get("e0_psr", None) if t4_results else None

    table = [
        {"strategy": "E0", "sharpe": m_e0["sharpe"], "cagr": m_e0["cagr"],
         "mdd": m_e0["mdd"], "trades": m_e0["trades"],
         "avg_hold": avg_hold_e0, "trail_exits": trail_exits_e0,
         "n_trail_suppressed": 0,
         "wfo_win_rate": "", "boot_p_sharpe": "", "psr": f"{psr_e0:.4f}" if psr_e0 else ""},
        {"strategy": f"E0+Filter({design})", "sharpe": m_f["sharpe"], "cagr": m_f["cagr"],
         "mdd": m_f["mdd"], "trades": m_f["trades"],
         "avg_hold": avg_hold_f, "trail_exits": trail_exits_f,
         "n_trail_suppressed": ts_f["n_trail_suppressed"],
         "wfo_win_rate": f"{wfo_wr:.0%}" if wfo_wr is not None else "",
         "boot_p_sharpe": f"{boot_p:.1%}" if boot_p is not None else "",
         "psr": f"{psr_f:.4f}" if psr_f else ""},
        {"strategy": "E5", "sharpe": m_e5["sharpe"], "cagr": m_e5["cagr"],
         "mdd": m_e5["mdd"], "trades": m_e5["trades"],
         "avg_hold": avg_hold_e5, "trail_exits": trail_exits_e5,
         "n_trail_suppressed": 0,
         "wfo_win_rate": "", "boot_p_sharpe": "", "psr": ""},
        {"strategy": "Oracle", "sharpe": m_or["sharpe"], "cagr": m_or["cagr"],
         "mdd": m_or["mdd"], "trades": m_or["trades"],
         "avg_hold": avg_hold_or, "trail_exits": trail_exits_or,
         "n_trail_suppressed": ts_or["n_trail_suppressed"],
         "wfo_win_rate": "", "boot_p_sharpe": "", "psr": ""},
    ]

    print(f"\n  {'Strategy':20s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Trades':>7s} "
          f"{'AvgHold':>8s} {'TrailEx':>8s} {'Supp':>6s} {'WFO':>6s} {'Boot':>6s} {'PSR':>7s}")
    print("  " + "-" * 105)
    for row in table:
        print(f"  {row['strategy']:20s} {row['sharpe']:8.4f} {row['cagr']:8.2f} {row['mdd']:8.2f} "
              f"{row['trades']:7d} {row['avg_hold']:8.1f} {row['trail_exits']:8d} "
              f"{row['n_trail_suppressed']:6d} {str(row['wfo_win_rate']):>6s} "
              f"{str(row['boot_p_sharpe']):>6s} {str(row['psr']):>7s}")

    return table


# =========================================================================
# SAVE RESULTS
# =========================================================================

def save_results(t0, t1, t2, t2_arrays, t3, t4, t5, verdict_info):
    """Save all results to JSON + CSV files."""

    # Master JSON
    out = {
        "verdict": verdict_info,
        "t0_screening": {k: v for k, v in t0.items() if k not in ("design_b_sweep", "design_c_sweep")},
        "t1_wfo": t1 if t1 else {},
        "t2_bootstrap": t2 if t2 else {},
        "t3_jackknife": t3 if t3 else {},
        "t4_psr": t4 if t4 else {},
    }
    with open(OUTDIR / "x14_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    # T0: screening CSV
    if t0.get("rows"):
        with open(OUTDIR / "x14_screening.csv", "w", newline="") as f:
            fields = ["design", "params", "sharpe", "cagr", "mdd", "trades",
                      "avg_hold", "trail_exits", "n_trail_triggered",
                      "n_trail_suppressed", "d_sharpe", "d_cagr", "d_mdd", "g0_pass"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in t0["rows"]:
                out_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        out_row[k] = f"{v:.6f}"
                    elif isinstance(v, bool):
                        out_row[k] = "True" if v else "False"
                    else:
                        out_row[k] = v
                w.writerow(out_row)

    # T1: WFO CSV
    if t1 and t1.get("results"):
        with open(OUTDIR / "x14_wfo_results.csv", "w", newline="") as f:
            fields = ["design", "fold", "param", "e0_sharpe_test",
                      "filter_sharpe_test", "d_sharpe", "win",
                      "e0_trades_test", "filter_trades_test"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for design_key, dr in t1["results"].items():
                for fold_r in dr["folds"]:
                    row = {"design": design_key}
                    for k, v in fold_r.items():
                        if isinstance(v, float):
                            row[k] = f"{v:.6f}"
                        elif isinstance(v, bool):
                            row[k] = "True" if v else "False"
                        else:
                            row[k] = v
                    w.writerow(row)

    # T2: bootstrap CSV
    if t2_arrays is not None:
        d_sharpes, d_cagrs, d_mdds = t2_arrays
        with open(OUTDIR / "x14_bootstrap.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "d_sharpe", "d_cagr", "d_mdd"])
            for i in range(len(d_sharpes)):
                w.writerow([i, f"{d_sharpes[i]:.6f}", f"{d_cagrs[i]:.6f}",
                            f"{d_mdds[i]:.6f}"])

    # T3: jackknife CSV
    if t3 and t3.get("folds"):
        with open(OUTDIR / "x14_jackknife.csv", "w", newline="") as f:
            fields = ["year", "e0_sharpe", "filter_sharpe", "d_sharpe",
                      "d_sharpe_negative"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for fold_r in t3["folds"]:
                row = {}
                for k, v in fold_r.items():
                    if isinstance(v, float):
                        row[k] = f"{v:.6f}"
                    elif isinstance(v, bool):
                        row[k] = "True" if v else "False"
                    else:
                        row[k] = v
                w.writerow(row)

    # T5: comparison CSV
    if t5:
        with open(OUTDIR / "x14_comparison.csv", "w", newline="") as f:
            fields = ["strategy", "sharpe", "cagr", "mdd", "trades",
                      "avg_hold", "trail_exits", "n_trail_suppressed",
                      "wfo_win_rate", "boot_p_sharpe", "psr"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in t5:
                out_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        out_row[k] = f"{v:.6f}"
                    else:
                        out_row[k] = v
                w.writerow(out_row)

    print(f"\n  Saved to {OUTDIR}/x14_*.{{json,csv}}")


# =========================================================================
# FIXED-SEQUENCE TESTING + VERDICT
# =========================================================================

def run_sequential_testing(cl, hi, lo, vo, tb, ef, es, vd, at,
                           regime_h4, d1_str_h4, wi, h4_ct, t0_results):
    """Fixed-sequence testing: A→B→C→D. First to pass all gates wins."""
    print("\n" + "=" * 70)
    print("FIXED-SEQUENCE TESTING")
    print("=" * 70)

    # Order: A, B, C, D (simplest first)
    design_order = ["A", "B", "C", "D"]
    t0_map = {r["design"]: r for r in t0_results["rows"]}

    # T1: WFO for all passing designs
    t1_results = run_t1_wfo(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                            wi, h4_ct, t0_results)

    # Track best design through sequential gates
    winner = None
    winner_t2 = None
    winner_t2_arrays = None
    winner_t3 = None
    winner_t4 = None
    winner_t5 = None
    gate_failures = {}

    for design in design_order:
        t0_row = t0_map.get(design)
        if not t0_row:
            continue

        print(f"\n  ========== Testing Design {design} ==========")

        # G0: T0 screen
        if not t0_row["g0_pass"]:
            gate_failures[design] = "G0"
            print(f"  Design {design}: FAIL G0 (d_sharpe={t0_row['d_sharpe']:+.4f})")
            continue

        # G1: T1 WFO
        t1_design = t1_results["results"].get(design)
        if not t1_design or not t1_design["g1_pass"]:
            gate_failures[design] = "G1"
            wr = t1_design["win_rate"] if t1_design else 0
            print(f"  Design {design}: FAIL G1 (win_rate={wr:.0%})")
            continue

        # Determine params for T2/T3/T4
        params = {}
        if design == "B":
            # WFO consensus: most common tau across folds
            fold_taus = [f["param"].replace("tau=", "")
                         for f in t1_design["folds"]]
            from collections import Counter
            tau_counts = Counter(fold_taus)
            consensus_tau = float(tau_counts.most_common(1)[0][0])
            params["tau"] = consensus_tau
            print(f"  Design B: WFO consensus tau={consensus_tau}")
        elif design == "C":
            fold_params = [f["param"] for f in t1_design["folds"]]
            from collections import Counter
            param_counts = Counter(tuple(f["param"] for f in t1_design["folds"]))
            best_param = param_counts.most_common(1)[0][0]
            # Parse "tau_ema=X,tau_d1=Y"
            parts = best_param.split(",")
            params["tau_ema"] = float(parts[0].split("=")[1])
            params["tau_d1"] = float(parts[1].split("=")[1])
            print(f"  Design C: WFO consensus tau_ema={params['tau_ema']}, tau_d1={params['tau_d1']}")

        # G2+G3: T2 Bootstrap
        t2, d_sharpes, d_cagrs, d_mdds = run_t2_bootstrap(
            cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4,
            wi, h4_ct, design, params, t0_results)

        if not t2["g2_pass"]:
            gate_failures[design] = "G2"
            print(f"  Design {design}: FAIL G2 (P(d_sharpe>0)={t2['p_d_sharpe_gt0']:.1%})")
            continue

        if not t2["g3_pass"]:
            gate_failures[design] = "G3"
            print(f"  Design {design}: FAIL G3 (median d_mdd={t2['d_mdd_median']:+.2f}pp)")
            continue

        # G4: T3 Jackknife
        t3 = run_t3_jackknife(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                              wi, h4_ct, design, params, t0_results)
        if not t3["g4_pass"]:
            gate_failures[design] = "G4"
            print(f"  Design {design}: FAIL G4 ({t3['n_negative']}/6 negative)")
            continue

        # G5: T4 PSR
        t4 = run_t4_psr(cl, hi, lo, ef, es, vd, at, regime_h4, wi, design, params,
                        d1_str_h4, t0_results)
        if not t4["g5_pass"]:
            gate_failures[design] = "G5"
            print(f"  Design {design}: FAIL G5 (PSR={t4['filter_psr']:.4f})")
            continue

        # ALL GATES PASSED
        print(f"\n  *** Design {design} PASSES ALL GATES ***")
        winner = design
        winner_t2 = t2
        winner_t2_arrays = (d_sharpes, d_cagrs, d_mdds)
        winner_t3 = t3
        winner_t4 = t4
        break  # Fixed-sequence: stop at first pass

    # T5 comparison for winner (or best failing design)
    if winner:
        winner_t5 = run_t5_comparison(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
            wi, h4_ct, winner, params, t0_results, t1_results,
            winner_t2, winner_t4)
    else:
        # No winner — run T5 for the design that got furthest
        furthest_design = None
        furthest_gate = -1
        gate_order = {"G0": 0, "G1": 1, "G2": 2, "G3": 3, "G4": 4, "G5": 5}
        for d in design_order:
            g = gate_failures.get(d, "none")
            if g == "none":
                continue
            gate_num = gate_order.get(g, -1)
            if gate_num > furthest_gate:
                furthest_gate = gate_num
                furthest_design = d

        if furthest_design:
            # Run T5 for the furthest design
            fp = {}
            if furthest_design == "B":
                fp["tau"] = t0_results["best_b_tau"]
            elif furthest_design == "C":
                fp["tau_ema"] = t0_results["best_c_tau_ema"]
                fp["tau_d1"] = t0_results["best_c_tau_d1"]

            winner_t5 = run_t5_comparison(
                cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                wi, h4_ct, furthest_design, fp, t0_results, t1_results,
                winner_t2, winner_t4)

    return {
        "winner": winner,
        "gate_failures": gate_failures,
        "t1": t1_results,
        "t2": winner_t2,
        "t2_arrays": winner_t2_arrays,
        "t3": winner_t3,
        "t4": winner_t4,
        "t5": winner_t5,
    }


# =========================================================================
# VERDICT
# =========================================================================

def compute_verdict(winner, gate_failures, t0_results):
    """Determine verdict from sequential testing results."""
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    if winner:
        verdict = f"PROMOTE_{winner}"
        print(f"  Design {winner} passes all 6 gates (G0-G5)")
        print(f"  VERDICT: {verdict}")
        return {"verdict": verdict, "winning_design": winner,
                "gate_failures": gate_failures}

    # All failed — determine verdict from failure pattern
    designs = ["A", "B", "C", "D"]
    failures = {d: gate_failures.get(d, "not_tested") for d in designs}

    # Check if all fail G0
    if all(failures[d] == "G0" for d in designs if failures[d] != "not_tested"):
        verdict = "CEILING_UNREACHABLE"
    # Check if all pass G0 but fail G1
    elif all(failures[d] in ("G1", "not_tested") for d in designs
             if failures[d] not in ("G0", "not_tested")):
        verdict = "NOT_TEMPORAL"
    # Check G2
    elif all(failures[d] in ("G2", "not_tested") for d in designs
             if failures[d] not in ("G0", "G1", "not_tested")):
        verdict = "NOT_ROBUST"
    # Check G3
    elif any(failures[d] == "G3" for d in designs):
        verdict = "MDD_TRADEOFF"
    # Check G4
    elif any(failures[d] == "G4" for d in designs):
        verdict = "JACKKNIFE_UNSTABLE"
    # Check G5
    elif any(failures[d] == "G5" for d in designs):
        verdict = "DOF_KILLED"
    else:
        verdict = "ALL_FAIL"

    print(f"  Gate failures: {failures}")
    print(f"  VERDICT: {verdict}")

    return {"verdict": verdict, "winning_design": None,
            "gate_failures": gate_failures}


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()

    print("X14: Trail-Stop Churn Filter — Design & Validation")
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
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    print(f"  Bars: {len(cl)} H4, {len(d1_cl)} D1, warmup_idx={wi}")
    print(f"  Period: {START} to {END}, warmup={WARMUP}d")

    # Precompute indicators
    ef, es, vd, at = _compute_indicators(cl, hi, lo, vo, tb)

    # T0: Full-sample screening
    t0 = run_t0_screening(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                          wi, h4_ct)

    # Sequential testing: T1→T2→T3→T4→T5 with fixed-sequence FWER
    seq = run_sequential_testing(cl, hi, lo, vo, tb, ef, es, vd, at,
                                regime_h4, d1_str_h4, wi, h4_ct, t0)

    # Verdict
    verdict_info = compute_verdict(seq["winner"], seq["gate_failures"], t0)

    # Save all results
    save_results(t0, seq["t1"], seq["t2"], seq["t2_arrays"],
                 seq["t3"], seq["t4"], seq["t5"], verdict_info)

    elapsed = time.time() - t_start
    print(f"\nX14 BENCHMARK COMPLETE — {elapsed:.0f}s — VERDICT: {verdict_info['verdict']}")


if __name__ == "__main__":
    main()
