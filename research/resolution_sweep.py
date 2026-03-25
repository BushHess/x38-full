#!/usr/bin/env python3
"""Multi-Resolution Timescale Sweep: H1, H4 (cached), D1.

Same methodology as timescale_robustness.py but applied to H1 and D1 candles.
Parameters scaled to maintain same physical time duration per resolution.
H4 results loaded from cache for cross-resolution comparison.

Question: Does the alpha region depend on H4 resolution, or does it exist
across H1 and D1 too? Which resolution gives widest alpha region, highest
Sharpe, best Calmar?
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ───────────────────────────────────────────────────────

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
COST = SCENARIOS["harsh"]
CPS  = COST.per_side_bps / 10_000.0   # 0.0025

START  = "2019-01-01"
END    = "2026-02-20"
WARMUP = 365
CASH   = 10_000.0

N_BOOT = 2000
SEED   = 42

VDO_ON  = 0.0
VDO_OFF = -1e9

# ── Resolution configs ──────────────────────────────────────────────

# Day grid shared across all resolutions (16 points, 5–120 days)
DAY_GRID = [5, 8, 10, 12, 14, 16, 18, 20, 24, 28, 33, 40, 50, 60, 83, 120]

RESOLUTIONS = {
    "H1": {
        "interval": "1h",
        "bars_per_day": 24,
        "ann": math.sqrt(24 * 365.25),    # √8766 ≈ 93.6
        "atr_p": 56,                       # 56 H1 bars ≈ 2.3 days (matches H4 ATR(14))
        "vdo_f": 48,                       # 48 H1 bars ≈ 2 days
        "vdo_s": 112,                      # 112 H1 bars ≈ 4.7 days
        "blksz": 240,                      # ~10 days
        "trail": 3.0,
        "min_fast": 5,
    },
    "H4": {
        "interval": "4h",
        "bars_per_day": 6,
        "ann": math.sqrt(6 * 365.25),     # √2191.5 ≈ 46.8
        "atr_p": 14,
        "vdo_f": 12,
        "vdo_s": 28,
        "blksz": 60,
        "trail": 3.0,
        "min_fast": 5,
    },
    "D1": {
        "interval": "1d",
        "bars_per_day": 1,
        "ann": math.sqrt(365.25),          # ≈ 19.1
        "atr_p": 14,                       # 14 days (standard daily ATR)
        "vdo_f": 12,                       # 12 days
        "vdo_s": 28,                       # 28 days
        "blksz": 10,                       # ~10 days
        "trail": 3.0,
        "min_fast": 3,
    },
}


def slow_periods_for(res_name):
    """Convert day grid to bar counts for given resolution."""
    bpd = RESOLUTIONS[res_name]["bars_per_day"]
    return [d * bpd for d in DAY_GRID]


# ═══════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════

def _date_to_ms(date_str):
    from datetime import datetime, timezone
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _load_from_csv(interval):
    """Load bars of given interval from CSV, with date filtering."""
    df = pd.read_csv(DATA)
    df = df[df["interval"] == interval].sort_values("open_time").reset_index(drop=True)

    start_ms = _date_to_ms(START)
    load_start_ms = start_ms - WARMUP * 86_400_000
    end_ms = _date_to_ms(END) + 86_400_000 - 1

    df = df[(df["open_time"] >= load_start_ms) & (df["open_time"] <= end_ms)]

    n = len(df)
    cl = df["close"].values.astype(np.float64)
    hi = df["high"].values.astype(np.float64)
    lo = df["low"].values.astype(np.float64)
    vo = df["volume"].values.astype(np.float64)
    tb = df["taker_buy_base_vol"].values.astype(np.float64)
    ct = df["close_time"].values.astype(np.int64)

    # Warmup index
    wi = 0
    for i in range(n):
        if ct[i] >= start_ms:
            wi = i
            break

    return cl, hi, lo, vo, tb, wi, n


def load_resolution(res_name):
    """Load data arrays for given resolution."""
    if res_name == "H4":
        # Use DataFeed for consistency with existing code
        feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
        bars = feed.h4_bars
        n = len(bars)
        cl = np.array([b.close for b in bars], dtype=np.float64)
        hi = np.array([b.high for b in bars], dtype=np.float64)
        lo = np.array([b.low for b in bars], dtype=np.float64)
        vo = np.array([b.volume for b in bars], dtype=np.float64)
        tb = np.array([b.taker_buy_base_vol for b in bars], dtype=np.float64)
        wi = 0
        if feed.report_start_ms is not None:
            for i, b in enumerate(bars):
                if b.close_time >= feed.report_start_ms:
                    wi = i
                    break
        return cl, hi, lo, vo, tb, wi, n
    else:
        interval = RESOLUTIONS[res_name]["interval"]
        return _load_from_csv(interval)


# ═══════════════════════════════════════════════════════════════════
# Bootstrap infrastructure
# ═══════════════════════════════════════════════════════════════════

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
# Fast VTREND simulation (parameterized)
# ═══════════════════════════════════════════════════════════════════

def sim_fast(cl, ef, es, at, vd, wi, vdo_thr, trail, ann):
    """VTREND binary sim (f=1.0). Returns metrics dict.

    Parameterized on trail and ann for multi-resolution support.
    """
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
            if p < pk - trail * a_val:
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
    bars_per_year = ann * ann   # ann = sqrt(bars_per_year)
    yrs = n_rets / bars_per_year
    cagr = ((1 + tr) ** (1 / yrs) - 1) * 100 if yrs > 0 and tr > -1 else -100.0

    mdd = (1.0 - nav_min_ratio) * 100.0

    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std) * ann if std > 1e-12 else 0.0

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    return {"cagr": cagr, "mdd": mdd, "sharpe": sharpe, "calmar": calmar, "trades": nt}


# ═══════════════════════════════════════════════════════════════════
# Sweep for one resolution
# ═══════════════════════════════════════════════════════════════════

def run_resolution(res_name):
    """Complete timescale sweep for one resolution."""
    cfg = RESOLUTIONS[res_name]
    slow_periods = slow_periods_for(res_name)
    n_sp = len(slow_periods)

    print(f"\n{'=' * 70}")
    print(f"RESOLUTION: {res_name} ({cfg['interval']})")
    print(f"{'=' * 70}")
    print(f"  Bars/day: {cfg['bars_per_day']}  ANN: {cfg['ann']:.1f}")
    print(f"  ATR: {cfg['atr_p']}  VDO: {cfg['vdo_f']}/{cfg['vdo_s']}  "
          f"BLKSZ: {cfg['blksz']}  Trail: {cfg['trail']}")
    print(f"  Timescale grid (bars): {slow_periods}")
    print(f"  Timescale grid (days): {DAY_GRID}")

    # Load data
    print(f"\n  Loading {res_name} data...")
    cl, hi, lo, vo, tb, wi, n = load_resolution(res_name)
    print(f"  {n} bars, warmup idx={wi}, trading={n - wi} bars")

    # ── Real data sweep ──────────────────────────────────────────
    print(f"\n  REAL DATA SWEEP:")
    print(f"  {'slow':>6s} {'days':>5s}  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Cm':>6s} {'Tr':>4s}  │  "
          f"{'CAGR':>7s} {'MDD':>6s} {'Sh':>6s} {'Cm':>6s} {'Tr':>4s}")
    print(f"  {'':>6s} {'':>5s}  {'--- WITH VDO ---':^30s}  │  {'--- NO VDO ---':^30s}")
    print("  " + "-" * 78)

    at = _atr(hi, lo, cl, cfg["atr_p"])
    vd = _vdo(cl, hi, lo, vo, tb, cfg["vdo_f"], cfg["vdo_s"])

    real_results = {}
    for j, sp in enumerate(slow_periods):
        fp = max(cfg["min_fast"], sp // 4)
        days = DAY_GRID[j]
        ef = _ema(cl, fp)
        es = _ema(cl, sp)

        r_on  = sim_fast(cl, ef, es, at, vd, wi, VDO_ON, cfg["trail"], cfg["ann"])
        r_off = sim_fast(cl, ef, es, at, vd, wi, VDO_OFF, cfg["trail"], cfg["ann"])

        real_results[sp] = {"with_vdo": r_on, "no_vdo": r_off}

        print(f"  {sp:6d} {days:5d}  "
              f"{r_on['cagr']:+6.1f}% {r_on['mdd']:5.1f}% {r_on['sharpe']:5.3f} "
              f"{r_on['calmar']:5.3f} {r_on['trades']:4d}  │  "
              f"{r_off['cagr']:+6.1f}% {r_off['mdd']:5.1f}% {r_off['sharpe']:5.3f} "
              f"{r_off['calmar']:5.3f} {r_off['trades']:4d}")

    # ── Bootstrap ────────────────────────────────────────────────
    print(f"\n  BOOTSTRAP: {N_BOOT} paths × {n_sp} timescales × 2 VDO variants")

    cr, hr, lr, vol, tbr = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cl) - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    mkeys = ["cagr", "mdd", "sharpe", "calmar", "trades"]
    boot_on  = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_off = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbr, n_trans, cfg["blksz"], p0, rng)

        at_b = _atr(h, l, c, cfg["atr_p"])
        vd_b = _vdo(c, h, l, v, t, cfg["vdo_f"], cfg["vdo_s"])

        for j, sp in enumerate(slow_periods):
            fp = max(cfg["min_fast"], sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            r_on  = sim_fast(c, ef, es, at_b, vd_b, wi, VDO_ON, cfg["trail"], cfg["ann"])
            r_off = sim_fast(c, ef, es, at_b, vd_b, wi, VDO_OFF, cfg["trail"], cfg["ann"])

            for m in mkeys:
                boot_on[m][b, j]  = r_on[m]
                boot_off[m][b, j] = r_off[m]

    el = time.time() - t0
    n_total = N_BOOT * n_sp * 2
    print(f"\n  Done: {el:.1f}s ({n_total:,} sims, {n_total / el:.0f} sims/sec)")

    return real_results, boot_on, boot_off, slow_periods


# ═══════════════════════════════════════════════════════════════════
# Analysis
# ═══════════════════════════════════════════════════════════════════

def analyze_resolution(res_name, real_results, boot_on, boot_off, slow_periods):
    """Analyze one resolution. Returns summary dict."""
    n_sp = len(slow_periods)

    print(f"\n{'=' * 70}")
    print(f"ANALYSIS: {res_name} TIMESCALE ROBUSTNESS (with VDO)")
    print(f"{'=' * 70}")

    print(f"\n  {'slow':>6s} {'days':>5s}  "
          f"{'medSh':>6s} {'p5Sh':>6s} {'p95Sh':>6s}  "
          f"{'medCAGR':>8s} {'medMDD':>7s} {'medCm':>7s}  "
          f"{'P(C>0)':>7s} {'P(S>0)':>7s}")
    print("  " + "-" * 80)

    prod_min = prod_max = strong_min = strong_max = None
    peak_sharpe = -999
    peak_sharpe_day = 0
    peak_calmar = -999
    peak_calmar_day = 0

    summary_rows = []

    for j, sp in enumerate(slow_periods):
        days = DAY_GRID[j]
        sh = boot_on["sharpe"][:, j]
        cg = boot_on["cagr"][:, j]
        md = boot_on["mdd"][:, j]
        cm = boot_on["calmar"][:, j]

        p5, med, p95 = np.percentile(sh, [5, 50, 95])
        med_cg = float(np.median(cg))
        med_md = float(np.median(md))
        med_cm = float(np.median(cm))
        p_cagr = float(np.mean(cg > 0)) * 100
        p_sh   = float(np.mean(sh > 0)) * 100

        marker = ""
        if med > 0:
            if prod_min is None: prod_min = days
            prod_max = days
            marker = " *"
        if p_cagr > 70:
            if strong_min is None: strong_min = days
            strong_max = days
            marker = " **"

        if med > peak_sharpe:
            peak_sharpe = med
            peak_sharpe_day = days
        if med_cm > peak_calmar:
            peak_calmar = med_cm
            peak_calmar_day = days

        summary_rows.append({
            "slow": sp, "days": days,
            "med_sh": float(med), "p5_sh": float(p5), "p95_sh": float(p95),
            "med_cagr": med_cg, "med_mdd": med_md, "med_calmar": med_cm,
            "p_cagr_pos": p_cagr, "p_sh_pos": p_sh,
        })

        print(f"  {sp:6d} {days:5d}  "
              f"{med:+6.3f} {p5:+6.3f} {p95:+6.3f}  "
              f"{med_cg:+7.1f}% {med_md:6.1f}% {med_cm:+6.3f}  "
              f"{p_cagr:6.1f}% {p_sh:6.1f}%{marker}")

    print("\n  Legend: * = productive (median Sharpe > 0), ** = strong (P(CAGR>0) > 70%)")

    # Width
    prod_width = prod_max / prod_min if prod_min and prod_max else 0
    strong_width = strong_max / strong_min if strong_min and strong_max else 0

    print(f"\n  ROBUSTNESS:")
    if prod_min:
        print(f"    Productive: {prod_min}–{prod_max} days (width {prod_width:.1f}x)")
    else:
        print(f"    No productive timescale!")
    if strong_min:
        print(f"    Strong:     {strong_min}–{strong_max} days (width {strong_width:.1f}x)")
    print(f"    Peak Sharpe: {peak_sharpe:.4f} at {peak_sharpe_day} days")
    print(f"    Peak Calmar: {peak_calmar:.4f} at {peak_calmar_day} days")

    # VDO contribution
    print(f"\n  VDO CONTRIBUTION:")
    print(f"  {'slow':>6s} {'days':>5s}  {'meanΔSh':>8s} {'P(VDO+)':>8s}  {'meanΔMDD':>9s}")
    print("  " + "-" * 45)

    vdo_helps = 0
    for j, sp in enumerate(slow_periods):
        days = DAY_GRID[j]
        d_sh = boot_on["sharpe"][:, j] - boot_off["sharpe"][:, j]
        d_md = boot_off["mdd"][:, j] - boot_on["mdd"][:, j]
        p_helps = np.mean(d_sh > 0)
        if p_helps > 0.5:
            vdo_helps += 1
        marker = " +" if p_helps > 0.55 else (" -" if p_helps < 0.45 else "")
        print(f"  {sp:6d} {days:5d}  {d_sh.mean():+8.4f} {p_helps*100:7.1f}%  "
              f"{d_md.mean():+8.2f}%{marker}")

    print(f"\n  VDO helps at {vdo_helps}/{n_sp} timescales")

    # Real data percentile
    print(f"\n  REAL DATA PERCENTILE:")
    print(f"  {'slow':>6s} {'days':>5s}  {'realSh':>7s} {'pctile':>7s}")
    print("  " + "-" * 35)

    for j, sp in enumerate(slow_periods):
        days = DAY_GRID[j]
        r_sh = real_results[sp]["with_vdo"]["sharpe"]
        pct = float(np.mean(boot_on["sharpe"][:, j] <= r_sh)) * 100
        flag = " !" if pct > 97.5 else (" ?" if pct > 95 else "")
        print(f"  {sp:6d} {days:5d}  {r_sh:+7.3f} {pct:6.1f}%{flag}")

    # Smoothness
    meds = [float(np.median(boot_on["sharpe"][:, j])) for j in range(n_sp)]
    adj_corr = float(np.corrcoef(meds[:-1], meds[1:])[0, 1]) if n_sp > 2 else 0
    print(f"\n  Smoothness: r = {adj_corr:.3f}")

    return {
        "prod_min_days": prod_min, "prod_max_days": prod_max,
        "prod_width": round(prod_width, 1),
        "strong_min_days": strong_min, "strong_max_days": strong_max,
        "strong_width": round(strong_width, 1),
        "peak_sharpe": round(peak_sharpe, 4),
        "peak_sharpe_day": peak_sharpe_day,
        "peak_calmar": round(peak_calmar, 4),
        "peak_calmar_day": peak_calmar_day,
        "vdo_helps": vdo_helps,
        "smoothness": round(adj_corr, 3),
        "rows": summary_rows,
    }


# ═══════════════════════════════════════════════════════════════════
# Cross-resolution comparison
# ═══════════════════════════════════════════════════════════════════

def load_h4_cache():
    """Load H4 results from timescale_robustness.json."""
    cache_path = Path(__file__).resolve().parent / "results" / "timescale_robustness.json"
    with open(cache_path) as f:
        data = json.load(f)

    # Build summary matching our format
    h4_slow_periods = data["config"]["slow_periods"]
    h4_bpd = 6

    rows = []
    for sp in h4_slow_periods:
        key = str(sp)
        days = round(sp * 4 / 24)  # convert to approximate days
        bv = data["bootstrap_with_vdo"][key]
        rows.append({
            "slow": sp, "days": days,
            "med_sh": bv["sharpe"]["median"],
            "med_cagr": bv["cagr"]["median"],
            "med_mdd": bv["mdd"]["median"],
            "med_calmar": bv["calmar"]["median"],
            "p_cagr_pos": bv["cagr"]["p_positive"] * 100,
        })

    return {
        "prod_min_days": data["robustness"]["strong_min"] * 4 // 24 if data["robustness"]["productive_min"] else None,
        "prod_max_days": data["robustness"]["productive_max"] * 4 // 24 if data["robustness"]["productive_max"] else None,
        "prod_width": data["robustness"]["productive_width_ratio"],
        "strong_min_days": data["robustness"]["strong_min"] * 4 // 24 if data["robustness"]["strong_min"] else None,
        "strong_max_days": data["robustness"]["strong_max"] * 4 // 24 if data["robustness"]["strong_max"] else None,
        "strong_width": data["robustness"]["strong_width_ratio"],
        "peak_sharpe": max(r["med_sh"] for r in rows),
        "peak_sharpe_day": max(rows, key=lambda r: r["med_sh"])["days"],
        "peak_calmar": max(r["med_calmar"] for r in rows),
        "peak_calmar_day": max(rows, key=lambda r: r["med_calmar"])["days"],
        "smoothness": None,  # not stored in cache
        "rows": rows,
    }


def cross_resolution_compare(summaries):
    """Compare H1, H4, D1 results at matching day-points."""
    print("\n" + "=" * 70)
    print("CROSS-RESOLUTION COMPARISON")
    print("=" * 70)

    # Summary table
    print(f"\n  {'':>4s}  {'Productive':>20s}  {'Strong':>20s}  "
          f"{'Peak Sh':>8s} {'@day':>5s}  {'Peak Cm':>8s} {'@day':>5s}  {'Smooth':>6s}")
    print("  " + "-" * 95)

    for rn in ["H1", "H4", "D1"]:
        s = summaries[rn]
        prod = f"{s['prod_min_days']}–{s['prod_max_days']}d ({s['prod_width']}x)" if s["prod_min_days"] else "none"
        strg = f"{s['strong_min_days']}–{s['strong_max_days']}d ({s['strong_width']}x)" if s.get("strong_min_days") else "none"
        sm = f"{s['smoothness']:.3f}" if s.get("smoothness") is not None else "n/a"
        print(f"  {rn:>4s}  {prod:>20s}  {strg:>20s}  "
              f"{s['peak_sharpe']:+8.4f} {s['peak_sharpe_day']:5d}  "
              f"{s['peak_calmar']:+8.4f} {s['peak_calmar_day']:5d}  {sm:>6s}")

    # Day-by-day comparison
    print(f"\n  Median Sharpe at matching day-points:")
    print(f"  {'days':>5s}  {'H1':>8s}  {'H4':>8s}  {'D1':>8s}  {'best':>6s}")
    print("  " + "-" * 40)

    for d in DAY_GRID:
        vals = {}
        for rn in ["H1", "H4", "D1"]:
            row = next((r for r in summaries[rn]["rows"] if r["days"] == d), None)
            vals[rn] = row["med_sh"] if row else None

        parts = []
        best = ""
        best_val = -999
        for rn in ["H1", "H4", "D1"]:
            v = vals[rn]
            if v is not None:
                parts.append(f"{v:+8.4f}")
                if v > best_val:
                    best_val = v
                    best = rn
            else:
                parts.append(f"{'n/a':>8s}")

        print(f"  {d:5d}  {'  '.join(parts)}  {best:>6s}")

    # Calmar comparison
    print(f"\n  Median Calmar at matching day-points:")
    print(f"  {'days':>5s}  {'H1':>8s}  {'H4':>8s}  {'D1':>8s}  {'best':>6s}")
    print("  " + "-" * 40)

    for d in DAY_GRID:
        vals = {}
        for rn in ["H1", "H4", "D1"]:
            row = next((r for r in summaries[rn]["rows"] if r["days"] == d), None)
            vals[rn] = row.get("med_calmar") if row else None

        parts = []
        best = ""
        best_val = -999
        for rn in ["H1", "H4", "D1"]:
            v = vals[rn]
            if v is not None:
                parts.append(f"{v:+8.4f}")
                if v > best_val:
                    best_val = v
                    best = rn
            else:
                parts.append(f"{'n/a':>8s}")

        print(f"  {d:5d}  {'  '.join(parts)}  {best:>6s}")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("MULTI-RESOLUTION TIMESCALE SWEEP: H1 / H4 / D1")
    print("=" * 70)
    print(f"  Period: {START} → {END}   Warmup: {WARMUP}d")
    print(f"  Cost: harsh ({COST.round_trip_bps:.0f} bps RT)")
    print(f"  Bootstrap: {N_BOOT} paths, seed={SEED}")
    print(f"  Day grid: {DAY_GRID}")
    print(f"\n  NOTE: H4 loaded from cache (timescale_robustness.json)")
    print(f"        Cross-resolution pairing not possible (different bar structures)")

    summaries = {}

    # ── D1 (fast, ~5 min) ───────────────────────────────────────
    real_d1, boot_d1_on, boot_d1_off, sp_d1 = run_resolution("D1")
    summaries["D1"] = analyze_resolution("D1", real_d1, boot_d1_on, boot_d1_off, sp_d1)

    # ── H1 (slow, ~110 min) ─────────────────────────────────────
    real_h1, boot_h1_on, boot_h1_off, sp_h1 = run_resolution("H1")
    summaries["H1"] = analyze_resolution("H1", real_h1, boot_h1_on, boot_h1_off, sp_h1)

    # ── H4 (from cache) ─────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("H4: LOADED FROM CACHE")
    print(f"{'=' * 70}")
    summaries["H4"] = load_h4_cache()
    print("  Results from timescale_robustness.json loaded successfully")
    h4s = summaries["H4"]
    print(f"  Productive: {h4s['prod_min_days']}–{h4s['prod_max_days']} days "
          f"(width {h4s['prod_width']}x)")
    if h4s.get("strong_min_days"):
        print(f"  Strong:     {h4s['strong_min_days']}–{h4s['strong_max_days']} days "
              f"(width {h4s['strong_width']}x)")
    print(f"  Peak Sharpe: {h4s['peak_sharpe']:.4f} at {h4s['peak_sharpe_day']} days")

    # ── Cross-resolution comparison ──────────────────────────────
    cross_resolution_compare(summaries)

    # ── Final determination ──────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("DETERMINATION")
    print(f"{'=' * 70}")

    for rn in ["H1", "H4", "D1"]:
        s = summaries[rn]
        prod = f"{s['prod_min_days']}–{s['prod_max_days']}d" if s["prod_min_days"] else "none"
        print(f"\n  {rn}: productive={prod} ({s['prod_width']}x)  "
              f"peak_Sharpe={s['peak_sharpe']:+.4f}@{s['peak_sharpe_day']}d  "
              f"peak_Calmar={s['peak_calmar']:+.4f}@{s['peak_calmar_day']}d")

    # Best resolution
    best_sh = max(summaries.items(), key=lambda x: x[1]["peak_sharpe"])
    best_cm = max(summaries.items(), key=lambda x: x[1]["peak_calmar"])
    best_wd = max(summaries.items(), key=lambda x: x[1]["prod_width"])

    print(f"\n  Widest productive region: {best_wd[0]} ({best_wd[1]['prod_width']}x)")
    print(f"  Highest peak Sharpe:      {best_sh[0]} ({best_sh[1]['peak_sharpe']:.4f})")
    print(f"  Best peak Calmar:         {best_cm[0]} ({best_cm[1]['peak_calmar']:.4f})")

    # ── Save ─────────────────────────────────────────────────────
    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    output = {
        "config": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "day_grid": DAY_GRID,
            "cost_rt_bps": COST.round_trip_bps,
            "resolutions": {rn: {k: v for k, v in cfg.items()
                                 if k != "interval"}
                            for rn, cfg in RESOLUTIONS.items()},
        },
        "summaries": {},
    }

    for rn in ["H1", "H4", "D1"]:
        s = summaries[rn]
        output["summaries"][rn] = {
            k: v for k, v in s.items() if k != "rows"
        }
        output["summaries"][rn]["per_day"] = {}
        for row in s["rows"]:
            output["summaries"][rn]["per_day"][str(row["days"])] = {
                "med_sharpe": round(row["med_sh"], 4),
                "med_cagr": round(row.get("med_cagr", 0), 4),
                "med_mdd": round(row.get("med_mdd", 0), 4),
                "med_calmar": round(row.get("med_calmar", 0), 4),
                "p_cagr_pos": round(row.get("p_cagr_pos", 0), 2),
            }

    outpath = outdir / "resolution_sweep.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved → {outpath}")
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
