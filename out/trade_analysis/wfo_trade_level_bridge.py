"""Bridge WFO window-level analysis with trade-level insights.

Maps matched V10-V11 trades into WFO OOS windows, proving that window-level
noise originates from small N and outlier trades. Shows that trade-level and
regime-level aggregation provide more stable inference.

Outputs:
  - window_trade_counts.csv             (per-window V10/V11 counts + delta stats)
  - wfo_window_detail.json              (full per-window trade-level details)

Usage:
    python out_trade_analysis/wfo_trade_level_bridge.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
SCENARIOS = ["harsh", "base"]

# WFO window boundaries (from generate_windows: 24m train, 6m test, 6m slide)
WFO_WINDOWS = [
    {"id": 0, "start": "2021-01-01", "end": "2021-07-01"},
    {"id": 1, "start": "2021-07-01", "end": "2022-01-01"},
    {"id": 2, "start": "2022-01-01", "end": "2022-07-01"},
    {"id": 3, "start": "2022-07-01", "end": "2023-01-01"},
    {"id": 4, "start": "2023-01-01", "end": "2023-07-01"},
    {"id": 5, "start": "2023-07-01", "end": "2024-01-01"},
    {"id": 6, "start": "2024-01-01", "end": "2024-07-01"},
    {"id": 7, "start": "2024-07-01", "end": "2025-01-01"},
    {"id": 8, "start": "2025-01-01", "end": "2025-07-01"},
    {"id": 9, "start": "2025-07-01", "end": "2026-01-01"},
]

N_BOOT_PER_WINDOW = 5_000
SEED = 42


def load_trades(strategy: str, scenario: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / f"trades_{strategy}_{scenario}.csv")
    df["entry_dt"] = pd.to_datetime(df["entry_ts"])
    return df


def load_matched(scenario: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / f"matched_trades_{scenario}.csv")
    df["entry_dt"] = pd.to_datetime(df["v10_entry_ts"])
    return df


def assign_wfo_window(entry_dt: pd.Timestamp) -> int | None:
    """Return WFO window ID if trade falls in an OOS window, else None."""
    # Strip tz for comparison (window boundaries are tz-naive)
    dt = entry_dt.tz_localize(None) if entry_dt.tzinfo else entry_dt
    for w in WFO_WINDOWS:
        if pd.Timestamp(w["start"]) <= dt < pd.Timestamp(w["end"]):
            return w["id"]
    return None


def window_se_analysis(deltas: np.ndarray, full_sigma: float) -> dict:
    """Compute SE and signal-to-noise for a window's trade deltas."""
    n = len(deltas)
    if n == 0:
        return {
            "n": 0, "sum_delta": 0.0, "mean_delta": 0.0, "std_delta": 0.0,
            "se_mean": float("inf"), "snr": 0.0,
            "ci95_lo": 0.0, "ci95_hi": 0.0,
        }
    mean_d = float(deltas.mean())
    std_d = float(deltas.std(ddof=1)) if n > 1 else full_sigma
    se = full_sigma / math.sqrt(n)  # use pooled sigma for consistency
    snr = abs(mean_d) / se if se > 0 else 0.0
    return {
        "n": n,
        "sum_delta": round(float(deltas.sum()), 2),
        "mean_delta": round(mean_d, 2),
        "std_delta": round(std_d, 2),
        "se_mean": round(se, 2),
        "snr": round(snr, 3),
        "ci95_lo": round(mean_d - 1.96 * se, 2),
        "ci95_hi": round(mean_d + 1.96 * se, 2),
    }


def identify_tail_trades(window_df: pd.DataFrame, threshold_pct: float = 0.5) -> list:
    """Find trades that dominate window result (>50% of window total delta)."""
    if len(window_df) == 0:
        return []
    total = window_df["delta_net_pnl"].sum()
    if abs(total) < 1.0:
        return []
    tails = []
    for _, row in window_df.iterrows():
        pct = row["delta_net_pnl"] / total if abs(total) > 0.01 else 0
        if abs(pct) >= threshold_pct:
            tails.append({
                "trade_id": row["v10_trade_id"],
                "entry_ts": row["v10_entry_ts"],
                "delta_pnl": round(row["delta_net_pnl"], 2),
                "pct_of_window": round(100 * pct, 1),
                "exit_reason_v10": row["v10_exit_reason"],
                "exit_reason_v11": row["v11_exit_reason"],
                "entry_regime": row["v10_entry_regime"],
                "size_ratio": round(row["size_ratio"], 3),
            })
    return sorted(tails, key=lambda x: abs(x["delta_pnl"]), reverse=True)


