#!/usr/bin/env python3
"""X8 Research — Full Benchmark: E0 + stretch cap only vs E0 baseline.

X8 = E0 with one addition: stretch cap prevents entry when price > EMA(slow) + cap*ATR.
This isolates the stretch cap from X7's filter pyramid.

Tests:
  T1: Full backtest via BacktestEngine (3 cost scenarios)
  T2: Permutation test (10K shuffles)
  T3: Timescale robustness (16 slow_periods)
  T4: Bootstrap VCBB (500 paths x 16 timescales)
  T5: Parity check (engine vs vectorized surrogate)
  T6: Parameter sensitivity (slow_period x trail_mult grid)
  T7: Cost study (timescale x cost)
  T8: Trade anatomy (win rate, streaks, holding time, concentration, jackknife, fat-tail)
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
from scipy.stats import skew, kurtosis, jarque_bera

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy
from strategies.vtrend_x8.strategy import VTrendX8Config, VTrendX8Strategy

# =========================================================================
# CONSTANTS
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

# X8 default params (E0 + stretch_cap)
SLOW = 120
TRAIL = 3.0
VDO_THR = 0.0
STRETCH_CAP = 1.5

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

OUTDIR = Path(__file__).resolve().parent

STRATEGY_IDS = ["E0", "X8"]


# =========================================================================
# FAST INDICATORS (via scipy.signal.lfilter)
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
        taker_sell = np.maximum(volume - taker_buy, 0.0)
        vdr = np.zeros(n)
        mask = volume > 1e-12
        vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]
    else:
        spread = high - low
        vdr = np.zeros(n)
        mask = spread > 1e-12
        vdr[mask] = (close[mask] - low[mask]) / spread[mask] * 2.0 - 1.0
    return _ema(vdr, fast) - _ema(vdr, slow)


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


# =========================================================================
# VECTORIZED SIMS
# =========================================================================

def sim_e0(cl, hi, lo, vo, tb, wi, slow_period=120, trail_mult=3.0, cps=CPS_HARSH):
    """VTREND E0 — baseline (no D1 filter, no stretch cap)."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
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
            if ef[i] > es[i] and vd[i] > 0.0:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - trail_mult * at[i]: px = True
            elif ef[i] < es[i]: px = True
    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
    return nav, nt


