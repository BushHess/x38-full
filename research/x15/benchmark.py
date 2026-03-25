#!/usr/bin/env python3
"""X15 Research — Churn Filter Integration: Design D Production Pipeline

Fixes X14's feature engineering mismatch (3 features zeroed at inference)
and validates the dynamic filter for production use.

Tests:
  T0: Feature fix validation (X14 static vs X15 dynamic)
  T1: Feature ablation (10, 7, top-4, top-1)
  T2: WFO validation (4 expanding folds, dynamic filter)
  T3: Bootstrap validation (500 VCBB paths)
  T4: Regime monitor interaction (factorial)
  T5: Retraining sensitivity (4 windows, coefficient stability)
  T6: Comprehensive comparison table
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
# CONSTANTS (identical to X14)
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

# E5 robust ATR
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0
CHURN_WINDOW = 20

C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]

# WFO folds
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

# Regime monitor thresholds (from prod_readiness)
MONITOR_RED_6M = 0.55
MONITOR_RED_12M = 0.70
MONITOR_6M_BARS = 6 * 30 * 6   # ~1080 H4 bars
MONITOR_12M_BARS = 12 * 30 * 6  # ~2160 H4 bars

FEATURE_NAMES = [
    "ema_ratio", "bars_held", "atr_pctl", "bar_range_atr",
    "dd_from_peak", "bars_since_peak", "close_position",
    "vdo_at_exit", "d1_regime_str", "trail_tightness",
]

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# INDICATORS (identical to X14)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high, low, close, period=ATR_P):
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
    import datetime
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ts_ms = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    idx = np.searchsorted(h4_ct, ts_ms, side='left')
    return min(idx, len(h4_ct) - 1)


# =========================================================================
# LOGISTIC MODEL UTILITIES
# =========================================================================

def _fit_logistic_l2(X, y, C=1.0, max_iter=100):
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
    n = X.shape[0]
    idx = np.arange(n) if rng is None else rng.permutation(n)
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
    pos = preds[y == 1]
    neg = preds[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    comp = pos[:, None] > neg[None, :]
    ties = pos[:, None] == neg[None, :]
    return float((np.sum(comp) + 0.5 * np.sum(ties)) / (len(pos) * len(neg)))


def _standardize(X):
    mu = np.mean(X, axis=0)
    std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


def _select_c(X, y, c_values=C_VALUES):
    Xs, mu, std = _standardize(X)
    best_c, best_auc = 1.0, 0.0
    for c in c_values:
        auc = _kfold_auc(Xs, y, C=c, k=5)
        if auc > best_auc:
            best_auc = auc
            best_c = c
    return best_c


# =========================================================================
# FEATURE COMPUTATION AT TRAIL-STOP TIME
# =========================================================================

def _compute_features_at_bar(i, entry_bar, peak_px, peak_bar,
                             cl, hi, lo, at, ef, es, vd,
                             d1_str_h4, trail_mult=TRAIL,
                             feature_mask=None):
    """Compute all 10 features at bar i with full trade context.

    feature_mask: optional boolean array (10,). If provided, zero out
    features where mask is False. Used for ablation studies.
    """
    # F1: ema_ratio
    f1 = ef[i] / es[i] if abs(es[i]) > 1e-12 else 1.0

    # F2: bars_held (NOW AVAILABLE — we know entry_bar)
    f2 = float(i - entry_bar)

    # F3: atr_pctl
    atr_start = max(0, i - 99)
    atr_window = at[atr_start:i + 1]
    valid_atr = atr_window[~np.isnan(atr_window)]
    f3 = float(np.sum(valid_atr <= at[i])) / len(valid_atr) if len(valid_atr) > 1 else 0.5

    # F4: bar_range_atr
    f4 = (hi[i] - lo[i]) / at[i] if at[i] > 1e-12 else 1.0

    # F5: dd_from_peak (NOW AVAILABLE — we track peak_px)
    f5 = (peak_px - cl[i]) / peak_px if peak_px > 1e-12 else 0.0

    # F6: bars_since_peak (NOW AVAILABLE — we track peak_bar)
    f6 = float(i - peak_bar)

    # F7: close_position
    bar_w = hi[i] - lo[i]
    f7 = (cl[i] - lo[i]) / bar_w if bar_w > 1e-12 else 0.5

    # F8: vdo_at_exit
    f8 = float(vd[i])

    # F9: d1_regime_str
    f9 = float(d1_str_h4[i])

    # F10: trail_tightness
    f10 = trail_mult * at[i] / cl[i] if cl[i] > 1e-12 else 0.0

    feat = np.array([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10])

    if feature_mask is not None:
        feat = feat * feature_mask

    return feat


# =========================================================================
# SIM CORE — E0+EMA1D21 with DYNAMIC logistic filter
# =========================================================================

def _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH, atr_arr=None):
    """Plain E0+EMA1D21 sim (no filter). Returns (nav, trades, trail_stats)."""
    n = len(cl)
    at_use = atr_arr if atr_arr is not None else at

    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    pk_bar = 0
    entry_px = 0.0
    entry_bar = 0
    entry_cost = 0.0
    exit_reason = ""
    n_trail = 0

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
                pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason,
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
            if p > pk:
                pk = p
                pk_bar = i
            ts = pk - trail_mult * a_val
            if p < ts:
                n_trail += 1
                exit_reason = "trail_stop"
                px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": pnl, "ret_pct": ret,
            "bars_held": (n - 1) - entry_bar, "exit_reason": "eod",
        })
        cash = received
        nt += 1
        nav[-1] = cash

    return nav, trades, {"n_trail": n_trail}


def _run_sim_dynamic(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                     model_w, model_mu, model_std,
                     trail_mult=TRAIL, cps=CPS_HARSH,
                     feature_mask=None, enable_monitor=False):
    """E0+EMA1D21 with DYNAMIC logistic filter at trail-stop time.

    model_w: logistic weights (n_feat + 1,)
    model_mu, model_std: standardization params (n_feat,)
    feature_mask: optional (10,) bool array for ablation
    enable_monitor: if True, also apply regime monitor entry blocking
    """
    n = len(cl)

    # Precompute regime monitor MDD if enabled
    monitor_blocked = np.zeros(n, dtype=np.bool_)
    if enable_monitor:
        # Compute rolling MDD for monitor
        # Use E0 nav as proxy for monitor (simplified)
        nav_proxy = np.zeros(n)
        nav_proxy[0] = CASH
        for i in range(1, n):
            nav_proxy[i] = nav_proxy[i - 1] * (cl[i] / cl[i - 1])
        peak_nav = np.maximum.accumulate(nav_proxy)
        dd_pct = (1.0 - nav_proxy / peak_nav) * 100

        for i in range(n):
            # 6-month MDD
            s6 = max(0, i - MONITOR_6M_BARS)
            mdd_6m = np.max(dd_pct[s6:i + 1]) if i > s6 else 0.0
            # 12-month MDD
            s12 = max(0, i - MONITOR_12M_BARS)
            mdd_12m = np.max(dd_pct[s12:i + 1]) if i > s12 else 0.0

            if mdd_6m > MONITOR_RED_6M * 100 or mdd_12m > MONITOR_RED_12M * 100:
                monitor_blocked[i] = True

    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    pk_bar = 0
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
                pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason,
                })
                cash = received
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1

        nav[i] = cash + bq * p
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            entry_ok = ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]
            if enable_monitor and monitor_blocked[i]:
                entry_ok = False
            if entry_ok:
                pe = True
        else:
            if p > pk:
                pk = p
                pk_bar = i
            ts = pk - trail_mult * a_val
            if p < ts:
                n_trail_triggered += 1

                # DYNAMIC filter: compute features with trade context
                feat = _compute_features_at_bar(
                    i, entry_bar, pk, pk_bar,
                    cl, hi, lo, at, ef, es, vd, d1_str_h4,
                    trail_mult, feature_mask)

                feat_s = (feat - model_mu) / model_std
                z = np.dot(np.append(feat_s, 1.0), model_w)
                prob = 1.0 / (1.0 + np.exp(-min(max(z, -500), 500)))

                if prob > 0.5:
                    n_trail_suppressed += 1
                    # Stay in position
                else:
                    exit_reason = "trail_stop"
                    px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": pnl, "ret_pct": ret,
            "bars_held": (n - 1) - entry_bar, "exit_reason": "eod",
        })
        cash = received
        nt += 1
        nav[-1] = cash

    return nav, trades, {
        "n_trail_triggered": n_trail_triggered,
        "n_trail_suppressed": n_trail_suppressed,
        "n_trail_allowed": n_trail_triggered - n_trail_suppressed,
    }


def _run_sim_static_mask(cl, ef, es, vd, at, regime_h4, wi,
                         suppress_mask, trail_mult=TRAIL, cps=CPS_HARSH):
    """X14-style static mask sim (for comparison)."""
    n = len(cl)
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
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "pnl_usd": pnl, "ret_pct": ret,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason,
                })
                cash = received
                bq = 0.0
                inp = False
                pk = 0.0
                nt += 1

        nav[i] = cash + bq * p
        a_val = at[i]
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
                if suppress_mask is not None and suppress_mask[i]:
                    n_trail_suppressed += 1
                else:
                    exit_reason = "trail_stop"
                    px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "pnl_usd": pnl, "ret_pct": ret,
            "bars_held": (n - 1) - entry_bar, "exit_reason": "eod",
        })
        cash = received
        nt += 1
        nav[-1] = cash

    return nav, trades, {
        "n_trail_triggered": n_trail_triggered,
        "n_trail_suppressed": n_trail_suppressed,
    }


# =========================================================================
# CHURN LABELING + FEATURE EXTRACTION (for training)
# =========================================================================

def _label_churn(trades, churn_window=CHURN_WINDOW):
    entry_bars = sorted(t["entry_bar"] for t in trades)
    results = []
    for idx, t in enumerate(trades):
        if t["exit_reason"] != "trail_stop":
            continue
        eb = t["exit_bar"]
        is_churn = any(eb < e <= eb + churn_window for e in entry_bars)
        results.append((idx, 1 if is_churn else 0))
    return results


def _extract_train_features(trades, churn_labels, cl, hi, lo, at, ef, es, vd,
                            d1_str_h4, trail_mult=TRAIL):
    """Extract 10 features for model training (full trade context available)."""
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

        eb = t["entry_bar"]
        peak_px = t["peak_px"]
        peak_bar = t.get("peak_bar", eb)

        feat = _compute_features_at_bar(
            sb, eb, peak_px, peak_bar,
            cl, hi, lo, at, ef, es, vd, d1_str_h4, trail_mult)

        features.append(feat)
        labels.append(label)

    if not features:
        return np.empty((0, 10)), np.empty(0, dtype=int)
    return np.array(features), np.array(labels, dtype=int)


def _train_model(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                 trail_mult=TRAIL, fixed_c=None):
    """Train logistic model on trail stop exits. Returns (w, mu, std, C, n_samples)."""
    churn_labels = _label_churn(trades)
    if len(churn_labels) < 10:
        return None, None, None, None, 0

    X, y = _extract_train_features(trades, churn_labels, cl, hi, lo, at, ef, es, vd,
                                   d1_str_h4, trail_mult)
    if len(y) < 10 or len(np.unique(y)) < 2:
        return None, None, None, None, 0

    Xs, mu, std = _standardize(X)

    if fixed_c is not None:
        best_c = fixed_c
    else:
        best_c = _select_c(X, y)

    w = _fit_logistic_l2(Xs, y, C=best_c)

    return w, mu, std, best_c, len(y)


def _build_x14_static_mask(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                           regime_h4, wi, train_end_idx,
                           trail_mult=TRAIL, cps=CPS_HARSH):
    """Reproduce X14's static Design D mask (with the feature mismatch bug)."""
    n = len(cl)

    nav_train, trades_train, _ = _run_sim_e0(
        cl[:train_end_idx], ef[:train_end_idx], es[:train_end_idx],
        vd[:train_end_idx], at[:train_end_idx], regime_h4[:train_end_idx], wi)

    churn_labels = _label_churn(trades_train)
    if len(churn_labels) < 10:
        return np.zeros(n, dtype=np.bool_)

    # X14's feature extraction (at signal bar, no trade context for features 2,5,6)
    features = []
    labels = []
    for trade_idx, label in churn_labels:
        t = trades_train[trade_idx]
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= train_end_idx:
            continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue
        # Full features for training (this matches X14)
        eb = t["entry_bar"]
        f1 = ef[sb] / es[sb] if abs(es[sb]) > 1e-12 else 1.0
        f2 = float(t["bars_held"])
        atr_start = max(0, sb - 99)
        atr_window = at[atr_start:sb + 1]
        valid_atr = atr_window[~np.isnan(atr_window)]
        f3 = float(np.sum(valid_atr <= at[sb])) / len(valid_atr) if len(valid_atr) > 1 else 0.5
        f4 = (hi[sb] - lo[sb]) / at[sb] if at[sb] > 1e-12 else 1.0
        peak_px = t["peak_px"]
        f5 = (peak_px - cl[sb]) / peak_px if peak_px > 1e-12 else 0.0
        trade_closes = cl[eb:t["exit_bar"]]
        f6 = float(sb - (eb + int(np.argmax(trade_closes)))) if len(trade_closes) > 0 else 0.0
        bar_w = hi[sb] - lo[sb]
        f7 = (cl[sb] - lo[sb]) / bar_w if bar_w > 1e-12 else 0.5
        f8 = float(vd[sb])
        f9 = float(d1_str_h4[sb])
        f10 = trail_mult * at[sb] / cl[sb] if cl[sb] > 1e-12 else 0.0
        features.append([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10])
        labels.append(label)

    if len(labels) < 10:
        return np.zeros(n, dtype=np.bool_)

    X_tr = np.array(features)
    y_tr = np.array(labels, dtype=int)
    if len(np.unique(y_tr)) < 2:
        return np.zeros(n, dtype=np.bool_)

    Xs, mu, std = _standardize(X_tr)
    best_c = _select_c(X_tr, y_tr)
    w = _fit_logistic_l2(Xs, y_tr, C=best_c)

    # Build mask: X14-style (features 2,5,6 zeroed at inference)
    mask = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at[i]):
            continue
        if abs(es[i]) < 1e-12 or at[i] < 1e-12 or cl[i] < 1e-12:
            continue
        f1 = ef[i] / es[i]
        f2 = 0.0  # ZEROED — X14 bug
        atr_start = max(0, i - 99)
        atr_window = at[atr_start:i + 1]
        valid_atr = atr_window[~np.isnan(atr_window)]
        f3 = float(np.sum(valid_atr <= at[i])) / len(valid_atr) if len(valid_atr) > 1 else 0.5
        f4 = (hi[i] - lo[i]) / at[i]
        f5 = 0.0  # ZEROED — X14 bug
        f6 = 0.0  # ZEROED — X14 bug
        bar_w = hi[i] - lo[i]
        f7 = (cl[i] - lo[i]) / bar_w if bar_w > 1e-12 else 0.5
        f8 = float(vd[i])
        f9 = float(d1_str_h4[i])
        f10 = TRAIL * at[i] / cl[i]
        feat = np.array([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10])
        feat_s = (feat - mu) / std
        z = np.dot(np.append(feat_s, 1.0), w)
        prob = 1.0 / (1.0 + np.exp(-min(max(z, -500), 500)))
        mask[i] = prob > 0.5

    return mask


