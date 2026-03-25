#!/usr/bin/env python3
"""D1 EMA(200) Regime Filter Study.

Tests adding a daily EMA(200) filter to VTREND entry:
  Entry: EMA crossover + VDO > 0 + close > EMA(1200 H4 bars ≈ 200 days)

The 200-day EMA is the classic bull/bear dividing line.
Hypothesis: filtering out bear-market entries reduces whipsaw losses.

Tests:
  1. Real data: E0 vs E0+filter on 14 coins × full history
  2. Real data: E0 vs E0+filter on 14 coins × 16 timescales
  3. Bootstrap: 2000 paths × 16 timescales on BTC (if real data promising)
"""

from __future__ import annotations

import glob
import json
import math
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from strategies.vtrend.strategy import _ema, _atr, _vdo

# ── Constants ─────────────────────────────────────────────────────────

CACHE_DIR = "/var/www/trading-bots/data-pipeline/.cache_binance_vision"

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "LTCUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "AVAXUSDT",
    "LINKUSDT", "BCHUSDT", "HBARUSDT", "XLMUSDT",
]

CASH     = 10_000.0
CPS      = 0.0025
TRAIL    = 3.0
ATR_P    = 14
VDO_F    = 12
VDO_S    = 28
VDO_THR  = 0.0
ANN      = math.sqrt(6.0 * 365.25)

WARMUP_DAYS = 365

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

# D1 EMA(200) ≈ H4 EMA(1200) — same calendar-time lookback
D1_EMA_PERIOD = 1200  # 200 days × 6 bars/day

# BTC data for bootstrap
BTC_DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")

N_BOOT = 2000
BLKSZ  = 60
SEED   = 42

OUTDIR = Path(__file__).resolve().parent / "results" / "d1_ema200_filter"


# ═══════════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════════

def load_coin_raw(symbol):
    monthly = sorted(glob.glob(
        f"{CACHE_DIR}/spot/monthly/klines/{symbol}/4h/*.zip"))
    daily = sorted(glob.glob(
        f"{CACHE_DIR}/spot/daily/klines/{symbol}/4h/*.zip"))

    rows = []
    for zp in monthly + daily:
        try:
            with zipfile.ZipFile(zp) as zf:
                fname = zf.namelist()[0]
                data = zf.read(fname).decode()
                for line in data.strip().split('\n'):
                    cols = line.split(',')
                    if len(cols) < 12:
                        continue
                    ts = int(cols[0])
                    if ts > 1e15:
                        ts = ts // 1000
                    rows.append((
                        ts, float(cols[2]), float(cols[3]), float(cols[4]),
                        float(cols[5]), float(cols[9]),
                    ))
        except Exception as e:
            print(f"  Warning: {zp}: {e}")

    rows.sort(key=lambda x: x[0])
    seen = set()
    unique = []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            unique.append(r)

    n = len(unique)
    return {
        "cl": np.array([r[3] for r in unique], dtype=np.float64),
        "hi": np.array([r[1] for r in unique], dtype=np.float64),
        "lo": np.array([r[2] for r in unique], dtype=np.float64),
        "vo": np.array([r[4] for r in unique], dtype=np.float64),
        "tb": np.array([r[5] for r in unique], dtype=np.float64),
        "n": n,
        "timestamps": np.array([r[0] for r in unique], dtype=np.int64),
    }


def load_btc_arrays():
    """Load BTC from the canonical CSV for bootstrap comparison."""
    from v10.core.data import DataFeed
    feed = DataFeed(BTC_DATA, start="2019-01-01", end="2026-02-20", warmup_days=WARMUP_DAYS)
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
# Metrics helper
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
    return {
        "sharpe": sharpe,
        "cagr": cagr,
        "mdd": mdd,
        "calmar": calmar,
        "trades": nt,
        "final_nav": navs_end,
    }


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E0 (standard)
# ═══════════════════════════════════════════════════════════════════════

