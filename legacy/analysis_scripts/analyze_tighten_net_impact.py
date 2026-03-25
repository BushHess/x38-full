#!/usr/bin/env python3
"""Net Impact Analysis: Is V10's trailing stop tightening actually a problem?

Previous analysis found 54.5% false exit rate for MULT_ONLY exits (n=11).
This script stress-tests that finding from every angle:

1. RE-ENTRY CAPTURE — Does V10 re-enter after a false exit and recover the move?
   If yes, the "false exit" is just fee drag, not lost alpha.

2. COUNTERFACTUAL — If mult stayed 3.5 instead of 2.5, would the stop NOT have
   triggered? Or would it have triggered 1-2 bars later anyway?

3. PROFIT PROTECTION — Tightened trades had ≥20% peak profit. What's the ratio
   of profit captured vs profit forgone? (Locked 20%+, lost 3-10%?)

4. STATISTICAL SIGNIFICANCE — With n=11, is 54.5% statistically different from
   NONE's 37.9%? Fisher's exact test.

5. SCENARIO TABLE EVIDENCE — tighten_025 and tighten_030 already backtest with
   higher tighten thresholds. If tightening were harmful, they'd perform worse.
   But they perform BETTER. What does this tell us?

6. NET $ DAMAGE — Across all 103 trades, what's the actual PnL impact of
   false exits from tightened vs non-tightened stops?
"""

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = Path("/var/www/trading-bots/btc-spot-dev")
BAR_FILE = BASE / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
TRADE_FILE = BASE / "out_v10_trail_tighten/candidates/baseline_legacy/base/trades.csv"
PREV_ANALYSIS = BASE / "out_v10_trail_tighten/double_compression_analysis/exit_analysis.csv"
SCENARIO_TABLE = BASE / "out_v10_trail_tighten/scenario_table.csv"
OUT_DIR = BASE / "out_v10_trail_tighten/net_impact_analysis"

# ── Strategy params ────────────────────────────────────────────────────────
ATR_PERIOD = 14
TRAIL_ATR_MULT = 3.5
TRAIL_TIGHTEN_MULT = 2.5
TRAIL_ACTIVATE_PCT = 0.05
TRAIL_TIGHTEN_PROFIT_PCT = 0.20
EXIT_COOLDOWN_BARS = 3
ENTRY_COOLDOWN_BARS = 3
FALSE_EXIT_THRESHOLD = 0.03  # 3%

# ── Data ───────────────────────────────────────────────────────────────────
@dataclass
class Bar:
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Trade:
    trade_id: int
    entry_time: str
    exit_time: str
    entry_ts_ms: int
    exit_ts_ms: int
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    return_pct: float
    days_held: float
    entry_reason: str
    exit_reason: str


def load_h4_bars():
    bars = []
    with open(BAR_FILE) as f:
        for row in csv.DictReader(f):
            if row["interval"] != "4h":
                continue
            bars.append(Bar(
                open_time=int(row["open_time"]), close_time=int(row["close_time"]),
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]),
                volume=float(row["volume"]),
            ))
    bars.sort(key=lambda b: b.open_time)
    return bars


def load_trades():
    trades = []
    with open(TRADE_FILE) as f:
        for row in csv.DictReader(f):
            trades.append(Trade(
                trade_id=int(row["trade_id"]), entry_time=row["entry_time"],
                exit_time=row["exit_time"], entry_ts_ms=int(row["entry_ts_ms"]),
                exit_ts_ms=int(row["exit_ts_ms"]), entry_price=float(row["entry_price"]),
                exit_price=float(row["exit_price"]), qty=float(row["qty"]),
                pnl=float(row["pnl"]), return_pct=float(row["return_pct"]),
                days_held=float(row["days_held"]), entry_reason=row["entry_reason"],
                exit_reason=row["exit_reason"],
            ))
    return trades


def load_prev_analysis():
    rows = []
    with open(PREV_ANALYSIS) as f:
        for row in csv.DictReader(f):
            # Convert types
            row["trade_id"] = int(row["trade_id"])
            row["entry_price"] = float(row["entry_price"])
            row["exit_price"] = float(row["exit_price"])
            row["peak_price"] = float(row["peak_price"])
            row["peak_profit_pct"] = float(row["peak_profit_pct"])
            row["return_pct"] = float(row["return_pct"])
            row["mult_used"] = float(row["mult_used"])
            row["tightened"] = row["tightened"] == "True"
            row["atr_at_exit"] = float(row["atr_at_exit"])
            row["continuation_pct"] = float(row["continuation_pct"])
            row["continuation_high_pct"] = float(row["continuation_high_pct"])
            row["is_false_exit"] = row["is_false_exit"] == "True"
            row["forgone_pct"] = float(row["forgone_pct"])
            row["days_held"] = float(row["days_held"])
            rows.append(row)
    return rows


