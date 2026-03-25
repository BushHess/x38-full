#!/usr/bin/env python3
"""X13 Research — Is Trail-Stop Churn Predictable?

Central question: At the moment E0+EMA1D21's trail stop fires, does
information exist in available data that distinguishes true reversals
from false stop-outs (churn)?

Phases:
  P0: Oracle Ceiling — max improvement from perfect churn suppression
  P1: Feature Census — 10 features at each trail stop exit
  P2: Univariate Predictability — Mann-Whitney U per feature
  P3: Multivariate Bound — L2-logistic LOOCV + permutation AUC
  P4: Bootstrap OOS — 500 VCBB paths
  P5: Churn Window Sensitivity — [10, 15, 20, 30, 40] bars

Single strategy (E0+EMA1D21), no parameter sweep.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import lfilter
from scipy.stats import mannwhitneyu
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
CHURN_WINDOWS = [10, 15, 20, 30, 40]

N_BOOT = 500
BLKSZ = 60
SEED = 42

N_PERM = 500
C_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0]
MIN_TRAIL_STOPS = 20

FEATURE_NAMES = [
    "ema_ratio", "bars_held", "atr_pctl", "bar_range_atr",
    "dd_from_peak", "bars_since_peak", "close_position",
    "vdo_at_exit", "d1_regime_str", "trail_tightness",
]

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# FAST INDICATORS (vectorized, identical to X12)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high, low, close, period=ATR_P):
    """Standard Wilder ATR."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
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


