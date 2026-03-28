#!/usr/bin/env python3
"""x39 — Feature Invention Explorer.

Tools to LOOK at BTC H4 data and find what existing quantities don't capture.
Not a framework. Not a pipeline. A magnifying glass.

Usage:
    python explore.py                    # Run all sections, print to terminal
    python explore.py --section 1        # Anomaly Atlas only
    python explore.py --section 2        # Loss Anatomy only
    python explore.py --section 3        # Residual Scan only

Output:
    output/bar_features.csv      — Every H4 bar with ~45 computed features
    output/anomalies_top100.csv  — 100 most multi-dimensionally unusual bars
    output/trades.csv            — Strategy replay: every trade with features
    output/residual_corr.csv     — Feature × forward-return correlations after
                                   conditioning on EMA/VDO regime
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv"
OUTDIR = Path(__file__).resolve().parent / "output"

# ═══════════════════════════════════════════════════════════════════════════
# Indicator helpers (exact match with strategy code)
# ═══════════════════════════════════════════════════════════════════════════

def ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series, dtype=np.float64)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
               cap_q: float = 0.90, cap_lb: int = 100,
               period: int = 20) -> np.ndarray:
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


def vdo(volume: np.ndarray, taker_buy: np.ndarray,
        fast: int = 12, slow: int = 28) -> np.ndarray:
    taker_sell = volume - taker_buy
    vdr = np.zeros(len(volume))
    mask = volume > 0
    vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    return ema(vdr, fast) - ema(vdr, slow)


def map_d1_to_h4(d1_arr: np.ndarray, d1_close_times: np.ndarray,
                 h4_close_times: np.ndarray, n_h4: int) -> np.ndarray:
    """Map a D1-indexed array to H4 bar grid (most recent completed D1 bar)."""
    result = np.full(n_h4, np.nan)
    d1_i = 0
    n_d1 = len(d1_arr)
    for i in range(n_h4):
        while d1_i + 1 < n_d1 and d1_close_times[d1_i + 1] < h4_close_times[i]:
            d1_i += 1
        if d1_close_times[d1_i] < h4_close_times[i]:
            result[i] = d1_arr[d1_i]
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load H4 and D1 bars from CSV."""
    raw = pd.read_csv(DATA)
    raw["datetime"] = pd.to_datetime(raw["open_time"], unit="ms")

    h4 = raw[raw["interval"] == "4h"].copy().sort_values("open_time").reset_index(drop=True)
    d1 = raw[raw["interval"] == "1d"].copy().sort_values("open_time").reset_index(drop=True)

    print(f"Loaded {len(h4)} H4 bars, {len(d1)} D1 bars")
    print(f"  H4 range: {h4['datetime'].iloc[0]} → {h4['datetime'].iloc[-1]}")
    return h4, d1


# ═══════════════════════════════════════════════════════════════════════════
# Section 0: Compute all bar features
# ═══════════════════════════════════════════════════════════════════════════

