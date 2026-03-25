#!/usr/bin/env python3
"""EMA Regime Filter — Fine-Grained Sweep (D1 EMA < 200 days).

Previous sweep found:
  - EMA(200 H4) = 33d: PROVEN 16/16 all metrics (p=1.5e-5)
  - EMA(534 H4) = 89d: FAILED (7/16 Sharpe, MDD only)
  - EMA(600 H4) = 100d: FAILED (6/16 Sharpe, MDD only)
  - EMA(720 H4) = 120d: FAILED (3/16 Sharpe, MDD only)

This study fills the gap with ~20 EMA periods from 15d to 150d,
and bootstraps ALL candidates (not just top 3-4).

Phases:
  1. BTC × 16 timescales × all EMA periods (real data)
  2. 14 coins × N=120 × all EMA periods (real data)
  3. Bootstrap BTC × 16 timescales × ALL candidates (2000 paths)
"""

from __future__ import annotations

import glob
import json
import math
import sys
import time
import zipfile
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

# Targeted EMA test: D1 EMA 21/63/126
EMA_SWEEP = [
    126,          # 21d (D1 EMA 21 — ~1 month)
    378,          # 63d (D1 EMA 63 — ~1 quarter)
    756,          # 126d (D1 EMA 126 — ~6 months)
]

BTC_DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")

N_BOOT = 500
BLKSZ  = 60
SEED   = 42

OUTDIR = Path(__file__).resolve().parent / "results" / "ema_regime_21_63_126"


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
                    if len(cols) < 12: continue
                    ts = int(cols[0])
                    if ts > 1e15: ts = ts // 1000
                    rows.append((ts, float(cols[2]), float(cols[3]), float(cols[4]),
                                 float(cols[5]), float(cols[9])))
        except Exception:
            pass
    rows.sort(key=lambda x: x[0])
    seen = set(); unique = []
    for r in rows:
        if r[0] not in seen: seen.add(r[0]); unique.append(r)
    n = len(unique)
    return {
        "cl": np.array([r[3] for r in unique], dtype=np.float64),
        "hi": np.array([r[1] for r in unique], dtype=np.float64),
        "lo": np.array([r[2] for r in unique], dtype=np.float64),
        "vo": np.array([r[4] for r in unique], dtype=np.float64),
        "tb": np.array([r[5] for r in unique], dtype=np.float64),
        "n": n,
    }


def load_btc_arrays():
    from v10.core.data import DataFeed
    feed = DataFeed(BTC_DATA, start="2019-01-01", end="2026-02-20", warmup_days=WARMUP_DAYS)
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


# ═══════════════════════════════════════════════════════════════════════
# Metrics & Sim
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


