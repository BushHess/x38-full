#!/usr/bin/env python3
"""Trail_mult fine sweep: find optimal trail in [2.0, 5.0].

Previous finding: trail=4.5 PROVEN ** on CAGR/NAV vs default trail=3.0,
but WORSE on MDD. Is there a trail value that improves returns WITHOUT
sacrificing MDD? Or a better sweet spot?

Method:
  Phase 1: Real data sweep trail=2.0 to 5.0 step 0.25 (13 values)
  Phase 2: Bootstrap 500 paths × 16 timescales, ALL trail values vs DEFAULT
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

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from strategies.vtrend.strategy import _ema, _atr, _vdo
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ── Constants ─────────────────────────────────────────────────────────

DATA     = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH     = 10_000.0
CPS      = 0.0025
ANN      = math.sqrt(6.0 * 365.25)
ATR_P    = 14
VDO_F    = 12
VDO_S    = 28
VDO_THR  = 0.0

N_BOOT   = 500
BLKSZ    = 60
SEED     = 42
WARMUP   = 365
START    = "2019-01-01"
END      = "2026-02-20"

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

# Trail sweep range
TRAIL_VALS = [2.00, 2.25, 2.50, 2.75, 3.00, 3.25, 3.50, 3.75, 4.00, 4.25, 4.50, 4.75, 5.00]
DEF_TRAIL  = 3.0

OUTDIR = Path(__file__).resolve().parent / "results" / "trail_sweep"


# ═══════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars; n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i; break
    return cl, hi, lo, vo, tb, wi, n


def sim_vtrend(cl, ef, es, at, vd, wi, trail):
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0; pe = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0; nt += 1; px = False
        nav = cash + bq * p
        if i >= wi:
            if not started:
                navs_start = nav; nav_peak = nav; prev_nav = nav; started = True
            else:
                if prev_nav > 0:
                    r = nav / prev_nav - 1.0
                    rets_sum += r; rets_sq_sum += r * r; n_rets += 1
                prev_nav = nav
            navs_end = nav
            if nav > nav_peak: nav_peak = nav
            ratio = nav / nav_peak if nav_peak > 0 else 1.0
            if ratio < nav_min_ratio: nav_min_ratio = ratio
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash

    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": 0, "final_nav": 0.0}
    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd,
            "calmar": calmar, "trades": nt, "final_nav": navs_end}


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    n_tv = len(TRAIL_VALS)
    n_sp = len(SLOW_PERIODS)

    print("TRAIL_MULT FINE SWEEP: 2.0 → 5.0")
    print("=" * 90)
    print(f"  Trail values: {TRAIL_VALS}")
    print(f"  Default: trail={DEF_TRAIL}")
    print(f"  Bootstrap: {N_BOOT} paths × {n_sp} timescales × {n_tv} trails")

    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  Data: {n} H4 bars, warmup index = {wi}")

    # ══════════════════════════════════════════════════════════════════
    # Phase 1: Real data — all trails × 16 timescales
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*90}")
    print("PHASE 1: REAL DATA — trail × timescale")
    print(f"{'='*90}")

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # Sharpe heatmap [trail][sp]
    real_sharpe = {}
    real_cagr = {}
    real_mdd = {}
    real_trades = {}

    for tv in TRAIL_VALS:
        real_sharpe[tv] = {}
        real_cagr[tv] = {}
        real_mdd[tv] = {}
        real_trades[tv] = {}
        for sp in SLOW_PERIODS:
            fp = max(5, sp // 4)
            ef = _ema(cl, fp); es = _ema(cl, sp)
            r = sim_vtrend(cl, ef, es, at, vd, wi, tv)
            real_sharpe[tv][sp] = r["sharpe"]
            real_cagr[tv][sp] = r["cagr"]
            real_mdd[tv][sp] = r["mdd"]
            real_trades[tv][sp] = r["trades"]

    # Print Sharpe heatmap
    print(f"\n  Sharpe heatmap (trail × slow_period):")
    header = f"  {'trail':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  mean   best"
    print(header)
    print("  " + "-" * (7 + 6 * n_sp + 14))

    for tv in TRAIL_VALS:
        row = f"  {tv:5.2f}"
        vals = []
        for sp in SLOW_PERIODS:
            sh = real_sharpe[tv][sp]
            row += f" {sh:+5.3f}"
            vals.append(sh)
        mean_sh = np.mean(vals)
        best_sh = max(vals)
        marker = " ← DEF" if tv == DEF_TRAIL else ""
        row += f"  {mean_sh:+5.3f}  {best_sh:+5.3f}{marker}"
        print(row)

    # Print CAGR heatmap
    print(f"\n  CAGR heatmap:")
    header = f"  {'trail':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  mean"
    print(header)
    print("  " + "-" * (7 + 6 * n_sp + 7))

    for tv in TRAIL_VALS:
        row = f"  {tv:5.2f}"
        vals = []
        for sp in SLOW_PERIODS:
            cg = real_cagr[tv][sp]
            row += f" {cg:+5.1f}"
            vals.append(cg)
        marker = " ← DEF" if tv == DEF_TRAIL else ""
        row += f"  {np.mean(vals):+5.1f}{marker}"
        print(row)

    # Print MDD heatmap
    print(f"\n  MDD heatmap:")
    header = f"  {'trail':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  mean"
    print(header)
    print("  " + "-" * (7 + 6 * n_sp + 7))

    for tv in TRAIL_VALS:
        row = f"  {tv:5.2f}"
        vals = []
        for sp in SLOW_PERIODS:
            md = real_mdd[tv][sp]
            row += f"  {md:4.1f}"
            vals.append(md)
        marker = " ← DEF" if tv == DEF_TRAIL else ""
        row += f"  {np.mean(vals):4.1f}{marker}"
        print(row)

    # Trades heatmap
    print(f"\n  Trades heatmap:")
    header = f"  {'trail':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    print(header)
    print("  " + "-" * (7 + 6 * n_sp))

    for tv in TRAIL_VALS:
        row = f"  {tv:5.2f}"
        for sp in SLOW_PERIODS:
            row += f"  {real_trades[tv][sp]:4d}"
        marker = " ← DEF" if tv == DEF_TRAIL else ""
        print(f"{row}{marker}")

    # ══════════════════════════════════════════════════════════════════
    # Phase 2: Bootstrap — all trails vs DEFAULT
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*90}")
    print(f"PHASE 2: BOOTSTRAP — {N_BOOT} paths × {n_sp} TS × {n_tv} trails")
    print(f"{'='*90}")

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    # boot[trail_idx][metric] = (N_BOOT, n_sp)
    mkeys = ["sharpe", "cagr", "mdd", "final_nav"]
    boot = {}
    for ti, tv in enumerate(TRAIL_VALS):
        boot[ti] = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 50 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)", flush=True)

        c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng, vcbb=vcbb_state)
        at_b = _atr(h, l, c, ATR_P)
        vd_b = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp); es = _ema(c, sp)

            for ti, tv in enumerate(TRAIL_VALS):
                r = sim_vtrend(c, ef, es, at_b, vd_b, 0, tv)
                for m in mkeys:
                    boot[ti][m][b, j] = r[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({el/60:.1f} min)")

    # Find DEFAULT index
    def_idx = TRAIL_VALS.index(DEF_TRAIL)

    # ── Per-trail binomial summary ──
    print(f"\n  BINOMIAL SUMMARY (each trail vs DEFAULT trail={DEF_TRAIL}):")
    print(f"  {'trail':>5s}  {'Sh w':>5s}  {'Sh p':>10s}  {'Sh':>5s}  "
          f"{'CG w':>5s}  {'CG p':>10s}  {'CG':>5s}  "
          f"{'MD w':>5s}  {'MD p':>10s}  {'MD':>5s}  "
          f"{'NV w':>5s}  {'NV p':>10s}  {'NV':>5s}")
    print("  " + "-" * 110)

    binom_results = {}

    for ti, tv in enumerate(TRAIL_VALS):
        if ti == def_idx:
            print(f"  {tv:5.2f}  --- DEFAULT ---")
            continue

        w = {"sharpe": 0, "cagr": 0, "mdd": 0, "nav": 0}
        for j in range(n_sp):
            d_sh = boot[ti]["sharpe"][:, j] - boot[def_idx]["sharpe"][:, j]
            d_cg = boot[ti]["cagr"][:, j] - boot[def_idx]["cagr"][:, j]
            d_md = boot[def_idx]["mdd"][:, j] - boot[ti]["mdd"][:, j]
            d_nv = boot[ti]["final_nav"][:, j] - boot[def_idx]["final_nav"][:, j]

            if float(np.mean(d_sh > 0)) > 0.5: w["sharpe"] += 1
            if float(np.mean(d_cg > 0)) > 0.5: w["cagr"] += 1
            if float(np.mean(d_md > 0)) > 0.5: w["mdd"] += 1
            if float(np.mean(d_nv > 0)) > 0.5: w["nav"] += 1

        p_sh = binomtest(w["sharpe"], n_sp, 0.5, alternative='greater').pvalue
        p_cg = binomtest(w["cagr"], n_sp, 0.5, alternative='greater').pvalue
        p_md = binomtest(w["mdd"], n_sp, 0.5, alternative='greater').pvalue
        p_nv = binomtest(w["nav"], n_sp, 0.5, alternative='greater').pvalue

        def verd(p):
            return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.025 else "~" if p < 0.05 else ""

        print(f"  {tv:5.2f}  {w['sharpe']:3d}/16  {p_sh:10.6f}  {verd(p_sh):>4s}  "
              f"{w['cagr']:3d}/16  {p_cg:10.6f}  {verd(p_cg):>4s}  "
              f"{w['mdd']:3d}/16  {p_md:10.6f}  {verd(p_md):>4s}  "
              f"{w['nav']:3d}/16  {p_nv:10.6f}  {verd(p_nv):>4s}")

        binom_results[str(tv)] = {
            "sharpe": {"wins": w["sharpe"], "p": round(p_sh, 8)},
            "cagr": {"wins": w["cagr"], "p": round(p_cg, 8)},
            "mdd": {"wins": w["mdd"], "p": round(p_md, 8)},
            "nav": {"wins": w["nav"], "p": round(p_nv, 8)},
        }

    # ── Median Sharpe per trail across timescales ──
    print(f"\n  Median Sharpe per trail (bootstrap):")
    header = f"  {'trail':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  mean"
    print(header)
    print("  " + "-" * (7 + 6 * n_sp + 7))

    for ti, tv in enumerate(TRAIL_VALS):
        row = f"  {tv:5.2f}"
        vals = []
        for j in range(n_sp):
            med = float(np.median(boot[ti]["sharpe"][:, j]))
            row += f" {med:+5.3f}"
            vals.append(med)
        marker = " ← DEF" if tv == DEF_TRAIL else ""
        row += f"  {np.mean(vals):+5.3f}{marker}"
        print(row)

    # ── Median MDD per trail ──
    print(f"\n  Median MDD per trail (bootstrap):")
    header = f"  {'trail':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  mean"
    print(header)
    print("  " + "-" * (7 + 6 * n_sp + 7))

    for ti, tv in enumerate(TRAIL_VALS):
        row = f"  {tv:5.2f}"
        vals = []
        for j in range(n_sp):
            med = float(np.median(boot[ti]["mdd"][:, j]))
            row += f"  {med:4.1f}"
            vals.append(med)
        marker = " ← DEF" if tv == DEF_TRAIL else ""
        row += f"  {np.mean(vals):4.1f}{marker}"
        print(row)

    # ── Overall verdict ──
    print(f"\n{'='*90}")
    print("VERDICT")
    print(f"{'='*90}")

    print(f"\n  Trail sweep summary (vs DEFAULT trail=3.0):")
    print(f"  {'trail':>5s}  {'Sharpe':>8s}  {'CAGR':>8s}  {'MDD':>8s}  {'NAV':>8s}  {'Assessment':>20s}")
    print("  " + "-" * 65)

    for tv in TRAIL_VALS:
        if tv == DEF_TRAIL:
            print(f"  {tv:5.2f}  {'--- DEFAULT ---':^55s}")
            continue
        br = binom_results[str(tv)]
        # Classify
        sh_ok = br["sharpe"]["wins"] >= 9
        cg_ok = br["cagr"]["wins"] >= 9
        md_ok = br["mdd"]["wins"] >= 9
        nv_ok = br["nav"]["wins"] >= 9

        if cg_ok and md_ok:
            assess = "BETTER (ret+risk)"
        elif cg_ok and not md_ok:
            assess = "MORE RETURN, MORE RISK"
        elif not cg_ok and md_ok:
            assess = "LESS RETURN, LESS RISK"
        elif br["cagr"]["wins"] <= 7 and br["mdd"]["wins"] <= 7:
            assess = "WORSE"
        else:
            assess = "~EQUIVALENT"

        print(f"  {tv:5.2f}  {br['sharpe']['wins']:5d}/16  {br['cagr']['wins']:5d}/16  "
              f"{br['mdd']['wins']:5d}/16  {br['nav']['wins']:5d}/16  {assess:>20s}")

    el_total = time.time() - t_start
    print(f"\n  Total time: {el_total:.0f}s ({el_total/60:.1f} min)")

    # Save
    OUTDIR.mkdir(parents=True, exist_ok=True)
    output = {
        "config": {"trail_vals": TRAIL_VALS, "default_trail": DEF_TRAIL,
                    "n_boot": N_BOOT, "seed": SEED},
        "real_data_sharpe": {str(tv): {str(sp): real_sharpe[tv][sp] for sp in SLOW_PERIODS}
                             for tv in TRAIL_VALS},
        "bootstrap_binomial": binom_results,
    }
    outfile = OUTDIR / "trail_sweep.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print("=" * 90)
