#!/usr/bin/env python3
"""P3.5 — Canonical final benchmark for X0 reconciliation.

DESIGN DECISIONS (differs from P3.4):
  1. T1 uses BacktestEngine with ACTUAL strategy code for ALL 7 strategies.
     No vectorized surrogate aliasing. This is the canonical source of truth.
  2. T2 uses vectorized sims for bootstrap (computational necessity: 3500 runs).
     Labeled explicitly as "surrogate bootstrap". Parity bounds documented.
  3. Exposure metrics split into 3 distinct definitions:
     - avg_exposure: mean(btc_value / nav) across all bars (engine definition)
     - time_in_market_pct: % of bars with exposure > 1% (engine definition)
     - mean_entry_weight: mean of Signal.target_exposure at entry (Phase 3 only)
  4. Trade counts reconciled: engine produces canonical count per scenario.

Strategies (7):
  E0, E0_EMA21, E5, E5_EMA21, X0, X0_E5EXIT, X0_VOLSIZE
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
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# Strategy imports — all 7 actual strategy classes
from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy
from strategies.vtrend_ema21_d1.strategy import VTrendEma21D1Config, VTrendEma21D1Strategy
from strategies.vtrend_e5.strategy import VTrendE5Config, VTrendE5Strategy
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Config, VTrendE5Ema21D1Strategy
from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy
from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy
from strategies.vtrend_x0_volsize.strategy import VTrendX0VolsizeConfig, VTrendX0VolsizeStrategy


# =========================================================================
# CONSTANTS (same as P2.4 / P3.4)
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

SLOW = 120
TRAIL = 3.0

N_BOOT = 500
BLKSZ = 60
SEED = 42

# Phase 3 vol-sizing parameters
TARGET_VOL = 0.15
VOL_LOOKBACK = 120
VOL_FLOOR = 0.08
BARS_PER_YEAR_4H = 365.0 * 6.0

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


def _make_strategy(sid):
    """Instantiate actual strategy object for BacktestEngine."""
    if sid == "E0":
        return VTrendStrategy(VTrendConfig())
    elif sid == "E0_EMA21":
        return VTrendEma21D1Strategy(VTrendEma21D1Config())
    elif sid == "E5":
        return VTrendE5Strategy(VTrendE5Config())
    elif sid == "E5_EMA21":
        return VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config())
    elif sid == "X0":
        return VTrendX0Strategy(VTrendX0Config())
    elif sid == "X0_E5EXIT":
        return VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    elif sid == "X0_VOLSIZE":
        return VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# =========================================================================
# T1: FULL BACKTEST via BacktestEngine (CANONICAL — no surrogates)
# =========================================================================

def run_backtests_engine():
    """Run all 7 strategies × 3 cost scenarios through BacktestEngine."""
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST via BacktestEngine (canonical, no surrogates)")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for scenario in ["smart", "base", "harsh"]:
            cost_cfg = SCENARIOS[scenario]
            strat = _make_strategy(sid)
            eng = BacktestEngine(feed=feed, strategy=strat, cost=cost_cfg,
                                 initial_cash=CASH, warmup_mode="no_trade")
            res = eng.run()
            s = res.summary
            results[sid][scenario] = {
                "sharpe": s.get("sharpe", 0),
                "cagr_pct": s.get("cagr_pct", 0),
                "max_drawdown_mid_pct": s.get("max_drawdown_mid_pct", 0),
                "calmar": s.get("calmar", 0),
                "trades": s.get("trades", 0),
                "wins": s.get("wins", 0),
                "losses": s.get("losses", 0),
                "win_rate_pct": s.get("win_rate_pct", 0),
                "profit_factor": s.get("profit_factor", 0),
                "total_return_pct": s.get("total_return_pct", 0),
                "avg_exposure": s.get("avg_exposure", 0),
                "time_in_market_pct": s.get("time_in_market_pct", 0),
                "avg_trade_pnl": s.get("avg_trade_pnl", 0),
                "avg_days_held": s.get("avg_days_held", 0),
                "fees_total": s.get("fees_total", 0),
                "turnover_per_year": s.get("turnover_per_year", 0),
            }

    # Print table
    header = (f"{'Strategy':14s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s} {'WR%':>6s} {'PF':>7s} "
              f"{'AvgExpo':>8s} {'TiM%':>7s}")
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            pf_str = f"{m['profit_factor']:.4f}" if isinstance(m['profit_factor'], (int, float)) else str(m['profit_factor'])
            print(f"{sid:14s} {sc:6s} {m['sharpe']:8.4f} {m['cagr_pct']:8.2f} "
                  f"{m['max_drawdown_mid_pct']:8.2f} {m['calmar']:8.4f} {m['trades']:7d} "
                  f"{m['win_rate_pct']:6.1f} {pf_str:>7s} "
                  f"{m['avg_exposure']:8.4f} {m['time_in_market_pct']:7.2f}")

    return results


# =========================================================================
# VECTORIZED SIMS (for bootstrap only — labeled as surrogates)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _atr(high, low, close, period=14):
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


def _vdo(close, high, low, volume, taker_buy, fast=12, slow=28):
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


def _realized_vol(close, lookback=VOL_LOOKBACK, bars_per_year=BARS_PER_YEAR_4H):
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    lr = np.full(n, np.nan, dtype=np.float64)
    lr[1:] = np.log(np.divide(close[1:], close[:-1],
                    out=np.full(n - 1, np.nan, dtype=np.float64),
                    where=close[:-1] > 0.0))
    ann_factor = math.sqrt(bars_per_year)
    for i in range(lookback, n):
        window = lr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=0)) * ann_factor
    return out


def _metrics_vec(nav, wi, nt=0):
    """Vectorized sim metrics (for bootstrap only)."""
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
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}


# --- vectorized sim functions (for bootstrap) ---

ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0


def _sim_e0(cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
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


def _sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
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


def _sim_e5(cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
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


def _sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
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


def _sim_x0_volsize(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                    slow_period=SLOW, trail_mult=TRAIL, cps=0.005):
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    rv = _realized_vol(cl)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    entry_weight = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False
                invest = entry_weight * cash
                bq = invest / (fp * (1 + cps))
                cash = cash - invest
                inp = True; pk = p
            elif px:
                px = False
                cash = cash + bq * fp * (1 - cps)
                bq = 0.0; inp = False; nt += 1
        nav[i] = cash + bq * p
        if math.isnan(ef[i]) or math.isnan(es[i]) or math.isnan(ratr[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                rv_val = rv[i] if rv is not None else float('nan')
                if math.isnan(rv_val):
                    entry_weight = 1.0
                else:
                    entry_weight = TARGET_VOL / max(rv_val, VOL_FLOOR)
                    entry_weight = max(0.0, min(1.0, entry_weight))
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * ratr[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def _run_surrogate(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    """Run vectorized surrogate sim. For bootstrap only."""
    kw = dict(slow_period=SLOW, cps=cps)
    if sid == "E0":
        return _sim_e0(cl, hi, lo, vo, tb, wi, **kw)
    elif sid in ("E0_EMA21", "X0"):
        return _sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "E5":
        return _sim_e5(cl, hi, lo, vo, tb, wi, **kw)
    elif sid in ("E5_EMA21", "X0_E5EXIT"):
        return _sim_e5_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    elif sid == "X0_VOLSIZE":
        return _sim_x0_volsize(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# =========================================================================
# T2: BOOTSTRAP VCBB (surrogate — labeled)
# =========================================================================

def run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print(f"T2: SURROGATE BOOTSTRAP VCBB ({N_BOOT} paths, block={BLKSZ})")
    print("    NOTE: Uses vectorized sims, not BacktestEngine.")
    print("    Bootstrap distributional properties are approximate.")
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
    for _ in range(N_BOOT):
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb)
        boot_paths.append((
            np.concatenate([cl[:wi], bcl]),
            np.concatenate([hi[:wi], bhi]),
            np.concatenate([lo[:wi], blo]),
            np.concatenate([vo[:wi], bvo]),
            np.concatenate([tb[:wi], btb]),
        ))
    print(f"done ({time.time() - t0:.1f}s)")

    results = {}
    for sid in STRATEGY_IDS:
        sharpes, cagrs, mdds = [], [], []
        t0 = time.time()
        for bcl, bhi, blo, bvo, btb in boot_paths:
            bnav, _ = _run_surrogate(sid, bcl, bhi, blo, bvo, btb, wi, d1_cl, d1_ct, h4_ct)
            bm = _metrics_vec(bnav, wi)
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
# T3: PARITY VERIFICATION (engine vs vectorized surrogate)
# =========================================================================

def run_parity_check(bt_results, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    """Compare engine trade counts vs vectorized surrogate trade counts."""
    print("\n" + "=" * 80)
    print("T3: ENGINE vs VECTORIZED SURROGATE PARITY CHECK")
    print("=" * 80)

    cps_base = SCENARIOS["base"].per_side_bps / 10_000.0
    parity_data = []
    for sid in STRATEGY_IDS:
        nav_vec, nt_vec = _run_surrogate(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps_base)
        m_vec = _metrics_vec(nav_vec, wi, nt_vec)
        m_eng = bt_results[sid]["base"]

        match_trades = nt_vec == m_eng["trades"]
        sharpe_diff = abs(m_vec["sharpe"] - m_eng["sharpe"])

        print(f"  {sid:14s}  Engine trades={m_eng['trades']:>4d}  Vec trades={nt_vec:>4d}  "
              f"{'MATCH' if match_trades else 'DIFFER':>6s}  "
              f"Sharpe eng={m_eng['sharpe']:.4f}  vec={m_vec['sharpe']:.4f}  diff={sharpe_diff:.4f}")

        parity_data.append({
            "strategy": sid,
            "engine_trades": m_eng["trades"],
            "vec_trades": nt_vec,
            "trades_match": match_trades,
            "engine_sharpe": m_eng["sharpe"],
            "vec_sharpe": m_vec["sharpe"],
            "sharpe_diff": sharpe_diff,
        })

    return parity_data


# =========================================================================
# T4: PHASE 3 ATTRIBUTION + EXPOSURE (engine-based)
# =========================================================================

def run_phase3_attribution():
    """Phase 3 vs Phase 2 attribution via BacktestEngine."""
    print("\n" + "=" * 80)
    print("T4: PHASE 3 vs PHASE 2 ATTRIBUTION (BacktestEngine)")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    attr = {}
    for scenario in ["smart", "base", "harsh"]:
        cost_cfg = SCENARIOS[scenario]

        p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
        p3_strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())

        p2_res = BacktestEngine(feed=feed, strategy=p2_strat, cost=cost_cfg,
                                initial_cash=CASH, warmup_mode="no_trade").run()
        p3_res = BacktestEngine(feed=feed, strategy=p3_strat, cost=cost_cfg,
                                initial_cash=CASH, warmup_mode="no_trade").run()

        p2_s, p3_s = p2_res.summary, p3_res.summary
        attr[scenario] = {
            "p2_sharpe": p2_s.get("sharpe", 0), "p3_sharpe": p3_s.get("sharpe", 0),
            "p2_cagr": p2_s.get("cagr_pct", 0), "p3_cagr": p3_s.get("cagr_pct", 0),
            "p2_mdd": p2_s.get("max_drawdown_mid_pct", 0), "p3_mdd": p3_s.get("max_drawdown_mid_pct", 0),
            "p2_calmar": p2_s.get("calmar", 0), "p3_calmar": p3_s.get("calmar", 0),
            "p2_trades": p2_s.get("trades", 0), "p3_trades": p3_s.get("trades", 0),
            "p2_winrate": p2_s.get("win_rate_pct", 0), "p3_winrate": p3_s.get("win_rate_pct", 0),
            "p2_pf": p2_s.get("profit_factor", 0), "p3_pf": p3_s.get("profit_factor", 0),
            "p2_avg_exposure": p2_s.get("avg_exposure", 0), "p3_avg_exposure": p3_s.get("avg_exposure", 0),
            "p2_time_in_market": p2_s.get("time_in_market_pct", 0),
            "p3_time_in_market": p3_s.get("time_in_market_pct", 0),
        }

    # Print delta table
    print("\n  --- Delta Table (P3 - P2) by cost scenario ---")
    print(f"  {'Scen':6s} {'dSharpe':>9s} {'dCAGR%':>9s} {'dMDD%':>9s} {'dCalmar':>9s} "
          f"{'dTrades':>8s} {'dExpo':>8s} {'dTiM%':>8s}")
    for sc in ["smart", "base", "harsh"]:
        a = attr[sc]
        print(f"  {sc:6s} {a['p3_sharpe']-a['p2_sharpe']:>+9.4f} "
              f"{a['p3_cagr']-a['p2_cagr']:>+9.2f} "
              f"{a['p3_mdd']-a['p2_mdd']:>+9.2f} "
              f"{a['p3_calmar']-a['p2_calmar']:>+9.4f} "
              f"{a['p3_trades']-a['p2_trades']:>+8.0f} "
              f"{a['p3_avg_exposure']-a['p2_avg_exposure']:>+8.4f} "
              f"{a['p3_time_in_market']-a['p2_time_in_market']:>+8.2f}")

    # Timing parity (base scenario)
    cost_cfg = SCENARIOS["base"]
    p2_strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())
    p3_strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig())
    p2_res = BacktestEngine(feed=feed, strategy=p2_strat, cost=cost_cfg,
                            initial_cash=CASH, warmup_mode="no_trade").run()
    p3_res = BacktestEngine(feed=feed, strategy=p3_strat, cost=cost_cfg,
                            initial_cash=CASH, warmup_mode="no_trade").run()

    p2_trades = p2_res.trades
    p3_trades = p3_res.trades

    entry_match = sum(1 for t2, t3 in zip(p2_trades, p3_trades) if t2.entry_ts_ms == t3.entry_ts_ms)
    exit_match = sum(1 for t2, t3 in zip(p2_trades, p3_trades) if t2.exit_ts_ms == t3.exit_ts_ms)
    timing_ok = (len(p2_trades) == len(p3_trades) and
                 entry_match == len(p2_trades) and exit_match == len(p2_trades))

    print(f"\n  Timing parity (base): P2={len(p2_trades)} trades, P3={len(p3_trades)} trades")
    print(f"    Entry match: {entry_match}/{len(p2_trades)}")
    print(f"    Exit match:  {exit_match}/{len(p2_trades)}")
    print(f"    TIMING PARITY: {'CONFIRMED' if timing_ok else 'BROKEN'}")

    # Exposure metrics for Phase 3 (base scenario)
    p3_entry_weights = []
    for t3 in p3_trades:
        # entry fill is the first fill of the trade
        for f in p3_res.fills:
            if f.ts_ms == t3.entry_ts_ms:
                # Find corresponding P2 fill for ratio
                for f2 in p2_res.fills:
                    if f2.ts_ms == t3.entry_ts_ms:
                        if abs(f2.qty) > 1e-12:
                            p3_entry_weights.append(abs(f.qty) / abs(f2.qty))
                        break
                break

    # Compute entry weights from qty ratio (P3 / P2)
    p3_entry_weights = []
    for t2, t3 in zip(p2_trades, p3_trades):
        if abs(t2.qty) > 1e-12:
            p3_entry_weights.append(abs(t3.qty) / abs(t2.qty))

    p3_entry_weights_arr = np.array(p3_entry_weights) if p3_entry_weights else np.array([0.0])

    exposure_metrics = {
        "p3_trades": len(p3_trades),
        "p3_avg_exposure": attr["base"]["p3_avg_exposure"],
        "p3_time_in_market_pct": attr["base"]["p3_time_in_market"],
        "p2_avg_exposure": attr["base"]["p2_avg_exposure"],
        "p2_time_in_market_pct": attr["base"]["p2_time_in_market"],
        "timing_parity": timing_ok,
    }

    # If qty ratio approach failed, recompute from vol-sizing formula directly
    if len(p3_entry_weights) == 0 or any(w > 1.5 for w in p3_entry_weights):
        feed2 = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
        h4 = feed2.h4_bars
        close = np.array([b.close for b in h4], dtype=np.float64)
        rv = _realized_vol(close)
        p3_entry_weights = []
        for t3 in p3_trades:
            for j, b in enumerate(h4):
                if b.close_time == t3.entry_ts_ms:
                    rv_val = rv[j] if j < len(rv) and not math.isnan(rv[j]) else float('nan')
                    if math.isnan(rv_val):
                        p3_entry_weights.append(1.0)
                    else:
                        w = TARGET_VOL / max(rv_val, VOL_FLOOR)
                        w = max(0.0, min(1.0, w))
                        p3_entry_weights.append(w)
                    break
        p3_entry_weights_arr = np.array(p3_entry_weights) if p3_entry_weights else np.array([0.0])

    if len(p3_entry_weights_arr) > 0 and p3_entry_weights_arr[0] > 0:
        exposure_metrics["mean_entry_weight"] = float(np.mean(p3_entry_weights_arr))
        exposure_metrics["median_entry_weight"] = float(np.median(p3_entry_weights_arr))
        exposure_metrics["min_entry_weight"] = float(np.min(p3_entry_weights_arr))
        exposure_metrics["max_entry_weight"] = float(np.max(p3_entry_weights_arr))
        exposure_metrics["std_entry_weight"] = float(np.std(p3_entry_weights_arr, ddof=0))
        exposure_metrics["p5_entry_weight"] = float(np.percentile(p3_entry_weights_arr, 5))
        exposure_metrics["p25_entry_weight"] = float(np.percentile(p3_entry_weights_arr, 25))
        exposure_metrics["p75_entry_weight"] = float(np.percentile(p3_entry_weights_arr, 75))
        exposure_metrics["p95_entry_weight"] = float(np.percentile(p3_entry_weights_arr, 95))

    print(f"\n  --- Exposure Metrics (base scenario) ---")
    print(f"  Phase 2:")
    print(f"    avg_exposure (mean BTC/NAV fraction): {attr['base']['p2_avg_exposure']:.4f}")
    print(f"    time_in_market_pct: {attr['base']['p2_time_in_market']:.2f}%")
    print(f"    mean_entry_weight: 1.0000 (binary: always full allocation)")
    print(f"  Phase 3:")
    print(f"    avg_exposure (mean BTC/NAV fraction): {attr['base']['p3_avg_exposure']:.4f}")
    print(f"    time_in_market_pct: {attr['base']['p3_time_in_market']:.2f}%")
    if "mean_entry_weight" in exposure_metrics:
        print(f"    mean_entry_weight: {exposure_metrics['mean_entry_weight']:.4f}")
        print(f"    median_entry_weight: {exposure_metrics['median_entry_weight']:.4f}")
        print(f"    [min, max] entry weight: [{exposure_metrics['min_entry_weight']:.4f}, "
              f"{exposure_metrics['max_entry_weight']:.4f}]")

    return attr, exposure_metrics


# =========================================================================
# PROMOTION DECISION
# =========================================================================

def promotion_decision(bt_results, boot_results):
    print("\n" + "=" * 80)
    print("PROMOTION DECISION (based on canonical engine results)")
    print("=" * 80)

    gates = {}

    # Gate 1: Sharpe > P2 in all cost scenarios
    g1 = all(bt_results["X0_VOLSIZE"][sc]["sharpe"] > bt_results["X0_E5EXIT"][sc]["sharpe"]
             for sc in ["smart", "base", "harsh"])
    gates["G1_sharpe_gt_p2_all_costs"] = g1
    print(f"  G1 Sharpe > P2 (all costs):  {'PASS' if g1 else 'FAIL'}")
    for sc in ["smart", "base", "harsh"]:
        p3s = bt_results["X0_VOLSIZE"][sc]["sharpe"]
        p2s = bt_results["X0_E5EXIT"][sc]["sharpe"]
        print(f"      {sc}: P3={p3s:.4f} vs P2={p2s:.4f} ({'+' if p3s > p2s else ''}{p3s-p2s:.4f})")

    # Gate 2: MDD < P2 in all cost scenarios
    g2 = all(bt_results["X0_VOLSIZE"][sc]["max_drawdown_mid_pct"] < bt_results["X0_E5EXIT"][sc]["max_drawdown_mid_pct"]
             for sc in ["smart", "base", "harsh"])
    gates["G2_mdd_lt_p2_all_costs"] = g2
    print(f"  G2 MDD < P2 (all costs):     {'PASS' if g2 else 'FAIL'}")

    # Gate 3: Calmar > P2 in all cost scenarios
    g3 = all(bt_results["X0_VOLSIZE"][sc]["calmar"] > bt_results["X0_E5EXIT"][sc]["calmar"]
             for sc in ["smart", "base", "harsh"])
    gates["G3_calmar_gt_p2_all_costs"] = g3
    print(f"  G3 Calmar > P2 (all costs):  {'PASS' if g3 else 'FAIL'}")
    for sc in ["smart", "base", "harsh"]:
        p3c = bt_results["X0_VOLSIZE"][sc]["calmar"]
        p2c = bt_results["X0_E5EXIT"][sc]["calmar"]
        print(f"      {sc}: P3={p3c:.4f} vs P2={p2c:.4f} ({'+' if p3c > p2c else ''}{p3c-p2c:.4f})")

    # Gate 4: Boot P(CAGR>0) >= 0.70
    g4 = boot_results["X0_VOLSIZE"]["p_cagr_gt0"] >= 0.70
    gates["G4_boot_pcagr_gte_70"] = g4
    print(f"  G4 Boot P(CAGR>0) >= 0.70:   {'PASS' if g4 else 'FAIL'} "
          f"({boot_results['X0_VOLSIZE']['p_cagr_gt0']:.3f})")

    # Gate 5: Boot P(Sharpe>0) >= 0.70
    g5 = boot_results["X0_VOLSIZE"]["p_sharpe_gt0"] >= 0.70
    gates["G5_boot_psharpe_gte_70"] = g5
    print(f"  G5 Boot P(Sharpe>0) >= 0.70: {'PASS' if g5 else 'FAIL'} "
          f"({boot_results['X0_VOLSIZE']['p_sharpe_gt0']:.3f})")

    # Gate 6: Trade count parity (engine P3 == engine P2)
    g6 = all(bt_results["X0_VOLSIZE"][sc]["trades"] == bt_results["X0_E5EXIT"][sc]["trades"]
             for sc in ["smart", "base", "harsh"])
    gates["G6_trade_count_parity"] = g6
    print(f"  G6 Trade count = P2:         {'PASS' if g6 else 'FAIL'}")
    for sc in ["smart", "base", "harsh"]:
        print(f"      {sc}: P3={bt_results['X0_VOLSIZE'][sc]['trades']} P2={bt_results['X0_E5EXIT'][sc]['trades']}")

    # Gate 7: Boot MDD median < P2
    g7 = boot_results["X0_VOLSIZE"]["mdd_median"] < boot_results["X0_E5EXIT"]["mdd_median"]
    gates["G7_boot_mdd_lt_p2"] = g7
    print(f"  G7 Boot MDD med < P2:        {'PASS' if g7 else 'FAIL'} "
          f"(P3={boot_results['X0_VOLSIZE']['mdd_median']:.2f}% vs P2={boot_results['X0_E5EXIT']['mdd_median']:.2f}%)")

    all_pass = all(gates.values())
    gates["all_pass"] = all_pass

    verdict = "PROMOTE" if all_pass else "HOLD"
    print(f"\n  ALL GATES: {'PASS' if all_pass else 'FAIL'}")
    if not all_pass:
        failed = [k for k, v in gates.items() if not v and k != "all_pass"]
        print(f"  Failed: {', '.join(failed)}")

    print(f"\n  VERDICT: {verdict}")

    return gates, verdict


# =========================================================================
# OUTPUT
# =========================================================================

def save_results(bt_results, boot_results, parity_data, attr, exposure_metrics,
                 gates, verdict):
    outdir = OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)

    # JSON
    payload = {
        "pipeline": "P3.5 canonical — BacktestEngine for T1/T3/T4, vectorized surrogate for T2",
        "settings": {
            "data": DATA, "start": START, "end": END, "warmup": WARMUP,
            "slow_period": SLOW, "trail_mult": TRAIL, "cash": CASH,
            "n_boot": N_BOOT, "blksz": BLKSZ, "seed": SEED,
            "target_vol": TARGET_VOL, "vol_lookback": VOL_LOOKBACK, "vol_floor": VOL_FLOOR,
        },
        "backtest_engine": bt_results,
        "bootstrap_surrogate": boot_results,
        "parity_check": parity_data,
        "attribution_delta": attr,
        "exposure_metrics": exposure_metrics,
        "promotion_gates": gates,
        "promotion_verdict": verdict,
    }
    with open(outdir / "p3_5_final_results.json", "w") as f:
        json.dump(payload, f, indent=2, default=str)

    # CSV — canonical backtest table (engine)
    with open(outdir / "p3_5_final_backtest_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy", "scenario", "pipeline", "sharpe", "cagr_pct",
                         "mdd_pct", "calmar", "trades", "win_rate_pct", "profit_factor",
                         "total_return_pct", "avg_exposure", "time_in_market_pct",
                         "avg_trade_pnl", "avg_days_held", "fees_total", "turnover_per_year"])
        for sid in STRATEGY_IDS:
            for sc in ["smart", "base", "harsh"]:
                m = bt_results[sid][sc]
                writer.writerow([sid, sc, "BacktestEngine",
                                 f"{m['sharpe']:.4f}", f"{m['cagr_pct']:.2f}",
                                 f"{m['max_drawdown_mid_pct']:.2f}", f"{m['calmar']:.4f}",
                                 m['trades'], f"{m['win_rate_pct']:.2f}",
                                 f"{m['profit_factor']}" if isinstance(m['profit_factor'], str) else f"{m['profit_factor']:.4f}",
                                 f"{m['total_return_pct']:.2f}", f"{m['avg_exposure']:.4f}",
                                 f"{m['time_in_market_pct']:.2f}", f"{m['avg_trade_pnl']:.2f}",
                                 f"{m['avg_days_held']:.2f}", f"{m['fees_total']:.2f}",
                                 f"{m['turnover_per_year']:.2f}"])

    # CSV — bootstrap table (surrogate)
    with open(outdir / "p3_5_final_bootstrap_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["strategy", "pipeline",
                         "sharpe_med", "sharpe_p5", "sharpe_p95",
                         "cagr_med", "cagr_p5", "cagr_p95",
                         "mdd_med", "mdd_p5", "mdd_p95",
                         "p_cagr_gt0", "p_sharpe_gt0"])
        for sid in STRATEGY_IDS:
            r = boot_results[sid]
            writer.writerow([sid, "vectorized_surrogate",
                             f"{r['sharpe_median']:.4f}", f"{r['sharpe_p5']:.4f}", f"{r['sharpe_p95']:.4f}",
                             f"{r['cagr_median']:.2f}", f"{r['cagr_p5']:.2f}", f"{r['cagr_p95']:.2f}",
                             f"{r['mdd_median']:.2f}", f"{r['mdd_p5']:.2f}", f"{r['mdd_p95']:.2f}",
                             f"{r['p_cagr_gt0']:.3f}", f"{r['p_sharpe_gt0']:.3f}"])

    # CSV — exposure metrics
    with open(outdir / "p3_5_final_exposure_metrics.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "definition", "value"])
        writer.writerow(["p2_avg_exposure", "mean(btc_value/nav) across all bars",
                         f"{exposure_metrics.get('p2_avg_exposure', 'N/A')}"])
        writer.writerow(["p2_time_in_market_pct", "pct of bars with exposure > 1%",
                         f"{exposure_metrics.get('p2_time_in_market_pct', 'N/A')}"])
        writer.writerow(["p2_mean_entry_weight", "Signal.target_exposure at entry (always 1.0 for binary)",
                         "1.0000"])
        writer.writerow(["p3_avg_exposure", "mean(btc_value/nav) across all bars",
                         f"{exposure_metrics.get('p3_avg_exposure', 'N/A')}"])
        writer.writerow(["p3_time_in_market_pct", "pct of bars with exposure > 1%",
                         f"{exposure_metrics.get('p3_time_in_market_pct', 'N/A')}"])
        writer.writerow(["p3_mean_entry_weight",
                         "mean of target_vol/max(rv,vol_floor) at entry, clipped [0,1]",
                         f"{exposure_metrics.get('mean_entry_weight', 'N/A')}"])
        writer.writerow(["p3_median_entry_weight", "median entry weight",
                         f"{exposure_metrics.get('median_entry_weight', 'N/A')}"])
        writer.writerow(["p3_min_entry_weight", "min entry weight",
                         f"{exposure_metrics.get('min_entry_weight', 'N/A')}"])
        writer.writerow(["p3_max_entry_weight", "max entry weight",
                         f"{exposure_metrics.get('max_entry_weight', 'N/A')}"])

    # CSV — trade count reconciliation
    with open(outdir / "p3_5_tradecount_reconciliation.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["count", "source", "pipeline", "data_window", "scenario",
                         "strategy", "explanation"])
        writer.writerow(["217", "P3.3 parity audit", "BacktestEngine (actual strategy)",
                         "full dataset (no start/end)", "base",
                         "vtrend_x0_e5exit / vtrend_x0_volsize",
                         "Full dataset run — includes trades before 2019-01-01"])
        for sid in STRATEGY_IDS:
            for sc in ["smart", "base", "harsh"]:
                nt = bt_results[sid][sc]["trades"]
                writer.writerow([str(nt), "P3.5 canonical", "BacktestEngine (actual strategy)",
                                 f"{START} to {END}", sc, sid,
                                 "Canonical engine count for restricted window"])

        for p in parity_data:
            writer.writerow([str(p["vec_trades"]), "P3.5 parity check",
                             "vectorized surrogate", f"{START} to {END}", "base",
                             p["strategy"],
                             f"Surrogate count — {'matches' if p['trades_match'] else 'DIFFERS from'} engine"])

    # CSV — pipeline audit matrix
    with open(outdir / "p3_5_pipeline_audit_matrix.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["artifact", "section", "pipeline", "strategies_via_actual_code",
                         "strategies_via_surrogate", "cost_scenario", "data_window",
                         "metric_source", "canonical"])
        writer.writerow(["p3_5_final_backtest_table.csv", "T1", "BacktestEngine",
                         "all 7", "none", "smart/base/harsh",
                         f"{START} to {END} + {WARMUP}d warmup",
                         "v10/core/metrics.py compute_metrics", "YES"])
        writer.writerow(["p3_5_final_bootstrap_table.csv", "T2", "vectorized surrogate",
                         "none", "all 7 (X0=E0_EMA21 alias, X0_E5EXIT=E5_EMA21 alias)",
                         "base (25 bps RT)",
                         f"{START} to {END} + {WARMUP}d warmup",
                         "inline _metrics_vec (Sharpe/CAGR/MDD only)", "YES (distributional)"])
        writer.writerow(["p3_5_final_exposure_metrics.csv", "T4", "BacktestEngine",
                         "X0_E5EXIT, X0_VOLSIZE", "none", "base",
                         f"{START} to {END} + {WARMUP}d warmup",
                         "v10/core/metrics.py + vol-sizing formula", "YES"])
        writer.writerow(["p3_4_backtest_table.csv", "T1 (P3.4)", "vectorized surrogate",
                         "none", "all 7 (hard aliases for X0, X0_E5EXIT)",
                         "smart/base/harsh",
                         f"{START} to {END} + {WARMUP}d warmup",
                         "inline _metrics (approximation)", "SUPERSEDED by P3.5"])
        writer.writerow(["p3_3_results.json", "P3.3", "BacktestEngine",
                         "X0_E5EXIT, X0_VOLSIZE", "none", "base",
                         "full dataset (no start/end)",
                         "v10/core/metrics.py", "YES for parity proof, different window"])

    print(f"\nResults saved to {outdir}/")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t_start = time.time()

    print("P3.5 — Canonical Final Benchmark (Reconciliation)")
    print("=" * 80)

    # Load data arrays for bootstrap
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
    print(f"  Warmup index: {wi}")

    # T1: Canonical backtest via BacktestEngine
    bt_results = run_backtests_engine()

    # T2: Bootstrap (vectorized surrogate)
    boot_results = run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T3: Parity check (engine vs vectorized)
    parity_data = run_parity_check(bt_results, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T4: Phase 3 attribution + exposure
    attr, exposure_metrics = run_phase3_attribution()

    # Promotion decision
    gates, verdict = promotion_decision(bt_results, boot_results)

    # Save all
    save_results(bt_results, boot_results, parity_data, attr, exposure_metrics, gates, verdict)

    # Final rankings (engine, harsh)
    print("\n" + "=" * 80)
    print("CANONICAL RANKINGS (harsh scenario, BacktestEngine)")
    print("=" * 80)
    harsh = {sid: bt_results[sid]["harsh"] for sid in STRATEGY_IDS}

    for metric, key, reverse in [
        ("Sharpe", "sharpe", True),
        ("CAGR%", "cagr_pct", True),
        ("MDD% (lower=better)", "max_drawdown_mid_pct", False),
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
