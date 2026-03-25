#!/usr/bin/env python3
"""X30 Phase 1: Signal Anatomy — OOS Validation of Churn Score

Null hypothesis (H0): Churn score has NO predictive power out of sample.
Monotonic Q1→Q4 is an artifact of in-sample overfitting.

5 analyses:
  A: Temporal stability (3 sub-periods, in-sample within each)
  B: Out-of-sample signal quality (train P1+P2, test P3)
  C: Feature importance (permutation + leave-one-out)
  D: Calibration (predicted vs actual churn rates)
  E: Score distribution (KDE, bimodality, threshold analysis)

Gate A: >=2/3 periods monotonic (both avg_ret and WR), P3 must not break
Gate B: OOS AUC > 0.65 AND P3 quartiles monotonic
Verdict: PROCEED if both gates pass, STOP otherwise
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
from scipy.stats import spearmanr, gaussian_kde

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

# =========================================================================
# CONSTANTS (frozen from E5+EMA1D21)
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
CPS_50 = SCENARIOS["harsh"].per_side_bps / 10_000.0

PERIODS = [
    ("P1", "2019-01-01", "2021-06-30"),
    ("P2", "2021-07-01", "2023-06-30"),
    ("P3", "2023-07-01", "2026-02-20"),
]

FEATURE_NAMES = [
    "ema_ratio", "atr_pctl", "bar_range_atr",
    "close_position", "vdo", "d1_regime_str", "trail_tightness",
]

N_PERM_REPS = 30  # permutation importance repetitions

OUTDIR = Path(__file__).resolve().parents[1]
TABLES = OUTDIR / "tables"
FIGURES = OUTDIR / "figures"


# =========================================================================
# INDICATORS (from x29)
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
# SIMULATION (E5+EMA1D21 base)
# =========================================================================

def _sim_base(cl, ef, es, vd, at, regime_h4, wi, cps):
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
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp, "peak_px": pk,
                    "pnl_usd": rcv - entry_cost,
                    "ret_pct": (rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                    "bars_held": i - entry_bar, "exit_reason": _er,
                })
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
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1], "peak_px": pk,
            "pnl_usd": rcv - entry_cost,
            "ret_pct": (rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
        })
        nav[-1] = rcv
    return nav, trades


# =========================================================================
# CHURN MODEL (7 features, L2 logistic — from x29)
# =========================================================================

def _extract_features_7(i, cl, hi, lo, at, ef, es, vd, d1_str_h4):
    """Extract 7 features at bar i for churn prediction."""
    f1 = ef[i] / es[i] if abs(es[i]) > 1e-12 else 1.0
    s = max(0, i - 99); w = at[s:i + 1]; v = w[~np.isnan(w)]
    f2 = float(np.sum(v <= at[i])) / len(v) if len(v) > 1 else 0.5
    f3 = (hi[i] - lo[i]) / at[i] if at[i] > 1e-12 else 1.0
    bw = hi[i] - lo[i]
    f4 = (cl[i] - lo[i]) / bw if bw > 1e-12 else 0.5
    f5 = float(vd[i]); f6 = float(d1_str_h4[i])
    f7 = TRAIL * at[i] / cl[i] if cl[i] > 1e-12 else 0.0
    return np.array([f1, f2, f3, f4, f5, f6, f7])


def _fit_logistic_l2(X, y, C=1.0, max_iter=100):
    """L2-regularized logistic regression via Newton-Raphson."""
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
    """K-fold cross-validated AUC. X must be pre-standardized."""
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


def _predict_scores(X, w, mu, std):
    """Score array of raw features → P(churn) per row."""
    Xs = (X - mu) / std
    Xa = np.column_stack([Xs, np.ones(len(Xs))])
    z = Xa @ w
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))


def _roc_auc(y_true, y_score):
    """AUC via concordance (Mann-Whitney U)."""
    pos = y_score[y_true == 1]; neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0: return 0.5
    comp = pos[:, None] > neg[None, :]
    ties = pos[:, None] == neg[None, :]
    return float((np.sum(comp) + 0.5 * np.sum(ties)) / (len(pos) * len(neg)))


def _train_model(X, y):
    """Train L2 logistic with 5-fold CV for C.
    Returns (w, mu, std, best_c, cv_auc) or (None,...,0.0) on failure."""
    if len(y) < 10 or len(np.unique(y)) < 2:
        return None, None, None, None, 0.0
    Xs, mu, std = _standardize(X)
    best_c, best_auc = 1.0, 0.0
    for c in C_VALUES:
        auc = _kfold_auc(Xs, y, C=c, k=5)
        if auc > best_auc: best_auc = auc; best_c = c
    w = _fit_logistic_l2(Xs, y, C=best_c)
    return w, mu, std, best_c, best_auc


# =========================================================================
# UTILITIES
# =========================================================================

def _date_to_bar_idx(h4_ct, date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ts_ms = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    return min(int(np.searchsorted(h4_ct, ts_ms, side='left')), len(h4_ct) - 1)


def _quartile_stats(scores, rets):
    """Split by score quartiles, return list of 4 dicts."""
    n = len(scores)
    if n < 4:
        return [{"quartile": q, "n": 0, "avg_ret": float('nan'),
                 "median_ret": float('nan'), "win_rate": float('nan'),
                 "avg_score": float('nan'), "n_trail_stops": 0}
                for q in range(1, 5)]
    q_edges = np.percentile(scores, [25, 50, 75])
    quartiles = np.digitize(scores, q_edges) + 1  # 1-4
    results = []
    for q in range(1, 5):
        mask = quartiles == q
        n_q = int(np.sum(mask))
        if n_q == 0:
            results.append({"quartile": q, "n": 0, "avg_ret": float('nan'),
                            "median_ret": float('nan'), "win_rate": float('nan'),
                            "avg_score": float('nan'), "n_trail_stops": 0})
            continue
        r = rets[mask]; s = scores[mask]
        results.append({
            "quartile": q, "n": n_q,
            "avg_ret": float(np.mean(r)),
            "median_ret": float(np.median(r)),
            "win_rate": float(np.mean(r > 0)) * 100,
            "avg_score": float(np.mean(s)),
            "n_trail_stops": n_q,
        })
    return results


def _is_monotonic(values):
    """Strictly increasing check. Returns False if any NaN or non-increasing."""
    if len(values) < 2:
        return False
    for v in values:
        if math.isnan(v):
            return False
    for i in range(1, len(values)):
        if values[i] <= values[i - 1]:
            return False
    return True


def _save_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# =========================================================================
# PART A: TEMPORAL STABILITY
# =========================================================================

def part_a(trail_X, trail_y, trail_rets, trail_exit_bars, period_ranges):
    print("\n" + "=" * 70)
    print("PART A: TEMPORAL STABILITY")
    print("=" * 70)

    rows = []
    period_results = {}

    for pname, pstart, pend in period_ranges:
        mask = (trail_exit_bars >= pstart) & (trail_exit_bars <= pend)
        X_p = trail_X[mask]; y_p = trail_y[mask]; r_p = trail_rets[mask]
        n_p = len(y_p); n_churn = int(np.sum(y_p))

        print(f"\n  {pname}: n_trail_stops={n_p}, churn={n_churn}, "
              f"non-churn={n_p - n_churn}")

        if n_p < 20:
            print(f"  WARNING: Too few trail-stops ({n_p})")
            period_results[pname] = {"monotonic_ret": False, "monotonic_wr": False}
            for q in range(1, 5):
                rows.append({"period": pname, "quartile": f"Q{q}", "n_trades": 0,
                             "avg_ret": 0, "median_ret": 0, "win_rate": 0,
                             "n_trail_stops": 0})
            continue

        # Train model within this period (in-sample)
        w, mu, std, best_c, cv_auc = _train_model(X_p, y_p)
        if w is None:
            print(f"  Model training failed")
            period_results[pname] = {"monotonic_ret": False, "monotonic_wr": False}
            for q in range(1, 5):
                rows.append({"period": pname, "quartile": f"Q{q}", "n_trades": 0,
                             "avg_ret": 0, "median_ret": 0, "win_rate": 0,
                             "n_trail_stops": 0})
            continue

        print(f"  Model: C={best_c}, CV AUC={cv_auc:.3f}")

        # Score within period (in-sample)
        scores = _predict_scores(X_p, w, mu, std)
        qstats = _quartile_stats(scores, r_p)

        avg_rets = [q["avg_ret"] for q in qstats]
        win_rates = [q["win_rate"] for q in qstats]
        mono_ret = _is_monotonic(avg_rets)
        mono_wr = _is_monotonic(win_rates)
        period_results[pname] = {"monotonic_ret": mono_ret, "monotonic_wr": mono_wr}

        for q in qstats:
            rows.append({
                "period": pname, "quartile": f"Q{q['quartile']}",
                "n_trades": q["n"],
                "avg_ret": round(q["avg_ret"], 4) if not math.isnan(q["avg_ret"]) else 0,
                "median_ret": round(q["median_ret"], 4) if not math.isnan(q["median_ret"]) else 0,
                "win_rate": round(q["win_rate"], 2) if not math.isnan(q["win_rate"]) else 0,
                "n_trail_stops": q["n_trail_stops"],
            })
            print(f"    Q{q['quartile']}: n={q['n']}, avg_ret={q['avg_ret']:.2f}%, "
                  f"WR={q['win_rate']:.1f}%")

        print(f"  Monotonic avg_ret: {'YES' if mono_ret else 'NO'}")
        print(f"  Monotonic win_rate: {'YES' if mono_wr else 'NO'}")

    # Gate A: >=2/3 monotonic AND P3 must not break
    n_mono = 0
    for pname in ["P1", "P2", "P3"]:
        pr = period_results.get(pname, {})
        if pr.get("monotonic_ret", False) and pr.get("monotonic_wr", False):
            n_mono += 1

    p3_ok = period_results.get("P3", {}).get("monotonic_ret", False) and \
            period_results.get("P3", {}).get("monotonic_wr", False)

    gate_a = n_mono >= 2 and p3_ok

    print(f"\n  Periods monotonic (both ret+WR): {n_mono}/3")
    print(f"  P3 monotonic: {'YES' if p3_ok else 'NO'}")
    print(f"  GATE A: {'PASS' if gate_a else 'FAIL'}")

    _save_csv(TABLES / "Tbl_temporal_stability.csv", rows,
              ["period", "quartile", "n_trades", "avg_ret", "median_ret",
               "win_rate", "n_trail_stops"])

    return gate_a, n_mono, period_results, rows


# =========================================================================
# PART B: OUT-OF-SAMPLE SIGNAL QUALITY
# =========================================================================

def part_b(trail_X, trail_y, trail_rets, trail_exit_bars, period_ranges):
    print("\n" + "=" * 70)
    print("PART B: OUT-OF-SAMPLE SIGNAL QUALITY")
    print("=" * 70)

    # Train on P1+P2, test on P3
    _, p1s, _ = period_ranges[0]
    _, _, p2e = period_ranges[1]
    _, p3s, p3e = period_ranges[2]

    train_mask = (trail_exit_bars >= p1s) & (trail_exit_bars <= p2e)
    test_mask = (trail_exit_bars >= p3s) & (trail_exit_bars <= p3e)

    X_tr, y_tr, r_tr = trail_X[train_mask], trail_y[train_mask], trail_rets[train_mask]
    X_te, y_te, r_te = trail_X[test_mask], trail_y[test_mask], trail_rets[test_mask]

    print(f"  Train (P1+P2): {len(y_tr)} trail-stops, churn={int(np.sum(y_tr))}")
    print(f"  Test  (P3):    {len(y_te)} trail-stops, churn={int(np.sum(y_te))}")

    # Train model on P1+P2
    w_tr, mu_tr, std_tr, best_c, cv_auc_tr = _train_model(X_tr, y_tr)
    if w_tr is None:
        print("  Model training FAILED")
        return False, 0.5, 0.5, 0.0, 1.0, [], []

    print(f"  Model: C={best_c}, train CV AUC={cv_auc_tr:.3f}")

    # Score test data with train model
    scores_te = _predict_scores(X_te, w_tr, mu_tr, std_tr)

    # Full-sample AUC for reference
    X_all = np.vstack([X_tr, X_te])
    y_all = np.concatenate([y_tr, y_te])
    w_full, mu_full, std_full, _, _ = _train_model(X_all, y_all)
    if w_full is not None:
        scores_all = _predict_scores(X_all, w_full, mu_full, std_full)
        auc_full = _roc_auc(y_all, scores_all)
    else:
        auc_full = 0.5

    # OOS AUC
    auc_oos = _roc_auc(y_te, scores_te)

    # Spearman correlation (score vs trade return)
    try:
        sp_corr, sp_pval = spearmanr(scores_te, r_te)
        if math.isnan(sp_corr): sp_corr, sp_pval = 0.0, 1.0
    except Exception:
        sp_corr, sp_pval = 0.0, 1.0

    print(f"  Full-sample AUC (in-sample): {auc_full:.3f}")
    print(f"  OOS AUC (P3):               {auc_oos:.3f}")
    print(f"  Spearman(score, ret):        {sp_corr:.3f} (p={sp_pval:.4f})")

    # Quartile analysis on test data
    qstats = _quartile_stats(scores_te, r_te)
    oos_rows = []
    for q in qstats:
        oos_rows.append({
            "quartile": f"Q{q['quartile']}", "n": q["n"],
            "avg_ret": round(q["avg_ret"], 4) if not math.isnan(q["avg_ret"]) else 0,
            "median_ret": round(q["median_ret"], 4) if not math.isnan(q["median_ret"]) else 0,
            "win_rate": round(q["win_rate"], 2) if not math.isnan(q["win_rate"]) else 0,
            "avg_score": round(q["avg_score"], 4) if not math.isnan(q["avg_score"]) else 0,
        })
        print(f"    Q{q['quartile']}: n={q['n']}, avg_ret={q['avg_ret']:.2f}%, "
              f"WR={q['win_rate']:.1f}%, avg_score={q['avg_score']:.3f}")

    avg_rets = [q["avg_ret"] for q in qstats]
    win_rates = [q["win_rate"] for q in qstats]
    mono_ret = _is_monotonic(avg_rets)
    mono_wr = _is_monotonic(win_rates)
    mono_ok = mono_ret and mono_wr

    gate_b = auc_oos > 0.65 and mono_ok

    print(f"\n  OOS monotonic avg_ret: {'YES' if mono_ret else 'NO'}")
    print(f"  OOS monotonic WR:      {'YES' if mono_wr else 'NO'}")
    print(f"  GATE B: {'PASS' if gate_b else 'FAIL'} "
          f"(AUC={auc_oos:.3f}>0.65={'Y' if auc_oos > 0.65 else 'N'}, "
          f"mono={'Y' if mono_ok else 'N'})")

    _save_csv(TABLES / "Tbl_oos_quartiles.csv", oos_rows,
              ["quartile", "n", "avg_ret", "median_ret", "win_rate", "avg_score"])

    return gate_b, auc_oos, auc_full, sp_corr, sp_pval, qstats, oos_rows


# =========================================================================
# PART C: FEATURE IMPORTANCE
# =========================================================================

def part_c(trail_X, trail_y):
    print("\n" + "=" * 70)
    print("PART C: FEATURE IMPORTANCE")
    print("=" * 70)

    # Train full model
    w, mu, std, best_c, cv_auc = _train_model(trail_X, trail_y)
    if w is None:
        print("  Model training FAILED")
        return [], ""

    # Baseline in-sample AUC
    scores_full = _predict_scores(trail_X, w, mu, std)
    baseline_auc = _roc_auc(trail_y, scores_full)
    print(f"  Baseline in-sample AUC: {baseline_auc:.3f}")
    print(f"  Baseline CV AUC:        {cv_auc:.3f}")

    rows = []
    rng = np.random.default_rng(42)

    for fi, fname in enumerate(FEATURE_NAMES):
        # Permutation importance (average over N_PERM_REPS)
        perm_drops = []
        for _ in range(N_PERM_REPS):
            X_perm = trail_X.copy()
            X_perm[:, fi] = rng.permutation(X_perm[:, fi])
            scores_perm = _predict_scores(X_perm, w, mu, std)
            auc_perm = _roc_auc(trail_y, scores_perm)
            perm_drops.append(baseline_auc - auc_perm)
        perm_imp = float(np.mean(perm_drops))

        # Leave-one-out: retrain without this feature
        X_loo = np.delete(trail_X, fi, axis=1)
        _, _, _, _, loo_cv_auc = _train_model(X_loo, trail_y)
        loo_auc_drop = cv_auc - loo_cv_auc

        rows.append({
            "feature": fname,
            "permutation_imp": round(perm_imp, 4),
            "loo_auc": round(loo_cv_auc, 4),
            "loo_auc_drop": round(loo_auc_drop, 4),
        })
        print(f"  {fname:20s}: perm_imp={perm_imp:+.4f}, "
              f"LOO_AUC={loo_cv_auc:.3f}, drop={loo_auc_drop:+.4f}")

    # Dominant feature
    max_imp = max(rows, key=lambda r: r["permutation_imp"])
    dominant = max_imp["feature"]
    print(f"\n  Dominant feature: {dominant} (perm_imp={max_imp['permutation_imp']:+.4f})")

    # Check if f7 (trail_tightness) dominates
    f7_imp = [r for r in rows if r["feature"] == "trail_tightness"]
    if f7_imp and f7_imp[0]["permutation_imp"] == max_imp["permutation_imp"]:
        print("  WARNING: trail_tightness dominates — signal may be proxy for trail width")

    _save_csv(TABLES / "Tbl_feature_importance.csv", rows,
              ["feature", "permutation_imp", "loo_auc", "loo_auc_drop"])

    return rows, dominant


# =========================================================================
# PART D: CALIBRATION
# =========================================================================

def part_d(trail_X, trail_y):
    print("\n" + "=" * 70)
    print("PART D: CALIBRATION")
    print("=" * 70)

    w, mu, std, _, _ = _train_model(trail_X, trail_y)
    if w is None:
        print("  Model training FAILED")
        return [], 0.0, 0.0

    scores = _predict_scores(trail_X, w, mu, std)

    # Brier score
    brier = float(np.mean((scores - trail_y) ** 2))

    # Calibration bins
    n_bins = 10
    bin_edges = np.linspace(0, 1, n_bins + 1)
    rows = []
    ece = 0.0
    total = len(scores)

    for b in range(n_bins):
        lo_e = bin_edges[b]; hi_e = bin_edges[b + 1]
        if b == n_bins - 1:
            mask = (scores >= lo_e) & (scores <= hi_e)
        else:
            mask = (scores >= lo_e) & (scores < hi_e)
        n_b = int(np.sum(mask))
        if n_b == 0:
            rows.append({"bin": b + 1, "mean_score": round((lo_e + hi_e) / 2, 3),
                         "actual_churn_rate": 0.0, "n_samples": 0})
            continue
        mean_s = float(np.mean(scores[mask]))
        actual_rate = float(np.mean(trail_y[mask]))
        ece += abs(actual_rate - mean_s) * n_b / total
        rows.append({
            "bin": b + 1, "mean_score": round(mean_s, 4),
            "actual_churn_rate": round(actual_rate, 4), "n_samples": n_b,
        })
        print(f"  Bin {b+1:2d}: [{lo_e:.1f},{hi_e:.1f}) n={n_b:3d}, "
              f"mean_score={mean_s:.3f}, actual={actual_rate:.3f}")

    print(f"\n  Brier score: {brier:.4f}")
    print(f"  ECE:         {ece:.4f}")

    well_calibrated = ece < 0.10
    print(f"  Calibration: {'GOOD (ECE<0.10)' if well_calibrated else 'POOR (ECE>=0.10)'}")
    print(f"  → {'Score can be used directly for sizing' if well_calibrated else 'Use rank-based (percentile) instead of raw score'}")

    _save_csv(TABLES / "Tbl_calibration.csv", rows,
              ["bin", "mean_score", "actual_churn_rate", "n_samples"])

    return rows, brier, ece


# =========================================================================
# PART E: SCORE DISTRIBUTION
# =========================================================================

def part_e(trail_X, trail_y):
    print("\n" + "=" * 70)
    print("PART E: SCORE DISTRIBUTION")
    print("=" * 70)

    w, mu, std, _, _ = _train_model(trail_X, trail_y)
    if w is None:
        print("  Model training FAILED")
        return {}, None, None

    scores = _predict_scores(trail_X, w, mu, std)

    # X18 threshold = P60 (suppress top 40%)
    x18_thresh = float(np.percentile(scores, 60))

    # Youden's J statistic
    thresholds = np.linspace(0, 1, 201)
    best_j, best_t = -1.0, 0.5
    for t in thresholds:
        pred_pos = scores >= t
        tp = np.sum(pred_pos & (trail_y == 1))
        fn = np.sum(~pred_pos & (trail_y == 1))
        fp = np.sum(pred_pos & (trail_y == 0))
        tn = np.sum(~pred_pos & (trail_y == 0))
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0
        j = sens + spec - 1
        if j > best_j: best_j = j; best_t = float(t)
    youden_thresh = best_t

    # Mass analysis
    mass_above = float(np.mean(scores > x18_thresh)) * 100

    # Bimodality: count peaks in KDE
    try:
        kde = gaussian_kde(scores, bw_method='silverman')
        x_grid = np.linspace(float(np.min(scores)) - 0.05,
                             float(np.max(scores)) + 0.05, 500)
        y_kde = kde(x_grid)
        peaks = []
        for i in range(1, len(y_kde) - 1):
            if y_kde[i] > y_kde[i - 1] and y_kde[i] > y_kde[i + 1]:
                peaks.append(float(x_grid[i]))
        bimodal = len(peaks) >= 2
    except Exception:
        bimodal = False; peaks = []

    print(f"  Score range: [{np.min(scores):.3f}, {np.max(scores):.3f}]")
    print(f"  Score mean:  {np.mean(scores):.3f}, std: {np.std(scores):.3f}")
    print(f"  X18 threshold (P60):  {x18_thresh:.3f}")
    print(f"  Youden's J threshold: {youden_thresh:.3f} (J={best_j:.3f})")
    print(f"  Mass above X18: {mass_above:.1f}%, below: {100 - mass_above:.1f}%")
    print(f"  KDE peaks: {len(peaks)} → {'BIMODAL' if bimodal else 'UNIMODAL'}")
    if peaks:
        print(f"  Peak locations: {[f'{p:.3f}' for p in peaks]}")

    # Interpretation
    if bimodal:
        print("  → Clear separation: binary suppress OK for extremes")
    else:
        print("  → Overlapping distributions: continuous actuator may capture more info")

    summary = {
        "score_min": round(float(np.min(scores)), 4),
        "score_max": round(float(np.max(scores)), 4),
        "score_mean": round(float(np.mean(scores)), 4),
        "score_std": round(float(np.std(scores)), 4),
        "x18_thresh": round(x18_thresh, 4),
        "youden_thresh": round(youden_thresh, 4),
        "youden_j": round(float(best_j), 4),
        "mass_above_x18_pct": round(mass_above, 2),
        "n_kde_peaks": len(peaks),
        "bimodal": bimodal,
    }

    return summary, scores, trail_y


# =========================================================================
# FIGURES
# =========================================================================

def _plot_temporal_quartiles(rows_a):
    fig, axes = plt.subplots(3, 1, figsize=(8, 10))
    fig.suptitle("Part A: Temporal Stability — Quartile Returns by Period",
                 fontsize=13, fontweight='bold')
    colors = ['#d32f2f', '#ff9800', '#4caf50', '#1976d2']

    for ax_idx, pname in enumerate(["P1", "P2", "P3"]):
        ax = axes[ax_idx]
        prows = [r for r in rows_a if r["period"] == pname]
        if not prows or all(r["n_trades"] == 0 for r in prows):
            ax.set_title(f"{pname}: No data"); continue
        qs = [r["quartile"] for r in prows]
        rets = [r["avg_ret"] for r in prows]
        wrs = [r["win_rate"] for r in prows]
        bars = ax.bar(qs, rets, color=colors, alpha=0.8, edgecolor='black')
        ax.set_title(f"{pname}: avg_ret by churn score quartile")
        ax.set_ylabel("Avg Return (%)")
        ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')
        for b, wr in zip(bars, wrs):
            h = b.get_height()
            va = 'bottom' if h >= 0 else 'top'
            ax.annotate(f'WR={wr:.0f}%',
                        (b.get_x() + b.get_width() / 2, h),
                        ha='center', va=va, fontsize=8)

    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_temporal_quartiles.png", dpi=150)
    plt.close()


def _plot_oos_quartiles(oos_rows):
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ['#d32f2f', '#ff9800', '#4caf50', '#1976d2']
    qs = [r["quartile"] for r in oos_rows]
    rets = [r["avg_ret"] for r in oos_rows]
    wrs = [r["win_rate"] for r in oos_rows]
    ns = [r["n"] for r in oos_rows]

    bars = ax.bar(qs, rets, color=colors, alpha=0.8, edgecolor='black')
    ax.set_title("Part B: OOS Quartile Returns (P3, model trained on P1+P2)",
                 fontweight='bold')
    ax.set_ylabel("Avg Return (%)"); ax.set_xlabel("Score Quartile")
    ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')
    for b, wr, n in zip(bars, wrs, ns):
        h = b.get_height()
        va = 'bottom' if h >= 0 else 'top'
        ax.annotate(f'n={n}\nWR={wr:.0f}%',
                    (b.get_x() + b.get_width() / 2, h),
                    ha='center', va=va, fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_oos_quartiles.png", dpi=150)
    plt.close()


def _plot_feature_importance(feat_rows):
    fig, ax = plt.subplots(figsize=(8, 5))
    names = [r["feature"] for r in feat_rows]
    imps = [r["permutation_imp"] for r in feat_rows]
    sorted_idx = np.argsort(imps)
    names = [names[i] for i in sorted_idx]
    imps = [imps[i] for i in sorted_idx]
    colors = ['#1976d2' if v >= 0 else '#d32f2f' for v in imps]
    ax.barh(names, imps, color=colors, alpha=0.8, edgecolor='black')
    ax.set_title("Part C: Feature Permutation Importance (ΔAUC)", fontweight='bold')
    ax.set_xlabel("Importance (baseline AUC − permuted AUC)")
    ax.axvline(0, color='gray', linewidth=0.5)
    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_feature_importance.png", dpi=150)
    plt.close()


def _plot_calibration(cal_rows, brier, ece):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 8),
                                   gridspec_kw={'height_ratios': [2, 1]})
    valid = [r for r in cal_rows if r["n_samples"] > 0]
    x = [r["mean_score"] for r in valid]
    y = [r["actual_churn_rate"] for r in valid]

    ax1.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Perfect')
    ax1.scatter(x, y, c='#1976d2', s=60, zorder=3)
    ax1.plot(x, y, '#1976d2', alpha=0.5)
    ax1.set_xlabel("Mean Predicted Score"); ax1.set_ylabel("Actual Churn Rate")
    ax1.set_title(f"Part D: Calibration (Brier={brier:.4f}, ECE={ece:.4f})",
                  fontweight='bold')
    ax1.legend(); ax1.set_xlim(0, 1); ax1.set_ylim(0, 1)

    bins = [r["bin"] for r in cal_rows]
    counts = [r["n_samples"] for r in cal_rows]
    ax2.bar(bins, counts, color='#4caf50', alpha=0.7, edgecolor='black')
    ax2.set_xlabel("Bin"); ax2.set_ylabel("N Samples")
    ax2.set_title("Sample Distribution across Calibration Bins")

    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_calibration.png", dpi=150)
    plt.close()


def _plot_score_kde(scores, labels):
    fig, ax = plt.subplots(figsize=(8, 5))
    s_churn = scores[labels == 1]; s_nochurn = scores[labels == 0]
    lo = max(0.0, float(np.min(scores)) - 0.05)
    hi = min(1.0, float(np.max(scores)) + 0.05)
    x_grid = np.linspace(lo, hi, 300)

    if len(s_churn) > 2:
        kde_c = gaussian_kde(s_churn, bw_method='silverman')
        ax.plot(x_grid, kde_c(x_grid), color='#d32f2f', linewidth=2,
                label=f'Churn (n={len(s_churn)})')
        ax.fill_between(x_grid, kde_c(x_grid), alpha=0.2, color='#d32f2f')
    if len(s_nochurn) > 2:
        kde_nc = gaussian_kde(s_nochurn, bw_method='silverman')
        ax.plot(x_grid, kde_nc(x_grid), color='#1976d2', linewidth=2,
                label=f'Non-churn (n={len(s_nochurn)})')
        ax.fill_between(x_grid, kde_nc(x_grid), alpha=0.2, color='#1976d2')

    ax.set_xlabel("Churn Score (P(churn))"); ax.set_ylabel("Density")
    ax.set_title("Part E: Score Distribution — Churn vs Non-Churn",
                 fontweight='bold')
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "Fig_score_kde.png", dpi=150)
    plt.close()


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    print("=" * 70)
    print("X30 PHASE 1: SIGNAL ANATOMY")
    print("=" * 70)

    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

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

    # --- Base sim (50 bps) ---
    print("Running base sim (50 bps)...")
    nav, trades = _sim_base(cl, ef, es, vd, at, regime_h4, wi, CPS_50)
    n_total = len(trades)
    n_trail = sum(1 for t in trades if t["exit_reason"] == "trail_stop")
    print(f"  Total trades: {n_total}, trail-stop exits: {n_trail}")

    # --- Extract features for ALL trail-stop trades ---
    print("Extracting features for trail-stop trades...")
    all_entry_bars = sorted(t["entry_bar"] for t in trades)

    trail_feats, trail_labels, trail_rets_list, trail_eb_list = [], [], [], []
    for t in trades:
        if t["exit_reason"] != "trail_stop": continue
        eb = t["exit_bar"]
        is_churn = any(eb < e <= eb + CHURN_WINDOW for e in all_entry_bars)
        sb = eb - 1
        if sb < 0 or sb >= n: continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]): continue
        feat = _extract_features_7(sb, cl, hi, lo, at, ef, es, vd, d1_str_h4)
        trail_feats.append(feat)
        trail_labels.append(1 if is_churn else 0)
        trail_rets_list.append(t["ret_pct"])
        trail_eb_list.append(eb)

    trail_X = np.array(trail_feats)
    trail_y = np.array(trail_labels, dtype=int)
    trail_rets = np.array(trail_rets_list)
    trail_exit_bars = np.array(trail_eb_list, dtype=int)

    n_churn = int(np.sum(trail_y))
    print(f"  Valid trail-stops: {len(trail_y)}, churn={n_churn}, "
          f"non-churn={len(trail_y) - n_churn}, "
          f"churn rate={n_churn / len(trail_y) * 100:.1f}%")

    # --- Period bar indices ---
    period_ranges = []
    for pname, pstart, pend in PERIODS:
        si = _date_to_bar_idx(h4_ct, pstart)
        ei = _date_to_bar_idx(h4_ct, pend)
        n_in = int(np.sum((trail_exit_bars >= si) & (trail_exit_bars <= ei)))
        period_ranges.append((pname, si, ei))
        print(f"  {pname}: bars [{si}, {ei}], trail-stops: {n_in}")

    # ================================================================
    # RUN ANALYSES A-E
    # ================================================================

    gate_a, n_mono, _, rows_a = part_a(
        trail_X, trail_y, trail_rets, trail_exit_bars, period_ranges)

    gate_b, auc_oos, auc_full, sp_corr, sp_pval, _, oos_rows = part_b(
        trail_X, trail_y, trail_rets, trail_exit_bars, period_ranges)

    feat_rows, dominant = part_c(trail_X, trail_y)

    cal_rows, brier, ece = part_d(trail_X, trail_y)

    dist_summary, dist_scores, dist_labels = part_e(trail_X, trail_y)

    # ================================================================
    # FIGURES
    # ================================================================

    print("\nGenerating figures...")
    _plot_temporal_quartiles(rows_a)
    if oos_rows:
        _plot_oos_quartiles(oos_rows)
    if feat_rows:
        _plot_feature_importance(feat_rows)
    if cal_rows:
        _plot_calibration(cal_rows, brier, ece)
    if dist_scores is not None:
        _plot_score_kde(dist_scores, dist_labels)

    # ================================================================
    # SUMMARY JSON + DISTRIBUTION TABLE
    # ================================================================

    verdict = "PROCEED" if gate_a and gate_b else "STOP"

    summary = {
        "gate_A": gate_a,
        "gate_B": gate_b,
        "oos_auc": round(auc_oos, 4),
        "full_auc": round(auc_full, 4),
        "spearman_corr": round(sp_corr, 4),
        "spearman_pval": round(sp_pval, 4),
        "periods_monotonic": n_mono,
        "dominant_feature": dominant,
        "calibration_brier": round(brier, 4),
        "calibration_ece": round(ece, 4),
        "score_bimodal": dist_summary.get("bimodal", False),
        "verdict": verdict,
    }
    # Merge distribution summary
    for k, v in dist_summary.items():
        summary[f"dist_{k}"] = v

    with open(TABLES / "signal_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Score distribution table (key-value)
    dist_rows = []
    for k in ["full_auc", "oos_auc", "calibration_brier", "calibration_ece",
              "spearman_corr", "spearman_pval"]:
        dist_rows.append({"metric": k, "value": summary[k]})
    for k, v in dist_summary.items():
        dist_rows.append({"metric": k, "value": v})
    _save_csv(TABLES / "Tbl_score_distribution.csv", dist_rows, ["metric", "value"])

    # ================================================================
    # FINAL VERDICT
    # ================================================================

    print(f"\n{'=' * 70}")
    print(f"VERDICT: {verdict}")
    print(f"{'=' * 70}")
    print(f"  Gate A (temporal stability): {'PASS' if gate_a else 'FAIL'} "
          f"({n_mono}/3 periods monotonic)")
    print(f"  Gate B (OOS signal quality): {'PASS' if gate_b else 'FAIL'} "
          f"(AUC={auc_oos:.3f}, mono={'Y' if gate_b else 'N'})")
    print(f"  OOS AUC:          {auc_oos:.3f} (full-sample: {auc_full:.3f})")
    print(f"  Spearman:         {sp_corr:.3f} (p={sp_pval:.4f})")
    print(f"  Dominant feature: {dominant}")
    print(f"  Calibration ECE:  {ece:.4f}, Brier: {brier:.4f}")
    print(f"  Score bimodal:    {dist_summary.get('bimodal', False)}")
    print(f"{'=' * 70}")
    print(f"\nArtifacts saved to: {OUTDIR}")
    print(f"Total time: {time.time() - t0:.1f}s")

    return verdict


if __name__ == "__main__":
    main()
