#!/usr/bin/env python3
"""X3 Research -- Benchmark: graduated exposure vs E0+EMA21(D1) baseline.

Hypothesis: Graduated exposure (3 tiers based on VDO conviction) improves
time-in-market and reduces missed entries while maintaining risk management
via graduated exit (trail stop reduces to core, not zero).

  Tier 1 (40%): EMA cross + D1 regime only
  Tier 2 (70%): + VDO > 0
  Tier 3 (100%): + VDO > 0.02 (strong)

Exit:
  Trail stop: tactical exit to core (40%), not full exit
  EMA cross-down: full exit (0%)

Comparison:
  BASELINE = E0+EMA21(D1) -- binary 0%/100%
  X3       = Graduated exposure (3 tiers + graduated exit)

Evaluation:
  T1: Full backtest via BacktestEngine (3 cost scenarios)
  T2: Bootstrap VCBB (500 paths, block=60)
  T3: Parity check (engine vs vectorized surrogate)
  T4: Exposure tier statistics (time spent at each tier, transitions)
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
from strategies.vtrend_ema21_d1.strategy import VTrendEma21D1Config, VTrendEma21D1Strategy
from strategies.vtrend_x3.strategy import VTrendX3Config, VTrendX3Strategy

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

# X3 graduated exposure defaults
EXPO_CORE = 0.40
EXPO_MODERATE = 0.70
EXPO_FULL = 1.00
VDO_THR = 0.0
VDO_STRONG = 0.02
TRAIL_MULT = 3.0

N_BOOT = 500
BLKSZ = 60
SEED = 42

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["E0_EMA21", "X3"]
STRATEGY_LABELS = {
    "E0_EMA21": "E0+EMA21(D1) [baseline]",
    "X3": "X3 graduated exposure",
}


def _make_strategy(sid):
    if sid == "E0_EMA21":
        return VTrendEma21D1Strategy(VTrendEma21D1Config())
    elif sid == "X3":
        return VTrendX3Strategy(VTrendX3Config(
            expo_core=EXPO_CORE,
            expo_moderate=EXPO_MODERATE,
            expo_full=EXPO_FULL,
            vdo_strong=VDO_STRONG,
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

            # Collect exit reason breakdown from trades
            exit_counts = {}
            for t in res.trades:
                exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
            results[sid][scenario]["exit_reason_counts"] = exit_counts

            # Collect entry reason breakdown
            entry_counts = {}
            for t in res.trades:
                entry_counts[t.entry_reason] = entry_counts.get(t.entry_reason, 0) + 1
            results[sid][scenario]["entry_reason_counts"] = entry_counts

    # Print table
    header = (f"{'Strategy':14s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s} {'WR%':>6s} {'PF':>7s} "
              f"{'AvgExpo':>8s} {'TiM%':>7s} {'AvgDays':>8s}")
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            pf_str = f"{m['profit_factor']:.4f}" if isinstance(m['profit_factor'], (int, float)) else str(m['profit_factor'])
            print(f"{sid:14s} {sc:6s} {m['sharpe']:8.4f} {m['cagr_pct']:8.2f} "
                  f"{m['max_drawdown_mid_pct']:8.2f} {m['calmar']:8.4f} {m['trades']:7d} "
                  f"{m['win_rate_pct']:6.1f} {pf_str:>7s} "
                  f"{m['avg_exposure']:8.4f} {m['time_in_market_pct']:7.2f} "
                  f"{m['avg_days_held']:8.2f}")

    # Print delta table (X3 - E0_EMA21)
    print(f"\n{'DELTA (X3 - BASELINE)':>30s}")
    print("-" * 80)
    for sc in ["smart", "base", "harsh"]:
        b = results["E0_EMA21"][sc]
        x = results["X3"][sc]
        d_sharpe = x["sharpe"] - b["sharpe"]
        d_cagr = x["cagr_pct"] - b["cagr_pct"]
        d_mdd = x["max_drawdown_mid_pct"] - b["max_drawdown_mid_pct"]
        d_trades = x["trades"] - b["trades"]
        d_wr = x["win_rate_pct"] - b["win_rate_pct"]
        d_expo = x["avg_exposure"] - b["avg_exposure"]
        d_tim = x["time_in_market_pct"] - b["time_in_market_pct"]
        print(f"  {sc:6s}  dSharpe={d_sharpe:+.4f}  dCAGR={d_cagr:+.2f}%  "
              f"dMDD={d_mdd:+.2f}%  dTrades={d_trades:+d}  dWR={d_wr:+.1f}%  "
              f"dExpo={d_expo:+.4f}  dTiM={d_tim:+.2f}%")

    # Print signal reason breakdown
    print(f"\n{'SIGNAL REASON BREAKDOWN (harsh)':>40s}")
    print("-" * 60)
    for sid in STRATEGY_IDS:
        m = results[sid]["harsh"]
        print(f"  {sid} entries: {m.get('entry_reason_counts', {})}")
        print(f"  {sid} exits:   {m.get('exit_reason_counts', {})}")

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


def _sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                     slow_period=SLOW, trail_mult=TRAIL_MULT, cps=0.005):
    """Vectorized E0+EMA21(D1) baseline sim."""
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


def _rebalance(cash, bq, price, target_expo, cps):
    """Rebalance portfolio to target exposure. Returns (new_cash, new_bq)."""
    nav = cash + bq * price
    if nav <= 0:
        return cash, bq
    desired_bq = (nav * target_expo) / price if price > 0 else 0.0
    delta_bq = desired_bq - bq
    if abs(delta_bq) < 1e-12:
        return cash, bq
    if delta_bq > 0:
        # Buy
        cost_per_unit = price * (1 + cps)
        max_bq = cash / cost_per_unit if cost_per_unit > 0 else 0.0
        buy_bq = min(delta_bq, max_bq)
        cash -= buy_bq * cost_per_unit
        bq += buy_bq
    else:
        # Sell
        sell_bq = min(-delta_bq, bq)
        cash += sell_bq * price * (1 - cps)
        bq -= sell_bq
    return cash, bq


# States for vectorized sim
_V_FLAT = 0
_V_POS = 1
_V_CORE = 2


def _sim_x3(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            slow_period=SLOW, trail_mult=TRAIL_MULT, cps=0.005,
            expo_core=EXPO_CORE, expo_moderate=EXPO_MODERATE,
            expo_full=EXPO_FULL, vdo_threshold=VDO_THR,
            vdo_strong=VDO_STRONG):
    """Vectorized X3 sim with graduated exposure."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p); es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)
    regime_h4 = _d1_regime_map(cl, d1_cl, d1_ct, h4_ct)

    cash = CASH; bq = 0.0; nt = 0; pk = 0.0
    st = _V_FLAT
    cur_expo = 0.0
    pending_expo = None  # target exposure from signal at prev bar
    nav = np.zeros(n)

    # Tier tracking
    tier_bars = [0, 0, 0, 0]  # flat, core, moderate, full bars
    n_rebalances = 0

    for i in range(n):
        p = cl[i]

        # Apply pending rebalance from previous bar
        if i > 0 and pending_expo is not None:
            fp = cl[i - 1]
            old_bq = bq
            cash, bq = _rebalance(cash, bq, fp, pending_expo, cps)
            if pending_expo == 0.0 and old_bq > 0:
                nt += 1  # round-trip completed
            if abs(bq - old_bq) > 1e-12:
                n_rebalances += 1
            pending_expo = None

        nav[i] = cash + bq * p

        # Track tier distribution
        if st == _V_FLAT:
            tier_bars[0] += 1
        elif cur_expo <= expo_core + 1e-9:
            tier_bars[1] += 1
        elif cur_expo <= expo_moderate + 1e-9:
            tier_bars[2] += 1
        else:
            tier_bars[3] += 1

        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if st == _V_FLAT:
            if ef[i] > es[i] and regime_h4[i]:
                # Determine initial tier
                if vd[i] > vdo_strong:
                    target = expo_full
                elif vd[i] > vdo_threshold:
                    target = expo_moderate
                else:
                    target = expo_core
                st = _V_POS
                pk = p
                cur_expo = target
                pending_expo = target

        elif st == _V_POS:
            pk = max(pk, p)

            # Trail stop → core only
            if p < pk - trail_mult * at[i]:
                st = _V_CORE
                pk = 0.0
                cur_expo = expo_core
                pending_expo = expo_core
            # EMA cross-down → full exit
            elif ef[i] < es[i]:
                st = _V_FLAT
                pk = 0.0
                cur_expo = 0.0
                pending_expo = 0.0
            else:
                # VDO-based rebalance
                if vd[i] > vdo_strong:
                    new_target = expo_full
                elif vd[i] > vdo_threshold:
                    new_target = expo_moderate
                else:
                    new_target = expo_core
                if abs(new_target - cur_expo) > 1e-9:
                    cur_expo = new_target
                    pending_expo = new_target

        elif st == _V_CORE:
            # Only exit on EMA cross-down
            if ef[i] < es[i]:
                st = _V_FLAT
                pk = 0.0
                cur_expo = 0.0
                pending_expo = 0.0

    # Close any open position at end
    if bq > 0:
        cash += bq * cl[-1] * (1 - cps)
        bq = 0.0
        nt += 1
        nav[-1] = cash

    return nav, nt, tier_bars, n_rebalances


