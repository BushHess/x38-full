#!/usr/bin/env python3
"""X31 Phase 0: Re-Entry Barrier — Oracle Ceiling Diagnostic

Strategy-level replay: run E5+EMA1D21, identify re-entries after trail stops,
then re-run with oracle blocking ALL bad (losing) re-entries.

GO/NO-GO gates:
  G1: Oracle ΔSharpe >= +0.08 at 20 bps
  G2: Oracle ΔSharpe >= 0 at 15 and 25 bps
  G3: Top-3 blocked re-entries <= 60% of oracle ΔP&L
  G4: Leave-one-year-out — no single year removal collapses oracle edge to <= 0

6 questions answered:
  Q1: Re-entry cohorts by latency (1/2/3/6 bars)
  Q2: Oracle block bad re-entries — savings vs base
  Q3: Oracle block good re-entries — missed upside vs base
  Q4: Strategy-level replay at 15/20/25 bps
  Q5: Concentration and temporal stability
  Q6: Feature separability (only if oracle passes)
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)
START, END, WARMUP = "2019-01-01", "2026-02-20", 365
VDO_F, VDO_S, VDO_THR = 12, 28, 0.0
SLOW, D1_EMA_P = 120, 21
RATR_P, RATR_Q, RATR_LB = 20, 0.90, 100
TRAIL = 3.0

COST_BPS_LIST = [15, 20, 25]
REENTRY_THRESHOLDS = [1, 2, 3, 6]

OUTDIR = Path(__file__).resolve().parents[1]
TABLES = OUTDIR / "tables"
FIGURES = OUTDIR / "figures"


# =========================================================================
# INDICATORS (same as x31_diagnostic.py)
# =========================================================================

def _ema(s, p):
    a = 2.0 / (p + 1)
    out, _ = lfilter([a], [1.0, -(1 - a)], s, zi=[(1 - a) * s[0]])
    return out


def _robust_atr(hi, lo, cl, cap_q=RATR_Q, cap_lb=RATR_LB, period=RATR_P):
    prev = np.empty_like(cl); prev[0] = cl[0]; prev[1:] = cl[:-1]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - prev), np.abs(lo - prev)))
    n = len(tr); tr_cap = np.full(n, np.nan)
    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)
    ratr = np.full(n, np.nan); s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.nanmean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period
    return ratr


def _vdo(cl, hi, lo, vo, tb, fast=VDO_F, slow=VDO_S):
    ts = np.maximum(vo - tb, 0.0); vdr = np.zeros(len(cl))
    m = vo > 1e-12; vdr[m] = (tb[m] - ts[m]) / vo[m]
    return _ema(vdr, fast) - _ema(vdr, slow)


def _d1_regime(h4_ct, d1_cl, d1_ct, p=D1_EMA_P):
    d1_ema = _ema(d1_cl, p)
    d1_reg = d1_cl > d1_ema
    n_h4 = len(h4_ct); out = np.zeros(n_h4, dtype=np.bool_)
    j = 0; nd = len(d1_cl)
    for i in range(n_h4):
        while j + 1 < nd and d1_ct[j + 1] < h4_ct[i]:
            j += 1
        if d1_ct[j] < h4_ct[i]:
            out[i] = d1_reg[j]
    return out


# =========================================================================
# METRICS
# =========================================================================

def _metrics(nav):
    """Sharpe, CAGR, MDD from NAV array."""
    r = np.diff(nav) / nav[:-1]
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return {"sharpe": 0.0, "cagr": 0.0, "mdd": 1.0}
    sharpe = float(np.mean(r) / np.std(r, ddof=0) * ANN) if np.std(r, ddof=0) > 0 else 0.0
    total_r = nav[-1] / nav[0]
    n_years = len(r) / (6 * 365.25)
    cagr = float(total_r ** (1 / n_years) - 1) if n_years > 0 and total_r > 0 else 0.0
    peak = np.maximum.accumulate(nav)
    dd = (peak - nav) / peak
    mdd = float(np.max(dd))
    return {"sharpe": sharpe, "cagr": cagr, "mdd": mdd}


# =========================================================================
# SIMULATION ENGINE — supports oracle block list
# =========================================================================

@dataclass
class TradeRecord:
    entry_bar: int
    exit_bar: int
    exit_reason: str
    entry_px: float
    exit_px: float
    peak_px: float
    pnl_usd: float
    ret_pct: float
    bars_held: int
    bars_since_prev_exit: int   # -1 if first trade
    is_reentry: dict            # {threshold: bool} for each REENTRY_THRESHOLD


def _sim(cl, ef, es, vd, at, regime_h4, cps, cooldown_windows=None):
    """Run E5+EMA1D21 simulation.

    cooldown_windows: list of (start_bar, end_bar) tuples. Entry is blocked
                      for ALL bars in [start_bar, end_bar] inclusive. This
                      models a re-entry barrier: after a trail stop, if oracle
                      says the next re-entry would be bad, impose a cooldown
                      covering the entire window where re-entry could occur.
    """
    # Build blocked set from cooldown windows
    block_bars = set()
    if cooldown_windows:
        for start, end in cooldown_windows:
            for b in range(start, end + 1):
                block_bars.add(b)

    n = len(cl)
    cash = CASH
    bq = 0.0
    inp = False
    pk = 0.0
    entry_bar = 0
    entry_cost = 0.0
    entry_px = 0.0
    exit_reason = ""
    prev_exit_bar = -9999

    nav = np.zeros(n)
    trades: list[TradeRecord] = []
    pending_entry = False
    pending_exit = False

    for i in range(n):
        p = cl[i]

        # Execute pending signals from previous bar
        if i > 0:
            fp = cl[i - 1]
            if pending_entry:
                pending_entry = False
                entry_px = fp
                entry_bar = i
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0
                inp = True
                pk = p
            elif pending_exit:
                pending_exit = False
                rcv = bq * fp * (1 - cps)
                bars_since = entry_bar - prev_exit_bar if prev_exit_bar >= 0 else -1
                is_re = {th: (0 < bars_since <= th) for th in REENTRY_THRESHOLDS}

                trades.append(TradeRecord(
                    entry_bar=entry_bar, exit_bar=i,
                    exit_reason=exit_reason,
                    entry_px=entry_px, exit_px=fp,
                    peak_px=pk,
                    pnl_usd=rcv - entry_cost,
                    ret_pct=(rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                    bars_held=i - entry_bar,
                    bars_since_prev_exit=bars_since,
                    is_reentry=is_re,
                ))
                prev_exit_bar = i
                cash = rcv
                bq = 0.0
                inp = False
                pk = 0.0

        nav[i] = cash + bq * p

        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                if i not in block_bars:
                    pending_entry = True
                # If blocked by cooldown window, skip — check again next bar
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                exit_reason = "trail_stop"
                pending_exit = True
            elif ef[i] < es[i]:
                exit_reason = "trend_exit"
                pending_exit = True

    # Close open position
    if inp and bq > 0:
        rcv = bq * cl[-1] * (1 - cps)
        bars_since = entry_bar - prev_exit_bar if prev_exit_bar >= 0 else -1
        is_re = {th: (0 < bars_since <= th) for th in REENTRY_THRESHOLDS}
        trades.append(TradeRecord(
            entry_bar=entry_bar, exit_bar=n - 1,
            exit_reason="end_of_data",
            entry_px=entry_px, exit_px=cl[-1],
            peak_px=pk,
            pnl_usd=rcv - entry_cost,
            ret_pct=(rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
            bars_held=n - 1 - entry_bar,
            bars_since_prev_exit=bars_since,
            is_reentry=is_re,
        ))
        nav[-1] = rcv

    return nav, trades


# =========================================================================
# ORACLE: identify re-entry bars to block
# =========================================================================

def _find_cooldown_windows(trades, threshold):
    """From base run, find cooldown windows for BAD (losing) re-entries.

    For each bad re-entry: the previous exit bar starts a cooldown window
    of `threshold` bars. This prevents any entry in that window, not just
    the specific entry bar (which the strategy would trivially bypass by
    entering 1 bar later).

    Returns: (windows, bad_trades, good_trades)
      windows: list of (start_bar, end_bar) tuples
    """
    windows = []
    bad_trades = []
    good_trades = []

    # Build index: for each trade, find the previous trade's exit bar
    for idx, t in enumerate(trades):
        if t.is_reentry.get(threshold, False):
            # The previous trade's exit bar is where cooldown should start
            prev_exit = t.entry_bar - t.bars_since_prev_exit if t.bars_since_prev_exit > 0 else t.entry_bar
            if t.pnl_usd < 0:
                # Block from prev_exit to prev_exit + threshold
                # This covers the entire window where the bad re-entry occurred
                windows.append((prev_exit, prev_exit + threshold))
                bad_trades.append(t)
            else:
                good_trades.append(t)

    return windows, bad_trades, good_trades


def _find_cooldown_windows_good(trades, threshold):
    """Cooldown windows for ALL good (winning) re-entries — Q3 cost analysis."""
    windows = []
    for t in trades:
        if t.is_reentry.get(threshold, False) and t.pnl_usd >= 0:
            prev_exit = t.entry_bar - t.bars_since_prev_exit if t.bars_since_prev_exit > 0 else t.entry_bar
            windows.append((prev_exit, prev_exit + threshold))
    return windows


# =========================================================================
# YEAR EXTRACTION
# =========================================================================

def _bar_to_year(bar_idx, h4_bars):
    """Get year from H4 bar index."""
    from datetime import datetime
    ts_ms = h4_bars[bar_idx].close_time
    return datetime.utcfromtimestamp(ts_ms / 1000).year


# =========================================================================
# FIGURES
# =========================================================================

def _plot_oracle_delta_by_cost(results_by_cost, threshold, path):
    """Bar chart: ΔSharpe by cost level."""
    costs = sorted(results_by_cost.keys())
    deltas = [results_by_cost[c]["delta_sharpe"] for c in costs]

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ['#4caf50' if d >= 0.08 else '#ff9800' if d >= 0 else '#d32f2f' for d in deltas]
    ax.bar(range(len(costs)), deltas, color=colors, edgecolor='black', alpha=0.8)
    ax.set_xticks(range(len(costs)))
    ax.set_xticklabels([f"{c} bps" for c in costs])
    ax.axhline(0.08, color='green', linestyle='--', alpha=0.5, label='GO threshold (+0.08)')
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.set_ylabel("ΔSharpe (oracle - base)")
    ax.set_title(f"X31 Phase 0: Oracle Re-Entry Barrier (threshold={threshold} bars)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_concentration(bad_trades, total_delta_pnl, path):
    """Cumulative contribution of blocked trades to oracle gain."""
    if not bad_trades or total_delta_pnl <= 0:
        return

    # Sort bad trades by loss magnitude (worst first = biggest savings)
    sorted_bad = sorted(bad_trades, key=lambda t: t.pnl_usd)
    cum_savings = np.cumsum([-t.pnl_usd for t in sorted_bad])
    cum_frac = cum_savings / total_delta_pnl * 100

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(range(1, len(sorted_bad) + 1), cum_frac, 'b-o', markersize=4)
    ax.axhline(60, color='red', linestyle='--', alpha=0.5, label='60% threshold')
    ax.axvline(3, color='orange', linestyle='--', alpha=0.5, label='top-3')
    ax.set_xlabel("# blocked trades (sorted by loss magnitude)")
    ax.set_ylabel("Cumulative % of oracle ΔP&L")
    ax.set_title("X31: Oracle Gain Concentration")
    ax.legend()
    ax.set_xlim(0, min(len(sorted_bad) + 1, 30))
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_loyo(loyo_results, base_delta, path):
    """Leave-one-year-out ΔSharpe stability."""
    years = sorted(loyo_results.keys())
    deltas = [loyo_results[y] for y in years]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['#4caf50' if d > 0 else '#d32f2f' for d in deltas]
    ax.bar(range(len(years)), deltas, color=colors, edgecolor='black', alpha=0.8)
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels(years)
    ax.axhline(base_delta, color='blue', linestyle='--', alpha=0.5,
               label=f'Full oracle ΔSh={base_delta:.4f}')
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.set_ylabel("ΔSharpe (oracle minus base)")
    ax.set_title("X31: Leave-One-Year-Out Oracle Stability")
    ax.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    print("=" * 70)
    print("X31 PHASE 0: RE-ENTRY BARRIER — ORACLE CEILING")
    print("=" * 70)

    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    # --- Load data ---
    print("\nLoading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
    d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)
    h4_bars = feed.h4_bars

    print(f"  H4 bars: {len(cl)}, D1 bars: {len(d1_cl)}")

    # --- Indicators ---
    print("Computing indicators...")
    ef = _ema(cl, max(5, SLOW // 4))
    es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb)
    at = _robust_atr(hi, lo, cl)
    reg = _d1_regime(h4_ct, d1_cl, d1_ct)

    # Use threshold=6 as primary (consistent with reentry_diagnostic.md)
    PRIMARY_TH = 6
    all_results = {}

    # ================================================================
    # Q1: RE-ENTRY COHORTS BY LATENCY
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Q1: RE-ENTRY COHORTS BY LATENCY")
    print(f"{'=' * 70}")

    # Base run at 20 bps for cohort analysis
    cps_20 = 20 / 10_000
    nav_base_20, trades_base_20 = _sim(cl, ef, es, vd, at, reg, cps_20)

    print(f"\n  Base trades (20 bps): {len(trades_base_20)}")
    print(f"\n  {'Threshold':>10s}  {'N_reentry':>10s}  {'% trades':>8s}  {'WinRate':>8s}  "
          f"{'MeanRet%':>9s}  {'MeanPnL':>9s}  {'AvgWinner':>10s}  {'AvgLoser':>10s}")

    for th in REENTRY_THRESHOLDS:
        re_trades = [t for t in trades_base_20 if t.is_reentry.get(th, False)]
        non_re = [t for t in trades_base_20 if not t.is_reentry.get(th, False)]
        n_re = len(re_trades)
        if n_re == 0:
            print(f"  {th:>10d}  {0:>10d}  {0:>8.1f}  {'N/A':>8s}  {'N/A':>9s}  {'N/A':>9s}  {'N/A':>10s}  {'N/A':>10s}")
            continue

        wr = sum(1 for t in re_trades if t.pnl_usd >= 0) / n_re * 100
        mean_ret = np.mean([t.ret_pct for t in re_trades])
        mean_pnl = np.mean([t.pnl_usd for t in re_trades])
        winners = [t for t in re_trades if t.pnl_usd >= 0]
        losers = [t for t in re_trades if t.pnl_usd < 0]
        avg_w = np.mean([t.pnl_usd for t in winners]) if winners else 0
        avg_l = np.mean([t.pnl_usd for t in losers]) if losers else 0

        print(f"  {th:>10d}  {n_re:>10d}  {n_re / len(trades_base_20) * 100:>8.1f}  "
              f"{wr:>8.1f}  {mean_ret:>+9.2f}  {mean_pnl:>+9.0f}  {avg_w:>+10.0f}  {avg_l:>+10.0f}")

    # Non-re-entry stats
    non_re_6 = [t for t in trades_base_20 if not t.is_reentry.get(6, False)]
    if non_re_6:
        wr_nr = sum(1 for t in non_re_6 if t.pnl_usd >= 0) / len(non_re_6) * 100
        print(f"\n  Non-re-entry (th=6): N={len(non_re_6)}, WR={wr_nr:.1f}%, "
              f"MeanPnL=${np.mean([t.pnl_usd for t in non_re_6]):+.0f}")

    # ================================================================
    # Q2-Q4: ORACLE REPLAY AT MULTIPLE COSTS
    # ================================================================
    print(f"\n{'=' * 70}")
    print(f"Q2-Q4: ORACLE STRATEGY-LEVEL REPLAY (threshold={PRIMARY_TH} bars)")
    print(f"{'=' * 70}")

    for cost_bps in COST_BPS_LIST:
        cps = cost_bps / 10_000
        print(f"\n  --- {cost_bps} bps ---")

        # Base run
        nav_base, trades_base = _sim(cl, ef, es, vd, at, reg, cps)
        m_base = _metrics(nav_base)

        # Oracle: block bad re-entries (cooldown windows)
        bad_windows, bad_trades, good_trades = _find_cooldown_windows(trades_base, PRIMARY_TH)
        nav_oracle, trades_oracle = _sim(cl, ef, es, vd, at, reg, cps, cooldown_windows=bad_windows)
        m_oracle = _metrics(nav_oracle)

        # Anti-oracle: block good re-entries (Q3 — missed upside)
        good_windows = _find_cooldown_windows_good(trades_base, PRIMARY_TH)
        nav_anti, trades_anti = _sim(cl, ef, es, vd, at, reg, cps, cooldown_windows=good_windows)
        m_anti = _metrics(nav_anti)

        delta_sh = m_oracle["sharpe"] - m_base["sharpe"]
        delta_cagr = m_oracle["cagr"] - m_base["cagr"]
        delta_mdd = m_oracle["mdd"] - m_base["mdd"]
        anti_delta_sh = m_anti["sharpe"] - m_base["sharpe"]

        print(f"    Base:       Sh={m_base['sharpe']:.4f}  CAGR={m_base['cagr']*100:.2f}%  MDD={m_base['mdd']*100:.2f}%  trades={len(trades_base)}")
        print(f"    Oracle:     Sh={m_oracle['sharpe']:.4f}  CAGR={m_oracle['cagr']*100:.2f}%  MDD={m_oracle['mdd']*100:.2f}%  trades={len(trades_oracle)}")
        print(f"    ΔOracle:    ΔSh={delta_sh:+.4f}  ΔCAGR={delta_cagr*100:+.2f}%  ΔMDD={delta_mdd*100:+.2f}pp")
        print(f"    Anti-oracle (block good): ΔSh={anti_delta_sh:+.4f}")
        print(f"    Blocked:    {len(bad_windows)} bad re-entry windows, {len(good_windows)} good re-entry windows")

        result = {
            "cost_bps": cost_bps,
            "base": m_base,
            "oracle": m_oracle,
            "delta_sharpe": delta_sh,
            "delta_cagr": delta_cagr,
            "delta_mdd": delta_mdd,
            "anti_oracle_delta_sharpe": anti_delta_sh,
            "n_blocked_bad": len(bad_windows),
            "n_blocked_good": len(good_windows),
            "n_base_trades": len(trades_base),
            "n_oracle_trades": len(trades_oracle),
            "bad_trades": bad_trades,
            "good_trades": good_trades,
        }
        all_results[cost_bps] = result

    # ================================================================
    # Q5: CONCENTRATION TEST
    # ================================================================
    print(f"\n{'=' * 70}")
    print("Q5: CONCENTRATION & TEMPORAL STABILITY")
    print(f"{'=' * 70}")

    r20 = all_results[20]
    bad_trades_20 = r20["bad_trades"]
    total_oracle_gain = r20["oracle"]["cagr"] - r20["base"]["cagr"]
    # Use P&L-based concentration (more direct than CAGR)
    total_bad_pnl = sum(-t.pnl_usd for t in bad_trades_20)  # total savings from blocking

    if bad_trades_20 and total_bad_pnl > 0:
        sorted_bad = sorted(bad_trades_20, key=lambda t: t.pnl_usd)  # worst first
        top3_savings = sum(-t.pnl_usd for t in sorted_bad[:3])
        top3_pct = top3_savings / total_bad_pnl * 100

        print(f"\n  Concentration (P&L-based, 20 bps):")
        print(f"    Total blocked trades:     {len(bad_trades_20)}")
        print(f"    Total savings (bad P&L):  ${total_bad_pnl:,.0f}")
        print(f"    Top-3 worst re-entries:   ${top3_savings:,.0f} ({top3_pct:.1f}%)")

        print(f"\n    Top-5 worst blocked re-entries:")
        print(f"    {'Rank':>4s}  {'PnL':>10s}  {'Ret%':>8s}  {'EntryBar':>9s}  {'Bars':>5s}  {'Year':>5s}")
        for rank, t in enumerate(sorted_bad[:5], 1):
            yr = _bar_to_year(t.entry_bar, h4_bars)
            print(f"    {rank:>4d}  ${t.pnl_usd:>+10,.0f}  {t.ret_pct:>+8.2f}  {t.entry_bar:>9d}  {t.bars_held:>5d}  {yr:>5d}")

        gate_concentration = top3_pct <= 60.0
        print(f"\n    GATE G3 (top-3 <= 60%): {'PASS' if gate_concentration else 'FAIL'} ({top3_pct:.1f}%)")
    else:
        gate_concentration = False
        top3_pct = 0.0
        print("  No bad re-entries or no oracle gain.")
        print(f"  GATE G3: FAIL (no data)")

    # Year distribution of blocked trades
    if bad_trades_20:
        year_counts = {}
        year_pnl = {}
        for t in bad_trades_20:
            yr = _bar_to_year(t.entry_bar, h4_bars)
            year_counts[yr] = year_counts.get(yr, 0) + 1
            year_pnl[yr] = year_pnl.get(yr, 0) + (-t.pnl_usd)
        print(f"\n    Year distribution of blocked trades:")
        print(f"    {'Year':>5s}  {'Count':>6s}  {'Savings':>10s}  {'% Total':>8s}")
        for yr in sorted(year_counts.keys()):
            pct = year_pnl[yr] / total_bad_pnl * 100 if total_bad_pnl > 0 else 0
            print(f"    {yr:>5d}  {year_counts[yr]:>6d}  ${year_pnl[yr]:>10,.0f}  {pct:>8.1f}%")

    # Leave-one-year-out
    print(f"\n  Leave-One-Year-Out (20 bps):")
    cps_20 = 20 / 10_000

    # Get all years present in bad trades
    all_years = sorted(set(_bar_to_year(t.entry_bar, h4_bars) for t in bad_trades_20)) if bad_trades_20 else []
    # Also include all years in the data range
    data_years = sorted(set(_bar_to_year(i, h4_bars) for i in range(0, len(h4_bars), 100)))

    loyo_results = {}
    full_oracle_delta = all_results[20]["delta_sharpe"]

    # Build per-trade cooldown windows from base run at 20 bps
    all_bad_windows_20, _, _ = _find_cooldown_windows(trades_base_20, PRIMARY_TH)
    # Pair each window with its trade for year filtering
    bad_window_trade_pairs = []
    bad_trades_20_copy = list(bad_trades_20)
    for idx, t in enumerate(bad_trades_20_copy):
        prev_exit = t.entry_bar - t.bars_since_prev_exit if t.bars_since_prev_exit > 0 else t.entry_bar
        bad_window_trade_pairs.append(((prev_exit, prev_exit + PRIMARY_TH), t))

    for leave_year in data_years:
        # Block bad re-entries EXCEPT those in leave_year
        loyo_windows = []
        for window, t in bad_window_trade_pairs:
            yr = _bar_to_year(t.entry_bar, h4_bars)
            if yr != leave_year:
                loyo_windows.append(window)
        nav_loyo, _ = _sim(cl, ef, es, vd, at, reg, cps_20, cooldown_windows=loyo_windows)
        m_loyo = _metrics(nav_loyo)
        loyo_delta = m_loyo["sharpe"] - all_results[20]["base"]["sharpe"]
        loyo_results[leave_year] = loyo_delta

        print(f"    Leave out {leave_year}: ΔSh={loyo_delta:+.4f} "
              f"(dropped {sum(1 for t in bad_trades_20 if _bar_to_year(t.entry_bar, h4_bars) == leave_year)} blocks)")

    # Check: does any single year removal collapse edge to <= 0?
    loyo_min = min(loyo_results.values()) if loyo_results else 0
    loyo_min_year = min(loyo_results, key=loyo_results.get) if loyo_results else "N/A"
    gate_loyo = loyo_min > 0

    print(f"\n    Worst LOYO: {loyo_min_year} → ΔSh={loyo_min:+.4f}")
    print(f"    GATE G4 (no year removal → ΔSh <= 0): {'PASS' if gate_loyo else 'FAIL'}")

    # ================================================================
    # GATES SUMMARY
    # ================================================================
    print(f"\n{'=' * 70}")
    print("GO/NO-GO GATES")
    print(f"{'=' * 70}")

    delta_20 = all_results[20]["delta_sharpe"]
    delta_15 = all_results[15]["delta_sharpe"]
    delta_25 = all_results[25]["delta_sharpe"]

    gate_g1 = delta_20 >= 0.08
    gate_g2 = delta_15 >= 0 and delta_25 >= 0
    gate_g3 = bool(gate_concentration)
    gate_g4 = bool(gate_loyo)

    print(f"  G1: Oracle ΔSh >= +0.08 @ 20 bps:     {'PASS' if gate_g1 else 'FAIL'} (ΔSh={delta_20:+.4f})")
    print(f"  G2: Oracle ΔSh >= 0 @ 15 & 25 bps:    {'PASS' if gate_g2 else 'FAIL'} (15bps={delta_15:+.4f}, 25bps={delta_25:+.4f})")
    print(f"  G3: Top-3 concentration <= 60%:        {'PASS' if gate_g3 else 'FAIL'} ({top3_pct:.1f}%)")
    print(f"  G4: LOYO stability (no year → ΔSh<=0): {'PASS' if gate_g4 else 'FAIL'} (worst={loyo_min:+.4f})")

    all_pass = gate_g1 and gate_g2 and gate_g3 and gate_g4
    verdict = "GO" if all_pass else "STOP"
    fail_reasons = []
    if not gate_g1:
        fail_reasons.append(f"ΔSh={delta_20:+.4f} < +0.08")
    if not gate_g2:
        fail_reasons.append(f"negative at {'15' if delta_15 < 0 else '25'} bps")
    if not gate_g3:
        fail_reasons.append(f"top-3={top3_pct:.1f}% > 60%")
    if not gate_g4:
        fail_reasons.append(f"LOYO {loyo_min_year} collapses to {loyo_min:+.4f}")

    print(f"\n  >>> VERDICT: {verdict}" + (f" ({'; '.join(fail_reasons)})" if fail_reasons else ""))

    # ================================================================
    # Q6: FEATURE SEPARABILITY (only if oracle passes or marginal)
    # ================================================================
    if delta_20 > 0:  # Report if any positive signal at all
        print(f"\n{'=' * 70}")
        print("Q6: FEATURE SEPARABILITY (bad vs good re-entries)")
        print(f"{'=' * 70}")

        re_entries_20 = [t for t in trades_base_20 if t.is_reentry.get(PRIMARY_TH, False)]
        if len(re_entries_20) >= 10:
            labels = np.array([1 if t.pnl_usd < 0 else 0 for t in re_entries_20])

            # Features available from OHLCV + strategy state
            features = {}
            features["bars_held_prev"] = np.array([
                trades_base_20[max(0, trades_base_20.index(t) - 1)].bars_held
                if trades_base_20.index(t) > 0 else 0 for t in re_entries_20
            ], dtype=np.float64)
            features["bars_since_exit"] = np.array([
                t.bars_since_prev_exit for t in re_entries_20
            ], dtype=np.float64)
            features["prev_ret_pct"] = np.array([
                trades_base_20[max(0, trades_base_20.index(t) - 1)].ret_pct
                if trades_base_20.index(t) > 0 else 0 for t in re_entries_20
            ], dtype=np.float64)

            # Price-based features at entry bar
            features["ema_spread"] = np.array([
                (ef[t.entry_bar] - es[t.entry_bar]) / cl[t.entry_bar] * 100
                if t.entry_bar < len(cl) else 0 for t in re_entries_20
            ], dtype=np.float64)
            features["ratr_pctl"] = np.array([
                at[t.entry_bar] / cl[t.entry_bar] * 100
                if t.entry_bar < len(cl) and not math.isnan(at[t.entry_bar]) else 0
                for t in re_entries_20
            ], dtype=np.float64)
            features["vdo_at_entry"] = np.array([
                vd[t.entry_bar] if t.entry_bar < len(cl) else 0
                for t in re_entries_20
            ], dtype=np.float64)

            # Simple AUC via Mann-Whitney U
            from scipy.stats import mannwhitneyu

            print(f"\n  {'Feature':>20s}  {'AUC':>6s}  {'p-value':>8s}  {'Mean(bad)':>10s}  {'Mean(good)':>10s}")
            for fname, fvals in features.items():
                bad_vals = fvals[labels == 1]
                good_vals = fvals[labels == 0]
                if len(bad_vals) < 3 or len(good_vals) < 3:
                    continue
                try:
                    u, p = mannwhitneyu(bad_vals, good_vals, alternative='two-sided')
                    auc = u / (len(bad_vals) * len(good_vals))
                except Exception:
                    auc, p = 0.5, 1.0
                print(f"  {fname:>20s}  {auc:>6.3f}  {p:>8.4f}  {np.mean(bad_vals):>+10.3f}  {np.mean(good_vals):>+10.3f}")

            print(f"\n  (AUC > 0.60 or < 0.40 suggests useful separability)")

    # ================================================================
    # SAVE ARTIFACTS
    # ================================================================

    # JSON summary
    summary = {
        "threshold": PRIMARY_TH,
        "gates": {
            "G1_oracle_delta_sharpe_20bps": {"value": round(delta_20, 4), "threshold": 0.08, "pass": bool(gate_g1)},
            "G2_non_negative_15_25bps": {"delta_15": round(delta_15, 4), "delta_25": round(delta_25, 4), "pass": bool(gate_g2)},
            "G3_concentration_top3": {"value": round(top3_pct, 1), "threshold": 60.0, "pass": bool(gate_g3)},
            "G4_loyo_stability": {"worst_year": int(loyo_min_year) if isinstance(loyo_min_year, (int, float)) else loyo_min_year,
                                   "worst_delta": round(float(loyo_min), 4), "pass": bool(gate_g4)},
        },
        "verdict": verdict,
        "results_by_cost": {
            str(c): {
                "base_sharpe": round(r["base"]["sharpe"], 4),
                "oracle_sharpe": round(r["oracle"]["sharpe"], 4),
                "delta_sharpe": round(r["delta_sharpe"], 4),
                "delta_cagr_pct": round(r["delta_cagr"] * 100, 2),
                "delta_mdd_pp": round(r["delta_mdd"] * 100, 2),
                "anti_oracle_delta_sharpe": round(r["anti_oracle_delta_sharpe"], 4),
                "n_blocked_bad": r["n_blocked_bad"],
                "n_blocked_good": r["n_blocked_good"],
            }
            for c, r in all_results.items()
        },
        "loyo": {str(y): round(float(d), 4) for y, d in loyo_results.items()},
    }
    with open(TABLES / "x31_phase0_barrier_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Figures
    print("\nGenerating figures...")
    cost_metrics = {c: {"delta_sharpe": r["delta_sharpe"]} for c, r in all_results.items()}
    _plot_oracle_delta_by_cost(cost_metrics, PRIMARY_TH,
                               FIGURES / "Fig_oracle_delta_by_cost.png")
    if bad_trades_20 and total_bad_pnl > 0:
        _plot_concentration(bad_trades_20, total_bad_pnl,
                            FIGURES / "Fig_concentration.png")
    if loyo_results:
        _plot_loyo(loyo_results, delta_20,
                   FIGURES / "Fig_loyo_stability.png")

    print(f"\nArtifacts: {TABLES}, {FIGURES}")
    print(f"Total time: {time.time() - t0:.1f}s")

    return verdict


if __name__ == "__main__":
    main()
