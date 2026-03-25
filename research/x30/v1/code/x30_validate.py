#!/usr/bin/env python3
"""X30 Phase 3: Validation Gauntlet — WFO + Bootstrap

Parts:
  A: Walk-Forward Optimization (4-fold expanding)
  B: VCBB Bootstrap (500 paths, 25 bps)
  C: Diagnostics (only if G3 fails)

Gates:
  G2: WFO ≥ 75% (3/4 folds) for at least 1 candidate
  G3: Bootstrap P(ΔSh>0) ≥ 55% for at least 1 candidate

Verdict Matrix:
  WFO ≥ 75% AND bootstrap ≥ 55% → PROMOTE
  WFO ≥ 75% AND bootstrap 45-55% → WATCH
  WFO ≥ 75% AND bootstrap < 45% → REJECT
  WFO 50% AND bootstrap ≥ 55% → WATCH
  WFO < 50% → REJECT
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
from scipy.stats import ks_2samp, norm

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
PRIMARY_CPS = 25 / 20_000.0   # 25 bps RT
TRAIN_CPS = 50 / 20_000.0     # 50 bps RT for model training

N_BOOT = 500
BLKSZ = 60
SEED = 42

OUTDIR = Path(__file__).resolve().parents[1]
TABLES = OUTDIR / "tables"
FIGURES = OUTDIR / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

WFO_FOLDS = [
    # (train_start, train_end, oos_start, oos_end)
    ("2019-01-01", "2021-06-30", "2021-07-01", "2022-12-31"),
    ("2019-01-01", "2022-12-31", "2023-01-01", "2024-06-30"),
    ("2019-01-01", "2024-06-30", "2024-07-01", "2025-06-30"),
    ("2019-01-01", "2025-06-30", "2025-07-01", "2026-02-20"),
]


# =========================================================================
# INDICATORS
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


def _predict_score(feat, w, mu, std):
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


def _score_trail_stops(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                       model_w, model_mu, model_std):
    """Score all trail-stop bars using churn model. Returns list of scores."""
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
    """Compute metrics on nav[s:e] (OOS window)."""
    return _metrics(nav[s:e], 0)


def _date_to_bar_idx(h4_ct, date_str):
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    ts_ms = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    idx = np.searchsorted(h4_ct, ts_ms, side='left')
    return min(idx, len(h4_ct) - 1)


# =========================================================================
# SIM ENGINES
# =========================================================================

def _sim_base(cl, ef, es, vd, at, regime_h4, cps):
    """Base E5+EMA1D21 sim."""
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
    """Generalized partial exit sim.

    keep_frac_fn(score) -> float in [0, 1]
    When trail fires: compute score, keep_frac = fn(score).
    If keep_frac < 0.01: full exit. Else: partial exit.
    Trend exit: always full exit.
    """
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
                total_rcv = cash + rcv  # include partial exit cash
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
    """B2: threshold + linear interpolation between lo/hi, capped at max_frac."""
    def fn(score):
        if score <= lo_thresh: return 0.0
        if score >= hi_thresh: return max_frac
        return max_frac * (score - lo_thresh) / (hi_thresh - lo_thresh)
    return fn


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
    print("X30 PHASE 3: VALIDATION GAUNTLET")
    print("=" * 70)

    # ── Load prior results ──────────────────────────────────────────────
    with open(TABLES / "signal_summary.json") as f:
        sig = json.load(f)
    with open(TABLES / "actuator_summary.json") as f:
        act = json.load(f)

    print(f"  Phase 1 verdict: {sig['verdict']}")
    if not sig["verdict"].startswith("PROCEED"):
        print("  ABORT: Phase 1 did not pass."); return

    candidates = act["candidates_for_wfo"]
    cnames = [c["name"] for c in candidates]
    print(f"  Candidates: {cnames}")
    print(f"  Phase 2 best: {act['overall_best']} (Sh@25={act['overall_best_sharpe_25']:.4f})")
    print(f"  MDD mechanism: {act['mdd_from_exposure_pct']:.0f}% exposure, "
          f"{act['mdd_from_timing_pct']:.0f}% timing")

    # ── Load data ───────────────────────────────────────────────────────
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
    if feed.report_start_ms:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms: wi = j; break
    print(f"  H4: {n}, D1: {len(d1_cl)}, warmup: {wi}")

    # ── Indicators ──────────────────────────────────────────────────────
    print("Computing indicators...")
    ef = _ema(cl, max(5, SLOW // 4)); es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb); at = _robust_atr(hi, lo, cl)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    # ── Base sim at 50 bps (for model training) ─────────────────────────
    print("Training full-sample churn model (50 bps)...")
    nav_train50, trades_train50 = _sim_base(cl, ef, es, vd, at, regime_h4, TRAIN_CPS)
    model_w, model_mu, model_std, best_c, n_train = _train_model(
        trades_train50, cl, hi, lo, at, ef, es, vd, d1_str_h4)
    print(f"  Model: C={best_c}, n_train={n_train}")

    # Full-sample scores and thresholds
    full_scores = _score_trail_stops(
        trades_train50, cl, hi, lo, at, ef, es, vd, d1_str_h4,
        model_w, model_mu, model_std)
    full_scores_arr = np.array(full_scores)
    x18_thresh_full = float(np.percentile(full_scores_arr, 100 - X18_ALPHA))
    p25_full = float(np.percentile(full_scores_arr, 25))
    p75_full = float(np.percentile(full_scores_arr, 75))
    print(f"  Thresholds: X18={x18_thresh_full:.4f}, P25={p25_full:.4f}, P75={p75_full:.4f}")

    # ── Base sim at 25 bps (for OOS evaluation) ─────────────────────────
    print("Running base sim at 25 bps (evaluation)...")
    nav_base25, _ = _sim_base(cl, ef, es, vd, at, regime_h4, PRIMARY_CPS)

    # ==================================================================
    # PART A: WALK-FORWARD OPTIMIZATION (4-fold expanding)
    # ==================================================================
    print(f"\n{'=' * 70}")
    print("PART A: WALK-FORWARD OPTIMIZATION (4-fold expanding)")
    print(f"{'=' * 70}")

    wfo_rows = []

    for fold_idx, (ts, te, os_s, os_e) in enumerate(WFO_FOLDS):
        print(f"\n  Fold {fold_idx + 1}: Train →{te}, OOS {os_s}→{os_e}")

        te_idx = _date_to_bar_idx(h4_ct, te)
        oos_s_idx = _date_to_bar_idx(h4_ct, os_s)
        oos_e_idx = _date_to_bar_idx(h4_ct, os_e)

        # Filter training trades (exited within training period)
        fold_trades = [t for t in trades_train50 if t["exit_bar"] <= te_idx]
        print(f"    Training trades: {len(fold_trades)}")

        # Train fold-specific model
        fw, fmu, fstd, fc, fn_tr = _train_model(
            fold_trades, cl, hi, lo, at, ef, es, vd, d1_str_h4)

        if fw is None:
            print(f"    MODEL FAILED — fold counts as loss for all candidates")
            for c in candidates:
                wfo_rows.append({
                    "candidate": c["name"], "fold": fold_idx + 1,
                    "train_start": ts, "train_end": te,
                    "oos_start": os_s, "oos_end": os_e,
                    "base_sharpe": 0.0, "cand_sharpe": 0.0, "delta_sh": 0.0,
                    "base_mdd": 0.0, "cand_mdd": 0.0, "delta_mdd": 0.0, "win": 0})
            continue

        print(f"    Model: C={fc}, n_train={fn_tr}")

        # Compute fold-specific thresholds from training scores
        fscores = _score_trail_stops(
            fold_trades, cl, hi, lo, at, ef, es, vd, d1_str_h4, fw, fmu, fstd)
        if len(fscores) < 5:
            print(f"    Too few scores ({len(fscores)}) — fold counts as loss")
            for c in candidates:
                wfo_rows.append({
                    "candidate": c["name"], "fold": fold_idx + 1,
                    "train_start": ts, "train_end": te,
                    "oos_start": os_s, "oos_end": os_e,
                    "base_sharpe": 0.0, "cand_sharpe": 0.0, "delta_sh": 0.0,
                    "base_mdd": 0.0, "cand_mdd": 0.0, "delta_mdd": 0.0, "win": 0})
            continue

        fscores_arr = np.array(fscores)
        ft = float(np.percentile(fscores_arr, 100 - X18_ALPHA))  # P60
        fp25 = float(np.percentile(fscores_arr, 25))
        fp75 = float(np.percentile(fscores_arr, 75))
        print(f"    Thresholds: X18={ft:.4f}, P25={fp25:.4f}, P75={fp75:.4f}")

        # Base OOS metrics (same for all candidates)
        mb = _metrics_window(nav_base25, oos_s_idx, oos_e_idx + 1)
        print(f"    Base OOS: Sh={mb['sharpe']:.4f}, MDD={mb['mdd']:.1f}%")

        # Each candidate
        for c in candidates:
            if c["type"] == "discrete":
                kfn = make_discrete_fn(ft, c["partial_frac"])
            elif c["design"] == "B2":
                kfn = make_b2_fn(fp25, fp75, c["params"]["max_frac"])
            else:
                continue

            nav_c, _, _ = _sim_partial(
                cl, hi, lo, ef, es, vd, at, regime_h4, d1_str_h4, PRIMARY_CPS,
                fw, fmu, fstd, kfn)
            mc = _metrics_window(nav_c, oos_s_idx, oos_e_idx + 1)
            dsh = mc["sharpe"] - mb["sharpe"]
            dmdd = mc["mdd"] - mb["mdd"]
            win = 1 if dsh > 0 else 0

            wfo_rows.append({
                "candidate": c["name"], "fold": fold_idx + 1,
                "train_start": ts, "train_end": te,
                "oos_start": os_s, "oos_end": os_e,
                "base_sharpe": round(mb["sharpe"], 4),
                "cand_sharpe": round(mc["sharpe"], 4),
                "delta_sh": round(dsh, 4),
                "base_mdd": round(mb["mdd"], 2),
                "cand_mdd": round(mc["mdd"], 2),
                "delta_mdd": round(dmdd, 2),
                "win": win})
            print(f"    {c['name']}: Sh={mc['sharpe']:.4f}, "
                  f"ΔSh={dsh:+.4f}, ΔMDD={dmdd:+.1f}pp, {'WIN' if win else 'LOSS'}")

    # Save WFO CSV
    _save_csv(TABLES / "Tbl_wfo_results.csv", wfo_rows,
              ["candidate", "fold", "train_start", "train_end",
               "oos_start", "oos_end", "base_sharpe", "cand_sharpe",
               "delta_sh", "base_mdd", "cand_mdd", "delta_mdd", "win"])

    # Gate G2
    wfo_summary = {}
    gate_g2 = False
    for c in candidates:
        cn = c["name"]
        crows = [r for r in wfo_rows if r["candidate"] == cn]
        wins = sum(r["win"] for r in crows)
        mean_dsh = float(np.mean([r["delta_sh"] for r in crows]))
        wfo_summary[cn] = {"wins": wins, "total": 4, "mean_delta_sh": round(mean_dsh, 4)}
        if wins >= 3: gate_g2 = True

    print(f"\n  WFO Summary:")
    for cn, s in wfo_summary.items():
        print(f"    {cn}: {s['wins']}/4 wins, mean ΔSh={s['mean_delta_sh']:+.4f}")
    print(f"  Gate G2 (≥3/4): {'PASS' if gate_g2 else 'FAIL'}")

    # ==================================================================
    # PART B: BOOTSTRAP VCBB (500 paths, 25 bps)
    # ==================================================================
    print(f"\n{'=' * 70}")
    print(f"PART B: BOOTSTRAP VCBB ({N_BOOT} paths, 25 bps)")
    print(f"{'=' * 70}")

    # Build candidate keep_frac functions with full-sample thresholds
    cand_fns = {}
    for c in candidates:
        if c["type"] == "discrete":
            cand_fns[c["name"]] = make_discrete_fn(x18_thresh_full, c["partial_frac"])
        elif c["design"] == "B2":
            cand_fns[c["name"]] = make_b2_fn(p25_full, p75_full, c["params"]["max_frac"])

    # Prepare VCBB
    cl_pw = cl[wi:]; hi_pw = hi[wi:]; lo_pw = lo[wi:]
    vo_pw = vo[wi:]; tb_pw = tb[wi:]
    cr, hr, lr, vol_r, tb_r = make_ratios(cl_pw, hi_pw, lo_pw, vo_pw, tb_pw)
    vcbb_state = precompute_vcbb(cr, BLKSZ)
    n_trans = len(cl) - wi - 1; p0 = cl[wi]
    rng = np.random.default_rng(SEED)
    reg_pw = regime_h4[wi:]
    d1s_pw = d1_str_h4[wi:]

    # Storage for bootstrap results
    boot = {cn: {"dsh": [], "dmdd": [], "n_trail": [], "n_trades": [], "n_partial": []}
            for cn in cnames}
    all_boot_scores = []  # for C1 diagnostic

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

        # Base sim
        bnav_b, btrades_b = _sim_base(bcl, bef, bes, bvd, bat, breg, PRIMARY_CPS)
        mb = _metrics(bnav_b, 0)

        # Score base trail-stops for C1 diagnostic
        bscores = _score_trail_stops(btrades_b, bcl, bhi, blo, bat, bef, bes, bvd,
                                     bd1s, model_w, model_mu, model_std)
        all_boot_scores.extend(bscores)
        n_trail_b = len(bscores)

        # Each candidate
        for c in candidates:
            cn = c["name"]
            bnav_c, btrades_c, n_part_c = _sim_partial(
                bcl, bhi, blo, bef, bes, bvd, bat, breg, bd1s, PRIMARY_CPS,
                model_w, model_mu, model_std, cand_fns[cn])
            mc = _metrics(bnav_c, 0)
            boot[cn]["dsh"].append(mc["sharpe"] - mb["sharpe"])
            boot[cn]["dmdd"].append(mc["mdd"] - mb["mdd"])
            boot[cn]["n_trail"].append(n_trail_b)
            boot[cn]["n_trades"].append(len(btrades_c))
            boot[cn]["n_partial"].append(n_part_c)

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    # Summarize bootstrap
    boot_summary = {}
    gate_g3 = False
    best_boot_cand = cnames[0]
    best_boot_p = 0.0

    boot_csv_rows = []
    for c in candidates:
        cn = c["name"]
        dsh = np.array(boot[cn]["dsh"])
        dmdd = np.array(boot[cn]["dmdd"])
        p_dsh = float(np.mean(dsh > 0))
        p_dmdd = float(np.mean(dmdd < 0))
        med_dsh = float(np.median(dsh))
        mean_dsh = float(np.mean(dsh))
        med_dmdd = float(np.median(dmdd))

        boot_summary[cn] = {
            "p_delta_sh_pos": round(p_dsh, 4),
            "median_delta_sh": round(med_dsh, 4),
            "mean_delta_sh": round(mean_dsh, 4),
            "p_delta_mdd_neg": round(p_dmdd, 4),
            "median_delta_mdd": round(med_dmdd, 2),
        }
        boot_csv_rows.append({
            "candidate": cn,
            "p_delta_sh_pos": round(p_dsh, 4),
            "median_delta_sh": round(med_dsh, 4),
            "mean_delta_sh": round(mean_dsh, 4),
            "p_delta_mdd_neg": round(p_dmdd, 4),
            "median_delta_mdd": round(med_dmdd, 2),
        })

        if p_dsh >= 0.55: gate_g3 = True
        if p_dsh > best_boot_p:
            best_boot_p = p_dsh; best_boot_cand = cn

        print(f"  {cn}: P(ΔSh>0)={p_dsh*100:.1f}%, med ΔSh={med_dsh:+.4f}, "
              f"P(ΔMDD<0)={p_dmdd*100:.1f}%, med ΔMDD={med_dmdd:+.1f}pp")

    _save_csv(TABLES / "Tbl_bootstrap.csv", boot_csv_rows,
              ["candidate", "p_delta_sh_pos", "median_delta_sh", "mean_delta_sh",
               "p_delta_mdd_neg", "median_delta_mdd"])

    print(f"\n  Gate G3 (P(ΔSh>0) ≥ 55%): {'PASS' if gate_g3 else 'FAIL'}")

    # ==================================================================
    # PART C: DIAGNOSTICS (only if G3 fails)
    # ==================================================================
    diagnostics = None

    if not gate_g3:
        print(f"\n{'=' * 70}")
        print("PART C: BOOTSTRAP DIAGNOSTICS (G3 FAIL)")
        print(f"{'=' * 70}")

        dc = best_boot_cand
        dsh_arr = np.array(boot[dc]["dsh"])
        dmdd_arr = np.array(boot[dc]["dmdd"])
        n_trail_arr = np.array(boot[dc]["n_trail"])
        n_trades_arr = np.array(boot[dc]["n_trades"])
        n_partial_arr = np.array(boot[dc]["n_partial"])

        print(f"  Diagnosing candidate: {dc}")

        # ── C1: Signal preservation test ────────────────────────────────
        print("\n  C1: Signal preservation (KS test)")
        if len(all_boot_scores) > 0 and len(full_scores) > 0:
            ks_stat, ks_pval = ks_2samp(full_scores, all_boot_scores)
            sig_ok = ks_pval > 0.05
            print(f"    Real scores: n={len(full_scores)}, "
                  f"mean={np.mean(full_scores):.4f}, std={np.std(full_scores):.4f}")
            print(f"    Boot scores: n={len(all_boot_scores)}, "
                  f"mean={np.mean(all_boot_scores):.4f}, std={np.std(all_boot_scores):.4f}")
            print(f"    KS D={ks_stat:.4f}, p={ks_pval:.4f} → "
                  f"{'preserved' if sig_ok else 'DISRUPTED'}")
        else:
            ks_stat, ks_pval, sig_ok = 0.0, 1.0, True
            print(f"    No scores to compare")

        # ── C2: Conditional analysis ────────────────────────────────────
        print("\n  C2: Conditional analysis (by trail-stop activity)")
        hi_act = dsh_arr[n_trail_arr >= 10]
        lo_act = dsh_arr[n_trail_arr < 10]
        p_hi = float(np.mean(hi_act > 0)) if len(hi_act) > 0 else 0.0
        p_lo = float(np.mean(lo_act > 0)) if len(lo_act) > 0 else 0.0
        print(f"    High activity (≥10 trail stops): n={len(hi_act)}, P(ΔSh>0)={p_hi*100:.1f}%")
        print(f"    Low activity (<10 trail stops):  n={len(lo_act)}, P(ΔSh>0)={p_lo*100:.1f}%")

        # ── C3: Path-by-path decomposition ──────────────────────────────
        print("\n  C3: Path-by-path decomposition")
        si = np.argsort(dsh_arr)
        b50 = si[:50]; t50 = si[-50:]
        print(f"    Bottom 50 (worst):")
        print(f"      avg ΔSh={np.mean(dsh_arr[b50]):+.4f}, "
              f"avg trades={np.mean(n_trades_arr[b50]):.1f}, "
              f"avg partial={np.mean(n_partial_arr[b50]):.1f}, "
              f"avg trails={np.mean(n_trail_arr[b50]):.1f}")
        print(f"    Top 50 (best):")
        print(f"      avg ΔSh={np.mean(dsh_arr[t50]):+.4f}, "
              f"avg trades={np.mean(n_trades_arr[t50]):.1f}, "
              f"avg partial={np.mean(n_partial_arr[t50]):.1f}, "
              f"avg trails={np.mean(n_trail_arr[t50]):.1f}")

        # ── C4: Paired permutation test ─────────────────────────────────
        print("\n  C4: Paired permutation test (10,000 permutations)")
        obs_mean = float(np.mean(dsh_arr))
        prng = np.random.default_rng(SEED)
        n_perm = 10_000
        count_ge = 0
        for _ in range(n_perm):
            signs = prng.choice([-1, 1], size=len(dsh_arr))
            if np.mean(dsh_arr * signs) >= obs_mean:
                count_ge += 1
        perm_p = count_ge / n_perm
        print(f"    Observed mean ΔSh: {obs_mean:+.4f}")
        print(f"    Permutation p-value: {perm_p:.4f}")

        # ── C5: Power analysis ──────────────────────────────────────────
        print("\n  C5: Power analysis")
        std_dsh = float(np.std(dsh_arr, ddof=0))
        eff_d = obs_mean / std_dsh if std_dsh > 1e-12 else 0.0
        d_tgt = float(norm.ppf(0.55))  # ≈ 0.1257
        cur_yrs = 7.0

        if eff_d <= 0:
            yrs_need = float('inf')
        elif eff_d >= d_tgt:
            yrs_need = cur_yrs  # already sufficient
        else:
            yrs_need = cur_yrs * (d_tgt / eff_d) ** 2

        print(f"    Effect size d = mean(ΔSh)/std(ΔSh) = {eff_d:.4f}")
        print(f"    Target d for P>55%: {d_tgt:.4f}")
        print(f"    Current data: ~{cur_yrs:.0f} years")
        if yrs_need < 1000:
            print(f"    Years needed: {yrs_need:.1f}")
        else:
            print(f"    Years needed: >1000 (effect too small or negative)")

        diagnostics = {
            "signal_preserved": bool(sig_ok),
            "ks_pvalue": round(float(ks_pval), 4),
            "conditional_p_high_activity": round(p_hi, 4),
            "conditional_p_low_activity": round(p_lo, 4),
            "n_high_activity": int(len(hi_act)),
            "n_low_activity": int(len(lo_act)),
            "permutation_pvalue": round(float(perm_p), 4),
            "effect_d": round(float(eff_d), 4),
            "years_needed_for_55pct": round(float(yrs_need), 1) if yrs_need < 1000 else None,
        }

        # Save diagnostics CSV
        diag_rows = [
            {"test": "C1", "metric": "KS_D", "value": round(float(ks_stat), 4),
             "interpretation": "preserved" if sig_ok else "disrupted"},
            {"test": "C1", "metric": "KS_pvalue", "value": round(float(ks_pval), 4),
             "interpretation": f"p {'>.05 preserved' if sig_ok else '<.05 disrupted'}"},
            {"test": "C2", "metric": "P_high_activity", "value": round(p_hi, 4),
             "interpretation": f"n={len(hi_act)} paths with >=10 trail stops"},
            {"test": "C2", "metric": "P_low_activity", "value": round(p_lo, 4),
             "interpretation": f"n={len(lo_act)} paths with <10 trail stops"},
            {"test": "C3", "metric": "bottom_50_avg_dsh", "value": round(float(np.mean(dsh_arr[b50])), 4),
             "interpretation": "worst 50 paths"},
            {"test": "C3", "metric": "top_50_avg_dsh", "value": round(float(np.mean(dsh_arr[t50])), 4),
             "interpretation": "best 50 paths"},
            {"test": "C4", "metric": "permutation_pvalue", "value": round(float(perm_p), 4),
             "interpretation": f"{'significant' if perm_p < 0.05 else 'not significant'} at 5%"},
            {"test": "C5", "metric": "effect_d", "value": round(float(eff_d), 4),
             "interpretation": "d = mean(dSh) / std(dSh)"},
            {"test": "C5", "metric": "years_needed",
             "value": round(float(yrs_need), 1) if yrs_need < 1000 else "inf",
             "interpretation": "years for P(dSh>0)>55%"},
        ]
        _save_csv(TABLES / "Tbl_bootstrap_diagnostics.csv", diag_rows,
                  ["test", "metric", "value", "interpretation"])

        # ── Diagnostic figures ──────────────────────────────────────────
        # C1: Signal preservation
        fig, ax = plt.subplots(figsize=(8, 5))
        if len(full_scores) > 0:
            ax.hist(full_scores, bins=30, density=True, alpha=0.5, label="Real", color="blue")
        if len(all_boot_scores) > 0:
            ax.hist(all_boot_scores, bins=30, density=True, alpha=0.5,
                    label="Bootstrap", color="orange")
        ax.set_xlabel("Churn Score"); ax.set_ylabel("Density")
        ax.set_title(f"C1: Score Distribution (KS D={ks_stat:.3f}, p={ks_pval:.3f})")
        ax.legend(); fig.tight_layout()
        fig.savefig(FIGURES / "Fig_signal_preservation.png", dpi=150); plt.close(fig)

        # C2: Conditional bootstrap
        fig, ax = plt.subplots(figsize=(8, 5))
        data_bp, labels_bp = [], []
        if len(hi_act) > 0:
            data_bp.append(hi_act)
            labels_bp.append(f"High (>=10)\nn={len(hi_act)}\nP={p_hi*100:.1f}%")
        if len(lo_act) > 0:
            data_bp.append(lo_act)
            labels_bp.append(f"Low (<10)\nn={len(lo_act)}\nP={p_lo*100:.1f}%")
        if data_bp:
            ax.boxplot(data_bp, tick_labels=labels_bp)
        ax.axhline(0, color="red", linestyle="--", alpha=0.5)
        ax.set_ylabel("ΔSharpe"); ax.set_title("C2: Conditional Bootstrap by Activity Level")
        fig.tight_layout()
        fig.savefig(FIGURES / "Fig_conditional_bootstrap.png", dpi=150); plt.close(fig)

    # ==================================================================
    # VERDICT
    # ==================================================================
    best_cand = cnames[0]; best_w = 0; best_bp = 0.0
    for c in candidates:
        cn = c["name"]
        w = wfo_summary[cn]["wins"]
        bp = boot_summary[cn]["p_delta_sh_pos"]
        if w > best_w or (w == best_w and bp > best_bp):
            best_cand = cn; best_w = w; best_bp = bp

    wfo_pct = best_w / 4 * 100
    if wfo_pct < 50:
        verdict = "REJECT"
    elif wfo_pct >= 75 and best_bp >= 0.55:
        verdict = "PROMOTE"
    elif wfo_pct >= 75 and 0.45 <= best_bp < 0.55:
        verdict = "WATCH"
    elif wfo_pct >= 75 and best_bp < 0.45:
        verdict = "REJECT"
    elif wfo_pct >= 50 and best_bp >= 0.55:
        verdict = "WATCH"
    else:
        verdict = "REJECT"

    # ==================================================================
    # GENERATE FIGURES
    # ==================================================================
    print("\nGenerating figures...")

    # Fig: WFO bars (grouped bar chart)
    fig, ax = plt.subplots(figsize=(10, 6))
    nc = len(cnames); x = np.arange(4)
    width = 0.8 / nc
    colors = plt.cm.Set2(np.linspace(0, 1, max(nc, 3)))
    for ci, cn in enumerate(cnames):
        vals = [r["delta_sh"] for r in wfo_rows if r["candidate"] == cn]
        bars = ax.bar(x + ci * width - 0.4 + width / 2, vals, width,
                      label=cn, color=colors[ci])
        for bi, v in enumerate(vals):
            color = "green" if v > 0 else "red"
            ax.annotate(f"{v:+.3f}", (x[bi] + ci * width - 0.4 + width / 2, v),
                       ha='center', va='bottom' if v > 0 else 'top',
                       fontsize=7, color=color)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Fold"); ax.set_ylabel("ΔSharpe (OOS)")
    ax.set_title("Part A: WFO — ΔSharpe per Fold per Candidate")
    ax.set_xticks(x)
    ax.set_xticklabels([f"F{i+1}\n{WFO_FOLDS[i][2]}→{WFO_FOLDS[i][3]}" for i in range(4)],
                       fontsize=7)
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "Fig_wfo_bars.png", dpi=150); plt.close(fig)

    # Fig: Bootstrap violin
    fig, ax = plt.subplots(figsize=(10, 6))
    dsh_data = [np.array(boot[cn]["dsh"]) for cn in cnames]
    parts = ax.violinplot(dsh_data, positions=range(nc), showmedians=True)
    ax.axhline(0, color="red", linestyle="--", alpha=0.5)
    ax.set_xticks(range(nc)); ax.set_xticklabels(cnames, fontsize=8)
    ax.set_ylabel("ΔSharpe"); ax.set_title("Part B: Bootstrap ΔSharpe Distribution")
    for ci, cn in enumerate(cnames):
        p = boot_summary[cn]["p_delta_sh_pos"]
        ymax = np.percentile(dsh_data[ci], 95)
        ax.annotate(f"P={p*100:.1f}%", (ci, ymax), ha='center', fontsize=9, fontweight='bold')
    fig.tight_layout(); fig.savefig(FIGURES / "Fig_bootstrap_violin.png", dpi=150); plt.close(fig)

    # Fig: Bootstrap histogram (best candidate)
    fig, ax = plt.subplots(figsize=(8, 5))
    d = np.array(boot[best_cand]["dsh"])
    ax.hist(d, bins=40, alpha=0.7, color="steelblue", edgecolor="white")
    ax.axvline(0, color="red", linestyle="--", linewidth=2, label="zero")
    ax.axvline(np.median(d), color="green", linestyle="-", linewidth=2,
               label=f"median={np.median(d):+.4f}")
    bp = boot_summary[best_cand]["p_delta_sh_pos"]
    ax.set_title(f"Bootstrap ΔSharpe: {best_cand}\n"
                 f"P(ΔSh>0)={bp*100:.1f}%, n={N_BOOT}")
    ax.set_xlabel("ΔSharpe"); ax.set_ylabel("Count"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGURES / "Fig_bootstrap_hist.png", dpi=150); plt.close(fig)

    # ==================================================================
    # SAVE SUMMARY JSON
    # ==================================================================
    summary = {
        "candidates_tested": cnames,
        "wfo_results": wfo_summary,
        "bootstrap_results": boot_summary,
        "gate_G2": bool(gate_g2),
        "gate_G3": bool(gate_g3),
        "best_candidate": best_cand,
        "verdict": verdict,
    }
    if diagnostics is not None:
        summary["diagnostics"] = diagnostics

    with open(TABLES / "validation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # ==================================================================
    # FINAL VERDICT
    # ==================================================================
    print(f"\n{'=' * 70}")
    print(f"PHASE 3 COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Gate G2 (WFO ≥75%): {'PASS' if gate_g2 else 'FAIL'}")
    print(f"  Gate G3 (Bootstrap ≥55%): {'PASS' if gate_g3 else 'FAIL'}")
    print(f"  Best candidate: {best_cand}")
    print(f"    WFO: {best_w}/4 wins")
    print(f"    Bootstrap P(ΔSh>0): {best_bp*100:.1f}%")

    # MDD reporting
    if best_cand in boot_summary:
        bs = boot_summary[best_cand]
        print(f"    Bootstrap P(ΔMDD<0): {bs['p_delta_mdd_neg']*100:.1f}% "
              f"(med ΔMDD={bs['median_delta_mdd']:+.1f}pp)")

    print(f"\n  VERDICT: {verdict}")
    if verdict == "PROMOTE":
        print(f"  → Proceed to Phase 4 (deployment spec)")
    elif verdict == "WATCH":
        print(f"  → Insufficient evidence today. Check with 2+ years new OOS data.")
    elif verdict == "REJECT":
        print(f"  → Effect too small/unreliable for production use.")
    print(f"{'=' * 70}")
    print(f"\nTotal time: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
