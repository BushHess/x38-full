#!/usr/bin/env python3
"""X21 Research — Conviction-Based Position Sizing: Entry Feature Scoring

Can entry-time observable features predict trade-level returns with sufficient
IC (information coefficient > 0.05) to justify conviction-based sizing over
fixed sizing, with >= 2% CAGR improvement?

Features at entry:
  vdo_value:     continuous VDO at entry bar
  ema_spread:    (ema_fast - ema_slow) / ema_slow
  atr_pctl:      ATR percentile within trailing 252-bar window
  d1_regime_str: (close - ema21d) / ema21d

Sizing:
  z = (prediction - mean) / std
  f_trade = f_base * clip(1 + beta * z, f_min/f_base, f_max/f_base)

Tests:
  T-1: IC measurement (abort gate: cross-validated IC < 0.05)
  T0:  Sizing sweep (8 configs = 4 beta x 2 feature_set)
  T1:  Nested WFO (4 expanding folds)
  T2:  Bootstrap (500 VCBB)
  T3:  Jackknife (leave-year-out)
  T4:  PSR with DOF correction
  T5:  Comparison table

Gates:
  ABORT: T-1 cross-validated IC < 0.05
  G0: T0 best CAGR > baseline + 2pp
  G1: T1 WFO >= 3/4 AND mean d_cagr > 0
  G2: T2 P(d_cagr > 0) > 60%
  G3: T2 median d_mdd <= +5pp
  G4: T3 <= 2 negative jackknife (on d_cagr)
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
from scipy.stats import spearmanr

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

# E5 robust ATR
RATR_P = 20
RATR_Q = 0.90
RATR_LB = 100

CPS = SCENARIOS["harsh"].per_side_bps / 10_000.0

# Sizing
F_BASE = 0.30
F_MIN = 0.10
F_MAX = 0.50
BETA_GRID = [0.25, 0.50, 0.75, 1.0]
FEATURE_SETS = ["all_4", "top_2"]
L2_ALPHA = 1.0

# IC
IC_ABORT = 0.05
IC_CV_FOLDS = 5

# WFO
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

FEATURE_NAMES = ["vdo_value", "ema_spread", "atr_pctl", "d1_regime_str"]

OUTDIR = Path(__file__).resolve().parent


# =========================================================================
# INDICATORS (E5: robust ATR for BTC)
# =========================================================================

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _robust_atr(high, low, close, cap_q=RATR_Q, cap_lb=RATR_LB, period=RATR_P):
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
    at = _robust_atr(hi, lo, cl)  # E5 for BTC
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
# SIM: E5+EMA1D21 baseline (fixed f)
# =========================================================================

def _run_sim_fixed(cl, ef, es, vd, at, regime_h4, wi,
                   f=F_BASE, trail_mult=TRAIL, cps=CPS):
    """E5+EMA1D21 with fixed fractional position f. Returns (nav, trades)."""
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
                alloc = cash * f  # allocate fraction f of total NAV
                bq = alloc / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash -= entry_cost
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
                cash += received
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
# SIM: E5+EMA1D21 with variable sizing per trade
# =========================================================================

def _run_sim_variable(cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                      model_w, model_mu, model_std, beta,
                      feature_mask=None,
                      trail_mult=TRAIL, cps=CPS):
    """E5+EMA1D21 with per-trade conviction sizing.

    At entry, extract features, predict return quality, size accordingly.
    feature_mask: boolean array indicating which features to use (for top_2).
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
    trade_fs = []  # per-trade f values

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp
                entry_bar = i

                # Extract features at entry bar (i-1, the signal bar)
                feat = _extract_entry_features(i - 1, cl, ef, es, vd, at, d1_str_h4)
                if feature_mask is not None:
                    feat = feat[feature_mask]
                # Predict
                feat_s = (feat - model_mu) / model_std
                pred = float(np.dot(model_w, feat_s))
                # z-score (model predictions have mean ~0 for centered features)
                # We use raw prediction as z since model is trained on standardized features
                z = pred  # already centered approximately
                f_trade = F_BASE * np.clip(1 + beta * z, F_MIN / F_BASE, F_MAX / F_BASE)
                f_trade = float(np.clip(f_trade, F_MIN, F_MAX))

                total_nav = cash  # NAV at entry time (not in position)
                alloc = total_nav * f_trade
                bq = alloc / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash -= entry_cost
                inp = True
                pk = p
                pk_bar = i
                trade_fs.append(f_trade)
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
                cash += received
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
    return nav, trades, trade_fs


# =========================================================================
# ENTRY FEATURE EXTRACTION
# =========================================================================

