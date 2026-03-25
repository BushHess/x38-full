#!/usr/bin/env python3
"""X17 Research — Percentile-Ranked Selective Exit: Nested WFO & ΔU Diagnostic

Central question: Can α-percentile thresholding + conservative grace windows
pass bootstrap where X16's τ-probability approach failed?

Key changes from X16:
  - α-percentile (rank-based) instead of τ-probability (calibration-dependent)
  - Nested WFO only (no full-sample screening)
  - Smaller grid: 60 configs (vs X16's 240)
  - Shorter G: {1,2,3,4} (vs X16's {4,6,8,12,16,20})
  - 7 market-state features only (vs X16's 10 with trade context)
  - D1 regime check during WATCH
  - ΔU diagnostic to validate ranker quality

Tests:
  T0: ΔU diagnostic (score-utility monotonicity)
  T1: Nested WFO (4 expanding folds, primary test)
  T2: Bootstrap (500 VCBB paths)
  T3: Jackknife (leave-year-out)
  T4: PSR with DOF correction
  T5: Comparison table

Gates (all must pass for PROMOTE):
  G0: T0 top 2 quintiles mean ΔU > 0
  G1: T1 WFO >= 3/4 wins, mean d_sharpe > 0
  G2: T2 P(d_sharpe > 0) > 0.60
  G3: T2 median d_mdd <= +5.0 pp
  G4: T3 <= 2 negative jackknife folds
  G5: T4 PSR > 0.95
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import Counter
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

CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0

CHURN_WINDOW = 20

# Grids (conservative, per external guidance)
ALPHA_GRID = [5, 10, 15, 20, 25]      # suppression budget (%)
G_GRID = [1, 2, 3, 4]                 # grace window (H4 bars)
DELTA_GRID = [0.5, 1.0, 1.5]          # deeper stop addon (ATR multiples)

# Logistic model
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]

FEATURE_NAMES_7 = [
    "ema_ratio", "atr_pctl", "bar_range_atr", "close_position",
    "vdo_at_exit", "d1_regime_str", "trail_tightness",
]

# WFO fold boundaries
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
# FAST INDICATORS (identical to X14/X16)
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
# STATISTICAL UTILITIES
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


def _psr(sharpe, n_returns, sr0=0.0):
    from scipy.stats import norm
    if n_returns < 3:
        return 0.5
    se = 1.0 / math.sqrt(n_returns)
    z = (sharpe - sr0) / se if se > 1e-12 else 0.0
    return float(norm.cdf(z))


# =========================================================================
# CHURN LABELING & 7-FEATURE EXTRACTION
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


def _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                          trail_mult=TRAIL):
    """Extract 7 market-state features at bar i (no trade context)."""
    f1 = ef[i] / es[i] if abs(es[i]) > 1e-12 else 1.0  # ema_ratio
    atr_start = max(0, i - 99)
    atr_window = at[atr_start:i + 1]
    valid_atr = atr_window[~np.isnan(atr_window)]
    f2 = float(np.sum(valid_atr <= at[i])) / len(valid_atr) if len(valid_atr) > 1 else 0.5  # atr_pctl
    f3 = (hi[i] - lo[i]) / at[i] if at[i] > 1e-12 else 1.0  # bar_range_atr
    bar_w = hi[i] - lo[i]
    f4 = (cl[i] - lo[i]) / bar_w if bar_w > 1e-12 else 0.5  # close_position
    f5 = float(vd[i])  # vdo_at_exit
    f6 = float(d1_str_h4[i])  # d1_regime_str
    f7 = trail_mult * at[i] / cl[i] if cl[i] > 1e-12 else 0.0  # trail_tightness
    return np.array([f1, f2, f3, f4, f5, f6, f7])


def _extract_features_from_trades_7(trades, cl, hi, lo, at, ef, es, vd,
                                      d1_str_h4, trail_mult=TRAIL):
    """Extract 7 features at each trail stop exit."""
    n = len(cl)
    churn_labels = _label_churn(trades)
    features = []
    labels = []
    for trade_idx, label in churn_labels:
        t = trades[trade_idx]
        sb = t["exit_bar"] - 1  # bar before execution
        if sb < 0 or sb >= n:
            continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd,
                                    d1_str_h4, trail_mult)
        features.append(feat)
        labels.append(label)
    if not features:
        return np.empty((0, 7)), np.empty(0, dtype=int)
    return np.array(features), np.array(labels, dtype=int)


def _train_model_7(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                     trail_mult=TRAIL, fixed_c=None):
    """Train L2-penalized logistic on 7 market-state features."""
    X, y = _extract_features_from_trades_7(trades, cl, hi, lo, at, ef, es, vd,
                                            d1_str_h4, trail_mult)
    if len(y) < 10 or len(np.unique(y)) < 2:
        return None, None, None, None, 0
    Xs, mu, std = _standardize(X)
    if fixed_c is not None:
        best_c = fixed_c
    else:
        best_c, best_auc = 1.0, 0.0
        for c_val in C_VALUES:
            auc_c = _kfold_auc(Xs, y, C=c_val, k=5)
            if auc_c > best_auc:
                best_auc = auc_c
                best_c = c_val
    w = _fit_logistic_l2(Xs, y, C=best_c)
    return w, mu, std, best_c, len(y)


def _predict_score(feat, w, mu, std):
    """Predict P(churn) from a single feature vector."""
    feat_s = (feat - mu) / std
    z = np.dot(np.append(feat_s, 1.0), w)
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))


def _compute_train_scores(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                            model_w, model_mu, model_std, trail_mult=TRAIL):
    """Compute P(churn) scores for all trail-stop exits."""
    n = len(cl)
    scores = []
    for t in trades:
        if t.get("exit_reason") != "trail_stop":
            continue
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n:
            continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd,
                                    d1_str_h4, trail_mult)
        score = _predict_score(feat, model_w, model_mu, model_std)
        scores.append(score)
    return np.array(scores)


# =========================================================================
# SIM CORE — E0 baseline (no filter)
# =========================================================================

def _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH):
    """Plain E0+EMA1D21 sim."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    pk_bar = 0
    entry_bar = 0
    entry_px = 0.0
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
                pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret_pct,
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
        ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
        })

    stats = {"n_trail_stops": sum(1 for t in trades if t["exit_reason"] == "trail_stop"),
             "n_trend_exits": sum(1 for t in trades if t["exit_reason"] == "trend_exit")}
    return nav, trades, stats