# =========================================================================
# T0: FEATURE FIX VALIDATION
# =========================================================================

def run_t0(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct):
    print("\n" + "=" * 70)
    print("T0: FEATURE FIX VALIDATION (X14 static vs X15 dynamic)")
    print("=" * 70)

    # E0 baseline
    nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))

    # X14-style static mask (reproduces X14 Design D with bug)
    mask_x14 = _build_x14_static_mask(cl, hi, lo, ef, es, vd, at, d1_str_h4,
                                      regime_h4, wi, len(cl))
    nav_x14, trades_x14, ts_x14 = _run_sim_static_mask(
        cl, ef, es, vd, at, regime_h4, wi, mask_x14)
    m_x14 = _metrics(nav_x14, wi, len(trades_x14))

    # X15 dynamic filter (fixed)
    w, mu, std, best_c, n_samples = _train_model(
        trades_e0, cl, hi, lo, at, ef, es, vd, d1_str_h4)

    if w is None:
        print("  ERROR: Model training failed")
        return {"error": "model_training_failed"}

    nav_x15, trades_x15, ts_x15 = _run_sim_dynamic(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        w, mu, std)
    m_x15 = _metrics(nav_x15, wi, len(trades_x15))

    avg_hold_e0 = float(np.mean([t["bars_held"] for t in trades_e0])) if trades_e0 else 0.0
    avg_hold_x14 = float(np.mean([t["bars_held"] for t in trades_x14])) if trades_x14 else 0.0
    avg_hold_x15 = float(np.mean([t["bars_held"] for t in trades_x15])) if trades_x15 else 0.0

    rows = [
        {"variant": "E0", "sharpe": m_e0["sharpe"], "cagr": m_e0["cagr"],
         "mdd": m_e0["mdd"], "trades": m_e0["trades"], "avg_hold": avg_hold_e0,
         "d_sharpe": 0.0},
        {"variant": "X14_static", "sharpe": m_x14["sharpe"], "cagr": m_x14["cagr"],
         "mdd": m_x14["mdd"], "trades": m_x14["trades"], "avg_hold": avg_hold_x14,
         "d_sharpe": m_x14["sharpe"] - m_e0["sharpe"],
         "n_suppressed": ts_x14["n_trail_suppressed"]},
        {"variant": "X15_dynamic", "sharpe": m_x15["sharpe"], "cagr": m_x15["cagr"],
         "mdd": m_x15["mdd"], "trades": m_x15["trades"], "avg_hold": avg_hold_x15,
         "d_sharpe": m_x15["sharpe"] - m_e0["sharpe"],
         "n_suppressed": ts_x15["n_trail_suppressed"]},
    ]

    g0_pass = m_x15["sharpe"] > m_x14["sharpe"]

    for r in rows:
        print(f"  {r['variant']:15s}: Sharpe={r['sharpe']:.4f}, d={r['d_sharpe']:+.4f}, "
              f"CAGR={r['cagr']:.2f}%, MDD={r['mdd']:.2f}%, trades={r['trades']}")

    print(f"\n  G0 (X15 > X14): {'PASS' if g0_pass else 'FAIL'} "
          f"(X15={m_x15['sharpe']:.4f} vs X14={m_x14['sharpe']:.4f})")
    print(f"  Model: C={best_c}, n_samples={n_samples}")
    print(f"  Coefficients: {dict(zip(FEATURE_NAMES, w[:-1].tolist()))}")

    return {
        "rows": rows, "g0_pass": g0_pass, "model_c": best_c,
        "model_w": w.tolist(), "model_mu": mu.tolist(), "model_std": std.tolist(),
        "n_samples": n_samples, "e0_baseline": m_e0,
    }


