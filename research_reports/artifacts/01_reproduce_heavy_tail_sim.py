#!/usr/bin/env python3
"""01_reproduce_heavy_tail_sim.py — Reproduce the heavy-tail coverage/TypeI/power claims.

This script reproduces the exact simulation that was originally run as inline
conversation code (Python heredoc in Bash tool calls) during the audit session.

ORIGINAL CLAIM
--------------
"With BTC-realistic heavy tails (Student-t df=3, kurtosis~24, Hill α≈2.88):
 - Both Bootstrap and Subsampling have ~95% coverage
 - Both have ~3-4% Type I error
 - Both have ~30% power for 5.6% annual edge"

PARAMETERS (exact match to the inline code)
-------------------------------------------
- Generator: Student-t df=3.0 innovations (NOT Gaussian, NOT GARCH)
- n_bars = 15000 (H4 bars, ~6.8 years)
- n_reps = 200 (Monte Carlo repetitions)
- vol = 0.0065 (per-bar volatility scale for Student-t)
- phi_vol = 0.15 (AR(1) coefficient for return mean-reversion)
- edge = 0.000025 (per-bar mean excess return for "edge" scenario)
- block_sizes = [10, 20, 40]
- n_bootstrap = 1000, seed_base = 42
- subsampling: ci_level = 0.95
- Population truth estimated from 30 long runs of 80000 bars each
- Seeds: candidate 1000+rep, baseline 5000+rep, H0 test 8000+rep/9000+rep

OUTPUT
------
- Console tables matching the original claimed format
- JSON artifacts for programmatic comparison

NOTE: This is a STANDALONE script — does NOT import any project code.
The bootstrap and subsampling are reimplemented inline to match the
exact algorithms in v10/research/bootstrap.py and v10/research/subsampling.py.
"""

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

BARS_PER_YEAR_4H = 2190.0
ARTIFACTS_DIR = Path(__file__).parent

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)


# ════════════════════════════════════════════════════════════════════════════
# Inline reimplementation of the two inference methods
# ════════════════════════════════════════════════════════════════════════════


def _calc_sharpe(returns: np.ndarray) -> float:
    """Annualized Sharpe from 4H returns (ddof=0, no risk-free).

    Matches v10/research/bootstrap.py:calc_sharpe exactly.
    """
    if len(returns) < 2:
        return 0.0
    mu = returns.mean()
    sigma = returns.std(ddof=0)
    if sigma < 1e-12:
        return 0.0
    return float(mu / sigma * math.sqrt(BARS_PER_YEAR_4H))


def paired_block_bootstrap_sharpe(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    n_bootstrap: int = 1000,
    block_size: int = 20,
    seed: int = 42,
) -> dict:
    """Paired circular block bootstrap for Sharpe difference.

    Matches v10/research/bootstrap.py:paired_block_bootstrap logic.
    Returns dict with ci_lower, ci_upper, p_a_better.
    """
    n = min(len(returns_a), len(returns_b))
    ra = returns_a[:n]
    rb = returns_b[:n]

    obs_a = _calc_sharpe(ra)
    obs_b = _calc_sharpe(rb)
    obs_delta = obs_a - obs_b

    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_size))
    deltas = np.empty(n_bootstrap)

    # Pre-build the block offset array once
    offsets = np.arange(block_size)

    for i in range(n_bootstrap):
        starts = rng.integers(0, n, size=n_blocks)
        indices = ((starts[:, None] + offsets[None, :]) % n).ravel()[:n]
        deltas[i] = _calc_sharpe(ra[indices]) - _calc_sharpe(rb[indices])

    return {
        "observed_delta": float(obs_delta),
        "ci_lower": float(np.percentile(deltas, 2.5)),
        "ci_upper": float(np.percentile(deltas, 97.5)),
        "p_a_better": float((deltas > 0).mean()),
    }