def sim_x8(cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL,
           stretch_cap=STRETCH_CAP, cps=CPS_HARSH):
    """X8 = E0 + stretch cap. Identical to E0 except entry adds stretch_ok check."""
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    at = _atr(hi, lo, cl, ATR_P)
    vd = _vdo(cl, hi, lo, vo, tb, VDO_F, VDO_S)

    cash = CASH; bq = 0.0; inp = False; pe = px = False; nt = 0; pk = 0.0
    nav = np.zeros(n)

    # Track trades for anatomy
    entry_bars = []
    exit_bars = []
    exit_reasons = []

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; bq = cash / (fp * (1 + cps)); cash = 0.0; inp = True; pk = p
                entry_bars.append(i)
            elif px:
                px = False; cash = bq * fp * (1 - cps); bq = 0.0; inp = False; nt += 1
                exit_bars.append(i)
        nav[i] = cash + bq * p
        if math.isnan(at[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue
        if not inp:
            # E0 entry + stretch cap
            stretch_ok = p < es[i] + stretch_cap * at[i]
            if ef[i] > es[i] and vd[i] > 0.0 and stretch_ok:
                pe = True
        else:
            pk = max(pk, p)
            # E0 exit (identical)
            if p < pk - trail_mult * at[i]:
                px = True
                exit_reasons.append("trail")
            elif ef[i] < es[i]:
                px = True
                exit_reasons.append("trend")

    if inp and bq > 0:
        cash += bq * cl[-1] * (1 - cps); bq = 0; nt += 1; nav[-1] = cash
        exit_bars.append(n - 1)
        exit_reasons.append("eod")

    return nav, nt, entry_bars, exit_bars, exit_reasons


def _run(sid, cl, hi, lo, vo, tb, wi, slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH):
    if sid == "E0":
        nav, nt = sim_e0(cl, hi, lo, vo, tb, wi, slow_period=slow_period,
                         trail_mult=trail_mult, cps=cps)
        return nav, nt
    elif sid == "X8":
        nav, nt, _, _, _ = sim_x8(cl, hi, lo, vo, tb, wi,
                                   slow_period=slow_period, trail_mult=trail_mult, cps=cps)
        return nav, nt
    else:
        raise ValueError(f"Unknown: {sid}")


# =========================================================================
# T1: FULL BACKTEST via BacktestEngine
# =========================================================================

def run_t1_backtest():
    print("\n" + "=" * 80)
    print("T1: FULL BACKTEST via BacktestEngine (3 scenarios)")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    results = {}

    for sid in STRATEGY_IDS:
        results[sid] = {}
        for scenario in ["smart", "base", "harsh"]:
            cost_cfg = SCENARIOS[scenario]
            if sid == "E0":
                strat = VTrendStrategy(VTrendConfig(slow_period=SLOW, trail_mult=TRAIL))
            else:
                strat = VTrendX8Strategy(VTrendX8Config(
                    slow_period=SLOW, trail_mult=TRAIL, stretch_cap=STRETCH_CAP))
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
            exit_counts = {}
            for t in res.trades:
                exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
            results[sid][scenario]["exit_reason_counts"] = exit_counts

    header = (f"{'Strategy':10s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s} {'WR%':>6s} {'PF':>7s} {'AvgExpo':>8s}")
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            pf_str = f"{m['profit_factor']:.4f}" if isinstance(m['profit_factor'], (int, float)) else str(m['profit_factor'])
            print(f"{sid:10s} {sc:6s} {m['sharpe']:8.4f} {m['cagr_pct']:8.2f} "
                  f"{m['max_drawdown_mid_pct']:8.2f} {m['calmar']:8.4f} {m['trades']:7d} "
                  f"{m['win_rate_pct']:6.1f} {pf_str:>7s} {m['avg_exposure']:8.4f}")

    print(f"\n{'DELTA (X8 - E0)':>30s}")
    print("-" * 80)
    for sc in ["smart", "base", "harsh"]:
        b = results["E0"][sc]; x = results["X8"][sc]
        print(f"  {sc:6s}  dSharpe={x['sharpe']-b['sharpe']:+.4f}  dCAGR={x['cagr_pct']-b['cagr_pct']:+.2f}%  "
              f"dMDD={x['max_drawdown_mid_pct']-b['max_drawdown_mid_pct']:+.2f}%  "
              f"dTrades={x['trades']-b['trades']:+d}")

    print(f"\n{'EXIT REASON BREAKDOWN':>30s}")
    for sid in STRATEGY_IDS:
        m = results[sid]["harsh"]
        print(f"  {sid} (harsh): {m['exit_reason_counts']}")

    return results


# =========================================================================
# T2: PERMUTATION TEST
# =========================================================================

def run_t2_permutation(cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 80)
    print(f"T2: PERMUTATION TEST ({N_PERM} shuffles)")
    print("=" * 80)

    rng = np.random.default_rng(SEED)
    n = len(cl)
    results = {}

    for sid in STRATEGY_IDS:
        nav, nt = _run(sid, cl, hi, lo, vo, tb, wi)
        real_sharpe = _metrics(nav, wi, nt)["sharpe"]

        rets_post = cl[wi + 1:] / cl[wi:-1] - 1.0
        count_ge = 0
        t0 = time.time()
        for _ in range(N_PERM):
            perm = rng.permutation(rets_post)
            perm_cl = np.empty(n)
            perm_cl[:wi + 1] = cl[:wi + 1]
            for j in range(len(perm)):
                perm_cl[wi + 1 + j] = perm_cl[wi + j] * (1 + perm[j])
            perm_hi = perm_cl * (hi / np.maximum(cl, 1e-12))
            perm_lo = perm_cl * (lo / np.maximum(cl, 1e-12))
            perm_vo = vo.copy()
            perm_tb = tb.copy()

            perm_nav, perm_nt = _run(sid, perm_cl, perm_hi, perm_lo, perm_vo, perm_tb, wi)
            perm_sharpe = _metrics(perm_nav, wi, perm_nt)["sharpe"]
            if perm_sharpe >= real_sharpe:
                count_ge += 1

        p_value = (count_ge + 1) / (N_PERM + 1)
        elapsed = time.time() - t0
        results[sid] = {"real_sharpe": real_sharpe, "p_value": p_value, "count_ge": count_ge}
        print(f"  {sid:10s}  Sharpe={real_sharpe:.4f}  p={p_value:.4f}  "
              f"({count_ge}/{N_PERM} >= real)  ({elapsed:.1f}s)")

    return results


# =========================================================================
# T3: TIMESCALE ROBUSTNESS (16 TS)
# =========================================================================

def run_t3_timescale(cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 80)
    print("T3: TIMESCALE ROBUSTNESS (16 slow_periods)")
    print("=" * 80)

    results = {sid: {} for sid in STRATEGY_IDS}
    for slow_p in SLOW_PERIODS:
        for sid in STRATEGY_IDS:
            nav, nt = _run(sid, cl, hi, lo, vo, tb, wi, slow_period=slow_p)
            m = _metrics(nav, wi, nt)
            results[sid][slow_p] = m

    print(f"\n{'Slow':>6s}", end="")
    for sid in STRATEGY_IDS:
        print(f"  {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s}", end="")
    print()
    print("-" * (6 + len(STRATEGY_IDS) * 28))
    for slow_p in SLOW_PERIODS:
        print(f"{slow_p:6d}", end="")
        for sid in STRATEGY_IDS:
            m = results[sid][slow_p]
            print(f"  {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f}", end="")
        print()

    for sid in STRATEGY_IDS:
        pos = sum(1 for sp in SLOW_PERIODS if results[sid][sp]["sharpe"] > 0)
        print(f"  {sid}: {pos}/{len(SLOW_PERIODS)} positive Sharpe")

    sharpe_wins = sum(1 for sp in SLOW_PERIODS if results["X8"][sp]["sharpe"] > results["E0"][sp]["sharpe"])
    mdd_wins = sum(1 for sp in SLOW_PERIODS if results["X8"][sp]["mdd"] < results["E0"][sp]["mdd"])
    print(f"\n  X8 vs E0: Sharpe wins {sharpe_wins}/{len(SLOW_PERIODS)}, MDD wins {mdd_wins}/{len(SLOW_PERIODS)}")

    return results


# =========================================================================
# T4: BOOTSTRAP VCBB
# =========================================================================

def run_t4_bootstrap(cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 80)
    print(f"T4: BOOTSTRAP VCBB ({N_BOOT} paths, block={BLKSZ})")
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
            bnav, bnt = _run(sid, bcl, bhi, blo, bvo, btb, wi)
            bm = _metrics(bnav, wi, bnt)
            sharpes.append(bm["sharpe"])
            cagrs.append(bm["cagr"])
            mdds.append(bm["mdd"])

            if sid == "E0":
                h2h_sharpe[b_idx] -= bm["sharpe"]
                h2h_cagr[b_idx] -= bm["cagr"]
                h2h_mdd[b_idx] -= bm["mdd"]
            elif sid == "X8":
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
        print(f"  {sid:10s}  Sharpe={r['sharpe_median']:.4f} [{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"CAGR={r['cagr_median']:.2f}% [{r['cagr_p5']:.2f}, {r['cagr_p95']:.2f}]  "
              f"MDD={r['mdd_median']:.2f}% [{r['mdd_p5']:.2f}, {r['mdd_p95']:.2f}]  "
              f"P(CAGR>0)={r['p_cagr_gt0']:.3f}  ({elapsed:.1f}s)")

    print(f"\n  HEAD-TO-HEAD (X8 - E0) across {N_BOOT} bootstrap paths:")
    print(f"    Sharpe: X8 wins {np.sum(h2h_sharpe > 0)}/{N_BOOT} ({np.mean(h2h_sharpe > 0)*100:.1f}%)")
    print(f"    CAGR:   X8 wins {np.sum(h2h_cagr > 0)}/{N_BOOT} ({np.mean(h2h_cagr > 0)*100:.1f}%)")
    print(f"    MDD:    X8 wins {np.sum(h2h_mdd < 0)}/{N_BOOT} ({np.mean(h2h_mdd < 0)*100:.1f}%)")

    results["h2h"] = {
        "sharpe_x8_win_pct": float(np.mean(h2h_sharpe > 0) * 100),
        "sharpe_mean_delta": float(np.mean(h2h_sharpe)),
        "cagr_x8_win_pct": float(np.mean(h2h_cagr > 0) * 100),
        "cagr_mean_delta": float(np.mean(h2h_cagr)),
        "mdd_x8_win_pct": float(np.mean(h2h_mdd < 0) * 100),
        "mdd_mean_delta": float(np.mean(h2h_mdd)),
    }

    return results


# =========================================================================
# T5: PARITY CHECK (engine vs vectorized)
# =========================================================================

def run_t5_parity(bt_results, cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 80)
    print("T5: ENGINE vs VECTORIZED PARITY CHECK")
    print("=" * 80)

    cps_base = COST_SCENARIOS["base"]
    parity_data = []
    for sid in STRATEGY_IDS:
        nav, nt = _run(sid, cl, hi, lo, vo, tb, wi, cps=cps_base)
        m_vec = _metrics(nav, wi, nt)
        m_eng = bt_results[sid]["base"]

        match_trades = nt == m_eng["trades"]
        sharpe_diff = abs(m_vec["sharpe"] - m_eng["sharpe"])

        print(f"  {sid:10s}  Engine trades={m_eng['trades']:>4d}  Vec trades={nt:>4d}  "
              f"{'MATCH' if match_trades else 'DIFFER':>6s}  "
              f"Sharpe eng={m_eng['sharpe']:.4f}  vec={m_vec['sharpe']:.4f}  diff={sharpe_diff:.4f}")

        parity_data.append({
            "strategy": sid, "engine_trades": m_eng["trades"], "vec_trades": nt,
            "trades_match": match_trades, "sharpe_diff": sharpe_diff,
        })

    return parity_data


# =========================================================================
# T6: PARAMETER SENSITIVITY (slow_period x trail_mult + stretch_cap sweep)
# =========================================================================

def run_t6_sensitivity(cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 80)
    print("T6: PARAMETER SENSITIVITY")
    print("=" * 80)

    # 6a: slow x trail grid (same as E0 reference)
    slow_range = [60, 84, 96, 108, 120, 144, 168, 200]
    trail_range = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    results = {}
    print(f"\n  6a: slow x trail (X8 Sharpe, cap={STRETCH_CAP})")
    print(f"{'Slow':>6s}", end="")
    for tr in trail_range:
        print(f"  trail={tr:.1f}", end="")
    print()
    print("-" * (6 + len(trail_range) * 11))

    for slow_p in slow_range:
        print(f"{slow_p:6d}", end="")
        for tr in trail_range:
            nav, nt, _, _, _ = sim_x8(cl, hi, lo, vo, tb, wi,
                                       slow_period=slow_p, trail_mult=tr)
            m = _metrics(nav, wi, nt)
            results[(slow_p, tr)] = m
            print(f"  {m['sharpe']:9.4f}", end="")
        print()

    sharpe_vals = [v["sharpe"] for v in results.values()]
    spread = max(sharpe_vals) - min(sharpe_vals) if sharpe_vals else 0
    print(f"\n  Sharpe spread: {spread:.4f}")

    # 6b: stretch_cap sweep at default slow/trail
    print(f"\n  6b: stretch_cap sweep (slow={SLOW}, trail={TRAIL})")
    cap_range = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 10.0, float("inf")]
    cap_results = {}
    print(f"{'Cap':>8s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} {'Trades':>7s}")
    print("-" * 42)
    for cap in cap_range:
        nav, nt, _, _, _ = sim_x8(cl, hi, lo, vo, tb, wi, stretch_cap=cap)
        m = _metrics(nav, wi, nt)
        cap_results[cap] = m
        cap_str = f"{cap:.1f}" if cap != float("inf") else "inf"
        print(f"{cap_str:>8s} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} {m['trades']:7d}")

    results["cap_sweep"] = {str(k): v for k, v in cap_results.items()}
    return results


# =========================================================================
# T7: COST STUDY (timescale x cost)
# =========================================================================

def run_t7_cost(cl, hi, lo, vo, tb, wi):
    print("\n" + "=" * 80)
    print("T7: COST STUDY (timescale x cost)")
    print("=" * 80)

    cost_bps = [0, 10, 20, 30, 40, 50, 75, 100]
    ts_subset = [60, 120, 200, 360]

    results = {}
    print(f"\n{'Cost(bps)':>10s}", end="")
    for sp in ts_subset:
        print(f"  E0_s{sp:d}   X8_s{sp:d}", end="")
    print()
    print("-" * (10 + len(ts_subset) * 22))

    for bps in cost_bps:
        cps = bps / 2.0 / 10_000.0
        print(f"{bps:10d}", end="")
        for sp in ts_subset:
            nav_e0, nt_e0 = sim_e0(cl, hi, lo, vo, tb, wi, slow_period=sp, cps=cps)
            nav_x8, nt_x8 = _run("X8", cl, hi, lo, vo, tb, wi, slow_period=sp, cps=cps)
            m_e0 = _metrics(nav_e0, wi, nt_e0)
            m_x8 = _metrics(nav_x8, wi, nt_x8)
            results[(bps, sp)] = {"e0": m_e0, "x8": m_x8}
            print(f"  {m_e0['sharpe']:7.3f} {m_x8['sharpe']:7.3f}", end="")
        print()

    return results


# =========================================================================
# T8: TRADE ANATOMY (8 techniques)
# =========================================================================

def run_t8_trade_anatomy():
    print("\n" + "=" * 80)
    print("T8: TRADE ANATOMY (8 techniques)")
    print("=" * 80)

    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    strat = VTrendX8Strategy(VTrendX8Config(
        slow_period=SLOW, trail_mult=TRAIL, stretch_cap=STRETCH_CAP))
    eng = BacktestEngine(feed=feed, strategy=strat, cost=SCENARIOS["harsh"],
                         initial_cash=CASH, warmup_mode="no_trade")
    res = eng.run()
    trades = res.trades

    if not trades:
        print("  No trades. Skipping.")
        return {}

    returns = np.array([t.return_pct for t in trades])
    pnls = np.array([t.pnl for t in trades])
    days = np.array([t.days_held for t in trades])
    n_trades = len(trades)

    results = {}

    # T8a: Win rate / avg W/L / PF
    wins = returns > 0
    n_wins = np.sum(wins)
    wr = n_wins / n_trades * 100
    avg_w = np.mean(returns[wins]) if n_wins > 0 else 0
    avg_l = np.mean(returns[~wins]) if np.sum(~wins) > 0 else 0
    total_w = np.sum(pnls[wins]) if n_wins > 0 else 0
    total_l = abs(np.sum(pnls[~wins])) if np.sum(~wins) > 0 else 1e-12
    pf = total_w / total_l

    results["t8a"] = {"win_rate": wr, "avg_win": avg_w, "avg_loss": avg_l,
                      "profit_factor": pf, "n_trades": n_trades, "n_wins": int(n_wins)}
    print(f"\n  T8a: Win rate={wr:.1f}%, avg_W={avg_w:.2f}%, avg_L={avg_l:.2f}%, PF={pf:.3f}")

    # T8b: Streaks
    max_w = max_l = cur_w = cur_l = 0
    for r in returns:
        if r > 0:
            cur_w += 1; cur_l = 0
            if cur_w > max_w: max_w = cur_w
        else:
            cur_l += 1; cur_w = 0
            if cur_l > max_l: max_l = cur_l

    results["t8b"] = {"max_win_streak": max_w, "max_loss_streak": max_l}
    print(f"  T8b: max_win_streak={max_w}, max_loss_streak={max_l}")

    # T8c: Holding time distribution
    results["t8c"] = {
        "mean_days": float(np.mean(days)), "median_days": float(np.median(days)),
        "p10_days": float(np.percentile(days, 10)), "p90_days": float(np.percentile(days, 90)),
        "min_days": float(np.min(days)), "max_days": float(np.max(days)),
    }
    print(f"  T8c: mean={np.mean(days):.1f}d, median={np.median(days):.1f}d, "
          f"P10={np.percentile(days, 10):.1f}d, P90={np.percentile(days, 90):.1f}d")

    # T8d: MFE/MAE
    results["t8d"] = {"note": "MFE/MAE via Tier 1 trade_level suite"}
    print(f"  T8d: MFE/MAE deferred to Tier 1 trade_level suite")

    # T8e: Exit reason profitability
    exit_groups = {}
    for t in trades:
        r = t.exit_reason
        if r not in exit_groups:
            exit_groups[r] = {"count": 0, "total_pnl": 0.0, "returns": []}
        exit_groups[r]["count"] += 1
        exit_groups[r]["total_pnl"] += t.pnl
        exit_groups[r]["returns"].append(t.return_pct)

    results["t8e"] = {}
    print(f"  T8e: Exit reason breakdown:")
    for reason, data in sorted(exit_groups.items()):
        avg_ret = np.mean(data["returns"])
        wr_r = sum(1 for r in data["returns"] if r > 0) / data["count"] * 100
        results["t8e"][reason] = {
            "count": data["count"], "total_pnl": data["total_pnl"],
            "avg_return": avg_ret, "win_rate": wr_r,
        }
        print(f"    {reason:25s}  n={data['count']:4d}  PnL={data['total_pnl']:10.2f}  "
              f"avgRet={avg_ret:+.2f}%  WR={wr_r:.1f}%")

    # T8f: Payoff concentration
    sorted_pnl = np.sort(pnls)[::-1]
    cum_pnl = np.cumsum(sorted_pnl)
    total_pnl = cum_pnl[-1] if len(cum_pnl) > 0 else 1e-12

    top1_pct = sorted_pnl[0] / total_pnl * 100 if total_pnl > 0 else 0
    top3_pct = cum_pnl[min(3, n_trades) - 1] / total_pnl * 100 if total_pnl > 0 else 0
    top5_pct = cum_pnl[min(5, n_trades) - 1] / total_pnl * 100 if total_pnl > 0 else 0
    top10_pct = cum_pnl[min(10, n_trades) - 1] / total_pnl * 100 if total_pnl > 0 else 0

    sorted_abs = np.sort(np.abs(pnls))
    n_g = len(sorted_abs)
    gini = (2 * np.sum((np.arange(1, n_g + 1) * sorted_abs)) / (n_g * np.sum(sorted_abs)) - (n_g + 1) / n_g) if np.sum(sorted_abs) > 0 else 0

    results["t8f"] = {
        "top1_pct": top1_pct, "top3_pct": top3_pct, "top5_pct": top5_pct, "top10_pct": top10_pct,
        "gini": gini,
    }
    print(f"  T8f: Top-1={top1_pct:.1f}%, Top-3={top3_pct:.1f}%, Top-5={top5_pct:.1f}%, "
          f"Top-10={top10_pct:.1f}%, Gini={gini:.3f}")

    # T8g: Top-N jackknife
    print(f"  T8g: Top-N jackknife:")
    for k in [1, 3, 5]:
        if k >= n_trades:
            continue
        sorted_idx = np.argsort(pnls)[::-1]
        mask_top = np.ones(n_trades, dtype=bool)
        mask_top[sorted_idx[:k]] = False
        jk_pnl = np.sum(pnls[mask_top])
        jk_ret = jk_pnl / CASH * 100

        mask_bot = np.ones(n_trades, dtype=bool)
        mask_bot[sorted_idx[-k:]] = False
        jk_pnl_bot = np.sum(pnls[mask_bot])
        jk_ret_bot = jk_pnl_bot / CASH * 100

        results[f"t8g_top{k}"] = {"drop_top_k_return_pct": jk_ret, "drop_bottom_k_return_pct": jk_ret_bot}
        print(f"    Drop top-{k}: total_return={jk_ret:.1f}%  |  Drop bottom-{k}: total_return={jk_ret_bot:.1f}%")

    # T8h: Fat-tail statistics
    sk = float(skew(returns))
    kurt_val = float(kurtosis(returns))
    jb_stat, jb_p = jarque_bera(returns)
    tail_ratio = np.percentile(returns, 95) / abs(np.percentile(returns, 5)) if abs(np.percentile(returns, 5)) > 0 else 0

    results["t8h"] = {
        "skewness": sk, "kurtosis": kurt_val,
        "jarque_bera_stat": float(jb_stat), "jarque_bera_p": float(jb_p),
        "tail_ratio_95_5": tail_ratio,
    }
    print(f"  T8h: skew={sk:.3f}, kurt={kurt_val:.3f}, JB_p={jb_p:.4f}, tail_ratio={tail_ratio:.3f}")

    return results


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(bt_results, perm_results, ts_results, boot_results,
                 parity_data, sens_results, cost_results, anatomy_results):
    out = {
        "backtest": {},
        "permutation": perm_results,
        "timescale": {},
        "bootstrap": {},
        "parity": parity_data,
        "sensitivity": {},
        "cost_study": {},
        "trade_anatomy": {},
    }

    for sid in STRATEGY_IDS:
        out["backtest"][sid] = {}
        for sc in ["smart", "base", "harsh"]:
            m = bt_results[sid][sc].copy()
            m.pop("exit_reason_counts", None)
            out["backtest"][sid][sc] = m

        out["timescale"][sid] = {}
        for sp in SLOW_PERIODS:
            out["timescale"][sid][str(sp)] = ts_results[sid][sp]

        if sid in boot_results:
            out["bootstrap"][sid] = boot_results[sid]
    if "h2h" in boot_results:
        out["bootstrap"]["h2h"] = boot_results["h2h"]

    # Sensitivity (slow x trail grid)
    grid_sens = {k: v for k, v in sens_results.items() if isinstance(k, tuple)}
    for (sp, tr), m in grid_sens.items():
        out["sensitivity"][f"s{sp}_t{tr}"] = m

    # Cap sweep
    if "cap_sweep" in sens_results:
        out["sensitivity"]["cap_sweep"] = sens_results["cap_sweep"]

    # Cost study
    for (bps, sp), m in cost_results.items():
        out["cost_study"][f"c{bps}_s{sp}"] = {k: v for k, v in m.items()}

    # Trade anatomy
    for k, v in anatomy_results.items():
        out["trade_anatomy"][k] = v

    json_path = OUTDIR / "x8_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV backtest table
    csv_path = OUTDIR / "x8_backtest_table.csv"
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
    csv_boot = OUTDIR / "x8_bootstrap_table.csv"
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
    csv_delta = OUTDIR / "x8_delta_table.csv"
    delta_fields = ["scenario", "d_sharpe", "d_cagr_pct", "d_mdd_pct", "d_trades",
                    "d_win_rate_pct", "d_avg_days_held"]
    with open(csv_delta, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=delta_fields)
        w.writeheader()
        for sc in ["smart", "base", "harsh"]:
            b = bt_results["E0"][sc]; x = bt_results["X8"][sc]
            w.writerow({
                "scenario": sc,
                "d_sharpe": x["sharpe"] - b["sharpe"],
                "d_cagr_pct": x["cagr_pct"] - b["cagr_pct"],
                "d_mdd_pct": x["max_drawdown_mid_pct"] - b["max_drawdown_mid_pct"],
                "d_trades": x["trades"] - b["trades"],
                "d_win_rate_pct": x["win_rate_pct"] - b["win_rate_pct"],
                "d_avg_days_held": x["avg_days_held"] - b["avg_days_held"],
            })
    print(f"Saved: {csv_delta}")

    # CSV timescale table
    csv_ts = OUTDIR / "x8_timescale_table.csv"
    with open(csv_ts, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slow_period", "e0_sharpe", "e0_cagr", "e0_mdd",
                     "x8_sharpe", "x8_cagr", "x8_mdd"])
        for sp in SLOW_PERIODS:
            e0 = ts_results["E0"][sp]; x8 = ts_results["X8"][sp]
            w.writerow([sp, f"{e0['sharpe']:.4f}", f"{e0['cagr']:.2f}", f"{e0['mdd']:.2f}",
                        f"{x8['sharpe']:.4f}", f"{x8['cagr']:.2f}", f"{x8['mdd']:.2f}"])
    print(f"Saved: {csv_ts}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 80)
    print("X8 RESEARCH BENCHMARK — E0 + Stretch Cap Only")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  X8 params: slow={SLOW}, trail={TRAIL}, vdo_thr={VDO_THR}, stretch_cap={STRETCH_CAP}")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")
    print(f"  Permutation: {N_PERM} shuffles")
    print("=" * 80)

    t_start = time.time()

    # T1: Backtest (engine-based)
    bt_results = run_t1_backtest()

    # Load raw arrays
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)

    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # T5: Parity check
    parity_data = run_t5_parity(bt_results, cl, hi, lo, vo, tb, wi)

    # T3: Timescale robustness
    ts_results = run_t3_timescale(cl, hi, lo, vo, tb, wi)

    # T6: Parameter sensitivity
    sens_results = run_t6_sensitivity(cl, hi, lo, vo, tb, wi)

    # T7: Cost study
    cost_results = run_t7_cost(cl, hi, lo, vo, tb, wi)

    # T8: Trade anatomy
    anatomy_results = run_t8_trade_anatomy()

    # T2: Permutation test (slow)
    perm_results = run_t2_permutation(cl, hi, lo, vo, tb, wi)

    # T4: Bootstrap VCBB (slow)
    boot_results = run_t4_bootstrap(cl, hi, lo, vo, tb, wi)

    # Save all
    save_results(bt_results, perm_results, ts_results, boot_results,
                 parity_data, sens_results, cost_results, anatomy_results)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 80}")
    print(f"X8 BENCHMARK COMPLETE — {elapsed:.0f}s total")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