# =========================================================================
# T1: FEATURE ABLATION
# =========================================================================

def run_t1(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, trades_e0, m_e0):
    print("\n" + "=" * 70)
    print("T1: FEATURE ABLATION")
    print("=" * 70)

    # Train model with all features
    w_full, mu_full, std_full, c_full, _ = _train_model(
        trades_e0, cl, hi, lo, at, ef, es, vd, d1_str_h4)

    if w_full is None:
        print("  ERROR: Model training failed")
        return {"error": "model_training_failed"}

    ablation_configs = {
        "all_10": np.ones(10, dtype=np.float64),
        "7_features": np.array([1, 0, 1, 1, 0, 0, 1, 1, 1, 1], dtype=np.float64),  # X14 equiv
        "top_4": np.array([1, 1, 0, 1, 0, 0, 0, 0, 1, 0], dtype=np.float64),  # ema_ratio, bars_held, bar_range_atr, d1_regime
        "ema_only": np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float64),
    }

    rows = []
    for name, mask in ablation_configs.items():
        nav_f, trades_f, ts_f = _run_sim_dynamic(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            w_full, mu_full, std_full, feature_mask=mask)
        m_f = _metrics(nav_f, wi, len(trades_f))
        d_sharpe = m_f["sharpe"] - m_e0["sharpe"]
        avg_hold = float(np.mean([t["bars_held"] for t in trades_f])) if trades_f else 0.0

        rows.append({
            "ablation": name, "sharpe": m_f["sharpe"], "cagr": m_f["cagr"],
            "mdd": m_f["mdd"], "trades": m_f["trades"], "avg_hold": avg_hold,
            "d_sharpe": d_sharpe,
            "n_suppressed": ts_f["n_trail_suppressed"],
            "features_active": int(np.sum(mask)),
        })

        print(f"  {name:15s}: Sharpe={m_f['sharpe']:.4f}, d={d_sharpe:+.4f}, "
              f"trades={m_f['trades']}, supp={ts_f['n_trail_suppressed']}")

    return {"rows": rows}


