#!/usr/bin/env python3
"""E5 (Robust ATR) Multi-Timescale Validation Study.

Q: Is E5's improvement over E0 a GENERIC property of the robust ATR
   mechanism, or is it specific to slow_period=120/144?

Method:
  - 16 timescales × 2 variants (E0 vs E5) × 2000 bootstrap paths
  - Same seed=42, same gen_path, same cost model as all prior work
  - f=1.0 (binary) since Sharpe is invariant to sizing
  - Harsh cost (50 bps RT)

Validation path to PROVEN:
  If E5 wins at ≥13/16 timescales: binomial p < 0.01 under H0(p=0.5)
  This is the same framework that PROVEN VDO (16/16, p=1.5e-5).

ALSO tests:
  - OUTCOME metrics (final NAV, CAGR) at each timescale on real data
  - Bootstrap P(CAGR+) at each timescale
  - Binomial test on BOTH outcome and Sharpe dimensions
"""
# ──────────────────────────────────────────────────────────────
# WARNING (Report 21, U6): The uncorrected binomial test in this script
# treats 16 timescale outcomes as independent. For CROSS-STRATEGY
# comparison, adjacent-timescale correlation yields M_eff ≈ 2.5–4.0,
# making the uncorrected p-values unreliable (demonstrated false
# positive: PROVEN*** on null pair, Report 20 §5.3).
#
# Cross-strategy results from this script MUST be verified with DOF
# correction (research/lib/effective_dof.py) before citation.
#
# WITHIN-STRATEGY results (e.g., VDO on/off, M_eff ≈ 10–11) are
# not affected by this limitation.
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from scipy import stats as sp_stats

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ───────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0   # 0.0025

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
BLKSZ  = 60
SEED   = 42

ANN = math.sqrt(6.0 * 365.25)

# Fixed VTREND structural constants
ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

# Same 16 timescales as timescale_robustness.py
SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

OUTDIR = Path(__file__).resolve().parent / "results" / "e5_validation"


# ═══════════════════════════════════════════════════════════════════
# Data loading & path generation (identical to timescale_robustness.py)
# ═══════════════════════════════════════════════════════════════════

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


def make_ratios(cl, hi, lo, vo, tb):
    pc = cl[:-1]
    return cl[1:] / pc, hi[1:] / pc, lo[1:] / pc, vo[1:].copy(), tb[1:].copy()


def gen_path(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng):
    n_blk = math.ceil(n_trans / blksz)
    mx = len(cr) - blksz
    if mx <= 0:
        idx = np.arange(min(n_trans, len(cr)))
    else:
        starts = rng.integers(0, mx + 1, size=n_blk)
        idx = np.concatenate([np.arange(s, s + blksz) for s in starts])[:n_trans]
    c = np.empty(len(idx) + 1, dtype=np.float64)
    c[0] = p0
    c[1:] = p0 * np.cumprod(cr[idx])
    h = np.empty_like(c); l = np.empty_like(c)
    v = np.empty_like(c); t = np.empty_like(c)
    h[0] = p0 * 1.002;  l[0] = p0 * 0.998
    v[0] = vol[idx[0]];  t[0] = tb[idx[0]]
    h[1:] = c[:-1] * hr[idx];  l[1:] = c[:-1] * lr[idx]
    v[1:] = vol[idx];          t[1:] = tb[idx]
    np.maximum(h, c, out=h);   np.minimum(l, c, out=l)
    return c, h, l, v, t


# ═══════════════════════════════════════════════════════════════════
# Robust ATR computation
# ═══════════════════════════════════════════════════════════════════

