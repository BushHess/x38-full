#!/usr/bin/env python3
"""VTREND-SM: slow_period=120 vs slow_period=126 — Full Statistical Comparison.

8-phase evaluation:
  Phase 1: Real data baseline for BOTH configs
  Phase 2: VCBB Bootstrap (2000 paths each) — CI for Sharpe/CAGR/MDD/Calmar
  Phase 3: Paired Block Bootstrap — Sharpe, CAGR, MDD (same block indices)
  Phase 4: Paired Block Subsampling — multi-block-size grid (10,20,40,80,120)
  Phase 5: Deflated Sharpe Ratio — selection bias correction (DSR)
  Phase 6: Sub-Period Analysis — yearly, halves, thirds for both configs
  Phase 7: Permutation Test — shuffle slow_period assignment (10,000 perms)
  Phase 8: Summary Verdict — aggregate all evidence

Uses identical infrastructure to all prior studies:
  VCBB bootstrap, DataFeed, harsh cost (50 bps RT), H4 resolution.
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
from research.lib.dsr import compute_dsr

# ── Constants (identical to all studies) ──────────────────────────────────
DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025 = 25 bps per side

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
BLKSZ  = 60
CTX    = 90
K_NN   = 50
SEED   = 42

ANN = math.sqrt(6.0 * 365.25)   # ~46.85  Sharpe annualization for H4
BPY = 6.0 * 365.0               # 2190.0  bars-per-year

# ── Two configs under test ────────────────────────────────────────────────
CONFIG_A_LABEL = "SM_slow120"
CONFIG_B_LABEL = "SM_slow126"

@dataclass
class SMParams:
    slow: int
    fast: int
    atr_period: int
    atr_mult: float
    entry_n: int
    exit_n: int
    target_vol: float
    vol_lb: int
    slope_lb: int
    min_rebal: float
    min_weight: float

def make_sm_params(slow: int) -> SMParams:
    return SMParams(
        slow=slow,
        fast=max(5, slow // 4),
        atr_period=14,
        atr_mult=3.0,
        entry_n=max(24, slow // 2),
        exit_n=max(12, slow // 4),
        target_vol=0.15,
        vol_lb=slow,
        slope_lb=6,
        min_rebal=0.05,
        min_weight=0.0,
    )

PARAMS_A = make_sm_params(120)
PARAMS_B = make_sm_params(126)
EPS = 1e-12


# ═══════════════════════════════════════════════════════════════════════════
# Indicators (frozen artifacts — identical to vtrend_sm_bootstrap.py)
# ═══════════════════════════════════════════════════════════════════════════

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _atr(high, low, close, period):
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.concatenate([[high[0]], close[:-1]])),
            np.abs(low - np.concatenate([[low[0]], close[:-1]])),
        ),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _rolling_high_shifted(high, lookback):
    n = len(high)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.max(high[i - lookback:i])
    return out


def _rolling_low_shifted(low, lookback):
    n = len(low)
    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(lookback, n):
        out[i] = np.min(low[i - lookback:i])
    return out


def _realized_vol(close, lookback, bars_per_year):
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    lr = np.full(n, np.nan, dtype=np.float64)
    lr[1:] = np.log(np.where(close[:-1] > 0, close[1:] / close[:-1], np.nan))
    ann_factor = math.sqrt(bars_per_year)
    for i in range(lookback, n):
        window = lr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=0)) * ann_factor
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Parameterized VTREND-SM Simulator
# ═══════════════════════════════════════════════════════════════════════════

def sim_vtrend_sm(cl, hi, lo, vo, tb, wi, p: SMParams):
    """Run VTREND-SM on price arrays with given params."""
    n = len(cl)

    ef = _ema(cl, p.fast)
    es = _ema(cl, p.slow)
    at = _atr(hi, lo, cl, p.atr_period)
    hh = _rolling_high_shifted(hi, p.entry_n)
    ll = _rolling_low_shifted(lo, p.exit_n)
    rv = _realized_vol(cl, p.vol_lb, BPY)

    slope_ref = np.full(n, np.nan, dtype=np.float64)
    if p.slope_lb < n:
        slope_ref[p.slope_lb:] = es[:-p.slope_lb]

    warmup_end = n
    for i in range(n):
        if (np.isfinite(ef[i]) and np.isfinite(es[i]) and np.isfinite(slope_ref[i])
                and np.isfinite(at[i]) and np.isfinite(hh[i])
                and np.isfinite(ll[i]) and np.isfinite(rv[i])):
            warmup_end = i
            break
    warmup_end = max(warmup_end, wi)

    cash = CASH
    bq = 0.0
    active = False
    nt = 0
    navs = np.full(n, CASH, dtype=np.float64)
    exposure = np.zeros(n, dtype=np.float64)

    has_pending = False
    pending_target = 0.0

    for i in range(n):
        price = cl[i]

        if i > 0 and has_pending:
            fp = cl[i - 1]
            has_pending = False
            nav_fp = cash + bq * fp

            if pending_target <= 0.0:
                if bq > 0:
                    cash += bq * fp * (1.0 - CPS)
                    bq = 0.0
                    active = False
                    nt += 1
            else:
                desired_bq = pending_target * nav_fp / fp
                delta_bq = desired_bq - bq

                if delta_bq > 1e-12:
                    cost = delta_bq * fp * (1.0 + CPS)
                    if cost <= cash + 1e-6:
                        cash -= cost
                        bq = desired_bq
                elif delta_bq < -1e-12:
                    sell_bq = -delta_bq
                    cash += sell_bq * fp * (1.0 - CPS)
                    bq = desired_bq

                if not active and bq > 1e-12:
                    active = True

        nav = cash + bq * price
        navs[i] = nav
        exposure[i] = (bq * price / nav) if nav > EPS else 0.0

        if i < warmup_end:
            continue

        if not (np.isfinite(ef[i]) and np.isfinite(es[i])
                and np.isfinite(slope_ref[i]) and np.isfinite(at[i])
                and np.isfinite(hh[i]) and np.isfinite(ll[i])
                and np.isfinite(rv[i])):
            continue

        regime_ok = (ef[i] > es[i]) and (es[i] > slope_ref[i])

        if not active:
            if regime_ok and price > hh[i]:
                w = p.target_vol / max(rv[i], EPS)
                w = min(1.0, max(0.0, w))
                if w >= p.min_weight and w > 0.0:
                    has_pending = True
                    pending_target = w
        else:
            exit_floor = max(ll[i], es[i] - p.atr_mult * at[i])
            if price < exit_floor:
                has_pending = True
                pending_target = 0.0
            else:
                curr_expo = bq * price / nav if nav > EPS else 0.0
                new_w = p.target_vol / max(rv[i], EPS)
                new_w = min(1.0, max(0.0, new_w))
                if new_w < p.min_weight:
                    new_w = 0.0
                delta = abs(new_w - curr_expo)
                if delta >= p.min_rebal - 1e-12:
                    has_pending = True
                    pending_target = new_w
                    if new_w <= 0.0:
                        active = False

    if bq > 1e-12:
        cash += bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        navs[-1] = cash
        exposure[-1] = 0.0
        nt += 1

    return navs, exposure, nt


# ═══════════════════════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════════════════════

def metrics_from_navs(navs, wi):
    active = navs[wi:]
    n = len(active)
    if n < 10:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0}

    rets = active[1:] / active[:-1] - 1.0
    n_rets = len(rets)
    if n_rets < 2:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0}

    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    tr = active[-1] / active[0] - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0

    peak = np.maximum.accumulate(active)
    dd = 1.0 - active / peak
    mdd = np.max(dd) * 100.0

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar}


def returns_from_navs(navs, wi):
    active = navs[wi:]
    return active[1:] / active[:-1] - 1.0


# ═══════════════════════════════════════════════════════════════════════════
# EquitySnap-like wrapper for bootstrap/subsampling APIs
# ═══════════════════════════════════════════════════════════════════════════

class _NavSnap:
    """Minimal equity snap for paired_block_bootstrap / subsampling."""
    __slots__ = ("nav_mid", "exposure")
    def __init__(self, nav: float, expo: float = 0.0):
        self.nav_mid = nav
        self.exposure = expo


def navs_to_snaps(navs, exposure=None):
    if exposure is None:
        return [_NavSnap(float(navs[i])) for i in range(len(navs))]
    return [_NavSnap(float(navs[i]), float(exposure[i])) for i in range(len(navs))]


# ═══════════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    ts = np.array([b.close_time for b in h4], dtype=np.int64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, ts, wi, n


# ═══════════════════════════════════════════════════════════════════════════
# Phase 1: Real Data Baseline (both configs)
# ═══════════════════════════════════════════════════════════════════════════

def phase1_real(cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 72)
    print("  PHASE 1: REAL DATA BASELINE — BOTH CONFIGS")
    print("=" * 72)

    results = {}
    for label, params in [(CONFIG_A_LABEL, PARAMS_A), (CONFIG_B_LABEL, PARAMS_B)]:
        navs, expo, nt = sim_vtrend_sm(cl, hi, lo, vo, tb, wi, params)
        m = metrics_from_navs(navs, wi)
        m["trades"] = nt

        avg_expo = float(np.mean(expo[wi:]))
        m["avg_exposure"] = avg_expo

        print(f"\n  [{label}] slow={params.slow}, fast={params.fast}, "
              f"entry_n={params.entry_n}, exit_n={params.exit_n}, vol_lb={params.vol_lb}")
        print(f"    Sharpe:     {m['sharpe']:.4f}")
        print(f"    CAGR:       {m['cagr']:.2f}%")
        print(f"    MDD:        {m['mdd']:.2f}%")
        print(f"    Calmar:     {m['calmar']:.4f}")
        print(f"    Trades:     {nt}")
        print(f"    Avg Expo:   {avg_expo:.2%}")
        print(f"    Final NAV:  ${navs[-1]:,.2f}")

        results[label] = {"metrics": m, "navs": navs, "exposure": expo}

    # Delta
    ma = results[CONFIG_A_LABEL]["metrics"]
    mb = results[CONFIG_B_LABEL]["metrics"]
    print(f"\n  Delta (B - A):")
    print(f"    Sharpe:  {mb['sharpe'] - ma['sharpe']:+.4f}")
    print(f"    CAGR:    {mb['cagr'] - ma['cagr']:+.2f}%")
    print(f"    MDD:     {mb['mdd'] - ma['mdd']:+.2f}%")
    print(f"    Calmar:  {mb['calmar'] - ma['calmar']:+.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2: VCBB Bootstrap (both configs, 2000 paths each)
# ═══════════════════════════════════════════════════════════════════════════

def _run_vcbb_one(label, params, cl, hi, lo, vo, tb, wi, n,
                  cr, hr, lr, vol_r, tb_r, vcbb_state, n_trans, p0):
    """VCBB bootstrap for a single config."""
    print(f"\n    [{label}] bootstrapping {N_BOOT} paths ...")
    rng = np.random.default_rng(SEED)

    sharpes = np.zeros(N_BOOT)
    cagrs   = np.zeros(N_BOOT)
    mdds    = np.zeros(N_BOOT)
    calmars = np.zeros(N_BOOT)
    trades  = np.zeros(N_BOOT, dtype=int)

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"      {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng,
            vcbb=vcbb_state, K=K_NN,
        )
        navs, _, nt = sim_vtrend_sm(c, h, l, v, t, wi, params)
        m = metrics_from_navs(navs, wi)

        sharpes[b] = m["sharpe"]
        cagrs[b]   = m["cagr"]
        mdds[b]    = m["mdd"]
        calmars[b] = m["calmar"]
        trades[b]  = nt

    el = time.time() - t0
    print(f"      Done: {el:.1f}s ({el/N_BOOT:.2f}s/path)")

    return {
        "sharpes": sharpes, "cagrs": cagrs, "mdds": mdds,
        "calmars": calmars, "trades": trades,
    }


def _boot_summary(arr, label_metric):
    """Compute summary stats for a bootstrap array."""
    percentiles = [0.025, 0.05, 0.25, 0.50, 0.75, 0.95, 0.975]
    pcts = {f"p{int(p*100)}": float(np.percentile(arr, p*100)) for p in percentiles}
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        **pcts,
    }


def phase2_bootstrap(cl, hi, lo, vo, tb, wi, n):
    print("\n" + "=" * 72)
    print(f"  PHASE 2: VCBB BOOTSTRAP ({N_BOOT} paths × 2 configs)")
    print("=" * 72)

    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=CTX)
    n_trans = n - 1
    p0 = cl[0]

    boot = {}
    for label, params in [(CONFIG_A_LABEL, PARAMS_A), (CONFIG_B_LABEL, PARAMS_B)]:
        raw = _run_vcbb_one(label, params, cl, hi, lo, vo, tb, wi, n,
                           cr, hr, lr, vol_r, tb_r, vcbb_state, n_trans, p0)
        summary = {}
        for name in ["sharpes", "cagrs", "mdds", "calmars"]:
            summary[name.rstrip("s")] = _boot_summary(raw[name], name)

        summary["P_cagr_gt_0"] = float(np.mean(raw["cagrs"] > 0))
        summary["P_sharpe_gt_0"] = float(np.mean(raw["sharpes"] > 0))
        summary["P_sharpe_gt_0.5"] = float(np.mean(raw["sharpes"] > 0.5))
        summary["P_mdd_lt_30"] = float(np.mean(raw["mdds"] < 30))

        boot[label] = {"summary": summary, "raw": raw}

    # Print comparison table
    print(f"\n  {'Metric':>12s} {'A (120)':>30s} {'B (126)':>30s}")
    print("  " + "-" * 75)
    for metric in ["sharpe", "cagr", "mdd", "calmar"]:
        sa = boot[CONFIG_A_LABEL]["summary"][metric]
        sb = boot[CONFIG_B_LABEL]["summary"][metric]
        fmt = ".4f" if metric in ("sharpe", "calmar") else ".2f"
        print(f"  {metric:>12s}  med={sa['median']:{fmt}} CI=[{sa['p2']:{fmt}},{sa['p97']:{fmt}}]"
              f"  med={sb['median']:{fmt}} CI=[{sb['p2']:{fmt}},{sb['p97']:{fmt}}]")

    for label in [CONFIG_A_LABEL, CONFIG_B_LABEL]:
        s = boot[label]["summary"]
        print(f"\n  [{label}] P(CAGR>0)={s['P_cagr_gt_0']:.1%}, "
              f"P(Sharpe>0)={s['P_sharpe_gt_0']:.1%}, "
              f"P(Sharpe>0.5)={s['P_sharpe_gt_0.5']:.1%}, "
              f"P(MDD<30%)={s['P_mdd_lt_30']:.1%}")

    return boot


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3: Paired Block Bootstrap (Sharpe, CAGR, MDD)
# ═══════════════════════════════════════════════════════════════════════════

def phase3_paired_bootstrap(navs_a, navs_b, expo_a, expo_b, wi):
    print("\n" + "=" * 72)
    print("  PHASE 3: PAIRED BLOCK BOOTSTRAP (same indices)")
    print("=" * 72)

    snaps_a = navs_to_snaps(navs_a[wi:], expo_a[wi:])
    snaps_b = navs_to_snaps(navs_b[wi:], expo_b[wi:])

    from v10.research.bootstrap import (
        paired_block_bootstrap, calc_sharpe, calc_cagr, calc_max_drawdown,
    )

    results = {}
    for metric_fn, name in [(calc_sharpe, "sharpe"), (calc_cagr, "cagr"),
                             (calc_max_drawdown, "max_drawdown")]:
        for bs in [10, 20, 40]:
            r = paired_block_bootstrap(
                equity_a=snaps_a, equity_b=snaps_b,
                metric_fn=metric_fn, metric_name=name,
                n_bootstrap=2000, block_size=bs, seed=1337,
            )
            key = f"{name}_bs{bs}"
            results[key] = {
                "metric": name, "block_size": bs,
                "observed_a": r.observed_a, "observed_b": r.observed_b,
                "observed_delta": r.observed_delta,
                "mean_delta": r.mean_delta, "std_delta": r.std_delta,
                "ci_lower": r.ci_lower, "ci_upper": r.ci_upper,
                "p_a_better": r.p_a_better,
            }
            direction = "A" if r.p_a_better > 0.5 else "B"
            print(f"    {name:>14s} bs={bs:3d}:  delta={r.observed_delta:+.4f}  "
                  f"CI=[{r.ci_lower:+.4f},{r.ci_upper:+.4f}]  "
                  f"p(A>B)={r.p_a_better:.3f} → {direction}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4: Paired Block Subsampling (multi-block grid)
# ═══════════════════════════════════════════════════════════════════════════

def phase4_subsampling(navs_a, navs_b, expo_a, expo_b, wi):
    print("\n" + "=" * 72)
    print("  PHASE 4: PAIRED BLOCK SUBSAMPLING (Politis-Romano-Wolf)")
    print("=" * 72)

    snaps_a = navs_to_snaps(navs_a[wi:], expo_a[wi:])
    snaps_b = navs_to_snaps(navs_b[wi:], expo_b[wi:])

    from v10.research.subsampling import paired_block_subsampling, summarize_block_grid

    block_sizes = [10, 20, 40, 80, 120]
    sub_results = []
    results_dict = {}

    for bs in block_sizes:
        try:
            r = paired_block_subsampling(
                equity_a=snaps_a, equity_b=snaps_b,
                block_size=bs,
            )
            sub_results.append(r)
            results_dict[f"bs{bs}"] = {
                "block_size": bs,
                "observed_delta": r.observed_delta,
                "ci_lower": r.ci_lower, "ci_upper": r.ci_upper,
                "p_a_better": r.p_a_better,
                "p_value_one_sided": r.p_value_one_sided,
                "n_blocks_used": r.n_blocks_used,
            }
            print(f"    bs={bs:4d}: delta={r.observed_delta:+.6f}  "
                  f"CI=[{r.ci_lower:+.6f},{r.ci_upper:+.6f}]  "
                  f"p(A>B)={r.p_a_better:.3f}  blocks={r.n_blocks_used}")
        except ValueError as e:
            print(f"    bs={bs:4d}: SKIPPED — {e}")

    grid_summary = None
    if sub_results:
        gs = summarize_block_grid(sub_results)
        grid_summary = {
            "median_p_a_better": gs.median_p_a_better,
            "min_p_a_better": gs.min_p_a_better,
            "support_ratio": gs.support_ratio,
            "decision_pass": gs.decision_pass,
            "median_ci_lower": gs.median_ci_lower,
            "median_ci_upper": gs.median_ci_upper,
        }
        print(f"\n    Grid summary: median_p={gs.median_p_a_better:.3f}, "
              f"support={gs.support_ratio:.2f}, pass={gs.decision_pass}")

    return {"per_block": results_dict, "grid_summary": grid_summary}


# ═══════════════════════════════════════════════════════════════════════════
# Phase 5: Deflated Sharpe Ratio (DSR)
# ═══════════════════════════════════════════════════════════════════════════

def phase5_dsr(navs_a, navs_b, wi):
    print("\n" + "=" * 72)
    print("  PHASE 5: DEFLATED SHARPE RATIO (selection bias correction)")
    print("=" * 72)

    rets_a = returns_from_navs(navs_a, wi)
    rets_b = returns_from_navs(navs_b, wi)

    trial_levels = [2, 5, 10, 27, 54, 100, 200, 500]
    results = {}

    for label, rets in [(CONFIG_A_LABEL, rets_a), (CONFIG_B_LABEL, rets_b)]:
        dsr_results = {}
        for nt in trial_levels:
            d = compute_dsr(rets, num_trials=nt)
            dsr_results[nt] = {
                "dsr_pvalue": d["dsr_pvalue"],
                "sr_annualized": d["sr_annualized"],
                "sr0_annualized": d["sr0_annualized"],
                "skewness": d["skewness"],
                "kurtosis": d["kurtosis"],
            }
        results[label] = dsr_results

        print(f"\n  [{label}]")
        print(f"    SR_ann={dsr_results[2]['sr_annualized']:.4f}, "
              f"skew={dsr_results[2]['skewness']:.3f}, "
              f"kurt={dsr_results[2]['kurtosis']:.3f}")
        print(f"    {'Trials':>8s}  {'SR0_ann':>8s}  {'DSR_pval':>8s}")
        for nt in trial_levels:
            d = dsr_results[nt]
            print(f"    {nt:8d}  {d['sr0_annualized']:8.4f}  {d['dsr_pvalue']:8.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Phase 6: Sub-Period Analysis (yearly, halves, thirds)
# ═══════════════════════════════════════════════════════════════════════════

def phase6_subperiod(cl, hi, lo, vo, tb, ts, wi, n):
    print("\n" + "=" * 72)
    print("  PHASE 6: SUB-PERIOD ANALYSIS")
    print("=" * 72)

    import calendar, datetime

    def year_ms(y):
        dt = datetime.datetime(y, 1, 1, tzinfo=datetime.timezone.utc)
        return int(dt.timestamp() * 1000)

    # Run full sim for both
    navs_a, _, _ = sim_vtrend_sm(cl, hi, lo, vo, tb, 0, PARAMS_A)
    navs_b, _, _ = sim_vtrend_sm(cl, hi, lo, vo, tb, 0, PARAMS_B)

    results = {"yearly": {}, "halves": {}, "thirds": {}}

    # ── Per-year ──
    print(f"\n  {'Period':>14s}  {'A Sharpe':>8s} {'A CAGR':>8s} {'A MDD':>7s}"
          f"  {'B Sharpe':>8s} {'B CAGR':>8s} {'B MDD':>7s}  {'dSh':>6s}")
    print("  " + "-" * 85)

    for yr in range(2019, 2026):
        t_start = year_ms(yr)
        t_end = year_ms(yr + 1)
        mask = (ts >= t_start) & (ts < t_end)
        if mask.sum() < 100:
            continue

        idx = np.where(mask)[0]
        i_start, i_end = idx[0], idx[-1] + 1

        sub_a = navs_a[i_start:i_end]
        sub_b = navs_b[i_start:i_end]
        if len(sub_a) < 10:
            continue

        ma = metrics_from_navs(sub_a, 0)
        mb = metrics_from_navs(sub_b, 0)
        results["yearly"][yr] = {"A": ma, "B": mb}

        dsh = mb["sharpe"] - ma["sharpe"]
        print(f"  {yr:>14d}  {ma['sharpe']:8.4f} {ma['cagr']:7.2f}% {ma['mdd']:6.2f}%"
              f"  {mb['sharpe']:8.4f} {mb['cagr']:7.2f}% {mb['mdd']:6.2f}%  {dsh:+6.4f}")

    # ── Halves ──
    print(f"\n  Half-Period:")
    mid = wi + (n - wi) // 2
    for label, i_start, i_end in [("First half", wi, mid), ("Second half", mid, n)]:
        sub_a = navs_a[i_start:i_end]
        sub_b = navs_b[i_start:i_end]
        if len(sub_a) < 10:
            continue
        ma = metrics_from_navs(sub_a, 0)
        mb = metrics_from_navs(sub_b, 0)
        results["halves"][label] = {"A": ma, "B": mb}
        dsh = mb["sharpe"] - ma["sharpe"]
        print(f"  {label:>14s}  {ma['sharpe']:8.4f} {ma['cagr']:7.2f}% {ma['mdd']:6.2f}%"
              f"  {mb['sharpe']:8.4f} {mb['cagr']:7.2f}% {mb['mdd']:6.2f}%  {dsh:+6.4f}")

    # ── Thirds ──
    print(f"\n  Third-Period:")
    third = (n - wi) // 3
    for j, label in enumerate(["First third", "Middle third", "Last third"]):
        i_start = wi + j * third
        i_end = wi + (j + 1) * third if j < 2 else n
        sub_a = navs_a[i_start:i_end]
        sub_b = navs_b[i_start:i_end]
        if len(sub_a) < 10:
            continue
        ma = metrics_from_navs(sub_a, 0)
        mb = metrics_from_navs(sub_b, 0)
        results["thirds"][label] = {"A": ma, "B": mb}
        dsh = mb["sharpe"] - ma["sharpe"]
        print(f"  {label:>14s}  {ma['sharpe']:8.4f} {ma['cagr']:7.2f}% {ma['mdd']:6.2f}%"
              f"  {mb['sharpe']:8.4f} {mb['cagr']:7.2f}% {mb['mdd']:6.2f}%  {dsh:+6.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Phase 7: Permutation Test (shuffle config assignment)
# ═══════════════════════════════════════════════════════════════════════════

def phase7_permutation(cl, hi, lo, vo, tb, wi, n):
    """Permutation test: is the Sharpe difference between slow=120 and slow=126
    statistically distinguishable from random slow_period noise?

    Under H0: the Sharpe difference arises from sampling variability in nearby
    slow_period values. We test by drawing N_PERM random slow periods from
    the range [115, 132] and computing the Sharpe difference against slow=120.
    """
    print("\n" + "=" * 72)
    print("  PHASE 7: PERMUTATION TEST (parameter noise)")
    print("=" * 72)

    N_PERM = 10_000
    SLOW_RANGE = list(range(115, 133))  # 115..132 inclusive (18 values)
    rng = np.random.default_rng(SEED + 7)

    # Real observed delta
    navs_a, _, _ = sim_vtrend_sm(cl, hi, lo, vo, tb, wi, PARAMS_A)
    navs_b, _, _ = sim_vtrend_sm(cl, hi, lo, vo, tb, wi, PARAMS_B)
    ma = metrics_from_navs(navs_a, wi)
    mb = metrics_from_navs(navs_b, wi)
    real_delta_sharpe = mb["sharpe"] - ma["sharpe"]
    real_delta_cagr = mb["cagr"] - ma["cagr"]

    print(f"  Real delta: Sharpe={real_delta_sharpe:+.4f}, CAGR={real_delta_cagr:+.2f}%")
    print(f"  Permuting slow_period from [{SLOW_RANGE[0]}, {SLOW_RANGE[-1]}] vs 120")
    print(f"  {N_PERM} permutations ...")

    # Pre-compute Sharpe for slow=120 (already done above)
    sharpe_120 = ma["sharpe"]

    # Cache: store Sharpe for each slow_period we encounter
    sharpe_cache = {120: sharpe_120}

    def get_sharpe(slow):
        if slow not in sharpe_cache:
            p = make_sm_params(slow)
            navs, _, _ = sim_vtrend_sm(cl, hi, lo, vo, tb, wi, p)
            m = metrics_from_navs(navs, wi)
            sharpe_cache[slow] = m["sharpe"]
        return sharpe_cache[slow]

    # Pre-compute all slow_periods in range (only 18 sims)
    print(f"  Pre-computing {len(SLOW_RANGE)} slow_period variants ...")
    t0 = time.time()
    for s in SLOW_RANGE:
        get_sharpe(s)
    print(f"  Done: {time.time() - t0:.1f}s")

    # Now draw permutation pairs
    perm_deltas = np.zeros(N_PERM)
    for i in range(N_PERM):
        s1, s2 = rng.choice(SLOW_RANGE, size=2, replace=False)
        perm_deltas[i] = get_sharpe(s2) - get_sharpe(s1)

    # Two-sided p-value: P(|perm_delta| >= |real_delta|)
    p_value = float(np.mean(np.abs(perm_deltas) >= abs(real_delta_sharpe)))

    print(f"\n  Permutation distribution:")
    print(f"    mean delta:   {np.mean(perm_deltas):+.4f}")
    print(f"    std delta:    {np.std(perm_deltas):.4f}")
    print(f"    median delta: {np.median(perm_deltas):+.4f}")
    print(f"    2.5% / 97.5%: [{np.percentile(perm_deltas, 2.5):+.4f}, "
          f"{np.percentile(perm_deltas, 97.5):+.4f}]")
    print(f"\n  Real |delta| = {abs(real_delta_sharpe):.4f}")
    print(f"  p-value (two-sided) = {p_value:.4f}")

    if p_value < 0.05:
        print(f"  --> SIGNIFICANT at alpha=0.05")
    elif p_value < 0.10:
        print(f"  --> MARGINAL (0.05 < p < 0.10)")
    else:
        print(f"  --> NOT SIGNIFICANT (p >= 0.10)")
        print(f"  --> Difference is within parameter noise range")

    # Also report the slow_period landscape
    print(f"\n  Slow period landscape (Sharpe):")
    print(f"    {'slow':>6s}  {'Sharpe':>8s}  {'vs 120':>8s}")
    for s in sorted(sharpe_cache.keys()):
        sh = sharpe_cache[s]
        d = sh - sharpe_120
        marker = " <-- A" if s == 120 else (" <-- B" if s == 126 else "")
        print(f"    {s:6d}  {sh:8.4f}  {d:+8.4f}{marker}")

    return {
        "real_delta_sharpe": real_delta_sharpe,
        "real_delta_cagr": real_delta_cagr,
        "p_value_two_sided": p_value,
        "perm_mean": float(np.mean(perm_deltas)),
        "perm_std": float(np.std(perm_deltas)),
        "perm_p2.5": float(np.percentile(perm_deltas, 2.5)),
        "perm_p97.5": float(np.percentile(perm_deltas, 97.5)),
        "slow_landscape": {s: sharpe_cache[s] for s in sorted(sharpe_cache.keys())},
        "n_perm": N_PERM,
        "slow_range": [SLOW_RANGE[0], SLOW_RANGE[-1]],
    }


# ═══════════════════════════════════════════════════════════════════════════
# Phase 8: Pair Profile & Summary
# ═══════════════════════════════════════════════════════════════════════════

def phase8_summary(navs_a, navs_b, expo_a, expo_b, wi,
                   real_results, boot_results, paired_boot, sub_results,
                   dsr_results, subperiod_results, perm_results):
    print("\n" + "=" * 72)
    print("  PHASE 8: PAIR PROFILE & VERDICT SUMMARY")
    print("=" * 72)

    # Pair profile (tolerance-based)
    rets_a = returns_from_navs(navs_a, wi)
    rets_b = returns_from_navs(navs_b, wi)

    diff = np.abs(rets_a - rets_b)
    n_bars = len(rets_a)
    eq_1bp = float(np.mean(diff < 1e-4))
    eq_10bp = float(np.mean(diff < 1e-3))
    corr = float(np.corrcoef(rets_a, rets_b)[0, 1]) if np.std(rets_a) > 1e-15 else 1.0

    # Direction agreement
    same_dir = float(np.mean(np.sign(rets_a) == np.sign(rets_b)))

    # Exposure agreement
    expo_agree = float(np.mean(
        ((expo_a[wi+1:] > 0) & (expo_b[wi+1:] > 0)) |
        ((expo_a[wi+1:] <= 0) & (expo_b[wi+1:] <= 0))
    ))

    print(f"\n  Pair Profile (n={n_bars}):")
    print(f"    near_equal_1bp:      {eq_1bp:.1%}")
    print(f"    near_equal_10bp:     {eq_10bp:.1%}")
    print(f"    same_direction:      {same_dir:.1%}")
    print(f"    return_correlation:  {corr:.4f}")
    print(f"    exposure_agreement:  {expo_agree:.1%}")

    # Classification
    if eq_1bp > 0.95 and corr > 0.97:
        pair_class = "near_identical"
    elif eq_1bp > 0.80 or corr > 0.90:
        pair_class = "borderline"
    else:
        pair_class = "materially_different"

    sub_reliable = eq_1bp <= 0.80
    print(f"\n  Classification:        {pair_class}")
    print(f"  Subsampling reliable:  {sub_reliable}")

    # Aggregate evidence
    print(f"\n  Evidence Summary:")
    ma = real_results[CONFIG_A_LABEL]["metrics"]
    mb = real_results[CONFIG_B_LABEL]["metrics"]
    print(f"    Real data delta:     Sharpe {mb['sharpe'] - ma['sharpe']:+.4f}, "
          f"CAGR {mb['cagr'] - ma['cagr']:+.2f}%, MDD {mb['mdd'] - ma['mdd']:+.2f}%")

    # Paired bootstrap consensus (median across block sizes for Sharpe)
    sharpe_p_values = []
    for k, v in paired_boot.items():
        if v["metric"] == "sharpe":
            sharpe_p_values.append(v["p_a_better"])
    if sharpe_p_values:
        med_p = float(np.median(sharpe_p_values))
        print(f"    Paired bootstrap:    median p(A>B Sharpe) = {med_p:.3f}")

    # Subsampling
    if sub_results.get("grid_summary"):
        gs = sub_results["grid_summary"]
        print(f"    Subsampling:         median p(A>B) = {gs['median_p_a_better']:.3f}, "
              f"support = {gs['support_ratio']:.2f}")

    # DSR
    for label in [CONFIG_A_LABEL, CONFIG_B_LABEL]:
        d27 = dsr_results[label].get(27, {}).get("dsr_pvalue", float("nan"))
        d100 = dsr_results[label].get(100, {}).get("dsr_pvalue", float("nan"))
        print(f"    DSR [{label}]:   N=27 p={d27:.4f}, N=100 p={d100:.4f}")

    # Permutation
    perm_p = perm_results["p_value_two_sided"]
    print(f"    Permutation test:    p = {perm_p:.4f} (two-sided)")

    # Sub-period stability
    yearly = subperiod_results.get("yearly", {})
    if yearly:
        b_better_years = sum(1 for yr, d in yearly.items()
                            if d["B"]["sharpe"] > d["A"]["sharpe"])
        total_years = len(yearly)
        print(f"    Sub-period:          B better in {b_better_years}/{total_years} years")

    # Verdict
    print(f"\n  {'=' * 50}")
    if pair_class == "near_identical":
        print(f"  VERDICT: Configs are NEAR-IDENTICAL.")
        print(f"  slow=126 provides no meaningful improvement over slow=120.")
    elif perm_p >= 0.10:
        print(f"  VERDICT: Difference is WITHIN PARAMETER NOISE.")
        print(f"  Permutation p={perm_p:.3f} — cannot reject H0 that slow=120")
        print(f"  and slow=126 are statistically equivalent under parameter noise.")
    else:
        print(f"  VERDICT: EVIDENCE OF DIFFERENCE (requires human judgment).")
        print(f"  Classification: {pair_class}, perm_p={perm_p:.3f}")
    print(f"  {'=' * 50}")

    profile = {
        "n_bars": n_bars,
        "near_equal_1bp": eq_1bp,
        "near_equal_10bp": eq_10bp,
        "same_direction": same_dir,
        "return_correlation": corr,
        "exposure_agreement": expo_agree,
        "pair_class": pair_class,
        "subsampling_reliable": sub_reliable,
    }

    return profile


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("  VTREND-SM: slow_period=120 vs slow_period=126")
    print("  FULL STATISTICAL COMPARISON")
    print("  Cost: harsh (50 bps RT), Resolution: H4, Bootstrap: VCBB")
    print("=" * 72)

    t_global = time.time()
    cl, hi, lo, vo, tb, ts, wi, n = load_arrays()
    print(f"  Data: {n} H4 bars, warmup index: {wi}")

    # Phase 1: Real data
    real_results = phase1_real(cl, hi, lo, vo, tb, wi)
    navs_a = real_results[CONFIG_A_LABEL]["navs"]
    navs_b = real_results[CONFIG_B_LABEL]["navs"]
    expo_a = real_results[CONFIG_A_LABEL]["exposure"]
    expo_b = real_results[CONFIG_B_LABEL]["exposure"]

    # Phase 2: VCBB Bootstrap (both configs)
    boot_results = phase2_bootstrap(cl, hi, lo, vo, tb, wi, n)

    # Phase 3: Paired Block Bootstrap
    paired_boot = phase3_paired_bootstrap(navs_a, navs_b, expo_a, expo_b, wi)

    # Phase 4: Paired Block Subsampling
    sub_results = phase4_subsampling(navs_a, navs_b, expo_a, expo_b, wi)

    # Phase 5: DSR
    dsr_results = phase5_dsr(navs_a, navs_b, wi)

    # Phase 6: Sub-period analysis
    subperiod_results = phase6_subperiod(cl, hi, lo, vo, tb, ts, wi, n)

    # Phase 7: Permutation test
    perm_results = phase7_permutation(cl, hi, lo, vo, tb, wi, n)

    # Phase 8: Summary
    profile = phase8_summary(
        navs_a, navs_b, expo_a, expo_b, wi,
        real_results, boot_results, paired_boot, sub_results,
        dsr_results, subperiod_results, perm_results,
    )

    # ── Save all results ──
    outdir = ROOT / "out" / "vtrend_sm_slow126_study"
    outdir.mkdir(parents=True, exist_ok=True)

    def clean_for_json(obj):
        """Remove numpy arrays and convert types for JSON."""
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()
                    if not isinstance(v, np.ndarray)}
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    output = {
        "study": "vtrend_sm_slow120_vs_slow126",
        "date": "2026-03-05",
        "cost": "harsh (50 bps RT)",
        "n_boot": N_BOOT,
        "seed": SEED,
        "config_a": {"label": CONFIG_A_LABEL, "slow": 120,
                     "fast": PARAMS_A.fast, "entry_n": PARAMS_A.entry_n,
                     "exit_n": PARAMS_A.exit_n, "vol_lb": PARAMS_A.vol_lb},
        "config_b": {"label": CONFIG_B_LABEL, "slow": 126,
                     "fast": PARAMS_B.fast, "entry_n": PARAMS_B.entry_n,
                     "exit_n": PARAMS_B.exit_n, "vol_lb": PARAMS_B.vol_lb},
        "phase1_real": {
            CONFIG_A_LABEL: real_results[CONFIG_A_LABEL]["metrics"],
            CONFIG_B_LABEL: real_results[CONFIG_B_LABEL]["metrics"],
        },
        "phase2_bootstrap": {
            CONFIG_A_LABEL: boot_results[CONFIG_A_LABEL]["summary"],
            CONFIG_B_LABEL: boot_results[CONFIG_B_LABEL]["summary"],
        },
        "phase3_paired_bootstrap": paired_boot,
        "phase4_subsampling": sub_results,
        "phase5_dsr": dsr_results,
        "phase6_subperiod": subperiod_results,
        "phase7_permutation": perm_results,
        "phase8_profile": profile,
    }

    output = clean_for_json(output)
    with open(outdir / "results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    # Save raw bootstrap arrays
    ba = boot_results[CONFIG_A_LABEL]["raw"]
    bb = boot_results[CONFIG_B_LABEL]["raw"]
    np.savez(outdir / "bootstrap_raw.npz",
             a_sharpes=ba["sharpes"], a_cagrs=ba["cagrs"],
             a_mdds=ba["mdds"], a_calmars=ba["calmars"],
             b_sharpes=bb["sharpes"], b_cagrs=bb["cagrs"],
             b_mdds=bb["mdds"], b_calmars=bb["calmars"])

    elapsed = time.time() - t_global
    print(f"\n  Results saved to {outdir}")
    print(f"  Total runtime: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print("\n" + "=" * 72)
    print("  STUDY COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
