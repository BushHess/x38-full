#!/usr/bin/env python3
"""X29: Optimal Stack — Combination of Validated Overlays on E5+EMA1D21

Factorial optimization: 2 (Monitor) × 3 (Churn) × 2 (Trail) = 12 strategies
Swept across 9 cost levels = 108 backtests.

Tests:
  T0: Full-sample matrix (108 backtests)
  T1: Interaction analysis (factorial decomposition)
  T2: WFO 4-fold (top strategies)
  T3: Bootstrap VCBB (top strategies)
  T4: Cost-crossover map
  T5: Dominance / Pareto analysis

All parameters frozen from prior studies. ZERO new DOF.
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

ROOT = Path(__file__).resolve().parents[3]
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
D1_EMA_P = 21

# E5 robust ATR
RATR_P = 20
RATR_Q = 0.90
RATR_LB = 100

# Churn filter
CHURN_WINDOW = 20
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
X18_ALPHA = 40

# Cost sweep (9 levels per SPEC)
COST_BPS = [10, 15, 20, 25, 30, 35, 50, 75, 100]
PRIMARY_COST = 25

# Trail multipliers
TRAIL_30 = 3.0
TRAIL_45 = 4.5

# WFO folds (same as X14/X18/X22)
WFO_FOLDS = [
    ("2021-12-31", "2022-01-01", "2022-12-31"),
    ("2022-12-31", "2023-01-01", "2023-12-31"),
    ("2023-12-31", "2024-01-01", "2024-12-31"),
    ("2024-12-31", "2025-01-01", "2026-02-20"),
]

# Bootstrap
N_BOOT = 500
BLKSZ = 60
SEED = 42

# Regime Monitor V2 thresholds (frozen from prod_readiness)
ROLL_6M = 180
ROLL_12M = 360
RED_MDD_6M = 0.55
RED_MDD_12M = 0.70

# Output
OUTDIR = Path(__file__).resolve().parents[1]

# =========================================================================
# 12-STRATEGY FACTORIAL DESIGN
# =========================================================================

STRATEGIES = [
    {"id": "S01", "name": "Base",            "monitor": False, "churn": "none", "trail": 3.0},
    {"id": "S02", "name": "Base+T45",        "monitor": False, "churn": "none", "trail": 4.5},
    {"id": "S03", "name": "X14D",            "monitor": False, "churn": "x14d", "trail": 3.0},
    {"id": "S04", "name": "X14D+T45",        "monitor": False, "churn": "x14d", "trail": 4.5},
    {"id": "S05", "name": "X18",             "monitor": False, "churn": "x18",  "trail": 3.0},
    {"id": "S06", "name": "X18+T45",         "monitor": False, "churn": "x18",  "trail": 4.5},
    {"id": "S07", "name": "Mon",             "monitor": True,  "churn": "none", "trail": 3.0},
    {"id": "S08", "name": "Mon+T45",         "monitor": True,  "churn": "none", "trail": 4.5},
    {"id": "S09", "name": "Mon+X14D",        "monitor": True,  "churn": "x14d", "trail": 3.0},
    {"id": "S10", "name": "Mon+X14D+T45",    "monitor": True,  "churn": "x14d", "trail": 4.5},
    {"id": "S11", "name": "Mon+X18",         "monitor": True,  "churn": "x18",  "trail": 3.0},
    {"id": "S12", "name": "Mon+X18+T45",     "monitor": True,  "churn": "x18",  "trail": 4.5},
]


# =========================================================================
# INDICATORS (from X22, vectorized)
# =========================================================================

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _robust_atr(high, low, close, cap_q=RATR_Q, cap_lb=RATR_LB, period=RATR_P):
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


# =========================================================================
# REGIME MONITOR V2 (from monitoring/regime_monitor.py)
# =========================================================================

def _rolling_mdd(close, window):
    n = len(close)
    mdd = np.full(n, np.nan)
    for t in range(window - 1, n):
        seg = close[t - window + 1: t + 1]
        peak = np.maximum.accumulate(seg)
        dd = 1.0 - seg / peak
        mdd[t] = np.max(dd)
    return mdd


def _compute_monitor_alerts(d1_cl):
    """Compute Monitor V2 alerts on D1 bars (0=NORMAL, 2=RED)."""
    mdd_6m = _rolling_mdd(d1_cl, ROLL_6M)
    mdd_12m = _rolling_mdd(d1_cl, ROLL_12M)
    n = len(d1_cl)
    alerts = np.zeros(n, dtype=np.int8)
    for t in range(n):
        m6 = mdd_6m[t] if not np.isnan(mdd_6m[t]) else 0.0
        m12 = mdd_12m[t] if not np.isnan(mdd_12m[t]) else 0.0
        if m6 > RED_MDD_6M or m12 > RED_MDD_12M:
            alerts[t] = 2
    return alerts


def _map_d1_alert_to_h4(d1_alerts, d1_ct, h4_ct):
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
# CHURN MODEL (L2-penalized logistic, 7 features — from X22)
# =========================================================================

def _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4, trail_mult):
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
                                   d1_str_h4, trail_mult=TRAIL_30):
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


def _predict_score(feat, w, mu, std):
    feat_s = (feat - mu) / std
    z = np.dot(np.append(feat_s, 1.0), w)
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))


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
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4, TRAIL_30)
        scores.append(_predict_score(feat, model_w, model_mu, model_std))
    return np.array(scores)


# =========================================================================
# METRICS
# =========================================================================

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
    # Additional: exposure, win rate, avg hold
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
            "trades": nt, "final_nav": float(navs[-1])}


def _metrics_window(nav, start_idx, end_idx, nt=0):
    navs = nav[start_idx:end_idx]
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
    calmar = cagr / mdd if mdd > 0 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar, "trades": nt}


def _trade_stats(trades):
    """Compute win_rate, avg_winner, avg_loser, profit_factor, avg_hold, exposure."""
    if not trades:
        return {"win_rate": 0.0, "avg_winner": 0.0, "avg_loser": 0.0,
                "profit_factor": 0.0, "avg_hold": 0.0, "exposure_bars": 0}
    winners = [t for t in trades if t["pnl_usd"] > 0]
    losers = [t for t in trades if t["pnl_usd"] <= 0]
    wr = len(winners) / len(trades) if trades else 0.0
    aw = np.mean([t["ret_pct"] for t in winners]) if winners else 0.0
    al = np.mean([t["ret_pct"] for t in losers]) if losers else 0.0
    gross_profit = sum(t["pnl_usd"] for t in winners)
    gross_loss = abs(sum(t["pnl_usd"] for t in losers))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    ah = np.mean([t["bars_held"] for t in trades])
    exp_bars = sum(t["bars_held"] for t in trades)
    return {"win_rate": wr, "avg_winner": aw, "avg_loser": al,
            "profit_factor": pf, "avg_hold": ah, "exposure_bars": exp_bars}


def _date_to_bar_idx(h4_ct, date_str):
    import datetime
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ts_ms = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    idx = np.searchsorted(h4_ct, ts_ms, side='left')
    return min(idx, len(h4_ct) - 1)


# =========================================================================
# UNIFIED SIMULATION ENGINE
# =========================================================================

def _run_sim(cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
             monitor_h4, wi, trail_mult=3.0, cps=0.0025,
             use_monitor=False, churn_type="none",
             model_w=None, model_mu=None, model_std=None,
             churn_threshold=None):
    """Unified sim: E5+EMA1D21 with optional Monitor V2, churn filter, trail mult.

    Parameters
    ----------
    use_monitor : bool
        If True, block entries when monitor_h4[i] == 2 (RED).
    churn_type : str
        "none", "x14d", "x18" — whether to suppress trail stops.
    churn_threshold : float
        Score threshold for churn suppress (X14D=0.5, X18=alpha-percentile).
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    pk = 0.0
    entry_bar = 0
    entry_px = 0.0
    entry_cost = 0.0
    exit_reason = ""

    nav = np.zeros(n)
    trades = []
    n_suppress = 0
    n_monitor_blocks = 0

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
                ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp,
                    "peak_px": pk, "pnl_usd": pnl, "ret_pct": ret_pct,
                    "bars_held": i - entry_bar, "exit_reason": exit_reason,
                })
                cash = received
                bq = 0.0
                inp = False
                pk = 0.0

        nav[i] = cash + bq * p
        a_val = at_e5[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        monitor_red = use_monitor and monitor_h4 is not None and monitor_h4[i] == 2

        if not inp:
            # ENTRY: trend up + VDO + D1 regime + not RED
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                if monitor_red:
                    n_monitor_blocks += 1
                else:
                    pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * a_val
            if p < ts:
                # Trail fires — check churn filter
                if churn_type != "none" and model_w is not None:
                    feat = _extract_features_7(i, cl, hi, lo, at_e5, ef, es, vd,
                                                d1_str_h4, trail_mult)
                    score = _predict_score(feat, model_w, model_mu, model_std)
                    if score > churn_threshold:
                        n_suppress += 1
                    else:
                        exit_reason = "trail_stop"
                        px = True
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
        ret_pct = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1],
            "peak_px": pk, "pnl_usd": pnl, "ret_pct": ret_pct,
            "bars_held": (n - 1) - entry_bar, "exit_reason": "end_of_data",
        })
        cash = received
        bq = 0.0
        nav[-1] = cash

    stats = {"n_suppress": n_suppress, "n_monitor_blocks": n_monitor_blocks,
             "n_trades": len(trades)}
    return nav, trades, stats


