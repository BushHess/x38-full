#!/usr/bin/env python3
"""Compare WFO gate verdicts: Wilcoxon vs Bootstrap CI vs binary win-rate.

Reads existing wfo_per_round_metrics.csv for 5 strategies and computes:
  1. Wilcoxon signed-rank (one-sided, H_a: median > 0)
  2. Bootstrap CI on mean delta (95% percentile)
  3. Binary win-rate (legacy, advisory only)

Usage:
    python -m research.wfo_gate_comparison
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"

STRATEGIES: dict[str, Path] = {
    "E0_plus_EMA1D21": RESULTS / "parity_20260305" / "eval_ema21d1_vs_e0" / "results" / "wfo_per_round_metrics.csv",
    "E5_vs_E0":        RESULTS / "parity_20260305" / "eval_e5_vs_e0"      / "results" / "wfo_per_round_metrics.csv",
    "E5_plus_EMA1D21": RESULTS / "parity_20260306" / "eval_e5_ema21d1_vs_e0" / "results" / "wfo_per_round_metrics.csv",
    "X2_vs_X0":        RESULTS / "eval_x2_vs_x0_full" / "results" / "wfo_per_round_metrics.csv",
    "X6_vs_X0":        RESULTS / "eval_x6_vs_x0_full" / "results" / "wfo_per_round_metrics.csv",
}

WILCOXON_ALPHA = 0.10
BOOTSTRAP_N = 10_000
BOOTSTRAP_ALPHA = 0.05
BINARY_THRESHOLD = 0.60
SMALL_SAMPLE_CUTOFF = 5


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_deltas(csv_path: Path) -> list[float]:
    """Extract valid-window delta_harsh_score values from WFO CSV."""
    deltas: list[float] = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("valid_window", "").strip().lower() not in ("true", "1"):
                continue
            val = float(row["delta_harsh_score"])
            if math.isfinite(val):
                deltas.append(val)
    return deltas


# ---------------------------------------------------------------------------
# Gate evaluations
# ---------------------------------------------------------------------------

def wilcoxon_gate(deltas: list[float], alpha: float = WILCOXON_ALPHA) -> dict:
    """Wilcoxon signed-rank, one-sided (greater)."""
    nonzero = [d for d in deltas if d != 0.0]
    if len(nonzero) < 6:
        return {"pass": False, "p": 1.0, "stat": None, "reason": f"n_nonzero={len(nonzero)}<6"}
    stat, p = wilcoxon(deltas, alternative="greater")
    return {"pass": p <= alpha, "p": round(p, 6), "stat": round(stat, 2), "reason": ""}


def bootstrap_ci_gate(
    deltas: list[float],
    n_resamples: int = BOOTSTRAP_N,
    alpha: float = BOOTSTRAP_ALPHA,
) -> dict:
    """Percentile bootstrap 95% CI on mean(delta)."""
    n = len(deltas)
    if n < 2:
        return {"pass": False, "ci_lo": None, "ci_hi": None, "mean": None, "reason": "n<2"}
    rng = np.random.default_rng(seed=42)
    arr = np.array(deltas)
    means = np.array([arr[rng.integers(0, n, size=n)].mean() for _ in range(n_resamples)])
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return {
        "pass": lo > 0.0,
        "ci_lo": round(lo, 4),
        "ci_hi": round(hi, 4),
        "mean": round(float(arr.mean()), 4),
        "reason": "",
    }


def binary_gate(deltas: list[float]) -> dict:
    """Legacy binary win-rate gate (advisory)."""
    n = len(deltas)
    wins = sum(1 for d in deltas if d > 0.0)
    rate = wins / n if n > 0 else 0.0
    if n <= SMALL_SAMPLE_CUTOFF:
        required = max(n - 1, 0)
        passed = wins >= required
        detail = f"{wins}/{n} (N-1 rule, required>={required})"
    else:
        passed = rate >= BINARY_THRESHOLD
        detail = f"{wins}/{n}={rate:.1%} (required>={BINARY_THRESHOLD:.0%})"
    return {"pass": passed, "rate": round(rate, 4), "wins": wins, "n": n, "detail": detail}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 100)
    print("WFO Gate Comparison: Wilcoxon vs Bootstrap CI vs Binary Win-Rate")
    print("=" * 100)
    print()

    rows: list[dict] = []

    for label, csv_path in STRATEGIES.items():
        if not csv_path.exists():
            print(f"  SKIP {label}: {csv_path} not found")
            continue

        deltas = load_deltas(csv_path)
        w = wilcoxon_gate(deltas)
        b = bootstrap_ci_gate(deltas)
        r = binary_gate(deltas)

        # Combined verdict: pass if EITHER Wilcoxon or Bootstrap CI passes
        combined = w["pass"] or b["pass"]

        rows.append({
            "label": label,
            "n": len(deltas),
            "deltas": deltas,
            "mean": round(sum(deltas) / len(deltas), 2) if deltas else 0,
            "wilcoxon": w,
            "bootstrap": b,
            "binary": r,
            "combined": combined,
        })

    # --- Detailed per-strategy output ---
    for row in rows:
        label = row["label"]
        deltas = row["deltas"]
        w = row["wilcoxon"]
        b = row["bootstrap"]
        r = row["binary"]

        print(f"--- {label} ---")
        print(f"  Windows: {row['n']}, Mean delta: {row['mean']}")
        print(f"  Deltas: [{', '.join(f'{d:+.2f}' for d in deltas)}]")
        print()
        print(f"  [BINDING] Wilcoxon signed-rank (α={WILCOXON_ALPHA}):")
        print(f"    p = {w['p']}, stat = {w['stat']}  →  {'PASS' if w['pass'] else 'FAIL'}")
        if w["reason"]:
            print(f"    Note: {w['reason']}")
        print()
        print(f"  [BINDING] Bootstrap CI (95%, B={BOOTSTRAP_N}):")
        print(f"    CI = [{b['ci_lo']}, {b['ci_hi']}], mean = {b['mean']}  →  {'PASS' if b['pass'] else 'FAIL'}")
        print()
        print(f"  [ADVISORY] Binary win-rate:")
        print(f"    {r['detail']}  →  {'PASS' if r['pass'] else 'FAIL'}")
        print()
        print(f"  *** Combined verdict (Wilcoxon OR Bootstrap): {'PASS' if row['combined'] else 'FAIL'} ***")
        print()

    # --- Summary table ---
    print()
    print("=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print()
    header = f"{'Strategy':<22} {'N':>3} {'Mean Δ':>8} │ {'Wilcoxon p':>11} {'W':>5} │ {'Boot CI lo':>10} {'B':>5} │ {'WinRate':>8} {'Bin':>5} │ {'Verdict':>8}"
    print(header)
    print("─" * len(header))

    for row in rows:
        w = row["wilcoxon"]
        b = row["bootstrap"]
        r = row["binary"]
        w_tag = "PASS" if w["pass"] else "FAIL"
        b_tag = "PASS" if b["pass"] else "FAIL"
        r_tag = "PASS" if r["pass"] else "FAIL"
        v_tag = "PASS" if row["combined"] else "FAIL"
        ci_lo_str = f"{b['ci_lo']:10.4f}" if b['ci_lo'] is not None else "       N/A"

        print(
            f"{row['label']:<22} {row['n']:>3} {row['mean']:>+8.2f} │ "
            f"{w['p']:>11.6f} {w_tag:>5} │ "
            f"{ci_lo_str} {b_tag:>5} │ "
            f"{r['rate']:>7.1%} {r_tag:>5} │ "
            f"{v_tag:>8}"
        )

    print()
    print("Legend: W=Wilcoxon, B=Bootstrap CI, Bin=Binary win-rate (advisory)")
    print(f"Binding: Wilcoxon α={WILCOXON_ALPHA} one-sided | Bootstrap 95% CI excludes zero")
    print("Combined: PASS if EITHER Wilcoxon OR Bootstrap CI passes")
    print()

    # --- Verdict change analysis ---
    print("=" * 100)
    print("VERDICT CHANGE ANALYSIS (new vs old gate)")
    print("=" * 100)
    print()
    for row in rows:
        old = row["binary"]["pass"]
        new = row["combined"]
        if old != new:
            direction = "FAIL→PASS" if new else "PASS→FAIL"
            print(f"  *** {row['label']}: {direction} ***")
            print(f"      Old (binary): {'PASS' if old else 'FAIL'} — {row['binary']['detail']}")
            w = row["wilcoxon"]
            b = row["bootstrap"]
            print(f"      New (Wilcoxon p={w['p']}, Boot CI lo={b['ci_lo']}): {'PASS' if new else 'FAIL'}")
            print()

    if all(row["binary"]["pass"] == row["combined"] for row in rows):
        print("  No verdict changes between old and new gates.")
        print()


if __name__ == "__main__":
    main()
