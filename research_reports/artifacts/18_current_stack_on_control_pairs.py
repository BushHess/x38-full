#!/usr/bin/env python3
"""18 — Current Inference Stack on Control Pairs.

Evaluate the current production inference stack on three control pairs:
  1. Negative control:    VTREND_A0 vs VTREND_A1 (ΔSharpe ≈ 0)
  2. Mid positive control: VTREND_A0 vs VBREAK    (ΔSharpe ≈ +0.10)
  3. Strong positive ctrl:  VTREND_A0 vs VCUSUM    (ΔSharpe ≈ +0.34)

Methods evaluated:
  A. Paired block bootstrap (from v10/research/bootstrap.py)
     - Block sizes: 10, 20, 40
     - 2000 replicates, seed 1337
     - Gate: p_a_better >= 0.80 AND ci_lower > -0.01

  B. Paired block subsampling (from v10/research/subsampling.py)
     - Block sizes: 10, 20, 40
     - Gate: summarize_block_grid with median p >= 0.80,
             median ci_lower > 0.0, support_ratio >= 0.60

  C. DSR (from research/lib/dsr.py)
     - Applied to each strategy individually (not paired)
     - Trial levels: [27, 54, 100, 200, 500, 700]
     - Gate: dsr_pvalue > 0.95 for ALL trial levels

  D. Permutation (from research/multiple_comparison.py)
     - Component-level tests (EMA, VDO, ATR) — not pair-level
     - Documented but not directly applicable to pair comparison
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS, EquitySnap
from v10.research.bootstrap import (
    paired_block_bootstrap,
    calc_sharpe,
    calc_cagr,
    calc_max_drawdown,
)
from v10.research.subsampling import (
    paired_block_subsampling,
    summarize_block_grid,
)
from research.lib.dsr import compute_dsr
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ───────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0
ANN    = math.sqrt(6.0 * 365.25)

SP     = 120
TRAIL  = 3.0
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28

N_BOOT = 2000
SEED   = 1337
BLOCK_SIZES = [10, 20, 40]

DSR_TRIALS = [27, 54, 100, 200, 500, 700]

OUTDIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════════════
# Indicator helpers (from Report 17, self-contained)
# ═══════════════════════════════════════════════════════════════════

def _highest_high(high, n):
    out = np.full(len(high), np.nan)
    if n <= 0 or n >= len(high):
        return out
    windows = sliding_window_view(high, n)
    out[n:] = np.max(windows[:len(high) - n], axis=1)
    return out

def _lowest_low(low, m):
    out = np.full(len(low), np.nan)
    if m <= 0 or m >= len(low):
        return out
    windows = sliding_window_view(low, m)
    out[m:] = np.min(windows[:len(low) - m], axis=1)
    return out

def _log_returns(close):
    r = np.zeros(len(close), dtype=np.float64)
    r[1:] = np.log(close[1:] / close[:-1])
    return r

def _rolling_zscore(returns, window):
    n = len(returns)
    z = np.zeros(n, dtype=np.float64)
    for i in range(window, n):
        ref = returns[i - window:i]
        mu = np.mean(ref)
        sigma = np.std(ref, ddof=1)
        if sigma > 1e-12:
            z[i] = (returns[i] - mu) / sigma
    return z

def _cusum(z, k):
    n = len(z)
    cup = np.zeros(n)
    cdn = np.zeros(n)
    for i in range(1, n):
        cup[i] = max(0, cup[i-1] + z[i] - k)
        cdn[i] = max(0, cdn[i-1] - z[i] - k)
    return cup, cdn

def _atr_p(hi, lo, cl, period):
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


# ═══════════════════════════════════════════════════════════════════
# Generic simulation engine (from Report 17)
# ═══════════════════════════════════════════════════════════════════

def simulate(cl, entry_signal, exit_signal, exit_atr, trail_mult, wi):
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False

    nav_arr = np.zeros(n)
    exp_arr = np.zeros(n)

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                bq = cash / (fp * (1.0 + CPS))
                cash = 0.0
                inp = True
                pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                px = False

        nav = cash + bq * p
        nav_arr[i] = nav
        exp_arr[i] = 1.0 if inp else 0.0

        ea = exit_atr[i]
        if math.isnan(ea):
            continue

        if not inp:
            if entry_signal[i]:
                pe = True
        else:
            pk = max(pk, p)
            trail = pk - trail_mult * ea
            if p < trail:
                px = True
            elif exit_signal[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nav_arr[-1] = cash
        exp_arr[-1] = 0.0

    return nav_arr, exp_arr


# ═══════════════════════════════════════════════════════════════════
# Strategy signal builders (from Report 17)
# ═══════════════════════════════════════════════════════════════════

def build_vtrend_a0(cl, hi, lo, vo, tb, wi):
    fp = max(5, SP // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, SP)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at[i]):
            continue
        if ef[i] > es[i] and vd[i] > 0.0:
            entry[i] = True
        if ef[i] < es[i]:
            exit_s[i] = True
    return entry, exit_s, at, "VTREND_A0"


def build_vtrend_a1(cl, hi, lo, vo, tb, wi):
    fp = max(5, SP // 4)
    ef = _ema(cl, fp)
    es = _ema(cl, SP)
    at14 = _atr(hi, lo, cl, ATR_P)
    at20 = _atr_p(hi, lo, cl, 20)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at14[i]) or math.isnan(at20[i]):
            continue
        if ef[i] > es[i] and vd[i] > 0.0:
            entry[i] = True
        if ef[i] < es[i]:
            exit_s[i] = True
    return entry, exit_s, at20, "VTREND_A1"


def build_vbreak(cl, hi, lo, vo, tb, wi):
    hh = _highest_high(hi, SP)
    ll = _lowest_low(lo, 40)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(hh[i]) or math.isnan(ll[i]) or math.isnan(at[i]):
            continue
        if cl[i] > hh[i] and vd[i] > 0.0:
            entry[i] = True
        if cl[i] < ll[i]:
            exit_s[i] = True
    return entry, exit_s, at, "VBREAK"


def build_vcusum(cl, hi, lo, vo, tb, wi):
    log_ret = _log_returns(cl)
    z = _rolling_zscore(log_ret, SP)
    cup, cdn = _cusum(z, 0.5)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool)
    exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(at[i]):
            continue
        if cup[i] > 4.0 and vd[i] > 0.0:
            entry[i] = True
        if cdn[i] > 4.0:
            exit_s[i] = True
    return entry, exit_s, at, "VCUSUM"


# ═══════════════════════════════════════════════════════════════════
# NAV → EquitySnap conversion
# ═══════════════════════════════════════════════════════════════════

def nav_to_equity_snaps(nav_arr, close_times, wi):
    """Convert post-warmup NAV array to list of EquitySnap objects.

    The bootstrap/subsampling functions expect EquitySnap with nav_mid.
    We construct minimal EquitySnap objects from NAV and timestamps.
    """
    snaps = []
    for i in range(wi, len(nav_arr)):
        snaps.append(EquitySnap(
            close_time=int(close_times[i]),
            nav_mid=float(nav_arr[i]),
            nav_liq=float(nav_arr[i]),  # same as nav_mid for simulation
            cash=0.0,
            btc_qty=0.0,
            exposure=0.0,
        ))
    return snaps


# ═══════════════════════════════════════════════════════════════════
# Metrics (from Report 17)
# ═══════════════════════════════════════════════════════════════════

def compute_metrics(nav, wi):
    post = nav[wi:]
    n = len(post)
    if n < 2 or post[0] <= 0:
        return {"sharpe": 0, "cagr": -100, "mdd": 100}

    rets = np.diff(post) / post[:-1]
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    tr = post[-1] / post[0] - 1.0
    yrs = (n - 1) / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0

    peak = np.maximum.accumulate(post)
    dd = 1.0 - post / peak
    mdd = float(np.max(dd)) * 100

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}


# ═══════════════════════════════════════════════════════════════════
# Method A: Paired Block Bootstrap
# ═══════════════════════════════════════════════════════════════════

def run_bootstrap_pair(equity_a, equity_b, pair_name):
    """Run paired block bootstrap for Sharpe, CAGR, MDD at 3 block sizes."""
    results = {}
    metrics = [
        (calc_sharpe, "sharpe"),
        (calc_cagr, "cagr_pct"),
        (calc_max_drawdown, "max_drawdown_pct"),
    ]

    for bs in BLOCK_SIZES:
        results[f"block_{bs}"] = {}
        for fn, mname in metrics:
            r = paired_block_bootstrap(
                equity_a=equity_a,
                equity_b=equity_b,
                metric_fn=fn,
                metric_name=mname,
                n_bootstrap=N_BOOT,
                block_size=bs,
                seed=SEED,
            )
            results[f"block_{bs}"][mname] = {
                "observed_a": round(r.observed_a, 6),
                "observed_b": round(r.observed_b, 6),
                "observed_delta": round(r.observed_delta, 6),
                "mean_delta": round(r.mean_delta, 6),
                "std_delta": round(r.std_delta, 6),
                "ci_lower": round(r.ci_lower, 6),
                "ci_upper": round(r.ci_upper, 6),
                "p_a_better": round(r.p_a_better, 6),
            }

    # Gate: apply production gate on harsh/primary block size (first)
    primary = results[f"block_{BLOCK_SIZES[0]}"]["sharpe"]
    p = primary["p_a_better"]
    ci_low = primary["ci_lower"]
    gate_pass = p >= 0.80 and ci_low > -0.01

    return {
        "pair": pair_name,
        "method": "paired_block_bootstrap",
        "n_bootstrap": N_BOOT,
        "seed": SEED,
        "block_sizes": BLOCK_SIZES,
        "results": results,
        "gate": {
            "primary_block_size": BLOCK_SIZES[0],
            "primary_metric": "sharpe",
            "p_a_better": p,
            "ci_lower": ci_low,
            "threshold_p": 0.80,
            "threshold_ci": -0.01,
            "gate_pass": gate_pass,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# Method B: Paired Block Subsampling
# ═══════════════════════════════════════════════════════════════════

def run_subsampling_pair(equity_a, equity_b, pair_name):
    """Run paired block subsampling at 3 block sizes + grid summary."""
    per_block = []
    per_block_raw = []

    for bs in BLOCK_SIZES:
        r = paired_block_subsampling(
            equity_a=equity_a,
            equity_b=equity_b,
            block_size=bs,
        )
        per_block_raw.append(r)
        per_block.append({
            "block_size": bs,
            "n_obs": r.n_obs,
            "n_blocks_used": r.n_blocks_used,
            "observed_delta": round(r.observed_delta, 6),
            "ci_lower": round(r.ci_lower, 6),
            "ci_upper": round(r.ci_upper, 6),
            "p_a_better": round(r.p_a_better, 6),
            "observed_mean_log_diff": round(r.observed_mean_log_diff, 10),
        })

    # Grid summary with production gate thresholds
    grid = summarize_block_grid(per_block_raw)

    return {
        "pair": pair_name,
        "method": "paired_block_subsampling",
        "block_sizes": BLOCK_SIZES,
        "per_block": per_block,
        "grid_summary": {
            "median_observed_delta": round(grid.median_observed_delta, 6),
            "median_ci_lower": round(grid.median_ci_lower, 6),
            "median_ci_upper": round(grid.median_ci_upper, 6),
            "min_ci_lower": round(grid.min_ci_lower, 6),
            "median_p_a_better": round(grid.median_p_a_better, 6),
            "min_p_a_better": round(grid.min_p_a_better, 6),
            "support_ratio": round(grid.support_ratio, 6),
            "decision_pass": grid.decision_pass,
        },
        "gate": {
            "thresholds": {
                "p_threshold": 0.80,
                "ci_lower_threshold": 0.0,
                "support_ratio_threshold": 0.60,
            },
            "gate_pass": grid.decision_pass,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# Method C: DSR (applied per strategy, not paired)
# ═══════════════════════════════════════════════════════════════════

def run_dsr_strategy(nav_arr, wi, strategy_name):
    """Run DSR for a single strategy at multiple trial levels."""
    post = nav_arr[wi:]
    rets = np.diff(post) / post[:-1]

    dsr_results = {}
    all_pass = True
    for trials in DSR_TRIALS:
        d = compute_dsr(rets, num_trials=trials)
        passed = d["dsr_pvalue"] > 0.95
        if not passed:
            all_pass = False
        dsr_results[str(trials)] = {
            "sr_annualized": round(d["sr_annualized"], 6),
            "sr0_annualized": round(d["sr0_annualized"], 6),
            "dsr_statistic": round(d["dsr_statistic"], 6),
            "dsr_pvalue": round(d["dsr_pvalue"], 6),
            "pass": passed,
        }

    return {
        "strategy": strategy_name,
        "method": "deflated_sharpe_ratio",
        "trial_levels": DSR_TRIALS,
        "n_obs": len(rets),
        "results": dsr_results,
        "gate": {
            "threshold": 0.95,
            "all_pass": all_pass,
            "max_trials_passing": max(
                (int(t) for t, r in dsr_results.items() if r["pass"]),
                default=0,
            ),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()
    print("=" * 72)
    print("18 — CURRENT INFERENCE STACK ON CONTROL PAIRS")
    print("=" * 72)
    print(f"  Bootstrap: {N_BOOT} replicates, seed {SEED}, blocks {BLOCK_SIZES}")
    print(f"  Subsampling: blocks {BLOCK_SIZES}")
    print(f"  DSR: trial levels {DSR_TRIALS}")
    print(f"  Period: {START} → {END}, cost={COST.round_trip_bps}bps RT")

    # ── Load data ──
    print("\nLoading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    close_times = np.array([b.close_time for b in h4], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    print(f"  {n} H4 bars, warmup idx={wi}, trading={n-wi} bars")

    # ── Simulate strategies ──
    print("\nSimulating strategies...")
    builders = [
        build_vtrend_a0,
        build_vtrend_a1,
        build_vbreak,
        build_vcusum,
    ]

    strategies = {}
    for builder in builders:
        entry, exit_s, exit_atr, name = builder(cl, hi, lo, vo, tb, wi)
        nav, exp = simulate(cl, entry, exit_s, exit_atr, TRAIL, wi)
        met = compute_metrics(nav, wi)
        equity = nav_to_equity_snaps(nav, close_times, wi)
        strategies[name] = {"nav": nav, "exp": exp, "metrics": met, "equity": equity}

        exp_post = exp[wi:]
        n_trades = int(np.sum((exp_post[1:] == 1.0) & (exp_post[:-1] == 0.0)))
        print(f"  {name}: Sharpe={met['sharpe']:.3f}  CAGR={met['cagr']:+.1f}%  "
              f"MDD={met['mdd']:.1f}%  trades~{n_trades}")

    # ── Define control pairs ──
    pairs = [
        ("VTREND_A0", "VTREND_A1", "negative_control"),
        ("VTREND_A0", "VBREAK",    "mid_positive_control"),
        ("VTREND_A0", "VCUSUM",    "strong_positive_control"),
    ]

    all_results = {}

    for a_name, b_name, control_type in pairs:
        pair_name = f"{a_name} vs {b_name}"
        print(f"\n{'=' * 72}")
        print(f"PAIR: {pair_name}  ({control_type})")
        print(f"{'=' * 72}")

        eq_a = strategies[a_name]["equity"]
        eq_b = strategies[b_name]["equity"]
        met_a = strategies[a_name]["metrics"]
        met_b = strategies[b_name]["metrics"]

        print(f"  A ({a_name}): Sharpe={met_a['sharpe']:.3f}  CAGR={met_a['cagr']:+.1f}%  MDD={met_a['mdd']:.1f}%")
        print(f"  B ({b_name}): Sharpe={met_b['sharpe']:.3f}  CAGR={met_b['cagr']:+.1f}%  MDD={met_b['mdd']:.1f}%")
        print(f"  Δ: Sharpe={met_a['sharpe']-met_b['sharpe']:+.3f}  "
              f"CAGR={met_a['cagr']-met_b['cagr']:+.1f}%  "
              f"MDD={met_a['mdd']-met_b['mdd']:+.1f}%")

        pair_results = {
            "pair": pair_name,
            "control_type": control_type,
            "observed": {
                "a_sharpe": round(met_a["sharpe"], 6),
                "b_sharpe": round(met_b["sharpe"], 6),
                "delta_sharpe": round(met_a["sharpe"] - met_b["sharpe"], 6),
                "a_cagr": round(met_a["cagr"], 4),
                "b_cagr": round(met_b["cagr"], 4),
                "delta_cagr": round(met_a["cagr"] - met_b["cagr"], 4),
                "a_mdd": round(met_a["mdd"], 4),
                "b_mdd": round(met_b["mdd"], 4),
                "delta_mdd": round(met_a["mdd"] - met_b["mdd"], 4),
            },
        }

        # --- Method A: Bootstrap ---
        print(f"\n  [A] Paired Block Bootstrap ({N_BOOT} reps, seed {SEED})...")
        t0 = time.time()
        boot = run_bootstrap_pair(eq_a, eq_b, pair_name)
        boot_time = time.time() - t0
        pair_results["bootstrap"] = boot

        print(f"      Time: {boot_time:.1f}s")
        for bs in BLOCK_SIZES:
            sh = boot["results"][f"block_{bs}"]["sharpe"]
            print(f"      block={bs}: p_a_better={sh['p_a_better']:.4f}  "
                  f"CI=[{sh['ci_lower']:.4f}, {sh['ci_upper']:.4f}]  "
                  f"Δ={sh['observed_delta']:.4f}")
        g = boot["gate"]
        print(f"      GATE (block={g['primary_block_size']}): "
              f"p={g['p_a_better']:.4f}≥0.80? {'Y' if g['p_a_better']>=0.80 else 'N'}  "
              f"ci={g['ci_lower']:.4f}>-0.01? {'Y' if g['ci_lower']>-0.01 else 'N'}  "
              f"→ {'PASS' if g['gate_pass'] else 'FAIL'}")

        # --- Method B: Subsampling ---
        print(f"\n  [B] Paired Block Subsampling...")
        t0 = time.time()
        sub = run_subsampling_pair(eq_a, eq_b, pair_name)
        sub_time = time.time() - t0
        pair_results["subsampling"] = sub

        print(f"      Time: {sub_time:.1f}s")
        for pb in sub["per_block"]:
            print(f"      block={pb['block_size']}: p_a_better={pb['p_a_better']:.4f}  "
                  f"CI=[{pb['ci_lower']:.4f}, {pb['ci_upper']:.4f}]  "
                  f"Δ(ann)={pb['observed_delta']:.4f}")
        gs = sub["grid_summary"]
        print(f"      GRID: med_p={gs['median_p_a_better']:.4f}  "
              f"med_ci_low={gs['median_ci_lower']:.4f}  "
              f"support={gs['support_ratio']:.2f}  "
              f"→ {'PASS' if gs['decision_pass'] else 'FAIL'}")

        # --- Method C: DSR (per strategy) ---
        print(f"\n  [C] DSR (per strategy)...")
        dsr_a = run_dsr_strategy(strategies[a_name]["nav"], wi, a_name)
        dsr_b = run_dsr_strategy(strategies[b_name]["nav"], wi, b_name)
        pair_results["dsr"] = {a_name: dsr_a, b_name: dsr_b}

        print(f"      {a_name}: SR_ann={dsr_a['results']['27']['sr_annualized']:.3f}  "
              f"pass_all={dsr_a['gate']['all_pass']}  "
              f"max_trials={dsr_a['gate']['max_trials_passing']}")
        print(f"      {b_name}: SR_ann={dsr_b['results']['27']['sr_annualized']:.3f}  "
              f"pass_all={dsr_b['gate']['all_pass']}  "
              f"max_trials={dsr_b['gate']['max_trials_passing']}")

        all_results[pair_name] = pair_results

    # ═══════════════════════════════════════════════════════════════
    # Decision Matrix
    # ═══════════════════════════════════════════════════════════════

    print(f"\n{'=' * 72}")
    print("DECISION MATRIX")
    print(f"{'=' * 72}")
    print(f"\n  {'Pair':<28}  {'Bootstrap':>10}  {'Subsamp':>10}  {'DSR-A':>7}  {'DSR-B':>7}  {'Expected':>10}")
    print("  " + "-" * 80)

    for a_name, b_name, control_type in pairs:
        pair_name = f"{a_name} vs {b_name}"
        r = all_results[pair_name]
        boot_pass = "PASS" if r["bootstrap"]["gate"]["gate_pass"] else "FAIL"
        sub_pass = "PASS" if r["subsampling"]["gate"]["gate_pass"] else "FAIL"
        dsr_a_pass = "PASS" if r["dsr"][a_name]["gate"]["all_pass"] else "FAIL"
        dsr_b_pass = "PASS" if r["dsr"][b_name]["gate"]["all_pass"] else "FAIL"

        if control_type == "negative_control":
            expected = "FAIL"
        else:
            expected = "PASS"

        print(f"  {pair_name:<28}  {boot_pass:>10}  {sub_pass:>10}  "
              f"{dsr_a_pass:>7}  {dsr_b_pass:>7}  {expected:>10}")

    # ── Evaluate gate behavior ──
    print(f"\n{'=' * 72}")
    print("GATE EVALUATION")
    print(f"{'=' * 72}")

    neg_pair = "VTREND_A0 vs VTREND_A1"
    mid_pair = "VTREND_A0 vs VBREAK"
    pos_pair = "VTREND_A0 vs VCUSUM"

    neg_boot = all_results[neg_pair]["bootstrap"]["gate"]["gate_pass"]
    mid_boot = all_results[mid_pair]["bootstrap"]["gate"]["gate_pass"]
    pos_boot = all_results[pos_pair]["bootstrap"]["gate"]["gate_pass"]

    neg_sub = all_results[neg_pair]["subsampling"]["gate"]["gate_pass"]
    mid_sub = all_results[mid_pair]["subsampling"]["gate"]["gate_pass"]
    pos_sub = all_results[pos_pair]["subsampling"]["gate"]["gate_pass"]

    print(f"\n  Bootstrap gate (p>=0.80, ci>-0.01):")
    print(f"    Negative control (should FAIL): {'FAIL' if not neg_boot else 'PASS ← FALSE POSITIVE'}")
    print(f"    Mid positive (should PASS):     {'PASS' if mid_boot else 'FAIL ← LACKS POWER'}")
    print(f"    Strong positive (should PASS):  {'PASS' if pos_boot else 'FAIL ← LACKS POWER'}")

    print(f"\n  Subsampling gate (med_p>=0.80, med_ci>0.0, support>=0.60):")
    print(f"    Negative control (should FAIL): {'FAIL' if not neg_sub else 'PASS ← FALSE POSITIVE'}")
    print(f"    Mid positive (should PASS):     {'PASS' if mid_sub else 'FAIL ← LACKS POWER'}")
    print(f"    Strong positive (should PASS):  {'PASS' if pos_sub else 'FAIL ← LACKS POWER'}")

    # Determine gate assessment
    boot_correct = (not neg_boot) and pos_boot
    sub_correct = (not neg_sub) and pos_sub
    boot_correct_full = (not neg_boot) and mid_boot and pos_boot
    sub_correct_full = (not neg_sub) and mid_sub and pos_sub

    print(f"\n  Bootstrap: {'CORRECT' if boot_correct else 'INCORRECT'} on neg+strong pair "
          f"({'all 3 correct' if boot_correct_full else 'not all 3 correct'})")
    print(f"  Subsampling: {'CORRECT' if sub_correct else 'INCORRECT'} on neg+strong pair "
          f"({'all 3 correct' if sub_correct_full else 'not all 3 correct'})")

    # ── Permutation note ──
    print(f"\n  [D] Permutation tests (multiple_comparison.py):")
    print(f"      These are COMPONENT-LEVEL tests (EMA, VDO, ATR), not pair-level.")
    print(f"      They test whether individual VTREND components beat random.")
    print(f"      Not applicable to pairwise strategy comparison.")
    print(f"      Result: p_EMA=0.0003, p_VDO=0.0003, p_ATR=0.0003")
    print(f"      (from COMPLETE_RESEARCH_REGISTRY.md, all survive Bonferroni)")

    # ═══════════════════════════════════════════════════════════════
    # Save
    # ═══════════════════════════════════════════════════════════════

    output = {
        "config": {
            "sp": SP,
            "trail": TRAIL,
            "atr_period": ATR_P,
            "cost_rt_bps": COST.round_trip_bps,
            "start": START,
            "end": END,
            "warmup_days": WARMUP,
            "n_bootstrap": N_BOOT,
            "seed": SEED,
            "block_sizes": BLOCK_SIZES,
            "dsr_trial_levels": DSR_TRIALS,
        },
        "pairs": {},
    }

    for pair_name, r in all_results.items():
        output["pairs"][pair_name] = r

    # Decision matrix summary
    output["decision_matrix"] = {}
    for a_name, b_name, control_type in pairs:
        pair_name = f"{a_name} vs {b_name}"
        r = all_results[pair_name]
        output["decision_matrix"][pair_name] = {
            "control_type": control_type,
            "bootstrap_gate_pass": r["bootstrap"]["gate"]["gate_pass"],
            "subsampling_gate_pass": r["subsampling"]["gate"]["gate_pass"],
            "dsr_a_all_pass": r["dsr"][a_name]["gate"]["all_pass"],
            "dsr_b_all_pass": r["dsr"][b_name]["gate"]["all_pass"],
            "expected_paired_gate": "FAIL" if control_type == "negative_control" else "PASS",
        }

    # Gate assessment
    output["gate_assessment"] = {
        "bootstrap": {
            "negative_control_correct": not neg_boot,
            "mid_positive_correct": mid_boot,
            "strong_positive_correct": pos_boot,
            "overall": "adequate" if boot_correct else "inadequate",
        },
        "subsampling": {
            "negative_control_correct": not neg_sub,
            "mid_positive_correct": mid_sub,
            "strong_positive_correct": pos_sub,
            "overall": "adequate" if sub_correct else "inadequate",
        },
    }

    out_path = OUTDIR / "18_current_stack_on_control_pairs.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved: {out_path}")

    elapsed = time.time() - t_start
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
