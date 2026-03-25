#!/usr/bin/env python3
"""X23 Research — State-Conditioned Exit Geometry Redesign

Redesign exit geometry ex ante:
- Separate hard invalidation stop from continuation stop
- Delay trail arming until trade has sufficient MFE
- Condition trail width on exogenous market state (wider in strong state)
- All logic deterministic, preset parameters, zero tuned DOF

Tests:
  T0: Full-sample comparison (E0, E5, X23-fixed, X23-cal)
  T1: Exit anatomy & churn diagnostic
  T2: Pullback calibration report
  T3: Walk-forward optimization (4 folds, nested calibration)
  T4: Bootstrap (500 VCBB paths)
  T5: Jackknife (leave-year-out)
  T6: PSR with DOF correction
  T7: Summary table & verdict

Gates:
  G0: T0 d_sharpe(X23-fixed, E5) > 0
  G1: T3 X23-fixed WFO >= 3/4, mean d > 0
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
ATR_P = 14                    # standard ATR (for score model features)
RATR_CAP_Q = 0.90             # robust ATR quantile cap
RATR_CAP_LB = 100             # robust ATR lookback
RATR_PERIOD = 20              # robust ATR Wilder period

# Trail baseline
TRAIL = 3.0                   # E0/E5 trail multiplier

# X23 architecture parameters (ALL PRESET, ZERO TUNED)
HARD_MULT = 2.5               # hard stop: E - HARD_MULT * rATR_entry
ARM_MULT = 1.5                # trail arms when MFE >= ARM_MULT * rATR_entry
SCORE_Q_LO = 15               # score percentile for weak/normal boundary
SCORE_Q_HI = 85               # score percentile for normal/strong boundary
M_WEAK = 2.25                 # trail mult in weak state
M_NORMAL = 3.0                # trail mult in normal state
M_STRONG = 4.25               # trail mult in strong state

# Score model (reused from X18)
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
CHURN_WINDOW = 20

# Pullback calibration quantiles (fixed by spec)
PB_Q_WEAK = 0.75
PB_Q_NORMAL = 0.85
PB_Q_STRONG = 0.90

# Cost
CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0

# Feature names
FEATURE_NAMES_7 = [
    "ema_ratio", "atr_pctl", "bar_range_atr", "close_position",
    "vdo_at_exit", "d1_regime_str", "trail_tightness",
]

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
# INDICATORS (identical to X18/X14)
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
    at = _atr(hi, lo, cl, ATR_P)
    return ef, es, vd, at


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
# MODEL: L2-PENALIZED LOGISTIC, 7 FEATURES (identical to X18)
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
        aucs.append(float(
            (np.sum(comp) + 0.5 * np.sum(ties)) / (len(pos) * len(neg))))
    return float(np.mean(aucs))


def _standardize(X):
    mu = np.mean(X, axis=0)
    std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


def _extract_features_7(i, cl, hi, lo, at_std, ef, es, vd, d1_str_h4,
                         trail_mult=TRAIL):
    """Extract 7 market-state features at bar i. Uses standard ATR (at_std)."""
    f1 = ef[i] / es[i] if abs(es[i]) > 1e-12 else 1.0
    atr_start = max(0, i - 99)
    atr_window = at_std[atr_start:i + 1]
    valid_atr = atr_window[~np.isnan(atr_window)]
    f2 = float(np.sum(valid_atr <= at_std[i])) / len(valid_atr) \
        if len(valid_atr) > 1 else 0.5
    f3 = (hi[i] - lo[i]) / at_std[i] if at_std[i] > 1e-12 else 1.0
    bar_w = hi[i] - lo[i]
    f4 = (cl[i] - lo[i]) / bar_w if bar_w > 1e-12 else 0.5
    f5 = float(vd[i])
    f6 = float(d1_str_h4[i])
    f7 = trail_mult * at_std[i] / cl[i] if cl[i] > 1e-12 else 0.0
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


def _extract_features_from_trades(trades, cl, hi, lo, at_std, ef, es, vd,
                                   d1_str_h4, trail_mult=TRAIL):
    n = len(cl)
    churn_labels = _label_churn(trades)
    features, labels = [], []
    for trade_idx, label in churn_labels:
        t = trades[trade_idx]
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n:
            continue
        if math.isnan(at_std[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue
        feat = _extract_features_7(sb, cl, hi, lo, at_std, ef, es, vd,
                                   d1_str_h4, trail_mult)
        features.append(feat)
        labels.append(label)
    if not features:
        return np.empty((0, 7)), np.empty(0, dtype=int)
    return np.array(features), np.array(labels, dtype=int)


def _train_model(trades, cl, hi, lo, at_std, ef, es, vd, d1_str_h4,
                  trail_mult=TRAIL):
    X, y = _extract_features_from_trades(
        trades, cl, hi, lo, at_std, ef, es, vd, d1_str_h4, trail_mult)
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


def _precompute_scores(cl, hi, lo, at_std, ef, es, vd, d1_str_h4,
                        model_w, model_mu, model_std, trail_mult=TRAIL):
    """Precompute logistic scores for ALL bars."""
    n = len(cl)
    scores = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(at_std[i]) or np.isnan(ef[i]) or np.isnan(es[i]):
            continue
        feat = _extract_features_7(i, cl, hi, lo, at_std, ef, es, vd,
                                   d1_str_h4, trail_mult)
        scores[i] = _predict_score(feat, model_w, model_mu, model_std)
    return scores


def _get_state(score, q15, q85):
    if np.isnan(score):
        return "normal"
    if score < q15:
        return "weak"
    if score >= q85:
        return "strong"
    return "normal"


# =========================================================================
# SIM: E0 BASELINE (standard ATR trail)
# =========================================================================

def _run_sim_e0(cl, ef, es, vd, at_std, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH):
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
                ret_pct = (received / entry_cost - 1.0) * 100 \
                    if entry_cost > 0 else 0.0
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

        nav[i] = cash + bq * p
        a_val = at_std[i]
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
        ret_pct = (received / entry_cost - 1.0) * 100 \
            if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
        })
    return nav, trades


# =========================================================================
# SIM: E5 BASELINE (robust ATR trail)
# =========================================================================

def _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi,
                trail_mult=TRAIL, cps=CPS_HARSH):
    """Identical to E0 except uses robust ATR for trail."""
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
                ret_pct = (received / entry_cost - 1.0) * 100 \
                    if entry_cost > 0 else 0.0
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

        nav[i] = cash + bq * p
        a_val = ratr[i]
        if np.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
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
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "peak_bar": pk_bar,
            "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
        })
    return nav, trades


# =========================================================================
# SIM: X23 — STATE-CONDITIONED EXIT GEOMETRY
# =========================================================================

def _run_sim_x23(cl, ef, es, vd, ratr, regime_h4, wi, scores,
                 score_q15, score_q85,
                 m_weak=M_WEAK, m_normal=M_NORMAL, m_strong=M_STRONG,
                 hard_mult=HARD_MULT, arm_mult=ARM_MULT,
                 cps=CPS_HARSH):
    """
    X23 exit geometry: hard stop + delayed trail arm + state-conditioned trail.

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
    hard_stop = 0.0
    trail_armed = False
    trail_arm_bar = -1
    exit_reason = ""
    state_at_exit = ""
    nav = np.zeros(n)
    trades = []
    stats = {
        "n_trades": 0, "n_hard_stop": 0, "n_trail_stop": 0,
        "n_trend_exit": 0, "n_end_of_data": 0, "n_arm_events": 0,
        "n_never_armed": 0,
        "n_trail_by_state": {"weak": 0, "normal": 0, "strong": 0},
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
                entry_ratr = ratr[i - 1]   # signal bar's rATR
                if np.isnan(entry_ratr):
                    # IMPL DECISION: spec §17.1 guard for NaN entry_ratr
                    hard_stop = -np.inf
                else:
                    hard_stop = entry_px - hard_mult * entry_ratr
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
                    "hard_stop_level": hard_stop,
                    "state_at_exit": state_at_exit,
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
            # ENTRY (unchanged from E0/E5)
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pending_entry = True

        else:
            # Update peak
            peak = max(peak, p)
            if p >= peak:
                peak_bar = i

            # Update MFE and trail arming
            mfe = peak - entry_px
            arm_threshold = arm_mult * entry_ratr \
                if not np.isnan(entry_ratr) else np.inf
            if not trail_armed and mfe >= arm_threshold:
                trail_armed = True
                trail_arm_bar = i
                stats["n_arm_events"] += 1

            # EXIT CHECK 1: Hard stop (always active)
            if p < hard_stop:
                exit_reason = "hard_stop"
                state_at_exit = _get_state(scores[i], score_q15, score_q85)
                pending_exit = True
                stats["n_hard_stop"] += 1
                continue

            # EXIT CHECK 2: Trend failure (always active)
            if ef[i] < es[i]:
                exit_reason = "trend_exit"
                state_at_exit = _get_state(scores[i], score_q15, score_q85)
                pending_exit = True
                stats["n_trend_exit"] += 1
                continue

            # EXIT CHECK 3: Trail stop (only when armed)
            if trail_armed:
                s = scores[i]
                if np.isnan(s):
                    m_t = m_normal
                    cur_state = "normal"
                elif s < score_q15:
                    m_t = m_weak
                    cur_state = "weak"
                elif s >= score_q85:
                    m_t = m_strong
                    cur_state = "strong"
                else:
                    m_t = m_normal
                    cur_state = "normal"

                trail_level = peak - m_t * a_val
                if p < trail_level:
                    exit_reason = "trail_stop"
                    state_at_exit = cur_state
                    pending_exit = True
                    stats["n_trail_stop"] += 1
                    stats["n_trail_by_state"][cur_state] += 1

    # --- Handle open position at end of data ---
    if in_position and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret_pct = (received / entry_cost - 1.0) * 100 \
            if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": peak, "peak_bar": peak_bar,
            "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": n - 1 - entry_bar,
            "exit_reason": "end_of_data",
            "trail_armed": trail_armed,
            "trail_arm_bar": trail_arm_bar,
            "hard_stop_level": hard_stop,
            "state_at_exit": "n/a",
        })
        stats["n_end_of_data"] += 1

    stats["n_trades"] = len(trades)
    return nav, trades, stats