def _run_strategy(strat, cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
                  monitor_h4, wi, cps,
                  model_w, model_mu, model_std,
                  x14d_thresh, x18_thresh):
    """Run a single strategy config at a given cost."""
    churn_thresh = None
    if strat["churn"] == "x14d":
        churn_thresh = x14d_thresh
    elif strat["churn"] == "x18":
        churn_thresh = x18_thresh

    nav, trades, stats = _run_sim(
        cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
        monitor_h4, wi, trail_mult=strat["trail"], cps=cps,
        use_monitor=strat["monitor"], churn_type=strat["churn"],
        model_w=model_w, model_mu=model_mu, model_std=model_std,
        churn_threshold=churn_thresh)
    return nav, trades, stats


# =========================================================================
# T0: FULL-SAMPLE MATRIX (108 backtests)
# =========================================================================

def run_t0(cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
           monitor_h4, wi, model_w, model_mu, model_std,
           x14d_thresh, x18_thresh):
    """12 strategies × 9 costs = 108 backtests."""
    print("\n" + "=" * 70)
    print("T0: Full-Sample Matrix (108 backtests)")
    print("=" * 70)

    n = len(cl)
    yrs = (n - wi) / (6.0 * 365.25)
    rows = []
    all_navs = {}  # (strat_id, cost_bps) -> nav for later use

    for strat in STRATEGIES:
        for cost_bps in COST_BPS:
            cps = cost_bps / 20_000.0
            nav, trades, stats = _run_strategy(
                strat, cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
                monitor_h4, wi, cps,
                model_w, model_mu, model_std, x14d_thresh, x18_thresh)

            m = _metrics(nav, wi, len(trades))
            ts = _trade_stats(trades)
            exposure = ts["exposure_bars"] / (n - wi) * 100 if (n - wi) > 0 else 0.0

            row = {
                "strategy_id": strat["id"],
                "strategy_name": strat["name"],
                "cost_bps": cost_bps,
                "sharpe": m["sharpe"],
                "cagr": m["cagr"],
                "mdd": m["mdd"],
                "calmar": m["calmar"],
                "n_trades": m["trades"],
                "exposure": exposure,
                "win_rate": ts["win_rate"],
                "avg_winner": ts["avg_winner"],
                "avg_loser": ts["avg_loser"],
                "profit_factor": ts["profit_factor"],
                "avg_hold": ts["avg_hold"],
                "suppressions": stats["n_suppress"],
                "monitor_blocks": stats["n_monitor_blocks"],
            }
            rows.append(row)
            all_navs[(strat["id"], cost_bps)] = nav

        # Print summary line at primary cost
        r25 = next(r for r in rows if r["strategy_id"] == strat["id"] and r["cost_bps"] == PRIMARY_COST)
        print(f"  {strat['id']:3s} {strat['name']:16s} @{PRIMARY_COST}bps: "
              f"Sh={r25['sharpe']:.3f} CAGR={r25['cagr']:.1f}% MDD={r25['mdd']:.1f}% "
              f"T={r25['n_trades']} Sup={r25['suppressions']} MonBlk={r25['monitor_blocks']}")

    # Write CSV
    csv_path = OUTDIR / "tables" / "Tbl_full_matrix.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy_id", "strategy_name", "cost_bps", "sharpe", "cagr", "mdd",
                     "calmar", "n_trades", "exposure", "win_rate", "avg_winner", "avg_loser",
                     "profit_factor", "avg_hold", "suppressions", "monitor_blocks"])
        for r in rows:
            w.writerow([r["strategy_id"], r["strategy_name"], r["cost_bps"],
                        f"{r['sharpe']:.4f}", f"{r['cagr']:.2f}", f"{r['mdd']:.2f}",
                        f"{r['calmar']:.4f}", r["n_trades"], f"{r['exposure']:.1f}",
                        f"{r['win_rate']:.3f}", f"{r['avg_winner']:.2f}", f"{r['avg_loser']:.2f}",
                        f"{r['profit_factor']:.2f}", f"{r['avg_hold']:.1f}",
                        r["suppressions"], r["monitor_blocks"]])
    print(f"\n  Saved: {csv_path}")

    # Gate T0: at least 1 combo beats S01 at each cost level
    gate_pass = True
    for cost_bps in COST_BPS:
        base_sh = next(r["sharpe"] for r in rows
                       if r["strategy_id"] == "S01" and r["cost_bps"] == cost_bps)
        best_other = max(r["sharpe"] for r in rows
                         if r["strategy_id"] != "S01" and r["cost_bps"] == cost_bps)
        if best_other <= base_sh:
            gate_pass = False
            print(f"  Gate T0 FAIL: no combo beats Base at {cost_bps} bps "
                  f"(base={base_sh:.4f}, best={best_other:.4f})")

    print(f"\n  Gate T0: {'PASS' if gate_pass else 'FAIL'}")
    return rows, all_navs, gate_pass


