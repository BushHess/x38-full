#!/usr/bin/env python3
"""X6 Research — Adaptive Trail + Breakeven Floor (X2 + X5 hybrid).

Hypothesis: Combine X2's adaptive trail (proven: +0.10 Sharpe, +8.2% CAGR,
68% bootstrap h2h) with X5's breakeven floor (proven: 100% WR on BE trades),
while keeping binary exposure (no partial sell) to preserve CAGR upside.

Trail stop logic:
  gain < 5%:   trail = 3×ATR          (tight, no BE floor — room to breathe)
  5% <= gain < 15%: trail = max(entry_price, peak - 4×ATR)  (mid + BE floor)
  gain >= 15%: trail = max(entry_price, peak - 5×ATR)        (wide + BE floor)

3-way comparison:
  X0  = baseline (fixed 3×ATR trail, binary exposure)
  X2  = adaptive trail only (3/4/5×ATR, no BE floor)
  X6  = adaptive trail + BE floor above tier1

Evaluation:
  T1: Full backtest via BacktestEngine (3 cost scenarios)
  T2: Bootstrap VCBB (500 paths, block=60)
  T3: Parity check (engine vs vectorized surrogate)
  T4: Exit reason analysis + BE floor hit rate
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

from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy
from strategies.vtrend_x2.strategy import VTrendX2Config, VTrendX2Strategy
from strategies.vtrend_x6.strategy import VTrendX6Config, VTrendX6Strategy

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
TRAIL_FIXED = 3.0

# X2/X6 shared adaptive trail params
TRAIL_TIGHT = 3.0
TRAIL_MID = 4.0
TRAIL_WIDE = 5.0
GAIN_TIER1 = 0.05
GAIN_TIER2 = 0.15

N_BOOT = 500
BLKSZ = 60
SEED = 42

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["X0", "X2", "X6"]
STRATEGY_LABELS = {
    "X0": "X0 baseline (fixed 3×ATR)",
    "X2": "X2 adaptive trail (3/4/5×ATR, no BE)",
    "X6": "X6 adaptive trail + BE floor",
}


def _make_strategy(sid):
    if sid == "X0":
        return VTrendX0Strategy(VTrendX0Config(slow_period=SLOW))
    elif sid == "X2":
        return VTrendX2Strategy(VTrendX2Config(
            slow_period=SLOW,
            trail_tight=TRAIL_TIGHT, trail_mid=TRAIL_MID, trail_wide=TRAIL_WIDE,
            gain_tier1=GAIN_TIER1, gain_tier2=GAIN_TIER2,
        ))
    elif sid == "X6":
        return VTrendX6Strategy(VTrendX6Config(
            slow_period=SLOW,
            trail_tight=TRAIL_TIGHT, trail_mid=TRAIL_MID, trail_wide=TRAIL_WIDE,
            gain_tier1=GAIN_TIER1, gain_tier2=GAIN_TIER2,
        ))
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# =========================================================================
# T1: FULL BACKTEST
# =========================================================================

def run_backtests_engine():
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST via BacktestEngine")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    results = {}
    all_trades = {}

    for sid in STRATEGY_IDS:
        results[sid] = {}
        all_trades[sid] = {}
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
                "fills": s.get("fills", 0),
            }

            entry_counts = {}
            exit_counts = {}
            for t in res.trades:
                entry_counts[t.entry_reason] = entry_counts.get(t.entry_reason, 0) + 1
                exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
            results[sid][scenario]["entry_reason_counts"] = entry_counts
            results[sid][scenario]["exit_reason_counts"] = exit_counts

            all_trades[sid][scenario] = res.trades

    # Print table
    header = (f"{'Strategy':8s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s} {'WR%':>6s} {'PF':>7s} "
              f"{'AvgExpo':>8s} {'TiM%':>7s} {'AvgDays':>8s} {'T/yr':>6s}")
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            pf_str = f"{m['profit_factor']:.4f}" if isinstance(m['profit_factor'], (int, float)) else str(m['profit_factor'])
            print(f"{sid:8s} {sc:6s} {m['sharpe']:8.4f} {m['cagr_pct']:8.2f} "
                  f"{m['max_drawdown_mid_pct']:8.2f} {m['calmar']:8.4f} {m['trades']:7d} "
                  f"{m['win_rate_pct']:6.1f} {pf_str:>7s} "
                  f"{m['avg_exposure']:8.4f} {m['time_in_market_pct']:7.2f} "
                  f"{m['avg_days_held']:8.2f} {m['turnover_per_year']:6.1f}")

    # Delta tables
    for test_sid in ["X2", "X6"]:
        print(f"\n{'DELTA (' + test_sid + ' - X0)':>35s}")
        print("-" * 100)
        for sc in ["smart", "base", "harsh"]:
            b = results["X0"][sc]
            x = results[test_sid][sc]
            d_sharpe = x["sharpe"] - b["sharpe"]
            d_cagr = x["cagr_pct"] - b["cagr_pct"]
            d_mdd = x["max_drawdown_mid_pct"] - b["max_drawdown_mid_pct"]
            d_trades = x["trades"] - b["trades"]
            d_wr = x["win_rate_pct"] - b["win_rate_pct"]
            d_days = x["avg_days_held"] - b["avg_days_held"]
            d_expo = x["avg_exposure"] - b["avg_exposure"]
            print(f"  {sc:6s}  dSharpe={d_sharpe:+.4f}  dCAGR={d_cagr:+.2f}%  "
                  f"dMDD={d_mdd:+.2f}%  dTrades={d_trades:+d}  dWR={d_wr:+.1f}%  "
                  f"dAvgDays={d_days:+.1f}  dExpo={d_expo:+.4f}")

    # X6 vs X2 delta
    print(f"\n{'DELTA (X6 - X2) — BE floor value-add':>45s}")
    print("-" * 100)
    for sc in ["smart", "base", "harsh"]:
        b = results["X2"][sc]
        x = results["X6"][sc]
        d_sharpe = x["sharpe"] - b["sharpe"]
        d_cagr = x["cagr_pct"] - b["cagr_pct"]
        d_mdd = x["max_drawdown_mid_pct"] - b["max_drawdown_mid_pct"]
        d_trades = x["trades"] - b["trades"]
        print(f"  {sc:6s}  dSharpe={d_sharpe:+.4f}  dCAGR={d_cagr:+.2f}%  "
              f"dMDD={d_mdd:+.2f}%  dTrades={d_trades:+d}")

    # Signal breakdown
    print(f"\n{'SIGNAL BREAKDOWN (harsh)':>35s}")
    print("-" * 70)
    for sid in STRATEGY_IDS:
        m = results[sid]["harsh"]
        print(f"  {sid}:")
        print(f"    Entry: {m['entry_reason_counts']}")
        print(f"    Exit:  {m['exit_reason_counts']}")

    return results, all_trades


# =========================================================================
# VECTORIZED SIMS
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
        alpha_w = 1.0 / period
        b = np.array([alpha_w])
        a = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr[period:]
        if len(tail) > 0:
            zi = np.array([(1.0 - alpha_w) * seed])
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


ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0


def _metrics_vec(nav, wi, nt=0):
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


def _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            slow_period=SLOW, trail_mult=TRAIL_FIXED, cps=0.005):
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


def _sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            slow_period=SLOW,
            trail_tight=TRAIL_TIGHT, trail_mid=TRAIL_MID, trail_wide=TRAIL_WIDE,
            gain_tier1=GAIN_TIER1, gain_tier2=GAIN_TIER2, cps=0.005):
    """X2: adaptive trail, no BE floor."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    ep = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p; ep = fp
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1; ep = 0.0
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            ug = (p - ep) / ep if ep > 0 else 0.0
            if ug < gain_tier1: tm = trail_tight
            elif ug < gain_tier2: tm = trail_mid
            else: tm = trail_wide
            if p < pk - tm * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def _sim_x6(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            slow_period=SLOW,
            trail_tight=TRAIL_TIGHT, trail_mid=TRAIL_MID, trail_wide=TRAIL_WIDE,
            gain_tier1=GAIN_TIER1, gain_tier2=GAIN_TIER2, cps=0.005):
    """X6: adaptive trail + breakeven floor above tier1."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)
    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    ep = 0.0
    nav = np.zeros(n)
    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe: pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p; ep = fp
            elif px: px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1; ep = 0.0
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]: pe = True
        else:
            pk = max(pk, p)
            ug = (p - ep) / ep if ep > 0 else 0.0
            # Adaptive trail + BE floor
            if ug < gain_tier1:
                trail_stop = pk - trail_tight * at[i]
            elif ug < gain_tier2:
                trail_stop = max(ep, pk - trail_mid * at[i])
            else:
                trail_stop = max(ep, pk - trail_wide * at[i])
            if p < trail_stop: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def _run_surrogate(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    if sid == "X0":
        return _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
    elif sid == "X2":
        return _sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
    elif sid == "X6":
        return _sim_x6(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# =========================================================================
# T2: BOOTSTRAP VCBB
# =========================================================================

def run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    print("\n" + "=" * 80)
    print(f"T2: SURROGATE BOOTSTRAP VCBB ({N_BOOT} paths, block={BLKSZ})")
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
    boot_sharpe = {sid: np.zeros(N_BOOT) for sid in STRATEGY_IDS}
    boot_cagr = {sid: np.zeros(N_BOOT) for sid in STRATEGY_IDS}
    boot_mdd = {sid: np.zeros(N_BOOT) for sid in STRATEGY_IDS}

    for sid in STRATEGY_IDS:
        t0 = time.time()
        for b_idx, (bcl, bhi, blo, bvo, btb) in enumerate(boot_paths):
            bnav, _ = _run_surrogate(sid, bcl, bhi, blo, bvo, btb, wi, d1_cl, d1_ct, h4_ct)
            bm = _metrics_vec(bnav, wi)
            boot_sharpe[sid][b_idx] = bm["sharpe"]
            boot_cagr[sid][b_idx] = bm["cagr"]
            boot_mdd[sid][b_idx] = bm["mdd"]

        sharpes = boot_sharpe[sid]
        cagrs = boot_cagr[sid]
        mdds = boot_mdd[sid]

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
        print(f"  {sid:8s}  Sharpe={r['sharpe_median']:.4f} [{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"CAGR={r['cagr_median']:.2f}% [{r['cagr_p5']:.2f}, {r['cagr_p95']:.2f}]  "
              f"MDD={r['mdd_median']:.2f}% [{r['mdd_p5']:.2f}, {r['mdd_p95']:.2f}]  "
              f"P(CAGR>0)={r['p_cagr_gt0']:.3f}  ({elapsed:.1f}s)")

    # Head-to-head: X2 vs X0, X6 vs X0, X6 vs X2
    pairs = [("X2", "X0"), ("X6", "X0"), ("X6", "X2")]
    for test, base in pairs:
        h2h_sharpe = boot_sharpe[test] - boot_sharpe[base]
        h2h_cagr = boot_cagr[test] - boot_cagr[base]
        h2h_mdd = boot_mdd[test] - boot_mdd[base]

        print(f"\n  HEAD-TO-HEAD ({test} - {base}) across {N_BOOT} paths:")
        print(f"    Sharpe: {test} wins {np.sum(h2h_sharpe > 0)}/{N_BOOT} "
              f"({np.mean(h2h_sharpe > 0)*100:.1f}%)  "
              f"mean delta={np.mean(h2h_sharpe):.4f}")
        print(f"    CAGR:   {test} wins {np.sum(h2h_cagr > 0)}/{N_BOOT} "
              f"({np.mean(h2h_cagr > 0)*100:.1f}%)  "
              f"mean delta={np.mean(h2h_cagr):.2f}%")
        print(f"    MDD:    {test} wins {np.sum(h2h_mdd < 0)}/{N_BOOT} "
              f"({np.mean(h2h_mdd < 0)*100:.1f}%)  "
              f"mean delta={np.mean(h2h_mdd):.2f}%")

        key = f"h2h_{test}_vs_{base}"
        results[key] = {
            "sharpe_win_pct": float(np.mean(h2h_sharpe > 0) * 100),
            "sharpe_mean_delta": float(np.mean(h2h_sharpe)),
            "cagr_win_pct": float(np.mean(h2h_cagr > 0) * 100),
            "cagr_mean_delta": float(np.mean(h2h_cagr)),
            "mdd_win_pct": float(np.mean(h2h_mdd < 0) * 100),
            "mdd_mean_delta": float(np.mean(h2h_mdd)),
        }

    return results


# =========================================================================
# T3: PARITY CHECK
# =========================================================================

def run_parity_check(bt_results, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
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

        print(f"  {sid:8s}  Engine trades={m_eng['trades']:>4d}  Vec trades={nt_vec:>4d}  "
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
# T4: EXIT ANALYSIS
# =========================================================================

def run_exit_analysis(all_trades):
    print("\n" + "=" * 80)
    print("T4: EXIT REASON ANALYSIS")
    print("=" * 80)

    analysis = {}

    for scenario in ["smart", "base", "harsh"]:
        print(f"\n  === {scenario.upper()} ===")
        for sid in STRATEGY_IDS:
            trades = all_trades[sid][scenario]
            exit_counts = {}
            exit_returns = {}
            for t in trades:
                exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
                if t.exit_reason not in exit_returns:
                    exit_returns[t.exit_reason] = []
                exit_returns[t.exit_reason].append(t.return_pct)

            total_pnl = sum(t.pnl for t in trades)
            print(f"\n  {sid}: {len(trades)} trades, PnL=${total_pnl:,.2f}")
            for reason, cnt in sorted(exit_counts.items()):
                rets = exit_returns[reason]
                avg_ret = np.mean(rets) if rets else 0
                wr = (sum(1 for r in rets if r > 0) / len(rets) * 100) if rets else 0
                print(f"    {reason:25s}  {cnt:4d} ({cnt/len(trades)*100:5.1f}%)  "
                      f"avgRet={avg_ret:+.2f}%  WR={wr:.1f}%")

        analysis[scenario] = {}
        for sid in STRATEGY_IDS:
            trades = all_trades[sid][scenario]
            analysis[scenario][sid] = {
                "n_trades": len(trades),
                "total_pnl": sum(t.pnl for t in trades),
                "winners_pnl": sum(t.pnl for t in trades if t.pnl > 0),
                "losers_pnl": sum(t.pnl for t in trades if t.pnl < 0),
            }

    return analysis


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(bt_results, boot_results, parity_data, exit_analysis):
    out = {
        "backtest": {},
        "bootstrap": {},
        "parity": parity_data,
        "exit_analysis": {},
    }
    for sid in STRATEGY_IDS:
        out["backtest"][sid] = {}
        for sc in ["smart", "base", "harsh"]:
            m = bt_results[sid][sc].copy()
            m.pop("entry_reason_counts", None)
            m.pop("exit_reason_counts", None)
            out["backtest"][sid][sc] = m
        if sid in boot_results:
            out["bootstrap"][sid] = boot_results[sid]
    for key in boot_results:
        if key.startswith("h2h"):
            out["bootstrap"][key] = boot_results[key]

    for sc in ["smart", "base", "harsh"]:
        if sc in exit_analysis:
            out["exit_analysis"][sc] = exit_analysis[sc]

    json_path = OUTDIR / "x6_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV backtest table
    csv_path = OUTDIR / "x6_backtest_table.csv"
    fields = ["strategy", "scenario", "sharpe", "cagr_pct", "max_drawdown_mid_pct",
              "calmar", "trades", "win_rate_pct", "profit_factor",
              "avg_exposure", "time_in_market_pct", "avg_days_held", "turnover_per_year"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in STRATEGY_IDS:
            for sc in ["smart", "base", "harsh"]:
                row = {"strategy": sid, "scenario": sc}
                row.update({k: bt_results[sid][sc][k] for k in fields if k not in ("strategy", "scenario")})
                w.writerow(row)
    print(f"Saved: {csv_path}")

    # CSV bootstrap
    csv_boot = OUTDIR / "x6_bootstrap_table.csv"
    boot_fields = ["strategy", "sharpe_median", "sharpe_p5", "sharpe_p95",
                   "cagr_median", "cagr_p5", "cagr_p95",
                   "mdd_median", "mdd_p5", "mdd_p95",
                   "p_cagr_gt0", "p_sharpe_gt0"]
    with open(csv_boot, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=boot_fields)
        w.writeheader()
        for sid in STRATEGY_IDS:
            if sid in boot_results:
                row = {"strategy": sid}
                row.update({k: boot_results[sid][k] for k in boot_fields if k != "strategy" and k in boot_results[sid]})
                w.writerow(row)
    print(f"Saved: {csv_boot}")

    # CSV delta table
    csv_delta = OUTDIR / "x6_delta_table.csv"
    delta_fields = ["variant", "vs", "scenario", "d_sharpe", "d_cagr_pct", "d_mdd_pct",
                    "d_trades", "d_win_rate_pct", "d_avg_days_held", "d_avg_exposure"]
    with open(csv_delta, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=delta_fields)
        w.writeheader()
        for test_sid, base_sid in [("X2", "X0"), ("X6", "X0"), ("X6", "X2")]:
            for sc in ["smart", "base", "harsh"]:
                b = bt_results[base_sid][sc]
                x = bt_results[test_sid][sc]
                w.writerow({
                    "variant": test_sid,
                    "vs": base_sid,
                    "scenario": sc,
                    "d_sharpe": x["sharpe"] - b["sharpe"],
                    "d_cagr_pct": x["cagr_pct"] - b["cagr_pct"],
                    "d_mdd_pct": x["max_drawdown_mid_pct"] - b["max_drawdown_mid_pct"],
                    "d_trades": x["trades"] - b["trades"],
                    "d_win_rate_pct": x["win_rate_pct"] - b["win_rate_pct"],
                    "d_avg_days_held": x["avg_days_held"] - b["avg_days_held"],
                    "d_avg_exposure": x["avg_exposure"] - b["avg_exposure"],
                })
    print(f"Saved: {csv_delta}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 80)
    print("X6 RESEARCH: Adaptive Trail + Breakeven Floor")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  X0: fixed trail {TRAIL_FIXED}×ATR")
    print(f"  X2: adaptive trail {TRAIL_TIGHT}/{TRAIL_MID}/{TRAIL_WIDE}×ATR "
          f"(tiers: {GAIN_TIER1*100:.0f}%/{GAIN_TIER2*100:.0f}%)")
    print(f"  X6: X2 + BE floor above {GAIN_TIER1*100:.0f}% gain")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")
    print("=" * 80)

    # T1
    bt_results, all_trades = run_backtests_engine()

    # Load arrays
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

    # T3 (before bootstrap)
    parity_data = run_parity_check(bt_results, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T2
    boot_results = run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T4
    exit_analysis = run_exit_analysis(all_trades)

    # Save
    save_results(bt_results, boot_results, parity_data, exit_analysis)

    print("\n" + "=" * 80)
    print("X6 BENCHMARK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
