#!/usr/bin/env python3
"""Selection Bias Analysis: CSCV/PBO + Deflated Sharpe Ratio.

With 30+ configs tested and 1 selected, there's a risk the improvement
is purely due to selection bias (multiple testing). This script quantifies
that risk via two methods:

1. CSCV/PBO (Bailey et al. 2017):
   - Split data into S=10 blocks (WFO windows)
   - Form C(10,5) = 252 symmetric train/test combinations
   - For each: optimize on train, rank selected config on test
   - PBO = P(selected config ranks below median on test)

2. Deflated Sharpe Ratio (Bailey & López de Prado 2014):
   - Adjust observed Sharpe for number of trials (N≥28)
   - Account for return skewness and kurtosis

Strategy universe: 27 V11 grid configs + V10 baseline = 28 total.
"""

import csv
import json
import itertools
import math
import sys
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.wfo import generate_windows
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
OUTDIR = Path("out_v11_validation_stepwise")
SCENARIO = "harsh"

# Grid (same as B2)
AGGRESSION_VALS = [0.85, 0.90, 0.95]
TRAIL_VALS = [2.7, 3.0, 3.3]
CAP_VALS = [0.75, 0.90, 0.95]


# ── Score without rejection ──────────────────────────────────────────────

def compute_score_no_reject(summary: dict) -> float:
    """Same formula as compute_objective but without <10 trades rejection."""
    cagr = summary.get("cagr_pct", 0.0)
    max_dd = summary.get("max_drawdown_mid_pct", 0.0)
    sharpe = summary.get("sharpe") or 0.0
    pf = summary.get("profit_factor", 0.0) or 0.0
    if isinstance(pf, str):
        pf = 3.0
    n_trades = summary.get("trades", 0)
    score = (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
        + min(n_trades / 50.0, 1.0) * 5.0
    )
    return score


# ── Strategy factories ───────────────────────────────────────────────────

def make_v10():
    return V8ApexStrategy(V8ApexConfig())


def make_v11(aggr, trail, cap):
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = aggr
    cfg.cycle_late_trail_mult = trail
    cfg.cycle_late_max_exposure = cap
    return V11HybridStrategy(cfg)


# ── Build config universe ────────────────────────────────────────────────

def build_configs():
    """Return list of (label, factory) tuples."""
    configs = [("V10_baseline", lambda: make_v10())]
    for aggr in AGGRESSION_VALS:
        for trail in TRAIL_VALS:
            for cap in CAP_VALS:
                label = f"V11_{aggr:.2f}_{trail:.1f}_{cap:.2f}"
                # Capture loop vars
                configs.append((label, (lambda a, t, c: lambda: make_v11(a, t, c))(aggr, trail, cap)))
    return configs


# ── Run backtest on a window ─────────────────────────────────────────────