# =========================================================================
# T2: WFO VALIDATION
# =========================================================================

def run_t2(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct):
    print("\n" + "=" * 70)
    print("T2: WFO VALIDATION (dynamic filter, 4 folds)")
    print("=" * 70)

    folds = []
    for train_end_str, test_start_str, test_end_str in WFO_FOLDS:
        train_end = _date_to_bar_idx(h4_ct, train_end_str)
        test_start = _date_to_bar_idx(h4_ct, test_start_str)
        test_end = _date_to_bar_idx(h4_ct, test_end_str)
        folds.append((train_end, test_start, test_end))

    # E0 baseline (full data)
    nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)

    fold_results = []
    fold_coeffs = []

    for fold_idx, (train_end, test_start, test_end) in enumerate(folds):
        # Train: run E0 on training portion, extract labels, fit model
        nav_train, trades_train, _ = _run_sim_e0(
            cl[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], at[:train_end + 1], regime_h4[:train_end + 1], wi)

        w, mu, std, best_c, n_samples = _train_model(
            trades_train, cl[:train_end + 1], hi[:train_end + 1], lo[:train_end + 1],
            at[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], d1_str_h4[:train_end + 1])

        if w is None:
            fold_results.append({
                "fold": fold_idx + 1, "e0_sharpe_test": 0.0,
                "filter_sharpe_test": 0.0, "d_sharpe": 0.0, "win": False,
                "c": 0.0, "n_samples": 0,
            })
            continue

        fold_coeffs.append(w[:-1].tolist())

        # E0 test metrics
        test_trades_e0 = [t for t in trades_e0 if test_start <= t["entry_bar"] < test_end]
        m_e0_test = _metrics_window(nav_e0, test_start, test_end + 1, len(test_trades_e0))

        # Dynamic filter on full data, extract test metrics
        nav_f, trades_f, _ = _run_sim_dynamic(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, w, mu, std)
        test_trades_f = [t for t in trades_f if test_start <= t["entry_bar"] < test_end]
        m_f_test = _metrics_window(nav_f, test_start, test_end + 1, len(test_trades_f))

        d_sharpe = m_f_test["sharpe"] - m_e0_test["sharpe"]
        win = d_sharpe > 0

        fold_results.append({
            "fold": fold_idx + 1, "e0_sharpe_test": m_e0_test["sharpe"],
            "filter_sharpe_test": m_f_test["sharpe"], "d_sharpe": d_sharpe,
            "win": win, "c": best_c, "n_samples": n_samples,
        })

        print(f"  Fold {fold_idx + 1}: E0={m_e0_test['sharpe']:.4f}, "
              f"Filt={m_f_test['sharpe']:.4f}, d={d_sharpe:+.4f} "
              f"{'WIN' if win else 'LOSE'} (C={best_c}, n={n_samples})")

    win_rate = sum(1 for f in fold_results if f["win"]) / len(fold_results)
    mean_d = float(np.mean([f["d_sharpe"] for f in fold_results]))
    g1_pass = win_rate >= 0.75 and mean_d > 0

    print(f"\n  Win rate: {win_rate:.0%}, mean d_sharpe: {mean_d:+.4f}")
    print(f"  G1 (>=75% AND mean_d>0): {'PASS' if g1_pass else 'FAIL'}")

    # Coefficient stability
    if fold_coeffs:
        coeffs_arr = np.array(fold_coeffs)
        coeff_std = np.std(coeffs_arr, axis=0)
        coeff_mean = np.mean(np.abs(coeffs_arr), axis=0)
        drift = coeff_std / (coeff_mean + 1e-12)
        print(f"  Coeff drift (std/|mean|): {dict(zip(FEATURE_NAMES, drift.tolist()))}")

    return {
        "folds": fold_results, "win_rate": win_rate, "mean_d_sharpe": mean_d,
        "g1_pass": g1_pass, "fold_coefficients": fold_coeffs,
    }


