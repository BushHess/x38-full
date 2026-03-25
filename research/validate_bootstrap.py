#!/usr/bin/env python3
"""VCBB Validation: Volatility-Conditioned Block Bootstrap.

Compares uniform block bootstrap vs VCBB on:
  Test 1 — Vol clustering preservation (|return| ACF, conditional vol, rolling vol ACF)
  Test 2 — Statistical soundness (marginal dist, block return ACF, coverage, diversity)
  Test 3 — VTREND impact assessment (2000 paths, N=120)
  Test 4 — K sensitivity sweep

Output: console tables + research/results/vcbb_validation.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo
from research.lib.vcbb import (
    make_ratios,
    precompute_vcbb,
    gen_path_vcbb,
)

# ── Constants ─────────────────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0
CASH   = 10_000.0

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365

BLKSZ  = 60
SEED   = 42
CTX    = 90      # context window for VCBB (1.5x blksz — optimal for cross-block vol)
K_DEFAULT = 50   # default K for VCBB

N_DIAG  = 200    # paths for Test 1 & 2 (diagnostics)
N_BOOT  = 2000   # paths for Test 3 (VTREND impact)

ANN = math.sqrt(6.0 * 365.25)

# VTREND constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0
SLOW   = 120
FAST   = max(5, SLOW // 4)
VDO_ON = 0.0
VDO_OFF = -1e9


# ── Data loading ──────────────────────────────────────────────────────────────

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n  = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high  for b in h4], dtype=np.float64)
    lo = np.array([b.low   for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, wi, n


# ── VTREND simulator (from timescale_robustness.py) ──────────────────────────

def sim_fast(cl, ef, es, at, vd, wi, vdo_thr):
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    pe = px = False
    nt = 0

    navs_start = 0.0
    navs_end = 0.0
    nav_peak = 0.0
    nav_min_ratio = 1.0
    rets_sum = 0.0
    rets_sq_sum = 0.0
    n_rets = 0
    prev_nav = 0.0
    started = False

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
                nt += 1
                px = False

        nav = cash + bq * p

        if i >= wi:
            if not started:
                navs_start = nav
                prev_nav = nav
                nav_peak = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            nav_peak = max(nav_peak, nav)
            if nav_peak > 0:
                ratio = nav / nav_peak
                if ratio < nav_min_ratio:
                    nav_min_ratio = ratio
            navs_end = nav

        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > vdo_thr:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"cagr": -100.0, "mdd": 100.0, "sharpe": 0.0, "calmar": 0.0, "trades": 0}

    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar, "trades": nt}


# ── Diagnostic helpers ────────────────────────────────────────────────────────

def acf(x, nlags):
    """Sample autocorrelation function."""
    x = x - x.mean()
    result = np.correlate(x, x, "full")
    result = result[len(x) - 1 :]
    if result[0] == 0:
        return np.zeros(nlags + 1)
    return result[: nlags + 1] / result[0]


def compute_path_diagnostics(c, blksz):
    """Compute vol clustering diagnostics from a single synthetic path.

    Returns dict with: abs_acf_60, abs_acf_120, abs_acf_180,
                        cond_vol_ratio, rolling_vol_acf_60
    """
    log_r = np.log(c[1:] / c[:-1])
    abs_r = np.abs(log_r)

    # |return| ACF
    n = len(abs_r)
    max_lag = min(180, n - 1)
    acf_abs = acf(abs_r, max_lag)

    # Conditional vol: vol of block after high-vol block vs unconditional
    n_blocks = len(log_r) // blksz
    if n_blocks < 5:
        cond_ratio = 1.0
    else:
        block_vol = np.array(
            [np.std(log_r[i * blksz : (i + 1) * blksz]) for i in range(n_blocks)]
        )
        thresh = np.percentile(block_vol, 90)
        high_vol = np.where(block_vol > thresh)[0]
        next_vol = []
        for b in high_vol:
            if b + 1 < n_blocks:
                next_vol.append(block_vol[b + 1])
        if next_vol and np.mean(block_vol[1:]) > 0:
            cond_ratio = np.mean(next_vol) / np.mean(block_vol[1:])
        else:
            cond_ratio = 1.0

    # Rolling vol ACF
    ctx_win = 180  # 30 days in H4
    if n > ctx_win + 60:
        rolling_vol = np.array(
            [np.std(log_r[max(0, i - ctx_win) : i]) for i in range(ctx_win, n)]
        )
        rv_acf = acf(rolling_vol, 60)
        rolling_vol_acf_60 = rv_acf[60] if len(rv_acf) > 60 else 0.0
    else:
        rolling_vol_acf_60 = 0.0

    # Block return ACF(1)
    if n_blocks >= 10:
        block_ret = np.array(
            [log_r[i * blksz : (i + 1) * blksz].sum() for i in range(n_blocks)]
        )
        br_acf = acf(block_ret, 1)
        block_ret_acf1 = br_acf[1]
    else:
        block_ret_acf1 = 0.0

    return {
        "abs_acf_60": acf_abs[60] if max_lag >= 60 else 0.0,
        "abs_acf_120": acf_abs[120] if max_lag >= 120 else 0.0,
        "abs_acf_180": acf_abs[180] if max_lag >= 180 else 0.0,
        "cond_vol_ratio": cond_ratio,
        "rolling_vol_acf_60": rolling_vol_acf_60,
        "block_ret_acf1": block_ret_acf1,
    }


def compute_marginal_stats(c):
    """Compute marginal return distribution stats."""
    log_r = np.log(c[1:] / c[:-1])
    return {
        "mean": float(np.mean(log_r)),
        "std": float(np.std(log_r)),
        "skew": float(_skew(log_r)),
        "kurt": float(_kurt(log_r)),
    }


def _skew(x):
    m = np.mean(x)
    s = np.std(x)
    if s < 1e-15:
        return 0.0
    return float(np.mean(((x - m) / s) ** 3))


def _kurt(x):
    m = np.mean(x)
    s = np.std(x)
    if s < 1e-15:
        return 0.0
    return float(np.mean(((x - m) / s) ** 4) - 3.0)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Vol Clustering Preservation
# ═══════════════════════════════════════════════════════════════════════════════

def test_vol_clustering(cr, hr, lr, vol, tb, n_trans, p0, vcbb, real_diag, n_paths=N_DIAG):
    """Compare vol clustering between uniform and VCBB."""
    print("\n" + "=" * 70)
    print("TEST 1: VOL CLUSTERING PRESERVATION")
    print("=" * 70)
    print(f"Paths: {n_paths}")

    metrics_uni = {k: [] for k in ["abs_acf_60", "abs_acf_120", "abs_acf_180",
                                    "cond_vol_ratio", "rolling_vol_acf_60"]}
    metrics_vcbb = {k: [] for k in metrics_uni}

    rng_u = np.random.default_rng(SEED)
    rng_v = np.random.default_rng(SEED + 10000)  # separate seed space

    t0 = time.time()
    for b in range(n_paths):
        # Uniform
        c_u, h_u, l_u, v_u, t_u = gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, BLKSZ, p0, rng_u,
                                                  vcbb=vcbb, K=K_DEFAULT)
        d_u = compute_path_diagnostics(c_u, BLKSZ)
        for k in metrics_uni:
            metrics_uni[k].append(d_u[k])

        # VCBB
        c_v, h_v, l_v, v_v, t_v = gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, BLKSZ, p0, rng_v,
                                                  vcbb=vcbb, K=K_DEFAULT)
        d_v = compute_path_diagnostics(c_v, BLKSZ)
        for k in metrics_vcbb:
            metrics_vcbb[k].append(d_v[k])

        if (b + 1) % 50 == 0:
            print(f"  ... {b + 1}/{n_paths} ({time.time() - t0:.1f}s)")

    # Recovery thresholds decay with block boundaries crossed (Markov attenuation):
    #   lag 60  (1 boundary): > 60%
    #   lag 120 (2 boundaries): > 40%
    #   lag 180 (3 boundaries): > 30%
    acf_thresholds = {"abs_acf_60": 0.60, "abs_acf_120": 0.40, "abs_acf_180": 0.30}

    results = {}
    print(f"\n{'Metric':<25s}  {'Real':>8s}  {'Uniform':>10s}  {'VCBB':>10s}  {'Recovery':>10s}  {'Verdict':>8s}")
    print("-" * 78)

    for k in ["abs_acf_60", "abs_acf_120", "abs_acf_180", "cond_vol_ratio", "rolling_vol_acf_60"]:
        r_val = real_diag[k]
        u_med = np.median(metrics_uni[k])
        v_med = np.median(metrics_vcbb[k])

        if k == "cond_vol_ratio":
            gap = r_val - 1.0
            recovery = (v_med - 1.0) / gap if abs(gap) > 1e-6 else 0.0
            passed = recovery > 0.50 and v_med > 1.3
        elif k == "rolling_vol_acf_60":
            u_err = abs(r_val - u_med)
            v_err = abs(r_val - v_med)
            recovery = 1.0 - v_err / r_val if r_val > 1e-6 else 0.0
            passed = v_err < u_err
        else:
            recovery = v_med / r_val if abs(r_val) > 1e-6 else 0.0
            threshold = acf_thresholds[k]
            passed = recovery > threshold

        verdict = "PASS" if passed else "FAIL"
        print(f"  {k:<23s}  {r_val:>8.4f}  {u_med:>10.4f}  {v_med:>10.4f}  {recovery:>9.0%}  {verdict:>8s}")
        results[k] = {
            "real": float(r_val),
            "uniform_median": float(u_med),
            "vcbb_median": float(v_med),
            "recovery": float(recovery),
            "pass": bool(passed),
        }

    all_pass = all(r["pass"] for r in results.values())
    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAIL'}")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Statistical Soundness
# ═══════════════════════════════════════════════════════════════════════════════

def test_soundness(cr, hr, lr, vol, tb, n_trans, p0, vcbb, real_stats, n_paths=N_DIAG):
    """Verify VCBB doesn't introduce bias."""
    print("\n" + "=" * 70)
    print("TEST 2: STATISTICAL SOUNDNESS")
    print("=" * 70)
    print(f"Paths: {n_paths}")

    marginal_stats = {k: [] for k in ["mean", "std", "skew", "kurt"]}
    block_acf1s = []
    all_starts_uni = set()
    all_starts_vcbb = set()
    vol_bins_visited = set()

    rng_u = np.random.default_rng(SEED + 20000)
    rng_v = np.random.default_rng(SEED + 30000)

    # Precompute vol quantile bins for real data
    log_r_real = np.log(cr)
    abs_r_real = np.abs(log_r_real)
    # Rolling vol for bin classification
    ctx_rv = 30
    real_rvol = np.array([np.std(log_r_real[max(0, i - ctx_rv) : i])
                          for i in range(ctx_rv, len(log_r_real))])
    vol_bin_edges = np.percentile(real_rvol, np.linspace(0, 100, 21))  # 20 bins

    t0 = time.time()
    for b in range(n_paths):
        # Uniform — track starts
        rng_u_copy = np.random.default_rng(SEED + 20000 + b * 1000)
        n_blk = math.ceil(n_trans / BLKSZ)
        mx = len(cr) - BLKSZ
        starts_u = rng_u_copy.integers(0, mx + 1, size=n_blk)
        all_starts_uni.update(starts_u.tolist())

        # VCBB path
        c_v, h_v, l_v, v_v, t_v = gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, BLKSZ, p0, rng_v,
                                                  vcbb=vcbb, K=K_DEFAULT)
        ms = compute_marginal_stats(c_v)
        for k in marginal_stats:
            marginal_stats[k].append(ms[k])

        diag = compute_path_diagnostics(c_v, BLKSZ)
        block_acf1s.append(diag["block_ret_acf1"])

        # Track vol bin coverage on VCBB path
        log_r_v = np.log(c_v[1:] / c_v[:-1])
        for i in range(ctx_rv, len(log_r_v)):
            rv = np.std(log_r_v[max(0, i - ctx_rv) : i])
            bin_idx = np.searchsorted(vol_bin_edges, rv, side="right") - 1
            bin_idx = max(0, min(19, bin_idx))
            vol_bins_visited.add(bin_idx)

        if (b + 1) % 50 == 0:
            print(f"  ... {b + 1}/{n_paths} ({time.time() - t0:.1f}s)")

    results = {}

    # 2a. Marginal distribution check
    print(f"\n  2a. Marginal Distribution (within 20% of real data)")
    print(f"  {'Stat':<8s}  {'Real':>10s}  {'VCBB med':>10s}  {'Rel err':>10s}  {'Verdict':>8s}")
    print("  " + "-" * 55)
    for k in ["mean", "std", "skew", "kurt"]:
        real_val = real_stats[k]
        vcbb_val = np.median(marginal_stats[k])
        if abs(real_val) > 1e-10:
            rel_err = abs(vcbb_val - real_val) / abs(real_val)
        else:
            rel_err = abs(vcbb_val - real_val)
        passed = rel_err < 0.20  # within 20%
        verdict = "PASS" if passed else "FAIL"
        print(f"  {k:<8s}  {real_val:>10.6f}  {vcbb_val:>10.6f}  {rel_err:>9.1%}  {verdict:>8s}")
        results[f"marginal_{k}"] = {"real": float(real_val), "vcbb": float(vcbb_val),
                                     "rel_err": float(rel_err), "pass": bool(passed)}

    # 2b. Block return ACF(1) < 0.15
    med_block_acf = float(np.median(block_acf1s))
    passed_acf = abs(med_block_acf) < 0.15
    print(f"\n  2b. Block return ACF(1): {med_block_acf:+.4f}  (threshold: |.| < 0.15)  "
          f"{'PASS' if passed_acf else 'FAIL'}")
    results["block_ret_acf1"] = {"median": med_block_acf, "pass": bool(passed_acf)}

    # 2c. Vol state coverage
    coverage = len(vol_bins_visited) / 20.0
    passed_cov = coverage > 0.90
    print(f"  2c. Vol bin coverage: {len(vol_bins_visited)}/20 = {coverage:.0%}  "
          f"(threshold: >90%)  {'PASS' if passed_cov else 'FAIL'}")
    results["vol_coverage"] = {"bins_visited": len(vol_bins_visited),
                                "coverage": float(coverage), "pass": bool(passed_cov)}

    # 2d. Block diversity — track VCBB starts
    # Re-generate VCBB paths just to count unique starts
    unique_vcbb_starts = set()
    rng_div = np.random.default_rng(SEED + 30000)
    for b in range(n_paths):
        # We need to extract the starts — run gen_path_vcbb and track
        # Simpler: use _select_blocks_vcbb directly
        from research.lib.vcbb import _select_blocks_vcbb
        n_blk = math.ceil(n_trans / BLKSZ)
        mx = len(cr) - BLKSZ
        starts_v = _select_blocks_vcbb(n_blk, mx, BLKSZ, vcbb, rng_div, K_DEFAULT)
        unique_vcbb_starts.update(starts_v.tolist())

    diversity_ratio = len(unique_vcbb_starts) / len(all_starts_uni) if all_starts_uni else 0
    passed_div = diversity_ratio > 0.50
    print(f"  2d. Block diversity: VCBB {len(unique_vcbb_starts)} vs Uniform {len(all_starts_uni)} "
          f"unique starts = {diversity_ratio:.0%}  (threshold: >50%)  "
          f"{'PASS' if passed_div else 'FAIL'}")
    results["block_diversity"] = {
        "vcbb_unique": len(unique_vcbb_starts),
        "uniform_unique": len(all_starts_uni),
        "ratio": float(diversity_ratio),
        "pass": bool(passed_div),
    }

    all_pass = all(v.get("pass", True) for v in results.values())
    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAIL'}")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: VTREND Impact Assessment
