"""Regime-conditional trade-level comparison: V10 vs V11.

Groups trades by entry_regime AND holding_regime_mode, computes per-regime stats
for each strategy, then computes regime-level deltas from matched pairs.

Outputs:
  - regime_trade_summary_{strategy}_{scenario}.csv  (per-regime stats)
  - regime_delta_summary_{scenario}.csv             (V10 vs V11 delta per regime)
  - regime_topping_deep_dive.json                   (TOPPING matched-pair details)

Usage:
    python out_trade_analysis/regime_comparison.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
SCENARIOS = ["harsh", "base"]
STRATEGIES = ["v10", "v11"]
REGIME_ORDER = ["BULL", "NEUTRAL", "CHOP", "TOPPING", "SHOCK"]
N_MIN = 10  # small-sample threshold


# ── Helpers ───────────────────────────────────────────────────────────────────

def regime_stats(df: pd.DataFrame, regime_col: str) -> pd.DataFrame:
    """Compute per-regime statistics for a single strategy/scenario."""
    rows = []
    for regime in REGIME_ORDER:
        sub = df[df[regime_col] == regime]
        n = len(sub)
        if n == 0:
            continue
        wins = (sub["net_pnl"] > 0).sum()
        rows.append({
            "regime": regime,
            "regime_type": regime_col,
            "n_trades": n,
            "total_net_pnl": round(sub["net_pnl"].sum(), 2),
            "mean_net_pnl": round(sub["net_pnl"].mean(), 2),
            "median_net_pnl": round(sub["net_pnl"].median(), 2),
            "mean_return_pct": round(sub["return_pct"].mean(), 4),
            "median_return_pct": round(sub["return_pct"].median(), 4),
            "hit_rate_pct": round(100.0 * wins / n, 1),
            "mean_mfe_pct": round(sub["mfe_pct"].mean(), 4),
            "mean_mae_pct": round(sub["mae_pct"].mean(), 4),
            "mfe_mae_ratio": round(sub["mfe_pct"].mean() / max(sub["mae_pct"].mean(), 0.001), 2),
            "mean_days_held": round(sub["days_held"].mean(), 1),
            "mean_bars_held": round(sub["bars_held"].mean(), 1),
            "mean_fees": round(sub["fees_total"].mean(), 2),
            "total_fees": round(sub["fees_total"].sum(), 2),
            "low_confidence": n < N_MIN,
        })
    return pd.DataFrame(rows)


def matched_regime_delta(
    mdf: pd.DataFrame, regime_col_prefix: str
) -> pd.DataFrame:
    """Compute per-regime delta stats from matched trades.

    Uses v10's regime label for grouping (matched pairs share ~same entry).
    """
    rcol = f"v10_{regime_col_prefix}"
    rows = []
    total_delta = mdf["delta_net_pnl"].sum()

    for regime in REGIME_ORDER:
        sub = mdf[mdf[rcol] == regime]
        n = len(sub)
        if n == 0:
            continue

        d_pnl = sub["delta_net_pnl"]
        d_ret = sub["delta_return_pct"]
        n_positive = (d_pnl > 0).sum()
        n_negative = (d_pnl < 0).sum()
        n_zero = (d_pnl == 0).sum()

        regime_total = d_pnl.sum()
        pct_of_total = (
            round(100.0 * regime_total / total_delta, 1)
            if abs(total_delta) > 0.01
            else float("nan")
        )

        rows.append({
            "regime": regime,
            "regime_type": regime_col_prefix,
            "n_matched": n,
            "delta_total_pnl": round(regime_total, 2),
            "delta_mean_pnl": round(d_pnl.mean(), 2),
            "delta_median_pnl": round(d_pnl.median(), 2),
            "delta_mean_return_pct": round(d_ret.mean(), 4),
            "p_v11_wins": round(100.0 * n_positive / n, 1),
            "n_v11_wins": n_positive,
            "n_v10_wins": n_negative,
            "n_zero": n_zero,
            "pct_of_total_delta": pct_of_total,
            # Decomposition aggregates
            "sum_exit_effect": round(sub["exit_effect"].sum(), 2),
            "sum_size_effect": round(sub["size_effect"].sum(), 2),
            "sum_fee_effect": round(sub["fee_effect"].sum(), 2),
            "sum_interaction": round(sub["interaction"].sum(), 2),
            # Size ratio
            "mean_size_ratio": round(sub["size_ratio"].mean(), 3),
            # MFE/MAE deltas
            "delta_mean_mfe": round(sub["delta_mfe_pct"].mean(), 4),
            "delta_mean_mae": round(sub["delta_mae_pct"].mean(), 4),
            "low_confidence": n < N_MIN,
        })
    return pd.DataFrame(rows)


def topping_deep_dive(scenarios_data: dict) -> dict:
    """Deep-dive on TOPPING regime matched trades across both scenarios."""
    result = {}

    for scenario, mdf in scenarios_data.items():
        # Filter TOPPING by entry_regime OR holding_regime_mode
        topping_entry = mdf[mdf["v10_entry_regime"] == "TOPPING"].copy()
        topping_hold = mdf[mdf["v10_holding_regime_mode"] == "TOPPING"].copy()

        # Combine unique trades (some overlap)
        all_ids = set(topping_entry["v10_trade_id"]).union(
            set(topping_hold["v10_trade_id"])
        )
        topping_all = mdf[mdf["v10_trade_id"].isin(all_ids)].copy()

        trades = []
        for _, row in topping_all.iterrows():
            trades.append({
                "v10_trade_id": row["v10_trade_id"],
                "entry_ts": row["v10_entry_ts"],
                "entry_regime": row["v10_entry_regime"],
                "holding_mode": row["v10_holding_regime_mode"],
                "worst_regime": row["v10_worst_regime"],
                # V10
                "v10_exit_reason": row["v10_exit_reason"],
                "v10_exit_ts": row["v10_exit_ts"],
                "v10_net_pnl": round(row["v10_net_pnl"], 2),
                "v10_return_pct": round(row["v10_return_pct"], 4),
                "v10_mfe_pct": round(row["v10_mfe_pct"], 4),
                "v10_mae_pct": round(row["v10_mae_pct"], 4),
                "v10_days_held": round(row["v10_days_held"], 2),
                "v10_qty": round(row["v10_qty"], 8),
                # V11
                "v11_exit_reason": row["v11_exit_reason"],
                "v11_exit_ts": row["v11_exit_ts"],
                "v11_net_pnl": round(row["v11_net_pnl"], 2),
                "v11_return_pct": round(row["v11_return_pct"], 4),
                "v11_mfe_pct": round(row["v11_mfe_pct"], 4),
                "v11_mae_pct": round(row["v11_mae_pct"], 4),
                "v11_days_held": round(row["v11_days_held"], 2),
                "v11_qty": round(row["v11_qty"], 8),
                # Delta
                "delta_net_pnl": round(row["delta_net_pnl"], 2),
                "delta_return_pct": round(row["delta_return_pct"], 4),
                "delta_mae_pct": round(row["delta_mae_pct"], 4),
                "delta_mfe_pct": round(row["delta_mfe_pct"], 4),
                "same_exit_reason": bool(row["same_exit_reason"]),
                "size_ratio": round(row["size_ratio"], 4),
                "exit_effect": round(row["exit_effect"], 2),
                "size_effect": round(row["size_effect"], 2),
            })

        n = len(trades)
        summary = {
            "n_topping_trades": n,
            "total_delta_pnl": round(sum(t["delta_net_pnl"] for t in trades), 2),
            "mean_delta_pnl": round(
                sum(t["delta_net_pnl"] for t in trades) / max(n, 1), 2
            ),
            "v10_mean_mae": round(
                sum(t["v10_mae_pct"] for t in trades) / max(n, 1), 4
            ),
            "v11_mean_mae": round(
                sum(t["v11_mae_pct"] for t in trades) / max(n, 1), 4
            ),
            "delta_mae": round(
                sum(t["delta_mae_pct"] for t in trades) / max(n, 1), 4
            ),
            "exit_changes": sum(1 for t in trades if not t["same_exit_reason"]),
            "mean_size_ratio": round(
                sum(t["size_ratio"] for t in trades) / max(n, 1), 4
            ),
            "trades": trades,
        }
        result[scenario] = summary

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    matched_data = {}

    for scenario in SCENARIOS:
        print(f"\n{'=' * 60}")
        print(f"  Scenario: {scenario.upper()}")
        print(f"{'=' * 60}")

        # ── 1) Per-strategy regime stats ──
        for strat in STRATEGIES:
            df = pd.read_csv(ROOT / f"trades_{strat}_{scenario}.csv")

            for regime_col in ["entry_regime", "holding_regime_mode"]:
                stats = regime_stats(df, regime_col)
                out_path = ROOT / f"regime_trade_summary_{strat}_{scenario}.csv"
                # Append both regime types into one file
                if regime_col == "entry_regime":
                    stats.to_csv(out_path, index=False)
                else:
                    stats.to_csv(out_path, mode="a", index=False, header=False)

            print(f"  Written: regime_trade_summary_{strat}_{scenario}.csv")

        # ── 2) Matched delta by regime ──
        mdf = pd.read_csv(ROOT / f"matched_trades_{scenario}.csv")
        matched_data[scenario] = mdf

        delta_rows = []
        for regime_col_prefix in ["entry_regime", "holding_regime_mode"]:
            delta_df = matched_regime_delta(mdf, regime_col_prefix)
            delta_rows.append(delta_df)

        delta_all = pd.concat(delta_rows, ignore_index=True)
        delta_path = ROOT / f"regime_delta_summary_{scenario}.csv"
        delta_all.to_csv(delta_path, index=False)
        print(f"  Written: {delta_path.name}")

        # Print summary
        entry_deltas = delta_all[delta_all["regime_type"] == "entry_regime"]
        print(f"\n  Delta by entry_regime (N={len(mdf)} matched):")
        print(f"  {'Regime':<10} {'N':>4} {'Δ Total':>10} {'Δ Mean':>9} "
              f"{'P(V11>)':>8} {'%Tot':>7} {'Flag':>5}")
        for _, r in entry_deltas.iterrows():
            flag = " *LC*" if r["low_confidence"] else ""
            pct = f"{r['pct_of_total_delta']:+.1f}%" if not np.isnan(r["pct_of_total_delta"]) else "N/A"
            print(f"  {r['regime']:<10} {r['n_matched']:>4} "
                  f"${r['delta_total_pnl']:>+9,.0f} "
                  f"${r['delta_mean_pnl']:>+8,.0f} "
                  f"{r['p_v11_wins']:>7.1f}% "
                  f"{pct:>7} {flag}")

    # ── 3) TOPPING deep dive ──
    print(f"\n{'=' * 60}")
    print("  TOPPING DEEP DIVE")
    print(f"{'=' * 60}")

    topping = topping_deep_dive(matched_data)
    topping_path = ROOT / "regime_topping_deep_dive.json"
    with open(topping_path, "w") as f:
        json.dump(topping, f, indent=2)
    print(f"  Written: {topping_path.name}")

    for scenario, td in topping.items():
        print(f"\n  {scenario.upper()} — {td['n_topping_trades']} TOPPING trades:")
        print(f"    Total Δ PnL:  ${td['total_delta_pnl']:+,.2f}")
        print(f"    Mean Δ PnL:   ${td['mean_delta_pnl']:+,.2f}")
        print(f"    V10 mean MAE: {td['v10_mean_mae']:.2f}%")
        print(f"    V11 mean MAE: {td['v11_mean_mae']:.2f}%")
        print(f"    Δ MAE:        {td['delta_mae']:+.4f}%")
        print(f"    Exit changes: {td['exit_changes']}")
        print(f"    Mean size ratio: {td['mean_size_ratio']:.3f}")

        for t in td["trades"]:
            exit_chg = "" if t["same_exit_reason"] else f" [{t['v10_exit_reason']}→{t['v11_exit_reason']}]"
            print(f"      {t['entry_ts'][:10]} | entry={t['entry_regime']:<8} "
                  f"hold={t['holding_mode']:<8} | "
                  f"Δ${t['delta_net_pnl']:+,.0f} "
                  f"(exit:{t['exit_effect']:+,.0f} size:{t['size_effect']:+,.0f}) "
                  f"SR={t['size_ratio']:.3f}{exit_chg}")

    print("\nDone.")


if __name__ == "__main__":
    main()