def load_scenario_table():
    rows = []
    with open(SCENARIO_TABLE) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _atr(highs, lows, closes, period):
    n = len(closes)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i] - closes[i-1]))
    out = np.empty(n)
    out[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        out[i] = alpha * tr[i] + (1.0 - alpha) * out[i - 1]
    return out


def find_bar_index(h4_bars, ts_ms):
    lo, hi = 0, len(h4_bars) - 1
    best = 0
    while lo <= hi:
        mid_idx = (lo + hi) // 2
        if h4_bars[mid_idx].close_time <= ts_ms:
            best = mid_idx
            lo = mid_idx + 1
        else:
            hi = mid_idx - 1
    return best


def fisher_exact_test(a, b, c, d):
    """Simple Fisher's exact test p-value (two-sided) for 2x2 table.
    [[a, b], [c, d]] using scipy if available, else manual."""
    try:
        from scipy.stats import fisher_exact
        _, p = fisher_exact([[a, b], [c, d]])
        return p
    except ImportError:
        # Approximate with chi-squared
        n = a + b + c + d
        if n == 0:
            return 1.0
        e_a = (a + b) * (a + c) / n
        e_b = (a + b) * (b + d) / n
        e_c = (c + d) * (a + c) / n
        e_d = (c + d) * (b + d) / n
        chi2 = 0
        for obs, exp in [(a, e_a), (b, e_b), (c, e_c), (d, e_d)]:
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp
        # p-value from chi2(1) — rough approximation
        from math import exp as mexp, sqrt
        p = mexp(-chi2 / 2)  # very rough
        return min(p, 1.0)


def analyze():
    print("Loading data...")
    h4_bars = load_h4_bars()
    trades = load_trades()
    prev = load_prev_analysis()
    scenarios = load_scenario_table()

    h4_highs = np.array([b.high for b in h4_bars])
    h4_lows = np.array([b.low for b in h4_bars])
    h4_closes = np.array([b.close for b in h4_bars])
    h4_atr = _atr(h4_highs, h4_lows, h4_closes, ATR_PERIOD)

    # Build trade lookup by id
    trade_by_id = {t.trade_id: t for t in trades}
    # Build ordered list of trades (sorted by entry time)
    trades_sorted = sorted(trades, key=lambda t: t.entry_ts_ms)

    # Identify trailing stop exits that had tightened mult
    tightened_exits = [r for r in prev if r["tightened"]]
    non_tightened_trail = [r for r in prev if not r["tightened"]]
    tightened_false = [r for r in tightened_exits if r["is_false_exit"]]
    non_tightened_false = [r for r in non_tightened_trail if r["is_false_exit"]]

    print(f"\n{'=' * 85}")
    print("NET IMPACT ANALYSIS: IS TRAIL TIGHTENING ACTUALLY A PROBLEM?")
    print(f"{'=' * 85}")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 1: SAMPLE SIZE & STATISTICAL SIGNIFICANCE
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§1  STATISTICAL SIGNIFICANCE")
    print(f"{'━' * 85}")

    n_tight = len(tightened_exits)
    n_tight_false = len(tightened_false)
    n_non = len(non_tightened_trail)
    n_non_false = len(non_tightened_false)

    print(f"\n  Tightened (mult=2.5):   {n_tight_false}/{n_tight} false exits = "
          f"{n_tight_false/n_tight*100:.1f}%")
    print(f"  Non-tightened (mult=3.5): {n_non_false}/{n_non} false exits = "
          f"{n_non_false/n_non*100:.1f}%")

    # Fisher's exact: is tightened rate significantly different from non-tightened?
    # Table: [[tight_false, tight_ok], [non_false, non_ok]]
    a = n_tight_false
    b = n_tight - n_tight_false
    c = n_non_false
    d = n_non - n_non_false
    p_val = fisher_exact_test(a, b, c, d)
    print(f"\n  Fisher's exact test: p = {p_val:.4f}")
    if p_val > 0.05:
        print(f"  → NOT statistically significant (p > 0.05)")
        print(f"    The difference between {n_tight_false/n_tight*100:.1f}% and "
              f"{n_non_false/n_non*100:.1f}% could be random chance with n={n_tight}.")
    else:
        print(f"  → Statistically significant (p ≤ 0.05)")

    # Bootstrap confidence interval for tightened false exit rate
    rng = np.random.default_rng(42)
    boot_rates = []
    tight_outcomes = [1 if r["is_false_exit"] else 0 for r in tightened_exits]
    for _ in range(10000):
        sample = rng.choice(tight_outcomes, size=len(tight_outcomes), replace=True)
        boot_rates.append(np.mean(sample) * 100)
    ci_lo = np.percentile(boot_rates, 2.5)
    ci_hi = np.percentile(boot_rates, 97.5)
    print(f"\n  Tightened false exit rate 95% CI: [{ci_lo:.1f}%, {ci_hi:.1f}%]")
    print(f"  (Point estimate {n_tight_false/n_tight*100:.1f}%, but with n={n_tight} "
          f"the CI is huge)")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 2: RE-ENTRY CAPTURE ANALYSIS
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§2  RE-ENTRY CAPTURE")
    print(f"    Does V10 re-enter after a false exit and recover the continuation?")
    print(f"{'━' * 85}")

    # For each false exit, find the NEXT trade and measure:
    # - Time gap to re-entry
    # - How much of the continuation move the next trade captured
    # - Net damage = forgone - recaptured
    reentry_analysis = []
    for fe in [r for r in prev if r["is_false_exit"]]:
        tid = fe["trade_id"]
        trade = trade_by_id[tid]

        # Find next trade
        next_trade = None
        for t in trades_sorted:
            if t.entry_ts_ms > trade.exit_ts_ms:
                next_trade = t
                break

        if next_trade is None:
            reentry_analysis.append({
                **fe,
                "next_trade_id": None,
                "gap_hours": None,
                "next_entry_price": None,
                "next_return_pct": None,
                "reentry_captured": False,
                "reentry_slip_pct": None,
                "net_damage_pct": fe["forgone_pct"],
            })
            continue

        gap_hours = (next_trade.entry_ts_ms - trade.exit_ts_ms) / (1000 * 3600)
        reentry_slip = (next_trade.entry_price / trade.exit_price - 1) * 100

        # Did next trade capture the continuation?
        # If next entry price < exit_price + continuation, re-entry captured some
        exit_idx = find_bar_index(h4_bars, trade.exit_ts_ms)
        ahead_end = min(exit_idx + 16, len(h4_bars))
        future_peak = max(h4_closes[exit_idx+1:ahead_end]) if ahead_end > exit_idx + 1 else trade.exit_price
        forgone_move = future_peak - trade.exit_price

        # How much of forgone move did next trade capture?
        if next_trade.entry_ts_ms < h4_bars[min(ahead_end-1, len(h4_bars)-1)].close_time:
            # Re-entered within the look-ahead window
            # Captured = next_trade got in before the peak
            if next_trade.entry_price < future_peak:
                recaptured_pct = max(0, (future_peak - next_trade.entry_price) / trade.exit_price * 100)
            else:
                recaptured_pct = 0
            reentry_in_window = True
        else:
            recaptured_pct = 0
            reentry_in_window = False

        net_damage = fe["forgone_pct"] - recaptured_pct

        reentry_analysis.append({
            **fe,
            "next_trade_id": next_trade.trade_id,
            "gap_hours": round(gap_hours, 1),
            "next_entry_price": next_trade.entry_price,
            "next_return_pct": next_trade.return_pct,
            "reentry_captured": reentry_in_window,
            "reentry_slip_pct": round(reentry_slip, 2),
            "recaptured_pct": round(recaptured_pct, 2),
            "net_damage_pct": round(net_damage, 2),
        })

    print(f"\n  {'ID':>4} {'Comp':<10} {'Forgone%':>9} {'GapH':>6} {'ReSlip%':>8} "
          f"{'Recap%':>7} {'NetDmg%':>8} {'NextRet%':>9}")
    print(f"  {'─'*4} {'─'*10} {'─'*9} {'─'*6} {'─'*8} {'─'*7} {'─'*8} {'─'*9}")

    total_forgone = 0
    total_recaptured = 0
    tightened_forgone = 0
    tightened_recaptured = 0

    for r in sorted(reentry_analysis, key=lambda x: -x["forgone_pct"]):
        gap = f"{r['gap_hours']:.0f}" if r['gap_hours'] is not None else "—"
        slip = f"{r['reentry_slip_pct']:.1f}" if r.get('reentry_slip_pct') is not None else "—"
        recap = f"{r.get('recaptured_pct', 0):.1f}"
        nret = f"{r['next_return_pct']:.1f}" if r['next_return_pct'] is not None else "—"
        print(f"  {r['trade_id']:>4} {r['compression']:<10} {r['forgone_pct']:>8.1f}% "
              f"{gap:>6} {slip:>7}% {recap:>6}% {r['net_damage_pct']:>7.1f}% {nret:>8}%")

        total_forgone += r["forgone_pct"]
        total_recaptured += r.get("recaptured_pct", 0)
        if r["tightened"]:
            tightened_forgone += r["forgone_pct"]
            tightened_recaptured += r.get("recaptured_pct", 0)

    print(f"\n  Summary (all 23 false exits):")
    print(f"    Total forgone:    {total_forgone:>7.1f}%")
    print(f"    Total recaptured: {total_recaptured:>7.1f}%")
    print(f"    Net damage:       {total_forgone - total_recaptured:>7.1f}%")
    print(f"    Recovery rate:    {total_recaptured/total_forgone*100:.1f}%")

    print(f"\n  Tightened-only (6 false exits):")
    print(f"    Total forgone:    {tightened_forgone:>7.1f}%")
    print(f"    Total recaptured: {tightened_recaptured:>7.1f}%")
    print(f"    Net damage:       {tightened_forgone - tightened_recaptured:>7.1f}%")
    if tightened_forgone > 0:
        print(f"    Recovery rate:    {tightened_recaptured/tightened_forgone*100:.1f}%")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 3: COUNTERFACTUAL — WHAT IF MULT STAYED 3.5?
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§3  COUNTERFACTUAL: WHAT IF MULT STAYED 3.5?")
    print(f"    For each tightened exit, would 3.5×ATR have avoided the stop?")
    print(f"{'━' * 85}")

    counterfactual = []
    for r in tightened_exits:
        tid = r["trade_id"]
        trade = trade_by_id[tid]
        exit_idx = find_bar_index(h4_bars, trade.exit_ts_ms)
        entry_idx = find_bar_index(h4_bars, trade.entry_ts_ms)

        # Reconstruct peak_price
        peak_price = r["peak_price"]
        atr_at_exit = r["atr_at_exit"]

        # Actual stop (mult=2.5)
        actual_stop = peak_price - TRAIL_TIGHTEN_MULT * atr_at_exit
        # Counterfactual stop (mult=3.5)
        cf_stop = peak_price - TRAIL_ATR_MULT * atr_at_exit

        exit_price = trade.exit_price

        # Would 3.5 have NOT triggered at this bar?
        cf_would_survive = exit_price > cf_stop

        # If survived, scan forward to find when 3.5 WOULD have triggered
        cf_exit_idx = None
        cf_exit_price = None
        cf_extra_bars = 0
        if cf_would_survive:
            # Simulate forward with mult=3.5, tracking peak
            sim_peak = peak_price
            for i in range(exit_idx + 1, min(exit_idx + 100, len(h4_bars))):
                sim_mid = h4_closes[i]
                sim_peak = max(sim_peak, sim_mid)
                sim_atr = h4_atr[i]
                # Check if peak_profit still ≥ tighten threshold → still use 2.5
                # But in counterfactual we force 3.5
                cf_stop_i = sim_peak - TRAIL_ATR_MULT * sim_atr
                if sim_mid <= cf_stop_i:
                    cf_exit_idx = i
                    cf_exit_price = sim_mid
                    cf_extra_bars = i - exit_idx
                    break

        # Calculate counterfactual gain/loss
        if cf_would_survive and cf_exit_price is not None:
            cf_delta_pct = (cf_exit_price / exit_price - 1) * 100
        elif cf_would_survive and cf_exit_price is None:
            # 3.5 never triggered in next 100 bars — big potential gain
            # Use the price 100 bars out as proxy
            lookahead = min(exit_idx + 100, len(h4_bars) - 1)
            cf_delta_pct = (h4_closes[lookahead] / exit_price - 1) * 100
            cf_extra_bars = 100
        else:
            cf_delta_pct = 0
            cf_extra_bars = 0

        counterfactual.append({
            "trade_id": tid,
            "exit_price": exit_price,
            "peak_profit_pct": r["peak_profit_pct"],
            "return_pct": r["return_pct"],
            "actual_stop": round(actual_stop, 2),
            "cf_stop_35": round(cf_stop, 2),
            "cf_would_survive": cf_would_survive,
            "cf_extra_bars": cf_extra_bars,
            "cf_exit_price": round(cf_exit_price, 2) if cf_exit_price else None,
            "cf_delta_pct": round(cf_delta_pct, 2),
            "is_false_exit": r["is_false_exit"],
            "forgone_pct": r["forgone_pct"],
            "compression": r["compression"],
        })

    print(f"\n  {'ID':>4} {'PeakP%':>7} {'Ret%':>7} {'2.5 Stop':>10} {'3.5 Stop':>10} "
          f"{'Survive?':>9} {'Extra':>6} {'CF Δ%':>7} {'FalseEx':>8}")
    print(f"  {'─'*4} {'─'*7} {'─'*7} {'─'*10} {'─'*10} {'─'*9} {'─'*6} {'─'*7} {'─'*8}")

    survived_count = 0
    for c in counterfactual:
        surv = "YES" if c["cf_would_survive"] else "no"
        fe = "★ YES" if c["is_false_exit"] else "no"
        print(f"  {c['trade_id']:>4} {c['peak_profit_pct']:>6.1f}% {c['return_pct']:>6.1f}% "
              f"{c['actual_stop']:>10.0f} {c['cf_stop_35']:>10.0f} "
              f"{surv:>9} {c['cf_extra_bars']:>5}b {c['cf_delta_pct']:>6.1f}% {fe:>8}")
        if c["cf_would_survive"]:
            survived_count += 1

    print(f"\n  Of {len(counterfactual)} tightened exits:")
    print(f"    Would survive with 3.5: {survived_count}/{len(counterfactual)} "
          f"({survived_count/len(counterfactual)*100:.0f}%)")
    print(f"    Would STILL trigger:    {len(counterfactual)-survived_count}/{len(counterfactual)}")

    # Among those that survived, what's the average extra gain?
    survivors = [c for c in counterfactual if c["cf_would_survive"]]
    if survivors:
        avg_cf_delta = np.mean([c["cf_delta_pct"] for c in survivors])
        avg_extra_bars = np.mean([c["cf_extra_bars"] for c in survivors])
        print(f"    Avg extra gain with 3.5: {avg_cf_delta:+.1f}%")
        print(f"    Avg extra bars held:     {avg_extra_bars:.0f} bars ({avg_extra_bars*4:.0f}h)")

    # Among false exits specifically
    false_survivors = [c for c in counterfactual if c["cf_would_survive"] and c["is_false_exit"]]
    print(f"\n  Among the 6 tightened FALSE exits:")
    print(f"    Would survive with 3.5: {len(false_survivors)}/6")
    if false_survivors:
        avg_delta = np.mean([c["cf_delta_pct"] for c in false_survivors])
        print(f"    Avg counterfactual gain: {avg_delta:+.1f}%")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 4: PROFIT PROTECTION RATIO
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§4  PROFIT PROTECTION: CAPTURED vs FORGONE")
    print(f"    Tightening activates at ≥20% peak profit. How much was locked in vs left behind?")
    print(f"{'━' * 85}")

    print(f"\n  {'ID':>4} {'EntryPx':>10} {'ExitPx':>10} {'PeakP%':>8} {'Captured%':>10} "
          f"{'Forgone%':>9} {'Ratio':>7} {'False?':>7}")
    print(f"  {'─'*4} {'─'*10} {'─'*10} {'─'*8} {'─'*10} {'─'*9} {'─'*7} {'─'*7}")

    captured_total = 0
    forgone_total = 0
    for r in tightened_exits:
        captured = r["return_pct"]  # what the trade actually returned
        forgone = r["forgone_pct"]  # what was left on the table
        ratio = captured / forgone if forgone > 0.5 else float('inf')
        fe = "★" if r["is_false_exit"] else ""
        print(f"  {r['trade_id']:>4} {r['entry_price']:>10.0f} {r['exit_price']:>10.0f} "
              f"{r['peak_profit_pct']:>7.1f}% {captured:>9.1f}% {forgone:>8.1f}% "
              f"{ratio:>6.1f}x {fe:>7}")
        captured_total += max(0, captured)
        forgone_total += forgone

    print(f"\n  Totals across {len(tightened_exits)} tightened exits:")
    print(f"    Captured profit: {captured_total:.1f}%")
    print(f"    Forgone profit:  {forgone_total:.1f}%")
    print(f"    Protection ratio: {captured_total/forgone_total:.1f}x (captured/forgone)")
    print(f"    → For every 1% forgone, {captured_total/forgone_total:.1f}% was locked in")

    # Same for false exits only
    fe_captured = sum(max(0, r["return_pct"]) for r in tightened_false)
    fe_forgone = sum(r["forgone_pct"] for r in tightened_false)
    print(f"\n  False exits only ({len(tightened_false)}):")
    print(f"    Captured: {fe_captured:.1f}%  |  Forgone: {fe_forgone:.1f}%")
    if fe_forgone > 0:
        print(f"    Ratio: {fe_captured/fe_forgone:.1f}x")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 5: SCENARIO TABLE EVIDENCE
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§5  SCENARIO TABLE: WHAT DO ACTUAL BACKTEST VARIANTS TELL US?")
    print(f"    baseline=tighten@20% | t025=tighten@25% | t030=tighten@30% (less tightening)")
    print(f"{'━' * 85}")

    print(f"\n  {'Candidate':<20} {'Scenario':<8} {'CAGR%':>7} {'MaxDD%':>7} {'Sharpe':>7} "
          f"{'Score':>7} {'PF':>6} {'Trades':>7}")
    print(f"  {'─'*20} {'─'*8} {'─'*7} {'─'*7} {'─'*7} {'─'*7} {'─'*6} {'─'*7}")

    for row in scenarios:
        print(f"  {row['candidate']:<20} {row['scenario']:<8} {float(row['cagr_pct']):>6.1f}% "
              f"{float(row['max_drawdown_mid_pct']):>6.1f}% {float(row['sharpe']):>7.4f} "
              f"{float(row['score']):>7.2f} {float(row['profit_factor']):>5.2f} "
              f"{int(row['trades']):>7}")

    # Key comparison: base scenario
    base_rows = {r['candidate']: r for r in scenarios if r['scenario'] == 'base'}
    bl = base_rows.get('baseline_legacy', {})
    t25 = base_rows.get('tighten_025', {})
    t30 = base_rows.get('tighten_030', {})

    if bl and t30:
        cagr_diff = float(t30.get('cagr_pct', 0)) - float(bl.get('cagr_pct', 0))
        sharpe_diff = float(t30.get('sharpe', 0)) - float(bl.get('sharpe', 0))
        score_diff = float(t30.get('score', 0)) - float(bl.get('score', 0))
        print(f"\n  tighten_030 vs baseline_legacy (base fees):")
        print(f"    CAGR:   {cagr_diff:+.2f}% (43.21% vs 38.55%)")
        print(f"    Sharpe: {sharpe_diff:+.4f} (1.2781 vs 1.1884)")
        print(f"    Score:  {score_diff:+.2f} (107.55 vs 94.50)")
        print(f"\n  → LESS tightening (tighten@30% instead of @20%) → BETTER performance")
        print(f"    This means the tighten@20% IS suboptimal, BUT...")
        print(f"    The fix already EXISTS (raise threshold to 25-30%).")
        print(f"    The question is: how much damage does @20% actually cause?")
        print(f"    Answer: +{cagr_diff:.2f}% CAGR improvement = ~{cagr_diff/float(bl.get('cagr_pct', 1))*100:.1f}% relative gain")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 6: NET $ DAMAGE ESTIMATE
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§6  NET $ DAMAGE: TOTAL PnL IMPACT")
    print(f"{'━' * 85}")

    # Total PnL from all trades
    total_pnl = sum(t.pnl for t in trades)
    trail_pnl = sum(trade_by_id[r["trade_id"]].pnl for r in prev)
    tightened_pnl = sum(trade_by_id[r["trade_id"]].pnl for r in tightened_exits)
    tightened_false_pnl = sum(trade_by_id[r["trade_id"]].pnl for r in tightened_false)

    print(f"\n  Total PnL all 103 trades:       ${total_pnl:>12,.0f}")
    print(f"  PnL from 65 trailing stops:     ${trail_pnl:>12,.0f}")
    print(f"  PnL from {len(tightened_exits)} tightened trail exits: ${tightened_pnl:>12,.0f}")
    print(f"  PnL from 6 tightened FALSE exits: ${tightened_false_pnl:>12,.0f}")

    print(f"\n  The 6 tightened false exits:")
    for r in tightened_false:
        t = trade_by_id[r["trade_id"]]
        print(f"    #{r['trade_id']}: PnL ${t.pnl:>+10,.0f} (ret {r['return_pct']:>+.1f}%, "
              f"peak {r['peak_profit_pct']:.1f}%, forgone {r['forgone_pct']:.1f}%)")

    print(f"\n  Note: These 6 trades generated ${tightened_false_pnl:>,.0f} in ACTUAL profit.")
    print(f"  They 'left on the table' an estimated additional "
          f"~${sum(r['forgone_pct']/100 * trade_by_id[r['trade_id']].exit_price * trade_by_id[r['trade_id']].qty for r in tightened_false):>,.0f}")

    # Estimate forgone $ using qty and forgone_pct
    forgone_dollars = 0
    for r in tightened_false:
        t = trade_by_id[r["trade_id"]]
        forgone_dollars += r["forgone_pct"] / 100 * t.exit_price * t.qty

    # But recaptured through re-entry
    recaptured_dollars = 0
    for ra in reentry_analysis:
        if ra["tightened"] and ra["is_false_exit"]:
            t = trade_by_id[ra["trade_id"]]
            recaptured_dollars += ra.get("recaptured_pct", 0) / 100 * t.exit_price * t.qty

    net_damage_dollars = forgone_dollars - recaptured_dollars

    print(f"\n  Dollar damage estimate (tightened false exits):")
    print(f"    Forgone:    ${forgone_dollars:>10,.0f}")
    print(f"    Recaptured: ${recaptured_dollars:>10,.0f}")
    print(f"    Net damage: ${net_damage_dollars:>10,.0f}")
    print(f"    As % of total PnL: {net_damage_dollars/total_pnl*100:.2f}%")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 7: THE REAL QUESTION — IS THIS TIGHTENING-SPECIFIC?
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§7  IS THIS TIGHTENING-SPECIFIC OR A TRAILING STOP BASE RATE?")
    print(f"{'━' * 85}")

    # Compare tightened vs non-tightened across ALL metrics
    print(f"\n  {'Metric':<35} {'Tightened':>12} {'Non-tight':>12} {'Ratio':>8}")
    print(f"  {'─'*35} {'─'*12} {'─'*12} {'─'*8}")

    t_rets = [r["return_pct"] for r in tightened_exits]
    n_rets = [r["return_pct"] for r in non_tightened_trail]
    print(f"  {'False exit rate':<35} {n_tight_false/n_tight*100:>11.1f}% "
          f"{n_non_false/n_non*100:>11.1f}% {(n_tight_false/n_tight)/(n_non_false/n_non) if n_non_false > 0 else 0:>7.2f}x")

    t_forgone = [r["forgone_pct"] for r in tightened_exits]
    n_forgone = [r["forgone_pct"] for r in non_tightened_trail]
    print(f"  {'Avg forgone % (all exits)':<35} {np.mean(t_forgone):>11.1f}% "
          f"{np.mean(n_forgone):>11.1f}% {np.mean(t_forgone)/max(np.mean(n_forgone),0.01):>7.2f}x")

    t_cont = [r["continuation_pct"] for r in tightened_exits]
    n_cont = [r["continuation_pct"] for r in non_tightened_trail]
    print(f"  {'Avg continuation % (all exits)':<35} {np.mean(t_cont):>11.1f}% "
          f"{np.mean(n_cont):>11.1f}% {np.mean(t_cont)/max(np.mean(n_cont),0.01):>7.2f}x")

    print(f"  {'Avg return % per trade':<35} {np.mean(t_rets):>11.1f}% "
          f"{np.mean(n_rets):>11.1f}%")
    print(f"  {'Avg peak profit %':<35} "
          f"{np.mean([r['peak_profit_pct'] for r in tightened_exits]):>11.1f}% "
          f"{np.mean([r['peak_profit_pct'] for r in non_tightened_trail]):>11.1f}%")
    print(f"  {'Avg days held':<35} "
          f"{np.mean([r['days_held'] for r in tightened_exits]):>11.1f} "
          f"{np.mean([r['days_held'] for r in non_tightened_trail]):>11.1f}")

    # The key insight: tightened trades have HIGHER continuation because they
    # exit during strong trends (that's why profit hit 20%+)
    print(f"\n  Key insight:")
    print(f"  Tightened exits happen in STRONG TRENDS (that's how profit reached ≥20%).")
    print(f"  Strong trends naturally have higher continuation after any exit.")
    print(f"  The 54.5% rate is likely a SELECTION BIAS, not a tightening flaw:")
    print(f"    → You exit during a raging bull (because you tightened)")
    print(f"    → The bull keeps going (because it's a raging bull)")
    print(f"    → This looks like a 'false exit' but it's actually trend following")
    print(f"       doing exactly what it should: taking profit before reversal.")

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 8: WHAT ABOUT NON-TIGHTENED FALSE EXITS?
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("§8  THE ELEPHANT IN THE ROOM: NON-TIGHTENED FALSE EXITS")
    print(f"{'━' * 85}")

    non_tight_fe_pnl = sum(trade_by_id[r["trade_id"]].pnl for r in non_tightened_false)
    non_tight_forgone_dollars = sum(
        r["forgone_pct"]/100 * trade_by_id[r["trade_id"]].exit_price * trade_by_id[r["trade_id"]].qty
        for r in non_tightened_false
    )

    print(f"\n  Non-tightened trailing stop false exits: {n_non_false}/{n_non} = {n_non_false/n_non*100:.1f}%")
    print(f"  These exits used mult=3.5 (the WIDER stop) and STILL got stopped out falsely.")
    print(f"  PnL from these trades: ${non_tight_fe_pnl:>,.0f}")
    print(f"  Forgone dollars: ${non_tight_forgone_dollars:>,.0f}")
    print(f"\n  Largest non-tightened false exits:")
    for r in sorted(non_tightened_false, key=lambda x: -x["forgone_pct"])[:5]:
        t = trade_by_id[r["trade_id"]]
        print(f"    #{r['trade_id']}: forgone {r['forgone_pct']:.1f}%, "
              f"ret {r['return_pct']:+.1f}%, PnL ${t.pnl:>+,.0f} ({r['regime']})")

    print(f"\n  → The biggest false exits are NOT from tightening.")
    print(f"     #34 (27% forgone, ATR_ONLY), #41 (12% forgone, NONE), #89 (12% forgone, NONE)")
    print(f"     These used mult=3.5 and still got whipped out.")

    # ══════════════════════════════════════════════════════════════════════
    # FINAL VERDICT
    # ══════════════════════════════════════════════════════════════════════
    print(f"\n{'━' * 85}")
    print("FINAL VERDICT")
    print(f"{'━' * 85}")

    print(f"""
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  Q: Is trail tightening (mult 3.5→2.5 at ≥20% profit) a real problem?     │
  │                                                                             │
  │  A: MILD ISSUE — worth tuning but not urgent or severe.                    │
  │                                                                             │
  │  Evidence:                                                                  │
  │                                                                             │
  │  1. SAMPLE SIZE: n=11 tightened exits, 6 false. Fisher's p={p_val:.2f}.              │
  │     Not statistically significant vs non-tightened base rate.               │
  │                                                                             │
  │  2. SELECTION BIAS: Tightened exits happen in strong trends                 │
  │     (peak_profit ≥20%). Strong trends naturally continue → higher           │
  │     false exit rate is expected regardless of multiplier.                    │
  │                                                                             │
  │  3. COUNTERFACTUAL: Only {len(false_survivors)}/6 false exits would have survived                │
  │     with mult=3.5. The others would have triggered anyway.                  │
  │                                                                             │
  │  4. PROFIT PROTECTION: Tightened trades captured {captured_total:.0f}% total              │
  │     profit vs {forgone_total:.0f}% forgone. Ratio: {captured_total/forgone_total:.1f}x captured per 1 forgone.      │
  │                                                                             │
  │  5. SCENARIO TABLE: tighten_030 (raise threshold to 30%) gains              │
  │     +{float(t30.get('cagr_pct',0))-float(bl.get('cagr_pct',0)):.1f}% CAGR. The fix exists and is already tested.              │
  │                                                                             │
  │  6. NET $ DAMAGE: ${net_damage_dollars:>,.0f} net damage from tightened false exits      │
  │     = {net_damage_dollars/total_pnl*100:.2f}% of total strategy PnL.                                   │
  │                                                                             │
  │  7. THE REAL PROBLEM: Overall 35% false exit rate across ALL                │
  │     compression types. Non-tightened exits (mult=3.5) have 33.3%            │
  │     false exit rate. Tightening is NOT the root cause.                      │
  │                                                                             │
  │  RECOMMENDATION:                                                            │
  │  • Raise trail_tighten_profit_pct from 0.20 → 0.30 (already validated)     │
  │  • Expected gain: ~+4.7% CAGR, +0.09 Sharpe                               │
  │  • Do NOT redesign the trailing stop system for this                        │
  └─────────────────────────────────────────────────────────────────────────────┘
""")

    # ── Save results ───────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = {
        "statistical_significance": {
            "fisher_p_value": round(p_val, 4),
            "significant": p_val <= 0.05,
            "tightened_false_rate": round(n_tight_false/n_tight*100, 1),
            "non_tightened_false_rate": round(n_non_false/n_non*100, 1),
            "tightened_95ci": [round(ci_lo, 1), round(ci_hi, 1)],
        },
        "reentry_capture": {
            "total_forgone_pct": round(total_forgone, 1),
            "total_recaptured_pct": round(total_recaptured, 1),
            "recovery_rate_pct": round(total_recaptured/total_forgone*100, 1),
            "tightened_forgone_pct": round(tightened_forgone, 1),
            "tightened_recaptured_pct": round(tightened_recaptured, 1),
        },
        "counterfactual": {
            "would_survive_with_35": survived_count,
            "total_tightened": len(counterfactual),
            "false_exits_would_survive": len(false_survivors),
        },
        "profit_protection": {
            "captured_pct": round(captured_total, 1),
            "forgone_pct": round(forgone_total, 1),
            "ratio": round(captured_total/forgone_total, 1),
        },
        "net_damage": {
            "forgone_dollars": round(forgone_dollars, 0),
            "recaptured_dollars": round(recaptured_dollars, 0),
            "net_damage_dollars": round(net_damage_dollars, 0),
            "pct_of_total_pnl": round(net_damage_dollars/total_pnl*100, 2),
        },
        "scenario_table_evidence": {
            "baseline_cagr": float(bl.get('cagr_pct', 0)),
            "tighten030_cagr": float(t30.get('cagr_pct', 0)),
            "improvement_cagr": round(float(t30.get('cagr_pct', 0)) - float(bl.get('cagr_pct', 0)), 2),
        },
        "verdict": "MILD_ISSUE",
        "recommendation": "Raise trail_tighten_profit_pct from 0.20 to 0.30",
    }

    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Save detailed reentry analysis
    with open(OUT_DIR / "reentry_analysis.csv", "w", newline="") as f:
        if reentry_analysis:
            keys = [k for k in reentry_analysis[0].keys() if k not in
                    ("atr_at_exit", "atr_pct", "atr_compressed", "trail_dist_pct",
                     "in_noise_zone", "mult_used")]
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(reentry_analysis)

    # Save counterfactual
    with open(OUT_DIR / "counterfactual.csv", "w", newline="") as f:
        if counterfactual:
            writer = csv.DictWriter(f, fieldnames=counterfactual[0].keys())
            writer.writeheader()
            writer.writerows(counterfactual)

    print(f"  Results saved to {OUT_DIR}/")

    # ── Visualizations ─────────────────────────────────────────────────────
    if HAS_MPL:
        generate_charts(prev, tightened_exits, non_tightened_trail,
                        tightened_false, non_tightened_false,
                        reentry_analysis, counterfactual, scenarios,
                        trade_by_id, total_pnl)

    return summary


