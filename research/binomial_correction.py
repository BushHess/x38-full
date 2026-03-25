#!/usr/bin/env python3
"""Binomial Correction: Effective DOF for Correlated Timescales.

Problem: the binomial meta-test (e.g., VDO helps at 16/16 timescales,
p=1.5e-5) assumes 16 independent Bernoulli trials. But adjacent
timescales are correlated (r > 0.8), so the effective DOF < 16.

This script:
  1. Generates 2000 VCBB paths (same methodology as all research)
  2. Computes VDO on/off Sharpe delta at each of 16 timescales per path
  3. Builds the 16×16 correlation matrix of binary win indicators
  4. Estimates effective DOF using 3 established methods
  5. Reports corrected binomial p-values for ALL binomial claims in research

Output: console report + research/results/binomial_correction.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

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
from research.lib.effective_dof import compute_meff, corrected_binomial

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
K_VCBB = 50

N_BOOT = 2000

ANN = math.sqrt(6.0 * 365.25)

ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

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
        return 0.0, 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ANN if std > 1e-12 else 0.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    return sharpe, mdd


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("BINOMIAL CORRECTION: Effective DOF for Correlated Timescales")
    print("=" * 80)
    print(f"  {N_BOOT} VCBB paths × {len(SLOW_PERIODS)} timescales × VDO on/off")
    print(f"  Goal: compute actual timescale correlation → effective DOF → corrected p-values")

    # Load data
    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]

    # Precompute VCBB
    print("Precomputing VCBB...")
    vcbb = precompute_vcbb(cr, BLKSZ, ctx=CTX)

    n_sp = len(SLOW_PERIODS)

    # Storage: per-path Sharpe and MDD for on/off at each timescale
    sharpe_on  = np.zeros((N_BOOT, n_sp))
    sharpe_off = np.zeros((N_BOOT, n_sp))
    mdd_on     = np.zeros((N_BOOT, n_sp))
    mdd_off    = np.zeros((N_BOOT, n_sp))

    # ── Bootstrap loop ────────────────────────────────────────────────────
    t0 = time.time()

    for b in range(N_BOOT):
        rng = np.random.default_rng(SEED + b)
        c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng,
                                        vcbb=vcbb, K=K_VCBB)

        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        for j, slow in enumerate(SLOW_PERIODS):
            fast = max(5, slow // 4)
            ef = _ema(c, fast)
            es = _ema(c, slow)

            sh_on, md_on = sim_fast(c, ef, es, at, vd, wi, VDO_ON)
            sh_off, md_off = sim_fast(c, ef, es, at, vd, wi, VDO_OFF)

            sharpe_on[b, j] = sh_on
            sharpe_off[b, j] = sh_off
            mdd_on[b, j] = md_on
            mdd_off[b, j] = md_off

        if (b + 1) % 100 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (b + 1) * (N_BOOT - b - 1)
            print(f"  ... {b + 1}/{N_BOOT} ({elapsed:.0f}s, ETA {eta:.0f}s)")

    total_time = time.time() - t0
    print(f"\n  Bootstrap complete in {total_time:.0f}s")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 1: Compute binary win matrices
    # ══════════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("STEP 1: BINARY WIN MATRICES")
    print("=" * 80)

    # VDO improves Sharpe: win[b,j] = 1 if sharpe_on > sharpe_off
    win_sharpe = (sharpe_on > sharpe_off).astype(float)
    # VDO reduces MDD: win[b,j] = 1 if mdd_on < mdd_off
    win_mdd = (mdd_on < mdd_off).astype(float)

    # Win rates per timescale
    print(f"\n  {'N':>5s}  {'days':>4s}  {'P(Sh+)':>8s}  {'P(MDD-)':>8s}")
    print("  " + "-" * 35)
    for j, slow in enumerate(SLOW_PERIODS):
        days = slow * 4 / 24
        p_sh = np.mean(win_sharpe[:, j]) * 100
        p_md = np.mean(win_mdd[:, j]) * 100
        print(f"  {slow:>5d}  {days:>3.0f}d  {p_sh:>7.1f}%  {p_md:>7.1f}%")

    # Count timescales where P > 50%
    sh_wins = sum(1 for j in range(n_sp) if np.mean(win_sharpe[:, j]) > 0.5)
    md_wins = sum(1 for j in range(n_sp) if np.mean(win_mdd[:, j]) > 0.5)
    print(f"\n  Sharpe wins: {sh_wins}/{n_sp}")
    print(f"  MDD wins:   {md_wins}/{n_sp}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 2: Correlation matrices
    # ══════════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("STEP 2: CORRELATION MATRICES")
    print("=" * 80)

    # Correlation of binary Sharpe wins across timescales
    corr_sh = np.corrcoef(win_sharpe.T)  # 16×16
    # Correlation of binary MDD wins across timescales
    corr_md = np.corrcoef(win_mdd.T)     # 16×16

    # Also compute from Sharpe deltas (continuous, more informative)
    delta_sharpe = sharpe_on - sharpe_off
    corr_delta_sh = np.corrcoef(delta_sharpe.T)  # 16×16

    delta_mdd = mdd_off - mdd_on  # positive = VDO reduces MDD
    corr_delta_md = np.corrcoef(delta_mdd.T)  # 16×16

    # Report adjacent correlations
    print("\n  Adjacent timescale correlations:")
    print(f"    {'Source':<25s}  {'Mean adj r':>10s}  {'Min adj r':>10s}  {'Max adj r':>10s}")
    print("  " + "-" * 60)
    for label, C in [("Binary Sharpe win", corr_sh),
                     ("Binary MDD win", corr_md),
                     ("Delta Sharpe (continuous)", corr_delta_sh),
                     ("Delta MDD (continuous)", corr_delta_md)]:
        adj_r = [C[j, j+1] for j in range(n_sp - 1)]
        print(f"    {label:<25s}  {np.mean(adj_r):>10.3f}  {min(adj_r):>10.3f}  {max(adj_r):>10.3f}")

    # Full correlation matrix for Sharpe delta (most informative)
    print(f"\n  Sharpe delta correlation matrix (selected):")
    sel = [0, 3, 7, 11, 15]  # N=30, 72, 120, 240, 720
    print(f"    {'':>5s}  " + "  ".join(f"N={SLOW_PERIODS[s]:>3d}" for s in sel))
    for i in sel:
        vals = "  ".join(f"{corr_delta_sh[i, j]:>5.2f}" for j in sel)
        print(f"    N={SLOW_PERIODS[i]:>3d}  {vals}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 3: Effective DOF
    # ══════════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("STEP 3: EFFECTIVE DEGREES OF FREEDOM")
    print("=" * 80)

    # Compute M_eff from each correlation source
    # Use binary win correlation (matches the binomial test context)
    # and delta correlation (more informative, captures effect size correlation)
    sources = {
        "Binary Sharpe win": corr_sh,
        "Binary MDD win": corr_md,
        "Delta Sharpe": corr_delta_sh,
        "Delta MDD": corr_delta_md,
    }

    meff_results = {}
    print(f"\n  {'Source':<25s}  {'Nyholt':>8s}  {'Li-Ji':>8s}  {'Galwey':>8s}  {'Conserv':>8s}")
    print("  " + "-" * 65)
    for label, C in sources.items():
        m = compute_meff(C)
        meff_results[label] = m
        print(f"    {label:<25s}  {m['nyholt']:>7.1f}  {m['li_ji']:>7.1f}  "
              f"{m['galwey']:>7.1f}  {m['conservative']:>7.1f}")

    # Eigenvalue spectrum — show BINARY win correlation (used for corrections)
    print(f"\n  Eigenvalue spectrum (binary Sharpe win correlation):")
    evals_binary = np.linalg.eigvalsh(corr_sh)
    evals_binary = np.maximum(evals_binary, 0.0)
    evals_binary = np.sort(evals_binary)[::-1]
    cum_var = np.cumsum(evals_binary) / np.sum(evals_binary) * 100
    for i, (ev, cv) in enumerate(zip(evals_binary, cum_var)):
        bar = "█" * int(ev * 5)
        print(f"    λ_{i+1:>2d} = {ev:>6.3f}  (cum {cv:>5.1f}%)  {bar}")

    # Also show delta correlation eigenvalues for comparison
    print(f"\n  Eigenvalue spectrum (continuous Sharpe delta — for reference only):")
    evals_delta = np.linalg.eigvalsh(corr_delta_sh)
    evals_delta = np.maximum(evals_delta, 0.0)
    evals_delta = np.sort(evals_delta)[::-1]
    cum_var_d = np.cumsum(evals_delta) / np.sum(evals_delta) * 100
    for i, (ev, cv) in enumerate(zip(evals_delta, cum_var_d)):
        bar = "█" * int(ev * 5)
        print(f"    λ_{i+1:>2d} = {ev:>6.3f}  (cum {cv:>5.1f}%)  {bar}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 4: Corrected p-values for ALL binomial claims
    # ══════════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("STEP 4: CORRECTED P-VALUES FOR ALL BINOMIAL CLAIMS")
    print("=" * 80)

    # IMPORTANT: The binomial test operates on BINARY outcomes (win/lose).
    # Therefore the correlation that governs effective DOF is the correlation
    # of binary win indicators — NOT the correlation of continuous deltas.
    # Continuous delta correlation (r~0.84) drastically over-corrects because
    # it captures effect-size similarity, not outcome-dependence.
    # Binary win correlation (r~0.60) is the correct input for M_eff.
    corr_for_sharpe = corr_sh  # binary Sharpe win correlation
    corr_for_mdd = corr_md     # binary MDD win correlation

    claims = [
        # (label, wins, K, metric_type, source_study)
        ("VDO Sharpe improvement", sh_wins, n_sp, "sharpe",
         "timescale_robustness.py, vcbb_vs_uniform.py"),
        ("VDO MDD reduction", md_wins, n_sp, "mdd",
         "timescale_robustness.py, vcbb_vs_uniform.py"),
        ("E5 MDD reduction (uniform)", 16, 16, "mdd",
         "e5_validation.py"),
        ("E5 MDD reduction (VCBB)", 15, 16, "mdd",
         "e5_vcbb_test.py"),
        ("E5 CAGR improvement (VCBB)", 1, 16, "sharpe",
         "e5_vcbb_test.py"),
        ("VTWIN MDD improvement", 13, 16, "mdd",
         "vexit_study.py"),
    ]

    print(f"\n  {'Claim':<30s}  {'Wins':>5s}  {'Nominal':>10s}  {'Corrected':>10s}  "
          f"{'M_eff':>6s}  {'Verdict':>12s}")
    print("  " + "-" * 85)

    all_corrections = {}
    for label, wins, K_test, mtype, source in claims:
        corr = corr_for_sharpe if mtype == "sharpe" else corr_for_mdd
        result = corrected_binomial(wins, K_test, corr)

        # Use the most conservative corrected p-value
        conservative = result["corrected"]["conservative"]
        p_nom = result["p_nominal"]
        p_corr = conservative["p_value"]
        m_eff = conservative["m_eff"]

        def verdict(p):
            if p < 0.001: return "PROVEN ***"
            if p < 0.01:  return "PROVEN **"
            if p < 0.025: return "PROVEN *"
            if p < 0.05:  return "STRONG"
            if p < 0.10:  return "MARGINAL"
            return "NOT SIG"

        v_nom = verdict(p_nom)
        v_corr = verdict(p_corr)
        changed = "← CHANGED" if v_nom != v_corr else ""

        print(f"  {label:<30s}  {wins:>2d}/{K_test:>2d}  {p_nom:>10.2e}  {p_corr:>10.2e}  "
              f"{m_eff:>5.1f}  {v_corr:<12s} {changed}")

        all_corrections[label] = {
            "wins": wins,
            "K": K_test,
            "metric_type": mtype,
            "source": source,
            "p_nominal": float(p_nom),
            "verdict_nominal": v_nom,
            "correction": {
                method: {
                    "m_eff": data["m_eff"],
                    "wins_scaled": data["wins_scaled"],
                    "p_value": data["p_value"],
                }
                for method, data in result["corrected"].items()
            },
            "p_corrected_conservative": float(p_corr),
            "verdict_corrected": v_corr,
            "verdict_changed": v_nom != v_corr,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 5: Detailed breakdown per method
    # ══════════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("STEP 5: DETAILED BREAKDOWN — VDO Sharpe (primary claim)")
    print("=" * 80)

    primary = corrected_binomial(sh_wins, n_sp, corr_for_sharpe)

    print(f"\n  Nominal: {sh_wins}/{n_sp} wins, p = {primary['p_nominal']:.2e}")
    print(f"\n  {'Method':<15s}  {'M_eff':>6s}  {'M_eff(int)':>10s}  "
          f"{'Scaled wins':>12s}  {'p-value':>10s}  {'Verdict':>12s}")
    print("  " + "-" * 75)

    for method in ["nyholt", "li_ji", "galwey", "conservative"]:
        d = primary["corrected"][method]
        def verdict(p):
            if p < 0.001: return "PROVEN ***"
            if p < 0.01:  return "PROVEN **"
            if p < 0.025: return "PROVEN *"
            if p < 0.05:  return "STRONG"
            if p < 0.10:  return "MARGINAL"
            return "NOT SIG"
        v = verdict(d["p_value"])
        print(f"  {method:<15s}  {d['m_eff']:>5.1f}  {d['m_eff_int']:>10d}  "
              f"{d['wins_scaled']:>12d}  {d['p_value']:>10.2e}  {v:<12s}")

    # ══════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    n_changed = sum(1 for v in all_corrections.values() if v["verdict_changed"])
    print(f"\n  Total claims checked: {len(claims)}")
    print(f"  Verdicts changed by correction: {n_changed}/{len(claims)}")

    if n_changed == 0:
        print(f"\n  ALL conclusions survive effective DOF correction.")
        print(f"  The binomial independence assumption inflated p-values")
        print(f"  but NOT enough to change any verdict.")
    else:
        print(f"\n  {n_changed} verdict(s) changed. Review claims above.")

    for label, v in all_corrections.items():
        if v["verdict_changed"]:
            print(f"    CHANGED: {label}")
            print(f"      Nominal: {v['verdict_nominal']} (p={v['p_nominal']:.2e})")
            print(f"      Corrected: {v['verdict_corrected']} (p={v['p_corrected_conservative']:.2e})")

    # Save results
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "binomial_correction.json"

    output = {
        "config": {
            "n_boot": N_BOOT,
            "blksz": BLKSZ,
            "ctx": CTX,
            "seed": SEED,
            "method": "VCBB",
            "correlation_note": "Binary win correlation used for M_eff (matches binomial test)",
        },
        "meff_by_source": {k: v for k, v in meff_results.items()},
        "eigenvalues_binary_sharpe_win": [round(float(e), 4) for e in evals_binary],
        "eigenvalues_delta_sharpe_ref": [round(float(e), 4) for e in evals_delta],
        "correlation_matrix_binary_sharpe_win": [[round(float(c), 4) for c in row]
                                                  for row in corr_sh],
        "correlation_matrix_binary_mdd_win": [[round(float(c), 4) for c in row]
                                               for row in corr_md],
        "claims": all_corrections,
        "total_time_s": round(total_time, 1),
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {out_path}")
    print(f"  Total time: {total_time:.0f}s")


if __name__ == "__main__":
    main()
