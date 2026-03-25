#!/usr/bin/env python3
"""D1.5 — Conditional re-entry / state divergence diagnostic on X0 default trades.

Analyzes whether bad re-entries cluster in identifiable states that could
justify a state-machine-lite conditional re-entry rule.

This is NOT a generic cooldown sweep. We test whether specific contexts
(breadth, derivatives, exit reason, VDO) make re-entries systematically worse.

This is a DIAGNOSTIC STUDY. No rule is implemented here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Load and prepare data
# ═══════════════════════════════════════════════════════════════════════════

def load_data():
    """Load X0 and anchor entry features, compute derived metrics."""
    ef = pd.read_csv(ARTIFACTS / "entry_features_X0_base.csv")
    ef_anchor = pd.read_csv(ARTIFACTS / "entry_features_E0_EMA21_base.csv")
    bf = pd.read_csv(ARTIFACTS / "bar_features.csv")

    ef["is_winner"] = ef["net_return_pct"] > 0
    ef_anchor["is_winner"] = ef_anchor["net_return_pct"] > 0
    ef["bse"] = pd.to_numeric(ef["bars_since_last_exit"], errors="coerce")
    ef_anchor["bse"] = pd.to_numeric(ef_anchor["bars_since_last_exit"], errors="coerce")

    # Compute breadth pct_rank from bar features
    breadth_vals = bf["breadth_ema21_share"].values.astype(np.float64)
    n = len(breadth_vals)
    window = 90
    pct_rank = np.full(n, np.nan)
    for i in range(window, n):
        w = breadth_vals[i - window:i + 1]
        valid = w[~np.isnan(w)]
        if len(valid) >= 20:
            current = breadth_vals[i]
            if not np.isnan(current):
                pct_rank[i] = np.sum(valid <= current) / len(valid)
    bf["breadth_pct_rank_90"] = pct_rank

    # Align funding to bar features
    try:
        funding = pd.read_csv(ARTIFACTS / "funding_btcusdt.csv")
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

        # Rolling pct_rank for funding
        fund_pct_rank = np.full(n_bf, np.nan)
        for i in range(90, n_bf):
            w = funding_at_bar[i - 90:i + 1]
            valid = w[~np.isnan(w)]
            if len(valid) >= 20:
                current = funding_at_bar[i]
                if not np.isnan(current):
                    fund_pct_rank[i] = np.sum(valid <= current) / len(valid)

        bf["funding_raw"] = funding_at_bar
        bf["funding_pct_rank_30d"] = fund_pct_rank
    except Exception:
        bf["funding_raw"] = np.nan
        bf["funding_pct_rank_30d"] = np.nan

    # Merge bar-level features to entry features
    bf_lookup = bf.set_index("bar_index")[["breadth_pct_rank_90", "funding_raw", "funding_pct_rank_30d"]]
    ef = ef.merge(bf_lookup, left_on="decision_bar_idx", right_index=True,
                  how="left", suffixes=("_old", ""))
    for col in ["funding_raw_old"]:
        if col in ef.columns:
            ef.drop(columns=[col], inplace=True)

    return ef, ef_anchor, bf


# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Re-entry definition table
# ═══════════════════════════════════════════════════════════════════════════

def reentry_definition_table(ef: pd.DataFrame) -> pd.DataFrame:
    """Compute re-entry stats for each definition threshold."""
    rows = []
    for n_bars in [1, 2, 3, 4, 6]:
        col = f"reentry_within_{n_bars}_bars"
        re = ef[ef[col] == 1]
        nre = ef[ef[col] == 0]

        row = {
            "threshold_bars": n_bars,
            "n_reentry": len(re),
            "n_nonreentry": len(nre),
            "pct_reentry": round(len(re) / len(ef) * 100, 1),
            "re_win_rate": round(re["is_winner"].mean() * 100, 1) if len(re) > 0 else None,
            "nre_win_rate": round(nre["is_winner"].mean() * 100, 1) if len(nre) > 0 else None,
            "re_mean_ret": round(re["net_return_pct"].mean(), 3) if len(re) > 0 else None,
            "nre_mean_ret": round(nre["net_return_pct"].mean(), 3) if len(nre) > 0 else None,
            "re_pnl": round(re["pnl_usd"].sum(), 0) if len(re) > 0 else 0,
            "nre_pnl": round(nre["pnl_usd"].sum(), 0) if len(nre) > 0 else 0,
        }

        if len(re) >= 5 and len(nre) >= 5:
            stat, p = sp_stats.mannwhitneyu(
                re["net_return_pct"].values, nre["net_return_pct"].values,
                alternative="two-sided")
            row["mwu_p"] = round(p, 4)
        else:
            row["mwu_p"] = None

        rows.append(row)

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Contextual clustering of re-entry losers
# ═══════════════════════════════════════════════════════════════════════════

def contextual_clustering(ef: pd.DataFrame) -> dict:
    """Check if re-entry losers cluster in specific contexts."""
    re = ef[ef["reentry_within_6_bars"] == 1].copy()
    re_w = re[re["is_winner"]]
    re_l = re[~re["is_winner"]]

    results = {}

    # --- Breadth clustering ---
    b_q20 = ef["breadth_ema21_share"].quantile(0.20)
    b_q80 = ef["breadth_ema21_share"].quantile(0.80)

    breadth_cluster = {
        "thresholds": {"q20": round(b_q20, 4), "q80": round(b_q80, 4)},
        "losers_n": len(re_l),
        "losers_in_low_breadth": int((re_l["breadth_ema21_share"] <= b_q20).sum()),
        "losers_in_high_breadth": int((re_l["breadth_ema21_share"] >= b_q80).sum()),
        "winners_n": len(re_w),
        "winners_in_low_breadth": int((re_w["breadth_ema21_share"] <= b_q20).sum()),
        "winners_in_high_breadth": int((re_w["breadth_ema21_share"] >= b_q80).sum()),
        "losers_mean_breadth": round(re_l["breadth_ema21_share"].mean(), 4),
        "winners_mean_breadth": round(re_w["breadth_ema21_share"].mean(), 4),
    }
    results["breadth"] = breadth_cluster

    # --- Breadth pct_rank clustering ---
    valid_pr = re.dropna(subset=["breadth_pct_rank_90"])
    if len(valid_pr) > 0:
        pr_q20 = valid_pr["breadth_pct_rank_90"].quantile(0.20)
        pr_q80 = valid_pr["breadth_pct_rank_90"].quantile(0.80)
        re_l_pr = valid_pr[~valid_pr["is_winner"]]
        re_w_pr = valid_pr[valid_pr["is_winner"]]
        results["breadth_pct_rank"] = {
            "thresholds": {"q20": round(pr_q20, 4), "q80": round(pr_q80, 4)},
            "losers_in_high_rank": int((re_l_pr["breadth_pct_rank_90"] >= pr_q80).sum()),
            "losers_in_low_rank": int((re_l_pr["breadth_pct_rank_90"] <= pr_q20).sum()),
            "winners_in_high_rank": int((re_w_pr["breadth_pct_rank_90"] >= pr_q80).sum()),
            "winners_in_low_rank": int((re_w_pr["breadth_pct_rank_90"] <= pr_q20).sum()),
            "losers_mean": round(re_l_pr["breadth_pct_rank_90"].mean(), 4),
            "winners_mean": round(re_w_pr["breadth_pct_rank_90"].mean(), 4),
        }

    # --- Funding clustering ---
    valid_f = re.dropna(subset=["funding_pct_rank_30d"])
    if len(valid_f) >= 10:
        f_q80 = valid_f["funding_pct_rank_30d"].quantile(0.80)
        re_l_f = valid_f[~valid_f["is_winner"]]
        re_w_f = valid_f[valid_f["is_winner"]]
        results["funding"] = {
            "threshold_q80": round(f_q80, 4),
            "losers_in_high_funding": int((re_l_f["funding_pct_rank_30d"] >= f_q80).sum()),
            "losers_total": len(re_l_f),
            "winners_in_high_funding": int((re_w_f["funding_pct_rank_30d"] >= f_q80).sum()),
            "winners_total": len(re_w_f),
            "losers_mean_funding": round(re_l_f["funding_pct_rank_30d"].mean(), 4),
            "winners_mean_funding": round(re_w_f["funding_pct_rank_30d"].mean(), 4),
        }

    # --- VDO clustering ---
    vdo_q20 = ef["vdo"].quantile(0.20)
    vdo_q80 = ef["vdo"].quantile(0.80)
    results["vdo"] = {
        "thresholds": {"q20": round(vdo_q20, 6), "q80": round(vdo_q80, 6)},
        "losers_low_vdo": int((re_l["vdo"] <= vdo_q20).sum()),
        "losers_high_vdo": int((re_l["vdo"] >= vdo_q80).sum()),
        "winners_low_vdo": int((re_w["vdo"] <= vdo_q20).sum()),
        "winners_high_vdo": int((re_w["vdo"] >= vdo_q80).sum()),
        "losers_mean_vdo": round(re_l["vdo"].mean(), 6),
        "winners_mean_vdo": round(re_w["vdo"].mean(), 6),
    }

    # --- BSE granularity within re-entries ---
    bse_data = []
    for n in [1, 2, 3, 4, 6]:
        col = f"reentry_within_{n}_bars"
        tight = re[re[col] == 1]
        bse_data.append({
            "within_bars": n,
            "n": len(tight),
            "win_rate": round(tight["is_winner"].mean() * 100, 1) if len(tight) > 0 else None,
            "mean_ret": round(tight["net_return_pct"].mean(), 3) if len(tight) > 0 else None,
            "pnl": round(tight["pnl_usd"].sum(), 0) if len(tight) > 0 else 0,
        })
    results["bse_granularity"] = bse_data

    # --- Exit reason clustering ---
    results["exit_reason"] = {
        "post_stop_n": len(re[re["prior_exit_reason"] == "x0_trail_stop"]),
        "post_stop_wr": round(re[re["prior_exit_reason"] == "x0_trail_stop"]["is_winner"].mean() * 100, 1),
        "post_trend_n": len(re[re["prior_exit_reason"] == "x0_trend_exit"]),
        "post_trend_wr": round(re[re["prior_exit_reason"] == "x0_trend_exit"]["is_winner"].mean() * 100, 1)
        if len(re[re["prior_exit_reason"] == "x0_trend_exit"]) > 0 else None,
    }

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Step 4: State divergence analysis (X0 vs anchor)
# ═══════════════════════════════════════════════════════════════════════════

def state_divergence(ef: pd.DataFrame, ef_anchor: pd.DataFrame) -> dict:
    """Analyze how X0's altered re-entry path affects outcomes vs anchor."""
    x0_entries = set(ef["entry_ts_ms"].values)
    anchor_entries = set(ef_anchor["entry_ts_ms"].values)
    shared = x0_entries & anchor_entries
    x0_only = x0_entries - anchor_entries
    anchor_only = anchor_entries - x0_entries

    x0_only_df = ef[ef["entry_ts_ms"].isin(x0_only)]
    anchor_only_df = ef_anchor[ef_anchor["entry_ts_ms"].isin(anchor_only)]
    shared_x0 = ef[ef["entry_ts_ms"].isin(shared)]
    shared_anchor = ef_anchor[ef_anchor["entry_ts_ms"].isin(shared)]

    # How many X0-only trades are re-entries?
    x0_only_reentry = x0_only_df["reentry_within_6_bars"].sum() if len(x0_only_df) > 0 else 0

    # Shared trades: do they have different outcomes due to different exits?
    # (Different trailing stop = different exit_ts_ms for same entry)
    shared_merged = shared_x0[["entry_ts_ms", "net_return_pct", "pnl_usd", "exit_ts_ms",
                                "holding_bars"]].merge(
        shared_anchor[["entry_ts_ms", "net_return_pct", "pnl_usd", "exit_ts_ms",
                        "holding_bars"]],
        on="entry_ts_ms", suffixes=("_x0", "_anchor"))

    same_exit = (shared_merged["exit_ts_ms_x0"] == shared_merged["exit_ts_ms_anchor"]).sum()
    diff_exit = len(shared_merged) - same_exit

    x0_pnl_shared = shared_merged["pnl_usd_x0"].sum()
    anchor_pnl_shared = shared_merged["pnl_usd_anchor"].sum()

    # Attribution: how much of X0's total PnL advantage comes from each source?
    x0_total = ef["pnl_usd"].sum()
    anchor_total = ef_anchor["pnl_usd"].sum()
    advantage = x0_total - anchor_total

    pnl_from_x0_only = x0_only_df["pnl_usd"].sum() if len(x0_only_df) > 0 else 0
    pnl_from_anchor_only = anchor_only_df["pnl_usd"].sum() if len(anchor_only_df) > 0 else 0
    pnl_from_shared_diff = x0_pnl_shared - anchor_pnl_shared

    return {
        "x0_trades": len(ef),
        "anchor_trades": len(ef_anchor),
        "shared_entries": len(shared),
        "x0_only_entries": len(x0_only),
        "anchor_only_entries": len(anchor_only),
        "x0_only_reentry_count": int(x0_only_reentry),
        "x0_only_pnl": round(pnl_from_x0_only, 0),
        "x0_only_wr": round(x0_only_df["is_winner"].mean() * 100, 1) if len(x0_only_df) > 0 else None,
        "anchor_only_pnl": round(pnl_from_anchor_only, 0),
        "anchor_only_wr": round(anchor_only_df["is_winner"].mean() * 100, 1) if len(anchor_only_df) > 0 else None,
        "shared_same_exit": int(same_exit),
        "shared_diff_exit": int(diff_exit),
        "shared_pnl_x0": round(x0_pnl_shared, 0),
        "shared_pnl_anchor": round(anchor_pnl_shared, 0),
        "x0_total_pnl": round(x0_total, 0),
        "anchor_total_pnl": round(anchor_total, 0),
        "total_advantage": round(advantage, 0),
        "advantage_from_x0_only_trades": round(pnl_from_x0_only, 0),
        "advantage_from_avoided_anchor_only": round(-pnl_from_anchor_only, 0),
        "advantage_from_shared_exit_diff": round(pnl_from_shared_diff, 0),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Step 5: Paper rule analysis
# ═══════════════════════════════════════════════════════════════════════════

def paper_rule_analysis(ef: pd.DataFrame) -> pd.DataFrame:
    """Test 3 narrow conditional re-entry rules."""
    re = ef[ef["reentry_within_6_bars"] == 1].copy()
    all_pnl = ef["pnl_usd"].sum()
    rows = []

    # Rule 1: Veto re-entry within 6 bars when breadth_pct_rank > 0.58
    valid = re.dropna(subset=["breadth_pct_rank_90"])
    if len(valid) > 0:
        blocked = valid[valid["breadth_pct_rank_90"] > 0.58]
        passed_re = valid[valid["breadth_pct_rank_90"] <= 0.58]
        nre = ef[ef["reentry_within_6_bars"] == 0]
        new_pnl = nre["pnl_usd"].sum() + passed_re["pnl_usd"].sum()
        rows.append({
            "rule": "re6_breadth_rank_gt_0.58",
            "description": "Veto re-entry (<=6 bars) when breadth_pct_rank_90 > 0.58",
            "n_blocked": len(blocked),
            "n_remaining": len(ef) - len(blocked),
            "blocked_losers": int((~blocked["is_winner"]).sum()),
            "blocked_winners": int(blocked["is_winner"].sum()),
            "blocked_pnl": round(blocked["pnl_usd"].sum(), 0),
            "original_pnl": round(all_pnl, 0),
            "remaining_pnl": round(new_pnl, 0),
            "net_effect": round(new_pnl - all_pnl, 0),
            "blocked_mean_ret": round(blocked["net_return_pct"].mean(), 3),
        })

    # Rule 2: Veto re-entry within 2 bars when breadth_ema21_share > 0.80
    re2 = ef[ef["reentry_within_2_bars"] == 1].copy()
    if len(re2) > 0:
        blocked = re2[re2["breadth_ema21_share"] > 0.80]
        nre2 = ef[ef["reentry_within_2_bars"] == 0]
        passed_re2 = re2[re2["breadth_ema21_share"] <= 0.80]
        new_pnl = nre2["pnl_usd"].sum() + passed_re2["pnl_usd"].sum()
        rows.append({
            "rule": "re2_breadth_share_gt_0.80",
            "description": "Veto re-entry (<=2 bars) when breadth_share > 0.80",
            "n_blocked": len(blocked),
            "n_remaining": len(ef) - len(blocked),
            "blocked_losers": int((~blocked["is_winner"]).sum()),
            "blocked_winners": int(blocked["is_winner"].sum()),
            "blocked_pnl": round(blocked["pnl_usd"].sum(), 0),
            "original_pnl": round(all_pnl, 0),
            "remaining_pnl": round(new_pnl, 0),
            "net_effect": round(new_pnl - all_pnl, 0),
            "blocked_mean_ret": round(blocked["net_return_pct"].mean(), 3),
        })

    # Rule 3: Veto re-entry within 6 bars when funding_pct_rank > 0.80
    valid_f = re.dropna(subset=["funding_pct_rank_30d"])
    if len(valid_f) > 0:
        blocked = valid_f[valid_f["funding_pct_rank_30d"] > 0.80]
        # For this rule, can only count on trades with funding data
        nre_f = ef[(ef["reentry_within_6_bars"] == 0)]
        passed_re_f = valid_f[valid_f["funding_pct_rank_30d"] <= 0.80]
        # Calculate on trades with funding data for fair comparison
        has_funding = ef.dropna(subset=["funding_pct_rank_30d"])
        nre_pnl = has_funding[has_funding["reentry_within_6_bars"] == 0]["pnl_usd"].sum()
        new_pnl = nre_pnl + passed_re_f["pnl_usd"].sum()
        original_with_funding = has_funding["pnl_usd"].sum()
        rows.append({
            "rule": "re6_funding_rank_gt_0.80",
            "description": "Veto re-entry (<=6 bars) when funding_pct_rank > 0.80",
            "n_blocked": len(blocked),
            "n_remaining": len(has_funding) - len(blocked),
            "blocked_losers": int((~blocked["is_winner"]).sum()),
            "blocked_winners": int(blocked["is_winner"].sum()),
            "blocked_pnl": round(blocked["pnl_usd"].sum(), 0),
            "original_pnl": round(original_with_funding, 0),
            "remaining_pnl": round(new_pnl, 0),
            "net_effect": round(new_pnl - original_with_funding, 0),
            "blocked_mean_ret": round(blocked["net_return_pct"].mean(), 3),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
# Step 6: Worst re-entry trade analysis
# ═══════════════════════════════════════════════════════════════════════════

def worst_reentry_analysis(ef: pd.DataFrame) -> dict:
    """Analyze the worst re-entry trades to see if they share contexts."""
    re = ef[ef["reentry_within_6_bars"] == 1].copy()
    re_sorted = re.sort_values("pnl_usd")

    # Worst 10 re-entries
    worst10 = re_sorted.head(10)
    best10 = re_sorted.tail(10)

    worst_years = worst10["entry_time"].str[:4].value_counts().to_dict()
    best_years = best10["entry_time"].str[:4].value_counts().to_dict()

    return {
        "worst10_pnl": round(worst10["pnl_usd"].sum(), 0),
        "worst10_mean_breadth": round(worst10["breadth_ema21_share"].mean(), 4),
        "worst10_mean_bse": round(worst10["bse"].mean(), 1),
        "worst10_years": worst_years,
        "best10_pnl": round(best10["pnl_usd"].sum(), 0),
        "best10_mean_breadth": round(best10["breadth_ema21_share"].mean(), 4),
        "best10_mean_bse": round(best10["bse"].mean(), 1),
        "best10_years": best_years,
        "total_re_pnl": round(re["pnl_usd"].sum(), 0),
        "worst10_as_pct_of_total": round(worst10["pnl_usd"].sum() / re["pnl_usd"].sum() * 100, 1)
        if re["pnl_usd"].sum() != 0 else None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("D1.5 — Conditional Re-entry / State Divergence Diagnostic")
    print("=" * 70)

    # ── Load data ─────────────────────────────────────────────────────
    print("\nStep 1: Loading data...")
    ef, ef_anchor, bf = load_data()
    print(f"  X0 trades: {len(ef)}, Anchor trades: {len(ef_anchor)}")
    print(f"  Re-entry (6 bars): {ef['reentry_within_6_bars'].sum()}/{len(ef)} "
          f"({ef['reentry_within_6_bars'].mean()*100:.1f}%)")

    # ── Re-entry definition table ─────────────────────────────────────
    print("\nStep 2: Re-entry definition table...")
    rdt = reentry_definition_table(ef)
    for _, row in rdt.iterrows():
        print(f"  Within {row['threshold_bars']} bars: {row['n_reentry']} ({row['pct_reentry']}%) "
              f"WR_re={row['re_win_rate']}% WR_nre={row['nre_win_rate']}% "
              f"MWU p={row['mwu_p']}")

    # ── Re-entry vs non-re-entry expectancy ───────────────────────────
    print("\nStep 2b: Re-entry vs non-re-entry expectancy (6-bar definition)...")
    re = ef[ef["reentry_within_6_bars"] == 1]
    nre = ef[ef["reentry_within_6_bars"] == 0]
    print(f"  Re-entry: N={len(re)}, WR={re['is_winner'].mean()*100:.1f}%, "
          f"MeanRet={re['net_return_pct'].mean():.3f}%, PnL=${re['pnl_usd'].sum():.0f}")
    print(f"  Non-re:   N={len(nre)}, WR={nre['is_winner'].mean()*100:.1f}%, "
          f"MeanRet={nre['net_return_pct'].mean():.3f}%, PnL=${nre['pnl_usd'].sum():.0f}")

    # Test if re-entry mean return is significantly different
    stat, p = sp_stats.mannwhitneyu(re["net_return_pct"].values, nre["net_return_pct"].values,
                                     alternative="two-sided")
    print(f"  MWU p={p:.4f} — {'significant' if p < 0.05 else 'NOT significant'}")

    # PnL per trade comparison
    re_pnl_per = re["pnl_usd"].mean()
    nre_pnl_per = nre["pnl_usd"].mean()
    print(f"  PnL/trade: re=${re_pnl_per:.0f}, nre=${nre_pnl_per:.0f}")

    # ── Contextual clustering ─────────────────────────────────────────
    print("\nStep 3: Contextual clustering of re-entry outcomes...")
    clustering = contextual_clustering(ef)

    print("\n  Breadth clustering (within re-entries):")
    bc = clustering["breadth"]
    print(f"    Losers in low breadth: {bc['losers_in_low_breadth']}/{bc['losers_n']} "
          f"({bc['losers_in_low_breadth']/bc['losers_n']*100:.0f}%)")
    print(f"    Losers in high breadth: {bc['losers_in_high_breadth']}/{bc['losers_n']} "
          f"({bc['losers_in_high_breadth']/bc['losers_n']*100:.0f}%)")
    print(f"    Winners in low breadth: {bc['winners_in_low_breadth']}/{bc['winners_n']} "
          f"({bc['winners_in_low_breadth']/bc['winners_n']*100:.0f}%)")

    if "breadth_pct_rank" in clustering:
        bpr = clustering["breadth_pct_rank"]
        print(f"\n  Breadth pct_rank clustering:")
        print(f"    Losers in high rank: {bpr['losers_in_high_rank']}/{bc['losers_n']} "
              f"— mean rank L={bpr['losers_mean']:.4f} vs W={bpr['winners_mean']:.4f}")

    if "funding" in clustering:
        fc = clustering["funding"]
        print(f"\n  Funding clustering:")
        print(f"    Losers in high funding: {fc['losers_in_high_funding']}/{fc['losers_total']}")
        print(f"    Winners in high funding: {fc['winners_in_high_funding']}/{fc['winners_total']}")
        print(f"    Mean funding rank: L={fc['losers_mean_funding']:.4f} vs W={fc['winners_mean_funding']:.4f}")

    vc = clustering["vdo"]
    print(f"\n  VDO clustering:")
    print(f"    Losers low VDO: {vc['losers_low_vdo']}/{bc['losers_n']}, "
          f"high VDO: {vc['losers_high_vdo']}/{bc['losers_n']}")
    print(f"    Winners low VDO: {vc['winners_low_vdo']}/{bc['winners_n']}, "
          f"high VDO: {vc['winners_high_vdo']}/{bc['winners_n']}")

    ec = clustering["exit_reason"]
    print(f"\n  Exit reason:")
    print(f"    Post-stop: {ec['post_stop_n']} re-entries, WR={ec['post_stop_wr']}%")
    print(f"    Post-trend: {ec['post_trend_n']} re-entries, WR={ec['post_trend_wr']}%")

    # ── State divergence ──────────────────────────────────────────────
    print("\nStep 4: State divergence (X0 vs anchor)...")
    sd = state_divergence(ef, ef_anchor)
    print(f"  X0 total PnL: ${sd['x0_total_pnl']}")
    print(f"  Anchor total PnL: ${sd['anchor_total_pnl']}")
    print(f"  X0 advantage: ${sd['total_advantage']}")
    print(f"\n  Attribution:")
    print(f"    From X0-only trades (new entries): ${sd['advantage_from_x0_only_trades']} "
          f"({sd['x0_only_entries']} trades, {sd['x0_only_reentry_count']} re-entries)")
    print(f"    From avoiding anchor-only trades: ${sd['advantage_from_avoided_anchor_only']} "
          f"({sd['anchor_only_entries']} trades)")
    print(f"    From different exits on shared trades: ${sd['advantage_from_shared_exit_diff']} "
          f"({sd['shared_diff_exit']}/{sd['shared_entries']} had different exits)")

    # ── Paper rule analysis ───────────────────────────────────────────
    print("\nStep 5: Paper rule analysis (3 narrow candidates)...")
    pra = paper_rule_analysis(ef)
    for _, row in pra.iterrows():
        print(f"\n  {row['rule']}:")
        print(f"    {row['description']}")
        print(f"    Blocked: {row['n_blocked']}, Remaining: {row['n_remaining']}")
        print(f"    Blocked losers: {row['blocked_losers']}, Blocked winners: {row['blocked_winners']}")
        print(f"    Net PnL effect: ${row['net_effect']:.0f} "
              f"({'HELPS' if row['net_effect'] > 0 else 'HURTS'})")
        print(f"    Blocked mean return: {row['blocked_mean_ret']:.3f}%")

    # ── Worst re-entry analysis ───────────────────────────────────────
    print("\nStep 6: Worst re-entry trade analysis...")
    wra = worst_reentry_analysis(ef)
    print(f"  Total re-entry PnL: ${wra['total_re_pnl']}")
    print(f"  Worst 10 re-entries PnL: ${wra['worst10_pnl']}")
    print(f"  Worst 10 mean breadth: {wra['worst10_mean_breadth']}")
    print(f"  Worst 10 mean bse: {wra['worst10_mean_bse']}")
    print(f"  Worst 10 years: {wra['worst10_years']}")
    print(f"  Best 10 re-entries PnL: ${wra['best10_pnl']}")
    print(f"  Best 10 mean breadth: {wra['best10_mean_breadth']}")

    # ── Save artifacts ────────────────────────────────────────────────
    print("\nStep 7: Saving artifacts...")
    rdt.to_csv(ARTIFACTS / "reentry_definition_table.csv", index=False)
    pra.to_csv(ARTIFACTS / "reentry_paper_rules.csv", index=False)

    with open(ARTIFACTS / "reentry_clustering.json", "w") as f:
        json.dump(clustering, f, indent=2, default=str)
    with open(ARTIFACTS / "reentry_state_divergence.json", "w") as f:
        json.dump(sd, f, indent=2)
    with open(ARTIFACTS / "reentry_worst_analysis.json", "w") as f:
        json.dump(wra, f, indent=2, default=str)

    print("  Saved: reentry_definition_table.csv")
    print("  Saved: reentry_paper_rules.csv")
    print("  Saved: reentry_clustering.json")
    print("  Saved: reentry_state_divergence.json")
    print("  Saved: reentry_worst_analysis.json")

    print("\n" + "=" * 70)
    print("D1.5 DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