def _extract_entry_features(i, cl, ef, es, vd, at, d1_str_h4):
    """Extract 4 features at entry bar i."""
    # f1: vdo_value (continuous)
    f1 = float(vd[i])

    # f2: ema_spread = (ema_fast - ema_slow) / ema_slow
    f2 = (ef[i] - es[i]) / es[i] if abs(es[i]) > 1e-12 else 0.0

    # f3: atr_pctl = percentile of ATR within trailing 252-bar window
    atr_start = max(0, i - 251)
    atr_window = at[atr_start:i + 1]
    valid_atr = atr_window[~np.isnan(atr_window)]
    if len(valid_atr) > 1:
        f3 = float(np.sum(valid_atr <= at[i])) / len(valid_atr)
    else:
        f3 = 0.5

    # f4: d1_regime_str = (close - ema21d) / ema21d
    f4 = float(d1_str_h4[i])

    return np.array([f1, f2, f3, f4])


def _extract_trade_features_and_returns(trades, cl, ef, es, vd, at, d1_str_h4, cps=CPS):
    """Extract entry features and log-returns for all trades."""
    n = len(cl)
    features = []
    returns = []
    for t in trades:
        eb = t["entry_bar"]
        # Signal bar is eb - 1 (entry_bar is the bar AFTER signal)
        sig_bar = eb - 1
        if sig_bar < 0 or sig_bar >= n:
            continue
        if math.isnan(at[sig_bar]) or math.isnan(ef[sig_bar]):
            continue
        feat = _extract_entry_features(sig_bar, cl, ef, es, vd, at, d1_str_h4)
        # log return adjusted for cost
        if t["entry_px"] > 0 and t["exit_px"] > 0:
            log_ret = math.log(t["exit_px"] / t["entry_px"]) - 2 * cps
        else:
            log_ret = 0.0
        features.append(feat)
        returns.append(log_ret)
    return np.array(features), np.array(returns)


# =========================================================================
# RIDGE MODEL
# =========================================================================

def _fit_ridge(X, y, alpha=L2_ALPHA):
    """L2-penalized linear regression (Ridge). Returns weight vector."""
    n, d = X.shape
    # Normal equation: w = (X^T X + alpha I)^{-1} X^T y
    XtX = X.T @ X
    Xty = X.T @ y
    w = np.linalg.solve(XtX + alpha * np.eye(d), Xty)
    return w


def _standardize(X):
    mu = np.mean(X, axis=0)
    std = np.std(X, axis=0, ddof=0)
    std[std < 1e-12] = 1.0
    return (X - mu) / std, mu, std


def _train_ridge(X, y, alpha=L2_ALPHA):
    """Standardize features and fit Ridge. Returns (weights, mu, std)."""
    Xs, mu, std = _standardize(X)
    w = _fit_ridge(Xs, y, alpha)
    return w, mu, std


# =========================================================================
# T-1: IC MEASUREMENT
# =========================================================================

def run_t_minus_1(trades, cl, ef, es, vd, at, d1_str_h4):
    """IC measurement: abort gate."""
    print("T-1: IC Measurement")
    X, y = _extract_trade_features_and_returns(trades, cl, ef, es, vd, at, d1_str_h4)
    n_trades = len(y)
    print(f"  Trades with features: {n_trades}")

    if n_trades < 20:
        print("  ABORT: too few trades for IC measurement")
        return {"abort": True, "reason": "too_few_trades", "n_trades": n_trades}

    # Full-sample IC
    Xs, mu, std = _standardize(X)
    w = _fit_ridge(Xs, y)
    preds = Xs @ w
    ic_full, ic_p = spearmanr(preds, y)
    print(f"  Full-sample IC: {ic_full:.4f} (p={ic_p:.4f})")

    # Per-feature IC
    per_feature_ic = {}
    for j, fname in enumerate(FEATURE_NAMES):
        rho, p_val = spearmanr(X[:, j], y)
        per_feature_ic[fname] = {"ic": float(rho), "p": float(p_val)}
        print(f"    {fname}: IC={rho:.4f} (p={p_val:.4f})")

    # Rank features by |IC| for top_2 selection
    abs_ics = [(abs(per_feature_ic[f]["ic"]), j, f) for j, f in enumerate(FEATURE_NAMES)]
    abs_ics.sort(reverse=True)
    top_2_indices = sorted([abs_ics[0][1], abs_ics[1][1]])
    top_2_names = [FEATURE_NAMES[j] for j in top_2_indices]
    print(f"  Top 2 by |IC|: {top_2_names}")

    # Cross-validated IC (5-fold)
    rng = np.random.default_rng(SEED)
    idx = np.arange(n_trades)
    rng.shuffle(idx)
    cv_ics = []
    fold_size = n_trades // IC_CV_FOLDS
    for fold in range(IC_CV_FOLDS):
        s = fold * fold_size
        e = s + fold_size if fold < IC_CV_FOLDS - 1 else n_trades
        val_idx = idx[s:e]
        train_idx = np.concatenate([idx[:s], idx[e:]])
        X_tr, y_tr = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]
        Xs_tr, mu_tr, std_tr = _standardize(X_tr)
        w_tr = _fit_ridge(Xs_tr, y_tr)
        Xs_val = (X_val - mu_tr) / std_tr
        preds_val = Xs_val @ w_tr
        if len(preds_val) > 2:
            rho_val, _ = spearmanr(preds_val, y_val)
            cv_ics.append(float(rho_val))
    cv_ic = float(np.mean(cv_ics)) if cv_ics else 0.0
    print(f"  Cross-validated IC (5-fold): {cv_ic:.4f}")

    abort = cv_ic < IC_ABORT
    if abort:
        print(f"  ABORT: CV IC {cv_ic:.4f} < {IC_ABORT}")
    else:
        print(f"  PASS: CV IC {cv_ic:.4f} >= {IC_ABORT}")

    result = {
        "n_trades": n_trades,
        "ic_full": float(ic_full),
        "ic_p": float(ic_p),
        "cv_ic": cv_ic,
        "per_feature_ic": per_feature_ic,
        "top_2_indices": top_2_indices,
        "top_2_names": top_2_names,
        "abort": abort,
    }
    # Write CSV
    with open(OUTDIR / "x21_ic.csv", "w", newline="") as f:
        w_csv = csv.writer(f)
        w_csv.writerow(["feature", "ic", "p_value"])
        for fname in FEATURE_NAMES:
            d = per_feature_ic[fname]
            w_csv.writerow([fname, f"{d['ic']:.6f}", f"{d['p']:.6f}"])
        w_csv.writerow(["full_model", f"{ic_full:.6f}", f"{ic_p:.6f}"])
        w_csv.writerow(["cv_mean", f"{cv_ic:.6f}", ""])
    return result


