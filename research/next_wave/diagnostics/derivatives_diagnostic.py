#!/usr/bin/env python3
"""D1.3 — Derivatives crowded-state diagnostic on X0 default trades.

Analyzes whether X0 losers/whipsaws cluster in interpretable derivatives states.
Uses D1.2 trade ledger + freshly fetched funding/basis data.

Variables analyzed:
  1. funding_rate (8h, mapped to H4 decision bars)
  2. basis_pct = (perp_close - spot_close) / spot_close * 100
  3. OI: EXCLUDED (only 83 records, covers last 2 weeks — unusable)

This is a DIAGNOSTIC STUDY. No overlay is implemented here.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Load and align data
# ═══════════════════════════════════════════════════════════════════════════

def load_and_align():
    """Load trade ledger, bar features, and derivatives data. Align by timestamp."""
    # Trade ledger (X0/base)
    trades = pd.read_csv(ARTIFACTS / "trades_X0_base.csv")
    # Entry features (X0/base)
    ef = pd.read_csv(ARTIFACTS / "entry_features_X0_base.csv")
    # Bar features
    bf = pd.read_csv(ARTIFACTS / "bar_features.csv")
    # Funding
    funding = pd.read_csv(ARTIFACTS / "funding_btcusdt.csv")
    # Perp klines
    perp = pd.read_csv(ARTIFACTS / "perp_klines_btcusdt_4h.csv")

    # ── Align funding to H4 bar grid ───────────────────────────────────
    # Funding events occur every 8h. For each H4 bar, use the most recent
    # funding rate with fundingTime <= bar close_time.
    funding = funding.sort_values("fundingTime").reset_index(drop=True)
    fund_times = funding["fundingTime"].values
    fund_rates = funding["fundingRate"].values

    bf_cts = bf["close_time_ms"].values
    n_bf = len(bf)

    # Map funding rate to each bar
    funding_at_bar = np.full(n_bf, np.nan)
    # Rolling 30-day (180 H4 bars ≈ 90 funding events) z-score
    # Use expanding percentile rank for robustness
    funding_pct_rank = np.full(n_bf, np.nan)

    fptr = 0
    recent_rates = []
    for i in range(n_bf):
        ct = bf_cts[i]
        while fptr + 1 < len(fund_times) and fund_times[fptr + 1] <= ct:
            fptr += 1
        if fptr < len(fund_times) and fund_times[fptr] <= ct:
            funding_at_bar[i] = fund_rates[fptr]
            recent_rates.append(fund_rates[fptr])
            # Keep last 90 funding events for percentile (30 days of 8h)
            if len(recent_rates) > 90:
                recent_rates.pop(0)
            if len(recent_rates) >= 10:
                arr = np.array(recent_rates)
                funding_pct_rank[i] = sp_stats.percentileofscore(
                    arr, fund_rates[fptr], kind="rank") / 100.0

    bf["funding_raw"] = funding_at_bar
    bf["funding_pct_rank_30d"] = funding_pct_rank

    # ── Align basis to H4 bar grid ────────────────────────────────────
    # basis_pct = (perp_close - spot_close) / spot_close * 100
    perp = perp.sort_values("close_time").reset_index(drop=True)
    perp_cts = perp["close_time"].values
    perp_closes = perp["close"].values

    basis_pct = np.full(n_bf, np.nan)
    pptr = 0
    for i in range(n_bf):
        ct = bf_cts[i]
        spot_close = bf.iloc[i]["close"]
        # Find perp bar with matching close_time (±30min tolerance = 1.8M ms)
        while pptr + 1 < len(perp_cts) and perp_cts[pptr + 1] <= ct:
            pptr += 1
        if pptr < len(perp_cts) and abs(perp_cts[pptr] - ct) < 1_800_000:
            basis_pct[i] = (perp_closes[pptr] - spot_close) / spot_close * 100

    bf["basis_pct"] = basis_pct

    # ── Merge derivatives features into entry features ─────────────────
    bf_lookup = bf.set_index("bar_index")[["funding_raw", "funding_pct_rank_30d", "basis_pct"]]
    ef = ef.merge(bf_lookup, left_on="decision_bar_idx", right_index=True,
                  how="left", suffixes=("_old", ""))

    # Clean up: remove old empty placeholder columns if they exist
    for col in ["funding_raw_old", "funding_pct_rank_old"]:
        if col in ef.columns:
            ef.drop(columns=[col], inplace=True)

    # Win/loss classification
    ef["is_winner"] = ef["net_return_pct"] > 0
    trades["is_winner"] = trades["net_return_pct"] > 0

    return trades, ef, bf


# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Outcome separation analysis
# ═══════════════════════════════════════════════════════════════════════════

def outcome_separation(ef: pd.DataFrame, var: str, label: str) -> dict:
    """Compute outcome separation for a derivatives variable."""
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
        "mean_all": round(valid[var].mean(), 6),
        "mean_winners": round(winners[var].mean(), 6) if len(winners) > 0 else None,
        "mean_losers": round(losers[var].mean(), 6) if len(losers) > 0 else None,
        "median_all": round(valid[var].median(), 6),
        "median_winners": round(winners[var].median(), 6) if len(winners) > 0 else None,
        "median_losers": round(losers[var].median(), 6) if len(losers) > 0 else None,
    }

    # Mann-Whitney U test (non-parametric)
    if len(winners) >= 5 and len(losers) >= 5:
        stat, p = sp_stats.mannwhitneyu(
            winners[var].values, losers[var].values, alternative="two-sided")
        result["mwu_stat"] = round(stat, 1)
        result["mwu_p"] = round(p, 4)
    else:
        result["mwu_p"] = None

    # KS test
    if len(winners) >= 5 and len(losers) >= 5:
        ks_stat, ks_p = sp_stats.ks_2samp(winners[var].values, losers[var].values)
        result["ks_stat"] = round(ks_stat, 4)
        result["ks_p"] = round(ks_p, 4)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Quantile expectancy tables
# ═══════════════════════════════════════════════════════════════════════════

def quantile_expectancy(ef: pd.DataFrame, var: str, label: str,
                        n_bins: int = 5) -> pd.DataFrame:
    """Bin trades by derivatives variable quantile, compute expectancy per bin."""
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
        ret_mean = subset["net_return_pct"].mean()
        ret_median = subset["net_return_pct"].median()
        pnl_sum = subset["pnl_usd"].sum()
        rows.append({
            "variable": label,
            "quintile": int(q),
            "range_lo": round(edges[0], 6),
            "range_hi": round(edges[1], 6),
            "n_trades": n,
            "win_rate": round(wins / n * 100, 1),
            "mean_return_pct": round(ret_mean, 3),
            "median_return_pct": round(ret_median, 3),
            "total_pnl_usd": round(pnl_sum, 0),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Paper veto analysis
# ═══════════════════════════════════════════════════════════════════════════

def paper_veto(ef: pd.DataFrame, var: str, label: str,
               thresholds: list, direction: str = "above") -> pd.DataFrame:
    """Simulate vetoing entries where var is above/below threshold.

    direction='above': veto when var > threshold (e.g., extreme funding)
    direction='below': veto when var < threshold
    """
    valid = ef.dropna(subset=[var]).copy()
    if len(valid) < 10:
        return pd.DataFrame()

    rows = []
    for thr in thresholds:
        if direction == "above":
            blocked = valid[valid[var] > thr]
            passed = valid[valid[var] <= thr]
        else:
            blocked = valid[valid[var] < thr]
            passed = valid[valid[var] >= thr]

        if len(blocked) == 0:
            continue

        bl_losers = blocked[~blocked["is_winner"]]
        bl_winners = blocked[blocked["is_winner"]]
        bl_pnl = blocked["pnl_usd"].sum()
        pa_pnl = passed["pnl_usd"].sum()

        rows.append({
            "variable": label,
            "threshold": thr,
            "direction": direction,
            "n_blocked": len(blocked),
            "n_passed": len(passed),
            "blocked_losers": len(bl_losers),
            "blocked_winners": len(bl_winners),
            "avoided_loss_pnl": round(bl_losers["pnl_usd"].sum(), 0),
            "missed_win_pnl": round(bl_winners["pnl_usd"].sum(), 0),
            "net_pnl_effect": round(-bl_pnl, 0),  # positive = blocking helped
            "blocked_mean_ret": round(blocked["net_return_pct"].mean(), 3),
            "passed_mean_ret": round(passed["net_return_pct"].mean(), 3),
            "original_total_pnl": round(valid["pnl_usd"].sum(), 0),
            "remaining_total_pnl": round(pa_pnl, 0),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Subset analysis (re-entry, post-stop)
# ═══════════════════════════════════════════════════════════════════════════

def subset_analysis(ef: pd.DataFrame, var: str, label: str) -> dict:
    """Run outcome separation on subsets: re-entry and post-stop."""
    results = {}

    # Re-entry trades (within 6 bars of prior exit)
    reentry = ef[ef["reentry_within_6_bars"] == 1]
    non_reentry = ef[ef["reentry_within_6_bars"] == 0]

    results["reentry"] = outcome_separation(reentry, var, f"{label}_reentry")
    results["non_reentry"] = outcome_separation(non_reentry, var, f"{label}_non_reentry")

    # Post-stop trades (prior exit was trail stop)
    post_stop = ef[ef["prior_exit_reason"] == "x0_trail_stop"]
    post_trend = ef[ef["prior_exit_reason"] == "x0_trend_exit"]

    results["post_stop"] = outcome_separation(post_stop, var, f"{label}_post_stop")
    results["post_trend"] = outcome_separation(post_trend, var, f"{label}_post_trend")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Step 6: Incremental information assessment
# ═══════════════════════════════════════════════════════════════════════════

def incremental_info(ef: pd.DataFrame, deriv_var: str, context_vars: list) -> dict:
    """Assess whether derivatives variable adds info beyond strategy context.

    Simple approach: correlation between deriv_var and context vars,
    plus partial correlation with trade outcome controlling for context.
    """
    valid = ef.dropna(subset=[deriv_var] + context_vars + ["net_return_pct"]).copy()
    if len(valid) < 30:
        return {"status": "INSUFFICIENT_DATA"}

    # Correlations with outcome
    r_deriv, p_deriv = sp_stats.spearmanr(valid[deriv_var], valid["net_return_pct"])

    # Correlations of deriv_var with context vars
    context_corrs = {}
    for cv in context_vars:
        r, p = sp_stats.spearmanr(valid[deriv_var], valid[cv])
        context_corrs[cv] = {"r": round(r, 4), "p": round(p, 4)}

    # Context variable correlations with outcome
    context_outcome_corrs = {}
    for cv in context_vars:
        r, p = sp_stats.spearmanr(valid[cv], valid["net_return_pct"])
        context_outcome_corrs[cv] = {"r": round(r, 4), "p": round(p, 4)}

    return {
        "deriv_var": deriv_var,
        "n": len(valid),
        "deriv_vs_outcome": {"r": round(r_deriv, 4), "p": round(p_deriv, 4)},
        "deriv_vs_context": context_corrs,
        "context_vs_outcome": context_outcome_corrs,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Step 7: Concentration analysis
# ═══════════════════════════════════════════════════════════════════════════

def concentration_analysis(ef: pd.DataFrame, var: str, label: str) -> dict:
    """Check if worst losses and best wins concentrate in extreme states."""
    valid = ef.dropna(subset=[var]).copy()
    if len(valid) < 20:
        return {"status": "INSUFFICIENT_DATA"}

    # Top/bottom 20% of derivatives variable
    q20 = valid[var].quantile(0.20)
    q80 = valid[var].quantile(0.80)

    extreme_high = valid[valid[var] > q80]
    extreme_low = valid[valid[var] < q20]
    middle = valid[(valid[var] >= q20) & (valid[var] <= q80)]

    # Worst 20% of trades by PnL
    pnl_q20 = valid["pnl_usd"].quantile(0.20)
    pnl_q80 = valid["pnl_usd"].quantile(0.80)
    worst_trades = valid[valid["pnl_usd"] <= pnl_q20]
    best_trades = valid[valid["pnl_usd"] >= pnl_q80]

    # How many worst trades are in extreme deriv states?
    worst_in_high = len(worst_trades[worst_trades[var] > q80])
    worst_in_low = len(worst_trades[worst_trades[var] < q20])
    best_in_high = len(best_trades[best_trades[var] > q80])
    best_in_low = len(best_trades[best_trades[var] < q20])

    n_worst = len(worst_trades)
    n_best = len(best_trades)

    return {
        "variable": label,
        "n_valid": len(valid),
        "q20_threshold": round(q20, 6),
        "q80_threshold": round(q80, 6),
        "extreme_high_trades": len(extreme_high),
        "extreme_high_mean_ret": round(extreme_high["net_return_pct"].mean(), 3),
        "extreme_low_trades": len(extreme_low),
        "extreme_low_mean_ret": round(extreme_low["net_return_pct"].mean(), 3),
        "middle_trades": len(middle),
        "middle_mean_ret": round(middle["net_return_pct"].mean(), 3),
        "worst_20pct_in_extreme_high": f"{worst_in_high}/{n_worst}",
        "worst_20pct_in_extreme_low": f"{worst_in_low}/{n_worst}",
        "best_20pct_in_extreme_high": f"{best_in_high}/{n_best}",
        "best_20pct_in_extreme_low": f"{best_in_low}/{n_best}",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("D1.3 — Derivatives Crowded-State Diagnostic")
    print("=" * 70)

    trades, ef, bf = load_and_align()

    # Coverage check
    n_funding_valid = ef["funding_raw"].notna().sum()
    n_basis_valid = ef["basis_pct"].notna().sum()
    print(f"\nCoverage: {n_funding_valid}/{len(ef)} entries have funding, "
          f"{n_basis_valid}/{len(ef)} have basis")
    print(f"Entries without derivatives: {len(ef) - n_funding_valid} "
          f"(pre-Sep 2019 trades)")

    # ── Outcome separation ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("OUTCOME SEPARATION (winners vs losers)")
    print("=" * 70)

    sep_results = []
    for var, label in [("funding_raw", "Funding Rate"),
                       ("funding_pct_rank_30d", "Funding Pct Rank (30d)"),
                       ("basis_pct", "Basis %")]:
        r = outcome_separation(ef, var, label)
        sep_results.append(r)
        print(f"\n{label}:")
        for k, v in r.items():
            if k != "variable":
                print(f"  {k}: {v}")

    # ── Concentration analysis ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CONCENTRATION OF EXTREME TRADES IN EXTREME DERIVATIVES STATES")
    print("=" * 70)

    conc_results = []
    for var, label in [("funding_raw", "Funding Rate"),
                       ("basis_pct", "Basis %")]:
        r = concentration_analysis(ef, var, label)
        conc_results.append(r)
        print(f"\n{label}:")
        for k, v in r.items():
            if k != "variable":
                print(f"  {k}: {v}")

    # ── Quantile expectancy tables ────────────────────────────────────
    print("\n" + "=" * 70)
    print("QUANTILE EXPECTANCY TABLES")
    print("=" * 70)

    all_qe = []
    for var, label in [("funding_raw", "Funding Rate"),
                       ("funding_pct_rank_30d", "Funding Pct Rank"),
                       ("basis_pct", "Basis %")]:
        qe = quantile_expectancy(ef, var, label, n_bins=5)
        if len(qe) > 0:
            all_qe.append(qe)
            print(f"\n{label}:")
            print(qe.to_string(index=False))

    if all_qe:
        pd.concat(all_qe).to_csv(ARTIFACTS / "deriv_quantile_expectancy.csv", index=False)

    # ── Paper veto analysis ───────────────────────────────────────────
    print("\n" + "=" * 70)
    print("PAPER VETO ANALYSIS")
    print("=" * 70)

    all_pv = []
    # Funding rate: veto extreme positive (crowded longs)
    fr_q90 = ef["funding_raw"].quantile(0.90)
    fr_q95 = ef["funding_raw"].quantile(0.95)
    fr_q80 = ef["funding_raw"].quantile(0.80)
    pv = paper_veto(ef, "funding_raw", "Funding Rate",
                    thresholds=[round(fr_q80, 6), round(fr_q90, 6), round(fr_q95, 6)],
                    direction="above")
    if len(pv) > 0:
        all_pv.append(pv)
        print("\nFunding Rate — veto when > threshold (crowded longs):")
        print(pv.to_string(index=False))

    # Funding rate: veto extreme negative (crowded shorts)
    fr_q10 = ef["funding_raw"].quantile(0.10)
    fr_q05 = ef["funding_raw"].quantile(0.05)
    fr_q20 = ef["funding_raw"].quantile(0.20)
    pv2 = paper_veto(ef, "funding_raw", "Funding Rate",
                     thresholds=[round(fr_q20, 6), round(fr_q10, 6), round(fr_q05, 6)],
                     direction="below")
    if len(pv2) > 0:
        all_pv.append(pv2)
        print("\nFunding Rate — veto when < threshold (crowded shorts):")
        print(pv2.to_string(index=False))

    # Basis: veto extreme positive (overheated perp premium)
    if ef["basis_pct"].notna().sum() > 20:
        bp_q80 = ef["basis_pct"].quantile(0.80)
        bp_q90 = ef["basis_pct"].quantile(0.90)
        bp_q95 = ef["basis_pct"].quantile(0.95)
        pv3 = paper_veto(ef, "basis_pct", "Basis %",
                         thresholds=[round(bp_q80, 4), round(bp_q90, 4), round(bp_q95, 4)],
                         direction="above")
        if len(pv3) > 0:
            all_pv.append(pv3)
            print("\nBasis % — veto when > threshold (overheated premium):")
            print(pv3.to_string(index=False))

    if all_pv:
        pd.concat(all_pv).to_csv(ARTIFACTS / "deriv_paper_veto.csv", index=False)

    # ── Subset analysis ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUBSET ANALYSIS (re-entry / post-stop)")
    print("=" * 70)

    for var, label in [("funding_raw", "Funding Rate"),
                       ("basis_pct", "Basis %")]:
        subs = subset_analysis(ef, var, label)
        for subset_name, res in subs.items():
            n = res.get("n_valid", 0)
            if n < 5:
                print(f"\n{label} / {subset_name}: insufficient data (n={n})")
                continue
            mw_p = res.get("mwu_p", "N/A")
            print(f"\n{label} / {subset_name}: n={n}, "
                  f"mean_W={res.get('mean_winners','')}, "
                  f"mean_L={res.get('mean_losers','')}, "
                  f"MWU p={mw_p}")

    # ── Incremental information ───────────────────────────────────────
    print("\n" + "=" * 70)
    print("INCREMENTAL INFORMATION vs STRATEGY CONTEXT")
    print("=" * 70)

    context_vars = ["vdo", "d1_regime"]
    # Add bars_since_last_exit (numeric only)
    ef_num = ef.copy()
    ef_num["bse_numeric"] = pd.to_numeric(ef_num["bars_since_last_exit"], errors="coerce")
    context_with_bse = context_vars + ["bse_numeric"]

    for var, label in [("funding_raw", "Funding Rate"),
                       ("basis_pct", "Basis %")]:
        info = incremental_info(ef_num, var, context_with_bse)
        print(f"\n{label}:")
        if "status" in info:
            print(f"  {info['status']}")
        else:
            print(f"  n={info['n']}")
            dvo = info["deriv_vs_outcome"]
            print(f"  {var} vs outcome: r={dvo['r']}, p={dvo['p']}")
            for cv, cr in info["deriv_vs_context"].items():
                print(f"  {var} vs {cv}: r={cr['r']}, p={cr['p']}")
            for cv, cr in info["context_vs_outcome"].items():
                print(f"  {cv} vs outcome: r={cr['r']}, p={cr['p']}")

    # ── Monotonicity check ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("MONOTONICITY CHECK (quintile mean return trend)")
    print("=" * 70)

    for var, label in [("funding_raw", "Funding Rate"),
                       ("basis_pct", "Basis %")]:
        qe = quantile_expectancy(ef, var, label, n_bins=5)
        if len(qe) > 0:
            rets = qe["mean_return_pct"].values
            # Check if monotonically decreasing (higher var = worse returns)
            mono_dec = all(rets[i] >= rets[i+1] for i in range(len(rets)-1))
            mono_inc = all(rets[i] <= rets[i+1] for i in range(len(rets)-1))
            tau, tau_p = sp_stats.kendalltau(range(len(rets)), rets)
            print(f"\n{label}: monotonic_dec={mono_dec}, monotonic_inc={mono_inc}")
            print(f"  Kendall tau={tau:.4f}, p={tau_p:.4f}")
            print(f"  Quintile returns: {[round(r, 2) for r in rets]}")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
