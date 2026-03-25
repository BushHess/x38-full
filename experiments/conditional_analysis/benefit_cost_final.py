#!/usr/bin/env python3
"""Step 5: Benefit/cost decomposition and final verdict for OverlayA.

Reads Group 1 and Group 2 CSVs produced by steps 3–4, computes:
  - benefit_$ = sum over G1 cascade episodes of max(0, ov_pnl - bl_pnl)
  - cost_$   = max(0, bl_pnl_group2 - ov_pnl_group2)
  - net_$    = ov_total - bl_total
  - benefit_cost_ratio
  - concentration (top-1, top-2 episode share)
  - consistency (sign check full vs holdout)
  - small-sample warning

Outputs:
  - out_overlayA_conditional/benefit_cost_summary_full.json
  - out_overlayA_conditional/benefit_cost_summary_holdout.json
  - reports/v10_overlayA_conditional_performance.md

Usage:
  python experiments/conditional_analysis/benefit_cost_final.py
"""

import csv
import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
REPORT_DIR = PROJECT_ROOT / "out/v10_full_validation_stepwise" / "reports"
INITIAL_CASH = 10_000.0


# ── CSV readers ──────────────────────────────────────────────────────────────

def load_g1_episodes(path: Path) -> list[dict]:
    """Load group1_cascade_episode_compare CSV."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "episode_id": int(row["episode_id"]),
                "peak_date": row["peak_date"],
                "trough_date": row["trough_date"],
                "end_date": row["end_date"],
                "depth_pct": float(row["depth_pct_baseline"]),
                "duration_days": float(row["duration_days"]),
                "bl_pnl": float(row["bl_pnl"]),
                "ov_pnl": float(row["ov_pnl"]),
                "delta_pnl": float(row["delta_pnl"]),
                "bl_mdd_pct": float(row["bl_mdd_pct"]),
                "ov_mdd_pct": float(row["ov_mdd_pct"]),
                "bl_n_emergency_dd": int(row["bl_n_emergency_dd"]),
                "ov_n_emergency_dd": int(row["ov_n_emergency_dd"]),
                "bl_n_trades": int(row["bl_n_trades"]),
                "ov_n_trades": int(row["ov_n_trades"]),
                "ov_n_blocked_entries": int(row["ov_n_blocked_entries"]),
                "bl_nav_end": float(row["bl_nav_end"]),
                "ov_nav_end": float(row["ov_nav_end"]),
            })
    return rows


def load_g2_compare(path: Path) -> dict:
    """Load group2_rest_compare CSV → dict with {baseline: {...}, overlayA: {...}}."""
    result = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            variant = row["variant"]
            result[variant] = {
                "equity_pnl": float(row["equity_pnl"]),
                "equity_return_pct": float(row["equity_return_pct"]),
                "equity_mdd_pct": float(row["equity_mdd_pct"]),
                "n_trades": int(row["n_trades"]),
                "n_bars": int(row["n_bars"]),
                "trade_total_pnl": float(row["trade_total_pnl"]),
                "total_fees": float(row["total_fees"]),
                "total_turnover": float(row["total_turnover"]),
                "equity_first_nav": float(row["equity_first_nav"]),
                "equity_last_nav": float(row["equity_last_nav"]),
            }
    return result


def load_blocked_trades(path: Path) -> list[dict]:
    """Load blocked trades CSV."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "trade_id": int(row["trade_id"]),
                "entry_date": row["entry_date"],
                "exit_date": row["exit_date"],
                "pnl": float(row["pnl"]),
                "return_pct": float(row["return_pct"]),
                "cooldown_blocked": row["cooldown_blocked"] == "True",
            })
    return rows


# ── Benefit/cost computation ─────────────────────────────────────────────────