# =========================================================================
# T0: SIZING SWEEP (8 configs)
# =========================================================================

def run_t0(trades, cl, ef, es, vd, at, regime_h4, d1_str_h4, wi, top_2_indices):
    """Sizing sweep: 4 beta x 2 feature_set = 8 configs."""
    print("\nT0: Sizing Sweep (8 configs)")

    # Baseline: fixed f
    nav_base, trades_base = _run_sim_fixed(cl, ef, es, vd, at, regime_h4, wi)
    m_base = _metrics(nav_base, wi, len(trades_base))
    print(f"  Baseline (f={F_BASE}): Sh={m_base['sharpe']:.4f}, CAGR={m_base['cagr']:.2f}%, "
          f"MDD={m_base['mdd']:.2f}%, trades={m_base['trades']}")

    # Extract features and train model on full sample
    X, y = _extract_trade_features_and_returns(trades, cl, ef, es, vd, at, d1_str_h4)
    top_2_mask = np.zeros(4, dtype=bool)
    top_2_mask[top_2_indices] = True

    results = []
    for feat_set in FEATURE_SETS:
        if feat_set == "all_4":
            X_use = X
            mask = None
        else:
            X_use = X[:, top_2_mask]
            mask = top_2_mask
        w, mu, std = _train_ridge(X_use, y)

        for beta in BETA_GRID:
            nav_v, trades_v, fs = _run_sim_variable(
                cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                w, mu, std, beta, feature_mask=mask)
            m_v = _metrics(nav_v, wi, len(trades_v))
            avg_f = float(np.mean(fs)) if fs else F_BASE
            d_cagr = m_v["cagr"] - m_base["cagr"]
            d_sharpe = m_v["sharpe"] - m_base["sharpe"]
            row = {
                "feature_set": feat_set, "beta": beta,
                "sharpe": m_v["sharpe"], "cagr": m_v["cagr"],
                "mdd": m_v["mdd"], "trades": m_v["trades"],
                "avg_f": avg_f,
                "d_cagr": d_cagr, "d_sharpe": d_sharpe,
            }
            results.append(row)
            print(f"  {feat_set} β={beta:.2f}: Sh={m_v['sharpe']:.4f}, CAGR={m_v['cagr']:.2f}%, "
                  f"MDD={m_v['mdd']:.2f}%, avg_f={avg_f:.3f}, Δcagr={d_cagr:+.2f}pp")

    # G0: best CAGR > baseline + 2pp
    best_d_cagr = max(r["d_cagr"] for r in results)
    g0_pass = best_d_cagr > 2.0
    print(f"  Best Δcagr: {best_d_cagr:+.2f}pp → G0: {'PASS' if g0_pass else 'FAIL'}")

    # Write CSV
    with open(OUTDIR / "x21_sweep.csv", "w", newline="") as f:
        w_csv = csv.writer(f)
        w_csv.writerow(["feature_set", "beta", "sharpe", "cagr", "mdd", "trades",
                         "avg_f", "d_cagr", "d_sharpe"])
        for r in results:
            w_csv.writerow([r["feature_set"], r["beta"],
                            f"{r['sharpe']:.4f}", f"{r['cagr']:.2f}", f"{r['mdd']:.2f}",
                            r["trades"], f"{r['avg_f']:.4f}",
                            f"{r['d_cagr']:.2f}", f"{r['d_sharpe']:.4f}"])

    return {
        "baseline": m_base,
        "configs": results,
        "best_d_cagr": best_d_cagr,
        "g0_pass": g0_pass,
    }


# =========================================================================
# T1: NESTED WALK-FORWARD VALIDATION (4 folds)
# =========================================================================

