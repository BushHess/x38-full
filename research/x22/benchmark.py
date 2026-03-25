#!/usr/bin/env python3
"""X22 Research — Cost Sensitivity Analysis: Strategy Robustness to Execution Cost

CHARACTERIZATION study — no gates, no new DOF. Sweep execution cost across
4 strategies to understand performance at realistic costs.

Strategies:
  E0:              Baseline (EMA entry + ATR trail + EMA exit)
  E5+EMA1D21:      Primary (robust ATR + D1 regime filter)
  E5+EMA1D21+X14D: + churn filter P>0.5 (risk-focused)
  E5+EMA1D21+X18:  + churn filter α=40% (return-focused)

Cost sweep: {2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100} bps RT

Tests:
  T0: Full metric table (44 backtests)
  T1: Breakeven analysis (interpolation)
  T2: Churn filter marginal value
  T3: Strategy ranking at realistic costs
  T4: Bootstrap at 15 bps (500 VCBB × 4 strategies)
  T5: Cost drag decomposition
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
ATR_P = 14           # E0 standard ATR period

# E5 robust ATR
RATR_P = 20
RATR_Q = 0.90
RATR_LB = 100

# Churn filter
CHURN_WINDOW = 20
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
X18_ALPHA = 40        # consensus α from X18 study

# Cost sweep
COST_BPS = [2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
CPS_50 = SCENARIOS["harsh"].per_side_bps / 10_000.0

# Bootstrap
N_BOOT = 500
BLKSZ = 60
SEED = 42
BOOT_CPS_BPS = 15    # realistic cost for bootstrap

STRATEGY_NAMES = ["E0", "E5+EMA1D21", "E5+EMA1D21+X14D", "E5+EMA1D21+X18"]

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# INDICATORS
# =========================================================================

def _ema(series, period):
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
        alpha_w = 1.0 / period
        b = np.array([alpha_w])
        a = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha_w) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


def _robust_atr(high, low, close, cap_q=RATR_Q, cap_lb=RATR_LB, period=RATR_P):
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


def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "final_nav": float(navs[-1]) if len(navs) else CASH}
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
    calmar = cagr / mdd if mdd > 0 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
            "trades": nt, "final_nav": float(navs[-1])}


# =========================================================================
# CHURN MODEL (L2-penalized logistic, 7 features)
# =========================================================================

def _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4, trail_mult=TRAIL):
    f1 = ef[i] / es[i] if abs(es[i]) > 1e-12 else 1.0
    atr_start = max(0, i - 99)
    atr_window = at[atr_start:i + 1]
    valid_atr = atr_window[~np.isnan(atr_window)]
    f2 = float(np.sum(valid_atr <= at[i])) / len(valid_atr) if len(valid_atr) > 1 else 0.5
    f3 = (hi[i] - lo[i]) / at[i] if at[i] > 1e-12 else 1.0
    bar_w = hi[i] - lo[i]
    f4 = (cl[i] - lo[i]) / bar_w if bar_w > 1e-12 else 0.5
    f5 = float(vd[i])
    f6 = float(d1_str_h4[i])
    f7 = trail_mult * at[i] / cl[i] if cl[i] > 1e-12 else 0.0
    return np.array([f1, f2, f3, f4, f5, f6, f7])


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


def _extract_features_from_trades(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    n = len(cl)
    churn_labels = _label_churn(trades)
    features, labels = [], []
    for trade_idx, label in churn_labels:
        t = trades[trade_idx]
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n:
            continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        features.append(feat)
        labels.append(label)
    if not features:
        return np.empty((0, 7)), np.empty(0, dtype=int)
    return np.array(features), np.array(labels, dtype=int)


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
        H_full = H + H_reg
        try:
            dw = np.linalg.solve(H_full, grad)
        except np.linalg.LinAlgError:
            break
        w -= dw
        if np.max(np.abs(dw)) < 1e-8:
            break
    return w


def _kfold_auc(X, y, C=1.0, k=5):
    n = len(y)
    idx = np.arange(n)
    rng = np.random.default_rng(42)
    rng.shuffle(idx)
    aucs = []
    fold_size = n // k
    for fold in range(k):
        s = fold * fold_size
        e = s + fold_size if fold < k - 1 else n
        val_idx = idx[s:e]
        train_idx = np.concatenate([idx[:s], idx[e:]])
        w = _fit_logistic_l2(X[train_idx], y[train_idx], C=C)
        preds = X[val_idx] @ w[:X.shape[1]] + w[-1]
        preds = 1.0 / (1.0 + np.exp(-np.clip(preds, -500, 500)))
        pos = preds[y[val_idx] == 1]
        neg = preds[y[val_idx] == 0]
        if len(pos) == 0 or len(neg) == 0:
            aucs.append(0.5)
            continue
        comp = pos[:, None] > neg[None, :]
        ties = pos[:, None] == neg[None, :]
        aucs.append(float((np.sum(comp) + 0.5 * np.sum(ties)) / (len(pos) * len(neg))))
    return float(np.mean(aucs))


def _standardize(X):
    mu = np.mean(X, axis=0)
    std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


def _train_churn_model(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    X, y = _extract_features_from_trades(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    if len(y) < 10 or len(np.unique(y)) < 2:
        return None, None, None, None, 0
    Xs, mu, std = _standardize(X)
    best_c, best_auc = 1.0, 0.0
    for c_val in C_VALUES:
        auc_c = _kfold_auc(Xs, y, C=c_val, k=5)
        if auc_c > best_auc:
            best_auc = auc_c
            best_c = c_val
    w = _fit_logistic_l2(Xs, y, C=best_c)
    return w, mu, std, best_c, len(y)


def _predict_score(feat, w, mu, std):
    feat_s = (feat - mu) / std
    z = np.dot(np.append(feat_s, 1.0), w)
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))


def _compute_train_scores(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                            model_w, model_mu, model_std):
    n = len(cl)
    scores = []
    for t in trades:
        if t.get("exit_reason") != "trail_stop":
            continue
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n or math.isnan(at[sb]) or math.isnan(ef[sb]):
            continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        scores.append(_predict_score(feat, model_w, model_mu, model_std))
    return np.array(scores)


# =========================================================================
# SIM FUNCTIONS
# =========================================================================

def _run_sim_e0(cl, ef_e0, es_e0, vd, at_e0, wi, cps=CPS_50):
    """E0 baseline: standard ATR, no regime filter."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    pk = 0.0; pk_bar = 0
    entry_bar = 0; entry_px = 0.0; entry_cost = 0.0
    exit_reason = ""
    nav = np.zeros(n)
    trades = []

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p; pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret_pct,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason})
                cash = received; bq = 0.0; inp = False; pk = 0.0

        nav[i] = cash + bq * p
        a_val = at_e0[i]
        if math.isnan(a_val) or math.isnan(ef_e0[i]) or math.isnan(es_e0[i]):
            continue

        if not inp:
            if ef_e0[i] > es_e0[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            if p >= pk: pk_bar = i
            ts = pk - TRAIL * a_val
            if p < ts:
                exit_reason = "trail_stop"; px = True
            elif ef_e0[i] < es_e0[i]:
                exit_reason = "trend_exit"; px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": received - entry_cost,
            "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
    return nav, trades


def _run_sim_e5_ema(cl, ef, es, vd, at_e5, regime_h4, wi, cps=CPS_50):
    """E5+EMA1D21: robust ATR + D1 regime filter."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    pk = 0.0; pk_bar = 0
    entry_bar = 0; entry_px = 0.0; entry_cost = 0.0
    exit_reason = ""
    nav = np.zeros(n)
    trades = []

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p; pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret_pct,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason})
                cash = received; bq = 0.0; inp = False; pk = 0.0

        nav[i] = cash + bq * p
        a_val = at_e5[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p >= pk: pk_bar = i
            ts = pk - TRAIL * a_val
            if p < ts:
                exit_reason = "trail_stop"; px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"; px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": received - entry_cost,
            "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
    return nav, trades


def _run_sim_churn_mask(cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4, wi,
                         model_w, model_mu, model_std, threshold,
                         cps=CPS_50):
    """E5+EMA1D21 + churn filter: suppress trail if score > threshold."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    pk = 0.0; pk_bar = 0
    entry_bar = 0; entry_px = 0.0; entry_cost = 0.0
    exit_reason = ""
    nav = np.zeros(n)
    trades = []
    n_suppress = 0

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p; pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret_pct,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason})
                cash = received; bq = 0.0; inp = False; pk = 0.0

        nav[i] = cash + bq * p
        a_val = at_e5[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p >= pk: pk_bar = i
            ts = pk - TRAIL * a_val
            if p < ts:
                feat = _extract_features_7(i, cl, hi, lo, at_e5, ef, es, vd,
                                            d1_str_h4, TRAIL)
                score = _predict_score(feat, model_w, model_mu, model_std)
                if score > threshold:
                    n_suppress += 1
                else:
                    exit_reason = "trail_stop"; px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"; px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": received - entry_cost,
            "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
    return nav, trades, n_suppress


# =========================================================================
# T0: FULL METRIC TABLE
# =========================================================================

def run_t0(cl, hi, lo, ef_e0, es_e0, ef_e5, es_e5, vd, at_e0, at_e5,
           regime_h4, d1_str_h4, wi,
           model_w, model_mu, model_std, x14d_thresh, x18_thresh):
    """44 backtests: 4 strategies × 11 costs."""
    print("\nT0: Full Metric Table (44 backtests)")

    yrs = (len(cl) - wi) / (6.0 * 365.25)
    rows = []

    for cost_bps in COST_BPS:
        cps = cost_bps / 20_000.0

        # E0
        nav_e0, tr_e0 = _run_sim_e0(cl, ef_e0, es_e0, vd, at_e0, wi, cps=cps)
        m_e0 = _metrics(nav_e0, wi, len(tr_e0))
        freq_e0 = m_e0["trades"] / yrs if yrs > 0 else 0
        drag_e0 = cost_bps * m_e0["trades"] / yrs if yrs > 0 else 0
        rows.append({"strategy": "E0", "cost_bps": cost_bps, **m_e0,
                      "freq": freq_e0, "cost_drag_bps_yr": drag_e0})

        # E5+EMA1D21
        nav_e5, tr_e5 = _run_sim_e5_ema(cl, ef_e5, es_e5, vd, at_e5, regime_h4, wi, cps=cps)
        m_e5 = _metrics(nav_e5, wi, len(tr_e5))
        freq_e5 = m_e5["trades"] / yrs if yrs > 0 else 0
        drag_e5 = cost_bps * m_e5["trades"] / yrs if yrs > 0 else 0
        rows.append({"strategy": "E5+EMA1D21", "cost_bps": cost_bps, **m_e5,
                      "freq": freq_e5, "cost_drag_bps_yr": drag_e5})

        # E5+EMA1D21+X14D
        nav_x14d, tr_x14d, _ = _run_sim_churn_mask(
            cl, hi, lo, ef_e5, es_e5, vd, at_e5, regime_h4, d1_str_h4, wi,
            model_w, model_mu, model_std, x14d_thresh, cps=cps)
        m_x14d = _metrics(nav_x14d, wi, len(tr_x14d))
        freq_x14d = m_x14d["trades"] / yrs if yrs > 0 else 0
        drag_x14d = cost_bps * m_x14d["trades"] / yrs if yrs > 0 else 0
        rows.append({"strategy": "E5+EMA1D21+X14D", "cost_bps": cost_bps, **m_x14d,
                      "freq": freq_x14d, "cost_drag_bps_yr": drag_x14d})

        # E5+EMA1D21+X18
        nav_x18, tr_x18, _ = _run_sim_churn_mask(
            cl, hi, lo, ef_e5, es_e5, vd, at_e5, regime_h4, d1_str_h4, wi,
            model_w, model_mu, model_std, x18_thresh, cps=cps)
        m_x18 = _metrics(nav_x18, wi, len(tr_x18))
        freq_x18 = m_x18["trades"] / yrs if yrs > 0 else 0
        drag_x18 = cost_bps * m_x18["trades"] / yrs if yrs > 0 else 0
        rows.append({"strategy": "E5+EMA1D21+X18", "cost_bps": cost_bps, **m_x18,
                      "freq": freq_x18, "cost_drag_bps_yr": drag_x18})

        print(f"  {cost_bps:3d} bps: E0 Sh={m_e0['sharpe']:.3f} | E5 Sh={m_e5['sharpe']:.3f} | "
              f"X14D Sh={m_x14d['sharpe']:.3f} | X18 Sh={m_x18['sharpe']:.3f}")

    # Write CSV
    with open(OUTDIR / "x22_full_table.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "cost_bps", "sharpe", "cagr", "mdd", "calmar",
                     "trades", "freq", "cost_drag_bps_yr", "final_nav"])
        for r in rows:
            w.writerow([r["strategy"], r["cost_bps"],
                        f"{r['sharpe']:.4f}", f"{r['cagr']:.2f}", f"{r['mdd']:.2f}",
                        f"{r['calmar']:.4f}", r["trades"],
                        f"{r['freq']:.1f}", f"{r['cost_drag_bps_yr']:.0f}",
                        f"{r['final_nav']:.2f}"])
    return rows