def _compute_d1_regime(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
    """Compute D1 EMA regime and map to H4 close_time grid."""
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
    """Compute (D1_close - D1_EMA) / D1_close mapped to H4 bars."""
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
# PRECOMPUTE INDICATORS
# =========================================================================

def _compute_indicators(cl, hi, lo, vo, tb, slow_period=SLOW):
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    vd = _vdo(cl, hi, lo, vo, tb)
    at = _atr(hi, lo, cl, ATR_P)
    return ef, es, vd, at


# =========================================================================
# SIM CORE — E0+EMA1D21 with optional oracle mode
# =========================================================================

def _run_sim(cl, ef, es, vd, at, regime_h4, wi,
             trail_mult=TRAIL, cps=CPS_HARSH,
             oracle_mode=False, churn_window=CHURN_WINDOW):
    """E0+EMA1D21 sim with precomputed indicators.

    oracle_mode: suppress trail stop exits where entry signal fires within
    churn_window bars (forward-looking, uses future information).

    Returns (nav, trades, n_suppressed) where n_suppressed > 0 only in oracle mode.
    """
    n = len(cl)

    # Precompute entry signal for oracle lookahead
    if oracle_mode:
        entry_sig = np.zeros(n, dtype=np.bool_)
        for j in range(n):
            if not (math.isnan(ef[j]) or math.isnan(es[j]) or math.isnan(at[j])):
                entry_sig[j] = ef[j] > es[j] and vd[j] > VDO_THR and regime_h4[j]

    cash = CASH
    bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    entry_px = 0.0
    entry_bar = 0
    entry_cost = 0.0
    exit_reason = ""
    n_suppressed = 0

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
            elif px:
                px = False
                received = bq * fp * (1 - cps)
                pnl = received - entry_cost
                ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
                a_val = at[i - 1] if not math.isnan(at[i - 1]) else 0.0
                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "entry_px": entry_px,
                    "exit_px": fp,
                    "peak_px": pk,
                    "pnl_usd": pnl,
                    "ret_pct": ret,
                    "bars_held": i - entry_bar,
                    "exit_reason": exit_reason,
                    "trail_dist": trail_mult * a_val,
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
            ts = pk - trail_mult * a_val
            if p < ts:
                # Oracle: suppress if entry signal fires within lookahead
                suppress = False
                if oracle_mode:
                    end = min(i + 1 + churn_window, n)
                    if end > i + 1 and np.any(entry_sig[i + 1:end]):
                        suppress = True
                        n_suppressed += 1
                if not suppress:
                    exit_reason = "trail_stop"
                    px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    # Close open position at end
    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        pnl = received - entry_cost
        ret = (received / entry_cost - 1.0) * 100 if entry_cost > 0 else 0.0
        a_val = at[-1] if not math.isnan(at[-1]) else 0.0
        trades.append({
            "entry_bar": entry_bar,
            "exit_bar": n - 1,
            "entry_px": entry_px,
            "exit_px": cl[-1],
            "peak_px": pk,
            "pnl_usd": pnl,
            "ret_pct": ret,
            "bars_held": (n - 1) - entry_bar,
            "exit_reason": "eod",
            "trail_dist": trail_mult * a_val,
        })
        cash = received
        bq = 0.0
        nt += 1
        nav[-1] = cash

    return nav, trades, n_suppressed


# =========================================================================
# CHURN LABELING
# =========================================================================

def _label_churn(trades, churn_window=CHURN_WINDOW):
    """Label each trail stop exit as churn (1) or true reversal (0).

    Returns list of (trade_index, label) for trail stop exits only.
    """
    entry_bars = sorted(t["entry_bar"] for t in trades)
    results = []
    for idx, t in enumerate(trades):
        if t["exit_reason"] != "trail_stop":
            continue
        eb = t["exit_bar"]
        # Check if any trade entry falls in (eb, eb + churn_window]
        is_churn = any(eb < e <= eb + churn_window for e in entry_bars)
        results.append((idx, 1 if is_churn else 0))
    return results


# =========================================================================
# FEATURE EXTRACTION
# =========================================================================

def _extract_features(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                      trail_mult=TRAIL, churn_window=CHURN_WINDOW):
    """Extract 10 features at each trail stop exit.

    Returns (X, y, trail_indices) where:
    - X: (n_trail, 10) feature matrix
    - y: (n_trail,) labels (1=churn, 0=true)
    - trail_indices: trade indices of trail stop exits
    """
    churn_labels = _label_churn(trades, churn_window)
    if not churn_labels:
        return np.empty((0, 10)), np.empty(0, dtype=int), []

    n = len(cl)
    features = []
    labels = []
    indices = []

    for trade_idx, label in churn_labels:
        t = trades[trade_idx]
        # Signal bar = exit_bar - 1 (trail stop fires at bar i, processed at i+1)
        sb = t["exit_bar"] - 1
        if sb < 0 or sb >= n:
            continue
        if math.isnan(at[sb]) or math.isnan(ef[sb]) or math.isnan(es[sb]):
            continue

        eb = t["entry_bar"]

        # F1: ema_ratio
        f1 = ef[sb] / es[sb] if abs(es[sb]) > 1e-12 else 1.0

        # F2: bars_held
        f2 = float(t["bars_held"])

        # F3: atr_pctl (percentile in trailing 100 bars)
        atr_start = max(0, sb - 99)
        atr_window = at[atr_start:sb + 1]
        valid_atr = atr_window[~np.isnan(atr_window)]
        if len(valid_atr) > 1:
            f3 = float(np.sum(valid_atr <= at[sb])) / len(valid_atr)
        else:
            f3 = 0.5

        # F4: bar_range_atr
        bar_range = hi[sb] - lo[sb]
        f4 = bar_range / at[sb] if at[sb] > 1e-12 else 1.0

        # F5: dd_from_peak
        peak_px = t["peak_px"]
        f5 = (peak_px - cl[sb]) / peak_px if peak_px > 1e-12 else 0.0

        # F6: bars_since_peak
        trade_closes = cl[eb:t["exit_bar"]]
        if len(trade_closes) > 0:
            peak_bar = eb + int(np.argmax(trade_closes))
            f6 = float(sb - peak_bar)
        else:
            f6 = 0.0

        # F7: close_position
        bar_w = hi[sb] - lo[sb]
        f7 = (cl[sb] - lo[sb]) / bar_w if bar_w > 1e-12 else 0.5

        # F8: vdo_at_exit
        f8 = float(vd[sb])

        # F9: d1_regime_str
        f9 = float(d1_str_h4[sb])

        # F10: trail_tightness
        f10 = trail_mult * at[sb] / cl[sb] if cl[sb] > 1e-12 else 0.0

        features.append([f1, f2, f3, f4, f5, f6, f7, f8, f9, f10])
        labels.append(label)
        indices.append(trade_idx)

    return np.array(features), np.array(labels, dtype=int), indices


# =========================================================================
# STATISTICAL UTILITIES
# =========================================================================

def _roc_auc(y_true, y_score):
    """AUC via concordance (Mann-Whitney U statistic)."""
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    comp = pos[:, None] > neg[None, :]
    ties = pos[:, None] == neg[None, :]
    return float((np.sum(comp) + 0.5 * np.sum(ties)) / (len(pos) * len(neg)))


def _cliffs_delta(group1, group2):
    """Cliff's delta effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return 0.0
    more = group1[:, None] > group2[None, :]
    less = group1[:, None] < group2[None, :]
    return float((np.sum(more) - np.sum(less)) / (n1 * n2))


def _cliffs_category(d):
    """Categorize Cliff's delta magnitude."""
    ad = abs(d)
    if ad < 0.147:
        return "negligible"
    elif ad < 0.33:
        return "small"
    elif ad < 0.474:
        return "medium"
    else:
        return "large"


def _fit_logistic_l2(X, y, C=1.0, max_iter=100):
    """Fit L2-regularized logistic regression via Newton-Raphson.

    Returns weight vector (d+1,) where last element is bias.
    """
    n, d = X.shape
    Xa = np.column_stack([X, np.ones(n)])
    w = np.zeros(d + 1)

    for _ in range(max_iter):
        z = Xa @ w
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

        # Gradient
        err = p - y
        reg = np.zeros(d + 1)
        reg[:d] = w[:d] / C
        grad = Xa.T @ err / n + reg

        # Hessian
        S = p * (1 - p) + 1e-12
        H = (Xa.T * S) @ Xa / n
        H_reg = np.zeros((d + 1, d + 1))
        np.fill_diagonal(H_reg[:d, :d], 1.0 / C)
        H += H_reg

        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            break
        w -= step

        if np.max(np.abs(step)) < 1e-8:
            break

    return w


def _logistic_loocv_auc(X, y, C=1.0):
    """L2-regularized logistic LOOCV, returns AUC."""
    n = X.shape[0]
    preds = np.zeros(n)

    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_tr, y_tr = X[mask], y[mask]

        # Skip if only one class in training
        if len(np.unique(y_tr)) < 2:
            preds[i] = np.mean(y_tr)
            continue

        w = _fit_logistic_l2(X_tr, y_tr, C)
        z = np.dot(np.append(X[i], 1.0), w)
        preds[i] = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    return _roc_auc(y, preds), preds


def _kfold_auc(X, y, C=1.0, k=10, rng=None):
    """K-fold CV AUC (faster than LOOCV for bootstrap)."""
    n = X.shape[0]
    if rng is None:
        idx = np.arange(n)
    else:
        idx = rng.permutation(n)

    preds = np.zeros(n)
    fold_size = n // k

    for fold in range(k):
        start = fold * fold_size
        end = start + fold_size if fold < k - 1 else n
        test_mask = np.zeros(n, dtype=bool)
        test_mask[idx[start:end]] = True
        train_mask = ~test_mask

        X_tr, y_tr = X[train_mask], y[train_mask]
        X_te = X[test_mask]

        if len(np.unique(y_tr)) < 2:
            preds[test_mask] = np.mean(y_tr)
            continue

        w = _fit_logistic_l2(X_tr, y_tr, C)
        z = np.column_stack([X_te, np.ones(X_te.shape[0])]) @ w
        preds[test_mask] = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    return _roc_auc(y, preds)


def _standardize(X):
    """Standardize to zero mean, unit variance."""
    mu = np.mean(X, axis=0)
    std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


# =========================================================================
# PHASE 0: ORACLE CEILING
# =========================================================================

def run_p0_oracle(cl, ef, es, vd, at, regime_h4, wi,
                  churn_window=CHURN_WINDOW, cps=CPS_HARSH):
    """P0: Oracle sim — max improvement from perfect churn prediction."""
    print("\n" + "=" * 70)
    print(f"P0: ORACLE CEILING (churn_window={churn_window})")
    print("=" * 70)

    # Baseline sim
    nav_base, trades_base, _ = _run_sim(
        cl, ef, es, vd, at, regime_h4, wi, cps=cps,
        oracle_mode=False)
    m_base = _metrics(nav_base, wi, len(trades_base))

    # Oracle sim
    nav_oracle, trades_oracle, n_supp = _run_sim(
        cl, ef, es, vd, at, regime_h4, wi, cps=cps,
        oracle_mode=True, churn_window=churn_window)
    m_oracle = _metrics(nav_oracle, wi, len(trades_oracle))

    d_sharpe = m_oracle["sharpe"] - m_base["sharpe"]
    d_cagr = m_oracle["cagr"] - m_base["cagr"]
    d_mdd = m_oracle["mdd"] - m_base["mdd"]

    results = {
        "baseline": m_base,
        "oracle": m_oracle,
        "d_sharpe": d_sharpe,
        "d_cagr": d_cagr,
        "d_mdd": d_mdd,
        "n_suppressed": n_supp,
        "n_allowed": len([t for t in trades_base if t["exit_reason"] == "trail_stop"]) - n_supp,
        "baseline_trades": len(trades_base),
        "oracle_trades": len(trades_oracle),
    }

    print(f"\n  Baseline: Sharpe={m_base['sharpe']:.4f}, CAGR={m_base['cagr']:.2f}%, "
          f"MDD={m_base['mdd']:.2f}%, trades={len(trades_base)}")
    print(f"  Oracle:   Sharpe={m_oracle['sharpe']:.4f}, CAGR={m_oracle['cagr']:.2f}%, "
          f"MDD={m_oracle['mdd']:.2f}%, trades={len(trades_oracle)}")
    print(f"\n  d_sharpe: {d_sharpe:+.4f}  d_cagr: {d_cagr:+.2f}pp  d_mdd: {d_mdd:+.2f}pp")
    print(f"  Suppressed: {n_supp}  Allowed: {results['n_allowed']}")

    if d_sharpe < 0:
        print(f"\n  *** ORACLE d_sharpe < 0: churn suppression HURTS performance ***")
        print(f"  *** Trail stop's \"false exits\" are profit-taking, not errors ***")

    v0 = d_sharpe > 0.10
    print(f"\n  V0 (d_sharpe > 0.10): {'PASS' if v0 else 'FAIL'}")
    results["v0"] = v0

    return results


# =========================================================================
# PHASE 1: FEATURE CENSUS
# =========================================================================

def run_p1_features(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                    churn_window=CHURN_WINDOW):
    """P1: Extract features at each trail stop exit."""
    print("\n" + "=" * 70)
    print(f"P1: FEATURE CENSUS (churn_window={churn_window})")
    print("=" * 70)

    X, y, indices = _extract_features(
        trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
        churn_window=churn_window)

    n_churn = int(np.sum(y == 1))
    n_true = int(np.sum(y == 0))

    print(f"\n  Trail stop exits: {len(y)}")
    print(f"  Churn: {n_churn} ({n_churn/len(y)*100:.1f}%)  True: {n_true} ({n_true/len(y)*100:.1f}%)")
    print(f"  Features: {len(FEATURE_NAMES)}")

    # Print feature summary
    for j, name in enumerate(FEATURE_NAMES):
        vals = X[:, j]
        print(f"    {name:18s}: mean={np.mean(vals):8.4f}, std={np.std(vals):8.4f}, "
              f"min={np.min(vals):8.4f}, max={np.max(vals):8.4f}")

    return X, y


# =========================================================================
# PHASE 2: UNIVARIATE PREDICTABILITY
# =========================================================================

def run_p2_univariate(X, y):
    """P2: Mann-Whitney U + Cliff's delta per feature."""
    print("\n" + "=" * 70)
    print("P2: UNIVARIATE PREDICTABILITY")
    print("=" * 70)

    n_features = X.shape[1]
    n_tests = n_features
    alpha = 0.05

    rows = []
    any_significant = False

    churn_mask = y == 1
    true_mask = y == 0

    print(f"\n  {'Feature':18s}  {'U':>8s}  {'p_raw':>8s}  {'p_bonf':>8s}  {'Cliff_d':>8s}  {'Effect':>10s}  {'Mean_C':>8s}  {'Mean_T':>8s}")
    print("  " + "-" * 100)

    for j in range(n_features):
        vals_churn = X[churn_mask, j]
        vals_true = X[true_mask, j]

        U, p_raw = mannwhitneyu(vals_churn, vals_true, alternative='two-sided')
        p_bonf = min(p_raw * n_tests, 1.0)

        cd = _cliffs_delta(vals_churn, vals_true)
        cat = _cliffs_category(cd)

        mean_c = float(np.mean(vals_churn))
        mean_t = float(np.mean(vals_true))

        if p_bonf < alpha:
            any_significant = True

        row = {
            "feature": FEATURE_NAMES[j],
            "U": float(U),
            "p_raw": float(p_raw),
            "p_bonferroni": float(p_bonf),
            "cliffs_delta": float(cd),
            "effect_size": cat,
            "mean_churn": mean_c,
            "mean_true": mean_t,
            "direction": "churn_higher" if mean_c > mean_t else "true_higher",
        }
        rows.append(row)

        sig = " ***" if p_bonf < alpha else ""
        print(f"  {FEATURE_NAMES[j]:18s}  {U:8.0f}  {p_raw:8.4f}  {p_bonf:8.4f}  {cd:+8.4f}  {cat:>10s}  {mean_c:8.4f}  {mean_t:8.4f}{sig}")

    v1 = any_significant
    print(f"\n  V1 (any Bonferroni p < 0.05): {'PASS' if v1 else 'FAIL'}")

    return {"rows": rows, "v1": v1}


# =========================================================================
# PHASE 3: MULTIVARIATE PREDICTABILITY BOUND
# =========================================================================

def run_p3_multivariate(X, y, n_perm=N_PERM):
    """P3: L2-logistic LOOCV + permutation AUC."""
    print("\n" + "=" * 70)
    print("P3: MULTIVARIATE PREDICTABILITY BOUND")
    print("=" * 70)

    if len(np.unique(y)) < 2 or len(y) < 10:
        print("  Insufficient data for multivariate analysis")
        return {"loocv_auc": 0.5, "permutation_p": 1.0, "v2": False}

    # Standardize features
    Xs, mu, std = _standardize(X)

    # Select best C by LOOCV
    print(f"\n  Selecting regularisation C from {C_VALUES} ...")
    best_c = 1.0
    best_auc = 0.0
    for c in C_VALUES:
        auc_c, _ = _logistic_loocv_auc(Xs, y, C=c)
        if auc_c > best_auc:
            best_auc = auc_c
            best_c = c
    print(f"  Best C={best_c}, LOOCV AUC={best_auc:.4f}")

    # Main LOOCV AUC
    observed_auc, preds = _logistic_loocv_auc(Xs, y, C=best_c)

    # Full-data coefficients
    w_full = _fit_logistic_l2(Xs, y, C=best_c)
    coefs = w_full[:-1]
    bias = w_full[-1]

    print(f"\n  LOOCV AUC: {observed_auc:.4f}")
    print(f"  Coefficients (standardized):")
    for j, name in enumerate(FEATURE_NAMES):
        print(f"    {name:18s}: {coefs[j]:+.4f}")
    print(f"    {'bias':18s}: {bias:+.4f}")

    # Permutation test
    print(f"\n  Permutation test ({n_perm} shuffles) ...")
    rng = np.random.default_rng(SEED)
    null_aucs = np.zeros(n_perm)
    for k in range(n_perm):
        y_perm = rng.permutation(y)
        null_aucs[k], _ = _logistic_loocv_auc(Xs, y_perm, C=best_c)
        if (k + 1) % 100 == 0:
            print(f"    ... {k + 1}/{n_perm} permutations done")

    perm_p = float((1 + np.sum(null_aucs >= observed_auc)) / (1 + n_perm))

    print(f"\n  Null AUC: mean={np.mean(null_aucs):.4f}, std={np.std(null_aucs):.4f}")
    print(f"  Permutation p-value: {perm_p:.4f}")

    # Confusion matrix at Youden's J
    thresholds = np.linspace(0, 1, 101)
    best_j = -1.0
    best_thr = 0.5
    for thr in thresholds:
        pred_pos = preds >= thr
        tp = np.sum(pred_pos & (y == 1))
        fp = np.sum(pred_pos & (y == 0))
        fn = np.sum(~pred_pos & (y == 1))
        tn = np.sum(~pred_pos & (y == 0))
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0
        j_stat = sens + spec - 1
        if j_stat > best_j:
            best_j = j_stat
            best_thr = thr

    pred_pos = preds >= best_thr
    tp = int(np.sum(pred_pos & (y == 1)))
    fp = int(np.sum(pred_pos & (y == 0)))
    fn = int(np.sum(~pred_pos & (y == 1)))
    tn = int(np.sum(~pred_pos & (y == 0)))

    v2 = perm_p < 0.05 and observed_auc > 0.60
    print(f"\n  Youden threshold: {best_thr:.2f}")
    print(f"  TP={tp}, FP={fp}, FN={fn}, TN={tn}")
    print(f"  V2 (perm_p < 0.05 AND AUC > 0.60): {'PASS' if v2 else 'FAIL'}")

    results = {
        "loocv_auc": float(observed_auc),
        "best_C": float(best_c),
        "permutation_p": float(perm_p),
        "null_auc_mean": float(np.mean(null_aucs)),
        "null_auc_std": float(np.std(null_aucs)),
        "null_auc_p5": float(np.percentile(null_aucs, 5)),
        "null_auc_p95": float(np.percentile(null_aucs, 95)),
        "coefficients": {name: float(coefs[j]) for j, name in enumerate(FEATURE_NAMES)},
        "bias": float(bias),
        "n_nonzero": int(np.sum(np.abs(coefs) > 0.01)),
        "youden_threshold": float(best_thr),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "v2": v2,
    }

    return results


# =========================================================================
# PHASE 4: BOOTSTRAP OOS
# =========================================================================

def run_p4_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi, d1_str_h4):
    """P4: 500 VCBB bootstrap paths — test if AUC survives OOS."""
    print("\n" + "=" * 70)
    print(f"P4: BOOTSTRAP OOS ({N_BOOT} VCBB paths)")
    print("=" * 70)

    # Prepare bootstrap inputs
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

    # D1 regime strength for bootstrap (same for all paths)
    d1_str_pw = d1_str_h4[wi:]

    # Get best C from main analysis (use C=1.0 as default for speed)
    best_c = 1.0

    boot_aucs = []
    boot_best_p = []
    boot_navs = []
    n_skipped = 0

    for b_idx in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)

        # Regime from original D1 data (shared)
        reg_pw = regime_h4[wi:]
        n_b = len(bcl)
        breg = reg_pw[:n_b] if len(reg_pw) >= n_b else np.ones(n_b, dtype=np.bool_)
        bd1_str = d1_str_pw[:n_b] if len(d1_str_pw) >= n_b else np.zeros(n_b)

        bwi = 0

        # Compute indicators
        bef, bes, bvd, bat = _compute_indicators(bcl, bhi, blo, bvo, btb)

        # Run sim
        bnav, btrades, _ = _run_sim(bcl, bef, bes, bvd, bat, breg, bwi)
        boot_navs.append(float(bnav[-1]))

        # Extract features
        bX, by, _ = _extract_features(
            btrades, bcl, bhi, blo, bat, bef, bes, bvd, bd1_str)

        if len(by) < MIN_TRAIL_STOPS or len(np.unique(by)) < 2:
            n_skipped += 1
            continue

        # Standardize
        bXs, _, _ = _standardize(bX)

        # 10-fold AUC (faster than LOOCV for bootstrap)
        auc = _kfold_auc(bXs, by, C=best_c, k=10, rng=rng)
        boot_aucs.append(auc)

        # Best univariate p-value
        churn_mask = by == 1
        true_mask = by == 0
        best_p = 1.0
        if np.sum(churn_mask) >= 3 and np.sum(true_mask) >= 3:
            for j in range(bX.shape[1]):
                try:
                    _, pj = mannwhitneyu(bX[churn_mask, j], bX[true_mask, j],
                                         alternative='two-sided')
                    best_p = min(best_p, pj)
                except ValueError:
                    pass
        boot_best_p.append(best_p)

        if (b_idx + 1) % 100 == 0:
            print(f"    ... {b_idx + 1}/{N_BOOT} paths done ({n_skipped} skipped)")

    boot_aucs = np.array(boot_aucs)
    boot_best_p = np.array(boot_best_p)

    n_valid = len(boot_aucs)
    p_auc_gt060 = float(np.mean(boot_aucs > 0.60)) if n_valid > 0 else 0.0
    p_auc_gt055 = float(np.mean(boot_aucs > 0.55)) if n_valid > 0 else 0.0
    med_auc = float(np.median(boot_aucs)) if n_valid > 0 else 0.5

    results = {
        "n_valid": n_valid,
        "n_skipped": n_skipped,
        "auc_median": med_auc,
        "auc_p5": float(np.percentile(boot_aucs, 5)) if n_valid > 0 else 0.5,
        "auc_p95": float(np.percentile(boot_aucs, 95)) if n_valid > 0 else 0.5,
        "auc_mean": float(np.mean(boot_aucs)) if n_valid > 0 else 0.5,
        "p_auc_gt060": p_auc_gt060,
        "p_auc_gt055": p_auc_gt055,
        "best_p_median": float(np.median(boot_best_p)) if n_valid > 0 else 1.0,
        "p_bestp_lt005": float(np.mean(boot_best_p < 0.05)) if n_valid > 0 else 0.0,
    }

    v3 = med_auc > 0.55 and p_auc_gt060 > 0.30
    results["v3"] = v3

    print(f"\n  Valid paths: {n_valid}/{N_BOOT} (skipped {n_skipped})")
    print(f"  AUC: median={med_auc:.4f}, [{results['auc_p5']:.4f}, {results['auc_p95']:.4f}]")
    print(f"  P(AUC > 0.60): {p_auc_gt060:.1%}")
    print(f"  P(AUC > 0.55): {p_auc_gt055:.1%}")
    print(f"  Best univariate p: median={results['best_p_median']:.4f}, P(p<0.05)={results['p_bestp_lt005']:.1%}")
    print(f"\n  V3 (median AUC > 0.55 AND P(AUC>0.60) > 0.30): {'PASS' if v3 else 'FAIL'}")

    return results


