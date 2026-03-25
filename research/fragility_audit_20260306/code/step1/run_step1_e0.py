#!/usr/bin/env python3
"""
Step 1 — E0 Home-Run Dependence & Behavioral Fragility Audit
=============================================================
Implements: giveback ratio, sensitivity curve (Native + Unit-Size),
cliff-edge detection, skip-after-N-losses.

All outputs written to research/fragility_audit_20260306/artifacts/step1/
"""
from __future__ import annotations
import bisect
import json
import math
import os
import sys
from datetime import datetime, UTC
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # btc-spot-dev
NS = ROOT / "research" / "fragility_audit_20260306"
OUT = NS / "artifacts" / "step1"
OUT.mkdir(parents=True, exist_ok=True)

# Step 0 canonical sources
E0_TRADE_CSV = ROOT / "results" / "parity_20260305" / "eval_e0_vs_e0" / "results" / "trades_candidate.csv"
E0_PROFILE_DIR = ROOT / "results" / "trade_profile_8x5" / "E0"
E0_PROFILE_JSON = E0_PROFILE_DIR / "profile.json"
E0_MFE_MAE_CSV = E0_PROFILE_DIR / "mfe_mae_per_trade.csv"
E0_BACKTEST_JSON = ROOT / "results" / "parity_20260305" / "eval_e0_vs_e0" / "results" / "full_backtest_detail.json"
BAR_CSV = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"

# Constants matching trade_profile_8x5.py exactly
BACKTEST_YEARS = 6.5
NAV0 = 10000.0

# ── helper functions (matching trade_profile_8x5 conventions) ───────────

def _trade_sharpe(returns: pd.Series, trades_per_year: float) -> float:
    if len(returns) < 2 or returns.std(ddof=0) < 1e-12:
        return 0.0
    return float(returns.mean() / returns.std(ddof=0) * np.sqrt(trades_per_year))

def _safe_cagr(total_pnl: float, nav0: float, years: float) -> float:
    final = nav0 + total_pnl
    if final <= 0:
        return -1.0
    return float((final / nav0) ** (1.0 / years) - 1.0)

def _safe_cagr_from_returns(returns: pd.Series, years: float) -> float:
    """CAGR from compounded per-trade returns (unit-size view)."""
    wealth = (1 + returns / 100.0).prod()
    if wealth <= 0:
        return -1.0
    return float(wealth ** (1.0 / years) - 1.0)

def load_h4_bars():
    df = pd.read_csv(BAR_CSV)
    h4 = df[df["interval"] == "4h"].copy()
    h4.sort_values("open_time", inplace=True)
    return (
        h4["open_time"].values.astype(np.int64),
        h4["high"].values.astype(np.float64),
        h4["low"].values.astype(np.float64),
    )

def compute_mfe_mae(entry_ts_ms, exit_ts_ms, entry_price, h4_times, h4_highs, h4_lows):
    i_start = bisect.bisect_left(h4_times, entry_ts_ms)
    i_end = bisect.bisect_right(h4_times, exit_ts_ms)
    if i_start >= i_end or entry_price < 1e-12:
        return 0.0, 0.0
    max_high = h4_highs[i_start:i_end].max()
    min_low = h4_lows[i_start:i_end].min()
    mfe = max(0.0, (max_high - entry_price) / entry_price * 100.0)
    mae = max(0.0, (entry_price - min_low) / entry_price * 100.0)
    return float(mfe), float(mae)


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 1: Load inputs, RECON_ASSERT, anchor checks
# ═══════════════════════════════════════════════════════════════════════════