def compute_features(h4: pd.DataFrame, d1: pd.DataFrame) -> pd.DataFrame:
    """Compute ~25 features per H4 bar."""
    o = h4["open"].values.astype(np.float64)
    h = h4["high"].values.astype(np.float64)
    lo = h4["low"].values.astype(np.float64)
    c = h4["close"].values.astype(np.float64)
    v = h4["volume"].values.astype(np.float64)
    tb = h4["taker_buy_base_vol"].values.astype(np.float64)
    nt = h4["num_trades"].values.astype(np.float64)
    n = len(c)

    rng = h - lo
    rng_safe = np.where(rng > 1e-10, rng, np.nan)
    v_safe = np.where(v > 0, v, np.nan)

    f = pd.DataFrame()
    f["datetime"] = h4["datetime"].values
    f["open_time"] = h4["open_time"].values
    f["close"] = c

    # ── Bar morphology ────────────────────────────────────────────────
    f["range"] = rng
    f["body"] = c - o                                    # signed body
    f["body_ratio"] = np.abs(c - o) / rng_safe           # |body| / range
    f["close_pos"] = (c - lo) / rng_safe                 # 0=low, 1=high
    f["upper_wick"] = (h - np.maximum(o, c)) / rng_safe
    f["lower_wick"] = (np.minimum(o, c) - lo) / rng_safe
    f["wick_asym"] = f["upper_wick"] - f["lower_wick"]   # +selling press, -buying press
    f["direction"] = np.sign(c - o)

    # ── Volume characteristics ────────────────────────────────────────
    f["volume"] = v
    f["taker_ratio"] = tb / v_safe                       # fraction aggressive buy
    f["taker_imbalance"] = (2 * tb - v) / v_safe         # [-1, +1] raw per-bar

    # ── Cross-dimensional (price × volume) ────────────────────────────
    f["range_per_vol"] = rng / v_safe                    # Amihud-like: price impact per volume
    f["vol_per_range"] = v / rng_safe                    # inverse: volume needed per unit move

    # Taker-price alignment: do aggressive buyers win?
    # +1 = buy pressure AND price up. -1 = buy pressure BUT price down.
    f["taker_price_align"] = f["taker_imbalance"] * np.sign(c - o)

    # ── Rolling z-scores (100-bar window) ─────────────────────────────
    win = 100
    for col, arr in [("volume", v), ("range", rng)]:
        s = pd.Series(arr)
        rm = s.rolling(win, min_periods=win).mean()
        rs = s.rolling(win, min_periods=win).std()
        f[f"{col}_z"] = ((arr - rm) / rs).values

    # ── Sequential / multi-bar ────────────────────────────────────────
    # Body consistency: rolling sum of sign(body) over last 6 bars
    body_sign = np.sign(c - o)
    f["body_consist_6"] = pd.Series(body_sign).rolling(6, min_periods=6).sum().values

    # Volume acceleration: V[i] / V[i-1]
    f["vol_accel"] = v / np.concatenate([[np.nan], v[:-1]])

    # Range acceleration
    f["range_accel"] = rng / np.concatenate([[np.nan], rng[:-1]])

    # Close-to-close return vs intra-bar body
    cc_ret = np.concatenate([[np.nan], (c[1:] - c[:-1]) / c[:-1]])
    body_pct = (c - o) / o
    f["cc_vs_body"] = cc_ret / np.where(np.abs(body_pct) > 1e-8, body_pct, np.nan)

    # ── Existing indicators ───────────────────────────────────────────
    ema_fast = ema(c, 30)
    ema_slow = ema(c, 120)
    f["ema_fast"] = ema_fast
    f["ema_slow"] = ema_slow
    f["ema_spread"] = (ema_fast - ema_slow) / ema_slow
    f["ema_regime"] = (ema_fast > ema_slow).astype(int)

    f["ratr"] = robust_atr(h, lo, c)
    f["ratr_pct"] = f["ratr"] / c  # ATR as % of price

    vdo_arr = vdo(v, tb)
    f["vdo"] = vdo_arr
    f["vdo_sign"] = (vdo_arr > 0).astype(int)

    # ── Gen4/Gen1 H4 features ────────────────────────────────────────

    # Multi-bar range position (gen4: strongest continuation signal, t=12.54)
    for lb in [84, 168]:
        roll_hi = pd.Series(h).rolling(lb, min_periods=lb).max().values
        roll_lo = pd.Series(lo).rolling(lb, min_periods=lb).min().values
        denom = roll_hi - roll_lo
        denom_safe = np.where(denom > 1e-10, denom, np.nan)
        f[f"rangepos_{lb}"] = (c - roll_lo) / denom_safe

    # H4 returns at key horizons (gen1 V6: ret_168 is frozen winner)
    for lb in [6, 84, 168]:
        shifted = np.concatenate([[np.nan] * lb, c[:-lb]])
        f[f"ret_{lb}"] = c / np.where(shifted > 0, shifted, np.nan) - 1

    # Relative volume (gen4: magnitude predictor)
    f["relvol_168"] = v / pd.Series(v).rolling(168, min_periods=168).mean().values

    # Trend quality ratio (gen1 V3: momentum / volatility)
    log_ret = np.log(c / np.concatenate([[c[0]], c[:-1]]))
    realized_vol_84 = pd.Series(log_ret).rolling(84, min_periods=84).std().values * np.sqrt(84)
    rv84_safe = np.where(realized_vol_84 > 1e-10, realized_vol_84, np.nan)
    f["trendq_84"] = f["ret_84"] / rv84_safe

    # Volatility ratio short/long (gen1 V6 finalist: compression/expansion)
    std_5 = pd.Series(c).rolling(5, min_periods=5).std().values
    std_20 = pd.Series(c).rolling(20, min_periods=20).std().values
    f["vol_ratio_5_20"] = std_5 / np.where(std_20 > 1e-10, std_20, np.nan)

    # Range-based volatility (gen4: alternative to realized vol)
    range_pct = rng / c
    f["range_vol_84"] = pd.Series(range_pct).rolling(84, min_periods=84).mean().values

    # Rolling taker imbalance at multiple horizons
    # (gen4: REVERSAL signal at long horizon, t=-15.85 on D1)
    for lb in [12, 168]:
        tb_roll = pd.Series(tb).rolling(lb, min_periods=lb).sum().values
        v_roll = pd.Series(v).rolling(lb, min_periods=lb).sum().values
        f[f"taker_imbal_{lb}"] = 2 * tb_roll / np.where(v_roll > 0, v_roll, np.nan) - 1

    # Trade surprise (gen4 C3 champion: residual of trades vs volume)
    log_nt = np.log1p(nt)
    log_v = np.log1p(v)
    fit_mask = np.isfinite(log_nt[:2000]) & np.isfinite(log_v[:2000])
    if fit_mask.sum() > 100:
        slope, intercept, _, _, _ = stats.linregress(
            log_v[:2000][fit_mask], log_nt[:2000][fit_mask],
        )
        residual = log_nt - (intercept + slope * log_v)
        roll_mean_res = pd.Series(residual).rolling(168, min_periods=168).mean().values
        f["trade_surprise_168"] = residual - roll_mean_res
    else:
        f["trade_surprise_168"] = np.nan

    # ── D1 features mapped to H4 ─────────────────────────────────────
    d1_c = d1["close"].values.astype(np.float64)
    d1_h = d1["high"].values.astype(np.float64)
    d1_lo = d1["low"].values.astype(np.float64)
    d1_v = d1["volume"].values.astype(np.float64)
    d1_tb = d1["taker_buy_base_vol"].values.astype(np.float64)
    d1_ct = d1["close_time"].values
    h4_ct = h4["close_time"].values

    # D1 EMA(21) regime (existing)
    d1_ema21 = ema(d1_c, 21)
    d1_regime = d1_c > d1_ema21
    regime_ok = np.zeros(n, dtype=bool)
    d1_idx = 0
    n_d1 = len(d1)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_ok[i] = d1_regime[d1_idx]
    f["d1_regime_ok"] = regime_ok.astype(int)

    # D1 distance from SMA(21) (gen1 V1: drift gate)
    d1_sma21 = pd.Series(d1_c).rolling(21, min_periods=21).mean().values
    d1_dist_21 = d1_c / np.where(d1_sma21 > 0, d1_sma21, np.nan) - 1
    f["d1_dist_mean_21"] = map_d1_to_h4(d1_dist_21, d1_ct, h4_ct, n)

    # D1 range-based volatility (gen4: anti-vol permission)
    d1_range_pct = (d1_h - d1_lo) / d1_c
    d1_rv84 = pd.Series(d1_range_pct).rolling(84, min_periods=84).mean().values
    f["d1_rangevol_84"] = map_d1_to_h4(d1_rv84, d1_ct, h4_ct, n)

    # D1 rangevol_84 percentile rank within trailing 365 days (gen4 C1)
    d1_rv84_rank = np.full(len(d1_rv84), np.nan)
    for i in range(365, len(d1_rv84)):
        window = d1_rv84[max(0, i - 365):i]
        valid_w = window[np.isfinite(window)]
        if len(valid_w) > 10 and np.isfinite(d1_rv84[i]):
            d1_rv84_rank[i] = np.mean(valid_w <= d1_rv84[i])
    f["d1_rangevol84_rank365"] = map_d1_to_h4(d1_rv84_rank, d1_ct, h4_ct, n)

    # D1 taker imbalance rolling 12 (gen4 C2: exhaustion signal)
    d1_tb_12 = pd.Series(d1_tb).rolling(12, min_periods=12).sum().values
    d1_v_12 = pd.Series(d1_v).rolling(12, min_periods=12).sum().values
    d1_ti_12 = 2 * d1_tb_12 / np.where(d1_v_12 > 0, d1_v_12, np.nan) - 1
    f["d1_taker_imbal_12"] = map_d1_to_h4(d1_ti_12, d1_ct, h4_ct, n)

    # ── Forward returns (for residual scan) ───────────────────────────
    f["fwd_ret_1"] = np.concatenate([(c[1:] - c[:-1]) / c[:-1], [np.nan]])
    f["fwd_ret_6"] = np.concatenate([(c[6:] - c[:-6]) / c[:-6], [np.nan] * 6])
    f["fwd_ret_24"] = np.concatenate([(c[24:] - c[:-24]) / c[:-24], [np.nan] * 24])
    f["fwd_ret_42"] = np.concatenate([(c[42:] - c[:-42]) / c[:-42], [np.nan] * 42])
    f["fwd_ret_168"] = np.concatenate([(c[168:] - c[:-168]) / c[:-168], [np.nan] * 168])

    return f