# =========================================================================
# T1: BREAKEVEN ANALYSIS
# =========================================================================

def run_t1(t0_rows):
    """Find breakeven costs by interpolation."""
    print("\nT1: Breakeven Analysis")

    results = {}
    for strat in STRATEGY_NAMES:
        strat_rows = [r for r in t0_rows if r["strategy"] == strat]
        strat_rows.sort(key=lambda r: r["cost_bps"])
        costs = [r["cost_bps"] for r in strat_rows]
        sharpes = [r["sharpe"] for r in strat_rows]
        cagrs = [r["cagr"] for r in strat_rows]

        be_sharpe = _interpolate_zero(costs, sharpes)
        be_cagr = _interpolate_zero(costs, cagrs)

        results[strat] = {"be_sharpe_0": be_sharpe, "be_cagr_0": be_cagr}
        print(f"  {strat:25s}: Sharpe=0 at {be_sharpe:>6.0f} bps, CAGR=0 at {be_cagr:>6.0f} bps")

    # Write CSV
    with open(OUTDIR / "x22_breakeven.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "be_sharpe_0", "be_cagr_0"])
        for strat in STRATEGY_NAMES:
            r = results[strat]
            w.writerow([strat, f"{r['be_sharpe_0']:.1f}", f"{r['be_cagr_0']:.1f}"])
    return results


def _interpolate_zero(costs, values):
    """Find cost at which value crosses zero by linear interpolation."""
    for i in range(len(values) - 1):
        if values[i] >= 0 and values[i + 1] < 0:
            # Linear interpolation
            frac = values[i] / (values[i] - values[i + 1])
            return costs[i] + frac * (costs[i + 1] - costs[i])
    # Never crosses zero
    if all(v > 0 for v in values):
        return 999.0  # always positive
    if all(v <= 0 for v in values):
        return 0.0  # always negative
    return 999.0


# =========================================================================
# T2: CHURN FILTER MARGINAL VALUE
# =========================================================================

def run_t2(t0_rows):
    """Churn filter marginal value vs cost."""
    print("\nT2: Churn Filter Marginal Value")

    rows = []
    for cost_bps in COST_BPS:
        e5_row = next(r for r in t0_rows if r["strategy"] == "E5+EMA1D21" and r["cost_bps"] == cost_bps)
        x14d_row = next(r for r in t0_rows if r["strategy"] == "E5+EMA1D21+X14D" and r["cost_bps"] == cost_bps)
        x18_row = next(r for r in t0_rows if r["strategy"] == "E5+EMA1D21+X18" and r["cost_bps"] == cost_bps)

        d_sh_x14d = x14d_row["sharpe"] - e5_row["sharpe"]
        d_sh_x18 = x18_row["sharpe"] - e5_row["sharpe"]
        d_cagr_x14d = x14d_row["cagr"] - e5_row["cagr"]
        d_cagr_x18 = x18_row["cagr"] - e5_row["cagr"]

        rows.append({
            "cost_bps": cost_bps,
            "d_sharpe_x14d": d_sh_x14d, "d_sharpe_x18": d_sh_x18,
            "d_cagr_x14d": d_cagr_x14d, "d_cagr_x18": d_cagr_x18,
        })
        print(f"  {cost_bps:3d} bps: X14D Δsh={d_sh_x14d:+.4f} Δcagr={d_cagr_x14d:+.2f} | "
              f"X18 Δsh={d_sh_x18:+.4f} Δcagr={d_cagr_x18:+.2f}")

    # Write CSV
    with open(OUTDIR / "x22_churn_value.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cost_bps", "d_sharpe_x14d", "d_sharpe_x18", "d_cagr_x14d", "d_cagr_x18"])
        for r in rows:
            w.writerow([r["cost_bps"], f"{r['d_sharpe_x14d']:.4f}", f"{r['d_sharpe_x18']:.4f}",
                        f"{r['d_cagr_x14d']:.2f}", f"{r['d_cagr_x18']:.2f}"])
    return rows