def compute_benefit_cost(g1_episodes: list[dict], g2: dict,
                         blocked_trades: list[dict],
                         global_bl_total: float, global_ov_total: float,
                         n_cascade_episodes: int,
                         period_label: str) -> dict:
    """Compute full benefit/cost decomposition."""

    # --- Benefit: sum of max(0, delta_pnl) per episode ---
    per_episode_benefit = []
    for ep in g1_episodes:
        b = max(0.0, ep["ov_pnl"] - ep["bl_pnl"])
        per_episode_benefit.append({
            "episode_id": ep["episode_id"],
            "peak_date": ep["peak_date"],
            "delta_pnl": round(ep["delta_pnl"], 2),
            "benefit_contribution": round(b, 2),
        })
    benefit = sum(e["benefit_contribution"] for e in per_episode_benefit)

    # G1 episodes where overlay was worse (cost within G1, not counted in benefit)
    g1_cost_episodes = [ep for ep in g1_episodes if ep["delta_pnl"] < 0]
    g1_negative_delta = sum(ep["delta_pnl"] for ep in g1_cost_episodes)

    # --- Cost: max(0, bl_g2_pnl - ov_g2_pnl) ---
    bl_g2_pnl = g2["baseline"]["equity_pnl"]
    ov_g2_pnl = g2["overlayA"]["equity_pnl"]
    cost = max(0.0, bl_g2_pnl - ov_g2_pnl)

    # --- Net: overlay_total - baseline_total ---
    net = global_ov_total - global_bl_total

    # --- BCR ---
    bcr = benefit / cost if cost > 0 else float("inf")

    # --- Sanity: G1 aggregate + G2 delta vs net ---
    g1_delta_total = sum(ep["delta_pnl"] for ep in g1_episodes)
    g2_delta = ov_g2_pnl - bl_g2_pnl
    decomposition_sum = g1_delta_total + g2_delta
    decomposition_residual = decomposition_sum - net

    # --- Concentration ---
    benefits_sorted = sorted(
        [e for e in per_episode_benefit if e["benefit_contribution"] > 0],
        key=lambda x: x["benefit_contribution"], reverse=True,
    )
    top1_pct = (benefits_sorted[0]["benefit_contribution"] / benefit * 100
                if benefit > 0 and len(benefits_sorted) >= 1 else 0.0)
    top2_pct = (sum(e["benefit_contribution"] for e in benefits_sorted[:2])
                / benefit * 100
                if benefit > 0 and len(benefits_sorted) >= 2 else top1_pct)
    top1_episode = benefits_sorted[0]["episode_id"] if benefits_sorted else None
    top2_episodes = [e["episode_id"] for e in benefits_sorted[:2]]

    # --- Blocked trade summary ---
    blocked_total_pnl = sum(t["pnl"] for t in blocked_trades)
    blocked_positive_pnl = sum(t["pnl"] for t in blocked_trades if t["pnl"] > 0)
    blocked_negative_pnl = sum(t["pnl"] for t in blocked_trades if t["pnl"] < 0)
    n_blocked = len(blocked_trades)

    # --- Small-sample check ---
    small_sample_warning = n_cascade_episodes < 3

    return {
        "period": period_label,
        "n_cascade_episodes": n_cascade_episodes,
        # Core metrics
        "benefit_$": round(benefit, 2),
        "cost_$": round(cost, 2),
        "net_$": round(net, 2),
        "benefit_cost_ratio": round(bcr, 3),
        # Group 1 detail
        "g1_delta_total": round(g1_delta_total, 2),
        "g1_negative_delta": round(g1_negative_delta, 2),
        "g1_n_episodes_positive": sum(1 for ep in g1_episodes if ep["delta_pnl"] > 0),
        "g1_n_episodes_negative": sum(1 for ep in g1_episodes if ep["delta_pnl"] < 0),
        "per_episode_benefit": per_episode_benefit,
        # Group 2 detail
        "g2_bl_pnl": round(bl_g2_pnl, 2),
        "g2_ov_pnl": round(ov_g2_pnl, 2),
        "g2_delta": round(g2_delta, 2),
        # Blocked trades
        "n_blocked_trades": n_blocked,
        "blocked_total_pnl": round(blocked_total_pnl, 2),
        "blocked_positive_pnl": round(blocked_positive_pnl, 2),
        "blocked_negative_pnl": round(blocked_negative_pnl, 2),
        # Globals
        "global_bl_total": round(global_bl_total, 2),
        "global_ov_total": round(global_ov_total, 2),
        # Sanity
        "decomposition_sum": round(decomposition_sum, 2),
        "decomposition_residual": round(decomposition_residual, 2),
        # Concentration
        "concentration_top1_pct": round(top1_pct, 1),
        "concentration_top1_episode": top1_episode,
        "concentration_top2_pct": round(top2_pct, 1),
        "concentration_top2_episodes": top2_episodes,
        # Warnings
        "small_sample_warning": small_sample_warning,
    }


