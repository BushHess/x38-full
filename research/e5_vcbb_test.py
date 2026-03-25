#!/usr/bin/env python3
"""E5 vs E0: Uniform vs VCBB Bootstrap Comparison.

Previous result (uniform bootstrap):
  - E5 WINS MDD at 16/16 timescales (p=1.5e-5) — proven MDD reduction
  - E5 LOSES CAGR at 0/16 timescales (p=1.0) — proven CAGR cost
  - Conclusion: REJECTED (trades CAGR for small MDD reduction, net negative)

Question: Does VCBB (preserved vol clustering) change this verdict?
Hypothesis: VCBB preserves extreme vol episodes → E5's ATR capping works
more realistically → E5 might perform differently.

Method: 16 timescales × 2000 paths × 2 bootstrap methods × E0/E5 paired comparison
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

ATR_P  = 14
VDO_F  = 12
VDO_S  = 28
TRAIL  = 3.0

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]


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


# ── Robust ATR (E5) ──────────────────────────────────────────────────────────

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


# ── Simulator ─────────────────────────────────────────────────────────────────

def _sim_core(cl, ef, es, at, vd, wi, exit_atr):
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

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS)
        bq = 0.0
        nt += 1
        navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "final_nav": navs_end}

    tr_val = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr_val) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr_val > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
            "trades": nt, "final_nav": navs_end}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 90)
    print("E5 vs E0: UNIFORM vs VCBB BOOTSTRAP COMPARISON")
    print("=" * 90)
    print(f"Paired comparison × 16 timescales × {N_BOOT} paths × 2 bootstrap methods")

    print("\nLoading data...")
    cl, hi, lo, vo, tb, wi, n = load_arrays()
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]
    print(f"  H4 bars: {n}, transitions: {n_trans}, warmup: {wi}")

    print("Precomputing VCBB state...")
    vcbb = precompute_vcbb(cr, BLKSZ, ctx=CTX)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "calmar", "final_nav"]

    # Storage: [method][variant][metric] → (N_BOOT, n_sp)
    R = {}
    for method in ["uniform", "vcbb"]:
        R[method] = {}
        for variant in ["e0", "e5"]:
            R[method][variant] = {k: np.zeros((N_BOOT, n_sp)) for k in mkeys}

    t0 = time.time()

    for b in range(N_BOOT):
        rng_u = np.random.default_rng(SEED + b)
        rng_v = np.random.default_rng(SEED + b)

        # Generate ONE path per method
        c_u, h_u, l_u, v_u, t_u = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng_u,
                                                   vcbb=vcbb, K=K)
        c_v, h_v, l_v, v_v, t_v = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng_v,
                                                   vcbb=vcbb, K=K)

        # Precompute per-path indicators
        at_u = _atr(h_u, l_u, c_u, ATR_P)
        vd_u = _vdo(c_u, h_u, l_u, v_u, t_u, VDO_F, VDO_S)
        ratr_u = _robust_atr(h_u, l_u, c_u)

        at_v = _atr(h_v, l_v, c_v, ATR_P)
        vd_v = _vdo(c_v, h_v, l_v, v_v, t_v, VDO_F, VDO_S)
        ratr_v = _robust_atr(h_v, l_v, c_v)

        for j, slow in enumerate(SLOW_PERIODS):
            fast = max(5, slow // 4)

            # Uniform
            ef_u = _ema(c_u, fast)
            es_u = _ema(c_u, slow)
            r_e0_u = _sim_core(c_u, ef_u, es_u, at_u, vd_u, wi, at_u)
            r_e5_u = _sim_core(c_u, ef_u, es_u, at_u, vd_u, wi, ratr_u)
            for k in mkeys:
                R["uniform"]["e0"][k][b, j] = r_e0_u[k]
                R["uniform"]["e5"][k][b, j] = r_e5_u[k]

            # VCBB
            ef_v = _ema(c_v, fast)
            es_v = _ema(c_v, slow)
            r_e0_v = _sim_core(c_v, ef_v, es_v, at_v, vd_v, wi, at_v)
            r_e5_v = _sim_core(c_v, ef_v, es_v, at_v, vd_v, wi, ratr_v)
            for k in mkeys:
                R["vcbb"]["e0"][k][b, j] = r_e0_v[k]
                R["vcbb"]["e5"][k][b, j] = r_e5_v[k]

        if (b + 1) % 100 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (b + 1) * (N_BOOT - b - 1)
            print(f"  ... {b + 1}/{N_BOOT} ({elapsed:.0f}s, ETA {eta:.0f}s)")

    total_time = time.time() - t0
    print(f"\n  Bootstrap complete in {total_time:.0f}s")

    # ══════════════════════════════════════════════════════════════════════════
    # Analysis
    # ══════════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 90)
    print("RESULTS: E5 vs E0 — Uniform vs VCBB")
    print("=" * 90)

    # Per-timescale table
    header = (f"{'N':>5s} {'days':>4s} │ "
              f"{'U P(Sh+)':>8s} {'V P(Sh+)':>8s} │ "
              f"{'U P(CG+)':>8s} {'V P(CG+)':>8s} │ "
              f"{'U P(MD-)':>8s} {'V P(MD-)':>8s} │ "
              f"{'U ΔSh':>7s} {'V ΔSh':>7s} │ "
              f"{'U ΔMD':>6s} {'V ΔMD':>6s}")
    print(f"\n{header}")
    print("-" * 110)

    wins = {m: {met: 0 for met in ["sharpe", "cagr", "mdd"]} for m in ["uniform", "vcbb"]}

    ts_results = []

    for j, slow in enumerate(SLOW_PERIODS):
        days = slow * 4 / 24
        row = {"N": slow, "days": round(days, 1)}

        for method in ["uniform", "vcbb"]:
            d_sh = R[method]["e5"]["sharpe"][:, j] - R[method]["e0"]["sharpe"][:, j]
            d_cg = R[method]["e5"]["cagr"][:, j] - R[method]["e0"]["cagr"][:, j]
            d_md = R[method]["e0"]["mdd"][:, j] - R[method]["e5"]["mdd"][:, j]  # positive = E5 lower MDD

            p_sh = float(np.mean(d_sh > 0))
            p_cg = float(np.mean(d_cg > 0))
            p_md = float(np.mean(d_md > 0))

            if p_sh > 0.5: wins[method]["sharpe"] += 1
            if p_cg > 0.5: wins[method]["cagr"] += 1
            if p_md > 0.5: wins[method]["mdd"] += 1

            row[method] = {
                "p_sharpe": round(p_sh, 4),
                "p_cagr": round(p_cg, 4),
                "p_mdd": round(p_md, 4),
                "delta_sharpe": round(float(np.median(d_sh)), 5),
                "delta_mdd": round(float(np.median(d_md)), 2),
                "median_sharpe_e0": round(float(np.median(R[method]["e0"]["sharpe"][:, j])), 4),
                "median_sharpe_e5": round(float(np.median(R[method]["e5"]["sharpe"][:, j])), 4),
                "median_mdd_e0": round(float(np.median(R[method]["e0"]["mdd"][:, j])), 2),
                "median_mdd_e5": round(float(np.median(R[method]["e5"]["mdd"][:, j])), 2),
                "median_cagr_e0": round(float(np.median(R[method]["e0"]["cagr"][:, j])), 2),
                "median_cagr_e5": round(float(np.median(R[method]["e5"]["cagr"][:, j])), 2),
            }

        u = row["uniform"]
        v = row["vcbb"]
        print(f"  {slow:>4d} {days:>3.0f}d │ "
              f"{u['p_sharpe']*100:>7.1f}% {v['p_sharpe']*100:>7.1f}% │ "
              f"{u['p_cagr']*100:>7.1f}% {v['p_cagr']*100:>7.1f}% │ "
              f"{u['p_mdd']*100:>7.1f}% {v['p_mdd']*100:>7.1f}% │ "
              f"{u['delta_sharpe']:>+6.4f} {v['delta_sharpe']:>+6.4f} │ "
              f"{u['delta_mdd']:>+5.1f} {v['delta_mdd']:>+5.1f}")

        ts_results.append(row)

    # Binomial meta-test
    print("\n" + "-" * 90)
    print("BINOMIAL META-TEST: E5 better at how many timescales?")
    print("-" * 90)

    print(f"  {'Metric':<20s}  {'Uniform':>15s}  {'VCBB':>15s}  │ {'Uni p':>10s} {'VCB p':>10s}")
    print("  " + "-" * 80)

    binomial_out = {}
    for met_label, met_key in [("P(Sharpe+)>50%", "sharpe"),
                                ("P(CAGR+)>50%", "cagr"),
                                ("P(MDD-)>50%", "mdd")]:
        uw = wins["uniform"][met_key]
        vw = wins["vcbb"][met_key]
        up = sp_stats.binomtest(uw, n_sp, 0.5, alternative='greater').pvalue
        vp = sp_stats.binomtest(vw, n_sp, 0.5, alternative='greater').pvalue
        print(f"  {met_label:<20s}  {uw:>7d}/{n_sp:>2d}       {vw:>7d}/{n_sp:>2d}       │ "
              f"{up:>10.2e} {vp:>10.2e}")
        binomial_out[met_key] = {
            "uniform_wins": uw, "vcbb_wins": vw,
            "uniform_p": float(up), "vcbb_p": float(vp),
        }

    # Aggregate effect sizes
    print("\n" + "-" * 90)
    print("AGGREGATE EFFECT SIZES (median across timescales)")
    print("-" * 90)

    for metric in ["sharpe", "cagr", "mdd"]:
        print(f"\n  {metric.upper()}:")
        for method in ["uniform", "vcbb"]:
            if metric == "mdd":
                deltas = [float(np.median(R[method]["e0"][metric][:, j]) -
                                np.median(R[method]["e5"][metric][:, j])) for j in range(n_sp)]
                label = "E5 MDD improvement"
            else:
                deltas = [float(np.median(R[method]["e5"][metric][:, j]) -
                                np.median(R[method]["e0"][metric][:, j])) for j in range(n_sp)]
                label = f"E5 {metric} delta"
            m_label = "Uniform" if method == "uniform" else "VCBB   "
            print(f"    {m_label} {label}: median {np.median(deltas):+.4f}, "
                  f"range [{min(deltas):+.4f}, {max(deltas):+.4f}]")

    # ── Verdict ──
    print("\n" + "=" * 90)
    print("VERDICT")
    print("=" * 90)

    # Compare conclusions
    for met_key, met_label in [("sharpe", "Sharpe"), ("cagr", "CAGR"), ("mdd", "MDD")]:
        uw = wins["uniform"][met_key]
        vw = wins["vcbb"][met_key]
        up = binomial_out[met_key]["uniform_p"]
        vp = binomial_out[met_key]["vcbb_p"]

        def verdict(p):
            if p < 0.001: return "PROVEN ***"
            if p < 0.01: return "PROVEN **"
            if p < 0.025: return "PROVEN *"
            if p < 0.05: return "STRONG"
            if p < 0.10: return "MARGINAL"
            return "NOT SIG"

        u_v = verdict(up)
        v_v = verdict(vp)
        changed = u_v != v_v
        flag = " ← CHANGED!" if changed else ""
        print(f"  {met_label:<8s}: Uniform {uw:>2d}/16 ({u_v:<12s})  VCBB {vw:>2d}/16 ({v_v:<12s}){flag}")

    # E5 approval check
    vcbb_cagr_p = binomial_out["cagr"]["vcbb_p"]
    vcbb_mdd_p = binomial_out["mdd"]["vcbb_p"]
    vcbb_sharpe_p = binomial_out["sharpe"]["vcbb_p"]

    print(f"\n  E5 APPROVAL under VCBB:")
    if vcbb_cagr_p < 0.05 and vcbb_mdd_p < 0.05:
        print(f"    E5 IMPROVES both CAGR and MDD → APPROVED")
    elif vcbb_mdd_p < 0.025 and vcbb_cagr_p > 0.10:
        print(f"    E5 reduces MDD but costs CAGR → REJECTED (same as uniform)")
    elif vcbb_mdd_p < 0.025 and vcbb_cagr_p > 0.05:
        print(f"    E5 reduces MDD, CAGR cost marginal → NEEDS REVIEW")
    else:
        cagr_wins = wins["vcbb"]["cagr"]
        mdd_wins = wins["vcbb"]["mdd"]
        if mdd_wins >= 13 and cagr_wins <= 3:
            print(f"    E5 reduces MDD ({mdd_wins}/16) but costs CAGR ({cagr_wins}/16) → REJECTED")
        elif mdd_wins >= 13 and cagr_wins >= 8:
            print(f"    E5 reduces MDD ({mdd_wins}/16) with acceptable CAGR ({cagr_wins}/16) → NEEDS REVIEW")
        else:
            print(f"    MDD wins={mdd_wins}/16, CAGR wins={cagr_wins}/16 → INCONCLUSIVE")

    # Save
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "e5_vcbb_test.json"
    with open(out_path, "w") as f:
        json.dump({"timescales": ts_results, "binomial": binomial_out,
                    "total_time_s": round(total_time, 1)}, f, indent=2)
    print(f"\n  Results saved to {out_path}")
    print(f"  Total time: {total_time:.0f}s")


if __name__ == "__main__":
    main()