# =========================================================================
# PULLBACK CALIBRATION
# =========================================================================

def _calibrate_pullback(cl, ef, es, ratr, scores,
                        score_q15, score_q85,
                        trades_baseline,
                        hard_mult=HARD_MULT,
                        q_weak=PB_Q_WEAK, q_normal=PB_Q_NORMAL,
                        q_strong=PB_Q_STRONG):
    """
    Estimate data-driven trail multipliers from healthy pullback distribution.

    Uses E5 baseline trades to identify in-position bars, then measures
    pullback depth per state for continuation instances.

    Returns (multipliers_dict, diagnostic_dict).
    """
    all_pb = {"weak": [], "normal": [], "strong": []}

    for trade in trades_baseline:
        eb = trade["entry_bar"]       # fill bar
        xb = trade["exit_bar"]
        epx = trade["entry_px"]       # cl[signal_bar] = cl[eb-1]
        entry_ratr_val = ratr[eb - 1] if eb > 0 else np.nan  # rATR at signal bar
        if np.isnan(entry_ratr_val):
            continue
        hard_stop_level = epx - hard_mult * entry_ratr_val

        # Reconstruct running peak for each in-position bar
        pk = cl[eb]
        for t in range(eb, xb):
            pk = max(pk, cl[t])
            state = _get_state(scores[t], score_q15, score_q85)

            # Find tau_next_peak: first u > t where cl[u] > peak
            tau_peak = None
            # IMPL DECISION: spec says search up to xb+1; limit to len(cl)
            upper = min(xb + 1, len(cl))
            for u in range(t + 1, upper):
                if cl[u] > pk:
                    tau_peak = u
                    break

            # Find tau_fail: first u > t where hard_stop or trend_exit
            tau_fail = None
            for u in range(t + 1, len(cl)):
                if cl[u] < hard_stop_level or ef[u] < es[u]:
                    tau_fail = u
                    break

            if tau_peak is not None and (tau_fail is None
                                         or tau_peak < tau_fail):
                # Continuation instance — measure pullback depth
                min_cl = cl[t]
                for v in range(t, tau_peak + 1):
                    if cl[v] < min_cl:
                        min_cl = cl[v]
                ratr_t = ratr[t]
                if not np.isnan(ratr_t) and ratr_t > 1e-12:
                    pb = (pk - min_cl) / ratr_t
                    all_pb[state].append(pb)

    # Per-state quantile estimation with shrinkage
    q_map = {"weak": q_weak, "normal": q_normal, "strong": q_strong}
    all_global = []
    for st in ("weak", "normal", "strong"):
        all_global.extend(all_pb[st])
    all_global = np.array(all_global) if all_global else np.array([3.0])

    multipliers = {}
    diagnostic = {}
    for st in ("weak", "normal", "strong"):
        vals = all_pb[st]
        n_vals = len(vals)
        q_level = q_map[st] * 100

        if n_vals >= 20:
            m_cal = float(np.percentile(vals, q_level))
            shrinkage = False
        elif n_vals >= 5:
            local_q = float(np.percentile(vals, q_level))
            global_q = float(np.percentile(all_global, q_level))
            weight = n_vals / 20.0
            m_cal = weight * local_q + (1 - weight) * global_q
            shrinkage = True
        else:
            m_cal = float(np.percentile(all_global, q_level))
            shrinkage = True

        multipliers[st] = m_cal
        arr = np.array(vals) if vals else np.array([0.0])
        diagnostic[st] = {
            "n": n_vals,
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr, ddof=0)),
            "q25": float(np.percentile(arr, 25)) if n_vals > 0 else 0.0,
            "q50": float(np.percentile(arr, 50)) if n_vals > 0 else 0.0,
            "q75": float(np.percentile(arr, 75)) if n_vals > 0 else 0.0,
            "q90": float(np.percentile(arr, 90)) if n_vals > 0 else 0.0,
            "q95": float(np.percentile(arr, 95)) if n_vals > 0 else 0.0,
            "calibrated_mult": m_cal,
            "shrinkage": shrinkage,
        }

    # Monotonicity constraint
    multipliers["weak"] = min(multipliers["weak"], multipliers["normal"])
    multipliers["strong"] = max(multipliers["strong"], multipliers["normal"])

    return multipliers, diagnostic