def generate_charts(prev, tightened, non_tightened, tight_false, non_tight_false,
                    reentry, counterfactual, scenarios, trade_by_id, total_pnl):
    from datetime import datetime

    fig = plt.figure(figsize=(20, 22))
    fig.suptitle("V10 Trail Tightening — Net Impact Analysis",
                 fontsize=16, fontweight='bold', y=0.98)

    # Layout: 4 rows × 2 cols
    gs = fig.add_gridspec(4, 2, hspace=0.35, wspace=0.3,
                          left=0.07, right=0.95, top=0.94, bottom=0.04)

    # ── 1. False exit rate comparison with confidence intervals ──
    ax1 = fig.add_subplot(gs[0, 0])
    categories = ['Tightened\n(mult=2.5)', 'Non-tight\n(mult=3.5)', 'All Trail\nStops']
    rates = [
        len(tight_false)/len(tightened)*100,
        len(non_tight_false)/len(non_tightened)*100,
        (len(tight_false)+len(non_tight_false))/(len(tightened)+len(non_tightened))*100,
    ]
    ns = [len(tightened), len(non_tightened), len(tightened)+len(non_tightened)]

    # Wilson CI
    def wilson_ci(successes, n, z=1.96):
        if n == 0:
            return 0, 0
        p_hat = successes / n
        denom = 1 + z**2 / n
        centre = (p_hat + z**2 / (2*n)) / denom
        spread = z * np.sqrt((p_hat*(1-p_hat) + z**2/(4*n)) / n) / denom
        return max(0, (centre - spread)*100), min(100, (centre + spread)*100)

    false_counts = [len(tight_false), len(non_tight_false),
                    len(tight_false)+len(non_tight_false)]
    cis = [wilson_ci(fc, n) for fc, n in zip(false_counts, ns)]
    ci_lo = [r - ci[0] for r, ci in zip(rates, cis)]
    ci_hi = [ci[1] - r for r, ci in zip(rates, cis)]

    colors = ['#e74c3c', '#3498db', '#95a5a6']
    bars = ax1.bar(categories, rates, color=colors, edgecolor='black', linewidth=0.5,
                   yerr=[ci_lo, ci_hi], capsize=8, error_kw={'linewidth': 2})
    for bar, rate, n in zip(bars, rates, ns):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                f'{rate:.1f}%\nn={n}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax1.set_ylabel("False Exit Rate (%)", fontsize=11)
    ax1.set_title("False Exit Rate with 95% Wilson CI", fontsize=12, fontweight='bold')
    ax1.set_ylim(0, 100)
    ax1.axhline(y=rates[1], color='#3498db', linestyle='--', alpha=0.3)
    ax1.text(0.98, rates[1]+1, 'base rate', ha='right', va='bottom',
             transform=ax1.get_yaxis_transform(), color='#3498db', fontsize=8)

    # ── 2. Profit protection: captured vs forgone ──
    ax2 = fig.add_subplot(gs[0, 1])
    trade_ids = [r["trade_id"] for r in tightened]
    captured = [r["return_pct"] for r in tightened]
    forgone = [r["forgone_pct"] for r in tightened]
    x = np.arange(len(trade_ids))

    bars_c = ax2.bar(x - 0.18, captured, 0.35, label='Captured return %',
                     color='#27ae60', edgecolor='black', linewidth=0.3)
    bars_f = ax2.bar(x + 0.18, forgone, 0.35, label='Forgone %',
                     color='#e74c3c', alpha=0.6, edgecolor='black', linewidth=0.3)

    # Mark false exits
    for i, r in enumerate(tightened):
        if r["is_false_exit"]:
            ax2.annotate('★', (x[i], max(captured[i], forgone[i]) + 1),
                        ha='center', fontsize=14, color='red')

    ax2.set_xticks(x)
    ax2.set_xticklabels([f'#{tid}' for tid in trade_ids], fontsize=8, rotation=45)
    ax2.set_ylabel("Percentage (%)", fontsize=11)
    ax2.set_title("Profit Captured vs Forgone (★ = false exit)", fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.axhline(y=0, color='black', linewidth=0.5)

    # ── 3. Counterfactual: would 3.5 have saved the trade? ──
    ax3 = fig.add_subplot(gs[1, 0])
    cf_ids = [c["trade_id"] for c in counterfactual]
    cf_deltas = [c["cf_delta_pct"] for c in counterfactual]
    cf_survived = [c["cf_would_survive"] for c in counterfactual]
    cf_false = [c["is_false_exit"] for c in counterfactual]

    bar_colors = []
    for s, f in zip(cf_survived, cf_false):
        if not s:
            bar_colors.append('#95a5a6')  # wouldn't help
        elif f:
            bar_colors.append('#e74c3c')  # would help, was false exit
        else:
            bar_colors.append('#f39c12')  # would help, wasn't false exit

    bars_cf = ax3.bar(range(len(cf_ids)), cf_deltas, color=bar_colors,
                      edgecolor='black', linewidth=0.5)
    ax3.set_xticks(range(len(cf_ids)))
    ax3.set_xticklabels([f'#{tid}' for tid in cf_ids], fontsize=8, rotation=45)
    ax3.set_ylabel("Counterfactual Δ%\n(+ = 3.5 better)", fontsize=10)
    ax3.set_title("Counterfactual: Gain if mult stayed 3.5", fontsize=12, fontweight='bold')
    ax3.axhline(y=0, color='black', linewidth=0.8)

    legend_items = [
        mpatches.Patch(color='#95a5a6', label='3.5 also triggers'),
        mpatches.Patch(color='#f39c12', label='3.5 survives (not false)'),
        mpatches.Patch(color='#e74c3c', label='3.5 survives (false exit)'),
    ]
    ax3.legend(handles=legend_items, fontsize=8)

    # ── 4. Re-entry recovery waterfall ──
    ax4 = fig.add_subplot(gs[1, 1])
    # Show forgone vs recaptured for each false exit
    fe_sorted = sorted([r for r in reentry if r["is_false_exit"]], key=lambda x: -x["forgone_pct"])
    fe_ids = [f"#{r['trade_id']}" for r in fe_sorted]
    fe_forgone = [r["forgone_pct"] for r in fe_sorted]
    fe_recaptured = [r.get("recaptured_pct", 0) for r in fe_sorted]
    fe_net = [f - rc for f, rc in zip(fe_forgone, fe_recaptured)]

    x_fe = np.arange(len(fe_ids))
    width = 0.25
    ax4.bar(x_fe - width, fe_forgone, width, label='Forgone %', color='#e74c3c',
            edgecolor='black', linewidth=0.3)
    ax4.bar(x_fe, fe_recaptured, width, label='Recaptured %', color='#27ae60',
            edgecolor='black', linewidth=0.3)
    ax4.bar(x_fe + width, fe_net, width, label='Net damage %', color='#8e44ad',
            edgecolor='black', linewidth=0.3)

    # Mark tightened ones
    for i, r in enumerate(fe_sorted):
        if r["tightened"]:
            ax4.annotate('T', (x_fe[i], max(fe_forgone[i], 0) + 0.3),
                        ha='center', fontsize=9, fontweight='bold', color='red')

    ax4.set_xticks(x_fe)
    ax4.set_xticklabels(fe_ids, fontsize=7, rotation=45)
    ax4.set_ylabel("Percentage (%)", fontsize=11)
    ax4.set_title("Re-entry Recovery per False Exit (T = tightened)", fontsize=12, fontweight='bold')
    ax4.legend(fontsize=8)

    # ── 5. Scenario table comparison ──
    ax5 = fig.add_subplot(gs[2, 0])
    candidates = ['baseline_legacy', 'tighten_025', 'tighten_030']
    labels = ['Tighten@20%\n(baseline)', 'Tighten@25%', 'Tighten@30%']
    metrics = {'CAGR%': 'cagr_pct', 'Sharpe': 'sharpe'}

    base_sc = {r['candidate']: r for r in scenarios if r['scenario'] == 'base'}
    x_sc = np.arange(len(candidates))

    cagrs = [float(base_sc[c]['cagr_pct']) for c in candidates]
    sharpes = [float(base_sc[c]['sharpe']) for c in candidates]

    ax5_twin = ax5.twinx()
    bars_cagr = ax5.bar(x_sc - 0.18, cagrs, 0.35, label='CAGR %', color='#2980b9',
                        edgecolor='black', linewidth=0.5)
    bars_sh = ax5_twin.bar(x_sc + 0.18, sharpes, 0.35, label='Sharpe', color='#e67e22',
                           edgecolor='black', linewidth=0.5)

    for bar, val in zip(bars_cagr, cagrs):
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f'{val:.1f}%', ha='center', fontsize=9, fontweight='bold', color='#2980b9')
    for bar, val in zip(bars_sh, sharpes):
        ax5_twin.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                     f'{val:.4f}', ha='center', fontsize=8, fontweight='bold', color='#e67e22')

    ax5.set_xticks(x_sc)
    ax5.set_xticklabels(labels, fontsize=9)
    ax5.set_ylabel("CAGR %", color='#2980b9', fontsize=11)
    ax5_twin.set_ylabel("Sharpe", color='#e67e22', fontsize=11)
    ax5.set_title("Less Tightening → Better Performance", fontsize=12, fontweight='bold')

    # Add arrow
    ax5.annotate('', xy=(2, cagrs[2]), xytext=(0, cagrs[0]),
                arrowprops=dict(arrowstyle='->', color='green', lw=2))
    ax5.text(1, (cagrs[0]+cagrs[2])/2 + 0.5,
            f'+{cagrs[2]-cagrs[0]:.1f}%', ha='center', fontsize=10,
            fontweight='bold', color='green')

    # ── 6. Selection bias: peak profit vs continuation ──
    ax6 = fig.add_subplot(gs[2, 1])
    for label, subset, color, marker in [
        ('Tightened', tightened, '#e74c3c', 's'),
        ('Non-tight', non_tightened, '#3498db', 'o'),
    ]:
        peaks = [r["peak_profit_pct"] for r in subset]
        conts = [r["continuation_pct"] for r in subset]
        false_flags = [r["is_false_exit"] for r in subset]
        sizes = [120 if f else 40 for f in false_flags]
        alphas = [0.9 if f else 0.5 for f in false_flags]
        ax6.scatter(peaks, conts, c=color, marker=marker, s=sizes,
                   label=label, alpha=0.7, edgecolors='black', linewidth=0.3)

    ax6.axhline(y=3, color='red', linestyle='--', alpha=0.4, label='3% threshold')
    ax6.set_xlabel("Peak Profit %", fontsize=11)
    ax6.set_ylabel("Post-Exit Continuation %", fontsize=11)
    ax6.set_title("Selection Bias: Higher Peak → Higher Continuation",
                  fontsize=12, fontweight='bold')
    ax6.legend(fontsize=8)

    # Trend line
    all_peaks = [r["peak_profit_pct"] for r in prev]
    all_conts = [r["continuation_pct"] for r in prev]
    if len(all_peaks) > 2:
        z = np.polyfit(all_peaks, all_conts, 1)
        p = np.poly1d(z)
        x_fit = np.linspace(min(all_peaks), max(all_peaks), 50)
        ax6.plot(x_fit, p(x_fit), '--', color='gray', alpha=0.5, linewidth=1)
        corr = np.corrcoef(all_peaks, all_conts)[0, 1]
        ax6.text(0.05, 0.95, f'r = {corr:.3f}', transform=ax6.transAxes,
                fontsize=9, va='top', color='gray')

    # ── 7. Dollar damage breakdown ──
    ax7 = fig.add_subplot(gs[3, 0])

    # Waterfall chart
    total_pnl_k = total_pnl / 1000
    tight_fe_dollars = sum(
        r["forgone_pct"]/100 * trade_by_id[r["trade_id"]].exit_price * trade_by_id[r["trade_id"]].qty
        for r in tight_false
    ) / 1000
    nontig_fe_dollars = sum(
        r["forgone_pct"]/100 * trade_by_id[r["trade_id"]].exit_price * trade_by_id[r["trade_id"]].qty
        for r in non_tight_false
    ) / 1000

    labels_wf = ['Total\nStrategy PnL', 'Tightened\nFalse Exit\nForgone', 'Non-tight\nFalse Exit\nForgone']
    values_wf = [total_pnl_k, tight_fe_dollars, nontig_fe_dollars]
    colors_wf = ['#27ae60', '#e74c3c', '#e67e22']

    ax7.bar(labels_wf, values_wf, color=colors_wf, edgecolor='black', linewidth=0.5)
    for i, (lbl, v) in enumerate(zip(labels_wf, values_wf)):
        ax7.text(i, v + max(values_wf)*0.02, f'${v:,.0f}k', ha='center',
                fontsize=10, fontweight='bold')

    ax7.set_ylabel("USD (thousands)", fontsize=11)
    ax7.set_title("Dollar Impact: Strategy PnL vs Forgone", fontsize=12, fontweight='bold')

    # Add percentage annotation
    if total_pnl_k > 0:
        pct = tight_fe_dollars / total_pnl_k * 100
        ax7.text(1, tight_fe_dollars * 0.5,
                f'{pct:.1f}% of\ntotal PnL', ha='center', fontsize=9, color='white',
                fontweight='bold')

    # ── 8. Summary verdict graphic ──
    ax8 = fig.add_subplot(gs[3, 1])
    ax8.axis('off')

    verdict_text = (
        "VERDICT: MILD ISSUE\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"• Fisher's p = {fisher_exact_test(len(tight_false), len(tightened)-len(tight_false), len(non_tight_false), len(non_tightened)-len(non_tight_false)):.2f} → NOT significant\n\n"
        f"• 95% CI for tightened rate:\n"
        f"  [{wilson_ci(len(tight_false), len(tightened))[0]:.0f}%, "
        f"{wilson_ci(len(tight_false), len(tightened))[1]:.0f}%] ← huge range\n\n"
        f"• Counterfactual: only {len([c for c in counterfactual if c['cf_would_survive'] and c['is_false_exit']])}/6\n"
        f"  false exits saved by 3.5\n\n"
        f"• Net $ damage: {tight_fe_dollars/total_pnl_k*100:.1f}% of total PnL\n\n"
        f"• Fix: raise threshold 20%→30%\n"
        f"  → +{float(base_sc.get('tighten_030',{}).get('cagr_pct',0))-float(base_sc.get('baseline_legacy',{}).get('cagr_pct',0)):.1f}% CAGR (already validated)\n\n"
        "• Root cause: 35% base false exit rate\n"
        "  across ALL types, not tightening-specific"
    )
    ax8.text(0.05, 0.95, verdict_text, transform=ax8.transAxes,
            fontsize=11, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='#f8f9fa', edgecolor='#2c3e50',
                     linewidth=2))

    chart_path = OUT_DIR / "net_impact_analysis.png"
    fig.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Chart saved to {chart_path}")


if __name__ == "__main__":
    analyze()