def run_t1(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4, h4_ct, wi,
           top_2_indices):
    """WFO: expanding folds, select best (beta, feature_set) by training CAGR."""
    print("\nT1: Nested Walk-Forward Validation")

    top_2_mask = np.zeros(4, dtype=bool)
    top_2_mask[top_2_indices] = True

    fold_results = []
    for fold_idx, (train_end_str, test_start_str, test_end_str) in enumerate(WFO_FOLDS):
        train_end = _date_to_bar_idx(h4_ct, train_end_str)
        test_start = _date_to_bar_idx(h4_ct, test_start_str)
        test_end = _date_to_bar_idx(h4_ct, test_end_str)

        # --- Baseline on full data, measure test window ---
        nav_base, trades_base = _run_sim_fixed(cl, ef, es, vd, at, regime_h4, wi)
        m_base_test = _metrics_window(nav_base, test_start, test_end + 1,
                                       sum(1 for t in trades_base if test_start <= t["entry_bar"] < test_end))

        # --- Train model on training trades ---
        nav_tr, trades_tr = _run_sim_fixed(
            cl[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], at[:train_end + 1], regime_h4[:train_end + 1], wi)
        X_tr, y_tr = _extract_trade_features_and_returns(
            trades_tr, cl[:train_end + 1], ef[:train_end + 1], es[:train_end + 1],
            vd[:train_end + 1], at[:train_end + 1], d1_str_h4[:train_end + 1])

        if len(y_tr) < 10:
            print(f"  Fold {fold_idx+1}: too few training trades ({len(y_tr)}), skip")
            fold_results.append({
                "fold": fold_idx + 1, "year": test_start_str[:4],
                "d_cagr": 0.0, "d_sharpe": 0.0, "d_mdd": 0.0,
                "win": False, "best_beta": 0.0, "best_feat": "all_4",
            })
            continue

        # --- Select best (beta, feature_set) by training CAGR ---
        best_train_cagr = -999.0
        best_beta = BETA_GRID[0]
        best_feat = "all_4"

        for feat_set in FEATURE_SETS:
            if feat_set == "all_4":
                X_use = X_tr
                mask = None
            else:
                X_use = X_tr[:, top_2_mask]
                mask = top_2_mask
            w, mu, std = _train_ridge(X_use, y_tr)

            for beta in BETA_GRID:
                nav_v, trades_v, _ = _run_sim_variable(
                    cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                    w, mu, std, beta, feature_mask=mask)
                m_v_train = _metrics_window(nav_v, wi, train_end + 1)
                if m_v_train["cagr"] > best_train_cagr:
                    best_train_cagr = m_v_train["cagr"]
                    best_beta = beta
                    best_feat = feat_set

        # --- Evaluate best config on test period ---
        if best_feat == "all_4":
            X_use = X_tr
            mask = None
        else:
            X_use = X_tr[:, top_2_mask]
            mask = top_2_mask
        w_best, mu_best, std_best = _train_ridge(X_use, y_tr)

        nav_v, trades_v, _ = _run_sim_variable(
            cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            w_best, mu_best, std_best, best_beta, feature_mask=mask)
        m_v_test = _metrics_window(nav_v, test_start, test_end + 1,
                                    sum(1 for t in trades_v if test_start <= t["entry_bar"] < test_end))

        d_cagr = m_v_test["cagr"] - m_base_test["cagr"]
        d_sharpe = m_v_test["sharpe"] - m_base_test["sharpe"]
        d_mdd = m_v_test["mdd"] - m_base_test["mdd"]
        win = d_cagr > 0

        fold_results.append({
            "fold": fold_idx + 1, "year": test_start_str[:4],
            "d_cagr": d_cagr, "d_sharpe": d_sharpe, "d_mdd": d_mdd,
            "win": win, "best_beta": best_beta, "best_feat": best_feat,
            "base_cagr": m_base_test["cagr"], "var_cagr": m_v_test["cagr"],
            "base_sharpe": m_base_test["sharpe"], "var_sharpe": m_v_test["sharpe"],
        })
        print(f"  Fold {fold_idx+1} ({test_start_str[:4]}): β={best_beta}, feat={best_feat}, "
              f"Δcagr={d_cagr:+.2f}pp, Δsharpe={d_sharpe:+.4f}, {'WIN' if win else 'LOSE'}")

    wins = sum(1 for f in fold_results if f["win"])
    mean_d_cagr = float(np.mean([f["d_cagr"] for f in fold_results]))
    g1_pass = wins >= 3 and mean_d_cagr > 0
    print(f"  WFO wins: {wins}/4, mean Δcagr: {mean_d_cagr:+.2f}pp → G1: {'PASS' if g1_pass else 'FAIL'}")

    # Consensus beta/feat
    betas = [f["best_beta"] for f in fold_results]
    feats = [f["best_feat"] for f in fold_results]
    beta_counts = Counter(betas)
    feat_counts = Counter(feats)
    consensus_beta = beta_counts.most_common(1)[0][0]
    consensus_feat = feat_counts.most_common(1)[0][0]
    print(f"  Consensus: β={consensus_beta}, feat={consensus_feat}")

    # Write CSV
    with open(OUTDIR / "x21_wfo.csv", "w", newline="") as f:
        w_csv = csv.writer(f)
        w_csv.writerow(["fold", "year", "best_beta", "best_feat",
                         "base_cagr", "var_cagr", "d_cagr", "d_sharpe", "d_mdd", "win"])
        for r in fold_results:
            w_csv.writerow([r["fold"], r["year"], r.get("best_beta", ""),
                            r.get("best_feat", ""),
                            f"{r.get('base_cagr', 0):.2f}", f"{r.get('var_cagr', 0):.2f}",
                            f"{r['d_cagr']:.2f}", f"{r['d_sharpe']:.4f}",
                            f"{r['d_mdd']:.2f}", r["win"]])

    return {
        "folds": fold_results,
        "wins": wins,
        "mean_d_cagr": mean_d_cagr,
        "g1_pass": g1_pass,
        "consensus_beta": consensus_beta,
        "consensus_feat": consensus_feat,
    }