def paired_block_subsampling_growth(
    equity_a: np.ndarray,
    equity_b: np.ndarray,
    block_size: int = 20,
    ci_level: float = 0.95,
) -> dict:
    """Paired block subsampling for excess geometric growth.

    Matches v10/research/subsampling.py:paired_block_subsampling logic.
    Takes NAV arrays (not returns).
    """
    log_a = np.log(equity_a[1:] / equity_a[:-1])
    log_b = np.log(equity_b[1:] / equity_b[:-1])
    diff = log_a - log_b
    n = len(diff)

    full_mean = float(np.mean(diff))

    # Overlapping block means via cumsum
    csum = np.cumsum(np.insert(diff, 0, 0.0))
    sums = csum[block_size:] - csum[:-block_size]
    block_means = sums / float(block_size)

    root = np.sqrt(block_size) * (block_means - full_mean)
    alpha = 1.0 - ci_level
    q_low = float(np.quantile(root, alpha / 2.0))
    q_high = float(np.quantile(root, 1.0 - alpha / 2.0))
    sqrt_n = math.sqrt(n)

    mean_ci_lower = full_mean - q_high / sqrt_n
    mean_ci_upper = full_mean - q_low / sqrt_n

    # Annualize
    observed_delta = float(np.expm1(BARS_PER_YEAR_4H * full_mean))
    ci_lower = float(np.expm1(BARS_PER_YEAR_4H * mean_ci_lower))
    ci_upper = float(np.expm1(BARS_PER_YEAR_4H * mean_ci_upper))

    test_stat = sqrt_n * full_mean
    p_value = float(np.mean(root >= test_stat))
    p_a_better = float(max(0.0, min(1.0, 1.0 - p_value)))

    return {
        "observed_delta": observed_delta,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "p_a_better": p_a_better,
    }


# ════════════════════════════════════════════════════════════════════════════
# Data generators
# ════════════════════════════════════════════════════════════════════════════


