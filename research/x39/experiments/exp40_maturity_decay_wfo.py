#!/usr/bin/env python3
"""Exp 40: Trend Maturity Decay Walk-Forward Validation.

Tests temporal robustness of exp38's maturity decay via anchored WFO (4 windows).
Per window: sweep 18 configs on training period, test selected + fixed + baseline.

Usage:
    python -m research.x39.experiments.exp40_maturity_decay_wfo
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.experiments.exp38_trend_maturity_decay import (  # noqa: E402
    compute_trend_age,
    effective_trail,
)
from research.x39.experiments.exp30_and_gate_walk_forward import (  # noqa: E402
    find_bar_idx,
)
from research.x39.explore import compute_features, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
TRAIL_BASE = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365

# ── Parameter grid (same as exp38) ───────────────────────────────────────
TRAIL_MINS = [1.5, 2.0, 2.5]
DECAY_STARTS = [30, 60]       # H4 bars
DECAY_ENDS = [120, 180, 240]  # H4 bars

# ── Fixed config (exp38 global optimum) ──────────────────────────────────
FIXED_TRAIL_MIN = 1.5
FIXED_DECAY_START = 60
FIXED_DECAY_END = 180

# ── Anchored WFO Windows (identical to exp30) ───────────────────────────
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


def run_backtest(
    feat: pd.DataFrame,
    trend_age: np.ndarray,
    start_bar: int,
    end_bar: int,
    *,
    trail_min: float | None = None,
    decay_start: int | None = None,
    decay_end: int | None = None,
) -> dict:
    """Replay E5-ema21D1 with optional maturity decay on bar range [start_bar, end_bar).

    All None = baseline (fixed trail=3.0).
    All set = maturity decay.
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values

    is_decay = trail_min is not None
    cost = COST_BPS / 10_000

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    n_bars = end_bar - start_bar
    equity = np.full(n_bars, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    trail_at_exit: list[float] = []
    age_at_exit: list[int] = []

    for i in range(start_bar, end_bar):
        ei = i - start_bar
        if np.isnan(ratr[i]):
            equity[ei] = cash
            continue

        if not in_pos:
            equity[ei] = cash
            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )
            if entry_ok:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / c[i]
                cash = 0.0
        else:
            equity[ei] = position_size * c[i]
            peak = max(peak, c[i])

            if is_decay:
                current_trail = effective_trail(
                    trend_age[i], TRAIL_BASE, trail_min, decay_start, decay_end,
                )
            else:
                current_trail = TRAIL_BASE

            trail_stop = peak - current_trail * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost

                trail_at_exit.append(current_trail)
                age_at_exit.append(int(trend_age[i]))

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "exit_reason": exit_reason,
                    "win": int(net_ret > 0),
                    "trend_age_at_exit": int(trend_age[i]),
                    "effective_trail_at_exit": current_trail,
                })

                equity[ei] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # Force-close any open position at window end
    if in_pos:
        last = end_bar - 1
        ei = last - start_bar
        half_cost = (COST_BPS / 2) / 10_000
        cash = position_size * c[last] * (1 - half_cost)
        gross_ret = (c[last] - entry_price) / entry_price
        net_ret = gross_ret - cost

        current_trail = (
            effective_trail(trend_age[last], TRAIL_BASE, trail_min, decay_start, decay_end)
            if is_decay
            else TRAIL_BASE
        )
        trail_at_exit.append(current_trail)
        age_at_exit.append(int(trend_age[last]))

        trades.append({
            "entry_bar": entry_bar,
            "exit_bar": last,
            "bars_held": last - entry_bar,
            "gross_ret": gross_ret,
            "net_ret": net_ret,
            "exit_reason": "window_end",
            "win": int(net_ret > 0),
            "trend_age_at_exit": int(trend_age[last]),
            "effective_trail_at_exit": current_trail,
        })
        equity[ei] = cash

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity).dropna()

    if len(eq) < 2 or len(trades) == 0:
        return {
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan,
            "avg_trend_age_exit": np.nan, "avg_eff_trail_exit": np.nan,
        }

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

    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["win"] == 1]

    return {
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_trend_age_exit": round(np.mean(age_at_exit), 1) if age_at_exit else np.nan,
        "avg_eff_trail_exit": round(np.mean(trail_at_exit), 3) if trail_at_exit else np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    configs = [
        (tm, ds, de)
        for tm in TRAIL_MINS
        for ds in DECAY_STARTS
        for de in DECAY_ENDS
        if ds < de
    ]

    print("=" * 80)
    print("EXP 40: Trend Maturity Decay Walk-Forward Validation")
    print(f"  Grid: trail_min={TRAIL_MINS}, decay_start={DECAY_STARTS}, decay_end={DECAY_ENDS}")
    print(f"  Valid configs: {len(configs)}")
    print(f"  Fixed: min={FIXED_TRAIL_MIN}, start={FIXED_DECAY_START}, end={FIXED_DECAY_END}")
    print(f"  Windows: {len(WFO_WINDOWS)} (anchored)")
    print(f"  Cost: {COST_BPS} bps RT, warmup: {WARMUP_DAYS} days")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    datetimes = pd.DatetimeIndex(feat["datetime"])

    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    trend_age = compute_trend_age(ema_f, ema_s)
    print(f"\nTrend age computed: max={trend_age.max()}")

    bars_per_day = 24 / 4
    warmup_bars = int(WARMUP_DAYS * bars_per_day)

    window_results: list[dict] = []

    for w_idx, w in enumerate(WFO_WINDOWS):
        print(f"\n{'─' * 80}")
        print(f"WINDOW {w_idx + 1}/{len(WFO_WINDOWS)}")
        print(f"  Train: {w['train_start']} → {w['train_end']}")
        print(f"  Test:  {w['test_start']} → {w['test_end']}")

        raw_train_start = find_bar_idx(datetimes, w["train_start"], "start")
        train_end = find_bar_idx(datetimes, w["train_end"], "end")
        test_start = find_bar_idx(datetimes, w["test_start"], "start")
        test_end = find_bar_idx(datetimes, w["test_end"], "end")

        # Apply warmup within train window
        train_start = raw_train_start + warmup_bars
        if train_start >= train_end:
            print(f"  WARNING: warmup exceeds train window, skipping")
            continue

        print(f"  Raw train start:  bar {raw_train_start}")
        print(f"  Warmup train start: bar {train_start} (+{warmup_bars} warmup)")
        print(f"  Train bars: [{train_start}, {train_end}) = {train_end - train_start}")
        print(f"  Test bars:  [{test_start}, {test_end}) = {test_end - test_start}")
        if train_start < len(datetimes) and test_end - 1 < len(datetimes):
            print(f"  Train actual: {datetimes[train_start].date()} → {datetimes[train_end - 1].date()}")
            print(f"  Test actual:  {datetimes[test_start].date()} → {datetimes[test_end - 1].date()}")
        print(f"{'─' * 80}")

        # ── Step 1: Train — sweep 18 configs ─────────────────────────
        print(f"\n  [TRAIN] Sweeping {len(configs)} configs...")

        best_train_sharpe = -np.inf
        best_cfg: tuple[float, int, int] = configs[0]
        train_grid: list[tuple[float, int, int, float]] = []

        for trail_min, decay_start, decay_end in configs:
            r = run_backtest(
                feat, trend_age, train_start, train_end,
                trail_min=trail_min, decay_start=decay_start, decay_end=decay_end,
            )
            train_grid.append((trail_min, decay_start, decay_end, r["sharpe"]))
            if np.isfinite(r["sharpe"]) and r["sharpe"] > best_train_sharpe:
                best_train_sharpe = r["sharpe"]
                best_cfg = (trail_min, decay_start, decay_end)

        train_baseline = run_backtest(feat, trend_age, train_start, train_end)

        print(f"  Train baseline: Sharpe={train_baseline['sharpe']}, "
              f"trades={train_baseline['trades']}")
        print(f"  Best train config: min={best_cfg[0]}, start={best_cfg[1]}, "
              f"end={best_cfg[2]}, Sharpe={best_train_sharpe:.4f}")
        print(f"  Train d_Sharpe (best vs base): "
              f"{best_train_sharpe - train_baseline['sharpe']:+.4f}")

        # Print train grid summary
        print("  Train grid (top 5 by Sharpe):")
        sorted_grid = sorted(train_grid, key=lambda x: x[3] if np.isfinite(x[3]) else -999, reverse=True)
        for tm, ds, de, sh in sorted_grid[:5]:
            marker = " *" if (tm, ds, de) == best_cfg else "  "
            print(f"    min={tm}, start={ds:>3d}, end={de:>3d}  "
                  f"Sharpe={sh:.4f}{marker}")

        # ── Step 2: Test — baseline, selected, fixed ──────────────────
        print(f"\n  [TEST] Running on test period...")

        test_baseline = run_backtest(feat, trend_age, test_start, test_end)
        test_selected = run_backtest(
            feat, trend_age, test_start, test_end,
            trail_min=best_cfg[0], decay_start=best_cfg[1], decay_end=best_cfg[2],
        )
        test_fixed = run_backtest(
            feat, trend_age, test_start, test_end,
            trail_min=FIXED_TRAIL_MIN, decay_start=FIXED_DECAY_START,
            decay_end=FIXED_DECAY_END,
        )

        def delta(a: float, b: float) -> float:
            return round(a - b, 4) if np.isfinite(a) and np.isfinite(b) else np.nan

        d_sh_sel = delta(test_selected["sharpe"], test_baseline["sharpe"])
        d_mdd_sel = delta(test_selected["mdd_pct"], test_baseline["mdd_pct"])
        d_sh_fix = delta(test_fixed["sharpe"], test_baseline["sharpe"])
        d_mdd_fix = delta(test_fixed["mdd_pct"], test_baseline["mdd_pct"])

        print(f"  Test baseline:  Sharpe={test_baseline['sharpe']:>8.4f}, "
              f"CAGR={test_baseline['cagr_pct']:>7.2f}%, "
              f"MDD={test_baseline['mdd_pct']:>5.2f}%, "
              f"trades={test_baseline['trades']}")
        print(f"  Test selected:  Sharpe={test_selected['sharpe']:>8.4f} "
              f"(d={d_sh_sel:+.4f}), "
              f"CAGR={test_selected['cagr_pct']:>7.2f}%, "
              f"MDD={test_selected['mdd_pct']:>5.2f}% (d={d_mdd_sel:+.2f}pp), "
              f"trades={test_selected['trades']}, "
              f"avg_trail={test_selected['avg_eff_trail_exit']}")
        print(f"  Test fixed:     Sharpe={test_fixed['sharpe']:>8.4f} "
              f"(d={d_sh_fix:+.4f}), "
              f"CAGR={test_fixed['cagr_pct']:>7.2f}%, "
              f"MDD={test_fixed['mdd_pct']:>5.2f}% (d={d_mdd_fix:+.2f}pp), "
              f"trades={test_fixed['trades']}, "
              f"avg_trail={test_fixed['avg_eff_trail_exit']}")

        window_results.append({
            "window": w_idx + 1,
            "train_period": f"{w['train_start']} → {w['train_end']}",
            "test_period": f"{w['test_start']} → {w['test_end']}",
            "train_bars": train_end - train_start,
            "test_bars": test_end - test_start,
            "train_baseline_sharpe": train_baseline["sharpe"],
            "train_best_sharpe": round(best_train_sharpe, 4),
            "selected_trail_min": best_cfg[0],
            "selected_decay_start": best_cfg[1],
            "selected_decay_end": best_cfg[2],
            "test_baseline_sharpe": test_baseline["sharpe"],
            "test_baseline_cagr": test_baseline["cagr_pct"],
            "test_baseline_mdd": test_baseline["mdd_pct"],
            "test_baseline_trades": test_baseline["trades"],
            "test_selected_sharpe": test_selected["sharpe"],
            "test_selected_cagr": test_selected["cagr_pct"],
            "test_selected_mdd": test_selected["mdd_pct"],
            "test_selected_trades": test_selected["trades"],
            "test_selected_avg_trail": test_selected["avg_eff_trail_exit"],
            "test_selected_avg_age": test_selected["avg_trend_age_exit"],
            "d_sharpe_selected": d_sh_sel,
            "d_mdd_selected": d_mdd_sel,
            "selected_wins_sharpe": int(np.isfinite(d_sh_sel) and d_sh_sel > 0),
            "test_fixed_sharpe": test_fixed["sharpe"],
            "test_fixed_cagr": test_fixed["cagr_pct"],
            "test_fixed_mdd": test_fixed["mdd_pct"],
            "test_fixed_trades": test_fixed["trades"],
            "test_fixed_avg_trail": test_fixed["avg_eff_trail_exit"],
            "test_fixed_avg_age": test_fixed["avg_trend_age_exit"],
            "d_sharpe_fixed": d_sh_fix,
            "d_mdd_fixed": d_mdd_fix,
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

    print(f"\n  TRAIN-SELECTED CONFIG:")
    print(f"    WFO win rate:       {sel_wins}/{len(df)} = {sel_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {sel_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_selected']]}")
    print(f"    Mean d_MDD:         {sel_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_selected']]}")

    # ── Fixed config ──────────────────────────────────────────────────
    fix_wins = df["fixed_wins_sharpe"].sum()
    fix_wr = fix_wins / len(df)
    fix_mean = df["d_sharpe_fixed"].mean()
    fix_mdd_mean = df["d_mdd_fixed"].mean()

    print(f"\n  FIXED CONFIG (min={FIXED_TRAIL_MIN}, start={FIXED_DECAY_START}, end={FIXED_DECAY_END}):")
    print(f"    WFO win rate:       {fix_wins}/{len(df)} = {fix_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {fix_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_fixed']]}")
    print(f"    Mean d_MDD:         {fix_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_fixed']]}")

    # ── Parameter stability ───────────────────────────────────────────
    print(f"\n  PARAMETER STABILITY:")
    for _, row in df.iterrows():
        print(f"    W{int(row['window'])}: min={row['selected_trail_min']}, "
              f"start={int(row['selected_decay_start'])}, "
              f"end={int(row['selected_decay_end'])}")
    unique_configs = df[["selected_trail_min", "selected_decay_start", "selected_decay_end"]].drop_duplicates()
    n_unique = len(unique_configs)
    stability = "STABLE" if n_unique <= 2 else ("MODERATE" if n_unique <= 3 else "UNSTABLE")
    print(f"    Unique configs: {n_unique}/4 → {stability}")

    # ── Fixed vs selected ─────────────────────────────────────────────
    print(f"\n  FIXED vs SELECTED (per window):")
    for _, row in df.iterrows():
        winner = "SEL" if row["d_sharpe_selected"] > row["d_sharpe_fixed"] else "FIX"
        print(f"    W{int(row['window'])}: sel d_Sh={row['d_sharpe_selected']:+.4f}, "
              f"fix d_Sh={row['d_sharpe_fixed']:+.4f} → {winner}")

    # ── Bear vs bull regime analysis ──────────────────────────────────
    print(f"\n  BEAR vs BULL REGIME:")
    print(f"    W1 (2021-07→2023-06, bear): sel d_Sh={df.iloc[0]['d_sharpe_selected']:+.4f}, "
          f"fix d_Sh={df.iloc[0]['d_sharpe_fixed']:+.4f}")
    print(f"    W2 (2022-07→2024-06, bear→bull): sel d_Sh={df.iloc[1]['d_sharpe_selected']:+.4f}, "
          f"fix d_Sh={df.iloc[1]['d_sharpe_fixed']:+.4f}")
    print(f"    W3 (2023-07→2025-06, bull): sel d_Sh={df.iloc[2]['d_sharpe_selected']:+.4f}, "
          f"fix d_Sh={df.iloc[2]['d_sharpe_fixed']:+.4f}")
    print(f"    W4 (2024-07→2026-02, bull): sel d_Sh={df.iloc[3]['d_sharpe_selected']:+.4f}, "
          f"fix d_Sh={df.iloc[3]['d_sharpe_fixed']:+.4f}")

    bear_wins = sum(1 for i in [0, 1] if df.iloc[i]["d_sharpe_fixed"] > 0)
    bull_wins = sum(1 for i in [2, 3] if df.iloc[i]["d_sharpe_fixed"] > 0)
    print(f"    Fixed: bear windows {bear_wins}/2, bull windows {bull_wins}/2")
    if bear_wins > 0 and bull_wins > 0:
        print("    → Maturity decay helps in BOTH regimes (breaks exp30 pattern)")
    elif bear_wins > bull_wins:
        print("    → Bear-only benefit (same pattern as exp30 AND gate)")
    elif bull_wins > bear_wins:
        print("    → Bull-only benefit")
    else:
        print("    → No consistent regime pattern")

    # ═══════════════════════════════════════════════════════════════════
    # Effective trail analysis
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n  EFFECTIVE TRAIL AT EXIT (test periods):")
    for _, row in df.iterrows():
        print(f"    W{int(row['window'])}: selected avg_trail={row['test_selected_avg_trail']}, "
              f"avg_age={row['test_selected_avg_age']}, "
              f"fixed avg_trail={row['test_fixed_avg_trail']}, "
              f"avg_age={row['test_fixed_avg_age']}")

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

    print(f"\n  FIXED (min={FIXED_TRAIL_MIN}, start={FIXED_DECAY_START}, end={FIXED_DECAY_END}):")
    print(f"    WFO win rate >= 75%:  {'PASS' if fix_pass_wr else 'FAIL'} ({fix_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if fix_pass_mean else 'FAIL'} ({fix_mean:+.4f})")
    fix_overall = "PASS" if fix_pass_wr and fix_pass_mean else "FAIL"
    print(f"    Overall:              {fix_overall}")

    print(f"\n  Parameter stability:    {stability} ({n_unique} unique)")

    verdict = "PASS" if sel_overall == "PASS" or fix_overall == "PASS" else "FAIL"
    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  MATURITY DECAY WFO VERDICT: {verdict:4s}                          ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")

    if verdict == "PASS":
        print("  → Maturity decay has temporal stability. First robust x39 mechanism.")
        print("  → exp38's +0.150 Sharpe / -9.82pp MDD is NOT period-specific.")
    else:
        print("  → Maturity decay LACKS temporal stability.")
        print("    exp38's improvements are period-specific (same as exp30 AND gate).")

    # ── Save ──────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp40_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
