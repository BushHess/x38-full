#!/usr/bin/env python3
"""P0.1 -- ML overlay feasibility gate for VTrend/E0 state.

This benchmark is intentionally conservative. It does not train XGBoost.
It answers four questions before any tree model is allowed:

  1. Is there measurable incremental information in compact E0-state features?
  2. What is the minimum compact baseline any future ML model must beat?
  3. After thinning and cluster accounting, how much effective sample size remains?
  4. Should the ML stack be killed, restricted to a tiny model, or allowed to benchmark trees?
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


# ============================================================================
# CONSTANTS
# ============================================================================

DATA = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
OUTDIR = Path(__file__).resolve().parent

START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365

H = 24
THIN_STRIDE = 3
TRAIN_YEARS = 3
TEST_DAYS = 180
STEP_DAYS = 180
EMBARGO_BARS = 24
BAR_MS = 4 * 60 * 60 * 1000

SLOW = 120
FAST = 30
ATR_P = 14
VDO_FAST = 12
VDO_SLOW = 28
D1_EMA = 21
TRAIL_MULT = 3.0

DD1_ATR = 2.5
DD1_FLOOR = 0.02
DD2_ATR = 5.0
DD2_FLOOR = 0.04
UP_ATR = 1.5
UP_FLOOR = 0.015

MODEL_SPECS = {
    "PRIOR": [],
    "DD_ONLY": ["dd_now_atr"],
    "CORE4": ["dd_now_atr", "ema_spread_atr", "atr_pct", "ret_3"],
    "EXPANDED7": [
        "dd_now_atr",
        "ema_spread_atr",
        "price_to_slow_atr",
        "atr_pct",
        "vdo",
        "ret_3",
        "d1_regime",
    ],
}

FEATURES_ALL = [
    "dd_now_atr",
    "ema_spread_atr",
    "price_to_slow_atr",
    "atr_pct",
    "vdo",
    "ret_3",
    "d1_regime",
]


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class Sample:
    bar_index: int
    close_time: int
    cluster_id: int
    cluster_pos: int
    keep_thin3: bool
    dd_now_pct: float
    features: dict[str, float]
    soft_label: int
    hard_label: int
    soft_censored: bool
    hard_censored: bool


@dataclass
class Fold:
    fold_id: int
    train_start_ms: int
    train_end_ms: int
    test_start_ms: int
    test_end_ms: int


# ============================================================================
# HELPERS
# ============================================================================


def _date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _ms_to_date(ms: int) -> str:
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1]
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _vdo(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    taker_buy: np.ndarray,
    fast: int,
    slow: int,
) -> np.ndarray:
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def _d1_regime_map(
    d1_close: np.ndarray,
    d1_close_time: np.ndarray,
    h4_close_time: np.ndarray,
    period: int,
) -> np.ndarray:
    d1_ema = _ema(d1_close, period)
    d1_regime = d1_close > d1_ema
    out = np.zeros(len(h4_close_time), dtype=np.float64)
    d1_idx = -1
    for i, h4_ct in enumerate(h4_close_time):
        while d1_idx + 1 < len(d1_close_time) and d1_close_time[d1_idx + 1] < h4_ct:
            d1_idx += 1
        if d1_idx >= 0:
            out[i] = 1.0 if d1_regime[d1_idx] else 0.0
    return out


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x_clip = np.clip(x, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-x_clip))


def _fit_logistic_ridge(
    x: np.ndarray,
    y: np.ndarray,
    l2: float = 1.0,
    max_iter: int = 100,
    tol: float = 1e-7,
) -> dict[str, np.ndarray] | None:
    if x.size == 0 or len(np.unique(y)) < 2:
        return None

    mu = np.mean(x, axis=0)
    sigma = np.std(x, axis=0, ddof=0)
    sigma = np.where(sigma < 1e-12, 1.0, sigma)
    xz = (x - mu) / sigma
    z = np.column_stack([np.ones(len(xz)), xz])

    beta = np.zeros(z.shape[1], dtype=np.float64)
    eye = np.eye(z.shape[1], dtype=np.float64)
    eye[0, 0] = 0.0  # do not penalize intercept

    for _ in range(max_iter):
        p = _sigmoid(z @ beta)
        w = np.clip(p * (1.0 - p), 1e-6, None)
        grad = z.T @ (p - y) + l2 * (eye @ beta)
        hess = z.T @ (z * w[:, None]) + l2 * eye
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hess) @ grad
        beta_new = beta - step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
        beta = beta_new

    return {"beta": beta, "mu": mu, "sigma": sigma}


def _predict_logistic(model: dict[str, np.ndarray] | None, x: np.ndarray, y_train: np.ndarray | None = None) -> np.ndarray:
    n_rows = x.shape[0] if x.ndim == 2 else len(x)
    if n_rows == 0:
        return np.zeros(0, dtype=np.float64)
    if model is None:
        if y_train is None or len(y_train) == 0:
            return np.full(n_rows, 0.5, dtype=np.float64)
        p = float(np.mean(y_train))
        p = min(max(p, 1e-6), 1.0 - 1e-6)
        return np.full(n_rows, p, dtype=np.float64)
    xz = (x - model["mu"]) / model["sigma"]
    z = np.column_stack([np.ones(len(xz)), xz])
    return _sigmoid(z @ model["beta"])


def _logloss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1.0 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def _auc(y: np.ndarray, score: np.ndarray) -> float:
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(score)
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, len(score) + 1, dtype=np.float64)
    rank_sum_pos = np.sum(ranks[y == 1])
    return float((rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def _autocorr(x: np.ndarray, lag: int) -> float:
    if lag >= len(x):
        return 0.0
    x0 = x[:-lag]
    x1 = x[lag:]
    x0 = x0 - np.mean(x0)
    x1 = x1 - np.mean(x1)
    den = math.sqrt(float(np.dot(x0, x0) * np.dot(x1, x1)))
    if den < 1e-12:
        return 0.0
    return float(np.dot(x0, x1) / den)


def _ess_bartlett(x: np.ndarray, max_lag: int = 24) -> float:
    n = len(x)
    if n < 3:
        return float(n)
    rho_sum = 0.0
    for lag in range(1, min(max_lag, n - 1) + 1):
        rho = _autocorr(x, lag)
        if not np.isfinite(rho) or rho <= 0.0:
            break
        rho_sum += rho * (1.0 - lag / n)
    denom = 1.0 + 2.0 * rho_sum
    if denom <= 0.0:
        return 1.0
    return float(max(1.0, n / denom))


def _principal_component_score(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return np.zeros(0, dtype=np.float64)
    mu = np.mean(x, axis=0)
    sigma = np.std(x, axis=0, ddof=0)
    sigma = np.where(sigma < 1e-12, 1.0, sigma)
    xz = (x - mu) / sigma
    _, _, vt = np.linalg.svd(xz, full_matrices=False)
    pc1 = vt[0]
    return xz @ pc1


def _build_folds() -> list[Fold]:
    folds: list[Fold] = []
    start_dt = datetime.strptime(START, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(END, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    test_start = datetime(start_dt.year + TRAIN_YEARS, start_dt.month, start_dt.day, tzinfo=timezone.utc)
    fold_id = 0
    while test_start + timedelta(days=TEST_DAYS) <= end_dt + timedelta(days=1):
        train_start = test_start - timedelta(days=int(TRAIN_YEARS * 365.25))
        train_end = test_start - timedelta(milliseconds=EMBARGO_BARS * BAR_MS)
        test_end = test_start + timedelta(days=TEST_DAYS) - timedelta(milliseconds=1)
        folds.append(
            Fold(
                fold_id=fold_id,
                train_start_ms=int(train_start.timestamp() * 1000),
                train_end_ms=int(train_end.timestamp() * 1000),
                test_start_ms=int(test_start.timestamp() * 1000),
                test_end_ms=int(test_end.timestamp() * 1000),
            )
        )
        fold_id += 1
        test_start += timedelta(days=STEP_DAYS)
    return folds


# ============================================================================
# DATA LOAD + SAMPLE BUILD
# ============================================================================


def _load_arrays() -> dict[str, np.ndarray]:
    start_ms = _date_to_ms(START)
    end_ms = _date_to_ms(END) + 86_400_000 - 1
    load_start_ms = start_ms - WARMUP_DAYS * 86_400_000

    h4_rows: list[dict[str, float]] = []
    d1_rows: list[dict[str, float]] = []
    with DATA.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            open_time = int(row["open_time"])
            if open_time < load_start_ms or open_time > end_ms:
                continue
            interval = row["interval"]
            target = h4_rows if interval == "4h" else d1_rows if interval == "1d" else None
            if target is None:
                continue
            target.append({
                "open_time": open_time,
                "close_time": int(row["close_time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "taker_buy": float(row.get("taker_buy_base_vol", 0.0) or 0.0),
            })

    close = np.array([r["close"] for r in h4_rows], dtype=np.float64)
    high = np.array([r["high"] for r in h4_rows], dtype=np.float64)
    low = np.array([r["low"] for r in h4_rows], dtype=np.float64)
    volume = np.array([r["volume"] for r in h4_rows], dtype=np.float64)
    taker = np.array([r["taker_buy"] for r in h4_rows], dtype=np.float64)
    close_time = np.array([r["close_time"] for r in h4_rows], dtype=np.int64)

    d1_close = np.array([r["close"] for r in d1_rows], dtype=np.float64)
    d1_close_time = np.array([r["close_time"] for r in d1_rows], dtype=np.int64)

    return {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
        "taker": taker,
        "close_time": close_time,
        "d1_close": d1_close,
        "d1_close_time": d1_close_time,
        "report_start_ms": start_ms,
        "report_end_ms": end_ms,
    }


def _build_samples(arrays: dict[str, np.ndarray]) -> list[Sample]:
    close = arrays["close"]
    high = arrays["high"]
    low = arrays["low"]
    volume = arrays["volume"]
    taker = arrays["taker"]
    close_time = arrays["close_time"]
    d1_close = arrays["d1_close"]
    d1_close_time = arrays["d1_close_time"]
    report_start_ms = int(arrays["report_start_ms"])
    report_end_ms = int(arrays["report_end_ms"])

    ema_fast = _ema(close, FAST)
    ema_slow = _ema(close, SLOW)
    atr = _atr(high, low, close, ATR_P)
    vdo = _vdo(close, high, low, volume, taker, VDO_FAST, VDO_SLOW)
    d1_regime = _d1_regime_map(d1_close, d1_close_time, close_time, D1_EMA)

    ret_3 = np.full(len(close), np.nan, dtype=np.float64)
    ret_3[3:] = close[3:] / close[:-3] - 1.0

    trend_up = (ema_fast > ema_slow) & np.isfinite(atr)
    watermark = np.full(len(close), np.nan, dtype=np.float64)
    seg_start = np.full(len(close), -1, dtype=np.int64)

    cur_start = -1
    cur_w = float("nan")
    for i in range(len(close)):
        if trend_up[i]:
            if i == 0 or not trend_up[i - 1]:
                cur_start = i
                cur_w = close[i]
            else:
                cur_w = max(cur_w, close[i])
            watermark[i] = cur_w
            seg_start[i] = cur_start
        else:
            cur_start = -1
            cur_w = float("nan")

    samples: list[Sample] = []
    cluster_id = -1
    prev_origin_i = -10
    cluster_pos = 0

    for i in range(len(close) - H):
        ct = int(close_time[i])
        if ct < report_start_ms or ct > report_end_ms:
            continue
        if not trend_up[i]:
            continue
        if not np.isfinite(watermark[i]) or watermark[i] <= 0.0:
            continue

        dd_now_pct = float((watermark[i] - close[i]) / watermark[i])
        near_peak_cut = max(float(atr[i] / close[i]), 0.01)
        if dd_now_pct > near_peak_cut:
            continue

        dd_now_atr = float((watermark[i] - close[i]) / atr[i])
        ema_spread_atr = float((ema_fast[i] - ema_slow[i]) / atr[i])
        price_to_slow_atr = float((close[i] - ema_slow[i]) / atr[i])
        atr_pct = float(atr[i] / close[i])

        feature_map = {
            "dd_now_atr": dd_now_atr,
            "ema_spread_atr": ema_spread_atr,
            "price_to_slow_atr": price_to_slow_atr,
            "atr_pct": atr_pct,
            "vdo": float(vdo[i]),
            "ret_3": float(ret_3[i]),
            "d1_regime": float(d1_regime[i]),
        }
        if not all(np.isfinite(v) for v in feature_map.values()):
            continue

        dd1 = max(DD1_ATR * atr_pct, DD1_FLOOR)
        dd2 = max(DD2_ATR * atr_pct, DD2_FLOOR)
        up = max(UP_ATR * atr_pct, UP_FLOOR)

        b_dd1 = watermark[i] * (1.0 - dd1)
        b_dd2 = watermark[i] * (1.0 - dd2)
        b_up = watermark[i] * (1.0 + up)

        tau_dd1 = None
        tau_dd2 = None
        tau_up = None
        for h in range(1, H + 1):
            ii = i + h
            if tau_dd1 is None and low[ii] <= b_dd1:
                tau_dd1 = h
            if tau_dd2 is None and low[ii] <= b_dd2:
                tau_dd2 = h
            if tau_up is None and high[ii] >= b_up:
                tau_up = h
            if tau_dd1 is not None and tau_dd2 is not None and tau_up is not None:
                break

        soft_censored = True
        soft_label = 0
        if tau_dd1 is not None and (tau_up is None or tau_dd1 < tau_up):
            soft_censored = False
            soft_label = 1
        elif tau_up is not None and (tau_dd1 is None or tau_up < tau_dd1):
            soft_censored = False
            soft_label = 0

        hard_censored = True
        hard_label = 0
        if tau_dd2 is not None and (tau_up is None or tau_dd2 < tau_up):
            hard_censored = False
            hard_label = 1
        elif tau_up is not None and (tau_dd2 is None or tau_up < tau_dd2):
            hard_censored = False
            hard_label = 0

        if i != prev_origin_i + 1:
            cluster_id += 1
            cluster_pos = 0
        else:
            cluster_pos += 1
        prev_origin_i = i

        samples.append(
            Sample(
                bar_index=i,
                close_time=ct,
                cluster_id=cluster_id,
                cluster_pos=cluster_pos,
                keep_thin3=(cluster_pos % THIN_STRIDE == 0),
                dd_now_pct=dd_now_pct,
                features=feature_map,
                soft_label=soft_label,
                hard_label=hard_label,
                soft_censored=soft_censored,
                hard_censored=hard_censored,
            )
        )

    return samples


# ============================================================================
# STEP 1: UNIVARIATE FEATURE SIGNAL
# ============================================================================


def _step1_feature_table(samples: list[Sample]) -> list[dict]:
    rows: list[dict] = []
    subset = [s for s in samples if s.keep_thin3]
    for target in ["soft", "hard"]:
        labels = []
        feats = {name: [] for name in FEATURES_ALL}
        for s in subset:
            censored = getattr(s, f"{target}_censored")
            if censored:
                continue
            labels.append(getattr(s, f"{target}_label"))
            for name in FEATURES_ALL:
                feats[name].append(s.features[name])
        y = np.array(labels, dtype=np.float64)
        for name in FEATURES_ALL:
            x = np.array(feats[name], dtype=np.float64)
            if len(x) == 0 or len(np.unique(y)) < 2:
                continue
            pos_mean = float(np.mean(x[y == 1]))
            neg_mean = float(np.mean(x[y == 0]))
            direction = "high_is_risk" if pos_mean >= neg_mean else "low_is_risk"
            score = x if direction == "high_is_risk" else -x
            rows.append({
                "target": target,
                "feature": name,
                "n": int(len(x)),
                "n_pos": int(np.sum(y == 1)),
                "pos_rate_pct": round(100.0 * float(np.mean(y)), 2),
                "mean_pos": round(pos_mean, 6),
                "mean_neg": round(neg_mean, 6),
                "direction": direction,
                "auc": round(_auc(y, score), 6),
            })
    rows.sort(key=lambda r: (r["target"], -r["auc"], r["feature"]))
    return rows


# ============================================================================
# STEP 2: COMPACT MODEL BENCHMARK
# ============================================================================


def _dataset_for_target(samples: list[Sample], target: str, only_thin3: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_rows = []
    y_rows = []
    ts_rows = []
    for s in samples:
        if only_thin3 and not s.keep_thin3:
            continue
        if getattr(s, f"{target}_censored"):
            continue
        x_rows.append([s.features[name] for name in FEATURES_ALL])
        y_rows.append(getattr(s, f"{target}_label"))
        ts_rows.append(s.close_time)
    return (
        np.array(x_rows, dtype=np.float64),
        np.array(y_rows, dtype=np.float64),
        np.array(ts_rows, dtype=np.int64),
    )


def _evaluate_models(samples: list[Sample], folds: list[Fold]) -> tuple[list[dict], list[dict]]:
    fold_rows: list[dict] = []
    summary_rows: list[dict] = []

    x_all_cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for target in ["soft", "hard"]:
        x_all_cache[target] = _dataset_for_target(samples, target, only_thin3=True)

    for target in ["soft", "hard"]:
        x_all, y_all, ts_all = x_all_cache[target]

        for fold in folds:
            train_mask = (ts_all >= fold.train_start_ms) & (ts_all <= fold.train_end_ms)
            test_mask = (ts_all >= fold.test_start_ms) & (ts_all <= fold.test_end_ms)
            if int(np.sum(train_mask)) < 50 or int(np.sum(test_mask)) < 20:
                continue

            x_train_all = x_all[train_mask]
            y_train = y_all[train_mask]
            x_test_all = x_all[test_mask]
            y_test = y_all[test_mask]

            if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
                continue

            for model_name, feature_list in MODEL_SPECS.items():
                if feature_list:
                    idx = [FEATURES_ALL.index(name) for name in feature_list]
                    x_train = x_train_all[:, idx]
                    x_test = x_test_all[:, idx]
                    model = _fit_logistic_ridge(x_train, y_train, l2=2.0)
                    p_test = _predict_logistic(model, x_test)
                else:
                    x_train = np.zeros((len(y_train), 0), dtype=np.float64)
                    x_test = np.zeros((len(y_test), 0), dtype=np.float64)
                    model = None
                    p_test = _predict_logistic(model, x_test, y_train=y_train)

                fold_rows.append({
                    "fold_id": fold.fold_id,
                    "target": target,
                    "model": model_name,
                    "train_start": _ms_to_date(fold.train_start_ms),
                    "train_end": _ms_to_date(fold.train_end_ms),
                    "test_start": _ms_to_date(fold.test_start_ms),
                    "test_end": _ms_to_date(fold.test_end_ms),
                    "train_n": int(len(y_train)),
                    "train_pos": int(np.sum(y_train == 1)),
                    "test_n": int(len(y_test)),
                    "test_pos": int(np.sum(y_test == 1)),
                    "logloss": _logloss(y_test, p_test),
                    "brier": _brier(y_test, p_test),
                    "auc": _auc(y_test, p_test),
                })

        # aggregate
        target_rows = [r for r in fold_rows if r["target"] == target]
        prior_rows = [r for r in target_rows if r["model"] == "PRIOR"]
        prior_logloss_med = float(np.median([r["logloss"] for r in prior_rows])) if prior_rows else float("nan")
        prior_brier_med = float(np.median([r["brier"] for r in prior_rows])) if prior_rows else float("nan")

        for model_name in MODEL_SPECS:
            rows = [r for r in target_rows if r["model"] == model_name]
            if not rows:
                continue
            ll_med = float(np.median([r["logloss"] for r in rows]))
            br_med = float(np.median([r["brier"] for r in rows]))
            auc_med = float(np.median([r["auc"] for r in rows]))
            ll_gain = (prior_logloss_med - ll_med) / prior_logloss_med * 100.0 if prior_logloss_med > 0 else 0.0
            br_gain = (prior_brier_med - br_med) / prior_brier_med * 100.0 if prior_brier_med > 0 else 0.0
            summary_rows.append({
                "target": target,
                "model": model_name,
                "folds": int(len(rows)),
                "logloss_med": ll_med,
                "brier_med": br_med,
                "auc_med": auc_med,
                "logloss_gain_vs_prior_pct": ll_gain,
                "brier_gain_vs_prior_pct": br_gain,
            })

    summary_rows.sort(key=lambda r: (r["target"], -r["logloss_gain_vs_prior_pct"], -r["auc_med"]))
    return fold_rows, summary_rows


# ============================================================================
# STEP 3: ESS + CLUSTER ACCOUNTING
# ============================================================================


def _step3_ess(samples: list[Sample], folds: list[Fold]) -> list[dict]:
    rows: list[dict] = []
    for target in ["soft", "hard"]:
        for fold in folds:
            raw = [
                s for s in samples
                if fold.train_start_ms <= s.close_time <= fold.train_end_ms
                and not getattr(s, f"{target}_censored")
            ]
            thin = [s for s in raw if s.keep_thin3]
            if not raw or not thin:
                continue

            raw_y = np.array([getattr(s, f"{target}_label") for s in raw], dtype=np.float64)
            thin_y = np.array([getattr(s, f"{target}_label") for s in thin], dtype=np.float64)
            raw_x = np.array([[s.features[name] for name in FEATURES_ALL] for s in raw], dtype=np.float64)
            thin_x = np.array([[s.features[name] for name in FEATURES_ALL] for s in thin], dtype=np.float64)

            raw_clusters = {s.cluster_id for s in raw}
            pos_clusters = {s.cluster_id for s in raw if getattr(s, f"{target}_label") == 1}

            rows.append({
                "fold_id": fold.fold_id,
                "target": target,
                "train_start": _ms_to_date(fold.train_start_ms),
                "train_end": _ms_to_date(fold.train_end_ms),
                "raw_n": int(len(raw)),
                "raw_pos": int(np.sum(raw_y == 1)),
                "thin3_n": int(len(thin)),
                "thin3_pos": int(np.sum(thin_y == 1)),
                "clusters": int(len(raw_clusters)),
                "positive_clusters": int(len(pos_clusters)),
                "ess_label_raw": _ess_bartlett(raw_y),
                "ess_label_thin3": _ess_bartlett(thin_y),
                "ess_pc1_raw": _ess_bartlett(_principal_component_score(raw_x)),
                "ess_pc1_thin3": _ess_bartlett(_principal_component_score(thin_x)),
            })
    return rows


# ============================================================================
# STEP 4: KILL LOGIC
# ============================================================================


def _step4_verdict(model_rows: list[dict], ess_rows: list[dict]) -> tuple[list[dict], dict]:
    decision_rows: list[dict] = []

    best_by_target: dict[str, dict] = {}
    for target in ["soft", "hard"]:
        candidates = [r for r in model_rows if r["target"] == target and r["model"] != "PRIOR"]
        if not candidates:
            continue
        best_by_target[target] = max(
            candidates,
            key=lambda r: (r["logloss_gain_vs_prior_pct"], r["auc_med"]),
        )

    ess_summary: dict[str, dict[str, float]] = {}
    for target in ["soft", "hard"]:
        rows = [r for r in ess_rows if r["target"] == target]
        if not rows:
            continue
        ess_summary[target] = {
            "median_thin3_pos": float(np.median([r["thin3_pos"] for r in rows])),
            "median_positive_clusters": float(np.median([r["positive_clusters"] for r in rows])),
            "median_ess_pc1_thin3": float(np.median([r["ess_pc1_thin3"] for r in rows])),
        }

    def add_check(name: str, description: str, value: float, threshold: float, op: str) -> bool:
        passed = value >= threshold if op == ">=" else value > threshold
        decision_rows.append({
            "criterion": name,
            "description": description,
            "value": round(float(value), 6),
            "threshold": round(float(threshold), 6),
            "pass": bool(passed),
        })
        return passed

    soft_best = best_by_target.get("soft")
    hard_best = best_by_target.get("hard")
    soft_ess = ess_summary.get("soft")
    hard_ess = ess_summary.get("hard")

    soft_pass = False
    hard_pass = False

    if soft_best and soft_ess:
        c1 = add_check(
            "SOFT_LL_GAIN",
            "Best compact soft model must improve median OOS logloss by at least 3% vs PRIOR",
            soft_best["logloss_gain_vs_prior_pct"],
            3.0,
            ">=",
        )
        c2 = add_check(
            "SOFT_AUC",
            "Best compact soft model must reach median OOS AUC >= 0.57",
            soft_best["auc_med"],
            0.57,
            ">=",
        )
        c3 = add_check(
            "SOFT_POS_CLUSTERS",
            "Median positive cluster count per train fold must be >= 60",
            soft_ess["median_positive_clusters"],
            60.0,
            ">=",
        )
        c4 = add_check(
            "SOFT_ESS_PC1",
            "Median thin3 ESS of feature PC1 must be >= 200",
            soft_ess["median_ess_pc1_thin3"],
            200.0,
            ">=",
        )
        soft_pass = c1 and c2 and c3 and c4

    if hard_best and hard_ess:
        c1 = add_check(
            "HARD_LL_GAIN",
            "Best compact hard model must improve median OOS logloss by at least 3% vs PRIOR",
            hard_best["logloss_gain_vs_prior_pct"],
            3.0,
            ">=",
        )
        c2 = add_check(
            "HARD_AUC",
            "Best compact hard model must reach median OOS AUC >= 0.56",
            hard_best["auc_med"],
            0.56,
            ">=",
        )
        c3 = add_check(
            "HARD_POS_CLUSTERS",
            "Median positive cluster count per train fold must be >= 45",
            hard_ess["median_positive_clusters"],
            45.0,
            ">=",
        )
        c4 = add_check(
            "HARD_ESS_PC1",
            "Median thin3 ESS of feature PC1 must be >= 180",
            hard_ess["median_ess_pc1_thin3"],
            180.0,
            ">=",
        )
        hard_pass = c1 and c2 and c3 and c4

    if soft_pass and hard_pass:
        verdict = "ALLOW_TREE_BENCHMARK"
    elif soft_pass:
        verdict = "PROCEED_SMALL_ONLY"
    else:
        verdict = "KILL_STACK"

    payload = {
        "verdict": verdict,
        "best_model_soft": soft_best,
        "best_model_hard": hard_best,
        "ess_soft": soft_ess,
        "ess_hard": hard_ess,
    }
    return decision_rows, payload


# ============================================================================
# REPORT
# ============================================================================


def _write_report(
    sample_summary: dict,
    feature_rows: list[dict],
    model_rows: list[dict],
    ess_rows: list[dict],
    decision_rows: list[dict],
    verdict: dict,
) -> None:
    best_soft = verdict.get("best_model_soft")
    best_hard = verdict.get("best_model_hard")
    lines = [
        "# P0.1 Initial Report",
        "",
        "## Scope",
        "",
        f"- Reporting window: `{START}` to `{END}`",
        f"- Horizon `H`: `{H}` bars",
        f"- Sample mode for model benchmark: `thin{THIN_STRIDE}`",
        "",
        "## Sample Summary",
        "",
        f"- Raw near-peak origins: `{sample_summary['raw_origins']}`",
        f"- Thin3 origins: `{sample_summary['thin3_origins']}`",
        f"- Near-peak clusters: `{sample_summary['clusters']}`",
        f"- Soft non-censored / positive: `{sample_summary['soft_noncens']}` / `{sample_summary['soft_pos']}`",
        f"- Hard non-censored / positive: `{sample_summary['hard_noncens']}` / `{sample_summary['hard_pos']}`",
        "",
        "## Best Compact Baselines",
        "",
        f"- Soft target: `{best_soft['model']}` with median OOS logloss gain `{best_soft['logloss_gain_vs_prior_pct']:.2f}%` and AUC `{best_soft['auc_med']:.4f}`" if best_soft else "- Soft target: n/a",
        f"- Hard target: `{best_hard['model']}` with median OOS logloss gain `{best_hard['logloss_gain_vs_prior_pct']:.2f}%` and AUC `{best_hard['auc_med']:.4f}`" if best_hard else "- Hard target: n/a",
        "",
        "## Verdict",
        "",
        f"- Decision: `{verdict['verdict']}`",
        "",
        "## Kill Matrix",
        "",
    ]
    for row in decision_rows:
        lines.append(
            f"- `{row['criterion']}`: value={row['value']} threshold={row['threshold']} pass={row['pass']}"
        )
    lines.append("")
    lines.append("## Top Univariate Features")
    lines.append("")
    for target in ["soft", "hard"]:
        top = [r for r in feature_rows if r["target"] == target][:3]
        if not top:
            continue
        lines.append(f"- {target}: " + ", ".join(f"{r['feature']} (AUC {r['auc']:.4f})" for r in top))
    lines.append("")
    OUTDIR.joinpath("P0_1_INITIAL_REPORT.md").write_text("\n".join(lines))


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    t0 = time.time()
    print("=" * 80)
    print("P0.1 ML FEASIBILITY GATE")
    print("=" * 80)

    print("\nLoading arrays...")
    arrays = _load_arrays()

    print("Building origin samples...")
    samples = _build_samples(arrays)
    folds = _build_folds()

    sample_summary = {
        "raw_origins": int(len(samples)),
        "thin3_origins": int(sum(1 for s in samples if s.keep_thin3)),
        "clusters": int(len({s.cluster_id for s in samples})),
        "soft_noncens": int(sum(not s.soft_censored for s in samples)),
        "soft_pos": int(sum((not s.soft_censored) and s.soft_label == 1 for s in samples)),
        "hard_noncens": int(sum(not s.hard_censored for s in samples)),
        "hard_pos": int(sum((not s.hard_censored) and s.hard_label == 1 for s in samples)),
        "folds": int(len(folds)),
    }
    print(f"  Raw origins:   {sample_summary['raw_origins']}")
    print(f"  Thin3 origins: {sample_summary['thin3_origins']}")
    print(f"  Clusters:      {sample_summary['clusters']}")

    print("\nStep 1: univariate feature scan...")
    feature_rows = _step1_feature_table(samples)

    print("Step 2: compact-model benchmark...")
    fold_rows, model_rows = _evaluate_models(samples, folds)

    print("Step 3: ESS and cluster accounting...")
    ess_rows = _step3_ess(samples, folds)

    print("Step 4: kill criteria...")
    decision_rows, verdict = _step4_verdict(model_rows, ess_rows)

    results = {
        "settings": {
            "data": str(DATA),
            "start": START,
            "end": END,
            "warmup_days": WARMUP_DAYS,
            "horizon_bars": H,
            "thin_stride": THIN_STRIDE,
            "train_years": TRAIN_YEARS,
            "test_days": TEST_DAYS,
            "step_days": STEP_DAYS,
            "embargo_bars": EMBARGO_BARS,
        },
        "sample_summary": sample_summary,
        "best_models": {
            "soft": verdict.get("best_model_soft"),
            "hard": verdict.get("best_model_hard"),
        },
        "ess_summary": {
            "soft": verdict.get("ess_soft"),
            "hard": verdict.get("ess_hard"),
        },
        "verdict": verdict["verdict"],
        "elapsed_seconds": time.time() - t0,
    }

    _write_csv(
        OUTDIR / "p0_1_feature_table.csv",
        feature_rows,
        ["target", "feature", "n", "n_pos", "pos_rate_pct", "mean_pos", "mean_neg", "direction", "auc"],
    )
    _write_csv(
        OUTDIR / "p0_1_fold_table.csv",
        fold_rows,
        ["fold_id", "target", "model", "train_start", "train_end", "test_start", "test_end",
         "train_n", "train_pos", "test_n", "test_pos", "logloss", "brier", "auc"],
    )
    _write_csv(
        OUTDIR / "p0_1_model_table.csv",
        model_rows,
        ["target", "model", "folds", "logloss_med", "brier_med", "auc_med",
         "logloss_gain_vs_prior_pct", "brier_gain_vs_prior_pct"],
    )
    _write_csv(
        OUTDIR / "p0_1_ess_table.csv",
        ess_rows,
        ["fold_id", "target", "train_start", "train_end", "raw_n", "raw_pos", "thin3_n", "thin3_pos",
         "clusters", "positive_clusters", "ess_label_raw", "ess_label_thin3", "ess_pc1_raw", "ess_pc1_thin3"],
    )
    _write_csv(
        OUTDIR / "p0_1_kill_matrix.csv",
        decision_rows,
        ["criterion", "description", "value", "threshold", "pass"],
    )
    _write_json(OUTDIR / "p0_1_results.json", results)
    _write_report(sample_summary, feature_rows, model_rows, ess_rows, decision_rows, verdict)

    print("\nVerdict:", verdict["verdict"])
    print(f"Artifacts written to {OUTDIR}")
    print(f"Elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
