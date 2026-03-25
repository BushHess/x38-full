#!/usr/bin/env python3
"""VCBB vs Uniform: Do Research Conclusions Change?

The definitive test: run the VDO on/off paired comparison under BOTH
bootstrap methods (uniform and VCBB) across 16 timescales × 2000 paths.

If conclusions are unchanged → VCBB improves accuracy but findings stand.
If conclusions change → previous results were biased by vol clustering destruction.

Output: console tables + research/results/vcbb_vs_uniform.json
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
CTX    = 90
K      = 50

N_BOOT = 2000

ANN = math.sqrt(6.0 * 365.25)

# VTREND structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

# Timescale grid (same as timescale_robustness.py)
SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

VDO_ON  = 0.0
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


# ── VTREND simulator ─────────────────────────────────────────────────────────

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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("VCBB vs UNIFORM: Do Research Conclusions Change?")
    print("=" * 80)
    print(f"VDO on/off paired comparison × 16 timescales × {N_BOOT} paths × 2 bootstrap methods")

    # Load data
    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]

    print(f"  H4 bars: {n}, transitions: {n_trans}, warmup: {wi}")

    # Precompute VCBB
    print("Precomputing VCBB state...")
    vcbb = precompute_vcbb(cr, BLKSZ, ctx=CTX)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "calmar"]

    # Storage: [method][variant][metric] → (N_BOOT, n_sp)
    results = {}
    for method in ["uniform", "vcbb"]:
        results[method] = {}
        for variant in ["on", "off"]:
            results[method][variant] = {k: np.zeros((N_BOOT, n_sp)) for k in mkeys}

    # ── Bootstrap loop ────────────────────────────────────────────────────────
    # Same seed for both methods → same random number sequence for fair comparison

    t0 = time.time()

    for b in range(N_BOOT):
        rng_u = np.random.default_rng(SEED + b)
        rng_v = np.random.default_rng(SEED + b)

        # Generate ONE path per method (shared across timescales)
        c_u, h_u, l_u, v_u, t_u = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng_u,
                                                   vcbb=vcbb, K=K)
        c_v, h_v, l_v, v_v, t_v = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng_v,
                                                   vcbb=vcbb, K=K)

        # Precompute per-path: ATR, VDO (shared across timescales)
        at_u = _atr(h_u, l_u, c_u, ATR_P)
        vd_u = _vdo(c_u, h_u, l_u, v_u, t_u, VDO_F, VDO_S)
        at_v = _atr(h_v, l_v, c_v, ATR_P)
        vd_v = _vdo(c_v, h_v, l_v, v_v, t_v, VDO_F, VDO_S)

        for j, slow in enumerate(SLOW_PERIODS):
            fast = max(5, slow // 4)

            # Uniform: VDO on/off
            ef_u = _ema(c_u, fast)
            es_u = _ema(c_u, slow)
            r_on_u  = sim_fast(c_u, ef_u, es_u, at_u, vd_u, wi, VDO_ON)
            r_off_u = sim_fast(c_u, ef_u, es_u, at_u, vd_u, wi, VDO_OFF)
            for k in mkeys:
                results["uniform"]["on"][k][b, j] = r_on_u[k]
                results["uniform"]["off"][k][b, j] = r_off_u[k]

            # VCBB: VDO on/off
            ef_v = _ema(c_v, fast)
            es_v = _ema(c_v, slow)
            r_on_v  = sim_fast(c_v, ef_v, es_v, at_v, vd_v, wi, VDO_ON)
            r_off_v = sim_fast(c_v, ef_v, es_v, at_v, vd_v, wi, VDO_OFF)
            for k in mkeys:
                results["vcbb"]["on"][k][b, j] = r_on_v[k]
                results["vcbb"]["off"][k][b, j] = r_off_v[k]

        if (b + 1) % 100 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (b + 1) * (N_BOOT - b - 1)
            print(f"  ... {b + 1}/{N_BOOT} ({elapsed:.0f}s, ETA {eta:.0f}s)")

    total_time = time.time() - t0
    print(f"\n  Bootstrap complete in {total_time:.0f}s")

    # ── Analysis ──────────────────────────────────────────────────────────────

    print("\n" + "=" * 80)
    print("RESULTS: VDO Contribution — Uniform vs VCBB")
    print("=" * 80)

    # Per-timescale comparison
    header = (f"{'N':>5s}  {'days':>5s}  │ {'Uni Sh+':>7s} {'VCB Sh+':>7s}  │ "
              f"{'Uni ΔSh':>7s} {'VCB ΔSh':>7s}  │ {'Uni MDD-':>8s} {'VCB MDD-':>8s}  │ "
              f"{'Uni ΔMD':>7s} {'VCB ΔMD':>7s}")
    print(f"\n{header}")
    print("-" * 105)

    json_out = {"timescales": [], "summary": {}}

    # Track wins for binomial test
    uni_sh_wins = 0
    vcb_sh_wins = 0
    uni_mdd_wins = 0
    vcb_mdd_wins = 0

    for j, slow in enumerate(SLOW_PERIODS):
        days = slow * 4 / 24

        # Uniform: P(VDO improves Sharpe) and delta
        sh_on_u  = results["uniform"]["on"]["sharpe"][:, j]
        sh_off_u = results["uniform"]["off"]["sharpe"][:, j]
        p_sh_u = np.mean(sh_on_u > sh_off_u) * 100
        delta_sh_u = np.median(sh_on_u) - np.median(sh_off_u)
        if p_sh_u > 50:
            uni_sh_wins += 1

        # VCBB: P(VDO improves Sharpe) and delta
        sh_on_v  = results["vcbb"]["on"]["sharpe"][:, j]
        sh_off_v = results["vcbb"]["off"]["sharpe"][:, j]
        p_sh_v = np.mean(sh_on_v > sh_off_v) * 100
        delta_sh_v = np.median(sh_on_v) - np.median(sh_off_v)
        if p_sh_v > 50:
            vcb_sh_wins += 1

        # Uniform: P(VDO reduces MDD) and delta
        mdd_on_u  = results["uniform"]["on"]["mdd"][:, j]
        mdd_off_u = results["uniform"]["off"]["mdd"][:, j]
        p_mdd_u = np.mean(mdd_on_u < mdd_off_u) * 100
        delta_mdd_u = np.median(mdd_on_u) - np.median(mdd_off_u)
        if p_mdd_u > 50:
            uni_mdd_wins += 1

        # VCBB: P(VDO reduces MDD) and delta
        mdd_on_v  = results["vcbb"]["on"]["mdd"][:, j]
        mdd_off_v = results["vcbb"]["off"]["mdd"][:, j]
        p_mdd_v = np.mean(mdd_on_v < mdd_off_v) * 100
        delta_mdd_v = np.median(mdd_on_v) - np.median(mdd_off_v)
        if p_mdd_v > 50:
            vcb_mdd_wins += 1

        print(f"  {slow:>4d}  {days:>4.0f}d  │ {p_sh_u:>6.1f}% {p_sh_v:>6.1f}%  │ "
              f"{delta_sh_u:>+6.3f} {delta_sh_v:>+6.3f}  │ "
              f"{p_mdd_u:>7.1f}% {p_mdd_v:>7.1f}%  │ "
              f"{delta_mdd_u:>+6.1f} {delta_mdd_v:>+6.1f}")

        json_out["timescales"].append({
            "N": slow,
            "days": round(days, 1),
            "uniform": {
                "p_sharpe_plus": round(float(p_sh_u), 2),
                "delta_sharpe": round(float(delta_sh_u), 4),
                "median_sharpe_on": round(float(np.median(sh_on_u)), 4),
                "median_sharpe_off": round(float(np.median(sh_off_u)), 4),
                "p_mdd_minus": round(float(p_mdd_u), 2),
                "delta_mdd": round(float(delta_mdd_u), 2),
                "median_mdd_on": round(float(np.median(mdd_on_u)), 2),
                "median_mdd_off": round(float(np.median(mdd_off_u)), 2),
            },
            "vcbb": {
                "p_sharpe_plus": round(float(p_sh_v), 2),
                "delta_sharpe": round(float(delta_sh_v), 4),
                "median_sharpe_on": round(float(np.median(sh_on_v)), 4),
                "median_sharpe_off": round(float(np.median(sh_off_v)), 4),
                "p_mdd_minus": round(float(p_mdd_v), 2),
                "delta_mdd": round(float(delta_mdd_v), 2),
                "median_mdd_on": round(float(np.median(mdd_on_v)), 2),
                "median_mdd_off": round(float(np.median(mdd_off_v)), 2),
            },
        })

    # ── Binomial meta-test ────────────────────────────────────────────────────

    from scipy import stats as sp_stats

    print("\n" + "-" * 80)
    print("BINOMIAL META-TEST: VDO helps at how many timescales?")
    print("-" * 80)

    for label, uni_w, vcb_w in [
        ("P(Sharpe+) > 50%", uni_sh_wins, vcb_sh_wins),
        ("P(MDD-)   > 50%", uni_mdd_wins, vcb_mdd_wins),
    ]:
        p_uni = sp_stats.binomtest(uni_w, n_sp, 0.5, alternative='greater').pvalue
        p_vcb = sp_stats.binomtest(vcb_w, n_sp, 0.5, alternative='greater').pvalue
        print(f"  {label}:  Uniform {uni_w}/{n_sp} (p={p_uni:.2e})  "
              f"VCBB {vcb_w}/{n_sp} (p={p_vcb:.2e})")

    json_out["summary"]["binomial"] = {
        "sharpe": {
            "uniform_wins": uni_sh_wins,
            "vcbb_wins": vcb_sh_wins,
            "uniform_p": float(sp_stats.binomtest(uni_sh_wins, n_sp, 0.5, alternative='greater').pvalue),
            "vcbb_p": float(sp_stats.binomtest(vcb_sh_wins, n_sp, 0.5, alternative='greater').pvalue),
        },
        "mdd": {
            "uniform_wins": uni_mdd_wins,
            "vcbb_wins": vcb_mdd_wins,
            "uniform_p": float(sp_stats.binomtest(uni_mdd_wins, n_sp, 0.5, alternative='greater').pvalue),
            "vcbb_p": float(sp_stats.binomtest(vcb_mdd_wins, n_sp, 0.5, alternative='greater').pvalue),
        },
    }

    # ── Aggregate effect sizes ────────────────────────────────────────────────

    print("\n" + "-" * 80)
    print("AGGREGATE EFFECT SIZES (median across timescales)")
    print("-" * 80)

    for metric in ["sharpe", "cagr", "mdd"]:
        uni_on_meds  = [float(np.median(results["uniform"]["on"][metric][:, j])) for j in range(n_sp)]
        uni_off_meds = [float(np.median(results["uniform"]["off"][metric][:, j])) for j in range(n_sp)]
        vcb_on_meds  = [float(np.median(results["vcbb"]["on"][metric][:, j])) for j in range(n_sp)]
        vcb_off_meds = [float(np.median(results["vcbb"]["off"][metric][:, j])) for j in range(n_sp)]

        uni_deltas = [a - b for a, b in zip(uni_on_meds, uni_off_meds)]
        vcb_deltas = [a - b for a, b in zip(vcb_on_meds, vcb_off_meds)]

        print(f"\n  {metric.upper()}:")
        print(f"    Uniform VDO delta: median {np.median(uni_deltas):+.4f}, "
              f"range [{min(uni_deltas):+.4f}, {max(uni_deltas):+.4f}]")
        print(f"    VCBB    VDO delta: median {np.median(vcb_deltas):+.4f}, "
              f"range [{min(vcb_deltas):+.4f}, {max(vcb_deltas):+.4f}]")
        print(f"    Median ON  — Uniform: {np.median(uni_on_meds):.4f}, VCBB: {np.median(vcb_on_meds):.4f}")
        print(f"    Median OFF — Uniform: {np.median(uni_off_meds):.4f}, VCBB: {np.median(vcb_off_meds):.4f}")

        json_out["summary"][metric] = {
            "uniform_vdo_delta_median": round(float(np.median(uni_deltas)), 4),
            "vcbb_vdo_delta_median": round(float(np.median(vcb_deltas)), 4),
            "uniform_on_median": round(float(np.median(uni_on_meds)), 4),
            "vcbb_on_median": round(float(np.median(vcb_on_meds)), 4),
            "uniform_off_median": round(float(np.median(uni_off_meds)), 4),
            "vcbb_off_median": round(float(np.median(vcb_off_meds)), 4),
        }

    # ── Conclusion ────────────────────────────────────────────────────────────

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    # Check if conclusions agree
    sh_agree = (uni_sh_wins == vcb_sh_wins) or (abs(uni_sh_wins - vcb_sh_wins) <= 1)
    mdd_agree = (uni_mdd_wins == vcb_mdd_wins) or (abs(uni_mdd_wins - vcb_mdd_wins) <= 1)

    if sh_agree and mdd_agree:
        print("  QUALITATIVE AGREEMENT: Uniform and VCBB give same VDO conclusion.")
        print("  → VCBB improves accuracy but does NOT change research findings.")
    else:
        print("  QUALITATIVE DISAGREEMENT: Uniform and VCBB give different conclusions!")
        print(f"  Sharpe wins: Uniform {uni_sh_wins}/16 vs VCBB {vcb_sh_wins}/16")
        print(f"  MDD wins:   Uniform {uni_mdd_wins}/16 vs VCBB {vcb_mdd_wins}/16")
        print("  → Previous results may have been biased by vol clustering destruction.")

    json_out["summary"]["conclusion"] = {
        "sharpe_agree": bool(sh_agree),
        "mdd_agree": bool(mdd_agree),
        "overall_agree": bool(sh_agree and mdd_agree),
    }

    # Save
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "vcbb_vs_uniform.json"
    with open(out_path, "w") as f:
        json.dump(json_out, f, indent=2)
    print(f"\n  Results saved to {out_path}")
    print(f"  Total time: {total_time:.0f}s")


if __name__ == "__main__":
    main()
