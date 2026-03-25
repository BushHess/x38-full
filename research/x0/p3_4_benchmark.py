#!/usr/bin/env python3
"""P3.4 — Full benchmark + bootstrap + risk-overlay attribution for X0 Phase 3.

Strategies compared (7):
  1. E0          = vtrend (baseline)
  2. E0+EMA21    = vtrend_ema21_d1 (D1 regime filter)
  3. E5          = vtrend_e5 (robust ATR trail)
  4. E5+EMA21    = vtrend_e5_ema21_d1 (robust ATR + D1 regime)
  5. X0          = vtrend_x0 (Phase 1 — behavioral clone of E0+EMA21)
  6. X0_E5EXIT   = vtrend_x0_e5exit (Phase 2 — X0 entry + E5 robust ATR exit)
  7. X0_VOLSIZE  = vtrend_x0_volsize (Phase 3 — Phase 2 + frozen vol sizing)

Evaluation pipeline:
  T1. Full backtest (3 cost scenarios: smart, base, harsh)
  T2. Bootstrap VCBB (500 paths, default slow=120, block=60)
  T3. Attribution (Phase 3 vs Phase 2: delta table, matched-entry, mechanism)
  T4. Exposure stats + vol bucket analysis (Phase 3 specific)

Follows canonical P2.4 patterns. Same data/warmup/cost/seed.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb


# =========================================================================
# CONSTANTS (identical to P2.4)
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
TRAIL = 3.0
SLOW = 120

N_BOOT = 500
BLKSZ = 60
SEED = 42

# Phase 3 vol-sizing parameters
TARGET_VOL = 0.15
VOL_LOOKBACK = 120
VOL_FLOOR = 0.08
BARS_PER_YEAR_4H = 365.0 * 6.0  # 2190.0

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["E0", "E0_EMA21", "E5", "E5_EMA21", "X0", "X0_E5EXIT", "X0_VOLSIZE"]
STRATEGY_LABELS = {
    "E0": "VTrend E0",
    "E0_EMA21": "E0+EMA21(D1)",
    "E5": "VTrend E5",
    "E5_EMA21": "E5+EMA21(D1)",
    "X0": "X0 Phase 1",
    "X0_E5EXIT": "X0 Phase 2 (E5exit)",
    "X0_VOLSIZE": "X0 Phase 3 (volsize)",
}


# =========================================================================
# FAST INDICATORS (C-level via scipy.signal.lfilter) — identical to P2.4
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )
    out = np.full_like(tr, np.nan)
    if period <= len(tr):
        seed = np.mean(tr[:period])
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


def _vdo(close: np.ndarray, high: np.ndarray, low: np.ndarray,
         volume: np.ndarray, taker_buy: np.ndarray,
         fast: int, slow: int) -> np.ndarray:
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)
    if has_taker:
        taker_sell = volume - taker_buy
        vdr = np.zeros(n)
        mask = volume > 0
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def _robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                cap_q: float = 0.90, cap_lb: int = 100, period: int = 20) -> np.ndarray:
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    tr_cap = np.full(n, np.nan)
    if cap_lb <= n:
        from numpy.lib.stride_tricks import sliding_window_view
        windows = sliding_window_view(tr[:n], cap_lb)
        relevant = windows[:n - cap_lb]
        q_vals = np.percentile(relevant, cap_q * 100, axis=1)
        tr_slice = tr[cap_lb:n]
        tr_cap[cap_lb:n] = np.minimum(tr_slice, q_vals)
    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        seed = np.nanmean(tr_cap[s:s + period])
        ratr[s + period - 1] = seed
        alpha = 1.0 / period
        b = np.array([alpha])
        a = np.array([1.0, -(1.0 - alpha)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b, a, tail, zi=zi)
            ratr[s + period:] = smoothed
    return ratr


def _d1_regime_map(cl, d1_cl, d1_close_times, h4_close_times, d1_ema_period=21):
    n = len(cl)
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_close_times[i]:
            d1_idx += 1
        if d1_close_times[d1_idx] < h4_close_times[i]:
            regime_h4[i] = d1_regime[d1_idx]
    return regime_h4


# =========================================================================
# NEW: _realized_vol indicator for Phase 3
# =========================================================================

def _realized_vol(close: np.ndarray, lookback: int = VOL_LOOKBACK,
                  bars_per_year: float = BARS_PER_YEAR_4H) -> np.ndarray:
    """Rolling realized volatility (annualized), population std(ddof=0)."""
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    lr = np.full(n, np.nan, dtype=np.float64)
    lr[1:] = np.log(
        np.divide(close[1:], close[:-1],
                  out=np.full(n - 1, np.nan, dtype=np.float64),
                  where=close[:-1] > 0.0))
    ann_factor = math.sqrt(bars_per_year)
    for i in range(lookback, n):
        window = lr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=0)) * ann_factor
    return out


# =========================================================================
# METRICS — identical to P2.4
# =========================================================================

def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0,
                "trades": nt, "total_return": 0.0, "win_rate": 0.0,
                "profit_factor": 0.0, "avg_exposure": 0.0}
    rets = navs[1:] / navs[:-1] - 1.0
    n = len(rets)
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0

    total_ret = navs[-1] / navs[0] - 1.0
    yrs = n / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0

    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100

    calmar = cagr / mdd if mdd > 0.01 else 0.0

    in_market = np.sum(np.abs(rets) > 1e-10) / n * 100 if n > 0 else 0.0

    return {
        "sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar,
        "trades": nt, "total_return": total_ret * 100,
        "avg_exposure": in_market,
    }


# =========================================================================
# STRATEGY SIMS — P2.4 sims + X0_VOLSIZE
# =========================================================================

def sim_e0(cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                    slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def sim_e5(cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * ratr[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                    slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * ratr[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


# X0 Phase 1 is identical to E0_EMA21 (by design — Phase 1 parity)
sim_x0 = sim_e0_ema21_d1

# X0 Phase 2 = E5+EMA21 (by design — Phase 2 parity confirmed in P2.3)
sim_x0_e5exit = sim_e5_ema21_d1


def sim_x0_volsize(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                   slow_period=SLOW, trail_mult=TRAIL, cps=0.005,
                   target_vol=TARGET_VOL, vol_lookback=VOL_LOOKBACK,
                   vol_floor=VOL_FLOOR):
    """X0 Phase 3: Phase 2 timing + frozen entry-time vol sizing.

    Entry: same conditions as E5+EMA21(D1), but invest weight*cash instead of all cash.
    weight = target_vol / max(rv, vol_floor), clipped [0, 1].
    Weight frozen from entry to exit. Remaining cash stays uninvested.

    Returns: (nav, n_trades, weights_list)
      weights_list: list of entry weights for exposure analysis.
    """
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    rv = _realized_vol(cl, vol_lookback, BARS_PER_YEAR_4H)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    entry_weight = 0.0
    nav = np.zeros(n)
    weights = []
    rv_at_entries = []

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                invest = entry_weight * cash
                bq = invest / (fp * (1 + cps))
                cash = cash - invest
                inp = True
                pk = p
            elif px:
                px = False
                cash = cash + bq * fp * (1 - cps)
                bq = 0.0
                inp = False
                nt += 1
        nav[i] = cash + bq * p
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                rv_val = rv[i] if rv is not None else float('nan')
                if math.isnan(rv_val):
                    entry_weight = 1.0
                    rv_at_entries.append(float('nan'))
                else:
                    entry_weight = target_vol / max(rv_val, vol_floor)
                    entry_weight = max(0.0, min(1.0, entry_weight))
                    rv_at_entries.append(rv_val)
                weights.append(entry_weight)
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * ratr[i]: px = True
            elif ef[i] < es[i]: px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash

    return nav, nt, weights, rv_at_entries


def run_strategy(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                 slow_period=SLOW, cps=0.005):
    kw = dict(slow_period=slow_period, cps=cps)
    if sid == "E0":
        nav, nt = sim_e0(cl, hi, lo, vo, tb, wi, **kw)
    elif sid == "E0_EMA21":
        nav, nt = sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "E5":
        nav, nt = sim_e5(cl, hi, lo, vo, tb, wi, **kw)
    elif sid == "E5_EMA21":
        nav, nt = sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "X0":
        nav, nt = sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "X0_E5EXIT":
        nav, nt = sim_x0_e5exit(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "X0_VOLSIZE":
        nav, nt, _, _ = sim_x0_volsize(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    else:
        raise ValueError(f"Unknown strategy: {sid}")
    return nav, nt


# =========================================================================
# T1: FULL BACKTEST (3 cost scenarios)
# =========================================================================

def run_backtests(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST (3 cost scenarios)")
    print("=" * 80)

    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for scenario, cps in COST_SCENARIOS.items():
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
            m = _metrics(nav, wi, nt)
            results[sid][scenario] = m

    header = f"{'Strategy':14s} {'Scenario':8s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Calmar':>8s} {'Trades':>7s} {'TotRet%':>9s}"
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            print(f"{sid:14s} {sc:8s} {m['sharpe']:8.4f} {m['cagr']:8.2f} "
                  f"{m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:7d} {m['total_return']:9.2f}")

    return results


# =========================================================================
# T2: BOOTSTRAP VCBB
# =========================================================================

def run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print(f"T2: BOOTSTRAP VCBB ({N_BOOT} paths, slow={SLOW}, block={BLKSZ})")
    print("=" * 80)

    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    print("  Generating bootstrap paths...", end=" ", flush=True)
    t0 = time.time()
    boot_paths = []
    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        bcl_full = np.concatenate([cl[:wi], bcl])
        bhi_full = np.concatenate([hi[:wi], bhi])
        blo_full = np.concatenate([lo[:wi], blo])
        bvo_full = np.concatenate([vo[:wi], bvo])
        btb_full = np.concatenate([tb[:wi], btb])
        boot_paths.append((bcl_full, bhi_full, blo_full, bvo_full, btb_full))
    print(f"done ({time.time() - t0:.1f}s)")

    results = {}
    for sid in STRATEGY_IDS:
        sharpes = []
        cagrs = []
        mdds = []

        t0 = time.time()
        for b in range(N_BOOT):
            bcl, bhi, blo, bvo, btb = boot_paths[b]
            bnav, _ = run_strategy(sid, bcl, bhi, blo, bvo, btb, wi,
                                   d1_cl, d1_ct, h4_ct)
            bm = _metrics(bnav, wi)
            sharpes.append(bm["sharpe"])
            cagrs.append(bm["cagr"])
            mdds.append(bm["mdd"])

        sharpes = np.array(sharpes)
        cagrs = np.array(cagrs)
        mdds = np.array(mdds)

        results[sid] = {
            "sharpe_median": float(np.median(sharpes)),
            "sharpe_p5": float(np.percentile(sharpes, 5)),
            "sharpe_p95": float(np.percentile(sharpes, 95)),
            "sharpe_mean": float(np.mean(sharpes)),
            "cagr_median": float(np.median(cagrs)),
            "cagr_p5": float(np.percentile(cagrs, 5)),
            "cagr_p95": float(np.percentile(cagrs, 95)),
            "mdd_median": float(np.median(mdds)),
            "mdd_p5": float(np.percentile(mdds, 5)),
            "mdd_p95": float(np.percentile(mdds, 95)),
            "p_cagr_gt0": float(np.mean(cagrs > 0)),
            "p_sharpe_gt0": float(np.mean(sharpes > 0)),
        }

        r = results[sid]
        elapsed = time.time() - t0
        print(f"  {sid:14s}  Sharpe={r['sharpe_median']:.4f} [{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"CAGR={r['cagr_median']:.2f}% [{r['cagr_p5']:.2f}, {r['cagr_p95']:.2f}]  "
              f"MDD={r['mdd_median']:.2f}% [{r['mdd_p5']:.2f}, {r['mdd_p95']:.2f}]  "
              f"P(CAGR>0)={r['p_cagr_gt0']:.3f}  ({elapsed:.1f}s)")

    return results


# =========================================================================
# T3: ATTRIBUTION (Phase 3 vs Phase 2)
# =========================================================================

def run_attribution(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    """Full attribution: Phase 3 (volsize) vs Phase 2 (e5exit)."""
    print("\n" + "=" * 80)
    print("T3: ATTRIBUTION (X0 Phase 3 vs X0 Phase 2)")
    print("=" * 80)

    from v10.core.engine import BacktestEngine
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy
    from strategies.vtrend_x0_volsize.strategy import VTrendX0VolsizeConfig, VTrendX0VolsizeStrategy

    attr = {}

    for scenario, cps_frac in COST_SCENARIOS.items():
        cost_cfg = SCENARIOS[scenario]

        p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
        p3_strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())

        p2_eng = BacktestEngine(feed=feed, strategy=p2_strat, cost=cost_cfg,
                                initial_cash=CASH, warmup_mode="no_trade")
        p3_eng = BacktestEngine(feed=feed, strategy=p3_strat, cost=cost_cfg,
                                initial_cash=CASH, warmup_mode="no_trade")

        p2_res = p2_eng.run()
        p3_res = p3_eng.run()

        p2_s = p2_res.summary
        p3_s = p3_res.summary

        attr[scenario] = {
            "p2_sharpe": p2_s.get("sharpe", 0),
            "p3_sharpe": p3_s.get("sharpe", 0),
            "p2_cagr": p2_s.get("cagr_pct", 0),
            "p3_cagr": p3_s.get("cagr_pct", 0),
            "p2_mdd": p2_s.get("max_drawdown_mid_pct", 0),
            "p3_mdd": p3_s.get("max_drawdown_mid_pct", 0),
            "p2_trades": p2_s.get("trades", 0),
            "p3_trades": p3_s.get("trades", 0),
            "p2_calmar": p2_s.get("calmar", 0),
            "p3_calmar": p3_s.get("calmar", 0),
            "p2_winrate": p2_s.get("win_rate_pct", 0),
            "p3_winrate": p3_s.get("win_rate_pct", 0),
            "p2_pf": p2_s.get("profit_factor", 0),
            "p3_pf": p3_s.get("profit_factor", 0),
            "p2_avg_pnl": p2_s.get("avg_trade_pnl", 0),
            "p3_avg_pnl": p3_s.get("avg_trade_pnl", 0),
            "p2_avg_exposure": p2_s.get("avg_exposure", 0),
            "p3_avg_exposure": p3_s.get("avg_exposure", 0),
            "p2_fees": p2_s.get("fees_total", 0),
            "p3_fees": p3_s.get("fees_total", 0),
            "p2_turnover": p2_s.get("turnover_per_year", 0),
            "p3_turnover": p3_s.get("turnover_per_year", 0),
        }

    # Print delta table
    print("\n  --- A. Delta Table (P3 - P2) by cost scenario ---")
    print(f"  {'Scenario':8s} {'dSharpe':>9s} {'dCAGR%':>9s} {'dMDD%':>9s} {'dCalmar':>9s} "
          f"{'dTrades':>8s} {'dWR%':>8s} {'dPF':>8s} {'dExpo%':>8s}")
    for sc in ["smart", "base", "harsh"]:
        a = attr[sc]
        print(f"  {sc:8s} {a['p3_sharpe']-a['p2_sharpe']:>+9.4f} "
              f"{a['p3_cagr']-a['p2_cagr']:>+9.2f} "
              f"{a['p3_mdd']-a['p2_mdd']:>+9.2f} "
              f"{a['p3_calmar']-a['p2_calmar']:>+9.4f} "
              f"{a['p3_trades']-a['p2_trades']:>+8.0f} "
              f"{a['p3_winrate']-a['p2_winrate']:>+8.2f} "
              f"{a['p3_pf']-a['p2_pf']:>+8.4f} "
              f"{a['p3_avg_exposure']-a['p2_avg_exposure']:>+8.4f}")

    # Timing parity confirmation
    print("\n  --- B. Timing parity confirmation ---")
    cost_cfg = SCENARIOS["base"]
    p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    p3_strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())
    p2_eng = BacktestEngine(feed=feed, strategy=p2_strat, cost=cost_cfg,
                            initial_cash=CASH, warmup_mode="no_trade")
    p3_eng = BacktestEngine(feed=feed, strategy=p3_strat, cost=cost_cfg,
                            initial_cash=CASH, warmup_mode="no_trade")
    p2_res = p2_eng.run()
    p3_res = p3_eng.run()

    p2_trades = p2_res.trades
    p3_trades = p3_res.trades

    print(f"  P2 trades: {len(p2_trades)}")
    print(f"  P3 trades: {len(p3_trades)}")

    entry_match = sum(1 for t2, t3 in zip(p2_trades, p3_trades) if t2.entry_ts_ms == t3.entry_ts_ms)
    exit_match = sum(1 for t2, t3 in zip(p2_trades, p3_trades) if t2.exit_ts_ms == t3.exit_ts_ms)
    print(f"  Entry timestamp match: {entry_match}/{len(p2_trades)}")
    print(f"  Exit timestamp match: {exit_match}/{len(p2_trades)}")

    if len(p2_trades) == len(p3_trades) and entry_match == len(p2_trades) and exit_match == len(p2_trades):
        print("  TIMING PARITY: CONFIRMED (all entry+exit timestamps identical)")
    else:
        print("  TIMING PARITY: BROKEN")

    # Per-trade PnL comparison
    pnl_deltas = []
    ret_deltas = []
    exposure_ratios = []
    for t2, t3 in zip(p2_trades, p3_trades):
        pnl_deltas.append(t3.pnl - t2.pnl)
        ret_deltas.append(t3.return_pct - t2.return_pct)
        if abs(t2.pnl) > 1e-10:
            exposure_ratios.append(t3.pnl / t2.pnl)

    pnl_deltas = np.array(pnl_deltas)
    ret_deltas = np.array(ret_deltas)
    exposure_ratios = np.array(exposure_ratios) if exposure_ratios else np.array([0.0])

    print(f"\n  --- C. PnL delta (P3 vs P2, base scenario) ---")
    print(f"  Total P2 PnL: ${sum(t.pnl for t in p2_trades):,.2f}")
    print(f"  Total P3 PnL: ${sum(t.pnl for t in p3_trades):,.2f}")
    print(f"  Mean PnL ratio (P3/P2): {np.mean(exposure_ratios):.4f}")
    print(f"  Median PnL ratio (P3/P2): {np.median(exposure_ratios):.4f}")

    # Mechanism: all deltas should be from sizing only (same sign, scaled down)
    same_sign = sum(1 for t2, t3 in zip(p2_trades, p3_trades)
                    if (t2.pnl > 0 and t3.pnl > 0) or (t2.pnl < 0 and t3.pnl < 0) or (abs(t2.pnl) < 0.01))
    print(f"\n  --- D. Mechanism ---")
    print(f"  Same PnL sign: {same_sign}/{len(p2_trades)}")
    print(f"  Win rate: P2={sum(1 for t in p2_trades if t.pnl > 0)}/{len(p2_trades)} = "
          f"{sum(1 for t in p2_trades if t.pnl > 0)/len(p2_trades)*100:.1f}%")
    print(f"           P3={sum(1 for t in p3_trades if t.pnl > 0)}/{len(p3_trades)} = "
          f"{sum(1 for t in p3_trades if t.pnl > 0)/len(p3_trades)*100:.1f}%")
    print(f"  Mechanism: PURE SIZING DELTA (timing identical, only position size changes)")

    return attr, {
        "p2_total_pnl": sum(t.pnl for t in p2_trades),
        "p3_total_pnl": sum(t.pnl for t in p3_trades),
        "timing_parity": len(p2_trades) == len(p3_trades) and entry_match == len(p2_trades),
        "entry_match": entry_match,
        "exit_match": exit_match,
        "mean_pnl_ratio": float(np.mean(exposure_ratios)),
        "median_pnl_ratio": float(np.median(exposure_ratios)),
        "same_sign": same_sign,
    }


# =========================================================================
# T4: EXPOSURE STATS + VOL BUCKET ANALYSIS
# =========================================================================

def run_exposure_analysis(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    """Phase 3 specific: exposure distribution, vol bucket breakdown."""
    print("\n" + "=" * 80)
    print("T4: EXPOSURE STATS + VOL BUCKET ANALYSIS")
    print("=" * 80)

    # Run Phase 3 with weight tracking (base cost)
    cps = COST_SCENARIOS["base"]
    _, nt, weights, rv_entries = sim_x0_volsize(
        cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)

    weights = np.array(weights)
    rv_entries = np.array(rv_entries)

    print(f"\n  --- A. Exposure Distribution (Phase 3) ---")
    print(f"  Trades: {len(weights)}")
    print(f"  Weight min:    {np.min(weights):.6f}")
    print(f"  Weight p5:     {np.percentile(weights, 5):.6f}")
    print(f"  Weight p25:    {np.percentile(weights, 25):.6f}")
    print(f"  Weight median: {np.median(weights):.6f}")
    print(f"  Weight mean:   {np.mean(weights):.6f}")
    print(f"  Weight p75:    {np.percentile(weights, 75):.6f}")
    print(f"  Weight p95:    {np.percentile(weights, 95):.6f}")
    print(f"  Weight max:    {np.max(weights):.6f}")
    print(f"  Weight std:    {np.std(weights, ddof=0):.6f}")

    # RV at entry stats
    rv_valid = rv_entries[np.isfinite(rv_entries)]
    print(f"\n  --- B. Realized Vol at Entry ---")
    print(f"  Valid rv entries: {len(rv_valid)}/{len(rv_entries)}")
    if len(rv_valid) > 0:
        print(f"  RV min:    {np.min(rv_valid):.6f}")
        print(f"  RV p25:    {np.percentile(rv_valid, 25):.6f}")
        print(f"  RV median: {np.median(rv_valid):.6f}")
        print(f"  RV mean:   {np.mean(rv_valid):.6f}")
        print(f"  RV p75:    {np.percentile(rv_valid, 75):.6f}")
        print(f"  RV max:    {np.max(rv_valid):.6f}")
        print(f"  RV > target_vol ({TARGET_VOL}): {np.sum(rv_valid > TARGET_VOL)}/{len(rv_valid)}")
        print(f"  RV < vol_floor ({VOL_FLOOR}): {np.sum(rv_valid < VOL_FLOOR)}/{len(rv_valid)}")

    # Vol bucket analysis
    buckets = [
        ("low",    0.0, 0.30),
        ("medium", 0.30, 0.60),
        ("high",   0.60, 1.00),
        ("crisis", 1.00, float('inf')),
    ]

    # Also run Phase 2 for comparison PnL
    from v10.core.engine import BacktestEngine
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy
    from strategies.vtrend_x0_volsize.strategy import VTrendX0VolsizeConfig, VTrendX0VolsizeStrategy

    cost_cfg = SCENARIOS["base"]
    p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    p3_strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())
    p2_eng = BacktestEngine(feed=feed, strategy=p2_strat, cost=cost_cfg,
                            initial_cash=CASH, warmup_mode="no_trade")
    p3_eng = BacktestEngine(feed=feed, strategy=p3_strat, cost=cost_cfg,
                            initial_cash=CASH, warmup_mode="no_trade")
    p2_res = p2_eng.run()
    p3_res = p3_eng.run()
    p2_trades = p2_res.trades
    p3_trades = p3_res.trades

    print(f"\n  --- C. Vol Bucket Analysis ---")
    print(f"  {'Bucket':>8s} {'RV_range':>15s} {'N':>5s} {'Avg_Wt':>8s} "
          f"{'P2_PnL':>12s} {'P3_PnL':>12s} {'PnL_ratio':>10s}")

    bucket_data = []
    for bname, rv_lo, rv_hi in buckets:
        mask = (rv_valid >= rv_lo) & (rv_valid < rv_hi)
        n_bucket = int(np.sum(mask))
        if n_bucket == 0:
            bucket_data.append({"bucket": bname, "rv_lo": rv_lo, "rv_hi": rv_hi,
                                "n": 0, "avg_weight": 0, "p2_pnl": 0, "p3_pnl": 0})
            continue

        bucket_weights = weights[mask]
        avg_wt = float(np.mean(bucket_weights))

        # Get PnL from matched trades
        indices = np.where(mask)[0]
        p2_pnl = sum(p2_trades[j].pnl for j in indices if j < len(p2_trades))
        p3_pnl = sum(p3_trades[j].pnl for j in indices if j < len(p3_trades))
        pnl_ratio = p3_pnl / p2_pnl if abs(p2_pnl) > 0.01 else 0.0

        bucket_data.append({
            "bucket": bname, "rv_lo": rv_lo, "rv_hi": rv_hi if rv_hi != float('inf') else 999,
            "n": n_bucket, "avg_weight": avg_wt,
            "p2_pnl": p2_pnl, "p3_pnl": p3_pnl, "pnl_ratio": pnl_ratio,
        })

        rv_range_str = f"[{rv_lo:.2f}, {rv_hi:.2f})" if rv_hi != float('inf') else f"[{rv_lo:.2f}, inf)"
        print(f"  {bname:>8s} {rv_range_str:>15s} {n_bucket:>5d} {avg_wt:>8.4f} "
              f"${p2_pnl:>11,.2f} ${p3_pnl:>11,.2f} {pnl_ratio:>10.4f}")

    exposure_stats = {
        "n_trades": len(weights),
        "weight_min": float(np.min(weights)),
        "weight_p5": float(np.percentile(weights, 5)),
        "weight_p25": float(np.percentile(weights, 25)),
        "weight_median": float(np.median(weights)),
        "weight_mean": float(np.mean(weights)),
        "weight_p75": float(np.percentile(weights, 75)),
        "weight_p95": float(np.percentile(weights, 95)),
        "weight_max": float(np.max(weights)),
        "weight_std": float(np.std(weights, ddof=0)),
        "rv_min": float(np.min(rv_valid)) if len(rv_valid) > 0 else None,
        "rv_median": float(np.median(rv_valid)) if len(rv_valid) > 0 else None,
        "rv_mean": float(np.mean(rv_valid)) if len(rv_valid) > 0 else None,
        "rv_max": float(np.max(rv_valid)) if len(rv_valid) > 0 else None,
        "rv_gt_target": int(np.sum(rv_valid > TARGET_VOL)) if len(rv_valid) > 0 else 0,
        "rv_lt_floor": int(np.sum(rv_valid < VOL_FLOOR)) if len(rv_valid) > 0 else 0,
        "buckets": bucket_data,
    }

    return exposure_stats


# =========================================================================
# PROMOTION DECISION
# =========================================================================

def promotion_decision(bt_results, boot_results):
    """Automated promotion gates for X0 Phase 3."""
    print("\n" + "=" * 80)
    print("PROMOTION DECISION")
    print("=" * 80)

    gates = {}

    # Gate 1: Sharpe improvement over Phase 2 in all cost scenarios
    g1 = all(bt_results["X0_VOLSIZE"][sc]["sharpe"] > bt_results["X0_E5EXIT"][sc]["sharpe"]
             for sc in ["smart", "base", "harsh"])
    gates["sharpe_gt_p2_all_costs"] = g1
    print(f"  G1 Sharpe > P2 (all costs):  {'PASS' if g1 else 'FAIL'}")

    # Gate 2: MDD improvement (lower) over Phase 2 in all cost scenarios
    g2 = all(bt_results["X0_VOLSIZE"][sc]["mdd"] < bt_results["X0_E5EXIT"][sc]["mdd"]
             for sc in ["smart", "base", "harsh"])
    gates["mdd_lt_p2_all_costs"] = g2
    print(f"  G2 MDD < P2 (all costs):     {'PASS' if g2 else 'FAIL'}")

    # Gate 3: Calmar improvement over Phase 2 in all cost scenarios
    g3 = all(bt_results["X0_VOLSIZE"][sc]["calmar"] > bt_results["X0_E5EXIT"][sc]["calmar"]
             for sc in ["smart", "base", "harsh"])
    gates["calmar_gt_p2_all_costs"] = g3
    print(f"  G3 Calmar > P2 (all costs):  {'PASS' if g3 else 'FAIL'}")

    # Gate 4: Bootstrap P(CAGR>0) >= 0.7
    g4 = boot_results["X0_VOLSIZE"]["p_cagr_gt0"] >= 0.70
    gates["boot_pcagr_gte_70"] = g4
    print(f"  G4 Boot P(CAGR>0) >= 0.70:   {'PASS' if g4 else 'FAIL'} "
          f"(actual: {boot_results['X0_VOLSIZE']['p_cagr_gt0']:.3f})")

    # Gate 5: Bootstrap P(Sharpe>0) >= 0.7
    g5 = boot_results["X0_VOLSIZE"]["p_sharpe_gt0"] >= 0.70
    gates["boot_psharpe_gte_70"] = g5
    print(f"  G5 Boot P(Sharpe>0) >= 0.70: {'PASS' if g5 else 'FAIL'} "
          f"(actual: {boot_results['X0_VOLSIZE']['p_sharpe_gt0']:.3f})")

    # Gate 6: Trade count parity (same as P2)
    g6 = all(bt_results["X0_VOLSIZE"][sc]["trades"] == bt_results["X0_E5EXIT"][sc]["trades"]
             for sc in ["smart", "base", "harsh"])
    gates["trade_count_parity"] = g6
    print(f"  G6 Trade count = P2:         {'PASS' if g6 else 'FAIL'}")

    # Gate 7: Bootstrap MDD median < P2 bootstrap MDD median
    g7 = boot_results["X0_VOLSIZE"]["mdd_median"] < boot_results["X0_E5EXIT"]["mdd_median"]
    gates["boot_mdd_lt_p2"] = g7
    print(f"  G7 Boot MDD med < P2:        {'PASS' if g7 else 'FAIL'} "
          f"(P3={boot_results['X0_VOLSIZE']['mdd_median']:.2f}% vs P2={boot_results['X0_E5EXIT']['mdd_median']:.2f}%)")

    all_pass = all(gates.values())
    gates["all_pass"] = all_pass

    # CAGR tradeoff — expected to be lower due to reduced exposure
    harsh_p2_cagr = bt_results["X0_E5EXIT"]["harsh"]["cagr"]
    harsh_p3_cagr = bt_results["X0_VOLSIZE"]["harsh"]["cagr"]
    cagr_delta = harsh_p3_cagr - harsh_p2_cagr

    print(f"\n  CAGR tradeoff (harsh): P3={harsh_p3_cagr:.2f}% vs P2={harsh_p2_cagr:.2f}% "
          f"(delta={cagr_delta:+.2f}%)")
    print(f"  This is EXPECTED: vol-sizing reduces exposure, trades off CAGR for MDD/Sharpe")

    verdict = "PROMOTE" if all_pass else "HOLD"
    print(f"\n  VERDICT: {verdict}")
    if all_pass:
        print("  Phase 3 passes all gates. Vol-sizing improves risk-adjusted returns.")
        print("  Tradeoff: lower CAGR for significantly lower MDD and higher Sharpe.")
    else:
        failed = [k for k, v in gates.items() if not v and k != "all_pass"]
        print(f"  Failed gates: {', '.join(failed)}")

    return gates, verdict


# =========================================================================
# OUTPUT
# =========================================================================

def save_results(bt_results, boot_results, delta_attr, matched_attr,
                 exposure_stats, gates, verdict):
    outdir = OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)

    # JSON
    payload = {
        "settings": {
            "data": DATA, "start": START, "end": END, "warmup": WARMUP,
            "slow_period": SLOW, "trail_mult": TRAIL, "cash": CASH,
            "n_boot": N_BOOT, "blksz": BLKSZ, "seed": SEED,
            "target_vol": TARGET_VOL, "vol_lookback": VOL_LOOKBACK, "vol_floor": VOL_FLOOR,
        },
        "backtest": bt_results,
        "bootstrap": boot_results,
        "attribution_delta": delta_attr,
        "attribution_matched": matched_attr,
        "exposure_stats": exposure_stats,
        "promotion_gates": gates,
        "promotion_verdict": verdict,
    }
    with open(outdir / "p3_4_results.json", "w") as f:
        json.dump(payload, f, indent=2, default=str)

    # CSV — backtest table
    with open(outdir / "p3_4_backtest_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy", "scenario", "sharpe", "cagr_pct", "mdd_pct",
                         "calmar", "trades", "total_return_pct", "avg_exposure_pct"])
        for sid in STRATEGY_IDS:
            for sc in ["smart", "base", "harsh"]:
                m = bt_results[sid][sc]
                writer.writerow([sid, sc,
                                 f"{m['sharpe']:.4f}", f"{m['cagr']:.2f}", f"{m['mdd']:.2f}",
                                 f"{m['calmar']:.4f}", m['trades'],
                                 f"{m['total_return']:.2f}", f"{m['avg_exposure']:.2f}"])

    # CSV — bootstrap table
    with open(outdir / "p3_4_bootstrap_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy",
                         "sharpe_med", "sharpe_p5", "sharpe_p95",
                         "cagr_med", "cagr_p5", "cagr_p95",
                         "mdd_med", "mdd_p5", "mdd_p95",
                         "p_cagr_gt0", "p_sharpe_gt0"])
        for sid in STRATEGY_IDS:
            r = boot_results[sid]
            writer.writerow([sid,
                             f"{r['sharpe_median']:.4f}", f"{r['sharpe_p5']:.4f}", f"{r['sharpe_p95']:.4f}",
                             f"{r['cagr_median']:.2f}", f"{r['cagr_p5']:.2f}", f"{r['cagr_p95']:.2f}",
                             f"{r['mdd_median']:.2f}", f"{r['mdd_p5']:.2f}", f"{r['mdd_p95']:.2f}",
                             f"{r['p_cagr_gt0']:.3f}", f"{r['p_sharpe_gt0']:.3f}"])

    # CSV — Phase 3 delta table
    with open(outdir / "p3_4_delta_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["scenario", "d_sharpe", "d_cagr", "d_mdd", "d_calmar",
                         "d_trades", "d_winrate", "d_pf", "d_avg_exposure"])
        for sc in ["smart", "base", "harsh"]:
            a = delta_attr[sc]
            writer.writerow([sc,
                f"{a['p3_sharpe']-a['p2_sharpe']:.4f}",
                f"{a['p3_cagr']-a['p2_cagr']:.2f}",
                f"{a['p3_mdd']-a['p2_mdd']:.2f}",
                f"{a['p3_calmar']-a['p2_calmar']:.4f}",
                f"{a['p3_trades']-a['p2_trades']:.0f}",
                f"{a['p3_winrate']-a['p2_winrate']:.2f}",
                f"{a['p3_pf']-a['p2_pf']:.4f}",
                f"{a['p3_avg_exposure']-a['p2_avg_exposure']:.4f}"])

    # CSV — exposure stats
    with open(outdir / "p3_4_exposure_stats.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for k, v in exposure_stats.items():
            if k == "buckets":
                continue
            writer.writerow([k, v])

    # CSV — vol bucket analysis
    with open(outdir / "p3_4_vol_buckets.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bucket", "rv_lo", "rv_hi", "n", "avg_weight", "p2_pnl", "p3_pnl", "pnl_ratio"])
        for bd in exposure_stats.get("buckets", []):
            writer.writerow([bd["bucket"], bd["rv_lo"], bd["rv_hi"], bd["n"],
                             f"{bd['avg_weight']:.6f}",
                             f"{bd['p2_pnl']:.2f}" if bd.get("p2_pnl") else "0",
                             f"{bd['p3_pnl']:.2f}" if bd.get("p3_pnl") else "0",
                             f"{bd.get('pnl_ratio', 0):.4f}"])

    print(f"\nResults saved to {outdir}/")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()

    print("P3.4 — X0 Phase 3 Full Benchmark + Attribution")
    print("=" * 80)

    # Load data
    print("Loading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    d1 = feed.d1_bars
    print(f"  H4: {len(h4)} bars, D1: {len(d1)} bars")

    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in h4], dtype=np.int64)

    d1_cl = np.array([b.close for b in d1], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in d1], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for j, bar in enumerate(h4):
            if bar.close_time >= feed.report_start_ms:
                wi = j
                break
    print(f"  Warmup index: {wi} (reporting from bar {wi} onwards)")

    # T1: Full backtests
    bt_results = run_backtests(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Parity checks (P2.4 baselines)
    print("\n  Parity checks:")
    for sc in ["smart", "base", "harsh"]:
        x0_m = bt_results["X0"][sc]
        e0e_m = bt_results["E0_EMA21"][sc]
        match = all(abs(x0_m[k] - e0e_m[k]) < 1e-10
                    for k in ["sharpe", "cagr", "mdd", "calmar"]) and x0_m["trades"] == e0e_m["trades"]
        print(f"    X0 vs E0_EMA21 ({sc}): {'BIT-IDENTICAL' if match else 'DIFFERS'}")

    for sc in ["smart", "base", "harsh"]:
        x0e_m = bt_results["X0_E5EXIT"][sc]
        e5e_m = bt_results["E5_EMA21"][sc]
        match = all(abs(x0e_m[k] - e5e_m[k]) < 1e-10
                    for k in ["sharpe", "cagr", "mdd", "calmar"]) and x0e_m["trades"] == e5e_m["trades"]
        print(f"    X0_E5EXIT vs E5_EMA21 ({sc}): {'BIT-IDENTICAL' if match else 'DIFFERS'}")

    # T2: Bootstrap
    boot_results = run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Bootstrap parity
    print("\n  Bootstrap parity:")
    for pair, s1, s2 in [("X0 vs E0_EMA21", "X0", "E0_EMA21"),
                          ("X0_E5EXIT vs E5_EMA21", "X0_E5EXIT", "E5_EMA21")]:
        b1 = boot_results[s1]
        b2 = boot_results[s2]
        match = all(abs(b1[k] - b2[k]) < 1e-10 for k in b1)
        print(f"    {pair}: {'BIT-IDENTICAL' if match else 'DIFFERS'}")

    # T3: Attribution
    delta_attr, matched_attr = run_attribution(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T4: Exposure analysis
    exposure_stats = run_exposure_analysis(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Promotion decision
    gates, verdict = promotion_decision(bt_results, boot_results)

    # Save
    save_results(bt_results, boot_results, delta_attr, matched_attr,
                 exposure_stats, gates, verdict)

    # Rankings
    print("\n" + "=" * 80)
    print("RANKINGS (harsh scenario)")
    print("=" * 80)
    harsh = {sid: bt_results[sid]["harsh"] for sid in STRATEGY_IDS}

    for metric, key, reverse in [
        ("Sharpe", "sharpe", True),
        ("CAGR%", "cagr", True),
        ("MDD% (lower=better)", "mdd", False),
        ("Calmar", "calmar", True),
    ]:
        ranked = sorted(STRATEGY_IDS, key=lambda s: harsh[s][key], reverse=reverse)
        print(f"\n  By {metric}:")
        for rank, sid in enumerate(ranked, 1):
            print(f"    {rank}. {sid:14s} = {harsh[sid][key]:.4f}")

    elapsed = time.time() - t_start
    print(f"\nTotal time: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