def generate_student_t_equity(
    n_bars: int,
    vol: float,
    mean_excess: float,
    phi: float,
    df: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate equity curve with Student-t innovations (heavy tails).

    Returns (equity_navs, pct_returns).
    """
    rng = np.random.default_rng(seed)
    # Scale Student-t so marginal std = vol
    t_scale = vol * math.sqrt((df - 2) / df) if df > 2 else vol
    innovations = rng.standard_t(df, size=n_bars) * t_scale

    # AR(1) returns with drift
    returns = np.empty(n_bars)
    returns[0] = mean_excess + innovations[0]
    for i in range(1, n_bars):
        returns[i] = mean_excess + phi * (returns[i - 1] - mean_excess) + innovations[i]

    # Build equity curve (NAV)
    equity = np.empty(n_bars + 1)
    equity[0] = 10000.0
    equity[1:] = 10000.0 * np.cumprod(1.0 + returns)

    return equity, returns


# ════════════════════════════════════════════════════════════════════════════
# Main simulation
# ════════════════════════════════════════════════════════════════════════════


def run_simulation():
    # ── Parameters (exact match to inline code) ──
    n_bars = 15000
    n_reps = 200
    vol = 0.0065
    phi = 0.15
    df = 3.0
    edge = 0.000025  # per-bar excess return
    block_sizes = [10, 20, 40]
    n_bootstrap = 1000
    ci_level = 0.95

    print("=" * 72)
    print("HEAVY-TAIL SIMULATION REPRODUCTION")
    print("=" * 72)
    print(f"Generator:     Student-t(df={df})")
    print(f"n_bars:        {n_bars}")
    print(f"n_reps:        {n_reps}")
    print(f"vol:           {vol}")
    print(f"phi (AR1):     {phi}")
    print(f"edge:          {edge} per bar")
    print(f"block_sizes:   {block_sizes}")
    print(f"n_bootstrap:   {n_bootstrap}")
    print(f"ci_level:      {ci_level}")
    print()

    # ── Step 1: Estimate population truth (30 long runs) ──
    print("Step 1: Estimating population truth (30 x 80000 bars)...")
    t0 = time.time()
    pop_sharpe_diffs = []
    pop_growth_diffs = []
    for i in range(30):
        eq_a, ret_a = generate_student_t_equity(80000, vol, edge, phi, df, seed=100000 + i)
        eq_b, ret_b = generate_student_t_equity(80000, vol, 0.0, phi, df, seed=200000 + i)
        pop_sharpe_diffs.append(_calc_sharpe(ret_a) - _calc_sharpe(ret_b))
        log_diff = np.log(eq_a[1:] / eq_a[:-1]) - np.log(eq_b[1:] / eq_b[:-1])
        pop_growth_diffs.append(float(np.expm1(BARS_PER_YEAR_4H * np.mean(log_diff))))

    true_sharpe_diff = float(np.median(pop_sharpe_diffs))
    true_growth_diff = float(np.median(pop_growth_diffs))
    print(f"  True Sharpe diff (median of 30): {true_sharpe_diff:.4f}")
    print(f"  True Growth diff (median of 30): {true_growth_diff:.4f}")
    print(f"  (took {time.time() - t0:.1f}s)")
    print()

    # ── Step 2: Verify kurtosis/tail properties ──
    print("Step 2: Verifying tail properties...")
    sample_eq, sample_ret = generate_student_t_equity(n_bars, vol, 0.0, phi, df, seed=999)
    kurt = float(sp_stats.kurtosis(sample_ret, fisher=False))
    skew = float(sp_stats.skew(sample_ret))

    # Hill estimator for tail index
    abs_ret = np.abs(sample_ret)
    sorted_abs = np.sort(abs_ret)[::-1]
    k_hill = max(10, int(0.05 * len(sorted_abs)))
    log_ratios = np.log(sorted_abs[:k_hill] / sorted_abs[k_hill])
    hill_alpha = float(k_hill / np.sum(log_ratios)) if np.sum(log_ratios) > 0 else float("nan")

    print(f"  Sample kurtosis (Fisher=False): {kurt:.2f}")
    print(f"  Sample skewness:                {skew:.4f}")
    print(f"  Hill tail index alpha (k={k_hill}): {hill_alpha:.2f}")
    print()

    # ── Combined coverage + power test (reuse same data) ──
    # Coverage and power use the SAME data (H1: edge exists),
    # so we run them together in one pass to halve the compute.
    print("Step 3+5: Coverage + Power test (H1 scenario)...")
    t0 = time.time()

    coverage = {"bootstrap": {bs: 0 for bs in block_sizes},
                "subsampling": {bs: 0 for bs in block_sizes}}
    power = {"bootstrap": {bs: 0 for bs in block_sizes},
             "subsampling": {bs: 0 for bs in block_sizes}}

    for rep in range(n_reps):
        if (rep + 1) % 25 == 0:
            elapsed = time.time() - t0
            rate = (rep + 1) / elapsed
            eta = (n_reps - rep - 1) / rate
            print(f"  rep {rep+1}/{n_reps} ({elapsed:.0f}s elapsed, ETA {eta:.0f}s)")

        eq_a, ret_a = generate_student_t_equity(n_bars, vol, edge, phi, df, seed=1000 + rep)
        eq_b, ret_b = generate_student_t_equity(n_bars, vol, 0.0, phi, df, seed=5000 + rep)

        for bs in block_sizes:
            # Bootstrap
            boot = paired_block_bootstrap_sharpe(ret_a, ret_b, n_bootstrap, bs, seed=42)
            if boot["ci_lower"] <= true_sharpe_diff <= boot["ci_upper"]:
                coverage["bootstrap"][bs] += 1
            if boot["ci_lower"] > 0:
                power["bootstrap"][bs] += 1

            # Subsampling (much faster — no resampling loop)
            sub = paired_block_subsampling_growth(eq_a, eq_b, bs, ci_level)
            if sub["ci_lower"] <= true_growth_diff <= sub["ci_upper"]:
                coverage["subsampling"][bs] += 1
            if sub["ci_lower"] > 0:
                power["subsampling"][bs] += 1

    print(f"  (took {time.time() - t0:.1f}s)")
    print()

    print("COVERAGE TABLE (nominal 95%):")
    print(f"{'Block':<8} {'Bootstrap':>12} {'Subsampling':>12}")
    print("-" * 34)
    coverage_results = {}
    for bs in block_sizes:
        bc = coverage["bootstrap"][bs] / n_reps * 100
        sc = coverage["subsampling"][bs] / n_reps * 100
        print(f"{bs:<8} {bc:>11.1f}% {sc:>11.1f}%")
        coverage_results[str(bs)] = {"bootstrap": bc, "subsampling": sc}
    print()

    print("POWER TABLE (ability to detect edge):")
    print(f"{'Block':<8} {'Bootstrap':>12} {'Subsampling':>12}")
    print("-" * 34)
    power_results = {}
    for bs in block_sizes:
        bp = power["bootstrap"][bs] / n_reps * 100
        sp = power["subsampling"][bs] / n_reps * 100
        print(f"{bs:<8} {bp:>11.1f}% {sp:>11.1f}%")
        power_results[str(bs)] = {"bootstrap": bp, "subsampling": sp}
    print()

    # ── Step 4: Type I error test (H0: no edge) ──
    print("Step 4: Type I error test (H0: no edge)...")
    t0 = time.time()

    type1 = {"bootstrap": {bs: 0 for bs in block_sizes},
             "subsampling": {bs: 0 for bs in block_sizes}}

    for rep in range(n_reps):
        if (rep + 1) % 25 == 0:
            elapsed = time.time() - t0
            rate = (rep + 1) / elapsed
            eta = (n_reps - rep - 1) / rate
            print(f"  rep {rep+1}/{n_reps} ({elapsed:.0f}s elapsed, ETA {eta:.0f}s)")

        eq_a, ret_a = generate_student_t_equity(n_bars, vol, 0.0, phi, df, seed=8000 + rep)
        eq_b, ret_b = generate_student_t_equity(n_bars, vol, 0.0, phi, df, seed=9000 + rep)

        for bs in block_sizes:
            boot = paired_block_bootstrap_sharpe(ret_a, ret_b, n_bootstrap, bs, seed=42)
            if boot["ci_lower"] > 0:
                type1["bootstrap"][bs] += 1

            sub = paired_block_subsampling_growth(eq_a, eq_b, bs, ci_level)
            if sub["ci_lower"] > 0:
                type1["subsampling"][bs] += 1

    print(f"  (took {time.time() - t0:.1f}s)")
    print()

    print("TYPE I ERROR TABLE (nominal 5% or less):")
    print(f"{'Block':<8} {'Bootstrap':>12} {'Subsampling':>12}")
    print("-" * 34)
    type1_results = {}
    for bs in block_sizes:
        bt = type1["bootstrap"][bs] / n_reps * 100
        st = type1["subsampling"][bs] / n_reps * 100
        print(f"{bs:<8} {bt:>11.1f}% {st:>11.1f}%")
        type1_results[str(bs)] = {"bootstrap": bt, "subsampling": st}
    print()

    # ── Annualize the edge for context ──
    annual_edge = (1 + edge) ** BARS_PER_YEAR_4H - 1
    print(f"Edge per bar: {edge}")
    print(f"Annualized edge: {annual_edge*100:.1f}%")
    print()

    # ── Save JSON artifacts ──
    artifact = {
        "parameters": {
            "generator": f"Student-t(df={df})",
            "n_bars": n_bars,
            "n_reps": n_reps,
            "vol": vol,
            "phi_ar1": phi,
            "edge_per_bar": edge,
            "edge_annualized_pct": round(annual_edge * 100, 2),
            "block_sizes": block_sizes,
            "n_bootstrap": n_bootstrap,
            "ci_level": ci_level,
            "bootstrap_seed": 42,
            "pop_truth_n_runs": 30,
            "pop_truth_n_bars": 80000,
        },
        "tail_properties": {
            "kurtosis_fisher_false": round(kurt, 2),
            "skewness": round(skew, 4),
            "hill_alpha": round(hill_alpha, 2),
            "hill_k": k_hill,
        },
        "population_truth": {
            "true_sharpe_diff": round(true_sharpe_diff, 4),
            "true_growth_diff": round(true_growth_diff, 4),
        },
        "coverage_pct": coverage_results,
        "type1_error_pct": type1_results,
        "power_pct": power_results,
    }

    out_path = ARTIFACTS_DIR / "01_heavy_tail_sim_results.json"
    with open(out_path, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"Saved: {out_path}")

    return artifact


if __name__ == "__main__":
    run_simulation()