def phase1_recon():
    print("Phase 1: RECON_ASSERT and anchor checks")

    # Load E0 trades
    trades = pd.read_csv(E0_TRADE_CSV)
    n_trades = len(trades)
    period_first = trades["entry_ts"].iloc[0][:10]
    period_last = trades["exit_ts"].iloc[-1][:10]

    # Load profile
    with open(E0_PROFILE_JSON) as f:
        profile = json.load(f)

    # Load MFE/MAE
    mfe_mae = pd.read_csv(E0_MFE_MAE_CSV)

    # Input manifest
    manifest = {
        "step0_artifacts_read": [
            "artifacts/step0/step0_summary.json",
            "artifacts/step0/missing_diagnostics_spec.md",
            "artifacts/step0/reconciliation_audit.csv",
            "artifacts/step0/candidate_repo_mapping.csv",
            "artifacts/step0/track_split_plan.md",
            "artifacts/step0/trade_metric_coverage_matrix.csv",
        ],
        "canonical_e0_trade_csv": str(E0_TRADE_CSV.relative_to(ROOT)),
        "canonical_e0_profile_dir": str(E0_PROFILE_DIR.relative_to(ROOT)),
        "canonical_e0_backtest_detail_json": str(E0_BACKTEST_JSON.relative_to(ROOT)),
        "canonical_period_start": "2019-01-01",
        "canonical_period_end": "2026-02-20",
        "canonical_fee_bps_round_trip": 50,
        "initial_cash": 10000.0,
        "expected_trade_count": 192,
    }
    with open(OUT / "e0_input_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    # RECON_ASSERT
    recon = {
        "trade_count_asserted": 192,
        "trade_count_observed": n_trades,
        "period_asserted": "2019-01-01 to 2026-02-20",
        "period_observed": f"{period_first} to {period_last}",
        "fee_asserted": "50 bps RT (from run_meta.json harsh_cost_bps=50)",
        "fee_observed": "50 bps RT (confirmed via Step 0 reconciliation)",
        "recon_status": "PASS" if n_trades == 192 else "FAIL",
        "notes": f"Trade count {'matches' if n_trades == 192 else 'MISMATCH'}. Period within canonical range.",
    }
    with open(OUT / "e0_recon_assertion.json", "w") as f:
        json.dump(recon, f, indent=2)
    assert n_trades == 192, f"RECON_FAIL: expected 192 trades, got {n_trades}"

    # T7 anchor check — reproduce base metrics and verify
    tpy = n_trades / BACKTEST_YEARS
    base_pnl = trades["pnl_usd"].sum()
    base_sharpe = _trade_sharpe(trades["return_pct"], tpy)
    base_cagr = _safe_cagr(base_pnl, NAV0, BACKTEST_YEARS)

    t7_anchors = {}
    tol_sharpe = 1e-6
    tol_cagr = 1e-6
    tol_pnl = 0.01

    checks = [
        ("base_sharpe", base_sharpe, profile["t7_base_sharpe"]),
        ("base_cagr_pct", base_cagr * 100, profile["t7_base_cagr_pct"]),
        ("base_total_pnl", base_pnl, profile["t7_base_total_pnl"]),
    ]
    # Also check drop-top-N
    sorted_idx = trades["pnl_usd"].sort_values(ascending=False).index
    for k in [1, 3, 5, 10]:
        drop_idx = sorted_idx[:k]
        remaining = trades.drop(drop_idx)
        r = remaining["return_pct"]
        pnl = remaining["pnl_usd"].sum()
        tpy_r = len(remaining) / BACKTEST_YEARS
        s = _trade_sharpe(r, tpy_r)
        c = _safe_cagr(pnl, NAV0, BACKTEST_YEARS)
        checks.append((f"drop_top{k}_sharpe", s, profile[f"t7_drop_top{k}_sharpe"]))
        checks.append((f"drop_top{k}_cagr_pct", c * 100, profile[f"t7_drop_top{k}_cagr_pct"]))
        checks.append((f"drop_top{k}_pnl", pnl, profile[f"t7_drop_top{k}_pnl"]))

    all_pass = True
    anchor_details = []
    for name, computed, expected in checks:
        if "pnl" in name:
            ok = abs(computed - expected) < tol_pnl
        elif "sharpe" in name:
            ok = abs(computed - expected) < tol_sharpe
        else:
            ok = abs(computed - expected) < tol_cagr
        anchor_details.append({
            "metric": name,
            "computed": float(round(computed, 8)),
            "expected": float(round(expected, 8)),
            "match": bool(ok),
        })
        if not ok:
            all_pass = False
            print(f"  ANCHOR MISMATCH: {name}: computed={computed}, expected={expected}")

    # Giveback join check
    join_expected = n_trades
    join_matched = len(mfe_mae)
    giveback_join_ok = (join_matched == join_expected)

    anchor_json = {
        "t7_anchor_check_status": "PASS" if all_pass else "FAIL",
        "t7_anchor_points_tested": len(checks),
        "t7_anchor_tolerance": {"sharpe": tol_sharpe, "cagr": tol_cagr, "pnl": tol_pnl},
        "t7_anchor_details": anchor_details,
        "t7_anchor_notes": "All T7 points reproduced exactly" if all_pass else "MISMATCH detected",
        "giveback_join_check_status": "PASS" if giveback_join_ok else "FAIL",
        "giveback_join_rows_expected": join_expected,
        "giveback_join_rows_matched": join_matched,
        "giveback_join_notes": f"MFE/MAE CSV has {join_matched} rows (expected {join_expected})",
    }
    with open(OUT / "e0_anchor_checks.json", "w") as f:
        json.dump(anchor_json, f, indent=2)

    assert all_pass, "T7 anchor check FAIL"
    print(f"  RECON_ASSERT: PASS (192 trades)")
    print(f"  T7 anchor check: PASS ({len(checks)} points)")
    print(f"  Giveback join: {'PASS' if giveback_join_ok else 'FAIL'}")

    return trades, profile, mfe_mae


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2: Build ledgers and giveback
# ═══════════════════════════════════════════════════════════════════════════

def phase2_ledgers_and_giveback(trades: pd.DataFrame, mfe_mae: pd.DataFrame):
    print("Phase 2: Build ledgers and giveback")

    h4_times, h4_highs, h4_lows = load_h4_bars()

    # Compute giveback per trade
    giveback_data = []
    for i, row in trades.iterrows():
        entry_ts_ms = int(row["entry_ts_ms"])
        exit_ts_ms = int(row["exit_ts_ms"])
        entry_price = float(row["entry_price"])
        realized_return_pct = float(row["return_pct"])

        mfe_pct, mae_pct = compute_mfe_mae(entry_ts_ms, exit_ts_ms, entry_price,
                                             h4_times, h4_highs, h4_lows)

        if mfe_pct > 0:
            giveback_pct = mfe_pct - realized_return_pct
            giveback_ratio = giveback_pct / mfe_pct
        else:
            giveback_ratio = np.nan

        giveback_data.append({
            "trade_id": int(row["trade_id"]),
            "mfe_pct": mfe_pct,
            "mae_pct": mae_pct,
            "giveback_ratio": giveback_ratio,
        })

    gb_df = pd.DataFrame(giveback_data)

    # Verify MFE/MAE matches existing trade_profile output
    existing_mfe = mfe_mae.set_index("trade_id")
    for _, grow in gb_df.iterrows():
        tid = grow["trade_id"]
        if tid in existing_mfe.index:
            exp_mfe = existing_mfe.loc[tid, "mfe_pct"]
            assert abs(grow["mfe_pct"] - exp_mfe) < 0.01, \
                f"MFE mismatch trade {tid}: {grow['mfe_pct']} vs {exp_mfe}"

    # Build episode ledger base
    ledger = trades.copy()
    ledger["episode_id"] = range(1, len(ledger) + 1)
    ledger["hold_bars"] = ((ledger["exit_ts_ms"] - ledger["entry_ts_ms"]) / (4 * 3600 * 1000)).round(0).astype(int)
    ledger["hold_days"] = ledger["days_held"]
    ledger["realized_return_pct"] = ledger["return_pct"]
    ledger["win_flag"] = (ledger["return_pct"] > 0).astype(int)
    ledger["entry_time"] = ledger["entry_ts"]
    ledger["exit_time"] = ledger["exit_ts"]

    # Join giveback and MFE/MAE
    gb_indexed = gb_df.set_index("trade_id")
    ledger = ledger.set_index("trade_id")
    ledger["mfe_pct"] = gb_indexed["mfe_pct"]
    ledger["mae_pct"] = gb_indexed["mae_pct"]
    ledger["giveback_ratio"] = gb_indexed["giveback_ratio"]
    ledger = ledger.reset_index()

    # ── Contribution ranks ──
    # Native positive contribution rank: by pnl_usd descending
    ledger["native_positive_contribution_rank_desc"] = ledger["pnl_usd"].rank(ascending=False, method="first").astype(int)
    # Unit-size positive contribution rank: by return_pct descending
    ledger["unit_size_positive_contribution_rank_desc"] = ledger["return_pct"].rank(ascending=False, method="first").astype(int)

    # ── Write Native Episode Ledger ──
    native_cols = [
        "episode_id", "entry_time", "exit_time", "hold_bars", "hold_days",
        "exit_reason", "realized_return_pct", "pnl_usd", "mfe_pct", "mae_pct",
        "giveback_ratio", "win_flag", "native_positive_contribution_rank_desc",
    ]
    ledger[native_cols].to_csv(OUT / "e0_native_episode_ledger.csv", index=False)

    # ── Write Unit-Size Episode Ledger ──
    unit_cols = [
        "episode_id", "entry_time", "exit_time", "hold_bars", "hold_days",
        "exit_reason", "realized_return_pct", "mfe_pct", "mae_pct",
        "giveback_ratio", "win_flag", "unit_size_positive_contribution_rank_desc",
    ]
    ledger[unit_cols].to_csv(OUT / "e0_unit_size_episode_ledger.csv", index=False)

    # ── Write giveback per trade ──
    gb_out = ledger[["episode_id", "entry_time", "exit_time", "exit_reason",
                      "hold_bars", "realized_return_pct", "mfe_pct",
                      "giveback_ratio", "win_flag"]].copy()
    gb_out.to_csv(OUT / "e0_giveback_per_trade.csv", index=False)

    # ── Giveback summary ──
    valid_gb = ledger["giveback_ratio"].dropna()
    na_count = ledger["giveback_ratio"].isna().sum()
    summary = {
        "mean_giveback": round(float(valid_gb.mean()), 6),
        "median_giveback": round(float(valid_gb.median()), 6),
        "p25": round(float(valid_gb.quantile(0.25)), 6),
        "p75": round(float(valid_gb.quantile(0.75)), 6),
        "p90": round(float(valid_gb.quantile(0.90)), 6),
        "p95": round(float(valid_gb.quantile(0.95)), 6),
        "frac_gt_025": round(float((valid_gb > 0.25).mean()), 6),
        "frac_gt_050": round(float((valid_gb > 0.50).mean()), 6),
        "frac_gt_075": round(float((valid_gb > 0.75).mean()), 6),
        "valid_trade_count": int(len(valid_gb)),
        "na_trade_count": int(na_count),
    }
    with open(OUT / "e0_giveback_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # ── Giveback by exit reason ──
    gb_by_exit = []
    for reason, grp in ledger.groupby("exit_reason"):
        valid = grp["giveback_ratio"].dropna()
        gb_by_exit.append({
            "exit_reason": reason,
            "trade_count": len(grp),
            "mean_giveback": round(float(valid.mean()), 6) if len(valid) > 0 else np.nan,
            "median_giveback": round(float(valid.median()), 6) if len(valid) > 0 else np.nan,
            "mean_realized_return_pct": round(float(grp["realized_return_pct"].mean()), 6),
            "mean_mfe_pct": round(float(grp["mfe_pct"].mean()), 6),
        })
    pd.DataFrame(gb_by_exit).to_csv(OUT / "e0_giveback_by_exit_reason.csv", index=False)

    # ── Giveback by hold bucket ──
    # Buckets: <1d, 1-3d, 3-7d, 7-14d, 14+d
    def hold_bucket(days):
        if days < 1: return "<1d"
        elif days < 3: return "1-3d"
        elif days < 7: return "3-7d"
        elif days < 14: return "7-14d"
        else: return "14d+"
    ledger["hold_bucket"] = ledger["hold_days"].apply(hold_bucket)
    bucket_order = ["<1d", "1-3d", "3-7d", "7-14d", "14d+"]
    gb_by_hold = []
    for bucket in bucket_order:
        grp = ledger[ledger["hold_bucket"] == bucket]
        if len(grp) == 0:
            continue
        valid = grp["giveback_ratio"].dropna()
        gb_by_hold.append({
            "hold_bucket": bucket,
            "trade_count": len(grp),
            "mean_giveback": round(float(valid.mean()), 6) if len(valid) > 0 else np.nan,
            "median_giveback": round(float(valid.median()), 6) if len(valid) > 0 else np.nan,
            "mean_realized_return_pct": round(float(grp["realized_return_pct"].mean()), 6),
            "mean_mfe_pct": round(float(grp["mfe_pct"].mean()), 6),
        })
    pd.DataFrame(gb_by_hold).to_csv(OUT / "e0_giveback_by_hold_bucket.csv", index=False)

    # ── Worst 10 giveback ──
    worst10 = ledger.dropna(subset=["giveback_ratio"]).nlargest(10, "giveback_ratio")
    w10_out = []
    for rank_i, (_, row) in enumerate(worst10.iterrows(), 1):
        w10_out.append({
            "rank": rank_i,
            "episode_id": int(row["episode_id"]),
            "entry_time": row["entry_time"],
            "exit_time": row["exit_time"],
            "exit_reason": row["exit_reason"],
            "hold_bars": int(row["hold_bars"]),
            "realized_return_pct": round(float(row["realized_return_pct"]), 6),
            "mfe_pct": round(float(row["mfe_pct"]), 6),
            "giveback_ratio": round(float(row["giveback_ratio"]), 6),
        })
    pd.DataFrame(w10_out).to_csv(OUT / "e0_giveback_worst10.csv", index=False)

    # ── Giveback distribution plot ──
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax1, ax2 = axes
    valid_gb_arr = valid_gb.values
    ax1.hist(valid_gb_arr, bins=40, edgecolor="black", alpha=0.7, color="#4C72B0")
    ax1.axvline(valid_gb_arr.mean(), color="red", ls="--", label=f"mean={valid_gb_arr.mean():.3f}")
    ax1.axvline(np.median(valid_gb_arr), color="orange", ls="--", label=f"median={np.median(valid_gb_arr):.3f}")
    ax1.set_xlabel("Giveback Ratio")
    ax1.set_ylabel("Count")
    ax1.set_title("E0 Giveback Ratio Distribution (all valid)")
    ax1.legend()

    # By win/loss
    wins_gb = ledger[ledger["win_flag"] == 1]["giveback_ratio"].dropna()
    losses_gb = ledger[ledger["win_flag"] == 0]["giveback_ratio"].dropna()
    ax2.hist(wins_gb.values, bins=30, alpha=0.6, label=f"Wins (n={len(wins_gb)})", color="green", edgecolor="black")
    ax2.hist(losses_gb.values, bins=30, alpha=0.6, label=f"Losses (n={len(losses_gb)})", color="red", edgecolor="black")
    ax2.set_xlabel("Giveback Ratio")
    ax2.set_ylabel("Count")
    ax2.set_title("Giveback by Win/Loss")
    ax2.legend()
    plt.tight_layout()
    plt.savefig(OUT / "e0_giveback_distribution.png", dpi=150)
    plt.close()

    print(f"  Giveback: {summary['valid_trade_count']} valid, mean={summary['mean_giveback']:.3f}, median={summary['median_giveback']:.3f}")
    return ledger


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 3: Sensitivity curves (Native + Unit-Size)
# ═══════════════════════════════════════════════════════════════════════════

def phase3_sensitivity_curves(ledger: pd.DataFrame, profile: dict):
    print("Phase 3: Sensitivity curves")
    n_trades = len(ledger)
    max_remove = int(np.floor(0.20 * n_trades))  # up to 20%

    # ── Native view: rank by pnl_usd descending ──
    native_sorted = ledger.sort_values("pnl_usd", ascending=False).reset_index(drop=True)
    native_rows = []
    base_pnl = ledger["pnl_usd"].sum()
    base_tpy = n_trades / BACKTEST_YEARS
    base_sharpe = _trade_sharpe(ledger["return_pct"], base_tpy)
    base_cagr = _safe_cagr(base_pnl, NAV0, BACKTEST_YEARS)
    base_terminal = NAV0 + base_pnl

    cumulative_removed_pnl = 0.0
    for k in range(0, max_remove + 1):
        if k == 0:
            remaining = ledger
        else:
            drop_ids = native_sorted.iloc[:k]["episode_id"].values
            remaining = ledger[~ledger["episode_id"].isin(drop_ids)]
        rem_pnl = remaining["pnl_usd"].sum()
        rem_terminal = NAV0 + rem_pnl
        tpy_r = len(remaining) / BACKTEST_YEARS
        rem_sharpe = _trade_sharpe(remaining["return_pct"], tpy_r)
        rem_cagr = _safe_cagr(rem_pnl, NAV0, BACKTEST_YEARS)

        removed_trade_pnl = float(native_sorted.iloc[k - 1]["pnl_usd"]) if k > 0 else 0.0
        removed_trade_return = float(native_sorted.iloc[k - 1]["return_pct"]) if k > 0 else 0.0
        removed_ep_id = int(native_sorted.iloc[k - 1]["episode_id"]) if k > 0 else 0
        removed_entry = native_sorted.iloc[k - 1]["entry_time"] if k > 0 else ""
        removed_exit = native_sorted.iloc[k - 1]["exit_time"] if k > 0 else ""
        removed_rank = int(native_sorted.iloc[k - 1]["native_positive_contribution_rank_desc"]) if k > 0 else 0
        cumulative_removed_pnl += removed_trade_pnl

        prev_terminal = native_rows[-1]["remaining_terminal_value"] if k > 0 else base_terminal
        prev_cagr = native_rows[-1]["remaining_cagr"] if k > 0 else base_cagr * 100
        prev_sharpe = native_rows[-1]["remaining_sharpe"] if k > 0 else base_sharpe

        native_rows.append({
            "removal_index": k,
            "removal_pct": round(100.0 * k / n_trades, 2),
            "removed_episode_id": removed_ep_id,
            "removed_entry_time": removed_entry,
            "removed_exit_time": removed_exit,
            "removed_trade_pnl_usd": round(removed_trade_pnl, 2),
            "removed_trade_return_pct": round(removed_trade_return, 6),
            "removed_native_positive_contribution_rank": removed_rank,
            "cumulative_removed_pnl_usd": round(cumulative_removed_pnl, 2),
            "cumulative_removed_share_of_total_net_pnl": round(100.0 * cumulative_removed_pnl / base_pnl, 4) if base_pnl != 0 else 0,
            "remaining_terminal_value": round(rem_terminal, 2),
            "remaining_cagr": round(rem_cagr * 100, 6),
            "remaining_sharpe": round(rem_sharpe, 6),
            "remaining_net_pnl": round(rem_pnl, 2),
            "marginal_terminal_damage": round(prev_terminal - rem_terminal, 2) if k > 0 else 0,
            "marginal_cagr_damage": round(prev_cagr - rem_cagr * 100, 6) if k > 0 else 0,
            "marginal_sharpe_damage": round(prev_sharpe - rem_sharpe, 6) if k > 0 else 0,
        })
    native_df = pd.DataFrame(native_rows)
    native_df.to_csv(OUT / "e0_native_sensitivity_curve.csv", index=False)

    # ── Unit-Size view: rank by return_pct descending ──
    unit_sorted = ledger.sort_values("return_pct", ascending=False).reset_index(drop=True)
    unit_rows = []
    base_returns = ledger["return_pct"]
    base_unit_sharpe = base_sharpe  # same computation
    base_unit_cagr = _safe_cagr_from_returns(base_returns, BACKTEST_YEARS)
    base_unit_terminal = NAV0 * (1 + base_returns / 100.0).prod()

    cumulative_removed_return = 0.0
    total_positive_return = ledger[ledger["return_pct"] > 0]["return_pct"].sum()

    for k in range(0, max_remove + 1):
        if k == 0:
            remaining = ledger
        else:
            drop_ids = unit_sorted.iloc[:k]["episode_id"].values
            remaining = ledger[~ledger["episode_id"].isin(drop_ids)]

        rem_returns = remaining.sort_values("entry_ts_ms")["return_pct"]
        tpy_r = len(remaining) / BACKTEST_YEARS
        rem_sharpe = _trade_sharpe(rem_returns, tpy_r)
        rem_cagr = _safe_cagr_from_returns(rem_returns, BACKTEST_YEARS)
        rem_terminal = NAV0 * (1 + rem_returns / 100.0).prod()

        removed_trade_return = float(unit_sorted.iloc[k - 1]["return_pct"]) if k > 0 else 0.0
        removed_ep_id = int(unit_sorted.iloc[k - 1]["episode_id"]) if k > 0 else 0
        removed_entry = unit_sorted.iloc[k - 1]["entry_time"] if k > 0 else ""
        removed_exit = unit_sorted.iloc[k - 1]["exit_time"] if k > 0 else ""
        removed_rank = int(unit_sorted.iloc[k - 1]["unit_size_positive_contribution_rank_desc"]) if k > 0 else 0
        cumulative_removed_return += removed_trade_return

        prev_terminal = unit_rows[-1]["remaining_terminal_value"] if k > 0 else base_unit_terminal
        prev_cagr = unit_rows[-1]["remaining_cagr"] if k > 0 else base_unit_cagr * 100
        prev_sharpe = unit_rows[-1]["remaining_sharpe"] if k > 0 else rem_sharpe

        unit_rows.append({
            "removal_index": k,
            "removal_pct": round(100.0 * k / n_trades, 2),
            "removed_episode_id": removed_ep_id,
            "removed_entry_time": removed_entry,
            "removed_exit_time": removed_exit,
            "removed_trade_return_pct": round(removed_trade_return, 6),
            "removed_unit_size_positive_contribution_rank": removed_rank,
            "cumulative_removed_return_contribution": round(cumulative_removed_return, 6),
            "cumulative_removed_share_of_total_positive_return_contribution": round(100.0 * cumulative_removed_return / total_positive_return, 4) if total_positive_return > 0 else 0,
            "remaining_terminal_value": round(rem_terminal, 2),
            "remaining_cagr": round(rem_cagr * 100, 6),
            "remaining_sharpe": round(rem_sharpe, 6),
            "remaining_net_return_equivalent": round(float((1 + rem_returns / 100.0).prod() - 1) * 100, 6),
            "marginal_terminal_damage": round(prev_terminal - rem_terminal, 2) if k > 0 else 0,
            "marginal_cagr_damage": round(prev_cagr - rem_cagr * 100, 6) if k > 0 else 0,
            "marginal_sharpe_damage": round(prev_sharpe - rem_sharpe, 6) if k > 0 else 0,
        })
    unit_df = pd.DataFrame(unit_rows)
    unit_df.to_csv(OUT / "e0_unit_size_sensitivity_curve.csv", index=False)

    # ── Anchor check against T7 for native view ──
    # T7 uses pnl_usd ranking (same as native view), additive PnL convention
    for k_check in [1, 3, 5, 10]:
        row = native_df[native_df["removal_index"] == k_check].iloc[0]
        expected_pnl = profile[f"t7_drop_top{k_check}_pnl"]
        expected_sharpe = profile[f"t7_drop_top{k_check}_sharpe"]
        assert abs(row["remaining_net_pnl"] - expected_pnl) < 0.02, \
            f"Native sensitivity curve k={k_check} PnL mismatch: {row['remaining_net_pnl']} vs {expected_pnl}"
        assert abs(row["remaining_sharpe"] - expected_sharpe) < 1e-4, \
            f"Native sensitivity curve k={k_check} Sharpe mismatch: {row['remaining_sharpe']} vs {expected_sharpe}"

    print(f"  Native sensitivity curve: {len(native_rows)} points, anchor checks PASS")
    print(f"  Unit-size sensitivity curve: {len(unit_rows)} points")

    # ── Plots ──
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for ax, metric, label in zip(axes,
        ["remaining_terminal_value", "remaining_cagr", "remaining_sharpe"],
        ["Terminal Value ($)", "CAGR (%)", "Sharpe"]):
        ax.plot(native_df["removal_index"], native_df[metric], "b-o", markersize=3, label="Native (pnl_usd ranked)")
        ax.axhline(native_df[metric].iloc[0], color="blue", ls=":", alpha=0.3)
        ax.set_xlabel("Top Trades Removed")
        ax.set_ylabel(label)
        ax.set_title(f"E0 Native: {label} vs Top-Trade Removal")
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "e0_native_sensitivity_curve.png", dpi=150)
    plt.close()

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for ax, metric, label in zip(axes,
        ["remaining_terminal_value", "remaining_cagr", "remaining_sharpe"],
        ["Terminal Value ($)", "CAGR (%)", "Sharpe"]):
        ax.plot(unit_df["removal_index"], unit_df[metric], "r-o", markersize=3, label="Unit-Size (return_pct ranked)")
        ax.axhline(unit_df[metric].iloc[0], color="red", ls=":", alpha=0.3)
        ax.set_xlabel("Top Trades Removed")
        ax.set_ylabel(label)
        ax.set_title(f"E0 Unit-Size: {label} vs Top-Trade Removal")
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "e0_unit_size_sensitivity_curve.png", dpi=150)
    plt.close()

    return native_df, unit_df


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 4: Cliff-edge detection
# ═══════════════════════════════════════════════════════════════════════════