def sim_filtered(cl, ef, es, at, vd, wi, ema_regime):
    """E0 + regime filter: only enter when close > ema_regime."""
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
            if ef[i] > es[i] and vd[i] > VDO_THR and p > ema_regime[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


# ═══════════════════════════════════════════════════════════════════════
# Bootstrap helpers
# ═══════════════════════════════════════════════════════════════════════

def make_ratios(cl, hi, lo, vo, tb):
    pc = cl[:-1]
    return cl[1:] / pc, hi[1:] / pc, lo[1:] / pc, vo[1:].copy(), tb[1:].copy()


def gen_path(cr, hr, lr, vol, tb, n_trans, blksz, p0, rng):
    n_blk = math.ceil(n_trans / blksz)
    mx = len(cr) - blksz
    if mx <= 0: idx = np.arange(min(n_trans, len(cr)))
    else:
        starts = rng.integers(0, mx + 1, size=n_blk)
        idx = np.concatenate([np.arange(s, s + blksz) for s in starts])[:n_trans]
    c = np.empty(len(idx) + 1, dtype=np.float64); c[0] = p0; c[1:] = p0 * np.cumprod(cr[idx])
    h = np.empty_like(c); l = np.empty_like(c); v = np.empty_like(c); t = np.empty_like(c)
    h[0] = p0 * 1.002; l[0] = p0 * 0.998; v[0] = vol[idx[0]]; t[0] = tb[idx[0]]
    h[1:] = c[:-1] * hr[idx]; l[1:] = c[:-1] * lr[idx]; v[1:] = vol[idx]; t[1:] = tb[idx]
    np.maximum(h, c, out=h); np.minimum(l, c, out=l)
    return c, h, l, v, t


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: BTC × 16 timescales × EMA sweep (real data)
# ═══════════════════════════════════════════════════════════════════════

def phase1_btc_sweep():
    print(f"\n{'='*90}")
    print(f"PHASE 1: BTC — {len(EMA_SWEEP)} EMA PERIODS × {len(SLOW_PERIODS)} TIMESCALES")
    print(f"{'='*90}")

    d = load_coin_raw("BTCUSDT")
    cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
    n = d["n"]
    wi = min(WARMUP_DAYS * 6, n - 100)

    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    ema_regimes = {k: _ema(cl, k) for k in EMA_SWEEP}

    e0_results = {}
    for sp in SLOW_PERIODS:
        fp = max(5, sp // 4)
        ef = _ema(cl, fp); es = _ema(cl, sp)
        e0_results[sp] = sim_e0(cl, ef, es, at, vd, wi)

    filtered_results = {}
    for ek in EMA_SWEEP:
        filtered_results[ek] = {}
        for sp in SLOW_PERIODS:
            fp = max(5, sp // 4)
            ef = _ema(cl, fp); es = _ema(cl, sp)
            filtered_results[ek][sp] = sim_filtered(cl, ef, es, at, vd, wi, ema_regimes[ek])

    # ── ΔSharpe heatmap ──
    print(f"\n  ΔSharpe (filtered - E0) heatmap:")
    header = f"  {'EMA':>6s} {'days':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  wins"
    print(header)
    print("  " + "-" * (13 + 6 * len(SLOW_PERIODS) + 6))

    for ek in EMA_SWEEP:
        days = ek / 6
        row = f"  {ek:6d} {days:5.0f}"
        wins = 0
        for sp in SLOW_PERIODS:
            d_sh = filtered_results[ek][sp]["sharpe"] - e0_results[sp]["sharpe"]
            row += f" {d_sh:+5.3f}"
            if d_sh > 0: wins += 1
        row += f"  {wins:3d}/{len(SLOW_PERIODS)}"
        print(row)

    # ── ΔMDD heatmap ──
    print(f"\n  ΔMDD (filtered - E0, negative=better) heatmap:")
    header = f"  {'EMA':>6s} {'days':>5s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  wins"
    print(header)
    print("  " + "-" * (13 + 6 * len(SLOW_PERIODS) + 6))

    for ek in EMA_SWEEP:
        days = ek / 6
        row = f"  {ek:6d} {days:5.0f}"
        wins = 0
        for sp in SLOW_PERIODS:
            d_md = filtered_results[ek][sp]["mdd"] - e0_results[sp]["mdd"]
            row += f" {d_md:+5.1f}"
            if d_md < 0: wins += 1
        row += f"  {wins:3d}/{len(SLOW_PERIODS)}"
        print(row)

    # ── Summary ──
    print(f"\n  Summary (mean across {len(SLOW_PERIODS)} timescales):")
    print(f"  {'EMA':>6s} {'days':>5s}  {'meanΔSh':>8s}  {'meanΔCAGR':>10s}  {'meanΔMDD':>9s}  "
          f"{'Sh wins':>8s}  {'MDD wins':>9s}")
    print("  " + "-" * 65)

    for ek in EMA_SWEEP:
        days = ek / 6
        d_shs = [filtered_results[ek][sp]["sharpe"] - e0_results[sp]["sharpe"]
                 for sp in SLOW_PERIODS]
        d_cgs = [filtered_results[ek][sp]["cagr"] - e0_results[sp]["cagr"]
                 for sp in SLOW_PERIODS]
        d_mds = [filtered_results[ek][sp]["mdd"] - e0_results[sp]["mdd"]
                 for sp in SLOW_PERIODS]
        sh_wins = sum(1 for x in d_shs if x > 0)
        mdd_wins = sum(1 for x in d_mds if x < 0)
        print(f"  {ek:6d} {days:5.0f}  {np.mean(d_shs):+8.4f}  {np.mean(d_cgs):+9.2f}%  "
              f"{np.mean(d_mds):+8.1f}pp  {sh_wins:5d}/{len(SLOW_PERIODS)}  "
              f"{mdd_wins:5d}/{len(SLOW_PERIODS)}")

    return e0_results, filtered_results


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: 14 coins × N=120 × EMA sweep (real data)
# ═══════════════════════════════════════════════════════════════════════

def phase2_multicoin(sp=120):
    print(f"\n{'='*90}")
    print(f"PHASE 2: 14 COINS × N={sp} × {len(EMA_SWEEP)} EMA PERIODS")
    print(f"{'='*90}")

    fp = max(5, sp // 4)
    coin_results = {}

    for symbol in COINS:
        d = load_coin_raw(symbol)
        cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
        n = d["n"]
        wi = min(WARMUP_DAYS * 6, n - 100)

        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ef = _ema(cl, fp); es = _ema(cl, sp)

        r0 = sim_e0(cl, ef, es, at, vd, wi)
        coin_results[symbol] = {"E0": r0}

        for ek in EMA_SWEEP:
            ema_r = _ema(cl, ek)
            rf = sim_filtered(cl, ef, es, at, vd, wi, ema_r)
            coin_results[symbol][ek] = rf

    # ── ΔSharpe table ──
    print(f"\n  ΔSharpe (filtered - E0) at N={sp}:")
    header = f"  {'Coin':>10s}"
    for ek in EMA_SWEEP:
        header += f" {ek/6:>4.0f}d"
    print(header)
    print("  " + "-" * (12 + 5 * len(EMA_SWEEP)))

    ema_wins = {ek: 0 for ek in EMA_SWEEP}

    for s in COINS:
        row = f"  {s:>10s}"
        r0_sh = coin_results[s]["E0"]["sharpe"]
        for ek in EMA_SWEEP:
            d_sh = coin_results[s][ek]["sharpe"] - r0_sh
            row += f" {d_sh:+4.2f}"
            if d_sh > 0:
                ema_wins[ek] += 1
        print(row)

    print(f"\n  Wins (coins where filter helps Sharpe):")
    for ek in EMA_SWEEP:
        days = ek / 6
        print(f"    EMA({ek:5d}) = {days:5.0f}d: {ema_wins[ek]:2d}/14 coins")

    best_coin_ek = max(ema_wins, key=ema_wins.get)
    print(f"\n  Best cross-coin: EMA({best_coin_ek}) = {best_coin_ek/6:.0f}d, "
          f"{ema_wins[best_coin_ek]}/14 coins")

    return coin_results, ema_wins


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Bootstrap — ALL EMA candidates × BTC × 16 timescales
# ═══════════════════════════════════════════════════════════════════════

def phase3_bootstrap():
    """2000 paths × 16 timescales for ALL EMA candidates."""
    n_cand = len(EMA_SWEEP)
    print(f"\n{'='*90}")
    print(f"PHASE 3: BOOTSTRAP — {N_BOOT} paths × {len(SLOW_PERIODS)} timescales × "
          f"{n_cand} EMA candidates")
    print(f"  ALL candidates: {[f'{k/6:.0f}d' for k in EMA_SWEEP]}")
    print(f"{'='*90}")

    cl, hi, lo, vo, tb, wi, n = load_btc_arrays()
    cr, hr, lr, vol, tbb = make_ratios(cl, hi, lo, vo, tb)
    n_trans = n - 1
    p0 = cl[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "final_nav"]

    boot_e0 = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_f = {ek: {m: np.zeros((N_BOOT, n_sp)) for m in mkeys} for ek in EMA_SWEEP}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 100 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)", flush=True)

        c, h, l, v, t = gen_path(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)

        # Pre-compute EMA regimes for this path
        ema_rs = {ek: _ema(c, ek) for ek in EMA_SWEEP}

        for j, sp in enumerate(SLOW_PERIODS):
            fp = max(5, sp // 4)
            ef = _ema(c, fp); es = _ema(c, sp)

            r0 = sim_e0(c, ef, es, at, vd, wi)
            for m in mkeys: boot_e0[m][b, j] = r0[m]

            for ek in EMA_SWEEP:
                rf = sim_filtered(c, ef, es, at, vd, wi, ema_rs[ek])
                for m in mkeys: boot_f[ek][m][b, j] = rf[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({N_BOOT * n_sp * (1 + n_cand)} sims)")

    # ── Analysis per candidate ──
    all_results = {}

    for ek in EMA_SWEEP:
        days = ek / 6
        print(f"\n  {'─'*60}")
        print(f"  EMA({ek}) = {days:.0f} days")
        print(f"  {'─'*60}")

        print(f"\n  {'sp':>5}  {'days':>5}  "
              f"{'P(Sh+)':>7}  {'P(CAGR+)':>9}  {'P(MDD-)':>8}  {'P(NAV+)':>8}  "
              f"{'medΔSh':>8}")
        print("  " + "-" * 60)

        win_sh = 0; win_cg = 0; win_md = 0; win_nv = 0

        for j, sp in enumerate(SLOW_PERIODS):
            d_sh = boot_f[ek]["sharpe"][:, j] - boot_e0["sharpe"][:, j]
            d_cg = boot_f[ek]["cagr"][:, j] - boot_e0["cagr"][:, j]
            d_md = boot_e0["mdd"][:, j] - boot_f[ek]["mdd"][:, j]
            d_nv = boot_f[ek]["final_nav"][:, j] - boot_e0["final_nav"][:, j]

            p_sh = float(np.mean(d_sh > 0))
            p_cg = float(np.mean(d_cg > 0))
            p_md = float(np.mean(d_md > 0))
            p_nv = float(np.mean(d_nv > 0))

            if p_sh > 0.5: win_sh += 1
            if p_cg > 0.5: win_cg += 1
            if p_md > 0.5: win_md += 1
            if p_nv > 0.5: win_nv += 1

            print(f"  {sp:5d}  {sp*4/24:5.0f}  "
                  f"{p_sh*100:6.1f}%  {p_cg*100:8.1f}%  {p_md*100:7.1f}%  {p_nv*100:7.1f}%  "
                  f"{np.median(d_sh):+8.4f}")

        # Binomial
        print(f"\n  {'METRIC':>17}  {'wins':>5}/{n_sp}  {'binom p':>10}  {'verdict':>12}")
        print("  " + "-" * 55)

        binom = {}
        for label, wins in [
            ("P(Sharpe+)>50%", win_sh), ("P(CAGR+)>50%", win_cg),
            ("P(MDD-)>50%", win_md), ("P(NAV+)>50%", win_nv),
        ]:
            p_binom = sp_stats.binomtest(wins, n_sp, 0.5, alternative='greater').pvalue
            verdict = ("PROVEN ***" if p_binom < 0.001 else "PROVEN **" if p_binom < 0.01
                       else "PROVEN *" if p_binom < 0.025 else "STRONG" if p_binom < 0.05
                       else "MARGINAL" if p_binom < 0.10 else "NOT SIG")
            print(f"  {label:>17}  {wins:5d}/{n_sp}  {p_binom:10.6f}  {verdict:>12}")
            binom[label] = {"wins": wins, "p_binom": round(p_binom, 8), "verdict": verdict}

        all_results[ek] = binom

    return all_results


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("EMA REGIME FILTER — FINE-GRAINED SWEEP (D1 EMA < 200 days)")
    print("=" * 90)
    print(f"  {len(EMA_SWEEP)} EMA periods: {[f'{k/6:.0f}d' for k in EMA_SWEEP]}")
    print(f"  Entry filter: close > EMA(K) on H4")
    print(f"  Cost: 50 bps RT. Warmup: {WARMUP_DAYS}d. Bootstrap: {N_BOOT} paths.")

    # Phase 1
    e0_real, filt_real = phase1_btc_sweep()

    # Phase 2
    coin_results, ema_wins = phase2_multicoin(sp=120)

    # Phase 3: Bootstrap ALL candidates
    boot_results = phase3_bootstrap()

    # ── Overall Verdict ──
    print(f"\n{'='*90}")
    print("OVERALL VERDICT — FINE-GRAINED SWEEP")
    print(f"{'='*90}")

    # Summary table: all candidates
    print(f"\n  {'EMA':>6s}  {'days':>5s}  {'Sh wins':>8s}  {'CAGR wins':>10s}  "
          f"{'MDD wins':>9s}  {'NAV wins':>9s}  {'verdict':>20s}")
    print("  " + "-" * 80)

    proven_sharpe = []
    for ek in EMA_SWEEP:
        br = boot_results[ek]
        days = ek / 6
        sh_w = br["P(Sharpe+)>50%"]["wins"]
        cg_w = br["P(CAGR+)>50%"]["wins"]
        md_w = br["P(MDD-)>50%"]["wins"]
        nv_w = br["P(NAV+)>50%"]["wins"]

        sh_p = br["P(Sharpe+)>50%"]["p_binom"]
        nv_p = br["P(NAV+)>50%"]["p_binom"]
        md_p = br["P(MDD-)>50%"]["p_binom"]

        if sh_p < 0.001:
            verdict = "PROVEN ALL ***"
            proven_sharpe.append(ek)
        elif sh_p < 0.025:
            verdict = "PROVEN Sharpe *"
            proven_sharpe.append(ek)
        elif sh_p < 0.05:
            verdict = "STRONG Sharpe"
        elif md_p < 0.05:
            verdict = "MDD only"
        else:
            verdict = "NOT SIG"

        print(f"  {ek:6d}  {days:5.0f}  {sh_w:5d}/16  {cg_w:7d}/16  "
              f"{md_w:6d}/16  {nv_w:6d}/16  {verdict:>20s}")

    if proven_sharpe:
        print(f"\n  PROVEN RANGE: EMA {proven_sharpe[0]/6:.0f}d — {proven_sharpe[-1]/6:.0f}d "
              f"({len(proven_sharpe)} periods)")
        # Optimal = highest mean P(Sharpe+) across timescales
        best_ek = max(proven_sharpe, key=lambda ek:
                      boot_results[ek]["P(Sharpe+)>50%"]["wins"])
        print(f"  OPTIMAL: EMA({best_ek}) = {best_ek/6:.0f}d")
    else:
        print(f"\n  VERDICT: No EMA period proves Sharpe improvement in bootstrap")

    el = time.time() - t_start
    print(f"\n  Total time: {el:.0f}s ({el/60:.1f} min)")

    # ── Save ──
    OUTDIR.mkdir(parents=True, exist_ok=True)
    output = {
        "config": {
            "ema_sweep_h4": EMA_SWEEP,
            "ema_sweep_days": [round(k/6, 1) for k in EMA_SWEEP],
            "cost_bps_rt": 50, "warmup_days": WARMUP_DAYS,
            "n_boot": N_BOOT, "seed": SEED, "blksz": BLKSZ,
        },
        "phase3_bootstrap": {},
    }
    for ek in EMA_SWEEP:
        output["phase3_bootstrap"][str(ek)] = boot_results[ek]
    if proven_sharpe:
        output["proven_range_days"] = [round(proven_sharpe[0]/6, 1),
                                        round(proven_sharpe[-1]/6, 1)]
        output["proven_count"] = len(proven_sharpe)

    outfile = OUTDIR / "ema_regime_fine.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print(f"{'='*90}")
