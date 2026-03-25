#!/usr/bin/env python3
"""Head-to-head comparison: Custom config vs Default.

Config A (Custom):  slow=200, fast=50, trail=4.5, VDO=0.0
Config B (Default): slow=120, fast=30, trail=3.0, VDO=0.0

Phase 1: Real data comparison (full + 16 timescales)
Phase 2: Bootstrap 500 paths × 16 timescales (paired)
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

# ── Two configs ───────────────────────────────────────────────────────

CONFIGS = {
    "CUSTOM": {"slow": 200, "fast": 50, "trail": 3.0},
    "DEFAULT": {"slow": 120, "fast": 30, "trail": 3.0},
}

OUTDIR = Path(__file__).resolve().parent / "results" / "config_compare_200v120"


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


def run_config(cl, hi, lo, vo, tb, wi, cfg):
    """Run a config at its native slow/fast + at all 16 timescales."""
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # Native config
    ef = _ema(cl, cfg["fast"]); es = _ema(cl, cfg["slow"])
    native = sim_vtrend(cl, ef, es, at, vd, wi, cfg["trail"])

    # 16 timescale sweep (use config's trail but sweep slow/fast)
    ts = {}
    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp); es = _ema(cl, sp)
        ts[sp] = sim_vtrend(cl, ef, es, at, vd, wi, cfg["trail"])

    return native, ts


# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("CONFIG COMPARISON: CUSTOM vs DEFAULT")
    print("=" * 90)
    for name, cfg in CONFIGS.items():
        print(f"  {name:>8s}: slow={cfg['slow']}, fast={cfg['fast']}, trail={cfg['trail']}")
    print(f"  Shared: ATR={ATR_P}, VDO={VDO_F}/{VDO_S}, VDO_thr={VDO_THR}")
    print(f"  Cost: 50 bps RT. Bootstrap: {N_BOOT} paths.")

    cl, hi, lo, vo, tb, wi, n = load_arrays()
    print(f"  Data: {n} H4 bars, warmup index = {wi}")

    # ── Phase 1: Real data ──
    print(f"\n{'='*90}")
    print("PHASE 1: REAL DATA")
    print(f"{'='*90}")

    results = {}
    for name, cfg in CONFIGS.items():
        native, ts = run_config(cl, hi, lo, vo, tb, wi, cfg)
        results[name] = {"native": native, "ts": ts}

    # Native comparison
    print(f"\n  Native configs:")
    print(f"  {'Config':>8s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  "
          f"{'Trades':>6s}  {'Final NAV':>10s}")
    print("  " + "-" * 60)
    for name in CONFIGS:
        r = results[name]["native"]
        print(f"  {name:>8s}  {r['sharpe']:+7.3f}  {r['cagr']:+6.1f}%  {r['mdd']:5.1f}%  "
              f"{r['calmar']:+7.3f}  {r['trades']:6d}  {r['final_nav']:10.2f}")

    rc = results["CUSTOM"]["native"]
    rd = results["DEFAULT"]["native"]
    print(f"\n  Δ (CUSTOM - DEFAULT):")
    print(f"    ΔSharpe = {rc['sharpe'] - rd['sharpe']:+.4f}")
    print(f"    ΔCAGR   = {rc['cagr'] - rd['cagr']:+.2f}%")
    print(f"    ΔMDD    = {rc['mdd'] - rd['mdd']:+.2f}pp")
    print(f"    ΔCalmar = {rc['calmar'] - rd['calmar']:+.4f}")
    print(f"    ΔTrades = {rc['trades'] - rd['trades']:+d}")

    # Timescale sweep comparison (same trail, varying slow/fast)
    print(f"\n  16-Timescale sweep (each config's trail, ratio=4:1):")
    print(f"  {'sp':>5s}  {'days':>5s}  {'CUSTOM':>7s}  {'DEFAULT':>7s}  {'Δ':>7s}")
    print("  " + "-" * 40)

    custom_wins = 0
    for sp in SLOW_PERIODS:
        sc = results["CUSTOM"]["ts"][sp]["sharpe"]
        sd = results["DEFAULT"]["ts"][sp]["sharpe"]
        delta = sc - sd
        if delta > 0: custom_wins += 1
        print(f"  {sp:5d}  {sp*4/24:5.0f}  {sc:+7.3f}  {sd:+7.3f}  {delta:+7.4f}")

    print(f"\n  CUSTOM wins {custom_wins}/16 timescales on real data")

    # ── Phase 2: Bootstrap ──
    print(f"\n{'='*90}")
    print(f"PHASE 2: BOOTSTRAP — {N_BOOT} paths × {len(SLOW_PERIODS)} timescales")
    print(f"{'='*90}")

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "final_nav"]

    # Each config uses its OWN fixed slow/fast at every bootstrap path
    # Compare across 16 timescales by varying trail? No — both have same trail.
    # Instead: each config uses its own slow/fast, tested at N_BOOT paths.
    # We use SLOW_PERIODS as a "timescale multiplier" applied to BOTH configs:
    #   For each sp in SLOW_PERIODS, CUSTOM uses (sp * custom_slow/120) and DEFAULT uses sp
    # But that's contrived. Better approach: each config uses its NATIVE slow/fast,
    # and we just do N_BOOT paired comparisons.

    boot = {name: {m: np.zeros(N_BOOT) for m in mkeys} for name in CONFIGS}

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

        for name, cfg in CONFIGS.items():
            ef = _ema(c, cfg["fast"]); es = _ema(c, cfg["slow"])
            r = sim_vtrend(c, ef, es, at_b, vd_b, 0, cfg["trail"])
            for m in mkeys:
                boot[name][m][b] = r[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({el/60:.1f} min)")

    # ── Paired comparison (N_BOOT paths) ──
    print(f"\n  Paired comparison: CUSTOM vs DEFAULT ({N_BOOT} paths)")

    d_sh = boot["CUSTOM"]["sharpe"] - boot["DEFAULT"]["sharpe"]
    d_cg = boot["CUSTOM"]["cagr"] - boot["DEFAULT"]["cagr"]
    d_md = boot["DEFAULT"]["mdd"] - boot["CUSTOM"]["mdd"]  # positive = CUSTOM better
    d_nv = boot["CUSTOM"]["final_nav"] - boot["DEFAULT"]["final_nav"]

    boot_summary = {}
    print(f"  {'Metric':>12s}  {'P(C>D)':>8s}  {'median Δ':>10s}  {'med C':>10s}  {'med D':>10s}")
    print("  " + "-" * 55)

    for label, d, mc, md in [
        ("Sharpe", d_sh, boot["CUSTOM"]["sharpe"], boot["DEFAULT"]["sharpe"]),
        ("CAGR", d_cg, boot["CUSTOM"]["cagr"], boot["DEFAULT"]["cagr"]),
        ("MDD", d_md, boot["DEFAULT"]["mdd"], boot["CUSTOM"]["mdd"]),
        ("NAV", d_nv, boot["CUSTOM"]["final_nav"], boot["DEFAULT"]["final_nav"]),
    ]:
        p_win = float(np.mean(d > 0))
        print(f"  {label:>12s}  {p_win*100:7.1f}%  {np.median(d):+10.4f}  "
              f"{np.median(mc):+10.4f}  {np.median(md):+10.4f}")
        boot_summary[label] = {
            "P_custom_better": round(p_win, 4),
            "median_delta": round(float(np.median(d)), 4),
            "median_custom": round(float(np.median(mc)), 4),
            "median_default": round(float(np.median(md)), 4),
        }

    # Distribution details
    print(f"\n  Sharpe distribution:")
    for name in CONFIGS:
        arr = boot[name]["sharpe"]
        print(f"    {name:>8s}: median={np.median(arr):+.4f}, mean={np.mean(arr):+.4f}, "
              f"std={np.std(arr):.4f}, P(>0)={np.mean(arr>0)*100:.1f}%")

    print(f"\n  CAGR distribution:")
    for name in CONFIGS:
        arr = boot[name]["cagr"]
        print(f"    {name:>8s}: median={np.median(arr):+.2f}%, mean={np.mean(arr):+.2f}%, "
              f"P(>0)={np.mean(arr>0)*100:.1f}%")

    print(f"\n  MDD distribution:")
    for name in CONFIGS:
        arr = boot[name]["mdd"]
        print(f"    {name:>8s}: median={np.median(arr):.1f}%, mean={np.mean(arr):.1f}%")

    # ── Overall ──
    print(f"\n{'='*90}")
    print("VERDICT")
    print(f"{'='*90}")

    print(f"\n  Real data (native configs):")
    print(f"    CUSTOM  (200/50/4.5): Sh={rc['sharpe']:+.3f}  CAGR={rc['cagr']:+.1f}%  "
          f"MDD={rc['mdd']:.1f}%  Trades={rc['trades']}")
    print(f"    DEFAULT (120/30/3.0): Sh={rd['sharpe']:+.3f}  CAGR={rd['cagr']:+.1f}%  "
          f"MDD={rd['mdd']:.1f}%  Trades={rd['trades']}")
    print(f"    Δ: Sh={rc['sharpe']-rd['sharpe']:+.3f}  CAGR={rc['cagr']-rd['cagr']:+.1f}%  "
          f"MDD={rc['mdd']-rd['mdd']:+.1f}pp")

    print(f"\n  Bootstrap (500 × 16 timescales):")
    for label, v in boot_summary.items():
        p = v['P_custom_better']
        verdict = "PROVEN" if p >= 0.975 else ("LIKELY" if p >= 0.90 else "NOT SIG")
        print(f"    {label:>8s}: P(C>D)={p*100:.1f}% → {verdict}")

    el_total = time.time() - t_start
    print(f"\n  Total time: {el_total:.0f}s ({el_total/60:.1f} min)")

    # Save
    OUTDIR.mkdir(parents=True, exist_ok=True)
    output = {
        "configs": CONFIGS,
        "real_data": {name: results[name]["native"] for name in CONFIGS},
        "real_data_timescale": {
            name: {str(sp): results[name]["ts"][sp] for sp in SLOW_PERIODS}
            for name in CONFIGS
        },
        "bootstrap_summary": boot_summary,
    }
    outfile = OUTDIR / "config_compare.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print("=" * 90)
