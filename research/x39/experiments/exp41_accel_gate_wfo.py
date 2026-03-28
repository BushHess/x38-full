#!/usr/bin/env python3
"""Exp 41: Momentum Acceleration Gate Walk-Forward Validation.

Tests temporal robustness of exp33's accel gate (best: lb=12, min_accel=0.0)
using anchored walk-forward with 4 windows.

For each window:
  1. Train: sweep 12 configs (4 lookbacks × 3 min_accels), pick best Sharpe
  2. Test: apply train-selected + fixed (lb=12, min_accel=0.0) + baseline
  3. Measure d_Sharpe, d_MDD, blocked entries, exposure reduction

Usage:
    python -m research.x39.experiments.exp41_accel_gate_wfo
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

# ── WFO sweep grid (from spec, same as exp33) ────────────────────────────
LOOKBACKS = [3, 6, 12, 24]
MIN_ACCELS = [0.0, 0.001, 0.002]

# ── Fixed config from exp33's global optimum ──────────────────────────────
FIXED_LB = 12
FIXED_ACCEL = 0.0

# ── Anchored WFO Windows (identical to exp30/exp40) ──────────────────────
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
# Backtest engine (from exp33, adapted for bar-range support)
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(
    feat: pd.DataFrame,
    lookback: int | None,
    min_accel: float | None,
    start_bar: int,
    end_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional momentum acceleration gate on bar range.

    lookback/min_accel both None = baseline (no accel gate).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n_total = len(c)

    # Compute ema_spread and ema_spread_roc
    with np.errstate(divide="ignore", invalid="ignore"):
        ema_spread = np.where(ema_s != 0, (ema_f - ema_s) / ema_s, np.nan)

    ema_spread_roc = np.full(n_total, np.nan)
    if lookback is not None and lookback < n_total:
        ema_spread_roc[lookback:] = ema_spread[lookback:] - ema_spread[:n_total - lookback]

    mode_accel = lookback is not None

    trades: list[dict] = []
    blocked_entries: list[int] = []
    in_pos = False
    peak = 0.0
    entry_bar_idx = 0
    entry_price = 0.0

    # Warmup: skip SLOW_PERIOD bars from start of window
    actual_start = start_bar + SLOW_PERIOD
    if actual_start >= end_bar:
        return _empty_result(lookback, min_accel)

    n_bars = end_bar - actual_start
    equity = np.full(n_bars, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(actual_start, end_bar):
        ei = i - actual_start
        if np.isnan(ratr[i]):
            equity[ei] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[ei] = cash

            base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if base_ok:
                accel_ok = True
                if mode_accel:
                    if np.isfinite(ema_spread_roc[i]):
                        accel_ok = ema_spread_roc[i] > min_accel
                    else:
                        accel_ok = False

                if accel_ok:
                    in_pos = True
                    entry_bar_idx = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
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
        return _empty_result(lookback, min_accel)

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

    return {
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
    }


def _empty_result(
    lookback: int | None,
    min_accel: float | None,
) -> dict:
    _ = lookback, min_accel
    return {
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "exposure_pct": np.nan,
        "blocked": 0, "blocked_win_rate": np.nan,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Date → bar index mapping (from exp30)
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

    n_configs = len(LOOKBACKS) * len(MIN_ACCELS)
    print("=" * 80)
    print("EXP 41: Momentum Acceleration Gate Walk-Forward Validation")
    print(f"  Grid: lb={LOOKBACKS}, min_accel={MIN_ACCELS} ({n_configs} configs)")
    print(f"  Fixed: lb={FIXED_LB}, min_accel={FIXED_ACCEL}")
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
        print(f"\n  [TRAIN] Sweeping {n_configs} configs...")

        best_train_sharpe = -np.inf
        best_lb: int = LOOKBACKS[0]
        best_accel: float = MIN_ACCELS[0]
        train_grid: list[tuple[int, float, float]] = []

        for lb in LOOKBACKS:
            for ma in MIN_ACCELS:
                r = run_backtest(feat, lb, ma, train_start, train_end)
                train_grid.append((lb, ma, r["sharpe"]))
                if np.isfinite(r["sharpe"]) and r["sharpe"] > best_train_sharpe:
                    best_train_sharpe = r["sharpe"]
                    best_lb = lb
                    best_accel = ma

        train_baseline = run_backtest(feat, None, None, train_start, train_end)

        print(f"  Train baseline: Sharpe={train_baseline['sharpe']}, "
              f"trades={train_baseline['trades']}")
        print(f"  Best train config: lb={best_lb}, min_accel={best_accel}, "
              f"Sharpe={best_train_sharpe:.4f}")

        # Print train grid
        print("  Train grid (Sharpe):")
        print(f"    {'lb\\accel':>10s}", end="")
        for ma in MIN_ACCELS:
            print(f"  {ma:>7.3f}", end="")
        print()
        for lb in LOOKBACKS:
            print(f"    {lb:>10d}", end="")
            for ma in MIN_ACCELS:
                sh = next(s for l, m, s in train_grid if l == lb and m == ma)
                marker = "*" if lb == best_lb and ma == best_accel else " "
                print(f"  {sh:>6.4f}{marker}", end="")
            print()

        # ── Step 2: Test — baseline, selected, fixed ──────────────────
        print(f"\n  [TEST] Running on test period...")

        test_baseline = run_backtest(feat, None, None, test_start, test_end)
        test_selected = run_backtest(feat, best_lb, best_accel, test_start, test_end)
        test_fixed = run_backtest(feat, FIXED_LB, FIXED_ACCEL, test_start, test_end)

        def delta(a: float, b: float) -> float:
            return round(a - b, 4) if np.isfinite(a) and np.isfinite(b) else np.nan

        d_sh_sel = delta(test_selected["sharpe"], test_baseline["sharpe"])
        d_mdd_sel = delta(test_selected["mdd_pct"], test_baseline["mdd_pct"])
        d_exp_sel = delta(test_selected["exposure_pct"], test_baseline["exposure_pct"])
        d_sh_fix = delta(test_fixed["sharpe"], test_baseline["sharpe"])
        d_mdd_fix = delta(test_fixed["mdd_pct"], test_baseline["mdd_pct"])
        d_exp_fix = delta(test_fixed["exposure_pct"], test_baseline["exposure_pct"])

        print(f"  Test baseline:  Sharpe={test_baseline['sharpe']:>8.4f}, "
              f"CAGR={test_baseline['cagr_pct']:>7.2f}%, "
              f"MDD={test_baseline['mdd_pct']:>5.2f}%, "
              f"trades={test_baseline['trades']}, "
              f"exposure={test_baseline['exposure_pct']:.1f}%")
        print(f"  Test selected:  Sharpe={test_selected['sharpe']:>8.4f} "
              f"(d={d_sh_sel:+.4f}), "
              f"MDD={test_selected['mdd_pct']:>5.2f}% (d={d_mdd_sel:+.2f}pp), "
              f"trades={test_selected['trades']}, "
              f"blocked={test_selected['blocked']}, "
              f"blocked_WR={test_selected['blocked_win_rate']}, "
              f"exposure={test_selected['exposure_pct']:.1f}% (d={d_exp_sel:+.1f}pp)")
        print(f"  Test fixed:     Sharpe={test_fixed['sharpe']:>8.4f} "
              f"(d={d_sh_fix:+.4f}), "
              f"MDD={test_fixed['mdd_pct']:>5.2f}% (d={d_mdd_fix:+.2f}pp), "
              f"trades={test_fixed['trades']}, "
              f"blocked={test_fixed['blocked']}, "
              f"blocked_WR={test_fixed['blocked_win_rate']}, "
              f"exposure={test_fixed['exposure_pct']:.1f}% (d={d_exp_fix:+.1f}pp)")

        window_results.append({
            "window": w_idx + 1,
            "train_period": f"{w['train_start']} → {w['train_end']}",
            "test_period": f"{w['test_start']} → {w['test_end']}",
            "train_bars": train_end - train_start,
            "test_bars": test_end - test_start,
            "train_baseline_sharpe": train_baseline["sharpe"],
            "train_best_sharpe": round(best_train_sharpe, 4),
            "selected_lb": best_lb,
            "selected_accel": best_accel,
            # Baseline test
            "test_baseline_sharpe": test_baseline["sharpe"],
            "test_baseline_cagr": test_baseline["cagr_pct"],
            "test_baseline_mdd": test_baseline["mdd_pct"],
            "test_baseline_trades": test_baseline["trades"],
            "test_baseline_exposure": test_baseline["exposure_pct"],
            # Selected test
            "test_selected_sharpe": test_selected["sharpe"],
            "test_selected_cagr": test_selected["cagr_pct"],
            "test_selected_mdd": test_selected["mdd_pct"],
            "test_selected_trades": test_selected["trades"],
            "test_selected_blocked": test_selected["blocked"],
            "test_selected_blocked_wr": test_selected["blocked_win_rate"],
            "test_selected_exposure": test_selected["exposure_pct"],
            "d_sharpe_selected": d_sh_sel,
            "d_mdd_selected": d_mdd_sel,
            "d_exposure_selected": d_exp_sel,
            "selected_wins_sharpe": int(np.isfinite(d_sh_sel) and d_sh_sel > 0),
            # Fixed test
            "test_fixed_sharpe": test_fixed["sharpe"],
            "test_fixed_cagr": test_fixed["cagr_pct"],
            "test_fixed_mdd": test_fixed["mdd_pct"],
            "test_fixed_trades": test_fixed["trades"],
            "test_fixed_blocked": test_fixed["blocked"],
            "test_fixed_blocked_wr": test_fixed["blocked_win_rate"],
            "test_fixed_exposure": test_fixed["exposure_pct"],
            "d_sharpe_fixed": d_sh_fix,
            "d_mdd_fixed": d_mdd_fix,
            "d_exposure_fixed": d_exp_fix,
            "fixed_wins_sharpe": int(np.isfinite(d_sh_fix) and d_sh_fix > 0),
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
    sel_exp_mean = df["d_exposure_selected"].mean()

    print(f"\n  TRAIN-SELECTED CONFIG:")
    print(f"    WFO win rate:       {sel_wins}/{len(df)} = {sel_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {sel_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_selected']]}")
    print(f"    Mean d_MDD:         {sel_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_selected']]}")
    print(f"    Mean d_exposure:    {sel_exp_mean:+.1f} pp")

    # ── Fixed config ──────────────────────────────────────────────────
    fix_wins = df["fixed_wins_sharpe"].sum()
    fix_wr = fix_wins / len(df)
    fix_mean = df["d_sharpe_fixed"].mean()
    fix_mdd_mean = df["d_mdd_fixed"].mean()
    fix_exp_mean = df["d_exposure_fixed"].mean()

    print(f"\n  FIXED CONFIG (lb={FIXED_LB}, min_accel={FIXED_ACCEL}):")
    print(f"    WFO win rate:       {fix_wins}/{len(df)} = {fix_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {fix_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_fixed']]}")
    print(f"    Mean d_MDD:         {fix_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_fixed']]}")
    print(f"    Mean d_exposure:    {fix_exp_mean:+.1f} pp")

    # ── Parameter stability ───────────────────────────────────────────
    print(f"\n  PARAMETER STABILITY:")
    for _, row in df.iterrows():
        print(f"    W{int(row['window'])}: lb={int(row['selected_lb'])}, "
              f"min_accel={row['selected_accel']}")
    unique_configs = df[["selected_lb", "selected_accel"]].drop_duplicates()
    n_unique = len(unique_configs)
    stability = "STABLE" if n_unique <= 2 else ("MODERATE" if n_unique <= 3 else "UNSTABLE")
    print(f"    Unique configs: {n_unique}/4 → {stability}")

    # ── lb=12 consistency check ───────────────────────────────────────
    lb12_count = (df["selected_lb"] == 12).sum()
    print(f"    lb=12 selected: {lb12_count}/4 windows")

    # ── Fixed vs selected ─────────────────────────────────────────────
    print(f"\n  FIXED vs SELECTED (per window):")
    for _, row in df.iterrows():
        winner = "SEL" if row["d_sharpe_selected"] > row["d_sharpe_fixed"] else "FIX"
        print(f"    W{int(row['window'])}: sel d_Sh={row['d_sharpe_selected']:+.4f}, "
              f"fix d_Sh={row['d_sharpe_fixed']:+.4f} → {winner}")

    # ── Bear vs bull regime analysis ──────────────────────────────────
    print(f"\n  REGIME ANALYSIS (bear/bull asymmetry):")
    # W1 (2021-07→2023-06) covers crypto winter → bear-ish
    # W2 (2022-07→2024-06) covers deep bear + early recovery → bear
    # W3 (2023-07→2025-06) covers recovery + new ATH → bull
    # W4 (2024-07→2026-02) covers late bull → bull
    regime_labels = ["bear-ish", "bear", "bull", "bull"]
    for i, row in df.iterrows():
        label = regime_labels[int(row["window"]) - 1]
        print(f"    W{int(row['window'])} ({label:>8s}): "
              f"d_Sh(sel)={row['d_sharpe_selected']:+.4f}, "
              f"d_Sh(fix)={row['d_sharpe_fixed']:+.4f}, "
              f"blocked(fix)={int(row['test_fixed_blocked'])}, "
              f"d_exp(fix)={row['d_exposure_fixed']:+.1f}pp")

    bear_windows = df[df["window"].isin([1, 2])]
    bull_windows = df[df["window"].isin([3, 4])]
    bear_mean_fix = bear_windows["d_sharpe_fixed"].mean()
    bull_mean_fix = bull_windows["d_sharpe_fixed"].mean()
    print(f"    Bear mean d_Sh(fix): {bear_mean_fix:+.4f}")
    print(f"    Bull mean d_Sh(fix): {bull_mean_fix:+.4f}")

    asymmetry = abs(bear_mean_fix - bull_mean_fix)
    if bear_mean_fix > 0 and bull_mean_fix <= 0:
        regime_verdict = "BEAR-ONLY (regime-dependent)"
    elif bull_mean_fix > 0 and bear_mean_fix <= 0:
        regime_verdict = "BULL-ONLY (regime-dependent)"
    elif asymmetry > 0.2:
        regime_verdict = "ASYMMETRIC (strong regime bias)"
    elif bear_mean_fix > 0 and bull_mean_fix > 0:
        regime_verdict = "REGIME-ROBUST (helps in both)"
    else:
        regime_verdict = "NO BENEFIT (hurts in both)"
    print(f"    Regime verdict: {regime_verdict}")

    # ── Blocked entry analysis ────────────────────────────────────────
    print(f"\n  BLOCKED ENTRY ANALYSIS (fixed config):")
    for _, row in df.iterrows():
        bl = int(row["test_fixed_blocked"])
        bl_wr = row["test_fixed_blocked_wr"]
        base_wr = row["test_baseline_sharpe"]  # use actual WR not sharpe
        bl_wr_str = f"{bl_wr:.1f}%" if np.isfinite(bl_wr) else "N/A"
        print(f"    W{int(row['window'])}: {bl} blocked, blocked_WR={bl_wr_str}")

    # ═══════════════════════════════════════════════════════════════════
    # Verdict
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    sel_pass_wr = sel_wr >= 0.75
    sel_pass_mean = sel_mean > 0
    fix_pass_wr = fix_wr >= 0.75
    fix_pass_mean = fix_mean > 0

    print(f"\n  TRAIN-SELECTED:")
    print(f"    WFO win rate >= 75%:  {'PASS' if sel_pass_wr else 'FAIL'} ({sel_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if sel_pass_mean else 'FAIL'} ({sel_mean:+.4f})")
    sel_overall = "PASS" if sel_pass_wr and sel_pass_mean else "FAIL"
    print(f"    Overall:              {sel_overall}")

    print(f"\n  FIXED (lb={FIXED_LB}, min_accel={FIXED_ACCEL}):")
    print(f"    WFO win rate >= 75%:  {'PASS' if fix_pass_wr else 'FAIL'} ({fix_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if fix_pass_mean else 'FAIL'} ({fix_mean:+.4f})")
    fix_overall = "PASS" if fix_pass_wr and fix_pass_mean else "FAIL"
    print(f"    Overall:              {fix_overall}")

    print(f"\n  Parameter stability:    {stability} ({n_unique} unique)")
    print(f"  Regime pattern:         {regime_verdict}")

    accel_verdict = "PASS" if sel_overall == "PASS" or fix_overall == "PASS" else "FAIL"
    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  ACCEL GATE WFO VERDICT: {accel_verdict:4s}                              ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")

    if accel_verdict == "PASS":
        print("  → Accel gate has temporal stability. Timing mechanism is robust.")
        if regime_verdict.startswith("REGIME-ROBUST"):
            print("  → Improvement persists across bull AND bear regimes.")
        else:
            print(f"  → Note: {regime_verdict}")
    else:
        print("  → Accel gate LACKS temporal stability.")
        print("    exp33's +0.1515 Sharpe improvement is period-specific, not robust.")
        if "BEAR-ONLY" in regime_verdict or "BULL-ONLY" in regime_verdict:
            print(f"    Regime analysis confirms: {regime_verdict}")

    # ── Save ──────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp41_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