# =========================================================================
# T3: BOOTSTRAP VALIDATION
# =========================================================================

def run_t3(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4, wi):
    print("\n" + "=" * 70)
    print(f"T3: BOOTSTRAP VALIDATION ({N_BOOT} VCBB paths, dynamic filter)")
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
        bnav_e0, btrades_e0, _ = _run_sim_e0(bcl, bef, bes, bvd, bat, breg, bwi)
        bm_e0 = _metrics(bnav_e0, bwi, len(btrades_e0))

        # Train model on first 60%
        train_end_b = int(n_b * 0.6)
        bnav_train, btrades_train, _ = _run_sim_e0(
            bcl[:train_end_b], bef[:train_end_b], bes[:train_end_b],
            bvd[:train_end_b], bat[:train_end_b], breg[:train_end_b], bwi)

        bw, bmu, bstd, _, _ = _train_model(
            btrades_train, bcl[:train_end_b], bhi[:train_end_b], blo[:train_end_b],
            bat[:train_end_b], bef[:train_end_b], bes[:train_end_b],
            bvd[:train_end_b], bd1_str[:train_end_b], fixed_c=1.0)

        if bw is None:
            d_sharpes.append(0.0)
            d_cagrs.append(0.0)
            d_mdds.append(0.0)
            continue

        # Dynamic filter on full path
        bnav_f, btrades_f, _ = _run_sim_dynamic(
            bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1_str, bwi,
            bw, bmu, bstd)
        bm_f = _metrics(bnav_f, bwi, len(btrades_f))

        d_sharpes.append(bm_f["sharpe"] - bm_e0["sharpe"])
        d_cagrs.append(bm_f["cagr"] - bm_e0["cagr"])
        d_mdds.append(bm_f["mdd"] - bm_e0["mdd"])

        if (b_idx + 1) % 100 == 0:
            print(f"    ... {b_idx + 1}/{N_BOOT} paths done")

    d_sharpes = np.array(d_sharpes)
    d_cagrs = np.array(d_cagrs)
    d_mdds = np.array(d_mdds)

    p_ds_gt0 = float(np.mean(d_sharpes > 0))
    med_d_mdd = float(np.median(d_mdds))
    g2_pass = p_ds_gt0 > 0.60
    g3_pass = med_d_mdd <= 5.0

    results = {
        "d_sharpe_median": float(np.median(d_sharpes)),
        "d_sharpe_p5": float(np.percentile(d_sharpes, 5)),
        "d_sharpe_p95": float(np.percentile(d_sharpes, 95)),
        "p_d_sharpe_gt0": p_ds_gt0,
        "d_mdd_median": med_d_mdd,
        "d_mdd_p5": float(np.percentile(d_mdds, 5)),
        "d_mdd_p95": float(np.percentile(d_mdds, 95)),
        "d_cagr_median": float(np.median(d_cagrs)),
        "g2_pass": g2_pass, "g3_pass": g3_pass,
    }

    print(f"\n  d_sharpe: median={results['d_sharpe_median']:+.4f}, "
          f"[{results['d_sharpe_p5']:+.4f}, {results['d_sharpe_p95']:+.4f}]")
    print(f"  P(d_sharpe > 0): {p_ds_gt0:.1%}")
    print(f"  d_mdd: median={med_d_mdd:+.2f}pp")
    print(f"  G2 (P>60%): {'PASS' if g2_pass else 'FAIL'}")
    print(f"  G3 (med_d_mdd<=5pp): {'PASS' if g3_pass else 'FAIL'}")

    return results, d_sharpes, d_cagrs, d_mdds


