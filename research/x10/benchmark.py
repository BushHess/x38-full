#!/usr/bin/env python3
"""X10 Research — Multi-TP Ladder for E5+EMA21D1.

Hypothesis: Partial exits at fixed take-profit levels (in R-multiples) lock
profit earlier, reducing per-trade drawdown and MDD.

Counter-hypothesis: Trend-following profits come from fat right tails.
Cutting winners early via fixed TPs attacks exactly this mechanism,
reducing CAGR more than it reduces MDD → worse risk-adjusted returns.

Variants (factorial):
  FULL — E5+EMA21D1 baseline (100% exit at trail/trend)
  TP2  — 2-level: 50% at TP1(1.5R), 50% trail
  TP3  — 3-level: 30% at TP1(1.5R), 30% at TP2(2.2R), 20% at TP3(3.0R), 20% trail

R = trail_mult × RATR at entry bar = initial risk per unit.

Tests:
  T1: Vectorized factorial (3 variants × 3 cost scenarios)
  T2: Timescale robustness (16 slow_periods × 3 variants)
  T3: Bootstrap VCBB (500 paths × 3 variants, head-to-head)
  T4: TP1 threshold sweep (0.5R to 3.0R, 2-level 50/50)
  T5: Trade anatomy — per-trade partial exit breakdown
  T6: Per-trade drawdown — does partial exit reduce intra-trade MDD?

Note: Uses vectorized sim only (no BacktestEngine). The engine's
target_exposure approach rebalances to maintain NAV fraction, which differs
from selling a fixed fraction of the original position. Vectorized sim
gives precise control over partial exit mechanics.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import lfilter
from scipy.stats import skew, kurtosis

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365

VDO_F = 12
VDO_S = 28
VDO_THR = 0.0

# E5+EMA21D1 default params
SLOW = 120
TRAIL = 3.0
D1_EMA_P = 21

# Robust ATR params
RATR_CAP_Q = 0.90
RATR_CAP_LB = 100
RATR_PERIOD = 20

SLOW_PERIODS = [30, 48, 60, 72, 84, 96, 108, 120, 144, 168, 200, 240, 300, 360, 500, 720]

N_BOOT = 500
BLKSZ = 60
SEED = 42

COST_SCENARIOS = {
    "smart": SCENARIOS["smart"].per_side_bps / 10_000.0,
    "base": SCENARIOS["base"].per_side_bps / 10_000.0,
    "harsh": SCENARIOS["harsh"].per_side_bps / 10_000.0,
}
CPS_HARSH = COST_SCENARIOS["harsh"]

OUTDIR = Path(__file__).resolve().parent

# TP level definitions
# Each: list of (threshold_R, fraction_of_original_to_sell)
TP2_LEVELS = [(1.5, 0.50)]                                     # 50% at 1.5R, 50% trail
TP3_LEVELS = [(1.5, 0.30), (2.2, 0.30), (3.0, 0.20)]          # 80% via TP, 20% trail

STRATEGY_IDS = ["FULL", "TP2", "TP3"]
STRATEGY_TP_MAP = {
    "FULL": None,
    "TP2": TP2_LEVELS,
    "TP3": TP3_LEVELS,
}

TP_SWEEP_RANGE = [round(x, 2) for x in np.arange(0.50, 3.25, 0.25)]


# =========================================================================
# FAST INDICATORS (vectorized)
# =========================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    b = np.array([alpha])
    a = np.array([1.0, -(1.0 - alpha)])
    zi = np.array([(1.0 - alpha) * series[0]])
    out, _ = lfilter(b, a, series, zi=zi)
    return out


def _robust_atr(high, low, close,
                cap_q=RATR_CAP_Q, cap_lb=RATR_CAP_LB, period=RATR_PERIOD):
    """Robust ATR: cap TR at rolling Q90, then Wilder EMA."""
    prev_cl = np.empty_like(close)
    prev_cl[0] = close[0]
    prev_cl[1:] = close[:-1]
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)))

    n = len(tr)

    windows = sliding_window_view(tr, cap_lb)
    q_vals = np.percentile(windows, cap_q * 100, axis=1)

    tr_cap = np.full(n, np.nan)
    num = n - cap_lb
    tr_cap[cap_lb:] = np.minimum(tr[cap_lb:], q_vals[:num])

    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        alpha_w = 1.0 / period
        b_w = np.array([alpha_w])
        a_w = np.array([1.0, -(1.0 - alpha_w)])
        tail = tr_cap[s + period:]
        if len(tail) > 0:
            zi_w = np.array([(1.0 - alpha_w) * ratr[s + period - 1]])
            smoothed, _ = lfilter(b_w, a_w, tail, zi=zi_w)
            ratr[s + period:] = smoothed

    return ratr


def _vdo(close, high, low, volume, taker_buy, fast=VDO_F, slow=VDO_S):
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
    mu = np.mean(rets)
    std = np.std(rets, ddof=0)
    sharpe = (mu / std * ANN) if std > 1e-12 else 0.0
    total_ret = navs[-1] / navs[0] - 1.0
    yrs = len(rets) / (6.0 * 365.25)
    cagr = ((1 + total_ret) ** (1.0 / yrs) - 1.0) * 100 if yrs > 0 and total_ret > -1 else -100.0
    peak = np.maximum.accumulate(navs)
    dd = 1.0 - navs / peak
    mdd = np.max(dd) * 100
    calmar = cagr / mdd if mdd > 0.01 else 0.0
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd, "calmar": calmar, "trades": nt}


# =========================================================================
# D1 REGIME FILTER
# =========================================================================

def _compute_d1_regime(h4_ct, d1_cl, d1_ct, d1_ema_period=D1_EMA_P):
    """Compute D1 EMA regime and map to H4 close_time grid."""
    d1_ema = _ema(d1_cl, d1_ema_period)
    d1_regime = d1_cl > d1_ema

    n_h4 = len(h4_ct)
    regime_h4 = np.zeros(n_h4, dtype=np.bool_)
    d1_idx = 0
    n_d1 = len(d1_cl)
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_h4[i] = d1_regime[d1_idx]

    return regime_h4


# =========================================================================
# VECTORIZED SIM: E5+EMA21D1 with Multi-TP Ladder
# =========================================================================

def sim_e5_d1_tp(cl, hi, lo, vo, tb, regime_h4, wi,
                 slow_period=SLOW, trail_mult=TRAIL,
                 tp_levels=None, cps=CPS_HARSH,
                 track_trades=False):
    """E5+EMA21D1 vectorized sim with optional multi-TP ladder.

    tp_levels: list of (threshold_R, fraction_of_original)
        e.g. [(1.5, 0.30), (2.2, 0.30), (3.0, 0.20)]
        Remaining = 1.0 - sum(fractions) exits at trail/trend.
        If None: full position exits at trail/trend (baseline).

    Returns (nav, nt) or (nav, nt, trades_list) if track_trades=True.
    """
    n = len(cl)
    fast_p = max(5, slow_period // 4)
    ef = _ema(cl, fast_p)
    es = _ema(cl, slow_period)
    ratr = _robust_atr(hi, lo, cl)
    vd = _vdo(cl, hi, lo, vo, tb)

    cash = CASH
    bq = 0.0
    original_bq = 0.0
    inp = False
    pe = px = False
    nt = 0
    pk = 0.0
    entry_px = 0.0
    ratr_at_entry = 0.0
    exit_reason = ""

    # TP state
    n_tp = len(tp_levels) if tp_levels else 0
    tp_hit = [False] * n_tp
    tp_sell_pending = 0.0

    nav = np.zeros(n)

    # Trade tracking
    trades_list = [] if track_trades else None
    cur_entry_bar = 0
    cur_entry_px = 0.0
    cur_entry_cost = 0.0
    cur_peak = 0.0
    cur_n_tp_hits = 0
    cur_tp_frac = 0.0
    cur_total_received = 0.0

    for i in range(n):
        p = cl[i]

        if i > 0:
            fp = cl[i - 1]

            if pe:
                pe = False
                entry_px = fp
                ratr_at_entry = ratr[i - 1] if not math.isnan(ratr[i - 1]) else 0.0
                bq = cash / (fp * (1 + cps))
                original_bq = bq
                cash = 0.0
                inp = True
                pk = p
                tp_hit = [False] * n_tp
                tp_sell_pending = 0.0
                if track_trades:
                    cur_entry_bar = i
                    cur_entry_px = fp
                    cur_entry_cost = original_bq * fp * (1 + cps)
                    cur_peak = p
                    cur_n_tp_hits = 0
                    cur_tp_frac = 0.0
                    cur_total_received = 0.0
            else:
                # Execute pending TP sells
                if tp_sell_pending > 0 and bq > 0:
                    sell_qty = min(tp_sell_pending, bq)
                    received = sell_qty * fp * (1 - cps)
                    cash += received
                    bq -= sell_qty
                    if track_trades:
                        cur_total_received += received
                    tp_sell_pending = 0.0
                    if bq < 1e-12:
                        bq = 0.0
                        inp = False
                        nt += 1
                        if track_trades:
                            R_val = trail_mult * ratr_at_entry if ratr_at_entry > 0 else 1.0
                            pnl_pct = (cur_total_received / cur_entry_cost - 1) * 100 if cur_entry_cost > 0 else 0
                            trades_list.append({
                                "entry_bar": cur_entry_bar, "exit_bar": i,
                                "entry_px": cur_entry_px, "peak_px": cur_peak,
                                "mfe_pct": (cur_peak / cur_entry_px - 1) * 100,
                                "mfe_R": (cur_peak - cur_entry_px) / R_val,
                                "pnl_pct": pnl_pct, "R": R_val,
                                "bars_held": i - cur_entry_bar,
                                "n_tp_hits": cur_n_tp_hits,
                                "tp_frac_exited": cur_tp_frac,
                                "final_exit_reason": "tp_full",
                            })

                # Execute full exit of remaining
                if px:
                    px = False
                    if bq > 0:
                        received = bq * fp * (1 - cps)
                        cash += received
                        if track_trades:
                            cur_total_received += received
                        bq = 0.0
                        inp = False
                        nt += 1
                        if track_trades:
                            R_val = trail_mult * ratr_at_entry if ratr_at_entry > 0 else 1.0
                            pnl_pct = (cur_total_received / cur_entry_cost - 1) * 100 if cur_entry_cost > 0 else 0
                            trades_list.append({
                                "entry_bar": cur_entry_bar, "exit_bar": i,
                                "entry_px": cur_entry_px, "peak_px": cur_peak,
                                "mfe_pct": (cur_peak / cur_entry_px - 1) * 100,
                                "mfe_R": (cur_peak - cur_entry_px) / R_val,
                                "pnl_pct": pnl_pct, "R": R_val,
                                "bars_held": i - cur_entry_bar,
                                "n_tp_hits": cur_n_tp_hits,
                                "tp_frac_exited": cur_tp_frac,
                                "final_exit_reason": exit_reason,
                            })

        nav[i] = cash + bq * p

        if math.isnan(ratr[i]) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if track_trades:
                cur_peak = max(cur_peak, p)

            # Check TP levels
            if n_tp > 0 and ratr_at_entry > 0:
                R = trail_mult * ratr_at_entry
                for j in range(n_tp):
                    if not tp_hit[j]:
                        tp_thr, tp_frac = tp_levels[j]
                        if p - entry_px >= tp_thr * R:
                            tp_hit[j] = True
                            tp_sell_pending += tp_frac * original_bq
                            if track_trades:
                                cur_n_tp_hits += 1
                                cur_tp_frac += tp_frac

            # Trail/trend exit (for remaining position)
            trail_stop = pk - trail_mult * ratr[i]
            if p < trail_stop:
                exit_reason = "trail_stop"
                px = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                px = True

    # Close open position at end
    if inp and bq > 0:
        received = bq * cl[-1] * (1 - cps)
        if track_trades:
            cur_total_received += received
        cash += received
        bq = 0
        nt += 1
        nav[-1] = cash
        if track_trades:
            R_val = trail_mult * ratr_at_entry if ratr_at_entry > 0 else 1.0
            pnl_pct = (cur_total_received / cur_entry_cost - 1) * 100 if cur_entry_cost > 0 else 0
            trades_list.append({
                "entry_bar": cur_entry_bar, "exit_bar": n - 1,
                "entry_px": cur_entry_px, "peak_px": cur_peak,
                "mfe_pct": (cur_peak / cur_entry_px - 1) * 100,
                "mfe_R": (cur_peak - cur_entry_px) / R_val,
                "pnl_pct": pnl_pct, "R": R_val,
                "bars_held": n - 1 - cur_entry_bar,
                "n_tp_hits": cur_n_tp_hits,
                "tp_frac_exited": cur_tp_frac,
                "final_exit_reason": "eod",
            })

    if track_trades:
        return nav, nt, trades_list
    return nav, nt


def _run_vec(sid, cl, hi, lo, vo, tb, regime_h4, wi,
             slow_period=SLOW, trail_mult=TRAIL, cps=CPS_HARSH,
             track_trades=False):
    """Dispatch to sim with correct tp_levels for strategy ID."""
    tp = STRATEGY_TP_MAP.get(sid)
    return sim_e5_d1_tp(cl, hi, lo, vo, tb, regime_h4, wi,
                        slow_period=slow_period, trail_mult=trail_mult,
                        tp_levels=tp, cps=cps, track_trades=track_trades)


# =========================================================================
# T1: VECTORIZED FACTORIAL (3 variants × 3 cost scenarios)
# =========================================================================

def run_t1_factorial(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T1: VECTORIZED FACTORIAL (3 variants × 3 cost scenarios)")
    print("=" * 80)

    results = {}
    for sid in STRATEGY_IDS:
        results[sid] = {}
        for scenario, cps_val in COST_SCENARIOS.items():
            nav, nt = _run_vec(sid, cl, hi, lo, vo, tb, regime_h4, wi, cps=cps_val)
            m = _metrics(nav, wi, nt)
            results[sid][scenario] = m

    # Print table
    header = (f"{'Strategy':8s} {'Scen':6s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
              f"{'Calmar':>8s} {'Trades':>7s}")
    print(f"\n{header}")
    print("-" * len(header))
    for sid in STRATEGY_IDS:
        for sc in ["smart", "base", "harsh"]:
            m = results[sid][sc]
            print(f"{sid:8s} {sc:6s} {m['sharpe']:8.4f} {m['cagr']:8.2f} "
                  f"{m['mdd']:8.2f} {m['calmar']:8.4f} {m['trades']:7d}")

    # Delta table
    print(f"\n{'DELTA vs FULL baseline':>30s}")
    print("-" * 80)
    for tp_sid in ["TP2", "TP3"]:
        for sc in ["smart", "base", "harsh"]:
            b = results["FULL"][sc]
            x = results[tp_sid][sc]
            print(f"  {tp_sid:4s} {sc:6s}  dSharpe={x['sharpe']-b['sharpe']:+.4f}  "
                  f"dCAGR={x['cagr']-b['cagr']:+.2f}%  "
                  f"dMDD={x['mdd']-b['mdd']:+.2f}%  "
                  f"dCalmar={x['calmar']-b['calmar']:+.4f}  "
                  f"dTrades={x['trades']-b['trades']:+d}")

    return results


# =========================================================================
# T2: TIMESCALE ROBUSTNESS (16 TS × 3 variants)
# =========================================================================

def run_t2_timescale(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T2: TIMESCALE ROBUSTNESS (16 slow_periods)")
    print("=" * 80)

    results = {sid: {} for sid in STRATEGY_IDS}
    for slow_p in SLOW_PERIODS:
        for sid in STRATEGY_IDS:
            nav, nt = _run_vec(sid, cl, hi, lo, vo, tb, regime_h4, wi,
                               slow_period=slow_p)
            m = _metrics(nav, wi, nt)
            results[sid][slow_p] = m

    # Print table
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

    # Head-to-head wins
    for tp_sid in ["TP2", "TP3"]:
        sharpe_wins = sum(1 for sp in SLOW_PERIODS
                          if results[tp_sid][sp]["sharpe"] > results["FULL"][sp]["sharpe"])
        mdd_wins = sum(1 for sp in SLOW_PERIODS
                       if results[tp_sid][sp]["mdd"] < results["FULL"][sp]["mdd"])
        cagr_wins = sum(1 for sp in SLOW_PERIODS
                        if results[tp_sid][sp]["cagr"] > results["FULL"][sp]["cagr"])
        calmar_wins = sum(1 for sp in SLOW_PERIODS
                          if results[tp_sid][sp]["calmar"] > results["FULL"][sp]["calmar"])
        print(f"\n  {tp_sid} vs FULL:  Sharpe {sharpe_wins}/16  CAGR {cagr_wins}/16  "
              f"MDD {mdd_wins}/16  Calmar {calmar_wins}/16")

    return results


# =========================================================================
# T3: BOOTSTRAP VCBB (500 paths × 3 variants, head-to-head)
# =========================================================================

def run_t3_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print(f"T3: BOOTSTRAP VCBB ({N_BOOT} paths, block={BLKSZ})")
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
        bcl, bhi, blo, bvo, btb = gen_path_vcbb(
            cr, hr, lr, vol_r, tb_r, n_trans, BLKSZ, p0, rng, vcbb,
        )
        boot_paths.append((
            np.concatenate([cl[:wi], bcl]),
            np.concatenate([hi[:wi], bhi]),
            np.concatenate([lo[:wi], blo]),
            np.concatenate([vo[:wi], bvo]),
            np.concatenate([tb[:wi], btb]),
        ))
    print(f"done ({time.time() - t0:.1f}s)")

    # Run all variants on bootstrap paths
    results = {}
    h2h = {tp_sid: {"sharpe": np.zeros(N_BOOT), "cagr": np.zeros(N_BOOT),
                     "mdd": np.zeros(N_BOOT)}
            for tp_sid in ["TP2", "TP3"]}

    for sid in STRATEGY_IDS:
        sharpes, cagrs, mdds = [], [], []
        t0 = time.time()
        for b_idx, (bcl, bhi, blo, bvo, btb) in enumerate(boot_paths):
            bnav, bnt = _run_vec(sid, bcl, bhi, blo, bvo, btb, regime_h4, wi)
            bm = _metrics(bnav, wi, bnt)
            sharpes.append(bm["sharpe"])
            cagrs.append(bm["cagr"])
            mdds.append(bm["mdd"])

            if sid == "FULL":
                for tp_sid in h2h:
                    h2h[tp_sid]["sharpe"][b_idx] -= bm["sharpe"]
                    h2h[tp_sid]["cagr"][b_idx] -= bm["cagr"]
                    h2h[tp_sid]["mdd"][b_idx] -= bm["mdd"]
            elif sid in h2h:
                h2h[sid]["sharpe"][b_idx] += bm["sharpe"]
                h2h[sid]["cagr"][b_idx] += bm["cagr"]
                h2h[sid]["mdd"][b_idx] += bm["mdd"]

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
        print(f"  {sid:8s}  Sharpe={r['sharpe_median']:.4f} "
              f"[{r['sharpe_p5']:.4f}, {r['sharpe_p95']:.4f}]  "
              f"CAGR={r['cagr_median']:.2f}% [{r['cagr_p5']:.2f}, {r['cagr_p95']:.2f}]  "
              f"MDD={r['mdd_median']:.2f}%  P(CAGR>0)={r['p_cagr_gt0']:.3f}  ({elapsed:.1f}s)")

    # Head-to-head
    print(f"\n  HEAD-TO-HEAD vs FULL across {N_BOOT} bootstrap paths:")
    for tp_sid in ["TP2", "TP3"]:
        d = h2h[tp_sid]
        sw = np.sum(d["sharpe"] > 0)
        cw = np.sum(d["cagr"] > 0)
        mw = np.sum(d["mdd"] < 0)  # lower MDD = win
        print(f"    {tp_sid}: Sharpe wins {sw}/{N_BOOT} ({sw/N_BOOT*100:.1f}%)  "
              f"CAGR wins {cw}/{N_BOOT} ({cw/N_BOOT*100:.1f}%)  "
              f"MDD wins {mw}/{N_BOOT} ({mw/N_BOOT*100:.1f}%)")
        results[f"h2h_{tp_sid}"] = {
            "sharpe_win_pct": float(sw / N_BOOT * 100),
            "sharpe_mean_delta": float(np.mean(d["sharpe"])),
            "cagr_win_pct": float(cw / N_BOOT * 100),
            "cagr_mean_delta": float(np.mean(d["cagr"])),
            "mdd_win_pct": float(mw / N_BOOT * 100),
            "mdd_mean_delta": float(np.mean(d["mdd"])),
        }

    return results


# =========================================================================
# T4: TP THRESHOLD SWEEP (2-level 50/50, varying TP1 from 0.5R to 3.0R)
# =========================================================================

def run_t4_tp_sweep(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print(f"T4: TP1 THRESHOLD SWEEP ({TP_SWEEP_RANGE[0]}R to {TP_SWEEP_RANGE[-1]}R, 2-level 50/50)")
    print("=" * 80)

    # Baseline (no TP)
    nav_base, nt_base = sim_e5_d1_tp(cl, hi, lo, vo, tb, regime_h4, wi,
                                      tp_levels=None)
    m_base = _metrics(nav_base, wi, nt_base)
    print(f"\n  Baseline (FULL): Sharpe={m_base['sharpe']:.4f}  "
          f"CAGR={m_base['cagr']:.2f}%  MDD={m_base['mdd']:.2f}%  "
          f"Trades={m_base['trades']}")

    results = {"baseline": m_base}
    print(f"\n{'TP1_R':>8s} {'Sharpe':>8s} {'CAGR%':>8s} {'MDD%':>8s} "
          f"{'Trades':>7s} {'dSharpe':>9s} {'dCAGR':>8s} {'dMDD':>8s}")
    print("-" * 72)
    for tp_thr in TP_SWEEP_RANGE:
        nav, nt = sim_e5_d1_tp(cl, hi, lo, vo, tb, regime_h4, wi,
                                tp_levels=[(tp_thr, 0.50)])
        m = _metrics(nav, wi, nt)
        results[f"tp_{tp_thr}"] = m
        print(f"{tp_thr:8.2f} {m['sharpe']:8.4f} {m['cagr']:8.2f} {m['mdd']:8.2f} "
              f"{m['trades']:7d} {m['sharpe']-m_base['sharpe']:+9.4f} "
              f"{m['cagr']-m_base['cagr']:+8.2f} {m['mdd']-m_base['mdd']:+8.2f}")

    return results


# =========================================================================
# T5: TRADE ANATOMY — per-trade partial exit breakdown
# =========================================================================

def run_t5_trade_anatomy(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T5: TRADE ANATOMY — per-trade partial exit breakdown")
    print("=" * 80)

    results = {}

    for sid in STRATEGY_IDS:
        nav, nt, trades = _run_vec(sid, cl, hi, lo, vo, tb, regime_h4, wi,
                                    track_trades=True)

        if not trades:
            print(f"  {sid}: no trades")
            continue

        pnls = np.array([t["pnl_pct"] for t in trades])
        mfes = np.array([t["mfe_R"] for t in trades])
        bars = np.array([t["bars_held"] for t in trades])

        n_t = len(trades)
        n_win = np.sum(pnls > 0)
        wr = n_win / n_t * 100

        print(f"\n  {sid}: {n_t} trades, WR={wr:.1f}%")

        # PnL distribution
        print(f"    PnL%: mean={np.mean(pnls):.2f}  median={np.median(pnls):.2f}  "
              f"P25={np.percentile(pnls, 25):.2f}  P75={np.percentile(pnls, 75):.2f}")

        # MFE distribution
        print(f"    MFE (R units): mean={np.mean(mfes):.2f}  "
              f"median={np.median(mfes):.2f}  "
              f"P25={np.percentile(mfes, 25):.2f}  "
              f"P75={np.percentile(mfes, 75):.2f}  "
              f"max={np.max(mfes):.2f}")

        # TP hit analysis
        if sid != "FULL":
            tp_hits_arr = np.array([t["n_tp_hits"] for t in trades])
            tp_frac_arr = np.array([t["tp_frac_exited"] for t in trades])
            print(f"    TP hits: mean={np.mean(tp_hits_arr):.2f}  "
                  f"0_hits={np.sum(tp_hits_arr == 0)}  "
                  f"1_hit={np.sum(tp_hits_arr == 1)}  "
                  f"2_hits={np.sum(tp_hits_arr == 2)}  "
                  f"3_hits={np.sum(tp_hits_arr == 3)}")
            print(f"    TP frac exited: mean={np.mean(tp_frac_arr):.3f}  "
                  f"median={np.median(tp_frac_arr):.3f}")

            # PnL comparison: trades with TP hits vs without
            tp_mask = tp_hits_arr > 0
            if np.sum(tp_mask) > 0 and np.sum(~tp_mask) > 0:
                print(f"    PnL when TP hit: mean={np.mean(pnls[tp_mask]):+.2f}%  "
                      f"(n={np.sum(tp_mask)})")
                print(f"    PnL when no TP:  mean={np.mean(pnls[~tp_mask]):+.2f}%  "
                      f"(n={np.sum(~tp_mask)})")

        # Exit reason breakdown
        exit_groups = {}
        for t in trades:
            r = t["final_exit_reason"]
            if r not in exit_groups:
                exit_groups[r] = {"count": 0, "pnls": []}
            exit_groups[r]["count"] += 1
            exit_groups[r]["pnls"].append(t["pnl_pct"])

        print(f"    Exit reasons:")
        for reason, data in sorted(exit_groups.items()):
            avg_pnl = np.mean(data["pnls"])
            wr_r = sum(1 for p in data["pnls"] if p > 0) / data["count"] * 100
            print(f"      {reason:20s}  n={data['count']:4d}  "
                  f"avg_pnl={avg_pnl:+.2f}%  WR={wr_r:.1f}%")

        # Holding time
        print(f"    Bars held: mean={np.mean(bars):.1f}  "
              f"median={np.median(bars):.1f}  "
              f"P10={np.percentile(bars, 10):.0f}  "
              f"P90={np.percentile(bars, 90):.0f}")

        # Fat-tail stats
        if len(pnls) > 8:
            sk = float(skew(pnls))
            kt = float(kurtosis(pnls))
            print(f"    Return stats: skew={sk:.3f}  kurtosis={kt:.3f}")

        results[sid] = {
            "n_trades": n_t,
            "win_rate": wr,
            "pnl_mean": float(np.mean(pnls)),
            "pnl_median": float(np.median(pnls)),
            "mfe_mean_R": float(np.mean(mfes)),
            "mfe_median_R": float(np.median(mfes)),
            "mfe_p75_R": float(np.percentile(mfes, 75)),
            "exit_reasons": {r: d["count"] for r, d in exit_groups.items()},
            "avg_bars_held": float(np.mean(bars)),
            "skew": float(skew(pnls)) if len(pnls) > 8 else None,
            "kurtosis": float(kurtosis(pnls)) if len(pnls) > 8 else None,
        }
        if sid != "FULL":
            results[sid]["tp_hit_rate"] = float(np.mean(tp_hits_arr > 0))
            results[sid]["avg_tp_frac"] = float(np.mean(tp_frac_arr))

    return results


# =========================================================================
# T6: PER-TRADE DRAWDOWN — does partial exit reduce intra-trade MDD?
# =========================================================================

def run_t6_trade_drawdown(cl, hi, lo, vo, tb, regime_h4, wi):
    print("\n" + "=" * 80)
    print("T6: PER-TRADE DRAWDOWN — does partial exit reduce intra-trade MDD?")
    print("=" * 80)

    results = {}

    for sid in STRATEGY_IDS:
        nav, nt, trades = _run_vec(sid, cl, hi, lo, vo, tb, regime_h4, wi,
                                    track_trades=True)

        if not trades:
            print(f"  {sid}: no trades")
            continue

        # Compute per-trade drawdown from nav
        trade_mdds = []
        trade_giveback = []
        for t in trades:
            eb = t["entry_bar"]
            xb = t["exit_bar"]
            if xb > eb:
                nav_slice = nav[eb:xb + 1]
                nav_peak = np.maximum.accumulate(nav_slice)
                dd = 1.0 - nav_slice / nav_peak
                tdd = float(np.max(dd)) * 100
            else:
                tdd = 0.0
            trade_mdds.append(tdd)

            # Giveback: how much of peak unrealized profit was returned
            if t["mfe_pct"] > 0:
                giveback = t["mfe_pct"] - t["pnl_pct"]
            else:
                giveback = 0.0
            trade_giveback.append(giveback)

        trade_mdds = np.array(trade_mdds)
        trade_giveback = np.array(trade_giveback)
        pnls = np.array([t["pnl_pct"] for t in trades])
        mfes = np.array([t["mfe_R"] for t in trades])

        n_t = len(trades)
        print(f"\n  {sid}: {n_t} trades")
        print(f"    Trade MDD%: mean={np.mean(trade_mdds):.2f}  "
              f"median={np.median(trade_mdds):.2f}  "
              f"P75={np.percentile(trade_mdds, 75):.2f}  "
              f"P90={np.percentile(trade_mdds, 90):.2f}  "
              f"max={np.max(trade_mdds):.2f}")
        print(f"    Giveback%:  mean={np.mean(trade_giveback):.2f}  "
              f"median={np.median(trade_giveback):.2f}  "
              f"P75={np.percentile(trade_giveback, 75):.2f}  "
              f"P90={np.percentile(trade_giveback, 90):.2f}")

        # Winners with large giveback (reached 1R+ but gave back >50% of MFE)
        winners_1r = mfes >= 1.0
        n_1r = np.sum(winners_1r)
        if n_1r > 0:
            gb_1r = trade_giveback[winners_1r]
            large_gb = np.sum(gb_1r > 50)
            print(f"    Trades reaching ≥1R: {n_1r}/{n_t}, "
                  f"giveback>50%: {large_gb} ({large_gb/n_1r*100:.1f}%)")

        results[sid] = {
            "trade_mdd_mean": float(np.mean(trade_mdds)),
            "trade_mdd_median": float(np.median(trade_mdds)),
            "trade_mdd_p75": float(np.percentile(trade_mdds, 75)),
            "trade_mdd_p90": float(np.percentile(trade_mdds, 90)),
            "trade_mdd_max": float(np.max(trade_mdds)),
            "giveback_mean": float(np.mean(trade_giveback)),
            "giveback_median": float(np.median(trade_giveback)),
            "giveback_p90": float(np.percentile(trade_giveback, 90)),
        }

    # Delta table
    if "FULL" in results:
        print(f"\n  DELTA vs FULL:")
        for tp_sid in ["TP2", "TP3"]:
            if tp_sid in results:
                b = results["FULL"]
                x = results[tp_sid]
                print(f"    {tp_sid}: dTradeMDD_mean={x['trade_mdd_mean']-b['trade_mdd_mean']:+.2f}%  "
                      f"dTradeMDD_p90={x['trade_mdd_p90']-b['trade_mdd_p90']:+.2f}%  "
                      f"dGiveback_mean={x['giveback_mean']-b['giveback_mean']:+.2f}%  "
                      f"dGiveback_p90={x['giveback_p90']-b['giveback_p90']:+.2f}%")

    return results


# =========================================================================
# SAVE OUTPUTS
# =========================================================================

def save_results(t1_results, ts_results, boot_results,
                 sweep_results, anatomy_results, dd_results):
    out = {
        "factorial": {},
        "timescale": {},
        "bootstrap": {},
        "tp_sweep": {},
        "trade_anatomy": {},
        "trade_drawdown": {},
    }

    for sid in STRATEGY_IDS:
        out["factorial"][sid] = {}
        for sc in ["smart", "base", "harsh"]:
            out["factorial"][sid][sc] = t1_results[sid][sc]

        out["timescale"][sid] = {}
        for sp in SLOW_PERIODS:
            out["timescale"][sid][str(sp)] = ts_results[sid][sp]

        if sid in boot_results:
            out["bootstrap"][sid] = boot_results[sid]

    for k in boot_results:
        if k.startswith("h2h_"):
            out["bootstrap"][k] = boot_results[k]

    for k, v in sweep_results.items():
        out["tp_sweep"][k] = v

    for k, v in anatomy_results.items():
        out["trade_anatomy"][k] = v

    for k, v in dd_results.items():
        out["trade_drawdown"][k] = v

    # JSON
    json_path = OUTDIR / "x10_results.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nSaved: {json_path}")

    # CSV factorial table
    csv_path = OUTDIR / "x10_factorial_table.csv"
    fields = ["strategy", "scenario", "sharpe", "cagr", "mdd", "calmar", "trades"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for sid in STRATEGY_IDS:
            for sc in ["smart", "base", "harsh"]:
                row = {"strategy": sid, "scenario": sc}
                row.update(t1_results[sid][sc])
                w.writerow(row)
    print(f"Saved: {csv_path}")

    # CSV timescale table
    csv_ts = OUTDIR / "x10_timescale_table.csv"
    with open(csv_ts, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slow_period",
                     "full_sharpe", "full_cagr", "full_mdd",
                     "tp2_sharpe", "tp2_cagr", "tp2_mdd",
                     "tp3_sharpe", "tp3_cagr", "tp3_mdd"])
        for sp in SLOW_PERIODS:
            full = ts_results["FULL"][sp]
            tp2 = ts_results["TP2"][sp]
            tp3 = ts_results["TP3"][sp]
            w.writerow([sp,
                        f"{full['sharpe']:.4f}", f"{full['cagr']:.2f}", f"{full['mdd']:.2f}",
                        f"{tp2['sharpe']:.4f}", f"{tp2['cagr']:.2f}", f"{tp2['mdd']:.2f}",
                        f"{tp3['sharpe']:.4f}", f"{tp3['cagr']:.2f}", f"{tp3['mdd']:.2f}"])
    print(f"Saved: {csv_ts}")

    # CSV bootstrap table
    csv_boot = OUTDIR / "x10_bootstrap_table.csv"
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
                row.update({k: boot_results[sid].get(k)
                           for k in boot_fields if k != "strategy"})
                w.writerow(row)
    print(f"Saved: {csv_boot}")

    # CSV TP sweep
    csv_sweep = OUTDIR / "x10_tp_sweep.csv"
    with open(csv_sweep, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tp1_R", "sharpe", "cagr", "mdd", "trades",
                     "d_sharpe", "d_cagr", "d_mdd"])
        base = sweep_results["baseline"]
        w.writerow(["none", f"{base['sharpe']:.4f}", f"{base['cagr']:.2f}",
                    f"{base['mdd']:.2f}", base["trades"], "0", "0", "0"])
        for tp_thr in TP_SWEEP_RANGE:
            k = f"tp_{tp_thr}"
            if k in sweep_results:
                m = sweep_results[k]
                w.writerow([f"{tp_thr:.2f}",
                           f"{m['sharpe']:.4f}", f"{m['cagr']:.2f}",
                           f"{m['mdd']:.2f}", m["trades"],
                           f"{m['sharpe']-base['sharpe']:+.4f}",
                           f"{m['cagr']-base['cagr']:+.2f}",
                           f"{m['mdd']-base['mdd']:+.2f}"])
    print(f"Saved: {csv_sweep}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 80)
    print("X10 RESEARCH — MULTI-TP LADDER FOR E5+EMA21D1")
    print(f"  Data: {DATA}")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  E5 params: slow={SLOW}, trail={TRAIL}, vdo_thr={VDO_THR}, "
          f"d1_ema={D1_EMA_P}")
    print(f"  Variants: FULL (baseline), TP2 (50% at 1.5R), "
          f"TP3 (30%@1.5R + 30%@2.2R + 20%@3.0R)")
    print(f"  TP sweep: {TP_SWEEP_RANGE[0]}R to {TP_SWEEP_RANGE[-1]}R (2-level 50/50)")
    print(f"  Bootstrap: {N_BOOT} VCBB paths, block={BLKSZ}")
    print("=" * 80)

    t_start = time.time()

    # Load raw arrays
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

    # Compute D1 regime mask
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct, D1_EMA_P)

    # Warmup index
    wi = 0
    if feed.report_start_ms is not None:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j
                break

    # T1: Factorial (fast)
    t1_results = run_t1_factorial(cl, hi, lo, vo, tb, regime_h4, wi)

    # T5 & T6: Trade anatomy + drawdown (fast, answers key questions)
    anatomy_results = run_t5_trade_anatomy(cl, hi, lo, vo, tb, regime_h4, wi)
    dd_results = run_t6_trade_drawdown(cl, hi, lo, vo, tb, regime_h4, wi)

    # T4: TP sweep
    sweep_results = run_t4_tp_sweep(cl, hi, lo, vo, tb, regime_h4, wi)

    # T2: Timescale robustness
    ts_results = run_t2_timescale(cl, hi, lo, vo, tb, regime_h4, wi)

    # T3: Bootstrap (slow — run last)
    boot_results = run_t3_bootstrap(cl, hi, lo, vo, tb, regime_h4, wi)

    # Save
    save_results(t1_results, ts_results, boot_results,
                 sweep_results, anatomy_results, dd_results)

    elapsed = time.time() - t_start
    print(f"\n{'=' * 80}")
    print(f"X10 BENCHMARK COMPLETE — {elapsed:.0f}s total")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