# ═══════════════════════════════════════════════════════════════════════════
# Section 1: Anomaly Atlas
# ═══════════════════════════════════════════════════════════════════════════

def anomaly_atlas(feat: pd.DataFrame, top_n: int = 100) -> pd.DataFrame:
    """Find bars that are multi-dimensionally unusual."""
    print("\n" + "=" * 70)
    print("SECTION 1: ANOMALY ATLAS")
    print("=" * 70)

    dims = [
        "volume_z", "range_z", "body_ratio", "close_pos",
        "upper_wick", "lower_wick", "taker_ratio",
        "range_per_vol", "taker_price_align", "vol_accel",
        "rangepos_168", "relvol_168", "taker_imbal_168",
        "trade_surprise_168", "vol_ratio_5_20",
    ]

    # Percentile rank each dimension, then distance from median
    scores = pd.DataFrame(index=feat.index)
    for d in dims:
        col = feat[d].copy()
        ranked = col.rank(pct=True)
        scores[d] = (ranked - 0.5).abs() * 2  # 0=median, 1=extreme

    feat = feat.copy()
    feat["anomaly_score"] = scores.mean(axis=1)

    top = feat.nlargest(top_n, "anomaly_score").copy()

    print(f"\nTop {top_n} anomalous bars (multi-dimensional outliers):")
    print(f"  Anomaly score range: {top['anomaly_score'].min():.3f} → {top['anomaly_score'].max():.3f}")
    print(f"  Median bar score:    {feat['anomaly_score'].median():.3f}")
    print()

    # Show top 20 with key features
    show_cols = ["datetime", "close", "anomaly_score",
                 "volume_z", "range_z", "body_ratio", "close_pos",
                 "taker_ratio", "range_per_vol", "vdo", "fwd_ret_1"]
    print(top[show_cols].head(20).to_string(index=False))

    # What dimensions drive anomalies?
    print("\n\nAnomaly dimension breakdown (mean score in top 100 vs all):")
    for d in dims:
        top_mean = scores.loc[top.index, d].mean()
        all_mean = scores[d].mean()
        print(f"  {d:25s}  top100={top_mean:.3f}  all={all_mean:.3f}  ratio={top_mean / all_mean:.1f}x")

    top.to_csv(OUTDIR / "anomalies_top100.csv", index=False)
    print(f"\n→ Saved to output/anomalies_top100.csv")

    return feat  # return with anomaly_score column added