def _robust_atr(hi, lo, cl, cap_q=0.90, cap_lb=100, period=20):
    """Robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.concatenate([[cl[0]], cl[:-1]])
    tr = np.maximum(
        hi - lo,
        np.maximum(np.abs(hi - prev_cl), np.abs(lo - prev_cl)),
    )
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb : i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s : s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


# ═══════════════════════════════════════════════════════════════════
# Fast VTREND simulation (E0 variant — standard ATR)
# ═══════════════════════════════════════════════════════════════════

def sim_e0(cl, ef, es, at, vd, wi):
    """VTREND E0 (standard ATR trail). Returns metrics dict."""
    return _sim_core(cl, ef, es, at, vd, wi, at)


def sim_e5(cl, ef, es, at, vd, wi, ratr):
    """VTREND E5 (robust ATR trail). Returns metrics dict."""
    return _sim_core(cl, ef, es, at, vd, wi, ratr)


def _sim_core(cl, ef, es, at, vd, wi, exit_atr):
    """Core VTREND simulation shared by E0 and E5."""
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

        # Fill pending
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
                nav_peak = nav
                prev_nav = nav
                started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r
                    rets_sq_sum += r * r
                    n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak:
                nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio:
                nav_min_ratio = ratio

        # Signal generation
        a_val = at[i]
        ea_val = exit_atr[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if math.isnan(ea_val):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > 0.0:
                pe = True
        else:
            pk = max(pk, p)
            trail = pk - TRAIL * ea_val
            if p < trail:
                px = True
            elif ef[i] < es[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    # Metrics
    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0,
                "trades": nt, "final_nav": navs_end}

    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100
    mdd = (1.0 - nav_min_ratio) * 100

    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {
        "sharpe": sharpe,
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "trades": nt,
        "final_nav": navs_end,
    }


# ═══════════════════════════════════════════════════════════════════
# Real-data sweep
# ═══════════════════════════════════════════════════════════════════

def run_real_data(cl, hi, lo, vo, tb, wi):
    """Sweep timescales on real data: E0 vs E5."""
    print("\n" + "=" * 70)
    print("REAL DATA: TIMESCALE SWEEP — E0 vs E5")
    print("=" * 70)

    results = {}
    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        days = sp * 4 / 24
        ef = _ema(cl, fp)
        es = _ema(cl, sp)
        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ratr = _robust_atr(hi, lo, cl)

        r_e0 = sim_e0(cl, ef, es, at, vd, wi)
        r_e5 = sim_e5(cl, ef, es, at, vd, wi, ratr)

        delta_nav = (r_e5["final_nav"] / max(r_e0["final_nav"], 1) - 1) * 100
        delta_cagr = r_e5["cagr"] - r_e0["cagr"]
        delta_sharpe = r_e5["sharpe"] - r_e0["sharpe"]

        results[sp] = {"e0": r_e0, "e5": r_e5}
        print(f"  sp={sp:4d} ({days:5.0f}d): "
              f"E0 NAV=${r_e0['final_nav']:>10,.0f} Sh={r_e0['sharpe']:+.3f} "
              f"CAGR={r_e0['cagr']:+.1f}% | "
              f"E5 NAV=${r_e5['final_nav']:>10,.0f} Sh={r_e5['sharpe']:+.3f} "
              f"CAGR={r_e5['cagr']:+.1f}% | "
              f"ΔNAV={delta_nav:+.1f}% ΔSh={delta_sharpe:+.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════
# Bootstrap comparison
# ═══════════════════════════════════════════════════════════════════

def run_bootstrap(cl, hi, lo, vo, tb, wi, n):
    """2000 bootstrap paths × 16 timescales × 2 variants."""
    print("\n" + "=" * 70)
    print(f"BOOTSTRAP: {N_BOOT} PATHS × {len(SLOW_PERIODS)} TIMESCALES × 2 VARIANTS")
    print("=" * 70)

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "calmar", "trades", "final_nav"]

    boot_e0 = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_e5 = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng)

        at = _atr(h, l, c, ATR_P)
        ratr = _robust_atr(h, l, c)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            r0 = sim_e0(c, ef, es, at, vd, wi)
            r5 = sim_e5(c, ef, es, at, vd, wi, ratr)

            for m in mkeys:
                boot_e0[m][b, j] = r0[m]
                boot_e5[m][b, j] = r5[m]

    el = time.time() - t0
    n_total = N_BOOT * n_sp * 2
    print(f"\n  Done: {el:.1f}s ({n_total} sims, {n_total / el:.0f} sims/sec)")

    return boot_e0, boot_e5


# ═══════════════════════════════════════════════════════════════════
# Analysis
# ═══════════════════════════════════════════════════════════════════

def analyze(boot_e0, boot_e5, real_results):
    """Comprehensive analysis: per-timescale + binomial."""
    n_sp = len(SLOW_PERIODS)

    print("\n" + "=" * 70)
    print("ANALYSIS: E5 vs E0 ACROSS TIMESCALES")
    print("=" * 70)

    # ── Per-timescale results ──
    print(f"\n  {'sp':>5}  {'days':>5}  "
          f"{'ΔSharpe':>9}  {'P(Sh+)':>7}  "
          f"{'ΔCAGR':>8}  {'P(CAGR+)':>9}  "
          f"{'ΔMDD':>7}  {'P(MDD-)':>8}  "
          f"{'ΔNAV%':>7}  {'P(NAV+)':>8}  "
          f"  real_ΔNAV%")
    print("  " + "-" * 110)

    win_sharpe = 0
    win_cagr = 0
    win_mdd = 0
    win_nav = 0
    win_outcome_real = 0

    per_ts_results = []

    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24

        d_sh = boot_e5["sharpe"][:, j] - boot_e0["sharpe"][:, j]
        d_cg = boot_e5["cagr"][:, j] - boot_e0["cagr"][:, j]
        d_md = boot_e0["mdd"][:, j] - boot_e5["mdd"][:, j]  # positive = improvement
        d_nv = boot_e5["final_nav"][:, j] / np.maximum(boot_e0["final_nav"][:, j], 1) - 1.0

        p_sh = float(np.mean(d_sh > 0))
        p_cg = float(np.mean(d_cg > 0))
        p_md = float(np.mean(d_md > 0))
        p_nv = float(np.mean(d_nv > 0))

        if p_sh > 0.50: win_sharpe += 1
        if p_cg > 0.50: win_cagr += 1
        if p_md > 0.50: win_mdd += 1
        if p_nv > 0.50: win_nav += 1

        # Real-data outcome
        rr = real_results.get(sp, {})
        r_e0 = rr.get("e0", {})
        r_e5 = rr.get("e5", {})
        real_delta_nav = (r_e5.get("final_nav", 0) / max(r_e0.get("final_nav", 1), 1) - 1) * 100
        if real_delta_nav > 0:
            win_outcome_real += 1

        marker = ""
        if p_cg >= 0.90:
            marker = " ***"
        elif p_cg >= 0.75:
            marker = " **"
        elif p_cg > 0.50:
            marker = " *"

        print(f"  {sp:5d}  {days:5.0f}  "
              f"{d_sh.mean():+9.4f}  {p_sh*100:6.1f}%  "
              f"{d_cg.mean():+8.2f}%  {p_cg*100:8.1f}%  "
              f"{d_md.mean():+7.2f}  {p_md*100:7.1f}%  "
              f"{d_nv.mean()*100:+7.2f}  {p_nv*100:7.1f}%  "
              f"  {real_delta_nav:+.1f}%{marker}")

        per_ts_results.append({
            "sp": sp, "days": days,
            "d_sharpe_mean": round(float(d_sh.mean()), 6),
            "p_sharpe": round(p_sh, 6),
            "d_cagr_mean": round(float(d_cg.mean()), 4),
            "p_cagr": round(p_cg, 6),
            "d_mdd_mean": round(float(d_md.mean()), 4),
            "p_mdd": round(p_md, 6),
            "d_nav_pct_mean": round(float(d_nv.mean()) * 100, 4),
            "p_nav": round(p_nv, 6),
            "real_delta_nav_pct": round(real_delta_nav, 4),
        })

    # ── Binomial tests ──
    print(f"\n  {'METRIC':>15}  {'wins':>5}/{n_sp}  {'binomial p':>12}  {'verdict':>12}")
    print("  " + "-" * 55)

    binomial_results = {}
    for label, wins in [
        ("P(Sharpe+)>50%", win_sharpe),
        ("P(CAGR+)>50%", win_cagr),
        ("P(MDD-)>50%", win_mdd),
        ("P(NAV+)>50%", win_nav),
        ("Real ΔNAV>0", win_outcome_real),
    ]:
        # Two-sided binomial test: H0 is p=0.5
        p_binom = sp_stats.binomtest(wins, n_sp, 0.5, alternative='greater').pvalue
        if p_binom < 0.001:
            verdict = "PROVEN ***"
        elif p_binom < 0.01:
            verdict = "PROVEN **"
        elif p_binom < 0.025:
            verdict = "PROVEN *"
        elif p_binom < 0.05:
            verdict = "STRONG"
        elif p_binom < 0.10:
            verdict = "MARGINAL"
        else:
            verdict = "NOT SIG"

        print(f"  {label:>15}  {wins:5d}/{n_sp}  {p_binom:12.6f}  {verdict:>12}")
        binomial_results[label] = {
            "wins": wins, "n": n_sp, "p_binom": round(p_binom, 8), "verdict": verdict,
        }

    # ── Median bootstrap improvement across timescales ──
    print(f"\n  Median P(E5 better on CAGR) across timescales: "
          f"{np.median([r['p_cagr'] for r in per_ts_results])*100:.1f}%")
    print(f"  Mean P(E5 better on CAGR) across timescales: "
          f"{np.mean([r['p_cagr'] for r in per_ts_results])*100:.1f}%")

    # ── Productive region analysis ──
    print("\n  Productive region (P(CAGR+) > 50% on bootstrap):")
    productive = [r for r in per_ts_results if r["p_cagr"] > 0.5]
    if productive:
        sp_min = min(r["sp"] for r in productive)
        sp_max = max(r["sp"] for r in productive)
        print(f"    Range: sp={sp_min}–{sp_max} ({sp_min*4/24:.0f}–{sp_max*4/24:.0f} days)")
        print(f"    Width: {len(productive)}/{n_sp} timescales")
    else:
        print(f"    No productive region found")

    print("\n  Strong region (P(CAGR+) > 75% on bootstrap):")
    strong = [r for r in per_ts_results if r["p_cagr"] > 0.75]
    if strong:
        sp_min = min(r["sp"] for r in strong)
        sp_max = max(r["sp"] for r in strong)
        print(f"    Range: sp={sp_min}–{sp_max} ({sp_min*4/24:.0f}–{sp_max*4/24:.0f} days)")
        print(f"    Width: {len(strong)}/{n_sp} timescales")
    else:
        print(f"    No strong region found")

    return per_ts_results, binomial_results


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("E5 (ROBUST ATR) MULTI-TIMESCALE VALIDATION")
    print("=" * 70)
    print(f"  Timescales: {len(SLOW_PERIODS)} ({SLOW_PERIODS[0]}–{SLOW_PERIODS[-1]} H4 bars)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  E5 mechanism: robust ATR (cap_q=0.90, cap_lb=100, period=20)")
    print(f"  Total sims: {N_BOOT * len(SLOW_PERIODS) * 2:,}")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n-wi} bars")

    # ── Real data sweep ──
    real_results = run_real_data(cl, hi, lo, vo, tb, wi)

    # ── Bootstrap comparison ──
    boot_e0, boot_e5 = run_bootstrap(cl, hi, lo, vo, tb, wi, n)

    # ── Analysis ──
    per_ts, binomial = analyze(boot_e0, boot_e5, real_results)

    # ── Save results ──
    output = {
        "config": {
            "n_boot": N_BOOT, "block_size": BLKSZ, "seed": SEED,
            "trail": TRAIL, "atr_period": ATR_P,
            "e5_cap_q": 0.90, "e5_cap_lb": 100, "e5_period": 20,
            "cost_rt_bps": COST.round_trip_bps,
            "slow_periods": SLOW_PERIODS,
        },
        "per_timescale": per_ts,
        "binomial_tests": binomial,
        "real_data": {},
    }
    for sp, rr in real_results.items():
        output["real_data"][str(sp)] = rr

    out_path = OUTDIR / "e5_validation.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"STUDY COMPLETE in {elapsed:.1f}s")

    # ── Final Verdict ──
    cagr_result = binomial.get("P(CAGR+)>50%", {})
    nav_result = binomial.get("P(NAV+)>50%", {})
    real_result = binomial.get("Real ΔNAV>0", {})

    print(f"\nFINAL VERDICT:")
    print(f"  Bootstrap CAGR: {cagr_result.get('wins',0)}/{len(SLOW_PERIODS)} timescales, "
          f"binomial p={cagr_result.get('p_binom',1):.6f} → {cagr_result.get('verdict','?')}")
    print(f"  Bootstrap NAV:  {nav_result.get('wins',0)}/{len(SLOW_PERIODS)} timescales, "
          f"binomial p={nav_result.get('p_binom',1):.6f} → {nav_result.get('verdict','?')}")
    print(f"  Real-data NAV:  {real_result.get('wins',0)}/{len(SLOW_PERIODS)} timescales, "
          f"binomial p={real_result.get('p_binom',1):.6f} → {real_result.get('verdict','?')}")
    print(f"{'='*70}")
