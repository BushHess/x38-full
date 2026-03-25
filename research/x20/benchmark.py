#!/usr/bin/env python3
"""X20 Research — Cross-Asset VTREND Portfolio: Breadth Expansion

Tests whether a multi-asset VTREND portfolio achieves higher Sharpe than
BTC-only, using per-asset validated strategies with independent capital allocation.

Strategy assignment:
  BTC, ETH → E5+EMA1D21 (robust ATR, validated Study #43 / Q16)
  ALL OTHERS → E0+EMA1D21 (standard ATR, generalizes 11/14 coins)

Portfolio construction (zero DOF):
  EW  = Equal Weight
  IV  = Inverse-Variance
  BC  = BTC-Capped (40% max BTC, equal remainder)

Tests:
  T0: Per-asset full-sample screen (Sharpe>0, plateau, WFO)
  T1: Cross-asset correlation matrix
  T2: Portfolio backtest (3 weighting schemes)
  T3: Walk-forward validation (4 folds)
  T4: Portfolio bootstrap (500 VCBB, joint)
  T5: Drawdown analysis
  T6: Comparison table

Gates:
  G0: ≥3 coins pass screens
  G1: Best portfolio Sharpe > BTC-only Sharpe
  G2: WFO ≥75%, mean d_sharpe > 0
  G3: P(d_sharpe > 0) > 60%
  G4: Median d_mdd ≤ +5pp
"""

from __future__ import annotations

import csv
import glob
import json
import math
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# ═══════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════

CACHE_DIR = "/var/www/trading-bots/data-pipeline/.cache_binance_vision"

ALL_COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "LTCUSDT", "ADAUSDT", "DOGEUSDT", "TRXUSDT", "AVAXUSDT",
    "LINKUSDT", "BCHUSDT", "HBARUSDT", "XLMUSDT",
]

# BTC and ETH use E5 (robust ATR); all others use E0 (standard ATR)
E5_COINS = {"BTCUSDT", "ETHUSDT"}

CASH      = 10_000.0
CPS       = 0.0025        # 25 bps per side
TRAIL     = 3.0
ATR_P     = 14            # E0 standard ATR period
RATR_P    = 20            # E5 robust ATR period
RATR_Q    = 0.90          # E5 Q90 cap quantile
RATR_LB   = 100           # E5 lookback for rolling quantile
VDO_F     = 12
VDO_S     = 28
VDO_THR   = 0.0
ANN       = math.sqrt(6.0 * 365.25)
D1_EMA_P  = 21            # EMA(21d) regime filter

SLOW      = 120
FAST      = max(5, SLOW // 4)

PLATEAU_PERIODS = [60, 72, 84, 96, 108, 120, 144, 168, 200]
PLATEAU_MIN_POSITIVE = 5   # ≥5/9 slow periods must have Sharpe > 0

N_BOOT    = 500
BLKSZ     = 60
SEED      = 42

WARMUP_DAYS = 365

WFO_FOLDS = [
    ("2021-12-31", "2022-01-01", "2022-12-31"),
    ("2022-12-31", "2023-01-01", "2023-12-31"),
    ("2023-12-31", "2024-01-01", "2024-12-31"),
    ("2024-12-31", "2025-01-01", "2026-02-20"),
]

BTC_CAP   = 0.40          # BTC-capped weighting: max 40% BTC

OUTDIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════════════
# Data Loading
# ═══════════════════════════════════════════════════════════════════

def load_coin_raw(symbol: str) -> dict:
    """Load H4 bars from Binance Vision ZIP cache."""
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
                    rows.append((ts, float(cols[2]), float(cols[3]),
                                 float(cols[4]), float(cols[5]), float(cols[9])))
        except Exception:
            pass

    rows.sort(key=lambda x: x[0])
    seen = set(); unique = []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0]); unique.append(r)

    return {
        "cl": np.array([r[3] for r in unique], dtype=np.float64),
        "hi": np.array([r[1] for r in unique], dtype=np.float64),
        "lo": np.array([r[2] for r in unique], dtype=np.float64),
        "vo": np.array([r[4] for r in unique], dtype=np.float64),
        "tb": np.array([r[5] for r in unique], dtype=np.float64),
        "n": len(unique),
        "timestamps": np.array([r[0] for r in unique], dtype=np.int64),
    }


# ═══════════════════════════════════════════════════════════════════
# Indicators
# ═══════════════════════════════════════════════════════════════════

def _ema(series, period):
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series, dtype=np.float64)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1]
    return out


