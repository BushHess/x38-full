#!/usr/bin/env python3
"""X30 Elastic Net Experiment — Replace L2 Logistic with Elastic Net

Hypothesis: L1 component may select features better, producing more stable
OOS scores and potentially improving WFO/Bootstrap performance.

Changes from x30_validate.py:
  - Model: L2 Logistic → Elastic Net Logistic (ISTA solver)
  - Grid search: C × l1_ratio (25 combinations) with 5-fold CV AUC
  - Everything else (sims, WFO structure, bootstrap) identical

Output: tables/enet_summary.json, console comparison
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
from scipy.stats import ks_2samp

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# =========================================================================
# CONSTANTS (identical to x30_validate.py)
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
X18_ALPHA = 40
PRIMARY_CPS = 25 / 20_000.0
TRAIN_CPS = 50 / 20_000.0

N_BOOT = 500
BLKSZ = 60
SEED = 42

OUTDIR = Path(__file__).resolve().parents[1]
TABLES = OUTDIR / "tables"
FIGURES = OUTDIR / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

WFO_FOLDS = [
    ("2019-01-01", "2021-06-30", "2021-07-01", "2022-12-31"),
    ("2019-01-01", "2022-12-31", "2023-01-01", "2024-06-30"),
    ("2019-01-01", "2024-06-30", "2024-07-01", "2025-06-30"),
    ("2019-01-01", "2025-06-30", "2025-07-01", "2026-02-20"),
]

# Elastic Net grid
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
L1_RATIOS = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9]  # 0.0 = pure L2 (baseline)


# =========================================================================
# INDICATORS (identical)
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
    ts = np.maximum(vo - tb, 0.0); vdr = np.zeros(len(cl))
    m = vo > 1e-12; vdr[m] = (tb[m] - ts[m]) / vo[m]
    return _ema(vdr, fast) - _ema(vdr, slow)


def _compute_d1_regime(h4_ct, d1_cl, d1_ct, p=D1_EMA_P):
    d1_ema = _ema(d1_cl, p); d1_reg = d1_cl > d1_ema
    n_h4 = len(h4_ct); out = np.zeros(n_h4, dtype=np.bool_)
    j = 0; nd = len(d1_cl)
    for i in range(n_h4):
        while j + 1 < nd and d1_ct[j + 1] < h4_ct[i]: j += 1
        if d1_ct[j] < h4_ct[i]: out[i] = d1_reg[j]
    return out


def _compute_d1_regime_str(h4_ct, d1_cl, d1_ct, p=D1_EMA_P):
    d1_ema = _ema(d1_cl, p)
    d1_s = np.where(d1_cl > 1e-12, (d1_cl - d1_ema) / d1_cl, 0.0)
    n_h4 = len(h4_ct); out = np.zeros(n_h4)
    j = 0; nd = len(d1_cl)
    for i in range(n_h4):
        while j + 1 < nd and d1_ct[j + 1] < h4_ct[i]: j += 1
        if d1_ct[j] < h4_ct[i]: out[i] = d1_s[j]
    return out


# =========================================================================
# ELASTIC NET LOGISTIC REGRESSION (ISTA solver)
# =========================================================================

def _soft_threshold(x, t):
    """Proximal operator for L1: sign(x) * max(|x| - t, 0)"""
    return np.sign(x) * np.maximum(np.abs(x) - t, 0.0)


def _fit_elastic_net(X, y, C=1.0, l1_ratio=0.5, max_iter=2000, tol=1e-7):
    """Elastic Net logistic regression via FISTA (accelerated proximal GD).

    Penalty: (1/C) * [l1_ratio * ||w||_1 + (1-l1_ratio)/2 * ||w||_2^2]
    Bias term is NOT regularized.

    When l1_ratio=0.0: equivalent to L2 logistic (same as _fit_logistic_l2).
    """
    n, d = X.shape
    Xa = np.column_stack([X, np.ones(n)])
    w = np.zeros(d + 1)
    w_prev = w.copy()

    lam1 = l1_ratio / C       # L1 penalty strength
    lam2 = (1 - l1_ratio) / C  # L2 penalty strength

    # Lipschitz constant: max eigenvalue of (X^T X / (4n)) + lam2
    XtX = Xa.T @ Xa / n
    L = float(np.max(np.linalg.eigvalsh(XtX))) / 4.0 + lam2
    eta = 1.0 / L  # step size

    t_fista = 1.0  # FISTA momentum parameter

    for it in range(max_iter):
        # FISTA momentum
        t_new = (1 + math.sqrt(1 + 4 * t_fista ** 2)) / 2
        beta = (t_fista - 1) / t_new
        t_fista = t_new

        # Extrapolation point
        v = w + beta * (w - w_prev)
        w_prev = w.copy()

        # Forward pass at extrapolation point
        z = Xa @ v
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

        # Gradient of smooth part (loss + L2)
        err = p - y
        grad = Xa.T @ err / n
        grad[:d] += lam2 * v[:d]  # L2 gradient (features only)

        # Gradient step
        w_temp = v - eta * grad

        # Proximal step: soft-threshold features, keep bias untouched
        w = np.empty(d + 1)
        w[:d] = _soft_threshold(w_temp[:d], eta * lam1)
        w[d] = w_temp[d]

        # Convergence check
        if np.max(np.abs(w - w_prev)) < tol:
            break

    return w


def _fit_logistic_l2(X, y, C=1.0, max_iter=100):
    """L2-regularized logistic regression via Newton-Raphson (original)."""
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


# =========================================================================
# CHURN MODEL
# =========================================================================

FEATURE_NAMES = [
    "ema_ratio", "atr_pctl", "bar_range_atr",
    "close_position", "vdo", "d1_regime_str", "trail_tightness",
]


def _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    f1 = ef[i] / es[i] if abs(es[i]) > 1e-12 else 1.0
    s = max(0, i - 99); w = at[s:i + 1]; v = w[~np.isnan(w)]
    f2 = float(np.sum(v <= at[i])) / len(v) if len(v) > 1 else 0.5
    f3 = (hi[i] - lo[i]) / at[i] if at[i] > 1e-12 else 1.0
    bw = hi[i] - lo[i]
    f4 = (cl[i] - lo[i]) / bw if bw > 1e-12 else 0.5
    f5 = float(vd[i]); f6 = float(d1_str_h4[i])
    f7 = TRAIL * at[i] / cl[i] if cl[i] > 1e-12 else 0.0
    return np.array([f1, f2, f3, f4, f5, f6, f7])


def _predict_score(feat, w, mu, std):
    fs = (feat - mu) / std
    z = np.dot(np.append(fs, 1.0), w)
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))


def _standardize(X):
    mu = np.mean(X, axis=0); std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


def _kfold_auc(X, y, C=1.0, l1_ratio=0.0, k=5, use_enet=False):
    """K-fold cross-validated AUC."""
    n = len(y); idx = np.arange(n)
    rng = np.random.default_rng(42); rng.shuffle(idx)
    aucs = []; fold_size = n // k
    for fold in range(k):
        s = fold * fold_size; e = s + fold_size if fold < k - 1 else n
        vi = idx[s:e]; ti = np.concatenate([idx[:s], idx[e:]])
        if len(np.unique(y[ti])) < 2: aucs.append(0.5); continue
        if use_enet and l1_ratio > 0:
            w = _fit_elastic_net(X[ti], y[ti], C=C, l1_ratio=l1_ratio)
        else:
            w = _fit_logistic_l2(X[ti], y[ti], C=C)
        pr = 1.0 / (1.0 + np.exp(-np.clip(
            np.column_stack([X[vi], np.ones(len(vi))]) @ w, -500, 500)))
        pos = pr[y[vi] == 1]; neg = pr[y[vi] == 0]
        if len(pos) == 0 or len(neg) == 0: aucs.append(0.5); continue
        aucs.append(float((np.sum(pos[:, None] > neg[None, :]) +
                           0.5 * np.sum(pos[:, None] == neg[None, :])) /
                          (len(pos) * len(neg))))
    return float(np.mean(aucs))


def _train_model_enet(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    """Train Elastic Net churn model. Grid search C × l1_ratio.

    Returns (w, mu, std, best_c, best_l1r, n_train, cv_auc, n_zero_feats).
    """
    entry_bars = sorted(t["entry_bar"] for t in trades)
    features, labels = [], []
    for t in trades:
        if t["exit_reason"] != "trail_stop": continue
        eb = t["exit_bar"]; sb = eb - 1
        if sb < 0 or sb >= len(cl): continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]): continue
        is_churn = any(eb < e <= eb + CHURN_WINDOW for e in entry_bars)
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        features.append(feat); labels.append(1 if is_churn else 0)
    if len(labels) < 10: return None, None, None, None, None, 0, 0.0, 0
    X = np.array(features); y = np.array(labels, dtype=int)
    if len(np.unique(y)) < 2: return None, None, None, None, None, 0, 0.0, 0
    Xs, mu, std = _standardize(X)

    best_c, best_l1r, best_auc = 1.0, 0.0, 0.0
    for c in C_VALUES:
        for l1r in L1_RATIOS:
            auc = _kfold_auc(Xs, y, C=c, l1_ratio=l1r, use_enet=(l1r > 0))
            if auc > best_auc:
                best_auc = auc; best_c = c; best_l1r = l1r

    # Train final model with best hyperparams
    if best_l1r > 0:
        w = _fit_elastic_net(Xs, y, C=best_c, l1_ratio=best_l1r)
    else:
        w = _fit_logistic_l2(Xs, y, C=best_c)

    n_zero = int(np.sum(np.abs(w[:-1]) < 1e-8))
    return w, mu, std, best_c, best_l1r, len(y), best_auc, n_zero


def _train_model_l2(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    """Train L2-only model (original, for comparison)."""
    entry_bars = sorted(t["entry_bar"] for t in trades)
    features, labels = [], []
    for t in trades:
        if t["exit_reason"] != "trail_stop": continue
        eb = t["exit_bar"]; sb = eb - 1
        if sb < 0 or sb >= len(cl): continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]): continue
        is_churn = any(eb < e <= eb + CHURN_WINDOW for e in entry_bars)
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        features.append(feat); labels.append(1 if is_churn else 0)
    if len(labels) < 10: return None, None, None, None, 0, 0.0
    X = np.array(features); y = np.array(labels, dtype=int)
    if len(np.unique(y)) < 2: return None, None, None, None, 0, 0.0
    Xs, mu, std = _standardize(X)
    best_c, best_auc = 1.0, 0.0
    for c in C_VALUES:
        auc = _kfold_auc(Xs, y, C=c)
        if auc > best_auc: best_auc = auc; best_c = c
    w = _fit_logistic_l2(Xs, y, C=best_c)
    return w, mu, std, best_c, len(y), best_auc


def _score_trail_stops(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                       model_w, model_mu, model_std):
    scores = []
    n = len(cl)
    for t in trades:
        if t.get("exit_reason") != "trail_stop": continue
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n: continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]): continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        scores.append(_predict_score(feat, model_w, model_mu, model_std))
    return scores


# =========================================================================
# METRICS
# =========================================================================

def _metrics(nav, wi):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0}
    rets = navs[1:] / navs[:-1] - 1.0
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    tr = navs[-1] / navs[0] - 1.0; yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    pk = np.maximum.accumulate(navs); mdd = np.max(1.0 - navs / pk) * 100
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}


def _metrics_window(nav, s, e):
    return _metrics(nav[s:e], 0)


def _date_to_bar_idx(h4_ct, date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ts_ms = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    return min(int(np.searchsorted(h4_ct, ts_ms, side='left')), len(h4_ct) - 1)


# =========================================================================
# SIM ENGINES (identical to x30_validate.py)
# =========================================================================

def _sim_base(cl, ef, es, vd, at, regime_h4, cps):
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False
    pk = 0.0; entry_bar = 0; entry_cost = 0.0; entry_px = 0.0; _er = ""
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
                px = False; rcv = bq * fp * (1 - cps)
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                               "entry_px": entry_px, "exit_px": fp, "peak_px": pk,
                               "pnl_usd": rcv - entry_cost,
                               "ret_pct": (rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _er})
                cash = rcv; bq = 0.0; inp = False; pk = 0.0
        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a: _er = "trail_stop"; px = True
            elif ef[i] < es[i]: _er = "trend_exit"; px = True
    if inp and bq > 0:
        rcv = bq * cl[-1] * (1 - cps)
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                       "entry_px": entry_px, "exit_px": cl[-1], "peak_px": pk,
                       "pnl_usd": rcv - entry_cost,
                       "ret_pct": (rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
        nav[-1] = rcv
    return nav, trades


def _sim_partial(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, cps,
                 model_w, model_mu, model_std, keep_frac_fn):
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False
    pk = 0.0; entry_bar = 0; entry_cost = 0.0; entry_px = 0.0; _er = ""
    nav = np.zeros(n); trades = []; n_partial = 0
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps)); entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p
            elif px:
                px = False; rcv = bq * fp * (1 - cps)
                total_rcv = cash + rcv
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                               "entry_px": entry_px, "exit_px": fp, "peak_px": pk,
                               "pnl_usd": total_rcv - entry_cost,
                               "ret_pct": (total_rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _er})
                cash = total_rcv; bq = 0.0; inp = False; pk = 0.0
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
                kf = keep_frac_fn(score)
                if kf < 0.01:
                    _er = "trail_stop"; px = True
                else:
                    sell_qty = bq * (1 - kf)
                    rcv_p = sell_qty * p * (1 - cps)
                    cash += rcv_p; bq -= sell_qty; n_partial += 1
                    if bq < 1e-12:
                        _er = "trail_stop_partial"; px = True
            elif ef[i] < es[i]:
                _er = "trend_exit"; px = True
    if inp and bq > 0:
        rcv = bq * cl[-1] * (1 - cps)
        total_rcv = cash + rcv
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                       "entry_px": entry_px, "exit_px": cl[-1], "peak_px": pk,
                       "pnl_usd": total_rcv - entry_cost,
                       "ret_pct": (total_rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
        cash = total_rcv; bq = 0.0; nav[-1] = cash
    return nav, trades, n_partial


# =========================================================================
# KEEP-FRACTION FUNCTIONS
# =========================================================================

def make_discrete_fn(thresh, partial_frac):
    def fn(score):
        return partial_frac if score > thresh else 0.0
    return fn


def make_b2_fn(lo_thresh, hi_thresh, max_frac):
    def fn(score):
        if score <= lo_thresh: return 0.0
        if score >= hi_thresh: return max_frac
        return max_frac * (score - lo_thresh) / (hi_thresh - lo_thresh)
    return fn


# =========================================================================
# CANDIDATES (from Phase 2)
# =========================================================================

CANDIDATES = [
    {"name": "discrete_pf90", "type": "discrete", "partial_frac": 0.9,
     "design": None, "params": {"threshold": 0.6867}},
    {"name": "B2_mf60", "type": "continuous", "partial_frac": None,
     "design": "B2", "params": {"lo": 0.5046, "hi": 0.7558, "max_frac": 0.6}},
    {"name": "B2_mf80", "type": "continuous", "partial_frac": None,
     "design": "B2", "params": {"lo": 0.5046, "hi": 0.7558, "max_frac": 0.8}},
]


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    print("=" * 70)
    print("X30 ELASTIC NET EXPERIMENT")
    print("=" * 70)

    # ── Load data ────────────────────────────────────────────────────────
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

    n = len(cl); wi = 0
    if feed.report_start_ms:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms: wi = j; break
    print(f"  H4: {n}, D1: {len(d1_cl)}, warmup: {wi}")

    # ── Indicators ───────────────────────────────────────────────────────
    print("Computing indicators...")
    ef = _ema(cl, max(5, SLOW // 4)); es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb); at = _robust_atr(hi, lo, cl)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    # ── Base sim (50 bps for training, 25 bps for eval) ──────────────────
    print("Running base sims...")
    nav_train50, trades_train50 = _sim_base(cl, ef, es, vd, at, regime_h4, TRAIN_CPS)
    nav_base25, _ = _sim_base(cl, ef, es, vd, at, regime_h4, PRIMARY_CPS)

    # ── Train full-sample models (both L2 and Elastic Net) ───────────────
    print("\n--- FULL-SAMPLE MODEL COMPARISON ---")

    # L2 model
    l2_w, l2_mu, l2_std, l2_c, l2_n, l2_auc = _train_model_l2(
        trades_train50, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    print(f"  L2 Logistic: C={l2_c}, CV AUC={l2_auc:.4f}, n={l2_n}")

    # Elastic Net model
    en_w, en_mu, en_std, en_c, en_l1r, en_n, en_auc, en_nz = _train_model_enet(
        trades_train50, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    print(f"  Elastic Net: C={en_c}, l1_ratio={en_l1r}, CV AUC={en_auc:.4f}, "
          f"n={en_n}, zeroed_features={en_nz}")

    # Feature weights comparison
    print("\n  Feature weights comparison:")
    print(f"  {'Feature':20s}  {'L2':>10s}  {'ENet':>10s}  {'ENet zero?':>10s}")
    for fi, fname in enumerate(FEATURE_NAMES):
        l2_wf = l2_w[fi] if l2_w is not None else 0.0
        en_wf = en_w[fi] if en_w is not None else 0.0
        zero = "ZERO" if abs(en_wf) < 1e-8 else ""
        print(f"  {fname:20s}  {l2_wf:+10.4f}  {en_wf:+10.4f}  {zero:>10s}")

    # Score distributions
    l2_scores = _score_trail_stops(trades_train50, cl, hi, lo, at, ef, es, vd,
                                   d1_str_h4, l2_w, l2_mu, l2_std)
    en_scores = _score_trail_stops(trades_train50, cl, hi, lo, at, ef, es, vd,
                                   d1_str_h4, en_w, en_mu, en_std)
    l2_arr = np.array(l2_scores)
    en_arr = np.array(en_scores)

    corr = float(np.corrcoef(l2_arr, en_arr)[0, 1])
    print(f"\n  Score correlation (L2 vs ENet): {corr:.4f}")
    print(f"  L2 scores: mean={np.mean(l2_arr):.4f}, std={np.std(l2_arr):.4f}")
    print(f"  EN scores: mean={np.mean(en_arr):.4f}, std={np.std(en_arr):.4f}")

    # Thresholds
    l2_t60 = float(np.percentile(l2_arr, 100 - X18_ALPHA))
    l2_p25 = float(np.percentile(l2_arr, 25))
    l2_p75 = float(np.percentile(l2_arr, 75))
    en_t60 = float(np.percentile(en_arr, 100 - X18_ALPHA))
    en_p25 = float(np.percentile(en_arr, 25))
    en_p75 = float(np.percentile(en_arr, 75))

    print(f"  L2 thresholds: P60={l2_t60:.4f}, P25={l2_p25:.4f}, P75={l2_p75:.4f}")
    print(f"  EN thresholds: P60={en_t60:.4f}, P25={en_p25:.4f}, P75={en_p75:.4f}")

    # ==================================================================
    # WFO: Compare L2 vs Elastic Net for all candidates
    # ==================================================================
    print(f"\n{'=' * 70}")
    print("WFO COMPARISON: L2 vs Elastic Net")
    print(f"{'=' * 70}")

    cnames = [c["name"] for c in CANDIDATES]
    wfo_results = {"l2": {cn: [] for cn in cnames}, "enet": {cn: [] for cn in cnames}}

    for fold_idx, (ts, te, os_s, os_e) in enumerate(WFO_FOLDS):
        print(f"\n  Fold {fold_idx + 1}: Train →{te}, OOS {os_s}→{os_e}")

        te_idx = _date_to_bar_idx(h4_ct, te)
        oos_s_idx = _date_to_bar_idx(h4_ct, os_s)
        oos_e_idx = _date_to_bar_idx(h4_ct, os_e)

        fold_trades = [t for t in trades_train50 if t["exit_bar"] <= te_idx]

        # Train both models on fold data
        fl2_w, fl2_mu, fl2_std, fl2_c, fl2_n, fl2_auc = _train_model_l2(
            fold_trades, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        fen_w, fen_mu, fen_std, fen_c, fen_l1r, fen_n, fen_auc, fen_nz = _train_model_enet(
            fold_trades, cl, hi, lo, at, ef, es, vd, d1_str_h4)

        if fl2_w is None or fen_w is None:
            print(f"    MODEL FAILED")
            for cn in cnames:
                wfo_results["l2"][cn].append(0.0)
                wfo_results["enet"][cn].append(0.0)
            continue

        print(f"    L2:   C={fl2_c}, AUC={fl2_auc:.4f}")
        print(f"    ENet: C={fen_c}, l1r={fen_l1r}, AUC={fen_auc:.4f}, "
              f"zeroed={fen_nz}/7")

        # Fold-specific thresholds from each model's scores
        fl2_scores = _score_trail_stops(fold_trades, cl, hi, lo, at, ef, es, vd,
                                        d1_str_h4, fl2_w, fl2_mu, fl2_std)
        fen_scores = _score_trail_stops(fold_trades, cl, hi, lo, at, ef, es, vd,
                                        d1_str_h4, fen_w, fen_mu, fen_std)

        fl2_arr = np.array(fl2_scores)
        fen_arr = np.array(fen_scores)

        fl2_t = float(np.percentile(fl2_arr, 100 - X18_ALPHA))
        fl2_p25 = float(np.percentile(fl2_arr, 25))
        fl2_p75 = float(np.percentile(fl2_arr, 75))
        fen_t = float(np.percentile(fen_arr, 100 - X18_ALPHA))
        fen_p25 = float(np.percentile(fen_arr, 25))
        fen_p75 = float(np.percentile(fen_arr, 75))

        # Base OOS metrics
        mb = _metrics_window(nav_base25, oos_s_idx, oos_e_idx + 1)

        # Each candidate × each model
        for c in CANDIDATES:
            cn = c["name"]

            for model_name, mw, mmu, mstd, mt, mp25, mp75 in [
                ("l2", fl2_w, fl2_mu, fl2_std, fl2_t, fl2_p25, fl2_p75),
                ("enet", fen_w, fen_mu, fen_std, fen_t, fen_p25, fen_p75),
            ]:
                if c["type"] == "discrete":
                    kfn = make_discrete_fn(mt, c["partial_frac"])
                elif c["design"] == "B2":
                    kfn = make_b2_fn(mp25, mp75, c["params"]["max_frac"])
                else:
                    continue

                nav_c, _, _ = _sim_partial(
                    cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, PRIMARY_CPS,
                    mw, mmu, mstd, kfn)
                mc = _metrics_window(nav_c, oos_s_idx, oos_e_idx + 1)
                dsh = mc["sharpe"] - mb["sharpe"]
                wfo_results[model_name][cn].append(dsh)

        # Print fold summary
        print(f"    Base OOS: Sh={mb['sharpe']:.4f}")
        for cn in cnames:
            l2_dsh = wfo_results["l2"][cn][-1]
            en_dsh = wfo_results["enet"][cn][-1]
            print(f"    {cn}: L2 ΔSh={l2_dsh:+.4f}, ENet ΔSh={en_dsh:+.4f}")

    # WFO Summary
    print(f"\n{'=' * 70}")
    print("WFO SUMMARY")
    print(f"{'=' * 70}")
    print(f"  {'Candidate':20s}  {'Model':6s}  {'Wins':>5s}  {'Mean ΔSh':>10s}")

    best_model = "l2"
    best_cand = cnames[0]
    best_wins = 0

    for cn in cnames:
        for mn in ["l2", "enet"]:
            vals = wfo_results[mn][cn]
            wins = sum(1 for v in vals if v > 0)
            mean_d = float(np.mean(vals))
            print(f"  {cn:20s}  {mn:6s}  {wins:>5d}/4  {mean_d:+10.4f}")
            if wins > best_wins:
                best_wins = wins
                best_model = mn
                best_cand = cn

    # ==================================================================
    # BOOTSTRAP: Best model variant
    # ==================================================================
    print(f"\n{'=' * 70}")
    print(f"BOOTSTRAP: L2 vs Elastic Net ({N_BOOT} paths)")
    print(f"{'=' * 70}")

    # Prepare VCBB
    cl_pw = cl[wi:]; hi_pw = hi[wi:]; lo_pw = lo[wi:]
    vo_pw = vo[wi:]; tb_pw = tb[wi:]
    cr, hr, lr, vol_r, tb_r = make_ratios(cl_pw, hi_pw, lo_pw, vo_pw, tb_pw)
    vcbb_state = precompute_vcbb(cr, BLKSZ)
    n_trans = len(cl) - wi - 1; p0 = cl[wi]
    rng = np.random.default_rng(SEED)
    reg_pw = regime_h4[wi:]
    d1s_pw = d1_str_h4[wi:]

    # Build keep_frac functions with full-sample thresholds for both models
    def _make_fns(model_t60, model_p25, model_p75):
        fns = {}
        for c in CANDIDATES:
            cn = c["name"]
            if c["type"] == "discrete":
                fns[cn] = make_discrete_fn(model_t60, c["partial_frac"])
            elif c["design"] == "B2":
                fns[cn] = make_b2_fn(model_p25, model_p75, c["params"]["max_frac"])
        return fns

    l2_fns = _make_fns(l2_t60, l2_p25, l2_p75)
    en_fns = _make_fns(en_t60, en_p25, en_p75)

    # Test only the best candidate from each model (+ B2_mf60 always)
    test_cands = list(set(["discrete_pf90", "B2_mf60"]))

    boot = {}
    for mn in ["l2", "enet"]:
        for cn in test_cands:
            boot[f"{mn}_{cn}"] = {"dsh": [], "dmdd": []}

    print(f"  Running {N_BOOT} bootstrap paths...")
    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb_state)
        nb = len(bcl)
        bef = _ema(bcl, max(5, SLOW // 4)); bes = _ema(bcl, SLOW)
        bvd = _vdo(bcl, bhi, blo, bvo, btb)
        bat = _robust_atr(bhi, blo, bcl)
        breg = reg_pw[:nb] if len(reg_pw) >= nb else np.ones(nb, dtype=np.bool_)
        bd1s = d1s_pw[:nb] if len(d1s_pw) >= nb else np.zeros(nb)

        # Base
        bnav_b, _ = _sim_base(bcl, bef, bes, bvd, bat, breg, PRIMARY_CPS)
        mb = _metrics(bnav_b, 0)

        # Each model × each candidate
        for cn in test_cands:
            for mn, mw, mmu, mstd, fns in [
                ("l2", l2_w, l2_mu, l2_std, l2_fns),
                ("enet", en_w, en_mu, en_std, en_fns),
            ]:
                bnav_c, _, _ = _sim_partial(
                    bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1s, PRIMARY_CPS,
                    mw, mmu, mstd, fns[cn])
                mc = _metrics(bnav_c, 0)
                key = f"{mn}_{cn}"
                boot[key]["dsh"].append(mc["sharpe"] - mb["sharpe"])
                boot[key]["dmdd"].append(mc["mdd"] - mb["mdd"])

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    # Bootstrap Summary
    print(f"\n{'=' * 70}")
    print("BOOTSTRAP SUMMARY")
    print(f"{'=' * 70}")
    print(f"  {'Model_Cand':25s}  {'P(ΔSh>0)':>10s}  {'Med ΔSh':>10s}  "
          f"{'P(ΔMDD<0)':>10s}  {'Med ΔMDD':>10s}")

    boot_summary = {}
    for key in sorted(boot.keys()):
        dsh = np.array(boot[key]["dsh"])
        dmdd = np.array(boot[key]["dmdd"])
        p_dsh = float(np.mean(dsh > 0))
        med_dsh = float(np.median(dsh))
        p_dmdd = float(np.mean(dmdd < 0))
        med_dmdd = float(np.median(dmdd))
        boot_summary[key] = {
            "p_dsh": round(p_dsh, 4),
            "med_dsh": round(med_dsh, 4),
            "p_dmdd": round(p_dmdd, 4),
            "med_dmdd": round(med_dmdd, 2),
        }
        print(f"  {key:25s}  {p_dsh*100:>9.1f}%  {med_dsh:>+10.4f}  "
              f"{p_dmdd*100:>9.1f}%  {med_dmdd:>+10.1f}pp")

    # ==================================================================
    # VERDICT
    # ==================================================================
    print(f"\n{'=' * 70}")
    print("ELASTIC NET EXPERIMENT — VERDICT")
    print(f"{'=' * 70}")

    # Compare best P(ΔSh>0) across all model/candidate combinations
    best_key = max(boot_summary, key=lambda k: boot_summary[k]["p_dsh"])
    best_p = boot_summary[best_key]["p_dsh"]
    l2_best_key = max([k for k in boot_summary if k.startswith("l2_")],
                       key=lambda k: boot_summary[k]["p_dsh"])
    en_best_key = max([k for k in boot_summary if k.startswith("enet_")],
                       key=lambda k: boot_summary[k]["p_dsh"])

    print(f"  L2 best:   {l2_best_key} → P(ΔSh>0)={boot_summary[l2_best_key]['p_dsh']*100:.1f}%")
    print(f"  ENet best: {en_best_key} → P(ΔSh>0)={boot_summary[en_best_key]['p_dsh']*100:.1f}%")

    enet_better = boot_summary[en_best_key]["p_dsh"] > boot_summary[l2_best_key]["p_dsh"]
    print(f"\n  Elastic Net {'BETTER' if enet_better else 'WORSE/SAME'} than L2")
    print(f"  Gate G3 (≥55%): {'PASS' if best_p >= 0.55 else 'FAIL'} (best={best_p*100:.1f}%)")

    if best_p >= 0.55:
        print("  → Elastic Net CHANGES the verdict! Further investigation needed.")
    else:
        print("  → Elastic Net does NOT change the verdict. REJECT stands.")

    # Save summary
    summary = {
        "l2_model": {
            "C": float(l2_c), "cv_auc": round(l2_auc, 4),
        },
        "enet_model": {
            "C": float(en_c), "l1_ratio": float(en_l1r),
            "cv_auc": round(en_auc, 4), "zeroed_features": int(en_nz),
        },
        "score_correlation": round(corr, 4),
        "wfo_results": {
            mn: {cn: {"wins": sum(1 for v in vals if v > 0), "mean_dsh": round(float(np.mean(vals)), 4)}
                 for cn, vals in model_results.items()}
            for mn, model_results in wfo_results.items()
        },
        "bootstrap": boot_summary,
        "enet_changes_verdict": bool(best_p >= 0.55),
        "best_overall": best_key,
        "best_p_dsh": round(best_p, 4),
    }
    with open(TABLES / "enet_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # ==================================================================
    # FIGURE: Score comparison
    # ==================================================================
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 1: L2 vs ENet score scatter
    ax = axes[0]
    ax.scatter(l2_arr, en_arr, alpha=0.5, s=20, c='steelblue')
    ax.plot([0, 1], [0, 1], 'r--', alpha=0.5)
    ax.set_xlabel("L2 Score"); ax.set_ylabel("ENet Score")
    ax.set_title(f"Score Correlation: r={corr:.3f}")

    # 2: Score distributions
    ax = axes[1]
    ax.hist(l2_arr, bins=25, alpha=0.5, label="L2", color="blue", density=True)
    ax.hist(en_arr, bins=25, alpha=0.5, label="ENet", color="orange", density=True)
    ax.set_xlabel("Churn Score"); ax.set_ylabel("Density")
    ax.set_title("Score Distributions"); ax.legend()

    # 3: Bootstrap ΔSh comparison
    ax = axes[2]
    keys_plot = sorted(boot.keys())
    data_plot = [np.array(boot[k]["dsh"]) for k in keys_plot]
    labels_short = [k.replace("_", "\n") for k in keys_plot]
    bp = ax.boxplot(data_plot, tick_labels=labels_short)
    ax.axhline(0, color="red", linestyle="--", alpha=0.5)
    ax.set_ylabel("ΔSharpe"); ax.set_title("Bootstrap ΔSharpe")
    for i, k in enumerate(keys_plot):
        p = boot_summary[k]["p_dsh"]
        y_pos = np.percentile(data_plot[i], 95)
        ax.annotate(f"P={p*100:.0f}%", (i + 1, y_pos), ha='center',
                    fontsize=8, fontweight='bold')

    fig.tight_layout()
    fig.savefig(FIGURES / "Fig_enet_comparison.png", dpi=150)
    plt.close(fig)

    print(f"\n  Artifacts: {TABLES / 'enet_summary.json'}")
    print(f"  Figure:    {FIGURES / 'Fig_enet_comparison.png'}")
    print(f"\nTotal time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
