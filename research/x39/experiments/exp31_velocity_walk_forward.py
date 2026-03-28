#!/usr/bin/env python3
"""Exp 31: Velocity Walk-Forward Validation.

Tests temporal robustness of exp28's velocity-based supplementary exits
using anchored walk-forward with 4 windows (same as exp30 for direct comparison).

Two configs:
  Config A — Velocity-only: delta_rp_6 < velocity_threshold
  Config C — Velocity + trendq AND: delta_rp_6 < vel_thr AND trendq_84 < tq_thr

N=6 is FIXED (not in training grid — exp28 showed N=6 is only viable window).

Usage:
    python -m research.x39.experiments.exp31_velocity_walk_forward
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

# ── Velocity parameter ────────────────────────────────────────────────────
VEL_WINDOW = 6  # FIXED — exp28 showed N=6 is only viable window

# ── Config A training grid ────────────────────────────────────────────────
A_VEL_THRESHOLDS = [-0.40, -0.30, -0.20, -0.10]

# ── Config C training grid ────────────────────────────────────────────────
C_VEL_THRESHOLDS = [-0.30, -0.20, -0.10]
C_TQ_THRESHOLDS = [-0.20, 0.00, 0.20]

# ── Fixed configs from exp28 full-sample optimum ──────────────────────────
FIXED_A_VEL = -0.30   # exp28 Part A best
FIXED_C_VEL = -0.20   # exp28 Part C best
FIXED_C_TQ = 0.00     # exp28 Part C best

# ── Anchored WFO Windows (identical to exp30) ────────────────────────────
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
# Velocity computation
# ═══════════════════════════════════════════════════════════════════════════

def compute_delta_rp(rangepos: np.ndarray, window: int) -> np.ndarray:
    """Compute rangepos velocity: delta_rp[i] = rangepos[i] - rangepos[i-window]."""
    delta = np.full_like(rangepos, np.nan)
    for i in range(window, len(rangepos)):
        if np.isfinite(rangepos[i]) and np.isfinite(rangepos[i - window]):
            delta[i] = rangepos[i] - rangepos[i - window]
    return delta


# ═══════════════════════════════════════════════════════════════════════════
# Backtest engine (adapted from exp28 + exp30 bar-range support)
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(
    feat: pd.DataFrame,
    delta_rp: np.ndarray,
    start_bar: int,
    end_bar: int,
    *,
    mode: str = "baseline",
    vel_threshold: float | None = None,
    tq_threshold: float | None = None,
) -> dict:
    """Replay E5-ema21D1 with optional velocity-based exit on bar range [start_bar, end_bar).

    Modes:
      "baseline"  — no supplementary exit
      "vel_only"  — exit when delta_rp_6 < vel_threshold
      "vel_tq"    — exit when delta_rp_6 < vel_threshold AND trendq_84 < tq_threshold
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    trendq = feat["trendq_84"].values

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "velocity": 0}
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
            elif mode == "vel_only" and vel_threshold is not None:
                if np.isfinite(delta_rp[i]) and delta_rp[i] < vel_threshold:
                    exit_reason = "velocity"
            elif mode == "vel_tq" and vel_threshold is not None and tq_threshold is not None:
                vel_neg = np.isfinite(delta_rp[i]) and delta_rp[i] < vel_threshold
                tq_low = np.isfinite(trendq[i]) and trendq[i] < tq_threshold
                if vel_neg and tq_low:
                    exit_reason = "velocity"

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
            "exit_trail": 0, "exit_trend": 0, "exit_velocity": 0,
            "vel_selectivity": np.nan,
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

    vel_trades = tdf[tdf["exit_reason"] == "velocity"]
    vel_selectivity = np.nan
    if len(vel_trades) > 0:
        vel_selectivity = round((vel_trades["win"] == 0).sum() / len(vel_trades) * 100, 1)

    return {
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "exit_trail": exit_counts["trail"],
        "exit_trend": exit_counts["trend"],
        "exit_velocity": exit_counts["velocity"],
        "vel_selectivity": vel_selectivity,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Date → bar index mapping (same as exp30)
# ═══════════════════════════════════════════════════════════════════════════

def find_bar_idx(datetimes: pd.DatetimeIndex, date_str: str, side: str) -> int:
    """Map a date boundary to a bar index.

    side="start": first bar >= date  (inclusive start)
    side="end":   first bar > date   (exclusive end)
    """
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

    n_a = len(A_VEL_THRESHOLDS)
    n_c = len(C_VEL_THRESHOLDS) * len(C_TQ_THRESHOLDS)

    print("=" * 80)
    print("EXP 31: Velocity Walk-Forward Validation")
    print(f"  Config A: velocity-only, N={VEL_WINDOW}, {n_a} configs/window")
    print(f"  Config C: velocity+trendq AND, N={VEL_WINDOW}, {n_c} configs/window")
    print(f"  Fixed A: vel={FIXED_A_VEL}")
    print(f"  Fixed C: vel={FIXED_C_VEL}, tq={FIXED_C_TQ}")
    print(f"  Windows: {len(WFO_WINDOWS)} (anchored, same as exp30)")
    print(f"  Cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    datetimes = pd.DatetimeIndex(feat["datetime"])

    # Pre-compute delta_rp once (N=6 fixed)
    rangepos = feat["rangepos_84"].values
    delta_rp = compute_delta_rp(rangepos, VEL_WINDOW)

    # Load exp30 results for comparison
    exp30_path = RESULTS_DIR / "exp30_results.csv"
    exp30_df = None
    if exp30_path.exists():
        exp30_df = pd.read_csv(exp30_path)
        print(f"  Loaded exp30 results for comparison ({len(exp30_df)} windows)")
    else:
        print("  exp30 results not found — skipping comparison")

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

        # ── Baseline on test period ──────────────────────────────────
        test_baseline = run_backtest(feat, delta_rp, test_start, test_end, mode="baseline")

        # ══════════════════════════════════════════════════════════════
        # CONFIG A — Velocity-only
        # ══════════════════════════════════════════════════════════════
        print(f"\n  [CONFIG A] Sweeping {n_a} velocity-only configs on train...")

        best_a_sharpe = -np.inf
        best_a_vel: float = A_VEL_THRESHOLDS[0]
        train_a_grid: list[tuple[float, float]] = []

        for vel in A_VEL_THRESHOLDS:
            r = run_backtest(feat, delta_rp, train_start, train_end,
                             mode="vel_only", vel_threshold=vel)
            train_a_grid.append((vel, r["sharpe"]))
            if np.isfinite(r["sharpe"]) and r["sharpe"] > best_a_sharpe:
                best_a_sharpe = r["sharpe"]
                best_a_vel = vel

        train_a_baseline = run_backtest(feat, delta_rp, train_start, train_end, mode="baseline")
        print(f"    Train baseline: Sharpe={train_a_baseline['sharpe']}")
        print(f"    Train grid: {[(v, f'{s:.4f}') for v, s in train_a_grid]}")
        print(f"    Best train A: vel={best_a_vel}, Sharpe={best_a_sharpe:.4f}")

        # Test: selected A
        test_a_sel = run_backtest(feat, delta_rp, test_start, test_end,
                                  mode="vel_only", vel_threshold=best_a_vel)
        # Test: fixed A
        test_a_fix = run_backtest(feat, delta_rp, test_start, test_end,
                                  mode="vel_only", vel_threshold=FIXED_A_VEL)

        d_sh_a_sel = round(test_a_sel["sharpe"] - test_baseline["sharpe"], 4)
        d_mdd_a_sel = round(test_a_sel["mdd_pct"] - test_baseline["mdd_pct"], 2)
        d_sh_a_fix = round(test_a_fix["sharpe"] - test_baseline["sharpe"], 4)
        d_mdd_a_fix = round(test_a_fix["mdd_pct"] - test_baseline["mdd_pct"], 2)

        print(f"\n    Test baseline:    Sharpe={test_baseline['sharpe']:>8.4f}, "
              f"CAGR={test_baseline['cagr_pct']:>7.2f}%, "
              f"MDD={test_baseline['mdd_pct']:>5.2f}%, "
              f"trades={test_baseline['trades']}")
        print(f"    Test A selected:  Sharpe={test_a_sel['sharpe']:>8.4f} "
              f"(d={d_sh_a_sel:+.4f}), "
              f"MDD={test_a_sel['mdd_pct']:>5.2f}% (d={d_mdd_a_sel:+.2f}pp), "
              f"trades={test_a_sel['trades']}, "
              f"vel_exits={test_a_sel['exit_velocity']}")
        print(f"    Test A fixed:     Sharpe={test_a_fix['sharpe']:>8.4f} "
              f"(d={d_sh_a_fix:+.4f}), "
              f"MDD={test_a_fix['mdd_pct']:>5.2f}% (d={d_mdd_a_fix:+.2f}pp), "
              f"trades={test_a_fix['trades']}, "
              f"vel_exits={test_a_fix['exit_velocity']}")

        # ══════════════════════════════════════════════════════════════
        # CONFIG C — Velocity + trendq AND
        # ══════════════════════════════════════════════════════════════
        print(f"\n  [CONFIG C] Sweeping {n_c} velocity+trendq configs on train...")

        best_c_sharpe = -np.inf
        best_c_vel: float = C_VEL_THRESHOLDS[0]
        best_c_tq: float = C_TQ_THRESHOLDS[0]
        train_c_grid: list[tuple[float, float, float]] = []

        for vel in C_VEL_THRESHOLDS:
            for tq in C_TQ_THRESHOLDS:
                r = run_backtest(feat, delta_rp, train_start, train_end,
                                 mode="vel_tq", vel_threshold=vel, tq_threshold=tq)
                train_c_grid.append((vel, tq, r["sharpe"]))
                if np.isfinite(r["sharpe"]) and r["sharpe"] > best_c_sharpe:
                    best_c_sharpe = r["sharpe"]
                    best_c_vel = vel
                    best_c_tq = tq

        print(f"    Best train C: vel={best_c_vel}, tq={best_c_tq}, Sharpe={best_c_sharpe:.4f}")

        # Print train C grid
        print("    Train C grid (Sharpe):")
        print(f"      {'vel\\tq':>8s}", end="")
        for tq in C_TQ_THRESHOLDS:
            print(f"  {tq:>7.2f}", end="")
        print()
        for vel in C_VEL_THRESHOLDS:
            print(f"      {vel:>8.2f}", end="")
            for tq in C_TQ_THRESHOLDS:
                sh = next(s for v, t, s in train_c_grid if v == vel and t == tq)
                marker = "*" if vel == best_c_vel and tq == best_c_tq else " "
                print(f"  {sh:>6.4f}{marker}", end="")
            print()

        # Test: selected C
        test_c_sel = run_backtest(feat, delta_rp, test_start, test_end,
                                  mode="vel_tq", vel_threshold=best_c_vel,
                                  tq_threshold=best_c_tq)
        # Test: fixed C
        test_c_fix = run_backtest(feat, delta_rp, test_start, test_end,
                                  mode="vel_tq", vel_threshold=FIXED_C_VEL,
                                  tq_threshold=FIXED_C_TQ)

        d_sh_c_sel = round(test_c_sel["sharpe"] - test_baseline["sharpe"], 4)
        d_mdd_c_sel = round(test_c_sel["mdd_pct"] - test_baseline["mdd_pct"], 2)
        d_sh_c_fix = round(test_c_fix["sharpe"] - test_baseline["sharpe"], 4)
        d_mdd_c_fix = round(test_c_fix["mdd_pct"] - test_baseline["mdd_pct"], 2)

        print(f"\n    Test C selected:  Sharpe={test_c_sel['sharpe']:>8.4f} "
              f"(d={d_sh_c_sel:+.4f}), "
              f"MDD={test_c_sel['mdd_pct']:>5.2f}% (d={d_mdd_c_sel:+.2f}pp), "
              f"trades={test_c_sel['trades']}, "
              f"vel_exits={test_c_sel['exit_velocity']}")
        print(f"    Test C fixed:     Sharpe={test_c_fix['sharpe']:>8.4f} "
              f"(d={d_sh_c_fix:+.4f}), "
              f"MDD={test_c_fix['mdd_pct']:>5.2f}% (d={d_mdd_c_fix:+.2f}pp), "
              f"trades={test_c_fix['trades']}, "
              f"vel_exits={test_c_fix['exit_velocity']}")

        # ── Store window results ─────────────────────────────────────
        window_results.append({
            "window": w_idx + 1,
            "train_period": f"{w['train_start']} → {w['train_end']}",
            "test_period": f"{w['test_start']} → {w['test_end']}",
            "train_bars": train_end - train_start,
            "test_bars": test_end - test_start,
            # Baseline
            "test_baseline_sharpe": test_baseline["sharpe"],
            "test_baseline_cagr": test_baseline["cagr_pct"],
            "test_baseline_mdd": test_baseline["mdd_pct"],
            "test_baseline_trades": test_baseline["trades"],
            # Config A — selected
            "a_selected_vel": best_a_vel,
            "a_train_best_sharpe": round(best_a_sharpe, 4),
            "a_test_sel_sharpe": test_a_sel["sharpe"],
            "a_test_sel_mdd": test_a_sel["mdd_pct"],
            "a_test_sel_trades": test_a_sel["trades"],
            "a_test_sel_vel_exits": test_a_sel["exit_velocity"],
            "a_test_sel_selectivity": test_a_sel["vel_selectivity"],
            "a_d_sharpe_sel": d_sh_a_sel,
            "a_d_mdd_sel": d_mdd_a_sel,
            "a_sel_wins_sharpe": int(d_sh_a_sel > 0),
            # Config A — fixed
            "a_test_fix_sharpe": test_a_fix["sharpe"],
            "a_test_fix_mdd": test_a_fix["mdd_pct"],
            "a_test_fix_vel_exits": test_a_fix["exit_velocity"],
            "a_d_sharpe_fix": d_sh_a_fix,
            "a_d_mdd_fix": d_mdd_a_fix,
            "a_fix_wins_sharpe": int(d_sh_a_fix > 0),
            # Config C — selected
            "c_selected_vel": best_c_vel,
            "c_selected_tq": best_c_tq,
            "c_train_best_sharpe": round(best_c_sharpe, 4),
            "c_test_sel_sharpe": test_c_sel["sharpe"],
            "c_test_sel_mdd": test_c_sel["mdd_pct"],
            "c_test_sel_trades": test_c_sel["trades"],
            "c_test_sel_vel_exits": test_c_sel["exit_velocity"],
            "c_test_sel_selectivity": test_c_sel["vel_selectivity"],
            "c_d_sharpe_sel": d_sh_c_sel,
            "c_d_mdd_sel": d_mdd_c_sel,
            "c_sel_wins_sharpe": int(d_sh_c_sel > 0),
            # Config C — fixed
            "c_test_fix_sharpe": test_c_fix["sharpe"],
            "c_test_fix_mdd": test_c_fix["mdd_pct"],
            "c_test_fix_vel_exits": test_c_fix["exit_velocity"],
            "c_d_sharpe_fix": d_sh_c_fix,
            "c_d_mdd_fix": d_mdd_c_fix,
            "c_fix_wins_sharpe": int(d_sh_c_fix > 0),
        })

    # ═══════════════════════════════════════════════════════════════════
    # Aggregate
    # ═══════════════════════════════════════════════════════════════════
    df = pd.DataFrame(window_results)

    print("\n" + "=" * 80)
    print("AGGREGATE RESULTS")
    print("=" * 80)

    def print_agg(label: str, d_sh_col: str, d_mdd_col: str, wins_col: str) -> tuple[int, float, float]:
        wins = int(df[wins_col].sum())
        wr = wins / len(df)
        mean_dsh = df[d_sh_col].mean()
        mean_dmdd = df[d_mdd_col].mean()
        print(f"\n  {label}:")
        print(f"    WFO win rate:       {wins}/{len(df)} = {wr * 100:.0f}%")
        print(f"    Mean d_Sharpe:      {mean_dsh:+.4f}")
        print(f"    d_Sharpe per window: {[round(x, 4) for x in df[d_sh_col]]}")
        print(f"    Mean d_MDD:         {mean_dmdd:+.2f} pp")
        print(f"    d_MDD per window:    {[round(x, 2) for x in df[d_mdd_col]]}")
        return wins, mean_dsh, mean_dmdd

    a_sel_wins, a_sel_mean, _ = print_agg(
        "CONFIG A — TRAIN-SELECTED", "a_d_sharpe_sel", "a_d_mdd_sel", "a_sel_wins_sharpe")
    a_fix_wins, a_fix_mean, _ = print_agg(
        f"CONFIG A — FIXED (vel={FIXED_A_VEL})", "a_d_sharpe_fix", "a_d_mdd_fix", "a_fix_wins_sharpe")
    c_sel_wins, c_sel_mean, _ = print_agg(
        "CONFIG C — TRAIN-SELECTED", "c_d_sharpe_sel", "c_d_mdd_sel", "c_sel_wins_sharpe")
    c_fix_wins, c_fix_mean, _ = print_agg(
        f"CONFIG C — FIXED (vel={FIXED_C_VEL}, tq={FIXED_C_TQ})",
        "c_d_sharpe_fix", "c_d_mdd_fix", "c_fix_wins_sharpe")

    # ── Parameter stability ───────────────────────────────────────────
    print(f"\n  PARAMETER STABILITY:")
    print("    Config A selected params:")
    for _, row in df.iterrows():
        print(f"      W{int(row['window'])}: vel={row['a_selected_vel']}")
    a_unique = df["a_selected_vel"].nunique()
    a_stab = "STABLE" if a_unique <= 2 else ("MODERATE" if a_unique <= 3 else "UNSTABLE")
    print(f"      Unique: {a_unique}/4 → {a_stab}")

    print("    Config C selected params:")
    for _, row in df.iterrows():
        print(f"      W{int(row['window'])}: vel={row['c_selected_vel']}, tq={row['c_selected_tq']}")
    c_unique = df[["c_selected_vel", "c_selected_tq"]].drop_duplicates()
    c_n_unique = len(c_unique)
    c_stab = "STABLE" if c_n_unique <= 2 else ("MODERATE" if c_n_unique <= 3 else "UNSTABLE")
    print(f"      Unique: {c_n_unique}/4 → {c_stab}")

    # ═══════════════════════════════════════════════════════════════════
    # Regime comparison with exp30
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'=' * 80}")
    print("REGIME COMPARISON: velocity (exp31) vs AND gate (exp30)")
    print("  W1/W2 = bear-inclusive, W3/W4 = bull-dominated")
    print("=" * 80)

    if exp30_df is not None:
        print(f"\n  {'Window':>8s}  {'exp30 sel':>12s}  {'exp31 A sel':>12s}  {'exp31 C sel':>12s}")
        for _, row in df.iterrows():
            w = int(row["window"])
            e30_dsh = exp30_df.loc[exp30_df["window"] == w, "d_sharpe_selected"].values
            e30_str = f"{e30_dsh[0]:+.4f}" if len(e30_dsh) > 0 else "N/A"
            print(f"  W{w:>7d}  {e30_str:>12s}  {row['a_d_sharpe_sel']:+12.4f}  {row['c_d_sharpe_sel']:+12.4f}")

        # Bear vs bull pattern
        bear_windows = df[df["window"].isin([1, 2])]
        bull_windows = df[df["window"].isin([3, 4])]

        a_bear_mean = bear_windows["a_d_sharpe_sel"].mean()
        a_bull_mean = bull_windows["a_d_sharpe_sel"].mean()
        c_bear_mean = bear_windows["c_d_sharpe_sel"].mean()
        c_bull_mean = bull_windows["c_d_sharpe_sel"].mean()

        print(f"\n  Bear-inclusive (W1+W2):")
        print(f"    A mean d_Sharpe: {a_bear_mean:+.4f}")
        print(f"    C mean d_Sharpe: {c_bear_mean:+.4f}")
        if exp30_df is not None and len(exp30_df) >= 2:
            e30_bear = exp30_df.loc[exp30_df["window"].isin([1, 2]), "d_sharpe_selected"].mean()
            print(f"    exp30 mean d_Sharpe: {e30_bear:+.4f}")

        print(f"  Bull-dominated (W3+W4):")
        print(f"    A mean d_Sharpe: {a_bull_mean:+.4f}")
        print(f"    C mean d_Sharpe: {c_bull_mean:+.4f}")
        if exp30_df is not None and len(exp30_df) >= 4:
            e30_bull = exp30_df.loc[exp30_df["window"].isin([3, 4]), "d_sharpe_selected"].mean()
            print(f"    exp30 mean d_Sharpe: {e30_bull:+.4f}")

        same_pattern_a = a_bear_mean > 0 and a_bull_mean < 0
        same_pattern_c = c_bear_mean > 0 and c_bull_mean < 0
        print(f"\n  Same bear+/bull- pattern as exp30?")
        print(f"    Config A: {'YES — structural, not fixable' if same_pattern_a else 'NO — different regime dependency'}")
        print(f"    Config C: {'YES — structural, not fixable' if same_pattern_c else 'NO — different regime dependency'}")
    else:
        print("  (exp30 results not available)")

    # ═══════════════════════════════════════════════════════════════════
    # Verdict
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    def check_pass(label: str, wins: int, mean_dsh: float) -> str:
        wr = wins / len(df)
        pass_wr = wr >= 0.75
        pass_mean = mean_dsh > 0
        print(f"\n  {label}:")
        print(f"    WFO win rate >= 75%:  {'PASS' if pass_wr else 'FAIL'} ({wr * 100:.0f}%)")
        print(f"    Mean d_Sharpe > 0:    {'PASS' if pass_mean else 'FAIL'} ({mean_dsh:+.4f})")
        verdict = "PASS" if pass_wr and pass_mean else ("INCONCLUSIVE" if wins == 2 and abs(mean_dsh) < 0.02 else "FAIL")
        print(f"    Verdict:              {verdict}")
        return verdict

    v_a_sel = check_pass("CONFIG A — TRAIN-SELECTED", a_sel_wins, a_sel_mean)
    v_a_fix = check_pass(f"CONFIG A — FIXED (vel={FIXED_A_VEL})", a_fix_wins, a_fix_mean)
    v_c_sel = check_pass("CONFIG C — TRAIN-SELECTED", c_sel_wins, c_sel_mean)
    v_c_fix = check_pass(f"CONFIG C — FIXED (vel={FIXED_C_VEL}, tq={FIXED_C_TQ})", c_fix_wins, c_fix_mean)

    any_pass = "PASS" in (v_a_sel, v_a_fix, v_c_sel, v_c_fix)
    any_inconclusive = "INCONCLUSIVE" in (v_a_sel, v_a_fix, v_c_sel, v_c_fix)

    if any_pass:
        overall = "PASS"
    elif any_inconclusive:
        overall = "INCONCLUSIVE"
    else:
        overall = "FAIL"

    print(f"\n  ╔══════════════════════════════════════════════════════════════╗")
    print(f"  ║  VELOCITY WFO VERDICT: {overall:<14s}                       ║")
    print(f"  ╚══════════════════════════════════════════════════════════════╝")

    if overall == "PASS":
        print("  → Velocity exit has temporal stability.")
        print("    Candidate for v10 formal validation pipeline.")
    elif overall == "INCONCLUSIVE":
        print("  → Velocity exit has MIXED temporal stability (same as exp30).")
        print("    x39 supplementary exit research line CLOSED.")
    else:
        print("  → Velocity exit is regime-dependent (like exp30 AND gate).")
        print("    Full-sample improvements from exp28 are selection bias.")
        print("    x39 supplementary exit research line CLOSED.")
        print("    Conclusion: E5-ema21D1 exit mechanism (trail + EMA cross-down)")
        print("    cannot be improved by supplementary exits from x39 feature space.")

    # ── Save ──────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp31_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