# =========================================================================
# T4: REGIME MONITOR INTERACTION
# =========================================================================

def run_t4(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, trades_e0):
    print("\n" + "=" * 70)
    print("T4: REGIME MONITOR INTERACTION")
    print("=" * 70)

    m_e0 = _metrics(_run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)[0],
                    wi, len(trades_e0))

    w, mu, std, _, _ = _train_model(
        trades_e0, cl, hi, lo, at, ef, es, vd, d1_str_h4)

    if w is None:
        print("  ERROR: Model training failed")
        return {"error": "model_training_failed"}

    # Filter only
    nav_f, trades_f, _ = _run_sim_dynamic(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        w, mu, std, enable_monitor=False)
    m_f = _metrics(nav_f, wi, len(trades_f))

    # Monitor only (dummy model that never suppresses)
    w_zero = np.zeros_like(w)
    w_zero[-1] = -10.0  # bias = -10 → sigmoid ≈ 0 → never suppress
    nav_m, trades_m, _ = _run_sim_dynamic(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        w_zero, mu, std, enable_monitor=True)
    m_m = _metrics(nav_m, wi, len(trades_m))

    # Both
    nav_fm, trades_fm, _ = _run_sim_dynamic(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        w, mu, std, enable_monitor=True)
    m_fm = _metrics(nav_fm, wi, len(trades_fm))

    d_f = m_f["sharpe"] - m_e0["sharpe"]
    d_m = m_m["sharpe"] - m_e0["sharpe"]
    d_fm = m_fm["sharpe"] - m_e0["sharpe"]
    expected_additive = d_f + d_m
    interaction = d_fm - expected_additive

    g4_pass = abs(interaction) < 0.05

    rows = [
        {"variant": "E0", "sharpe": m_e0["sharpe"], "cagr": m_e0["cagr"],
         "mdd": m_e0["mdd"], "trades": m_e0["trades"], "d_sharpe": 0.0},
        {"variant": "E0+Filter", "sharpe": m_f["sharpe"], "cagr": m_f["cagr"],
         "mdd": m_f["mdd"], "trades": m_f["trades"], "d_sharpe": d_f},
        {"variant": "E0+Monitor", "sharpe": m_m["sharpe"], "cagr": m_m["cagr"],
         "mdd": m_m["mdd"], "trades": m_m["trades"], "d_sharpe": d_m},
        {"variant": "E0+Filter+Monitor", "sharpe": m_fm["sharpe"], "cagr": m_fm["cagr"],
         "mdd": m_fm["mdd"], "trades": m_fm["trades"], "d_sharpe": d_fm},
    ]

    for r in rows:
        print(f"  {r['variant']:22s}: Sharpe={r['sharpe']:.4f}, d={r['d_sharpe']:+.4f}, "
              f"trades={r['trades']}")

    print(f"\n  Expected additive: {expected_additive:+.4f}")
    print(f"  Actual combined:   {d_fm:+.4f}")
    print(f"  Interaction:       {interaction:+.4f}")
    print(f"  G4 (|interaction| < 0.05): {'PASS' if g4_pass else 'FAIL'}")

    return {"rows": rows, "interaction": interaction, "g4_pass": g4_pass}


# =========================================================================
# T5: RETRAINING SENSITIVITY
# =========================================================================

