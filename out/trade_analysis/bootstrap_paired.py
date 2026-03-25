"""Bootstrap inference on trade-level V10 vs V11 paired differences.

Two methods (both implemented):
  A) Cluster bootstrap by semi-annual window — resample windows with replacement,
     preserving intra-window correlation.
  B) Moving block bootstrap — resample contiguous blocks of K trades to preserve
     temporal autocorrelation.

Also runs IID bootstrap for comparison (assumes independence).

Outputs per scenario:
  - bootstrap_trade_level_{scenario}.csv   (10k bootstrap sample means)
  - bootstrap_summary.json                 (aggregated stats)
  - (report written separately)

Usage:
    python out_trade_analysis/bootstrap_paired.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
SEED = 20260224
N_BOOT = 10_000
BLOCK_SIZES = [5, 8, 12]          # sensitivity: trades per block
PRIMARY_BLOCK = 8                  # ~1 WFO half-year worth of trades
SCENARIOS = ["harsh", "base"]
ROOT = Path(__file__).parent


# ── Data loading ──────────────────────────────────────────────────────────────

def load_matched(scenario: str) -> pd.DataFrame:
    path = ROOT / f"matched_trades_{scenario}.csv"
    df = pd.read_csv(path)
    df["entry_dt"] = pd.to_datetime(df["v10_entry_ts"])
    df = df.sort_values("entry_dt").reset_index(drop=True)
    return df


def assign_semi_annual_windows(df: pd.DataFrame) -> pd.DataFrame:
    """Assign 6-month window IDs matching WFO cadence (YYYYH1 / YYYYH2)."""
    df = df.copy()
    df["window_id"] = df["entry_dt"].apply(
        lambda dt: f"{dt.year}H{1 if dt.month <= 6 else 2}"
    )
    return df


# ── Bootstrap methods ─────────────────────────────────────────────────────────

def cluster_bootstrap(
    df: pd.DataFrame, col: str, n_boot: int, rng: np.random.Generator
) -> np.ndarray:
    """Resample semi-annual windows with replacement, take all trades per window."""
    windows = df["window_id"].unique()
    n_w = len(windows)
    groups = {w: df.loc[df["window_id"] == w, col].values for w in windows}

    means = np.empty(n_boot)
    for b in range(n_boot):
        sampled = rng.choice(windows, size=n_w, replace=True)
        pooled = np.concatenate([groups[w] for w in sampled])
        means[b] = pooled.mean()
    return means


def moving_block_bootstrap(
    series: np.ndarray, block_size: int, n_boot: int, rng: np.random.Generator
) -> np.ndarray:
    """Resample contiguous blocks of trades; preserves local autocorrelation."""
    n = len(series)
    n_blocks = max(1, (n + block_size - 1) // block_size)  # ceil(n / block_size)
    max_start = n - block_size  # inclusive

    if max_start < 0:
        # Fewer trades than block_size — fall back to IID
        return iid_bootstrap(series, n_boot, rng)

    means = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        sample = np.concatenate([series[s : s + block_size] for s in starts])
        means[b] = sample[:n].mean()  # truncate to original length
    return means


def iid_bootstrap(
    series: np.ndarray, n_boot: int, rng: np.random.Generator
) -> np.ndarray:
    """Standard IID bootstrap (assumes independent trades)."""
    n = len(series)
    means = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        means[b] = series[idx].mean()
    return means


# ── Statistics ────────────────────────────────────────────────────────────────

def boot_stats(boot_means: np.ndarray, observed: float) -> dict:
    return {
        "observed_mean": round(float(observed), 2),
        "boot_mean": round(float(boot_means.mean()), 2),
        "boot_se": round(float(boot_means.std()), 2),
        "p_v11_gt_v10": round(float((boot_means > 0).mean()), 4),
        "ci95_lo": round(float(np.percentile(boot_means, 2.5)), 2),
        "ci95_hi": round(float(np.percentile(boot_means, 97.5)), 2),
        "ci90_lo": round(float(np.percentile(boot_means, 5.0)), 2),
        "ci90_hi": round(float(np.percentile(boot_means, 95.0)), 2),
    }


def window_diagnostics(df: pd.DataFrame) -> dict:
    """Trades per window — explains WFO jumpiness."""
    counts = df.groupby("window_id").size()
    return {
        "n_windows": int(len(counts)),
        "trades_per_window": counts.to_dict(),
        "mean_trades_per_window": round(float(counts.mean()), 1),
        "min_trades_per_window": int(counts.min()),
        "max_trades_per_window": int(counts.max()),
        "windows_lt_10": int((counts < 10).sum()),
    }


# ── Autocorrelation diagnostic ───────────────────────────────────────────────

def lag1_autocorr(series: np.ndarray) -> float:
    """Lag-1 autocorrelation of delta series."""
    if len(series) < 3:
        return 0.0
    x = series - series.mean()
    c0 = np.dot(x, x)
    if c0 == 0:
        return 0.0
    c1 = np.dot(x[:-1], x[1:])
    return round(float(c1 / c0), 4)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    results = {}

    for scenario in SCENARIOS:
        print(f"\n{'=' * 60}")
        print(f"  Scenario: {scenario.upper()}")
        print(f"{'=' * 60}")

        df = load_matched(scenario)
        df = assign_semi_annual_windows(df)

        deltas_pnl = df["delta_net_pnl"].values
        deltas_ret = df["delta_return_pct"].values
        n = len(deltas_pnl)
        obs_mean_pnl = deltas_pnl.mean()
        obs_mean_ret = deltas_ret.mean()

        print(f"  N matched trades: {n}")
        print(f"  Observed mean Δ PnL:    ${obs_mean_pnl:+.2f}")
        print(f"  Observed mean Δ Return:  {obs_mean_ret:+.4f}%")
        print(f"  Lag-1 autocorr (Δ PnL): {lag1_autocorr(deltas_pnl)}")

        # Window diagnostics
        wdiag = window_diagnostics(df)
        print(f"  Windows: {wdiag['n_windows']}, "
              f"trades/window: {wdiag['mean_trades_per_window']:.1f} "
              f"(min {wdiag['min_trades_per_window']}, max {wdiag['max_trades_per_window']})")
        print(f"  Windows with <10 trades: {wdiag['windows_lt_10']}")

        # Fresh RNG for each scenario (deterministic)
        rng = np.random.default_rng(SEED)

        # ── A) Cluster bootstrap ──
        cluster_means = cluster_bootstrap(df, "delta_net_pnl", N_BOOT, rng)
        cluster_s = boot_stats(cluster_means, obs_mean_pnl)

        # Also for return %
        cluster_ret_means = cluster_bootstrap(df, "delta_return_pct", N_BOOT, rng)
        cluster_ret_s = boot_stats(cluster_ret_means, obs_mean_ret)

        print(f"\n  [A] Cluster bootstrap (by semi-annual window):")
        print(f"      P(V11 > V10) = {cluster_s['p_v11_gt_v10']:.4f}")
        print(f"      95% CI mean Δ PnL: [${cluster_s['ci95_lo']}, ${cluster_s['ci95_hi']}]")

        # ── B) Moving block bootstrap (multiple block sizes) ──
        block_results = {}
        for bs in BLOCK_SIZES:
            rng_block = np.random.default_rng(SEED + bs)
            bm = moving_block_bootstrap(deltas_pnl, bs, N_BOOT, rng_block)
            block_results[bs] = boot_stats(bm, obs_mean_pnl)

            if bs == PRIMARY_BLOCK:
                primary_block_means = bm
                print(f"\n  [B] Moving block bootstrap (K={bs} trades):")
                print(f"      P(V11 > V10) = {block_results[bs]['p_v11_gt_v10']:.4f}")
                print(f"      95% CI mean Δ PnL: "
                      f"[${block_results[bs]['ci95_lo']}, ${block_results[bs]['ci95_hi']}]")

        # ── IID bootstrap (reference) ──
        rng_iid = np.random.default_rng(SEED + 99)
        iid_means = iid_bootstrap(deltas_pnl, N_BOOT, rng_iid)
        iid_s = boot_stats(iid_means, obs_mean_pnl)

        print(f"\n  [IID] Naive bootstrap (assumes independence):")
        print(f"      P(V11 > V10) = {iid_s['p_v11_gt_v10']:.4f}")
        print(f"      95% CI mean Δ PnL: [${iid_s['ci95_lo']}, ${iid_s['ci95_hi']}]")

        # ── Export CSV ──
        boot_df = pd.DataFrame({
            "sample_id": range(N_BOOT),
            "cluster_mean_delta_pnl": cluster_means,
            "block8_mean_delta_pnl": primary_block_means,
            "iid_mean_delta_pnl": iid_means,
        })
        csv_path = ROOT / f"bootstrap_trade_level_{scenario}.csv"
        boot_df.to_csv(csv_path, index=False)
        print(f"\n  Written: {csv_path}")

        # ── Collect results ──
        results[scenario] = {
            "n_trades": n,
            "observed_mean_delta_pnl": round(float(obs_mean_pnl), 2),
            "observed_total_delta_pnl": round(float(deltas_pnl.sum()), 2),
            "observed_mean_delta_return": round(float(obs_mean_ret), 4),
            "lag1_autocorr": lag1_autocorr(deltas_pnl),
            "window_diagnostics": wdiag,
            "cluster_bootstrap_pnl": cluster_s,
            "cluster_bootstrap_return": cluster_ret_s,
            "block_bootstrap_pnl": {str(k): v for k, v in block_results.items()},
            "iid_bootstrap_pnl": iid_s,
        }

    # ── Save JSON summary ──
    json_path = ROOT / "bootstrap_summary.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWritten: {json_path}")

    # ── Cross-scenario comparison ──
    print(f"\n{'=' * 60}")
    print("  CROSS-SCENARIO COMPARISON")
    print(f"{'=' * 60}")
    for method_key, method_name in [
        ("cluster_bootstrap_pnl", "Cluster"),
        ("iid_bootstrap_pnl", "IID"),
    ]:
        print(f"\n  {method_name} bootstrap:")
        for sc in SCENARIOS:
            s = results[sc][method_key]
            print(f"    {sc:6s}: P(V11>V10) = {s['p_v11_gt_v10']:.4f}  "
                  f"CI95 = [${s['ci95_lo']}, ${s['ci95_hi']}]")

    print("\nDone.")


if __name__ == "__main__":
    main()