# =========================================================================
# PHASE 5: CHURN WINDOW SENSITIVITY
# =========================================================================

def run_p5_sensitivity(cl, hi, lo, ef, es, vd, at, regime_h4, wi,
                       trades, X_base, d1_str_h4):
    """P5: Repeat P0+P2+P3 at multiple churn window sizes."""
    print("\n" + "=" * 70)
    print("P5: CHURN WINDOW SENSITIVITY")
    print("=" * 70)

    rows = []
    v_directions = []  # Track V0/V1/V2 at default window (20)

    for cw in CHURN_WINDOWS:
        print(f"\n  --- Window={cw} bars ---")

        # P0: Oracle at this window
        nav_oracle, trades_oracle, n_supp = _run_sim(
            cl, ef, es, vd, at, regime_h4, wi,
            oracle_mode=True, churn_window=cw)
        nav_base, trades_base, _ = _run_sim(
            cl, ef, es, vd, at, regime_h4, wi,
            oracle_mode=False)
        m_oracle = _metrics(nav_oracle, wi, len(trades_oracle))
        m_base = _metrics(nav_base, wi, len(trades_base))
        d_sharpe = m_oracle["sharpe"] - m_base["sharpe"]

        # Re-label features with this window
        _, y_cw = _extract_features(
            trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
            churn_window=cw)[:2]

        # Use pre-extracted features X_base (features don't change, only labels)
        if len(y_cw) != len(X_base):
            # Edge case: different number of valid trail stops
            X_cw, y_cw, _ = _extract_features(
                trades, cl, hi, lo, at, ef, es, vd, d1_str_h4,
                churn_window=cw)
        else:
            X_cw = X_base

        churn_rate = float(np.mean(y_cw == 1)) if len(y_cw) > 0 else 0.0

        # P2: Best univariate p
        best_p_bonf = 1.0
        if len(y_cw) >= 10 and len(np.unique(y_cw)) == 2:
            churn_m = y_cw == 1
            true_m = y_cw == 0
            for j in range(X_cw.shape[1]):
                try:
                    _, pj = mannwhitneyu(X_cw[churn_m, j], X_cw[true_m, j],
                                         alternative='two-sided')
                    p_bonf = min(pj * X_cw.shape[1], 1.0)
                    best_p_bonf = min(best_p_bonf, p_bonf)
                except ValueError:
                    pass

        # P3: LOOCV AUC + permutation (reduced permutations for speed)
        loocv_auc = 0.5
        perm_p = 1.0
        if len(y_cw) >= 10 and len(np.unique(y_cw)) == 2:
            Xs_cw, _, _ = _standardize(X_cw)
            loocv_auc, _ = _logistic_loocv_auc(Xs_cw, y_cw, C=1.0)

            # Quick permutation (100 shuffles for sensitivity check)
            rng = np.random.default_rng(SEED + cw)
            null_aucs = np.zeros(100)
            for k in range(100):
                null_aucs[k], _ = _logistic_loocv_auc(Xs_cw, rng.permutation(y_cw), C=1.0)
            perm_p = float((1 + np.sum(null_aucs >= loocv_auc)) / 101)

        v0_cw = d_sharpe > 0.10
        v1_cw = best_p_bonf < 0.05
        v2_cw = perm_p < 0.05 and loocv_auc > 0.60

        row = {
            "churn_window": cw,
            "churn_rate": churn_rate,
            "oracle_d_sharpe": d_sharpe,
            "best_p_bonferroni": best_p_bonf,
            "loocv_auc": loocv_auc,
            "permutation_p": perm_p,
            "v0": v0_cw,
            "v1": v1_cw,
            "v2": v2_cw,
            "n_suppressed": n_supp,
        }
        rows.append(row)
        v_directions.append((v0_cw, v1_cw, v2_cw))

        print(f"    Churn rate: {churn_rate:.1%}, Oracle d_sharpe: {d_sharpe:+.4f}, "
              f"Best p: {best_p_bonf:.4f}, AUC: {loocv_auc:.4f}, Perm p: {perm_p:.4f}")
        print(f"    V0={'P' if v0_cw else 'F'} V1={'P' if v1_cw else 'F'} V2={'P' if v2_cw else 'F'}")

    # Stability check
    n_windows = len(CHURN_WINDOWS)
    # Use the result at default window (20) as reference direction
    ref_idx = CHURN_WINDOWS.index(CHURN_WINDOW)
    ref_v0, ref_v1, ref_v2 = v_directions[ref_idx]

    stable_count = sum(1 for v0, v1, v2 in v_directions
                       if v0 == ref_v0 and v1 == ref_v1 and v2 == ref_v2)
    v4 = stable_count >= 4

    print(f"\n  Stability: {stable_count}/{n_windows} windows match reference direction")
    print(f"  V4 (stable >= 4/5): {'PASS' if v4 else 'FAIL'}")

    return {"rows": rows, "stable_count": stable_count, "v4": v4}