# =========================================================================
# T0 FIGURES
# =========================================================================

def _plot_t0_figures(rows):
    """Generate T0 heatmaps and line plots."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  [WARN] matplotlib not available, skipping figures")
        return

    strat_ids = [s["id"] for s in STRATEGIES]
    strat_names = [s["name"] for s in STRATEGIES]

    # Build matrices
    sharpe_mat = np.zeros((len(strat_ids), len(COST_BPS)))
    mdd_mat = np.zeros_like(sharpe_mat)
    for r in rows:
        si = strat_ids.index(r["strategy_id"])
        ci = COST_BPS.index(r["cost_bps"])
        sharpe_mat[si, ci] = r["sharpe"]
        mdd_mat[si, ci] = r["mdd"]

    # Fig 1: Sharpe heatmap
    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(sharpe_mat, aspect="auto", cmap="RdYlGn")
    ax.set_xticks(range(len(COST_BPS)))
    ax.set_xticklabels([str(c) for c in COST_BPS])
    ax.set_yticks(range(len(strat_names)))
    ax.set_yticklabels(strat_names, fontsize=9)
    ax.set_xlabel("Cost (bps RT)")
    ax.set_title("X29: Sharpe Ratio (Strategy × Cost)")
    for si in range(len(strat_ids)):
        for ci in range(len(COST_BPS)):
            ax.text(ci, si, f"{sharpe_mat[si, ci]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_sharpe_heatmap.png", dpi=150)
    plt.close(fig)

    # Fig 2: MDD heatmap
    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(mdd_mat, aspect="auto", cmap="RdYlGn_r")
    ax.set_xticks(range(len(COST_BPS)))
    ax.set_xticklabels([str(c) for c in COST_BPS])
    ax.set_yticks(range(len(strat_names)))
    ax.set_yticklabels(strat_names, fontsize=9)
    ax.set_xlabel("Cost (bps RT)")
    ax.set_title("X29: Max Drawdown % (Strategy × Cost)")
    for si in range(len(strat_ids)):
        for ci in range(len(COST_BPS)):
            ax.text(ci, si, f"{mdd_mat[si, ci]:.1f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_mdd_heatmap.png", dpi=150)
    plt.close(fig)

    # Fig 3: Sharpe vs cost line plot
    fig, ax = plt.subplots(figsize=(12, 7))
    colors = plt.cm.tab20(np.linspace(0, 1, 12))
    for si, sname in enumerate(strat_names):
        ax.plot(COST_BPS, sharpe_mat[si, :], marker="o", markersize=4,
                label=sname, color=colors[si])
    ax.set_xlabel("Cost (bps RT)")
    ax.set_ylabel("Sharpe")
    ax.set_title("X29: Sharpe vs Cost per Strategy")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_sharpe_vs_cost.png", dpi=150)
    plt.close(fig)

    # Fig 4: Pareto (Sharpe vs MDD) at primary cost
    fig, ax = plt.subplots(figsize=(10, 7))
    pc_rows = [r for r in rows if r["cost_bps"] == PRIMARY_COST]
    for r in pc_rows:
        si = strat_ids.index(r["strategy_id"])
        ax.scatter(r["mdd"], r["sharpe"], color=colors[si], s=80, zorder=5)
        ax.annotate(r["strategy_name"], (r["mdd"], r["sharpe"]),
                    fontsize=7, textcoords="offset points", xytext=(5, 5))
    ax.set_xlabel("MDD (%)")
    ax.set_ylabel("Sharpe")
    ax.set_title(f"X29: Sharpe vs MDD at {PRIMARY_COST} bps")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_pareto.png", dpi=150)
    plt.close(fig)
    print("  T0 figures saved.")


# =========================================================================
# T1: INTERACTION ANALYSIS
# =========================================================================

def run_t1(rows):
    """Factorial interaction decomposition at each cost level."""
    print("\n" + "=" * 70)
    print("T1: Interaction Analysis (factorial decomposition)")
    print("=" * 70)

    def sh(sid, cost):
        return next(r["sharpe"] for r in rows
                    if r["strategy_id"] == sid and r["cost_bps"] == cost)

    interactions = []
    max_abs = 0.0

    for cost_bps in COST_BPS:
        base = sh("S01", cost_bps)

        # Pair 1: Monitor × X14D
        # I(A,B) = Sh(A+B) - Sh(A) - Sh(B) + Sh(base)
        ia_mon_x14d = sh("S09", cost_bps) - sh("S07", cost_bps) - sh("S03", cost_bps) + base
        # Pair 2: Monitor × X18
        ia_mon_x18 = sh("S11", cost_bps) - sh("S07", cost_bps) - sh("S05", cost_bps) + base
        # Pair 3: Monitor × Trail4.5
        ia_mon_t45 = sh("S08", cost_bps) - sh("S07", cost_bps) - sh("S02", cost_bps) + base
        # Pair 4: X14D × Trail4.5
        ia_x14d_t45 = sh("S04", cost_bps) - sh("S03", cost_bps) - sh("S02", cost_bps) + base
        # Pair 5: X18 × Trail4.5
        ia_x18_t45 = sh("S06", cost_bps) - sh("S05", cost_bps) - sh("S02", cost_bps) + base

        # 3-way: Monitor × X14D × Trail4.5
        # I3 = Sh(ABC) - Sh(AB) - Sh(AC) - Sh(BC) + Sh(A) + Sh(B) + Sh(C) - Sh(base)
        ia3_mon_x14d_t45 = (sh("S10", cost_bps)
                            - sh("S09", cost_bps) - sh("S08", cost_bps) - sh("S04", cost_bps)
                            + sh("S07", cost_bps) + sh("S03", cost_bps) + sh("S02", cost_bps)
                            - base)
        # 3-way: Monitor × X18 × Trail4.5
        ia3_mon_x18_t45 = (sh("S12", cost_bps)
                           - sh("S11", cost_bps) - sh("S08", cost_bps) - sh("S06", cost_bps)
                           + sh("S07", cost_bps) + sh("S05", cost_bps) + sh("S02", cost_bps)
                           - base)

        row = {
            "cost_bps": cost_bps,
            "Mon×X14D": ia_mon_x14d,
            "Mon×X18": ia_mon_x18,
            "Mon×T45": ia_mon_t45,
            "X14D×T45": ia_x14d_t45,
            "X18×T45": ia_x18_t45,
            "Mon×X14D×T45": ia3_mon_x14d_t45,
            "Mon×X18×T45": ia3_mon_x18_t45,
        }
        interactions.append(row)

        for k, v in row.items():
            if k != "cost_bps":
                max_abs = max(max_abs, abs(v))

        if cost_bps == PRIMARY_COST:
            print(f"  @{cost_bps} bps interactions:")
            for k, v in row.items():
                if k != "cost_bps":
                    flag = " ***" if abs(v) > 0.10 else ""
                    print(f"    {k:20s}: {v:+.4f}{flag}")

    # Write CSV
    csv_path = OUTDIR / "tables" / "Tbl_interactions.csv"
    pair_names = ["Mon×X14D", "Mon×X18", "Mon×T45", "X14D×T45", "X18×T45",
                  "Mon×X14D×T45", "Mon×X18×T45"]
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cost_bps"] + pair_names)
        for r in interactions:
            w.writerow([r["cost_bps"]] + [f"{r[p]:.4f}" for p in pair_names])
    print(f"  Saved: {csv_path}")

    # Gate T1: |interaction| < 0.10 for majority cost levels
    gate_pass = True
    for pair in pair_names:
        n_above = sum(1 for r in interactions if abs(r[pair]) > 0.10)
        if n_above > len(COST_BPS) // 2:
            print(f"  Gate T1 WARN: {pair} has |interaction| > 0.10 in {n_above}/{len(COST_BPS)} costs")
            gate_pass = False
    print(f"  Max |interaction|: {max_abs:.4f}")
    print(f"  Gate T1: {'PASS' if gate_pass else 'WARN (strong interference)'}")

    # Figure
    _plot_t1_figure(interactions, pair_names)
    return interactions, gate_pass


def _plot_t1_figure(interactions, pair_names):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig, ax = plt.subplots(figsize=(12, 7))
    for pair in pair_names:
        vals = [r[pair] for r in interactions]
        ax.plot(COST_BPS, vals, marker="o", markersize=4, label=pair)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.axhline(0.10, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.axhline(-0.10, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax.set_xlabel("Cost (bps RT)")
    ax.set_ylabel("Interaction Term (Sharpe)")
    ax.set_title("X29 T1: Interaction Effects vs Cost")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_interaction_by_cost.png", dpi=150)
    plt.close(fig)


# =========================================================================
# T2: WALK-FORWARD OPTIMIZATION (4-fold)
# =========================================================================

def run_t2(t0_rows, cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
           monitor_h4, h4_ct, wi,
           model_w, model_mu, model_std, x14d_thresh, x18_thresh):
    """WFO 4-fold for top strategies at primary cost."""
    print("\n" + "=" * 70)
    print("T2: Walk-Forward Optimization (4-fold)")
    print("=" * 70)

    cps = PRIMARY_COST / 20_000.0

    # Select top-6 from T0 at primary cost
    pc_rows = [r for r in t0_rows if r["cost_bps"] == PRIMARY_COST]
    by_sharpe = sorted(pc_rows, key=lambda r: r["sharpe"], reverse=True)[:3]
    by_mdd = sorted(pc_rows, key=lambda r: r["mdd"])[:3]
    top_ids = list(dict.fromkeys(
        [r["strategy_id"] for r in by_sharpe] + [r["strategy_id"] for r in by_mdd]))
    # Add S01, S07 as benchmarks
    for bench in ["S01", "S07"]:
        if bench not in top_ids:
            top_ids.append(bench)
    top_strats = [s for s in STRATEGIES if s["id"] in top_ids]

    print(f"  Top strategies for WFO: {[s['name'] for s in top_strats]}")

    wfo_results = []
    n_bars = len(cl)

    for strat in top_strats:
        wins = 0
        fold_results = []
        for fold_idx, (train_end, test_start, test_end) in enumerate(WFO_FOLDS):
            test_s = _date_to_bar_idx(h4_ct, test_start)
            test_e = _date_to_bar_idx(h4_ct, test_end)

            # Run strategy on full data, compute OOS window metrics
            nav_full, trades_full, stats_full = _run_strategy(
                strat, cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
                monitor_h4, wi, cps,
                model_w, model_mu, model_std, x14d_thresh, x18_thresh)

            # Run base on full data
            base_strat = STRATEGIES[0]  # S01
            nav_base, _, _ = _run_strategy(
                base_strat, cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
                monitor_h4, wi, cps,
                model_w, model_mu, model_std, x14d_thresh, x18_thresh)

            # OOS metrics
            oos_trades = [t for t in trades_full
                          if test_s <= t["entry_bar"] < test_e]
            m_strat = _metrics_window(nav_full, test_s, test_e, len(oos_trades))
            m_base = _metrics_window(nav_base, test_s, test_e)

            d_sharpe = m_strat["sharpe"] - m_base["sharpe"]
            win = d_sharpe > 0
            if win:
                wins += 1

            fold_results.append({
                "fold": fold_idx + 1, "d_sharpe": d_sharpe,
                "oos_sharpe": m_strat["sharpe"], "base_sharpe": m_base["sharpe"],
                "win": win,
            })

        win_rate = wins / len(WFO_FOLDS)
        mean_d = np.mean([f["d_sharpe"] for f in fold_results])
        wfo_results.append({
            "strategy_id": strat["id"],
            "strategy_name": strat["name"],
            "win_rate": win_rate,
            "wins": wins,
            "mean_d_sharpe": mean_d,
            "folds": fold_results,
        })
        print(f"  {strat['name']:16s}: WFO {wins}/4 ({win_rate:.0%}), mean Δsh={mean_d:+.3f}")

    # Write CSV
    csv_path = OUTDIR / "tables" / "Tbl_wfo_results.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy_id", "strategy_name", "fold", "oos_sharpe",
                     "base_sharpe", "d_sharpe", "win"])
        for wr in wfo_results:
            for fr in wr["folds"]:
                w.writerow([wr["strategy_id"], wr["strategy_name"], fr["fold"],
                            f"{fr['oos_sharpe']:.4f}", f"{fr['base_sharpe']:.4f}",
                            f"{fr['d_sharpe']:.4f}", int(fr["win"])])
    print(f"  Saved: {csv_path}")

    # Gate T2: best combo WFO >= 50%
    best_wr = max(wr["win_rate"] for wr in wfo_results if wr["strategy_id"] != "S01")
    best_name = next(wr["strategy_name"] for wr in wfo_results
                     if wr["win_rate"] == best_wr and wr["strategy_id"] != "S01")
    gate_pass = best_wr >= 0.50
    print(f"\n  Best WFO: {best_name} ({best_wr:.0%})")
    print(f"  Gate T2: {'PASS' if gate_pass else 'FAIL'}")

    _plot_t2_figure(wfo_results)
    return wfo_results, gate_pass


def _plot_t2_figure(wfo_results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    names = [wr["strategy_name"] for wr in wfo_results]
    n_strats = len(names)
    x = np.arange(n_strats)
    width = 0.18
    for fold_idx in range(4):
        ds = [wr["folds"][fold_idx]["d_sharpe"] for wr in wfo_results]
        colors = ["green" if d > 0 else "red" for d in ds]
        ax.bar(x + fold_idx * width, ds, width, color=colors, alpha=0.7,
               label=f"Fold {fold_idx + 1}" if fold_idx == 0 else None)
    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(names, fontsize=8, rotation=30, ha="right")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("ΔSharpe vs Base (OOS)")
    ax.set_title(f"X29 T2: WFO OOS ΔSharpe ({PRIMARY_COST} bps)")
    ax.legend(["Fold 1", "Fold 2", "Fold 3", "Fold 4"], fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_wfo_bars.png", dpi=150)
    plt.close(fig)


# =========================================================================
# T3: BOOTSTRAP (500 VCBB)
# =========================================================================

def run_t3(wfo_results, cl, hi, lo, vo, tb, ef, es, vd, at_e5,
           regime_h4, d1_str_h4, monitor_h4, wi, h4_ct,
           model_w, model_mu, model_std, x14d_thresh, x18_thresh):
    """Bootstrap VCBB for top strategies."""
    print("\n" + "=" * 70)
    print("T3: Bootstrap Validation (500 VCBB)")
    print("=" * 70)

    cps = PRIMARY_COST / 20_000.0

    # Use same top strategies from T2 (non-base)
    top_strats = [s for s in STRATEGIES
                  if s["id"] in [wr["strategy_id"] for wr in wfo_results]
                  and s["id"] != "S01"]
    base_strat = STRATEGIES[0]  # S01

    # Prepare bootstrap
    cl_pw = cl[wi:]
    hi_pw = hi[wi:]
    lo_pw = lo[wi:]
    vo_pw = vo[wi:]
    tb_pw = tb[wi:]
    cr, hr, lr, vol_r, tb_r = make_ratios(cl_pw, hi_pw, lo_pw, vo_pw, tb_pw)
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = len(cl) - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    regime_pw = regime_h4[wi:]
    d1_str_pw = d1_str_h4[wi:]
    monitor_pw = monitor_h4[wi:] if monitor_h4 is not None else None

    boot_data = {s["id"]: {"d_sharpe": [], "d_mdd": []} for s in top_strats}

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        n_b = len(bcl)

        # Indicators on bootstrap path
        fast_p = max(5, SLOW // 4)
        bef = _ema(bcl, fast_p)
        bes = _ema(bcl, SLOW)
        bvd = _vdo(bcl, bhi, blo, bvo, btb)
        bat = _robust_atr(bhi, blo, bcl)

        breg = regime_pw[:n_b] if len(regime_pw) >= n_b else np.ones(n_b, dtype=np.bool_)
        bd1 = d1_str_pw[:n_b] if len(d1_str_pw) >= n_b else np.zeros(n_b)
        bmon = monitor_pw[:n_b] if monitor_pw is not None and len(monitor_pw) >= n_b else np.zeros(n_b, dtype=np.int8)

        # Base
        nav_base, _, _ = _run_sim(
            bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1,
            bmon, 0, trail_mult=TRAIL_30, cps=cps,
            use_monitor=False, churn_type="none")
        m_base = _metrics(nav_base, 0)

        # Each top strategy
        for strat in top_strats:
            churn_thresh = None
            if strat["churn"] == "x14d":
                churn_thresh = x14d_thresh
            elif strat["churn"] == "x18":
                churn_thresh = x18_thresh

            nav_s, _, _ = _run_sim(
                bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1,
                bmon, 0, trail_mult=strat["trail"], cps=cps,
                use_monitor=strat["monitor"], churn_type=strat["churn"],
                model_w=model_w, model_mu=model_mu, model_std=model_std,
                churn_threshold=churn_thresh)
            m_s = _metrics(nav_s, 0)

            boot_data[strat["id"]]["d_sharpe"].append(m_s["sharpe"] - m_base["sharpe"])
            boot_data[strat["id"]]["d_mdd"].append(m_s["mdd"] - m_base["mdd"])

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    # Summarize
    boot_summary = []
    for strat in top_strats:
        ds = np.array(boot_data[strat["id"]]["d_sharpe"])
        dm = np.array(boot_data[strat["id"]]["d_mdd"])
        row = {
            "strategy_id": strat["id"],
            "strategy_name": strat["name"],
            "p_d_sharpe_gt0": float(np.mean(ds > 0)),
            "p_d_mdd_lt0": float(np.mean(dm < 0)),
            "median_d_sharpe": float(np.median(ds)),
            "median_d_mdd": float(np.median(dm)),
            "d_sharpe_p5": float(np.percentile(ds, 5)),
            "d_sharpe_p95": float(np.percentile(ds, 95)),
        }
        boot_summary.append(row)
        print(f"  {strat['name']:16s}: P(Δsh>0)={row['p_d_sharpe_gt0']:.1%}, "
              f"med Δsh={row['median_d_sharpe']:+.3f}, "
              f"P(Δmdd<0)={row['p_d_mdd_lt0']:.1%}, "
              f"med Δmdd={row['median_d_mdd']:+.1f}pp")

    # Write CSV
    csv_path = OUTDIR / "tables" / "Tbl_bootstrap.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy_id", "strategy_name", "p_d_sharpe_gt0", "p_d_mdd_lt0",
                     "median_d_sharpe", "median_d_mdd", "d_sharpe_p5", "d_sharpe_p95"])
        for r in boot_summary:
            w.writerow([r["strategy_id"], r["strategy_name"],
                        f"{r['p_d_sharpe_gt0']:.4f}", f"{r['p_d_mdd_lt0']:.4f}",
                        f"{r['median_d_sharpe']:.4f}", f"{r['median_d_mdd']:.2f}",
                        f"{r['d_sharpe_p5']:.4f}", f"{r['d_sharpe_p95']:.4f}"])
    print(f"  Saved: {csv_path}")

    # Gate T3: P(d_sharpe > 0) >= 55%
    best_p = max(r["p_d_sharpe_gt0"] for r in boot_summary)
    best_name = next(r["strategy_name"] for r in boot_summary if r["p_d_sharpe_gt0"] == best_p)
    gate_pass = best_p >= 0.55
    print(f"\n  Best P(Δsh>0): {best_name} ({best_p:.1%})")
    print(f"  Gate T3: {'PASS' if gate_pass else 'FAIL'}")

    _plot_t3_figure(boot_data, top_strats)
    return boot_summary, boot_data, gate_pass


def _plot_t3_figure(boot_data, top_strats):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    data_list = [boot_data[s["id"]]["d_sharpe"] for s in top_strats]
    names = [s["name"] for s in top_strats]
    parts = ax.violinplot(data_list, positions=range(len(names)), showmedians=True)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, fontsize=8, rotation=30, ha="right")
    ax.axhline(0, color="red", linewidth=0.5, linestyle="--")
    ax.set_ylabel("ΔSharpe vs Base")
    ax.set_title(f"X29 T3: Bootstrap ΔSharpe Distribution ({PRIMARY_COST} bps, {N_BOOT} VCBB)")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_bootstrap_violin.png", dpi=150)
    plt.close(fig)


# =========================================================================
# T4: COST-CROSSOVER MAP
# =========================================================================

def run_t4(t0_rows):
    """Determine optimal strategy at each cost level."""
    print("\n" + "=" * 70)
    print("T4: Cost-Crossover Map")
    print("=" * 70)

    reco_rows = []
    for cost_bps in COST_BPS:
        cost_rows = [r for r in t0_rows if r["cost_bps"] == cost_bps]
        by_sharpe = sorted(cost_rows, key=lambda r: r["sharpe"], reverse=True)
        by_calmar = sorted(cost_rows, key=lambda r: r["calmar"], reverse=True)
        best_sh = by_sharpe[0]["sharpe"]
        # MDD-optimal among strategies with Sharpe > 0.8 × best
        eligible_mdd = [r for r in cost_rows if r["sharpe"] > 0.8 * best_sh]
        by_mdd = sorted(eligible_mdd, key=lambda r: r["mdd"])

        reco_rows.append({
            "cost_bps": cost_bps,
            "opt_sharpe_id": by_sharpe[0]["strategy_id"],
            "opt_sharpe_name": by_sharpe[0]["strategy_name"],
            "opt_sharpe_val": by_sharpe[0]["sharpe"],
            "opt_calmar_id": by_calmar[0]["strategy_id"],
            "opt_calmar_name": by_calmar[0]["strategy_name"],
            "opt_calmar_val": by_calmar[0]["calmar"],
            "opt_mdd_id": by_mdd[0]["strategy_id"],
            "opt_mdd_name": by_mdd[0]["strategy_name"],
            "opt_mdd_val": by_mdd[0]["mdd"],
        })
        print(f"  {cost_bps:3d} bps: Sharpe→{by_sharpe[0]['strategy_name']:16s} ({by_sharpe[0]['sharpe']:.3f}) | "
              f"MDD→{by_mdd[0]['strategy_name']:16s} ({by_mdd[0]['mdd']:.1f}%)")

    # Write CSV
    csv_path = OUTDIR / "tables" / "Tbl_recommendation_matrix.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cost_bps", "opt_sharpe_id", "opt_sharpe_name", "opt_sharpe_val",
                     "opt_calmar_id", "opt_calmar_name", "opt_calmar_val",
                     "opt_mdd_id", "opt_mdd_name", "opt_mdd_val"])
        for r in reco_rows:
            w.writerow([r["cost_bps"], r["opt_sharpe_id"], r["opt_sharpe_name"],
                        f"{r['opt_sharpe_val']:.4f}",
                        r["opt_calmar_id"], r["opt_calmar_name"],
                        f"{r['opt_calmar_val']:.4f}",
                        r["opt_mdd_id"], r["opt_mdd_name"],
                        f"{r['opt_mdd_val']:.2f}"])
    print(f"  Saved: {csv_path}")

    # Check consistency with X22
    print("\n  X22 consistency check:")
    for cost_bps in [10, 15, 20]:
        r = next(rr for rr in reco_rows if rr["cost_bps"] == cost_bps)
        print(f"    {cost_bps} bps: optimal={r['opt_sharpe_name']} "
              f"(X22 expected: Base or Mon)")

    return reco_rows


# =========================================================================
# T5: DOMINANCE / PARETO ANALYSIS
# =========================================================================

def run_t5(t0_rows):
    """Pareto-efficient strategies at each cost level."""
    print("\n" + "=" * 70)
    print("T5: Dominance / Pareto Analysis")
    print("=" * 70)

    all_pareto = []
    for cost_bps in COST_BPS:
        cost_rows = [r for r in t0_rows if r["cost_bps"] == cost_bps]
        # Pareto: no other strategy has both higher Sharpe AND lower MDD
        pareto_set = []
        for r in cost_rows:
            dominated = False
            for other in cost_rows:
                if other["strategy_id"] == r["strategy_id"]:
                    continue
                if other["sharpe"] >= r["sharpe"] and other["mdd"] <= r["mdd"]:
                    if other["sharpe"] > r["sharpe"] or other["mdd"] < r["mdd"]:
                        dominated = True
                        break
            if not dominated:
                pareto_set.append(r["strategy_id"])

        all_pareto.append({
            "cost_bps": cost_bps,
            "pareto_set": pareto_set,
            "n_pareto": len(pareto_set),
            "n_dominated": 12 - len(pareto_set),
        })
        names = [next(s["name"] for s in STRATEGIES if s["id"] == sid) for sid in pareto_set]
        print(f"  {cost_bps:3d} bps: {len(pareto_set)} Pareto-efficient — {', '.join(names)}")

    # Write CSV
    csv_path = OUTDIR / "tables" / "Tbl_pareto_efficient.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cost_bps", "n_pareto", "n_dominated", "pareto_set"])
        for r in all_pareto:
            w.writerow([r["cost_bps"], r["n_pareto"], r["n_dominated"],
                        "|".join(r["pareto_set"])])
    print(f"  Saved: {csv_path}")

    _plot_t5_figure(t0_rows, all_pareto)
    return all_pareto


def _plot_t5_figure(t0_rows, all_pareto):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    # Plot at 3 key cost levels
    key_costs = [15, 25, 50]
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    strat_ids = [s["id"] for s in STRATEGIES]
    colors = plt.cm.tab20(np.linspace(0, 1, 12))

    for ax, cost_bps in zip(axes, key_costs):
        cost_rows = [r for r in t0_rows if r["cost_bps"] == cost_bps]
        pareto_ids = next(p["pareto_set"] for p in all_pareto if p["cost_bps"] == cost_bps)

        for r in cost_rows:
            si = strat_ids.index(r["strategy_id"])
            is_pareto = r["strategy_id"] in pareto_ids
            ax.scatter(r["mdd"], r["sharpe"], color=colors[si], s=100 if is_pareto else 40,
                       edgecolors="black" if is_pareto else "none", linewidths=2 if is_pareto else 0,
                       zorder=5 if is_pareto else 3)
            if is_pareto:
                ax.annotate(r["strategy_name"], (r["mdd"], r["sharpe"]),
                            fontsize=7, textcoords="offset points", xytext=(5, 5))

        # Draw Pareto frontier
        pareto_rows = sorted([r for r in cost_rows if r["strategy_id"] in pareto_ids],
                             key=lambda r: r["mdd"])
        if len(pareto_rows) > 1:
            ax.plot([r["mdd"] for r in pareto_rows], [r["sharpe"] for r in pareto_rows],
                    "k--", alpha=0.5, linewidth=1)

        ax.set_xlabel("MDD (%)")
        ax.set_ylabel("Sharpe")
        ax.set_title(f"{cost_bps} bps")
        ax.grid(True, alpha=0.3)

    fig.suptitle("X29 T5: Dominance Frontier at Key Costs", fontsize=14)
    fig.tight_layout()
    fig.savefig(OUTDIR / "figures" / "Fig_dominance_frontier.png", dpi=150)
    plt.close(fig)


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()
    print("=" * 70)
    print("X29: Optimal Stack — Combination of Validated Overlays on E5+EMA1D21")
    print("=" * 70)
    print(f"  12 strategies × 9 costs = 108 backtests")
    print(f"  Primary cost: {PRIMARY_COST} bps RT")

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
    print("\nComputing indicators...")
    fast_p = max(5, SLOW // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb)
    at_e5 = _robust_atr(hi, lo, cl)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    # --- Compute Monitor V2 alerts ---
    print("Computing Monitor V2 alerts...")
    d1_alerts = _compute_monitor_alerts(d1_cl)
    monitor_h4 = _map_d1_alert_to_h4(d1_alerts, d1_ct, h4_ct)
    n_red = int(np.sum(monitor_h4 == 2))
    print(f"  RED bars on H4: {n_red} ({n_red / n * 100:.1f}%)")

    # --- Train churn model (on E5+EMA1D21 trades at 50 bps, same as X22) ---
    print("\nTraining churn model on E5+EMA1D21 trades (50 bps)...")
    cps_50 = SCENARIOS["harsh"].per_side_bps / 10_000.0
    nav_base_50, trades_base_50, _ = _run_sim(
        cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
        monitor_h4, wi, trail_mult=TRAIL_30, cps=cps_50,
        use_monitor=False, churn_type="none")
    m_base_50 = _metrics(nav_base_50, wi, len(trades_base_50))
    print(f"  E5+EMA1D21 @ 50 bps: {len(trades_base_50)} trades, Sh={m_base_50['sharpe']:.4f}")

    model_w, model_mu, model_std, best_c, n_train = _train_churn_model(
        trades_base_50, cl, hi, lo, at_e5, ef, es, vd, d1_str_h4)
    print(f"  Churn model: C={best_c}, n_train={n_train}")

    if model_w is None:
        print("  ERROR: Churn model training failed!")
        return

    # X14D threshold: P > 0.5 (fixed)
    x14d_thresh = 0.5

    # X18 threshold: α-percentile of training scores
    train_scores = _compute_train_scores(
        trades_base_50, cl, hi, lo, at_e5, ef, es, vd, d1_str_h4,
        model_w, model_mu, model_std)
    x18_thresh = float(np.percentile(train_scores, 100 - X18_ALPHA))
    print(f"  X14D threshold: {x14d_thresh:.3f}")
    print(f"  X18 threshold (α={X18_ALPHA}%): {x18_thresh:.3f}")

    results = {
        "study": "X29",
        "config": {
            "strategies": [s["name"] for s in STRATEGIES],
            "cost_bps": COST_BPS,
            "primary_cost": PRIMARY_COST,
            "x14d_thresh": x14d_thresh,
            "x18_thresh": float(x18_thresh),
            "n_boot": N_BOOT,
            "n_h4_bars": n,
            "n_d1_bars": len(d1_cl),
            "warmup_bars": wi,
            "years": yrs,
        },
        "gates": {},
    }

    # === T0 ===
    t0_rows, all_navs, t0_pass = run_t0(
        cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
        monitor_h4, wi, model_w, model_mu, model_std,
        x14d_thresh, x18_thresh)
    results["gates"]["T0"] = t0_pass
    _plot_t0_figures(t0_rows)

    if not t0_pass:
        print("\n*** T0 FAIL: No combination beats base. STOP. ***")
        results["verdict"] = "STOP: overlays incompatible"
        _save_results(results)
        return

    # === T1 ===
    t1_interactions, t1_pass = run_t1(t0_rows)
    results["gates"]["T1"] = t1_pass

    # === T2 ===
    t2_results, t2_pass = run_t2(
        t0_rows, cl, hi, lo, ef, es, vd, at_e5, regime_h4, d1_str_h4,
        monitor_h4, h4_ct, wi,
        model_w, model_mu, model_std, x14d_thresh, x18_thresh)
    results["gates"]["T2"] = t2_pass

    if not t2_pass:
        print("\n*** T2 FAIL: WFO < 50%. Recommend Monitor V2 only. ***")
        results["verdict"] = "RECOMMEND: Monitor V2 only (WFO fail)"
        _save_results(results)
        _write_report(results, t0_rows, t1_interactions, t2_results, None, None, None)
        return

    # === T3 ===
    t3_summary, t3_boot_data, t3_pass = run_t3(
        t2_results, cl, hi, lo, vo, tb, ef, es, vd, at_e5,
        regime_h4, d1_str_h4, monitor_h4, wi, h4_ct,
        model_w, model_mu, model_std, x14d_thresh, x18_thresh)
    results["gates"]["T3"] = t3_pass

    if not t3_pass:
        print("\n*** T3 FAIL: P(d_sharpe>0) < 55%. Recommend Monitor V2 only. ***")
        results["verdict"] = "RECOMMEND: Monitor V2 only (bootstrap fail)"
        _save_results(results)
        _write_report(results, t0_rows, t1_interactions, t2_results, t3_summary, None, None)
        return

    # === T4 ===
    t4_reco = run_t4(t0_rows)
    results["t4_recommendations"] = [
        {"cost_bps": r["cost_bps"], "opt_sharpe": r["opt_sharpe_name"],
         "opt_mdd": r["opt_mdd_name"]}
        for r in t4_reco
    ]

    # === T5 ===
    t5_pareto = run_t5(t0_rows)
    results["t5_pareto"] = [
        {"cost_bps": r["cost_bps"], "pareto_set": r["pareto_set"]}
        for r in t5_pareto
    ]

    # Finalize
    results["verdict"] = "FULL_RECOMMENDATION"
    _save_results(results)
    _write_report(results, t0_rows, t1_interactions, t2_results, t3_summary, t4_reco, t5_pareto)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"X29 complete in {elapsed:.1f}s")
    print(f"{'=' * 70}")


def _save_results(results):
    path = OUTDIR / "x29_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Results saved: {path}")


def _write_report(results, t0_rows, t1_interactions, t2_results, t3_summary,
                  t4_reco, t5_pareto):
    """Generate x29_report.md."""
    lines = []
    lines.append("# X29: Optimal Stack — Results Report\n")
    lines.append(f"**Verdict**: {results['verdict']}\n")
    lines.append(f"**Gates**: {results['gates']}\n")

    # T0 summary at primary cost
    lines.append(f"\n## T0: Full-Sample Matrix at {PRIMARY_COST} bps\n")
    lines.append("| Strategy | Sharpe | CAGR% | MDD% | Calmar | Trades | Suppress | MonBlk |")
    lines.append("|----------|--------|-------|------|--------|--------|----------|--------|")
    for s in STRATEGIES:
        r = next(rr for rr in t0_rows
                 if rr["strategy_id"] == s["id"] and rr["cost_bps"] == PRIMARY_COST)
        lines.append(f"| {r['strategy_name']:16s} | {r['sharpe']:.3f} | {r['cagr']:.1f} | "
                     f"{r['mdd']:.1f} | {r['calmar']:.3f} | {r['n_trades']} | "
                     f"{r['suppressions']} | {r['monitor_blocks']} |")

    # T1 interactions at primary cost
    if t1_interactions:
        lines.append(f"\n## T1: Interactions at {PRIMARY_COST} bps\n")
        row = next(r for r in t1_interactions if r["cost_bps"] == PRIMARY_COST)
        for k, v in row.items():
            if k != "cost_bps":
                lines.append(f"- {k}: {v:+.4f}")

    # T2 WFO
    if t2_results:
        lines.append(f"\n## T2: WFO Results at {PRIMARY_COST} bps\n")
        for wr in t2_results:
            lines.append(f"- {wr['strategy_name']}: {wr['wins']}/4 ({wr['win_rate']:.0%}), "
                         f"mean Δsh={wr['mean_d_sharpe']:+.3f}")

    # T3 Bootstrap
    if t3_summary:
        lines.append(f"\n## T3: Bootstrap Results at {PRIMARY_COST} bps\n")
        for r in t3_summary:
            lines.append(f"- {r['strategy_name']}: P(Δsh>0)={r['p_d_sharpe_gt0']:.1%}, "
                         f"med Δsh={r['median_d_sharpe']:+.3f}")

    # T4 Recommendations
    if t4_reco:
        lines.append("\n## T4: Cost-Crossover Recommendations\n")
        lines.append("| Cost | Sharpe-Optimal | MDD-Optimal |")
        lines.append("|------|---------------|-------------|")
        for r in t4_reco:
            lines.append(f"| {r['cost_bps']:3d} bps | {r['opt_sharpe_name']} | {r['opt_mdd_name']} |")

    # T5 Pareto
    if t5_pareto:
        lines.append("\n## T5: Pareto-Efficient Sets\n")
        for r in t5_pareto:
            names = [next(s["name"] for s in STRATEGIES if s["id"] == sid)
                     for sid in r["pareto_set"]]
            lines.append(f"- {r['cost_bps']} bps: {', '.join(names)}")

    path = OUTDIR / "x29_report.md"
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Report saved: {path}")


if __name__ == "__main__":
    main()
