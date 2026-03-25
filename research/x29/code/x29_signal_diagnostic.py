#!/usr/bin/env python3
"""X29 Signal Diagnostic + Fractional Actuator Pilot

Part A: Root cause — WHY does X18 fail at 25 bps?
  - Decompose into cost savings vs alpha loss
  - Profile each suppression: was it correct?

Part B: Signal quality — Do Monitor/X18 carry useful INFORMATION?
  - Monitor: trade outcomes by regime (NORMAL vs AMBER vs RED entries)
  - X18: trade outcomes by churn score (high vs low score entries)

Part C: Fractional actuator pilot — new actuator, frozen signals
  - C1: Monitor position sizing (f=0.30/0.15/0.00 by regime)
  - C2: X18 partial exit (half-exit instead of full suppress)
  - C3: Combined
  - Compare vs Base, Mon(binary), X18(binary) at 9 cost levels

DOF note: thresholds/model frozen. Only new params:
  f_normal=0.30, f_amber=0.15, f_red=0.00 (Monitor sizing)
  partial_frac=0.50 (X18 partial exit)
These are structural choices, not optimized.
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

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)
START, END, WARMUP = "2019-01-01", "2026-02-20", 365
VDO_F, VDO_S, VDO_THR = 12, 28, 0.0
SLOW, D1_EMA_P = 120, 21
RATR_P, RATR_Q, RATR_LB = 20, 0.90, 100
TRAIL = 3.0
CHURN_WINDOW = 20
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
X18_ALPHA = 40

ROLL_6M, ROLL_12M = 180, 360
RED_MDD_6M, RED_MDD_12M = 0.55, 0.70
AMBER_MDD_6M, AMBER_MDD_12M = 0.45, 0.60

COST_BPS = [10, 15, 20, 25, 30, 35, 50, 75, 100]

# Fractional sizing (structural, not optimized)
F_NORMAL = 0.30
F_AMBER = 0.15
F_RED = 0.00
PARTIAL_FRAC = 0.50  # keep 50% on churn suppress

# Bootstrap
N_BOOT = 500
BLKSZ = 60
SEED = 42

OUTDIR = Path(__file__).resolve().parents[1]

# =========================================================================
# INDICATORS (identical to x29_benchmark)
# =========================================================================

def _ema(s, p):
    a = 2.0 / (p + 1)
    out, _ = lfilter([a], [1.0, -(1 - a)], s, zi=[(1 - a) * s[0]])
    return out

def _robust_atr(hi, lo, cl, cap_q=RATR_Q, cap_lb=RATR_LB, period=RATR_P):
    prev = np.empty_like(cl); prev[0] = cl[0]; prev[1:] = cl[:-1]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev), np.abs(lo - prev)))
    n = len(tr); tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan); s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.nanmean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr

def _vdo(cl, hi, lo, vo, tb, fast=VDO_F, slow=VDO_S):
    n = len(cl)
    ts = np.maximum(vo - tb, 0.0); vdr = np.zeros(n)
    m = vo > 1e-12; vdr[m] = (tb[m] - ts[m]) / vo[m]
    return _ema(vdr, fast) - _ema(vdr, slow)

def _compute_d1_regime(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema
    n_h4 = len(h4_ct); regime_h4 = np.zeros(n_h4, dtype=np.bool_)
    d1_idx = 0; n_d1 = len(d1_cl)
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]: d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]: regime_h4[i] = d1_regime[d1_idx]
    return regime_h4

def _compute_d1_regime_str(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_str = np.where(d1_cl > 1e-12, (d1_cl - d1_ema) / d1_cl, 0.0)
    n_h4 = len(h4_ct); str_h4 = np.zeros(n_h4)
    d1_idx = 0; n_d1 = len(d1_cl)
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]: d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]: str_h4[i] = d1_str[d1_idx]
    return str_h4


# =========================================================================
# MONITOR V2
# =========================================================================

def _compute_monitor_alerts_d1(d1_cl):
    """Monitor V2 alerts on D1: 0=NORMAL, 1=AMBER, 2=RED."""
    from monitoring.regime_monitor import rolling_mdd
    mdd_6m = rolling_mdd(d1_cl, ROLL_6M)
    mdd_12m = rolling_mdd(d1_cl, ROLL_12M)
    n = len(d1_cl)
    alerts = np.zeros(n, dtype=np.int8)
    for t in range(n):
        m6 = mdd_6m[t] if not np.isnan(mdd_6m[t]) else 0.0
        m12 = mdd_12m[t] if not np.isnan(mdd_12m[t]) else 0.0
        if m6 > RED_MDD_6M or m12 > RED_MDD_12M:
            alerts[t] = 2
        elif m6 > AMBER_MDD_6M or m12 > AMBER_MDD_12M:
            alerts[t] = 1
    return alerts

def _map_d1_alert_to_h4(d1_alerts, d1_ct, h4_ct):
    n_h4 = len(h4_ct); n_d1 = len(d1_ct)
    h4_alerts = np.zeros(n_h4, dtype=np.int8); d1_idx = 0
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]: d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]: h4_alerts[i] = d1_alerts[d1_idx]
    return h4_alerts


# =========================================================================
# CHURN MODEL (from X22/X18)
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
    f5 = float(vd[i]); f6 = float(d1_str_h4[i])
    f7 = trail_mult * at[i] / cl[i] if cl[i] > 1e-12 else 0.0
    return np.array([f1, f2, f3, f4, f5, f6, f7])

def _label_churn(trades, churn_window=CHURN_WINDOW):
    entry_bars = sorted(t["entry_bar"] for t in trades)
    results = []
    for idx, t in enumerate(trades):
        if t["exit_reason"] != "trail_stop": continue
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
        if sb < 0 or sb >= n or math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue
        features.append(_extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4))
        labels.append(label)
    if not features: return np.empty((0, 7)), np.empty(0, dtype=int)
    return np.array(features), np.array(labels, dtype=int)

def _fit_logistic_l2(X, y, C=1.0, max_iter=100):
    n, d = X.shape; Xa = np.column_stack([X, np.ones(n)]); w = np.zeros(d + 1)
    for _ in range(max_iter):
        z = Xa @ w; p = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
        err = p - y; reg = np.zeros(d + 1); reg[:d] = w[:d] / C
        grad = Xa.T @ err / n + reg
        S = p * (1 - p) + 1e-12; H = (Xa.T * S) @ Xa / n
        H_reg = np.zeros((d + 1, d + 1)); np.fill_diagonal(H_reg[:d, :d], 1.0 / C)
        try: dw = np.linalg.solve(H + H_reg, grad)
        except np.linalg.LinAlgError: break
        w -= dw
        if np.max(np.abs(dw)) < 1e-8: break
    return w

def _kfold_auc(X, y, C=1.0, k=5):
    n = len(y); idx = np.arange(n); rng = np.random.default_rng(42); rng.shuffle(idx)
    aucs = []; fold_size = n // k
    for fold in range(k):
        s = fold * fold_size; e = s + fold_size if fold < k - 1 else n
        vi = idx[s:e]; ti = np.concatenate([idx[:s], idx[e:]])
        w = _fit_logistic_l2(X[ti], y[ti], C=C)
        preds = 1.0 / (1.0 + np.exp(-np.clip(X[vi] @ w[:X.shape[1]] + w[-1], -500, 500)))
        pos = preds[y[vi] == 1]; neg = preds[y[vi] == 0]
        if len(pos) == 0 or len(neg) == 0: aucs.append(0.5); continue
        aucs.append(float((np.sum(pos[:, None] > neg[None, :]) + 0.5 * np.sum(pos[:, None] == neg[None, :])) / (len(pos) * len(neg))))
    return float(np.mean(aucs))

def _standardize(X):
    mu = np.mean(X, axis=0); std = np.std(X, axis=0, ddof=0); std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std

def _predict_score(feat, w, mu, std):
    fs = (feat - mu) / std; z = np.dot(np.append(fs, 1.0), w)
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))

def _train_churn_model(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    X, y = _extract_features_from_trades(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    if len(y) < 10 or len(np.unique(y)) < 2: return None, None, None, None, 0
    Xs, mu, std = _standardize(X)
    best_c, best_auc = 1.0, 0.0
    for c_val in C_VALUES:
        auc_c = _kfold_auc(Xs, y, C=c_val, k=5)
        if auc_c > best_auc: best_auc = auc_c; best_c = c_val
    w = _fit_logistic_l2(Xs, y, C=best_c)
    return w, mu, std, best_c, len(y)


# =========================================================================
# METRICS
# =========================================================================

def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": nt}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    tr = navs[-1] / navs[0] - 1.0; yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    pk = np.maximum.accumulate(navs); mdd = np.max(1.0 - navs / pk) * 100
    calmar = cagr / mdd if mdd > 0 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar, "trades": nt}


# =========================================================================
# SIM ENGINES
# =========================================================================

def _sim_base(cl, ef, es, vd, at, regime_h4, wi, cps):
    """S01: Base E5+EMA1D21, binary in/out."""
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False; pk = 0.0
    entry_bar = 0; entry_cost = 0.0; entry_px = 0.0
    nav = np.zeros(n); trades = []
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps)); entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p
            elif px:
                px = False; received = bq * fp * (1 - cps)
                trades.append({"entry_bar": entry_bar, "exit_bar": i, "entry_px": entry_px,
                               "exit_px": fp, "pnl_usd": received - entry_cost,
                               "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _exit_reason})
                cash = received; bq = 0.0; inp = False; pk = 0.0
        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a: _exit_reason = "trail_stop"; px = True
            elif ef[i] < es[i]: _exit_reason = "trend_exit"; px = True
    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1, "entry_px": entry_px,
                       "exit_px": cl[-1], "pnl_usd": received - entry_cost,
                       "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
        cash = received; bq = 0.0; nav[-1] = cash
    return nav, trades


def _sim_binary_monitor(cl, ef, es, vd, at, regime_h4, monitor_h4, wi, cps):
    """S07: Binary monitor — block entries when RED."""
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False; pk = 0.0
    entry_bar = 0; entry_cost = 0.0; entry_px = 0.0; _exit_reason = ""
    nav = np.zeros(n); trades = []; n_blocks = 0
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps)); entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p
            elif px:
                px = False; received = bq * fp * (1 - cps)
                trades.append({"entry_bar": entry_bar, "exit_bar": i, "entry_px": entry_px,
                               "exit_px": fp, "pnl_usd": received - entry_cost,
                               "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _exit_reason})
                cash = received; bq = 0.0; inp = False; pk = 0.0
        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        red = monitor_h4[i] == 2
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                if red: n_blocks += 1
                else: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a: _exit_reason = "trail_stop"; px = True
            elif ef[i] < es[i]: _exit_reason = "trend_exit"; px = True
    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1, "entry_px": entry_px,
                       "exit_px": cl[-1], "pnl_usd": received - entry_cost,
                       "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
        cash = received; bq = 0.0; nav[-1] = cash
    return nav, trades, n_blocks


def _sim_binary_x18(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
                     model_w, model_mu, model_std, x18_thresh):
    """S05: Binary X18 — suppress trail when score > threshold."""
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False; pk = 0.0
    entry_bar = 0; entry_cost = 0.0; entry_px = 0.0; _exit_reason = ""
    nav = np.zeros(n); trades = []; n_suppress = 0
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps)); entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p
            elif px:
                px = False; received = bq * fp * (1 - cps)
                trades.append({"entry_bar": entry_bar, "exit_bar": i, "entry_px": entry_px,
                               "exit_px": fp, "pnl_usd": received - entry_cost,
                               "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _exit_reason})
                cash = received; bq = 0.0; inp = False; pk = 0.0
        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                feat = _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4)
                score = _predict_score(feat, model_w, model_mu, model_std)
                if score > x18_thresh: n_suppress += 1
                else: _exit_reason = "trail_stop"; px = True
            elif ef[i] < es[i]: _exit_reason = "trend_exit"; px = True
    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1, "entry_px": entry_px,
                       "exit_px": cl[-1], "pnl_usd": received - entry_cost,
                       "ret_pct": (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
        cash = received; bq = 0.0; nav[-1] = cash
    return nav, trades, n_suppress


# =========================================================================
# NEW: FRACTIONAL ACTUATOR SIMS
# =========================================================================

def _sim_monitor_sizing(cl, ef, es, vd, at, regime_h4, monitor_h4, wi, cps,
                         f_normal=F_NORMAL, f_amber=F_AMBER, f_red=F_RED):
    """C1: Position sizing by Monitor regime.

    Instead of binary block, enter with fraction f based on regime:
      NORMAL → f_normal (full)
      AMBER  → f_amber (reduced)
      RED    → f_red (minimal or zero)
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = False
    px = False
    pk = 0.0
    entry_bar = 0
    entry_cost = 0.0
    entry_px = 0.0
    entry_f = 0.0
    _exit_reason = ""
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
                # Size based on entry_f: invest entry_f fraction of total NAV
                total_nav = cash + bq * fp
                invest = total_nav * entry_f
                if invest > 1e-6 and not inp:
                    bq = invest / (fp * (1 + cps))
                    entry_cost = bq * fp * (1 + cps)
                    cash = total_nav - entry_cost
                    inp = True
                    pk = p
                else:
                    pe = False  # skip if already in or zero size
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                total_entry = entry_cost + cash  # cash held during trade
                pnl = (cash + received) - total_entry
                ret = ((cash + received) / total_entry - 1.0) * 100 if total_entry > 0 else 0.0
                trades.append({"entry_bar": entry_bar, "exit_bar": i, "entry_px": entry_px,
                               "exit_px": fp, "pnl_usd": pnl, "ret_pct": ret,
                               "bars_held": i - entry_bar, "exit_reason": _exit_reason,
                               "entry_f": entry_f})
                cash = cash + received
                bq = 0.0
                inp = False
                pk = 0.0

        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        alert = int(monitor_h4[i])
        if alert == 2:
            f_now = f_red
        elif alert == 1:
            f_now = f_amber
        else:
            f_now = f_normal

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                if f_now > 1e-6:
                    entry_f = f_now
                    pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                _exit_reason = "trail_stop"
                px = True
            elif ef[i] < es[i]:
                _exit_reason = "trend_exit"
                px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        total_entry = entry_cost + cash
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1, "entry_px": entry_px,
                       "exit_px": cl[-1], "pnl_usd": (cash + received) - total_entry,
                       "ret_pct": ((cash + received) / total_entry - 1.0) * 100 if total_entry > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
                       "entry_f": entry_f})
        cash = cash + received; bq = 0.0; nav[-1] = cash
    return nav, trades