# =========================================================================
# T2: BOOTSTRAP (500 VCBB)
# =========================================================================

def run_t2(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4, wi,
           consensus_beta, consensus_feat, top_2_indices, trades_full):
    """Bootstrap: 500 VCBB paths, retrain model per path."""
    print(f"\nT2: Bootstrap (500 VCBB) β={consensus_beta}, feat={consensus_feat}")

    top_2_mask = np.zeros(4, dtype=bool)
    top_2_mask[top_2_indices] = True

    # Full-data model for fallback
    X_full, y_full = _extract_trade_features_and_returns(
        trades_full, cl, ef, es, vd, at, d1_str_h4)
    if consensus_feat == "all_4":
        mask = None
        X_use_full = X_full
    else:
        mask = top_2_mask
        X_use_full = X_full[:, mask]
    w_full, mu_full, std_full = _train_ridge(X_use_full, y_full)

    # Prepare VCBB
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

    d_cagrs = []
    d_sharpes = []
    d_mdds = []
    boot_rows = []

    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        n_b = len(bcl)
        breg = regime_pw[:n_b] if len(regime_pw) >= n_b else np.ones(n_b, dtype=np.bool_)
        bd1 = d1_str_pw[:n_b] if len(d1_str_pw) >= n_b else np.zeros(n_b)
        bef, bes, bvd, bat = _compute_indicators(bcl, bhi, blo, bvo, btb)

        # Baseline: fixed f
        bnav_base, btrades_base = _run_sim_fixed(bcl, bef, bes, bvd, bat, breg, 0)
        bm_base = _metrics(bnav_base, 0, len(btrades_base))

        # Train model on first 60% of bootstrap data
        te = int(n_b * 0.6)
        _, btr = _run_sim_fixed(
            bcl[:te], bef[:te], bes[:te], bvd[:te], bat[:te], breg[:te], 0)
        bX, by = _extract_trade_features_and_returns(
            btr, bcl[:te], bef[:te], bes[:te], bvd[:te], bat[:te], bd1[:te])

        if len(by) >= 10:
            if mask is not None:
                bX_use = bX[:, mask]
            else:
                bX_use = bX
            bw, bmu, bstd = _train_ridge(bX_use, by)
        else:
            bw, bmu, bstd = w_full, mu_full, std_full

        # Variable sizing on full bootstrap path
        bnav_v, btrades_v, _ = _run_sim_variable(
            bcl, bef, bes, bvd, bat, breg, bd1, 0,
            bw, bmu, bstd, consensus_beta, feature_mask=mask)
        bm_v = _metrics(bnav_v, 0, len(btrades_v))

        d_cagr = bm_v["cagr"] - bm_base["cagr"]
        d_sharpe = bm_v["sharpe"] - bm_base["sharpe"]
        d_mdd = bm_v["mdd"] - bm_base["mdd"]
        d_cagrs.append(d_cagr)
        d_sharpes.append(d_sharpe)
        d_mdds.append(d_mdd)

        boot_rows.append({
            "path": b,
            "base_sharpe": bm_base["sharpe"], "var_sharpe": bm_v["sharpe"],
            "base_cagr": bm_base["cagr"], "var_cagr": bm_v["cagr"],
            "d_cagr": d_cagr, "d_sharpe": d_sharpe, "d_mdd": d_mdd,
        })

        if (b + 1) % 100 == 0:
            print(f"    ... {b + 1}/{N_BOOT}")

    d_cagrs = np.array(d_cagrs)
    d_sharpes = np.array(d_sharpes)
    d_mdds = np.array(d_mdds)

    p_cagr_gt0 = float(np.mean(d_cagrs > 0))
    med_d_mdd = float(np.median(d_mdds))

    g2_pass = p_cagr_gt0 > 0.60
    g3_pass = med_d_mdd <= 5.0

    print(f"  P(Δcagr > 0) = {p_cagr_gt0:.3f} → G2: {'PASS' if g2_pass else 'FAIL'}")
    print(f"  Median Δmdd = {med_d_mdd:+.2f}pp → G3: {'PASS' if g3_pass else 'FAIL'}")
    print(f"  Median Δcagr = {float(np.median(d_cagrs)):+.2f}pp")
    print(f"  Median Δsharpe = {float(np.median(d_sharpes)):+.4f}")

    # Write CSV
    with open(OUTDIR / "x21_bootstrap.csv", "w", newline="") as f:
        w_csv = csv.writer(f)
        w_csv.writerow(["path", "base_cagr", "var_cagr", "d_cagr", "d_sharpe", "d_mdd"])
        for r in boot_rows:
            w_csv.writerow([r["path"],
                            f"{r['base_cagr']:.2f}", f"{r['var_cagr']:.2f}",
                            f"{r['d_cagr']:.2f}", f"{r['d_sharpe']:.4f}",
                            f"{r['d_mdd']:.2f}"])

    return {
        "p_cagr_gt0": p_cagr_gt0,
        "med_d_mdd": med_d_mdd,
        "med_d_cagr": float(np.median(d_cagrs)),
        "med_d_sharpe": float(np.median(d_sharpes)),
        "g2_pass": g2_pass,
        "g3_pass": g3_pass,
    }


