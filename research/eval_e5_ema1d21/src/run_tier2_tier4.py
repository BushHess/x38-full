#!/usr/bin/env python3
"""Tier 2 (T1-T7) + Tier 4 (8 trade anatomy) for E5_plus_EMA1D21.

Compares 3 strategies:
  E0              — baseline
  E0_plus_EMA1D21 — current PROMOTED strategy
  E5_plus_EMA1D21 — candidate

Tier 2 Tests:
  T1. Full backtest (3 scenarios)
  T2. Permutation test (10K shuffles)
  T3. Timescale robustness (16 TS)
  T4. Bootstrap VCBB (500 paths × 16 TS)
  T5. Postmortem (4 slow periods)
  T6. Param sensitivity (slow + trail sweeps)
  T7. Cost study (6 cost levels)

Tier 4 Techniques:
  1. Win rate / profit factor
  2. Win/loss streaks
  3. Holding time distribution
  4. MFE / MAE
  5. Exit reason profitability
  6. Payoff concentration
  7. Top-N jackknife
  8. Fat-tail statistics

NO modification of any production file.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import skew, kurtosis, jarque_bera

# ── Path setup ─────────────────────────────────────────────────────────────
_SCRIPT = Path(__file__).resolve()
_SRC = _SCRIPT.parent
_NAMESPACE = _SRC.parent
_REPO = _NAMESPACE.parent.parent

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

ARTIFACTS = _NAMESPACE / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

DATA = str(_REPO / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
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
DEFAULT_SLOW = 120

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
N_BOOT = 500
BLKSZ = 60
SEED = 42
N_PERM = 10_000

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}
CPS_HARSH = COST_SCENARIOS["harsh"]

STRATEGY_IDS = ["E0", "E0_plus_EMA1D21", "E5_plus_EMA1D21"]


# ═══════════════════════════════════════════════════════════════════════════
# FAST INDICATORS
# ═══════════════════════════════════════════════════════════════════════════

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high, low, close, period):
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
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


def _vdo(close, high, low, volume, taker_buy, fast, slow):
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


def _robust_atr(high, low, close, cap_q=0.90, cap_lb=100, period=20):
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))
    n = len(tr)
    from numpy.lib.stride_tricks import sliding_window_view
    tr_cap = np.full(n, np.nan)
    if cap_lb <= n:
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
    """Map D1 EMA regime to H4 bars."""
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


# ═══════════════════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════════════════

def _metrics(nav, wi, nt=0):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0, "calmar": 0.0, "trades": nt}
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
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar, "trades": nt}


# ═══════════════════════════════════════════════════════════════════════════
# SIM FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def sim_e0(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH,
           return_trades=False, **_kw):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    trades = [] if return_trades else None
    entry_bar = 0; entry_price = 0.0; exit_reason = ""
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                entry_bar = i; entry_price = fp * (1 + cps)
            elif px:
                px = False
                ep = fp * (1 - cps)
                pnl = bq * (ep - entry_price)
                ret_pct = (ep / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
                if return_trades:
                    trades.append({"entry_bar": entry_bar, "exit_bar": i,
                                   "entry_price": entry_price, "exit_price": ep,
                                   "pnl_usd": pnl, "return_pct": ret_pct,
                                   "exit_reason": exit_reason})
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True; exit_reason = "trail_stop"
            elif ef[i] < es[i]:
                px = True; exit_reason = "trend_exit"
    if inp and bq > 0:
        ep = cl[-1] * (1 - cps)
        pnl = bq * (ep - entry_price)
        ret_pct = (ep / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
        if return_trades:
            trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                           "entry_price": entry_price, "exit_price": ep,
                           "pnl_usd": pnl, "return_pct": ret_pct, "exit_reason": "end_of_data"})
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash
    if return_trades:
        return nav, nt, trades
    return nav, nt


def sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
                    slow_period=120, trail_mult=3.0, cps=CPS_HARSH, d1_ema_period=21,
                    return_trades=False, **_kw):
    """E0 + EMA(21) D1 regime filter — standard ATR trail."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_close_times, h4_close_times, d1_ema_period)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    trades = [] if return_trades else None
    entry_bar = 0; entry_price = 0.0; exit_reason = ""
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                entry_bar = i; entry_price = fp * (1 + cps)
            elif px:
                px = False
                ep = fp * (1 - cps)
                pnl = bq * (ep - entry_price)
                ret_pct = (ep / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
                if return_trades:
                    trades.append({"entry_bar": entry_bar, "exit_bar": i,
                                   "entry_price": entry_price, "exit_price": ep,
                                   "pnl_usd": pnl, "return_pct": ret_pct,
                                   "exit_reason": exit_reason})
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True; exit_reason = "trail_stop"
            elif ef[i] < es[i]:
                px = True; exit_reason = "trend_exit"
    if inp and bq > 0:
        ep = cl[-1] * (1 - cps)
        pnl = bq * (ep - entry_price)
        ret_pct = (ep / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
        if return_trades:
            trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                           "entry_price": entry_price, "exit_price": ep,
                           "pnl_usd": pnl, "return_pct": ret_pct, "exit_reason": "end_of_data"})
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash
    if return_trades:
        return nav, nt, trades
    return nav, nt


def sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
                    slow_period=120, trail_mult=3.0, cps=CPS_HARSH, d1_ema_period=21,
                    return_trades=False, **_kw):
    """E5 + EMA(21) D1 regime filter — robust ATR trail."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_close_times, h4_close_times, d1_ema_period)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)
    trades = [] if return_trades else None
    entry_bar = 0; entry_price = 0.0; exit_reason = ""
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                entry_bar = i; entry_price = fp * (1 + cps)
            elif px:
                px = False
                ep = fp * (1 - cps)
                pnl = bq * (ep - entry_price)
                ret_pct = (ep / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
                if return_trades:
                    trades.append({"entry_bar": entry_bar, "exit_bar": i,
                                   "entry_price": entry_price, "exit_price": ep,
                                   "pnl_usd": pnl, "return_pct": ret_pct,
                                   "exit_reason": exit_reason})
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * ratr[i]
            if p < ts:
                px = True; exit_reason = "trail_stop"
            elif ef[i] < es[i]:
                px = True; exit_reason = "trend_exit"
    if inp and bq > 0:
        ep = cl[-1] * (1 - cps)
        pnl = bq * (ep - entry_price)
        ret_pct = (ep / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
        if return_trades:
            trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                           "entry_price": entry_price, "exit_price": ep,
                           "pnl_usd": pnl, "return_pct": ret_pct, "exit_reason": "end_of_data"})
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash
    if return_trades:
        return nav, nt, trades
    return nav, nt


def run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=120, cps=CPS_HARSH,
                 trail_mult=3.0, d1_cl=None, d1_close_times=None, h4_close_times=None,
                 return_trades=False):
    kw = dict(slow_period=slow_period, trail_mult=trail_mult, cps=cps,
              return_trades=return_trades)
    if sid == "E0":
        return sim_e0(cl, hi, lo, vo, tb, wi, **kw)
    elif sid == "E0_plus_EMA1D21":
        return sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times, **kw)
    elif sid == "E5_plus_EMA1D21":
        return sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times, **kw)
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2: T1-T7
# ═══════════════════════════════════════════════════════════════════════════

def test_t1_backtest(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T1: FULL BACKTEST (3 scenarios)")
    print("=" * 72)
    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for scenario, cps in COST_SCENARIOS.items():
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, cps=cps,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid][scenario] = m
    print(f"\n{'Strategy':22s} {'Sc':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Calmar':>8s} {'Tr':>5s}")
    print("-" * 72)
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            print(f"{sid:22s} {sc:6s} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:5d}")
    return results


def test_t2_permutation(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print(f"T2: PERMUTATION TEST ({N_PERM} shuffles)")
    print("=" * 72)
    rng = np.random.default_rng(SEED)
    n = len(cl)
    results = {}
    for sid in STRATEGY_IDS:
        nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                               d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        real_sharpe = _metrics(nav, wi, nt)["sharpe"]
        log_rets = np.log(cl[1:] / cl[:-1])
        count_above = 0
        for _ in range(N_PERM):
            perm_rets = rng.permutation(log_rets)
            perm_cl = np.zeros(n)
            perm_cl[0] = cl[0]
            perm_cl[1:] = cl[0] * np.exp(np.cumsum(perm_rets))
            perm_hi = perm_cl * (hi / np.maximum(cl, 1e-12))
            perm_lo = perm_cl * (lo / np.maximum(cl, 1e-12))
            perm_nav, _ = run_strategy(sid, perm_cl, perm_hi, perm_lo, vo, tb, wi,
                                       d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            perm_m = _metrics(perm_nav, wi)
            if perm_m["sharpe"] >= real_sharpe:
                count_above += 1
        p_val = (count_above + 1) / (N_PERM + 1)
        results[sid] = {"real_sharpe": real_sharpe, "p_value": p_val, "count_above": count_above}
        print(f"  {sid:22s}  Sharpe={real_sharpe:.4f}  p={p_val:.6f}  (count={count_above})")
    return results


def test_t3_timescale(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T3: TIMESCALE ROBUSTNESS (16 TS)")
    print("=" * 72)
    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for sp in SLOW_PERIODS:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=sp,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid][sp] = m
    print(f"\n{'SP':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>22s}", end="")
    print()
    print("-" * 80)
    for sp in SLOW_PERIODS:
        print(f"{sp:5d}", end="")
        for sid in STRATEGY_IDS:
            print(f"  {results[sid][sp]['sharpe']:22.4f}", end="")
        print()
    # Count positive Sharpe
    print("\n  Positive Sharpe count:")
    for sid in STRATEGY_IDS:
        pos = sum(1 for sp in SLOW_PERIODS if results[sid][sp]["sharpe"] > 0)
        print(f"  {sid:22s}: {pos}/16")
    # E5_plus vs E0_plus wins
    wins_sharpe = sum(1 for sp in SLOW_PERIODS
                      if results["E5_plus_EMA1D21"][sp]["sharpe"] > results["E0_plus_EMA1D21"][sp]["sharpe"])
    wins_cagr = sum(1 for sp in SLOW_PERIODS
                    if results["E5_plus_EMA1D21"][sp]["cagr"] > results["E0_plus_EMA1D21"][sp]["cagr"])
    wins_mdd = sum(1 for sp in SLOW_PERIODS
                   if results["E5_plus_EMA1D21"][sp]["mdd"] < results["E0_plus_EMA1D21"][sp]["mdd"])
    print(f"\n  E5_plus vs E0_plus wins: Sharpe {wins_sharpe}/16, CAGR {wins_cagr}/16, MDD {wins_mdd}/16")
    return results


def test_t4_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print(f"T4: BOOTSTRAP VCBB ({N_BOOT} paths × {len(SLOW_PERIODS)} TS)")
    print("=" * 72)
    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)
    # Pre-generate bootstrap paths
    print("  Generating bootstrap paths...")
    boot_paths = []
    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        boot_paths.append((
            np.concatenate([cl[:wi], bcl]),
            np.concatenate([hi[:wi], bhi]),
            np.concatenate([lo[:wi], blo]),
            np.concatenate([vo[:wi], bvo]),
            np.concatenate([tb[:wi], btb]),
        ))
    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        t0 = time.time()
        for sp in SLOW_PERIODS:
            sharpes = []; cagrs = []; mdds = []
            for b in range(N_BOOT):
                bcl, bhi, blo, bvo, btb = boot_paths[b]
                bnav, _ = run_strategy(sid, bcl, bhi, blo, bvo, btb, wi, slow_period=sp,
                                       d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
                bm = _metrics(bnav, wi)
                sharpes.append(bm["sharpe"]); cagrs.append(bm["cagr"]); mdds.append(bm["mdd"])
            results[sid][sp] = {
                "sharpe_median": float(np.median(sharpes)),
                "sharpe_mean": float(np.mean(sharpes)),
                "cagr_median": float(np.median(cagrs)),
                "mdd_median": float(np.median(mdds)),
                "p_cagr_gt0": float(np.mean(np.array(cagrs) > 0)),
            }
        elapsed = time.time() - t0
        sp120 = results[sid].get(120, {})
        print(f"  {sid:22s} ({elapsed:.1f}s)  SP=120: Sharpe_med={sp120.get('sharpe_median',0):.4f}  "
              f"CAGR_med={sp120.get('cagr_median',0):.2f}%  MDD_med={sp120.get('mdd_median',0):.2f}%  "
              f"P(CAGR>0)={sp120.get('p_cagr_gt0',0):.3f}")
    # Paired bootstrap wins
    print("\n  Paired Bootstrap Wins (E5_plus vs E0_plus):")
    sharpe_w = cagr_w = mdd_w = 0
    for sp in SLOW_PERIODS:
        if results["E5_plus_EMA1D21"][sp]["sharpe_median"] > results["E0_plus_EMA1D21"][sp]["sharpe_median"]:
            sharpe_w += 1
        if results["E5_plus_EMA1D21"][sp]["cagr_median"] > results["E0_plus_EMA1D21"][sp]["cagr_median"]:
            cagr_w += 1
        if results["E5_plus_EMA1D21"][sp]["mdd_median"] < results["E0_plus_EMA1D21"][sp]["mdd_median"]:
            mdd_w += 1
    print(f"  Sharpe {sharpe_w}/16  CAGR {cagr_w}/16  MDD {mdd_w}/16")
    return results


def test_t5_postmortem(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T5: POSTMORTEM / FAILURE ANALYSIS")
    print("=" * 72)
    test_periods = [60, 120, 200, 360]
    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for sp in test_periods:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=sp,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            navs = nav[wi:]
            peak = np.maximum.accumulate(navs)
            dd = 1.0 - navs / peak
            in_dd = False; episodes = []
            for j in range(len(dd)):
                if dd[j] > 0.20 and not in_dd:
                    in_dd = True; dd_start = j
                elif dd[j] < 0.01 and in_dd:
                    in_dd = False
                    episodes.append({"max_dd": float(np.max(dd[dd_start:j+1]))})
            if in_dd:
                episodes.append({"max_dd": float(np.max(dd[dd_start:]))})
            results[sid][sp] = {**m, "dd_episodes_gt20": len(episodes)}
    print(f"\n{'Strategy':22s} {'SP':>5s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'DD>20%':>8s} {'Tr':>5s}")
    print("-" * 72)
    for sid in STRATEGY_IDS:
        for sp in test_periods:
            m = results[sid][sp]
            print(f"{sid:22s} {sp:5d} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} {m['dd_episodes_gt20']:8d} {m['trades']:5d}")
    return results


def test_t6_sensitivity(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T6: PARAM SENSITIVITY")
    print("=" * 72)
    slow_sweep = [60, 72, 84, 96, 108, 120, 144, 168, 200, 240]
    trail_sweep = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {"slow": {}, "trail": {}}
        for sp in slow_sweep:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=sp,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            results[sid]["slow"][sp] = _metrics(nav, wi, nt)
        for tm in trail_sweep:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, trail_mult=tm,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            results[sid]["trail"][tm] = _metrics(nav, wi, nt)
    # Print slow sweep
    print(f"\n  Slow Sweep (Sharpe):")
    print(f"  {'SP':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>22s}", end="")
    print()
    for sp in slow_sweep:
        print(f"  {sp:5d}", end="")
        for sid in STRATEGY_IDS:
            print(f"  {results[sid]['slow'][sp]['sharpe']:22.4f}", end="")
        print()
    # Print trail sweep
    print(f"\n  Trail Sweep (Sharpe):")
    print(f"  {'Trail':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>22s}", end="")
    print()
    for tm in trail_sweep:
        print(f"  {tm:5.1f}", end="")
        for sid in STRATEGY_IDS:
            print(f"  {results[sid]['trail'][tm]['sharpe']:22.4f}", end="")
        print()
    return results


def test_t7_cost(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T7: COST STUDY (6 levels)")
    print("=" * 72)
    cost_levels_bps = [0, 10, 25, 50, 75, 100]
    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for bps in cost_levels_bps:
            cps = bps / 10_000.0
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, cps=cps,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            results[sid][bps] = _metrics(nav, wi, nt)
    print(f"\n  {'BPS':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>22s}", end="")
    print()
    for bps in cost_levels_bps:
        print(f"  {bps:5d}", end="")
        for sid in STRATEGY_IDS:
            print(f"  {results[sid][bps]['sharpe']:22.4f}", end="")
        print()
    # E5_plus beats E0_plus at all cost levels?
    all_win = all(results["E5_plus_EMA1D21"][b]["sharpe"] > results["E0_plus_EMA1D21"][b]["sharpe"]
                  for b in cost_levels_bps)
    print(f"\n  E5_plus beats E0_plus at ALL cost levels: {all_win}")
    return results


# ═══════════════════════════════════════════════════════════════════════════
# TIER 4: 8 TRADE ANATOMY TECHNIQUES
# ═══════════════════════════════════════════════════════════════════════════

def tier4_trade_anatomy(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_open_times):
    print("\n" + "=" * 72)
    print("TIER 4: 8-TECHNIQUE TRADE ANATOMY")
    print("=" * 72)
    results = {}
    for sid in STRATEGY_IDS:
        nav, nt, trades = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                                       d1_cl=d1_cl, d1_close_times=d1_ct,
                                       h4_close_times=h4_ct, return_trades=True)
        if not trades:
            print(f"  {sid}: No trades")
            results[sid] = {}
            continue
        df = pd.DataFrame(trades)
        m = _metrics(nav, wi, nt)
        navs = nav[wi:]
        n_bars = len(navs) - 1
        bt_years = n_bars / (6.0 * 365.25)
        print(f"\n  === {sid} ({len(df)} trades) ===")
        print(f"  Sharpe={m['sharpe']:.4f}  CAGR={m['cagr']:.2f}%  MDD={m['mdd']:.2f}%")

        r = {}

        # T4.1: Win rate / profit factor
        wins = df[df["pnl_usd"] > 0]
        losses = df[df["pnl_usd"] <= 0]
        win_rate = len(wins) / len(df) * 100
        avg_win = wins["return_pct"].mean() if len(wins) > 0 else 0.0
        avg_loss = losses["return_pct"].mean() if len(losses) > 0 else 0.0
        gross_win = wins["pnl_usd"].sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses["pnl_usd"].sum()) if len(losses) > 0 else 0.0
        pf = gross_win / gross_loss if gross_loss > 0 else 99.0
        expectancy = df["return_pct"].mean()
        r["t1_win_rate_pf"] = {
            "n_trades": len(df), "win_rate_pct": round(win_rate, 2),
            "avg_win_pct": round(avg_win, 2), "avg_loss_pct": round(avg_loss, 2),
            "wl_ratio": round(abs(avg_win / avg_loss) if avg_loss != 0 else 99.0, 3),
            "profit_factor": round(pf, 3), "expectancy_pct": round(expectancy, 3),
        }
        print(f"  T4.1: WR={win_rate:.1f}% PF={pf:.3f} E={expectancy:.3f}%")

        # T4.2: Streaks
        is_win = (df["pnl_usd"] > 0).values
        streaks_w = []; streaks_l = []; cur = 0; cur_type = None
        for w in is_win:
            if w == cur_type:
                cur += 1
            else:
                if cur_type is not None:
                    (streaks_w if cur_type else streaks_l).append(cur)
                cur = 1; cur_type = w
        if cur_type is not None:
            (streaks_w if cur_type else streaks_l).append(cur)
        r["t2_streaks"] = {
            "max_win_streak": max(streaks_w) if streaks_w else 0,
            "max_loss_streak": max(streaks_l) if streaks_l else 0,
            "avg_win_streak": round(np.mean(streaks_w), 2) if streaks_w else 0,
            "avg_loss_streak": round(np.mean(streaks_l), 2) if streaks_l else 0,
        }
        print(f"  T4.2: MaxWS={r['t2_streaks']['max_win_streak']} MaxLS={r['t2_streaks']['max_loss_streak']}")

        # T4.3: Holding time
        bars_held = df["exit_bar"] - df["entry_bar"]
        days_held = bars_held * 4.0 / 24.0  # H4 bars to days
        r["t3_holding_time"] = {
            "mean_days": round(float(days_held.mean()), 2),
            "median_days": round(float(days_held.median()), 2),
            "min_days": round(float(days_held.min()), 2),
            "max_days": round(float(days_held.max()), 2),
            "p10_days": round(float(np.percentile(days_held, 10)), 2),
            "p90_days": round(float(np.percentile(days_held, 90)), 2),
        }
        print(f"  T4.3: Mean={r['t3_holding_time']['mean_days']:.1f}d "
              f"Med={r['t3_holding_time']['median_days']:.1f}d")

        # T4.4: MFE / MAE
        mfe_list = []; mae_list = []
        for _, row in df.iterrows():
            eb = int(row["entry_bar"]); xb = int(row["exit_bar"])
            ep = row["entry_price"]
            if eb >= xb or ep < 1e-12:
                mfe_list.append(0.0); mae_list.append(0.0)
                continue
            max_h = hi[eb:xb + 1].max()
            min_l = lo[eb:xb + 1].min()
            mfe_list.append(max(0, (max_h - ep) / ep * 100))
            mae_list.append(max(0, (ep - min_l) / ep * 100))
        df["mfe"] = mfe_list; df["mae"] = mae_list
        r["t4_mfe_mae"] = {
            "mfe_mean_pct": round(float(df["mfe"].mean()), 2),
            "mfe_median_pct": round(float(df["mfe"].median()), 2),
            "mae_mean_pct": round(float(df["mae"].mean()), 2),
            "mae_median_pct": round(float(df["mae"].median()), 2),
            "mfe_mae_ratio": round(float(df["mfe"].mean() / df["mae"].mean()), 3) if df["mae"].mean() > 0 else 99.0,
        }
        print(f"  T4.4: MFE_med={r['t4_mfe_mae']['mfe_median_pct']:.2f}% "
              f"MAE_med={r['t4_mfe_mae']['mae_median_pct']:.2f}% "
              f"ratio={r['t4_mfe_mae']['mfe_mae_ratio']:.3f}")

        # T4.5: Exit reason profitability
        exit_groups = df.groupby("exit_reason")
        r["t5_exit_reason"] = {}
        for reason, grp in exit_groups:
            wr = (grp["pnl_usd"] > 0).mean() * 100
            r["t5_exit_reason"][reason] = {
                "count": len(grp), "win_rate_pct": round(wr, 1),
                "avg_return_pct": round(grp["return_pct"].mean(), 3),
                "total_pnl": round(grp["pnl_usd"].sum(), 2),
            }
            print(f"  T4.5: {reason}: n={len(grp)} WR={wr:.1f}% "
                  f"avg_ret={grp['return_pct'].mean():.3f}%")

        # T4.6: Payoff concentration
        sorted_pnl = df["pnl_usd"].sort_values(ascending=False)
        total_pnl = df["pnl_usd"].sum()
        abs_total = abs(total_pnl)
        n_t = len(df)
        top5_pct = sorted_pnl.iloc[:max(1, n_t // 20)].sum() / abs_total * 100 if abs_total > 0 else 0
        top10_pct = sorted_pnl.iloc[:max(1, n_t // 10)].sum() / abs_total * 100 if abs_total > 0 else 0
        hhi = float(((df["pnl_usd"] / abs_total) ** 2).sum()) if abs_total > 0 else 0
        sorted_abs = np.sort(np.abs(df["pnl_usd"].values))
        cum = np.cumsum(sorted_abs)
        gini = float(1 - 2 * cum.sum() / (n_t * cum[-1])) if cum[-1] > 0 else 0
        r["t6_payoff_concentration"] = {
            "top5pct_contribution": round(top5_pct, 1),
            "top10pct_contribution": round(top10_pct, 1),
            "herfindahl": round(hhi, 6),
            "gini": round(gini, 4),
        }
        print(f"  T4.6: Top5%={top5_pct:.1f}% Top10%={top10_pct:.1f}% Gini={gini:.4f}")

        # T4.7: Top-N jackknife
        sorted_idx = df["pnl_usd"].sort_values(ascending=False).index
        tpy = len(df) / bt_years
        base_rets = df["return_pct"].values
        base_sharpe_t = _trade_sharpe(base_rets, tpy)
        base_cagr_t = _safe_cagr(total_pnl, CASH, bt_years)
        r["t7_jackknife"] = {"base_sharpe": base_sharpe_t, "base_cagr_pct": base_cagr_t * 100}
        print(f"  T4.7: Jackknife (base Sharpe={base_sharpe_t:.4f}, CAGR={base_cagr_t*100:.2f}%)")
        for k in [1, 3, 5, 10]:
            if k >= len(df):
                continue
            rem = df.drop(sorted_idx[:k])
            tpy_r = len(rem) / bt_years
            sh = _trade_sharpe(rem["return_pct"].values, tpy_r)
            cg = _safe_cagr(rem["pnl_usd"].sum(), CASH, bt_years)
            sh_d = (sh - base_sharpe_t) / abs(base_sharpe_t) * 100 if base_sharpe_t != 0 else 0
            r["t7_jackknife"][f"drop_top{k}"] = {
                "sharpe": round(sh, 4), "cagr_pct": round(cg * 100, 2),
                "sharpe_delta_pct": round(sh_d, 1),
            }
            print(f"    -top{k}: Sharpe={sh:.4f} (Δ={sh_d:+.1f}%)  CAGR={cg*100:.2f}%")

        # T4.8: Fat-tail statistics
        rets = df["return_pct"].values
        r["t8_fat_tail"] = {
            "skewness": round(float(skew(rets)), 4),
            "excess_kurtosis": round(float(kurtosis(rets)), 4),
            "jarque_bera_stat": round(float(jarque_bera(rets).statistic), 4),
            "jarque_bera_p": round(float(jarque_bera(rets).pvalue), 6),
            "p10_pct": round(float(np.percentile(rets, 10)), 3),
            "p90_pct": round(float(np.percentile(rets, 90)), 3),
        }
        print(f"  T4.8: Skew={r['t8_fat_tail']['skewness']:.4f} "
              f"Kurt={r['t8_fat_tail']['excess_kurtosis']:.4f} "
              f"JB_p={r['t8_fat_tail']['jarque_bera_p']:.6f}")

        results[sid] = r
    return results


def _trade_sharpe(returns, trades_per_year):
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    std = np.std(arr, ddof=0)
    if std < 1e-12:
        return 0.0
    return np.mean(arr) / std * np.sqrt(trades_per_year)


def _safe_cagr(total_pnl, nav0, years):
    final = nav0 + total_pnl
    if final <= 0:
        return -1.0
    return (final / nav0) ** (1.0 / years) - 1.0


# ═══════════════════════════════════════════════════════════════════════════
# JSON SERIALIZER
# ═══════════════════════════════════════════════════════════════════════════

def _json_default(obj):
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if isinstance(obj, np.bool_): return bool(obj)
    return str(obj)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("E5_plus_EMA1D21: Tier 2 (T1-T7) + Tier 4 (8 techniques)")
    print("=" * 72)
    t0_total = time.time()

    print("Loading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    h4 = feed.h4_bars
    d1 = feed.d1_bars

    n = len(h4)
    cl = np.array([b.close for b in h4], dtype=np.float64)
    hi = np.array([b.high for b in h4], dtype=np.float64)
    lo = np.array([b.low for b in h4], dtype=np.float64)
    vo = np.array([b.volume for b in h4], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in h4], dtype=np.int64)
    h4_ot = np.array([b.open_time for b in h4], dtype=np.int64)
    d1_cl = np.array([b.close for b in d1], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in d1], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    print(f"  H4 bars: {n}  D1 bars: {len(d1)}  Warmup idx: {wi}")

    args = (cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    all_results = {}

    # T1: Backtest
    t0 = time.time()
    all_results["T1"] = test_t1_backtest(*args)
    print(f"  T1 done in {time.time()-t0:.1f}s")

    # T2: Permutation (slowest)
    t0 = time.time()
    all_results["T2"] = test_t2_permutation(*args)
    print(f"  T2 done in {time.time()-t0:.1f}s")

    # T3: Timescale
    t0 = time.time()
    all_results["T3"] = test_t3_timescale(*args)
    print(f"  T3 done in {time.time()-t0:.1f}s")

    # T4: Bootstrap
    t0 = time.time()
    all_results["T4"] = test_t4_bootstrap(*args)
    print(f"  T4 done in {time.time()-t0:.1f}s")

    # T5: Postmortem
    t0 = time.time()
    all_results["T5"] = test_t5_postmortem(*args)
    print(f"  T5 done in {time.time()-t0:.1f}s")

    # T6: Sensitivity
    t0 = time.time()
    all_results["T6"] = test_t6_sensitivity(*args)
    print(f"  T6 done in {time.time()-t0:.1f}s")

    # T7: Cost
    t0 = time.time()
    all_results["T7"] = test_t7_cost(*args)
    print(f"  T7 done in {time.time()-t0:.1f}s")

    # Tier 4: Trade anatomy
    t0 = time.time()
    all_results["Tier4"] = tier4_trade_anatomy(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_ot)
    print(f"  Tier4 done in {time.time()-t0:.1f}s")

    # Save
    elapsed = time.time() - t0_total
    all_results["_meta"] = {
        "elapsed_s": round(elapsed, 1),
        "date": "2026-03-06",
        "strategies": STRATEGY_IDS,
    }

    out_path = ARTIFACTS / "tier2_tier4_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=_json_default)
    print(f"\nSaved: {out_path}")
    print(f"Total elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