def sim_e0(cl, ef, es, at, vd, wi, vdo_thr=0.0):
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
            if ef[i] > es[i] and vd[i] > vdo_thr: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Simulation: E0 + D1 EMA(200) filter
# ═══════════════════════════════════════════════════════════════════════

def sim_e0_d1filter(cl, ef, es, at, vd, wi, ema200, vdo_thr=0.0):
    """E0 + extra entry condition: close > EMA(1200 H4 bars ≈ 200 days).

    Exit logic unchanged — filter only affects ENTRY.
    """
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
            # D1 EMA(200) filter: only enter when price above long-term trend
            if ef[i] > es[i] and vd[i] > vdo_thr and p > ema200[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Bootstrap path generation
# ═══════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Real data — 14 coins × N=120
# ═══════════════════════════════════════════════════════════════════════

def phase1_coins(sp=120):
    """E0 vs E0+D1filter on each coin at single timescale."""
    print(f"\n{'='*80}")
    print(f"PHASE 1: REAL DATA — 14 COINS × N={sp}")
    print(f"{'='*80}")

    fp = max(5, sp // 4)
    results = {}

    for symbol in COINS:
        d = load_coin_raw(symbol)
        cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
        n = d["n"]
        wi = min(WARMUP_DAYS * 6, n - 100)

        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ef = _ema(cl, fp)
        es = _ema(cl, sp)
        ema200 = _ema(cl, D1_EMA_PERIOD)

        r0 = sim_e0(cl, ef, es, at, vd, wi)
        rf = sim_e0_d1filter(cl, ef, es, at, vd, wi, ema200)

        results[symbol] = {"E0": r0, "E0+D1": rf, "n": n, "wi": wi}

    # Print table
    print(f"\n  {'Coin':>10s}  {'Bars':>6s}  "
          f"{'E0 Sh':>7s}  {'E0+D1 Sh':>9s}  {'ΔSh':>7s}  "
          f"{'E0 CAGR':>8s}  {'D1 CAGR':>8s}  {'ΔCAGR':>7s}  "
          f"{'E0 MDD':>7s}  {'D1 MDD':>7s}  {'ΔMDD':>6s}  "
          f"{'E0 Tr':>5s}  {'D1 Tr':>5s}")
    print("  " + "-" * 110)

    n_sh_better = 0
    n_cagr_better = 0
    n_mdd_better = 0

    for s in COINS:
        r = results[s]
        r0, rf = r["E0"], r["E0+D1"]
        d_sh = rf["sharpe"] - r0["sharpe"]
        d_cg = rf["cagr"] - r0["cagr"]
        d_md = rf["mdd"] - r0["mdd"]
        if d_sh > 0: n_sh_better += 1
        if d_cg > 0: n_cagr_better += 1
        if d_md < 0: n_mdd_better += 1

        print(f"  {s:>10s}  {r['n']:6d}  "
              f"{r0['sharpe']:+7.3f}  {rf['sharpe']:+9.3f}  {d_sh:+7.4f}  "
              f"{r0['cagr']:+7.1f}%  {rf['cagr']:+7.1f}%  {d_cg:+6.1f}pp  "
              f"{r0['mdd']:6.1f}%  {rf['mdd']:6.1f}%  {d_md:+5.1f}  "
              f"{r0['trades']:5d}  {rf['trades']:5d}")

    print(f"\n  Filter helps Sharpe: {n_sh_better}/{len(COINS)}")
    print(f"  Filter helps CAGR:   {n_cagr_better}/{len(COINS)}")
    print(f"  Filter helps MDD:    {n_mdd_better}/{len(COINS)}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Real data — BTC × 16 timescales
# ═══════════════════════════════════════════════════════════════════════

def phase2_timescales():
    """E0 vs E0+D1filter on BTC across 16 timescales."""
    print(f"\n{'='*80}")
    print(f"PHASE 2: BTC TIMESCALE SWEEP — E0 vs E0+D1 filter")
    print(f"{'='*80}")

    d = load_coin_raw("BTCUSDT")
    cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
    n = d["n"]
    wi = min(WARMUP_DAYS * 6, n - 100)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    ema200 = _ema(cl, D1_EMA_PERIOD)

    print(f"\n  {'sp':>5s}  {'days':>5s}  "
          f"{'E0 Sh':>7s}  {'D1 Sh':>7s}  {'ΔSh':>8s}  "
          f"{'E0 CAGR':>8s}  {'D1 CAGR':>8s}  "
          f"{'E0 MDD':>7s}  {'D1 MDD':>7s}  {'ΔMDD':>6s}  "
          f"{'E0 Tr':>5s}  {'D1 Tr':>5s}")
    print("  " + "-" * 95)

    n_better = 0
    results = {}

    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        days = sp * 4 / 24
        ef = _ema(cl, fp)
        es = _ema(cl, sp)

        r0 = sim_e0(cl, ef, es, at, vd, wi)
        rf = sim_e0_d1filter(cl, ef, es, at, vd, wi, ema200)

        d_sh = rf["sharpe"] - r0["sharpe"]
        d_md = rf["mdd"] - r0["mdd"]
        if rf["sharpe"] > r0["sharpe"]: n_better += 1

        results[sp] = {"E0": r0, "E0+D1": rf}

        print(f"  {sp:5d}  {days:5.0f}  "
              f"{r0['sharpe']:+7.3f}  {rf['sharpe']:+7.3f}  {d_sh:+8.4f}  "
              f"{r0['cagr']:+7.1f}%  {rf['cagr']:+7.1f}%  "
              f"{r0['mdd']:6.1f}%  {rf['mdd']:6.1f}%  {d_md:+5.1f}  "
              f"{r0['trades']:5d}  {rf['trades']:5d}")

    print(f"\n  D1 filter better Sharpe: {n_better}/{len(SLOW_PERIODS)} timescales")

    return results


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Bootstrap — BTC × 16 timescales × 2000 paths
# ═══════════════════════════════════════════════════════════════════════

def phase3_bootstrap():
    """Paired bootstrap comparison: E0 vs E0+D1 on BTC."""
    print(f"\n{'='*80}")
    print(f"PHASE 3: BOOTSTRAP — {N_BOOT} paths × {len(SLOW_PERIODS)} timescales")
    print(f"{'='*80}")

    cl, hi, lo, vo, tb, wi, n = load_btc_arrays()
    print(f"  BTC: {n} bars, wi={wi}")

    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "final_nav"]

    boot_e0 = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_d1 = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 200 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)")

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng)

        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ema200 = _ema(c, D1_EMA_PERIOD)

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp)
            es = _ema(c, sp)

            r0 = sim_e0(c, ef, es, at, vd, wi)
            rf = sim_e0_d1filter(c, ef, es, at, vd, wi, ema200)

            for m in mkeys:
                boot_e0[m][b, j] = r0[m]
                boot_d1[m][b, j] = rf[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT * n_sp * 2} sims)")

    # ── Analysis ──
    print(f"\n  {'sp':>5}  {'days':>5}  "
          f"{'P(Sh+)':>7}  {'P(CAGR+)':>9}  {'P(MDD-)':>8}  {'P(NAV+)':>8}  "
          f"{'medΔSh':>8}  {'medΔCAGR':>9}")
    print("  " + "-" * 75)

    win_sh = 0; win_cagr = 0; win_mdd = 0; win_nav = 0

    per_ts = []
    for j, sp in enumerate(SLOW_PERIODS):
        days = sp * 4 / 24

        d_sh = boot_d1["sharpe"][:, j] - boot_e0["sharpe"][:, j]
        d_cg = boot_d1["cagr"][:, j] - boot_e0["cagr"][:, j]
        d_md = boot_e0["mdd"][:, j] - boot_d1["mdd"][:, j]
        d_nv = boot_d1["final_nav"][:, j] - boot_e0["final_nav"][:, j]

        p_sh = float(np.mean(d_sh > 0))
        p_cg = float(np.mean(d_cg > 0))
        p_md = float(np.mean(d_md > 0))
        p_nv = float(np.mean(d_nv > 0))

        if p_sh > 0.5: win_sh += 1
        if p_cg > 0.5: win_cagr += 1
        if p_md > 0.5: win_mdd += 1
        if p_nv > 0.5: win_nav += 1

        print(f"  {sp:5d}  {days:5.0f}  "
              f"{p_sh*100:6.1f}%  {p_cg*100:8.1f}%  {p_md*100:7.1f}%  {p_nv*100:7.1f}%  "
              f"{np.median(d_sh):+8.4f}  {np.median(d_cg):+8.2f}%")

        per_ts.append({
            "sp": sp, "days": days,
            "p_sharpe": round(p_sh, 4), "p_cagr": round(p_cg, 4),
            "p_mdd": round(p_md, 4), "p_nav": round(p_nv, 4),
            "med_d_sharpe": round(float(np.median(d_sh)), 6),
            "med_d_cagr": round(float(np.median(d_cg)), 4),
        })

    # Binomial tests
    print(f"\n  {'METRIC':>17}  {'wins':>5}/{n_sp}  {'binom p':>10}  {'verdict':>12}")
    print("  " + "-" * 55)

    binom = {}
    for label, wins in [
        ("P(Sharpe+)>50%", win_sh),
        ("P(CAGR+)>50%", win_cagr),
        ("P(MDD-)>50%", win_mdd),
        ("P(NAV+)>50%", win_nav),
    ]:
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

        print(f"  {label:>17}  {wins:5d}/{n_sp}  {p_binom:10.6f}  {verdict:>12}")
        binom[label] = {"wins": wins, "n": n_sp, "p_binom": round(p_binom, 8), "verdict": verdict}

    return per_ts, binom, boot_e0, boot_d1


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Multi-coin × 16 timescales (real data)
# ═══════════════════════════════════════════════════════════════════════

