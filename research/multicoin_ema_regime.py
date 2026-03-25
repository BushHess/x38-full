#!/usr/bin/env python3
"""Multi-Coin E0 + EMA(21d) Regime Filter Study.

Applies the PROVEN optimal EMA regime filter to VTREND E0 across all 14 coins.

EMA(21d) = EMA(126 H4 bars) selection rationale:
  - Bootstrap: 16/16 timescales PROVEN ALL metrics (p=1.5e-5)
  - Cross-coin: 11/14 coins improved at N=120 (BEST of all EMA periods)
  - Mean P(Sharpe+) = 58.8% across 16 timescales
  - Within PROVEN range (15-40d), optimal for multi-coin deployment

Design:
  1. Per-coin full history: E0 vs E0+EMA(21d) at N=120
  2. Per-coin 16 timescales: E0 vs E0+EMA(21d)
  3. Portfolio simulation (equal-weight): E0-only vs E0+filter
  4. Cross-asset correlation comparison
  5. Bootstrap: 500 paths × 16 timescales on BTC (paired comparison)
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
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from strategies.vtrend.strategy import _ema, _atr, _vdo
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ── Constants ─────────────────────────────────────────────────────────

CACHE_DIR = "/var/www/trading-bots/data-pipeline/.cache_binance_vision"

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "LTCUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "AVAXUSDT",
    "LINKUSDT", "BCHUSDT", "HBARUSDT", "XLMUSDT",
]

LARGE_CAP = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

CASH     = 10_000.0
CPS      = 0.0025
TRAIL    = 3.0
ATR_P    = 14
VDO_F    = 12
VDO_S    = 28
VDO_THR  = 0.0
ANN      = math.sqrt(6.0 * 365.25)

EMA_REGIME_P = 126   # EMA(21d) = 126 H4 bars
EMA_REGIME_DAYS = 21

N_BOOT   = 500
BLKSZ    = 60
SEED     = 42

WARMUP_DAYS = 365

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

OUTDIR = Path(__file__).resolve().parent / "results" / "multicoin_ema_regime"


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
        "timestamps": np.array([r[0] for r in unique], dtype=np.int64),
    }


# ═══════════════════════════════════════════════════════════════════════
# Simulation
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


def sim_nav_series(cl, ef, es, at, vd, wi, start_cash, ema_r=None):
    """Run sim and return per-bar NAV array. If ema_r is not None, apply regime filter."""
    n = len(cl)
    cash = start_cash; bq = 0.0; inp = False; pk = 0.0; pe = px = False
    navs = np.full(n, start_cash)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1.0 + CPS)); cash = 0.0; inp = True; pk = p
            elif px:
                px = False; cash = bq * fp * (1.0 - CPS); bq = 0.0; inp = False; pk = 0.0
        nav = cash + bq * p
        navs[i] = nav
        a_val = at[i]
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]): continue
        if not inp:
            entry_ok = ef[i] > es[i] and vd[i] > VDO_THR
            if ema_r is not None:
                entry_ok = entry_ok and p > ema_r[i]
            if entry_ok: pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); navs[-1] = cash
    return navs


def metrics_from_navs(navs, wi):
    active = navs[wi:]
    n = len(active)
    if n < 10:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "final_nav": active[-1] if n > 0 else 0}
    rets = active[1:] / active[:-1] - 1.0
    n_rets = len(rets)
    if n_rets < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "final_nav": active[-1]}
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    tr = active[-1] / active[0] - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    peak = np.maximum.accumulate(active)
    dd = 1.0 - active / peak
    mdd = float(np.max(dd)) * 100.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd,
            "calmar": calmar, "final_nav": active[-1]}


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Per-Coin Full History (E0 vs E0+EMA21)
# ═══════════════════════════════════════════════════════════════════════

def phase1_per_coin_full():
    """Each coin uses its FULL available data history."""
    print(f"\n{'='*90}")
    print(f"PHASE 1: PER-COIN FULL HISTORY — E0 vs E0+EMA({EMA_REGIME_DAYS}d)")
    print(f"{'='*90}")

    sp = 120; fp = max(5, sp // 4)
    results = {}

    print(f"\n  {'Coin':>10s}  {'':^28s}  {'':^28s}  {'ΔSh':>6s}  {'ΔCAGR':>7s}  {'ΔMDD':>6s}")
    print(f"  {'':>10s}  {'E0':^28s}  {'E0+EMA21':^28s}")
    print(f"  {'':>10s}  {'Sh':>6s} {'CAGR':>7s} {'MDD':>6s} {'Trd':>4s}  "
          f"{'Sh':>6s} {'CAGR':>7s} {'MDD':>6s} {'Trd':>4s}")
    print("  " + "-" * 88)

    for symbol in COINS:
        d = load_coin_raw(symbol)
        cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
        n = d["n"]
        wi = min(WARMUP_DAYS * 6, n - 100)

        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ef = _ema(cl, fp); es = _ema(cl, sp)
        ema_r = _ema(cl, EMA_REGIME_P)

        r0 = sim_e0(cl, ef, es, at, vd, wi)
        rf = sim_filtered(cl, ef, es, at, vd, wi, ema_r)

        d_sh = rf["sharpe"] - r0["sharpe"]
        d_cg = rf["cagr"] - r0["cagr"]
        d_md = rf["mdd"] - r0["mdd"]

        results[symbol] = {"e0": r0, "filtered": rf,
                           "d_sharpe": round(d_sh, 4), "d_cagr": round(d_cg, 2), "d_mdd": round(d_md, 2)}

        print(f"  {symbol:>10s}  {r0['sharpe']:+6.3f} {r0['cagr']:+6.1f}% {r0['mdd']:5.1f}% {r0['trades']:4d}  "
              f"{rf['sharpe']:+6.3f} {rf['cagr']:+6.1f}% {rf['mdd']:5.1f}% {rf['trades']:4d}  "
              f"{d_sh:+5.3f}  {d_cg:+6.1f}%  {d_md:+5.1f}")

    # Summary
    sh_better = sum(1 for s in COINS if results[s]["d_sharpe"] > 0)
    cg_better = sum(1 for s in COINS if results[s]["d_cagr"] > 0)
    md_better = sum(1 for s in COINS if results[s]["d_mdd"] < 0)

    print(f"\n  Summary: Sharpe better {sh_better}/14, CAGR better {cg_better}/14, MDD better {md_better}/14")

    return results


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Per-Coin × 16 Timescales
# ═══════════════════════════════════════════════════════════════════════

def phase2_timescale_sweep():
    """Each coin × 16 timescales: E0 vs E0+EMA21."""
    print(f"\n{'='*90}")
    print(f"PHASE 2: PER-COIN × 16 TIMESCALES — E0 vs E0+EMA({EMA_REGIME_DAYS}d)")
    print(f"{'='*90}")

    results = {}

    for symbol in COINS:
        d = load_coin_raw(symbol)
        cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
        n = d["n"]
        wi = min(WARMUP_DAYS * 6, n - 100)

        at = _atr(hi, lo, cl, ATR_P)
        vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
        ema_r = _ema(cl, EMA_REGIME_P)

        coin_results = {}
        for sp in SLOW_PERIODS:
            fp = max(5, sp // 4)
            ef = _ema(cl, fp); es = _ema(cl, sp)
            r0 = sim_e0(cl, ef, es, at, vd, wi)
            rf = sim_filtered(cl, ef, es, at, vd, wi, ema_r)
            coin_results[sp] = {"e0": r0, "filtered": rf,
                                "d_sharpe": round(rf["sharpe"] - r0["sharpe"], 4)}

        results[symbol] = coin_results

    # ── ΔSharpe heatmap ──
    print(f"\n  ΔSharpe (E0+EMA21 - E0) heatmap:")
    header = f"  {'Coin':>10s}"
    for sp in SLOW_PERIODS:
        header += f" {sp:>5d}"
    header += "  wins"
    print(header)
    print("  " + "-" * (12 + 6 * len(SLOW_PERIODS) + 6))

    coin_wins = {}
    for s in COINS:
        row = f"  {s:>10s}"
        wins = 0
        for sp in SLOW_PERIODS:
            d_sh = results[s][sp]["d_sharpe"]
            row += f" {d_sh:+5.3f}"
            if d_sh > 0: wins += 1
        row += f"  {wins:3d}/{len(SLOW_PERIODS)}"
        coin_wins[s] = wins
        print(row)

    # Coins where filter helps at majority of timescales
    majority_coins = [s for s in COINS if coin_wins[s] >= 9]
    print(f"\n  Coins where EMA21 helps ≥9/16 timescales: {len(majority_coins)}/14")
    for s in majority_coins:
        print(f"    {s}: {coin_wins[s]}/16")

    return results, coin_wins


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: Portfolio Simulation (aligned common range)
# ═══════════════════════════════════════════════════════════════════════

def phase3_portfolio():
    """Equal-weight portfolio: E0-only vs E0+EMA21, on aligned common range."""
    print(f"\n{'='*90}")
    print(f"PHASE 3: PORTFOLIO SIMULATION — ALIGNED COMMON RANGE")
    print(f"{'='*90}")

    # Load all coins and find common range
    print("\n  Loading data...")
    raw = {}
    for s in COINS:
        raw[s] = load_coin_raw(s)

    latest_start = max(d["timestamps"][0] for d in raw.values())
    earliest_end = min(d["timestamps"][-1] for d in raw.values())

    # Find common range per coin
    coin_ranges = {}
    for s in COINS:
        ts = raw[s]["timestamps"]
        i0 = int(np.searchsorted(ts, latest_start, side='left'))
        i1 = int(np.searchsorted(ts, earliest_end, side='right'))
        coin_ranges[s] = (i0, i1)

    n_common = min(i1 - i0 for i0, i1 in coin_ranges.values())
    wi = min(WARMUP_DAYS * 6, n_common - 100)

    common_start = datetime.fromtimestamp(latest_start / 1000, tz=timezone.utc)
    common_end = datetime.fromtimestamp(earliest_end / 1000, tz=timezone.utc)
    print(f"  Common range: {common_start:%Y-%m-%d} -> {common_end:%Y-%m-%d}")
    print(f"  Bars: {n_common}, Analysis: {n_common - wi}")

    # Compute indicators on full history, extract common range
    sp = 120; fp = max(5, sp // 4)
    K = len(COINS)
    per_coin_cash = CASH  # Each coin gets CASH (portfolio = K × CASH)

    e0_navs = {}
    filt_navs = {}

    print(f"\n  {'Coin':>10s}  {'E0 NAV':>10s}  {'Filt NAV':>10s}  {'ΔSh':>6s}  {'ΔMDD':>6s}")
    print("  " + "-" * 50)

    for s in COINS:
        d = raw[s]
        i0 = coin_ranges[s][0]
        i1 = i0 + n_common

        # Compute indicators on full data for maximum warmup
        at_full = _atr(d["hi"], d["lo"], d["cl"], ATR_P)
        vd_full = _vdo(d["cl"], d["hi"], d["lo"], d["vo"], d["tb"], VDO_F, VDO_S)
        ef_full = _ema(d["cl"], fp)
        es_full = _ema(d["cl"], sp)
        ema_r_full = _ema(d["cl"], EMA_REGIME_P)

        # Extract common range
        cl_c = d["cl"][i0:i1]
        at_c = at_full[i0:i1]
        vd_c = vd_full[i0:i1]
        ef_c = ef_full[i0:i1]
        es_c = es_full[i0:i1]
        ema_r_c = ema_r_full[i0:i1]

        # NAV series
        nav_e0 = sim_nav_series(cl_c, ef_c, es_c, at_c, vd_c, wi, per_coin_cash)
        nav_f = sim_nav_series(cl_c, ef_c, es_c, at_c, vd_c, wi, per_coin_cash, ema_r_c)

        e0_navs[s] = nav_e0
        filt_navs[s] = nav_f

        m_e0 = metrics_from_navs(nav_e0, wi)
        m_f = metrics_from_navs(nav_f, wi)

        print(f"  {s:>10s}  {nav_e0[-1]:10.2f}  {nav_f[-1]:10.2f}  "
              f"{m_f['sharpe'] - m_e0['sharpe']:+5.3f}  {m_f['mdd'] - m_e0['mdd']:+5.1f}")

    # Portfolio NAV = sum of per-coin NAVs
    port_e0 = sum(e0_navs[s] for s in COINS)
    port_filt = sum(filt_navs[s] for s in COINS)

    # Large-cap portfolio
    port_lc_e0 = sum(e0_navs[s] for s in LARGE_CAP)
    port_lc_filt = sum(filt_navs[s] for s in LARGE_CAP)

    # BTC-only (same total capital as full portfolio)
    btc_e0_scaled = e0_navs["BTCUSDT"] * K  # Scale to same total capital
    btc_filt_scaled = filt_navs["BTCUSDT"] * K

    # Metrics
    combos = [
        ("BTC-only E0", btc_e0_scaled),
        ("BTC-only +EMA21", btc_filt_scaled),
        ("14-coin E0", port_e0),
        ("14-coin +EMA21", port_filt),
        ("5-LC E0", port_lc_e0),
        ("5-LC +EMA21", port_lc_filt),
    ]

    print(f"\n  {'Portfolio':>18s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}  "
          f"{'Final NAV':>12s}")
    print("  " + "-" * 65)

    portfolio_results = {}
    for label, nav_arr in combos:
        m = metrics_from_navs(nav_arr, wi)
        print(f"  {label:>18s}  {m['sharpe']:+7.3f}  {m['cagr']:+6.1f}%  {m['mdd']:5.1f}%  "
              f"{m['calmar']:+7.3f}  {m['final_nav']:12.2f}")
        portfolio_results[label] = m

    # Cross-asset correlation
    print(f"\n  Cross-asset strategy return correlation (N=120, E0+EMA21):")
    returns_f = {}
    for s in COINS:
        nav = filt_navs[s][wi:]
        returns_f[s] = nav[1:] / nav[:-1] - 1.0

    rhos = []
    for i in range(K):
        for j in range(i + 1, K):
            r = np.corrcoef(returns_f[COINS[i]], returns_f[COINS[j]])[0, 1]
            rhos.append(r)

    mean_rho = float(np.mean(rhos))
    print(f"    Mean ρ = {mean_rho:.3f}, Median ρ = {np.median(rhos):.3f}, "
          f"Min = {np.min(rhos):.3f}, Max = {np.max(rhos):.3f}")

    # Diversification ratio
    k_eff = 1 + (K - 1) * (1 - mean_rho)
    div_ratio = math.sqrt(K / (1 + (K - 1) * mean_rho))
    print(f"    K_eff = {k_eff:.1f}, Diversification ratio = {div_ratio:.2f}x")

    return portfolio_results, n_common, wi


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Bootstrap BTC (paired comparison, reference)
# ═══════════════════════════════════════════════════════════════════════

def phase4_bootstrap():
    """500 paths × 16 timescales: E0 vs E0+EMA21 on BTC."""
    print(f"\n{'='*90}")
    print(f"PHASE 4: BOOTSTRAP BTC — {N_BOOT} paths × {len(SLOW_PERIODS)} timescales")
    print(f"{'='*90}")

    # Use BTC full data from coin loader (consistent with other phases)
    d = load_coin_raw("BTCUSDT")
    cl, hi, lo, vo, tb = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"]
    n = d["n"]

    from v10.core.data import DataFeed
    BTC_DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
    feed = DataFeed(BTC_DATA, start="2019-01-01", end="2026-02-20", warmup_days=WARMUP_DAYS)
    h4 = feed.h4_bars; nb = len(h4)
    cl_b = np.array([b.close for b in h4], dtype=np.float64)
    hi_b = np.array([b.high for b in h4], dtype=np.float64)
    lo_b = np.array([b.low for b in h4], dtype=np.float64)
    vo_b = np.array([b.volume for b in h4], dtype=np.float64)
    tb_b = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    wi_b = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi_b = i; break

    cr, hr, lr, vol, tbb = make_ratios(cl_b, hi_b, lo_b, vo_b, tb_b)
    vcbb_state = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
    n_trans = nb - 1
    p0 = cl_b[0]
    rng = np.random.default_rng(SEED)

    n_sp = len(SLOW_PERIODS)
    mkeys = ["sharpe", "cagr", "mdd", "final_nav"]
    boot_e0 = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}
    boot_f = {m: np.zeros((N_BOOT, n_sp)) for m in mkeys}

    t0 = time.time()
    for b in range(N_BOOT):
        if (b + 1) % 100 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)", flush=True)

        c, h, l, v, t = gen_path_vcbb(cr, hr, lr, vol, tbb, n_trans, BLKSZ, p0, rng, vcbb=vcbb_state)
        at = _atr(h, l, c, ATR_P)
        vd = _vdo(c, h, l, v, t, VDO_F, VDO_S)
        ema_r = _ema(c, EMA_REGIME_P)

        for j, sp in enumerate(SLOW_PERIODS):
            fp_v = max(5, sp // 4)
            ef = _ema(c, fp_v); es = _ema(c, sp)

            r0 = sim_e0(c, ef, es, at, vd, wi_b)
            rf = sim_filtered(c, ef, es, at, vd, wi_b, ema_r)

            for m in mkeys:
                boot_e0[m][b, j] = r0[m]
                boot_f[m][b, j] = rf[m]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s")

    # Results table
    print(f"\n  {'sp':>5}  {'days':>5}  {'P(Sh+)':>7}  {'P(CAGR+)':>9}  {'P(MDD-)':>8}  "
          f"{'P(NAV+)':>8}  {'medΔSh':>8}  {'medE0Sh':>8}  {'medFSh':>8}")
    print("  " + "-" * 80)

    win_sh = 0; win_cg = 0; win_md = 0; win_nv = 0

    for j, sp in enumerate(SLOW_PERIODS):
        d_sh = boot_f["sharpe"][:, j] - boot_e0["sharpe"][:, j]
        d_cg = boot_f["cagr"][:, j] - boot_e0["cagr"][:, j]
        d_md = boot_e0["mdd"][:, j] - boot_f["mdd"][:, j]
        d_nv = boot_f["final_nav"][:, j] - boot_e0["final_nav"][:, j]

        p_sh = float(np.mean(d_sh > 0))
        p_cg = float(np.mean(d_cg > 0))
        p_md = float(np.mean(d_md > 0))
        p_nv = float(np.mean(d_nv > 0))

        if p_sh > 0.5: win_sh += 1
        if p_cg > 0.5: win_cg += 1
        if p_md > 0.5: win_md += 1
        if p_nv > 0.5: win_nv += 1

        med_e0 = float(np.median(boot_e0["sharpe"][:, j]))
        med_f = float(np.median(boot_f["sharpe"][:, j]))

        print(f"  {sp:5d}  {sp*4/24:5.0f}  {p_sh*100:6.1f}%  {p_cg*100:8.1f}%  "
              f"{p_md*100:7.1f}%  {p_nv*100:7.1f}%  {np.median(d_sh):+8.4f}  "
              f"{med_e0:+8.4f}  {med_f:+8.4f}")

    # Binomial
    print(f"\n  {'METRIC':>17}  {'wins':>5}/{n_sp}  {'binom p':>10}  {'verdict':>12}")
    print("  " + "-" * 55)

    boot_summary = {}
    for label, wins in [
        ("P(Sharpe+)>50%", win_sh), ("P(CAGR+)>50%", win_cg),
        ("P(MDD-)>50%", win_md), ("P(NAV+)>50%", win_nv),
    ]:
        p_binom = binomtest(wins, n_sp, 0.5, alternative='greater').pvalue
        verdict = ("PROVEN ***" if p_binom < 0.001 else "PROVEN **" if p_binom < 0.01
                   else "PROVEN *" if p_binom < 0.025 else "STRONG" if p_binom < 0.05
                   else "MARGINAL" if p_binom < 0.10 else "NOT SIG")
        print(f"  {label:>17}  {wins:5d}/{n_sp}  {p_binom:10.6f}  {verdict:>12}")
        boot_summary[label] = {"wins": wins, "p_binom": round(p_binom, 8), "verdict": verdict}

    return boot_summary


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t_start = time.time()

    print("MULTI-COIN E0 + EMA REGIME FILTER STUDY")
    print("=" * 90)
    print(f"  Algorithm: VTREND E0 (slow=120, trail=3.0, vdo_thr=0.0)")
    print(f"  Regime filter: close > EMA({EMA_REGIME_DAYS}d) = EMA({EMA_REGIME_P} H4 bars)")
    print(f"  Entry only — does NOT affect exit")
    print(f"  Cost: 50 bps RT. Warmup: {WARMUP_DAYS}d.")

    # Phase 1: Per-coin full history
    p1_results = phase1_per_coin_full()

    # Phase 2: Per-coin × 16 timescales
    p2_results, p2_wins = phase2_timescale_sweep()

    # Phase 3: Portfolio simulation
    p3_results, n_common, wi = phase3_portfolio()

    # Phase 4: Bootstrap BTC
    p4_results = phase4_bootstrap()

    # ── Overall Verdict ──
    print(f"\n{'='*90}")
    print("OVERALL VERDICT")
    print(f"{'='*90}")

    sh_better = sum(1 for s in COINS if p1_results[s]["d_sharpe"] > 0)
    cg_better = sum(1 for s in COINS if p1_results[s]["d_cagr"] > 0)
    md_better = sum(1 for s in COINS if p1_results[s]["d_mdd"] < 0)

    print(f"\n  Per-coin real data (N=120, full history):")
    print(f"    Sharpe improved: {sh_better}/14 coins")
    print(f"    CAGR improved:   {cg_better}/14 coins")
    print(f"    MDD improved:    {md_better}/14 coins")

    ts_majority = sum(1 for s in COINS if p2_wins[s] >= 9)
    print(f"\n  Per-coin timescale robustness:")
    print(f"    Filter helps ≥9/16 timescales: {ts_majority}/14 coins")

    print(f"\n  Portfolio (common range, equal-weight):")
    for label in ["14-coin E0", "14-coin +EMA21", "BTC-only E0", "BTC-only +EMA21"]:
        m = p3_results[label]
        print(f"    {label:>18s}: Sh={m['sharpe']:+.3f}  CAGR={m['cagr']:+.1f}%  MDD={m['mdd']:.1f}%")

    print(f"\n  Bootstrap BTC (500 paths × 16 timescales):")
    for label, br in p4_results.items():
        print(f"    {label:>17s}: {br['wins']}/16 → {br['verdict']}")

    el = time.time() - t_start
    print(f"\n  Total time: {el:.0f}s ({el/60:.1f} min)")

    # ── Save ──
    OUTDIR.mkdir(parents=True, exist_ok=True)
    output = {
        "config": {
            "ema_regime_h4": EMA_REGIME_P,
            "ema_regime_days": EMA_REGIME_DAYS,
            "cost_bps_rt": 50, "warmup_days": WARMUP_DAYS,
            "n_boot": N_BOOT, "seed": SEED,
        },
        "phase1_per_coin": {s: {
            "e0_sharpe": p1_results[s]["e0"]["sharpe"],
            "e0_cagr": p1_results[s]["e0"]["cagr"],
            "e0_mdd": p1_results[s]["e0"]["mdd"],
            "e0_trades": p1_results[s]["e0"]["trades"],
            "filt_sharpe": p1_results[s]["filtered"]["sharpe"],
            "filt_cagr": p1_results[s]["filtered"]["cagr"],
            "filt_mdd": p1_results[s]["filtered"]["mdd"],
            "filt_trades": p1_results[s]["filtered"]["trades"],
            "d_sharpe": p1_results[s]["d_sharpe"],
            "d_cagr": p1_results[s]["d_cagr"],
            "d_mdd": p1_results[s]["d_mdd"],
        } for s in COINS},
        "phase2_timescale_wins": {s: p2_wins[s] for s in COINS},
        "phase3_portfolio": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                                  for kk, vv in v.items()}
                             for k, v in p3_results.items()},
        "phase4_bootstrap": p4_results,
    }

    outfile = OUTDIR / "multicoin_ema_regime.json"
    with open(outfile, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Saved: {outfile}")
    print(f"{'='*90}")