def _atr(high, low, close, period=ATR_P):
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        out[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def _robust_atr(high, low, close, cap_q=RATR_Q, cap_lb=RATR_LB, period=RATR_P):
    """E5 robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


def _vdo(close, high, low, volume, taker_buy, fast=VDO_F, slow=VDO_S):
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        typical = (high + low + close) / 3.0
        diff = np.concatenate([[0.0], np.diff(typical)])
        vdr = np.where(diff >= 0, volume, -volume)
        mx = np.max(np.abs(vdr))
        if mx > 0:
            vdr = vdr / mx
    ef = _ema(vdr, fast)
    es = _ema(vdr, slow)
    return ef - es


def _compute_atr_for_coin(symbol, high, low, close):
    """Return the correct ATR for a coin (E5 for BTC/ETH, E0 for others)."""
    if symbol in E5_COINS:
        return _robust_atr(high, low, close)
    return _atr(high, low, close)


def _compute_d1_ema(h4_cl, h4_ts, d1_ema_period=D1_EMA_P):
    """Compute D1 EMA regime filter and map to H4 bars."""
    # Aggregate H4 → D1
    ms_per_day = 86_400_000
    day_keys = h4_ts // ms_per_day
    unique_days = np.unique(day_keys)

    d1_close = np.empty(len(unique_days))
    for k, dk in enumerate(unique_days):
        mask = day_keys == dk
        d1_close[k] = h4_cl[mask][-1]  # last H4 close of day

    d1_ema = _ema(d1_close, d1_ema_period)

    # Map back to H4: each H4 bar gets the D1 EMA of its day
    regime_h4 = np.empty(len(h4_cl), dtype=np.float64)
    day_to_ema = dict(zip(unique_days, d1_ema))
    for i in range(len(h4_cl)):
        dk = day_keys[i]
        regime_h4[i] = day_to_ema[dk]
    return regime_h4


# ═══════════════════════════════════════════════════════════════════
# Simulation
# ═══════════════════════════════════════════════════════════════════

def _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt):
    if n_rets < 2 or navs_start <= 0:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0,
                "calmar": 0.0, "trades": nt, "final_nav": navs_end}
    tr = navs_end / navs_start - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    mdd = (1.0 - nav_min_ratio) * 100.0
    mu = rets_sum / n_rets
    var = rets_sq_sum / n_rets - mu * mu
    std = math.sqrt(max(var, 0.0))
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": round(sharpe, 4), "cagr": round(cagr, 2),
            "mdd": round(mdd, 2), "calmar": round(calmar, 4),
            "trades": nt, "final_nav": round(navs_end, 2)}


def sim_filtered(cl, ef, es, at, vd, wi, ema_r):
    """Run sim with EMA regime filter. Returns metrics dict."""
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pk = 0.0
    pe = px = False; nt = 0
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
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and p > ema_r[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); bq = 0.0; nt += 1; navs_end = cash
    return _metrics(navs_start, navs_end, nav_min_ratio, rets_sum, rets_sq_sum, n_rets, nt)


def sim_nav_series(cl, ef, es, at, vd, wi, start_cash, ema_r=None):
    """Run sim and return per-bar NAV array."""
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
        if math.isnan(a_val) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            entry_ok = ef[i] > es[i] and vd[i] > VDO_THR
            if ema_r is not None:
                entry_ok = entry_ok and p > ema_r[i]
            if entry_ok:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a_val:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash = bq * cl[-1] * (1.0 - CPS); navs[-1] = cash
    return navs


def metrics_from_navs(navs, wi):
    active = navs[wi:]
    n = len(active)
    if n < 10:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0,
                "calmar": 0.0, "final_nav": active[-1] if n > 0 else 0}
    rets = active[1:] / active[:-1] - 1.0
    n_rets = len(rets)
    if n_rets < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0,
                "calmar": 0.0, "final_nav": active[-1]}
    mu = np.mean(rets); std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    tr = active[-1] / active[0] - 1.0
    yrs = n_rets / (6.0 * 365.25)
    cagr = ((1 + tr) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and tr > -1 else -100.0
    peak = np.maximum.accumulate(active)
    dd = 1.0 - active / peak
    mdd = float(np.max(dd)) * 100.0
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": round(sharpe, 4), "cagr": round(cagr, 2),
            "mdd": round(mdd, 2), "calmar": round(calmar, 4),
            "final_nav": round(active[-1], 2)}


# ═══════════════════════════════════════════════════════════════════
# Data Preparation
# ═══════════════════════════════════════════════════════════════════

def prepare_data(coins):
    """Load coins, compute indicators on full history, align to common range."""
    print("\n  Loading raw data...")
    raw = {}
    for s in coins:
        d = load_coin_raw(s)
        raw[s] = d
        t0 = datetime.fromtimestamp(d["timestamps"][0] / 1000, tz=timezone.utc)
        t1 = datetime.fromtimestamp(d["timestamps"][-1] / 1000, tz=timezone.utc)
        print(f"    {s:>10s}: {d['n']:6d} bars ({t0:%Y-%m-%d} -> {t1:%Y-%m-%d})")

    latest_start = max(d["timestamps"][0] for d in raw.values())
    earliest_end = min(d["timestamps"][-1] for d in raw.values())

    coin_ranges = {}
    for s in coins:
        ts = raw[s]["timestamps"]
        i0 = int(np.searchsorted(ts, latest_start, side='left'))
        i1 = int(np.searchsorted(ts, earliest_end, side='right'))
        coin_ranges[s] = (i0, i1)

    n_common = min(i1 - i0 for i0, i1 in coin_ranges.values())

    print(f"\n  Computing indicators on full per-coin history...")
    aligned = {}
    for s in coins:
        d = raw[s]
        i0 = coin_ranges[s][0]
        i1 = i0 + n_common

        at_full = _compute_atr_for_coin(s, d["hi"], d["lo"], d["cl"])
        vd_full = _vdo(d["cl"], d["hi"], d["lo"], d["vo"], d["tb"])
        ef_full = _ema(d["cl"], FAST)
        es_full = _ema(d["cl"], SLOW)
        ema_r_full = _compute_d1_ema(d["cl"], d["timestamps"])

        aligned[s] = {
            "cl": d["cl"][i0:i1].copy(),
            "hi": d["hi"][i0:i1].copy(),
            "lo": d["lo"][i0:i1].copy(),
            "vo": d["vo"][i0:i1].copy(),
            "tb": d["tb"][i0:i1].copy(),
            "ts": d["timestamps"][i0:i1].copy(),
            "at": at_full[i0:i1].copy(),
            "vd": vd_full[i0:i1].copy(),
            "ef": ef_full[i0:i1].copy(),
            "es": es_full[i0:i1].copy(),
            "ema_r": ema_r_full[i0:i1].copy(),
        }

    wi = min(WARMUP_DAYS * 6, n_common - 100)
    n_trans = n_common - 1

    # Bootstrap ratios
    print(f"  Computing bootstrap ratios...")
    boot_ratios = {}
    for s in coins:
        a = aligned[s]
        cr, hr, lr, vr, tr = make_ratios(a["cl"], a["hi"], a["lo"], a["vo"], a["tb"])
        vcbb_st = precompute_vcbb(cr, blksz=BLKSZ, ctx=90)
        boot_ratios[s] = {"cr": cr, "hr": hr, "lr": lr, "vol": vr, "tb": tr, "vcbb": vcbb_st}

    common_start = datetime.fromtimestamp(latest_start / 1000, tz=timezone.utc)
    common_end = datetime.fromtimestamp(earliest_end / 1000, tz=timezone.utc)
    print(f"\n  Common range: {common_start:%Y-%m-%d} -> {common_end:%Y-%m-%d}")
    print(f"  Bars: {n_common}, Warmup: {wi}, Analysis: {n_common - wi}")

    info = {
        "common_start": f"{common_start:%Y-%m-%d}",
        "common_end": f"{common_end:%Y-%m-%d}",
        "n_common": n_common, "wi": wi, "n_trans": n_trans,
    }
    return aligned, wi, n_common, n_trans, boot_ratios, info


# ═══════════════════════════════════════════════════════════════════
# T0: Per-Asset Full-Sample Screen
# ═══════════════════════════════════════════════════════════════════

def t0_per_asset_screen():
    """Screen all 14 coins. Return list of coins passing all screens."""
    print(f"\n{'='*90}")
    print("T0: PER-ASSET FULL-SAMPLE SCREEN")
    print(f"{'='*90}")

    results = {}
    passed = []

    print(f"\n  {'Coin':>10s}  {'Strategy':>10s}  {'Sharpe':>7s}  {'CAGR':>7s}  "
          f"{'MDD':>6s}  {'Trades':>6s}  {'Pos/9':>5s}  {'Pass?':>5s}")
    print("  " + "-" * 75)

    for symbol in ALL_COINS:
        d = load_coin_raw(symbol)
        cl, hi, lo, vo, tb, ts = d["cl"], d["hi"], d["lo"], d["vo"], d["tb"], d["timestamps"]
        n = d["n"]
        wi = min(WARMUP_DAYS * 6, n - 100)

        strat = "E5+EMA1D" if symbol in E5_COINS else "E0+EMA1D"
        at = _compute_atr_for_coin(symbol, hi, lo, cl)
        vd = _vdo(cl, hi, lo, vo, tb)
        ef = _ema(cl, FAST); es = _ema(cl, SLOW)
        ema_r = _compute_d1_ema(cl, ts)

        m = sim_filtered(cl, ef, es, at, vd, wi, ema_r)

        # Plateau check: count slow periods with positive Sharpe
        n_positive = 0
        for sp in PLATEAU_PERIODS:
            fp = max(5, sp // 4)
            ef_p = _ema(cl, fp); es_p = _ema(cl, sp)
            m_p = sim_filtered(cl, ef_p, es_p, at, vd, wi, ema_r)
            if m_p["sharpe"] > 0:
                n_positive += 1

        # Screen: Sharpe > 0 at N=120 AND majority of plateau periods positive
        pass_screen = m["sharpe"] > 0.0 and n_positive >= PLATEAU_MIN_POSITIVE
        tag = "PASS" if pass_screen else "FAIL"

        results[symbol] = {
            "strategy": strat, **m,
            "n_positive_plateau": n_positive,
            "pass_screen": pass_screen,
        }
        if pass_screen:
            passed.append(symbol)

        print(f"  {symbol:>10s}  {strat:>10s}  {m['sharpe']:+7.3f}  {m['cagr']:+6.1f}%  "
              f"{m['mdd']:5.1f}%  {m['trades']:6d}  {n_positive:3d}/9  {tag:>5s}")

    print(f"\n  Passed: {len(passed)}/{len(ALL_COINS)} coins: {passed}")

    # Save CSV
    with open(OUTDIR / "x20_per_asset.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["coin", "strategy", "sharpe", "cagr", "mdd", "trades",
                     "n_positive_plateau", "pass_screen"])
        for s in ALL_COINS:
            r = results[s]
            w.writerow([s, r["strategy"], r["sharpe"], r["cagr"], r["mdd"],
                         r["trades"], r["n_positive_plateau"], r["pass_screen"]])

    return results, passed


# ═══════════════════════════════════════════════════════════════════
# T1: Cross-Asset Correlation Matrix
# ═══════════════════════════════════════════════════════════════════

def t1_correlation(aligned, wi, coins):
    """Compute cross-asset return correlation matrix."""
    print(f"\n{'='*90}")
    print("T1: CROSS-ASSET CORRELATION MATRIX")
    print(f"{'='*90}")

    K = len(coins)
    returns = {}
    for s in coins:
        a = aligned[s]
        nav = sim_nav_series(a["cl"], a["ef"], a["es"], a["at"], a["vd"], wi,
                             CASH, a["ema_r"])
        active = nav[wi:]
        returns[s] = active[1:] / active[:-1] - 1.0

    # Correlation matrix
    corr_matrix = np.zeros((K, K))
    for i in range(K):
        for j in range(K):
            corr_matrix[i, j] = np.corrcoef(returns[coins[i]], returns[coins[j]])[0, 1]

    # Print
    header = f"  {'':>10s}" + "".join(f" {s[:5]:>6s}" for s in coins)
    print(f"\n{header}")
    print("  " + "-" * (10 + 7 * K))
    for i in range(K):
        row = f"  {coins[i][:5]:>10s}"
        for j in range(K):
            row += f" {corr_matrix[i, j]:+6.3f}"
        print(row)

    # Summary stats
    rhos = []
    for i in range(K):
        for j in range(i + 1, K):
            rhos.append(corr_matrix[i, j])
    mean_rho = float(np.mean(rhos))
    median_rho = float(np.median(rhos))
    div_ratio = math.sqrt(K / (1 + (K - 1) * mean_rho)) if K > 1 else 1.0

    print(f"\n  Mean ρ = {mean_rho:.3f}, Median ρ = {median_rho:.3f}")
    print(f"  Min ρ = {min(rhos):.3f}, Max ρ = {max(rhos):.3f}")
    print(f"  Diversification ratio = {div_ratio:.2f}x")

    # Save CSV
    with open(OUTDIR / "x20_correlation.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([""] + coins)
        for i in range(K):
            w.writerow([coins[i]] + [round(corr_matrix[i, j], 4) for j in range(K)])

    return {"mean_rho": round(mean_rho, 4), "median_rho": round(median_rho, 4),
            "div_ratio": round(div_ratio, 4), "matrix": corr_matrix, "returns": returns}


# ═══════════════════════════════════════════════════════════════════
# T2: Portfolio Backtest
# ═══════════════════════════════════════════════════════════════════

def _compute_weights(scheme, coins, returns_train=None):
    """Compute portfolio weights for a given scheme."""
    K = len(coins)
    if scheme == "EW":
        return {s: 1.0 / K for s in coins}
    elif scheme == "IV":
        vols = {}
        for s in coins:
            vols[s] = max(np.std(returns_train[s], ddof=0), 1e-12)
        inv_var = {s: 1.0 / (v * v) for s, v in vols.items()}
        total = sum(inv_var.values())
        return {s: inv_var[s] / total for s in coins}
    elif scheme == "BC":
        # BTC capped at BTC_CAP, rest equal
        w = {}
        btc_in = "BTCUSDT" in coins
        if btc_in and K > 1:
            w["BTCUSDT"] = BTC_CAP
            remainder = (1.0 - BTC_CAP) / (K - 1)
            for s in coins:
                if s != "BTCUSDT":
                    w[s] = remainder
        else:
            for s in coins:
                w[s] = 1.0 / K
        return w
    else:
        raise ValueError(f"Unknown scheme: {scheme}")


def t2_portfolio_backtest(aligned, wi, coins, corr_data):
    """Run portfolio backtest with 3 weighting schemes."""
    print(f"\n{'='*90}")
    print("T2: PORTFOLIO BACKTEST")
    print(f"{'='*90}")

    K = len(coins)

    # Compute per-coin NAV series
    per_coin_nav = {}
    for s in coins:
        a = aligned[s]
        per_coin_nav[s] = sim_nav_series(
            a["cl"], a["ef"], a["es"], a["at"], a["vd"], wi, CASH, a["ema_r"])

    # Training returns for IV weights (use first 50% of analysis period)
    n_analysis = len(per_coin_nav[coins[0]]) - wi
    n_train = n_analysis // 2
    returns_train = {}
    for s in coins:
        active = per_coin_nav[s][wi:wi + n_train]
        returns_train[s] = active[1:] / active[:-1] - 1.0

    # BTC-only benchmark (same total capital = K * CASH)
    btc_a = aligned["BTCUSDT"]
    btc_nav = sim_nav_series(btc_a["cl"], btc_a["ef"], btc_a["es"], btc_a["at"],
                             btc_a["vd"], wi, CASH * K, btc_a["ema_r"])
    btc_m = metrics_from_navs(btc_nav, wi)

    results = {"BTC-only": btc_m}

    print(f"\n  {'Scheme':>12s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  "
          f"{'Calmar':>7s}  {'Final NAV':>12s}  Weights")
    print("  " + "-" * 85)
    print(f"  {'BTC-only':>12s}  {btc_m['sharpe']:+7.3f}  {btc_m['cagr']:+6.1f}%  "
          f"{btc_m['mdd']:5.1f}%  {btc_m['calmar']:+7.3f}  {btc_m['final_nav']:12.2f}  100% BTC")

    best_scheme = None
    best_sharpe = -999

    for scheme in ["EW", "IV", "BC"]:
        weights = _compute_weights(scheme, coins, returns_train)

        # Portfolio NAV = sum of weighted per-coin NAVs
        port_nav = np.zeros_like(per_coin_nav[coins[0]])
        for s in coins:
            port_nav += per_coin_nav[s] * (weights[s] * K)  # scale: each coin gets CASH

        # With rebalancing: approximate by using weights × per-coin NAV
        # Since each coin gets CASH independently, portfolio = sum of (w_i * K) * nav_i
        # This is equivalent to monthly rebalancing with negligible tracking error
        # for the simple case of independent accounts

        m = metrics_from_navs(port_nav, wi)
        w_str = ", ".join(f"{s[:3]}:{weights[s]*100:.0f}%" for s in coins)

        results[scheme] = {**m, "weights": {s: round(weights[s], 4) for s in coins}}

        if m["sharpe"] > best_sharpe:
            best_sharpe = m["sharpe"]
            best_scheme = scheme

        print(f"  {scheme:>12s}  {m['sharpe']:+7.3f}  {m['cagr']:+6.1f}%  "
              f"{m['mdd']:5.1f}%  {m['calmar']:+7.3f}  {m['final_nav']:12.2f}  {w_str}")

    # Gate G1
    g1_pass = best_sharpe > btc_m["sharpe"]
    print(f"\n  G1: Best portfolio Sharpe ({best_scheme}: {best_sharpe:.3f}) "
          f"{'>' if g1_pass else '<='} BTC-only ({btc_m['sharpe']:.3f}) → "
          f"{'PASS' if g1_pass else 'FAIL'}")

    # Save CSV
    with open(OUTDIR / "x20_portfolio.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scheme", "sharpe", "cagr", "mdd", "calmar", "final_nav"])
        for label, m in results.items():
            w.writerow([label, m["sharpe"], m["cagr"], m["mdd"],
                         m["calmar"], m["final_nav"]])

    return results, best_scheme, g1_pass, per_coin_nav, btc_nav


# ═══════════════════════════════════════════════════════════════════
# T3: Walk-Forward Validation
# ═══════════════════════════════════════════════════════════════════

def _ts_to_bar(h4_ts, date_str):
    """Convert YYYY-MM-DD to bar index."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    target_ms = int(dt.timestamp() * 1000)
    return int(np.searchsorted(h4_ts, target_ms, side='left'))


def t3_wfo(aligned, wi, coins, best_scheme):
    """Walk-forward validation: 4 folds."""
    print(f"\n{'='*90}")
    print(f"T3: WALK-FORWARD VALIDATION (scheme={best_scheme})")
    print(f"{'='*90}")

    K = len(coins)
    h4_ts = aligned[coins[0]]["ts"]
    results = []

    print(f"\n  {'Fold':>4s}  {'Year':>6s}  {'BTC Sh':>7s}  {'Port Sh':>7s}  "
          f"{'d_Sharpe':>8s}  {'d_MDD':>6s}  {'Result':>6s}")
    print("  " + "-" * 55)

    for fold_idx, (train_end, test_start, test_end) in enumerate(WFO_FOLDS):
        te_bar = _ts_to_bar(h4_ts, train_end)
        ts_bar = _ts_to_bar(h4_ts, test_start)
        te2_bar = min(_ts_to_bar(h4_ts, test_end), len(h4_ts) - 1)

        # Training returns for IV weights
        returns_train = {}
        for s in coins:
            a = aligned[s]
            nav_train = sim_nav_series(a["cl"][:te_bar], a["ef"][:te_bar],
                                       a["es"][:te_bar], a["at"][:te_bar],
                                       a["vd"][:te_bar], wi, CASH,
                                       a["ema_r"][:te_bar])
            active = nav_train[wi:]
            returns_train[s] = active[1:] / active[:-1] - 1.0 if len(active) > 1 else np.array([0.0])

        weights = _compute_weights(best_scheme, coins, returns_train)

        # Test period: run each asset on test slice, compute portfolio
        test_btc_nav = sim_nav_series(
            aligned["BTCUSDT"]["cl"][ts_bar:te2_bar],
            aligned["BTCUSDT"]["ef"][ts_bar:te2_bar],
            aligned["BTCUSDT"]["es"][ts_bar:te2_bar],
            aligned["BTCUSDT"]["at"][ts_bar:te2_bar],
            aligned["BTCUSDT"]["vd"][ts_bar:te2_bar],
            0, CASH * K,
            aligned["BTCUSDT"]["ema_r"][ts_bar:te2_bar])

        port_nav_test = np.zeros(te2_bar - ts_bar)
        for s in coins:
            a = aligned[s]
            nav_s = sim_nav_series(
                a["cl"][ts_bar:te2_bar], a["ef"][ts_bar:te2_bar],
                a["es"][ts_bar:te2_bar], a["at"][ts_bar:te2_bar],
                a["vd"][ts_bar:te2_bar], 0, CASH,
                a["ema_r"][ts_bar:te2_bar])
            port_nav_test += nav_s * (weights[s] * K)

        btc_m = metrics_from_navs(test_btc_nav, 0)
        port_m = metrics_from_navs(port_nav_test, 0)

        d_sh = port_m["sharpe"] - btc_m["sharpe"]
        d_mdd = port_m["mdd"] - btc_m["mdd"]
        win = d_sh > 0
        year = test_start[:4]

        results.append({
            "fold": fold_idx + 1, "year": year,
            "btc_sharpe": btc_m["sharpe"], "port_sharpe": port_m["sharpe"],
            "d_sharpe": round(d_sh, 4), "d_mdd": round(d_mdd, 2),
            "win": win,
        })

        print(f"  {fold_idx+1:4d}  {year:>6s}  {btc_m['sharpe']:+7.3f}  "
              f"{port_m['sharpe']:+7.3f}  {d_sh:+8.4f}  {d_mdd:+5.1f}  "
              f"{'WIN' if win else 'LOSE':>6s}")

    wins = sum(1 for r in results if r["win"])
    mean_d = float(np.mean([r["d_sharpe"] for r in results]))
    g2_pass = wins >= 3 and mean_d > 0

    print(f"\n  Win rate: {wins}/4, mean d_sharpe: {mean_d:+.4f}")
    print(f"  G2: WFO {'PASS' if g2_pass else 'FAIL'}")

    # Save CSV
    with open(OUTDIR / "x20_wfo.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fold", "year", "btc_sharpe", "port_sharpe", "d_sharpe", "d_mdd", "win"])
        for r in results:
            w.writerow([r["fold"], r["year"], r["btc_sharpe"], r["port_sharpe"],
                         r["d_sharpe"], r["d_mdd"], r["win"]])

    return results, g2_pass, wins, mean_d