def phase4_cliff_edge(native_curve: pd.DataFrame, unit_curve: pd.DataFrame):
    print("Phase 4: Cliff-edge detection")
    CLIFF_THRESHOLD = 3.0

    results = []
    for view_name, curve in [("native", native_curve), ("unit_size", unit_curve)]:
        max_k = curve["removal_index"].max()
        base_terminal = curve.iloc[0]["remaining_terminal_value"]
        base_cagr = curve.iloc[0]["remaining_cagr"]
        base_sharpe = curve.iloc[0]["remaining_sharpe"]

        for metric_name, base_val in [("terminal", "remaining_terminal_value"),
                                       ("cagr", "remaining_cagr"),
                                       ("sharpe", "remaining_sharpe")]:
            # Marginal damages (k=1..max_k)
            damages = []
            for k in range(1, max_k + 1):
                prev = float(curve[curve["removal_index"] == k - 1][base_val].iloc[0])
                curr = float(curve[curve["removal_index"] == k][base_val].iloc[0])
                damage = prev - curr
                damages.append((k, damage))

            abs_damages = [abs(d) for _, d in damages]
            avg_damage = np.mean(abs_damages) if abs_damages else 1.0

            cliff_scores = []
            for k, d in damages:
                score = abs(d) / avg_damage if avg_damage > 1e-12 else 0.0
                cliff_scores.append((k, score))

            max_score = max(s for _, s in cliff_scores) if cliff_scores else 0.0
            max_k_idx = [k for k, s in cliff_scores if s == max_score][0] if cliff_scores else 0
            cliff_flag = max_score > CLIFF_THRESHOLD

            # Determine first flagged index
            first_cliff = 0
            for k, s in cliff_scores:
                if s > CLIFF_THRESHOLD:
                    first_cliff = k
                    break

            results.append({
                "ledger_view": view_name,
                "metric": metric_name,
                "max_cliff_score": round(max_score, 4),
                "max_cliff_index": max_k_idx,
                "first_cliff_index": first_cliff,
                "cliff_flag": cliff_flag,
                "avg_marginal_damage": round(avg_damage, 6),
                "cliff_threshold": CLIFF_THRESHOLD,
            })

    # Build summary CSV
    cliff_rows = []
    for view_name, curve in [("native", native_curve), ("unit_size", unit_curve)]:
        base_terminal = curve.iloc[0]["remaining_terminal_value"]
        base_cagr = curve.iloc[0]["remaining_cagr"]
        base_sharpe = curve.iloc[0]["remaining_sharpe"]

        r_terminal = [r for r in results if r["ledger_view"] == view_name and r["metric"] == "terminal"][0]
        r_cagr = [r for r in results if r["ledger_view"] == view_name and r["metric"] == "cagr"][0]
        r_sharpe = [r for r in results if r["ledger_view"] == view_name and r["metric"] == "sharpe"][0]

        # Interpretation
        any_cliff = r_terminal["cliff_flag"] or r_cagr["cliff_flag"]
        if any_cliff:
            if r_terminal["first_cliff_index"] <= 1:
                interp = "single-point collapse"
            elif r_terminal["first_cliff_index"] <= 3:
                interp = "multi-step cliff"
            else:
                interp = "late cliff"
        else:
            max_all = max(r_terminal["max_cliff_score"], r_cagr["max_cliff_score"])
            if max_all > 2.0:
                interp = "near-cliff (smooth but concentrated)"
            else:
                interp = "smooth decay"

        cliff_rows.append({
            "ledger_view": view_name,
            "tested_window_max_removal_pct": round(100.0 * curve["removal_index"].max() / 192, 2),
            "base_terminal_value": round(base_terminal, 2),
            "base_cagr": round(base_cagr, 6),
            "base_sharpe": round(base_sharpe, 6),
            "max_cliff_score_terminal": r_terminal["max_cliff_score"],
            "max_cliff_score_cagr": r_cagr["max_cliff_score"],
            "max_cliff_score_sharpe": r_sharpe["max_cliff_score"],
            "first_terminal_cliff_index": r_terminal["first_cliff_index"],
            "first_cagr_cliff_index": r_cagr["first_cliff_index"],
            "first_sharpe_cliff_index": r_sharpe["first_cliff_index"],
            "cliff_flag_terminal": r_terminal["cliff_flag"],
            "cliff_flag_cagr": r_cagr["cliff_flag"],
            "cliff_flag_sharpe": r_sharpe["cliff_flag"],
            "interpretation": interp,
        })

    pd.DataFrame(cliff_rows).to_csv(OUT / "e0_cliff_edge_summary.csv", index=False)
    for row in cliff_rows:
        print(f"  {row['ledger_view']}: terminal cliff={row['cliff_flag_terminal']} "
              f"(score={row['max_cliff_score_terminal']:.2f}), "
              f"cagr cliff={row['cliff_flag_cagr']} (score={row['max_cliff_score_cagr']:.2f}), "
              f"interp={row['interpretation']}")

    return cliff_rows


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 5: Skip-after-N-losses
# ═══════════════════════════════════════════════════════════════════════════