# =========================================================================
# T3: JACKKNIFE (leave-year-out)
# =========================================================================

def run_t3(cl, ef, es, vd, at, regime_h4, d1_str_h4, h4_ct, wi,
           consensus_beta, consensus_feat, top_2_indices, trades_full):
    """Jackknife: leave one year out, measure d_cagr."""
    print(f"\nT3: Jackknife (leave-year-out)")

    top_2_mask = np.zeros(4, dtype=bool)
    top_2_mask[top_2_indices] = True
    mask = top_2_mask if consensus_feat == "top_2" else None

    jk_results = []
    n_negative = 0

    for year in JK_YEARS:
        year_start = _date_to_bar_idx(h4_ct, f"{year}-01-01")
        year_end = _date_to_bar_idx(h4_ct, f"{year}-12-31")

        # Baseline on full data
        nav_base, trades_base = _run_sim_fixed(cl, ef, es, vd, at, regime_h4, wi)
        m_base = _metrics_window(nav_base, year_start, year_end + 1)

        # Train model excluding this year's trades
        train_trades = [t for t in trades_full
                        if not (year_start <= t["entry_bar"] <= year_end)]
        X_jk, y_jk = _extract_trade_features_and_returns(
            train_trades, cl, ef, es, vd, at, d1_str_h4)

        if len(y_jk) < 10:
            jk_results.append({"year": year, "d_cagr": 0.0, "d_sharpe": 0.0, "negative": False})
            continue

        X_use = X_jk[:, mask] if mask is not None else X_jk
        w, mu, std = _train_ridge(X_use, y_jk)

        nav_v, trades_v, _ = _run_sim_variable(
            cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
            w, mu, std, consensus_beta, feature_mask=mask)
        m_v = _metrics_window(nav_v, year_start, year_end + 1)

        d_cagr = m_v["cagr"] - m_base["cagr"]
        d_sharpe = m_v["sharpe"] - m_base["sharpe"]
        negative = d_cagr < 0
        if negative:
            n_negative += 1

        jk_results.append({
            "year": year, "d_cagr": d_cagr, "d_sharpe": d_sharpe,
            "negative": negative,
            "base_cagr": m_base["cagr"], "var_cagr": m_v["cagr"],
        })
        print(f"  {year}: Δcagr={d_cagr:+.2f}pp, Δsharpe={d_sharpe:+.4f} "
              f"{'[NEGATIVE]' if negative else ''}")

    g4_pass = n_negative <= 2
    print(f"  Negative folds: {n_negative}/{len(JK_YEARS)} → G4: {'PASS' if g4_pass else 'FAIL'}")

    # Write CSV
    with open(OUTDIR / "x21_jackknife.csv", "w", newline="") as f:
        w_csv = csv.writer(f)
        w_csv.writerow(["year", "base_cagr", "var_cagr", "d_cagr", "d_sharpe", "negative"])
        for r in jk_results:
            w_csv.writerow([r["year"], f"{r.get('base_cagr', 0):.2f}",
                            f"{r.get('var_cagr', 0):.2f}",
                            f"{r['d_cagr']:.2f}", f"{r['d_sharpe']:.4f}", r["negative"]])

    return {
        "results": jk_results,
        "n_negative": n_negative,
        "g4_pass": g4_pass,
    }


# =========================================================================
# T4: PSR WITH DOF CORRECTION
# =========================================================================