def bootstrap_window_means(matched_df: pd.DataFrame, n_boot: int, rng) -> np.ndarray:
    """Bootstrap the per-window mean-delta as WFO would see it.

    For each bootstrap: resample windows with replacement, compute the
    mean-of-window-means (WFO-style aggregation).
    """
    # Group by wfo_window
    window_means = {}
    for wid in range(10):
        sub = matched_df[matched_df["wfo_window"] == wid]
        if len(sub) > 0:
            window_means[wid] = sub["delta_net_pnl"].mean()
    # Only windows with trades
    active_means = np.array(list(window_means.values()))
    n_active = len(active_means)
    if n_active == 0:
        return np.zeros(n_boot)

    boot = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n_active, size=n_active)
        boot[b] = active_means[idx].mean()
    return boot


def main() -> None:
    all_results = {}
    csv_rows = []

    for scenario in SCENARIOS:
        print(f"\n{'=' * 70}")
        print(f"  Scenario: {scenario.upper()}")
        print(f"{'=' * 70}")

        # Load data
        v10 = load_trades("v10", scenario)
        v11 = load_trades("v11", scenario)
        matched = load_matched(scenario)

        # Assign WFO windows
        v10["wfo_window"] = v10["entry_dt"].apply(assign_wfo_window)
        v11["wfo_window"] = v11["entry_dt"].apply(assign_wfo_window)
        matched["wfo_window"] = matched["entry_dt"].apply(assign_wfo_window)

        # Full-sample sigma for SE calculations
        full_sigma = float(matched["delta_net_pnl"].std(ddof=1))
        full_mean = float(matched["delta_net_pnl"].mean())
        n_total = len(matched)

        print(f"  Total matched: {n_total}")
        print(f"  Full-sample σ(Δ PnL): ${full_sigma:,.0f}")
        print(f"  Full-sample mean(Δ PnL): ${full_mean:+,.0f}")

        # Pre-WFO trades (before 2021-01-01)
        pre_wfo_v10 = v10[v10["wfo_window"].isna()]
        pre_wfo_matched = matched[matched["wfo_window"].isna()]
        print(f"  Pre-WFO trades (before 2021): V10={len(pre_wfo_v10)}, "
              f"matched={len(pre_wfo_matched)}")

        # Per-window analysis
        print(f"\n  {'Win':>3} {'Period':<27} {'V10':>4} {'V11':>4} {'Mtch':>4} "
              f"{'ΣΔ PnL':>10} {'Mean Δ':>9} {'SE':>8} {'SNR':>6} "
              f"{'95% CI':>22} {'Tail?':>6}")
        print(f"  {'-'*110}")

        window_details = {}
        for w in WFO_WINDOWS:
            wid = w["id"]
            period = f"{w['start']} → {w['end']}"
            days = (pd.Timestamp(w["end"]) - pd.Timestamp(w["start"])).days

            n_v10 = int((v10["wfo_window"] == wid).sum())
            n_v11 = int((v11["wfo_window"] == wid).sum())
            w_matched = matched[matched["wfo_window"] == wid]
            n_matched = len(w_matched)

            turnover_v10 = float(v10.loc[v10["wfo_window"] == wid, "notional"].sum())
            turnover_v11 = float(v11.loc[v11["wfo_window"] == wid, "notional"].sum())

            deltas = w_matched["delta_net_pnl"].values
            se_info = window_se_analysis(deltas, full_sigma)
            tails = identify_tail_trades(w_matched)

            ci_str = f"[${se_info['ci95_lo']:+,.0f}, ${se_info['ci95_hi']:+,.0f}]"
            tail_flag = f"{len(tails)}T" if tails else ""

            print(f"  {wid:>3} {period:<27} {n_v10:>4} {n_v11:>4} {n_matched:>4} "
                  f"${se_info['sum_delta']:>+9,.0f} ${se_info['mean_delta']:>+8,.0f} "
                  f"${se_info['se_mean']:>7,.0f} {se_info['snr']:>6.2f} "
                  f"{ci_str:>22} {tail_flag:>6}")

            # CSV row
            csv_rows.append({
                "scenario": scenario,
                "window_id": wid,
                "period_start": w["start"],
                "period_end": w["end"],
                "days": days,
                "v10_trades": n_v10,
                "v11_trades": n_v11,
                "matched_trades": n_matched,
                "v10_turnover": round(turnover_v10, 2),
                "v11_turnover": round(turnover_v11, 2),
                "sum_delta_pnl": se_info["sum_delta"],
                "mean_delta_pnl": se_info["mean_delta"],
                "std_delta_pnl": se_info["std_delta"],
                "se_mean": se_info["se_mean"],
                "snr": se_info["snr"],
                "ci95_lo": se_info["ci95_lo"],
                "ci95_hi": se_info["ci95_hi"],
                "n_tail_trades": len(tails),
                "tail_trades": json.dumps(tails) if tails else "",
            })

            window_details[wid] = {
                "period": period,
                "days": days,
                "v10_trades": n_v10,
                "v11_trades": n_v11,
                "matched_trades": n_matched,
                **se_info,
                "tail_trades": tails,
            }

        # Trade count distribution
        matched_per_w = [
            len(matched[matched["wfo_window"] == w["id"]]) for w in WFO_WINDOWS
        ]
        active_counts = [c for c in matched_per_w if c > 0]

        print(f"\n  Trade count distribution (matched, WFO windows):")
        print(f"    All 10 windows: {matched_per_w}")
        print(f"    Active ({len(active_counts)}): min={min(active_counts)}, "
              f"median={np.median(active_counts):.0f}, max={max(active_counts)}, "
              f"mean={np.mean(active_counts):.1f}")
        print(f"    Empty windows: {matched_per_w.count(0)}")
        print(f"    Windows < 10 trades: {sum(1 for c in matched_per_w if 0 < c < 10)}")

        # Window-level vs trade-level comparison
        rng = np.random.default_rng(SEED)

        # WFO-style: mean of window means (only active windows)
        active_window_means = []
        for w in WFO_WINDOWS:
            sub = matched[matched["wfo_window"] == w["id"]]
            if len(sub) > 0:
                active_window_means.append(sub["delta_net_pnl"].mean())
        wfo_mean_of_means = np.mean(active_window_means) if active_window_means else 0
        wfo_se = (
            np.std(active_window_means, ddof=1) / math.sqrt(len(active_window_means))
            if len(active_window_means) > 1
            else float("inf")
        )

        # Trade-level: simple pooled mean
        trade_mean = matched["delta_net_pnl"].mean()
        trade_se = full_sigma / math.sqrt(n_total)

        # Bootstrap comparison
        boot_wfo = bootstrap_window_means(matched, N_BOOT_PER_WINDOW, rng)
        boot_trade = np.empty(N_BOOT_PER_WINDOW)
        for b in range(N_BOOT_PER_WINDOW):
            idx = rng.integers(0, n_total, size=n_total)
            boot_trade[b] = matched["delta_net_pnl"].values[idx].mean()

        print(f"\n  Window-level vs Trade-level comparison:")
        print(f"    WFO (mean of window means): ${wfo_mean_of_means:+,.0f} ± ${wfo_se:,.0f}")
        print(f"    Trade-level (pooled mean):  ${trade_mean:+,.0f} ± ${trade_se:,.0f}")
        print(f"    Boot WFO P(>0):   {(boot_wfo > 0).mean():.4f}")
        print(f"    Boot Trade P(>0): {(boot_trade > 0).mean():.4f}")
        print(f"    Boot WFO 95% CI:   [${np.percentile(boot_wfo, 2.5):+,.0f}, "
              f"${np.percentile(boot_wfo, 97.5):+,.0f}]")
        print(f"    Boot Trade 95% CI: [${np.percentile(boot_trade, 2.5):+,.0f}, "
              f"${np.percentile(boot_trade, 97.5):+,.0f}]")

        all_results[scenario] = {
            "n_total_matched": n_total,
            "n_pre_wfo": len(pre_wfo_matched),
            "full_sigma": round(full_sigma, 2),
            "full_mean": round(full_mean, 2),
            "trade_counts_per_window": matched_per_w,
            "empty_windows": matched_per_w.count(0),
            "windows_lt_10": sum(1 for c in matched_per_w if 0 < c < 10),
            "window_details": window_details,
            "wfo_mean_of_means": round(float(wfo_mean_of_means), 2),
            "wfo_se": round(float(wfo_se), 2),
            "trade_pooled_mean": round(float(trade_mean), 2),
            "trade_pooled_se": round(float(trade_se), 2),
            "boot_wfo_p_gt0": round(float((boot_wfo > 0).mean()), 4),
            "boot_trade_p_gt0": round(float((boot_trade > 0).mean()), 4),
            "boot_wfo_ci95": [
                round(float(np.percentile(boot_wfo, 2.5)), 2),
                round(float(np.percentile(boot_wfo, 97.5)), 2),
            ],
            "boot_trade_ci95": [
                round(float(np.percentile(boot_trade, 2.5)), 2),
                round(float(np.percentile(boot_trade, 97.5)), 2),
            ],
        }

    # Save CSV
    csv_path = ROOT / "window_trade_counts.csv"
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False)
    print(f"\nWritten: {csv_path}")

    # Save JSON
    json_path = ROOT / "wfo_window_detail.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Written: {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