def phase5_skip_after_n(ledger: pd.DataFrame):
    print("Phase 5: Skip-after-N-losses")
    n_trades = len(ledger)
    chron = ledger.sort_values("entry_ts_ms").reset_index(drop=True)

    # Compute top-N thresholds for the home-run lens
    native_top = chron.sort_values("pnl_usd", ascending=False)
    unit_top = chron.sort_values("return_pct", ascending=False)
    native_top1_ids = set(native_top.iloc[:1]["episode_id"])
    native_top3_ids = set(native_top.iloc[:3]["episode_id"])
    native_top5_ids = set(native_top.iloc[:5]["episode_id"])
    native_top10_ids = set(native_top.iloc[:10]["episode_id"])
    unit_top1_ids = set(unit_top.iloc[:1]["episode_id"])
    unit_top3_ids = set(unit_top.iloc[:3]["episode_id"])
    unit_top5_ids = set(unit_top.iloc[:5]["episode_id"])
    unit_top10_ids = set(unit_top.iloc[:10]["episode_id"])

    N_GRID = [2, 3, 4, 5]
    event_log = []
    summary_rows = []

    for N in N_GRID:
        consec_losses = 0
        skip_next = False
        kept_mask = []
        skipped_episodes = []

        for i, row in chron.iterrows():
            ep_id = int(row["episode_id"])
            is_win = row["return_pct"] > 0

            if skip_next:
                # This trade is skipped
                kept_mask.append(False)
                skipped_episodes.append(ep_id)
                # Record event
                # Find the trigger trade (the one that completed the streak)
                trigger_idx = i - 1
                while trigger_idx >= 0 and not kept_mask[trigger_idx]:
                    trigger_idx -= 1
                trigger_ep = int(chron.iloc[trigger_idx]["episode_id"]) if trigger_idx >= 0 else 0
                trigger_exit = chron.iloc[trigger_idx]["exit_time"] if trigger_idx >= 0 else ""

                event_log.append({
                    "n_threshold": N,
                    "trigger_trade_episode_id": trigger_ep,
                    "trigger_trade_exit_time": trigger_exit,
                    "skipped_trade_episode_id": ep_id,
                    "skipped_trade_entry_time": row["entry_time"],
                    "skipped_trade_exit_time": row["exit_time"],
                    "skipped_trade_was_win": int(is_win),
                    "skipped_trade_return_pct": round(float(row["return_pct"]), 6),
                    "skipped_trade_pnl_usd": round(float(row["pnl_usd"]), 6),
                    "skipped_trade_native_positive_contribution_rank": int(row["native_positive_contribution_rank_desc"]),
                    "skipped_trade_unit_size_positive_contribution_rank": int(row["unit_size_positive_contribution_rank_desc"]),
                    "native_top1_flag": int(ep_id in native_top1_ids),
                    "native_top3_flag": int(ep_id in native_top3_ids),
                    "native_top5_flag": int(ep_id in native_top5_ids),
                    "native_top10_flag": int(ep_id in native_top10_ids),
                    "unit_size_top1_flag": int(ep_id in unit_top1_ids),
                    "unit_size_top3_flag": int(ep_id in unit_top3_ids),
                    "unit_size_top5_flag": int(ep_id in unit_top5_ids),
                    "unit_size_top10_flag": int(ep_id in unit_top10_ids),
                })
                skip_next = False
                consec_losses = 0  # reset after skip
            else:
                kept_mask.append(True)
                if is_win:
                    consec_losses = 0
                else:
                    consec_losses += 1
                    if consec_losses >= N:
                        skip_next = True

        remaining = chron[kept_mask].copy()
        skipped_set = set(skipped_episodes)

        # Metrics for both views
        for view in ["native", "unit_size"]:
            rem_returns = remaining.sort_values("entry_ts_ms")["return_pct"]
            tpy_r = len(remaining) / BACKTEST_YEARS

            if view == "native":
                rem_pnl = remaining["pnl_usd"].sum()
                rem_terminal = NAV0 + rem_pnl
                rem_cagr = _safe_cagr(rem_pnl, NAV0, BACKTEST_YEARS)
                base_terminal = NAV0 + chron["pnl_usd"].sum()
                base_cagr_val = _safe_cagr(chron["pnl_usd"].sum(), NAV0, BACKTEST_YEARS)
            else:
                rem_terminal = NAV0 * (1 + rem_returns / 100.0).prod()
                rem_cagr = _safe_cagr_from_returns(rem_returns, BACKTEST_YEARS)
                base_terminal = NAV0 * (1 + chron["return_pct"] / 100.0).prod()
                base_cagr_val = _safe_cagr_from_returns(chron["return_pct"], BACKTEST_YEARS)

            base_tpy = n_trades / BACKTEST_YEARS
            base_sharpe_val = _trade_sharpe(chron["return_pct"], base_tpy)
            rem_sharpe = _trade_sharpe(rem_returns, tpy_r)

            # Count skipped categories
            skip_events_for_n = [e for e in event_log if e["n_threshold"] == N]
            n_skip = len(skip_events_for_n)
            n_skip_win = sum(1 for e in skip_events_for_n if e["skipped_trade_was_win"])
            n_skip_loss = n_skip - n_skip_win

            top_key = "native" if view == "native" else "unit_size"
            n_top1 = sum(1 for e in skip_events_for_n if e[f"{top_key}_top1_flag"])
            n_top3 = sum(1 for e in skip_events_for_n if e[f"{top_key}_top3_flag"])
            n_top5 = sum(1 for e in skip_events_for_n if e[f"{top_key}_top5_flag"])
            n_top10 = sum(1 for e in skip_events_for_n if e[f"{top_key}_top10_flag"])

            summary_rows.append({
                "ledger_view": view,
                "n_threshold": N,
                "skip_event_count": n_skip,
                "skipped_trade_count": n_skip,
                "skipped_winner_count": n_skip_win,
                "skipped_loser_count": n_skip_loss,
                "skipped_top1_count": n_top1,
                "skipped_top3_count": n_top3,
                "skipped_top5_count": n_top5,
                "skipped_top10_count": n_top10,
                "terminal_value": round(rem_terminal, 2),
                "cagr": round(rem_cagr * 100, 6),
                "sharpe": round(rem_sharpe, 6),
                "delta_terminal_value": round(rem_terminal - base_terminal, 2),
                "delta_cagr": round((rem_cagr - base_cagr_val) * 100, 6),
                "delta_sharpe": round(rem_sharpe - base_sharpe_val, 6),
            })

    pd.DataFrame(event_log).to_csv(OUT / "e0_skip_after_n_event_log.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(OUT / "e0_skip_after_n_summary.csv", index=False)

    # ── Plot ──
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for view in ["native", "unit_size"]:
        color = "blue" if view == "native" else "red"
        ls = "-" if view == "native" else "--"
        view_data = [r for r in summary_rows if r["ledger_view"] == view]
        ns = [r["n_threshold"] for r in view_data]

        for ax, metric, label in zip(axes,
            ["delta_terminal_value", "delta_cagr", "delta_sharpe"],
            ["Delta Terminal Value ($)", "Delta CAGR (pp)", "Delta Sharpe"]):
            vals = [r[metric] for r in view_data]
            ax.plot(ns, vals, f"{color[0]}{ls}o", label=view, markersize=6)
            ax.axhline(0, color="gray", ls=":")
    for ax, label in zip(axes, ["Delta Terminal Value ($)", "Delta CAGR (pp)", "Delta Sharpe"]):
        ax.set_xlabel("N (skip after N consecutive losses)")
        ax.set_ylabel(label)
        ax.set_title(f"E0 Skip-After-N: {label}")
        ax.legend()
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "e0_skip_after_n_impact.png", dpi=150)
    plt.close()

    for r in summary_rows:
        if r["ledger_view"] == "native":
            print(f"  N={r['n_threshold']}: skips={r['skip_event_count']}, "
                  f"winners_skipped={r['skipped_winner_count']}, "
                  f"delta_sharpe={r['delta_sharpe']:.4f}, "
                  f"top10_hit={r['skipped_top10_count']}")

    return summary_rows


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 6: Column dictionary and synthesis
# ═══════════════════════════════════════════════════════════════════════════