# =========================================================================
# CHURN LABELING (X23 version: separate per exit type)
# =========================================================================

def _label_churn_x23(trades, churn_window=CHURN_WINDOW):
    """Label churn for trail_stop and hard_stop exits separately."""
    all_entry_bars = sorted(t["entry_bar"] for t in trades)
    results = []
    for t in trades:
        if t["exit_reason"] not in ("trail_stop", "hard_stop"):
            continue
        eb = t["exit_bar"]
        is_churn = any(eb < e <= eb + churn_window for e in all_entry_bars)
        results.append({
            "trade": t,
            "is_churn": is_churn,
            "exit_type": t["exit_reason"],
        })
    return results


# =========================================================================
# T0: FULL-SAMPLE COMPARISON
# =========================================================================

def run_t0_fullsample(cl, hi, lo, ef, es, vd, at_std, ratr, regime_h4,
                       d1_str_h4, wi, h4_ct):
    print("\n" + "=" * 70)
    print("T0: FULL-SAMPLE COMPARISON")
    print("=" * 70)

    # E0 baseline (standard ATR)
    nav_e0, trades_e0 = _run_sim_e0(cl, ef, es, vd, at_std, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))

    # E5 baseline (robust ATR)
    nav_e5, trades_e5 = _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi)
    m_e5 = _metrics(nav_e5, wi, len(trades_e5))

    # Train logistic model on ALL E0 trades (full-sample, for diagnostic)
    model_w, model_mu, model_std, model_c, n_train = _train_model(
        trades_e0, cl, hi, lo, at_std, ef, es, vd, d1_str_h4)
    if model_w is None:
        print("  MODEL FAILED — aborting T0")
        return None

    # Precompute scores and quantiles
    scores = _precompute_scores(cl, hi, lo, at_std, ef, es, vd, d1_str_h4,
                                 model_w, model_mu, model_std)
    valid_scores = scores[~np.isnan(scores)]
    score_q15 = float(np.percentile(valid_scores, SCORE_Q_LO))
    score_q85 = float(np.percentile(valid_scores, SCORE_Q_HI))

    # X23-fixed (preset multipliers)
    nav_x23f, trades_x23f, stats_x23f = _run_sim_x23(
        cl, ef, es, vd, ratr, regime_h4, wi, scores, score_q15, score_q85)
    m_x23f = _metrics(nav_x23f, wi, len(trades_x23f))

    # Calibrate multipliers on full data (diagnostic)
    cal_mult, cal_diag = _calibrate_pullback(
        cl, ef, es, ratr, scores, score_q15, score_q85, trades_e5)

    # X23-cal (calibrated multipliers)
    nav_x23c, trades_x23c, stats_x23c = _run_sim_x23(
        cl, ef, es, vd, ratr, regime_h4, wi, scores, score_q15, score_q85,
        m_weak=cal_mult["weak"], m_normal=cal_mult["normal"],
        m_strong=cal_mult["strong"])
    m_x23c = _metrics(nav_x23c, wi, len(trades_x23c))

    # Exposure computation
    n_reporting = len(nav_e0) - wi
    for label, trades_list, m in [("E0", trades_e0, m_e0),
                                    ("E5", trades_e5, m_e5),
                                    ("X23-fixed", trades_x23f, m_x23f),
                                    ("X23-cal", trades_x23c, m_x23c)]:
        total_bars_held = sum(t["bars_held"] for t in trades_list)
        m["exposure"] = total_bars_held / n_reporting * 100 \
            if n_reporting > 0 else 0.0

    d_sharpe_fixed = m_x23f["sharpe"] - m_e5["sharpe"]
    g0 = d_sharpe_fixed > 0

    # Print results
    print(f"\n  {'Strategy':<12} {'Sharpe':>8} {'CAGR%':>8} {'MDD%':>8} "
          f"{'Trades':>7} {'Exp%':>7}")
    print("  " + "-" * 52)
    for label, m in [("E0", m_e0), ("E5", m_e5),
                     ("X23-fixed", m_x23f), ("X23-cal", m_x23c)]:
        print(f"  {label:<12} {m['sharpe']:>8.4f} {m['cagr']:>8.2f} "
              f"{m['mdd']:>8.2f} {m['trades']:>7} {m['exposure']:>7.1f}")
    print(f"\n  d_sharpe(X23-fixed vs E5) = {d_sharpe_fixed:+.4f}")
    print(f"  G0: {'PASS' if g0 else 'FAIL'}")
    print(f"  Calibrated multipliers: weak={cal_mult['weak']:.3f}, "
          f"normal={cal_mult['normal']:.3f}, strong={cal_mult['strong']:.3f}")

    return {
        "e0": m_e0, "e5": m_e5, "x23_fixed": m_x23f, "x23_cal": m_x23c,
        "calibrated_multipliers": cal_mult,
        "calibration_diagnostic": cal_diag,
        "stats_x23_fixed": stats_x23f, "stats_x23_cal": stats_x23c,
        "d_sharpe_fixed": d_sharpe_fixed, "g0_pass": g0,
        "model_w": model_w, "model_mu": model_mu, "model_std": model_std,
        "model_c": model_c, "n_train": n_train,
        "scores": scores, "score_q15": score_q15, "score_q85": score_q85,
        "nav_e0": nav_e0, "trades_e0": trades_e0,
        "nav_e5": nav_e5, "trades_e5": trades_e5,
        "nav_x23f": nav_x23f, "trades_x23f": trades_x23f,
        "nav_x23c": nav_x23c, "trades_x23c": trades_x23c,
    }