def run_t5(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct):
    print("\n" + "=" * 70)
    print("T5: RETRAINING SENSITIVITY")
    print("=" * 70)

    # Training windows
    windows = [
        ("2019-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
        ("2019-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
        ("2019-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
        ("2019-01-01", "2024-12-31", "2025-01-01", "2026-02-20"),
    ]

    nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)

    results = []
    all_coeffs = []
    all_c_values = []

    for train_start, train_end_str, test_start_str, test_end_str in windows:
        train_end = _date_to_bar_idx(h4_ct, train_end_str)
        test_start = _date_to_bar_idx(h4_ct, test_start_str)
        test_end = _date_to_bar_idx(h4_ct, test_end_str)

        # Train
        nav_train, trades_train, _ = _run_sim_e0(
            cl[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], at[:train_end + 1], regime_h4[:train_end + 1], wi)

        w, mu, std, best_c, n_samples = _train_model(
            trades_train, cl[:train_end + 1], hi[:train_end + 1], lo[:train_end + 1],
            at[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], d1_str_h4[:train_end + 1])

        if w is None:
            results.append({"train_end": train_end_str, "test_period": test_start_str,
                            "d_sharpe": 0.0, "c": 0.0, "n_samples": 0})
            continue

        all_coeffs.append(w[:-1].tolist())
        all_c_values.append(best_c)

        # Also test with fixed C=1.0
        w_fixed, mu_f, std_f, _, _ = _train_model(
            trades_train, cl[:train_end + 1], hi[:train_end + 1], lo[:train_end + 1],
            at[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], d1_str_h4[:train_end + 1], fixed_c=1.0)

        # Test: dynamic filter on full data, extract test window
        nav_f, trades_f, _ = _run_sim_dynamic(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, w, mu, std)
        test_trades_e0 = [t for t in trades_e0 if test_start <= t["entry_bar"] < test_end]
        test_trades_f = [t for t in trades_f if test_start <= t["entry_bar"] < test_end]
        m_e0_t = _metrics_window(nav_e0, test_start, test_end + 1, len(test_trades_e0))
        m_f_t = _metrics_window(nav_f, test_start, test_end + 1, len(test_trades_f))

        # Fixed C test
        d_sharpe_cv = m_f_t["sharpe"] - m_e0_t["sharpe"]
        d_sharpe_fixed = 0.0
        if w_fixed is not None:
            nav_ff, trades_ff, _ = _run_sim_dynamic(
                cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                w_fixed, mu_f, std_f)
            test_trades_ff = [t for t in trades_ff if test_start <= t["entry_bar"] < test_end]
            m_ff_t = _metrics_window(nav_ff, test_start, test_end + 1, len(test_trades_ff))
            d_sharpe_fixed = m_ff_t["sharpe"] - m_e0_t["sharpe"]

        results.append({
            "train_end": train_end_str, "test_period": test_start_str,
            "d_sharpe_cv": d_sharpe_cv, "d_sharpe_fixed_c": d_sharpe_fixed,
            "c_selected": best_c, "n_samples": n_samples,
        })

        print(f"  Train→{train_end_str}, Test {test_start_str}: "
              f"d_cv={d_sharpe_cv:+.4f}, d_fixC={d_sharpe_fixed:+.4f}, C={best_c}")

    # Coefficient stability
    g5_pass = True
    if len(all_coeffs) >= 2:
        coeffs_arr = np.array(all_coeffs)
        coeff_std = np.std(coeffs_arr, axis=0)
        coeff_mean = np.mean(np.abs(coeffs_arr), axis=0)
        drift = coeff_std / (coeff_mean + 1e-12)
        max_drift = float(np.max(drift))
        g5_pass = max_drift < 0.50

        print(f"\n  Coefficient drift (std/|mean|):")
        for j, name in enumerate(FEATURE_NAMES):
            print(f"    {name:18s}: {drift[j]:.3f}")
        print(f"  Max drift: {max_drift:.3f}")
        print(f"  C values across folds: {all_c_values}")

    print(f"  G5 (max_drift < 50%): {'PASS' if g5_pass else 'FAIL'}")

    return {"results": results, "g5_pass": g5_pass,
            "coefficients": all_coeffs, "c_values": all_c_values}


# =========================================================================
# T6: COMPREHENSIVE COMPARISON
# =========================================================================

def run_t6(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct,
           t0_results, t2_results, t4_results):
    print("\n" + "=" * 70)
    print("T6: COMPREHENSIVE COMPARISON")
    print("=" * 70)

    nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))

    # X15 dynamic
    w = np.array(t0_results["model_w"])
    mu = np.array(t0_results["model_mu"])
    std = np.array(t0_results["model_std"])

    nav_x15, trades_x15, ts_x15 = _run_sim_dynamic(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, w, mu, std)
    m_x15 = _metrics(nav_x15, wi, len(trades_x15))

    # E5
    rat = _robust_atr(hi, lo, cl)
    nav_e5, trades_e5, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi, atr_arr=rat)
    m_e5 = _metrics(nav_e5, wi, len(trades_e5))

    # Oracle
    n = len(cl)
    entry_sig = np.zeros(n, dtype=np.bool_)
    for j in range(n):
        if not (math.isnan(ef[j]) or math.isnan(es[j]) or math.isnan(at[j])):
            entry_sig[j] = ef[j] > es[j] and vd[j] > VDO_THR and regime_h4[j]
    oracle_mask = np.zeros(n, dtype=np.bool_)
    for i in range(n):
        end = min(i + 1 + CHURN_WINDOW, n)
        if end > i + 1 and np.any(entry_sig[i + 1:end]):
            oracle_mask[i] = True
    nav_or, trades_or, ts_or = _run_sim_static_mask(
        cl, ef, es, vd, at, regime_h4, wi, oracle_mask)
    m_or = _metrics(nav_or, wi, len(trades_or))

    def _avg_hold(trades):
        return float(np.mean([t["bars_held"] for t in trades])) if trades else 0.0

    table = [
        {"strategy": "E0", **m_e0, "avg_hold": _avg_hold(trades_e0)},
        {"strategy": "E0+FilterD(X15)", **m_x15, "avg_hold": _avg_hold(trades_x15),
         "n_suppressed": ts_x15["n_trail_suppressed"]},
        {"strategy": "E5", **m_e5, "avg_hold": _avg_hold(trades_e5)},
        {"strategy": "Oracle", **m_or, "avg_hold": _avg_hold(trades_or),
         "n_suppressed": ts_or["n_trail_suppressed"]},
    ]

    print(f"\n  {'Strategy':22s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Trades':>7s} {'AvgHold':>8s}")
    print("  " + "-" * 65)
    for r in table:
        print(f"  {r['strategy']:22s} {r['sharpe']:8.4f} {r['cagr']:8.2f} "
              f"{r['mdd']:8.2f} {r['trades']:7d} {r['avg_hold']:8.1f}")

    return table


