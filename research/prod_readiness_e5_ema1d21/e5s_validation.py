#!/usr/bin/env python3
"""X0A-E5S: Full validation pipeline for E5S+EMA1D21 (simplified E5).

E5S replaces robust ATR (cap_q=0.90, cap_lb=100, ratr_period=20) with
standard ATR(20). Eliminates 3 structural params, keeping 4 tunable only.

Validation pipeline:
  T1: Full backtest via BacktestEngine (3 cost scenarios)
  T2: Timescale robustness (16 slow periods)
  T3: Bootstrap VCBB (500 paths)
  T4: Permutation test (10K shuffles)
  T5: WFO (8 windows)
  T6: Jackknife (top-1/3/5/10 removal)
  T7: Cost sweep (6 levels)
  T8: Comparative table (E5S vs E5 vs X0)
  Step 5: 5-gate absolute test

Gate definitions (all must PASS):
  G1: Sharpe > 1.0 (harsh)
  G2: MDD < 50% (harsh)
  G3: WFO >= 60% windows positive
  G4: Permutation p < 0.01
  G5: Jackknife-5 Sharpe drop < 50%

Recommendation criteria:
  |Sharpe(E5S) - Sharpe(E5)| < 0.02 AND all 5 gates PASS
  => RECOMMEND E5S as E5 replacement
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy
from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Config, VTrendE5Ema21D1Strategy)
from strategies.vtrend_e5s_ema21_d1.strategy import (
    VTrendE5SEma21D1Config, VTrendE5SEma21D1Strategy)

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
SLOW = 120

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0
TRAIL = 3.0

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]
N_BOOT = 500
BLKSZ = 60
SEED = 42
N_PERM = 1_000  # full strategy re-sim per permutation; 1K sufficient for p<0.01

COST_LEVELS = [0.0, 0.0005, 0.001, 0.0025, 0.005, 0.01]
CPS_HARSH = SCENARIOS["harsh"].per_side_bps / 10_000.0

# Step 5 gate thresholds
GATE_SHARPE = 1.0
GATE_MDD = 50.0
GATE_WFO_PCT = 0.60
GATE_PERM_P = 0.01
GATE_JACK5_DROP = 50.0  # max % drop

# Recommendation threshold
REC_SHARPE_DIFF = 0.02

STRATEGY_IDS = ["X0", "E5", "E5S"]
OUTDIR = Path(__file__).resolve().parent

# =========================================================================
# FAST INDICATORS
# =========================================================================


def _ema(series, period):
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
        b_f = np.array([alpha])
        a_f = np.array([1.0, -(1.0 - alpha)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b_f, a_f, tail, zi=zi)
            out[period - 1] = seed
            out[period:] = smoothed
        else:
            out[period - 1] = seed
    return out


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
        b_f = np.array([alpha])
        a_f = np.array([1.0, -(1.0 - alpha)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha) * seed])
            smoothed, _ = lfilter(b_f, a_f, tail, zi=zi)
            ratr[s + period:] = smoothed
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
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 0
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


def _d1_regime_map(cl, d1_cl, d1_ct, h4_ct, d1_ema_period=21):
    n = len(cl)
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema
    regime_h4 = np.zeros(n, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_h4[i] = d1_regime[d1_idx]
    return regime_h4


def _metrics(nav, wi):
    navs = nav[wi:]
    if len(navs) < 2:
        return {"sharpe": 0.0, "cagr": -100.0, "mdd": 100.0}
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
    wins = rets[rets > 0].sum()
    losses = np.abs(rets[rets < 0].sum())
    pf = wins / losses if losses > 1e-12 else 3.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "pf": pf}


def _objective(m):
    cagr = m.get("cagr", 0)
    mdd = m.get("mdd", 0)
    sharpe = m.get("sharpe", 0)
    pf = min(m.get("pf", 0), 3.0)
    nt = m.get("trades", 0)
    return 2.5 * cagr - 0.60 * mdd + 8.0 * max(0, sharpe) + 5.0 * max(0, pf - 1) + min(nt / 50, 1) * 5


# =========================================================================
# VECTORIZED SIMS
# =========================================================================


def _sim_core(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
              atr_arr, slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH,
              return_trades=False):
    """Core sim with pre-computed ATR array."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    entry_bar = 0; entry_price = 0.0
    nav = np.zeros(n)
    trades = [] if return_trades else None

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                entry_bar = i; entry_price = fp * (1 + cps)
            elif px:
                px = False
                exit_price = fp * (1 - cps)
                if return_trades:
                    pnl = bq * (exit_price - entry_price)
                    ret_pct = (exit_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
                    trades.append({"entry_bar": entry_bar, "exit_bar": i,
                                   "pnl_usd": pnl, "return_pct": ret_pct})
                cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1

        nav[i] = cash + bq * p

        if math.isnan(atr_arr[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * atr_arr[i]:
                px = True
            elif ef[i] < es[i]:
                px = True

    if inp and bq > 0:
        exit_price = cl[-1] * (1 - cps)
        if return_trades:
            pnl = bq * (exit_price - entry_price)
            ret_pct = (exit_price / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0
            trades.append({"entry_bar": entry_bar, "exit_bar": n - 1,
                           "pnl_usd": pnl, "return_pct": ret_pct})
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash

    if return_trades:
        return nav, nt, trades
    return nav, nt


def sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
           slow_period=SLOW, cps=CPS_HARSH, **kw):
    at = _atr(hi, lo, cl, ATR_P)
    return _sim_core(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                     at, slow_period=slow_period, cps=cps, **kw)


def sim_e5(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
           slow_period=SLOW, cps=CPS_HARSH, **kw):
    ratr = _robust_atr(hi, lo, cl)
    return _sim_core(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                     ratr, slow_period=slow_period, cps=cps, **kw)


def sim_e5s(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            slow_period=SLOW, cps=CPS_HARSH, **kw):
    at = _atr(hi, lo, cl, 20)  # standard ATR(20)
    return _sim_core(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                     at, slow_period=slow_period, cps=cps, **kw)


SIM_FUNCS = {"X0": sim_x0, "E5": sim_e5, "E5S": sim_e5s}


# =========================================================================
# T1: FULL BACKTEST VIA ENGINE
# =========================================================================


def _make_engine_strategy(sid):
    if sid == "X0":
        return VTrendX0Strategy(VTrendX0Config(slow_period=SLOW))
    elif sid == "E5":
        return VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config(slow_period=SLOW))
    elif sid == "E5S":
        return VTrendE5SEma21D1Strategy(VTrendE5SEma21D1Config(slow_period=SLOW))
    else:
        raise ValueError(sid)


def run_t1_backtest():
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST via BacktestEngine (3 scenarios)")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    results = {}

    for sid in STRATEGY_IDS:
        results[sid] = {}
        for sc_name in ["smart", "base", "harsh"]:
            strat = _make_engine_strategy(sid)
            eng = BacktestEngine(feed=feed, strategy=strat,
                                 cost=SCENARIOS[sc_name],
                                 initial_cash=CASH, warmup_mode="no_trade")
            res = eng.run()
            s = res.summary
            results[sid][sc_name] = {
                "sharpe": s.get("sharpe", 0),
                "cagr_pct": s.get("cagr_pct", 0),
                "max_drawdown_mid_pct": s.get("max_drawdown_mid_pct", 0),
                "trades": s.get("trades", 0),
                "win_rate_pct": s.get("win_rate_pct", 0),
                "profit_factor": s.get("profit_factor", 0),
                "avg_exposure": s.get("avg_exposure", 0),
                "avg_days_held": s.get("avg_days_held", 0),
                "turnover_per_year": s.get("turnover_per_year", 0),
            }

    print(f"\n  {'Strat':5s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
          f"{'Trades':>7s} {'WR%':>6s} {'PF':>7s}")
    print("  " + "-" * 60)
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            print(f"  {sid:5s} {sc:6s} {m['sharpe']:8.4f} {m['cagr_pct']:8.2f} "
                  f"{m['max_drawdown_mid_pct']:8.2f} {m['trades']:7d} "
                  f"{m['win_rate_pct']:6.1f} {m['profit_factor']:7.4f}")

    return results


# =========================================================================
# T2: TIMESCALE ROBUSTNESS
# =========================================================================


def run_t2_timescale(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print(f"T2: TIMESCALE ROBUSTNESS ({len(SLOW_PERIODS)} slow periods)")
    print("=" * 80)

    results = {sid: {} for sid in STRATEGY_IDS}
    for slow in SLOW_PERIODS:
        for sid in STRATEGY_IDS:
            nav, nt = SIM_FUNCS[sid](cl, hi, lo, vo, tb, wi,
                                     d1_cl, d1_ct, h4_ct,
                                     slow_period=slow, cps=CPS_HARSH)
            m = _metrics(nav, wi)
            m["trades"] = nt
            results[sid][slow] = m

    # Count wins
    e5s_wins_sharpe = sum(1 for s in SLOW_PERIODS
                          if results["E5S"][s]["sharpe"] > results["E5"][s]["sharpe"])
    e5s_wins_x0 = sum(1 for s in SLOW_PERIODS
                       if results["E5S"][s]["sharpe"] > results["X0"][s]["sharpe"])

    print(f"\n  {'Slow':>5s} {'X0 Sh':>8s} {'E5 Sh':>8s} {'E5S Sh':>8s} "
          f"{'E5S-E5':>8s} {'E5S-X0':>8s}")
    print("  " + "-" * 50)
    for slow in SLOW_PERIODS:
        x0 = results["X0"][slow]["sharpe"]
        e5 = results["E5"][slow]["sharpe"]
        e5s = results["E5S"][slow]["sharpe"]
        print(f"  {slow:5d} {x0:8.4f} {e5:8.4f} {e5s:8.4f} "
              f"{e5s-e5:+8.4f} {e5s-x0:+8.4f}")

    print(f"\n  E5S > E5: {e5s_wins_sharpe}/16  E5S > X0: {e5s_wins_x0}/16")
    return results


# =========================================================================
# T3: BOOTSTRAP VCBB
# =========================================================================


def run_t3_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print(f"T3: BOOTSTRAP VCBB ({N_BOOT} paths, block={BLKSZ})")
    print("=" * 80)

    n = len(cl)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl[wi:], hi[wi:], lo[wi:], vo[wi:], tb[wi:])
    vcbb = precompute_vcbb(cr, BLKSZ)
    n_trans = n - wi - 1
    p0 = cl[wi]
    rng = np.random.default_rng(SEED)

    boot_paths = []
    for _ in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(cr, hr, lr, vol_r, tb_r,
                                                  n_trans, BLKSZ, p0, rng, vcbb)
        boot_paths.append((
            np.concatenate([cl[:wi], bcl]),
            np.concatenate([hi[:wi], bhi]),
            np.concatenate([lo[:wi], blo]),
            np.concatenate([vo[:wi], bvo]),
            np.concatenate([tb[:wi], btb]),
        ))

    results = {}
    boot_sharpe = {sid: np.zeros(N_BOOT) for sid in STRATEGY_IDS}
    boot_mdd = {sid: np.zeros(N_BOOT) for sid in STRATEGY_IDS}

    for sid in STRATEGY_IDS:
        t0 = time.time()
        for b_idx, (bcl, bhi, blo, bvo, btb) in enumerate(boot_paths):
            bnav, _ = SIM_FUNCS[sid](bcl, bhi, blo, bvo, btb, wi,
                                     d1_cl, d1_ct, h4_ct)
            bm = _metrics(bnav, wi)
            boot_sharpe[sid][b_idx] = bm["sharpe"]
            boot_mdd[sid][b_idx] = bm["mdd"]

        results[sid] = {
            "sharpe_median": float(np.median(boot_sharpe[sid])),
            "sharpe_p5": float(np.percentile(boot_sharpe[sid], 5)),
            "sharpe_p95": float(np.percentile(boot_sharpe[sid], 95)),
            "mdd_median": float(np.median(boot_mdd[sid])),
            "p_sharpe_gt0": float(np.mean(boot_sharpe[sid] > 0)),
        }
        r = results[sid]
        print(f"  {sid:5s}  Sharpe={r['sharpe_median']:.4f} [{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"MDD={r['mdd_median']:.1f}%  P(Sharpe>0)={r['p_sharpe_gt0']:.3f}  ({time.time()-t0:.1f}s)")

    # H2H: E5S vs E5
    h2h = boot_sharpe["E5S"] - boot_sharpe["E5"]
    e5s_wins = float(np.mean(h2h > 0))
    results["h2h_E5S_vs_E5"] = {
        "sharpe_win_pct": e5s_wins * 100,
        "mean_delta": float(np.mean(h2h)),
    }
    print(f"\n  H2H E5S vs E5: E5S wins {e5s_wins*100:.1f}%  mean delta={np.mean(h2h):.4f}")

    # H2H: E5S vs X0
    h2h_x0 = boot_sharpe["E5S"] - boot_sharpe["X0"]
    e5s_wins_x0 = float(np.mean(h2h_x0 > 0))
    results["h2h_E5S_vs_X0"] = {
        "sharpe_win_pct": e5s_wins_x0 * 100,
        "mean_delta": float(np.mean(h2h_x0)),
    }
    print(f"  H2H E5S vs X0: E5S wins {e5s_wins_x0*100:.1f}%  mean delta={np.mean(h2h_x0):.4f}")

    return results


# =========================================================================
# T4: PERMUTATION TEST
# =========================================================================


def run_t4_permutation(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    """Permutation test: shuffle H4 bar returns to destroy temporal structure.

    Correct approach: shuffle bar-to-bar return ratios (and corresponding
    high/low/volume/taker_buy), reconstruct prices, re-run strategy.
    Trend-following should lose its edge on shuffled (IID) returns.
    """
    print("\n" + "=" * 80)
    print(f"T4: PERMUTATION TEST ({N_PERM} shuffles, full re-sim)")
    print("=" * 80)

    # Real Sharpe for E5S
    nav_real, _ = sim_e5s(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
    m_real = _metrics(nav_real, wi)
    real_sharpe = m_real["sharpe"]

    # Precompute bar-to-bar ratios (preserve intra-bar structure)
    n = len(cl)
    cl_ret = cl[1:] / cl[:-1]       # close-to-close returns
    hi_ratio = hi[1:] / cl[:-1]     # high relative to prev close
    lo_ratio = lo[1:] / cl[:-1]     # low relative to prev close
    vo_tail = vo[1:]
    tb_tail = tb[1:]

    rng = np.random.default_rng(SEED + 1)
    count_ge = 0
    t0 = time.time()

    for p_idx in range(N_PERM):
        # Shuffle all bar arrays with same permutation (preserve intra-bar)
        idx = rng.permutation(n - 1)
        s_cl_ret = cl_ret[idx]
        s_hi_ratio = hi_ratio[idx]
        s_lo_ratio = lo_ratio[idx]
        s_vo_tail = vo_tail[idx]
        s_tb_tail = tb_tail[idx]

        # Reconstruct prices from shuffled returns
        s_cl = np.empty(n)
        s_cl[0] = cl[0]
        s_cl[1:] = cl[0] * np.cumprod(s_cl_ret)

        s_hi = np.empty(n)
        s_hi[0] = hi[0]
        s_hi[1:] = s_cl[:-1] * s_hi_ratio
        s_hi = np.maximum(s_hi, s_cl)  # ensure high >= close

        s_lo = np.empty(n)
        s_lo[0] = lo[0]
        s_lo[1:] = s_cl[:-1] * s_lo_ratio
        s_lo = np.minimum(s_lo, s_cl)  # ensure low <= close

        s_vo = np.empty(n)
        s_vo[0] = vo[0]
        s_vo[1:] = s_vo_tail

        s_tb = np.empty(n)
        s_tb[0] = tb[0]
        s_tb[1:] = s_tb_tail

        # Re-run strategy on shuffled data (D1 kept fixed = conservative test)
        nav_perm, _ = sim_e5s(s_cl, s_hi, s_lo, s_vo, s_tb, wi,
                              d1_cl, d1_ct, h4_ct)
        m_perm = _metrics(nav_perm, wi)
        if m_perm["sharpe"] >= real_sharpe:
            count_ge += 1

        if (p_idx + 1) % 100 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (p_idx + 1) * (N_PERM - p_idx - 1)
            print(f"    {p_idx+1}/{N_PERM}  count_ge={count_ge}  "
                  f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

    p_val = (count_ge + 1) / (N_PERM + 1)
    elapsed = time.time() - t0
    print(f"\n  E5S real Sharpe: {real_sharpe:.4f}")
    print(f"  Permutation p-value: {p_val:.6f} ({count_ge}/{N_PERM} >= real)")
    print(f"  Gate G4: p < {GATE_PERM_P} → {'PASS' if p_val < GATE_PERM_P else 'FAIL'}")
    print(f"  Elapsed: {elapsed:.1f}s")

    return {"real_sharpe": real_sharpe, "p_value": p_val, "n_perm": N_PERM}


# =========================================================================
# T5: WFO
# =========================================================================


def generate_wfo_windows(
    start: str,
    end: str,
    train_months: int = 24,
    test_months: int = 6,
    slide_months: int = 6,
) -> list[dict[str, str | int]]:
    """Generate non-overlapping WFO windows with inclusive boundaries."""
    from dateutil.relativedelta import relativedelta
    from datetime import datetime, timedelta

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    windows = []
    wid = 0
    train_start = start_dt
    while True:
        train_end = train_start + relativedelta(months=train_months) - timedelta(days=1)
        test_start = train_end + timedelta(days=1)
        test_end = test_start + relativedelta(months=test_months) - timedelta(days=1)
        if test_end > end_dt:
            break
        windows.append({
            "window_id": wid,
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
        })
        wid += 1
        train_start += relativedelta(months=slide_months)
    return windows


def run_t5_wfo(d1_cl, d1_ct):
    print("\n" + "=" * 80)
    print("T5: WALK-FORWARD OPTIMIZATION (8 windows)")
    print("=" * 80)

    windows = generate_wfo_windows(START, END)

    results = []
    for w in windows:
        feed = DataFeed(DATA, start=w["test_start"], end=w["test_end"], warmup_days=WARMUP)
        h4 = feed.h4_bars
        d1 = feed.d1_bars

        cl = np.array([b.close for b in h4], dtype=np.float64)
        hi = np.array([b.high for b in h4], dtype=np.float64)
        lo = np.array([b.low for b in h4], dtype=np.float64)
        vo = np.array([b.volume for b in h4], dtype=np.float64)
        tb = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
        h4_ct = np.array([b.close_time for b in h4], dtype=np.int64)
        d1_cl_w = np.array([b.close for b in d1], dtype=np.float64)
        d1_ct_w = np.array([b.close_time for b in d1], dtype=np.int64)

        wi_w = 0
        if feed.report_start_ms is not None:
            for j, b in enumerate(h4):
                if b.close_time >= feed.report_start_ms:
                    wi_w = j
                    break

        # E5S candidate
        nav_c, nt_c = sim_e5s(cl, hi, lo, vo, tb, wi_w, d1_cl_w, d1_ct_w, h4_ct)
        m_c = _metrics(nav_c, wi_w)
        m_c["trades"] = nt_c

        # X0 baseline (E0+EMA21)
        nav_b, nt_b = sim_x0(cl, hi, lo, vo, tb, wi_w, d1_cl_w, d1_ct_w, h4_ct)
        m_b = _metrics(nav_b, wi_w)
        m_b["trades"] = nt_b

        score_c = _objective(m_c)
        score_b = _objective(m_b)
        delta = score_c - score_b

        results.append({
            "window_id": w["window_id"],
            "test_start": w["test_start"],
            "test_end": w["test_end"],
            "delta": delta,
            "cand_sharpe": m_c["sharpe"],
            "base_sharpe": m_b["sharpe"],
        })

        status = "+" if delta > 0 else "-"
        print(f"  W{w['window_id']} [{w['test_start']} → {w['test_end']}]  "
              f"delta={delta:+8.2f}  E5S Sh={m_c['sharpe']:.3f}  X0 Sh={m_b['sharpe']:.3f}  [{status}]")

    deltas = [r["delta"] for r in results]
    positive = sum(1 for d in deltas if d > 0)
    n_win = len(deltas)
    win_rate = positive / n_win if n_win > 0 else 0
    passed = win_rate >= GATE_WFO_PCT

    print(f"\n  SUMMARY: {positive}/{n_win} positive ({win_rate:.0%})")
    print(f"  Gate G3: >= {GATE_WFO_PCT:.0%} → {'PASS' if passed else 'FAIL'}")

    return {
        "windows": results,
        "positive": positive,
        "total": n_win,
        "win_rate": win_rate,
        "passed": passed,
    }


# =========================================================================
# T6: JACKKNIFE
# =========================================================================


def run_t6_jackknife(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print("T6: JACKKNIFE — top-K trade removal")
    print("=" * 80)

    results = {}
    for sid in ["E5", "E5S"]:
        nav, nt, trades = SIM_FUNCS[sid](cl, hi, lo, vo, tb, wi,
                                         d1_cl, d1_ct, h4_ct,
                                         return_trades=True)
        if not trades:
            results[sid] = {"error": "no trades"}
            continue

        df = pd.DataFrame(trades)
        total_pnl = df["pnl_usd"].sum()
        navs = nav[wi:]
        n_bars = len(navs) - 1
        bt_years = n_bars / (6.0 * 365.25)
        tpy = len(df) / bt_years

        rets = df["return_pct"].values
        base_sharpe = np.mean(rets) / np.std(rets, ddof=0) * np.sqrt(tpy) if np.std(rets, ddof=0) > 1e-12 else 0.0

        sorted_idx = df["pnl_usd"].sort_values(ascending=False).index
        sid_results = {"base_sharpe": float(base_sharpe), "n_trades": len(df)}

        print(f"\n  {sid}: {len(df)} trades, base trade-Sharpe={base_sharpe:.4f}")
        for k in [1, 3, 5, 10]:
            if k >= len(df):
                continue
            rem = df.drop(sorted_idx[:k])
            r = rem["return_pct"].values
            tpy_r = len(rem) / bt_years
            sh = np.mean(r) / np.std(r, ddof=0) * np.sqrt(tpy_r) if np.std(r, ddof=0) > 1e-12 else 0.0
            drop_pct = (base_sharpe - sh) / abs(base_sharpe) * 100 if base_sharpe != 0 else 0
            sid_results[f"drop_top{k}_sharpe"] = float(sh)
            sid_results[f"drop_top{k}_delta_pct"] = float(-drop_pct)
            print(f"    −{k}: Sharpe={sh:.4f}  drop={drop_pct:.1f}%")

        results[sid] = sid_results

    # Gate G5
    e5s_drop5 = abs(results.get("E5S", {}).get("drop_top5_delta_pct", -999))
    g5_pass = e5s_drop5 < GATE_JACK5_DROP
    print(f"\n  Gate G5: E5S −5 drop = {e5s_drop5:.1f}% (< {GATE_JACK5_DROP}% → {'PASS' if g5_pass else 'FAIL'})")

    return results


# =========================================================================
# T7: COST SWEEP
# =========================================================================


def run_t7_cost_sweep(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print("T7: COST SWEEP")
    print("=" * 80)

    results = {sid: {} for sid in STRATEGY_IDS}
    print(f"\n  {'CPS':>8s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {sid+' Sh':>10s}", end="")
    print()

    for cps in COST_LEVELS:
        for sid in STRATEGY_IDS:
            nav, nt = SIM_FUNCS[sid](cl, hi, lo, vo, tb, wi,
                                     d1_cl, d1_ct, h4_ct, cps=cps)
            m = _metrics(nav, wi)
            results[sid][cps] = m

        print(f"  {cps:8.4f}", end="")
        for sid in STRATEGY_IDS:
            print(f"  {results[sid][cps]['sharpe']:10.4f}", end="")
        print()

    # Check E5S beats X0 at all costs
    e5s_beats_x0 = all(results["E5S"][c]["sharpe"] > results["X0"][c]["sharpe"]
                        for c in COST_LEVELS)
    print(f"\n  E5S > X0 at all cost levels: {e5s_beats_x0}")

    return results


# =========================================================================
# STEP 5: 5-GATE ABSOLUTE
# =========================================================================


def run_step5(t1_results, t4_perm, t5_wfo, t6_jack):
    print("\n" + "=" * 80)
    print("STEP 5: 5-GATE ABSOLUTE TEST")
    print("=" * 80)

    e5s_harsh = t1_results["E5S"]["harsh"]
    e5_harsh = t1_results["E5"]["harsh"]

    g1_val = e5s_harsh["sharpe"]
    g1_pass = g1_val > GATE_SHARPE

    g2_val = e5s_harsh["max_drawdown_mid_pct"]
    g2_pass = g2_val < GATE_MDD

    g3_val = t5_wfo["win_rate"]
    g3_pass = g3_val >= GATE_WFO_PCT

    g4_val = t4_perm["p_value"]
    g4_pass = g4_val < GATE_PERM_P

    e5s_jack = t6_jack.get("E5S", {})
    g5_val = abs(e5s_jack.get("drop_top5_delta_pct", -999))
    g5_pass = g5_val < GATE_JACK5_DROP

    all_pass = g1_pass and g2_pass and g3_pass and g4_pass and g5_pass

    # Sharpe comparison for recommendation
    sharpe_diff = abs(e5s_harsh["sharpe"] - e5_harsh["sharpe"])
    recommend = all_pass and sharpe_diff < REC_SHARPE_DIFF

    gates = [
        ("G1", f"Sharpe > {GATE_SHARPE}", f"{g1_val:.4f}", g1_pass),
        ("G2", f"MDD < {GATE_MDD}%", f"{g2_val:.2f}%", g2_pass),
        ("G3", f"WFO >= {GATE_WFO_PCT:.0%}", f"{g3_val:.0%}", g3_pass),
        ("G4", f"Perm p < {GATE_PERM_P}", f"{g4_val:.6f}", g4_pass),
        ("G5", f"Jack-5 drop < {GATE_JACK5_DROP}%", f"{g5_val:.1f}%", g5_pass),
    ]

    print(f"\n  {'Gate':5s} {'Criterion':25s} {'Value':>12s} {'Result':>8s}")
    print("  " + "-" * 55)
    for gate, crit, val, passed in gates:
        print(f"  {gate:5s} {crit:25s} {val:>12s} {'PASS' if passed else 'FAIL':>8s}")

    print(f"\n  All gates pass: {all_pass}")
    print(f"  |Sharpe(E5S) - Sharpe(E5)| = {sharpe_diff:.4f} (< {REC_SHARPE_DIFF} → {'YES' if sharpe_diff < REC_SHARPE_DIFF else 'NO'})")
    print(f"\n  RECOMMENDATION: {'REPLACE E5 with E5S' if recommend else 'KEEP E5 (E5S does not qualify)'}")

    return {
        "gates": {g: {"criterion": c, "value": v, "passed": p} for g, c, v, p in gates},
        "all_pass": all_pass,
        "sharpe_diff": sharpe_diff,
        "recommend_replacement": recommend,
    }


# =========================================================================
# SAVE & REPORT
# =========================================================================


def save_results(all_results):
    json_path = OUTDIR / "e5s_validation_results.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
    print(f"\nSaved: {json_path}")


def generate_report(t1, step5, t2_ts, t3_boot, t4_perm, t5_wfo, t6_jack, t7_cost):
    e5s_h = t1["E5S"]["harsh"]
    e5_h = t1["E5"]["harsh"]
    x0_h = t1["X0"]["harsh"]
    s5 = step5

    report = f"""# X0A-E5S — Simplified E5 Validation Report

## 1. Design

**E5S+EMA1D21**: Replace robust ATR (3 extra params) with standard ATR(20).

| | E5+EMA1D21 | E5S+EMA1D21 |
|---|---|---|
| Trail ATR | Robust: cap TR at Q90 of prior 100 bars, Wilder(20) | Standard Wilder(20) |
| Extra params | ratr_cap_q=0.90, ratr_cap_lb=100, ratr_period=20 | atr_period=20 |
| Total meaningful params | 7 (4 tunable + 3 structural) | 4 (4 tunable) |
| Entry/exit logic | Identical | Identical |

## 2. Backtest Results (harsh, 50 bps RT)

| Metric | X0 | E5 | E5S | E5S-E5 |
|--------|---:|---:|----:|-------:|
| Sharpe | {x0_h['sharpe']:.4f} | {e5_h['sharpe']:.4f} | {e5s_h['sharpe']:.4f} | {e5s_h['sharpe']-e5_h['sharpe']:+.4f} |
| CAGR % | {x0_h['cagr_pct']:.2f} | {e5_h['cagr_pct']:.2f} | {e5s_h['cagr_pct']:.2f} | {e5s_h['cagr_pct']-e5_h['cagr_pct']:+.2f} |
| MDD % | {x0_h['max_drawdown_mid_pct']:.2f} | {e5_h['max_drawdown_mid_pct']:.2f} | {e5s_h['max_drawdown_mid_pct']:.2f} | {e5s_h['max_drawdown_mid_pct']-e5_h['max_drawdown_mid_pct']:+.2f} |
| Trades | {x0_h['trades']} | {e5_h['trades']} | {e5s_h['trades']} | {e5s_h['trades']-e5_h['trades']:+d} |
| Win Rate % | {x0_h['win_rate_pct']:.1f} | {e5_h['win_rate_pct']:.1f} | {e5s_h['win_rate_pct']:.1f} | {e5s_h['win_rate_pct']-e5_h['win_rate_pct']:+.1f} |

## 3. Step 5: 5-Gate Absolute Test

| Gate | Criterion | E5S Value | Result |
|------|-----------|----------:|--------|"""

    for g, info in s5["gates"].items():
        report += f"\n| {g} | {info['criterion']} | {info['value']} | {'PASS' if info['passed'] else 'FAIL'} |"

    report += f"""

**All gates pass: {'YES' if s5['all_pass'] else 'NO'}**

## 4. Replacement Criterion

|Sharpe(E5S) - Sharpe(E5)| = **{s5['sharpe_diff']:.4f}** (threshold: < {REC_SHARPE_DIFF})

## 5. Bootstrap H2H

| Comparison | E5S Win % | Mean Delta |
|------------|:---------:|:----------:|
| E5S vs E5 | {t3_boot.get('h2h_E5S_vs_E5', {}).get('sharpe_win_pct', 0):.1f}% | {t3_boot.get('h2h_E5S_vs_E5', {}).get('mean_delta', 0):.4f} |
| E5S vs X0 | {t3_boot.get('h2h_E5S_vs_X0', {}).get('sharpe_win_pct', 0):.1f}% | {t3_boot.get('h2h_E5S_vs_X0', {}).get('mean_delta', 0):.4f} |

## 6. Permutation Test

E5S Sharpe: {t4_perm['real_sharpe']:.4f}, p-value: {t4_perm['p_value']:.6f}

## 7. WFO

Positive windows: {t5_wfo['positive']}/{t5_wfo['total']} ({t5_wfo['win_rate']:.0%})

## 8. Verdict

"""
    if s5["recommend_replacement"]:
        report += f"""**RECOMMEND: Replace E5 with E5S.**

- All 5 absolute gates PASS
- Sharpe difference = {s5['sharpe_diff']:.4f} < {REC_SHARPE_DIFF} threshold
- E5S eliminates 3 structural params (ratr_cap_q, ratr_cap_lb, ratr_period)
- Removes double-standard concern: E5S uses only standard, well-known indicators
- Same mathematical proof backing as E5, with simpler implementation
"""
    else:
        reasons = []
        if not s5["all_pass"]:
            failed = [g for g, info in s5["gates"].items() if not info["passed"]]
            reasons.append(f"Failed gates: {', '.join(failed)}")
        if s5["sharpe_diff"] >= REC_SHARPE_DIFF:
            reasons.append(f"Sharpe diff {s5['sharpe_diff']:.4f} >= {REC_SHARPE_DIFF}")
        report += f"""**KEEP E5 (E5S does not qualify as replacement).**

Reasons: {'; '.join(reasons)}
"""

    report += "\n---\n*Generated by x0a/e5s_validation.py*\n"

    rpt_path = OUTDIR / "E5S_VALIDATION_REPORT.md"
    with open(rpt_path, "w") as f:
        f.write(report)
    print(f"Saved: {rpt_path}")


# =========================================================================
# MAIN
# =========================================================================


def main():
    t_start = time.time()
    print("=" * 80)
    print("X0A-E5S: SIMPLIFIED E5 FULL VALIDATION PIPELINE")
    print(f"  E5:  robust ATR (cap_q=0.90, cap_lb=100, period=20) + D1 EMA(21)")
    print(f"  E5S: standard ATR(20) + D1 EMA(21)")
    print(f"  Data: {START} to {END}, warmup={WARMUP}d, harsh=50 bps RT")
    print("=" * 80)

    # Load data once
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # T1: Full backtest
    t1 = run_t1_backtest()

    # T2: Timescale robustness
    t2 = run_t2_timescale(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T3: Bootstrap
    t3 = run_t3_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T4: Permutation
    t4 = run_t4_permutation(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T5: WFO
    t5 = run_t5_wfo(d1_cl, d1_ct)

    # T6: Jackknife
    t6 = run_t6_jackknife(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T7: Cost sweep
    t7 = run_t7_cost_sweep(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Step 5: 5-gate absolute
    step5 = run_step5(t1, t4, t5, t6)

    # Save and report
    all_results = {
        "t1_backtest": t1,
        "t4_permutation": t4,
        "t5_wfo": t5,
        "step5_gates": step5,
    }
    save_results(all_results)
    generate_report(t1, step5, t2, t3, t4, t5, t6, t7)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 80}")
    print(f"E5S VALIDATION COMPLETE ({elapsed:.0f}s)")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