# =========================================================================
# T3: STRATEGY RANKING AT REALISTIC COSTS
# =========================================================================

def run_t3(t0_rows):
    """Rank strategies at 10, 15, 20, 50 bps."""
    print("\nT3: Strategy Ranking at Realistic Costs")

    target_costs = [10, 15, 20, 50]
    rankings = {}
    for cost_bps in target_costs:
        cost_rows = [r for r in t0_rows if r["cost_bps"] == cost_bps]
        by_sharpe = sorted(cost_rows, key=lambda r: r["sharpe"], reverse=True)
        by_cagr = sorted(cost_rows, key=lambda r: r["cagr"], reverse=True)
        by_calmar = sorted(cost_rows, key=lambda r: r["calmar"], reverse=True)

        rankings[cost_bps] = {
            "by_sharpe": [r["strategy"] for r in by_sharpe],
            "by_cagr": [r["strategy"] for r in by_cagr],
            "by_calmar": [r["strategy"] for r in by_calmar],
        }
        print(f"  {cost_bps} bps — Sharpe: {' > '.join(r['strategy'] for r in by_sharpe)}")

    # Write CSV
    with open(OUTDIR / "x22_ranking.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cost_bps", "rank_metric", "rank_1", "rank_2", "rank_3", "rank_4"])
        for cost_bps in target_costs:
            for metric in ["by_sharpe", "by_cagr", "by_calmar"]:
                r = rankings[cost_bps][metric]
                w.writerow([cost_bps, metric] + r)
    return rankings


