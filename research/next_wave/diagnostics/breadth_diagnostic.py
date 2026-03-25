#!/usr/bin/env python3
"""D1.4 — Breadth / regime diagnostic on X0 default trades.

Analyzes whether BTC X0 default expectancy depends materially on
cross-sectional market breadth (fraction of alts above their D1 EMA(21)).

This is a BTC overlay diagnostic using cross-sectional market state
information — NOT basket construction, NOT multi-asset portfolio.

Variables analyzed:
  1. breadth_ema21_share = fraction of 13 alts with close > H4 EMA(126)
     (approximation of D1 EMA(21) via 6:1 mapping)
  2. breadth_pct_rank_90 = percentile rank of breadth within rolling 90-bar
     window (to capture "is breadth high/low relative to recent history?")

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
# Step 1: Load data and compute derived breadth metrics
# ═══════════════════════════════════════════════════════════════════════════

def load_data():
    """Load trade ledger and entry features with breadth already populated."""
    ef = pd.read_csv(ARTIFACTS / "entry_features_X0_base.csv")
    bf = pd.read_csv(ARTIFACTS / "bar_features.csv")

    # breadth_ema21_share is already in both DataFrames from D1.2
    # Compute rolling percentile rank for bar-level breadth
    breadth_vals = bf["breadth_ema21_share"].values.astype(np.float64)
    n = len(breadth_vals)
    window = 90  # ~15 days of H4 bars
    pct_rank = np.full(n, np.nan)
    for i in range(window, n):
        w = breadth_vals[i - window:i + 1]
        valid = w[~np.isnan(w)]
        if len(valid) >= 20:
            current = breadth_vals[i]
            if not np.isnan(current):
                pct_rank[i] = np.sum(valid <= current) / len(valid)
    bf["breadth_pct_rank_90"] = pct_rank

    # Map bar-level features to entry features via decision_bar_idx
    bf_lookup = bf.set_index("bar_index")[["breadth_pct_rank_90"]]
    ef = ef.merge(bf_lookup, left_on="decision_bar_idx", right_index=True,
                  how="left")

    # Win/loss classification
    ef["is_winner"] = ef["net_return_pct"] > 0

    return ef, bf


# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Outcome separation analysis
# ═══════════════════════════════════════════════════════════════════════════

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
        "mean_all": round(valid[var].mean(), 4),
        "mean_winners": round(winners[var].mean(), 4) if len(winners) > 0 else None,
        "mean_losers": round(losers[var].mean(), 4) if len(losers) > 0 else None,
        "median_all": round(valid[var].median(), 4),
        "median_winners": round(winners[var].median(), 4) if len(winners) > 0 else None,
        "median_losers": round(losers[var].median(), 4) if len(losers) > 0 else None,
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

    # Spearman correlation with net_return_pct
    valid_both = ef.dropna(subset=[var, "net_return_pct"])
    if len(valid_both) >= 20:
        r, p = sp_stats.spearmanr(valid_both[var], valid_both["net_return_pct"])
        result["spearman_r"] = round(r, 4)
        result["spearman_p"] = round(p, 4)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Quantile expectancy tables
# ═══════════════════════════════════════════════════════════════════════════

def quantile_expectancy(ef: pd.DataFrame, var: str, label: str,
                        n_bins: int = 5) -> pd.DataFrame:
    """Bin trades by breadth variable quantile, compute expectancy per bin."""
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
            "range_lo": round(edges[0], 4),
            "range_hi": round(edges[1], 4),
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
               thresholds: list, direction: str = "below") -> pd.DataFrame:
    """Simulate vetoing entries where breadth is weak (below threshold).

    direction='below': veto when var < threshold (weak breadth)
    direction='above': veto when var > threshold (extreme breadth)
    """
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

def incremental_info(ef: pd.DataFrame, breadth_var: str, context_vars: list) -> dict:
    """Assess whether breadth adds info beyond strategy context variables."""
    valid = ef.dropna(subset=[breadth_var] + context_vars + ["net_return_pct"]).copy()
    if len(valid) < 30:
        return {"status": "INSUFFICIENT_DATA"}

    # Breadth vs outcome
    r_breadth, p_breadth = sp_stats.spearmanr(valid[breadth_var], valid["net_return_pct"])

    # Breadth vs context vars
    context_corrs = {}
    for cv in context_vars:
        r, p = sp_stats.spearmanr(valid[breadth_var], valid[cv])
        context_corrs[cv] = {"r": round(r, 4), "p": round(p, 4)}

    # Context vars vs outcome
    context_outcome = {}
    for cv in context_vars:
        r, p = sp_stats.spearmanr(valid[cv], valid["net_return_pct"])
        context_outcome[cv] = {"r": round(r, 4), "p": round(p, 4)}

    return {
        "breadth_var": breadth_var,
        "n": len(valid),
        "breadth_vs_outcome": {"r": round(r_breadth, 4), "p": round(p_breadth, 4)},
        "breadth_vs_context": context_corrs,
        "context_vs_outcome": context_outcome,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Step 7: Concentration analysis
# ═══════════════════════════════════════════════════════════════════════════

def concentration_analysis(ef: pd.DataFrame, var: str, label: str) -> dict:
    """Check if worst/best trades cluster in extreme breadth states."""
    valid = ef.dropna(subset=[var, "pnl_usd"]).copy()
    if len(valid) < 20:
        return {"status": "INSUFFICIENT_DATA"}

    n = len(valid)
    n_worst = max(1, n // 5)  # bottom 20%
    n_best = max(1, n // 5)   # top 20%

    worst = valid.nsmallest(n_worst, "pnl_usd")
    best = valid.nlargest(n_best, "pnl_usd")

    # Define "weak breadth" and "strong breadth" states
    q20 = valid[var].quantile(0.20)
    q80 = valid[var].quantile(0.80)

    result = {
        "variable": label,
        "n_valid": n,
        "n_worst": len(worst),
        "n_best": len(best),
        "weak_threshold_q20": round(q20, 4),
        "strong_threshold_q80": round(q80, 4),
        "worst_in_weak_breadth": int((worst[var] <= q20).sum()),
        "worst_in_strong_breadth": int((worst[var] >= q80).sum()),
        "best_in_weak_breadth": int((best[var] <= q20).sum()),
        "best_in_strong_breadth": int((best[var] >= q80).sum()),
        "worst_mean_breadth": round(worst[var].mean(), 4),
        "best_mean_breadth": round(best[var].mean(), 4),
        "all_mean_breadth": round(valid[var].mean(), 4),
        "worst_pnl": round(worst["pnl_usd"].sum(), 0),
        "best_pnl": round(best["pnl_usd"].sum(), 0),
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Step 8: Derivatives vs breadth comparison
# ═══════════════════════════════════════════════════════════════════════════

def derivatives_comparison(ef: pd.DataFrame) -> dict:
    """Compare breadth and derivatives (funding) signal properties."""
    # Load derivatives diagnostic results for comparison
    deriv_report = ARTIFACTS.parent / "derivatives_diagnostic.md"

    # Compute breadth signal properties directly
    valid_b = ef.dropna(subset=["breadth_ema21_share", "net_return_pct"])
    r_b, p_b = sp_stats.spearmanr(valid_b["breadth_ema21_share"], valid_b["net_return_pct"])

    # Check funding if available
    funding_stats = None
    if "funding_raw" in ef.columns:
        valid_f = ef.dropna(subset=["funding_raw", "net_return_pct"])
        if len(valid_f) >= 20:
            r_f, p_f = sp_stats.spearmanr(valid_f["funding_raw"], valid_f["net_return_pct"])
            funding_stats = {
                "n": len(valid_f),
                "spearman_r": round(r_f, 4),
                "spearman_p": round(p_f, 4),
            }

    # Orthogonality: correlation between breadth and funding
    orthogonality = None
    if "funding_raw" in ef.columns:
        valid_bf = ef.dropna(subset=["breadth_ema21_share", "funding_raw"])
        if len(valid_bf) >= 20:
            r_bf, p_bf = sp_stats.spearmanr(valid_bf["breadth_ema21_share"], valid_bf["funding_raw"])
            orthogonality = {
                "breadth_funding_r": round(r_bf, 4),
                "breadth_funding_p": round(p_bf, 4),
                "n": len(valid_bf),
            }

    return {
        "breadth": {
            "n": len(valid_b),
            "spearman_r": round(r_b, 4),
            "spearman_p": round(p_b, 4),
            "coverage": f"{len(valid_b)}/186",
        },
        "funding": funding_stats,
        "orthogonality": orthogonality,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("D1.4 — Breadth / Regime Diagnostic on X0 Default Trades")
    print("=" * 70)

    # ── Load data ─────────────────────────────────────────────────────
    print("\nStep 1: Loading and preparing data...")
    ef, bf = load_data()
    print(f"  Trades: {len(ef)}")
    print(f"  Bar features: {len(bf)}")
    print(f"  Breadth NaN in entries: {ef['breadth_ema21_share'].isna().sum()}")
    print(f"  Breadth pct_rank NaN in entries: {ef['breadth_pct_rank_90'].isna().sum()}")
    print(f"  Winners: {ef['is_winner'].sum()}, Losers: {(~ef['is_winner']).sum()}")

    breadth_vars = [
        ("breadth_ema21_share", "breadth_share"),
        ("breadth_pct_rank_90", "breadth_pct_rank"),
    ]

    # ── Outcome separation ────────────────────────────────────────────
    print("\nStep 2: Outcome separation analysis...")
    sep_results = []
    for var, label in breadth_vars:
        result = outcome_separation(ef, var, label)
        sep_results.append(result)
        print(f"\n  {label}:")
        print(f"    N valid: {result.get('n_valid', 'N/A')}")
        print(f"    Mean W: {result.get('mean_winners', 'N/A')}, "
              f"Mean L: {result.get('mean_losers', 'N/A')}")
        print(f"    MWU p: {result.get('mwu_p', 'N/A')}, "
              f"KS p: {result.get('ks_p', 'N/A')}")
        print(f"    Spearman r: {result.get('spearman_r', 'N/A')}, "
              f"p: {result.get('spearman_p', 'N/A')}")

    # ── Quantile expectancy ───────────────────────────────────────────
    print("\nStep 3: Quantile expectancy tables...")
    qe_frames = []
    for var, label in breadth_vars:
        qe = quantile_expectancy(ef, var, label)
        if len(qe) > 0:
            qe_frames.append(qe)
            print(f"\n  {label}:")
            for _, row in qe.iterrows():
                print(f"    Q{row['quintile']}: [{row['range_lo']:.4f}-{row['range_hi']:.4f}] "
                      f"N={row['n_trades']} WR={row['win_rate']}% "
                      f"MeanRet={row['mean_return_pct']:.3f}% "
                      f"PnL=${row['total_pnl_usd']:.0f}")

    # ── Monotonicity test ─────────────────────────────────────────────
    print("\nStep 3b: Monotonicity assessment...")
    for qe in qe_frames:
        label = qe["variable"].iloc[0]
        wr = qe["win_rate"].values
        pnl = qe["total_pnl_usd"].values
        # Check if win rate is monotonically increasing with breadth
        wr_mono_up = all(wr[i] <= wr[i+1] for i in range(len(wr)-1))
        wr_mono_down = all(wr[i] >= wr[i+1] for i in range(len(wr)-1))
        pnl_mono_up = all(pnl[i] <= pnl[i+1] for i in range(len(pnl)-1))

        # Jonckheere-Terpstra trend test on returns across quintiles
        valid = ef.dropna(subset=[qe["variable"].iloc[0].replace("breadth_share", "breadth_ema21_share").replace("breadth_pct_rank", "breadth_pct_rank_90")]).copy()
        var_col = "breadth_ema21_share" if "share" in label else "breadth_pct_rank_90"
        valid["qbin"] = pd.qcut(valid[var_col], 5, labels=False, duplicates="drop")
        groups = [valid[valid["qbin"] == q]["net_return_pct"].values for q in sorted(valid["qbin"].unique())]

        # Kruskal-Wallis as monotonicity proxy
        if len(groups) >= 3 and all(len(g) >= 3 for g in groups):
            kw_stat, kw_p = sp_stats.kruskal(*groups)
        else:
            kw_stat, kw_p = np.nan, np.nan

        print(f"  {label}:")
        print(f"    Win rate monotone increasing: {wr_mono_up}")
        print(f"    Win rate monotone decreasing: {wr_mono_down}")
        print(f"    PnL monotone increasing: {pnl_mono_up}")
        print(f"    Kruskal-Wallis across quintiles: H={kw_stat:.2f}, p={kw_p:.4f}")

    # ── Paper veto analysis ───────────────────────────────────────────
    print("\nStep 4: Paper veto analysis...")
    # Breadth share: veto when breadth is LOW (weak market)
    # Use Q10, Q20, Q30 as narrow thresholds
    share_q10 = ef["breadth_ema21_share"].quantile(0.10)
    share_q20 = ef["breadth_ema21_share"].quantile(0.20)
    share_q30 = ef["breadth_ema21_share"].quantile(0.30)

    pv_share = paper_veto(ef, "breadth_ema21_share", "breadth_share_low",
                          [share_q10, share_q20, share_q30], direction="below")

    # Also test high breadth veto (contrarian)
    share_q90 = ef["breadth_ema21_share"].quantile(0.90)
    pv_share_high = paper_veto(ef, "breadth_ema21_share", "breadth_share_high",
                               [share_q90], direction="above")

    # Breadth pct_rank: veto when rank is LOW
    valid_pr = ef.dropna(subset=["breadth_pct_rank_90"])
    if len(valid_pr) > 0:
        pr_q10 = valid_pr["breadth_pct_rank_90"].quantile(0.10)
        pr_q20 = valid_pr["breadth_pct_rank_90"].quantile(0.20)
        pr_q30 = valid_pr["breadth_pct_rank_90"].quantile(0.30)
        pv_rank = paper_veto(ef, "breadth_pct_rank_90", "breadth_rank_low",
                             [pr_q10, pr_q20, pr_q30], direction="below")
    else:
        pv_rank = pd.DataFrame()

    pv_all = pd.concat([pv_share, pv_share_high, pv_rank], ignore_index=True)

    print("\n  Paper veto results:")
    for _, row in pv_all.iterrows():
        print(f"    {row['variable']} {row['direction']} {row['threshold']:.4f}: "
              f"blocked={row['n_blocked']}, "
              f"losers={row['blocked_losers']}, winners={row['blocked_winners']}, "
              f"net PnL effect=${row['net_pnl_effect']:.0f}")

    # ── Subset analysis ───────────────────────────────────────────────
    print("\nStep 5: Subset analysis...")
    subset_results = {}
    for var, label in breadth_vars:
        sub = subset_analysis(ef, var, label)
        subset_results[label] = sub
        for subset_name, result in sub.items():
            n = result.get("n_valid", 0)
            p = result.get("mwu_p", "N/A")
            print(f"  {label}_{subset_name}: N={n}, MWU p={p}")

    # ── Incremental information ───────────────────────────────────────
    print("\nStep 6: Incremental information...")
    context_vars = ["vdo", "bars_since_last_exit"]
    # Filter to entries that have context vars
    ef_ctx = ef.copy()
    ef_ctx["bars_since_last_exit"] = pd.to_numeric(ef_ctx["bars_since_last_exit"], errors="coerce")

    for var, label in breadth_vars:
        inc = incremental_info(ef_ctx, var, context_vars)
        print(f"\n  {label}:")
        if inc.get("status") == "INSUFFICIENT_DATA":
            print("    Insufficient data")
        else:
            bo = inc["breadth_vs_outcome"]
            print(f"    vs outcome: r={bo['r']}, p={bo['p']}")
            for cv, corr in inc["breadth_vs_context"].items():
                print(f"    vs {cv}: r={corr['r']}, p={corr['p']}")

    # ── Concentration analysis ────────────────────────────────────────
    print("\nStep 7: Concentration analysis...")
    conc_results = {}
    for var, label in breadth_vars:
        conc = concentration_analysis(ef, var, label)
        conc_results[label] = conc
        if conc.get("status") != "INSUFFICIENT_DATA":
            print(f"\n  {label}:")
            print(f"    Weak threshold (Q20): {conc['weak_threshold_q20']}")
            print(f"    Strong threshold (Q80): {conc['strong_threshold_q80']}")
            print(f"    Worst 20% in weak breadth: {conc['worst_in_weak_breadth']}/{conc['n_worst']}")
            print(f"    Worst 20% in strong breadth: {conc['worst_in_strong_breadth']}/{conc['n_worst']}")
            print(f"    Best 20% in weak breadth: {conc['best_in_weak_breadth']}/{conc['n_best']}")
            print(f"    Best 20% in strong breadth: {conc['best_in_strong_breadth']}/{conc['n_best']}")
            print(f"    Worst mean breadth: {conc['worst_mean_breadth']}, "
                  f"Best mean: {conc['best_mean_breadth']}, "
                  f"All mean: {conc['all_mean_breadth']}")

    # ── Derivatives vs breadth comparison ─────────────────────────────
    print("\nStep 8: Derivatives vs breadth comparison...")

    # Need funding data merged in for comparison
    # Load from derivatives artifacts if available
    try:
        funding = pd.read_csv(ARTIFACTS / "funding_btcusdt.csv")
        perp = pd.read_csv(ARTIFACTS / "perp_klines_btcusdt_4h.csv")

        # Align funding to entry features via bar_features
        funding = funding.sort_values("fundingTime").reset_index(drop=True)
        fund_times = funding["fundingTime"].values
        fund_rates = funding["fundingRate"].values

        bf_cts = bf["close_time_ms"].values
        n_bf = len(bf)
        funding_at_bar = np.full(n_bf, np.nan)
        ptr = 0
        for i in range(n_bf):
            while ptr + 1 < len(fund_times) and fund_times[ptr + 1] <= bf_cts[i]:
                ptr += 1
            if ptr < len(fund_times) and fund_times[ptr] <= bf_cts[i]:
                funding_at_bar[i] = fund_rates[ptr]
        bf["funding_raw"] = funding_at_bar

        bf_fund_lookup = bf.set_index("bar_index")[["funding_raw"]]
        ef = ef.merge(bf_fund_lookup, left_on="decision_bar_idx", right_index=True,
                      how="left", suffixes=("_old", ""))
        if "funding_raw_old" in ef.columns:
            ef.drop(columns=["funding_raw_old"], inplace=True)
    except Exception as e:
        print(f"  Warning: could not load derivatives data for comparison: {e}")

    comp = derivatives_comparison(ef)
    print(f"\n  Breadth vs outcome: r={comp['breadth']['spearman_r']}, "
          f"p={comp['breadth']['spearman_p']}, "
          f"coverage={comp['breadth']['coverage']}")
    if comp["funding"]:
        print(f"  Funding vs outcome: r={comp['funding']['spearman_r']}, "
              f"p={comp['funding']['spearman_p']}, "
              f"n={comp['funding']['n']}")
    if comp["orthogonality"]:
        orth = comp["orthogonality"]
        print(f"  Breadth-Funding correlation: r={orth['breadth_funding_r']}, "
              f"p={orth['breadth_funding_p']}")

    # ── Save machine-readable artifacts ───────────────────────────────
    print("\nStep 9: Saving artifacts...")

    # Outcome separation
    sep_df = pd.DataFrame(sep_results)
    sep_df.to_csv(ARTIFACTS / "breadth_outcome_separation.csv", index=False)

    # Quantile expectancy
    if qe_frames:
        qe_all = pd.concat(qe_frames, ignore_index=True)
        qe_all.to_csv(ARTIFACTS / "breadth_quantile_expectancy.csv", index=False)

    # Paper veto
    pv_all.to_csv(ARTIFACTS / "breadth_paper_veto.csv", index=False)

    # Comparison
    with open(ARTIFACTS / "breadth_vs_derivatives.json", "w") as f:
        json.dump(comp, f, indent=2)

    print("  Saved: breadth_outcome_separation.csv")
    print("  Saved: breadth_quantile_expectancy.csv")
    print("  Saved: breadth_paper_veto.csv")
    print("  Saved: breadth_vs_derivatives.json")

    print("\n" + "=" * 70)
    print("D1.4 DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
