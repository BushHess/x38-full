#!/usr/bin/env python3
"""E5+Ratchet Conditional Hybrid Test.

Q: Does combining E5 (robust ATR) with ratcheting — only when trade is
   profitable — produce a provable improvement over E0?

Variants tested (all vs E0 baseline):
  COND-E5:    Standard ATR while losing, switch to robust ATR when profitable
  RATCH-STD:  Standard ATR + ratchet trail multiplier (3.0→2.0 as MFE_R grows)
  E5R:        Conditional E5 + ratchet (both combined)

Ratchet mechanism (from exit_family_study.py E1):
  MFE_R = (peak_close - entry_price) / entry_ATR
  MFE_R < 1.0 → trail_mult = 3.0  (no tightening)
  1.0 ≤ MFE_R < 2.0 → trail_mult = 2.0  (tighten)
  MFE_R ≥ 2.0 → trail_mult = 1.5  (tight)

Method:
  16 timescales × 4 variants × 2000 bootstrap paths
  Same seed=42, same gen_path, same cost model as all prior work
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

# ── Constants ───────────────────────────────────────────────────────

DATA   = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST   = SCENARIOS["harsh"]
CPS    = COST.per_side_bps / 10_000.0

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

# Ratchet thresholds (from exit_family_study.py E1 defaults)
RATCH_T1   = 1.0   # MFE_R threshold 1
RATCH_T2   = 2.0   # MFE_R threshold 2
RATCH_MID  = 2.0   # trail_mult when MFE_R ∈ [T1, T2)
RATCH_TIGHT = 1.5  # trail_mult when MFE_R ≥ T2

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

OUTDIR = Path(__file__).resolve().parent / "results" / "e5r_test"

VARIANTS = ["E0", "COND-E5", "RATCH-STD", "E5R"]


# ═══════════════════════════════════════════════════════════════════
# Data loading & path generation (identical to e5_validation.py)
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
# Robust ATR computation (identical to e5_validation.py)
# ═══════════════════════════════════════════════════════════════════

def _robust_atr(hi, lo, cl, cap_q=0.90, cap_lb=100, period=20):
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
# Simulation variants
# ═══════════════════════════════════════════════════════════════════

def _metrics(navs_start, navs_end, nav_peak_unused, nav_min_ratio,
             rets_sum, rets_sq_sum, n_rets, nt):
    """Compute standard metrics from accumulated stats."""
    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0, "cagr": -100, "mdd": 100, "calmar": 0,
                "trades": nt, "final_nav": navs_end}
    tr = navs_end / navs_start - 1.0
    years = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / years) - 1.0) * 100 if tr > -1 else -100
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


def sim_variant(cl, ef, es, at, vd, wi, ratr, variant):
    """Simulate a VTREND variant.

    variant: "E0", "COND-E5", "RATCH-STD", "E5R"
    """
    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0           # peak close during trade
    entry_px = 0.0     # entry fill price (for MFE_R)
    entry_atr = 0.0    # ATR at entry (for MFE_R)
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

    use_cond_e5 = variant in ("COND-E5", "E5R")
    use_ratchet = variant in ("RATCH-STD", "E5R")

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
                entry_px = fp   # filled at previous close
                entry_atr = at[i - 1] if not math.isnan(at[i - 1]) else 1.0
            elif px:
                cash = bq * fp * (1.0 - CPS)
                bq = 0.0
                inp = False
                pk = 0.0
                entry_px = 0.0
                entry_atr = 0.0
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
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > 0.0:
                pe = True
        else:
            pk = max(pk, p)

            # ── Determine which ATR to use for exit ──
            profitable = (p > entry_px) if entry_px > 0 else False

            if use_cond_e5 and profitable:
                # Switch to robust ATR when in profit
                ea_val = ratr[i] if not math.isnan(ratr[i]) else a_val
            else:
                ea_val = a_val

            if math.isnan(ea_val):
                continue

            # ── Determine trail multiplier ──
            if use_ratchet and entry_atr > 1e-12:
                mfe_r = (pk - entry_px) / entry_atr
                if mfe_r < RATCH_T1:
                    t_mult = TRAIL
                elif mfe_r < RATCH_T2:
                    t_mult = RATCH_MID
                else:
                    t_mult = RATCH_TIGHT
            else:
                t_mult = TRAIL

            # ── Trail stop ──
            trail = pk - t_mult * ea_val
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

    return _metrics(navs_start, navs_end, nav_peak, nav_min_ratio,
                    rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════
# Real-data sweep
# ═══════════════════════════════════════════════════════════════════

def run_real_data(cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 90)
    print("REAL DATA: TIMESCALE SWEEP — 4 VARIANTS")
    print("=" * 90)

    results = {}
    hdr = (f"  {'sp':>5} {'days':>5}"
           + "".join(f"  {'NAV_'+v:>12} {'Sh_'+v:>8}" for v in VARIANTS)
           + f"  {'ΔNAV_E5R':>10}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        days = sp * 4 / 24
        ef = _ema(cl, fp)
        es = _ema(cl, sp)
        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ratr = _robust_atr(hi, lo, cl)

        row = {}
        for v in VARIANTS:
            row[v] = sim_variant(cl, ef, es, at, vd, wi, ratr, v)
        results[sp] = row

        e0_nav = row["E0"]["final_nav"]
        e5r_nav = row["E5R"]["final_nav"]
        delta = (e5r_nav / max(e0_nav, 1) - 1) * 100

        line = f"  {sp:5d} {days:5.0f}"
        for v in VARIANTS:
            line += f"  ${row[v]['final_nav']:>11,.0f} {row[v]['sharpe']:>8.3f}"
        line += f"  {delta:+10.1f}%"
        print(line)

    return results


# ═══════════════════════════════════════════════════════════════════
# Bootstrap comparison
# ═══════════════════════════════════════════════════════════════════

def run_bootstrap(cl, hi, lo, vo, tb, wi, n):
    print("\n" + "=" * 90)
    print(f"BOOTSTRAP: {N_BOOT} PATHS × {len(SLOW_PERIODS)} TIMESCALES × {len(VARIANTS)} VARIANTS")
    print("=" * 90)

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "calmar", "trades", "final_nav"]

    boot = {v: {m: np.zeros((N_BOOT, n_sp)) for m in mkeys} for v in VARIANTS}

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

            for var in VARIANTS:
                r = sim_variant(c, ef, es, at, vd, wi, ratr, var)
                for m in mkeys:
                    boot[var][m][b, j] = r[m]

    el = time.time() - t0
    n_total = N_BOOT * n_sp * len(VARIANTS)
    print(f"\n  Done: {el:.1f}s ({n_total} sims, {n_total / el:.0f} sims/sec)")

    return boot


# ═══════════════════════════════════════════════════════════════════
# Analysis
# ═══════════════════════════════════════════════════════════════════

def analyze(boot, real_results):
    n_sp = len(SLOW_PERIODS)
    test_variants = [v for v in VARIANTS if v != "E0"]

    print("\n" + "=" * 90)
    print("ANALYSIS: EACH VARIANT vs E0 ACROSS TIMESCALES")
    print("=" * 90)

    all_results = {}

    for var in test_variants:
        print(f"\n  ── {var} vs E0 ──")
        print(f"  {'sp':>5} {'days':>5}  "
              f"{'ΔCAGR':>8} {'P(CAGR+)':>9}  "
              f"{'ΔMDD':>7} {'P(MDD-)':>8}  "
              f"{'ΔSharpe':>9} {'P(Sh+)':>7}  "
              f"{'ΔNAV%':>7} {'P(NAV+)':>8}  "
              f"  real_ΔNAV%")
        print("  " + "-" * 105)

        win_cagr = win_mdd = win_sharpe = win_nav = win_real = 0
        per_ts = []

        for j, sp in enumerate(SLOW_PERIODS):
            days = sp * 4 / 24

            d_sh = boot[var]["sharpe"][:, j] - boot["E0"]["sharpe"][:, j]
            d_cg = boot[var]["cagr"][:, j] - boot["E0"]["cagr"][:, j]
            d_md = boot["E0"]["mdd"][:, j] - boot[var]["mdd"][:, j]
            d_nv = boot[var]["final_nav"][:, j] / np.maximum(boot["E0"]["final_nav"][:, j], 1) - 1.0

            p_sh = float(np.mean(d_sh > 0))
            p_cg = float(np.mean(d_cg > 0))
            p_md = float(np.mean(d_md > 0))
            p_nv = float(np.mean(d_nv > 0))

            if p_sh > 0.50: win_sharpe += 1
            if p_cg > 0.50: win_cagr += 1
            if p_md > 0.50: win_mdd += 1
            if p_nv > 0.50: win_nav += 1

            rr = real_results.get(sp, {})
            r_e0 = rr.get("E0", {})
            r_var = rr.get(var, {})
            real_delta = (r_var.get("final_nav", 0) / max(r_e0.get("final_nav", 1), 1) - 1) * 100
            if real_delta > 0:
                win_real += 1

            print(f"  {sp:5d} {days:5.0f}  "
                  f"{d_cg.mean():+8.2f}% {p_cg*100:8.1f}%  "
                  f"{d_md.mean():+7.2f} {p_md*100:7.1f}%  "
                  f"{d_sh.mean():+9.4f} {p_sh*100:6.1f}%  "
                  f"{d_nv.mean()*100:+7.2f} {p_nv*100:7.1f}%  "
                  f"  {real_delta:+.1f}%")

            per_ts.append({
                "sp": sp, "days": days,
                "d_cagr_mean": round(float(d_cg.mean()), 4),
                "p_cagr": round(p_cg, 6),
                "d_mdd_mean": round(float(d_md.mean()), 4),
                "p_mdd": round(p_md, 6),
                "d_sharpe_mean": round(float(d_sh.mean()), 6),
                "p_sharpe": round(p_sh, 6),
                "d_nav_pct_mean": round(float(d_nv.mean()) * 100, 4),
                "p_nav": round(p_nv, 6),
                "real_delta_nav_pct": round(real_delta, 4),
            })

        # Binomial tests
        print(f"\n  {'METRIC':>15}  {'wins':>5}/{n_sp}  {'binom p':>10}  {'verdict':>12}")
        print("  " + "-" * 50)

        binomial = {}
        for label, wins in [
            ("P(Sharpe+)>50%", win_sharpe),
            ("P(CAGR+)>50%", win_cagr),
            ("P(MDD-)>50%", win_mdd),
            ("P(NAV+)>50%", win_nav),
            ("Real ΔNAV>0", win_real),
        ]:
            p_binom = sp_stats.binomtest(wins, n_sp, 0.5, alternative='greater').pvalue
            verdict = ("PROVEN ***" if p_binom < 0.001 else
                       "PROVEN **" if p_binom < 0.01 else
                       "PROVEN *" if p_binom < 0.025 else
                       "STRONG" if p_binom < 0.05 else
                       "MARGINAL" if p_binom < 0.10 else
                       "NOT SIG")
            print(f"  {label:>15}  {wins:5d}/{n_sp}  {p_binom:10.6f}  {verdict:>12}")
            binomial[label] = {"wins": wins, "n": n_sp,
                               "p_binom": round(p_binom, 8), "verdict": verdict}

        # Tradeoff ratio
        mean_dcagr = np.mean([r["d_cagr_mean"] for r in per_ts])
        mean_dmdd = np.mean([r["d_mdd_mean"] for r in per_ts])
        ratio = abs(mean_dcagr) / mean_dmdd if mean_dmdd > 0.01 else float('inf')
        print(f"\n  Tradeoff: ΔCAGR={mean_dcagr:+.3f}pp, ΔMDD={mean_dmdd:+.3f}pp, "
              f"ratio={ratio:.2f} (pp CAGR lost per pp MDD saved)")

        all_results[var] = {
            "per_timescale": per_ts,
            "binomial_tests": binomial,
            "tradeoff": {"mean_dcagr": round(mean_dcagr, 4),
                         "mean_dmdd": round(mean_dmdd, 4),
                         "ratio": round(ratio, 4)},
        }

    # ── Interaction check: E5R vs sum(COND-E5 + RATCH-STD) ──
    print("\n" + "=" * 90)
    print("INTERACTION CHECK: E5R vs COND-E5 + RATCH-STD (additive model)")
    print("=" * 90)
    print(f"\n  {'sp':>5}  {'E5R_ΔCAGR':>10}  {'sum_ΔCAGR':>10}  {'interact':>10}  "
          f"{'E5R_ΔMDD':>9}  {'sum_ΔMDD':>9}  {'interact':>10}")
    print("  " + "-" * 75)

    for j, sp in enumerate(SLOW_PERIODS):
        e5r_cagr = all_results["E5R"]["per_timescale"][j]["d_cagr_mean"]
        cond_cagr = all_results["COND-E5"]["per_timescale"][j]["d_cagr_mean"]
        ratch_cagr = all_results["RATCH-STD"]["per_timescale"][j]["d_cagr_mean"]
        sum_cagr = cond_cagr + ratch_cagr
        int_cagr = e5r_cagr - sum_cagr

        e5r_mdd = all_results["E5R"]["per_timescale"][j]["d_mdd_mean"]
        cond_mdd = all_results["COND-E5"]["per_timescale"][j]["d_mdd_mean"]
        ratch_mdd = all_results["RATCH-STD"]["per_timescale"][j]["d_mdd_mean"]
        sum_mdd = cond_mdd + ratch_mdd
        int_mdd = e5r_mdd - sum_mdd

        print(f"  {sp:5d}  {e5r_cagr:+10.3f}  {sum_cagr:+10.3f}  {int_cagr:+10.3f}  "
              f"{e5r_mdd:+9.3f}  {sum_mdd:+9.3f}  {int_mdd:+10.3f}")

    return all_results


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    n_total = N_BOOT * len(SLOW_PERIODS) * len(VARIANTS)
    print("=" * 90)
    print("E5+RATCHET CONDITIONAL HYBRID TEST")
    print("=" * 90)
    print(f"  Variants: {VARIANTS}")
    print(f"  Timescales: {len(SLOW_PERIODS)} ({SLOW_PERIODS[0]}–{SLOW_PERIODS[-1]} H4 bars)")
    print(f"  Bootstrap: {N_BOOT} paths, block={BLKSZ}, seed={SEED}")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Ratchet: MFE_R<{RATCH_T1}→{TRAIL}, "
          f"[{RATCH_T1},{RATCH_T2})→{RATCH_MID}, ≥{RATCH_T2}→{RATCH_TIGHT}")
    print(f"  Total sims: {n_total:,}")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  {n} H4 bars, warmup idx={wi}, trading={n-wi} bars")

    # ── Real data sweep ──
    real_results = run_real_data(cl, hi, lo, vo, tb, wi)

    # ── Bootstrap comparison ──
    boot = run_bootstrap(cl, hi, lo, vo, tb, wi, n)

    # ── Analysis ──
    all_results = analyze(boot, real_results)

    # ── Save results ──
    output = {
        "config": {
            "n_boot": N_BOOT, "block_size": BLKSZ, "seed": SEED,
            "trail": TRAIL, "atr_period": ATR_P,
            "ratchet": {"t1": RATCH_T1, "t2": RATCH_T2,
                        "mid": RATCH_MID, "tight": RATCH_TIGHT},
            "e5_cap_q": 0.90, "e5_cap_lb": 100, "e5_period": 20,
            "cost_rt_bps": COST.round_trip_bps,
            "slow_periods": SLOW_PERIODS,
            "variants": VARIANTS,
        },
        "results": all_results,
        "real_data": {str(sp): rr for sp, rr in real_results.items()},
    }
    out_path = OUTDIR / "e5r_test.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {out_path}")

    elapsed = time.time() - t0
    print(f"\n{'='*90}")
    print(f"STUDY COMPLETE in {elapsed:.1f}s")

    # ── Final Verdict ──
    print(f"\nFINAL VERDICT:")
    for var in ["COND-E5", "RATCH-STD", "E5R"]:
        r = all_results[var]
        cagr_v = r["binomial_tests"]["P(CAGR+)>50%"]
        mdd_v = r["binomial_tests"]["P(MDD-)>50%"]
        tf = r["tradeoff"]
        print(f"  {var:>10}: CAGR {cagr_v['wins']}/{cagr_v['n']} ({cagr_v['verdict']}), "
              f"MDD {mdd_v['wins']}/{mdd_v['n']} ({mdd_v['verdict']}), "
              f"tradeoff {tf['ratio']:.2f}:1")
    print(f"{'='*90}")
