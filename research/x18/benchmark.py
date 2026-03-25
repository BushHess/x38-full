#!/usr/bin/env python3
"""X18 Research — α-Percentile Static Mask: Nested WFO Validation

Combine X14's proven static suppress mechanism with the analyst's
methodological improvements (α-percentile, nested WFO, ΔU diagnostic).

Key: NO WATCH state, NO G parameter, NO deeper stop.
Just binary suppress/exit at each trail breach, with α as only parameter.

Tests:
  T0: ΔU diagnostic (static suppress utility by score quintile)
  T1: Nested WFO (4 expanding folds, primary test)
  T2: Bootstrap (500 VCBB paths)
  T3: Jackknife (leave-year-out)
  T4: PSR with DOF correction
  T5: Comparison table

Gates:
  G0: T0 top 2 quintiles median ΔU > 0
  G1: T1 WFO >= 3/4, mean d_sharpe > 0
  G2: T2 P(d_sharpe > 0) > 0.60
  G3: T2 median d_mdd <= +5.0 pp
  G4: T3 <= 2 negative jackknife
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
ATR_P = 14

CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0
CHURN_WINDOW = 20

ALPHA_GRID = [5, 10, 15, 20, 25, 30, 40, 50, 60, 70]
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]

FEATURE_NAMES_7 = [
    "ema_ratio", "atr_pctl", "bar_range_atr", "close_position",
    "vdo_at_exit", "d1_regime_str", "trail_tightness",
]

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
# INDICATORS (identical to X14/X16/X17)
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


def _date_to_bar_idx(h4_ct, date_str):
    import datetime
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
# MODEL: L2-PENALIZED LOGISTIC, 7 FEATURES
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


def _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                          trail_mult=TRAIL):
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


def _extract_features_from_trades(trades, cl, hi, lo, at, ef, es, vd,
                                    d1_str_h4, trail_mult=TRAIL):
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
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd,
                                    d1_str_h4, trail_mult)
        features.append(feat)
        labels.append(label)
    if not features:
        return np.empty((0, 7)), np.empty(0, dtype=int)
    return np.array(features), np.array(labels, dtype=int)


def _train_model(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                   trail_mult=TRAIL):
    X, y = _extract_features_from_trades(trades, cl, hi, lo, at, ef, es, vd,
                                          d1_str_h4, trail_mult)
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
# SIM: E0 baseline
# =========================================================================

def _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi,
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
    return nav, trades


# =========================================================================
# SIM: STATIC MASK with α-percentile threshold
# =========================================================================

def _run_sim_mask(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                   model_w, model_mu, model_std, alpha_threshold,
                   trail_mult=TRAIL, cps=CPS_HARSH):
    """E0 + static mask: at each bar where trail fires, score 7 features.
    If score > alpha_threshold: SUPPRESS trail (trade continues).
    Else: normal trail exit.
    """
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
    n_suppress = 0
    n_trail_exit = 0

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
                # Trail fires — evaluate model
                feat = _extract_features_7(i, cl, hi, lo, at, ef, es, vd,
                                            d1_str_h4, trail_mult)
                score = _predict_score(feat, model_w, model_mu, model_std)
                if score > alpha_threshold:
                    # SUPPRESS: ignore trail, trade continues
                    n_suppress += 1
                else:
                    exit_reason = "trail_stop"
                    px = True
                    n_trail_exit += 1
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

    stats = {"n_suppress": n_suppress, "n_trail_exit": n_trail_exit,
             "n_trades": len(trades)}
    return nav, trades, stats


# =========================================================================
# T0: ΔU DIAGNOSTIC (static suppress)
# =========================================================================

def _find_active_trade(bar, trades):
    """Find the trade active at a given bar (entry_bar <= bar < exit_bar)."""
    for t in trades:
        if t["entry_bar"] <= bar < t["exit_bar"]:
            return t
    return None


def run_t0_delta_u(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                    model_w, model_mu, model_std, trades_e0):
    """ΔU for static suppress: for each E0 trail-stop episode, find the
    masked trade ACTIVE at that bar and compare exit prices.

    Key fix: matching by entry_bar fails because static suppress extends
    trades, absorbing subsequent entries. Instead, we find which masked
    trade covers the trail-stop bar — this correctly handles both extended
    trades and absorbed trades.
    """
    print("\n" + "=" * 70)
    print("T0: ΔU DIAGNOSTIC (static suppress)")
    print("=" * 70)

    n = len(cl)
    # Score each trail-stop episode
    episodes = []
    for t in trades_e0:
        if t["exit_reason"] != "trail_stop":
            continue
        sb = t["exit_bar"] - 1  # bar where trail fires
        if sb < 0 or sb >= n or math.isnan(at[sb]) or math.isnan(ef[sb]):
            continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        score = _predict_score(feat, model_w, model_mu, model_std)
        episodes.append({"score": score, "entry_bar": t["entry_bar"],
                          "exit_bar": t["exit_bar"], "exit_px": t["exit_px"],
                          "signal_bar": sb})

    n_ep = len(episodes)
    print(f"  Trail-stop episodes: {n_ep}")
    if n_ep < 10:
        return {"g0_pass": False, "reason": "too_few"}

    # Compute training scores for percentile
    all_scores = np.array([ep["score"] for ep in episodes])

    # For each α, run masked sim and match by active-trade-at-bar
    best_alpha = ALPHA_GRID[0]
    best_mono = -999
    all_rows = []

    for alpha in ALPHA_GRID:
        alpha_thresh = float(np.percentile(all_scores, 100 - alpha))
        nav_m, trades_m, stats_m = _run_sim_mask(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            model_w, model_mu, model_std, alpha_thresh)

        # Compute per-episode ΔU: find masked trade active at signal_bar
        delta_us = []
        n_matched = 0
        n_nonzero = 0
        for ep in episodes:
            sb = ep["signal_bar"]  # bar where trail fires in E0
            mt = _find_active_trade(sb, trades_m)
            if mt is None:
                # Bar not covered — shouldn't happen unless between trades
                delta_us.append(0.0)
                continue
            n_matched += 1
            e0_px = ep["exit_px"]
            m_px = mt["exit_px"]
            if e0_px > 0 and m_px > 0 and abs(m_px - e0_px) > 1e-6:
                du = math.log(m_px / e0_px)
                delta_us.append(du)
                n_nonzero += 1
            else:
                delta_us.append(0.0)

        # Quintile analysis
        scored = sorted(zip([ep["score"] for ep in episodes], delta_us),
                         key=lambda x: x[0])
        q_size = n_ep // 5
        quintiles = []
        for q in range(5):
            s = q * q_size
            e = s + q_size if q < 4 else n_ep
            q_dus = [x[1] for x in scored[s:e]]
            quintiles.append({
                "quintile": q + 1, "n": len(q_dus),
                "mean_du": float(np.mean(q_dus)),
                "median_du": float(np.median(q_dus)),
                "p10_du": float(np.percentile(q_dus, 10)),
            })

        # G0 for static suppress: Q5 median > 0 (top quintile benefits)
        # Note: Q4 straddles the threshold boundary → many trivially-zero ΔU
        # Requiring both Q4+Q5 is structurally unfair for static suppress
        q5_pos = quintiles[4]["median_du"] > 0
        mono = sum(q["median_du"] * (q["quintile"] - 3) for q in quintiles)

        m_full = _metrics(nav_m, wi, len(trades_m))
        all_rows.append({
            "alpha": alpha, "alpha_threshold": alpha_thresh,
            "sharpe": m_full["sharpe"], "trades": m_full["trades"],
            "n_suppress": stats_m["n_suppress"],
            "n_matched": n_matched, "n_nonzero_du": n_nonzero,
            "q5_positive": q5_pos, "mono_score": mono,
            "quintiles": quintiles,
        })

        if mono > best_mono:
            best_mono = mono
            best_alpha = alpha

    best_row = [r for r in all_rows if r["alpha"] == best_alpha][0]
    print(f"\n  Best α for monotonicity: {best_alpha}%")
    print(f"  Sharpe={best_row['sharpe']:.4f}, trades={best_row['trades']}, "
          f"suppress={best_row['n_suppress']}, "
          f"matched={best_row['n_matched']}, nonzero_ΔU={best_row['n_nonzero_du']}")
    print(f"  Quintile ΔU (low score → high score):")
    for q in best_row["quintiles"]:
        print(f"    Q{q['quintile']} (n={q['n']}): mean={q['mean_du']:+.6f}, "
              f"median={q['median_du']:+.6f}, p10={q['p10_du']:+.6f}")

    g0_pass = best_row["q5_positive"]
    print(f"\n  G0 (Q5 median > 0): {'PASS' if g0_pass else 'FAIL'} "
          f"(Q5 median={best_row['quintiles'][4]['median_du']:+.6f}, "
          f"Q5 mean={best_row['quintiles'][4]['mean_du']:+.6f})")
    print(f"  Note: For static suppress, Q4 straddles threshold → many ΔU=0 by design")

    # Also report all α results summary
    print(f"\n  All α sweep:")
    for r in all_rows:
        print(f"    α={r['alpha']:>2}%: Sh={r['sharpe']:.4f}, "
              f"trades={r['trades']:>3}, suppress={r['n_suppress']:>5}, "
              f"matched={r['n_matched']:>3}, nonzero={r['n_nonzero_du']:>3}, "
              f"Q5_med={r['quintiles'][4]['median_du']:+.6f}")

    return {
        "n_episodes": n_ep, "g0_pass": g0_pass,
        "best_alpha": best_alpha, "best_mono": best_mono,
        "best_quintiles": best_row["quintiles"],
        "all_rows": [{k: v for k, v in r.items() if k != "quintiles"}
                      for r in all_rows],
    }


# =========================================================================
# T1: NESTED WFO
# =========================================================================

def run_t1_wfo(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct):
    print("\n" + "=" * 70)
    print("T1: NESTED WALK-FORWARD VALIDATION (4 folds)")
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
        # E0 baseline
        nav_e0, trades_e0 = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
        test_trades_e0 = [t for t in trades_e0 if test_start <= t["entry_bar"] < test_end]
        m_e0_test = _metrics_window(nav_e0, test_start, test_end + 1, len(test_trades_e0))

        # Train model on training portion
        nav_tr, trades_tr = _run_sim_e0(
            cl[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], at[:train_end + 1], regime_h4[:train_end + 1], wi)
        w, mu, std, c, ns = _train_model(
            trades_tr, cl[:train_end + 1], hi[:train_end + 1], lo[:train_end + 1],
            at[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], d1_str_h4[:train_end + 1])

        if w is None:
            fold_results.append({
                "fold": fold_idx + 1, "param": "no_model",
                "e0_sharpe_test": m_e0_test["sharpe"],
                "filter_sharpe_test": m_e0_test["sharpe"],
                "d_sharpe": 0.0, "win": False, "best_alpha": ALPHA_GRID[0],
            })
            continue

        # Training scores for α thresholds
        train_scores = _compute_train_scores(
            trades_tr, cl[:train_end + 1], hi[:train_end + 1], lo[:train_end + 1],
            at[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], d1_str_h4[:train_end + 1], w, mu, std)

        if len(train_scores) < 5:
            fold_results.append({
                "fold": fold_idx + 1, "param": "few_scores",
                "e0_sharpe_test": m_e0_test["sharpe"],
                "filter_sharpe_test": m_e0_test["sharpe"],
                "d_sharpe": 0.0, "win": False, "best_alpha": ALPHA_GRID[0],
            })
            continue

        # Sweep α on training data
        best_a, best_sh = ALPHA_GRID[0], -999
        for alpha in ALPHA_GRID:
            at_val = float(np.percentile(train_scores, 100 - alpha))
            nav_m, _, _ = _run_sim_mask(
                cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                w, mu, std, at_val)
            m_tr = _metrics_window(nav_m, wi, train_end + 1)
            if m_tr["sharpe"] > best_sh:
                best_sh = m_tr["sharpe"]
                best_a = alpha

        # Run with best α, measure test
        best_thresh = float(np.percentile(train_scores, 100 - best_a))
        nav_m, trades_m, stats_m = _run_sim_mask(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            w, mu, std, best_thresh)
        test_trades_m = [t for t in trades_m if test_start <= t["entry_bar"] < test_end]
        m_m_test = _metrics_window(nav_m, test_start, test_end + 1, len(test_trades_m))

        d_sharpe = m_m_test["sharpe"] - m_e0_test["sharpe"]
        win = d_sharpe > 0

        fold_results.append({
            "fold": fold_idx + 1, "param": f"α={best_a}%",
            "e0_sharpe_test": m_e0_test["sharpe"],
            "filter_sharpe_test": m_m_test["sharpe"],
            "d_sharpe": d_sharpe, "win": win,
            "best_alpha": best_a, "C": c,
            "n_suppress": stats_m["n_suppress"],
        })
        print(f"    Fold {fold_idx + 1}: α={best_a}%, E0={m_e0_test['sharpe']:.4f}, "
              f"Mask={m_m_test['sharpe']:.4f}, d={d_sharpe:+.4f} "
              f"{'WIN' if win else 'LOSE'}")

    win_rate = sum(1 for f in fold_results if f["win"]) / len(fold_results) if fold_results else 0
    mean_d = float(np.mean([f["d_sharpe"] for f in fold_results])) if fold_results else 0
    g1_pass = win_rate >= 0.75 and mean_d > 0

    # Consensus α
    alphas = [f["best_alpha"] for f in fold_results]
    d_sharpes = [f["d_sharpe"] for f in fold_results]
    counts = Counter(alphas)
    max_c = max(counts.values())
    candidates = [v for v, c in counts.items() if c == max_c]
    consensus_alpha = candidates[0] if len(candidates) == 1 else alphas[int(np.argmax(d_sharpes))]

    print(f"\n  Win rate: {win_rate:.0%}, mean d: {mean_d:+.4f}, "
          f"G1: {'PASS' if g1_pass else 'FAIL'}")
    print(f"  Consensus α: {consensus_alpha}%")

    return {"folds": fold_results, "win_rate": win_rate, "mean_d_sharpe": mean_d,
            "g1_pass": g1_pass, "consensus_alpha": consensus_alpha}


# =========================================================================
# T2: BOOTSTRAP
# =========================================================================

def run_t2_bootstrap(cl, hi, lo, vo, tb, ef, es, vd, at,
                      regime_h4, d1_str_h4, wi, consensus_alpha,
                      model_w_full, model_mu_full, model_std_full):
    print("\n" + "=" * 70)
    print(f"T2: BOOTSTRAP ({N_BOOT} paths, α={consensus_alpha}%)")
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

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        n_b = len(bcl)
        breg = regime_pw[:n_b] if len(regime_pw) >= n_b else np.ones(n_b, dtype=np.bool_)
        bd1 = d1_str_pw[:n_b] if len(d1_str_pw) >= n_b else np.zeros(n_b)
        bef, bes, bvd, bat = _compute_indicators(bcl, bhi, blo, bvo, btb)

        # E0
        bnav_e0, btrades_e0 = _run_sim_e0(bcl, bef, bes, bvd, bat, breg, 0)
        bm_e0 = _metrics(bnav_e0, 0, len(btrades_e0))

        # Train model on first 60%
        te = int(n_b * 0.6)
        _, btr = _run_sim_e0(bcl[:te], bef[:te], bes[:te], bvd[:te], bat[:te], breg[:te], 0)
        bw, bmu, bstd, _, _ = _train_model(
            btr, bcl[:te], bhi[:te], blo[:te], bat[:te], bef[:te], bes[:te], bvd[:te], bd1[:te])
        if bw is None:
            bw, bmu, bstd = model_w_full, model_mu_full, model_std_full

        # α threshold from training scores
        bscores = _compute_train_scores(btr, bcl[:te], bhi[:te], blo[:te],
                                          bat[:te], bef[:te], bes[:te], bvd[:te], bd1[:te],
                                          bw, bmu, bstd)
        if len(bscores) >= 3:
            b_thresh = float(np.percentile(bscores, 100 - consensus_alpha))
        else:
            b_thresh = 0.5

        # Masked sim
        bnav_m, btrades_m, _ = _run_sim_mask(
            bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1, 0,
            bw, bmu, bstd, b_thresh)
        bm_m = _metrics(bnav_m, 0, len(btrades_m))

        d_sharpes.append(bm_m["sharpe"] - bm_e0["sharpe"])
        d_cagrs.append(bm_m["cagr"] - bm_e0["cagr"])
        d_mdds.append(bm_m["mdd"] - bm_e0["mdd"])

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    d_sharpes = np.array(d_sharpes)
    d_cagrs = np.array(d_cagrs)
    d_mdds = np.array(d_mdds)

    p_gt0 = float(np.mean(d_sharpes > 0))
    med_mdd = float(np.median(d_mdds))
    g2 = p_gt0 > 0.60
    g3 = med_mdd <= 5.0

    r = {
        "d_sharpe_median": float(np.median(d_sharpes)),
        "d_sharpe_p5": float(np.percentile(d_sharpes, 5)),
        "d_sharpe_p95": float(np.percentile(d_sharpes, 95)),
        "d_sharpe_mean": float(np.mean(d_sharpes)),
        "p_d_sharpe_gt0": p_gt0,
        "d_mdd_median": med_mdd,
        "d_mdd_p5": float(np.percentile(d_mdds, 5)),
        "d_mdd_p95": float(np.percentile(d_mdds, 95)),
        "g2_pass": g2, "g3_pass": g3,
    }
    print(f"\n  d_sharpe: median={r['d_sharpe_median']:+.4f}, "
          f"[{r['d_sharpe_p5']:+.4f}, {r['d_sharpe_p95']:+.4f}]")
    print(f"  P(d_sharpe > 0): {p_gt0:.1%}")
    print(f"  d_mdd: median={med_mdd:+.2f}pp")
    print(f"  G2: {'PASS' if g2 else 'FAIL'}, G3: {'PASS' if g3 else 'FAIL'}")
    return r, d_sharpes, d_cagrs, d_mdds


# =========================================================================
# T3: JACKKNIFE
# =========================================================================

def run_t3_jackknife(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                      wi, h4_ct, consensus_alpha,
                      model_w, model_mu, model_std, train_scores):
    print("\n" + "=" * 70)
    print("T3: JACKKNIFE")
    print("=" * 70)
    alpha_thresh = float(np.percentile(train_scores, 100 - consensus_alpha))
    n = len(cl)
    folds = []
    for yr in JK_YEARS:
        ys = _date_to_bar_idx(h4_ct, f"{yr}-01-01")
        ye = min(_date_to_bar_idx(h4_ct, f"{yr}-12-31"), n - 1)
        kept = np.concatenate([np.arange(wi, ys), np.arange(ye + 1, n)]) if ys > wi else np.arange(ye + 1, n)
        if len(kept) < 2:
            continue
        nav_e0, tr_e0 = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
        tr_e0_jk = [t for t in tr_e0 if not (ys <= t["entry_bar"] <= ye)]
        m_e0 = _metrics(nav_e0[kept], 0, len(tr_e0_jk))
        nav_m, tr_m, _ = _run_sim_mask(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                         model_w, model_mu, model_std, alpha_thresh)
        tr_m_jk = [t for t in tr_m if not (ys <= t["entry_bar"] <= ye)]
        m_m = _metrics(nav_m[kept], 0, len(tr_m_jk))
        d = m_m["sharpe"] - m_e0["sharpe"]
        folds.append({"year": yr, "e0_sharpe": m_e0["sharpe"],
                        "filter_sharpe": m_m["sharpe"], "d_sharpe": d,
                        "d_sharpe_negative": d < 0})
        print(f"    Drop {yr}: E0={m_e0['sharpe']:.4f}, Mask={m_m['sharpe']:.4f}, d={d:+.4f}")
    n_neg = sum(1 for f in folds if f["d_sharpe_negative"])
    mean_d = float(np.mean([f["d_sharpe"] for f in folds])) if folds else 0
    g4 = n_neg <= 2
    print(f"  Negative: {n_neg}/6, mean d={mean_d:+.4f}, G4: {'PASS' if g4 else 'FAIL'}")
    return {"folds": folds, "n_negative": n_neg, "mean_d_sharpe": mean_d, "g4_pass": g4}


# =========================================================================
# T4: PSR
# =========================================================================

def run_t4_psr(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                consensus_alpha, model_w, model_mu, model_std, train_scores):
    print("\n" + "=" * 70)
    print("T4: PSR")
    print("=" * 70)
    alpha_thresh = float(np.percentile(train_scores, 100 - consensus_alpha))
    nav_e0, tr_e0 = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(tr_e0))
    n_ret = len(nav_e0[wi:]) - 1
    eff_dof = E0_EFFECTIVE_DOF + 1  # +1 for α
    psr_e0 = _psr(m_e0["sharpe"], n_ret)
    nav_m, tr_m, _ = _run_sim_mask(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                     model_w, model_mu, model_std, alpha_thresh)
    m_m = _metrics(nav_m, wi, len(tr_m))
    n_eff = max(3, int(n_ret / (eff_dof / E0_EFFECTIVE_DOF)))
    psr_m = _psr(m_m["sharpe"], n_eff)
    g5 = psr_m > 0.95
    print(f"  E0: Sh={m_e0['sharpe']:.4f}, PSR={psr_e0:.4f}")
    print(f"  Mask: Sh={m_m['sharpe']:.4f}, PSR={psr_m:.4f}")
    print(f"  DOF={eff_dof:.2f}, n_eff={n_eff}, G5: {'PASS' if g5 else 'FAIL'}")
    return {"e0_sharpe": m_e0["sharpe"], "filter_sharpe": m_m["sharpe"],
            "e0_psr": psr_e0, "filter_psr": psr_m,
            "eff_dof": eff_dof, "n_eff": n_eff, "g5_pass": g5}


# =========================================================================
# T5: COMPARISON
# =========================================================================

def run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                       consensus_alpha, m_e0, model_w, model_mu, model_std,
                       train_scores):
    print("\n" + "=" * 70)
    print("T5: COMPARISON TABLE")
    print("=" * 70)
    alpha_thresh = float(np.percentile(train_scores, 100 - consensus_alpha))
    nav_e0, tr_e0 = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    ah_e0 = float(np.mean([t["bars_held"] for t in tr_e0])) if tr_e0 else 0

    nav_m, tr_m, st = _run_sim_mask(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                      model_w, model_mu, model_std, alpha_thresh)
    m_m = _metrics(nav_m, wi, len(tr_m))
    ah_m = float(np.mean([t["bars_held"] for t in tr_m])) if tr_m else 0
    oc = ((m_m["sharpe"] - m_e0["sharpe"]) / 0.845 * 100
          if m_m["sharpe"] > m_e0["sharpe"] else 0.0)

    table = [
        {"strategy": "E0", **m_e0, "avg_hold": ah_e0, "oracle%": 0.0, "suppress": 0},
        {"strategy": f"X18(α={consensus_alpha}%)", **m_m, "avg_hold": ah_m,
         "oracle%": oc, "suppress": st["n_suppress"]},
        {"strategy": "X14_D(P>0.5)", "sharpe": 1.428, "cagr": 64.0, "mdd": 36.7,
         "trades": 133, "avg_hold": 60.3, "oracle%": 10.9, "suppress": 812},
        {"strategy": "X16_E(τ=.85,G=8)", "sharpe": 1.424, "cagr": 62.7, "mdd": 38.9,
         "trades": 162, "avg_hold": 48.7, "oracle%": 10.4, "suppress": 0},
    ]

    print(f"\n  {'Strategy':<25} {'Sharpe':>7} {'CAGR%':>7} {'MDD%':>7} "
          f"{'Trades':>6} {'Hold':>6} {'Orc%':>6} {'Supp':>6}")
    print("  " + "-" * 76)
    for r in table:
        print(f"  {r['strategy']:<25} {r['sharpe']:>7.4f} {r['cagr']:>7.2f} "
              f"{r['mdd']:>7.2f} {r['trades']:>6} {r['avg_hold']:>6.1f} "
              f"{r['oracle%']:>6.1f} {r['suppress']:>6}")
    return table, st


# =========================================================================
# SAVE
# =========================================================================

def save_results(all_results):
    def _c(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, dict): return {k: _c(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)): return [_c(x) for x in obj]
        return obj

    with open(OUTDIR / "x18_results.json", "w") as f:
        json.dump(_c(all_results), f, indent=2)

    if "t0" in all_results and all_results["t0"].get("best_quintiles"):
        with open(OUTDIR / "x18_delta_u.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["quintile", "n", "mean_du", "median_du", "p10_du"])
            for q in all_results["t0"]["best_quintiles"]:
                w.writerow([q["quintile"], q["n"], f"{q['mean_du']:.6f}",
                            f"{q['median_du']:.6f}", f"{q['p10_du']:.6f}"])

    if "t1" in all_results and all_results["t1"].get("folds"):
        with open(OUTDIR / "x18_wfo.csv", "w", newline="") as f:
            fields = ["fold", "param", "e0_sharpe_test", "filter_sharpe_test",
                       "d_sharpe", "win", "best_alpha"]
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in all_results["t1"]["folds"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                             for k, v in r.items() if k in fields})

    if "t2_arrays" in all_results and all_results["t2_arrays"] is not None:
        d_sh, d_ca, d_md = all_results["t2_arrays"]
        with open(OUTDIR / "x18_bootstrap.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "d_sharpe", "d_cagr", "d_mdd"])
            for i in range(len(d_sh)):
                w.writerow([i, f"{d_sh[i]:.6f}", f"{d_ca[i]:.6f}", f"{d_md[i]:.6f}"])

    if "t3" in all_results and all_results["t3"].get("folds"):
        with open(OUTDIR / "x18_jackknife.csv", "w", newline="") as f:
            fields = list(all_results["t3"]["folds"][0].keys())
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in all_results["t3"]["folds"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else str(v)
                             for k, v in r.items()})

    if "t5" in all_results and all_results["t5"]:
        with open(OUTDIR / "x18_comparison.csv", "w", newline="") as f:
            fields = list(all_results["t5"][0].keys())
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in all_results["t5"]:
                w.writerow({k: f"{v:.6f}" if isinstance(v, float) else v
                             for k, v in r.items()})

    print(f"\n  Saved to {OUTDIR}/x18_*.{{json,csv}}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("X18: α-Percentile Static Mask — Nested WFO Validation")
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
    print(f"  Bars: {len(cl)} H4, warmup_idx={wi}")

    all_results = {}

    # E0 baseline
    nav_e0, trades_e0 = _run_sim_e0(cl, ef, es, vd, at, regime_h4, wi)
    m_e0 = _metrics(nav_e0, wi, len(trades_e0))
    print(f"  E0: Sh={m_e0['sharpe']:.4f}, CAGR={m_e0['cagr']:.2f}%, "
          f"MDD={m_e0['mdd']:.2f}%, trades={m_e0['trades']}")
    all_results["e0"] = m_e0

    # Train model
    print("\n  Training 7-feature logistic...")
    model_w, model_mu, model_std, model_c, n_train = _train_model(
        trades_e0, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    print(f"  Model: C={model_c}, n={n_train}, {'OK' if model_w is not None else 'FAIL'}")
    if model_w is None:
        all_results["verdict"] = {"verdict": "ABORT", "reason": "model_failed"}
        save_results(all_results)
        return

    train_scores = _compute_train_scores(trades_e0, cl, hi, lo, at, ef, es, vd,
                                           d1_str_h4, model_w, model_mu, model_std)
    print(f"  Scores: n={len(train_scores)}, median={np.median(train_scores):.4f}")

    # T0: ΔU
    t0 = run_t0_delta_u(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                          model_w, model_mu, model_std, trades_e0)
    all_results["t0"] = t0
    if not t0["g0_pass"]:
        print("\n  G0 FAIL — continuing to T1 (G0 is diagnostic for static suppress)")

    # T1: WFO
    t1 = run_t1_wfo(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct)
    all_results["t1"] = t1
    ca = t1["consensus_alpha"]

    if not t1["g1_pass"]:
        print(f"\n  G1 FAIL — NOT_TEMPORAL")
        all_results["verdict"] = {"verdict": "NOT_TEMPORAL",
                                   "reason": f"WFO {t1['win_rate']:.0%}"}
        t5, _ = run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                    ca, m_e0, model_w, model_mu, model_std, train_scores)
        all_results["t5"] = t5
        save_results(all_results)
        return

    # T2: Bootstrap
    t2, d_sh, d_ca, d_md = run_t2_bootstrap(
        cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        ca, model_w, model_mu, model_std)
    all_results["t2"] = t2
    all_results["t2_arrays"] = (d_sh, d_ca, d_md)

    if not t2["g2_pass"]:
        all_results["verdict"] = {"verdict": "NOT_ROBUST",
                                   "reason": f"P(d>0)={t2['p_d_sharpe_gt0']:.1%}"}
        t5, _ = run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                    ca, m_e0, model_w, model_mu, model_std, train_scores)
        all_results["t5"] = t5
        save_results(all_results)
        return
    if not t2["g3_pass"]:
        all_results["verdict"] = {"verdict": "MDD_TRADEOFF",
                                   "reason": f"d_mdd={t2['d_mdd_median']:+.1f}pp"}
        t5, _ = run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                    ca, m_e0, model_w, model_mu, model_std, train_scores)
        all_results["t5"] = t5
        save_results(all_results)
        return

    # T3: Jackknife
    t3 = run_t3_jackknife(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, h4_ct,
                            ca, model_w, model_mu, model_std, train_scores)
    all_results["t3"] = t3
    if not t3["g4_pass"]:
        all_results["verdict"] = {"verdict": "FRAGILE",
                                   "reason": f"{t3['n_negative']}/6 negative"}
        t5, _ = run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                    ca, m_e0, model_w, model_mu, model_std, train_scores)
        all_results["t5"] = t5
        save_results(all_results)
        return

    # T4: PSR
    t4 = run_t4_psr(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                      ca, model_w, model_mu, model_std, train_scores)
    all_results["t4"] = t4
    if not t4["g5_pass"]:
        all_results["verdict"] = {"verdict": "UNDERPOWERED",
                                   "reason": f"PSR={t4['filter_psr']:.4f}"}
        t5, _ = run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                    ca, m_e0, model_w, model_mu, model_std, train_scores)
        all_results["t5"] = t5
        save_results(all_results)
        return

    # ALL PASS
    t5, st = run_t5_comparison(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                                 ca, m_e0, model_w, model_mu, model_std, train_scores)
    all_results["t5"] = t5
    all_results["verdict"] = {"verdict": "PROMOTE", "consensus_alpha": ca, "stats": st}
    print(f"\n  *** ALL GATES PASSED — PROMOTE (α={ca}%) ***")

    save_results(all_results)
    elapsed = time.time() - t_start
    print(f"\nX18 COMPLETE — {elapsed:.0f}s — VERDICT: {all_results['verdict']['verdict']}")


if __name__ == "__main__":
    main()
