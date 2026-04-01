#!/usr/bin/env python3
"""D1.7 — Rebuild breadth metric with true D1 EMA(21) from H4-to-D1 resampling.

Instead of approximating D1 EMA(21) as H4 EMA(126), this script:
1. Resamples each alt's H4 bars to exact D1 closes (last H4 close of each UTC day)
2. Computes true D1 EMA(21) on the D1 close series
3. Recomputes breadth_d1_ema21_share using strict no-lookahead alignment
4. Re-runs the minimum necessary breadth diagnostics
5. Compares old (proxy) vs new (exact) results
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
BREADTH_DATA = "/var/www/trading-bots/data-pipeline/output/bars_multi_4h.parquet"


def ema(arr: np.ndarray, period: int) -> np.ndarray:
    """Compute EMA with standard exponential smoothing."""
    alpha = 2.0 / (period + 1.0)
    out = np.empty_like(arr, dtype=np.float64)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1 - alpha) * out[i - 1]
    return out


def resample_h4_to_d1(h4_df: pd.DataFrame) -> pd.DataFrame:
    """Resample H4 bars to D1 bars using last close of each UTC day.

    D1 bar for date YYYY-MM-DD:
      - close = last H4 close with close_time on that day
      - close_time = max close_time of that day's H4 bars

    No-lookahead: we only use H4 bars that have already closed.
    """
    h4_df = h4_df.sort_values("close_time").copy()
    # Day boundary: UTC day from close_time
    h4_df["d1_date"] = pd.to_datetime(h4_df["close_time"], unit="ms").dt.date

    # For each day, take the LAST H4 bar (close_time is max for that day)
    # This is the 20:00-23:59:59 bar
    d1_rows = []
    for date, group in h4_df.groupby("d1_date"):
        last = group.iloc[-1]
        d1_rows.append({
            "d1_date": date,
            "close": last["close"],
            "close_time_ms": last["close_time"],
        })

    return pd.DataFrame(d1_rows)


def compute_breadth_exact(breadth_path: str, btc_h4_close_times: np.ndarray,
                           d1_ema_period: int = 21) -> np.ndarray:
    """Compute breadth_d1_ema21_share using true D1 EMA(21).

    For each BTC H4 bar at time T:
    1. For each alt symbol, find the most recent COMPLETED D1 bar
       (D1 bar close_time <= T)
    2. Check if that D1 close > D1 EMA(21) at that bar
    3. breadth = fraction of eligible symbols with close > EMA(21)

    No-lookahead: only uses D1 bars that completed before BTC H4 bar close.
    """
    bdf = pd.read_parquet(breadth_path)
    symbols = sorted(s for s in bdf["symbol"].unique() if s != "BTCUSDT")

    n_btc = len(btc_h4_close_times)
    breadth_share = np.full(n_btc, np.nan, dtype=np.float64)

    # Precompute per-symbol D1 data
    sym_data = {}
    for sym in symbols:
        h4 = bdf[bdf["symbol"] == sym].sort_values("close_time")
        if len(h4) < d1_ema_period * 6 + 10:
            continue

        d1 = resample_h4_to_d1(h4)
        if len(d1) < d1_ema_period + 10:
            continue

        closes = d1["close"].values.astype(np.float64)
        close_times = d1["close_time_ms"].values.astype(np.int64)
        ema_vals = ema(closes, d1_ema_period)
        regime = closes > ema_vals

        sym_data[sym] = (close_times, regime)

    if not sym_data:
        return breadth_share

    sym_list = sorted(sym_data.keys())
    pointers = {s: 0 for s in sym_list}

    for i in range(n_btc):
        btc_ct = btc_h4_close_times[i]
        n_above = 0
        n_valid = 0
        for s in sym_list:
            ct_arr, regime_arr = sym_data[s]
            ptr = pointers[s]
            # Advance pointer to latest D1 bar with close_time <= btc_ct
            while ptr + 1 < len(ct_arr) and ct_arr[ptr + 1] <= btc_ct:
                ptr += 1
            pointers[s] = ptr
            if ct_arr[ptr] <= btc_ct:
                n_valid += 1
                if regime_arr[ptr]:
                    n_above += 1
        if n_valid > 0:
            breadth_share[i] = n_above / n_valid

    return breadth_share


def outcome_separation(ef: pd.DataFrame, var: str, label: str) -> dict:
    """Compute outcome separation for a breadth variable."""
    valid = ef.dropna(subset=[var])
    if len(valid) < 20:
        return {"variable": label, "n_valid": len(valid), "status": "INSUFFICIENT_DATA"}

    winners = valid[valid["is_winner"]]
    losers = valid[~valid["is_winner"]]

    result = {
        "variable": label,
        "n_valid": len(valid),
        "n_winners": len(winners),
        "n_losers": len(losers),
        "mean_winners": round(winners[var].mean(), 4) if len(winners) > 0 else None,
        "mean_losers": round(losers[var].mean(), 4) if len(losers) > 0 else None,
    }

    if len(winners) >= 5 and len(losers) >= 5:
        stat, p = sp_stats.mannwhitneyu(
            winners[var].values, losers[var].values, alternative="two-sided")
        result["mwu_p"] = round(p, 4)
        ks_stat, ks_p = sp_stats.ks_2samp(winners[var].values, losers[var].values)
        result["ks_p"] = round(ks_p, 4)

    valid_both = ef.dropna(subset=[var, "net_return_pct"])
    if len(valid_both) >= 20:
        r, p = sp_stats.spearmanr(valid_both[var], valid_both["net_return_pct"])
        result["spearman_r"] = round(r, 4)
        result["spearman_p"] = round(p, 4)

    return result


def quantile_expectancy(ef: pd.DataFrame, var: str, label: str,
                        n_bins: int = 5) -> pd.DataFrame:
    valid = ef.dropna(subset=[var]).copy()
    if len(valid) < n_bins * 3:
        return pd.DataFrame()
    valid["qbin"] = pd.qcut(valid[var], n_bins, labels=False, duplicates="drop")
    rows = []
    for q in sorted(valid["qbin"].unique()):
        subset = valid[valid["qbin"] == q]
        edges = (subset[var].min(), subset[var].max())
        n = len(subset)
        wins = subset["is_winner"].sum()
        rows.append({
            "variable": label,
            "quintile": int(q),
            "range_lo": round(edges[0], 4),
            "range_hi": round(edges[1], 4),
            "n_trades": n,
            "win_rate": round(wins / n * 100, 1),
            "mean_return_pct": round(subset["net_return_pct"].mean(), 3),
            "total_pnl_usd": round(subset["pnl_usd"].sum(), 0),
        })
    return pd.DataFrame(rows)


def paper_veto(ef: pd.DataFrame, var: str, label: str,
               thresholds: list, direction: str = "below") -> pd.DataFrame:
    valid = ef.dropna(subset=[var]).copy()
    if len(valid) < 10:
        return pd.DataFrame()
    rows = []
    for thr in thresholds:
        if direction == "below":
            blocked = valid[valid[var] < thr]
            passed = valid[valid[var] >= thr]
        else:
            blocked = valid[valid[var] > thr]
            passed = valid[valid[var] <= thr]
        if len(blocked) == 0:
            continue
        bl_losers = blocked[~blocked["is_winner"]]
        bl_winners = blocked[blocked["is_winner"]]
        rows.append({
            "variable": label,
            "threshold": thr,
            "direction": direction,
            "n_blocked": len(blocked),
            "n_passed": len(passed),
            "blocked_losers": len(bl_losers),
            "blocked_winners": len(bl_winners),
            "net_pnl_effect": round(-blocked["pnl_usd"].sum(), 0),
            "remaining_pnl": round(passed["pnl_usd"].sum(), 0),
        })
    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("D1.7 — Breadth Reconciliation: True D1 EMA(21)")
    print("=" * 70)

    # Load BTC bar features for H4 close times
    bf = pd.read_csv(ARTIFACTS / "bar_features.csv")
    btc_h4_cts = bf["close_time_ms"].values.astype(np.int64)
    bar_indices = bf["bar_index"].values

    # Load old (proxy) breadth
    old_breadth = bf["breadth_ema21_share"].values.astype(np.float64)

    # Compute new (exact D1 EMA(21)) breadth
    print("\nStep 1: Computing exact D1 EMA(21) breadth...")
    new_breadth = compute_breadth_exact(BREADTH_DATA, btc_h4_cts, d1_ema_period=21)

    # Compare old vs new
    valid_mask = ~(np.isnan(old_breadth) | np.isnan(new_breadth))
    n_valid = valid_mask.sum()
    diff = new_breadth[valid_mask] - old_breadth[valid_mask]

    print(f"\n  Valid comparison points: {n_valid}")
    print(f"  Mean absolute difference: {np.abs(diff).mean():.6f}")
    print(f"  Max absolute difference: {np.abs(diff).max():.6f}")
    print(f"  Correlation: {np.corrcoef(old_breadth[valid_mask], new_breadth[valid_mask])[0,1]:.6f}")
    print(f"  Mean old: {old_breadth[valid_mask].mean():.4f}")
    print(f"  Mean new: {new_breadth[valid_mask].mean():.4f}")

    # Exact match rate
    exact = (np.abs(diff) < 0.001).sum()
    close = (np.abs(diff) < 0.05).sum()
    print(f"  Exact match (< 0.001): {exact}/{n_valid} ({exact/n_valid*100:.1f}%)")
    print(f"  Close match (< 0.05): {close}/{n_valid} ({close/n_valid*100:.1f}%)")

    # Load entry features and replace breadth
    ef = pd.read_csv(ARTIFACTS / "entry_features_X0_base.csv")
    ef["is_winner"] = ef["net_return_pct"] > 0

    # Map new breadth to bar features by bar_index
    bf_new = bf.copy()
    bf_new["breadth_d1_exact"] = new_breadth

    # Map to entry features
    bf_lookup = bf_new.set_index("bar_index")[["breadth_d1_exact"]]
    ef = ef.merge(bf_lookup, left_on="decision_bar_idx", right_index=True, how="left")

    # Also keep old breadth for comparison
    ef["breadth_old"] = ef["breadth_ema21_share"]

    print(f"\n  Entry-level comparison:")
    old_vals = ef["breadth_old"].values
    new_vals = ef["breadth_d1_exact"].values
    valid_e = ~(np.isnan(old_vals) | np.isnan(new_vals))
    diff_e = new_vals[valid_e] - old_vals[valid_e]
    print(f"  Entries with both values: {valid_e.sum()}")
    print(f"  Mean abs diff: {np.abs(diff_e).mean():.6f}")
    print(f"  Max abs diff: {np.abs(diff_e).max():.6f}")
    print(f"  Correlation: {np.corrcoef(old_vals[valid_e], new_vals[valid_e])[0,1]:.6f}")

    # ── Reconciled diagnostics ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Step 2: Reconciled Breadth Diagnostics")
    print("=" * 70)

    # Outcome separation: new vs old
    print("\nOutcome separation (new exact D1 EMA(21)):")
    sep_new = outcome_separation(ef, "breadth_d1_exact", "breadth_d1_exact")
    sep_old = outcome_separation(ef, "breadth_old", "breadth_old_proxy")
    for label, result in [("NEW (exact)", sep_new), ("OLD (proxy)", sep_old)]:
        print(f"\n  {label}:")
        print(f"    Mean W: {result.get('mean_winners')}, Mean L: {result.get('mean_losers')}")
        print(f"    MWU p: {result.get('mwu_p')}, KS p: {result.get('ks_p')}")
        print(f"    Spearman r: {result.get('spearman_r')}, p: {result.get('spearman_p')}")

    # Quintile expectancy
    print("\nQuintile expectancy (new exact):")
    qe_new = quantile_expectancy(ef, "breadth_d1_exact", "breadth_d1_exact")
    if len(qe_new) > 0:
        for _, row in qe_new.iterrows():
            print(f"  Q{row['quintile']}: [{row['range_lo']:.4f}-{row['range_hi']:.4f}] "
                  f"N={row['n_trades']} WR={row['win_rate']}% "
                  f"MeanRet={row['mean_return_pct']:.3f}% PnL=${row['total_pnl_usd']:.0f}")

    # Paper veto: low breadth (full sample)
    print("\nPaper veto (new exact, full sample, veto low breadth):")
    q10 = ef["breadth_d1_exact"].dropna().quantile(0.10)
    q20 = ef["breadth_d1_exact"].dropna().quantile(0.20)
    q30 = ef["breadth_d1_exact"].dropna().quantile(0.30)
    pv_new = paper_veto(ef, "breadth_d1_exact", "breadth_d1_exact_low",
                        [q10, q20, q30], direction="below")
    for _, row in pv_new.iterrows():
        print(f"  below {row['threshold']:.4f}: blocked={row['n_blocked']}, "
              f"L={row['blocked_losers']}, W={row['blocked_winners']}, "
              f"net=${row['net_pnl_effect']:.0f}")

    # Re-entry subset
    print("\nRe-entry subset (new exact):")
    re = ef[ef["reentry_within_6_bars"] == 1]
    nre = ef[ef["reentry_within_6_bars"] == 0]
    sep_re = outcome_separation(re, "breadth_d1_exact", "breadth_d1_exact_reentry")
    sep_nre = outcome_separation(nre, "breadth_d1_exact", "breadth_d1_exact_non_reentry")
    for label, result in [("Re-entry", sep_re), ("Non-re-entry", sep_nre)]:
        print(f"  {label}: MWU p={result.get('mwu_p')}, "
              f"Spearman r={result.get('spearman_r')}, p={result.get('spearman_p')}")

    # Best paper rule from D1.5: re2_breadth_share > 0.80 (using new metric)
    print("\nPaper rule (re2_breadth_d1_exact > 0.80):")
    re2 = ef[ef["reentry_within_2_bars"] == 1].copy()
    blocked = re2[re2["breadth_d1_exact"] > 0.80]
    if len(blocked) > 0:
        nre2 = ef[ef["reentry_within_2_bars"] == 0]
        passed_re2 = re2[re2["breadth_d1_exact"] <= 0.80]
        new_pnl = nre2["pnl_usd"].sum() + passed_re2["pnl_usd"].sum()
        original = ef["pnl_usd"].sum()
        bl_l = (~blocked["is_winner"]).sum()
        bl_w = blocked["is_winner"].sum()
        print(f"  Blocked: {len(blocked)}, L={bl_l}, W={bl_w}")
        print(f"  Net effect: ${new_pnl - original:.0f}")
        print(f"  Remaining PnL: ${new_pnl:.0f}")
    else:
        print("  No trades blocked at this threshold")

    # ── Save reconciled artifacts ─────────────────────────────────────
    print("\nStep 3: Saving reconciled artifacts...")

    # Save reconciled entry features
    ef_out = ef[["trade_id", "breadth_old", "breadth_d1_exact"]].copy()
    ef_out.to_csv(ARTIFACTS / "breadth_reconciled_entries.csv", index=False)

    # Save reconciled bar-level breadth
    bf_out = bf[["bar_index", "close_time_ms"]].copy()
    bf_out["breadth_old_proxy"] = old_breadth
    bf_out["breadth_d1_exact"] = new_breadth
    bf_out.to_csv(ARTIFACTS / "breadth_reconciled_bars.csv", index=False)

    if len(qe_new) > 0:
        qe_new.to_csv(ARTIFACTS / "breadth_reconciled_quintile.csv", index=False)

    if len(pv_new) > 0:
        pv_new.to_csv(ARTIFACTS / "breadth_reconciled_paper_veto.csv", index=False)

    print("  Saved: breadth_reconciled_entries.csv")
    print("  Saved: breadth_reconciled_bars.csv")
    print("  Saved: breadth_reconciled_quintile.csv")
    print("  Saved: breadth_reconciled_paper_veto.csv")

    print("\n" + "=" * 70)
    print("D1.7 BREADTH RECONCILIATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
