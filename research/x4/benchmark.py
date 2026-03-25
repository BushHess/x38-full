#!/usr/bin/env python3
"""X4 Research — Entry Signal Speed: faster EMA vs breakout trigger.

Hypothesis: X0's EMA(30)/EMA(120) entry is too slow, missing wave starts.
Two options to improve entry speed:

  X4A — Faster EMAs: EMA(20)/EMA(80) instead of EMA(30)/EMA(120).
         Same 1:4 ratio, ~30% faster response. No structural change.

  X4B — Parallel breakout trigger: keep EMA(30)/EMA(120) as trend filter,
         add breakout entry (close > highest_high(20) AND volume > vol_SMA(20)).
         Breakout + D1 regime → 40% exposure immediately.
         EMA cross still required for full 100% exposure.

Comparison:
  BASELINE = X0 (E0+EMA21 D1, slow=120, fast=30)
  X4A      = X0 with slow=80 (fast=20)
  X4B      = X0 + breakout trigger (40% early, 100% on EMA cross)

Evaluation:
  T1: Full backtest via BacktestEngine (3 cost scenarios)
  T2: Bootstrap VCBB (500 paths, block=60)
  T3: Parity check (engine vs vectorized surrogate)
  T4: Signal breakdown (entry reasons, scale-up events)
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

# Strategy imports
from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy
from strategies.vtrend_x4b.strategy import VTrendX4BConfig, VTrendX4BStrategy

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

# X0 baseline params
SLOW_BASELINE = 120

# X4A params (faster EMAs)
SLOW_X4A = 80

# X4B params (breakout trigger)
SLOW_X4B = 120
BREAKOUT_LOOKBACK = 20
VOL_LOOKBACK = 20
BREAKOUT_EXPOSURE = 0.4

# Common
TRAIL_MULT = 3.0

N_BOOT = 500
BLKSZ = 60
SEED = 42

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["X0", "X4A", "X4B"]
STRATEGY_LABELS = {
    "X0": "X0 baseline (EMA 30/120)",
    "X4A": "X4A faster EMAs (EMA 20/80)",
    "X4B": "X4B breakout trigger + EMA 30/120",
}


def _make_strategy(sid):
    if sid == "X0":
        return VTrendX0Strategy(VTrendX0Config(slow_period=SLOW_BASELINE))
    elif sid == "X4A":
        return VTrendX0Strategy(VTrendX0Config(slow_period=SLOW_X4A))
    elif sid == "X4B":
        return VTrendX4BStrategy(VTrendX4BConfig(
            slow_period=SLOW_X4B,
            breakout_lookback=BREAKOUT_LOOKBACK,
            vol_lookback=VOL_LOOKBACK,
            breakout_exposure=BREAKOUT_EXPOSURE,
        ))
    else:
        raise ValueError(f"Unknown strategy: {sid}")


# =========================================================================
# T1: FULL BACKTEST via BacktestEngine
# =========================================================================

def run_backtests_engine():
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST via BacktestEngine")
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

            # Collect exit/entry reason breakdown from trades
            entry_counts = {}
            exit_counts = {}
            for t in res.trades:
                entry_counts[t.entry_reason] = entry_counts.get(t.entry_reason, 0) + 1
                exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
            results[sid][scenario]["entry_reason_counts"] = entry_counts
            results[sid][scenario]["exit_reason_counts"] = exit_counts

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

    # Print delta tables
    for test_sid in ["X4A", "X4B"]:
        print(f"\n{'DELTA (' + test_sid + ' - X0)':>35s}")
        print("-" * 85)
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

    # Print signal breakdown
    print(f"\n{'SIGNAL BREAKDOWN (harsh)':>35s}")
    print("-" * 70)
    for sid in STRATEGY_IDS:
        m = results[sid]["harsh"]
        print(f"  {sid}:")
        print(f"    Entry: {m['entry_reason_counts']}")
        print(f"    Exit:  {m['exit_reason_counts']}")

    return results


# =========================================================================
# VECTORIZED SIMS (for bootstrap)
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


def _rolling_max_vec(series, window):
    """Rolling max over previous `window` bars (no lookahead)."""
    n = len(series)
    out = np.full(n, np.nan)
    for i in range(window, n):
        out[i] = np.max(series[i - window: i])
    return out


def _sma_vec(series, window):
    """SMA over previous `window` bars (no lookahead)."""
    n = len(series)
    out = np.full(n, np.nan)
    cs = np.cumsum(series)
    for i in range(window, n):
        out[i] = (cs[i - 1] - (cs[i - window - 1] if i > window else 0.0)) / window
    return out


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


ATR_P = 14
VDO_F = 12
VDO_S = 28
VDO_THR = 0.0


def _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            slow_period=SLOW_BASELINE, trail_mult=TRAIL_MULT, cps=0.005):
    """Vectorized X0 baseline sim."""
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


def _sim_x4b(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
             slow_period=SLOW_X4B, trail_mult=TRAIL_MULT,
             breakout_lookback=BREAKOUT_LOOKBACK, vol_lookback=VOL_LOOKBACK,
             breakout_exposure=BREAKOUT_EXPOSURE, cps=0.005):
    """Vectorized X4B sim with breakout trigger + partial exposure."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

    hh = _rolling_max_vec(hi, breakout_lookback)
    vol_sma = _sma_vec(vo, vol_lookback)

    cash = CASH; bq = 0.0; state = "FLAT"; pk = 0.0; nt = 0
    # Pending signals: pe_full, pe_bo (breakout entry), pe_scale (scale up), px (exit)
    pe_full = pe_bo = pe_scale = px = False
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]

        # Execute pending signals at open (use previous bar's close as proxy)
        if i > 0:
            fp = cl[i - 1]
            if px:
                px = False
                cash += bq * fp * (1 - cps); bq = 0.0
                state = "FLAT"; nt += 1
            elif pe_full:
                pe_full = False
                if state == "BREAKOUT" and bq > 0:
                    # Scale up: sell existing partial, buy full
                    cash += bq * fp * (1 - cps); bq = 0.0
                bq = cash / (fp * (1 + cps)); cash = 0.0
                state = "FULL"; pk = p
            elif pe_scale:
                pe_scale = False
                if bq > 0:
                    cash += bq * fp * (1 - cps); bq = 0.0
                bq = cash / (fp * (1 + cps)); cash = 0.0
                state = "FULL"
            elif pe_bo:
                pe_bo = False
                # Partial entry: only use breakout_exposure fraction of cash
                alloc = cash * breakout_exposure
                bq = alloc / (fp * (1 + cps)); cash -= alloc
                state = "BREAKOUT"; pk = p

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        trend_up = ef[i] > es[i]
        trend_down = ef[i] < es[i]
        reg_ok = bool(regime_h4[i])

        bo_ok = (not math.isnan(hh[i]) and not math.isnan(vol_sma[i])
                 and p > hh[i] and vo[i] > vol_sma[i])

        if state == "FLAT":
            # Full EMA entry (higher priority)
            if trend_up and vd[i] > VDO_THR and reg_ok:
                pe_full = True
            elif bo_ok and reg_ok:
                pe_bo = True
        elif state == "BREAKOUT":
            pk = max(pk, p)
            if trend_up and vd[i] > VDO_THR:
                pe_scale = True
            elif p < pk - trail_mult * at[i]:
                px = True
            elif trend_down:
                px = True
        elif state == "FULL":
            pk = max(pk, p)
            if p < pk - trail_mult * at[i]:
                px = True
            elif trend_down:
                px = True

    if bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def _run_surrogate(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    if sid == "X0":
        return _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                        slow_period=SLOW_BASELINE, cps=cps)
    elif sid == "X4A":
        return _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                        slow_period=SLOW_X4A, cps=cps)
    elif sid == "X4B":
        return _sim_x4b(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
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

    # Per-path metrics for head-to-head
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

    # Head-to-head for each variant vs baseline
    for test_sid in ["X4A", "X4B"]:
        h2h_sharpe = boot_sharpe[test_sid] - boot_sharpe["X0"]
        h2h_cagr = boot_cagr[test_sid] - boot_cagr["X0"]
        h2h_mdd = boot_mdd[test_sid] - boot_mdd["X0"]

        print(f"\n  HEAD-TO-HEAD ({test_sid} - X0) across {N_BOOT} bootstrap paths:")
        print(f"    Sharpe: {test_sid} wins {np.sum(h2h_sharpe > 0)}/{N_BOOT} "
              f"({np.mean(h2h_sharpe > 0)*100:.1f}%)  "
              f"mean delta={np.mean(h2h_sharpe):.4f}")
        print(f"    CAGR:   {test_sid} wins {np.sum(h2h_cagr > 0)}/{N_BOOT} "
              f"({np.mean(h2h_cagr > 0)*100:.1f}%)  "
              f"mean delta={np.mean(h2h_cagr):.2f}%")
        print(f"    MDD:    {test_sid} wins {np.sum(h2h_mdd < 0)}/{N_BOOT} "
              f"({np.mean(h2h_mdd < 0)*100:.1f}%)  "
              f"mean delta={np.mean(h2h_mdd):.2f}%")

        results[f"h2h_{test_sid}"] = {
            "sharpe_win_pct": float(np.mean(h2h_sharpe > 0) * 100),
            "sharpe_mean_delta": float(np.mean(h2h_sharpe)),
            "cagr_win_pct": float(np.mean(h2h_cagr > 0) * 100),
            "cagr_mean_delta": float(np.mean(h2h_cagr)),
            "mdd_win_pct": float(np.mean(h2h_mdd < 0) * 100),
            "mdd_mean_delta": float(np.mean(h2h_mdd)),
        }

    # X4A vs X4B head-to-head
    h2h_ab_sharpe = boot_sharpe["X4B"] - boot_sharpe["X4A"]
    h2h_ab_cagr = boot_cagr["X4B"] - boot_cagr["X4A"]
    h2h_ab_mdd = boot_mdd["X4B"] - boot_mdd["X4A"]
    print(f"\n  HEAD-TO-HEAD (X4B - X4A) across {N_BOOT} bootstrap paths:")
    print(f"    Sharpe: X4B wins {np.sum(h2h_ab_sharpe > 0)}/{N_BOOT} "
          f"({np.mean(h2h_ab_sharpe > 0)*100:.1f}%)")
    print(f"    CAGR:   X4B wins {np.sum(h2h_ab_cagr > 0)}/{N_BOOT} "
          f"({np.mean(h2h_ab_cagr > 0)*100:.1f}%)")
    print(f"    MDD:    X4B wins {np.sum(h2h_ab_mdd < 0)}/{N_BOOT} "
          f"({np.mean(h2h_ab_mdd < 0)*100:.1f}%)")

    results["h2h_X4B_vs_X4A"] = {
        "sharpe_x4b_win_pct": float(np.mean(h2h_ab_sharpe > 0) * 100),
        "cagr_x4b_win_pct": float(np.mean(h2h_ab_cagr > 0) * 100),
        "mdd_x4b_win_pct": float(np.mean(h2h_ab_mdd < 0) * 100),
    }

    return results


# =========================================================================
# T3: PARITY CHECK (engine vs vectorized)
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
# T4: SIGNAL BREAKDOWN (X4B specific)
# =========================================================================

def run_signal_breakdown():
    """Analyze X4B signal patterns: breakout entries, scale-ups, exits."""
    print("\n" + "=" * 80)
    print("T4: X4B SIGNAL BREAKDOWN")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)

    for scenario in ["smart", "base", "harsh"]:
        cost_cfg = SCENARIOS[scenario]

        strat = VTrendX4BStrategy(VTrendX4BConfig(
            breakout_lookback=BREAKOUT_LOOKBACK,
            vol_lookback=VOL_LOOKBACK,
            breakout_exposure=BREAKOUT_EXPOSURE,
        ))
        eng = BacktestEngine(feed=feed, strategy=strat, cost=cost_cfg,
                             initial_cash=CASH, warmup_mode="no_trade")
        res = eng.run()

        # Count by entry/exit reason
        entry_counts = {}
        exit_counts = {}
        entry_returns = {}

        for t in res.trades:
            entry_counts[t.entry_reason] = entry_counts.get(t.entry_reason, 0) + 1
            exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
            if t.entry_reason not in entry_returns:
                entry_returns[t.entry_reason] = []
            entry_returns[t.entry_reason].append(t.return_pct)

        n_total = len(res.trades)
        print(f"\n  {scenario} scenario ({n_total} total trades):")
        print(f"    Entry reasons:")
        for reason, cnt in sorted(entry_counts.items()):
            rets = entry_returns.get(reason, [])
            avg_ret = np.mean(rets) if rets else 0
            wr = (sum(1 for r in rets if r > 0) / len(rets) * 100) if rets else 0
            print(f"      {reason:25s}  {cnt:4d} ({cnt/n_total*100:5.1f}%)  "
                  f"avgRet={avg_ret:+.2f}%  WR={wr:.1f}%")
        print(f"    Exit reasons:")
        for reason, cnt in sorted(exit_counts.items()):
            print(f"      {reason:25s}  {cnt:4d} ({cnt/n_total*100:5.1f}%)")

    # Also run X0 baseline for comparison
    print(f"\n  X0 BASELINE (harsh):")
    strat_base = VTrendX0Strategy(VTrendX0Config())
    eng_base = BacktestEngine(feed=feed, strategy=strat_base, cost=SCENARIOS["harsh"],
                              initial_cash=CASH, warmup_mode="no_trade")
    res_base = eng_base.run()
    n_trail = sum(1 for t in res_base.trades if "trail" in t.exit_reason)
    n_trend = sum(1 for t in res_base.trades if "trend" in t.exit_reason)
    avg_days = np.mean([t.days_held for t in res_base.trades]) if res_base.trades else 0
    print(f"    {len(res_base.trades)} trades, {n_trail} trail stops, {n_trend} trend exits, "
          f"avg days held: {avg_days:.1f}")


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(bt_results, boot_results, parity_data):
    # JSON
    out = {
        "backtest": {},
        "bootstrap": {},
        "parity": parity_data,
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

    json_path = OUTDIR / "x4_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV backtest table
    csv_path = OUTDIR / "x4_backtest_table.csv"
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

    # CSV bootstrap table
    csv_boot = OUTDIR / "x4_bootstrap_table.csv"
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
    csv_delta = OUTDIR / "x4_delta_table.csv"
    delta_fields = ["variant", "scenario", "d_sharpe", "d_cagr_pct", "d_mdd_pct", "d_trades",
                    "d_win_rate_pct", "d_avg_days_held", "d_avg_exposure"]
    with open(csv_delta, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=delta_fields)
        w.writeheader()
        for test_sid in ["X4A", "X4B"]:
            for sc in ["smart", "base", "harsh"]:
                b = bt_results["X0"][sc]
                x = bt_results[test_sid][sc]
                w.writerow({
                    "variant": test_sid,
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
    print("X4 RESEARCH: Entry Signal Speed")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  X0 baseline: slow={SLOW_BASELINE}, fast={max(5, SLOW_BASELINE//4)}")
    print(f"  X4A faster:  slow={SLOW_X4A}, fast={max(5, SLOW_X4A//4)}")
    print(f"  X4B breakout: slow={SLOW_X4B}, lookback={BREAKOUT_LOOKBACK}, "
          f"vol_lb={VOL_LOOKBACK}, bo_expo={BREAKOUT_EXPOSURE}")
    print(f"  Trail mult: {TRAIL_MULT}")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")
    print("=" * 80)

    # T1: Backtest
    bt_results = run_backtests_engine()

    # Load raw arrays for vectorized sims
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    # Warmup index
    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # T3: Parity check (before bootstrap to catch bugs early)
    parity_data = run_parity_check(bt_results, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T2: Bootstrap
    boot_results = run_bootstrap(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # T4: Signal breakdown
    run_signal_breakdown()

    # Save
    save_results(bt_results, boot_results, parity_data)

    print("\n" + "=" * 80)
    print("X4 BENCHMARK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
