#!/usr/bin/env python3
"""19 — Same-Statistic Control Pair Audit.

Report 18 compared bootstrap (Sharpe) vs subsampling (annualized excess
geometric growth) — DIFFERENT statistics.  This audit runs BOTH methods
on the SAME statistic to separate method-family behavior from statistic
choice.

Statistics tested:
  A. Per-bar mean log-return difference  (= subsampling's native statistic)
  B. Sharpe of paired pct-return difference  (bootstrap's native territory)

For statistic A, we create an audit-only metric_fn for bootstrap that
computes mean(log1p(returns)), making bootstrap's delta identical to
subsampling's observed_mean_log_diff.  No production code is modified.

Also: deep-dive into the subsampling block-10 CI anomaly on the negative
control pair (A0 vs A1).
"""

from __future__ import annotations

import json
import math
import sys
import time
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
    PERIODS_PER_YEAR_4H,
)
from v10.research.subsampling import (
    paired_block_subsampling,
    summarize_block_grid,
    _overlapping_block_means,
    _navs_to_log_returns,
    BARS_PER_YEAR_4H,
)
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

OUTDIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════════════
# Audit-only metric functions (NOT modifying production code)
# ═══════════════════════════════════════════════════════════════════

def mean_log_return(returns: np.ndarray) -> float:
    """Per-bar mean log return.

    When used with paired_block_bootstrap, the delta becomes:
      mean(log1p(rets_a[idx])) - mean(log1p(rets_b[idx]))
    which equals subsampling's observed_mean_log_diff on the same indices.
    This makes bootstrap and subsampling test the SAME statistic.
    """
    log_rets = np.log1p(returns)
    return float(np.mean(log_rets))


def annualize_log_diff(mean_log_diff: float) -> float:
    """Convert per-bar mean log-return difference to annualized simple return."""
    return float(np.expm1(BARS_PER_YEAR_4H * mean_log_diff))


# ═══════════════════════════════════════════════════════════════════
# Indicator helpers (from Report 17/18, self-contained)
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

def _log_returns_arr(close):
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
# Generic simulation engine (from Report 17/18)
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
# Strategy signal builders (from Report 17/18)
# ═══════════════════════════════════════════════════════════════════

def build_vtrend_a0(cl, hi, lo, vo, tb, wi):
    fp = max(5, SP // 4)
    ef = _ema(cl, fp); es = _ema(cl, SP)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool); exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at[i]): continue
        if ef[i] > es[i] and vd[i] > 0.0: entry[i] = True
        if ef[i] < es[i]: exit_s[i] = True
    return entry, exit_s, at, "VTREND_A0"

def build_vtrend_a1(cl, hi, lo, vo, tb, wi):
    fp = max(5, SP // 4)
    ef = _ema(cl, fp); es = _ema(cl, SP)
    at14 = _atr(hi, lo, cl, ATR_P); at20 = _atr_p(hi, lo, cl, 20)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool); exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(at14[i]) or math.isnan(at20[i]): continue
        if ef[i] > es[i] and vd[i] > 0.0: entry[i] = True
        if ef[i] < es[i]: exit_s[i] = True
    return entry, exit_s, at20, "VTREND_A1"

def build_vbreak(cl, hi, lo, vo, tb, wi):
    hh = _highest_high(hi, SP); ll = _lowest_low(lo, 40)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool); exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(hh[i]) or math.isnan(ll[i]) or math.isnan(at[i]): continue
        if cl[i] > hh[i] and vd[i] > 0.0: entry[i] = True
        if cl[i] < ll[i]: exit_s[i] = True
    return entry, exit_s, at, "VBREAK"

def build_vcusum(cl, hi, lo, vo, tb, wi):
    log_ret = _log_returns_arr(cl)
    z = _rolling_zscore(log_ret, SP)
    cup, cdn = _cusum(z, 0.5)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    n = len(cl)
    entry = np.zeros(n, dtype=bool); exit_s = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if math.isnan(at[i]): continue
        if cup[i] > 4.0 and vd[i] > 0.0: entry[i] = True
        if cdn[i] > 4.0: exit_s[i] = True
    return entry, exit_s, at, "VCUSUM"


def nav_to_equity_snaps(nav_arr, close_times, wi):
    snaps = []
    for i in range(wi, len(nav_arr)):
        snaps.append(EquitySnap(
            close_time=int(close_times[i]),
            nav_mid=float(nav_arr[i]),
            nav_liq=float(nav_arr[i]),
            cash=0.0, btc_qty=0.0, exposure=0.0,
        ))
    return snaps