# =========================================================================
# T1: EXIT ANATOMY & CHURN DIAGNOSTIC
# =========================================================================

def run_t1_churn(t0_data):
    print("\n" + "=" * 70)
    print("T1: EXIT ANATOMY & CHURN DIAGNOSTIC")
    print("=" * 70)

    results = {}
    configs = [
        ("E0", t0_data["trades_e0"]),
        ("E5", t0_data["trades_e5"]),
        ("X23-fixed", t0_data["trades_x23f"]),
        ("X23-cal", t0_data["trades_x23c"]),
    ]

    print(f"\n  {'Strategy':<12} {'Total':>6} {'Trail':>6} {'Hard':>6} "
          f"{'Trend':>6} {'EndDat':>6} {'Ch/Tr':>7} {'Ch/Tot':>7}")
    print("  " + "-" * 62)

    for label, trades in configs:
        total = len(trades)
        n_trail = sum(1 for t in trades if t["exit_reason"] == "trail_stop")
        n_hard = sum(1 for t in trades
                     if t.get("exit_reason") == "hard_stop")
        n_trend = sum(1 for t in trades if t["exit_reason"] == "trend_exit")
        n_eod = sum(1 for t in trades if t["exit_reason"] == "end_of_data")

        churn_results = _label_churn_x23(trades)
        n_trail_churn = sum(1 for r in churn_results
                            if r["exit_type"] == "trail_stop" and r["is_churn"])
        n_hard_churn = sum(1 for r in churn_results
                           if r["exit_type"] == "hard_stop" and r["is_churn"])
        n_total_churn = n_trail_churn + n_hard_churn
        n_total_non_trend = n_trail + n_hard

        churn_trail_rate = n_trail_churn / n_trail * 100 \
            if n_trail > 0 else 0.0
        churn_total_rate = n_total_churn / n_total_non_trend * 100 \
            if n_total_non_trend > 0 else 0.0

        print(f"  {label:<12} {total:>6} {n_trail:>6} {n_hard:>6} "
              f"{n_trend:>6} {n_eod:>6} {churn_trail_rate:>6.1f}% "
              f"{churn_total_rate:>6.1f}%")

        results[label] = {
            "total": total, "trail": n_trail, "hard": n_hard,
            "trend": n_trend, "end_of_data": n_eod,
            "churn_trail": n_trail_churn, "churn_hard": n_hard_churn,
            "churn_trail_rate": churn_trail_rate,
            "churn_total_rate": churn_total_rate,
        }

    # X23 arm statistics
    for label in ("X23-fixed", "X23-cal"):
        stats_key = "stats_x23_fixed" if "fixed" in label else "stats_x23_cal"
        stats = t0_data[stats_key]
        print(f"\n  {label} arm stats: "
              f"armed={stats['n_arm_events']}, "
              f"never_armed={stats['n_never_armed']}, "
              f"trail_by_state={stats['n_trail_by_state']}")

    return results


# =========================================================================
# T2: PULLBACK CALIBRATION REPORT
# =========================================================================

def run_t2_pullback(t0_data):
    print("\n" + "=" * 70)
    print("T2: PULLBACK CALIBRATION REPORT")
    print("=" * 70)

    diag = t0_data["calibration_diagnostic"]
    cal_mult = t0_data["calibrated_multipliers"]
    presets = {"weak": M_WEAK, "normal": M_NORMAL, "strong": M_STRONG}

    print(f"\n  {'State':<8} {'N':>6} {'Mean':>7} {'Std':>7} {'Q25':>7} "
          f"{'Q50':>7} {'Q75':>7} {'Q90':>7} {'Q95':>7} "
          f"{'Cal':>7} {'Preset':>7}")
    print("  " + "-" * 82)

    for st in ("weak", "normal", "strong"):
        d = diag[st]
        print(f"  {st:<8} {d['n']:>6} {d['mean']:>7.3f} {d['std']:>7.3f} "
              f"{d['q25']:>7.3f} {d['q50']:>7.3f} {d['q75']:>7.3f} "
              f"{d['q90']:>7.3f} {d['q95']:>7.3f} "
              f"{cal_mult[st]:>7.3f} {presets[st]:>7.3f}")

    return {"diagnostic": diag, "calibrated": cal_mult, "presets": presets}


# =========================================================================
# T3: WALK-FORWARD OPTIMIZATION (4 folds, nested calibration)
# =========================================================================