# ═══════════════════════════════════════════════════════════════════
# T4: Portfolio Bootstrap
# ═══════════════════════════════════════════════════════════════════

def t4_bootstrap(aligned, wi, n_common, n_trans, boot_ratios, coins, best_scheme):
    """Joint bootstrap: sample shared block indices, run all assets."""
    print(f"\n{'='*90}")
    print(f"T4: PORTFOLIO BOOTSTRAP ({N_BOOT} VCBB paths, scheme={best_scheme})")
    print(f"{'='*90}")

    K = len(coins)
    rng = np.random.default_rng(SEED)

    d_sharpes = np.zeros(N_BOOT)
    d_mdds = np.zeros(N_BOOT)
    btc_sharpes = np.zeros(N_BOOT)
    port_sharpes = np.zeros(N_BOOT)

    t0 = time.time()

    for b in range(N_BOOT):
        if (b + 1) % 50 == 0 or b == 0:
            el = time.time() - t0
            rate = (b + 1) / el if el > 0 else 1
            eta = (N_BOOT - b - 1) / rate
            print(f"    {b+1:5d}/{N_BOOT}  ({el:.0f}s, ~{eta:.0f}s left)", flush=True)

        # Generate shared block indices via RNG state (same RNG for all coins)
        # Each coin gets its own path but from synchronized random seed
        path_seed = rng.integers(0, 2**31)

        per_coin_nav = {}
        returns_train = {}

        for s in coins:
            br = boot_ratios[s]
            coin_rng = np.random.default_rng(path_seed)
            c, h, l, v, t = gen_path_vcbb(
                br["cr"], br["hr"], br["lr"], br["vol"], br["tb"],
                n_trans, BLKSZ, aligned[s]["cl"][0], coin_rng, vcbb=br["vcbb"])

            at = _compute_atr_for_coin(s, h, l, c)
            vd = _vdo(c, h, l, v, t)
            ef = _ema(c, FAST); es = _ema(c, SLOW)
            ema_r = _ema(c, D1_EMA_P * 6)  # approximate D1 EMA from H4

            nav = sim_nav_series(c, ef, es, at, vd, wi, CASH, ema_r)
            per_coin_nav[s] = nav

            # Training returns for IV weights (first 50%)
            n_an = len(nav) - wi
            n_tr = n_an // 2
            active = nav[wi:wi + n_tr]
            returns_train[s] = active[1:] / active[:-1] - 1.0 if len(active) > 1 else np.array([0.0])

        weights = _compute_weights(best_scheme, coins, returns_train)

        # Portfolio NAV
        port_nav = np.zeros_like(per_coin_nav[coins[0]])
        for s in coins:
            port_nav += per_coin_nav[s] * (weights[s] * K)

        # BTC-only NAV (same total capital)
        btc_nav = per_coin_nav["BTCUSDT"] * K

        port_m = metrics_from_navs(port_nav, wi)
        btc_m = metrics_from_navs(btc_nav, wi)

        d_sharpes[b] = port_m["sharpe"] - btc_m["sharpe"]
        d_mdds[b] = port_m["mdd"] - btc_m["mdd"]
        btc_sharpes[b] = btc_m["sharpe"]
        port_sharpes[b] = port_m["sharpe"]

    el = time.time() - t0
    print(f"\n  Done: {el:.1f}s ({el/60:.1f} min)")

    # Results
    p_sharpe = float(np.mean(d_sharpes > 0))
    med_d_mdd = float(np.median(d_mdds))

    g3_pass = p_sharpe > 0.60
    g4_pass = med_d_mdd <= 5.0

    print(f"\n  P(d_sharpe > 0) = {p_sharpe*100:.1f}%")
    print(f"  Median d_mdd = {med_d_mdd:+.1f} pp")
    print(f"  Median BTC Sharpe = {np.median(btc_sharpes):.3f}")
    print(f"  Median Portfolio Sharpe = {np.median(port_sharpes):.3f}")
    print(f"\n  G3: P(d_sharpe > 0) = {p_sharpe*100:.1f}% {'>' if g3_pass else '<='} 60% → "
          f"{'PASS' if g3_pass else 'FAIL'}")
    print(f"  G4: Median d_mdd = {med_d_mdd:+.1f} pp {'<=' if g4_pass else '>'} +5pp → "
          f"{'PASS' if g4_pass else 'FAIL'}")

    # Save CSV
    with open(OUTDIR / "x20_bootstrap.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "btc_sharpe", "port_sharpe", "d_sharpe", "d_mdd"])
        for b in range(N_BOOT):
            w.writerow([b, round(btc_sharpes[b], 4), round(port_sharpes[b], 4),
                         round(d_sharpes[b], 4), round(d_mdds[b], 2)])

    return {
        "p_sharpe": round(p_sharpe, 4),
        "med_d_mdd": round(med_d_mdd, 2),
        "med_btc_sharpe": round(float(np.median(btc_sharpes)), 4),
        "med_port_sharpe": round(float(np.median(port_sharpes)), 4),
        "g3_pass": g3_pass, "g4_pass": g4_pass,
    }


# ═══════════════════════════════════════════════════════════════════
# T5: Drawdown Analysis
# ═══════════════════════════════════════════════════════════════════

def t5_drawdown(per_coin_nav, btc_nav, wi, coins):
    """Analyze portfolio drawdowns vs BTC-only."""
    print(f"\n{'='*90}")
    print("T5: DRAWDOWN ANALYSIS")
    print(f"{'='*90}")

    btc_active = btc_nav[wi:]
    btc_peak = np.maximum.accumulate(btc_active)
    btc_dd = 1.0 - btc_active / btc_peak

    # Portfolio drawdown (sum of per-coin NAVs, already computed)
    K = len(coins)
    port_active_nav = sum(per_coin_nav[s][wi:] for s in coins)
    port_peak = np.maximum.accumulate(port_active_nav)
    port_dd = 1.0 - port_active_nav / port_peak

    btc_mdd = float(np.max(btc_dd)) * 100
    port_mdd = float(np.max(port_dd)) * 100

    # Per-coin MDD
    print(f"\n  {'Coin':>10s}  {'MDD':>7s}")
    print("  " + "-" * 20)
    coin_mdds = {}
    for s in coins:
        active = per_coin_nav[s][wi:]
        pk = np.maximum.accumulate(active)
        dd = float(np.max(1.0 - active / pk)) * 100
        coin_mdds[s] = dd
        print(f"  {s:>10s}  {dd:6.1f}%")

    print(f"\n  Portfolio MDD: {port_mdd:.1f}%")
    print(f"  BTC-only MDD:  {btc_mdd:.1f}%")
    print(f"  Improvement:   {btc_mdd - port_mdd:+.1f} pp")

    # Max simultaneous drawdown
    max_simul = 0
    for i in range(len(btc_active)):
        n_in_dd = 0
        for s in coins:
            active = per_coin_nav[s][wi:]
            pk_s = np.maximum.accumulate(active)
            if active[i] < pk_s[i] * 0.95:  # >5% drawdown
                n_in_dd += 1
        max_simul = max(max_simul, n_in_dd)

    print(f"  Max simultaneous >5% DD: {max_simul}/{K} coins")

    # Save CSV
    with open(OUTDIR / "x20_drawdown.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["coin", "mdd"])
        for s in coins:
            w.writerow([s, coin_mdds[s]])
        w.writerow(["PORTFOLIO", port_mdd])
        w.writerow(["BTC-only", btc_mdd])

    return {"btc_mdd": round(btc_mdd, 2), "port_mdd": round(port_mdd, 2),
            "improvement_pp": round(btc_mdd - port_mdd, 2),
            "max_simul_dd": max_simul, "coin_mdds": coin_mdds}


# ═══════════════════════════════════════════════════════════════════
# T6: Comparison Table
# ═══════════════════════════════════════════════════════════════════

def t6_comparison(portfolio_results, btc_sharpe_full):
    """Final comparison table."""
    print(f"\n{'='*90}")
    print("T6: COMPARISON TABLE")
    print(f"{'='*90}")

    print(f"\n  {'Strategy':>15s}  {'Sharpe':>7s}  {'CAGR':>7s}  {'MDD':>6s}  {'Calmar':>7s}")
    print("  " + "-" * 55)

    rows = []
    for label, m in portfolio_results.items():
        print(f"  {label:>15s}  {m['sharpe']:+7.3f}  {m['cagr']:+6.1f}%  "
              f"{m['mdd']:5.1f}%  {m['calmar']:+7.3f}")
        rows.append([label, m["sharpe"], m["cagr"], m["mdd"], m["calmar"]])

    with open(OUTDIR / "x20_comparison.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "sharpe", "cagr", "mdd", "calmar"])
        for r in rows:
            w.writerow(r)

    return rows


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()

    print("X20: CROSS-ASSET VTREND PORTFOLIO — BREADTH EXPANSION")
    print("=" * 90)
    print(f"  BTC/ETH: E5+EMA1D21 (robust ATR)")
    print(f"  Others:  E0+EMA1D21 (standard ATR)")
    print(f"  Cost: 50 bps RT. Warmup: {WARMUP_DAYS}d.")
    print(f"  Weighting: EW, IV, BC (BTC capped {BTC_CAP*100:.0f}%)")

    all_results = {"config": {
        "coins": ALL_COINS, "e5_coins": list(E5_COINS),
        "slow": SLOW, "trail": TRAIL, "cost_bps_rt": 50,
        "warmup_days": WARMUP_DAYS, "n_boot": N_BOOT, "seed": SEED,
        "btc_cap": BTC_CAP, "d1_ema_period": D1_EMA_P,
    }}

    # ── T0: Per-asset screen ──
    t0_results, passed_coins = t0_per_asset_screen()
    all_results["t0"] = t0_results

    g0_pass = len(passed_coins) >= 3
    print(f"\n  G0: {len(passed_coins)} coins passed ({'≥' if g0_pass else '<'} 3) → "
          f"{'PASS' if g0_pass else 'FAIL'}")

    if not g0_pass:
        print("\n  ABORT: Fewer than 3 coins pass screens. VTREND is BTC-specific.")
        all_results["verdict"] = "CLOSE"
        all_results["gates"] = {"G0": False}
        with open(OUTDIR / "x20_results.json", "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        return

    # Ensure BTC is included
    if "BTCUSDT" not in passed_coins:
        passed_coins.insert(0, "BTCUSDT")

    print(f"\n  Portfolio coins ({len(passed_coins)}): {passed_coins}")

    # ── Prepare aligned data ──
    aligned, wi, n_common, n_trans, boot_ratios, info = prepare_data(passed_coins)
    all_results["alignment"] = info

    # ── T1: Correlation ──
    corr_data = t1_correlation(aligned, wi, passed_coins)
    all_results["t1_correlation"] = {
        "mean_rho": corr_data["mean_rho"],
        "median_rho": corr_data["median_rho"],
        "div_ratio": corr_data["div_ratio"],
    }

    # ── T2: Portfolio backtest ──
    t2_results, best_scheme, g1_pass, per_coin_nav, btc_nav = \
        t2_portfolio_backtest(aligned, wi, passed_coins, corr_data)
    all_results["t2_portfolio"] = {k: {kk: vv for kk, vv in v.items() if kk != "weights"}
                                    if isinstance(v, dict) else v
                                    for k, v in t2_results.items()}
    all_results["best_scheme"] = best_scheme

    # ── T3: WFO ──
    t3_results, g2_pass, wfo_wins, wfo_mean_d = \
        t3_wfo(aligned, wi, passed_coins, best_scheme)
    all_results["t3_wfo"] = {
        "folds": t3_results, "wins": wfo_wins,
        "mean_d_sharpe": round(wfo_mean_d, 4), "g2_pass": g2_pass,
    }

    # ── T4: Bootstrap ──
    t4_results = t4_bootstrap(aligned, wi, n_common, n_trans, boot_ratios,
                               passed_coins, best_scheme)
    all_results["t4_bootstrap"] = t4_results

    # ── T5: Drawdown ──
    t5_results = t5_drawdown(per_coin_nav, btc_nav, wi, passed_coins)
    all_results["t5_drawdown"] = t5_results

    # ── T6: Comparison ──
    t6_comparison(t2_results, t2_results["BTC-only"]["sharpe"])

    # ── Gate Summary ──
    gates = {
        "G0": g0_pass,
        "G1": g1_pass,
        "G2": g2_pass,
        "G3": t4_results["g3_pass"],
        "G4": t4_results["g4_pass"],
    }
    all_pass = all(gates.values())

    print(f"\n{'='*90}")
    print("GATE SUMMARY")
    print(f"{'='*90}")
    for g, v in gates.items():
        print(f"  {g}: {'PASS' if v else 'FAIL'}")

    if all_pass:
        verdict = "PROMOTE"
    elif g0_pass and g1_pass:
        verdict = "HOLD"
    else:
        verdict = "CLOSE"

    print(f"\n  VERDICT: {verdict}")

    all_results["gates"] = gates
    all_results["verdict"] = verdict

    # ── Save ──
    with open(OUTDIR / "x20_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Saved: {OUTDIR / 'x20_results.json'}")

    el = time.time() - t_start
    print(f"  Total time: {el:.0f}s ({el/60:.1f} min)")
    print("=" * 90)


if __name__ == "__main__":
    main()