# =========================================================================
# T4: BOOTSTRAP AT 15 BPS (500 VCBB)
# =========================================================================

def run_t4(cl, hi, lo, vo, tb, ef_e0, es_e0, ef_e5, es_e5, vd,
           at_e0, at_e5, regime_h4, d1_str_h4, wi, h4_ct,
           model_w, model_mu, model_std, x14d_thresh, x18_thresh):
    """Bootstrap at 15 bps: 500 paths × 4 strategies."""
    print(f"\nT4: Bootstrap at {BOOT_CPS_BPS} bps (500 VCBB)")

    cps_boot = BOOT_CPS_BPS / 20_000.0

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

    boot_rows = []

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        n_b = len(bcl)
        breg = regime_pw[:n_b] if len(regime_pw) >= n_b else np.ones(n_b, dtype=np.bool_)
        bd1 = d1_str_pw[:n_b] if len(d1_str_pw) >= n_b else np.zeros(n_b)

        # Compute E0 and E5 indicators
        fast_p = max(5, SLOW // 4)
        bef = _ema(bcl, fast_p)
        bes = _ema(bcl, SLOW)
        bvd = _vdo(bcl, bhi, blo, bvo, btb)
        bat_e0 = _atr(bhi, blo, bcl, ATR_P)
        bat_e5 = _robust_atr(bhi, blo, bcl)

        # E0
        bnav_e0, btr_e0 = _run_sim_e0(bcl, bef, bes, bvd, bat_e0, 0, cps=cps_boot)
        bm_e0 = _metrics(bnav_e0, 0, len(btr_e0))

        # E5+EMA1D21
        bnav_e5, btr_e5 = _run_sim_e5_ema(bcl, bef, bes, bvd, bat_e5, breg, 0, cps=cps_boot)
        bm_e5 = _metrics(bnav_e5, 0, len(btr_e5))

        # E5+EMA1D21+X14D
        bnav_x14d, btr_x14d, _ = _run_sim_churn_mask(
            bcl, bhi, blo, bef, bes, bvd, bat_e5, breg, bd1, 0,
            model_w, model_mu, model_std, x14d_thresh, cps=cps_boot)
        bm_x14d = _metrics(bnav_x14d, 0, len(btr_x14d))

        # E5+EMA1D21+X18
        bnav_x18, btr_x18, _ = _run_sim_churn_mask(
            bcl, bhi, blo, bef, bes, bvd, bat_e5, breg, bd1, 0,
            model_w, model_mu, model_std, x18_thresh, cps=cps_boot)
        bm_x18 = _metrics(bnav_x18, 0, len(btr_x18))

        boot_rows.append({
            "path": b,
            "e0_sharpe": bm_e0["sharpe"], "e0_cagr": bm_e0["cagr"],
            "e5_sharpe": bm_e5["sharpe"], "e5_cagr": bm_e5["cagr"],
            "x14d_sharpe": bm_x14d["sharpe"], "x14d_cagr": bm_x14d["cagr"],
            "x18_sharpe": bm_x18["sharpe"], "x18_cagr": bm_x18["cagr"],
        })

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    # Summarize
    summary = {}
    for strat, prefix in [("E0", "e0"), ("E5+EMA1D21", "e5"),
                           ("E5+EMA1D21+X14D", "x14d"), ("E5+EMA1D21+X18", "x18")]:
        sharpes = np.array([r[f"{prefix}_sharpe"] for r in boot_rows])
        cagrs = np.array([r[f"{prefix}_cagr"] for r in boot_rows])
        summary[strat] = {
            "med_sharpe": float(np.median(sharpes)),
            "p_sharpe_gt0": float(np.mean(sharpes > 0)),
            "med_cagr": float(np.median(cagrs)),
            "p_cagr_gt0": float(np.mean(cagrs > 0)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_p95": float(np.percentile(sharpes, 95)),
        }
        print(f"  {strat:25s}: med Sh={summary[strat]['med_sharpe']:.3f}, "
              f"P(Sh>0)={summary[strat]['p_sharpe_gt0']:.1%}, "
              f"med CAGR={summary[strat]['med_cagr']:.1f}%, "
              f"P(CAGR>0)={summary[strat]['p_cagr_gt0']:.1%}")

    # Write CSV
    with open(OUTDIR / "x22_bootstrap_15bps.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "e0_sharpe", "e0_cagr", "e5_sharpe", "e5_cagr",
                     "x14d_sharpe", "x14d_cagr", "x18_sharpe", "x18_cagr"])
        for r in boot_rows:
            w.writerow([r["path"],
                        f"{r['e0_sharpe']:.4f}", f"{r['e0_cagr']:.2f}",
                        f"{r['e5_sharpe']:.4f}", f"{r['e5_cagr']:.2f}",
                        f"{r['x14d_sharpe']:.4f}", f"{r['x14d_cagr']:.2f}",
                        f"{r['x18_sharpe']:.4f}", f"{r['x18_cagr']:.2f}"])
    return summary


# =========================================================================
# T5: COST DRAG DECOMPOSITION
# =========================================================================

def run_t5(t0_rows):
    """Cost drag decomposition at 50 bps and 15 bps."""
    print("\nT5: Cost Drag Decomposition")

    rows = []
    for cost_bps in [15, 50]:
        for strat in STRATEGY_NAMES:
            r_at_cost = next(r for r in t0_rows if r["strategy"] == strat and r["cost_bps"] == cost_bps)
            r_at_zero = next(r for r in t0_rows if r["strategy"] == strat and r["cost_bps"] == 2)  # ~zero

            gross_cagr = r_at_zero["cagr"]  # approximate gross CAGR
            net_cagr = r_at_cost["cagr"]
            cost_drag_cagr = gross_cagr - net_cagr
            frac = cost_drag_cagr / gross_cagr if abs(gross_cagr) > 0.01 else 0.0

            row = {
                "strategy": strat, "cost_bps": cost_bps,
                "gross_cagr": gross_cagr, "net_cagr": net_cagr,
                "cost_drag_cagr": cost_drag_cagr,
                "drag_fraction": frac,
                "trades": r_at_cost["trades"],
                "annual_drag_bps": r_at_cost["cost_drag_bps_yr"],
            }
            rows.append(row)
            print(f"  {strat:25s} @ {cost_bps:2d} bps: gross={gross_cagr:.1f}%, "
                  f"net={net_cagr:.1f}%, drag={cost_drag_cagr:.1f}pp ({frac:.1%})")

    # Write CSV
    with open(OUTDIR / "x22_cost_decomp.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "cost_bps", "gross_cagr", "net_cagr",
                     "cost_drag_cagr", "drag_fraction", "trades", "annual_drag_bps"])
        for r in rows:
            w.writerow([r["strategy"], r["cost_bps"],
                        f"{r['gross_cagr']:.2f}", f"{r['net_cagr']:.2f}",
                        f"{r['cost_drag_cagr']:.2f}", f"{r['drag_fraction']:.4f}",
                        r["trades"], f"{r['annual_drag_bps']:.0f}"])
    return rows


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0_wall = time.time()
    print("=" * 70)
    print("X22: Cost Sensitivity Analysis — Strategy Robustness to Execution Cost")
    print("=" * 70)

    # --- Load data ---
    print("\nLoading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    n = len(cl)
    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break
    print(f"  H4 bars: {n}, D1 bars: {len(d1_cl)}, warmup: {wi} bars")

    yrs = (n - wi) / (6.0 * 365.25)
    print(f"  Post-warmup years: {yrs:.2f}")

    # --- Compute indicators ---
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb)
    at_e0 = _atr(hi, lo, cl, ATR_P)
    at_e5 = _robust_atr(hi, lo, cl)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    # --- Train churn model (cost-independent, trained on E5+EMA1D21 trades at 50 bps) ---
    print("\nTraining churn model on E5+EMA1D21 trades...")
    nav_e5_50, trades_e5_50 = _run_sim_e5_ema(cl, ef, es, vd, at_e5, regime_h4, wi, cps=CPS_50)
    m_e5_50 = _metrics(nav_e5_50, wi, len(trades_e5_50))
    print(f"  E5+EMA1D21 @ 50 bps: {len(trades_e5_50)} trades, Sh={m_e5_50['sharpe']:.4f}")

    model_w, model_mu, model_std, best_c, n_train = _train_churn_model(
        trades_e5_50, cl, hi, lo, at_e5, ef, es, vd, d1_str_h4)
    print(f"  Churn model: C={best_c}, n_train={n_train}")

    # X14D threshold: P > 0.5
    x14d_thresh = 0.5

    # X18 threshold: α-percentile of training scores
    train_scores = _compute_train_scores(
        trades_e5_50, cl, hi, lo, at_e5, ef, es, vd, d1_str_h4,
        model_w, model_mu, model_std)
    x18_thresh = float(np.percentile(train_scores, 100 - X18_ALPHA))
    print(f"  X14D threshold: {x14d_thresh:.3f}")
    print(f"  X18 threshold (α={X18_ALPHA}%): {x18_thresh:.3f}")

    results = {"config": {
        "cost_bps": COST_BPS,
        "strategies": STRATEGY_NAMES,
        "x18_alpha": X18_ALPHA,
        "x14d_thresh": x14d_thresh,
        "x18_thresh": x18_thresh,
        "boot_cps_bps": BOOT_CPS_BPS,
        "n_boot": N_BOOT,
    }}

    # === T0 ===
    t0_rows = run_t0(cl, hi, lo, ef, es, ef, es, vd, at_e0, at_e5,
                     regime_h4, d1_str_h4, wi,
                     model_w, model_mu, model_std, x14d_thresh, x18_thresh)
    results["t0_summary"] = {
        strat: {
            cost_bps: next(r for r in t0_rows if r["strategy"] == strat and r["cost_bps"] == cost_bps)
            for cost_bps in [10, 15, 20, 50]
        }
        for strat in STRATEGY_NAMES
    }

    # === T1 ===
    t1_results = run_t1(t0_rows)
    results["t1_breakeven"] = t1_results

    # === T2 ===
    t2_rows = run_t2(t0_rows)
    results["t2_churn_value"] = t2_rows

    # === T3 ===
    t3_rankings = run_t3(t0_rows)
    results["t3_rankings"] = t3_rankings

    # === T4 ===
    t4_summary = run_t4(cl, hi, lo, vo, tb, ef, es, ef, es, vd,
                        at_e0, at_e5, regime_h4, d1_str_h4, wi, h4_ct,
                        model_w, model_mu, model_std, x14d_thresh, x18_thresh)
    results["t4_bootstrap"] = t4_summary

    # === T5 ===
    t5_rows = run_t5(t0_rows)
    results["t5_decomp"] = t5_rows

    # === Write results ===
    elapsed = time.time() - t0_wall
    results["elapsed_s"] = round(elapsed, 1)

    print(f"\n{'=' * 70}")
    print(f"X22 COMPLETE — Characterization study (no gates)")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"{'=' * 70}")

    with open(OUTDIR / "x22_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults written to {OUTDIR / 'x22_results.json'}")


if __name__ == "__main__":
    main()