# ═══════════════════════════════════════════════════════════════════
# Same-statistic paired tests
# ═══════════════════════════════════════════════════════════════════

def run_same_statistic_pair(equity_a, equity_b, pair_name):
    """Run bootstrap and subsampling on the SAME statistics."""

    results = {"pair": pair_name}

    # ── Statistic A: mean log-return difference (subsampling's native) ──
    stat_a = {}
    for bs in BLOCK_SIZES:
        # Bootstrap with mean_log_return metric
        boot = paired_block_bootstrap(
            equity_a=equity_a,
            equity_b=equity_b,
            metric_fn=mean_log_return,
            metric_name="mean_log_return",
            n_bootstrap=N_BOOT,
            block_size=bs,
            seed=SEED,
        )
        # Subsampling (native)
        sub = paired_block_subsampling(
            equity_a=equity_a,
            equity_b=equity_b,
            block_size=bs,
        )

        stat_a[f"block_{bs}"] = {
            "bootstrap": {
                "observed_delta": float(boot.observed_delta),
                "observed_delta_ann": annualize_log_diff(boot.observed_delta),
                "mean_delta": float(boot.mean_delta),
                "std_delta": float(boot.std_delta),
                "ci_lower": float(boot.ci_lower),
                "ci_upper": float(boot.ci_upper),
                "ci_lower_ann": annualize_log_diff(boot.ci_lower),
                "ci_upper_ann": annualize_log_diff(boot.ci_upper),
                "p_a_better": float(boot.p_a_better),
                "ci_width": float(boot.ci_upper - boot.ci_lower),
            },
            "subsampling": {
                "observed_delta": float(sub.observed_delta),
                "observed_mean_log_diff": float(sub.observed_mean_log_diff),
                "ci_lower": float(sub.ci_lower),
                "ci_upper": float(sub.ci_upper),
                "ci_lower_raw": None,  # filled below
                "ci_upper_raw": None,
                "p_a_better": float(sub.p_a_better),
                "ci_width": float(sub.ci_upper - sub.ci_lower),
                "n_blocks_used": int(sub.n_blocks_used),
            },
        }

    results["stat_A_mean_log_diff"] = stat_a

    # ── Statistic B: Sharpe ratio (bootstrap's native) ──
    stat_b = {}
    for bs in BLOCK_SIZES:
        boot = paired_block_bootstrap(
            equity_a=equity_a,
            equity_b=equity_b,
            metric_fn=calc_sharpe,
            metric_name="sharpe",
            n_bootstrap=N_BOOT,
            block_size=bs,
            seed=SEED,
        )
        stat_b[f"block_{bs}"] = {
            "bootstrap": {
                "observed_delta": float(boot.observed_delta),
                "mean_delta": float(boot.mean_delta),
                "std_delta": float(boot.std_delta),
                "ci_lower": float(boot.ci_lower),
                "ci_upper": float(boot.ci_upper),
                "p_a_better": float(boot.p_a_better),
                "ci_width": float(boot.ci_upper - boot.ci_lower),
            },
        }

    results["stat_B_sharpe"] = stat_b

    # ── Subsampling grid summary ──
    sub_results = []
    for bs in BLOCK_SIZES:
        sub = paired_block_subsampling(
            equity_a=equity_a,
            equity_b=equity_b,
            block_size=bs,
        )
        sub_results.append(sub)

    grid = summarize_block_grid(sub_results)
    results["subsampling_grid"] = {
        "decision_pass": grid.decision_pass,
        "median_p_a_better": float(grid.median_p_a_better),
        "median_ci_lower": float(grid.median_ci_lower),
        "support_ratio": float(grid.support_ratio),
    }

    # ── Bootstrap gate (production, Sharpe on primary block) ──
    primary_sharpe = stat_b[f"block_{BLOCK_SIZES[0]}"]["bootstrap"]
    results["production_gate_bootstrap"] = {
        "metric": "sharpe",
        "block_size": BLOCK_SIZES[0],
        "p_a_better": primary_sharpe["p_a_better"],
        "ci_lower": primary_sharpe["ci_lower"],
        "gate_pass": (primary_sharpe["p_a_better"] >= 0.80
                      and primary_sharpe["ci_lower"] > -0.01),
    }

    return results


# ═══════════════════════════════════════════════════════════════════
# Block-10 anomaly deep-dive
# ═══════════════════════════════════════════════════════════════════