# =========================================================================
# SIM CORE — WATCH state machine (α-percentile threshold)
# =========================================================================

_FLAT = 0
_LONG_NORMAL = 1
_LONG_WATCH = 2


def _run_sim_watch(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                    G, delta, model_w, model_mu, model_std,
                    alpha_threshold=0.5,
                    trail_mult=TRAIL, cps=CPS_HARSH):
    """WATCH state machine with α-percentile threshold.

    At first trail breach:
      - Compute 7-feature score
      - If score > alpha_threshold AND trend positive AND regime on → WATCH(G,δ)
      - Else: exit immediately

    During WATCH:
      - Reclaim (back above original trail) → LONG_NORMAL
      - Deeper stop (peak - (trail+δ)×ATR) → exit
      - Timeout (G bars) → exit
      - Trend reversal (ema_f < ema_s) → exit
      - Regime off → exit
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    state = _FLAT
    pe = px = False
    nt = 0
    pk = 0.0
    pk_bar = 0
    entry_bar = 0
    entry_px = 0.0
    entry_cost = 0.0
    exit_reason = ""

    # WATCH state vars
    watch_start = 0
    original_trail = 0.0

    n_watch_entered = 0
    n_watch_reclaimed = 0
    n_watch_deeper = 0
    n_watch_timeout = 0
    n_watch_trend_exit = 0
    n_watch_regime_exit = 0
    n_trail_direct = 0

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
                state = _LONG_NORMAL
                pk = p
                pk_bar = i
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "peak_bar": pk_bar,
                    "pnl_usd": pnl, "ret_pct": ret_pct,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason,
                })
                cash = received
                bq = 0.0
                state = _FLAT
                pk = 0.0
                nt += 1

        nav[i] = cash + bq * p
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if state == _FLAT:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True

        elif state == _LONG_NORMAL:
            pk = max(pk, p)
            if p >= pk:
                pk_bar = i
            ts = pk - trail_mult * a_val
            if p < ts:
                # First breach: query model ONCE
                should_watch = False
                if model_w is not None and ef[i] > es[i] and regime_h4[i]:
                    feat = _extract_features_7(
                        i, cl, hi, lo, at, ef, es, vd, d1_str_h4, trail_mult)
                    score = _predict_score(feat, model_w, model_mu, model_std)
                    should_watch = score > alpha_threshold

                if should_watch:
                    state = _LONG_WATCH
                    watch_start = i
                    original_trail = ts
                    n_watch_entered += 1
                else:
                    exit_reason = "trail_stop"
                    px = True
                    n_trail_direct += 1

            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

        elif state == _LONG_WATCH:
            pk = max(pk, p)
            if p >= pk:
                pk_bar = i
            deeper_stop = pk - (trail_mult + delta) * a_val

            if p > original_trail:
                # Reclaim: back to normal
                state = _LONG_NORMAL
                n_watch_reclaimed += 1
            elif p < deeper_stop:
                exit_reason = "deeper_stop"
                px = True
                n_watch_deeper += 1
            elif (i - watch_start) >= G:
                exit_reason = "watch_timeout"
                px = True
                n_watch_timeout += 1
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True
                n_watch_trend_exit += 1
            elif not regime_h4[i]:
                exit_reason = "regime_exit"
                px = True
                n_watch_regime_exit += 1

    if state != _FLAT and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
        })

    stats = {
        "n_watch_entered": n_watch_entered,
        "n_watch_reclaimed": n_watch_reclaimed,
        "n_watch_deeper": n_watch_deeper,
        "n_watch_timeout": n_watch_timeout,
        "n_watch_trend_exit": n_watch_trend_exit,
        "n_watch_regime_exit": n_watch_regime_exit,
        "n_trail_direct": n_trail_direct,
    }
    return nav, trades, stats


# =========================================================================
# PER-EPISODE ΔU COMPUTATION
# =========================================================================

def _compute_episode_delta_u(signal_bar, peak_px, cl, hi, lo, at, ef, es,
                               regime_h4, G, delta, trail_mult=TRAIL):
    """Compute ΔU for a single trail-stop episode under WATCH(G,δ).

    signal_bar: bar where trail fires (= trade exit_bar - 1)
    peak_px: peak price during this trade
    ΔU = log(watch_exit_price / exit_now_price)
    Positive means WATCH would have been better than immediate exit.
    """
    n = len(cl)
    i = signal_bar
    exit_now_px = cl[i]

    # Actual trail and deeper stop levels (matching the sim)
    a_val = at[i] if not math.isnan(at[i]) else 0.0
    original_trail = peak_px - trail_mult * a_val
    deeper_stop = peak_px - (trail_mult + delta) * a_val

    watch_exit_px = None
    watch_exit_reason = None

    for j in range(i + 1, min(i + G + 1, n)):
        p = cl[j]
        # Check reclaim (back above original trail)
        if p > original_trail:
            watch_exit_px = p
            watch_exit_reason = "reclaim"
            break
        # Check deeper stop
        if p < deeper_stop:
            watch_exit_px = p
            watch_exit_reason = "deeper_stop"
            break
        # Check trend reversal
        if j < len(ef) and ef[j] < es[j]:
            watch_exit_px = p
            watch_exit_reason = "trend_exit"
            break
        # Check regime
        if j < len(regime_h4) and not regime_h4[j]:
            watch_exit_px = p
            watch_exit_reason = "regime_exit"
            break

    if watch_exit_px is None:
        # Timeout
        j = min(i + G, n - 1)
        watch_exit_px = cl[j]
        watch_exit_reason = "timeout"

    if exit_now_px > 0 and watch_exit_px > 0:
        delta_u = math.log(watch_exit_px / exit_now_px)
    else:
        delta_u = 0.0

    return delta_u, watch_exit_reason


# =========================================================================
# T0: ΔU DIAGNOSTIC
# =========================================================================

def run_t0_delta_u(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                    model_w, model_mu, model_std, trades_e0):
    """T0: Per-episode ΔU diagnostic to validate ranker quality."""
    print("\n" + "=" * 70)
    print("T0: ΔU DIAGNOSTIC (score-utility monotonicity)")
    print("=" * 70)

    # Get trail-stop episodes and their scores
    n = len(cl)
    episodes = []
    for t in trades_e0:
        if t["exit_reason"] != "trail_stop":
            continue
        sb = t["exit_bar"] - 1  # signal bar (bar where trail fires)
        if sb < 0 or sb >= n:
            continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd,
                                    d1_str_h4, TRAIL)
        score = _predict_score(feat, model_w, model_mu, model_std)
        episodes.append({"signal_bar": sb, "score": score,
                          "entry_bar": t["entry_bar"],
                          "peak_px": t["peak_px"]})

    n_ep = len(episodes)
    print(f"  Trail-stop episodes with scores: {n_ep}")

    if n_ep < 10:
        print("  Too few episodes for ΔU diagnostic")
        return {"go": False, "reason": "too_few_episodes"}

    # Compute ΔU for each (G, δ) combination
    best_gd = None
    best_monotonicity = -999
    all_rows = []

    for G in G_GRID:
        for delta in DELTA_GRID:
            delta_us = []
            for ep in episodes:
                du, reason = _compute_episode_delta_u(
                    ep["signal_bar"], ep["peak_px"],
                    cl, hi, lo, at, ef, es, regime_h4, G, delta)
                delta_us.append(du)

            # Sort by score, compute quintiles
            scored = sorted(zip([ep["score"] for ep in episodes], delta_us),
                             key=lambda x: x[0])
            q_size = n_ep // 5
            quintile_stats = []
            for q in range(5):
                s = q * q_size
                e = s + q_size if q < 4 else n_ep
                q_dus = [x[1] for x in scored[s:e]]
                quintile_stats.append({
                    "quintile": q + 1,
                    "n": len(q_dus),
                    "mean_du": float(np.mean(q_dus)),
                    "median_du": float(np.median(q_dus)),
                    "p10_du": float(np.percentile(q_dus, 10)),
                })

            # Monotonicity: top 2 quintiles have median ΔU > 0
            top2_positive = (quintile_stats[3]["median_du"] > 0 and
                              quintile_stats[4]["median_du"] > 0)
            # Score: sum of quintile medians (higher = better monotonicity)
            mono_score = sum(q["median_du"] * (q["quintile"] - 3) for q in quintile_stats)

            all_rows.append({
                "G": G, "delta": delta,
                "top2_positive": top2_positive,
                "mono_score": mono_score,
                "quintiles": quintile_stats,
                "overall_mean_du": float(np.mean(delta_us)),
                "overall_median_du": float(np.median(delta_us)),
            })

            if mono_score > best_monotonicity:
                best_monotonicity = mono_score
                best_gd = (G, delta)

    # Report best (G, δ)
    best_row = [r for r in all_rows if (r["G"], r["delta"]) == best_gd][0]
    print(f"\n  Best (G,δ) for monotonicity: G={best_gd[0]}, δ={best_gd[1]}")
    print(f"  Overall mean ΔU: {best_row['overall_mean_du']:+.6f}")
    print(f"  Quintile breakdown (sorted by score, low→high):")
    for q in best_row["quintiles"]:
        print(f"    Q{q['quintile']} (n={q['n']}): mean={q['mean_du']:+.6f}, "
              f"median={q['median_du']:+.6f}, p10={q['p10_du']:+.6f}")

    g0_pass = best_row["top2_positive"]
    print(f"\n  G0: {'PASS' if g0_pass else 'FAIL'} "
          f"(top 2 quintiles median ΔU > 0: "
          f"Q4={best_row['quintiles'][3]['median_du']:+.6f}, "
          f"Q5={best_row['quintiles'][4]['median_du']:+.6f})")

    return {
        "n_episodes": n_ep,
        "best_G": best_gd[0], "best_delta": best_gd[1],
        "best_mono_score": best_monotonicity,
        "g0_pass": g0_pass,
        "best_quintiles": best_row["quintiles"],
        "overall_mean_du": best_row["overall_mean_du"],
        "all_rows": [{k: v for k, v in r.items() if k != "quintiles"}
                      for r in all_rows],
    }


# =========================================================================
# T1: NESTED WALK-FORWARD VALIDATION
# =========================================================================

def run_t1_nested_wfo(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                       wi, h4_ct):
    """T1: 4-fold expanding WFO with per-fold param sweep."""
    print("\n" + "=" * 70)
    print("T1: NESTED WALK-FORWARD VALIDATION (4 folds)")
    print("=" * 70)

    folds_cfg = []
    for train_end_str, test_start_str, test_end_str in WFO_FOLDS:
        train_end = _date_to_bar_idx(h4_ct, train_end_str)
        test_start = _date_to_bar_idx(h4_ct, test_start_str)
        test_end = _date_to_bar_idx(h4_ct, test_end_str)
        folds_cfg.append((train_end, test_start, test_end))

    fold_results = []

    for fold_idx, (train_end, test_start, test_end) in enumerate(folds_cfg):
        # E0 baseline
        nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
        test_trades_e0 = [t for t in trades_e0 if test_start <= t["entry_bar"] < test_end]
        m_e0_test = _metrics_window(nav_e0, test_start, test_end + 1, len(test_trades_e0))

        # Train model on training portion
        nav_tr, trades_tr, _ = _run_sim_e0(
            cl[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], at[:train_end + 1], regime_h4[:train_end + 1], wi)
        w, mu, std, best_c, n_samp = _train_model_7(
            trades_tr, cl[:train_end + 1], hi[:train_end + 1], lo[:train_end + 1],
            at[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], d1_str_h4[:train_end + 1])

        if w is None:
            fold_results.append({
                "fold": fold_idx + 1, "param": "no_model",
                "e0_sharpe_test": m_e0_test["sharpe"],
                "filter_sharpe_test": m_e0_test["sharpe"],
                "d_sharpe": 0.0, "win": False,
                "best_alpha": ALPHA_GRID[0], "best_G": G_GRID[0],
                "best_delta": DELTA_GRID[0],
            })
            continue

        # Compute training scores for α-threshold
        train_scores = _compute_train_scores(
            trades_tr, cl[:train_end + 1], hi[:train_end + 1], lo[:train_end + 1],
            at[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], d1_str_h4[:train_end + 1],
            w, mu, std)

        if len(train_scores) < 5:
            fold_results.append({
                "fold": fold_idx + 1, "param": "few_scores",
                "e0_sharpe_test": m_e0_test["sharpe"],
                "filter_sharpe_test": m_e0_test["sharpe"],
                "d_sharpe": 0.0, "win": False,
                "best_alpha": ALPHA_GRID[0], "best_G": G_GRID[0],
                "best_delta": DELTA_GRID[0],
            })
            continue

        # Sweep (α, G, δ) on training data
        best_params = {"alpha": ALPHA_GRID[0], "G": G_GRID[0],
                        "delta": DELTA_GRID[0], "alpha_threshold": 0.5}
        best_train_sh = -999

        for alpha in ALPHA_GRID:
            alpha_thresh = float(np.percentile(train_scores, 100 - alpha))
            for G in G_GRID:
                for delta in DELTA_GRID:
                    nav_w, _, _ = _run_sim_watch(
                        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                        G=G, delta=delta, model_w=w, model_mu=mu, model_std=std,
                        alpha_threshold=alpha_thresh)
                    m_train = _metrics_window(nav_w, wi, train_end + 1)
                    if m_train["sharpe"] > best_train_sh:
                        best_train_sh = m_train["sharpe"]
                        best_params = {"alpha": alpha, "G": G, "delta": delta,
                                        "alpha_threshold": alpha_thresh}

        # Run with best params on full data, measure test
        nav_w, trades_w, stats_w = _run_sim_watch(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            G=best_params["G"], delta=best_params["delta"],
            model_w=w, model_mu=mu, model_std=std,
            alpha_threshold=best_params["alpha_threshold"])
        test_trades_w = [t for t in trades_w if test_start <= t["entry_bar"] < test_end]
        m_w_test = _metrics_window(nav_w, test_start, test_end + 1, len(test_trades_w))

        d_sharpe = m_w_test["sharpe"] - m_e0_test["sharpe"]
        win = d_sharpe > 0

        fold_results.append({
            "fold": fold_idx + 1,
            "param": f"α={best_params['alpha']}%,G={best_params['G']},δ={best_params['delta']}",
            "e0_sharpe_test": m_e0_test["sharpe"],
            "filter_sharpe_test": m_w_test["sharpe"],
            "d_sharpe": d_sharpe, "win": win,
            "best_alpha": best_params["alpha"],
            "best_G": best_params["G"],
            "best_delta": best_params["delta"],
            "C": best_c, "n_train_scores": len(train_scores),
            "watch_stats": stats_w,
        })
        print(f"    Fold {fold_idx + 1}: α={best_params['alpha']}% G={best_params['G']} "
              f"δ={best_params['delta']}, E0={m_e0_test['sharpe']:.4f}, "
              f"Filt={m_w_test['sharpe']:.4f}, d={d_sharpe:+.4f} "
              f"{'WIN' if win else 'LOSE'}")

    if not fold_results:
        return {"folds": [], "win_rate": 0.0, "mean_d_sharpe": 0.0,
                "g1_pass": False, "consensus": {}}

    win_rate = sum(1 for f in fold_results if f["win"]) / len(fold_results)
    mean_d = float(np.mean([f["d_sharpe"] for f in fold_results]))
    g1_pass = win_rate >= 0.75 and mean_d > 0

    # Consensus params (mode across folds)
    alphas = [f["best_alpha"] for f in fold_results]
    gs = [f["best_G"] for f in fold_results]
    deltas = [f["best_delta"] for f in fold_results]

    def _mode_with_tiebreak(values, d_sharpes):
        counts = Counter(values)
        max_count = max(counts.values())
        candidates = [v for v, c in counts.items() if c == max_count]
        if len(candidates) == 1:
            return candidates[0]
        # Tiebreak: pick value from fold with highest d_sharpe
        best_idx = int(np.argmax(d_sharpes))
        return values[best_idx]

    d_sharpes = [f["d_sharpe"] for f in fold_results]
    consensus = {
        "alpha": _mode_with_tiebreak(alphas, d_sharpes),
        "G": _mode_with_tiebreak(gs, d_sharpes),
        "delta": _mode_with_tiebreak(deltas, d_sharpes),
    }

    print(f"\n  Win rate: {win_rate:.0%}, mean d_sharpe: {mean_d:+.4f}, "
          f"G1: {'PASS' if g1_pass else 'FAIL'}")
    print(f"  Consensus: α={consensus['alpha']}%, G={consensus['G']}, "
          f"δ={consensus['delta']}")

    return {"folds": fold_results, "win_rate": win_rate,
            "mean_d_sharpe": mean_d, "g1_pass": g1_pass,
            "consensus": consensus}


# =========================================================================
# T2: BOOTSTRAP VALIDATION
# =========================================================================

def run_t2_bootstrap(cl, hi, lo, vo, tb, ef, es, vd, at,
                      regime_h4, d1_str_h4, wi, consensus,
                      model_w_full, model_mu_full, model_std_full):
    """T2: 500 VCBB bootstrap with consensus params."""
    print("\n" + "=" * 70)
    print(f"T2: BOOTSTRAP VALIDATION ({N_BOOT} paths)")
    print("=" * 70)

    alpha = consensus["alpha"]
    G = consensus["G"]
    delta = consensus["delta"]

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

    d_sharpes, d_cagrs, d_mdds = [], [], []

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
        bnav_tr, btrades_tr, _ = _run_sim_e0(
            bcl[:train_end_b], bef[:train_end_b], bes[:train_end_b],
            bvd[:train_end_b], bat[:train_end_b], breg[:train_end_b], bwi)
        bw, bmu, bstd, _, _ = _train_model_7(
            btrades_tr, bcl[:train_end_b], bhi[:train_end_b], blo[:train_end_b],
            bat[:train_end_b], bef[:train_end_b], bes[:train_end_b],
            bvd[:train_end_b], bd1_str[:train_end_b])

        if bw is None:
            bw, bmu, bstd = model_w_full, model_mu_full, model_std_full

        # Compute α-threshold from training scores
        b_train_scores = _compute_train_scores(
            btrades_tr, bcl[:train_end_b], bhi[:train_end_b], blo[:train_end_b],
            bat[:train_end_b], bef[:train_end_b], bes[:train_end_b],
            bvd[:train_end_b], bd1_str[:train_end_b],
            bw, bmu, bstd)
        if len(b_train_scores) >= 3:
            b_alpha_thresh = float(np.percentile(b_train_scores, 100 - alpha))
        else:
            b_alpha_thresh = 0.5  # fallback

        # WATCH sim
        bnav_w, btrades_w, _ = _run_sim_watch(
            bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1_str, bwi,
            G=G, delta=delta, model_w=bw, model_mu=bmu, model_std=bstd,
            alpha_threshold=b_alpha_thresh)
        bm_w = _metrics(bnav_w, bwi, len(btrades_w))

        d_sharpes.append(bm_w["sharpe"] - bm_e0["sharpe"])
        d_cagrs.append(bm_w["cagr"] - bm_e0["cagr"])
        d_mdds.append(bm_w["mdd"] - bm_e0["mdd"])

        if (b_idx + 1) % 100 == 0:
            print(f"    ... {b_idx + 1}/{N_BOOT} paths done")

    d_sharpes = np.array(d_sharpes)
    d_cagrs = np.array(d_cagrs)
    d_mdds = np.array(d_mdds)

    p_dsharpe_gt0 = float(np.mean(d_sharpes > 0))
    med_d_mdd = float(np.median(d_mdds))
    g2_pass = p_dsharpe_gt0 > 0.60
    g3_pass = med_d_mdd <= 5.0

    results = {
        "consensus": consensus,
        "d_sharpe_median": float(np.median(d_sharpes)),
        "d_sharpe_p5": float(np.percentile(d_sharpes, 5)),
        "d_sharpe_p95": float(np.percentile(d_sharpes, 95)),
        "d_sharpe_mean": float(np.mean(d_sharpes)),
        "p_d_sharpe_gt0": p_dsharpe_gt0,
        "d_cagr_median": float(np.median(d_cagrs)),
        "d_mdd_median": med_d_mdd,
        "d_mdd_p5": float(np.percentile(d_mdds, 5)),
        "d_mdd_p95": float(np.percentile(d_mdds, 95)),
        "g2_pass": g2_pass,
        "g3_pass": g3_pass,
    }

    print(f"\n  d_sharpe: median={results['d_sharpe_median']:+.4f}, "
          f"[{results['d_sharpe_p5']:+.4f}, {results['d_sharpe_p95']:+.4f}]")
    print(f"  P(d_sharpe > 0): {p_dsharpe_gt0:.1%}")
    print(f"  d_mdd: median={med_d_mdd:+.2f}pp")
    print(f"  G2: {'PASS' if g2_pass else 'FAIL'}, G3: {'PASS' if g3_pass else 'FAIL'}")

    return results, d_sharpes, d_cagrs, d_mdds


# =========================================================================
# T3: JACKKNIFE
# =========================================================================

def run_t3_jackknife(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                      wi, h4_ct, consensus,
                      model_w, model_mu, model_std, train_scores_full):
    """T3: Leave-year-out jackknife."""
    print("\n" + "=" * 70)
    print("T3: JACKKNIFE (leave-year-out)")
    print("=" * 70)

    alpha = consensus["alpha"]
    G = consensus["G"]
    delta = consensus["delta"]
    alpha_thresh = float(np.percentile(train_scores_full, 100 - alpha))

    n = len(cl)
    fold_results = []

    for yr in JK_YEARS:
        yr_start = _date_to_bar_idx(h4_ct, f"{yr}-01-01")
        yr_end = _date_to_bar_idx(h4_ct, f"{yr}-12-31")
        yr_end = min(yr_end, n - 1)

        kept = np.concatenate([np.arange(wi, yr_start), np.arange(yr_end + 1, n)]) \
            if yr_start > wi else np.arange(yr_end + 1, n)
        if len(kept) < 2:
            continue

        # E0
        nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
        trades_e0_jk = [t for t in trades_e0 if not (yr_start <= t["entry_bar"] <= yr_end)]
        m_e0_jk = _metrics(nav_e0[kept], 0, len(trades_e0_jk))

        # WATCH
        nav_w, trades_w, _ = _run_sim_watch(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            G=G, delta=delta, model_w=model_w, model_mu=model_mu, model_std=model_std,
            alpha_threshold=alpha_thresh)
        trades_w_jk = [t for t in trades_w if not (yr_start <= t["entry_bar"] <= yr_end)]
        m_w_jk = _metrics(nav_w[kept], 0, len(trades_w_jk))

        d_sh = m_w_jk["sharpe"] - m_e0_jk["sharpe"]
        fold_results.append({
            "year": yr, "e0_sharpe": m_e0_jk["sharpe"],
            "filter_sharpe": m_w_jk["sharpe"], "d_sharpe": d_sh,
            "d_sharpe_negative": d_sh < 0,
        })
        print(f"    Drop {yr}: E0={m_e0_jk['sharpe']:.4f}, "
              f"Filt={m_w_jk['sharpe']:.4f}, d={d_sh:+.4f}")

    n_neg = sum(1 for f in fold_results if f["d_sharpe_negative"])
    mean_d = float(np.mean([f["d_sharpe"] for f in fold_results])) if fold_results else 0.0
    g4_pass = n_neg <= 2

    print(f"  Negative: {n_neg}/6, mean d={mean_d:+.4f}, "
          f"G4: {'PASS' if g4_pass else 'FAIL'}")

    return {"folds": fold_results, "n_negative": n_neg,
            "mean_d_sharpe": mean_d, "g4_pass": g4_pass}


# =========================================================================
# T4: PSR
# =========================================================================

def run_t4_psr(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                consensus, model_w, model_mu, model_std, train_scores_full):
    """T4: PSR with DOF correction."""
    print("\n" + "=" * 70)
    print("T4: PSR")
    print("=" * 70)

    alpha = consensus["alpha"]
    G = consensus["G"]
    delta = consensus["delta"]
    alpha_thresh = float(np.percentile(train_scores_full, 100 - alpha))

    nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))
    n_returns = len(nav_e0[wi:]) - 1

    # DOF: E0 base (4.35) + 3 new params (α, G, δ)
    extra_dof = 3
    effective_dof = E0_EFFECTIVE_DOF + extra_dof

    psr_e0 = _psr(m_e0["sharpe"], n_returns)

    nav_w, trades_w, _ = _run_sim_watch(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        G=G, delta=delta, model_w=model_w, model_mu=model_mu, model_std=model_std,
        alpha_threshold=alpha_thresh)
    m_w = _metrics(nav_w, wi, len(trades_w))
    n_eff = max(3, int(n_returns / (effective_dof / E0_EFFECTIVE_DOF)))
    psr_w = _psr(m_w["sharpe"], n_eff)
    g5_pass = psr_w > 0.95

    results = {
        "e0_sharpe": m_e0["sharpe"], "filter_sharpe": m_w["sharpe"],
        "e0_psr": psr_e0, "filter_psr": psr_w,
        "effective_dof": effective_dof, "extra_dof": extra_dof,
        "n_returns": n_returns, "n_eff": n_eff, "g5_pass": g5_pass,
    }

    print(f"  E0: Sharpe={m_e0['sharpe']:.4f}, PSR={psr_e0:.4f}")
    print(f"  Filter: Sharpe={m_w['sharpe']:.4f}, PSR={psr_w:.4f}")
    print(f"  DOF={effective_dof:.2f}, n_eff={n_eff}, "
          f"G5: {'PASS' if g5_pass else 'FAIL'}")

    return results


# =========================================================================
# T5: COMPARISON TABLE
# =========================================================================

def run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                       consensus, m_e0, model_w, model_mu, model_std,
                       train_scores_full):
    """T5: Side-by-side comparison."""
    print("\n" + "=" * 70)
    print("T5: COMPARISON TABLE")
    print("=" * 70)

    alpha = consensus["alpha"]
    G = consensus["G"]
    delta = consensus["delta"]
    alpha_thresh = float(np.percentile(train_scores_full, 100 - alpha))

    # E0
    nav_e0, trades_e0, _ = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    avg_hold_e0 = float(np.mean([t["bars_held"] for t in trades_e0])) if trades_e0 else 0.0

    # X17 WATCH
    nav_w, trades_w, stats_w = _run_sim_watch(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        G=G, delta=delta, model_w=model_w, model_mu=model_mu, model_std=model_std,
        alpha_threshold=alpha_thresh)
    m_w = _metrics(nav_w, wi, len(trades_w))
    avg_hold_w = float(np.mean([t["bars_held"] for t in trades_w])) if trades_w else 0.0
    oracle_capture = ((m_w["sharpe"] - m_e0["sharpe"]) / 0.845 * 100
                      if m_w["sharpe"] > m_e0["sharpe"] else 0.0)

    table = [
        {"strategy": "E0", **m_e0, "avg_hold": avg_hold_e0, "oracle_capture": 0.0},
        {"strategy": f"X17_WATCH(α={alpha}%,G={G},δ={delta})",
         **m_w, "avg_hold": avg_hold_w, "oracle_capture": oracle_capture},
        {"strategy": "X14_D", "sharpe": 1.428, "cagr": 64.0, "mdd": 36.7,
         "trades": 133, "avg_hold": 60.3, "oracle_capture": 10.9},
        {"strategy": "X16_E", "sharpe": 1.424, "cagr": 62.7, "mdd": 38.9,
         "trades": 162, "avg_hold": 48.7, "oracle_capture": 10.4},
    ]

    print(f"\n  {'Strategy':<35} {'Sharpe':>8} {'CAGR%':>8} {'MDD%':>8} "
          f"{'Trades':>7} {'AvgHold':>8} {'Oracle%':>8}")
    print("  " + "-" * 86)
    for row in table:
        print(f"  {row['strategy']:<35} {row['sharpe']:>8.4f} {row['cagr']:>8.2f} "
              f"{row['mdd']:>8.2f} {row['trades']:>7} {row['avg_hold']:>8.1f} "
              f"{row['oracle_capture']:>8.1f}")

    return table, stats_w


# =========================================================================
# SAVE RESULTS
# =========================================================================

def save_results(all_results):
    """Save all results to JSON and CSV."""

    # Main JSON (strip numpy arrays)
    def _clean(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_clean(x) for x in obj]
        return obj

    with open(OUTDIR / "x17_results.json", "w") as f:
        json.dump(_clean(all_results), f, indent=2)

    # T0 ΔU CSV
    if "t0" in all_results and all_results["t0"].get("best_quintiles"):
        with open(OUTDIR / "x17_delta_u.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["quintile", "n", "mean_du", "median_du", "p10_du",
                         "best_G", "best_delta"])
            for q in all_results["t0"]["best_quintiles"]:
                w.writerow([q["quintile"], q["n"],
                            f"{q['mean_du']:.6f}", f"{q['median_du']:.6f}",
                            f"{q['p10_du']:.6f}",
                            all_results["t0"]["best_G"],
                            all_results["t0"]["best_delta"]])

    # T1 WFO CSV
    if "t1" in all_results and all_results["t1"].get("folds"):
        with open(OUTDIR / "x17_wfo.csv", "w", newline="") as f:
            fields = ["fold", "param", "e0_sharpe_test", "filter_sharpe_test",
                       "d_sharpe", "win", "best_alpha", "best_G", "best_delta"]
            w_csv = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w_csv.writeheader()
            for row in all_results["t1"]["folds"]:
                w_csv.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                                 for k, v in row.items() if k in fields})

    # T2 bootstrap CSV
    if "t2_arrays" in all_results and all_results["t2_arrays"] is not None:
        d_sh, d_ca, d_md = all_results["t2_arrays"]
        with open(OUTDIR / "x17_bootstrap.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "d_sharpe", "d_cagr", "d_mdd"])
            for i in range(len(d_sh)):
                w.writerow([i, f"{d_sh[i]:.6f}", f"{d_ca[i]:.6f}", f"{d_md[i]:.6f}"])

    # T3 jackknife CSV
    if "t3" in all_results and all_results["t3"].get("folds"):
        with open(OUTDIR / "x17_jackknife.csv", "w", newline="") as f:
            fields = list(all_results["t3"]["folds"][0].keys())
            w_csv = csv.DictWriter(f, fieldnames=fields)
            w_csv.writeheader()
            for row in all_results["t3"]["folds"]:
                w_csv.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                                 for k, v in row.items()})

    # T5 comparison CSV
    if "t5" in all_results and all_results["t5"]:
        with open(OUTDIR / "x17_comparison.csv", "w", newline="") as f:
            fields = list(all_results["t5"][0].keys())
            w_csv = csv.DictWriter(f, fieldnames=fields)
            w_csv.writeheader()
            for row in all_results["t5"]:
                w_csv.writerow({k: f"{v:.6f}" if isinstance(v, float) else v
                                 for k, v in row.items()})

    print(f"\n  Saved to {OUTDIR}/x17_*.{{json,csv}}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("X17: Percentile-Ranked Selective Exit — Nested WFO & ΔU Diagnostic")
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

    ef, es, vd, at = _compute_indicators(cl, hi, lo, vo, tb)

    all_results = {}

    # ===== E0 baseline =====
    nav_e0, trades_e0, stats_e0 = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))
    print(f"  E0: Sharpe={m_e0['sharpe']:.4f}, CAGR={m_e0['cagr']:.2f}%, "
          f"MDD={m_e0['mdd']:.2f}%, trades={m_e0['trades']}")
    all_results["e0_baseline"] = m_e0

    # ===== Train model on full data (for T0 ΔU diagnostic) =====
    print("\n  Training 7-feature logistic model on E0 trail stops...")
    model_w, model_mu, model_std, model_c, n_train = _train_model_7(
        trades_e0, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    print(f"  Model: C={model_c}, n_samples={n_train}, "
          f"{'OK' if model_w is not None else 'FAILED'}")

    if model_w is None:
        print("\n  Model training failed — ABORT")
        all_results["verdict"] = {"verdict": "ABORT", "reason": "model_training_failed"}
        save_results(all_results)
        return

    # Compute full-data training scores
    train_scores_full = _compute_train_scores(
        trades_e0, cl, hi, lo, at, ef, es, vd, d1_str_h4,
        model_w, model_mu, model_std)
    print(f"  Training scores: n={len(train_scores_full)}, "
          f"median={float(np.median(train_scores_full)):.4f}, "
          f"[p5={float(np.percentile(train_scores_full, 5)):.4f}, "
          f"p95={float(np.percentile(train_scores_full, 95)):.4f}]")

    # ===== T0: ΔU Diagnostic =====
    t0 = run_t0_delta_u(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                          model_w, model_mu, model_std, trades_e0)
    all_results["t0"] = t0

    if not t0["g0_pass"]:
        print("\n  T0 FAILED — ranker doesn't sort by utility. ABORT.")
        all_results["verdict"] = {"verdict": "ABORT",
                                   "reason": "G0 failed — no score-ΔU monotonicity"}
        save_results(all_results)
        return

    # ===== T1: Nested WFO (primary test) =====
    t1 = run_t1_nested_wfo(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                             wi, h4_ct)
    all_results["t1"] = t1

    if not t1["g1_pass"]:
        print(f"\n  T1 FAILED — WFO win_rate={t1['win_rate']:.0%}, "
              f"mean_d={t1['mean_d_sharpe']:+.4f}")
        all_results["verdict"] = {"verdict": "NOT_TEMPORAL",
                                   "reason": f"G1 failed — WFO {t1['win_rate']:.0%}"}
        # Still run comparison for report
        t5, stats_w = run_t5_comparison(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            t1["consensus"], m_e0, model_w, model_mu, model_std, train_scores_full)
        all_results["t5"] = t5
        save_results(all_results)
        return

    consensus = t1["consensus"]

    # ===== T2: Bootstrap =====
    t2, d_sh, d_ca, d_md = run_t2_bootstrap(
        cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        consensus, model_w, model_mu, model_std)
    all_results["t2"] = t2
    all_results["t2_arrays"] = (d_sh, d_ca, d_md)

    if not t2["g2_pass"]:
        print(f"\n  T2 FAILED — P(d>0)={t2['p_d_sharpe_gt0']:.1%}")
        all_results["verdict"] = {"verdict": "NOT_ROBUST",
                                   "reason": f"G2 failed — bootstrap P(d>0)={t2['p_d_sharpe_gt0']:.1%}"}
        t5, stats_w = run_t5_comparison(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            consensus, m_e0, model_w, model_mu, model_std, train_scores_full)
        all_results["t5"] = t5
        save_results(all_results)
        return

    if not t2["g3_pass"]:
        print(f"\n  T2 G3 FAILED — d_mdd={t2['d_mdd_median']:+.2f}pp")
        all_results["verdict"] = {"verdict": "MDD_TRADEOFF",
                                   "reason": f"G3 failed — d_mdd={t2['d_mdd_median']:+.2f}pp"}
        t5, stats_w = run_t5_comparison(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            consensus, m_e0, model_w, model_mu, model_std, train_scores_full)
        all_results["t5"] = t5
        save_results(all_results)
        return

    # ===== T3: Jackknife =====
    t3 = run_t3_jackknife(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                            wi, h4_ct, consensus,
                            model_w, model_mu, model_std, train_scores_full)
    all_results["t3"] = t3

    if not t3["g4_pass"]:
        print(f"\n  T3 FAILED — {t3['n_negative']}/6 negative")
        all_results["verdict"] = {"verdict": "FRAGILE",
                                   "reason": f"G4 failed — {t3['n_negative']}/6 negative"}
        t5, stats_w = run_t5_comparison(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            consensus, m_e0, model_w, model_mu, model_std, train_scores_full)
        all_results["t5"] = t5
        save_results(all_results)
        return

    # ===== T4: PSR =====
    t4 = run_t4_psr(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                      consensus, model_w, model_mu, model_std, train_scores_full)
    all_results["t4"] = t4

    if not t4["g5_pass"]:
        print(f"\n  T4 FAILED — PSR={t4['filter_psr']:.4f}")
        all_results["verdict"] = {"verdict": "UNDERPOWERED",
                                   "reason": f"G5 failed — PSR={t4['filter_psr']:.4f}"}
        t5, stats_w = run_t5_comparison(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            consensus, m_e0, model_w, model_mu, model_std, train_scores_full)
        all_results["t5"] = t5
        save_results(all_results)
        return

    # ===== ALL GATES PASSED =====
    print("\n  *** ALL GATES PASSED ***")

    t5, stats_w = run_t5_comparison(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        consensus, m_e0, model_w, model_mu, model_std, train_scores_full)
    all_results["t5"] = t5
    all_results["t5_stats"] = stats_w

    all_results["verdict"] = {
        "verdict": "PROMOTE",
        "consensus": consensus,
        "stats": stats_w,
    }

    print(f"\n  VERDICT: PROMOTE (α={consensus['alpha']}%, "
          f"G={consensus['G']}, δ={consensus['delta']})")

    save_results(all_results)

    elapsed = time.time() - t_start
    print(f"\nX17 BENCHMARK COMPLETE — {elapsed:.0f}s — "
          f"VERDICT: {all_results['verdict']['verdict']}")


if __name__ == "__main__":
    main()