def _run_surrogate(sid, cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, cps=0.005):
    kw = dict(slow_period=SLOW, cps=cps)
    if sid == "E0_EMA21":
        nav, nt = _sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
        return nav, nt
    elif sid == "X3":
        nav, nt, _, _ = _sim_x3(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct, **kw)
        return nav, nt
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
    h2h_sharpe = np.zeros(N_BOOT)
    h2h_cagr = np.zeros(N_BOOT)
    h2h_mdd = np.zeros(N_BOOT)

    for sid in STRATEGY_IDS:
        sharpes, cagrs, mdds = [], [], []
        t0 = time.time()
        for b_idx, (bcl, bhi, blo, bvo, btb) in enumerate(boot_paths):
            bnav, bnt = _run_surrogate(sid, bcl, bhi, blo, bvo, btb, wi, d1_cl, d1_ct, h4_ct)
            bm = _metrics_vec(bnav, wi)
            sharpes.append(bm["sharpe"])
            cagrs.append(bm["cagr"])
            mdds.append(bm["mdd"])

            if sid == "E0_EMA21":
                h2h_sharpe[b_idx] -= bm["sharpe"]
                h2h_cagr[b_idx] -= bm["cagr"]
                h2h_mdd[b_idx] -= bm["mdd"]
            elif sid == "X3":
                h2h_sharpe[b_idx] += bm["sharpe"]
                h2h_cagr[b_idx] += bm["cagr"]
                h2h_mdd[b_idx] += bm["mdd"]

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

    # Head-to-head summary
    print(f"\n  HEAD-TO-HEAD (X3 - E0_EMA21) across {N_BOOT} bootstrap paths:")
    print(f"    Sharpe: X3 wins {np.sum(h2h_sharpe > 0)}/{N_BOOT} "
          f"({np.mean(h2h_sharpe > 0)*100:.1f}%)  "
          f"mean delta={np.mean(h2h_sharpe):.4f}")
    print(f"    CAGR:   X3 wins {np.sum(h2h_cagr > 0)}/{N_BOOT} "
          f"({np.mean(h2h_cagr > 0)*100:.1f}%)  "
          f"mean delta={np.mean(h2h_cagr):.2f}%")
    print(f"    MDD:    X3 wins {np.sum(h2h_mdd < 0)}/{N_BOOT} "
          f"({np.mean(h2h_mdd < 0)*100:.1f}%)  "
          f"mean delta={np.mean(h2h_mdd):.2f}%")

    results["h2h"] = {
        "sharpe_x3_win_pct": float(np.mean(h2h_sharpe > 0) * 100),
        "sharpe_mean_delta": float(np.mean(h2h_sharpe)),
        "cagr_x3_win_pct": float(np.mean(h2h_cagr > 0) * 100),
        "cagr_mean_delta": float(np.mean(h2h_cagr)),
        "mdd_x3_win_pct": float(np.mean(h2h_mdd < 0) * 100),
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
# T4: EXPOSURE TIER STATISTICS
# =========================================================================

def run_exposure_tier_stats(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct):
    """Analyze X3 exposure distribution across tiers."""
    print("\n" + "=" * 80)
    print("T4: EXPOSURE TIER STATISTICS")
    print("=" * 80)

    for scenario_name, cps in [("smart", SCENARIOS["smart"].per_side_bps / 10_000.0),
                                ("base", SCENARIOS["base"].per_side_bps / 10_000.0),
                                ("harsh", SCENARIOS["harsh"].per_side_bps / 10_000.0)]:
        nav, nt, tier_bars, n_rebal = _sim_x3(
            cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
            cps=cps,
        )

        n_total = sum(tier_bars)
        n_report = n_total - wi  # bars in report period

        # Only count bars after warmup for percentages
        print(f"\n  {scenario_name} scenario ({nt} round-trips, {n_rebal} rebalances):")
        print(f"    {'Tier':12s} {'Bars':>7s} {'Pct':>7s}")
        print(f"    {'-'*28}")
        labels = ["flat", "core(40%)", "moderate(70%)", "full(100%)"]
        for j, label in enumerate(labels):
            pct = tier_bars[j] / n_total * 100 if n_total > 0 else 0
            print(f"    {label:12s} {tier_bars[j]:7d} {pct:6.1f}%")

        # Time-in-market = bars not flat
        tim = sum(tier_bars[1:]) / n_total * 100 if n_total > 0 else 0
        print(f"    Time-in-market: {tim:.1f}%")

        # Compare with baseline time-in-market
        nav_base, nt_base = _sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                                              cps=cps)
        # For baseline, count bars where bq > 0 (approximate)
        m = _metrics_vec(nav, wi)
        m_base = _metrics_vec(nav_base, wi)
        print(f"    X3 final NAV:       {nav[-1]:12.2f}  Sharpe={m['sharpe']:.4f}")
        print(f"    Baseline final NAV: {nav_base[-1]:12.2f}  Sharpe={m_base['sharpe']:.4f}")

    return tier_bars


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(bt_results, boot_results, parity_data, tier_bars):
    # JSON
    out = {
        "backtest": {},
        "bootstrap": {},
        "parity": parity_data,
        "tier_bars": {"flat": tier_bars[0], "core": tier_bars[1],
                      "moderate": tier_bars[2], "full": tier_bars[3]},
    }
    for sid in STRATEGY_IDS:
        out["backtest"][sid] = {}
        for sc in ["smart", "base", "harsh"]:
            m = bt_results[sid][sc].copy()
            m.pop("exit_reason_counts", None)
            m.pop("entry_reason_counts", None)
            out["backtest"][sid][sc] = m
        if sid in boot_results:
            out["bootstrap"][sid] = boot_results[sid]
    if "h2h" in boot_results:
        out["bootstrap"]["h2h"] = boot_results["h2h"]

    json_path = OUTDIR / "x3_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV backtest table
    csv_path = OUTDIR / "x3_backtest_table.csv"
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
    csv_boot = OUTDIR / "x3_bootstrap_table.csv"
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
    csv_delta = OUTDIR / "x3_delta_table.csv"
    delta_fields = ["scenario", "d_sharpe", "d_cagr_pct", "d_mdd_pct", "d_trades",
                    "d_win_rate_pct", "d_avg_exposure", "d_time_in_market_pct"]
    with open(csv_delta, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=delta_fields)
        w.writeheader()
        for sc in ["smart", "base", "harsh"]:
            b = bt_results["E0_EMA21"][sc]
            x = bt_results["X3"][sc]
            w.writerow({
                "scenario": sc,
                "d_sharpe": x["sharpe"] - b["sharpe"],
                "d_cagr_pct": x["cagr_pct"] - b["cagr_pct"],
                "d_mdd_pct": x["max_drawdown_mid_pct"] - b["max_drawdown_mid_pct"],
                "d_trades": x["trades"] - b["trades"],
                "d_win_rate_pct": x["win_rate_pct"] - b["win_rate_pct"],
                "d_avg_exposure": x["avg_exposure"] - b["avg_exposure"],
                "d_time_in_market_pct": x["time_in_market_pct"] - b["time_in_market_pct"],
            })
    print(f"Saved: {csv_delta}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 80)
    print("X3 RESEARCH: Graduated Exposure Benchmark")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  Params: slow={SLOW}, trail_mult={TRAIL_MULT}")
    print(f"  Exposure tiers: core={EXPO_CORE}, moderate={EXPO_MODERATE}, full={EXPO_FULL}")
    print(f"  VDO thresholds: tier2={VDO_THR}, tier3(strong)={VDO_STRONG}")
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

    # T4: Exposure tier stats
    tier_bars = run_exposure_tier_stats(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

    # Save
    save_results(bt_results, boot_results, parity_data, tier_bars)

    print("\n" + "=" * 80)
    print("X3 BENCHMARK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
