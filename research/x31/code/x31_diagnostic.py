#!/usr/bin/env python3
"""X31 Phase 0: D1 Regime Exit Diagnostic

Answers: Does D1 regime flip bearish DURING trades, BEFORE the actual
trail-stop or EMA-cross exit fires? If so, is it selective (saves losers
more than it cuts winners)?

Decision matrix:
  Coverage < 10%        → STOP (redundant)
  Timing median < 2 bars → STOP (no edge)
  Cuts losers selectively → PROCEED
  Cuts both equally      → STOP (no selectivity)
  Cuts winners mostly    → STOP (destroys alpha)
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS

# =========================================================================
# CONSTANTS (frozen from E5+EMA1D21)
# =========================================================================

DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CASH = 10_000.0
ANN = math.sqrt(6.0 * 365.25)
START, END, WARMUP = "2019-01-01", "2026-02-20", 365
VDO_F, VDO_S, VDO_THR = 12, 28, 0.0
SLOW, D1_EMA_P = 120, 21
RATR_P, RATR_Q, RATR_LB = 20, 0.90, 100
TRAIL = 3.0
CPS = SCENARIOS["harsh"].per_side_bps / 10_000.0  # 50 bps RT

OUTDIR = Path(__file__).resolve().parents[1]
TABLES = OUTDIR / "tables"
FIGURES = OUTDIR / "figures"


# =========================================================================
# INDICATORS
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


def _compute_d1_regime(h4_ct, d1_cl, d1_ct, p=D1_EMA_P):
    """Boolean: D1 close > D1 EMA(p), mapped to H4 bars."""
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
# BASE SIMULATION — records trade details including per-bar regime
# =========================================================================

def _sim_base(cl, ef, es, vd, at, regime_h4, cps):
    """Run E5+EMA1D21 base. Returns (nav, trades).

    Each trade dict includes:
      entry_bar, exit_bar, exit_reason, ret_pct, pnl_usd,
      entry_px, exit_px, peak_px, bars_held
    """
    n = len(cl)
    cash = CASH; bq = 0.0; inp = False; pe = px = False
    pk = 0.0; entry_bar = 0; entry_cost = 0.0; entry_px = 0.0; _er = ""
    nav = np.zeros(n); trades = []

    for i in range(n):
        p = cl[i]
        if i > 0:
            fp = cl[i - 1]
            if pe:
                pe = False; entry_px = fp; entry_bar = i
                bq = cash / (fp * (1 + cps))
                entry_cost = bq * fp * (1 + cps)
                cash = 0.0; inp = True; pk = p
            elif px:
                px = False; rcv = bq * fp * (1 - cps)
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "entry_px": entry_px, "exit_px": fp, "peak_px": pk,
                    "pnl_usd": rcv - entry_cost,
                    "ret_pct": (rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
                    "bars_held": i - entry_bar, "exit_reason": _er,
                })
                cash = rcv; bq = 0.0; inp = False; pk = 0.0

        nav[i] = cash + bq * p
        a = at[i]
        if math.isnan(a) or math.isnan(ef[i]) or math.isnan(es[i]):
            continue

        if not inp:
            if ef[i] > es[i] and vd[i] > VDO_THR and regime_h4[i]:
                pe = True
        else:
            pk = max(pk, p)
            if p < pk - TRAIL * a:
                _er = "trail_stop"; px = True
            elif ef[i] < es[i]:
                _er = "trend_exit"; px = True

    # Close open position at end
    if inp and bq > 0:
        rcv = bq * cl[-1] * (1 - cps)
        trades.append({
            "entry_bar": entry_bar, "exit_bar": n - 1,
            "entry_px": entry_px, "exit_px": cl[-1], "peak_px": pk,
            "pnl_usd": rcv - entry_cost,
            "ret_pct": (rcv / entry_cost - 1) * 100 if entry_cost > 0 else 0.0,
            "bars_held": n - 1 - entry_bar, "exit_reason": "end_of_data",
        })
        nav[-1] = rcv

    return nav, trades


# =========================================================================
# DIAGNOSTIC: Find D1 regime flips during trades
# =========================================================================

def _analyze_d1_flips(trades, cl, regime_h4, cps):
    """For each trade, find the first bar where D1 regime flips bearish.

    Returns list of dicts with diagnostic info per trade.
    """
    results = []

    for t in trades:
        eb = t["entry_bar"]
        xb = t["exit_bar"]
        reason = t["exit_reason"]

        # Find first bar AFTER entry where regime flips False
        # Entry bar has regime=True (by construction), so start from eb+1
        d1_flip_bar = None
        for i in range(eb + 1, xb):
            if not regime_h4[i]:
                d1_flip_bar = i
                break

        # Hypothetical exit price at D1 flip (use close of bar before flip,
        # same execution logic as trail/trend exits)
        if d1_flip_bar is not None and d1_flip_bar > 0:
            hyp_exit_px = cl[d1_flip_bar - 1]
            # Hypothetical P&L
            entry_cost_per_unit = t["entry_px"] * (1 + cps)
            hyp_rcv_per_unit = hyp_exit_px * (1 - cps)
            hyp_ret_pct = (hyp_rcv_per_unit / entry_cost_per_unit - 1) * 100
            bars_saved = xb - d1_flip_bar
        else:
            hyp_exit_px = None
            hyp_ret_pct = None
            bars_saved = 0

        results.append({
            "entry_bar": eb,
            "exit_bar": xb,
            "exit_reason": reason,
            "bars_held": t["bars_held"],
            "actual_ret_pct": t["ret_pct"],
            "actual_pnl_usd": t["pnl_usd"],
            "entry_px": t["entry_px"],
            "actual_exit_px": t["exit_px"],
            "peak_px": t["peak_px"],
            "d1_flip_bar": d1_flip_bar,
            "d1_flip_before_exit": d1_flip_bar is not None,
            "hyp_exit_px": hyp_exit_px,
            "hyp_ret_pct": hyp_ret_pct,
            "bars_saved": bars_saved,
        })

    return results


# =========================================================================
# FIGURES
# =========================================================================

def _plot_scatter(results, path):
    """Scatter: actual ret vs hypothetical ret for D1-flip trades."""
    flip_trades = [r for r in results if r["d1_flip_before_exit"]]
    if len(flip_trades) < 3:
        return

    actual = [r["actual_ret_pct"] for r in flip_trades]
    hyp = [r["hyp_ret_pct"] for r in flip_trades]

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ['#d32f2f' if a < 0 else '#4caf50' for a in actual]
    ax.scatter(actual, hyp, c=colors, alpha=0.7, s=40, edgecolors='black', linewidths=0.5)

    lim = max(abs(min(actual + hyp)), abs(max(actual + hyp))) * 1.1
    ax.plot([-lim, lim], [-lim, lim], 'k--', alpha=0.3, label='no change')
    ax.axhline(0, color='gray', linewidth=0.5)
    ax.axvline(0, color='gray', linewidth=0.5)

    ax.set_xlabel("Actual Return (%)")
    ax.set_ylabel("Hypothetical D1-Exit Return (%)")
    ax.set_title(f"X31 Diagnostic: D1 Regime Exit vs Actual Exit (n={len(flip_trades)})")
    ax.legend()

    # Annotate quadrants
    n_saved = sum(1 for a, h in zip(actual, hyp) if a < 0 and h > a)
    n_cut = sum(1 for a, h in zip(actual, hyp) if a > 0 and h < a)
    ax.annotate(f"Losers improved: {n_saved}", xy=(0.02, 0.98),
                xycoords='axes fraction', va='top', fontsize=9, color='#d32f2f')
    ax.annotate(f"Winners cut: {n_cut}", xy=(0.98, 0.02),
                xycoords='axes fraction', ha='right', fontsize=9, color='#4caf50')

    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_bars_saved_hist(results, path):
    """Histogram of bars saved by D1 exit."""
    flip_trades = [r for r in results if r["d1_flip_before_exit"]]
    if len(flip_trades) < 3:
        return

    bars = [r["bars_saved"] for r in flip_trades]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(bars, bins=range(0, max(bars) + 5, 2), color='steelblue',
            edgecolor='black', alpha=0.8)
    ax.axvline(np.median(bars), color='red', linestyle='--',
               label=f'median={np.median(bars):.0f} bars')
    ax.set_xlabel("Bars Saved (actual_exit - d1_flip)")
    ax.set_ylabel("Count")
    ax.set_title("X31: Timing Advantage of D1 Regime Exit")
    ax.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def _plot_pnl_delta_by_exit_reason(results, path):
    """Bar chart: mean P&L delta grouped by actual exit reason."""
    flip_trades = [r for r in results if r["d1_flip_before_exit"]]
    if len(flip_trades) < 3:
        return

    reasons = sorted(set(r["exit_reason"] for r in flip_trades))
    fig, ax = plt.subplots(figsize=(7, 5))

    for idx, reason in enumerate(reasons):
        subset = [r for r in flip_trades if r["exit_reason"] == reason]
        deltas = [r["hyp_ret_pct"] - r["actual_ret_pct"] for r in subset]
        mean_d = np.mean(deltas) if deltas else 0
        color = '#4caf50' if mean_d > 0 else '#d32f2f'
        ax.bar(idx, mean_d, color=color, edgecolor='black', alpha=0.8)
        ax.annotate(f'n={len(subset)}', (idx, mean_d),
                    ha='center', va='bottom' if mean_d >= 0 else 'top', fontsize=9)

    ax.set_xticks(range(len(reasons)))
    ax.set_xticklabels(reasons, rotation=15)
    ax.set_ylabel("Mean ΔReturn (hyp - actual) %")
    ax.set_title("X31: P&L Impact by Exit Reason")
    ax.axhline(0, color='gray', linewidth=0.5)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    print("=" * 70)
    print("X31 PHASE 0: D1 REGIME EXIT DIAGNOSTIC")
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

    n = len(cl)
    wi = 0
    if feed.report_start_ms:
        for j, b in enumerate(feed.h4_bars):
            if b.close_time >= feed.report_start_ms:
                wi = j; break
    print(f"  H4 bars: {n}, D1 bars: {len(d1_cl)}, warmup idx: {wi}")

    # --- Indicators ---
    print("Computing indicators...")
    ef = _ema(cl, max(5, SLOW // 4))
    es = _ema(cl, SLOW)
    vd = _vdo(cl, hi, lo, vo, tb)
    at = _robust_atr(hi, lo, cl)
    regime_h4 = _compute_d1_regime(h4_ct, d1_cl, d1_ct)

    # --- Base simulation ---
    print("Running base sim (50 bps)...")
    nav, trades = _sim_base(cl, ef, es, vd, at, regime_h4, CPS)
    print(f"  Total trades: {len(trades)}")
    print(f"  Trail stops:  {sum(1 for t in trades if t['exit_reason'] == 'trail_stop')}")
    print(f"  Trend exits:  {sum(1 for t in trades if t['exit_reason'] == 'trend_exit')}")
    print(f"  End of data:  {sum(1 for t in trades if t['exit_reason'] == 'end_of_data')}")

    # --- D1 flip diagnostic ---
    print("\nAnalyzing D1 regime flips during trades...")
    results = _analyze_d1_flips(trades, cl, regime_h4, CPS)

    # ================================================================
    # ANALYSIS 1: Coverage
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ANALYSIS 1: COVERAGE")
    print(f"{'=' * 70}")

    n_total = len(results)
    n_flip = sum(1 for r in results if r["d1_flip_before_exit"])
    n_no_flip = n_total - n_flip
    coverage_pct = n_flip / n_total * 100 if n_total > 0 else 0

    print(f"  Total trades:              {n_total}")
    print(f"  D1 flips before exit:      {n_flip} ({coverage_pct:.1f}%)")
    print(f"  No D1 flip (regime held):  {n_no_flip} ({100 - coverage_pct:.1f}%)")

    # Breakdown by exit reason
    print("\n  By exit reason:")
    for reason in ["trail_stop", "trend_exit", "end_of_data"]:
        sub = [r for r in results if r["exit_reason"] == reason]
        n_sub = len(sub)
        n_f = sum(1 for r in sub if r["d1_flip_before_exit"])
        pct = n_f / n_sub * 100 if n_sub > 0 else 0
        print(f"    {reason:15s}: {n_f}/{n_sub} ({pct:.1f}%)")

    gate_coverage = coverage_pct >= 10.0
    print(f"\n  GATE 1 (coverage >= 10%): {'PASS' if gate_coverage else 'FAIL'} ({coverage_pct:.1f}%)")

    # ================================================================
    # ANALYSIS 2: Timing
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ANALYSIS 2: TIMING ADVANTAGE")
    print(f"{'=' * 70}")

    flip_trades = [r for r in results if r["d1_flip_before_exit"]]

    if flip_trades:
        bars_saved = [r["bars_saved"] for r in flip_trades]
        median_saved = np.median(bars_saved)
        mean_saved = np.mean(bars_saved)
        p25 = np.percentile(bars_saved, 25)
        p75 = np.percentile(bars_saved, 75)
        hours_saved_median = median_saved * 4  # H4 bars → hours

        print(f"  Bars saved (D1 exit earlier than actual):")
        print(f"    Median:  {median_saved:.0f} bars ({hours_saved_median:.0f} hours)")
        print(f"    Mean:    {mean_saved:.1f} bars ({mean_saved * 4:.0f} hours)")
        print(f"    P25-P75: [{p25:.0f}, {p75:.0f}] bars")
        print(f"    Min-Max: [{min(bars_saved)}, {max(bars_saved)}] bars")

        gate_timing = median_saved >= 2.0
        print(f"\n  GATE 2 (median >= 2 bars): {'PASS' if gate_timing else 'FAIL'} ({median_saved:.0f})")
    else:
        gate_timing = False
        print("  No D1-flip trades to analyze.")
        print(f"\n  GATE 2: FAIL (no data)")

    # ================================================================
    # ANALYSIS 3: P&L Split — Loser Savings vs Winner Cuts
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ANALYSIS 3: P&L SELECTIVITY")
    print(f"{'=' * 70}")

    if flip_trades:
        # Classify by actual outcome
        losers = [r for r in flip_trades if r["actual_ret_pct"] < 0]
        winners = [r for r in flip_trades if r["actual_ret_pct"] >= 0]

        print(f"\n  D1-flip trades breakdown:")
        print(f"    Actual losers:  {len(losers)}")
        print(f"    Actual winners: {len(winners)}")

        # For losers: does D1 exit improve them?
        if losers:
            loser_deltas = [r["hyp_ret_pct"] - r["actual_ret_pct"] for r in losers]
            loser_improved = sum(1 for d in loser_deltas if d > 0)
            print(f"\n  LOSERS (D1 exit vs actual):")
            print(f"    Improved by D1 exit: {loser_improved}/{len(losers)} "
                  f"({loser_improved / len(losers) * 100:.1f}%)")
            print(f"    Mean Δret:   {np.mean(loser_deltas):+.2f}%")
            print(f"    Median Δret: {np.median(loser_deltas):+.2f}%")
            print(f"    Mean actual ret:  {np.mean([r['actual_ret_pct'] for r in losers]):.2f}%")
            print(f"    Mean hyp ret:     {np.mean([r['hyp_ret_pct'] for r in losers]):.2f}%")

        # For winners: does D1 exit hurt them?
        if winners:
            winner_deltas = [r["hyp_ret_pct"] - r["actual_ret_pct"] for r in winners]
            winner_hurt = sum(1 for d in winner_deltas if d < 0)
            print(f"\n  WINNERS (D1 exit vs actual):")
            print(f"    Hurt by D1 exit: {winner_hurt}/{len(winners)} "
                  f"({winner_hurt / len(winners) * 100:.1f}%)")
            print(f"    Mean Δret:   {np.mean(winner_deltas):+.2f}%")
            print(f"    Median Δret: {np.median(winner_deltas):+.2f}%")
            print(f"    Mean actual ret:  {np.mean([r['actual_ret_pct'] for r in winners]):.2f}%")
            print(f"    Mean hyp ret:     {np.mean([r['hyp_ret_pct'] for r in winners]):.2f}%")

        # Net effect
        all_deltas = [r["hyp_ret_pct"] - r["actual_ret_pct"] for r in flip_trades]
        net_mean = np.mean(all_deltas)
        net_sum = sum(all_deltas)
        print(f"\n  NET EFFECT (all D1-flip trades):")
        print(f"    Mean Δret:   {net_mean:+.2f}%")
        print(f"    Sum Δret:    {net_sum:+.1f}%")

        # Selectivity: does D1 exit help losers more than it hurts winners?
        loser_benefit = np.mean([r["hyp_ret_pct"] - r["actual_ret_pct"] for r in losers]) if losers else 0
        winner_cost = np.mean([r["actual_ret_pct"] - r["hyp_ret_pct"] for r in winners]) if winners else 0

        print(f"\n  SELECTIVITY:")
        print(f"    Mean loser benefit (saved):  {loser_benefit:+.2f}%")
        print(f"    Mean winner cost (cut):      {winner_cost:+.2f}%")
        if loser_benefit > 0 and winner_cost > 0:
            selectivity_ratio = loser_benefit / winner_cost
            print(f"    Selectivity ratio (benefit/cost): {selectivity_ratio:.2f}")
            selective = selectivity_ratio > 1.5
        elif loser_benefit > 0 and winner_cost <= 0:
            print(f"    Selectivity: INFINITE (helps losers, doesn't hurt winners)")
            selective = True
            selectivity_ratio = float('inf')
        else:
            selective = False
            selectivity_ratio = 0.0
            print(f"    Selectivity: NONE")
    else:
        selective = False
        selectivity_ratio = 0.0

    # ================================================================
    # ANALYSIS 4: Winner Damage — Top 20
    # ================================================================
    print(f"\n{'=' * 70}")
    print("ANALYSIS 4: TOP-20 WINNER DAMAGE")
    print(f"{'=' * 70}")

    sorted_trades = sorted(results, key=lambda r: r["actual_ret_pct"], reverse=True)
    top20 = sorted_trades[:20]
    n_top20_flip = sum(1 for r in top20 if r["d1_flip_before_exit"])

    print(f"  Top-20 winners with D1 flip: {n_top20_flip}/20 ({n_top20_flip / 20 * 100:.1f}%)")

    print(f"\n  {'Rank':>4s}  {'ActRet%':>8s}  {'HypRet%':>8s}  {'ΔRet%':>8s}  {'D1Flip':>6s}  {'BarsSaved':>9s}  {'Exit':>12s}")
    for rank, r in enumerate(top20, 1):
        hyp_s = f"{r['hyp_ret_pct']:+8.2f}" if r["hyp_ret_pct"] is not None else "     N/A"
        delta_s = f"{r['hyp_ret_pct'] - r['actual_ret_pct']:+8.2f}" if r["hyp_ret_pct"] is not None else "     N/A"
        flip_s = "YES" if r["d1_flip_before_exit"] else "no"
        bars_s = f"{r['bars_saved']:>9d}" if r["d1_flip_before_exit"] else "      N/A"
        print(f"  {rank:>4d}  {r['actual_ret_pct']:+8.2f}  {hyp_s}  {delta_s}  {flip_s:>6s}  {bars_s}  {r['exit_reason']:>12s}")

    winner_damage_ok = n_top20_flip / 20 <= 0.50
    print(f"\n  GATE 4 (top-20 flip <= 50%): {'PASS' if winner_damage_ok else 'WARNING'} ({n_top20_flip}/20)")

    # ================================================================
    # OVERALL VERDICT
    # ================================================================
    print(f"\n{'=' * 70}")
    print("PHASE 0 VERDICT")
    print(f"{'=' * 70}")

    print(f"  Gate 1 — Coverage >= 10%:      {'PASS' if gate_coverage else 'FAIL'} ({coverage_pct:.1f}%)")
    print(f"  Gate 2 — Timing >= 2 bars:     {'PASS' if gate_timing else 'FAIL'}")
    print(f"  Gate 3 — Selective:            {'PASS' if selective else 'FAIL'} (ratio={selectivity_ratio:.2f})")
    print(f"  Gate 4 — Top-20 damage <= 50%: {'PASS' if winner_damage_ok else 'WARNING'}")

    if gate_coverage and gate_timing and selective:
        verdict = "PROCEED"
    else:
        reasons = []
        if not gate_coverage:
            reasons.append(f"coverage {coverage_pct:.1f}% < 10%")
        if not gate_timing:
            reasons.append("timing too small")
        if not selective:
            reasons.append("not selective")
        verdict = f"STOP ({'; '.join(reasons)})"

    print(f"\n  >>> VERDICT: {verdict}")
    print(f"{'=' * 70}")

    # ================================================================
    # SAVE ARTIFACTS
    # ================================================================

    # CSV: per-trade diagnostic
    csv_rows = []
    for r in results:
        csv_rows.append({
            "entry_bar": r["entry_bar"],
            "exit_bar": r["exit_bar"],
            "exit_reason": r["exit_reason"],
            "bars_held": r["bars_held"],
            "actual_ret_pct": round(r["actual_ret_pct"], 4),
            "d1_flip_before_exit": r["d1_flip_before_exit"],
            "d1_flip_bar": r["d1_flip_bar"] if r["d1_flip_bar"] is not None else "",
            "hyp_ret_pct": round(r["hyp_ret_pct"], 4) if r["hyp_ret_pct"] is not None else "",
            "bars_saved": r["bars_saved"],
            "delta_ret_pct": round(r["hyp_ret_pct"] - r["actual_ret_pct"], 4) if r["hyp_ret_pct"] is not None else "",
        })
    with open(TABLES / "Tbl_trade_diagnostic.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    # JSON summary
    summary = {
        "total_trades": n_total,
        "d1_flip_trades": n_flip,
        "coverage_pct": round(coverage_pct, 2),
        "gate_1_coverage": bool(gate_coverage),
        "median_bars_saved": float(np.median([r["bars_saved"] for r in flip_trades])) if flip_trades else 0,
        "gate_2_timing": bool(gate_timing),
        "n_losers_with_flip": len(losers) if flip_trades else 0,
        "n_winners_with_flip": len(winners) if flip_trades else 0,
        "loser_mean_delta_pct": round(float(np.mean([r["hyp_ret_pct"] - r["actual_ret_pct"] for r in losers])), 4) if losers else 0,
        "winner_mean_delta_pct": round(float(np.mean([r["hyp_ret_pct"] - r["actual_ret_pct"] for r in winners])), 4) if winners else 0,
        "selectivity_ratio": round(selectivity_ratio, 4) if selectivity_ratio != float('inf') else "inf",
        "gate_3_selective": bool(selective),
        "top20_flip_count": n_top20_flip,
        "gate_4_winner_damage": bool(winner_damage_ok),
        "verdict": verdict,
    }
    with open(TABLES / "x31_phase0_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Figures
    print("\nGenerating figures...")
    _plot_scatter(results, FIGURES / "Fig_scatter_actual_vs_hyp.png")
    _plot_bars_saved_hist(results, FIGURES / "Fig_bars_saved_hist.png")
    _plot_pnl_delta_by_exit_reason(results, FIGURES / "Fig_pnl_delta_by_reason.png")

    print(f"\nArtifacts: {TABLES}, {FIGURES}")
    print(f"Total time: {time.time() - t0:.1f}s")

    return verdict


if __name__ == "__main__":
    main()