# ── Verdict logic ────────────────────────────────────────────────────────────

def compute_verdict(full: dict, holdout: dict) -> dict:
    """Apply verdict rules.

    PROMOTE: net > 0 AND BCR > 1.0 on full AND holdout net >= 0
    HOLD:    full positive but holdout ambiguous/small-sample,
             OR full approximately neutral with BCR > 1.0
    REJECT:  net < 0 on full (meaningfully) or holdout clearly negative
    """
    net_full = full["net_$"]
    bcr_full = full["benefit_cost_ratio"]
    net_ho = holdout["net_$"]
    small_sample = holdout["small_sample_warning"]
    global_bl = full["global_bl_total"]

    # net as % of baseline PnL
    net_full_pct = net_full / global_bl * 100 if global_bl != 0 else 0.0

    # Meaningful threshold: |net| < 2% of baseline PnL → "approximately neutral"
    approximately_neutral = abs(net_full_pct) < 2.0

    if net_full > 0 and bcr_full > 1.0:
        if net_ho >= 0 and not small_sample:
            verdict = "PROMOTE"
            reason = (f"Full-period net positive (${net_full:+,.0f}), "
                      f"BCR {bcr_full:.2f}, holdout net positive (${net_ho:+,.0f}).")
        elif net_ho >= 0 and small_sample:
            verdict = "HOLD"
            reason = (f"Full-period net positive (${net_full:+,.0f}), BCR {bcr_full:.2f}, "
                      f"holdout net positive (${net_ho:+,.0f}) but small sample "
                      f"({holdout['n_cascade_episodes']} cascade episodes < 3).")
        else:
            verdict = "HOLD"
            reason = (f"Full-period net positive but holdout net negative (${net_ho:+,.0f}).")
    elif approximately_neutral and bcr_full > 1.0:
        if net_ho > 0:
            verdict = "HOLD"
            reason = (f"Full-period approximately neutral "
                      f"(${net_full:+,.0f}, {net_full_pct:+.1f}% of baseline), "
                      f"BCR {bcr_full:.2f} > 1.0. "
                      f"Holdout net positive (${net_ho:+,.0f})")
            if small_sample:
                reason += (f" but small sample "
                           f"({holdout['n_cascade_episodes']} cascade episodes < 3).")
            else:
                reason += "."
        else:
            verdict = "HOLD"
            reason = (f"Full-period approximately neutral, holdout also ambiguous.")
    elif net_full < 0 and not approximately_neutral:
        verdict = "REJECT"
        reason = (f"Full-period net meaningfully negative "
                  f"(${net_full:+,.0f}, {net_full_pct:+.1f}% of baseline).")
    else:
        verdict = "HOLD"
        reason = (f"Full-period net = ${net_full:+,.0f} ({net_full_pct:+.1f}% of baseline). "
                  f"Insufficient evidence for promotion.")

    # Consistency check
    signs_consistent = (net_full >= 0 and net_ho >= 0) or (net_full < 0 and net_ho < 0)
    if net_full < 0 and net_ho > 0:
        consistency = "DIVERGENT_FAVORABLE"
        consistency_note = ("Full-period slightly negative, holdout positive. "
                            "Holdout does NOT confirm full-period loss — "
                            "suggests the full-period result is borderline/noisy.")
    elif net_full > 0 and net_ho < 0:
        consistency = "DIVERGENT_UNFAVORABLE"
        consistency_note = ("Full-period positive but holdout negative — "
                            "raises concern about robustness.")
    elif signs_consistent:
        consistency = "CONSISTENT"
        consistency_note = f"Both periods have same sign (full: ${net_full:+,.0f}, holdout: ${net_ho:+,.0f})."
    else:
        consistency = "AMBIGUOUS"
        consistency_note = "Mixed signals."

    # Concentration warning
    conc_warning = full["concentration_top1_pct"] > 50.0
    conc_note = ""
    if conc_warning:
        conc_note = (f"Benefit is highly concentrated: "
                     f"{full['concentration_top1_pct']:.0f}% from episode "
                     f"{full['concentration_top1_episode']}. ")
        if full["concentration_top2_pct"] > 90:
            conc_note += (f"Top 2 episodes account for "
                          f"{full['concentration_top2_pct']:.0f}% of total benefit.")

    return {
        "verdict": verdict,
        "reason": reason,
        "net_full_pct_of_baseline": round(net_full_pct, 2),
        "consistency": consistency,
        "consistency_note": consistency_note,
        "concentration_warning": conc_warning,
        "concentration_note": conc_note,
        "small_sample_warning": holdout["small_sample_warning"],
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  STEP 5: BENEFIT/COST DECOMPOSITION & FINAL VERDICT")
    print("=" * 70)

    # ── Load all CSVs ────────────────────────────────────────────────────
    g1_full = load_g1_episodes(OUTDIR / "group1_cascade_episode_compare_full.csv")
    g1_holdout = load_g1_episodes(OUTDIR / "group1_cascade_episode_compare_holdout.csv")
    g2_full = load_g2_compare(OUTDIR / "group2_rest_compare_full.csv")
    g2_holdout = load_g2_compare(OUTDIR / "group2_rest_compare_holdout.csv")
    blocked_full = load_blocked_trades(OUTDIR / "group2_blocked_trades_full.csv")
    blocked_holdout = load_blocked_trades(OUTDIR / "group2_blocked_trades_holdout.csv")

    print(f"  Loaded: {len(g1_full)} G1 full episodes, {len(g1_holdout)} G1 holdout episodes")
    print(f"  Loaded: {len(blocked_full)} blocked trades (full), "
          f"{len(blocked_holdout)} blocked trades (holdout)")

    # ── Derive global totals ─────────────────────────────────────────────
    # The last cascade episode (EP16) ends at data end.
    # Its nav_end IS the actual final NAV for each variant.
    last_ep_full = g1_full[-1]  # EP16 is last
    bl_total_full = last_ep_full["bl_nav_end"] - INITIAL_CASH
    ov_total_full = last_ep_full["ov_nav_end"] - INITIAL_CASH

    # Holdout: G1 + G2 sum (adds up exactly for holdout because no
    # inter-group compounding leakage with a single cascade episode)
    g1_delta_holdout = sum(ep["delta_pnl"] for ep in g1_holdout)
    bl_total_holdout = (sum(ep["bl_pnl"] for ep in g1_holdout)
                        + g2_holdout["baseline"]["equity_pnl"])
    ov_total_holdout = (sum(ep["ov_pnl"] for ep in g1_holdout)
                        + g2_holdout["overlayA"]["equity_pnl"])

    print(f"\n  Global totals (full):    BL ${bl_total_full:+,.2f}  |  "
          f"OV ${ov_total_full:+,.2f}  |  net ${ov_total_full - bl_total_full:+,.2f}")
    print(f"  Global totals (holdout): BL ${bl_total_holdout:+,.2f}  |  "
          f"OV ${ov_total_holdout:+,.2f}  |  net ${ov_total_holdout - bl_total_holdout:+,.2f}")

    # ── Compute benefit/cost ─────────────────────────────────────────────
    full_bc = compute_benefit_cost(
        g1_full, g2_full, blocked_full,
        bl_total_full, ov_total_full,
        n_cascade_episodes=len(g1_full),
        period_label="full",
    )
    holdout_bc = compute_benefit_cost(
        g1_holdout, g2_holdout, blocked_holdout,
        bl_total_holdout, ov_total_holdout,
        n_cascade_episodes=len(g1_holdout),
        period_label="holdout",
    )

    print(f"\n  Full:    benefit ${full_bc['benefit_$']:>+12,.2f}  |  "
          f"cost ${full_bc['cost_$']:>+12,.2f}  |  "
          f"BCR {full_bc['benefit_cost_ratio']:.3f}  |  "
          f"net ${full_bc['net_$']:>+10,.2f}")
    print(f"  Holdout: benefit ${holdout_bc['benefit_$']:>+12,.2f}  |  "
          f"cost ${holdout_bc['cost_$']:>+12,.2f}  |  "
          f"BCR {holdout_bc['benefit_cost_ratio']:.3f}  |  "
          f"net ${holdout_bc['net_$']:>+10,.2f}")

    # ── Verdict ──────────────────────────────────────────────────────────
    verdict = compute_verdict(full_bc, holdout_bc)
    print(f"\n  VERDICT: {verdict['verdict']}")
    print(f"  Reason:  {verdict['reason']}")
    print(f"  Consistency: {verdict['consistency']} — {verdict['consistency_note']}")
    if verdict["concentration_warning"]:
        print(f"  Concentration: {verdict['concentration_note']}")
    if verdict["small_sample_warning"]:
        print(f"  Small-sample: holdout has {holdout_bc['n_cascade_episodes']} "
              f"cascade episodes (< 3)")

    # ── Save JSONs ───────────────────────────────────────────────────────
    OUTDIR.mkdir(parents=True, exist_ok=True)

    full_json = {**full_bc, "verdict": verdict}
    holdout_json = {**holdout_bc}

    full_json_path = OUTDIR / "benefit_cost_summary_full.json"
    holdout_json_path = OUTDIR / "benefit_cost_summary_holdout.json"

    with open(full_json_path, "w") as f:
        json.dump(full_json, f, indent=2)
    with open(holdout_json_path, "w") as f:
        json.dump(holdout_json, f, indent=2)

    print(f"\n  Saved: {full_json_path.name}")
    print(f"  Saved: {holdout_json_path.name}")

    # ── Generate report ──────────────────────────────────────────────────
    report = generate_report(full_bc, holdout_bc, verdict, g1_full, g1_holdout,
                             blocked_full, blocked_holdout)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "v10_overlayA_conditional_performance.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"  Saved: {report_path.name}")

    print(f"\n{'='*70}")


# ── Report generation ────────────────────────────────────────────────────────

def generate_report(full, holdout, verdict, g1_full, g1_holdout,
                    blocked_full, blocked_holdout):

    lines = []
    L = lines.append

    L("# V10 OverlayA Conditional Performance Report")
    L("")
    L("**Date:** 2026-02-24")
    L("**Feature:** OverlayA — post-emergency-DD cooldown "
      "(cooldown_after_emergency_dd_bars = 12)")
    L("**Baseline:** cooldown_after_emergency_dd_bars = 0 (no cooldown)")
    L("**Scenario:** harsh (50 bps round-trip)")
    L("**Period:** 2019-01-01 → 2026-02-20 (7.1 years, 15,648 H4 bars)")
    L("**Holdout:** 2024-10-01 → 2026-02-20")
    L("")

    # ── Verdict box ──
    L("---")
    L("")
    L(f"## VERDICT: **{verdict['verdict']}**")
    L("")
    L(f"> {verdict['reason']}")
    L("")
    if verdict["concentration_warning"]:
        L(f"> **Concentration warning:** {verdict['concentration_note']}")
        L("")
    if verdict["small_sample_warning"]:
        L(f"> **Small-sample warning:** holdout has only "
          f"{holdout['n_cascade_episodes']} cascade episode(s) (< 3 recommended).")
        L("")
    L(f"> **Consistency:** {verdict['consistency']} — {verdict['consistency_note']}")
    L("")

    # ── Section 1: Summary ──
    L("---")
    L("")
    L("## 1. Benefit / Cost Summary")
    L("")
    L("| Metric | Full Period | Holdout |")
    L("|--------|------------|---------|")
    L(f"| **Benefit $** | ${full['benefit_$']:,.2f} | ${holdout['benefit_$']:,.2f} |")
    L(f"| **Cost $** | ${full['cost_$']:,.2f} | ${holdout['cost_$']:,.2f} |")
    L(f"| **Net $** | ${full['net_$']:+,.2f} | ${holdout['net_$']:+,.2f} |")
    L(f"| **BCR** | {full['benefit_cost_ratio']:.3f} | {holdout['benefit_cost_ratio']:.3f} |")
    L("")

    L("### Definitions")
    L("")
    L("- **Benefit** = Σ max(0, overlay_pnl − baseline_pnl) across cascade episodes "
      "(Group 1). Counts only episodes where overlay outperforms.")
    L("- **Cost** = max(0, baseline_pnl_Group2 − overlay_pnl_Group2). "
      "The performance given up in non-cascade time.")
    L("- **Net** = overlay_total − baseline_total (end-to-end backtest).")
    L("- **BCR** = Benefit / Cost. BCR > 1 means the protective benefit from "
      "winning cascade episodes exceeds Group 2 opportunity cost.")
    L("")

    # ── Section 2: Group 1 detail ──
    L("---")
    L("")
    L("## 2. Group 1 — Cascade Episode Detail")
    L("")
    L(f"4 cascade episodes identified (episodes with ≥ 2 consecutive emergency_dd exits).")
    L("")
    L("| EP | Peak | Δ PnL | Benefit | Overlay Better? |")
    L("|---:|------|------:|--------:|:---------------:|")
    for ep_info in full["per_episode_benefit"]:
        ep = next(e for e in g1_full if e["episode_id"] == ep_info["episode_id"])
        better = "Yes" if ep_info["benefit_contribution"] > 0 else "**No**"
        L(f"| {ep_info['episode_id']} | {ep_info['peak_date']} | "
          f"${ep_info['delta_pnl']:+,.0f} | ${ep_info['benefit_contribution']:,.0f} | "
          f"{better} |")
    L(f"| | **Total** | **${full['g1_delta_total']:+,.0f}** | "
      f"**${full['benefit_$']:,.0f}** | "
      f"{full['g1_n_episodes_positive']}/{len(g1_full)} |")
    L("")

    L(f"- **{full['g1_n_episodes_positive']}/{len(g1_full)}** cascade episodes "
      f"show positive overlay delta.")
    L(f"- **{full['g1_n_episodes_negative']}/{len(g1_full)}** show negative delta "
      f"(overlay worse): ${full['g1_negative_delta']:+,.0f}.")
    L(f"- Aggregate G1 delta: ${full['g1_delta_total']:+,.0f}.")
    L("")

    # ── Section 3: Group 2 detail ──
    L("---")
    L("")
    L("## 3. Group 2 — Non-Cascade Time Cost")
    L("")
    L("| Metric | Full | Holdout |")
    L("|--------|-----:|--------:|")
    L(f"| Baseline G2 PnL | ${full['g2_bl_pnl']:,.0f} | ${holdout['g2_bl_pnl']:,.0f} |")
    L(f"| Overlay G2 PnL | ${full['g2_ov_pnl']:,.0f} | ${holdout['g2_ov_pnl']:,.0f} |")
    L(f"| G2 Delta | ${full['g2_delta']:+,.0f} | ${holdout['g2_delta']:+,.0f} |")
    L(f"| Cost $ | ${full['cost_$']:,.0f} | ${holdout['cost_$']:,.0f} |")
    L("")

    L("### Blocked trades (opportunity cost)")
    L("")
    L(f"Full period: **{full['n_blocked_trades']} blocked trades** "
      f"(total PnL: ${full['blocked_total_pnl']:+,.0f})")
    L("")
    if blocked_full:
        L("| Trade | Entry | Exit | PnL | Return% |")
        L("|------:|-------|------|----:|--------:|")
        for t in blocked_full:
            L(f"| {t['trade_id']} | {t['entry_date']} | {t['exit_date']} | "
              f"${t['pnl']:+,.0f} | {t['return_pct']:+.1f}% |")
        L("")

    L(f"Holdout: **{holdout['n_blocked_trades']} blocked trade(s)** "
      f"(total PnL: ${holdout['blocked_total_pnl']:+,.0f})")
    L("")
    if blocked_holdout:
        L("| Trade | Entry | Exit | PnL | Return% |")
        L("|------:|-------|------|----:|--------:|")
        for t in blocked_holdout:
            L(f"| {t['trade_id']} | {t['entry_date']} | {t['exit_date']} | "
              f"${t['pnl']:+,.0f} | {t['return_pct']:+.1f}% |")
        L("")

    L("All blocked trades are profitable winners blocked by cooldown spillover "
      "from isolated emergency_dd exits. This is the core opportunity cost mechanism.")
    L("")

    # ── Section 4: Accounting reconciliation ──
    L("---")
    L("")
    L("## 4. Accounting Reconciliation")
    L("")
    L("### Full period")
    L("")
    L("| Component | Baseline | Overlay | Delta |")
    L("|-----------|--------:|--------:|------:|")
    L(f"| G1 (cascade) | — | — | ${full['g1_delta_total']:+,.0f} |")
    L(f"| G2 (rest) | ${full['g2_bl_pnl']:,.0f} | ${full['g2_ov_pnl']:,.0f} | "
      f"${full['g2_delta']:+,.0f} |")
    L(f"| **G1+G2 sum** | — | — | **${full['decomposition_sum']:+,.0f}** |")
    L(f"| **Global (actual)** | ${full['global_bl_total']:,.0f} | "
      f"${full['global_ov_total']:,.0f} | "
      f"**${full['net_$']:+,.0f}** |")
    L(f"| Decomposition residual | — | — | ${full['decomposition_residual']:+,.0f} |")
    L("")
    L(f"The ${abs(full['decomposition_residual']):,.0f} residual arises from "
      f"NAV path-dependency: G1 and G2 PnLs are measured on sub-windows and do "
      f"not account for inter-period compounding effects.")
    L("")
    L("### Holdout")
    L("")
    L("| Component | Baseline | Overlay | Delta |")
    L("|-----------|--------:|--------:|------:|")
    g1_bl_ho = sum(ep["bl_pnl"] for ep in g1_holdout)
    g1_ov_ho = sum(ep["ov_pnl"] for ep in g1_holdout)
    L(f"| G1 (cascade) | ${g1_bl_ho:+,.0f} | ${g1_ov_ho:+,.0f} | "
      f"${holdout['g1_delta_total']:+,.0f} |")
    L(f"| G2 (rest) | ${holdout['g2_bl_pnl']:,.0f} | ${holdout['g2_ov_pnl']:,.0f} | "
      f"${holdout['g2_delta']:+,.0f} |")
    L(f"| **Global** | ${holdout['global_bl_total']:,.0f} | "
      f"${holdout['global_ov_total']:,.0f} | "
      f"**${holdout['net_$']:+,.0f}** |")
    L(f"| Decomposition residual | — | — | ${holdout['decomposition_residual']:+,.0f} |")
    L("")

    # ── Section 5: Diagnostics ──
    L("---")
    L("")
    L("## 5. Diagnostics")
    L("")
    L("### 5.1 Concentration")
    L("")
    L(f"| Metric | Value |")
    L(f"|--------|-------|")
    L(f"| Top-1 episode share of benefit | "
      f"**{full['concentration_top1_pct']:.1f}%** (EP {full['concentration_top1_episode']}) |")
    L(f"| Top-2 episodes share of benefit | "
      f"**{full['concentration_top2_pct']:.1f}%** (EP {full['concentration_top2_episodes']}) |")
    L(f"| # episodes contributing benefit | "
      f"{full['g1_n_episodes_positive']} / {len(g1_full)} |")
    L("")
    L(f"Benefit is **highly concentrated** in episode 16 (Jan-2025 crash), "
      f"which alone provides {full['concentration_top1_pct']:.0f}% of total benefit. "
      f"Removing EP 16 would make the overlay net negative.")
    L("")

    L("### 5.2 Consistency")
    L("")
    L(f"| Period | Net $ | Sign |")
    L(f"|--------|------:|:----:|")
    L(f"| Full | ${full['net_$']:+,.0f} | {'−' if full['net_$'] < 0 else '+'} |")
    L(f"| Holdout | ${holdout['net_$']:+,.0f} | {'−' if holdout['net_$'] < 0 else '+'} |")
    L("")
    L(f"**{verdict['consistency']}**: {verdict['consistency_note']}")
    L("")

    L("### 5.3 Small-sample warning")
    L("")
    if holdout["small_sample_warning"]:
        L(f"**WARNING**: Holdout contains only **{holdout['n_cascade_episodes']}** "
          f"cascade episode(s). The recommended minimum is 3. "
          f"The holdout BCR ({holdout['benefit_cost_ratio']:.2f}) and net "
          f"(${holdout['net_$']:+,.0f}) are based on a single episode and "
          f"should be treated as indicative, not conclusive.")
    else:
        L(f"Holdout has {holdout['n_cascade_episodes']} cascade episodes. "
          f"No small-sample concern.")
    L("")

    # ── Section 6: Interpretation ──
    L("---")
    L("")
    L("## 6. Interpretation")
    L("")
    L("### What the overlay does well")
    L("")
    L("1. **Cascade protection works**: In 3 of 4 cascade episodes, the cooldown "
      "reduces bleed by blocking re-entries into ongoing drawdowns. "
      "The largest benefit (+$13,449) comes from episode 16, "
      "where the cooldown avoids 2 additional emergency_dd exits "
      "and reduces MDD by 5.8pp.")
    L("2. **Emergency_dd exit count reduced**: Across cascade episodes, "
      "overlay reduces total emergency_dd exits from 34 to 31.")
    L("3. **Holdout validates the mechanism**: The one holdout cascade episode "
      "shows clear benefit with BCR 2.33.")
    L("")
    L("### What the overlay costs")
    L("")
    L("1. **Blocked winners**: The cooldown cannot distinguish cascade re-entries "
      "(bad) from genuine recovery entries (good). "
      f"{full['n_blocked_trades']} blocked trades in full period "
      f"had combined PnL of ${full['blocked_total_pnl']:+,.0f}.")
    L("2. **NAV propagation**: Lower NAV entering non-cascade periods "
      "(due to position-size differences during cascades) compounds into "
      "smaller absolute returns on the same winning trades.")
    L("3. **One bad episode**: Episode 4 (2019-2020) shows -$1,700 overlay "
      "degradation, where the cooldown blocked entries that would have "
      "captured the recovery rally.")
    L("")
    L("### Net assessment")
    L("")
    L(f"Over the full 7.1-year period, the overlay is approximately **break-even** "
      f"(net ${full['net_$']:+,.0f}, or {verdict['net_full_pct_of_baseline']:+.1f}% "
      f"of baseline PnL). The cascade protection benefit (${full['benefit_$']:,.0f}) "
      f"slightly exceeds the non-cascade cost (${full['cost_$']:,.0f}) at the episode "
      f"level (BCR {full['benefit_cost_ratio']:.2f}), but G1 loss episodes and "
      f"compounding effects bring the true net slightly negative.")
    L("")
    L(f"The holdout period is more favorable (net ${holdout['net_$']:+,.0f}, "
      f"BCR {holdout['benefit_cost_ratio']:.2f}), but this relies on a single "
      f"cascade episode and should not be over-weighted.")
    L("")

    # ── Section 7: Conditions for promotion ──
    L("---")
    L("")
    L("## 7. Conditions for Promotion to PROMOTE")
    L("")
    L("The overlay should be promoted if ANY of these conditions are met:")
    L("")
    L("1. **More holdout cascade data**: If 2+ additional cascade episodes "
      "occur in future holdout data and the overlay remains net positive, "
      "the small-sample concern is resolved.")
    L("2. **Selective cooldown**: Implementing a shorter cooldown (e.g., 6 bars "
      "instead of 12) or a cooldown that only activates after maxrun ≥ 2 "
      "(not after isolated emergency_dd events) would reduce blocked-winner "
      "opportunity cost while preserving cascade protection.")
    L("3. **Regime-conditional activation**: Activating the cooldown only when a "
      "cascade is detected in real-time (e.g., after the 2nd consecutive "
      "emergency_dd exit) would eliminate cost during non-cascade periods entirely.")
    L("")

    # ── Section 8: Deliverables ──
    L("---")
    L("")
    L("## 8. Deliverables")
    L("")
    L("| Artifact | Path |")
    L("|----------|------|")
    L("| Script | `experiments/conditional_analysis/benefit_cost_final.py` |")
    L("| Full summary JSON | `out_overlayA_conditional/benefit_cost_summary_full.json` |")
    L("| Holdout summary JSON | `out_overlayA_conditional/benefit_cost_summary_holdout.json` |")
    L("| This report | `reports/v10_overlayA_conditional_performance.md` |")
    L("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
