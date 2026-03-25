#!/usr/bin/env python3
"""PARITY EVALUATION — X-Series (X0, X2, X6) vs E0 baseline.

Runs ALL research-level tests on 4 strategies:
  E0           = vtrend (baseline, no D1 regime)
  X0           = E0 + D1 EMA(21) regime filter (= E0+EMA1D21)
  X2           = X0 + adaptive trail (tight/mid/wide)
  X6           = X2 + breakeven floor (BE floor above gain_tier1)

Tests per strategy (Tier 2):
  T1.  Full backtest (3 scenarios: smart, base, harsh)
  T2.  Permutation test (10K shuffles)
  T3.  Timescale robustness (16 TS)
  T4.  Bootstrap VCBB (500 paths x 16 TS)
  T5.  Postmortem / failure analysis (4 slow_periods)
  T6.  Param sensitivity (1D sweeps: slow, trail)
  T7.  Cost study (timescale x cost)

Plus Tier 3 comparative analysis:
  T8.  Calendar slice
  T9.  Rolling window stability
  T10. Start-date sensitivity
  T11. Paired bootstrap Sharpe diff + Holm correction
  T12. Signal concordance

Plus Tier 4 trade anatomy (from vectorized sim):
  T13. Win rate / avg W/L / PF
  T14. Holding time distribution
  T15. Payoff concentration (Gini, HHI)
  T16. Top-N jackknife
  T17. Fat-tail statistics
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import lfilter
from scipy.stats import binomtest, skew, kurtosis, jarque_bera

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb


# ═══════════════════════════════════════════════════════════════════════════
# FAST INDICATORS (C-level via scipy.signal.lfilter)
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

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

# X2/X6 adaptive trail defaults
TRAIL_TIGHT = 3.0
TRAIL_MID = 4.0
TRAIL_WIDE = 5.0
GAIN_TIER1 = 0.05
GAIN_TIER2 = 0.15

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
DEFAULT_SLOW = 120

N_BOOT = 500
BLKSZ = 60
SEED = 42

N_PERM = 1_000

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}
CPS_HARSH = COST_SCENARIOS["harsh"]

OUTDIR = Path(__file__).resolve().parent / "results" / "parity_eval_x"

STRATEGY_IDS = ["E0", "X0", "X2", "X6"]


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
# STRATEGY SIMS (vectorized)
# ═══════════════════════════════════════════════════════════════════════════

def sim_e0(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH):
    """VTREND E0 — baseline, no D1 regime."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
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
            if ef[i] > es[i] and vd[i] > VDO_THR:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt


def sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
           slow_period=120, trail_mult=3.0, cps=CPS_HARSH, d1_ema_period=21):
    """X0 = E0 + D1 EMA(21) regime filter (= E0+EMA1D21)."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # D1 regime
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

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0
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
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            ts = pk - trail_mult * at[i]
            if p < ts:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt


def sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
           slow_period=120, cps=CPS_HARSH, d1_ema_period=21,
           trail_tight=TRAIL_TIGHT, trail_mid=TRAIL_MID, trail_wide=TRAIL_WIDE,
           gain_tier1=GAIN_TIER1, gain_tier2=GAIN_TIER2):
    """X2 = X0 + adaptive trail (tight/mid/wide based on unrealized gain).

    Returns (nav, trades, trade_list) where trade_list has per-trade details.
    """
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # D1 regime
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

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0; entry_px = 0.0
    nav = np.zeros(n)
    trades = []  # per-trade records

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp
                bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px:
                px = False
                exit_px = fp
                ret_pct = (exit_px / entry_px - 1.0) * 100 if entry_px > 0 else 0.0
                pnl = bq * fp * (1 - cps) - (bq * entry_px * (1 + cps))
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                                "entry_price": entry_px, "exit_price": exit_px,
                                "return_pct": ret_pct, "pnl_usd": pnl,
                                "exit_reason": exit_reason})
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
                entry_bar = i
        else:
            pk = max(pk, p)
            # Adaptive trail
            unrealized = (p - entry_px) / entry_px if entry_px > 0 else 0.0
            if unrealized < gain_tier1:
                tm = trail_tight
            elif unrealized < gain_tier2:
                tm = trail_mid
            else:
                tm = trail_wide
            ts = pk - tm * at[i]
            if p < ts:
                px = True
                exit_reason = "trail_stop"
            elif ef[i] < es[i]:
                px = True
                exit_reason = "trend_exit"

    if inp and bq > 0:
        exit_px = cl[-1]
        ret_pct = (exit_px / entry_px - 1.0) * 100 if entry_px > 0 else 0.0
        pnl = bq * cl[-1] * (1 - cps) - (bq * entry_px * (1 + cps))
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                        "entry_price": entry_px, "exit_price": exit_px,
                        "return_pct": ret_pct, "pnl_usd": pnl,
                        "exit_reason": "end_of_data"})
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt, trades


def sim_x6(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
           slow_period=120, cps=CPS_HARSH, d1_ema_period=21,
           trail_tight=TRAIL_TIGHT, trail_mid=TRAIL_MID, trail_wide=TRAIL_WIDE,
           gain_tier1=GAIN_TIER1, gain_tier2=GAIN_TIER2):
    """X6 = X2 + breakeven floor (BE floor active when gain >= gain_tier1).

    Returns (nav, trades, trade_list).
    """
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # D1 regime
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

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0
    pk = 0.0; entry_px = 0.0
    nav = np.zeros(n)
    trades = []

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                entry_px = fp
                bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
            elif px:
                px = False
                exit_px = fp
                ret_pct = (exit_px / entry_px - 1.0) * 100 if entry_px > 0 else 0.0
                pnl = bq * fp * (1 - cps) - (bq * entry_px * (1 + cps))
                trades.append({"entry_bar": entry_bar, "exit_bar": i,
                                "entry_price": entry_px, "exit_price": exit_px,
                                "return_pct": ret_pct, "pnl_usd": pnl,
                                "exit_reason": exit_reason})
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
                entry_bar = i
        else:
            pk = max(pk, p)
            unrealized = (p - entry_px) / entry_px if entry_px > 0 else 0.0

            # Adaptive trail with BE floor
            if unrealized < gain_tier1:
                # Tight trail, NO breakeven floor
                ts = pk - trail_tight * at[i]
            elif unrealized < gain_tier2:
                # Mid trail + BE floor
                ts = max(entry_px, pk - trail_mid * at[i])
            else:
                # Wide trail + BE floor
                ts = max(entry_px, pk - trail_wide * at[i])

            if p < ts:
                px = True
                if unrealized >= gain_tier1:
                    exit_reason = "be_stop"
                else:
                    exit_reason = "trail_stop"
            elif ef[i] < es[i]:
                px = True
                exit_reason = "trend_exit"

    if inp and bq > 0:
        exit_px = cl[-1]
        ret_pct = (exit_px / entry_px - 1.0) * 100 if entry_px > 0 else 0.0
        pnl = bq * cl[-1] * (1 - cps) - (bq * entry_px * (1 + cps))
        trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                        "entry_price": entry_px, "exit_price": exit_px,
                        "return_pct": ret_pct, "pnl_usd": pnl,
                        "exit_reason": "end_of_data"})
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1
        nav[-1] = cash

    return nav, nt, trades


# ═══════════════════════════════════════════════════════════════════════════
# DISPATCHER
# ═══════════════════════════════════════════════════════════════════════════

def run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=120, cps=CPS_HARSH,
                 d1_cl=None, d1_close_times=None, h4_close_times=None,
                 trail_mult=TRAIL, with_trades=False):
    """Run a strategy and return (nav, trades) or (nav, trades, trade_list)."""
    if sid == "E0":
        nav, nt = sim_e0(cl, hi, lo, vo, tb, wi, slow_period=slow_period,
                         trail_mult=trail_mult, cps=cps)
        return (nav, nt, []) if with_trades else (nav, nt)
    elif sid == "X0":
        nav, nt = sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
                         slow_period=slow_period, trail_mult=trail_mult, cps=cps)
        return (nav, nt, []) if with_trades else (nav, nt)
    elif sid == "X2":
        nav, nt, tl = sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
                              slow_period=slow_period, cps=cps)
        return (nav, nt, tl) if with_trades else (nav, nt)
    elif sid == "X6":
        nav, nt, tl = sim_x6(cl, hi, lo, vo, tb, wi, d1_cl, d1_close_times, h4_close_times,
                              slow_period=slow_period, cps=cps)
        return (nav, nt, tl) if with_trades else (nav, nt)
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# ═══════════════════════════════════════════════════════════════════════════
# T1: FULL BACKTEST (3 scenarios)
# ═══════════════════════════════════════════════════════════════════════════

def test_backtest(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
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

    print(f"\n{'Strategy':12s} {'Scenario':8s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Calmar':>8s} {'Trades':>8s}")
    print("-" * 72)
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            print(f"{sid:12s} {sc:8s} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:8d}")

    # Delta tables
    print("\n  Delta vs E0:")
    print(f"  {'Strategy':12s} {'Scenario':8s} {'dSharpe':>8s} {'dCAGR%':>8s} {'dMDD%':>8s} {'dTrades':>8s}")
    for sid in ["X0", "X2", "X6"]:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            e0 = results["E0"][sc]
            print(f"  {sid:12s} {sc:8s} {m['sharpe']-e0['sharpe']:+8.4f} {m['cagr']-e0['cagr']:+8.2f} "
                  f"{m['mdd']-e0['mdd']:+8.2f} {m['trades']-e0['trades']:+8d}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T2: PERMUTATION TEST (10K shuffles)
# ═══════════════════════════════════════════════════════════════════════════

def test_permutation(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print(f"T2: PERMUTATION TEST ({N_PERM} shuffles)")
    print("=" * 72)

    rng = np.random.default_rng(SEED)
    n = len(cl)

    results = {}
    for sid in STRATEGY_IDS:
        nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                               d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        real_m = _metrics(nav, wi, nt)
        real_sharpe = real_m["sharpe"]

        log_rets = np.log(cl[1:] / cl[:-1])
        count_above = 0

        for p in range(N_PERM):
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
        print(f"  {sid:12s}  Sharpe={real_sharpe:.4f}  p={p_val:.6f}  (count_above={count_above})")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T3: TIMESCALE ROBUSTNESS (16 TS)
# ═══════════════════════════════════════════════════════════════════════════

def test_timescale(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
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

    print(f"\n{'TS':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>12s}", end="")
    print()
    print("-" * 65)
    for sp in SLOW_PERIODS:
        print(f"{sp:5d}", end="")
        for sid in STRATEGY_IDS:
            m = results[sid][sp]
            print(f"  {m['sharpe']:12.4f}", end="")
        print()

    # Count wins
    print("\n  Positive Sharpe count (out of 16):")
    for sid in STRATEGY_IDS:
        pos = sum(1 for sp in SLOW_PERIODS if results[sid][sp]["sharpe"] > 0)
        print(f"  {sid:12s}: {pos}/16")

    # Head-to-head vs E0
    print("\n  Wins vs E0 (Sharpe, out of 16):")
    for sid in ["X0", "X2", "X6"]:
        wins = sum(1 for sp in SLOW_PERIODS if results[sid][sp]["sharpe"] > results["E0"][sp]["sharpe"])
        print(f"  {sid:12s}: {wins}/16")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T4: BOOTSTRAP VCBB (500 paths x 16 TS)
# ═══════════════════════════════════════════════════════════════════════════

def test_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print(f"T4: BOOTSTRAP VCBB ({N_BOOT} paths x {len(SLOW_PERIODS)} TS)")
    print("=" * 72)

    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    # Pre-generate bootstrap paths
    boot_paths = []
    for b in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        bcl_full = np.concatenate([cl[:wi], bcl])
        bhi_full = np.concatenate([hi[:wi], bhi])
        blo_full = np.concatenate([lo[:wi], blo])
        bvo_full = np.concatenate([vo[:wi], bvo])
        btb_full = np.concatenate([tb[:wi], btb])
        boot_paths.append((bcl_full, bhi_full, blo_full, bvo_full, btb_full))

    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for sp in SLOW_PERIODS:
            sharpes = []; cagrs = []; mdds = []
            for b in range(N_BOOT):
                bcl_full, bhi_full, blo_full, bvo_full, btb_full = boot_paths[b]
                bnav, _ = run_strategy(sid, bcl_full, bhi_full, blo_full, bvo_full, btb_full,
                                       wi, slow_period=sp,
                                       d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
                bm = _metrics(bnav, wi)
                sharpes.append(bm["sharpe"])
                cagrs.append(bm["cagr"])
                mdds.append(bm["mdd"])

            results[sid][sp] = {
                "sharpe_median": float(np.median(sharpes)),
                "sharpe_mean": float(np.mean(sharpes)),
                "cagr_median": float(np.median(cagrs)),
                "mdd_median": float(np.median(mdds)),
                "p_cagr_gt0": float(np.mean(np.array(cagrs) > 0)),
            }

        sp120 = results[sid].get(120, {})
        print(f"  {sid:12s}  SP=120: Sharpe_med={sp120.get('sharpe_median', 0):.4f}  "
              f"CAGR_med={sp120.get('cagr_median', 0):.2f}%  "
              f"MDD_med={sp120.get('mdd_median', 0):.2f}%  "
              f"P(CAGR>0)={sp120.get('p_cagr_gt0', 0):.3f}")

    # Paired comparison vs E0
    print("\n  Paired Bootstrap Wins (vs E0, out of 16 TS):")
    print(f"  {'Strategy':12s} {'Sharpe':>8s} {'CAGR':>8s} {'MDD':>8s}")
    for sid in ["X0", "X2", "X6"]:
        sharpe_wins = cagr_wins = mdd_wins = 0
        for sp in SLOW_PERIODS:
            if results[sid][sp]["sharpe_median"] > results["E0"][sp]["sharpe_median"]:
                sharpe_wins += 1
            if results[sid][sp]["cagr_median"] > results["E0"][sp]["cagr_median"]:
                cagr_wins += 1
            if results[sid][sp]["mdd_median"] < results["E0"][sp]["mdd_median"]:
                mdd_wins += 1
        print(f"  {sid:12s} {sharpe_wins:>5d}/16 {cagr_wins:>5d}/16 {mdd_wins:>5d}/16")

    # Paired comparison vs X0
    print("\n  Paired Bootstrap Wins (vs X0, out of 16 TS):")
    print(f"  {'Strategy':12s} {'Sharpe':>8s} {'CAGR':>8s} {'MDD':>8s}")
    for sid in ["X2", "X6"]:
        sharpe_wins = cagr_wins = mdd_wins = 0
        for sp in SLOW_PERIODS:
            if results[sid][sp]["sharpe_median"] > results["X0"][sp]["sharpe_median"]:
                sharpe_wins += 1
            if results[sid][sp]["cagr_median"] > results["X0"][sp]["cagr_median"]:
                cagr_wins += 1
            if results[sid][sp]["mdd_median"] < results["X0"][sp]["mdd_median"]:
                mdd_wins += 1
        print(f"  {sid:12s} {sharpe_wins:>5d}/16 {cagr_wins:>5d}/16 {mdd_wins:>5d}/16")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T5: POSTMORTEM / FAILURE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def test_postmortem(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
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

            in_dd = False
            episodes = []
            for j in range(len(dd)):
                if dd[j] > 0.20 and not in_dd:
                    in_dd = True; dd_start = j
                elif dd[j] < 0.01 and in_dd:
                    in_dd = False
                    episodes.append({"start": dd_start, "end": j, "max_dd": float(np.max(dd[dd_start:j+1]))})
            if in_dd:
                episodes.append({"start": dd_start, "end": len(dd)-1, "max_dd": float(np.max(dd[dd_start:]))})

            results[sid][sp] = {**m, "dd_episodes_gt20": len(episodes), "episodes": episodes}

    print(f"\n{'Strategy':12s} {'SP':>5s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'DD>20%':>8s} {'Trades':>8s}")
    print("-" * 72)
    for sid in STRATEGY_IDS:
        for sp in test_periods:
            m = results[sid][sp]
            print(f"{sid:12s} {sp:5d} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} {m['dd_episodes_gt20']:8d} {m['trades']:8d}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T6: PARAM SENSITIVITY (1D sweeps)
# ═══════════════════════════════════════════════════════════════════════════

def test_param_sensitivity(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T6: PARAM SENSITIVITY")
    print("=" * 72)

    slow_sweep = [60, 72, 84, 96, 108, 120, 144, 168, 200, 240]
    trail_sweep = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {"slow": {}, "trail": {}}

        # Slow sweep
        for sp in slow_sweep:
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, slow_period=sp,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid]["slow"][sp] = m

        # Trail sweep (for E0/X0 only — X2/X6 have adaptive trails)
        if sid in ("E0", "X0"):
            for tm in trail_sweep:
                nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, trail_mult=tm,
                                       d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
                m = _metrics(nav, wi, nt)
                results[sid]["trail"][tm] = m
        elif sid == "X2":
            # Sweep trail_tight for X2
            for tm in trail_sweep:
                nav, nt, _ = sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                                     trail_tight=tm)
                m = _metrics(nav, wi, nt)
                results[sid]["trail"][tm] = m
        elif sid == "X6":
            # Sweep trail_tight for X6
            for tm in trail_sweep:
                nav, nt, _ = sim_x6(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                                     trail_tight=tm)
                m = _metrics(nav, wi, nt)
                results[sid]["trail"][tm] = m

    print(f"\n  Slow Period Sweep (Sharpe):")
    print(f"  {'SP':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>12s}", end="")
    print()
    for sp in slow_sweep:
        print(f"  {sp:5d}", end="")
        for sid in STRATEGY_IDS:
            m = results[sid]["slow"][sp]
            print(f"  {m['sharpe']:12.4f}", end="")
        print()

    print(f"\n  Trail Sweep (Sharpe) — E0/X0: trail_mult, X2/X6: trail_tight:")
    print(f"  {'Trail':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>12s}", end="")
    print()
    for tm in trail_sweep:
        print(f"  {tm:5.1f}", end="")
        for sid in STRATEGY_IDS:
            m = results[sid]["trail"].get(tm, {})
            print(f"  {m.get('sharpe', 0):12.4f}", end="")
        print()

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T7: COST STUDY
# ═══════════════════════════════════════════════════════════════════════════

def test_cost_study(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T7: COST STUDY (6 cost levels)")
    print("=" * 72)

    cost_levels_bps = [0, 10, 25, 50, 75, 100]
    results = {}

    for sid in STRATEGY_IDS:
        results[sid] = {}
        for bps in cost_levels_bps:
            cps = bps / 10_000.0
            nav, nt = run_strategy(sid, cl, hi, lo, vo, tb, wi, cps=cps,
                                   d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
            m = _metrics(nav, wi, nt)
            results[sid][bps] = m

    print(f"\n  {'BPS':>5s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>12s}", end="")
    print()
    print("  " + "-" * 60)
    for bps in cost_levels_bps:
        print(f"  {bps:5d}", end="")
        for sid in STRATEGY_IDS:
            m = results[sid][bps]
            print(f"  {m['sharpe']:12.4f}", end="")
        print()

    # X2/X6 vs X0 at each cost level
    print("\n  X2 vs X0 Sharpe delta at each cost level:")
    for bps in cost_levels_bps:
        d = results["X2"][bps]["sharpe"] - results["X0"][bps]["sharpe"]
        print(f"    {bps:3d} bps: {d:+.4f}")
    print("\n  X6 vs X0 Sharpe delta at each cost level:")
    for bps in cost_levels_bps:
        d = results["X6"][bps]["sharpe"] - results["X0"][bps]["sharpe"]
        print(f"    {bps:3d} bps: {d:+.4f}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T8: CALENDAR SLICE
# ═══════════════════════════════════════════════════════════════════════════

def test_calendar_slice(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_times):
    print("\n" + "=" * 72)
    print("T8: CALENDAR SLICE")
    print("=" * 72)

    import datetime

    # Run full sims once
    navs = {}
    for sid in STRATEGY_IDS:
        nav, _ = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                              d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        navs[sid] = nav

    # Convert timestamps to dates
    dates = [datetime.datetime.utcfromtimestamp(t / 1000) for t in h4_times]

    # Slice by year
    years = sorted(set(d.year for d in dates[wi:]))
    results = {}

    for year in years:
        mask = np.array([d.year == year for d in dates])
        idx = np.where(mask & (np.arange(len(dates)) >= wi))[0]
        if len(idx) < 10:
            continue

        results[year] = {}
        for sid in STRATEGY_IDS:
            nav_slice = navs[sid][idx]
            rets = nav_slice[1:] / nav_slice[:-1] - 1.0
            mu = np.mean(rets)
            std = np.std(rets, ddof=0)
            sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
            total_ret = (nav_slice[-1] / nav_slice[0] - 1.0) * 100
            results[year][sid] = {"sharpe": sharpe, "return_pct": total_ret}

    print(f"\n  {'Year':>6s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>12s}", end="")
    print()
    print("  " + "-" * 60)
    for year in sorted(results.keys()):
        print(f"  {year:6d}", end="")
        for sid in STRATEGY_IDS:
            s = results[year][sid]["sharpe"]
            print(f"  {s:12.4f}", end="")
        print()

    # Count wins per year vs X0
    print("\n  Year-by-year wins vs X0:")
    for sid in ["X2", "X6"]:
        wins = sum(1 for y in results if results[y][sid]["sharpe"] > results[y]["X0"]["sharpe"])
        print(f"  {sid}: {wins}/{len(results)} years")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T9: ROLLING WINDOW STABILITY
# ═══════════════════════════════════════════════════════════════════════════

def test_rolling_window(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T9: ROLLING WINDOW STABILITY (24-month windows)")
    print("=" * 72)

    navs = {}
    for sid in STRATEGY_IDS:
        nav, _ = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                              d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        navs[sid] = nav

    window = 24 * 30 * 6  # ~24 months in H4 bars
    step = 6 * 30 * 6     # ~6 months step

    results = []
    start = wi
    win_id = 0
    while start + window <= len(cl):
        end = start + window
        win_results = {"window": win_id, "start_idx": start, "end_idx": end}
        for sid in STRATEGY_IDS:
            nav_slice = navs[sid][start:end]
            rets = nav_slice[1:] / nav_slice[:-1] - 1.0
            mu = np.mean(rets)
            std = np.std(rets, ddof=0)
            sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
            win_results[f"{sid}_sharpe"] = sharpe
        results.append(win_results)
        start += step
        win_id += 1

    # Print results
    print(f"\n  {'Win':>4s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>10s}", end="")
    print()
    for r in results:
        print(f"  {r['window']:4d}", end="")
        for sid in STRATEGY_IDS:
            print(f"  {r[f'{sid}_sharpe']:10.4f}", end="")
        print()

    # Count windows where X2/X6 beats X0
    for comp in ["X2", "X6"]:
        wins = sum(1 for r in results if r[f"{comp}_sharpe"] > r["X0_sharpe"])
        print(f"\n  {comp} beats X0 in {wins}/{len(results)} windows")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T10: START-DATE SENSITIVITY
# ═══════════════════════════════════════════════════════════════════════════

def test_start_date(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_times):
    print("\n" + "=" * 72)
    print("T10: START-DATE SENSITIVITY")
    print("=" * 72)

    import datetime

    navs = {}
    for sid in STRATEGY_IDS:
        nav, _ = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                              d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        navs[sid] = nav

    dates = [datetime.datetime.utcfromtimestamp(t / 1000) for t in h4_times]

    start_years = ["2019-01", "2019-07", "2020-01", "2020-07", "2021-01", "2022-01", "2023-01"]
    results = {}

    for sy in start_years:
        y, m = int(sy[:4]), int(sy[5:])
        # Find first bar >= this date
        idx_start = None
        for i in range(wi, len(dates)):
            if dates[i].year > y or (dates[i].year == y and dates[i].month >= m):
                idx_start = i
                break
        if idx_start is None:
            continue

        results[sy] = {}
        for sid in STRATEGY_IDS:
            nav_slice = navs[sid][idx_start:]
            if len(nav_slice) < 10:
                continue
            rets = nav_slice[1:] / nav_slice[:-1] - 1.0
            mu = np.mean(rets)
            std = np.std(rets, ddof=0)
            sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
            total_ret = nav_slice[-1] / nav_slice[0] - 1.0
            yrs = len(rets) / (6.0 * 365.25)
            cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0
            results[sy][sid] = {"sharpe": sharpe, "cagr": cagr}

    print(f"\n  {'Start':>8s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>10s}", end="")
    print()
    for sy in start_years:
        if sy not in results:
            continue
        print(f"  {sy:>8s}", end="")
        for sid in STRATEGY_IDS:
            s = results[sy].get(sid, {}).get("sharpe", 0)
            print(f"  {s:10.4f}", end="")
        print()

    # Robustness: X2/X6 vs X0 across all start dates
    for comp in ["X2", "X6"]:
        wins = sum(1 for sy in results if results[sy].get(comp, {}).get("sharpe", 0) > results[sy].get("X0", {}).get("sharpe", 0))
        print(f"\n  {comp} beats X0 across {wins}/{len(results)} start dates")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T11: PAIRED BOOTSTRAP SHARPE DIFF + HOLM CORRECTION
# ═══════════════════════════════════════════════════════════════════════════

def test_paired_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T11: PAIRED BOOTSTRAP SHARPE DIFF + HOLM CORRECTION")
    print("=" * 72)

    # Get nav arrays
    navs = {}
    for sid in STRATEGY_IDS:
        nav, _ = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                              d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        navs[sid] = nav[wi:]

    # Returns
    rets = {sid: navs[sid][1:] / navs[sid][:-1] - 1.0 for sid in STRATEGY_IDS}

    n_boot = 5000
    block = 126
    rng = np.random.default_rng(SEED)

    # Test all pairs
    pairs = [("X0", "E0"), ("X2", "E0"), ("X6", "E0"), ("X2", "X0"), ("X6", "X0"), ("X6", "X2")]
    results = {}

    for a, b in pairs:
        r_a = rets[a]
        r_b = rets[b]
        n_r = len(r_a)

        diff_sharpes = []
        for _ in range(n_boot):
            # Circular block bootstrap
            starts = rng.integers(0, n_r, size=(n_r // block + 1,))
            idx = np.concatenate([np.arange(s, s + block) % n_r for s in starts])[:n_r]
            boot_a = r_a[idx]
            boot_b = r_b[idx]
            sa = np.mean(boot_a) / max(np.std(boot_a, ddof=0), 1e-12) * ANN
            sb = np.mean(boot_b) / max(np.std(boot_b, ddof=0), 1e-12) * ANN
            diff_sharpes.append(sa - sb)

        diff_arr = np.array(diff_sharpes)
        mean_diff = float(np.mean(diff_arr))
        ci_lo = float(np.percentile(diff_arr, 2.5))
        ci_hi = float(np.percentile(diff_arr, 97.5))
        sign_prob = float(np.mean(diff_arr > 0))

        results[f"{a}_vs_{b}"] = {
            "mean": mean_diff,
            "ci_lo_95": ci_lo,
            "ci_hi_95": ci_hi,
            "sign_probability": sign_prob,
        }
        print(f"  {a:4s} vs {b:4s}: mean={mean_diff:+.4f}  CI=[{ci_lo:.4f}, {ci_hi:.4f}]  P(A>B)={sign_prob:.3f}")

    # Holm correction
    print("\n  Holm-adjusted p-values (H0: Sharpe_A = Sharpe_B):")
    raw_p = []
    pair_labels = []
    for key, val in results.items():
        p = 1.0 - val["sign_probability"] if val["sign_probability"] > 0.5 else val["sign_probability"]
        p = 2.0 * p  # two-sided
        raw_p.append(min(p, 1.0))
        pair_labels.append(key)

    # Holm correction
    order = np.argsort(raw_p)
    m = len(raw_p)
    holm_p = np.ones(m)
    for rank, idx in enumerate(order):
        holm_p[idx] = min(raw_p[idx] * (m - rank), 1.0)
    # Enforce monotonicity
    for rank in range(1, m):
        idx = order[rank]
        prev_idx = order[rank - 1]
        holm_p[idx] = max(holm_p[idx], holm_p[prev_idx])

    for i in range(m):
        sig = "***" if holm_p[i] < 0.001 else "**" if holm_p[i] < 0.01 else "*" if holm_p[i] < 0.05 else "ns"
        results[pair_labels[i]]["holm_p"] = float(holm_p[i])
        results[pair_labels[i]]["significant"] = sig
        print(f"  {pair_labels[i]:12s}: raw_p={raw_p[i]:.4f}  holm_p={holm_p[i]:.4f}  {sig}")

    return results


# ═══════════════════════════════════════════════════════════════════════════
# T12: SIGNAL CONCORDANCE
# ═══════════════════════════════════════════════════════════════════════════

def test_signal_concordance(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T12: SIGNAL CONCORDANCE")
    print("=" * 72)

    # Generate in-position arrays for each strategy
    positions = {}

    for sid in STRATEGY_IDS:
        nav, _ = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                              d1_cl=d1_cl, d1_close_times=d1_ct, h4_close_times=h4_ct)
        # Derive in_position from NAV changes
        in_pos = np.zeros(len(nav), dtype=np.bool_)
        nav_start = nav[0]
        for i in range(1, len(nav)):
            # If NAV changes differently from price, we might be in position
            # Better: just re-run sim and track position
            pass

        # Re-run with position tracking via checking if we own BTC
        positions[sid] = _extract_position(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Concordance matrix
    n_post_wi = len(cl) - wi
    print(f"\n  Signal agreement (% of bars, post-warmup):")
    print(f"  {'':8s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid:>8s}", end="")
    print()
    results = {}
    for a in STRATEGY_IDS:
        results[a] = {}
        print(f"  {a:8s}", end="")
        for b in STRATEGY_IDS:
            agree = np.mean(positions[a][wi:] == positions[b][wi:]) * 100
            results[a][b] = agree
            print(f"  {agree:8.1f}", end="")
        print()

    return results


def _extract_position(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    """Extract boolean in-position array from strategy sim."""
    n = len(cl)
    fast_p = max(5, DEFAULT_SLOW // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, DEFAULT_SLOW)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    # D1 regime
    has_d1 = sid in ("X0", "X2", "X6")
    regime_h4 = np.ones(n, dtype=np.bool_)
    if has_d1 and d1_cl is not None:
        d1_ema = _ema(d1_cl, 21)
        d1_regime = d1_cl > d1_ema
        regime_h4 = np.zeros(n, dtype=np.bool_)
        d1_idx = 0
        n_d1 = len(d1_cl)
        for i in range(n):
            while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
                d1_idx += 1
            if d1_ct[d1_idx] < h4_ct[i]:
                regime_h4[i] = d1_regime[d1_idx]

    in_pos = np.zeros(n, dtype=np.bool_)
    inp = False; pk = 0.0; entry_px = 0.0

    for i in range(n):
        p = cl[i]
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            in_pos[i] = inp
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and (regime_h4[i] if has_d1 else True):
                inp = True; pk = p; entry_px = p
        else:
            pk = max(pk, p)

            if sid == "E0":
                ts = pk - TRAIL * at[i]
            elif sid == "X0":
                ts = pk - TRAIL * at[i]
            elif sid == "X2":
                unrealized = (p - entry_px) / entry_px if entry_px > 0 else 0.0
                if unrealized < GAIN_TIER1:
                    tm = TRAIL_TIGHT
                elif unrealized < GAIN_TIER2:
                    tm = TRAIL_MID
                else:
                    tm = TRAIL_WIDE
                ts = pk - tm * at[i]
            elif sid == "X6":
                unrealized = (p - entry_px) / entry_px if entry_px > 0 else 0.0
                if unrealized < GAIN_TIER1:
                    ts = pk - TRAIL_TIGHT * at[i]
                elif unrealized < GAIN_TIER2:
                    ts = max(entry_px, pk - TRAIL_MID * at[i])
                else:
                    ts = max(entry_px, pk - TRAIL_WIDE * at[i])
            else:
                ts = pk - TRAIL * at[i]

            if p < ts:
                inp = False; pk = 0.0; entry_px = 0.0
            elif ef[i] < es[i]:
                inp = False; pk = 0.0; entry_px = 0.0

        in_pos[i] = inp

    return in_pos


# ═══════════════════════════════════════════════════════════════════════════
# T13-T17: TRADE ANATOMY (Tier 4)
# ═══════════════════════════════════════════════════════════════════════════

def test_trade_anatomy(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 72)
    print("T13-T17: TRADE ANATOMY (Tier 4)")
    print("=" * 72)

    results = {}
    for sid in ["X0", "X2", "X6"]:
        nav, nt, trade_list = run_strategy(sid, cl, hi, lo, vo, tb, wi,
                                            d1_cl=d1_cl, d1_close_times=d1_ct,
                                            h4_close_times=h4_ct, with_trades=True)
        if not trade_list:
            results[sid] = {"error": "no trades"}
            continue

        returns = np.array([t["return_pct"] for t in trade_list])
        pnls = np.array([t["pnl_usd"] for t in trade_list])
        hold_bars = np.array([t["exit_bar"] - t["entry_bar"] for t in trade_list])
        hold_days = hold_bars * 4.0 / 24.0  # H4 bars to days

        # T13: Win rate / PF / Expectancy
        n_trades = len(returns)
        wins = returns > 0
        n_wins = int(np.sum(wins))
        n_losses = n_trades - n_wins
        win_rate = n_wins / n_trades * 100
        avg_win = float(np.mean(returns[wins])) if n_wins > 0 else 0.0
        avg_loss = float(np.mean(returns[~wins])) if n_losses > 0 else 0.0
        wl_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        gross_profit = float(np.sum(pnls[pnls > 0]))
        gross_loss = float(abs(np.sum(pnls[pnls < 0])))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        expectancy = float(np.mean(returns))

        # T14: Holding time
        hold_stats = {
            "mean_days": float(np.mean(hold_days)),
            "median_days": float(np.median(hold_days)),
            "min_days": float(np.min(hold_days)),
            "max_days": float(np.max(hold_days)),
            "p10": float(np.percentile(hold_days, 10)),
            "p90": float(np.percentile(hold_days, 90)),
        }

        # T15: Payoff concentration
        abs_pnl = np.abs(pnls)
        total_abs = np.sum(abs_pnl)
        sorted_abs = np.sort(abs_pnl)[::-1]
        top5_pct = float(np.sum(sorted_abs[:max(1, n_trades // 20)]) / total_abs * 100) if total_abs > 0 else 0.0
        top10_pct = float(np.sum(sorted_abs[:max(1, n_trades // 10)]) / total_abs * 100) if total_abs > 0 else 0.0

        # Gini coefficient
        sorted_pnl_abs = np.sort(np.abs(pnls))
        n_t = len(sorted_pnl_abs)
        gini = float((2 * np.sum(np.arange(1, n_t + 1) * sorted_pnl_abs) / (n_t * np.sum(sorted_pnl_abs))) - (n_t + 1) / n_t) if np.sum(sorted_pnl_abs) > 0 else 0.0

        # HHI
        shares = abs_pnl / total_abs if total_abs > 0 else np.zeros(n_trades)
        hhi = float(np.sum(shares ** 2))

        # T16: Top-N jackknife
        jackknife = {}
        sorted_idx = np.argsort(returns)  # ascending
        base_sharpe = _trade_sharpe(returns)
        base_cagr_approx = float(np.sum(returns))  # cumulative return proxy

        for k in [1, 3, 5, 10]:
            if k >= n_trades:
                continue
            # Remove top-K winners
            top_k_idx = sorted_idx[-k:]
            mask_top = np.ones(n_trades, dtype=bool)
            mask_top[top_k_idx] = False
            rem_returns = returns[mask_top]
            s_top = _trade_sharpe(rem_returns)

            # Remove top-K losers
            bot_k_idx = sorted_idx[:k]
            mask_bot = np.ones(n_trades, dtype=bool)
            mask_bot[bot_k_idx] = False
            rem_returns_bot = returns[mask_bot]
            s_bot = _trade_sharpe(rem_returns_bot)

            jackknife[k] = {
                "drop_top_sharpe": s_top,
                "drop_top_delta_pct": (s_top / base_sharpe - 1.0) * 100 if base_sharpe != 0 else 0.0,
                "drop_bot_sharpe": s_bot,
                "drop_bot_delta_pct": (s_bot / base_sharpe - 1.0) * 100 if base_sharpe != 0 else 0.0,
            }

        # T17: Fat-tail statistics
        sk = float(skew(returns))
        kt = float(kurtosis(returns, fisher=True))  # excess kurtosis
        jb_stat, jb_p = jarque_bera(returns)

        # Exit reason breakdown
        exit_reasons = {}
        for t in trade_list:
            r = t["exit_reason"]
            if r not in exit_reasons:
                exit_reasons[r] = {"count": 0, "returns": [], "pnls": []}
            exit_reasons[r]["count"] += 1
            exit_reasons[r]["returns"].append(t["return_pct"])
            exit_reasons[r]["pnls"].append(t["pnl_usd"])

        exit_summary = {}
        for reason, data in exit_reasons.items():
            rets_r = np.array(data["returns"])
            pnls_r = np.array(data["pnls"])
            exit_summary[reason] = {
                "count": data["count"],
                "pct_of_total": data["count"] / n_trades * 100,
                "win_rate_pct": float(np.mean(rets_r > 0) * 100),
                "avg_return_pct": float(np.mean(rets_r)),
                "total_pnl": float(np.sum(pnls_r)),
            }

        results[sid] = {
            "t13_n_trades": n_trades,
            "t13_win_rate_pct": win_rate,
            "t13_avg_win_pct": avg_win,
            "t13_avg_loss_pct": avg_loss,
            "t13_wl_ratio": wl_ratio,
            "t13_profit_factor": pf,
            "t13_expectancy_pct": expectancy,
            "t14_holding": hold_stats,
            "t15_top5_pct": top5_pct,
            "t15_top10_pct": top10_pct,
            "t15_gini": gini,
            "t15_hhi": hhi,
            "t16_jackknife": jackknife,
            "t17_skew": sk,
            "t17_excess_kurtosis": kt,
            "t17_jarque_bera_p": float(jb_p),
            "exit_reasons": exit_summary,
        }

        # Print summary
        print(f"\n  {sid}:")
        print(f"    Trades: {n_trades}  Win rate: {win_rate:.1f}%  PF: {pf:.3f}  Expectancy: {expectancy:.2f}%")
        print(f"    Hold: mean={hold_stats['mean_days']:.1f}d  median={hold_stats['median_days']:.1f}d")
        print(f"    Payoff: top5%={top5_pct:.1f}%  Gini={gini:.3f}  HHI={hhi:.4f}")
        print(f"    Fat-tail: skew={sk:.3f}  excess_kurt={kt:.3f}  JB_p={jb_p:.4f}")
        print(f"    Jackknife drop-1: {jackknife.get(1, {}).get('drop_top_delta_pct', 0):.1f}%")
        print(f"    Exit reasons:")
        for reason, data in exit_summary.items():
            print(f"      {reason:15s}: {data['count']:4d} ({data['pct_of_total']:.1f}%)  "
                  f"WR={data['win_rate_pct']:.1f}%  avg={data['avg_return_pct']:.2f}%  "
                  f"total=${data['total_pnl']:.0f}")

    return results


def _trade_sharpe(returns, trades_per_year=52.0):
    """Annualized Sharpe from per-trade returns."""
    if len(returns) < 2:
        return 0.0
    mu = np.mean(returns)
    std = np.std(returns, ddof=0)
    if std < 1e-12:
        return 0.0
    return float(mu / std * math.sqrt(trades_per_year))


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("PARITY EVALUATION X-SERIES (E0, X0, X2, X6)")
    print("=" * 72)

    print("\nLoading data...")
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
    h4_times = h4_ct  # alias for convenience

    d1_cl = np.array([b.close for b in d1], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in d1], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for i, b in enumerate(h4):
            if b.close_time >= feed.report_start_ms:
                wi = i
                break

    print(f"Data: {n} H4 bars, {len(d1)} D1 bars, warmup_idx={wi}")

    all_results = {}

    # Tier 2: T1-T7
    t0 = time.time()
    all_results["T1_backtest"] = test_backtest(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T1 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T2_permutation"] = test_permutation(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T2 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T3_timescale"] = test_timescale(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T3 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T4_bootstrap"] = test_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T4 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T5_postmortem"] = test_postmortem(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T5 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T6_sensitivity"] = test_param_sensitivity(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T6 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T7_cost"] = test_cost_study(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T7 completed in {time.time() - t0:.1f}s")

    # Tier 3: T8-T12
    t0 = time.time()
    all_results["T8_calendar"] = test_calendar_slice(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_times)
    print(f"  T8 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T9_rolling"] = test_rolling_window(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T9 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T10_start_date"] = test_start_date(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, h4_times)
    print(f"  T10 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T11_paired_boot"] = test_paired_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T11 completed in {time.time() - t0:.1f}s")

    t0 = time.time()
    all_results["T12_concordance"] = test_signal_concordance(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T12 completed in {time.time() - t0:.1f}s")

    # Tier 4: T13-T17
    t0 = time.time()
    all_results["T13_T17_trade_anatomy"] = test_trade_anatomy(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    print(f"  T13-T17 completed in {time.time() - t0:.1f}s")

    # Save results
    def _serialize(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, dict): return {str(k): _serialize(v) for k, v in obj.items()}
        if isinstance(obj, list): return [_serialize(v) for v in obj]
        return obj

    outpath = OUTDIR / "parity_eval_x_results.json"
    with open(outpath, "w") as f:
        json.dump(_serialize(all_results), f, indent=2)
    print(f"\nResults saved to: {outpath}")

    # Summary
    print("\n" + "=" * 72)
    print("FINAL SUMMARY")
    print("=" * 72)

    t1 = all_results["T1_backtest"]
    print(f"\n  {'Metric':12s} {'E0':>10s} {'X0':>10s} {'X2':>10s} {'X6':>10s}")
    print("  " + "-" * 55)
    for metric, key in [("Sharpe", "sharpe"), ("CAGR%", "cagr"), ("MDD%", "mdd"),
                         ("Calmar", "calmar"), ("Trades", "trades")]:
        print(f"  {metric:12s}", end="")
        for sid in STRATEGY_IDS:
            v = t1[sid]["harsh"][key]
            if isinstance(v, int):
                print(f"  {v:10d}", end="")
            else:
                print(f"  {v:10.4f}", end="")
        print()

    t2 = all_results["T2_permutation"]
    print(f"\n  Permutation p-values:")
    for sid in STRATEGY_IDS:
        print(f"    {sid}: p={t2[sid]['p_value']:.6f}")

    t4 = all_results["T4_bootstrap"]
    print(f"\n  Bootstrap Sharpe median (SP=120):")
    for sid in STRATEGY_IDS:
        print(f"    {sid}: {t4[sid][120]['sharpe_median']:.4f}")

    print("\n" + "=" * 72)
    print("PARITY EVALUATION X-SERIES COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