def _sim_x18_partial(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
                      model_w, model_mu, model_std, x18_thresh,
                      partial_frac=PARTIAL_FRAC):
    """C2: X18 partial exit — when churn predicted, exit partial_frac, keep rest.

    When trail fires and score > threshold: sell (1-partial_frac) of position.
    Keep partial_frac running with trail. This is a softer version of suppress.
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = False
    px = False
    pk = 0.0
    entry_bar = 0
    entry_cost = 0.0
    entry_px = 0.0
    _exit_reason = ""
    nav = np.zeros(n)
    trades = []
    n_partial = 0

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
                total_received = cash + received  # include partial exit cash
                trades.append({"entry_bar": entry_bar, "exit_bar": i, "entry_px": entry_px,
                               "exit_px": fp, "pnl_usd": total_received - entry_cost,
                               "ret_pct": (total_received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _exit_reason})
                cash = total_received  # FIX: preserve partial exit cash
                bq = 0.0
                inp = False
                pk = 0.0

        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                feat = _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4)
                score = _predict_score(feat, model_w, model_mu, model_std)
                if score > x18_thresh:
                    # PARTIAL EXIT: sell (1 - partial_frac) of position
                    # Use deferred execution: schedule partial for next bar
                    sell_qty = bq * (1 - partial_frac)
                    received_partial = sell_qty * p * (1 - cps)
                    cash += received_partial
                    bq -= sell_qty
                    n_partial += 1
                    # Keep remaining bq with same trail
                    if bq < 1e-12:
                        _exit_reason = "trail_stop_partial"
                        px = True
                else:
                    _exit_reason = "trail_stop"
                    px = True
            elif ef[i] < es[i]:
                _exit_reason = "trend_exit"
                px = True

    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        total_received = cash + received
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1, "entry_px": entry_px,
                       "exit_px": cl[-1], "pnl_usd": total_received - entry_cost,
                       "ret_pct": (total_received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
        cash = total_received; bq = 0.0; nav[-1] = cash
    return nav, trades, n_partial


def _sim_combined_frac(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                        monitor_h4, wi, cps,
                        model_w, model_mu, model_std, x18_thresh,
                        f_normal=F_NORMAL, f_amber=F_AMBER, f_red=F_RED,
                        partial_frac=PARTIAL_FRAC):
    """C3: Combined — Monitor sizing + X18 partial exit."""
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pe = False
    px = False
    pk = 0.0
    entry_bar = 0
    entry_cost = 0.0
    entry_px = 0.0
    entry_f = 0.0
    _exit_reason = ""
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
                total_nav = cash + bq * fp
                invest = total_nav * entry_f
                if invest > 1e-6 and not inp:
                    bq = invest / (fp * (1 + cps))
                    entry_cost = bq * fp * (1 + cps)
                    cash = total_nav - entry_cost
                    inp = True
                    pk = p
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                trades.append({"entry_bar": entry_bar, "exit_bar": i, "entry_px": entry_px,
                               "exit_px": fp, "bars_held": i - entry_bar,
                               "exit_reason": _exit_reason, "entry_f": entry_f,
                               "pnl_usd": 0.0, "ret_pct": 0.0})
                cash = cash + received
                bq = 0.0
                inp = False
                pk = 0.0

        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        alert = int(monitor_h4[i])
        f_now = f_red if alert == 2 else (f_amber if alert == 1 else f_normal)

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                if f_now > 1e-6:
                    entry_f = f_now
                    pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                feat = _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4)
                score = _predict_score(feat, model_w, model_mu, model_std)
                if score > x18_thresh:
                    sell_qty = bq * (1 - partial_frac)
                    cash += sell_qty * p * (1 - cps)
                    bq -= sell_qty
                    if bq < 1e-12:
                        px = True; _exit_reason = "trail_partial"
                else:
                    _exit_reason = "trail_stop"
                    px = True
            elif ef[i] < es[i]:
                _exit_reason = "trend_exit"
                px = True

    if inp and bq > 0:
        cash = cash + bq * cl[-1] * (1 - cps)
        bq = 0.0
        nav[-1] = cash
    return nav, trades


# =========================================================================
# PART A: X18 ROOT CAUSE
# =========================================================================

def part_a(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            model_w, model_mu, model_std, x18_thresh, trades_base_25):
    """Why does X18 fail at 25 bps? Decompose suppress outcomes."""
    print("\n" + "=" * 70)
    print("PART A: X18 Root Cause at 25 bps")
    print("=" * 70)

    cps = 25 / 20_000.0
    n = len(cl)

    # Run X18 to get trades
    nav_x18, trades_x18, n_supp = _sim_binary_x18(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
        model_w, model_mu, model_std, x18_thresh)
    m_base = _metrics(nav_x18, wi, len(trades_x18))

    # Compare trades: Base has 199, X18 has 153 (at 25 bps)
    # X18 suppresses 609 trail-stop bars → fewer round-trips → fewer trades
    n_base_trades = len(trades_base_25)
    n_x18_trades = len(trades_x18)
    saved_roundtrips = n_base_trades - n_x18_trades

    # Cost saved per round-trip = 2 * cps * avg_trade_value
    # Approximate: at 25 bps RT, each RT costs 25 bps of notional
    # With ~199 trades over 7.14 years, annual trade cost = 199/7.14 * 25 bps ≈ 697 bps/yr
    # X18: 153/7.14 * 25 bps ≈ 536 bps/yr → saves ~161 bps/yr
    yrs = (n - wi) / (6.0 * 365.25)
    base_annual_cost = n_base_trades / yrs * 25
    x18_annual_cost = n_x18_trades / yrs * 25
    cost_saved_bps_yr = base_annual_cost - x18_annual_cost

    print(f"\n  Base trades: {n_base_trades}, X18 trades: {n_x18_trades}")
    print(f"  Saved round-trips: {saved_roundtrips}")
    print(f"  Suppressions (bar-level): {n_supp}")
    print(f"  Annual cost: Base={base_annual_cost:.0f} bps/yr, X18={x18_annual_cost:.0f} bps/yr")
    print(f"  Cost savings: {cost_saved_bps_yr:.0f} bps/yr")

    # Profile suppressions: run Base at 0 cost to see gross returns
    nav_base_0, tr_base_0 = _sim_base(cl, ef, es, vd, at, regime_h4, wi, 0.0)
    nav_x18_0, _, _ = _sim_binary_x18(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, 0.0,
        model_w, model_mu, model_std, x18_thresh)
    m_base_0 = _metrics(nav_base_0, wi)
    m_x18_0 = _metrics(nav_x18_0, wi)

    print(f"\n  At 0 cost (gross alpha):")
    print(f"    Base: Sh={m_base_0['sharpe']:.4f}, CAGR={m_base_0['cagr']:.1f}%")
    print(f"    X18:  Sh={m_x18_0['sharpe']:.4f}, CAGR={m_x18_0['cagr']:.1f}%")
    print(f"    ΔSh(gross) = {m_x18_0['sharpe'] - m_base_0['sharpe']:+.4f}")

    # Run at multiple costs to find crossover
    print(f"\n  Crossover analysis:")
    for c in COST_BPS:
        cps_c = c / 20_000.0
        nb, _ = _sim_base(cl, ef, es, vd, at, regime_h4, wi, cps_c)
        nx, _, _ = _sim_binary_x18(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps_c,
            model_w, model_mu, model_std, x18_thresh)
        mb = _metrics(nb, wi); mx = _metrics(nx, wi)
        delta = mx["sharpe"] - mb["sharpe"]
        winner = "X18" if delta > 0 else "Base"
        print(f"    {c:3d} bps: Base Sh={mb['sharpe']:.3f}, X18 Sh={mx['sharpe']:.3f}, "
              f"Δ={delta:+.3f} → {winner}")


# =========================================================================
# PART B: SIGNAL QUALITY
# =========================================================================

def part_b(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, monitor_h4, wi,
            trades_base_25, model_w, model_mu, model_std):
    """Do Monitor and X18 signals carry useful information?"""
    print("\n" + "=" * 70)
    print("PART B: Signal Quality Assessment")
    print("=" * 70)

    n = len(cl)

    # B1: Monitor — trade outcomes by regime at entry
    print("\n  B1: Trade outcomes by Monitor regime at entry")
    regime_trades = {"NORMAL": [], "AMBER": [], "RED_would_enter": []}
    for t in trades_base_25:
        eb = t["entry_bar"]
        if eb < len(monitor_h4):
            alert = int(monitor_h4[eb])
            if alert == 0:
                regime_trades["NORMAL"].append(t)
            elif alert == 1:
                regime_trades["AMBER"].append(t)
            # RED: no trades entered (blocked), but we want to know what WOULD happen
            # Can't directly measure — those entries were blocked

    for regime, tr_list in regime_trades.items():
        if not tr_list:
            print(f"    {regime}: no trades")
            continue
        rets = [t["ret_pct"] for t in tr_list]
        wins = sum(1 for r in rets if r > 0)
        print(f"    {regime}: {len(tr_list)} trades, WR={wins/len(tr_list):.1%}, "
              f"avg ret={np.mean(rets):+.2f}%, med ret={np.median(rets):+.2f}%")

    # How many entry bars are in AMBER territory? (potential sizing opportunity)
    n_amber_bars = int(np.sum(monitor_h4[wi:] == 1))
    n_red_bars = int(np.sum(monitor_h4[wi:] == 2))
    total_bars = n - wi
    print(f"\n    AMBER bars: {n_amber_bars} ({n_amber_bars/total_bars*100:.1f}%)")
    print(f"    RED bars: {n_red_bars} ({n_red_bars/total_bars*100:.1f}%)")

    # Count entries that would occur during AMBER
    n_amber_entries = 0
    for i in range(wi, n):
        if (not math.isnan(at[i]) and not math.isnan(ef[i]) and not math.isnan(es[i])
                and ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]
                and monitor_h4[i] == 1):
            n_amber_entries += 1
    print(f"    Entry signals during AMBER: {n_amber_entries}")

    # B2: Churn score — outcome by score quartile
    print("\n  B2: Trail-stop outcomes by churn score quartile")
    trail_trades = [t for t in trades_base_25 if t["exit_reason"] == "trail_stop"]
    print(f"    Trail-stop trades: {len(trail_trades)}")

    if trail_trades:
        # Score each trail-stop bar
        scored = []
        for t in trail_trades:
            sb = t["exit_bar"] - 1
            if sb < 0 or sb >= n or math.isnan(at[sb]) or math.isnan(ef[sb]):
                continue
            feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
            score = _predict_score(feat, model_w, model_mu, model_std)
            scored.append({"score": score, "ret_pct": t["ret_pct"], "bars_held": t["bars_held"]})

        if scored:
            scores = np.array([s["score"] for s in scored])
            rets = np.array([s["ret_pct"] for s in scored])
            # Quartiles
            q25, q50, q75 = np.percentile(scores, [25, 50, 75])
            for label, mask in [("Q1 (low score)", scores <= q25),
                                ("Q2", (scores > q25) & (scores <= q50)),
                                ("Q3", (scores > q50) & (scores <= q75)),
                                ("Q4 (high score)", scores > q75)]:
                r = rets[mask]
                if len(r) > 0:
                    print(f"    {label}: n={len(r)}, avg ret={np.mean(r):+.2f}%, "
                          f"med ret={np.median(r):+.2f}%, WR={np.mean(r>0):.1%}")


# =========================================================================
# PART C: FRACTIONAL ACTUATOR PILOT
# =========================================================================

def part_c(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, monitor_h4, wi,
            model_w, model_mu, model_std, x18_thresh):
    """Test fractional actuators at all cost levels."""
    print("\n" + "=" * 70)
    print("PART C: Fractional Actuator Pilot")
    print("=" * 70)
    print(f"  Monitor sizing: NORMAL={F_NORMAL}, AMBER={F_AMBER}, RED={F_RED}")
    print(f"  X18 partial: keep {PARTIAL_FRAC:.0%} on churn suppress")

    strategies = {
        "Base":        lambda cps: _sim_base(cl, ef, es, vd, at, regime_h4, wi, cps),
        "Mon(binary)": lambda cps: _sim_binary_monitor(cl, ef, es, vd, at, regime_h4, monitor_h4, wi, cps)[:2],
        "X18(binary)": lambda cps: _sim_binary_x18(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
                                                    model_w, model_mu, model_std, x18_thresh)[:2],
        "Mon(sizing)": lambda cps: _sim_monitor_sizing(cl, ef, es, vd, at, regime_h4, monitor_h4, wi, cps),
        "X18(partial)": lambda cps: _sim_x18_partial(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
                                                      model_w, model_mu, model_std, x18_thresh)[:2],
        "Combined(frac)": lambda cps: _sim_combined_frac(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4,
                                                          monitor_h4, wi, cps,
                                                          model_w, model_mu, model_std, x18_thresh),
    }

    rows = []
    for cost_bps in COST_BPS:
        cps = cost_bps / 20_000.0
        line = f"  {cost_bps:3d} bps:"
        for sname, sfunc in strategies.items():
            nav, trades = sfunc(cps)
            m = _metrics(nav, wi, len(trades))
            rows.append({"strategy": sname, "cost_bps": cost_bps, **m})
            line += f"  {sname}={m['sharpe']:.3f}"
        print(line)

    # Write CSV
    csv_path = OUTDIR / "tables" / "Tbl_fractional_pilot.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "cost_bps", "sharpe", "cagr", "mdd", "calmar", "trades"])
        for r in rows:
            w.writerow([r["strategy"], r["cost_bps"], f"{r['sharpe']:.4f}",
                        f"{r['cagr']:.2f}", f"{r['mdd']:.2f}", f"{r['calmar']:.4f}", r["trades"]])
    print(f"\n  Saved: {csv_path}")

    # Summary at key costs
    print(f"\n  Summary — Delta vs Base at key costs:")
    for cost_bps in [15, 25, 50]:
        base_sh = next(r["sharpe"] for r in rows
                       if r["strategy"] == "Base" and r["cost_bps"] == cost_bps)
        print(f"\n    {cost_bps} bps (Base Sh={base_sh:.3f}):")
        for sname in strategies:
            if sname == "Base":
                continue
            sh = next(r["sharpe"] for r in rows
                      if r["strategy"] == sname and r["cost_bps"] == cost_bps)
            mdd = next(r["mdd"] for r in rows
                       if r["strategy"] == sname and r["cost_bps"] == cost_bps)
            delta = sh - base_sh
            print(f"      {sname:18s}: Sh={sh:.3f} (Δ={delta:+.3f}), MDD={mdd:.1f}%")

    return rows


# =========================================================================
# PART D: BOOTSTRAP FRACTIONAL (quick, 25 bps only)
# =========================================================================

def part_d(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4,
           monitor_h4, wi, h4_ct, d1_cl, d1_ct,
           model_w, model_mu, model_std, x18_thresh):
    """Quick bootstrap of fractional vs binary at 25 bps."""
    print("\n" + "=" * 70)
    print("PART D: Bootstrap Fractional vs Base (500 VCBB, 25 bps)")
    print("=" * 70)

    cps = 25 / 20_000.0

    cl_pw = cl[wi:]; hi_pw = hi[wi:]; lo_pw = lo[wi:]; vo_pw = vo[wi:]; tb_pw = tb[wi:]
    cr, hr, lr, vol_r, tb_r = make_ratios(cl_pw, hi_pw, lo_pw, vo_pw, tb_pw)
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = len(cl) - wi - 1; p0 = cl[wi]
    rng = np.random.default_rng(SEED)
    reg_pw = regime_h4[wi:]
    d1s_pw = d1_str_h4[wi:]

    # For bootstrap, compute Monitor on H4 prices directly
    from x29_monitor_diagnostic import _compute_h4_monitor

    ds = {"Mon(binary)": [], "Mon(sizing)": [], "X18(partial)": [], "Combined(frac)": []}

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        nb = len(bcl)
        bef = _ema(bcl, max(5, SLOW // 4)); bes = _ema(bcl, SLOW)
        bvd = _vdo(bcl, bhi, blo, bvo, btb)
        bat = _robust_atr(bhi, blo, bcl)
        breg = reg_pw[:nb] if len(reg_pw) >= nb else np.ones(nb, dtype=np.bool_)
        bd1s = d1s_pw[:nb] if len(d1s_pw) >= nb else np.zeros(nb)
        bmon = _compute_h4_monitor(bcl)

        # Base
        nb_base, _ = _sim_base(bcl, bef, bes, bvd, bat, breg, 0, cps)
        mb = _metrics(nb_base, 0)

        # Mon(binary)
        nb_mon, _, _ = _sim_binary_monitor(bcl, bef, bes, bvd, bat, breg, bmon, 0, cps)
        mm = _metrics(nb_mon, 0)
        ds["Mon(binary)"].append(mm["sharpe"] - mb["sharpe"])

        # Mon(sizing)
        nb_ms, _ = _sim_monitor_sizing(bcl, bef, bes, bvd, bat, breg, bmon, 0, cps)
        mms = _metrics(nb_ms, 0)
        ds["Mon(sizing)"].append(mms["sharpe"] - mb["sharpe"])

        # X18(partial)
        nb_xp, _, _ = _sim_x18_partial(bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1s, 0, cps,
                                         model_w, model_mu, model_std, x18_thresh)
        mxp = _metrics(nb_xp, 0)
        ds["X18(partial)"].append(mxp["sharpe"] - mb["sharpe"])

        # Combined
        nb_cf, _ = _sim_combined_frac(bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1s,
                                       bmon, 0, cps,
                                       model_w, model_mu, model_std, x18_thresh)
        mcf = _metrics(nb_cf, 0)
        ds["Combined(frac)"].append(mcf["sharpe"] - mb["sharpe"])

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    print("\n  Results:")
    for sname, deltas in ds.items():
        d = np.array(deltas)
        print(f"    {sname:18s}: P(Δsh>0)={np.mean(d > 0)*100:.1f}%, "
              f"med Δsh={np.median(d):+.4f}, mean={np.mean(d):+.4f}")

    return ds


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    print("=" * 70)
    print("X29 Signal Diagnostic + Fractional Actuator Pilot")
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

    n = len(cl); wi = 0
    if feed.report_start_ms:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms: wi = j; break
    print(f"  H4: {n}, D1: {len(d1_cl)}, warmup: {wi}")

    # Indicators
    ef = _ema(cl, max(5, SLOW // 4)); es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb); at = _robust_atr(hi, lo, cl)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    # Monitor
    d1_alerts = _compute_monitor_alerts_d1(d1_cl)
    monitor_h4 = _map_d1_alert_to_h4(d1_alerts, d1_ct, h4_ct)

    # Train churn model
    cps_50 = SCENARIOS["harsh"].per_side_bps / 10_000.0
    nav_base_50, trades_base_50 = _sim_base(cl, ef, es, vd, at, regime_h4, wi, cps_50)
    model_w, model_mu, model_std, best_c, n_train = _train_churn_model(
        trades_base_50, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    print(f"  Churn model: C={best_c}, n_train={n_train}")

    # X18 threshold
    scores = []
    for t in trades_base_50:
        if t.get("exit_reason") != "trail_stop": continue
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n or math.isnan(at[sb]) or math.isnan(ef[sb]): continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        scores.append(_predict_score(feat, model_w, model_mu, model_std))
    x18_thresh = float(np.percentile(scores, 100 - X18_ALPHA))
    print(f"  X18 threshold: {x18_thresh:.3f}")

    # Base trades at 25 bps
    _, trades_base_25 = _sim_base(cl, ef, es, vd, at, regime_h4, wi, 25 / 20_000.0)

    # === PARTS ===
    part_a(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi,
           model_w, model_mu, model_std, x18_thresh, trades_base_25)

    part_b(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, monitor_h4, wi,
           trades_base_25, model_w, model_mu, model_std)

    rows_c = part_c(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, monitor_h4, wi,
                     model_w, model_mu, model_std, x18_thresh)

    # Part D: Bootstrap (expensive, run last)
    part_d(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4,
           monitor_h4, wi, h4_ct, d1_cl, d1_ct,
           model_w, model_mu, model_std, x18_thresh)

    print(f"\nTotal time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