def run_t3_wfo(cl, hi, lo, ef, es, vd, at_std, ratr, regime_h4,
               d1_str_h4, wi, h4_ct):
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
        # --- TRAIN ---
        te = train_end + 1  # slice end (exclusive)

        # a. E0 sim on training data (for model training)
        _, trades_e0_tr = _run_sim_e0(
            cl[:te], ef[:te], es[:te], vd[:te], at_std[:te],
            regime_h4[:te], wi)

        # b. Train logistic model
        w, mu, std, c, ns = _train_model(
            trades_e0_tr, cl[:te], hi[:te], lo[:te], at_std[:te],
            ef[:te], es[:te], vd[:te], d1_str_h4[:te])

        if w is None:
            fold_results.append({
                "fold": fold_idx + 1, "status": "no_model",
                "e5_sharpe": 0.0, "x23_fixed_sharpe": 0.0,
                "x23_cal_sharpe": 0.0,
                "d_sharpe_fixed": 0.0, "d_sharpe_cal": 0.0,
                "cal_multipliers": {"weak": M_WEAK, "normal": M_NORMAL,
                                    "strong": M_STRONG},
                "score_q15": 0.5, "score_q85": 0.5,
            })
            continue

        # c. Precompute scores on training data
        scores_tr = _precompute_scores(
            cl[:te], hi[:te], lo[:te], at_std[:te], ef[:te], es[:te],
            vd[:te], d1_str_h4[:te], w, mu, std)

        # d-e. Score quantiles from training data
        valid_sc = scores_tr[~np.isnan(scores_tr)]
        if len(valid_sc) < 10:
            fold_results.append({
                "fold": fold_idx + 1, "status": "few_scores",
                "e5_sharpe": 0.0, "x23_fixed_sharpe": 0.0,
                "x23_cal_sharpe": 0.0,
                "d_sharpe_fixed": 0.0, "d_sharpe_cal": 0.0,
                "cal_multipliers": {"weak": M_WEAK, "normal": M_NORMAL,
                                    "strong": M_STRONG},
                "score_q15": 0.5, "score_q85": 0.5,
            })
            continue

        sq15 = float(np.percentile(valid_sc, SCORE_Q_LO))
        sq85 = float(np.percentile(valid_sc, SCORE_Q_HI))

        # f. E5 sim on training data (for pullback calibration)
        _, trades_e5_tr = _run_sim_e5(
            cl[:te], ef[:te], es[:te], vd[:te], ratr[:te],
            regime_h4[:te], wi)

        # g. Pullback calibration on training data
        cal_mult, _ = _calibrate_pullback(
            cl[:te], ef[:te], es[:te], ratr[:te], scores_tr,
            sq15, sq85, trades_e5_tr)

        # --- APPLY (full data with frozen params) ---
        # Precompute scores on full data with frozen model
        scores_full = _precompute_scores(
            cl, hi, lo, at_std, ef, es, vd, d1_str_h4, w, mu, std)

        # E5 baseline on full data
        nav_e5, trades_e5 = _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi)
        test_trades_e5 = [t for t in trades_e5
                          if test_start <= t["entry_bar"] < test_end]
        m_e5_test = _metrics_window(
            nav_e5, test_start, test_end + 1, len(test_trades_e5))

        # X23-fixed on full data with frozen score quantiles
        nav_x23f, trades_x23f, _ = _run_sim_x23(
            cl, ef, es, vd, ratr, regime_h4, wi, scores_full, sq15, sq85)
        test_trades_x23f = [t for t in trades_x23f
                            if test_start <= t["entry_bar"] < test_end]
        m_x23f_test = _metrics_window(
            nav_x23f, test_start, test_end + 1, len(test_trades_x23f))

        # X23-cal on full data with frozen calibrated multipliers
        nav_x23c, trades_x23c, _ = _run_sim_x23(
            cl, ef, es, vd, ratr, regime_h4, wi, scores_full, sq15, sq85,
            m_weak=cal_mult["weak"], m_normal=cal_mult["normal"],
            m_strong=cal_mult["strong"])
        test_trades_x23c = [t for t in trades_x23c
                            if test_start <= t["entry_bar"] < test_end]
        m_x23c_test = _metrics_window(
            nav_x23c, test_start, test_end + 1, len(test_trades_x23c))

        # --- MEASURE ---
        d_fixed = m_x23f_test["sharpe"] - m_e5_test["sharpe"]
        d_cal = m_x23c_test["sharpe"] - m_e5_test["sharpe"]

        fold_results.append({
            "fold": fold_idx + 1, "status": "ok",
            "train_end": WFO_FOLDS[fold_idx][0],
            "test_start": WFO_FOLDS[fold_idx][1],
            "test_end": WFO_FOLDS[fold_idx][2],
            "e5_sharpe": m_e5_test["sharpe"],
            "x23_fixed_sharpe": m_x23f_test["sharpe"],
            "x23_cal_sharpe": m_x23c_test["sharpe"],
            "d_sharpe_fixed": d_fixed,
            "d_sharpe_cal": d_cal,
            "cal_multipliers": cal_mult,
            "score_q15": sq15, "score_q85": sq85,
        })
        print(f"    Fold {fold_idx + 1}: E5={m_e5_test['sharpe']:.4f}, "
              f"X23f={m_x23f_test['sharpe']:.4f} (d={d_fixed:+.4f}), "
              f"X23c={m_x23c_test['sharpe']:.4f} (d={d_cal:+.4f}) "
              f"{'WIN' if d_fixed > 0 else 'LOSE'}")

    # Aggregate for X23-fixed (gate decisions on fixed only)
    valid_folds = [f for f in fold_results if f.get("status") == "ok"]
    if valid_folds:
        win_rate_fixed = sum(
            1 for f in valid_folds if f["d_sharpe_fixed"] > 0
        ) / len(valid_folds)
        mean_d_fixed = float(np.mean(
            [f["d_sharpe_fixed"] for f in valid_folds]))
        win_rate_cal = sum(
            1 for f in valid_folds if f["d_sharpe_cal"] > 0
        ) / len(valid_folds)
        mean_d_cal = float(np.mean(
            [f["d_sharpe_cal"] for f in valid_folds]))
    else:
        win_rate_fixed = mean_d_fixed = win_rate_cal = mean_d_cal = 0.0

    g1 = win_rate_fixed >= 0.75 and mean_d_fixed > 0

    print(f"\n  X23-fixed: win_rate={win_rate_fixed:.0%}, "
          f"mean_d={mean_d_fixed:+.4f}, G1: {'PASS' if g1 else 'FAIL'}")
    print(f"  X23-cal:   win_rate={win_rate_cal:.0%}, "
          f"mean_d={mean_d_cal:+.4f} (supplementary)")

    return {
        "folds": fold_results,
        "win_rate_fixed": win_rate_fixed,
        "mean_d_fixed": mean_d_fixed,
        "win_rate_cal": win_rate_cal,
        "mean_d_cal": mean_d_cal,
        "g1_pass": g1,
    }


