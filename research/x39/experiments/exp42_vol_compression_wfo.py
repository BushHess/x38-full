#!/usr/bin/env python3
"""Exp 42: Volatility Compression Entry Walk-Forward Validation.

Tests temporal robustness of exp34's vol compression gate
(vol_ratio_5_20 < threshold) using anchored walk-forward with 4 windows.

For each window:
  1. Train: sweep 6 thresholds, pick best Sharpe
  2. Test: apply train-selected + fixed A (0.6) + fixed B (0.7) + baseline
  3. Measure d_Sharpe, d_MDD, blocked entries, blocked WR, vol_ratio distribution

Usage:
    python -m research.x39.experiments.exp42_vol_compression_wfo
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
TRAIL_MULT = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0

# ── Sweep grid (same as exp34) ───────────────────────────────────────────
COMPRESSION_THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

# ── Fixed configs from exp34 global optima ───────────────────────────────
FIXED_A = 0.6  # best Sharpe
FIXED_B = 0.7  # best Sharpe/MDD balance

# ── Anchored WFO Windows (identical to exp30/exp40/exp41) ────────────────
WFO_WINDOWS = [
    {"train_start": "2019-01-01", "train_end": "2021-06-30",
     "test_start": "2021-07-01", "test_end": "2023-06-30"},
    {"train_start": "2019-01-01", "train_end": "2022-06-30",
     "test_start": "2022-07-01", "test_end": "2024-06-30"},
    {"train_start": "2019-01-01", "train_end": "2023-06-30",
     "test_start": "2023-07-01", "test_end": "2025-06-30"},
    {"train_start": "2019-01-01", "train_end": "2024-06-30",
     "test_start": "2024-07-01", "test_end": "2026-02-28"},
]


# ═══════════════════════════════════════════════════════════════════════════
# Backtest engine (from exp34, adapted for bar-range support)
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(
    feat: pd.DataFrame,
    compression_threshold: float | None,
    start_bar: int,
    end_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional vol compression gate on bar range.

    compression_threshold=None → baseline (no gate).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    vol_ratio = feat["vol_ratio_5_20"].values

    trades: list[dict] = []
    blocked_entries: list[int] = []
    in_pos = False
    peak = 0.0
    entry_bar_idx = 0
    entry_price = 0.0

    # Warmup: skip SLOW_PERIOD bars from start of window
    actual_start = start_bar + SLOW_PERIOD
    if actual_start >= end_bar:
        return _empty_result()

    n_bars = end_bar - actual_start
    equity = np.full(n_bars, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    entry_vol_ratios: list[float] = []

    for i in range(actual_start, end_bar):
        ei = i - actual_start
        if np.isnan(ratr[i]):
            equity[ei] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[ei] = cash

            base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if base_ok:
                compression_ok = True
                if compression_threshold is not None:
                    if np.isfinite(vol_ratio[i]):
                        compression_ok = vol_ratio[i] < compression_threshold
                    else:
                        compression_ok = False

                if compression_ok:
                    in_pos = True
                    entry_bar_idx = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
                    if np.isfinite(vol_ratio[i]):
                        entry_vol_ratios.append(vol_ratio[i])
                else:
                    blocked_entries.append(i)
        else:
            equity[ei] = position_size * c[i]
            peak = max(peak, c[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                cost_rt = COST_BPS / 10_000
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost_rt

                trades.append({
                    "entry_bar": entry_bar_idx,
                    "exit_bar": i,
                    "bars_held": i - entry_bar_idx,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                })

                equity[ei] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # Force-close any open position at window end
    if in_pos:
        last = end_bar - 1
        ei = last - actual_start
        half_cost = (COST_BPS / 2) / 10_000
        cash = position_size * c[last] * (1 - half_cost)
        cost_rt = COST_BPS / 10_000
        gross_ret = (c[last] - entry_price) / entry_price
        net_ret = gross_ret - cost_rt
        trades.append({
            "entry_bar": entry_bar_idx,
            "exit_bar": last,
            "bars_held": last - entry_bar_idx,
            "net_ret": net_ret,
            "win": int(net_ret > 0),
        })
        equity[ei] = cash

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result()

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = rets.mean() / rets.std() * np.sqrt(bars_per_year) if rets.std() > 0 else 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars

    tdf = pd.DataFrame(trades)
    n_wins = int(tdf["win"].sum())
    win_rate = n_wins / len(trades) * 100

    # ── Blocked entry analysis ────────────────────────────────────────
    blocked_wins = 0
    blocked_total = len(blocked_entries)

    for b_i in blocked_entries:
        b_entry = c[b_i]
        b_peak = b_entry
        b_exited = False
        for j in range(b_i + 1, end_bar):
            if np.isnan(ratr[j]):
                continue
            b_peak = max(b_peak, c[j])
            b_trail = b_peak - TRAIL_MULT * ratr[j]
            if c[j] < b_trail or ema_f[j] < ema_s[j]:
                cost_rt = COST_BPS / 10_000
                if (c[j] - b_entry) / b_entry - cost_rt > 0:
                    blocked_wins += 1
                b_exited = True
                break
        if not b_exited:
            cost_rt = COST_BPS / 10_000
            if (c[end_bar - 1] - b_entry) / b_entry - cost_rt > 0:
                blocked_wins += 1

    blocked_wr = (blocked_wins / blocked_total * 100) if blocked_total > 0 else np.nan

    # ── Entry vol_ratio distribution ──────────────────────────────────
    median_entry_vr = float(np.median(entry_vol_ratios)) if entry_vol_ratios else np.nan

    return {
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
        "median_entry_vol_ratio": round(median_entry_vr, 4) if np.isfinite(median_entry_vr) else np.nan,
    }


def _empty_result() -> dict:
    return {
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "exposure_pct": np.nan,
        "blocked": 0, "blocked_win_rate": np.nan,
        "median_entry_vol_ratio": np.nan,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Date → bar index mapping (from exp30/exp41)
# ═══════════════════════════════════════════════════════════════════════════

def find_bar_idx(datetimes: pd.DatetimeIndex, date_str: str, side: str) -> int:
    """Map a date boundary to a bar index."""
    dt = pd.Timestamp(date_str)
    if side == "start":
        mask = datetimes >= dt
        if not mask.any():
            return len(datetimes)
        return int(np.argmax(mask))
    else:
        end_dt = dt + pd.Timedelta(days=1)
        mask = datetimes >= end_dt
        if not mask.any():
            return len(datetimes)
        return int(np.argmax(mask))


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 42: Volatility Compression Entry Walk-Forward Validation")
    print(f"  Thresholds: {COMPRESSION_THRESHOLDS} ({len(COMPRESSION_THRESHOLDS)} configs)")
    print(f"  Fixed A: threshold={FIXED_A} (best Sharpe from exp34)")
    print(f"  Fixed B: threshold={FIXED_B} (best Sharpe/MDD balance from exp34)")
    print(f"  Windows: {len(WFO_WINDOWS)} (anchored)")
    print(f"  Warmup: {SLOW_PERIOD} bars per window")
    print(f"  Cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    datetimes = pd.DatetimeIndex(feat["datetime"])

    window_results: list[dict] = []

    for w_idx, w in enumerate(WFO_WINDOWS):
        print(f"\n{'─' * 80}")
        print(f"WINDOW {w_idx + 1}/{len(WFO_WINDOWS)}")
        print(f"  Train: {w['train_start']} → {w['train_end']}")
        print(f"  Test:  {w['test_start']} → {w['test_end']}")

        train_start = find_bar_idx(datetimes, w["train_start"], "start")
        train_end = find_bar_idx(datetimes, w["train_end"], "end")
        test_start = find_bar_idx(datetimes, w["test_start"], "start")
        test_end = find_bar_idx(datetimes, w["test_end"], "end")

        print(f"  Train bars: [{train_start}, {train_end}) = {train_end - train_start}")
        print(f"  Test bars:  [{test_start}, {test_end}) = {test_end - test_start}")
        if train_start < len(datetimes) and test_end - 1 < len(datetimes):
            print(f"  Train actual: {datetimes[train_start].date()} → {datetimes[train_end - 1].date()}")
            print(f"  Test actual:  {datetimes[test_start].date()} → {datetimes[test_end - 1].date()}")
        print(f"{'─' * 80}")

        # ── Step 1: Train — sweep grid on training period ─────────────
        print(f"\n  [TRAIN] Sweeping {len(COMPRESSION_THRESHOLDS)} thresholds...")

        best_train_sharpe = -np.inf
        best_threshold: float = COMPRESSION_THRESHOLDS[0]
        train_grid: list[tuple[float, float]] = []

        for thresh in COMPRESSION_THRESHOLDS:
            r = run_backtest(feat, thresh, train_start, train_end)
            train_grid.append((thresh, r["sharpe"]))
            if np.isfinite(r["sharpe"]) and r["sharpe"] > best_train_sharpe:
                best_train_sharpe = r["sharpe"]
                best_threshold = thresh

        train_baseline = run_backtest(feat, None, train_start, train_end)

        print(f"  Train baseline: Sharpe={train_baseline['sharpe']}, "
              f"trades={train_baseline['trades']}")
        print(f"  Best train config: threshold={best_threshold}, "
              f"Sharpe={best_train_sharpe:.4f}")

        # Print train grid
        print("  Train grid (Sharpe):")
        for thresh, sh in train_grid:
            marker = " *" if thresh == best_threshold else ""
            print(f"    threshold={thresh}: {sh:.4f}{marker}")

        # ── Step 2: Test — baseline, selected, fixed A, fixed B ───────
        print(f"\n  [TEST] Running on test period...")

        test_baseline = run_backtest(feat, None, test_start, test_end)
        test_selected = run_backtest(feat, best_threshold, test_start, test_end)
        test_fixed_a = run_backtest(feat, FIXED_A, test_start, test_end)
        test_fixed_b = run_backtest(feat, FIXED_B, test_start, test_end)

        def delta(a: float, b: float) -> float:
            return round(a - b, 4) if np.isfinite(a) and np.isfinite(b) else np.nan

        d_sh_sel = delta(test_selected["sharpe"], test_baseline["sharpe"])
        d_mdd_sel = delta(test_selected["mdd_pct"], test_baseline["mdd_pct"])
        d_sh_fa = delta(test_fixed_a["sharpe"], test_baseline["sharpe"])
        d_mdd_fa = delta(test_fixed_a["mdd_pct"], test_baseline["mdd_pct"])
        d_sh_fb = delta(test_fixed_b["sharpe"], test_baseline["sharpe"])
        d_mdd_fb = delta(test_fixed_b["mdd_pct"], test_baseline["mdd_pct"])

        # vol_ratio distribution in test window entry bars
        test_vr = feat["vol_ratio_5_20"].iloc[test_start:test_end].dropna()
        vr_median = test_vr.median()
        vr_p25 = test_vr.quantile(0.25)
        vr_p75 = test_vr.quantile(0.75)
        frac_below_06 = (test_vr < 0.6).mean() * 100
        frac_below_07 = (test_vr < 0.7).mean() * 100

        print(f"  Test baseline:  Sharpe={test_baseline['sharpe']:>8.4f}, "
              f"CAGR={test_baseline['cagr_pct']:>7.2f}%, "
              f"MDD={test_baseline['mdd_pct']:>5.2f}%, "
              f"trades={test_baseline['trades']}, "
              f"WR={test_baseline['win_rate']:.1f}%")
        print(f"  Test selected:  Sharpe={test_selected['sharpe']:>8.4f} "
              f"(d={d_sh_sel:+.4f}), "
              f"MDD={test_selected['mdd_pct']:>5.2f}% (d={d_mdd_sel:+.2f}pp), "
              f"trades={test_selected['trades']}, "
              f"blocked={test_selected['blocked']}, "
              f"blocked_WR={test_selected['blocked_win_rate']}")
        print(f"  Test fixed A:   Sharpe={test_fixed_a['sharpe']:>8.4f} "
              f"(d={d_sh_fa:+.4f}), "
              f"MDD={test_fixed_a['mdd_pct']:>5.2f}% (d={d_mdd_fa:+.2f}pp), "
              f"trades={test_fixed_a['trades']}, "
              f"blocked={test_fixed_a['blocked']}, "
              f"blocked_WR={test_fixed_a['blocked_win_rate']}")
        print(f"  Test fixed B:   Sharpe={test_fixed_b['sharpe']:>8.4f} "
              f"(d={d_sh_fb:+.4f}), "
              f"MDD={test_fixed_b['mdd_pct']:>5.2f}% (d={d_mdd_fb:+.2f}pp), "
              f"trades={test_fixed_b['trades']}, "
              f"blocked={test_fixed_b['blocked']}, "
              f"blocked_WR={test_fixed_b['blocked_win_rate']}")
        print(f"  vol_ratio dist: median={vr_median:.4f}, "
              f"IQR=[{vr_p25:.4f}, {vr_p75:.4f}], "
              f"<0.6: {frac_below_06:.1f}%, <0.7: {frac_below_07:.1f}%")

        window_results.append({
            "window": w_idx + 1,
            "train_period": f"{w['train_start']} → {w['train_end']}",
            "test_period": f"{w['test_start']} → {w['test_end']}",
            "train_bars": train_end - train_start,
            "test_bars": test_end - test_start,
            "train_baseline_sharpe": train_baseline["sharpe"],
            "train_best_sharpe": round(best_train_sharpe, 4),
            "selected_threshold": best_threshold,
            # Baseline test
            "test_baseline_sharpe": test_baseline["sharpe"],
            "test_baseline_cagr": test_baseline["cagr_pct"],
            "test_baseline_mdd": test_baseline["mdd_pct"],
            "test_baseline_trades": test_baseline["trades"],
            "test_baseline_win_rate": test_baseline["win_rate"],
            "test_baseline_exposure": test_baseline["exposure_pct"],
            # Selected test
            "test_selected_sharpe": test_selected["sharpe"],
            "test_selected_cagr": test_selected["cagr_pct"],
            "test_selected_mdd": test_selected["mdd_pct"],
            "test_selected_trades": test_selected["trades"],
            "test_selected_blocked": test_selected["blocked"],
            "test_selected_blocked_wr": test_selected["blocked_win_rate"],
            "test_selected_exposure": test_selected["exposure_pct"],
            "test_selected_median_vr": test_selected["median_entry_vol_ratio"],
            "d_sharpe_selected": d_sh_sel,
            "d_mdd_selected": d_mdd_sel,
            "selected_wins_sharpe": int(np.isfinite(d_sh_sel) and d_sh_sel > 0),
            # Fixed A (0.6) test
            "test_fixedA_sharpe": test_fixed_a["sharpe"],
            "test_fixedA_cagr": test_fixed_a["cagr_pct"],
            "test_fixedA_mdd": test_fixed_a["mdd_pct"],
            "test_fixedA_trades": test_fixed_a["trades"],
            "test_fixedA_blocked": test_fixed_a["blocked"],
            "test_fixedA_blocked_wr": test_fixed_a["blocked_win_rate"],
            "test_fixedA_exposure": test_fixed_a["exposure_pct"],
            "test_fixedA_median_vr": test_fixed_a["median_entry_vol_ratio"],
            "d_sharpe_fixedA": d_sh_fa,
            "d_mdd_fixedA": d_mdd_fa,
            "fixedA_wins_sharpe": int(np.isfinite(d_sh_fa) and d_sh_fa > 0),
            # Fixed B (0.7) test
            "test_fixedB_sharpe": test_fixed_b["sharpe"],
            "test_fixedB_cagr": test_fixed_b["cagr_pct"],
            "test_fixedB_mdd": test_fixed_b["mdd_pct"],
            "test_fixedB_trades": test_fixed_b["trades"],
            "test_fixedB_blocked": test_fixed_b["blocked"],
            "test_fixedB_blocked_wr": test_fixed_b["blocked_win_rate"],
            "test_fixedB_exposure": test_fixed_b["exposure_pct"],
            "test_fixedB_median_vr": test_fixed_b["median_entry_vol_ratio"],
            "d_sharpe_fixedB": d_sh_fb,
            "d_mdd_fixedB": d_mdd_fb,
            "fixedB_wins_sharpe": int(np.isfinite(d_sh_fb) and d_sh_fb > 0),
            # vol_ratio distribution in test window
            "test_vr_median": round(vr_median, 4),
            "test_vr_p25": round(vr_p25, 4),
            "test_vr_p75": round(vr_p75, 4),
            "test_frac_below_06": round(frac_below_06, 1),
            "test_frac_below_07": round(frac_below_07, 1),
        })

    # ═══════════════════════════════════════════════════════════════════
    # Aggregate
    # ═══════════════════════════════════════════════════════════════════
    df = pd.DataFrame(window_results)

    print("\n" + "=" * 80)
    print("AGGREGATE RESULTS")
    print("=" * 80)

    # ── Selected config ───────────────────────────────────────────────
    sel_wins = df["selected_wins_sharpe"].sum()
    sel_wr = sel_wins / len(df)
    sel_mean = df["d_sharpe_selected"].mean()
    sel_mdd_mean = df["d_mdd_selected"].mean()

    print(f"\n  TRAIN-SELECTED CONFIG:")
    print(f"    WFO win rate:       {sel_wins}/{len(df)} = {sel_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {sel_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_selected']]}")
    print(f"    Mean d_MDD:         {sel_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_selected']]}")

    # ── Fixed A (0.6) ────────────────────────────────────────────────
    fa_wins = df["fixedA_wins_sharpe"].sum()
    fa_wr = fa_wins / len(df)
    fa_mean = df["d_sharpe_fixedA"].mean()
    fa_mdd_mean = df["d_mdd_fixedA"].mean()

    print(f"\n  FIXED A (threshold={FIXED_A}):")
    print(f"    WFO win rate:       {fa_wins}/{len(df)} = {fa_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {fa_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_fixedA']]}")
    print(f"    Mean d_MDD:         {fa_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_fixedA']]}")

    # ── Fixed B (0.7) ────────────────────────────────────────────────
    fb_wins = df["fixedB_wins_sharpe"].sum()
    fb_wr = fb_wins / len(df)
    fb_mean = df["d_sharpe_fixedB"].mean()
    fb_mdd_mean = df["d_mdd_fixedB"].mean()

    print(f"\n  FIXED B (threshold={FIXED_B}):")
    print(f"    WFO win rate:       {fb_wins}/{len(df)} = {fb_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {fb_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_fixedB']]}")
    print(f"    Mean d_MDD:         {fb_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_fixedB']]}")

    # ── Parameter stability ───────────────────────────────────────────
    print(f"\n  PARAMETER STABILITY:")
    for _, row in df.iterrows():
        print(f"    W{int(row['window'])}: threshold={row['selected_threshold']}")
    unique_thresholds = df["selected_threshold"].nunique()
    stability = "STABLE" if unique_thresholds <= 2 else ("MODERATE" if unique_thresholds <= 3 else "UNSTABLE")
    print(f"    Unique thresholds: {unique_thresholds}/4 → {stability}")

    # ── 0.6 consistency check ─────────────────────────────────────────
    t06_count = (df["selected_threshold"] == 0.6).sum()
    t07_count = (df["selected_threshold"] == 0.7).sum()
    print(f"    threshold=0.6 selected: {t06_count}/4 windows")
    print(f"    threshold=0.7 selected: {t07_count}/4 windows")

    # ── Regime analysis (bear vs bull) ────────────────────────────────
    print(f"\n  REGIME ANALYSIS (vol_ratio distribution & performance):")
    regime_labels = ["bear-ish", "bear", "bull", "bull"]
    for _, row in df.iterrows():
        label = regime_labels[int(row["window"]) - 1]
        print(f"    W{int(row['window'])} ({label:>8s}): "
              f"vr_median={row['test_vr_median']:.4f}, "
              f"<0.6: {row['test_frac_below_06']:.0f}%, "
              f"<0.7: {row['test_frac_below_07']:.0f}%, "
              f"d_Sh(A)={row['d_sharpe_fixedA']:+.4f}, "
              f"d_Sh(B)={row['d_sharpe_fixedB']:+.4f}")

    bear_windows = df[df["window"].isin([1, 2])]
    bull_windows = df[df["window"].isin([3, 4])]
    bear_mean_fa = bear_windows["d_sharpe_fixedA"].mean()
    bull_mean_fa = bull_windows["d_sharpe_fixedA"].mean()
    bear_mean_fb = bear_windows["d_sharpe_fixedB"].mean()
    bull_mean_fb = bull_windows["d_sharpe_fixedB"].mean()
    print(f"    Bear mean d_Sh(A): {bear_mean_fa:+.4f}, d_Sh(B): {bear_mean_fb:+.4f}")
    print(f"    Bull mean d_Sh(A): {bull_mean_fa:+.4f}, d_Sh(B): {bull_mean_fb:+.4f}")

    # Regime verdict using Fixed B (more conservative)
    if bear_mean_fb > 0 and bull_mean_fb > 0:
        regime_verdict = "REGIME-ROBUST (helps in both)"
    elif bear_mean_fb > 0 and bull_mean_fb <= 0:
        regime_verdict = "BEAR-ONLY (regime-dependent)"
    elif bull_mean_fb > 0 and bear_mean_fb <= 0:
        regime_verdict = "BULL-ONLY (regime-dependent)"
    else:
        regime_verdict = "NO BENEFIT (hurts in both)"
    print(f"    Regime verdict (B): {regime_verdict}")

    # ── Blocked entry selectivity ─────────────────────────────────────
    print(f"\n  BLOCKED ENTRY SELECTIVITY:")
    all_selective = True
    for _, row in df.iterrows():
        bl_wr_b = row["test_fixedB_blocked_wr"]
        base_wr = row["test_baseline_win_rate"]
        if np.isfinite(bl_wr_b) and np.isfinite(base_wr):
            selective = bl_wr_b < base_wr
            tag = "GOOD" if selective else "BAD"
            if not selective:
                all_selective = False
        else:
            tag = "N/A"
            all_selective = False
        bl_wr_str = f"{bl_wr_b:.1f}%" if np.isfinite(bl_wr_b) else "N/A"
        print(f"    W{int(row['window'])} (B): "
              f"blocked={int(row['test_fixedB_blocked'])}, "
              f"blocked_WR={bl_wr_str} vs baseline_WR={base_wr:.1f}% [{tag}]")
    selectivity_verdict = "ALL SELECTIVE" if all_selective else "NOT ALL SELECTIVE"
    print(f"    Selectivity: {selectivity_verdict}")

    # ═══════════════════════════════════════════════════════════════════
    # Verdict
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    sel_pass_wr = sel_wr >= 0.75
    sel_pass_mean = sel_mean > 0
    fa_pass_wr = fa_wr >= 0.75
    fa_pass_mean = fa_mean > 0
    fb_pass_wr = fb_wr >= 0.75
    fb_pass_mean = fb_mean > 0

    print(f"\n  TRAIN-SELECTED:")
    print(f"    WFO win rate >= 75%:  {'PASS' if sel_pass_wr else 'FAIL'} ({sel_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if sel_pass_mean else 'FAIL'} ({sel_mean:+.4f})")
    sel_overall = "PASS" if sel_pass_wr and sel_pass_mean else "FAIL"
    print(f"    Overall:              {sel_overall}")

    print(f"\n  FIXED A (threshold={FIXED_A}):")
    print(f"    WFO win rate >= 75%:  {'PASS' if fa_pass_wr else 'FAIL'} ({fa_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if fa_pass_mean else 'FAIL'} ({fa_mean:+.4f})")
    fa_overall = "PASS" if fa_pass_wr and fa_pass_mean else "FAIL"
    print(f"    Overall:              {fa_overall}")

    print(f"\n  FIXED B (threshold={FIXED_B}):")
    print(f"    WFO win rate >= 75%:  {'PASS' if fb_pass_wr else 'FAIL'} ({fb_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if fb_pass_mean else 'FAIL'} ({fb_mean:+.4f})")
    fb_overall = "PASS" if fb_pass_wr and fb_pass_mean else "FAIL"
    print(f"    Overall:              {fb_overall}")

    print(f"\n  Parameter stability:    {stability} ({unique_thresholds} unique)")
    print(f"  Selectivity:            {selectivity_verdict}")
    print(f"  Regime pattern:         {regime_verdict}")

    any_pass = sel_overall == "PASS" or fa_overall == "PASS" or fb_overall == "PASS"
    vol_verdict = "PASS" if any_pass else "FAIL"

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  VOL COMPRESSION WFO VERDICT: {vol_verdict:4s}                         ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")

    if vol_verdict == "PASS":
        best_label = "selected" if sel_overall == "PASS" else (
            f"fixedA({FIXED_A})" if fa_overall == "PASS" else f"fixedB({FIXED_B})")
        print(f"  → Vol compression gate has temporal stability ({best_label} passes).")
        if all_selective:
            print("  → Selectivity confirmed: blocked entries have lower WR in ALL windows.")
        print("  → Methodological finding: unconditional residual scan MISSES")
        print("    conditional signals. vol_ratio_5_20 has zero unconditional")
        print("    predictive power but conditional timing value within E5-ema21D1.")
    else:
        print("  → Vol compression gate LACKS temporal stability.")
        print("    exp34's Sharpe improvement is period-specific, not robust.")
        if not all_selective:
            print(f"    Selectivity: {selectivity_verdict}")
        if "BEAR-ONLY" in regime_verdict or "BULL-ONLY" in regime_verdict:
            print(f"    Regime analysis confirms: {regime_verdict}")

    # ── Save ──────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp42_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
