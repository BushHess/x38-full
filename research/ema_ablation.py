#!/usr/bin/env python3
"""EMA(21d) Ablation Study — Does VTREND add value beyond simple EMA timing?

Hypothesis: The EMA(21d) regime filter is doing all the work, and VTREND's
complex signal (EMA crossover + VDO + ATR trail) adds nothing.

Three strategies compared:
  A) Simple EMA(21d): hold BTC when close > EMA(126 H4), cash otherwise
  B) VTREND E0: standard algorithm (3 params)
  C) VTREND E0 + EMA(21d): E0 with regime entry filter

If A ≈ C: VTREND is redundant — the simple EMA does all the work.
If C >> A: VTREND adds genuine alpha on top of regime timing.

Phases:
  1. BTC real data: 3-way comparison at N=120 + all 16 timescales
  2. Bootstrap: 500 paths × 3-way paired comparison
  3. Bootstrap × 16 timescales (VTREND variants vs simple EMA baseline)
"""

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
CPS      = 0.0025       # 50 bps RT
TRAIL    = 3.0
ATR_P    = 14
VDO_F    = 12
VDO_S    = 28
VDO_THR  = 0.0
ANN      = math.sqrt(6.0 * 365.25)

EMA_REGIME_P    = 126    # EMA(21d) = 126 H4 bars
EMA_REGIME_DAYS = 21

N_BOOT   = 500
BLKSZ    = 60
SEED     = 42
WARMUP   = 365

START    = "2019-01-01"
END      = "2026-02-20"

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

OUTDIR = Path(__file__).resolve().parent / "results" / "ema_ablation"


# ═══════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════

def load_arrays():
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break
    return cl, hi, lo, vo, tb, wi, n


# ═══════════════════════════════════════════════════════════════════════
# Strategy A: Simple EMA hold/cash
# ═══════════════════════════════════════════════════════════════════════

def _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt):
    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "final_nav": navs_end}
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


def sim_simple_ema(cl, ema_r, wi):
    """Strategy A: hold when close > EMA(21d), cash otherwise.

    Entry: close > EMA → buy next bar open (= prev close).
    Exit: close < EMA → sell next bar open.
    Same cost model as VTREND.
    """
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    navs_start = 0.0; navs_end = 0.0; nav_peak = 0.0; nav_min_ratio = 1.0
    rets_sum = 0.0; rets_sq_sum = 0.0; n_rets = 0; prev_nav = 0.0; started = False

    for i in range(n):
        p = cl[i]

        # Fill pending orders at bar open (= previous close)
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True
            elif px:
                px = False; cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; nt += 1

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

        # Signal: simple price vs EMA crossover
        if math.isnan(ema_r[i]):
            continue

        if not inp:
            if p > ema_r[i]:
                pe = True
        else:
            if p < ema_r[i]:
                px = True

    # Force close
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash

    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Strategy B: VTREND E0 (standard)
# ═══════════════════════════════════════════════════════════════════════

def sim_e0(cl, ef, es, at, vd, wi):
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
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Strategy C: VTREND E0 + EMA(21d) filter
# ═══════════════════════════════════════════════════════════════════════