def phase6_column_dictionary():
    print("Phase 6: Column dictionary")
    rows = [
        # Native Episode Ledger
        ("e0_native_episode_ledger.csv", "episode_id", "Sequential episode identifier (1-192)", "derived", "sequential counter"),
        ("e0_native_episode_ledger.csv", "entry_time", "ISO timestamp of trade entry", "trades_candidate.csv:entry_ts", "direct copy"),
        ("e0_native_episode_ledger.csv", "exit_time", "ISO timestamp of trade exit", "trades_candidate.csv:exit_ts", "direct copy"),
        ("e0_native_episode_ledger.csv", "hold_bars", "Number of H4 bars held", "trades_candidate.csv:entry_ts_ms,exit_ts_ms", "(exit_ts_ms - entry_ts_ms) / (4*3600*1000)"),
        ("e0_native_episode_ledger.csv", "hold_days", "Holding time in days", "trades_candidate.csv:days_held", "direct copy"),
        ("e0_native_episode_ledger.csv", "exit_reason", "Exit type (vtrend_trail_stop or vtrend_trend_exit)", "trades_candidate.csv:exit_reason", "direct copy"),
        ("e0_native_episode_ledger.csv", "realized_return_pct", "Net realized return after fees (%)", "trades_candidate.csv:return_pct", "direct copy"),
        ("e0_native_episode_ledger.csv", "pnl_usd", "Realized PnL in USD (deploy-reality, NAV-weighted)", "trades_candidate.csv:pnl_usd", "direct copy"),
        ("e0_native_episode_ledger.csv", "mfe_pct", "Maximum favorable excursion (% of entry price)", "computed", "max(H4 highs during hold) / entry_price - 1, *100"),
        ("e0_native_episode_ledger.csv", "mae_pct", "Maximum adverse excursion (% of entry price)", "computed", "1 - min(H4 lows during hold) / entry_price, *100"),
        ("e0_native_episode_ledger.csv", "giveback_ratio", "Fraction of MFE surrendered: (MFE - realized) / MFE", "computed", "(mfe_pct - realized_return_pct) / mfe_pct; NA if mfe_pct=0"),
        ("e0_native_episode_ledger.csv", "win_flag", "1 if realized_return_pct > 0, else 0", "derived", "return_pct > 0"),
        ("e0_native_episode_ledger.csv", "native_positive_contribution_rank_desc", "Rank by pnl_usd descending (1=highest PnL)", "derived", "rank of pnl_usd, method=first"),
        # Unit-Size Episode Ledger
        ("e0_unit_size_episode_ledger.csv", "episode_id", "Sequential episode identifier (1-192)", "derived", "same as native"),
        ("e0_unit_size_episode_ledger.csv", "entry_time", "ISO timestamp of trade entry", "trades_candidate.csv:entry_ts", "direct copy"),
        ("e0_unit_size_episode_ledger.csv", "exit_time", "ISO timestamp of trade exit", "trades_candidate.csv:exit_ts", "direct copy"),
        ("e0_unit_size_episode_ledger.csv", "hold_bars", "Number of H4 bars held", "trades_candidate.csv", "(exit_ts_ms - entry_ts_ms) / (4*3600*1000)"),
        ("e0_unit_size_episode_ledger.csv", "hold_days", "Holding time in days", "trades_candidate.csv:days_held", "direct copy"),
        ("e0_unit_size_episode_ledger.csv", "exit_reason", "Exit type", "trades_candidate.csv:exit_reason", "direct copy"),
        ("e0_unit_size_episode_ledger.csv", "realized_return_pct", "Net realized return after fees (%) — exposure-neutral", "trades_candidate.csv:return_pct", "direct copy"),
        ("e0_unit_size_episode_ledger.csv", "mfe_pct", "Maximum favorable excursion (%)", "computed", "same as native"),
        ("e0_unit_size_episode_ledger.csv", "mae_pct", "Maximum adverse excursion (%)", "computed", "same as native"),
        ("e0_unit_size_episode_ledger.csv", "giveback_ratio", "Fraction of MFE surrendered", "computed", "same as native"),
        ("e0_unit_size_episode_ledger.csv", "win_flag", "1 if realized_return_pct > 0, else 0", "derived", "same as native"),
        ("e0_unit_size_episode_ledger.csv", "unit_size_positive_contribution_rank_desc", "Rank by return_pct descending (1=highest return)", "derived", "rank of return_pct, method=first"),
    ]
    df = pd.DataFrame(rows, columns=["artifact_name", "column_name", "definition", "source", "transformation"])
    df.to_csv(OUT / "e0_column_dictionary.csv", index=False)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("Step 1: E0 Home-Run Dependence & Behavioral Fragility Audit")
    print("=" * 70)

    trades, profile, mfe_mae = phase1_recon()
    ledger = phase2_ledgers_and_giveback(trades, mfe_mae)
    native_curve, unit_curve = phase3_sensitivity_curves(ledger, profile)
    cliff_rows = phase4_cliff_edge(native_curve, unit_curve)
    skip_summary = phase5_skip_after_n(ledger)
    phase6_column_dictionary()

    print("\n" + "=" * 70)
    print("All Step 1 artifacts written successfully.")
    print("=" * 70)