def phase4_multicoin_timescales():
    """D1 filter on all 14 coins × 16 timescales — real data only."""
    print(f"\n{'='*80}")
    print(f"PHASE 4: ALL COINS × 16 TIMESCALES (real data)")
    print(f"{'='*80}")

    # Per-coin: count how many timescales the filter helps
    coin_wins = {}

    for symbol in COINS:
        d = load_coin_raw(symbol)
        cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
        n = d["n"]
        wi = min(WARMUP_DAYS * 6, n - 100)

        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ema200 = _ema(cl, D1_EMA_PERIOD)

        wins = 0
        for sp in SLOW_PERIODS:
            fp = max(5, sp // 4)
            ef = _ema(cl, fp)
            es = _ema(cl, sp)

            r0 = sim_e0(cl, ef, es, at, vd, wi)
            rf = sim_e0_d1filter(cl, ef, es, at, vd, wi, ema200)

            if rf["sharpe"] > r0["sharpe"]:
                wins += 1

        coin_wins[symbol] = wins

    n_sp = len(SLOW_PERIODS)
    print(f"\n  D1 filter wins (Sharpe) per coin across {n_sp} timescales:")
    print(f"  {'Coin':>10s}  {'Wins':>5s}/{n_sp}  {'Pct':>6s}")
    print("  " + "-" * 30)

    n_majority = 0
    for s in COINS:
        w = coin_wins[s]
        pct = w / n_sp * 100
        marker = " *" if w > n_sp // 2 else ""
        if w > n_sp // 2: n_majority += 1
        print(f"  {s:>10s}  {w:5d}/{n_sp}  {pct:5.1f}%{marker}")

    print(f"\n  Coins where filter helps at majority of timescales: {n_majority}/{len(COINS)}")

    # Binomial meta-test: under H0 (filter random), each coin has 50% chance of majority wins
    p_meta = sp_stats.binomtest(n_majority, len(COINS), 0.5, alternative='greater').pvalue
    print(f"  Meta-test (binomial): p={p_meta:.6f}")

    return coin_wins


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("D1 EMA(200) REGIME FILTER STUDY")
    print("=" * 80)
    print(f"  Filter: close > EMA({D1_EMA_PERIOD} H4 bars ≈ 200 days)")
    print(f"  Applied to ENTRY only. Exit unchanged (ATR trail + EMA cross-down).")
    print(f"  Cost: 50 bps RT. Warmup: {WARMUP_DAYS}d.")

    # Phase 1: 14 coins at N=120
    p1 = phase1_coins(sp=120)

    # Phase 2: BTC × 16 timescales
    p2 = phase2_timescales()

    # Phase 4: All coins × 16 timescales
    p4 = phase4_multicoin_timescales()

    # Phase 3: Bootstrap (BTC, 2000 paths × 16 timescales)
    per_ts, binom, boot_e0, boot_d1 = phase3_bootstrap()

    # ── Overall verdict ──
    print(f"\n{'='*80}")
    print("OVERALL VERDICT")
    print(f"{'='*80}")

    # Check: does filter help at majority of timescales in bootstrap?
    nav_result = binom.get("P(NAV+)>50%", {})
    sh_result = binom.get("P(Sharpe+)>50%", {})
    mdd_result = binom.get("P(MDD-)>50%", {})

    boot_pass = nav_result.get("p_binom", 1.0) < 0.05

    # Real data: count how many coins improve
    n_coins_better = sum(1 for s in COINS
                         if p1[s]["E0+D1"]["sharpe"] > p1[s]["E0"]["sharpe"])

    print(f"  Real data (N=120): filter helps {n_coins_better}/{len(COINS)} coins")
    print(f"  Bootstrap NAV: {nav_result.get('wins',0)}/{len(SLOW_PERIODS)} timescales, "
          f"p={nav_result.get('p_binom',1):.6f} → {nav_result.get('verdict','?')}")
    print(f"  Bootstrap Sharpe: {sh_result.get('wins',0)}/{len(SLOW_PERIODS)} timescales, "
          f"p={sh_result.get('p_binom',1):.6f} → {sh_result.get('verdict','?')}")
    print(f"  Bootstrap MDD: {mdd_result.get('wins',0)}/{len(SLOW_PERIODS)} timescales, "
          f"p={mdd_result.get('p_binom',1):.6f} → {mdd_result.get('verdict','?')}")

    if boot_pass and n_coins_better >= 8:
        overall = "ACCEPT — D1 EMA(200) filter adds value"
    elif boot_pass:
        overall = "BOOT ONLY — bootstrap passes but real data inconsistent"
    elif n_coins_better >= 8:
        overall = "REAL ONLY — real data looks good but bootstrap fails"
    else:
        overall = "REJECT — D1 EMA(200) filter does NOT improve VTREND"

    print(f"\n  VERDICT: {overall}")

    el = time.time() - t_start
    print(f"\n  Total time: {el:.0f}s ({el/60:.1f} min)")

    # ── Save ──
    OUTDIR.mkdir(parents=True, exist_ok=True)

    output = {
        "config": {
            "d1_ema_period": D1_EMA_PERIOD,
            "h4_days_equiv": D1_EMA_PERIOD / 6,
            "cost_bps_rt": 50,
            "warmup_days": WARMUP_DAYS,
            "n_boot": N_BOOT,
            "seed": SEED,
        },
        "phase1_coins_n120": {s: {"E0": r["E0"], "E0+D1": r["E0+D1"]}
                              for s, r in p1.items()},
        "phase3_bootstrap": {
            "per_timescale": per_ts,
            "binomial": binom,
        },
        "phase4_coin_timescale_wins": p4,
        "overall_verdict": overall,
    }
    outfile = OUTDIR / "d1_ema200_filter.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print("=" * 80)