def run_window(factory, test_start, test_end):
    cost = SCENARIOS[SCENARIO]
    strategy = factory()
    feed = DataFeed(DATA_PATH, start=test_start, end=test_end,
                    warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result


def run_full(factory):
    cost = SCENARIOS[SCENARIO]
    strategy = factory()
    feed = DataFeed(DATA_PATH, start=START, end=END,
                    warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result


# ── CSCV / PBO ───────────────────────────────────────────────────────────

def cscv_pbo(perf_matrix):
    """Combinatorially Symmetric Cross-Validation.

    perf_matrix: (n_configs, n_blocks) array

    For each C(S, S/2) combination of train/test split:
      - Select best config on train (average performance across train blocks)
      - Check its rank on test
      - PBO = fraction where test rank is below median

    Returns (pbo, logit_distribution, oos_rank_distribution)
    """
    n_configs, n_blocks = perf_matrix.shape
    half = n_blocks // 2
    combos = list(itertools.combinations(range(n_blocks), half))

    oos_ranks = []
    logits = []  # log(rank_oos / (n_configs - rank_oos))

    for train_idx in combos:
        test_idx = tuple(i for i in range(n_blocks) if i not in train_idx)

        # In-sample: average across train blocks
        is_perf = perf_matrix[:, list(train_idx)].mean(axis=1)
        # Out-of-sample: average across test blocks
        oos_perf = perf_matrix[:, list(test_idx)].mean(axis=1)

        # Best IS config
        best_is = int(np.argmax(is_perf))

        # Rank of best-IS in OOS (1 = best, n = worst)
        oos_rank = int((oos_perf > oos_perf[best_is]).sum()) + 1
        oos_ranks.append(oos_rank)

        # Logit: log(rank / (N+1-rank))
        if oos_rank < n_configs:
            logit = math.log(oos_rank / max(n_configs - oos_rank, 1))
        else:
            logit = 5.0  # cap for worst rank
        logits.append(logit)

    pbo = sum(1 for r in oos_ranks if r > n_configs / 2) / len(oos_ranks)

    return pbo, logits, oos_ranks


# ── Deflated Sharpe Ratio ────────────────────────────────────────────────

def deflated_sharpe(sr_observed, n_trials, T, skew, kurt):
    """Deflated Sharpe Ratio (Bailey & López de Prado 2014).

    Parameters:
        sr_observed: annualized Sharpe of selected strategy
        n_trials: number of strategies tried
        T: number of independent return observations
        skew: skewness of returns
        kurt: excess kurtosis of returns

    Returns: (dsr_pvalue, e_max_sr, sr_std)
    """
    gamma_em = 0.5772156649  # Euler-Mascheroni

    # Variance of Sharpe ratio estimator
    sr_var = (1.0 - skew * sr_observed
              + (kurt - 1.0) / 4.0 * sr_observed ** 2) / T
    sr_std = math.sqrt(max(sr_var, 1e-12))

    # Expected maximum Sharpe under null (N iid trials, true SR=0)
    if n_trials <= 1:
        e_max_sr = 0.0
    else:
        # Approximation: E[Z_(N)] for standard normal
        from scipy.stats import norm
        z1 = norm.ppf(1.0 - 1.0 / n_trials)
        z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
        e_max_z = (1.0 - gamma_em) * z1 + gamma_em * z2
        e_max_sr = sr_std * e_max_z

    # DSR: P(SR > 0 | adjustment for multiple testing)
    z_score = (sr_observed - e_max_sr) / sr_std
    from scipy.stats import norm as norm_dist
    dsr = norm_dist.cdf(z_score)

    return dsr, e_max_sr, sr_std


def compute_daily_returns(equity):
    """Extract daily log returns from equity curve."""
    navs = [e.nav_mid for e in equity]
    if len(navs) < 2:
        return np.array([0.0])
    navs = np.array(navs)
    # Sample to daily (take every ~6th point for H4 data)
    # Actually, equity has one point per H4 bar. Sample daily.
    times = [e.close_time for e in equity]
    # Group by day
    daily_navs = []
    current_day = None
    for i, t in enumerate(times):
        day = t // (86400 * 1000)  # ms to days
        if day != current_day:
            daily_navs.append(navs[i])
            current_day = day
    if len(daily_navs) < 2:
        return np.array([0.0])
    daily_navs = np.array(daily_navs)
    returns = np.diff(np.log(daily_navs))
    return returns


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  SELECTION BIAS ANALYSIS: CSCV/PBO + Deflated Sharpe")
    print("=" * 70)

    configs = build_configs()
    N = len(configs)
    print(f"  Strategy universe: {N} configs ({N-1} V11 grid + V10 baseline)")
    print(f"  Scenario: {SCENARIO}")
    print()

    # ── Phase 1: Build performance matrix (N configs × 10 windows) ─────
    windows = generate_windows(START, END, train_months=24, test_months=6,
                               slide_months=6)
    S = len(windows)
    print(f"  Blocks: {S} WFO windows (6-month each)")
    print(f"  CSCV combinations: C({S},{S//2}) = {math.comb(S, S//2)}")
    print(f"  Backtests needed: {N} × {S} = {N * S}")
    print()

    # Performance matrices
    perf_score = np.zeros((N, S))
    perf_return = np.zeros((N, S))

    total = N * S
    done = 0
    for ci, (label, factory) in enumerate(configs):
        for wi, w in enumerate(windows):
            result = run_window(factory, w.test_start, w.test_end)
            s = result.summary
            perf_score[ci, wi] = compute_score_no_reject(s)
            perf_return[ci, wi] = s.get("total_return_pct", 0.0)
            done += 1

        # Progress
        pct = done / total * 100
        avg_s = perf_score[ci].mean()
        print(f"  [{done:3d}/{total}] {pct:5.1f}%  {label:30s}  "
              f"avg_score_nr={avg_s:+.2f}")

    print(f"\n  Performance matrix: ({N}, {S}) built.\n")

    # ── Identify the "selected" config ────────────────────────────────
    # The WFO-optimal config is (0.95, 2.8, 0.90)
    # But 2.8 is NOT in our grid. Closest: (0.95, 3.0, 0.90) = grid index?
    # Actually, our grid has trail=2.7, 3.0, 3.3. The WFO-optimal trail=2.8
    # is between 2.7 and 3.0. For this analysis, we use the grid universe.
    # The "selected" config = the one with highest full-period score.
    full_period_scores = perf_score.sum(axis=1)  # proxy for full-period performance
    selected_idx = int(np.argmax(full_period_scores))
    selected_label = configs[selected_idx][0]
    print(f"  Selected config (best sum-of-blocks): {selected_label}")
    print(f"  Sum score: {full_period_scores[selected_idx]:+.2f}")
    print(f"  V10 baseline sum: {full_period_scores[0]:+.2f}")

    # ── Phase 2: CSCV/PBO ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  CSCV / PBO ANALYSIS")
    print("=" * 70)

    # Using score_no_reject
    pbo_score, logits_score, ranks_score = cscv_pbo(perf_score)

    print(f"\n  Metric: score_no_reject")
    print(f"  PBO = {pbo_score:.4f} ({pbo_score*100:.1f}%)")
    print(f"  Interpretation: {pbo_score*100:.0f}% chance the IS-optimal config")
    print(f"    ranks below median OOS (across {math.comb(S, S//2)} combinations)")

    rank_hist_score = np.bincount(ranks_score, minlength=N + 1)[1:]
    print(f"  OOS rank distribution of IS-optimal:")
    print(f"    Best (rank 1-7):   {sum(rank_hist_score[:7])}/{len(ranks_score)}")
    print(f"    Mid  (rank 8-21):  {sum(rank_hist_score[7:21])}/{len(ranks_score)}")
    print(f"    Worst(rank 22-28): {sum(rank_hist_score[21:])}/{len(ranks_score)}")
    mean_rank = np.mean(ranks_score)
    median_rank = np.median(ranks_score)
    print(f"    Mean rank:   {mean_rank:.1f} / {N}")
    print(f"    Median rank: {median_rank:.1f} / {N}")

    # Using total_return_pct
    pbo_return, logits_return, ranks_return = cscv_pbo(perf_return)
    print(f"\n  Metric: total_return_pct")
    print(f"  PBO = {pbo_return:.4f} ({pbo_return*100:.1f}%)")
    rank_hist_ret = np.bincount(ranks_return, minlength=N + 1)[1:]
    mean_rank_ret = np.mean(ranks_return)
    print(f"    Mean rank: {mean_rank_ret:.1f} / {N}")

    # ── Phase 3: Deflated Sharpe Ratio ───────────────────────────────────
    print("\n" + "=" * 70)
    print("  DEFLATED SHARPE RATIO")
    print("=" * 70)

    # Run full-period backtest for the selected config to get daily returns
    print("  Running full-period backtest for return distribution...")
    result_selected = run_full(configs[selected_idx][1])
    daily_rets = compute_daily_returns(result_selected.equity)
    T = len(daily_rets)
    sr_obs = result_selected.summary.get("sharpe") or 0.0
    skew = float(np.nan_to_num(
        np.mean(((daily_rets - daily_rets.mean()) / max(daily_rets.std(), 1e-12)) ** 3)
    ))
    kurt = float(np.nan_to_num(
        np.mean(((daily_rets - daily_rets.mean()) / max(daily_rets.std(), 1e-12)) ** 4)
    ))

    print(f"  Selected config: {selected_label}")
    print(f"  Observed Sharpe (annualized): {sr_obs:.4f}")
    print(f"  Daily return observations (T): {T}")
    print(f"  Return skewness: {skew:.4f}")
    print(f"  Return kurtosis: {kurt:.4f}")
    print(f"  Number of trials (N): {N}")

    try:
        dsr, e_max_sr, sr_std = deflated_sharpe(sr_obs, N, T, skew, kurt)
        print(f"\n  E[max(SR)] under null (N={N} trials): {e_max_sr:.4f}")
        print(f"  SE(SR): {sr_std:.4f}")
        print(f"  Deflated Sharpe p-value: {dsr:.4f}")
        print(f"  Interpretation: {'PASS (DSR > 0.95)' if dsr > 0.95 else 'FAIL (DSR <= 0.95)'}")
        dsr_result = {
            "sr_observed": round(sr_obs, 4),
            "n_trials": N,
            "T_observations": T,
            "skewness": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "e_max_sr_null": round(e_max_sr, 4),
            "se_sr": round(sr_std, 4),
            "dsr_pvalue": round(dsr, 4),
            "dsr_pass": dsr > 0.95,
        }
    except ImportError:
        print("\n  scipy not available — using manual approximation")
        # Manual approximation without scipy
        gamma_em = 0.5772156649
        sr_var = (1.0 - skew * sr_obs + (kurt - 1.0) / 4.0 * sr_obs ** 2) / T
        sr_std = math.sqrt(max(sr_var, 1e-12))

        # Approximation for Φ^(-1)(p) using rational approximation
        def probit(p):
            """Approximate inverse normal CDF."""
            if p <= 0 or p >= 1:
                return 0.0
            t = math.sqrt(-2.0 * math.log(min(p, 1 - p)))
            c0, c1, c2 = 2.515517, 0.802853, 0.010328
            d1, d2, d3 = 1.432788, 0.189269, 0.001308
            val = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
            return val if p > 0.5 else -val

        def norm_cdf(z):
            return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

        z1 = probit(1.0 - 1.0 / N)
        z2 = probit(1.0 - 1.0 / (N * math.e))
        e_max_z = (1.0 - gamma_em) * z1 + gamma_em * z2
        e_max_sr = sr_std * e_max_z

        z_score = (sr_obs - e_max_sr) / sr_std if sr_std > 0 else 0
        dsr = norm_cdf(z_score)

        print(f"  E[max(SR)] under null: {e_max_sr:.4f}")
        print(f"  SE(SR): {sr_std:.4f}")
        print(f"  DSR z-score: {z_score:.4f}")
        print(f"  DSR p-value: {dsr:.4f}")
        print(f"  Interpretation: {'PASS (DSR > 0.95)' if dsr > 0.95 else 'FAIL (DSR <= 0.95)'}")
        dsr_result = {
            "sr_observed": round(sr_obs, 4),
            "n_trials": N,
            "T_observations": T,
            "skewness": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "e_max_sr_null": round(e_max_sr, 4),
            "se_sr": round(sr_std, 4),
            "dsr_pvalue": round(dsr, 4),
            "dsr_pass": dsr > 0.95,
            "note": "manual approximation (scipy unavailable)",
        }

    # ── Also check: what if N=30 (actual number of trials)? ──────────
    print(f"\n  Sensitivity to N:")
    for n_try in [28, 30, 40, 50]:
        try:
            d, e, _ = deflated_sharpe(sr_obs, n_try, T, skew, kurt)
        except ImportError:
            z1t = probit(1.0 - 1.0 / n_try)
            z2t = probit(1.0 - 1.0 / (n_try * math.e))
            e_max_zt = (1.0 - gamma_em) * z1t + gamma_em * z2t
            e_t = sr_std * e_max_zt
            z_t = (sr_obs - e_t) / sr_std if sr_std > 0 else 0
            d = norm_cdf(z_t)
            e = e_t
        print(f"    N={n_try:3d}: E[max(SR)]={e:.4f}  DSR={d:.4f}")

    # ── Verdict ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  COMBINED VERDICT")
    print("=" * 70)

    if pbo_score < 0.50 and dsr_result["dsr_pass"]:
        verdict = "PASS — low overfitting risk"
    elif pbo_score < 0.50:
        verdict = "MARGINAL — PBO acceptable but DSR fails"
    elif pbo_score >= 0.50 and not dsr_result["dsr_pass"]:
        verdict = "FAIL — high overfitting risk (both PBO and DSR)"
    else:
        verdict = "FAIL — PBO indicates overfitting"

    print(f"  PBO (score_no_reject): {pbo_score:.2%}")
    print(f"  PBO (return):          {pbo_return:.2%}")
    print(f"  DSR p-value:           {dsr_result['dsr_pvalue']:.4f}")
    print(f"  VERDICT: {verdict}")
    print("=" * 70)

    # ── Save JSON ────────────────────────────────────────────────────────
    def _c(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: _c(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_c(v) for v in obj]
        return obj

    json_data = {
        "description": "Selection bias analysis: CSCV/PBO + Deflated Sharpe",
        "n_configs": N,
        "n_blocks": S,
        "n_cscv_combinations": math.comb(S, S // 2),
        "scenario": SCENARIO,
        "selected_config": selected_label,
        "cscv_pbo": {
            "score_no_reject": {
                "pbo": round(pbo_score, 4),
                "mean_oos_rank": round(float(mean_rank), 2),
                "median_oos_rank": round(float(median_rank), 2),
                "rank_histogram": rank_hist_score.tolist(),
                "logit_mean": round(float(np.mean(logits_score)), 4),
                "logit_std": round(float(np.std(logits_score)), 4),
            },
            "total_return_pct": {
                "pbo": round(pbo_return, 4),
                "mean_oos_rank": round(float(mean_rank_ret), 2),
            },
        },
        "deflated_sharpe": dsr_result,
        "perf_matrix_score": perf_score.tolist(),
        "perf_matrix_return": perf_return.tolist(),
        "config_labels": [c[0] for c in configs],
        "window_labels": [f"{w.test_start}_{w.test_end}" for w in windows],
        "verdict": verdict,
    }

    json_path = OUTDIR / "selection_bias_results.json"
    with open(json_path, "w") as f:
        json.dump(_c(json_data), f, indent=2)
    print(f"\n  Saved: {json_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
