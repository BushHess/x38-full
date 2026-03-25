#!/usr/bin/env python3
"""
07b — Reconciliation
=====================
Recompute all metrics directly from the bar-level CSV produced by report 07.
Compare with the JSON artifact. Identify and explain every discrepancy.
Measure "identical decisions" precisely. Reconcile all prior claims.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
ART = ROOT / "research_reports" / "artifacts"

CSV_PATH = ART / "07_bar_level_paired_returns.csv"
JSON_PATH = ART / "07_exact_series_tail_sanity.json"

HILL_FRACS = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20]


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: Load CSV and JSON
# ═══════════════════════════════════════════════════════════════════════

def load_csv():
    """Load bar-level CSV into dict of numpy arrays."""
    data = {
        "close_time": [],
        "candidate_simple_ret": [],
        "baseline_simple_ret": [],
        "candidate_log_ret": [],
        "baseline_log_ret": [],
        "simple_differential": [],
        "log_differential": [],
        "candidate_exposure": [],
        "baseline_exposure": [],
    }
    with open(CSV_PATH) as f:
        header = f.readline().strip().split(",")
        for line in f:
            vals = line.strip().split(",")
            for col, val in zip(header, vals):
                data[col].append(float(val))
    return {k: np.array(v) for k, v in data.items()}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: Zero-counting and consistency checks
# ═══════════════════════════════════════════════════════════════════════

def zero_analysis(csv):
    """Detailed zero analysis on all six return series."""
    series_names = [
        "candidate_simple_ret", "baseline_simple_ret",
        "candidate_log_ret", "baseline_log_ret",
        "simple_differential", "log_differential",
    ]
    results = {}
    for name in series_names:
        arr = csv[name]
        n = len(arr)
        n_zero = int(np.sum(arr == 0.0))
        # Also count near-zero (|x| < 1e-15) to catch CSV rounding
        n_near_zero = int(np.sum(np.abs(arr) < 1e-15))
        results[name] = {
            "n": n,
            "n_exact_zero": n_zero,
            "frac_exact_zero": n_zero / n,
            "n_near_zero_1e15": n_near_zero,
            "frac_near_zero_1e15": n_near_zero / n,
        }
    return results


def exposure_analysis(csv):
    """Analyze exposure equality and joint states."""
    exp_c = csv["candidate_exposure"]
    exp_b = csv["baseline_exposure"]
    n = len(exp_c)

    # Exact equality
    n_exp_equal = int(np.sum(exp_c == exp_b))

    # Joint states
    both_flat = (exp_c == 0.0) & (exp_b == 0.0)
    both_in_market = (exp_c > 0.0) & (exp_b > 0.0)
    cand_only = (exp_c > 0.0) & (exp_b == 0.0)
    base_only = (exp_c == 0.0) & (exp_b > 0.0)

    n_both_flat = int(np.sum(both_flat))
    n_both_market = int(np.sum(both_in_market))
    n_cand_only = int(np.sum(cand_only))
    n_base_only = int(np.sum(base_only))

    # When both are in market, are exposures identical?
    if n_both_market > 0:
        market_mask = both_in_market
        n_market_exp_equal = int(np.sum(exp_c[market_mask] == exp_b[market_mask]))
        # Close to equal (within 1%)
        n_market_exp_close = int(np.sum(
            np.abs(exp_c[market_mask] - exp_b[market_mask]) < 0.01
        ))
    else:
        n_market_exp_equal = 0
        n_market_exp_close = 0

    return {
        "n_bars": n,
        "n_exposure_exactly_equal": n_exp_equal,
        "frac_exposure_exactly_equal": n_exp_equal / n,
        "n_both_flat": n_both_flat,
        "frac_both_flat": n_both_flat / n,
        "n_both_in_market": n_both_market,
        "frac_both_in_market": n_both_market / n,
        "n_candidate_only_in_market": n_cand_only,
        "n_baseline_only_in_market": n_base_only,
        "n_disagree_direction": n_cand_only + n_base_only,
        "frac_disagree_direction": (n_cand_only + n_base_only) / n,
        "frac_agree_direction": (n_both_flat + n_both_market) / n,
        "n_both_market_exposure_identical": n_market_exp_equal,
        "n_both_market_exposure_close_1pct": n_market_exp_close,
    }


def identical_decisions_analysis(csv):
    """Measure 'identical decisions' precisely with multiple definitions."""
    exp_c = csv["candidate_exposure"]
    exp_b = csv["baseline_exposure"]
    ret_c = csv["candidate_simple_ret"]
    ret_b = csv["baseline_simple_ret"]
    n = len(exp_c)

    # Definition 1: Same direction (both flat or both in market)
    same_direction = ((exp_c == 0.0) & (exp_b == 0.0)) | ((exp_c > 0.0) & (exp_b > 0.0))
    n_same_dir = int(np.sum(same_direction))

    # Definition 2: Same direction AND returns within 0.1%
    close_returns = np.abs(ret_c - ret_b) < 0.001  # 10 bps
    n_same_dir_close = int(np.sum(same_direction & close_returns))

    # Definition 3: Exact zero differential
    n_zero_diff = int(np.sum(csv["simple_differential"] == 0.0))

    # Definition 4: Returns within 1 bps
    n_within_1bps = int(np.sum(np.abs(ret_c - ret_b) < 0.0001))

    # Definition 5: Both have exact same return (float equality)
    n_exact_same_return = int(np.sum(ret_c == ret_b))

    return {
        "n_bars": n,
        "def1_same_direction": {
            "count": n_same_dir,
            "frac": n_same_dir / n,
            "definition": "both flat OR both in market",
        },
        "def2_same_dir_and_close_returns": {
            "count": n_same_dir_close,
            "frac": n_same_dir_close / n,
            "definition": "same direction AND |ret_diff| < 10bps",
        },
        "def3_exact_zero_differential": {
            "count": n_zero_diff,
            "frac": n_zero_diff / n,
            "definition": "simple_differential == 0.0 (float exact)",
        },
        "def4_returns_within_1bps": {
            "count": n_within_1bps,
            "frac": n_within_1bps / n,
            "definition": "|candidate_ret - baseline_ret| < 0.0001",
        },
        "def5_exact_same_return": {
            "count": n_exact_same_return,
            "frac": n_exact_same_return / n,
            "definition": "candidate_ret == baseline_ret (float exact)",
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: Correlation
# ═══════════════════════════════════════════════════════════════════════

def correlation_analysis(csv):
    """Correlations between candidate and baseline."""
    ret_c = csv["candidate_simple_ret"]
    ret_b = csv["baseline_simple_ret"]
    log_c = csv["candidate_log_ret"]
    log_b = csv["baseline_log_ret"]

    # Full series correlation
    corr_simple = float(np.corrcoef(ret_c, ret_b)[0, 1])
    corr_log = float(np.corrcoef(log_c, log_b)[0, 1])

    # Correlation excluding bars where both are zero
    mask_nonzero = (ret_c != 0.0) | (ret_b != 0.0)
    n_nonzero = int(np.sum(mask_nonzero))
    if n_nonzero > 2:
        corr_simple_nonzero = float(np.corrcoef(
            ret_c[mask_nonzero], ret_b[mask_nonzero])[0, 1])
        corr_log_nonzero = float(np.corrcoef(
            log_c[mask_nonzero], log_b[mask_nonzero])[0, 1])
    else:
        corr_simple_nonzero = float("nan")
        corr_log_nonzero = float("nan")

    return {
        "corr_simple_full": corr_simple,
        "corr_log_full": corr_log,
        "n_nonzero_bars": n_nonzero,
        "corr_simple_nonzero_only": corr_simple_nonzero,
        "corr_log_nonzero_only": corr_log_nonzero,
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: Zero-count discrepancy investigation
# ═══════════════════════════════════════════════════════════════════════

def investigate_zero_discrepancy(csv):
    """Investigate why log_differential has more zeros than simple_differential."""
    simp_d = csv["simple_differential"]
    log_d = csv["log_differential"]

    simp_zero = (simp_d == 0.0)
    log_zero = (log_d == 0.0)

    n_both_zero = int(np.sum(simp_zero & log_zero))
    n_simp_zero_only = int(np.sum(simp_zero & ~log_zero))
    n_log_zero_only = int(np.sum(~simp_zero & log_zero))
    n_neither_zero = int(np.sum(~simp_zero & ~log_zero))

    # For bars where log is zero but simple is not: what are the simple values?
    log_zero_simp_not = ~simp_zero & log_zero
    if np.sum(log_zero_simp_not) > 0:
        simp_at_discrepancy = simp_d[log_zero_simp_not]
        disc_stats = {
            "count": int(np.sum(log_zero_simp_not)),
            "simple_vals_min": float(np.min(simp_at_discrepancy)),
            "simple_vals_max": float(np.max(simp_at_discrepancy)),
            "simple_vals_mean": float(np.mean(simp_at_discrepancy)),
            "simple_vals_absmax": float(np.max(np.abs(simp_at_discrepancy))),
            "simple_vals_abs_p50": float(np.median(np.abs(simp_at_discrepancy))),
            "simple_vals_abs_p99": float(np.percentile(np.abs(simp_at_discrepancy), 99)),
        }
    else:
        disc_stats = {"count": 0}

    # Also check: is this a CSV rounding issue?
    # CSV uses 12 decimal places. Values < 5e-13 round to 0.000000000000
    n_log_near_zero = int(np.sum(np.abs(log_d) < 5e-13))
    n_simp_near_zero = int(np.sum(np.abs(simp_d) < 5e-13))

    # What are the actual exposure states at these discrepant bars?
    exp_c = csv["candidate_exposure"]
    exp_b = csv["baseline_exposure"]
    if np.sum(log_zero_simp_not) > 0:
        disc_exp_c = exp_c[log_zero_simp_not]
        disc_exp_b = exp_b[log_zero_simp_not]
        both_flat_disc = int(np.sum((disc_exp_c == 0.0) & (disc_exp_b == 0.0)))
        both_market_disc = int(np.sum((disc_exp_c > 0.0) & (disc_exp_b > 0.0)))
        mixed_disc = int(np.sum(log_zero_simp_not)) - both_flat_disc - both_market_disc
    else:
        both_flat_disc = both_market_disc = mixed_disc = 0

    return {
        "n_both_zero": n_both_zero,
        "n_simple_zero_only": n_simp_zero_only,
        "n_log_zero_only": n_log_zero_only,
        "n_neither_zero": n_neither_zero,
        "discrepancy_log_zero_simp_not": disc_stats,
        "n_log_nearfloatzero_5e13": n_log_near_zero,
        "n_simp_nearfloatzero_5e13": n_simp_near_zero,
        "discrepancy_exposure_states": {
            "both_flat": both_flat_disc,
            "both_in_market": both_market_disc,
            "mixed": mixed_disc,
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: CSV vs JSON consistency
# ═══════════════════════════════════════════════════════════════════════

def csv_vs_json_consistency(csv, json_data):
    """Compare statistics computed from CSV with those in the JSON."""
    json_stats = json_data["summary_stats"]
    series_map = {
        "candidate_simple_ret": csv["candidate_simple_ret"],
        "baseline_simple_ret": csv["baseline_simple_ret"],
        "candidate_log_ret": csv["candidate_log_ret"],
        "baseline_log_ret": csv["baseline_log_ret"],
        "simple_differential": csv["simple_differential"],
        "log_differential": csv["log_differential"],
    }

    comparisons = {}
    for name, arr in series_map.items():
        js = json_stats[name]
        csv_mean = float(np.mean(arr))
        csv_std = float(np.std(arr, ddof=0))
        csv_n_zero = int(np.sum(arr == 0.0))
        csv_n = len(arr)
        z = (arr - csv_mean) / csv_std if csv_std > 0 else arr * 0
        csv_skew = float(np.mean(z ** 3)) if csv_std > 0 else 0.0
        csv_kurt = float(np.mean(z ** 4) - 3.0) if csv_std > 0 else 0.0

        comparisons[name] = {
            "json_n": js["n"],
            "csv_n": csv_n,
            "n_match": js["n"] == csv_n,
            "json_mean": js["mean"],
            "csv_mean": csv_mean,
            "mean_diff": abs(csv_mean - js["mean"]),
            "json_std": js["std"],
            "csv_std": csv_std,
            "std_diff": abs(csv_std - js["std"]),
            "json_n_zero": js["n_zero"],
            "csv_n_zero": csv_n_zero,
            "n_zero_match": js["n_zero"] == csv_n_zero,
            "json_skew": js["skewness"],
            "csv_skew": csv_skew,
            "skew_diff": abs(csv_skew - js["skewness"]),
            "json_kurt": js["excess_kurtosis"],
            "csv_kurt": csv_kurt,
            "kurt_diff": abs(csv_kurt - js["excess_kurtosis"]),
        }
    return comparisons


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: Hill sensitivity (from CSV)
# ═══════════════════════════════════════════════════════════════════════

def hill_estimator(x, k):
    absvals = np.sort(np.abs(x))[::-1]
    if k < 2 or k >= len(absvals):
        return float("nan")
    top_k = absvals[:k]
    threshold = absvals[k]
    if threshold <= 0:
        return float("nan")
    log_ratios = np.log(top_k / threshold)
    mean_log = np.mean(log_ratios)
    if mean_log <= 0:
        return float("nan")
    return 1.0 / mean_log


def hill_sensitivity(x, fracs):
    n = len(x)
    results = []
    for frac in fracs:
        k = max(2, int(n * frac))
        alpha = hill_estimator(x, k)
        results.append({"frac": frac, "k": k, "alpha": float(alpha)})
    return results


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("07b — RECONCILIATION")
    print("=" * 72)

    # Load data
    csv = load_csv()
    with open(JSON_PATH) as f:
        json_data = json.load(f)

    n = len(csv["close_time"])
    print(f"CSV rows: {n}")
    print()

    # ── 1. CSV vs JSON consistency ────────────────────────────────────
    print("=== CSV vs JSON CONSISTENCY ===")
    comp = csv_vs_json_consistency(csv, json_data)
    for name, c in comp.items():
        mean_ok = c["mean_diff"] < 1e-10
        std_ok = c["std_diff"] < 1e-10
        zero_ok = c["n_zero_match"]
        # Skew/kurt tolerance wider due to CSV's 12-digit truncation
        skew_ok = c["skew_diff"] < 0.1
        kurt_ok = c["kurt_diff"] < 5.0

        issues = []
        if not mean_ok:
            issues.append(f"mean_diff={c['mean_diff']:.2e}")
        if not std_ok:
            issues.append(f"std_diff={c['std_diff']:.2e}")
        if not zero_ok:
            issues.append(f"n_zero: json={c['json_n_zero']} csv={c['csv_n_zero']}")
        if not skew_ok:
            issues.append(f"skew_diff={c['skew_diff']:.4f}")
        if not kurt_ok:
            issues.append(f"kurt_diff={c['kurt_diff']:.4f}")

        status = "OK" if not issues else "MISMATCH"
        print(f"  {name:28s}: {status}", end="")
        if issues:
            print(f"  [{', '.join(issues)}]", end="")
        print()

    # ── 2. Zero analysis ──────────────────────────────────────────────
    print()
    print("=== ZERO ANALYSIS (from CSV) ===")
    zeros = zero_analysis(csv)
    for name, z in zeros.items():
        print(f"  {name:28s}: n_zero={z['n_exact_zero']:6d} ({z['frac_exact_zero']*100:6.2f}%)  "
              f"n_near_zero={z['n_near_zero_1e15']:6d} ({z['frac_near_zero_1e15']*100:6.2f}%)")

    # ── 3. Zero discrepancy investigation ─────────────────────────────
    print()
    print("=== ZERO DISCREPANCY: simple_diff vs log_diff ===")
    disc = investigate_zero_discrepancy(csv)
    print(f"  Both zero:       {disc['n_both_zero']:6d}")
    print(f"  Simple zero only:{disc['n_simple_zero_only']:6d}")
    print(f"  Log zero only:   {disc['n_log_zero_only']:6d}")
    print(f"  Neither zero:    {disc['n_neither_zero']:6d}")
    d = disc["discrepancy_log_zero_simp_not"]
    if d["count"] > 0:
        print(f"  Log-zero-but-simp-not: {d['count']} bars")
        print(f"    simple vals: min={d['simple_vals_min']:.2e}, max={d['simple_vals_max']:.2e}, "
              f"absmax={d['simple_vals_absmax']:.2e}, abs_p50={d['simple_vals_abs_p50']:.2e}")
        exp = disc["discrepancy_exposure_states"]
        print(f"    exposure: both_flat={exp['both_flat']}, both_market={exp['both_in_market']}, mixed={exp['mixed']}")

    # ── 4. Exposure analysis ──────────────────────────────────────────
    print()
    print("=== EXPOSURE ANALYSIS ===")
    ea = exposure_analysis(csv)
    print(f"  Both flat:           {ea['n_both_flat']:6d} ({ea['frac_both_flat']*100:.2f}%)")
    print(f"  Both in market:      {ea['n_both_in_market']:6d} ({ea['frac_both_in_market']*100:.2f}%)")
    print(f"  Candidate only:      {ea['n_candidate_only_in_market']:6d}")
    print(f"  Baseline only:       {ea['n_baseline_only_in_market']:6d}")
    print(f"  Disagree direction:  {ea['n_disagree_direction']:6d} ({ea['frac_disagree_direction']*100:.2f}%)")
    print(f"  Agree direction:     {ea['n_both_flat'] + ea['n_both_in_market']:6d} ({ea['frac_agree_direction']*100:.2f}%)")
    print(f"  Exposure exact equal:{ea['n_exposure_exactly_equal']:6d} ({ea['frac_exposure_exactly_equal']*100:.2f}%)")

    # ── 5. Identical decisions ────────────────────────────────────────
    print()
    print("=== IDENTICAL DECISIONS (multiple definitions) ===")
    idd = identical_decisions_analysis(csv)
    for key in ["def1_same_direction", "def2_same_dir_and_close_returns",
                "def3_exact_zero_differential", "def4_returns_within_1bps",
                "def5_exact_same_return"]:
        d = idd[key]
        print(f"  {key:40s}: {d['count']:6d} ({d['frac']*100:.2f}%)  — {d['definition']}")

    # ── 6. Correlations ───────────────────────────────────────────────
    print()
    print("=== CORRELATIONS ===")
    corr = correlation_analysis(csv)
    print(f"  Simple returns (full):       {corr['corr_simple_full']:.6f}")
    print(f"  Log returns (full):          {corr['corr_log_full']:.6f}")
    print(f"  Simple returns (nonzero):    {corr['corr_simple_nonzero_only']:.6f}")
    print(f"  Log returns (nonzero):       {corr['corr_log_nonzero_only']:.6f}")
    print(f"  N nonzero bars:              {corr['n_nonzero_bars']}")

    # ── 7. Hill sensitivity from CSV ──────────────────────────────────
    print()
    print("=== HILL SENSITIVITY (from CSV) ===")
    for series_name in ["simple_differential", "log_differential",
                        "candidate_simple_ret", "baseline_simple_ret"]:
        arr = csv[series_name]
        h = hill_sensitivity(arr, HILL_FRACS)
        print(f"  {series_name:28s}:", end="")
        for entry in h:
            a = entry["alpha"]
            if not math.isnan(a):
                print(f"  {a:5.2f}", end="")
            else:
                print(f"    NaN", end="")
        print()

    # ── 8. Build JSON artifact ────────────────────────────────────────
    result = {
        "meta": {
            "script": "07b_reconciliation.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "csv_source": str(CSV_PATH),
            "json_source": str(JSON_PATH),
        },
        "csv_vs_json": comp,
        "zero_analysis_from_csv": zeros,
        "zero_discrepancy": disc,
        "exposure_analysis": ea,
        "identical_decisions": idd,
        "correlations": corr,
        "hill_from_csv": {
            name: hill_sensitivity(csv[name], HILL_FRACS)
            for name in ["simple_differential", "log_differential",
                         "candidate_simple_ret", "baseline_simple_ret"]
        },
        "p_a_better_meaning": {
            "value": 0.6485,
            "source": "out/validate/v12_vs_v10/2026-02-24/results/bootstrap_summary.json",
            "computation": "float((deltas > 0).mean()) where deltas[i] = Sharpe(resampled_A[i]) - Sharpe(resampled_B[i])",
            "source_file": "v10/research/bootstrap.py",
            "source_line": 216,
            "metric": "sharpe",
            "scenario": "harsh",
            "block_size": 10,
            "n_bootstrap": 2000,
            "is_proper_p_value": False,
            "explanation": (
                "This is the fraction of 2000 bootstrap replicates where "
                "Sharpe(resampled_candidate) > Sharpe(resampled_baseline), "
                "using identical block indices for both curves. "
                "It is NOT a p-value in the hypothesis-testing sense. "
                "A proper bootstrap p-value would test H0: delta <= 0 using "
                "a centered or pivotal statistic. This is a heuristic "
                "probability estimate P(Sharpe_A > Sharpe_B | bootstrap distribution)."
            ),
            "gate_rule": "pass if p_a_better >= 0.80 AND ci_lower > -0.01 (source: validation/suites/bootstrap.py line 104)",
            "gate_is_calibrated": False,
            "gate_explanation": (
                "The 0.80 threshold was chosen heuristically, not derived from "
                "any formal Type-I error control or power analysis."
            ),
        },
    }

    json_out = ART / "07b_reconciliation.json"
    with open(json_out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved: {json_out}")
    print("Done.")


if __name__ == "__main__":
    main()