def run_t4(cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
           consensus_beta, consensus_feat, top_2_indices, trades_full):
    """PSR: DOF-corrected probabilistic Sharpe ratio."""
    print("\nT4: PSR with DOF Correction")

    top_2_mask = np.zeros(4, dtype=bool)
    top_2_mask[top_2_indices] = True
    mask = top_2_mask if consensus_feat == "top_2" else None

    # Baseline
    nav_base, _ = _run_sim_fixed(cl, ef, es, vd, at, regime_h4, wi)
    m_base = _metrics(nav_base, wi)
    n_ret = len(nav_base[wi:]) - 1

    # Variable sizing with full-sample model
    X_full, y_full = _extract_trade_features_and_returns(
        trades_full, cl, ef, es, vd, at, d1_str_h4)
    X_use = X_full[:, mask] if mask is not None else X_full
    w, mu, std = _train_ridge(X_use, y_full)

    nav_v, _, _ = _run_sim_variable(
        cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
        w, mu, std, consensus_beta, feature_mask=mask)
    m_v = _metrics(nav_v, wi)

    # DOF correction
    eff_dof = E0_EFFECTIVE_DOF + 1  # +1 for beta
    n_eff = max(3, int(n_ret / (eff_dof / E0_EFFECTIVE_DOF)))

    psr_base = _psr(m_base["sharpe"], n_ret)
    psr_v = _psr(m_v["sharpe"], n_eff)

    g5_pass = psr_v > 0.95
    print(f"  Baseline: Sh={m_base['sharpe']:.4f}, PSR={psr_base:.4f} (n={n_ret})")
    print(f"  Variable: Sh={m_v['sharpe']:.4f}, PSR={psr_v:.4f} (n_eff={n_eff}, DOF={eff_dof:.2f})")
    print(f"  G5: {'PASS' if g5_pass else 'FAIL'}")

    return {
        "baseline_sharpe": m_base["sharpe"],
        "variable_sharpe": m_v["sharpe"],
        "psr_base": psr_base,
        "psr_variable": psr_v,
        "n_ret": n_ret,
        "n_eff": n_eff,
        "eff_dof": eff_dof,
        "g5_pass": g5_pass,
    }


# =========================================================================
# T5: COMPARISON TABLE
# =========================================================================