# =========================================================================
# SAVE RESULTS
# =========================================================================

def save_results(p0, X, y, p2, p3, p4, p5):
    """Save all results to JSON + CSV files."""
    # Master JSON
    out = {
        "oracle_ceiling": {k: v for k, v in p0.items()
                           if k not in ("baseline", "oracle")},
        "oracle_baseline": p0["baseline"],
        "oracle_result": p0["oracle"],
        "univariate": {k: v for k, v in p2.items() if k != "rows"},
        "multivariate": p3,
        "bootstrap": p4,
        "window_sensitivity": {k: v for k, v in p5.items() if k != "rows"},
    }
    with open(OUTDIR / "x13_results.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    # P1: features CSV
    with open(OUTDIR / "x13_features.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FEATURE_NAMES + ["label"])
        for i in range(len(y)):
            w.writerow([f"{X[i, j]:.6f}" for j in range(X.shape[1])] + [int(y[i])])

    # P2: univariate CSV
    if p2.get("rows"):
        with open(OUTDIR / "x13_univariate.csv", "w", newline="") as f:
            fields = ["feature", "U", "p_raw", "p_bonferroni", "cliffs_delta",
                       "effect_size", "mean_churn", "mean_true", "direction"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in p2["rows"]:
                out_row = {}
                for k, v in row.items():
                    out_row[k] = f"{v:.6f}" if isinstance(v, float) else v
                w.writerow(out_row)

    # P3: multivariate JSON
    with open(OUTDIR / "x13_multivariate.json", "w") as f:
        json.dump(p3, f, indent=2)

    # P4: bootstrap CSV
    with open(OUTDIR / "x13_bootstrap_auc.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in p4.items():
            w.writerow([k, f"{v:.6f}" if isinstance(v, float) else v])

    # P5: window sensitivity CSV
    if p5.get("rows"):
        with open(OUTDIR / "x13_window_sensitivity.csv", "w", newline="") as f:
            fields = ["churn_window", "churn_rate", "oracle_d_sharpe",
                       "best_p_bonferroni", "loocv_auc", "permutation_p",
                       "v0", "v1", "v2", "n_suppressed"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in p5["rows"]:
                out_row = {}
                for k, v in row.items():
                    if isinstance(v, float):
                        out_row[k] = f"{v:.6f}"
                    elif isinstance(v, bool):
                        out_row[k] = "True" if v else "False"
                    else:
                        out_row[k] = v
                w.writerow(out_row)

    print(f"\n  Saved to {OUTDIR}/x13_*.{{json,csv}}")


# =========================================================================
# VERDICT
# =========================================================================

def print_verdict(p0, p2, p3, p4, p5):
    """Print verdict gates and decision matrix."""
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    v0 = p0.get("v0", False)
    v0_neg = p0.get("d_sharpe", 0) < 0
    v1 = p2.get("v1", False)
    v2 = p3.get("v2", False)
    v3 = p4.get("v3", False)
    v4 = p5.get("v4", False)

    gates = [
        ("V0", f"Oracle ceiling > 0.10 Sharpe (d_sharpe={p0.get('d_sharpe', 0):+.4f})", v0),
        ("V1", f"Any feature Bonferroni p < 0.05", v1),
        ("V2", f"LOOCV AUC > 0.60 + perm p < 0.05 (AUC={p3.get('loocv_auc', 0):.4f}, p={p3.get('permutation_p', 1):.4f})", v2),
        ("V3", f"Bootstrap median AUC > 0.55 + P(AUC>0.60) > 30% (med={p4.get('auc_median', 0):.4f})", v3),
        ("V4", f"Stable across >= 4/5 windows ({p5.get('stable_count', 0)}/5)", v4),
    ]

    for gid, desc, val in gates:
        print(f"  {gid}: {desc}: {'PASS' if val else 'FAIL'}")

    # Decision matrix
    if v0_neg:
        verdict = "CHURN_IS_OPTIMAL"
    elif not v0:
        verdict = "CEILING_TOO_LOW"
    elif not v1 and not v2:
        verdict = "NO_INFORMATION"
    elif v1 and not v2:
        verdict = "WEAK_SIGNAL"
    elif v2 and not v3:
        verdict = "IN_SAMPLE_ONLY"
    elif v3 and not v4:
        verdict = "FRAGILE"
    elif v3 and v4:
        verdict = "INFORMATION_EXISTS"
    else:
        verdict = "INCONCLUSIVE"

    print(f"\n  VERDICT: {verdict}")
    return verdict


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()

    print("X13: Is Trail-Stop Churn Predictable?")
    print("=" * 70)

    # Load data (same pattern as X12)
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
    print(f"  Period: {START} to {END}, warmup={WARMUP}d")

    # Precompute indicators
    ef, es, vd, at = _compute_indicators(cl, hi, lo, vo, tb)

    # Run baseline sim
    print("\n  Running E0+EMA1D21 baseline ...")
    nav, trades, _ = _run_sim(cl, ef, es, vd, at, regime_h4, wi)
    m = _metrics(nav, wi, len(trades))
    print(f"  E0: Sharpe={m['sharpe']:.4f}, CAGR={m['cagr']:.2f}%, "
          f"MDD={m['mdd']:.2f}%, trades={m['trades']}")

    # P0: Oracle Ceiling
    p0 = run_p0_oracle(cl, ef, es, vd, at, regime_h4, wi)

    # P1: Feature Census
    X, y = run_p1_features(trades, cl, hi, lo, at, ef, es, vd, d1_str_h4)

    # P2: Univariate Predictability
    p2 = run_p2_univariate(X, y)

    # P3: Multivariate Bound
    p3 = run_p3_multivariate(X, y)

    # P4: Bootstrap OOS
    p4 = run_p4_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi, d1_str_h4)

    # P5: Window Sensitivity
    p5 = run_p5_sensitivity(cl, hi, lo, ef, es, vd, at, regime_h4, wi,
                            trades, X, d1_str_h4)

    # Save
    save_results(p0, X, y, p2, p3, p4, p5)

    # Verdict
    verdict = print_verdict(p0, p2, p3, p4, p5)

    elapsed = time.time() - t_start
    print(f"\nX13 BENCHMARK COMPLETE — {elapsed:.0f}s — VERDICT: {verdict}")


if __name__ == "__main__":
    main()
