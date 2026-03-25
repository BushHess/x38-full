#!/usr/bin/env python3
"""
07 — Exact Series Tail Sanity
==============================
Recompute diagnostics on the EXACT series each inference method consumes:

  Bootstrap:    individual simple-pct returns per strategy
                  returns = diff(nav) / nav[:-1]
                Resampled jointly with same block indices.
                Metric delta = metric(resample_A) - metric(resample_B).
                *** Does NOT form a bar-level return differential. ***

  Subsampling:  differential log-return series
                  log_a = log(nav_a[1:] / nav_a[:-1])
                  log_b = log(nav_b[1:] / nav_b[:-1])
                  diff  = log_a - log_b
                Overlapping block means of diff.

Canonical config (from out/validate/v12_vs_v10/2026-02-24/run_meta.json):
  start=2019-01-01, end=2026-02-20, warmup=365d, cash=10000, harsh=50bps
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, EquitySnap

# Strategy imports
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from strategies.v12_emdd_ref_fix.strategy import (
    V12EMDDRefFixConfig,
    V12EMDDRefFixStrategy,
)

# ── Canonical config ──────────────────────────────────────────────────
DATA_PATH = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
COST = SCENARIOS["harsh"]

OUT_DIR = ROOT / "research_reports" / "artifacts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HILL_FRACS = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20]


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: Reproduce equity curves
# ═══════════════════════════════════════════════════════════════════════

def run_backtest(strategy, label: str) -> list[EquitySnap]:
    feed = DataFeed(path=str(DATA_PATH), start=START, end=END,
                    warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=COST,
                            initial_cash=INITIAL_CASH,
                            warmup_days=WARMUP_DAYS)
    result = engine.run()
    s = result.summary
    print(f"  {label:20s}: Sharpe={s.get('sharpe', 0):.4f}  "
          f"CAGR={s.get('cagr_pct', 0):.2f}%  "
          f"MDD={s.get('max_drawdown_mid_pct', 0):.2f}%  "
          f"trades={s.get('trades', 0)}")
    return result.equity


def make_candidate():
    cfg = V12EMDDRefFixConfig()
    cfg.emdd_ref_mode = "fixed"
    cfg.emergency_dd_pct = 0.04
    cfg.rsi_method = "wilder"
    cfg.entry_cooldown_bars = 3
    return V12EMDDRefFixStrategy(cfg)


def make_baseline():
    cfg = V8ApexConfig()
    cfg.emergency_ref = "pre_cost_legacy"
    cfg.rsi_method = "wilder"
    cfg.entry_cooldown_bars = 3
    return V8ApexStrategy(cfg)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: Exact series as consumed by each method
# ═══════════════════════════════════════════════════════════════════════

def bootstrap_series(equity: list[EquitySnap]) -> np.ndarray:
    """Exact series bootstrap consumes: simple pct returns.

    Source: v10/research/bootstrap.py lines 106-107:
        navs = np.array([e.nav_mid for e in equity], dtype=np.float64)
        returns = np.diff(navs) / navs[:-1]
    """
    navs = np.array([e.nav_mid for e in equity], dtype=np.float64)
    return np.diff(navs) / navs[:-1]


def subsampling_log_diff(equity_a: list[EquitySnap],
                         equity_b: list[EquitySnap]) -> np.ndarray:
    """Exact series subsampling consumes: differential log-return.

    Source: v10/research/subsampling.py lines 129-133, 180-182:
        log_a = log(navs_a[1:] / navs_a[:-1])
        log_b = log(navs_b[1:] / navs_b[:-1])
        diff = log_a - log_b
    """
    navs_a = np.array([e.nav_mid for e in equity_a], dtype=np.float64)
    navs_b = np.array([e.nav_mid for e in equity_b], dtype=np.float64)
    log_a = np.log(navs_a[1:] / navs_a[:-1])
    log_b = np.log(navs_b[1:] / navs_b[:-1])
    return log_a - log_b


def simple_diff(ret_a: np.ndarray, ret_b: np.ndarray) -> np.ndarray:
    """Simple pct-return differential (not used by either method, but
    this is what report 06 analyzed)."""
    return ret_a - ret_b


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: Hill tail index — multi-threshold sensitivity
# ═══════════════════════════════════════════════════════════════════════

def hill_estimator(x: np.ndarray, k: int) -> float:
    """Hill tail index estimator using top-k order statistics of |x|.

    Parameters
    ----------
    x : array of observations (can be positive or negative)
    k : number of upper order statistics to use

    Returns
    -------
    alpha : estimated tail index. P(|X| > t) ~ t^{-alpha}.
            Higher alpha = thinner tails.

    Notes
    -----
    The Hill estimator is:
        alpha_hat = [ (1/k) * sum_{i=1}^{k} log(X_{(n-i+1)} / X_{(n-k)}) ]^{-1}

    where X_{(1)} <= ... <= X_{(n)} are the order statistics.

    It assumes a Pareto-like upper tail. It is applied to |x| to
    capture both tails jointly.
    """
    absvals = np.sort(np.abs(x))[::-1]  # descending
    if k < 2 or k >= len(absvals):
        return float("nan")
    top_k = absvals[:k]
    threshold = absvals[k]  # the (k+1)-th largest
    if threshold <= 0:
        return float("nan")
    log_ratios = np.log(top_k / threshold)
    mean_log = np.mean(log_ratios)
    if mean_log <= 0:
        return float("nan")
    return 1.0 / mean_log


def hill_sensitivity(x: np.ndarray, fracs: list[float]) -> list[dict]:
    """Hill estimator at multiple tail fractions."""
    n = len(x)
    results = []
    for frac in fracs:
        k = max(2, int(n * frac))
        alpha = hill_estimator(x, k)
        results.append({
            "frac": frac,
            "k": k,
            "alpha": float(alpha) if not math.isnan(alpha) else None,
        })
    return results


def hill_upper_lower(x: np.ndarray, fracs: list[float]) -> dict:
    """Hill estimator on upper tail (positive) and lower tail (negative)
    separately, plus combined |x|."""
    pos = x[x > 0]
    neg = -x[x < 0]  # flip sign so we're looking at magnitudes
    return {
        "combined_abs": hill_sensitivity(x, fracs),
        "upper_tail_only": hill_sensitivity(pos, fracs) if len(pos) > 10 else [],
        "lower_tail_only": hill_sensitivity(neg, fracs) if len(neg) > 10 else [],
        "n_positive": int(len(pos)),
        "n_negative": int(len(neg)),
        "n_zero": int(np.sum(x == 0)),
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: Standard diagnostics
# ═══════════════════════════════════════════════════════════════════════

def acf(x: np.ndarray, max_lag: int = 10) -> list[float]:
    n = len(x)
    mu = np.mean(x)
    var = np.var(x, ddof=0)
    if var == 0:
        return [0.0] * max_lag
    result = []
    for lag in range(1, max_lag + 1):
        cov = np.mean((x[:n - lag] - mu) * (x[lag:] - mu))
        result.append(round(float(cov / var), 6))
    return result


def summary_stats(x: np.ndarray, label: str) -> dict:
    n = len(x)
    mu = float(np.mean(x))
    sigma = float(np.std(x, ddof=0))
    skew = 0.0
    kurt = 0.0
    if sigma > 0:
        z = (x - mu) / sigma
        skew = float(np.mean(z ** 3))
        kurt = float(np.mean(z ** 4) - 3.0)
    return {
        "label": label,
        "n": n,
        "mean": mu,
        "std": sigma,
        "skewness": skew,
        "excess_kurtosis": kurt,
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "pct_1": float(np.percentile(x, 1)),
        "pct_5": float(np.percentile(x, 5)),
        "median": float(np.median(x)),
        "pct_95": float(np.percentile(x, 95)),
        "pct_99": float(np.percentile(x, 99)),
        "n_zero": int(np.sum(x == 0.0)),
        "frac_zero": float(np.mean(x == 0.0)),
        "acf_returns_lag1_5": acf(x, 5),
        "acf_squared_lag1_5": acf(x ** 2, 5),
        "acf_abs_lag1_5": acf(np.abs(x), 5),
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("07 — EXACT SERIES TAIL SANITY")
    print("=" * 72)
    print(f"  Config: {START} → {END}, warmup={WARMUP_DAYS}d, "
          f"harsh={COST.round_trip_bps:.0f}bps, cash=${INITIAL_CASH:,.0f}")
    print()

    # ── 1. Reproduce equity curves ────────────────────────────────────
    print("Reproducing equity curves...")
    eq_cand = run_backtest(make_candidate(), "v12_emdd_ref_fix")
    eq_base = run_backtest(make_baseline(), "v8_apex_baseline")
    print()

    # ── 2. Extract the EXACT series each method consumes ──────────────
    # Bootstrap input: individual simple pct returns
    ret_cand = bootstrap_series(eq_cand)    # candidate simple returns
    ret_base = bootstrap_series(eq_base)    # baseline simple returns

    # Subsampling input: differential log-return
    log_diff = subsampling_log_diff(eq_cand, eq_base)

    # Also compute: simple differential (what report 06 analyzed — NOT
    # used by either method, computed here only for comparison)
    simp_diff = simple_diff(ret_cand, ret_base)

    # Also compute: individual log returns (for completeness)
    navs_c = np.array([e.nav_mid for e in eq_cand], dtype=np.float64)
    navs_b = np.array([e.nav_mid for e in eq_base], dtype=np.float64)
    log_cand = np.log(navs_c[1:] / navs_c[:-1])
    log_base = np.log(navs_b[1:] / navs_b[:-1])

    print(f"Series lengths: returns={len(ret_cand)}, log_diff={len(log_diff)}")
    print()

    # ── 3. Summary statistics ─────────────────────────────────────────
    series_map = {
        "candidate_simple_ret": ret_cand,
        "baseline_simple_ret": ret_base,
        "candidate_log_ret": log_cand,
        "baseline_log_ret": log_base,
        "simple_differential": simp_diff,
        "log_differential": log_diff,
    }

    stats = {}
    for name, arr in series_map.items():
        stats[name] = summary_stats(arr, name)

    # ── 4. Hill sensitivity at multiple thresholds ────────────────────
    print("Computing Hill sensitivity...")
    hill = {}
    for name, arr in series_map.items():
        hill[name] = hill_upper_lower(arr, HILL_FRACS)

    # ── 5. Print results ──────────────────────────────────────────────
    print()
    print("=" * 72)
    print("SUMMARY STATISTICS")
    print("=" * 72)
    hdr = f"{'Series':28s} {'Mean':>12s} {'Std':>12s} {'Skew':>8s} {'Kurt':>10s} {'%Zero':>8s}"
    print(hdr)
    print("-" * len(hdr))
    for name, s in stats.items():
        print(f"{name:28s} {s['mean']:12.8f} {s['std']:12.8f} "
              f"{s['skewness']:8.3f} {s['excess_kurtosis']:10.3f} "
              f"{s['frac_zero']*100:7.2f}%")

    print()
    print("=" * 72)
    print("HILL TAIL INDEX SENSITIVITY — COMBINED |x|")
    print("=" * 72)
    print(f"{'Series':28s}", end="")
    for frac in HILL_FRACS:
        print(f"  {frac*100:5.1f}%", end="")
    print()
    print("-" * (28 + 8 * len(HILL_FRACS)))
    for name in series_map:
        h = hill[name]["combined_abs"]
        print(f"{name:28s}", end="")
        for entry in h:
            a = entry["alpha"]
            if a is not None:
                print(f"  {a:5.2f}", end="")
            else:
                print(f"    NaN", end="")
        print()

    print()
    print("=" * 72)
    print("HILL TAIL INDEX — UPPER vs LOWER TAILS (at 5% threshold)")
    print("=" * 72)
    for name in series_map:
        h = hill[name]
        # Find 5% entry
        up5 = next((e for e in h["upper_tail_only"] if e["frac"] == 0.05), None)
        lo5 = next((e for e in h["lower_tail_only"] if e["frac"] == 0.05), None)
        co5 = next((e for e in h["combined_abs"] if e["frac"] == 0.05), None)
        ua = up5["alpha"] if up5 and up5["alpha"] else float("nan")
        la = lo5["alpha"] if lo5 and lo5["alpha"] else float("nan")
        ca = co5["alpha"] if co5 and co5["alpha"] else float("nan")
        print(f"  {name:28s}: upper={ua:6.2f}  lower={la:6.2f}  "
              f"combined={ca:6.2f}  n+={h['n_positive']}  n-={h['n_negative']}  "
              f"n0={h['n_zero']}")

    print()
    print("=" * 72)
    print("ACF STRUCTURE (lag 1)")
    print("=" * 72)
    for name, s in stats.items():
        r1 = s["acf_returns_lag1_5"][0]
        s1 = s["acf_squared_lag1_5"][0]
        a1 = s["acf_abs_lag1_5"][0]
        print(f"  {name:28s}: ret={r1:+.4f}  sq={s1:+.4f}  abs={a1:+.4f}")

    # ── 6. Save bar-level CSV ─────────────────────────────────────────
    print()
    print("Saving bar-level CSV...")
    csv_path = OUT_DIR / "07_bar_level_paired_returns.csv"
    with open(csv_path, "w") as f:
        f.write("close_time,candidate_simple_ret,baseline_simple_ret,"
                "candidate_log_ret,baseline_log_ret,"
                "simple_differential,log_differential,"
                "candidate_exposure,baseline_exposure\n")
        for i in range(len(ret_cand)):
            ts = eq_cand[i + 1].close_time  # return[i] is from snap[i] to snap[i+1]
            exp_c = eq_cand[i + 1].exposure
            exp_b = eq_base[i + 1].exposure
            f.write(f"{ts},{ret_cand[i]:.12f},{ret_base[i]:.12f},"
                    f"{log_cand[i]:.12f},{log_base[i]:.12f},"
                    f"{simp_diff[i]:.12f},{log_diff[i]:.12f},"
                    f"{exp_c:.6f},{exp_b:.6f}\n")
    print(f"  Saved: {csv_path}")

    # ── 7. Build JSON artifact ────────────────────────────────────────
    result = {
        "meta": {
            "script": "07_exact_series_tail_sanity.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "start": START,
            "end": END,
            "warmup_days": WARMUP_DAYS,
            "cost_rt_bps": COST.round_trip_bps,
            "initial_cash": INITIAL_CASH,
            "hill_fracs": HILL_FRACS,
        },
        "series_definitions": {
            "candidate_simple_ret": {
                "method_consumer": "bootstrap (paired_block_bootstrap)",
                "formula": "diff(nav_cand) / nav_cand[:-1]",
                "source_file": "v10/research/bootstrap.py",
                "source_lines": "106-107",
            },
            "baseline_simple_ret": {
                "method_consumer": "bootstrap (paired_block_bootstrap)",
                "formula": "diff(nav_base) / nav_base[:-1]",
                "source_file": "v10/research/bootstrap.py",
                "source_lines": "106-107",
            },
            "log_differential": {
                "method_consumer": "subsampling (paired_block_subsampling)",
                "formula": "log(nav_a[1:]/nav_a[:-1]) - log(nav_b[1:]/nav_b[:-1])",
                "source_file": "v10/research/subsampling.py",
                "source_lines": "129-133, 180-182",
            },
            "simple_differential": {
                "method_consumer": "NONE — not used by any inference method",
                "formula": "simple_ret_cand - simple_ret_base",
                "note": "Analyzed by report 06, but neither bootstrap nor subsampling uses this series",
            },
        },
        "summary_stats": stats,
        "hill_sensitivity": hill,
    }

    json_path = OUT_DIR / "07_exact_series_tail_sanity.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  Saved: {json_path}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