def sim_filtered(cl, ef, es, at, vd, wi, ema_r):
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
            if ef[i] > es[i] and vd[i] > VDO_THR and p > ema_r[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: BTC Real Data — 3-way comparison
# ═══════════════════════════════════════════════════════════════════════

def phase1_real_data(cl, hi, lo, vo, tb, wi):
    print(f"\n{'='*90}")
    print(f"PHASE 1: BTC REAL DATA — 3-WAY COMPARISON")
    print(f"{'='*90}")

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    ema_r = _ema(cl, EMA_REGIME_P)

    # ── Part A: At N=120 (default VTREND timescale) ──
    sp = 120; fp = max(5, sp // 4)
    ef = _ema(cl, fp); es = _ema(cl, sp)

    r_simple = sim_simple_ema(cl, ema_r, wi)
    r_e0 = sim_e0(cl, ef, es, at, vd, wi)
    r_filt = sim_filtered(cl, ef, es, at, vd, wi, ema_r)

    print(f"\n  At N=120 (default):")
    print(f"  {'Strategy':>20s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  {'Trades':>6s}  {'Final':>10s}")
    print("  " + "-" * 70)
    for label, r in [("A) Simple EMA(21d)", r_simple),
                     ("B) VTREND E0", r_e0),
                     ("C) E0 + EMA(21d)", r_filt)]:
        print(f"  {label:>20s}  {r['sharpe']:+7.3f}  {r['cagr']:+6.1f}%  {r['mdd']:5.1f}%  "
              f"{r['calmar']:+7.3f}  {r['trades']:6d}  {r['final_nav']:10.2f}")

    print(f"\n  VTREND E0 vs Simple EMA:")
    print(f"    ΔSharpe (B-A) = {r_e0['sharpe'] - r_simple['sharpe']:+.4f}")
    print(f"    ΔCAGR   (B-A) = {r_e0['cagr'] - r_simple['cagr']:+.2f}%")
    print(f"    ΔMDD    (B-A) = {r_e0['mdd'] - r_simple['mdd']:+.2f}pp")

    print(f"\n  E0+EMA21 vs Simple EMA:")
    print(f"    ΔSharpe (C-A) = {r_filt['sharpe'] - r_simple['sharpe']:+.4f}")
    print(f"    ΔCAGR   (C-A) = {r_filt['cagr'] - r_simple['cagr']:+.2f}%")
    print(f"    ΔMDD    (C-A) = {r_filt['mdd'] - r_simple['mdd']:+.2f}pp")

    results_n120 = {
        "simple_ema": r_simple,
        "vtrend_e0": r_e0,
        "e0_plus_ema": r_filt,
    }

    # ── Part B: 16-timescale sweep ──
    print(f"\n  16-Timescale Sweep:")
    print(f"  {'sp':>5s}  {'days':>5s}  {'Simple':>7s}  {'E0':>7s}  {'E0+EMA':>7s}  "
          f"{'E0-Simp':>8s}  {'E0E-Simp':>9s}  {'E0E-E0':>7s}")
    print("  " + "-" * 65)

    ts_results = {}
    e0_beats_simple = 0
    filt_beats_simple = 0
    filt_beats_e0 = 0

    for sp in SLOW_PERIODS:
        fp_v = max(5, sp // 4)
        ef = _ema(cl, fp_v); es = _ema(cl, sp)

        r_s = sim_simple_ema(cl, ema_r, wi)    # Simple EMA doesn't depend on sp
        r_e = sim_e0(cl, ef, es, at, vd, wi)
        r_f = sim_filtered(cl, ef, es, at, vd, wi, ema_r)

        d_e0_s = r_e["sharpe"] - r_s["sharpe"]
        d_f_s = r_f["sharpe"] - r_s["sharpe"]
        d_f_e = r_f["sharpe"] - r_e["sharpe"]

        if d_e0_s > 0: e0_beats_simple += 1
        if d_f_s > 0: filt_beats_simple += 1
        if d_f_e > 0: filt_beats_e0 += 1

        days = sp * 4 / 24
        print(f"  {sp:5d}  {days:5.0f}  {r_s['sharpe']:+7.3f}  {r_e['sharpe']:+7.3f}  "
              f"{r_f['sharpe']:+7.3f}  {d_e0_s:+8.4f}  {d_f_s:+9.4f}  {d_f_e:+7.4f}")

        ts_results[sp] = {
            "simple_sharpe": r_s["sharpe"],
            "e0_sharpe": r_e["sharpe"],
            "filt_sharpe": r_f["sharpe"],
            "e0_cagr": r_e["cagr"],
            "filt_cagr": r_f["cagr"],
            "simple_cagr": r_s["cagr"],
            "e0_mdd": r_e["mdd"],
            "filt_mdd": r_f["mdd"],
            "simple_mdd": r_s["mdd"],
        }

    print(f"\n  Summary (Sharpe):")
    print(f"    E0 > Simple EMA:     {e0_beats_simple}/16 timescales")
    print(f"    E0+EMA > Simple EMA: {filt_beats_simple}/16 timescales")
    print(f"    E0+EMA > E0:         {filt_beats_e0}/16 timescales")

    return results_n120, ts_results


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Bootstrap 500 paths — 3-way paired comparison
# ═══════════════════════════════════════════════════════════════════════

def phase2_bootstrap(cl, hi, lo, vo, tb, wi):
    print(f"\n{'='*90}")
    print(f"PHASE 2: BOOTSTRAP — {N_BOOT} paths × 16 timescales × 3 strategies")
    print(f"{'='*90}")

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "final_nav"]

    # [strategy][metric] = (N_BOOT, n_sp) — but simple EMA has same value across sp
    boot_simple = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_e0 = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_filt = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 50 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)", flush=True)

        c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng, vcbb=vcbb_state)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ema_r = _ema(c, EMA_REGIME_P)

        # Simple EMA (same across all timescales — compute once)
        r_s = sim_simple_ema(c, ema_r, 0)

        for j, sp in enumerate(SLOW_PERIODS):
            fp_v = max(5, sp // 4)
            ef = _ema(c, fp_v); es = _ema(c, sp)

            r_e = sim_e0(c, ef, es, at, vd, 0)
            r_f = sim_filtered(c, ef, es, at, vd, 0, ema_r)

            for m in mkeys:
                boot_simple[m][b, j] = r_s[m]
                boot_e0[m][b, j] = r_e[m]
                boot_filt[m][b, j] = r_f[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({el/60:.1f} min)")

    # ── Part A: Per-timescale comparison ──
    print(f"\n  E0 vs Simple EMA (Sharpe):")
    print(f"  {'sp':>5}  {'days':>5}  {'P(E0>S)':>8}  {'P(F>S)':>8}  {'P(F>E0)':>8}  "
          f"{'medS':>8}  {'medE0':>8}  {'medF':>8}")
    print("  " + "-" * 70)

    wins_e0_s = {"sharpe": 0, "cagr": 0, "mdd": 0, "nav": 0}
    wins_f_s = {"sharpe": 0, "cagr": 0, "mdd": 0, "nav": 0}
    wins_f_e = {"sharpe": 0, "cagr": 0, "mdd": 0, "nav": 0}

    ts_boot = {}

    for j, sp in enumerate(SLOW_PERIODS):
        # E0 vs Simple
        d_e0_s_sh = boot_e0["sharpe"][:, j] - boot_simple["sharpe"][:, j]
        d_e0_s_cg = boot_e0["cagr"][:, j] - boot_simple["cagr"][:, j]
        d_e0_s_md = boot_simple["mdd"][:, j] - boot_e0["mdd"][:, j]  # positive = E0 better
        d_e0_s_nv = boot_e0["final_nav"][:, j] - boot_simple["final_nav"][:, j]

        # E0+EMA vs Simple
        d_f_s_sh = boot_filt["sharpe"][:, j] - boot_simple["sharpe"][:, j]
        d_f_s_cg = boot_filt["cagr"][:, j] - boot_simple["cagr"][:, j]
        d_f_s_md = boot_simple["mdd"][:, j] - boot_filt["mdd"][:, j]
        d_f_s_nv = boot_filt["final_nav"][:, j] - boot_simple["final_nav"][:, j]

        # E0+EMA vs E0
        d_f_e_sh = boot_filt["sharpe"][:, j] - boot_e0["sharpe"][:, j]

        p_e0_s = float(np.mean(d_e0_s_sh > 0))
        p_f_s = float(np.mean(d_f_s_sh > 0))
        p_f_e = float(np.mean(d_f_e_sh > 0))

        if p_e0_s > 0.5: wins_e0_s["sharpe"] += 1
        if float(np.mean(d_e0_s_cg > 0)) > 0.5: wins_e0_s["cagr"] += 1
        if float(np.mean(d_e0_s_md > 0)) > 0.5: wins_e0_s["mdd"] += 1
        if float(np.mean(d_e0_s_nv > 0)) > 0.5: wins_e0_s["nav"] += 1

        if p_f_s > 0.5: wins_f_s["sharpe"] += 1
        if float(np.mean(d_f_s_cg > 0)) > 0.5: wins_f_s["cagr"] += 1
        if float(np.mean(d_f_s_md > 0)) > 0.5: wins_f_s["mdd"] += 1
        if float(np.mean(d_f_s_nv > 0)) > 0.5: wins_f_s["nav"] += 1

        if p_f_e > 0.5: wins_f_e["sharpe"] += 1
        if float(np.mean(boot_filt["cagr"][:, j] > boot_e0["cagr"][:, j])) > 0.5: wins_f_e["cagr"] += 1
        if float(np.mean(boot_e0["mdd"][:, j] > boot_filt["mdd"][:, j])) > 0.5: wins_f_e["mdd"] += 1
        if float(np.mean(boot_filt["final_nav"][:, j] > boot_e0["final_nav"][:, j])) > 0.5: wins_f_e["nav"] += 1

        med_s = float(np.median(boot_simple["sharpe"][:, j]))
        med_e = float(np.median(boot_e0["sharpe"][:, j]))
        med_f = float(np.median(boot_filt["sharpe"][:, j]))

        days = sp * 4 / 24
        print(f"  {sp:5d}  {days:5.0f}  {p_e0_s*100:7.1f}%  {p_f_s*100:7.1f}%  {p_f_e*100:7.1f}%  "
              f"{med_s:+8.4f}  {med_e:+8.4f}  {med_f:+8.4f}")

        ts_boot[sp] = {
            "P_e0_beats_simple": round(p_e0_s, 4),
            "P_filt_beats_simple": round(p_f_s, 4),
            "P_filt_beats_e0": round(p_f_e, 4),
            "med_simple_sharpe": round(med_s, 4),
            "med_e0_sharpe": round(med_e, 4),
            "med_filt_sharpe": round(med_f, 4),
        }

    # ── Part B: Binomial meta-tests ──
    print(f"\n  Binomial meta-test (>50% at how many of 16 timescales):")
    print(f"  {'Comparison':>25s}  {'Metric':>8s}  {'wins':>5}/{n_sp}  {'binom p':>10s}  {'verdict':>12s}")
    print("  " + "-" * 75)

    binom_results = {}

    for comp_label, wins_dict in [
        ("E0 vs Simple", wins_e0_s),
        ("E0+EMA vs Simple", wins_f_s),
        ("E0+EMA vs E0", wins_f_e),
    ]:
        binom_results[comp_label] = {}
        for metric, wins in wins_dict.items():
            p_b = binomtest(wins, n_sp, 0.5, alternative='greater').pvalue
            verdict = ("PROVEN ***" if p_b < 0.001 else "PROVEN **" if p_b < 0.01
                       else "PROVEN *" if p_b < 0.025 else "STRONG" if p_b < 0.05
                       else "MARGINAL" if p_b < 0.10 else "NOT SIG")
            print(f"  {comp_label:>25s}  {metric:>8s}  {wins:5d}/{n_sp}  {p_b:10.6f}  {verdict:>12s}")
            binom_results[comp_label][metric] = {
                "wins": wins, "p_binom": round(p_b, 8), "verdict": verdict
            }

    # ── Part C: At N=120 specifically ──
    j120 = SLOW_PERIODS.index(120)
    print(f"\n  At N=120 specifically (500 paths):")

    comparisons = [
        ("E0 vs Simple", boot_e0, boot_simple),
        ("E0+EMA vs Simple", boot_filt, boot_simple),
        ("E0+EMA vs E0", boot_filt, boot_e0),
    ]

    n120_results = {}
    for label, ba, bb in comparisons:
        d_sh = ba["sharpe"][:, j120] - bb["sharpe"][:, j120]
        d_cg = ba["cagr"][:, j120] - bb["cagr"][:, j120]
        d_md = bb["mdd"][:, j120] - ba["mdd"][:, j120]  # positive = first is better
        d_nv = ba["final_nav"][:, j120] - bb["final_nav"][:, j120]

        print(f"\n    {label}:")
        print(f"      P(Sharpe better)  = {np.mean(d_sh > 0)*100:.1f}%  (median Δ = {np.median(d_sh):+.4f})")
        print(f"      P(CAGR better)    = {np.mean(d_cg > 0)*100:.1f}%  (median Δ = {np.median(d_cg):+.2f}%)")
        print(f"      P(MDD lower)      = {np.mean(d_md > 0)*100:.1f}%  (median Δ = {np.median(d_md):+.2f}pp)")
        print(f"      P(NAV higher)     = {np.mean(d_nv > 0)*100:.1f}%  (median Δ = {np.median(d_nv):+.0f})")

        n120_results[label] = {
            "P_sharpe": round(float(np.mean(d_sh > 0)), 4),
            "P_cagr": round(float(np.mean(d_cg > 0)), 4),
            "P_mdd": round(float(np.mean(d_md > 0)), 4),
            "P_nav": round(float(np.mean(d_nv > 0)), 4),
            "median_d_sharpe": round(float(np.median(d_sh)), 4),
            "median_d_cagr": round(float(np.median(d_cg)), 2),
            "median_d_mdd": round(float(np.median(d_md)), 2),
        }

    # ── Part D: Median Sharpe distributions ──
    print(f"\n  Median Sharpe at N=120:")
    print(f"    Simple EMA(21d):  {np.median(boot_simple['sharpe'][:, j120]):+.4f}")
    print(f"    VTREND E0:        {np.median(boot_e0['sharpe'][:, j120]):+.4f}")
    print(f"    E0 + EMA(21d):    {np.median(boot_filt['sharpe'][:, j120]):+.4f}")

    print(f"\n  Median CAGR at N=120:")
    print(f"    Simple EMA(21d):  {np.median(boot_simple['cagr'][:, j120]):+.2f}%")
    print(f"    VTREND E0:        {np.median(boot_e0['cagr'][:, j120]):+.2f}%")
    print(f"    E0 + EMA(21d):    {np.median(boot_filt['cagr'][:, j120]):+.2f}%")

    print(f"\n  Median MDD at N=120:")
    print(f"    Simple EMA(21d):  {np.median(boot_simple['mdd'][:, j120]):.1f}%")
    print(f"    VTREND E0:        {np.median(boot_e0['mdd'][:, j120]):.1f}%")
    print(f"    E0 + EMA(21d):    {np.median(boot_filt['mdd'][:, j120]):.1f}%")

    return binom_results, ts_boot, n120_results


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("EMA(21d) ABLATION STUDY")
    print("=" * 90)
    print(f"  Question: Does VTREND add value beyond simple EMA(21d) hold/cash?")
    print(f"  A) Simple: hold BTC when close > EMA({EMA_REGIME_DAYS}d), cash otherwise")
    print(f"  B) VTREND E0: EMA crossover + VDO + ATR trail (3 params)")
    print(f"  C) E0 + EMA({EMA_REGIME_DAYS}d): VTREND with regime entry filter")
    print(f"  Cost: 50 bps RT. Bootstrap: {N_BOOT} paths × 16 timescales.")

    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  Data: {n} H4 bars, warmup index = {wi}")

    # Phase 1: Real data
    p1_n120, p1_ts = phase1_real_data(cl, hi, lo, vo, tb, wi)

    # Phase 2: Bootstrap
    p2_binom, p2_ts, p2_n120 = phase2_bootstrap(cl, hi, lo, vo, tb, wi)

    # ── Overall Verdict ──
    print(f"\n{'='*90}")
    print("OVERALL VERDICT")
    print(f"{'='*90}")

    print(f"\n  Real data at N=120:")
    for label in ["simple_ema", "vtrend_e0", "e0_plus_ema"]:
        r = p1_n120[label]
        print(f"    {label:>15s}: Sh={r['sharpe']:+.3f}  CAGR={r['cagr']:+.1f}%  "
              f"MDD={r['mdd']:.1f}%  Trades={r['trades']}")

    print(f"\n  Bootstrap binomial (16 timescales):")
    for comp in ["E0 vs Simple", "E0+EMA vs Simple", "E0+EMA vs E0"]:
        d = p2_binom[comp]
        line = f"    {comp:>22s}:"
        for m in ["sharpe", "cagr", "mdd", "nav"]:
            line += f"  {m}={d[m]['wins']}/16({d[m]['verdict']})"
        print(line)

    print(f"\n  Bootstrap at N=120 (P values):")
    for comp in ["E0 vs Simple", "E0+EMA vs Simple", "E0+EMA vs E0"]:
        d = p2_n120[comp]
        print(f"    {comp:>22s}: Sh={d['P_sharpe']*100:.1f}%  CAGR={d['P_cagr']*100:.1f}%  "
              f"MDD={d['P_mdd']*100:.1f}%  NAV={d['P_nav']*100:.1f}%")

    # Key conclusion
    e0_vs_simple_sh = p2_binom["E0 vs Simple"]["sharpe"]
    filt_vs_simple_sh = p2_binom["E0+EMA vs Simple"]["sharpe"]

    print(f"\n  CONCLUSION:")
    if e0_vs_simple_sh["verdict"].startswith("PROVEN") or e0_vs_simple_sh["verdict"] == "STRONG":
        print(f"    VTREND E0 ADDS genuine value beyond simple EMA timing")
        print(f"    (E0 beats Simple EMA at {e0_vs_simple_sh['wins']}/16 timescales, p={e0_vs_simple_sh['p_binom']:.6f})")
    elif e0_vs_simple_sh["wins"] <= 8:
        print(f"    VTREND E0 does NOT add value — Simple EMA is equivalent or better")
        print(f"    (E0 beats Simple EMA at only {e0_vs_simple_sh['wins']}/16 timescales)")
    else:
        print(f"    Inconclusive — E0 vs Simple EMA: {e0_vs_simple_sh['wins']}/16, p={e0_vs_simple_sh['p_binom']:.6f}")

    el = time.time() - t_start
    print(f"\n  Total time: {el:.0f}s ({el/60:.1f} min)")

    # ── Save ──
    OUTDIR.mkdir(parents=True, exist_ok=True)
    output = {
        "config": {
            "ema_regime_h4": EMA_REGIME_P,
            "ema_regime_days": EMA_REGIME_DAYS,
            "cost_bps_rt": 50, "warmup_days": WARMUP,
            "n_boot": N_BOOT, "seed": SEED,
        },
        "phase1_real_n120": {
            k: {kk: vv for kk, vv in v.items()}
            for k, v in p1_n120.items()
        },
        "phase1_timescale_sweep": {
            str(sp): v for sp, v in p1_ts.items()
        },
        "phase2_binomial": {
            comp: {m: v for m, v in metrics.items()}
            for comp, metrics in p2_binom.items()
        },
        "phase2_n120_paired": p2_n120,
        "phase2_timescale_boot": {
            str(sp): v for sp, v in p2_ts.items()
        },
    }

    outfile = OUTDIR / "ema_ablation.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print(f"{'='*90}")
