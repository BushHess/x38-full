#!/usr/bin/env python3
"""Exp 52: Vol Compression at Realistic Costs.

Characterizes vol compression (exp34/42) across the cost spectrum.
X22 showed mechanisms are COST-DEPENDENT: churn filters HURT at <30 bps.
This experiment tests whether vol compression is a genuine quality filter
or a cost-reduction mechanism.

Configs: baseline, threshold=0.6, threshold=0.7
Costs:   10, 15, 20, 25, 30, 40, 50 bps RT
Total:   3 × 7 = 21 runs

Usage:
    python -m research.x39.experiments.exp52_compression_realistic_costs
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
INITIAL_CASH = 10_000.0

# ── Sweep grids ──────────────────────────────────────────────────────────
COST_LEVELS = [10, 15, 20, 25, 30, 40, 50]
COMPRESSION_THRESHOLDS: list[float | None] = [None, 0.6, 0.7]


def run_backtest(
    feat: pd.DataFrame,
    compression_threshold: float | None,
    cost_bps: int,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional vol compression gate at given cost."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    vol_ratio = feat["vol_ratio_5_20"].values
    n = len(c)

    trades: list[dict] = []
    blocked_entries: list[int] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    half_cost = (cost_bps / 2) / 10_000
    cost_rt = cost_bps / 10_000

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash

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
                    entry_bar = i
                    entry_price = c[i]
                    peak = c[i]
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
                else:
                    blocked_entries.append(i)
        else:
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost_rt

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                })

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Metrics ───────────────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result(compression_threshold, cost_bps)

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = (rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    tdf = pd.DataFrame(trades)
    n_wins = int(tdf["win"].sum())
    win_rate = n_wins / len(trades) * 100

    # ── Blocked entry analysis (at this cost level) ──────────────────
    blocked_wins = 0
    blocked_total = len(blocked_entries)

    for b_i in blocked_entries:
        b_entry = c[b_i]
        b_peak = b_entry
        b_exited = False
        for j in range(b_i + 1, n):
            if np.isnan(ratr[j]):
                continue
            b_peak = max(b_peak, c[j])
            b_trail = b_peak - TRAIL_MULT * ratr[j]
            if c[j] < b_trail or ema_f[j] < ema_s[j]:
                if (c[j] - b_entry) / b_entry - cost_rt > 0:
                    blocked_wins += 1
                b_exited = True
                break
        if not b_exited:
            if (c[-1] - b_entry) / b_entry - cost_rt > 0:
                blocked_wins += 1

    blocked_wr = (blocked_wins / blocked_total * 100) if blocked_total > 0 else np.nan

    return {
        "cost_bps": cost_bps,
        "threshold": compression_threshold if compression_threshold is not None else "baseline",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
    }


def _empty_result(compression_threshold: float | None, cost_bps: int) -> dict:
    return {
        "cost_bps": cost_bps,
        "threshold": compression_threshold if compression_threshold is not None else "baseline",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "blocked": 0, "blocked_win_rate": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 52: Vol Compression at Realistic Costs")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    warmup_bar = SLOW_PERIOD

    # ── Run all 21 configurations ────────────────────────────────────
    results = []
    for cost in COST_LEVELS:
        for thresh in COMPRESSION_THRESHOLDS:
            label = f"cost={cost:>2}bps, {'baseline' if thresh is None else f'thr={thresh}'}"
            print(f"  {label} ...", end="", flush=True)
            r = run_backtest(feat, thresh, cost, warmup_bar)
            results.append(r)
            print(f"  Sh={r['sharpe']}, CAGR={r['cagr_pct']}%, "
                  f"MDD={r['mdd_pct']}%, trades={r['trades']}")

    df = pd.DataFrame(results)

    # ── Compute d_Sharpe vs baseline at same cost ────────────────────
    baselines = df[df["threshold"] == "baseline"].set_index("cost_bps")
    d_sharpe_list = []
    d_cagr_list = []
    d_mdd_list = []
    for _, row in df.iterrows():
        cost = row["cost_bps"]
        base_sh = baselines.loc[cost, "sharpe"]
        base_cagr = baselines.loc[cost, "cagr_pct"]
        base_mdd = baselines.loc[cost, "mdd_pct"]
        d_sharpe_list.append(round(row["sharpe"] - base_sh, 4) if row["threshold"] != "baseline" else 0.0)
        d_cagr_list.append(round(row["cagr_pct"] - base_cagr, 2) if row["threshold"] != "baseline" else 0.0)
        d_mdd_list.append(round(row["mdd_pct"] - base_mdd, 2) if row["threshold"] != "baseline" else 0.0)
    df["d_sharpe"] = d_sharpe_list
    df["d_cagr"] = d_cagr_list
    df["d_mdd"] = d_mdd_list

    # ── Save results ─────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp52_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Analysis ─────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FULL RESULTS TABLE")
    print("=" * 80)
    print(df.to_string(index=False))

    # ── 1. d_Sharpe vs cost curve ────────────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 1: d_Sharpe vs Cost (compression delta at each cost level)")
    print("=" * 80)
    for thresh in [0.6, 0.7]:
        subset = df[df["threshold"] == thresh]
        print(f"\n  threshold={thresh}:")
        print(f"  {'cost':>6s}  {'d_Sharpe':>9s}  {'d_CAGR':>8s}  {'d_MDD':>7s}")
        for _, row in subset.iterrows():
            print(f"  {row['cost_bps']:>4d}bp  {row['d_sharpe']:>+9.4f}  "
                  f"{row['d_cagr']:>+8.2f}  {row['d_mdd']:>+7.2f}")

        # Trend assessment
        deltas = subset["d_sharpe"].values
        if deltas[0] < deltas[-1]:
            trend = "INCREASING (cost reducer — more value at high cost)"
        elif abs(deltas[0] - deltas[-1]) < 0.02:
            trend = "FLAT (genuine quality filter — value independent of cost)"
        else:
            trend = "DECREASING (cost-dependent — like churn filters in X22)"
        print(f"  Trend: {trend}")

    # ── 2. Selectivity vs cost ───────────────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 2: Selectivity (blocked WR vs baseline WR at each cost)")
    print("=" * 80)
    for thresh in [0.6, 0.7]:
        subset = df[df["threshold"] == thresh]
        print(f"\n  threshold={thresh}:")
        print(f"  {'cost':>6s}  {'base_WR':>8s}  {'blocked_WR':>11s}  {'selective':>10s}")
        for _, row in subset.iterrows():
            cost = row["cost_bps"]
            base_wr = baselines.loc[cost, "win_rate"]
            b_wr = row["blocked_win_rate"]
            sel = "YES" if (np.isfinite(b_wr) and b_wr < base_wr) else "NO"
            print(f"  {cost:>4d}bp  {base_wr:>8.1f}%  {b_wr:>10.1f}%  {sel:>10s}")

    # ── 3. Breakeven cost ────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 3: Breakeven Cost (where d_Sharpe crosses zero)")
    print("=" * 80)
    for thresh in [0.6, 0.7]:
        subset = df[df["threshold"] == thresh].sort_values("cost_bps")
        costs = subset["cost_bps"].values
        deltas = subset["d_sharpe"].values

        # Find sign change
        breakeven = None
        for k in range(len(deltas) - 1):
            if deltas[k] * deltas[k + 1] < 0:
                # Linear interpolation
                c1, c2 = costs[k], costs[k + 1]
                d1_val, d2_val = deltas[k], deltas[k + 1]
                breakeven = c1 + (0 - d1_val) * (c2 - c1) / (d2_val - d1_val)
                break

        if breakeven is not None:
            print(f"  threshold={thresh}: breakeven ~{breakeven:.0f} bps RT")
        elif all(d > 0 for d in deltas):
            print(f"  threshold={thresh}: d_Sharpe > 0 at ALL costs (always helps)")
        elif all(d <= 0 for d in deltas):
            print(f"  threshold={thresh}: d_Sharpe <= 0 at ALL costs (never helps)")
        else:
            print(f"  threshold={thresh}: no clean breakeven (non-monotonic)")

    # ── 4. Optimal threshold vs cost ─────────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 4: Optimal Threshold per Cost Level")
    print("=" * 80)
    print(f"  {'cost':>6s}  {'best_thr':>9s}  {'d_Sharpe':>9s}  {'note':>20s}")
    for cost in COST_LEVELS:
        gated = df[(df["cost_bps"] == cost) & (df["threshold"] != "baseline")]
        if gated.empty:
            continue
        best = gated.loc[gated["d_sharpe"].idxmax()]
        base_sh = baselines.loc[cost, "sharpe"]
        note = "helps" if best["d_sharpe"] > 0 else "HURTS"
        print(f"  {cost:>4d}bp  {best['threshold']:>9}  {best['d_sharpe']:>+9.4f}  {note:>20s}")

    # ── Verdict ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Check if compression helps at realistic costs (15-25 bps)
    realistic_costs = [15, 20, 25]
    helps_realistic = {}
    for thresh in [0.6, 0.7]:
        subset = df[(df["threshold"] == thresh) & (df["cost_bps"].isin(realistic_costs))]
        n_helps = (subset["d_sharpe"] > 0).sum()
        helps_realistic[thresh] = n_helps

    all_help = all(v == len(realistic_costs) for v in helps_realistic.values())
    none_help = all(v == 0 for v in helps_realistic.values())

    if all_help:
        # Check if delta is cost-dependent or cost-independent
        for thresh in [0.6, 0.7]:
            sub = df[df["threshold"] == thresh]
            d_at_15 = sub[sub["cost_bps"] == 15]["d_sharpe"].values[0]
            d_at_50 = sub[sub["cost_bps"] == 50]["d_sharpe"].values[0]
            ratio = d_at_15 / d_at_50 if d_at_50 != 0 else float("inf")
            print(f"  thr={thresh}: d_Sharpe@15bps / d_Sharpe@50bps = {ratio:.2f}")

        print("\n  COST-INDEPENDENT: Compression helps at ALL cost levels.")
        print("  → Genuine quality filter, NOT a cost-reduction mechanism.")
        print("  → DEPLOY compression at realistic costs.")
    elif none_help:
        print("  COST-DEPENDENT: Compression HURTS at realistic costs (15-25 bps).")
        print("  → Like churn filters in X22, compression is a cost-reduction mechanism.")
        print("  → DO NOT deploy compression at realistic costs.")
    else:
        print("  MIXED: Compression helps at some realistic costs, not others.")
        for thresh in [0.6, 0.7]:
            subset = df[(df["threshold"] == thresh) & (df["cost_bps"].isin(realistic_costs))]
            for _, row in subset.iterrows():
                status = "HELPS" if row["d_sharpe"] > 0 else "HURTS"
                print(f"    thr={thresh} @ {row['cost_bps']}bps: d_Sharpe={row['d_sharpe']:+.4f} [{status}]")

    # X22 comparison
    print("\n  Connection to X22:")
    base_15 = baselines.loc[15] if 15 in baselines.index else None
    if base_15 is not None:
        print(f"    E5-ema21D1 @ 15 bps: Sharpe={base_15['sharpe']}, CAGR={base_15['cagr_pct']}%")
        for thresh in [0.6, 0.7]:
            row = df[(df["threshold"] == thresh) & (df["cost_bps"] == 15)].iloc[0]
            print(f"    + compression thr={thresh} @ 15 bps: "
                  f"Sharpe={row['sharpe']} (d={row['d_sharpe']:+.4f})")


if __name__ == "__main__":
    main()