# =========================================================================
# T4: BOOTSTRAP (500 VCBB paths)
# =========================================================================

def run_t4_bootstrap(cl, hi, lo, vo, tb, ef, es, vd, at_std, ratr,
                      regime_h4, d1_str_h4, wi,
                      model_w_full, model_mu_full, model_std_full,
                      score_q15_full, score_q85_full):
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
    d1_str_pw = d1_str_h4[wi:]

    d_sharpes, d_cagrs, d_mdds = [], [], []
    sharpes_x23, sharpes_e5 = [], []

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        n_b = len(bcl)
        breg = regime_pw[:n_b] if len(regime_pw) >= n_b \
            else np.ones(n_b, dtype=np.bool_)
        bd1 = d1_str_pw[:n_b] if len(d1_str_pw) >= n_b \
            else np.zeros(n_b)

        bef, bes, bvd, bat = _compute_indicators(bcl, bhi, blo, bvo, btb)
        bratr = _compute_ratr(bhi, blo, bcl)

        # E5 baseline
        bnav_e5, btrades_e5 = _run_sim_e5(bcl, bef, bes, bvd, bratr, breg, 0)
        bm_e5 = _metrics(bnav_e5, 0, len(btrades_e5))

        # Train model on first 60%
        te = int(n_b * 0.6)
        _, btr_e0 = _run_sim_e0(
            bcl[:te], bef[:te], bes[:te], bvd[:te], bat[:te], breg[:te], 0)
        bw, bmu, bstd, _, _ = _train_model(
            btr_e0, bcl[:te], bhi[:te], blo[:te], bat[:te],
            bef[:te], bes[:te], bvd[:te], bd1[:te])
        if bw is None:
            bw, bmu, bstd = model_w_full, model_mu_full, model_std_full

        # Precompute scores and quantiles on first 60%
        bscores_tr = _precompute_scores(
            bcl[:te], bhi[:te], blo[:te], bat[:te], bef[:te], bes[:te],
            bvd[:te], bd1[:te], bw, bmu, bstd)
        bvalid = bscores_tr[~np.isnan(bscores_tr)]
        if len(bvalid) >= 10:
            bsq15 = float(np.percentile(bvalid, SCORE_Q_LO))
            bsq85 = float(np.percentile(bvalid, SCORE_Q_HI))
        else:
            bsq15, bsq85 = score_q15_full, score_q85_full

        # Precompute scores on full synthetic path
        bscores_full = _precompute_scores(
            bcl, bhi, blo, bat, bef, bes, bvd, bd1, bw, bmu, bstd)

        # X23-fixed
        bnav_x23, btrades_x23, _ = _run_sim_x23(
            bcl, bef, bes, bvd, bratr, breg, 0, bscores_full,
            bsq15, bsq85)
        bm_x23 = _metrics(bnav_x23, 0, len(btrades_x23))

        d_sharpes.append(bm_x23["sharpe"] - bm_e5["sharpe"])
        d_cagrs.append(bm_x23["cagr"] - bm_e5["cagr"])
        d_mdds.append(bm_x23["mdd"] - bm_e5["mdd"])
        sharpes_x23.append(bm_x23["sharpe"])
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
        "median_sharpe_x23": float(np.median(sharpes_x23)),
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

def run_t5_jackknife(cl, ef, es, vd, ratr, regime_h4, wi, h4_ct,
                      scores, score_q15, score_q85):
    print("\n" + "=" * 70)
    print("T5: JACKKNIFE (leave-year-out)")
    print("=" * 70)

    n = len(cl)

    # Full-data sims (no retraining per fold)
    nav_e5, trades_e5 = _run_sim_e5(cl, ef, es, vd, ratr, regime_h4, wi)
    nav_x23, trades_x23, _ = _run_sim_x23(
        cl, ef, es, vd, ratr, regime_h4, wi, scores, score_q15, score_q85)

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

        tr_x23_jk = [t for t in trades_x23
                      if not (ys <= t["entry_bar"] <= ye)]
        m_x23 = _metrics(nav_x23[kept], 0, len(tr_x23_jk))

        d = m_x23["sharpe"] - m_e5["sharpe"]
        folds.append({
            "year": yr,
            "e5_sharpe": m_e5["sharpe"],
            "x23_sharpe": m_x23["sharpe"],
            "d_sharpe": d,
            "d_sharpe_negative": d < 0,
        })
        print(f"    Drop {yr}: E5={m_e5['sharpe']:.4f}, "
              f"X23={m_x23['sharpe']:.4f}, d={d:+.4f}")

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

def run_t6_psr(nav_x23, wi):
    print("\n" + "=" * 70)
    print("T6: PSR WITH DOF CORRECTION")
    print("=" * 70)

    navs = nav_x23[wi:]
    rets = navs[1:] / navs[:-1] - 1.0
    n_returns = len(rets)
    mu = np.mean(rets)
    std_ret = np.std(rets, ddof=0)
    sharpe_per_bar = mu / std_ret if std_ret > 1e-12 else 0.0
    sharpe_ann = sharpe_per_bar * ANN

    # IMPL DECISION: benchmark_sr0 requires int num_trials. Round DOF.
    num_trials = max(2, int(round(E0_EFFECTIVE_DOF)))
    sr0 = benchmark_sr0(num_trials, n_returns)
    # sr0 is per-bar scale from the library; annualize it
    sr0_ann = sr0 * ANN

    psr = _psr(sharpe_ann, n_returns, sr0_ann)
    g5 = psr > 0.95

    print(f"  X23-fixed Sharpe (ann): {sharpe_ann:.4f}")
    print(f"  SR0 (DOF={num_trials}): {sr0_ann:.4f}")
    print(f"  PSR: {psr:.4f}")
    print(f"  G5: {'PASS' if g5 else 'FAIL'}")
    return {"sharpe": sharpe_ann, "sr0": sr0_ann, "psr": psr,
            "n_returns": n_returns, "g5_pass": g5}