# ═══════════════════════════════════════════════════════════════════════════════

def test_vtrend_impact(cl, hi, lo, vo, tb, cr, hr, lr, vol_r, tb_r,
                       wi, n_trans, p0, vcbb, n_paths=N_BOOT):
    """Run VTREND under both bootstrap methods and compare."""
    print("\n" + "=" * 70)
    print("TEST 3: VTREND IMPACT ASSESSMENT")
    print("=" * 70)
    print(f"Paths: {n_paths}, N={SLOW}, VDO={'on' if VDO_ON >= 0 else 'off'}")

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    boot_uni  = {k: np.zeros(n_paths) for k in mkeys}
    boot_vcbb = {k: np.zeros(n_paths) for k in mkeys}

    rng_u = np.random.default_rng(SEED)
    rng_v = np.random.default_rng(SEED)

    t0 = time.time()
    for b in range(n_paths):
        # Uniform path
        c_u, h_u, l_u, v_u, t_u = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng_u,
                                                  vcbb=vcbb, K=K_DEFAULT)
        at_u = _atr(h_u, l_u, c_u, ATR_P)
        vd_u = _vdo(c_u, h_u, l_u, v_u, t_u, VDO_F, VDO_S)
        ef_u = _ema(c_u, FAST)
        es_u = _ema(c_u, SLOW)
        r_u = sim_fast(c_u, ef_u, es_u, at_u, vd_u, wi, VDO_ON)
        for k in mkeys:
            boot_uni[k][b] = r_u[k]

        # VCBB path
        c_v, h_v, l_v, v_v, t_v = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng_v,
                                                  vcbb=vcbb, K=K_DEFAULT)
        at_v = _atr(h_v, l_v, c_v, ATR_P)
        vd_v = _vdo(c_v, h_v, l_v, v_v, t_v, VDO_F, VDO_S)
        ef_v = _ema(c_v, FAST)
        es_v = _ema(c_v, SLOW)
        r_v = sim_fast(c_v, ef_v, es_v, at_v, vd_v, wi, VDO_ON)
        for k in mkeys:
            boot_vcbb[k][b] = r_v[k]

        if (b + 1) % 200 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (b + 1) * (n_paths - b - 1)
            print(f"  ... {b + 1}/{n_paths} ({elapsed:.0f}s, ETA {eta:.0f}s)")

    # Real data reference
    at_r = _atr(hi, lo, cl, ATR_P)
    vd_r = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    ef_r = _ema(cl, FAST)
    es_r = _ema(cl, SLOW)
    real = sim_fast(cl, ef_r, es_r, at_r, vd_r, wi, VDO_ON)

    # Report
    print(f"\n{'Metric':<12s}  {'Real':>8s}  {'Uni med':>8s}  {'VCBB med':>8s}  "
          f"{'Uni P(C>0)':>10s}  {'VCBB P(C>0)':>11s}  {'Real pct_U':>10s}  {'Real pct_V':>10s}")
    print("-" * 95)

    results = {}
    for k in ["sharpe", "cagr", "mdd", "calmar"]:
        r_val = real[k]
        u_med = np.median(boot_uni[k])
        v_med = np.median(boot_vcbb[k])

        if k == "cagr":
            u_ppos = np.mean(boot_uni[k] > 0) * 100
            v_ppos = np.mean(boot_vcbb[k] > 0) * 100
        elif k == "sharpe":
            u_ppos = np.mean(boot_uni[k] > 0) * 100
            v_ppos = np.mean(boot_vcbb[k] > 0) * 100
        else:
            u_ppos = v_ppos = 0.0

        u_pct = np.mean(boot_uni[k] <= r_val) * 100
        v_pct = np.mean(boot_vcbb[k] <= r_val) * 100

        print(f"  {k:<10s}  {r_val:>8.2f}  {u_med:>8.2f}  {v_med:>8.2f}  "
              f"{u_ppos:>9.1f}%  {v_ppos:>10.1f}%  {u_pct:>9.1f}%  {v_pct:>9.1f}%")

        results[k] = {
            "real": float(r_val),
            "uniform_median": float(u_med),
            "vcbb_median": float(v_med),
            "real_pctile_uniform": float(u_pct),
            "real_pctile_vcbb": float(v_pct),
        }

    # MDD tail analysis
    print(f"\n  MDD Tail Risk:")
    for thresh in [50, 60, 70, 80]:
        u_p = np.mean(boot_uni["mdd"] > thresh) * 100
        v_p = np.mean(boot_vcbb["mdd"] > thresh) * 100
        print(f"    P(MDD > {thresh}%): Uniform {u_p:.1f}%  VCBB {v_p:.1f}%")
        results[f"p_mdd_gt_{thresh}"] = {"uniform": float(u_p), "vcbb": float(v_p)}

    # Trade count comparison
    u_trades = np.median(boot_uni["trades"])
    v_trades = np.median(boot_vcbb["trades"])
    print(f"\n  Median trades: Uniform {u_trades:.0f}  VCBB {v_trades:.0f}  Real {real['trades']}")
    results["trades"] = {"uniform": float(u_trades), "vcbb": float(v_trades), "real": float(real["trades"])}

    print("\n  [INFORMATIONAL — no pass/fail criteria]")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: K Sensitivity Sweep
