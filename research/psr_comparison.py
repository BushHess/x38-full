#!/usr/bin/env python3
"""Compare PSR (relative ranking) vs DSR (absolute) across strategies.

Demonstrates that DSR trivially passes for all strategies (Sharpe >1.0 on
multi-year data), while PSR discriminates between candidates by testing
whether each genuinely beats its baseline.

Usage:
    python -m research.psr_comparison
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from research.lib.dsr import compute_psr, deflated_sharpe

# ---------------------------------------------------------------------------
# Strategy data (from selection_bias.json + full_backtest_summary.csv)
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"

# Each entry: (label, sr_candidate, sr_baseline, T, skew, kurt, family)
STRATEGIES = [
    # E-family: candidate vs E0 baseline (harsh Sharpe = 1.2653)
    {
        "label": "E0 (self)",
        "sr_candidate": 1.2653,
        "sr_baseline": 1.2653,
        "T": 2607,
        "skew": 0.874119,
        "kurt": 14.910651,
        "family": "E",
        "sb_path": "parity_20260305/eval_e0_vs_e0",
    },
    {
        "label": "E5",
        "sr_candidate": 1.3573,
        "sr_baseline": 1.2653,
        "T": 2607,
        "skew": 0.978623,
        "kurt": 15.014054,
        "family": "E",
        "sb_path": "parity_20260305/eval_e5_vs_e0",
    },
    {
        "label": "E0+EMA1D21",
        "sr_candidate": 1.3249,
        "sr_baseline": 1.2653,
        "T": 2607,
        "skew": 0.883609,
        "kurt": 15.312742,
        "family": "E",
        "sb_path": "eval_ema21d1_full_20260306/eval_ema21d1_vs_e0",
    },
    {
        "label": "E5+EMA1D21",
        "sr_candidate": 1.4300,
        "sr_baseline": 1.2653,
        "T": 2607,
        "skew": 0.996004,
        "kurt": 15.453261,
        "family": "E",
        "sb_path": "parity_20260306/eval_e5_ema21d1_vs_e0",
    },
    # X-family: candidate vs X0 baseline (harsh Sharpe = 1.3249)
    {
        "label": "X0 (self)",
        "sr_candidate": 1.3249,
        "sr_baseline": 1.3249,
        "T": 2607,
        "skew": 0.883609,
        "kurt": 15.312742,
        "family": "X",
        "sb_path": None,
    },
    {
        "label": "X2",
        "sr_candidate": 1.4227,
        "sr_baseline": 1.3249,
        "T": 2607,
        "skew": 0.813499,
        "kurt": 15.350609,
        "family": "X",
        "sb_path": "eval_x2_vs_x0_full",
    },
    {
        "label": "X6",
        "sr_candidate": 1.4324,
        "sr_baseline": 1.3249,
        "T": 2607,
        "skew": 0.815774,
        "kurt": 15.376529,
        "family": "X",
        "sb_path": "eval_x6_vs_x0_full",
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    PSR_THRESHOLD = 0.95
    DSR_THRESHOLD = 0.95
    TRIAL_LEVELS = [27, 54, 100, 200, 500, 700]

    print("=" * 110)
    print("PSR vs DSR Comparison: Relative Ranking vs Absolute Significance")
    print("=" * 110)
    print()

    rows: list[dict] = []
    for s in STRATEGIES:
        # PSR: relative test (candidate vs baseline)
        psr = compute_psr(
            sr_candidate=s["sr_candidate"],
            sr_benchmark=s["sr_baseline"],
            n_obs=s["T"],
            skew=s["skew"],
            kurt=s["kurt"],
        )

        # DSR: absolute test (at worst-case trial level = 700)
        dsr_p, dsr_emax, dsr_std = deflated_sharpe(
            sr_observed=s["sr_candidate"],
            n_trials=700,
            t_samples=s["T"],
            skew=s["skew"],
            kurt=s["kurt"],
        )

        # DSR at all trial levels
        dsr_all: dict[int, float] = {}
        for t in TRIAL_LEVELS:
            p, _, _ = deflated_sharpe(
                sr_observed=s["sr_candidate"],
                n_trials=t,
                t_samples=s["T"],
                skew=s["skew"],
                kurt=s["kurt"],
            )
            dsr_all[t] = p

        rows.append({
            "label": s["label"],
            "family": s["family"],
            "sr_cand": s["sr_candidate"],
            "sr_base": s["sr_baseline"],
            "sr_gap": s["sr_candidate"] - s["sr_baseline"],
            "psr": psr["psr"],
            "psr_z": psr["z_score"],
            "psr_se": psr["se"],
            "psr_pass": psr["psr"] >= PSR_THRESHOLD,
            "dsr_700": dsr_p,
            "dsr_pass": dsr_p >= DSR_THRESHOLD,
            "dsr_all": dsr_all,
        })

    # --- Detailed output ---
    for r in rows:
        print(f"--- {r['label']} (family {r['family']}) ---")
        print(f"  SR candidate: {r['sr_cand']:.4f}  |  SR baseline: {r['sr_base']:.4f}  |  Gap: {r['sr_gap']:+.4f}")
        print(f"  PSR = {r['psr']:.6f}  (z={r['psr_z']:.4f}, se={r['psr_se']:.6f})")
        print(f"    → {'PASS' if r['psr_pass'] else 'FAIL'} (threshold={PSR_THRESHOLD})")
        print(f"  DSR@700 = {r['dsr_700']:.6f}")
        print(f"    → {'PASS' if r['dsr_pass'] else 'FAIL'} (threshold={DSR_THRESHOLD}) — ADVISORY ONLY")
        dsr_str = ", ".join(f"{t}:{r['dsr_all'][t]:.4f}" for t in TRIAL_LEVELS)
        print(f"  DSR all trials: [{dsr_str}]")
        print()

    # --- Summary table ---
    print("=" * 110)
    print("SUMMARY TABLE")
    print("=" * 110)
    print()
    hdr = (
        f"{'Strategy':<16} {'Family':>6} │ {'SR_cand':>8} {'SR_base':>8} {'Gap':>7} │ "
        f"{'PSR':>8} {'z':>7} {'PSR':>5} │ {'DSR@700':>8} {'DSR':>5} │ {'Old':>5} {'New':>5}"
    )
    print(hdr)
    print("─" * len(hdr))
    for r in rows:
        psr_tag = "PASS" if r["psr_pass"] else "FAIL"
        dsr_tag = "PASS" if r["dsr_pass"] else "FAIL"
        # Old gate: DSR-based (all strategies pass trivially)
        old_tag = "PASS" if r["dsr_pass"] else "FAIL"
        # New gate: PSR-based (relative ranking)
        new_tag = "PASS" if r["psr_pass"] else "FAIL"
        print(
            f"{r['label']:<16} {r['family']:>6} │ "
            f"{r['sr_cand']:>8.4f} {r['sr_base']:>8.4f} {r['sr_gap']:>+7.4f} │ "
            f"{r['psr']:>8.4f} {r['psr_z']:>7.3f} {psr_tag:>5} │ "
            f"{r['dsr_700']:>8.4f} {dsr_tag:>5} │ "
            f"{old_tag:>5} {new_tag:>5}"
        )

    print()
    print("Legend: Old=DSR absolute (advisory), New=PSR relative (binding)")
    print(f"PSR threshold: {PSR_THRESHOLD} | DSR threshold: {DSR_THRESHOLD}")
    print()

    # --- Verdict change analysis ---
    print("=" * 110)
    print("VERDICT CHANGE ANALYSIS")
    print("=" * 110)
    print()

    print("Key insight: DSR trivially passes ALL strategies (p=1.000) because")
    print("Sharpe >1.0 on 2607 daily observations far exceeds the noise floor")
    print("from even 700 independent trials. DSR is not discriminating.")
    print()
    print("PSR discriminates by testing each candidate AGAINST its baseline:")
    print()

    for r in rows:
        if r["sr_gap"] == 0.0:
            print(f"  {r['label']}: baseline self-comparison → PSR=0.500 (FAIL, correctly)")
        elif r["psr_pass"]:
            print(f"  {r['label']}: SR gap={r['sr_gap']:+.4f} → PSR={r['psr']:.4f} (PASS, genuine outperformance)")
        else:
            print(f"  {r['label']}: SR gap={r['sr_gap']:+.4f} → PSR={r['psr']:.4f} (FAIL, gap not significant)")
    print()

    changes = [(r["label"], r["dsr_pass"], r["psr_pass"]) for r in rows if r["dsr_pass"] != r["psr_pass"]]
    if changes:
        print("Verdict changes (DSR→PSR):")
        for label, old, new in changes:
            print(f"  *** {label}: {'PASS' if old else 'FAIL'}→{'PASS' if new else 'FAIL'} ***")
    else:
        print("No verdict changes.")
    print()


if __name__ == "__main__":
    main()