# ═══════════════════════════════════════════════════════════════════════════
# Section 2: Loss Anatomy — replay strategy, dissect losing trades
# ═══════════════════════════════════════════════════════════════════════════

def replay_trades(feat: pd.DataFrame) -> pd.DataFrame:
    """Simplified E5-ema21D1 replay. Returns trade list with features."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    trades = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    trail_mult = 3.0
    cost_bps = 50  # harsh RT

    for i in range(120, n):  # skip warmup
        if np.isnan(ratr[i]):
            continue

        if not in_pos:
            if ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
        else:
            peak = max(peak, c[i])
            trail_stop = peak - trail_mult * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                exit_price = c[i]
                gross_ret = (exit_price - entry_price) / entry_price
                cost = cost_bps / 10_000
                net_ret = gross_ret - cost

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "exit_reason": exit_reason,
                    "mfe": (peak - entry_price) / entry_price,  # max favorable
                    "mae": (min(c[entry_bar:i + 1]) - entry_price) / entry_price,  # max adverse
                    "win": int(net_ret > 0),
                })

                in_pos = False
                peak = 0.0

    return pd.DataFrame(trades)


def loss_anatomy(feat: pd.DataFrame) -> None:
    """Compare features at entry of winning vs losing trades."""
    print("\n" + "=" * 70)
    print("SECTION 2: LOSS ANATOMY")
    print("=" * 70)

    trades = replay_trades(feat)
    if trades.empty:
        print("No trades found.")
        return

    wins = trades[trades["win"] == 1]
    losses = trades[trades["win"] == 0]

    print(f"\nReplayed {len(trades)} trades: {len(wins)} wins, {len(losses)} losses")
    print(f"  Win rate: {len(wins) / len(trades):.1%}")
    print(f"  Avg win:  {wins['net_ret'].mean():.2%}")
    print(f"  Avg loss: {losses['net_ret'].mean():.2%}")
    print(f"  Avg bars held (win): {wins['bars_held'].mean():.0f}")
    print(f"  Avg bars held (loss): {losses['bars_held'].mean():.0f}")

    # Attach entry-bar features to each trade
    compare_cols = [
        "volume_z", "range_z", "body_ratio", "close_pos",
        "upper_wick", "lower_wick", "taker_ratio", "taker_imbalance",
        "range_per_vol", "taker_price_align", "vdo", "ema_spread",
        "ratr_pct", "vol_accel", "range_accel", "body_consist_6",
        "wick_asym",
        # gen4/gen1 features
        "rangepos_84", "rangepos_168", "ret_168", "relvol_168",
        "trendq_84", "vol_ratio_5_20", "range_vol_84",
        "taker_imbal_12", "taker_imbal_168", "trade_surprise_168",
        "d1_dist_mean_21", "d1_rangevol_84", "d1_rangevol84_rank365",
        "d1_taker_imbal_12",
    ]

    for col in compare_cols:
        vals = feat[col].values
        trades[f"entry_{col}"] = [vals[int(eb)] for eb in trades["entry_bar"]]

    # Compare distributions
    print("\n\nEntry-bar features: WINNERS vs LOSERS")
    print(f"{'Feature':30s}  {'Win mean':>10s}  {'Loss mean':>10s}  {'Diff':>10s}  {'p-value':>10s}  {'Sig':>5s}")
    print("-" * 80)

    results = []
    for col in compare_cols:
        ecol = f"entry_{col}"
        w_vals = trades.loc[trades["win"] == 1, ecol].dropna()
        l_vals = trades.loc[trades["win"] == 0, ecol].dropna()

        if len(w_vals) < 5 or len(l_vals) < 5:
            continue

        w_mean = w_vals.mean()
        l_mean = l_vals.mean()
        diff = w_mean - l_mean

        stat, pval = stats.mannwhitneyu(w_vals, l_vals, alternative="two-sided")
        sig = "*" if pval < 0.05 else ""

        print(f"  {col:28s}  {w_mean:10.4f}  {l_mean:10.4f}  {diff:+10.4f}  {pval:10.4f}  {sig:>5s}")
        results.append({"feature": col, "win_mean": w_mean, "loss_mean": l_mean,
                         "diff": diff, "p_value": pval})

    # MFE/MAE analysis
    print("\n\nMFE/MAE distribution:")
    print(f"  {'':15s}  {'Median':>10s}  {'P25':>10s}  {'P75':>10s}")
    for label, subset in [("WIN MFE", wins["mfe"]), ("WIN MAE", wins["mae"]),
                          ("LOSS MFE", losses["mfe"]), ("LOSS MAE", losses["mae"])]:
        print(f"  {label:15s}  {subset.median():10.2%}  {subset.quantile(0.25):10.2%}  {subset.quantile(0.75):10.2%}")

    trades.to_csv(OUTDIR / "trades.csv", index=False)
    print(f"\n→ Saved to output/trades.csv")


# ═══════════════════════════════════════════════════════════════════════════
# Section 3: Residual Scan — what predicts returns AFTER known indicators?
# ═══════════════════════════════════════════════════════════════════════════

def residual_scan(feat: pd.DataFrame) -> None:
    """For each feature, measure correlation with forward returns
    AFTER conditioning on EMA regime × VDO sign × D1 regime."""
    print("\n" + "=" * 70)
    print("SECTION 3: RESIDUAL SCAN")
    print("=" * 70)
    print("Question: which features predict returns INDEPENDENT of EMA/VDO/D1 regime?")

    candidate_cols = [
        # Original bar morphology
        "body_ratio", "close_pos", "upper_wick", "lower_wick", "wick_asym",
        "taker_ratio", "taker_imbalance", "range_per_vol", "vol_per_range",
        "taker_price_align", "volume_z", "range_z", "vol_accel", "range_accel",
        "body_consist_6", "cc_vs_body", "ratr_pct",
        # Gen4 features
        "rangepos_84", "rangepos_168", "relvol_168",
        "taker_imbal_12", "taker_imbal_168", "trade_surprise_168",
        "range_vol_84",
        # Gen1 features
        "ret_168", "trendq_84", "vol_ratio_5_20",
        # D1 features mapped to H4
        "d1_dist_mean_21", "d1_rangevol_84", "d1_rangevol84_rank365",
        "d1_taker_imbal_12",
    ]

    fwd_horizons = ["fwd_ret_1", "fwd_ret_6", "fwd_ret_24", "fwd_ret_42", "fwd_ret_168"]

    # Create regime groups
    valid = feat.dropna(subset=candidate_cols + fwd_horizons + ["ema_regime", "vdo_sign", "d1_regime_ok"]).copy()
    valid["regime_group"] = (valid["ema_regime"].astype(str) + "_" +
                             valid["vdo_sign"].astype(str) + "_" +
                             valid["d1_regime_ok"].astype(str))

    groups = valid["regime_group"].unique()
    print(f"\nRegime groups: {len(groups)}")
    for g in sorted(groups):
        cnt = (valid["regime_group"] == g).sum()
        print(f"  {g}: {cnt} bars")

    # For each feature × horizon, compute within-group rank correlation, then pool
    print(f"\n{'Feature':25s}", end="")
    for hz in fwd_horizons:
        print(f"  {'rho_' + hz:>14s}  {'p':>8s}", end="")
    print(f"  {'sig_count':>10s}")
    print("-" * 110)

    all_results = []

    for col in candidate_cols:
        row = {"feature": col}
        sig_count = 0

        for hz in fwd_horizons:
            # Pool within-group Spearman correlations
            rhos = []
            ns = []
            for g in groups:
                subset = valid[valid["regime_group"] == g]
                if len(subset) < 30:
                    continue
                x = subset[col].values
                y = subset[hz].values
                mask = np.isfinite(x) & np.isfinite(y)
                if mask.sum() < 30:
                    continue
                rho, _ = stats.spearmanr(x[mask], y[mask])
                if np.isfinite(rho):
                    rhos.append(rho)
                    ns.append(mask.sum())

            if not rhos:
                row[f"rho_{hz}"] = np.nan
                row[f"p_{hz}"] = np.nan
                continue

            # Weighted average rho (by sample size)
            weights = np.array(ns, dtype=float)
            avg_rho = np.average(rhos, weights=weights)

            # Test if avg_rho is significantly != 0 using Fisher z-transform
            total_n = sum(ns)
            z = np.arctanh(avg_rho) * np.sqrt(total_n - 3)
            p = 2 * (1 - stats.norm.cdf(abs(z)))

            row[f"rho_{hz}"] = avg_rho
            row[f"p_{hz}"] = p
            if p < 0.01:
                sig_count += 1

        row["sig_count"] = sig_count
        all_results.append(row)

        # Print
        print(f"  {col:23s}", end="")
        for hz in fwd_horizons:
            rho = row.get(f"rho_{hz}", np.nan)
            p = row.get(f"p_{hz}", np.nan)
            flag = "**" if (np.isfinite(p) and p < 0.01) else "*" if (np.isfinite(p) and p < 0.05) else ""
            print(f"  {rho:+12.4f}{flag:2s}  {p:8.4f}", end="")
        print(f"  {sig_count:>10d}")

    results_df = pd.DataFrame(all_results)
    results_df.to_csv(OUTDIR / "residual_corr.csv", index=False)
    print(f"\n→ Saved to output/residual_corr.csv")

    # Highlight features with significant residual predictive power
    sig = results_df[results_df["sig_count"] > 0].sort_values("sig_count", ascending=False)
    if not sig.empty:
        print(f"\n*** Features with significant residual correlation (p<0.01 at ≥1 horizon):")
        for _, r in sig.iterrows():
            print(f"  {r['feature']:25s}  sig at {int(r['sig_count'])}/3 horizons")
        print("\nThese are candidates: they predict returns BEYOND what EMA/VDO/D1 already capture.")
    else:
        print("\nNo features show significant residual predictive power at p<0.01.")
        print("This suggests existing indicators may have captured most exploitable structure.")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="x39 — Feature Invention Explorer")
    parser.add_argument("--section", type=int, choices=[1, 2, 3], default=None,
                        help="Run specific section only (1=Anomaly, 2=Loss, 3=Residual)")
    args = parser.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Save full feature matrix
    feat.to_csv(OUTDIR / "bar_features.csv", index=False)
    print(f"→ Saved {len(feat)} bars × {len(feat.columns)} features to output/bar_features.csv")

    if args.section is None or args.section == 1:
        feat = anomaly_atlas(feat)

    if args.section is None or args.section == 2:
        loss_anatomy(feat)

    if args.section is None or args.section == 3:
        residual_scan(feat)

    print("\n" + "=" * 70)
    print("DONE. Explore output/ CSVs to find what surprises you.")
    print("=" * 70)


if __name__ == "__main__":
    main()