# =========================================================================
# T7: SUMMARY TABLE & VERDICT
# =========================================================================

def run_t7_summary(g0, g1, g2, g3, g4, g5, t0_data, t3_data, t4_data,
                    t5_data, t6_data):
    print("\n" + "=" * 70)
    print("T7: SUMMARY TABLE & VERDICT")
    print("=" * 70)

    gates = {
        "G0": {"test": "T0", "criterion": "d_sharpe > 0 vs E5",
                "value": t0_data["d_sharpe_fixed"], "pass": g0},
        "G1": {"test": "T3", "criterion": "WFO >= 3/4, mean d > 0",
                "value": f"wr={t3_data['win_rate_fixed']:.0%}, "
                         f"d={t3_data['mean_d_fixed']:+.4f}",
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
    """Generate x23_report.md from all_results."""
    lines = []
    lines.append("# X23 Report: State-Conditioned Exit Geometry Redesign\n")
    lines.append(f"Generated: {datetime.datetime.utcnow().isoformat()}Z\n")

    # T0
    t0 = all_results.get("t0", {})
    lines.append("\n## T0: Full-Sample Comparison\n")
    lines.append("| Strategy | Sharpe | CAGR% | MDD% | Trades | Exposure% |")
    lines.append("|----------|--------|-------|------|--------|-----------|")
    for label in ("e0", "e5", "x23_fixed", "x23_cal"):
        m = t0.get(label, {})
        lines.append(
            f"| {label} | {m.get('sharpe', 0):.4f} | {m.get('cagr', 0):.2f} "
            f"| {m.get('mdd', 0):.2f} | {m.get('trades', 0)} "
            f"| {m.get('exposure', 0):.1f} |")
    lines.append(f"\nd_sharpe(X23-fixed vs E5) = "
                 f"{t0.get('d_sharpe_fixed', 0):+.4f}")
    lines.append(f"G0: **{'PASS' if t0.get('g0_pass') else 'FAIL'}**\n")

    cal = t0.get("calibrated_multipliers", {})
    lines.append(f"Calibrated multipliers: weak={cal.get('weak', 0):.3f}, "
                 f"normal={cal.get('normal', 0):.3f}, "
                 f"strong={cal.get('strong', 0):.3f}\n")

    # T1
    t1 = all_results.get("t1", {})
    lines.append("\n## T1: Exit Anatomy & Churn Diagnostic\n")
    lines.append("| Strategy | Total | Trail | Hard | Trend | "
                 "Ch/Trail% | Ch/Total% |")
    lines.append("|----------|-------|-------|------|-------|"
                 "----------|-----------|")
    for label in ("E0", "E5", "X23-fixed", "X23-cal"):
        r = t1.get(label, {})
        lines.append(
            f"| {label} | {r.get('total', 0)} | {r.get('trail', 0)} "
            f"| {r.get('hard', 0)} | {r.get('trend', 0)} "
            f"| {r.get('churn_trail_rate', 0):.1f} "
            f"| {r.get('churn_total_rate', 0):.1f} |")

    # T2
    t2 = all_results.get("t2", {})
    diag = t2.get("diagnostic", {})
    lines.append("\n## T2: Pullback Calibration Report\n")
    lines.append("| State | N | Mean | Q50 | Q75 | Q90 | Cal.Mult | Preset |")
    lines.append("|-------|---|------|-----|-----|-----|----------|--------|")
    presets = {"weak": M_WEAK, "normal": M_NORMAL, "strong": M_STRONG}
    cal_m = t2.get("calibrated", {})
    for st in ("weak", "normal", "strong"):
        d = diag.get(st, {})
        lines.append(
            f"| {st} | {d.get('n', 0)} | {d.get('mean', 0):.3f} "
            f"| {d.get('q50', 0):.3f} | {d.get('q75', 0):.3f} "
            f"| {d.get('q90', 0):.3f} | {cal_m.get(st, 0):.3f} "
            f"| {presets[st]:.3f} |")

    # T3
    t3 = all_results.get("t3", {})
    lines.append("\n## T3: Walk-Forward Optimization\n")
    lines.append("| Fold | E5 Sharpe | X23f Sharpe | d_fixed | "
                 "X23c Sharpe | d_cal |")
    lines.append("|------|-----------|-------------|---------|"
                 "------------|-------|")
    for f in t3.get("folds", []):
        lines.append(
            f"| {f.get('fold', 0)} | {f.get('e5_sharpe', 0):.4f} "
            f"| {f.get('x23_fixed_sharpe', 0):.4f} "
            f"| {f.get('d_sharpe_fixed', 0):+.4f} "
            f"| {f.get('x23_cal_sharpe', 0):.4f} "
            f"| {f.get('d_sharpe_cal', 0):+.4f} |")
    lines.append(f"\nX23-fixed: win_rate={t3.get('win_rate_fixed', 0):.0%}, "
                 f"mean_d={t3.get('mean_d_fixed', 0):+.4f}")
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
    lines.append("| Year | E5 Sharpe | X23 Sharpe | d_sharpe |")
    lines.append("|------|-----------|------------|----------|")
    for f in t5.get("folds", []):
        lines.append(
            f"| {f.get('year', 0)} | {f.get('e5_sharpe', 0):.4f} "
            f"| {f.get('x23_sharpe', 0):.4f} "
            f"| {f.get('d_sharpe', 0):+.4f} |")
    lines.append(f"\nNegative: {t5.get('n_negative', 0)}/6")
    lines.append(f"G4: **{'PASS' if t5.get('g4_pass') else 'FAIL'}**\n")

    # T6
    t6 = all_results.get("t6", {})
    lines.append("\n## T6: PSR\n")
    lines.append(f"- X23-fixed Sharpe: {t6.get('sharpe', 0):.4f}")
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
        if k in ("t0",):
            # Strip nav/trades/model arrays from T0 for JSON
            t0_clean = {kk: vv for kk, vv in v.items()
                        if kk not in ("nav_e0", "nav_e5", "nav_x23f",
                                      "nav_x23c", "trades_e0", "trades_e5",
                                      "trades_x23f", "trades_x23c",
                                      "model_w", "model_mu", "model_std",
                                      "scores")}
            json_data[k] = t0_clean
        else:
            json_data[k] = v

    json_data["study_id"] = "X23"
    json_data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
    json_data["constants"] = {
        "HARD_MULT": HARD_MULT, "ARM_MULT": ARM_MULT,
        "SCORE_Q_LO": SCORE_Q_LO, "SCORE_Q_HI": SCORE_Q_HI,
        "M_WEAK": M_WEAK, "M_NORMAL": M_NORMAL, "M_STRONG": M_STRONG,
        "PB_Q_WEAK": PB_Q_WEAK, "PB_Q_NORMAL": PB_Q_NORMAL,
        "PB_Q_STRONG": PB_Q_STRONG,
        "TRAIL": TRAIL, "COST_BPS_RT": SCENARIOS["harsh"].round_trip_bps,
    }

    with open(OUTDIR / "x23_results.json", "w") as f:
        json.dump(_coerce(json_data), f, indent=2)

    # Bootstrap CSV
    if d_sharpes is not None:
        with open(OUTDIR / "x23_bootstrap.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "d_sharpe", "d_cagr", "d_mdd"])
            for i in range(len(d_sharpes)):
                w.writerow([i, f"{d_sharpes[i]:.6f}",
                            f"{d_cagrs[i]:.6f}", f"{d_mdds[i]:.6f}"])

    # WFO CSV
    t3 = all_results.get("t3", {})
    if t3.get("folds"):
        with open(OUTDIR / "x23_wfo.csv", "w", newline="") as f:
            fields = ["fold", "e5_sharpe", "x23_fixed_sharpe",
                       "d_sharpe_fixed", "x23_cal_sharpe", "d_sharpe_cal"]
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in t3["folds"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                            for k, v in r.items() if k in fields})

    # Jackknife CSV
    t5 = all_results.get("t5", {})
    if t5.get("folds"):
        with open(OUTDIR / "x23_jackknife.csv", "w", newline="") as f:
            fields = list(t5["folds"][0].keys())
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in t5["folds"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                            for k, v in r.items()})

    # Report
    report = _generate_report(all_results)
    with open(OUTDIR / "x23_report.md", "w") as f:
        f.write(report)

    print(f"\n  Saved to {OUTDIR}/x23_*.{{json,csv,md}}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("X23: State-Conditioned Exit Geometry Redesign")
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
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)
    ef, es, vd, at_std = _compute_indicators(cl, hi, lo, vo, tb)
    ratr = _compute_ratr(hi, lo, cl)
    print(f"  Bars: {len(cl)} H4, warmup_idx={wi}")
    print(f"  rATR first valid: {np.argmax(~np.isnan(ratr))}")

    all_results = {}

    # --- T0: Full-sample comparison ---
    t0_data = run_t0_fullsample(cl, hi, lo, ef, es, vd, at_std, ratr,
                                 regime_h4, d1_str_h4, wi, h4_ct)
    if t0_data is None:
        all_results["verdict"] = "ABORT"
        save_results(all_results)
        print(f"\n  Total time: {time.time() - t_start:.1f}s")
        return

    # Store T0 results (strip large arrays for JSON later)
    all_results["t0"] = t0_data
    g0 = t0_data["g0_pass"]

    # Extract reusable data from T0
    model_w = t0_data["model_w"]
    model_mu = t0_data["model_mu"]
    model_std = t0_data["model_std"]
    scores = t0_data["scores"]
    score_q15 = t0_data["score_q15"]
    score_q85 = t0_data["score_q85"]

    # --- T1: Churn diagnostic ---
    t1_data = run_t1_churn(t0_data)
    all_results["t1"] = t1_data

    # --- T2: Pullback calibration ---
    t2_data = run_t2_pullback(t0_data)
    all_results["t2"] = t2_data

    # --- T3: WFO ---
    t3_data = run_t3_wfo(cl, hi, lo, ef, es, vd, at_std, ratr, regime_h4,
                          d1_str_h4, wi, h4_ct)
    all_results["t3"] = t3_data
    g1 = t3_data["g1_pass"]

    # --- T4: Bootstrap ---
    t4_data, d_sharpes, d_cagrs, d_mdds = run_t4_bootstrap(
        cl, hi, lo, vo, tb, ef, es, vd, at_std, ratr,
        regime_h4, d1_str_h4, wi,
        model_w, model_mu, model_std, score_q15, score_q85)
    all_results["t4"] = t4_data
    g2 = t4_data["g2_pass"]
    g3 = t4_data["g3_pass"]

    # --- T5: Jackknife ---
    t5_data = run_t5_jackknife(cl, ef, es, vd, ratr, regime_h4, wi, h4_ct,
                                scores, score_q15, score_q85)
    all_results["t5"] = t5_data
    g4 = t5_data["g4_pass"]

    # --- T6: PSR ---
    nav_x23f = t0_data["nav_x23f"]
    t6_data = run_t6_psr(nav_x23f, wi)
    all_results["t6"] = t6_data
    g5 = t6_data["g5_pass"]

    # --- T7: Summary & Verdict ---
    t7_data = run_t7_summary(g0, g1, g2, g3, g4, g5,
                              t0_data, t3_data, t4_data, t5_data, t6_data)
    all_results["t7"] = t7_data

    # --- Save ---
    save_results(all_results, d_sharpes, d_cagrs, d_mdds)

    elapsed = time.time() - t_start
    print(f"\n  Total time: {elapsed:.1f}s ({elapsed / 60:.1f}m)")


if __name__ == "__main__":
    main()