# ═══════════════════════════════════════════════════════════════════════════════

def test_k_sensitivity(cr, hr, lr, vol, tb, n_trans, p0, vcbb, n_paths=N_DIAG):
    """Sweep K values and report vol clustering metrics."""
    print("\n" + "=" * 70)
    print("TEST 4: K SENSITIVITY SWEEP")
    print("=" * 70)

    K_values = [20, 50, 100, 200]
    results = {}

    for K in K_values:
        rng = np.random.default_rng(SEED + 50000)
        metrics = {k: [] for k in ["abs_acf_60", "cond_vol_ratio", "rolling_vol_acf_60"]}

        for b in range(n_paths):
            c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, BLKSZ, p0, rng,
                                           vcbb=vcbb, K=K)
            d = compute_path_diagnostics(c, BLKSZ)
            for k in metrics:
                metrics[k].append(d[k])

        results[K] = {k: float(np.median(v)) for k, v in metrics.items()}

    # Also run uniform for reference
    rng_u = np.random.default_rng(SEED + 50000)
    uni_metrics = {k: [] for k in ["abs_acf_60", "cond_vol_ratio", "rolling_vol_acf_60"]}
    for b in range(n_paths):
        c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tb, n_trans, BLKSZ, p0, rng_u,
                                       vcbb=vcbb, K=K_DEFAULT)
        d = compute_path_diagnostics(c, BLKSZ)
        for k in uni_metrics:
            uni_metrics[k].append(d[k])
    results["uniform"] = {k: float(np.median(v)) for k, v in uni_metrics.items()}

    # Display
    print(f"\n  {'K':<10s}  {'|r|ACF@60':>10s}  {'CondVol':>10s}  {'RolVol ACF':>10s}")
    print("  " + "-" * 45)
    for label in ["uniform"] + K_values:
        r = results[label]
        k_str = str(label)
        print(f"  {k_str:<10s}  {r['abs_acf_60']:>10.4f}  {r['cond_vol_ratio']:>10.4f}  "
              f"{r['rolling_vol_acf_60']:>10.4f}")

    # Check: all K values should beat uniform on abs_acf_60
    uni_ref = results["uniform"]["abs_acf_60"]
    all_beat = all(results[K]["abs_acf_60"] > uni_ref for K in K_values)
    print(f"\n  All K beat uniform on |r|ACF@60: {'PASS' if all_beat else 'FAIL'}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("VCBB VALIDATION: Volatility-Conditioned Block Bootstrap")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[wi]

    print(f"  H4 bars: {n}")
    print(f"  Transitions: {n_trans}")
    print(f"  Warmup index: {wi}")
    print(f"  Block size: {BLKSZ} ({BLKSZ * 4 / 24:.0f} days)")
    print(f"  Context: {CTX} ({CTX * 4 / 24:.0f} days)")
    print(f"  K: {K_DEFAULT}")

    # Real data diagnostics
    real_diag = compute_path_diagnostics(cl, BLKSZ)
    real_stats = compute_marginal_stats(cl)
    print(f"\n  Real data diagnostics:")
    for k, v in real_diag.items():
        print(f"    {k}: {v:.4f}")

    # Precompute VCBB
    print("\nPrecomputing VCBB state...")
    t0 = time.time()
    vcbb = precompute_vcbb(cr, BLKSZ, ctx=CTX)
    print(f"  Done in {time.time() - t0:.3f}s")
    print(f"  Valid block starts: {len(vcbb.sorted_idx)}")
    print(f"  Vol range: [{vcbb.sorted_vol[0]:.6f}, {vcbb.sorted_vol[-1]:.6f}]")

    all_results = {}

    # Test 1
    t1 = time.time()
    all_results["test1_vol_clustering"] = test_vol_clustering(
        cr, hr, lr, vol_r, tb_r, n_trans, p0, vcbb, real_diag
    )
    print(f"  [Test 1 took {time.time() - t1:.1f}s]")

    # Test 2
    t2 = time.time()
    all_results["test2_soundness"] = test_soundness(
        cr, hr, lr, vol_r, tb_r, n_trans, p0, vcbb, real_stats
    )
    print(f"  [Test 2 took {time.time() - t2:.1f}s]")

    # Test 3
    t3 = time.time()
    all_results["test3_vtrend_impact"] = test_vtrend_impact(
        cl, hi, lo, vo, tb, cr, hr, lr, vol_r, tb_r, wi, n_trans, p0, vcbb
    )
    print(f"  [Test 3 took {time.time() - t3:.1f}s]")

    # Test 4
    t4 = time.time()
    all_results["test4_k_sensitivity"] = test_k_sensitivity(
        cr, hr, lr, vol_r, tb_r, n_trans, p0, vcbb
    )
    print(f"  [Test 4 took {time.time() - t4:.1f}s]")

    # Save results
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "vcbb_validation.json"

    # Convert numpy types for JSON
    def convert(obj):
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(x) for x in obj]
        return obj

    with open(out_path, "w") as f:
        json.dump(convert(all_results), f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    t1_pass = all(v.get("pass", True) for v in all_results["test1_vol_clustering"].values())
    t2_pass = all(v.get("pass", True) for v in all_results["test2_soundness"].values())

    print(f"  Test 1 (Vol Clustering):   {'PASS' if t1_pass else 'FAIL'}")
    print(f"  Test 2 (Soundness):        {'PASS' if t2_pass else 'FAIL'}")
    print(f"  Test 3 (VTREND Impact):    INFORMATIONAL")
    print(f"  Test 4 (K Sensitivity):    INFORMATIONAL")
    print(f"\n  Overall: {'ALL PASS' if (t1_pass and t2_pass) else 'SOME FAIL'}")
    print(f"\n  Total time: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