def run_t5(cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
           top_2_indices, trades_full):
    """Final comparison table: baseline vs best configs."""
    print("\nT5: Comparison Table")

    top_2_mask = np.zeros(4, dtype=bool)
    top_2_mask[top_2_indices] = True

    # Baseline
    nav_base, trades_base = _run_sim_fixed(cl, ef, es, vd, at, regime_h4, wi)
    m_base = _metrics(nav_base, wi, len(trades_base))

    X_full, y_full = _extract_trade_features_and_returns(
        trades_full, cl, ef, es, vd, at, d1_str_h4)

    rows = [{
        "strategy": f"E5+EMA1D21 (f={F_BASE} fixed)",
        "sharpe": m_base["sharpe"], "cagr": m_base["cagr"],
        "mdd": m_base["mdd"], "trades": m_base["trades"], "avg_f": F_BASE,
    }]

    for feat_set in FEATURE_SETS:
        mask = top_2_mask if feat_set == "top_2" else None
        X_use = X_full[:, mask] if mask is not None else X_full
        w, mu, std = _train_ridge(X_use, y_full)

        for beta in BETA_GRID:
            nav_v, trades_v, fs = _run_sim_variable(
                cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                w, mu, std, beta, feature_mask=mask)
            m_v = _metrics(nav_v, wi, len(trades_v))
            avg_f = float(np.mean(fs)) if fs else F_BASE
            rows.append({
                "strategy": f"X21 β={beta} {feat_set}",
                "sharpe": m_v["sharpe"], "cagr": m_v["cagr"],
                "mdd": m_v["mdd"], "trades": m_v["trades"], "avg_f": avg_f,
            })

    # Write CSV
    with open(OUTDIR / "x21_comparison.csv", "w", newline="") as f:
        w_csv = csv.writer(f)
        w_csv.writerow(["strategy", "sharpe", "cagr", "mdd", "trades", "avg_f"])
        for r in rows:
            w_csv.writerow([r["strategy"], f"{r['sharpe']:.4f}", f"{r['cagr']:.2f}",
                            f"{r['mdd']:.2f}", r["trades"], f"{r['avg_f']:.4f}"])

    print("  Strategy                          | Sharpe | CAGR    | MDD     | Trades | Avg f")
    print("  " + "-" * 85)
    for r in rows:
        print(f"  {r['strategy']:<35s} | {r['sharpe']:6.4f} | {r['cagr']:6.2f}% | "
              f"{r['mdd']:6.2f}% | {r['trades']:6d} | {r['avg_f']:.4f}")

    return rows


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0_wall = time.time()
    print("=" * 70)
    print("X21: Conviction-Based Position Sizing — Entry Feature Scoring")
    print("=" * 70)

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

    # --- Compute indicators ---
    ef, es, vd, at = _compute_indicators(cl, hi, lo, vo, tb)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)
    d1_str_h4 = _compute_d1_regime_str(h4_ct, d1_cl, d1_ct)

    # --- Run baseline to get trades ---
    print("\nRunning E5+EMA1D21 baseline...")
    nav_base, trades_base = _run_sim_fixed(cl, ef, es, vd, at, regime_h4, wi)
    m_base = _metrics(nav_base, wi, len(trades_base))
    print(f"  Baseline: Sh={m_base['sharpe']:.4f}, CAGR={m_base['cagr']:.2f}%, "
          f"MDD={m_base['mdd']:.2f}%, trades={m_base['trades']}")

    results = {"config": {
        "f_base": F_BASE, "f_min": F_MIN, "f_max": F_MAX,
        "l2_alpha": L2_ALPHA, "beta_grid": BETA_GRID,
        "n_boot": N_BOOT, "seed": SEED,
    }}

    # === T-1: IC Measurement ===
    ic_result = run_t_minus_1(trades_base, cl, ef, es, vd, at, d1_str_h4)
    results["t_minus_1"] = ic_result

    if ic_result["abort"]:
        results["verdict"] = "CLOSE"
        results["verdict_reason"] = f"ABORT: CV IC = {ic_result['cv_ic']:.4f} < {IC_ABORT}"
        results["gates"] = {"ABORT": True}
        _write_results(results, t0_wall)
        return

    top_2_indices = ic_result["top_2_indices"]

    # === T0: Sizing Sweep ===
    t0_result = run_t0(trades_base, cl, ef, es, vd, at, regime_h4, d1_str_h4, wi, top_2_indices)
    results["t0"] = {
        "baseline": t0_result["baseline"],
        "best_d_cagr": t0_result["best_d_cagr"],
        "g0_pass": t0_result["g0_pass"],
    }

    if not t0_result["g0_pass"]:
        results["verdict"] = "CLOSE"
        results["verdict_reason"] = f"G0 FAIL: best Δcagr = {t0_result['best_d_cagr']:+.2f}pp < +2.0pp"
        results["gates"] = {"ABORT": False, "G0": False}
        _write_results(results, t0_wall)
        return

    # === T1: WFO ===
    t1_result = run_t1(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4,
                       h4_ct, wi, top_2_indices)
    results["t1"] = {
        "wins": t1_result["wins"],
        "mean_d_cagr": t1_result["mean_d_cagr"],
        "g1_pass": t1_result["g1_pass"],
        "consensus_beta": t1_result["consensus_beta"],
        "consensus_feat": t1_result["consensus_feat"],
        "folds": t1_result["folds"],
    }

    consensus_beta = t1_result["consensus_beta"]
    consensus_feat = t1_result["consensus_feat"]

    # === T2: Bootstrap ===
    t2_result = run_t2(cl, hi, lo, vo, tb, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                       consensus_beta, consensus_feat, top_2_indices, trades_base)
    results["t2"] = t2_result

    # === T3: Jackknife ===
    t3_result = run_t3(cl, ef, es, vd, at, regime_h4, d1_str_h4, h4_ct, wi,
                       consensus_beta, consensus_feat, top_2_indices, trades_base)
    results["t3"] = {
        "n_negative": t3_result["n_negative"],
        "g4_pass": t3_result["g4_pass"],
        "results": t3_result["results"],
    }

    # === T4: PSR ===
    t4_result = run_t4(cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                       consensus_beta, consensus_feat, top_2_indices, trades_base)
    results["t4"] = t4_result

    # === T5: Comparison Table ===
    t5_rows = run_t5(cl, ef, es, vd, at, regime_h4, d1_str_h4, wi,
                     top_2_indices, trades_base)
    results["t5"] = t5_rows

    # === Verdict ===
    gates = {
        "ABORT": False,
        "G0": t0_result["g0_pass"],
        "G1": t1_result["g1_pass"],
        "G2": t2_result["g2_pass"],
        "G3": t2_result["g3_pass"],
        "G4": t3_result["g4_pass"],
        "G5": t4_result["g5_pass"],
    }
    results["gates"] = gates

    all_pass = all(gates[g] for g in ["G0", "G1", "G2", "G3", "G4", "G5"])
    if all_pass and t0_result["best_d_cagr"] >= 2.0:
        results["verdict"] = "PROMOTE"
        results["verdict_reason"] = "All gates pass, CAGR improvement sufficient"
    elif all_pass:
        results["verdict"] = "CLOSE"
        results["verdict_reason"] = "All gates pass but CAGR improvement marginal"
    else:
        failed = [g for g, v in gates.items() if not v and g != "ABORT"]
        results["verdict"] = "CLOSE"
        results["verdict_reason"] = f"Failed gates: {', '.join(failed)}"

    _write_results(results, t0_wall)


def _write_results(results, t0_wall):
    elapsed = time.time() - t0_wall
    results["elapsed_s"] = round(elapsed, 1)

    print(f"\n{'=' * 70}")
    print(f"VERDICT: {results['verdict']}")
    print(f"Reason:  {results.get('verdict_reason', '')}")
    print(f"Gates:   {results.get('gates', {})}")
    print(f"Elapsed: {elapsed:.1f}s")
    print(f"{'=' * 70}")

    with open(OUTDIR / "x21_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults written to {OUTDIR / 'x21_results.json'}")


if __name__ == "__main__":
    main()
