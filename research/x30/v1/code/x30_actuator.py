#!/usr/bin/env python3
"""X30 Phase 2: Actuator Design

Parts:
  A: Partial fraction sweep (11 × 9 = 99 backtests)
  B: Continuous sizing designs (9 × 9 = 81 backtests)
  C: MDD mechanism analysis (vs Base(f=0.20/0.30) benchmarks)
  D: Cost interaction analysis

Gate A: (a) >=3 consecutive frac beat Base @25bps, (b) best dSh>0.03, (c) best wins >=7/9 costs
Gate B: Best continuous > best discrete @25bps
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

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

COST_BPS = [10, 15, 20, 25, 30, 35, 50, 75, 100]
PARTIAL_FRACS = [0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
X18_ALPHA = 40
B2_MAX_FRACS = [0.60, 0.70, 0.80, 0.90]
B3_MAX_FRACS = [0.60, 0.70, 0.80, 0.90]

OUTDIR = Path(__file__).resolve().parents[1]
TABLES = OUTDIR / "tables"
FIGURES = OUTDIR / "figures"


# =========================================================================
# INDICATORS (from x29/x30 Phase 1)
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
# CHURN MODEL (7 features, L2 logistic)
# =========================================================================

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


def _predict_score_single(feat, w, mu, std):
    fs = (feat - mu) / std
    z = np.dot(np.append(fs, 1.0), w)
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, z))))


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
    n = len(y); idx = np.arange(n)
    rng = np.random.default_rng(42); rng.shuffle(idx)
    aucs = []; fold_size = n // k
    for fold in range(k):
        s = fold * fold_size; e = s + fold_size if fold < k - 1 else n
        vi = idx[s:e]; ti = np.concatenate([idx[:s], idx[e:]])
        if len(np.unique(y[ti])) < 2: aucs.append(0.5); continue
        w = _fit_logistic_l2(X[ti], y[ti], C=C)
        pr = 1.0 / (1.0 + np.exp(-np.clip(
            np.column_stack([X[vi], np.ones(len(vi))]) @ w, -500, 500)))
        pos = pr[y[vi] == 1]; neg = pr[y[vi] == 0]
        if len(pos) == 0 or len(neg) == 0: aucs.append(0.5); continue
        aucs.append(float((np.sum(pos[:, None] > neg[None, :]) +
                           0.5 * np.sum(pos[:, None] == neg[None, :])) /
                          (len(pos) * len(neg))))
    return float(np.mean(aucs))


def _standardize(X):
    mu = np.mean(X, axis=0); std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


def _train_model(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    """Train churn model on trail-stop trades. Returns (w, mu, std, best_c, n_train)."""
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
    if len(labels) < 10: return None, None, None, None, 0
    X = np.array(features); y = np.array(labels, dtype=int)
    if len(np.unique(y)) < 2: return None, None, None, None, 0
    Xs, mu, std = _standardize(X)
    best_c, best_auc = 1.0, 0.0
    for c in C_VALUES:
        auc = _kfold_auc(Xs, y, C=c, k=5)
        if auc > best_auc: best_auc = auc; best_c = c
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
    """Base E5+EMA1D21, 100% invested."""
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False
    pk = 0.0; entry_bar = 0; entry_cost = 0.0; entry_px = 0.0; _er = ""
    nav = np.zeros(n); trades = []; exposure = np.zeros(n)
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
        if nav[i] > 0: exposure[i] = bq * p / nav[i]
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
    return nav, trades, exposure


def _sim_base_frac(cl, ef, es, vd, at, regime_h4, wi, cps, f):
    """Base sim with fractional allocation f (invest f of NAV at entry)."""
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False
    pk = 0.0; entry_bar = 0; invest_amount = 0.0; entry_px = 0.0; _er = ""
    nav = np.zeros(n); trades = []; exposure = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; entry_px = fp; entry_bar = i
                total_nav = cash  # bq should be 0 here
                invest_amount = total_nav * f
                bq = invest_amount / (fp * (1 + cps))
                cash = total_nav - bq * fp * (1 + cps)
                inp = True; pk = p
            elif px:
                px = False; rcv = bq * fp * (1 - cps)
                cash += rcv
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                               "entry_px": entry_px, "exit_px": fp, "peak_px": pk,
                               "pnl_usd": rcv - invest_amount,
                               "ret_pct": (rcv / invest_amount - 1) * 100 if invest_amount > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _er})
                bq = 0.0; inp = False; pk = 0.0
        nav[i] = cash + bq * p
        if nav[i] > 0: exposure[i] = bq * p / nav[i]
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
        cash += rcv
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                       "entry_px": entry_px, "exit_px": cl[-1], "peak_px": pk,
                       "pnl_usd": rcv - invest_amount,
                       "ret_pct": (rcv / invest_amount - 1) * 100 if invest_amount > 0 else 0.0,
                       "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data"})
        bq = 0.0; nav[-1] = cash
    return nav, trades, exposure


def _sim_partial(cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
                 model_w, model_mu, model_std, keep_frac_fn):
    """Generalized partial exit sim.

    keep_frac_fn(score) -> float in [0, 1]
    When trail fires: compute score, keep_frac = fn(score).
    If keep_frac < 0.01: full exit. Else: partial exit.
    Trend exit: always full exit.
    """
    n = len(cl); cash = CASH; bq = 0.0; inp = False; pe = px = False
    pk = 0.0; entry_bar = 0; entry_cost = 0.0; entry_px = 0.0; _er = ""
    nav = np.zeros(n); exposure = np.zeros(n)
    trades = []; n_partial = 0

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
                total_rcv = cash + rcv  # include partial exit cash
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                               "entry_px": entry_px, "exit_px": fp, "peak_px": pk,
                               "pnl_usd": total_rcv - entry_cost,
                               "ret_pct": (total_rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                               "bars_held": i - entry_bar, "exit_reason": _er})
                cash = total_rcv; bq = 0.0; inp = False; pk = 0.0

        nav[i] = cash + bq * p
        if nav[i] > 0: exposure[i] = bq * p / nav[i]
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]): continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                feat = _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4)
                score = _predict_score_single(feat, model_w, model_mu, model_std)
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

    avg_exp = float(np.mean(exposure[wi:])) if wi < n else 0.0
    return nav, trades, n_partial, avg_exp, exposure


# =========================================================================
# KEEP-FRACTION FUNCTIONS
# =========================================================================

def make_discrete_fn(thresh, partial_frac):
    def fn(score):
        return partial_frac if score > thresh else 0.0
    return fn


def make_b1_fn():
    """B1: Linear map — keep_frac = clip(score, 0, 1)."""
    def fn(score):
        return max(0.0, min(1.0, score))
    return fn


def make_b2_fn(lo_thresh, hi_thresh, max_frac):
    """B2: Threshold + continuous — linear interp between lo/hi thresh."""
    def fn(score):
        if score <= lo_thresh: return 0.0
        if score >= hi_thresh: return max_frac
        return max_frac * (score - lo_thresh) / (hi_thresh - lo_thresh)
    return fn


def make_b3_fn(all_scores_sorted, max_frac):
    """B3: Rank-based — keep_frac = percentile_rank(score) * max_frac."""
    def fn(score):
        rank = float(np.searchsorted(all_scores_sorted, score, side='right')) / len(all_scores_sorted)
        return rank * max_frac
    return fn


# =========================================================================
# DRAWDOWN EPISODE FINDER
# =========================================================================

def _find_dd_episodes(nav, wi, n_episodes=5):
    """Find top N non-overlapping drawdown episodes."""
    navs = nav[wi:]
    pk = np.maximum.accumulate(navs)
    dd = 1.0 - navs / pk
    episodes = []
    used = np.zeros(len(dd), dtype=bool)

    for _ in range(n_episodes):
        dd_m = dd.copy(); dd_m[used] = 0.0
        trough = int(np.argmax(dd_m))
        if dd_m[trough] < 0.01: break
        # Trace back to start (dd near 0)
        start = trough
        while start > 0 and dd[start - 1] > 0.001: start -= 1
        # Trace forward to recovery
        end = trough
        while end < len(dd) - 1 and dd[end + 1] > 0.001: end += 1
        episodes.append({
            "start": start + wi, "trough": trough + wi, "end": end + wi,
            "dd_pct": float(dd[trough]) * 100,
        })
        used[start:end + 1] = True

    return episodes


# =========================================================================
# UTILITIES
# =========================================================================

def _save_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    print("=" * 70)
    print("X30 PHASE 2: ACTUATOR DESIGN")
    print("=" * 70)

    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    # --- Check Phase 1 verdict ---
    sig_path = TABLES / "signal_summary.json"
    with open(sig_path) as f:
        sig = json.load(f)
    verdict_p1 = sig.get("verdict", "STOP")
    print(f"  Phase 1 verdict: {verdict_p1}")
    if verdict_p1 == "STOP":
        print("  Signal not viable → STOP. No actuator design needed.")
        return

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

    n = len(cl); wi = 0
    if feed.report_start_ms:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms: wi = j; break
    print(f"  H4: {n}, D1: {len(d1_cl)}, warmup: {wi}")

    # --- Indicators ---
    print("Computing indicators...")
    ef = _ema(cl, max(5, SLOW // 4)); es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb); at = _robust_atr(hi, lo, cl)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    # --- Train churn model (50 bps, same protocol) ---
    print("Training churn model (50 bps)...")
    cps_50 = SCENARIOS["harsh"].per_side_bps / 10_000.0
    nav_50, trades_50, _ = _sim_base(cl, ef, es, vd, at, regime_h4, wi, cps_50)
    model_w, model_mu, model_std, best_c, n_train = _train_model(
        trades_50, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    print(f"  Model: C={best_c}, n_train={n_train}")

    # --- Score distribution (for X18 threshold & B2/B3) ---
    scores_all = []
    for t in trades_50:
        if t["exit_reason"] != "trail_stop": continue
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n or math.isnan(at[sb]) or math.isnan(ef[sb]): continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        scores_all.append(_predict_score_single(feat, model_w, model_mu, model_std))
    scores_all = np.array(scores_all)
    x18_thresh = float(np.percentile(scores_all, 100 - X18_ALPHA))
    score_p25 = float(np.percentile(scores_all, 25))
    score_p75 = float(np.percentile(scores_all, 75))
    scores_sorted = np.sort(scores_all)
    print(f"  X18 threshold (P60): {x18_thresh:.3f}")
    print(f"  Score P25={score_p25:.3f}, P75={score_p75:.3f}")

    # --- Precompute base results for all costs ---
    print("\nPrecomputing base results for 9 cost levels...")
    base_results = {}
    for cbps in COST_BPS:
        cps = cbps / 20_000.0
        nav_b, tr_b, exp_b = _sim_base(cl, ef, es, vd, at, regime_h4, wi, cps)
        m = _metrics(nav_b, wi, len(tr_b))
        base_results[cbps] = {"metrics": m, "nav": nav_b, "exposure": exp_b}

    # ==================================================================
    # PART A: PARTIAL FRACTION SWEEP
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART A: PARTIAL FRACTION SWEEP (11 × 9 = 99 backtests)")
    print("=" * 70)

    sweep_rows = []
    # For Gate A evaluation at 25 bps
    sharpe_at_25 = {}

    for pf in PARTIAL_FRACS:
        kf_fn = make_discrete_fn(x18_thresh, pf)
        for cbps in COST_BPS:
            cps = cbps / 20_000.0
            nav_p, tr_p, n_part, avg_exp, _ = _sim_partial(
                cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
                model_w, model_mu, model_std, kf_fn)
            m = _metrics(nav_p, wi, len(tr_p))
            sweep_rows.append({
                "partial_frac": pf, "cost_bps": cbps,
                "sharpe": round(m["sharpe"], 4), "cagr": round(m["cagr"], 2),
                "mdd": round(m["mdd"], 2), "calmar": round(m["calmar"], 4),
                "trades": m["trades"], "n_partial_exits": n_part,
                "avg_exposure": round(avg_exp, 4),
            })
            if cbps == 25:
                sharpe_at_25[pf] = m["sharpe"]

        print(f"  pf={pf:.2f}: Sharpe@25={sharpe_at_25[pf]:.4f}, "
              f"dSh={sharpe_at_25[pf] - base_results[25]['metrics']['sharpe']:+.4f}")

    _save_csv(TABLES / "Tbl_partial_sweep.csv", sweep_rows,
              ["partial_frac", "cost_bps", "sharpe", "cagr", "mdd", "calmar",
               "trades", "n_partial_exits", "avg_exposure"])

    # --- Gate A evaluation ---
    base_sh_25 = base_results[25]["metrics"]["sharpe"]
    beats_25 = [pf for pf in PARTIAL_FRACS if sharpe_at_25.get(pf, 0) > base_sh_25]

    # (a) >=3 consecutive beats
    max_consec = 0; cur_consec = 0
    for pf in PARTIAL_FRACS:
        if pf in beats_25: cur_consec += 1; max_consec = max(max_consec, cur_consec)
        else: cur_consec = 0
    gate_a_plateau = max_consec >= 3

    # (b) Best dSh > 0.03
    best_pf = max(PARTIAL_FRACS, key=lambda pf: sharpe_at_25.get(pf, 0))
    best_dsh = sharpe_at_25[best_pf] - base_sh_25
    gate_a_effect = best_dsh > 0.03

    # (c) Best pf wins >=7/9 costs
    n_cost_wins = 0
    for cbps in COST_BPS:
        base_sh = base_results[cbps]["metrics"]["sharpe"]
        # Find Sharpe for best_pf at this cost
        for r in sweep_rows:
            if r["partial_frac"] == best_pf and r["cost_bps"] == cbps:
                if r["sharpe"] > base_sh: n_cost_wins += 1
                break
    gate_a_robust = n_cost_wins >= 7

    gate_a = gate_a_plateau and gate_a_effect and gate_a_robust

    print(f"\n  Base Sharpe @25bps: {base_sh_25:.4f}")
    print(f"  Best discrete: pf={best_pf:.2f}, Sharpe={sharpe_at_25[best_pf]:.4f}, "
          f"dSh={best_dsh:+.4f}")
    print(f"  Beats Base @25bps: {sorted(beats_25)}")
    print(f"  (a) Consecutive plateau: {max_consec} ({'PASS' if gate_a_plateau else 'FAIL'} >=3)")
    print(f"  (b) Effect size: dSh={best_dsh:+.4f} ({'PASS' if gate_a_effect else 'FAIL'} >0.03)")
    print(f"  (c) Cost robustness: {n_cost_wins}/9 ({'PASS' if gate_a_robust else 'FAIL'} >=7)")
    print(f"  GATE A: {'PASS' if gate_a else 'FAIL'}")

    if not gate_a:
        print("\n  Gate A FAIL → no robust plateau. Writing STOP_FRAGILE.")
        summary = {"gate_A": False, "gate_B": False, "verdict": "STOP_FRAGILE",
                    "best_discrete_frac": best_pf, "best_discrete_sharpe_25": round(sharpe_at_25[best_pf], 4),
                    "best_dsh": round(best_dsh, 4), "plateau_len": max_consec,
                    "cost_wins": n_cost_wins}
        with open(TABLES / "actuator_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        _plot_sweep_heatmaps(sweep_rows, base_results)
        print(f"\nTotal time: {time.time() - t0:.1f}s")
        return

    # ==================================================================
    # PART B: CONTINUOUS SIZING (9 designs × 9 costs = 81 backtests)
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART B: CONTINUOUS SIZING (9 × 9 = 81 backtests)")
    print("=" * 70)

    cont_rows = []
    cont_sharpe_25 = {}  # {design_name: sharpe}

    designs = []
    # B1: Linear
    designs.append(("B1", "linear", make_b1_fn(), {}))
    # B2: Threshold + continuous
    for mf in B2_MAX_FRACS:
        name = f"B2_mf{int(mf*100)}"
        designs.append((name, "B2", make_b2_fn(score_p25, score_p75, mf),
                        {"lo": score_p25, "hi": score_p75, "max_frac": mf}))
    # B3: Rank-based
    for mf in B3_MAX_FRACS:
        name = f"B3_mf{int(mf*100)}"
        designs.append((name, "B3", make_b3_fn(scores_sorted, mf),
                        {"max_frac": mf}))

    for dname, dtype, kf_fn, params in designs:
        for cbps in COST_BPS:
            cps = cbps / 20_000.0
            nav_c, tr_c, n_part, avg_exp, _ = _sim_partial(
                cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
                model_w, model_mu, model_std, kf_fn)
            m = _metrics(nav_c, wi, len(tr_c))
            cont_rows.append({
                "design": dname, "param": json.dumps(params),
                "cost_bps": cbps,
                "sharpe": round(m["sharpe"], 4), "cagr": round(m["cagr"], 2),
                "mdd": round(m["mdd"], 2), "calmar": round(m["calmar"], 4),
                "trades": m["trades"],
            })
            if cbps == 25:
                cont_sharpe_25[dname] = m["sharpe"]

        print(f"  {dname:12s}: Sharpe@25={cont_sharpe_25[dname]:.4f}, "
              f"dSh={cont_sharpe_25[dname] - base_sh_25:+.4f}")

    _save_csv(TABLES / "Tbl_continuous_sizing.csv", cont_rows,
              ["design", "param", "cost_bps", "sharpe", "cagr", "mdd", "calmar", "trades"])

    # --- Gate B: best continuous > best discrete @25bps ---
    best_cont_name = max(cont_sharpe_25, key=cont_sharpe_25.get)
    best_cont_sh = cont_sharpe_25[best_cont_name]
    best_disc_sh = sharpe_at_25[best_pf]
    gate_b = best_cont_sh > best_disc_sh

    print(f"\n  Best discrete: pf={best_pf:.2f}, Sharpe={best_disc_sh:.4f}")
    print(f"  Best continuous: {best_cont_name}, Sharpe={best_cont_sh:.4f}")
    print(f"  GATE B: {'PASS' if gate_b else 'FAIL'} "
          f"(continuous {'>' if gate_b else '<='} discrete)")

    # Select overall best actuator
    if gate_b:
        overall_best_name = best_cont_name
        overall_best_sh = best_cont_sh
        overall_best_type = "continuous"
        # Find the design for running the sim
        for dname, dtype, kf_fn, params in designs:
            if dname == best_cont_name:
                best_kf_fn = kf_fn
                break
    else:
        overall_best_name = f"discrete_pf{int(best_pf*100)}"
        overall_best_sh = best_disc_sh
        overall_best_type = "discrete"
        best_kf_fn = make_discrete_fn(x18_thresh, best_pf)

    print(f"\n  Overall best: {overall_best_name} ({overall_best_type}), "
          f"Sharpe@25={overall_best_sh:.4f}")

    # ==================================================================
    # PART C: MDD MECHANISM ANALYSIS
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART C: MDD MECHANISM ANALYSIS")
    print("=" * 70)

    cps_25 = 25 / 20_000.0

    # Run best actuator at 25 bps
    nav_best, tr_best, n_part_best, avg_exp_best, exp_best = _sim_partial(
        cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps_25,
        model_w, model_mu, model_std, best_kf_fn)
    m_best = _metrics(nav_best, wi, len(tr_best))

    # Base at 25 bps (already computed)
    nav_base_25 = base_results[25]["nav"]
    exp_base_25 = base_results[25]["exposure"]
    m_base_25 = base_results[25]["metrics"]

    # Base(f=0.30) and Base(f=0.20) at 25 bps
    nav_f30, tr_f30, exp_f30 = _sim_base_frac(cl, ef, es, vd, at, regime_h4, wi, cps_25, 0.30)
    m_f30 = _metrics(nav_f30, wi, len(tr_f30))
    nav_f20, tr_f20, exp_f20 = _sim_base_frac(cl, ef, es, vd, at, regime_h4, wi, cps_25, 0.20)
    m_f20 = _metrics(nav_f20, wi, len(tr_f20))

    # Exposure-matched benchmark
    avg_exp_base_25 = float(np.mean(exp_base_25[wi:]))
    f_matched = avg_exp_best  # match X18(partial) avg exposure
    nav_fmatch, tr_fmatch, exp_fmatch = _sim_base_frac(
        cl, ef, es, vd, at, regime_h4, wi, cps_25, f_matched)
    m_fmatch = _metrics(nav_fmatch, wi, len(tr_fmatch))

    print(f"\n  --- 3-Column Comparison @25bps ---")
    print(f"  {'Config':25s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Calmar':>8s} {'AvgExp':>8s}")
    for label, m, avg_e in [
        ("Base (f=1.00)", m_base_25, avg_exp_base_25),
        ("Base (f=0.30)", m_f30, float(np.mean(exp_f30[wi:]))),
        ("Base (f=0.20)", m_f20, float(np.mean(exp_f20[wi:]))),
        (f"Base (f={f_matched:.2f}) matched", m_fmatch, float(np.mean(exp_fmatch[wi:]))),
        (f"{overall_best_name}", m_best, avg_exp_best),
    ]:
        print(f"  {label:25s} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} "
              f"{m['calmar']:8.4f} {avg_e:8.3f}")

    # --- Top 5 Drawdown Episodes ---
    episodes = _find_dd_episodes(nav_base_25, wi, 5)
    decomp_rows = []

    print(f"\n  --- Top {len(episodes)} Drawdown Episodes ---")
    total_dd_base = 0.0
    total_exp_comp = 0.0
    total_timing_comp = 0.0

    for ep_idx, ep in enumerate(episodes):
        si, ti, ei = ep["start"], ep["trough"], ep["end"]
        # Base DD in episode
        base_navs_ep = nav_base_25[si:ei + 1]
        base_pk_ep = np.maximum.accumulate(base_navs_ep)
        base_dd_ep = float(np.max(1 - base_navs_ep / base_pk_ep)) * 100

        # Best actuator DD in same window
        best_navs_ep = nav_best[si:ei + 1]
        best_pk_ep = np.maximum.accumulate(best_navs_ep)
        best_dd_ep = float(np.max(1 - best_navs_ep / best_pk_ep)) * 100

        delta_dd = best_dd_ep - base_dd_ep

        # Average exposure in episode
        base_avg_exp_ep = float(np.mean(exp_base_25[si:ei + 1]))
        best_avg_exp_ep = float(np.mean(exp_best[si:ei + 1]))

        # Decomposition
        if base_avg_exp_ep > 0.01:
            exp_component = base_dd_ep * (best_avg_exp_ep / base_avg_exp_ep - 1)
        else:
            exp_component = 0.0
        timing_component = delta_dd - exp_component

        # Count partial exits in episode
        n_partials_ep = sum(1 for t in tr_best
                           if t.get("exit_reason", "").startswith("trail_stop") and
                           si <= t["exit_bar"] <= ei)

        total_dd_base += base_dd_ep
        total_exp_comp += exp_component
        total_timing_comp += timing_component

        decomp_rows.append({
            "episode": ep_idx + 1,
            "base_dd": round(base_dd_ep, 2),
            "partial_dd": round(best_dd_ep, 2),
            "delta_dd": round(delta_dd, 2),
            "exposure_component": round(exp_component, 2),
            "timing_component": round(timing_component, 2),
            "n_partials": n_partials_ep,
        })

        print(f"  Ep{ep_idx+1}: base_dd={base_dd_ep:.1f}%, partial_dd={best_dd_ep:.1f}%, "
              f"Δ={delta_dd:+.1f}pp (exp={exp_component:+.1f}, timing={timing_component:+.1f}), "
              f"n_partial={n_partials_ep}")

    _save_csv(TABLES / "Tbl_mdd_decomposition.csv", decomp_rows,
              ["episode", "base_dd", "partial_dd", "delta_dd",
               "exposure_component", "timing_component", "n_partials"])

    # Summary attribution
    total_delta = total_exp_comp + total_timing_comp
    if abs(total_delta) > 0.01:
        pct_exposure = total_exp_comp / total_delta * 100
        pct_timing = total_timing_comp / total_delta * 100
    else:
        pct_exposure = 50.0; pct_timing = 50.0

    print(f"\n  MDD Attribution (across {len(episodes)} episodes):")
    print(f"    Exposure component: {pct_exposure:.1f}%")
    print(f"    Timing component:   {pct_timing:.1f}%")

    # Exposure-matched verdict
    if m_best["sharpe"] > m_fmatch["sharpe"] and m_best["mdd"] < m_fmatch["mdd"]:
        mdd_verdict = "TIMING_ALPHA (beats exposure-matched on both Sharpe and MDD)"
    elif m_best["sharpe"] > m_fmatch["sharpe"]:
        mdd_verdict = "PARTIAL_TIMING (better Sharpe, worse MDD than exposure-matched)"
    elif m_best["mdd"] < m_fmatch["mdd"]:
        mdd_verdict = "PARTIAL_TIMING (better MDD, worse Sharpe than exposure-matched)"
    else:
        mdd_verdict = "EXPOSURE_ONLY (exposure-matched beats on both metrics)"
    print(f"  Mechanism verdict: {mdd_verdict}")

    # ==================================================================
    # PART D: COST INTERACTION ANALYSIS
    # ==================================================================
    print("\n" + "=" * 70)
    print("PART D: COST INTERACTION ANALYSIS")
    print("=" * 70)

    cost_rows = []
    delta_shs = []
    delta_mdds = []

    for cbps in COST_BPS:
        cps = cbps / 20_000.0
        nav_d, tr_d, _, _, _ = _sim_partial(
            cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, wi, cps,
            model_w, model_mu, model_std, best_kf_fn)
        m_d = _metrics(nav_d, wi, len(tr_d))
        m_b = base_results[cbps]["metrics"]

        dsh = m_d["sharpe"] - m_b["sharpe"]
        dmdd = m_d["mdd"] - m_b["mdd"]
        dcalmar = m_d["calmar"] - m_b["calmar"]

        cost_rows.append({
            "cost_bps": cbps,
            "base_sharpe": round(m_b["sharpe"], 4),
            "best_sharpe": round(m_d["sharpe"], 4),
            "delta_sh": round(dsh, 4),
            "base_mdd": round(m_b["mdd"], 2),
            "best_mdd": round(m_d["mdd"], 2),
            "delta_mdd": round(dmdd, 2),
        })
        delta_shs.append(dsh)
        delta_mdds.append(dmdd)

        print(f"  {cbps:3d} bps: base_sh={m_b['sharpe']:.4f}, best_sh={m_d['sharpe']:.4f}, "
              f"dSh={dsh:+.4f}, dMDD={dmdd:+.1f}pp")

    _save_csv(TABLES / "Tbl_cost_interaction.csv", cost_rows,
              ["cost_bps", "base_sharpe", "best_sharpe", "delta_sh",
               "base_mdd", "best_mdd", "delta_mdd"])

    # Cost interaction trend
    dsh_arr = np.array(delta_shs)
    corr_cost_dsh = float(np.corrcoef(COST_BPS, dsh_arr)[0, 1])
    if corr_cost_dsh > 0.5:
        cost_trend = "increasing"
    elif corr_cost_dsh < -0.5:
        cost_trend = "decreasing"
    else:
        cost_trend = "flat"

    # Crossover
    crossover_bps = None
    for i, cbps in enumerate(COST_BPS):
        if delta_shs[i] <= 0:
            crossover_bps = cbps
            break

    print(f"\n  Cost-dSh correlation: {corr_cost_dsh:.3f} → {cost_trend}")
    if crossover_bps:
        print(f"  Crossover (dSh<=0) at: {crossover_bps} bps")
    else:
        print(f"  No crossover: actuator wins at ALL cost levels")

    # ==================================================================
    # FIGURES
    # ==================================================================
    print("\nGenerating figures...")
    _plot_sweep_heatmaps(sweep_rows, base_results)
    _plot_continuous_compare(cont_sharpe_25, base_sh_25, best_disc_sh)
    _plot_mdd_decomposition(decomp_rows)
    _plot_cost_interaction(cost_rows)

    # ==================================================================
    # SUMMARY JSON
    # ==================================================================
    # Candidates for WFO: top 2-3 configs
    candidates = []
    # Best discrete
    candidates.append({
        "name": f"discrete_pf{int(best_pf*100)}", "type": "discrete",
        "partial_frac": best_pf, "design": None,
        "params": {"threshold": round(x18_thresh, 4)},
    })
    # Best continuous
    for dname, dtype, kf_fn, params in designs:
        if dname == best_cont_name:
            candidates.append({
                "name": best_cont_name, "type": "continuous",
                "partial_frac": None, "design": dtype,
                "params": params,
            })
            break
    # Second-best continuous (if different from best)
    sorted_cont = sorted(cont_sharpe_25.items(), key=lambda x: -x[1])
    if len(sorted_cont) >= 2 and sorted_cont[1][0] != best_cont_name:
        sec_name = sorted_cont[1][0]
        for dname, dtype, kf_fn, params in designs:
            if dname == sec_name:
                candidates.append({
                    "name": sec_name, "type": "continuous",
                    "partial_frac": None, "design": dtype,
                    "params": params,
                })
                break

    summary = {
        "best_discrete_frac": float(best_pf),
        "best_discrete_sharpe_25": round(float(best_disc_sh), 4),
        "best_continuous_design": best_cont_name,
        "best_continuous_sharpe_25": round(float(best_cont_sh), 4),
        "continuous_beats_discrete": bool(gate_b),
        "mdd_from_exposure_pct": round(float(pct_exposure), 1),
        "mdd_from_timing_pct": round(float(pct_timing), 1),
        "mdd_mechanism": mdd_verdict,
        "cost_interaction": cost_trend,
        "cost_dsh_corr": round(float(corr_cost_dsh), 3),
        "crossover_bps": int(crossover_bps) if crossover_bps is not None else None,
        "candidates_for_wfo": candidates,
        "gate_A": bool(gate_a),
        "gate_B": bool(gate_b),
        "overall_best": overall_best_name,
        "overall_best_type": overall_best_type,
        "overall_best_sharpe_25": round(float(overall_best_sh), 4),
        "base_sharpe_25": round(float(base_sh_25), 4),
    }

    with open(TABLES / "actuator_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # ==================================================================
    # FINAL VERDICT
    # ==================================================================
    print(f"\n{'=' * 70}")
    print(f"PHASE 2 COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Gate A (discrete plateau): {'PASS' if gate_a else 'FAIL'}")
    print(f"  Gate B (continuous > discrete): {'PASS' if gate_b else 'FAIL'}")
    print(f"  Overall best: {overall_best_name} ({overall_best_type})")
    print(f"  Sharpe@25: {overall_best_sh:.4f} (base: {base_sh_25:.4f}, "
          f"dSh={overall_best_sh - base_sh_25:+.4f})")
    print(f"  MDD mechanism: {mdd_verdict}")
    print(f"  Cost trend: {cost_trend}")
    print(f"  Candidates for WFO: {[c['name'] for c in candidates]}")
    print(f"{'=' * 70}")
    print(f"\nTotal time: {time.time() - t0:.1f}s")


# =========================================================================
# FIGURES
# =========================================================================

def _plot_sweep_heatmaps(sweep_rows, base_results):
    """Heatmap: partial_frac × cost → Sharpe and MDD."""
    pfs = sorted(set(r["partial_frac"] for r in sweep_rows))
    costs = sorted(set(r["cost_bps"] for r in sweep_rows))
    nc, np_ = len(costs), len(pfs)

    # Build matrices
    sh_mat = np.zeros((np_, nc))
    mdd_mat = np.zeros((np_, nc))
    for r in sweep_rows:
        pi = pfs.index(r["partial_frac"])
        ci = costs.index(r["cost_bps"])
        sh_mat[pi, ci] = r["sharpe"]
        mdd_mat[pi, ci] = r["mdd"]

    # Delta from base
    dsh_mat = np.zeros_like(sh_mat)
    dmdd_mat = np.zeros_like(mdd_mat)
    for ci, cbps in enumerate(costs):
        bsh = base_results[cbps]["metrics"]["sharpe"]
        bmdd = base_results[cbps]["metrics"]["mdd"]
        dsh_mat[:, ci] = sh_mat[:, ci] - bsh
        dmdd_mat[:, ci] = mdd_mat[:, ci] - bmdd

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    im1 = ax1.imshow(dsh_mat, aspect='auto', cmap='RdYlGn',
                     vmin=-0.15, vmax=0.15, origin='lower')
    ax1.set_xticks(range(nc)); ax1.set_xticklabels(costs)
    ax1.set_yticks(range(np_)); ax1.set_yticklabels([f"{p:.1f}" for p in pfs])
    ax1.set_xlabel("Cost (bps)"); ax1.set_ylabel("Partial Fraction")
    ax1.set_title("ΔSharpe vs Base", fontweight='bold')
    plt.colorbar(im1, ax=ax1, label="ΔSharpe")

    im2 = ax2.imshow(dmdd_mat, aspect='auto', cmap='RdYlGn_r',
                     vmin=-15, vmax=5, origin='lower')
    ax2.set_xticks(range(nc)); ax2.set_xticklabels(costs)
    ax2.set_yticks(range(np_)); ax2.set_yticklabels([f"{p:.1f}" for p in pfs])
    ax2.set_xlabel("Cost (bps)"); ax2.set_ylabel("Partial Fraction")
    ax2.set_title("ΔMDD vs Base (pp)", fontweight='bold')
    plt.colorbar(im2, ax=ax2, label="ΔMDD (pp)")

    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_partial_sweep.png", dpi=150)
    plt.close()

    # Separate MDD figure
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(mdd_mat, aspect='auto', cmap='YlOrRd', origin='lower')
    ax.set_xticks(range(nc)); ax.set_xticklabels(costs)
    ax.set_yticks(range(np_)); ax.set_yticklabels([f"{p:.1f}" for p in pfs])
    ax.set_xlabel("Cost (bps)"); ax.set_ylabel("Partial Fraction")
    ax.set_title("MDD (%) — Partial Fraction Sweep", fontweight='bold')
    plt.colorbar(im, ax=ax, label="MDD (%)")
    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_partial_sweep_mdd.png", dpi=150)
    plt.close()


def _plot_continuous_compare(cont_sharpe_25, base_sh, best_disc_sh):
    """Bar chart: designs at 25 bps."""
    fig, ax = plt.subplots(figsize=(10, 5))
    names = sorted(cont_sharpe_25.keys())
    shs = [cont_sharpe_25[n] for n in names]

    colors = ['#4caf50' if s > base_sh else '#d32f2f' for s in shs]
    bars = ax.bar(range(len(names)), shs, color=colors, alpha=0.8, edgecolor='black')
    ax.axhline(base_sh, color='blue', linewidth=2, linestyle='--', label=f'Base ({base_sh:.4f})')
    ax.axhline(best_disc_sh, color='orange', linewidth=2, linestyle=':',
               label=f'Best Discrete ({best_disc_sh:.4f})')
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.set_ylabel("Sharpe @25bps")
    ax.set_title("Part B: Continuous Designs vs Base & Discrete @25bps", fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_continuous_compare.png", dpi=150)
    plt.close()


def _plot_mdd_decomposition(decomp_rows):
    """Stacked bar: exposure vs timing per episode."""
    fig, ax = plt.subplots(figsize=(8, 5))
    eps = [r["episode"] for r in decomp_rows]
    exp_comp = [r["exposure_component"] for r in decomp_rows]
    tim_comp = [r["timing_component"] for r in decomp_rows]

    ax.bar(eps, exp_comp, label='Exposure', color='#ff9800', alpha=0.8, edgecolor='black')
    ax.bar(eps, tim_comp, bottom=exp_comp, label='Timing', color='#1976d2',
           alpha=0.8, edgecolor='black')
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.set_xlabel("Drawdown Episode"); ax.set_ylabel("ΔDD (pp)")
    ax.set_title("Part C: MDD Decomposition — Exposure vs Timing", fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_mdd_decomposition.png", dpi=150)
    plt.close()


def _plot_cost_interaction(cost_rows):
    """Line plot: ΔSh, ΔMDD vs cost."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    costs = [r["cost_bps"] for r in cost_rows]
    dshs = [r["delta_sh"] for r in cost_rows]
    dmdds = [r["delta_mdd"] for r in cost_rows]

    ax1.plot(costs, dshs, 'o-', color='#1976d2', linewidth=2, markersize=8)
    ax1.axhline(0, color='gray', linewidth=0.5, linestyle='--')
    ax1.set_xlabel("Cost (bps RT)"); ax1.set_ylabel("ΔSharpe")
    ax1.set_title("ΔSharpe vs Cost", fontweight='bold')

    ax2.plot(costs, dmdds, 's-', color='#d32f2f', linewidth=2, markersize=8)
    ax2.axhline(0, color='gray', linewidth=0.5, linestyle='--')
    ax2.set_xlabel("Cost (bps RT)"); ax2.set_ylabel("ΔMDD (pp)")
    ax2.set_title("ΔMDD vs Cost", fontweight='bold')

    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_cost_interaction.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    main()