def block_10_anomaly_analysis(equity_a, equity_b, pair_name):
    """Deep-dive into why subsampling block=10 CI collapses on degenerate pairs."""

    navs_a = np.array([e.nav_mid for e in equity_a], dtype=np.float64)
    navs_b = np.array([e.nav_mid for e in equity_b], dtype=np.float64)
    log_a = np.diff(np.log(navs_a))
    log_b = np.diff(np.log(navs_b))
    diff = log_a - log_b
    n = len(diff)

    full_mean = float(np.mean(diff))

    # Degeneracy diagnostics
    exact_zero = float(np.mean(np.abs(diff) < 1e-15))
    near_zero_1e10 = float(np.mean(np.abs(diff) < 1e-10))
    near_zero_1e8 = float(np.mean(np.abs(diff) < 1e-8))
    nonzero_count = int(np.sum(np.abs(diff) >= 1e-15))

    analysis = {
        "pair": pair_name,
        "n_returns": n,
        "full_mean_log_diff": full_mean,
        "full_mean_ann": annualize_log_diff(full_mean),
        "degeneracy": {
            "exact_zero_rate": exact_zero,
            "near_zero_1e10_rate": near_zero_1e10,
            "near_zero_1e8_rate": near_zero_1e8,
            "nonzero_count": nonzero_count,
            "nonzero_rate": 1.0 - exact_zero,
        },
    }

    # Per-block-size analysis
    for bs in BLOCK_SIZES:
        block_means = _overlapping_block_means(diff, bs)
        n_blocks = len(block_means)

        root = math.sqrt(bs) * (block_means - full_mean)
        sqrt_n = math.sqrt(n)
        test_stat = sqrt_n * full_mean

        # Root distribution
        root_zero_rate = float(np.mean(np.abs(root) < 1e-15))
        root_near_zero = float(np.mean(np.abs(root) < 1e-10))
        n_unique_roots = len(np.unique(np.round(root, 15)))

        q025 = float(np.quantile(root, 0.025))
        q975 = float(np.quantile(root, 0.975))
        q050 = float(np.quantile(root, 0.050))
        q950 = float(np.quantile(root, 0.950))

        # How many root values exceed test_stat?
        n_exceed = int(np.sum(root >= test_stat))
        p_one_sided = float(np.mean(root >= test_stat))

        # CI in raw log-return space
        ci_lower_raw = full_mean - q975 / sqrt_n
        ci_upper_raw = full_mean - q025 / sqrt_n

        # Fraction of blocks containing at least one non-zero bar
        blocks_with_signal = 0
        for start in range(n - bs + 1):
            block = diff[start:start + bs]
            if np.any(np.abs(block) >= 1e-15):
                blocks_with_signal += 1
        frac_with_signal = blocks_with_signal / n_blocks

        analysis[f"block_{bs}"] = {
            "n_blocks": n_blocks,
            "root_distribution": {
                "exact_zero_rate": root_zero_rate,
                "near_zero_1e10_rate": root_near_zero,
                "n_unique_values": n_unique_roots,
                "q2.5": q025,
                "q5.0": q050,
                "q50": float(np.median(root)),
                "q95": q950,
                "q97.5": q975,
                "std": float(np.std(root)),
                "min": float(np.min(root)),
                "max": float(np.max(root)),
            },
            "test_statistic": {
                "test_stat": test_stat,
                "n_exceed": n_exceed,
                "p_one_sided": p_one_sided,
                "p_a_better": 1.0 - p_one_sided,
            },
            "ci_raw": {
                "ci_lower": ci_lower_raw,
                "ci_upper": ci_upper_raw,
                "ci_width": ci_upper_raw - ci_lower_raw,
            },
            "ci_annualized": {
                "ci_lower": annualize_log_diff(ci_lower_raw),
                "ci_upper": annualize_log_diff(ci_upper_raw),
            },
            "blocks_with_nonzero_bar": {
                "count": blocks_with_signal,
                "fraction": frac_with_signal,
            },
        }

    return analysis


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()
    print("=" * 72)
    print("19 — SAME-STATISTIC CONTROL PAIR AUDIT")
    print("=" * 72)
    print(f"  Bootstrap: {N_BOOT} reps, seed {SEED}, blocks {BLOCK_SIZES}")
    print(f"  Statistics: A = mean_log_diff (subsampling native)")
    print(f"              B = Sharpe (bootstrap native)")

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

    print(f"  {n} bars, warmup idx={wi}, trading={n-wi}")

    # ── Simulate strategies ──
    print("\nSimulating strategies...")
    builders = [build_vtrend_a0, build_vtrend_a1, build_vbreak, build_vcusum]
    strategies = {}
    for builder in builders:
        entry, exit_s, exit_atr, name = builder(cl, hi, lo, vo, tb, wi)
        nav, exp = simulate(cl, entry, exit_s, exit_atr, TRAIL, wi)
        equity = nav_to_equity_snaps(nav, close_times, wi)
        strategies[name] = {"nav": nav, "exp": exp, "equity": equity}
        print(f"  {name}: NAV[0]={nav[wi]:.0f}  NAV[-1]={nav[-1]:.0f}")

    # ── Define control pairs ──
    pairs = [
        ("VTREND_A0", "VTREND_A1", "negative_control"),
        ("VTREND_A0", "VBREAK",    "mid_positive"),
        ("VTREND_A0", "VCUSUM",    "strong_positive"),
    ]

    all_results = {"config": {
        "n_bootstrap": N_BOOT, "seed": SEED, "block_sizes": BLOCK_SIZES,
        "start": START, "end": END, "cost_rt_bps": COST.round_trip_bps,
    }}

    # ═══════════════════════════════════════════════════════════════
    # Run same-statistic tests on each pair
    # ═══════════════════════════════════════════════════════════════

    for a_name, b_name, control_type in pairs:
        pair_name = f"{a_name} vs {b_name}"
        print(f"\n{'=' * 72}")
        print(f"PAIR: {pair_name}  ({control_type})")
        print(f"{'=' * 72}")

        eq_a = strategies[a_name]["equity"]
        eq_b = strategies[b_name]["equity"]

        pair_result = run_same_statistic_pair(eq_a, eq_b, pair_name)
        pair_result["control_type"] = control_type

        # Print stat A comparison (same statistic: mean log diff)
        print(f"\n  STAT A: Per-bar mean log-return difference")
        print(f"  {'block':>5}  {'method':>12}  {'obs_delta':>12}  {'p_a_better':>10}  "
              f"{'ci_low':>12}  {'ci_high':>12}  {'ci_width':>10}")
        print("  " + "-" * 85)

        for bs in BLOCK_SIZES:
            bk = f"block_{bs}"
            b = pair_result["stat_A_mean_log_diff"][bk]["bootstrap"]
            s = pair_result["stat_A_mean_log_diff"][bk]["subsampling"]
            print(f"  {bs:5d}  {'bootstrap':>12}  {b['observed_delta']:12.2e}  "
                  f"{b['p_a_better']:10.4f}  {b['ci_lower']:12.2e}  "
                  f"{b['ci_upper']:12.2e}  {b['ci_width']:10.2e}")
            print(f"  {bs:5d}  {'subsampling':>12}  {s['observed_mean_log_diff']:12.2e}  "
                  f"{s['p_a_better']:10.4f}  {s['ci_lower']:12.4f}  "
                  f"{s['ci_upper']:12.4f}  {s['ci_width']:10.4f}")

        # Print stat A annualized comparison
        print(f"\n  STAT A (annualized):")
        print(f"  {'block':>5}  {'method':>12}  {'Δ_ann':>12}  {'ci_low_ann':>12}  {'ci_hi_ann':>12}")
        print("  " + "-" * 60)
        for bs in BLOCK_SIZES:
            bk = f"block_{bs}"
            b = pair_result["stat_A_mean_log_diff"][bk]["bootstrap"]
            s = pair_result["stat_A_mean_log_diff"][bk]["subsampling"]
            print(f"  {bs:5d}  {'bootstrap':>12}  {b['observed_delta_ann']:12.4f}  "
                  f"{b['ci_lower_ann']:12.4f}  {b['ci_upper_ann']:12.4f}")
            print(f"  {bs:5d}  {'subsampling':>12}  {s['observed_delta']:12.4f}  "
                  f"{s['ci_lower']:12.4f}  {s['ci_upper']:12.4f}")

        # Print stat B (Sharpe — bootstrap only)
        print(f"\n  STAT B: Sharpe (bootstrap only, for reference)")
        for bs in BLOCK_SIZES:
            bk = f"block_{bs}"
            b = pair_result["stat_B_sharpe"][bk]["bootstrap"]
            print(f"    block={bs}: Δ={b['observed_delta']:.4f}  "
                  f"p={b['p_a_better']:.4f}  "
                  f"CI=[{b['ci_lower']:.4f}, {b['ci_upper']:.4f}]")

        # Production gate
        g = pair_result["production_gate_bootstrap"]
        print(f"\n  PRODUCTION GATE (bootstrap/Sharpe/block={g['block_size']}): "
              f"{'PASS' if g['gate_pass'] else 'FAIL'}")

        # Subsampling grid gate
        sg = pair_result["subsampling_grid"]
        print(f"  PRODUCTION GATE (subsampling grid): "
              f"{'PASS' if sg['decision_pass'] else 'FAIL'}")

        all_results[pair_name] = pair_result

    # ═══════════════════════════════════════════════════════════════
    # Block-10 anomaly deep-dive
    # ═══════════════════════════════════════════════════════════════

    print(f"\n{'=' * 72}")
    print("BLOCK-10 ANOMALY ANALYSIS")
    print(f"{'=' * 72}")

    anomaly_results = {}
    for a_name, b_name, control_type in pairs:
        pair_name = f"{a_name} vs {b_name}"
        print(f"\n  --- {pair_name} ({control_type}) ---")

        eq_a = strategies[a_name]["equity"]
        eq_b = strategies[b_name]["equity"]

        analysis = block_10_anomaly_analysis(eq_a, eq_b, pair_name)
        anomaly_results[pair_name] = analysis

        deg = analysis["degeneracy"]
        print(f"  Diff series: exact_zero={deg['exact_zero_rate']:.1%}  "
              f"nonzero={deg['nonzero_count']}  "
              f"full_mean={analysis['full_mean_log_diff']:.2e}")

        for bs in BLOCK_SIZES:
            bk = f"block_{bs}"
            a = analysis[bk]
            rd = a["root_distribution"]
            ts = a["test_statistic"]
            ci = a["ci_raw"]
            bns = a["blocks_with_nonzero_bar"]
            print(f"\n  block={bs}:")
            print(f"    n_blocks={a['n_blocks']}  blocks_w_signal={bns['count']} ({bns['fraction']:.1%})")
            print(f"    root: zero_rate={rd['exact_zero_rate']:.1%}  "
                  f"unique={rd['n_unique_values']}  "
                  f"std={rd['std']:.2e}")
            print(f"    root quantiles: "
                  f"[{rd['q2.5']:.2e}, {rd['q50']:.2e}, {rd['q97.5']:.2e}]")
            print(f"    test_stat={ts['test_stat']:.4f}  "
                  f"n_exceed={ts['n_exceed']}  "
                  f"p_a_better={ts['p_a_better']:.4f}")
            print(f"    CI_raw: [{ci['ci_lower']:.2e}, {ci['ci_upper']:.2e}]  "
                  f"width={ci['ci_width']:.2e}")

    all_results["anomaly_analysis"] = anomaly_results

    # ═══════════════════════════════════════════════════════════════
    # Summary: Method agreement table
    # ═══════════════════════════════════════════════════════════════

    print(f"\n{'=' * 72}")
    print("SUMMARY: SAME-STATISTIC METHOD COMPARISON")
    print(f"{'=' * 72}")
    print(f"\n  Statistic A: annualized excess geometric growth (block=20)")
    print(f"  {'Pair':<28}  {'Boot p':>7}  {'Sub p':>7}  {'Boot CI':>24}  "
          f"{'Sub CI':>24}  {'Agree?':>6}")
    print("  " + "-" * 100)

    for a_name, b_name, control_type in pairs:
        pair_name = f"{a_name} vs {b_name}"
        r = all_results[pair_name]
        b20 = r["stat_A_mean_log_diff"]["block_20"]["bootstrap"]
        s20 = r["stat_A_mean_log_diff"]["block_20"]["subsampling"]
        b_ci = f"[{b20['ci_lower_ann']:+.4f}, {b20['ci_upper_ann']:+.4f}]"
        s_ci = f"[{s20['ci_lower']:+.4f}, {s20['ci_upper']:+.4f}]"

        # Do they agree on direction?
        b_pass = b20["p_a_better"] >= 0.80 and b20["ci_lower"] > 0
        s_pass = s20["p_a_better"] >= 0.80 and s20["ci_lower"] > 0
        agree = "YES" if b_pass == s_pass else "NO"

        print(f"  {pair_name:<28}  {b20['p_a_better']:7.4f}  {s20['p_a_better']:7.4f}  "
              f"{b_ci:>24}  {s_ci:>24}  {agree:>6}")

    # ── Save ──
    out_path = OUTDIR / "19_same_statistic_control_pair_audit.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Saved: {out_path}")

    elapsed = time.time() - t_start
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
