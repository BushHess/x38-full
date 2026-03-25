#!/usr/bin/env python3
"""X5 Research — Partial Profit-Taking for X0 (E0+EMA21 D1).

Hypothesis: Instead of relying entirely on trailing stop, lock in partial gains
at predetermined thresholds to reduce profit give-back:

  TP1: unrealized >= +10% → sell 25% of position, move stop to breakeven
  TP2: unrealized >= +20% → sell another 25%, widen trail to 5×ATR

This addresses the pattern where trades gain +10%+ then erode via trailing stop.

Comparison:
  BASELINE = X0 (E0+EMA21 D1, binary 0/1 exposure)
  X5       = X0 + partial profit-taking (TP1=10%, TP2=20%)

Evaluation:
  T1: Full backtest via BacktestEngine (3 cost scenarios)
  T2: Bootstrap VCBB (500 paths, block=60)
  T3: Parity check (engine vs vectorized surrogate)
  T4: Trade-level analysis (TP hit rates, profit lock-in, exit reason breakdown)
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
from strategies.vtrend_x5.strategy import VTrendX5Config, VTrendX5Strategy

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
SLOW = 120
TRAIL_MULT = 3.0

# X5 take-profit params
TP1_PCT = 0.10
TP2_PCT = 0.20
TP1_SELL = 0.25
TP2_SELL = 0.25
TRAIL_MULT_TP2 = 5.0

N_BOOT = 500
BLKSZ = 60
SEED = 42

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["X0", "X5"]
STRATEGY_LABELS = {
    "X0": "X0 baseline (binary exposure, 3×ATR trail)",
    "X5": "X5 partial profit-taking (TP1=10%, TP2=20%)",
}


def _make_strategy(sid):
    if sid == "X0":
        return VTrendX0Strategy(VTrendX0Config(slow_period=SLOW))
    elif sid == "X5":
        return VTrendX5Strategy(VTrendX5Config(
            slow_period=SLOW,
            tp1_pct=TP1_PCT, tp2_pct=TP2_PCT,
            tp1_sell_frac=TP1_SELL, tp2_sell_frac=TP2_SELL,
            trail_mult_tp2=TRAIL_MULT_TP2,
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
    all_trades = {}  # store trades for T4 analysis

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

            # Collect exit/entry reason breakdown
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
              f"{'AvgExpo':>8s} {'TiM%':>7s} {'AvgDays':>8s} {'T/yr':>6s} {'Fills':>6s}")
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
                  f"{m['avg_days_held']:8.2f} {m['turnover_per_year']:6.1f} {m['fills']:6d}")

    # Delta table
    print(f"\n{'DELTA (X5 - X0)':>35s}")
    print("-" * 100)
    for sc in ["smart", "base", "harsh"]:
        b = results["X0"][sc]
        x = results["X5"][sc]
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
            slow_period=SLOW, trail_mult=TRAIL_MULT, cps=0.005):
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


def _sim_x5(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            slow_period=SLOW, trail_mult=TRAIL_MULT,
            tp1_pct=TP1_PCT, tp2_pct=TP2_PCT,
            tp1_sell=TP1_SELL, tp2_sell=TP2_SELL,
            trail_mult_tp2=TRAIL_MULT_TP2, cps=0.005):
    """Vectorized X5 sim with partial profit-taking."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

    cash = CASH; bq = 0.0; nt = 0; pk = 0.0; ep = 0.0  # ep = entry price
    # state: 0=FLAT, 1=LONG_FULL, 2=LONG_T1, 3=LONG_T2
    state = 0
    # Pending signals: pe=pending entry, px=pending exit, ptp1=pending tp1, ptp2=pending tp2
    pe = px = ptp1 = ptp2 = False
    nav = np.zeros(n)

    for i in range(n):
        p = cl[i]

        # Execute pending signals at open (use previous close as proxy)
        if i > 0:
            fp = cl[i - 1]
            if px:
                px = False
                cash += bq * fp * (1 - cps); bq = 0.0
                state = 0; nt += 1; pk = 0.0; ep = 0.0
            elif pe:
                pe = False
                bq = cash / (fp * (1 + cps)); cash = 0.0
                state = 1; pk = p; ep = fp
            elif ptp1:
                ptp1 = False
                # Sell tp1_sell fraction of position
                sell_qty = bq * tp1_sell
                cash += sell_qty * fp * (1 - cps)
                bq -= sell_qty
                state = 2
            elif ptp2:
                ptp2 = False
                # Sell tp2_sell fraction of ORIGINAL position
                # At this point bq = (1 - tp1_sell) * original
                # We want to sell tp2_sell * original = tp2_sell / (1-tp1_sell) * current_bq
                sell_qty = bq * (tp2_sell / (1.0 - tp1_sell))
                if sell_qty > bq:
                    sell_qty = bq
                cash += sell_qty * fp * (1 - cps)
                bq -= sell_qty
                state = 3

        nav[i] = cash + bq * p

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if state == 0:  # FLAT
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            unrealized = (p - ep) / ep if ep > 0 else 0.0

            # Take-profit checks (before exit checks)
            if state == 1 and unrealized >= tp1_pct:
                ptp1 = True
                continue
            if state == 2 and unrealized >= tp2_pct:
                ptp2 = True
                continue

            # Trailing stop computation per state
            if state == 1:  # LONG_FULL
                trail_stop = pk - trail_mult * at[i]
            elif state == 2:  # LONG_T1 (breakeven floor)
                trail_stop = max(ep, pk - trail_mult * at[i])
            else:  # state == 3, LONG_T2 (wider trail)
                trail_stop = pk - trail_mult_tp2 * at[i]

            if p < trail_stop:
                px = True
            elif ef[i] < es[i]:
                px = True

    if bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def _run_surrogate(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    if sid == "X0":
        return _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
    elif sid == "X5":
        return _sim_x5(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=cps)
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

    # Head-to-head
    h2h_sharpe = boot_sharpe["X5"] - boot_sharpe["X0"]
    h2h_cagr = boot_cagr["X5"] - boot_cagr["X0"]
    h2h_mdd = boot_mdd["X5"] - boot_mdd["X0"]

    print(f"\n  HEAD-TO-HEAD (X5 - X0) across {N_BOOT} bootstrap paths:")
    print(f"    Sharpe: X5 wins {np.sum(h2h_sharpe > 0)}/{N_BOOT} "
          f"({np.mean(h2h_sharpe > 0)*100:.1f}%)  "
          f"mean delta={np.mean(h2h_sharpe):.4f}")
    print(f"    CAGR:   X5 wins {np.sum(h2h_cagr > 0)}/{N_BOOT} "
          f"({np.mean(h2h_cagr > 0)*100:.1f}%)  "
          f"mean delta={np.mean(h2h_cagr):.2f}%")
    print(f"    MDD:    X5 wins {np.sum(h2h_mdd < 0)}/{N_BOOT} "
          f"({np.mean(h2h_mdd < 0)*100:.1f}%)  "
          f"mean delta={np.mean(h2h_mdd):.2f}%")

    results["h2h_X5"] = {
        "sharpe_win_pct": float(np.mean(h2h_sharpe > 0) * 100),
        "sharpe_mean_delta": float(np.mean(h2h_sharpe)),
        "cagr_win_pct": float(np.mean(h2h_cagr > 0) * 100),
        "cagr_mean_delta": float(np.mean(h2h_cagr)),
        "mdd_win_pct": float(np.mean(h2h_mdd < 0) * 100),
        "mdd_mean_delta": float(np.mean(h2h_mdd)),
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
# T4: TRADE-LEVEL ANALYSIS (X5 profit-taking patterns)
# =========================================================================

def run_trade_analysis(all_trades):
    print("\n" + "=" * 80)
    print("T4: TRADE-LEVEL ANALYSIS — PROFIT-TAKING PATTERNS")
    print("=" * 80)

    analysis = {}

    for scenario in ["smart", "base", "harsh"]:
        x0_trades = all_trades["X0"][scenario]
        x5_trades = all_trades["X5"][scenario]

        # X0 analysis: how many trades hit 10%, 20% thresholds?
        # (We can approximate from return_pct — note: return_pct is exit-based,
        # but it gives us a sense of peak unrealized gain)
        x0_above_10 = sum(1 for t in x0_trades if t.return_pct > 10.0)
        x0_above_20 = sum(1 for t in x0_trades if t.return_pct > 20.0)

        # X5 exit reason breakdown
        x5_exit_counts = {}
        x5_exit_returns = {}
        for t in x5_trades:
            x5_exit_counts[t.exit_reason] = x5_exit_counts.get(t.exit_reason, 0) + 1
            if t.exit_reason not in x5_exit_returns:
                x5_exit_returns[t.exit_reason] = []
            x5_exit_returns[t.exit_reason].append(t.return_pct)

        # Profit stats
        x0_total_pnl = sum(t.pnl for t in x0_trades)
        x5_total_pnl = sum(t.pnl for t in x5_trades)

        x0_winners_pnl = sum(t.pnl for t in x0_trades if t.pnl > 0)
        x5_winners_pnl = sum(t.pnl for t in x5_trades if t.pnl > 0)

        x0_losers_pnl = sum(t.pnl for t in x0_trades if t.pnl < 0)
        x5_losers_pnl = sum(t.pnl for t in x5_trades if t.pnl < 0)

        print(f"\n  === {scenario.upper()} ===")
        print(f"\n  X0 baseline: {len(x0_trades)} trades, "
              f"{x0_above_10} exit >10%, {x0_above_20} exit >20%")
        print(f"    Total PnL: ${x0_total_pnl:,.2f}  "
              f"Winners: ${x0_winners_pnl:,.2f}  Losers: ${x0_losers_pnl:,.2f}")

        print(f"\n  X5 partial TP: {len(x5_trades)} trades")
        print(f"    Total PnL: ${x5_total_pnl:,.2f}  "
              f"Winners: ${x5_winners_pnl:,.2f}  Losers: ${x5_losers_pnl:,.2f}")

        print(f"    Exit reasons:")
        for reason, cnt in sorted(x5_exit_counts.items()):
            rets = x5_exit_returns.get(reason, [])
            avg_ret = np.mean(rets) if rets else 0
            wr = (sum(1 for r in rets if r > 0) / len(rets) * 100) if rets else 0
            print(f"      {reason:25s}  {cnt:4d} ({cnt/len(x5_trades)*100:5.1f}%)  "
                  f"avgRet={avg_ret:+.2f}%  WR={wr:.1f}%")

        analysis[scenario] = {
            "x0_trades": len(x0_trades),
            "x0_above_10pct": x0_above_10,
            "x0_above_20pct": x0_above_20,
            "x0_total_pnl": x0_total_pnl,
            "x5_trades": len(x5_trades),
            "x5_total_pnl": x5_total_pnl,
            "x5_exit_counts": x5_exit_counts,
            "pnl_delta": x5_total_pnl - x0_total_pnl,
        }

    return analysis


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(bt_results, boot_results, parity_data, trade_analysis):
    # JSON
    out = {
        "backtest": {},
        "bootstrap": {},
        "parity": parity_data,
        "trade_analysis": {},
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
        if sc in trade_analysis:
            ta = trade_analysis[sc].copy()
            ta.pop("x5_exit_counts", None)  # not JSON-friendly as-is
            out["trade_analysis"][sc] = ta

    json_path = OUTDIR / "x5_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV backtest table
    csv_path = OUTDIR / "x5_backtest_table.csv"
    fields = ["strategy", "scenario", "sharpe", "cagr_pct", "max_drawdown_mid_pct",
              "calmar", "trades", "win_rate_pct", "profit_factor",
              "avg_exposure", "time_in_market_pct", "avg_days_held",
              "turnover_per_year", "fills"]
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
    csv_boot = OUTDIR / "x5_bootstrap_table.csv"
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
    csv_delta = OUTDIR / "x5_delta_table.csv"
    delta_fields = ["scenario", "d_sharpe", "d_cagr_pct", "d_mdd_pct", "d_trades",
                    "d_win_rate_pct", "d_avg_days_held", "d_avg_exposure"]
    with open(csv_delta, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=delta_fields)
        w.writeheader()
        for sc in ["smart", "base", "harsh"]:
            b = bt_results["X0"][sc]
            x = bt_results["X5"][sc]
            w.writerow({
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
    print("X5 RESEARCH: Partial Profit-Taking")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  X0 baseline: slow={SLOW}, trail={TRAIL_MULT}")
    print(f"  X5 TP levels: TP1={TP1_PCT*100:.0f}% (sell {TP1_SELL*100:.0f}%), "
          f"TP2={TP2_PCT*100:.0f}% (sell {TP2_SELL*100:.0f}%)")
    print(f"  X5 trail post-TP2: {TRAIL_MULT_TP2}×ATR")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")
    print("=" * 80)

    # T1: Backtest
    bt_results, all_trades = run_backtests_engine()

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

    # T4: Trade analysis
    trade_analysis = run_trade_analysis(all_trades)

    # Save
    save_results(bt_results, boot_results, parity_data, trade_analysis)

    print("\n" + "=" * 80)
    print("X5 BENCHMARK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