# =========================================================================
# SAVE + VERDICT + MAIN
# =========================================================================

def save_results(t0, t1, t2, t2_arrays, t3_results, t4, t5, t6, verdict):
    out = {
        "verdict": verdict,
        "t0_feature_fix": {k: v for k, v in t0.items() if k not in ("model_w", "model_mu", "model_std")},
        "t1_ablation": t1,
        "t2_wfo": t2,
        "t3_bootstrap": t3_results,
        "t4_monitor": {k: v for k, v in t4.items() if k != "rows"} if t4 else {},
        "t5_retrain": {k: v for k, v in t5.items() if k != "coefficients"} if t5 else {},
    }
    with open(OUTDIR / "x15_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    # T0
    if t0.get("rows"):
        all_keys = []
        for row in t0["rows"]:
            for k in row:
                if k not in all_keys:
                    all_keys.append(k)
        with open(OUTDIR / "x15_feature_fix.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=all_keys)
            w.writeheader()
            for row in t0["rows"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else v for k, v in row.items()})

    # T1
    if t1 and t1.get("rows"):
        with open(OUTDIR / "x15_ablation.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(t1["rows"][0].keys()))
            w.writeheader()
            for row in t1["rows"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else v for k, v in row.items()})

    # T2
    if t2 and t2.get("folds"):
        with open(OUTDIR / "x15_wfo_results.csv", "w", newline="") as f:
            fields = list(t2["folds"][0].keys())
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in t2["folds"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else v for k, v in row.items()})

    # T3 bootstrap
    if t2_arrays is not None:
        d_sharpes, d_cagrs, d_mdds = t2_arrays
        with open(OUTDIR / "x15_bootstrap.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "d_sharpe", "d_cagr", "d_mdd"])
            for i in range(len(d_sharpes)):
                w.writerow([i, f"{d_sharpes[i]:.6f}", f"{d_cagrs[i]:.6f}", f"{d_mdds[i]:.6f}"])

    # T4
    if t4 and t4.get("rows"):
        with open(OUTDIR / "x15_monitor_interaction.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(t4["rows"][0].keys()))
            w.writeheader()
            for row in t4["rows"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else v for k, v in row.items()})

    # T5
    if t5 and t5.get("results"):
        with open(OUTDIR / "x15_retrain_sensitivity.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(t5["results"][0].keys()))
            w.writeheader()
            for row in t5["results"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else v for k, v in row.items()})

    # T6
    if t6:
        with open(OUTDIR / "x15_comparison.csv", "w", newline="") as f:
            fields = ["strategy", "sharpe", "cagr", "mdd", "trades", "avg_hold"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in t6:
                out_row = {k: f"{v:.6f}" if isinstance(v, float) else v for k, v in row.items()
                           if k in fields}
                w.writerow(out_row)

    print(f"\n  Saved to {OUTDIR}/x15_*.{{json,csv}}")


def main():
    t_start = time.time()

    print("X15: Churn Filter Integration — Design D Production Pipeline")
    print("=" * 70)

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
    ef, es, vd, at = _compute_indicators(cl, hi, lo, vo, tb)

    print(f"  Bars: {len(cl)} H4, {len(d1_cl)} D1, warmup_idx={wi}")

    # E0 baseline
    nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))
    print(f"  E0: Sharpe={m_e0['sharpe']:.4f}, CAGR={m_e0['cagr']:.2f}%, "
          f"MDD={m_e0['mdd']:.2f}%, trades={m_e0['trades']}")

    # T0: Feature fix
    t0 = run_t0(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct)

    # T1: Ablation
    t1 = run_t1(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, trades_e0, m_e0)

    # T2: WFO
    t2 = run_t2(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct)

    # T3: Bootstrap
    t3_results, d_sharpes, d_cagrs, d_mdds = run_t3(
        cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4, wi)

    # T4: Monitor interaction
    t4 = run_t4(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, trades_e0)

    # T5: Retrain sensitivity
    t5 = run_t5(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct)

    # T6: Comparison
    t6 = run_t6(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct,
                t0, t3_results, t4)

    # Verdict
    gates = {
        "G0": t0.get("g0_pass", False),
        "G1": t2.get("g1_pass", False),
        "G2": t3_results.get("g2_pass", False),
        "G3": t3_results.get("g3_pass", False),
        "G4": t4.get("g4_pass", False),
        "G5": t5.get("g5_pass", False),
    }

    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    for g, v in gates.items():
        print(f"  {g}: {'PASS' if v else 'FAIL'}")

    all_pass = all(gates.values())
    if all_pass:
        verdict = "INTEGRATE"
    elif not gates["G0"]:
        verdict = "ABORT"
    elif not gates["G1"] or not gates["G2"]:
        verdict = "HOLD"
    elif not gates["G4"]:
        verdict = "SEPARATE"
    elif not gates["G5"]:
        verdict = "RETRAIN_REQUIRED"
    else:
        verdict = "PARTIAL_FAIL"

    print(f"\n  VERDICT: {verdict}")

    verdict_info = {"verdict": verdict, "gates": gates}

    save_results(t0, t1, t2, (d_sharpes, d_cagrs, d_mdds), t3_results,
                 t4, t5, t6, verdict_info)

    elapsed = time.time() - t_start
    print(f"\nX15 BENCHMARK COMPLETE — {elapsed:.0f}s — VERDICT: {verdict}")


if __name__ == "__main__":
    main()
