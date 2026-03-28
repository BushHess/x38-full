#!/usr/bin/env python3
"""Exp 30: AND-Gate Walk-Forward Validation.

Tests temporal robustness of exp22's AND gate (rp=0.20, tq=-0.10) using
anchored walk-forward with 4 windows. Train window grows, test window ~2 years.

For each window:
  1. Train: sweep 16 configs, pick best Sharpe on training period
  2. Test: apply train-selected AND fixed (0.20, -0.10) on unseen test period
  3. Measure d_Sharpe, d_MDD vs baseline (no AND gate)

Usage:
    python -m research.x39.experiments.exp30_and_gate_walk_forward
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

# ── WFO sweep grid (from spec) ──────────────────────────────────────────
RP_THRESHOLDS = [0.15, 0.20, 0.25, 0.30]
TQ_THRESHOLDS = [-0.30, -0.10, 0.10, 0.30]

# ── Fixed config from exp22's full-sample optimum ───────────────────────
FIXED_RP = 0.20
FIXED_TQ = -0.10

# ── Anchored WFO Windows ───────────────────────────────────────────────
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
# Backtest engine (adapted from exp22, with bar-range support)
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(
    feat: pd.DataFrame,
    rp_threshold: float | None,
    tq_threshold: float | None,
    start_bar: int,
    end_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional AND-gated exit on bar range [start_bar, end_bar).

    rp/tq both None = baseline (no supplementary exit).
    rp/tq both set = AND gate.
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    trendq = feat["trendq_84"].values

    mode_and = rp_threshold is not None and tq_threshold is not None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "and_gate": 0}
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    n_bars = end_bar - start_bar
    equity = np.full(n_bars, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

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
            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"
            elif mode_and:
                rp_ok = np.isfinite(rangepos[i]) and rangepos[i] < rp_threshold
                tq_ok = np.isfinite(trendq[i]) and trendq[i] < tq_threshold
                if rp_ok and tq_ok:
                    exit_reason = "and_gate"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost
                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "exit_reason": exit_reason,
                    "win": int(net_ret > 0),
                })
                exit_counts[exit_reason] += 1
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
        trades.append({
            "entry_bar": entry_bar,
            "exit_bar": last,
            "bars_held": last - entry_bar,
            "gross_ret": gross_ret,
            "net_ret": net_ret,
            "exit_reason": "window_end",
            "win": int(net_ret > 0),
        })
        equity[ei] = cash

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity).dropna()

    if len(eq) < 2 or len(trades) == 0:
        return {
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_and_gate": 0,
            "and_selectivity": np.nan,
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

    supp_trades = tdf[tdf["exit_reason"] == "and_gate"]
    selectivity = np.nan
    if len(supp_trades) > 0:
        selectivity = round((supp_trades["win"] == 0).sum() / len(supp_trades) * 100, 1)

    return {
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "exit_trail": exit_counts["trail"],
        "exit_trend": exit_counts["trend"],
        "exit_and_gate": exit_counts["and_gate"],
        "and_selectivity": selectivity,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Date → bar index mapping
# ═══════════════════════════════════════════════════════════════════════════

def find_bar_idx(datetimes: pd.DatetimeIndex, date_str: str, side: str) -> int:
    """Map a date boundary to a bar index.

    side="start": first bar >= date  (inclusive start)
    side="end":   first bar > date   (exclusive end, i.e. last bar <= date + 1)
    """
    dt = pd.Timestamp(date_str)
    if side == "start":
        mask = datetimes >= dt
        if not mask.any():
            return len(datetimes)
        return int(np.argmax(mask))
    else:
        # exclusive end: first bar AFTER the end date
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
    print("EXP 30: AND-Gate Walk-Forward Validation")
    print(f"  Grid: rp={RP_THRESHOLDS}, tq={TQ_THRESHOLDS} ({len(RP_THRESHOLDS) * len(TQ_THRESHOLDS)} configs)")
    print(f"  Fixed: rp={FIXED_RP}, tq={FIXED_TQ}")
    print(f"  Windows: {len(WFO_WINDOWS)} (anchored)")
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
        print(f"\n  [TRAIN] Sweeping {len(RP_THRESHOLDS)*len(TQ_THRESHOLDS)} configs...")

        best_train_sharpe = -np.inf
        best_rp: float = RP_THRESHOLDS[0]
        best_tq: float = TQ_THRESHOLDS[0]
        train_grid: list[tuple[float, float, float]] = []

        for rp in RP_THRESHOLDS:
            for tq in TQ_THRESHOLDS:
                r = run_backtest(feat, rp, tq, train_start, train_end)
                train_grid.append((rp, tq, r["sharpe"]))
                if np.isfinite(r["sharpe"]) and r["sharpe"] > best_train_sharpe:
                    best_train_sharpe = r["sharpe"]
                    best_rp = rp
                    best_tq = tq

        train_baseline = run_backtest(feat, None, None, train_start, train_end)

        print(f"  Train baseline: Sharpe={train_baseline['sharpe']}, "
              f"trades={train_baseline['trades']}")
        print(f"  Best train config: rp={best_rp}, tq={best_tq}, "
              f"Sharpe={best_train_sharpe:.4f}")

        # Print train grid
        print("  Train grid (Sharpe):")
        print(f"    {'rp\\tq':>8s}", end="")
        for tq in TQ_THRESHOLDS:
            print(f"  {tq:>7.2f}", end="")
        print()
        for rp in RP_THRESHOLDS:
            print(f"    {rp:>8.2f}", end="")
            for tq in TQ_THRESHOLDS:
                sh = next(s for r, t, s in train_grid if r == rp and t == tq)
                marker = " *" if rp == best_rp and tq == best_tq else "  "
                print(f"  {sh:>6.4f}{marker[1]}", end="")
            print()

        # ── Step 2: Test — baseline, selected, fixed ──────────────────
        print(f"\n  [TEST] Running on test period...")

        test_baseline = run_backtest(feat, None, None, test_start, test_end)
        test_selected = run_backtest(feat, best_rp, best_tq, test_start, test_end)
        test_fixed = run_backtest(feat, FIXED_RP, FIXED_TQ, test_start, test_end)

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
              f"AND_exits={test_selected['exit_and_gate']}")
        print(f"  Test fixed:     Sharpe={test_fixed['sharpe']:>8.4f} "
              f"(d={d_sh_fix:+.4f}), "
              f"CAGR={test_fixed['cagr_pct']:>7.2f}%, "
              f"MDD={test_fixed['mdd_pct']:>5.2f}% (d={d_mdd_fix:+.2f}pp), "
              f"trades={test_fixed['trades']}, "
              f"AND_exits={test_fixed['exit_and_gate']}")

        window_results.append({
            "window": w_idx + 1,
            "train_period": f"{w['train_start']} → {w['train_end']}",
            "test_period": f"{w['test_start']} → {w['test_end']}",
            "train_bars": train_end - train_start,
            "test_bars": test_end - test_start,
            "train_baseline_sharpe": train_baseline["sharpe"],
            "train_best_sharpe": round(best_train_sharpe, 4),
            "selected_rp": best_rp,
            "selected_tq": best_tq,
            "test_baseline_sharpe": test_baseline["sharpe"],
            "test_baseline_cagr": test_baseline["cagr_pct"],
            "test_baseline_mdd": test_baseline["mdd_pct"],
            "test_baseline_trades": test_baseline["trades"],
            "test_selected_sharpe": test_selected["sharpe"],
            "test_selected_cagr": test_selected["cagr_pct"],
            "test_selected_mdd": test_selected["mdd_pct"],
            "test_selected_trades": test_selected["trades"],
            "test_selected_and_exits": test_selected["exit_and_gate"],
            "test_selected_selectivity": test_selected["and_selectivity"],
            "d_sharpe_selected": d_sh_sel,
            "d_mdd_selected": d_mdd_sel,
            "selected_wins_sharpe": int(np.isfinite(d_sh_sel) and d_sh_sel > 0),
            "test_fixed_sharpe": test_fixed["sharpe"],
            "test_fixed_cagr": test_fixed["cagr_pct"],
            "test_fixed_mdd": test_fixed["mdd_pct"],
            "test_fixed_trades": test_fixed["trades"],
            "test_fixed_and_exits": test_fixed["exit_and_gate"],
            "test_fixed_selectivity": test_fixed["and_selectivity"],
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

    print(f"\n  FIXED CONFIG (rp={FIXED_RP}, tq={FIXED_TQ}):")
    print(f"    WFO win rate:       {fix_wins}/{len(df)} = {fix_wr * 100:.0f}%")
    print(f"    Mean d_Sharpe:      {fix_mean:+.4f}")
    print(f"    d_Sharpe per window: {[round(x, 4) for x in df['d_sharpe_fixed']]}")
    print(f"    Mean d_MDD:         {fix_mdd_mean:+.2f} pp")
    print(f"    d_MDD per window:    {[round(x, 2) for x in df['d_mdd_fixed']]}")

    # ── Parameter stability ───────────────────────────────────────────
    print(f"\n  PARAMETER STABILITY:")
    for _, row in df.iterrows():
        print(f"    W{int(row['window'])}: rp={row['selected_rp']}, tq={row['selected_tq']}")
    unique_configs = df[["selected_rp", "selected_tq"]].drop_duplicates()
    n_unique = len(unique_configs)
    stability = "STABLE" if n_unique <= 2 else ("MODERATE" if n_unique <= 3 else "UNSTABLE")
    print(f"    Unique configs: {n_unique}/4 → {stability}")

    # ── Fixed vs selected ─────────────────────────────────────────────
    print(f"\n  FIXED vs SELECTED (per window):")
    for _, row in df.iterrows():
        winner = "SEL" if row["d_sharpe_selected"] > row["d_sharpe_fixed"] else "FIX"
        print(f"    W{int(row['window'])}: sel d_Sh={row['d_sharpe_selected']:+.4f}, "
              f"fix d_Sh={row['d_sharpe_fixed']:+.4f} → {winner}")

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

    print(f"\n  FIXED (rp={FIXED_RP}, tq={FIXED_TQ}):")
    print(f"    WFO win rate >= 75%:  {'PASS' if fix_pass_wr else 'FAIL'} ({fix_wr * 100:.0f}%)")
    print(f"    Mean d_Sharpe > 0:    {'PASS' if fix_pass_mean else 'FAIL'} ({fix_mean:+.4f})")
    fix_overall = "PASS" if fix_pass_wr and fix_pass_mean else "FAIL"
    print(f"    Overall:              {fix_overall}")

    print(f"\n  Parameter stability:    {stability} ({n_unique} unique)")

    and_gate_verdict = "PASS" if sel_overall == "PASS" or fix_overall == "PASS" else "FAIL"
    print(f"\n  ╔══════════════════════════════════════════╗")
    print(f"  ║  AND-GATE WFO VERDICT: {and_gate_verdict:4s}               ║")
    print(f"  ╚══════════════════════════════════════════╝")

    if and_gate_verdict == "PASS":
        print("  → AND gate has temporal stability. Proceed with exp25/26/27 findings.")
    else:
        print("  → AND gate LACKS temporal stability. Full-sample improvement is period-specific.")
        print("    The +0.057 Sharpe from exp22 should NOT be relied upon.")

    # ── Save ──────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp30_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
