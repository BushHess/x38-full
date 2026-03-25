#!/usr/bin/env python3
"""V10 baseline regime decomposition — per-regime equity + trade stats.

Reuses backtest from reproduce_v10_full_backtest.py constants.
Outputs:
  - v10_regime_decomposition.csv  (one row per scenario × regime)
  - reports/v10_baseline_profile.md
"""

import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Bar, EquitySnap, Fill, Trade
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, AnalyticalRegime, compute_regime_returns
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
OUTDIR = Path(__file__).resolve().parents[1]

SCENARIO_ORDER = ["smart", "base", "harsh"]
REGIME_ORDER = ["BULL", "TOPPING", "BEAR", "SHOCK", "CHOP", "NEUTRAL"]


def _map_trade_to_regime(
    trade: Trade,
    d1_bars: list[Bar],
    regimes: list[AnalyticalRegime],
) -> str:
    """Map a trade to the dominant regime during its holding period.

    Uses the regime at trade entry (the D1 bar whose close_time is
    strictly before the trade entry timestamp).
    """
    d1_close_times = [b.close_time for b in d1_bars]
    # Find latest D1 bar with close_time < trade entry
    idx = -1
    for i, ct in enumerate(d1_close_times):
        if ct < trade.entry_ts_ms:
            idx = i
        else:
            break
    if idx >= 0:
        return regimes[idx].value
    return "NEUTRAL"


def _map_fill_to_regime(
    fill: Fill,
    d1_bars: list[Bar],
    regimes: list[AnalyticalRegime],
) -> str:
    """Map a fill to the regime at its timestamp."""
    d1_close_times = [b.close_time for b in d1_bars]
    idx = -1
    for i, ct in enumerate(d1_close_times):
        if ct < fill.ts_ms:
            idx = i
        else:
            break
    if idx >= 0:
        return regimes[idx].value
    return "NEUTRAL"


def compute_trade_stats_by_regime(
    trades: list[Trade],
    fills: list[Fill],
    d1_bars: list[Bar],
    regimes: list[AnalyticalRegime],
) -> dict[str, dict]:
    """Compute per-regime trade statistics."""
    # Pre-compute d1_close_times as numpy array for fast searchsorted
    d1_ct = np.array([b.close_time for b in d1_bars], dtype=np.int64)
    regime_arr = regimes

    def _regime_at(ts_ms: int) -> str:
        idx = int(np.searchsorted(d1_ct, ts_ms, side="left")) - 1
        if idx >= 0:
            return regime_arr[idx].value
        return "NEUTRAL"

    # Group trades by regime at entry
    trade_groups: dict[str, list[Trade]] = {r: [] for r in REGIME_ORDER}
    for t in trades:
        r = _regime_at(t.entry_ts_ms)
        trade_groups[r].append(t)

    # Group fills by regime
    fill_groups: dict[str, list[Fill]] = {r: [] for r in REGIME_ORDER}
    for f in fills:
        r = _regime_at(f.ts_ms)
        fill_groups[r].append(f)

    results = {}
    for regime_name in REGIME_ORDER:
        rtrades = trade_groups[regime_name]
        rfills = fill_groups[regime_name]
        n = len(rtrades)

        wins = sum(1 for t in rtrades if t.pnl > 0)
        losses = n - wins
        win_rate = (wins / n * 100.0) if n > 0 else 0.0

        gross_profit = sum(t.pnl for t in rtrades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in rtrades if t.pnl < 0))
        if gross_loss > 0:
            pf = gross_profit / gross_loss
        elif gross_profit > 0:
            pf = float("inf")
        else:
            pf = 0.0

        total_pnl = sum(t.pnl for t in rtrades)
        avg_pnl = total_pnl / n if n > 0 else 0.0
        avg_days = sum(t.days_held for t in rtrades) / n if n > 0 else 0.0

        fees = sum(f.fee for f in rfills)
        turnover = sum(f.notional for f in rfills)

        results[regime_name] = {
            "trade_count": n,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(pf, 4) if not math.isinf(pf) else "inf",
            "total_pnl": round(total_pnl, 2),
            "avg_trade_pnl": round(avg_pnl, 2),
            "avg_days_held": round(avg_days, 2),
            "fees_paid": round(fees, 2),
            "turnover": round(turnover, 2),
        }

    return results


def run():
    t0 = time.time()
    print("=" * 70)
    print("  V10 BASELINE REGIME PROFILE")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)

    # Classify regimes on D1 bars
    regimes = classify_d1_regimes(feed.d1_bars)
    d1_bars = feed.d1_bars

    # Count regime days (D1 bars in reporting window)
    report_start_ms = feed.report_start_ms
    regime_day_counts = {r: 0 for r in REGIME_ORDER}
    for i, bar in enumerate(d1_bars):
        if report_start_ms and bar.close_time < report_start_ms:
            continue
        regime_day_counts[regimes[i].value] += 1

    total_d1 = sum(regime_day_counts.values())
    print("\nRegime distribution (D1 bars in reporting window):")
    for r in REGIME_ORDER:
        pct = regime_day_counts[r] / total_d1 * 100.0 if total_d1 > 0 else 0
        print(f"  {r:<10} {regime_day_counts[r]:>5} days  ({pct:5.1f}%)")

    # Run backtests (3 scenarios)
    all_rows = []
    all_data = {}

    for scenario_name in SCENARIO_ORDER:
        cost = SCENARIOS[scenario_name]
        strategy = V8ApexStrategy(V8ApexConfig())
        engine = BacktestEngine(
            feed=feed, strategy=strategy, cost=cost,
            initial_cash=INITIAL_CASH, warmup_mode="no_trade",
        )
        result = engine.run()
        score = compute_objective(result.summary)

        # Equity-based regime returns (CAGR proxy, MDD, Sharpe)
        regime_returns = compute_regime_returns(
            result.equity, d1_bars, regimes, report_start_ms,
        )

        # Trade-based regime stats
        trade_stats = compute_trade_stats_by_regime(
            result.trades, result.fills, d1_bars, regimes,
        )

        all_data[scenario_name] = {
            "summary": result.summary,
            "score": score,
            "regime_returns": regime_returns,
            "trade_stats": trade_stats,
        }

        print(f"\n--- {scenario_name.upper()} (score={score:.2f}) ---")
        print(f"  {'Regime':<10} {'Ret%':>8} {'MDD%':>8} {'Sharpe':>8} "
              f"{'Trades':>7} {'WR%':>7} {'PF':>7} {'AvgPnL':>9} {'Fees':>9}")
        print("  " + "-" * 85)

        for regime_name in REGIME_ORDER:
            rr = regime_returns.get(regime_name, {})
            ts = trade_stats.get(regime_name, {})

            ret = rr.get("total_return_pct", 0.0)
            mdd = rr.get("max_dd_pct", 0.0)
            sharpe = rr.get("sharpe")
            sharpe_s = f"{sharpe:8.4f}" if sharpe is not None else "     N/A"
            n_trades = ts.get("trade_count", 0)
            wr = ts.get("win_rate_pct", 0.0)
            pf = ts.get("profit_factor", 0.0)
            pf_s = f"{pf:7.2f}" if isinstance(pf, (int, float)) else f"{'inf':>7}"
            avg_pnl = ts.get("avg_trade_pnl", 0.0)
            fees = ts.get("fees_paid", 0.0)

            print(f"  {regime_name:<10} {ret:8.2f} {mdd:8.2f} {sharpe_s} "
                  f"{n_trades:>7} {wr:7.1f} {pf_s} {avg_pnl:9.2f} {fees:9.2f}")

            all_rows.append({
                "scenario": scenario_name,
                "regime": regime_name,
                "regime_days": regime_day_counts.get(regime_name, 0),
                "total_return_pct": rr.get("total_return_pct", 0.0),
                "max_dd_pct": rr.get("max_dd_pct", 0.0),
                "sharpe": rr.get("sharpe"),
                "n_equity_bars": rr.get("n_bars", 0),
                "trade_count": ts.get("trade_count", 0),
                "wins": ts.get("wins", 0),
                "losses": ts.get("losses", 0),
                "win_rate_pct": ts.get("win_rate_pct", 0.0),
                "profit_factor": ts.get("profit_factor", 0.0),
                "total_pnl": ts.get("total_pnl", 0.0),
                "avg_trade_pnl": ts.get("avg_trade_pnl", 0.0),
                "avg_days_held": ts.get("avg_days_held", 0.0),
                "fees_paid": ts.get("fees_paid", 0.0),
                "turnover": ts.get("turnover", 0.0),
            })

    # Write CSV
    csv_path = OUTDIR / "v10_regime_decomposition.csv"
    fieldnames = [
        "scenario", "regime", "regime_days",
        "total_return_pct", "max_dd_pct", "sharpe", "n_equity_bars",
        "trade_count", "wins", "losses", "win_rate_pct", "profit_factor",
        "total_pnl", "avg_trade_pnl", "avg_days_held", "fees_paid", "turnover",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)
    print(f"\nCSV saved: {csv_path}")

    # Write JSON
    json_path = OUTDIR / "v10_regime_decomposition.json"
    with open(json_path, "w") as f:
        json.dump(all_data, f, indent=2, default=str)
    print(f"JSON saved: {json_path}")

    # Generate markdown report
    _write_report(all_data, regime_day_counts, total_d1)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")


def _write_report(all_data, regime_day_counts, total_d1):
    """Generate the baseline profile markdown report."""
    report_path = OUTDIR / "reports" / "v10_baseline_profile.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# V10 Baseline Profile — Regime Decomposition")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("V10 baseline = `V8ApexStrategy(V8ApexConfig())` — long-only H4 VDO-momentum")
    lines.append("strategy with D1 EMA50/200 regime gating, trailing + fixed stops.")
    lines.append("")
    lines.append(f"Evaluation period: {START} → {END} (warmup={WARMUP_DAYS}d, ~7.14 years)")
    lines.append("")

    # Overall scores table
    lines.append("## Overall Performance")
    lines.append("")
    lines.append("| Scenario | Score | CAGR% | MDD% | Sharpe | Sortino | PF | Trades |")
    lines.append("|----------|-------|-------|------|--------|---------|-----|--------|")
    for sc in SCENARIO_ORDER:
        s = all_data[sc]["summary"]
        score = all_data[sc]["score"]
        sharpe = s.get("sharpe")
        sortino = s.get("sortino")
        pf = s.get("profit_factor", 0)
        sharpe_s = f"{sharpe:.4f}" if sharpe is not None else "N/A"
        sortino_s = f"{sortino:.4f}" if sortino is not None else "N/A"
        pf_s = f"{pf:.4f}" if isinstance(pf, (int, float)) else "inf"
        lines.append(
            f"| {sc} | {score:.2f} | {s.get('cagr_pct', 0):.2f} | "
            f"{s.get('max_drawdown_mid_pct', 0):.2f} | {sharpe_s} | {sortino_s} | "
            f"{pf_s} | {s.get('trades', 0)} |"
        )
    lines.append("")

    # Regime distribution
    lines.append("## Market Regime Distribution")
    lines.append("")
    lines.append("| Regime | D1 Days | % of Period | Definition |")
    lines.append("|--------|---------|-------------|------------|")
    defs = {
        "BULL": "close > EMA200 AND EMA50 > EMA200",
        "TOPPING": "|close - EMA50|/EMA50 < 1% AND ADX < 25",
        "BEAR": "close < EMA200 AND EMA50 < EMA200",
        "SHOCK": "|daily return| > 8%",
        "CHOP": "ATR% > 3.5% AND ADX < 20",
        "NEUTRAL": "everything else",
    }
    for r in REGIME_ORDER:
        days = regime_day_counts.get(r, 0)
        pct = days / total_d1 * 100.0 if total_d1 > 0 else 0
        lines.append(f"| {r} | {days} | {pct:.1f}% | {defs[r]} |")
    lines.append("")

    # Per-scenario regime tables
    for sc in SCENARIO_ORDER:
        rr = all_data[sc]["regime_returns"]
        ts = all_data[sc]["trade_stats"]
        score = all_data[sc]["score"]

        lines.append(f"## Regime Breakdown — {sc.upper()} (score={score:.2f})")
        lines.append("")
        lines.append("| Regime | Return% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees | Turnover |")
        lines.append("|--------|---------|------|--------|--------|-----|-----|---------|------|----------|")

        for regime_name in REGIME_ORDER:
            r = rr.get(regime_name, {})
            t = ts.get(regime_name, {})
            ret = r.get("total_return_pct", 0.0)
            mdd = r.get("max_dd_pct", 0.0)
            sharpe = r.get("sharpe")
            sharpe_s = f"{sharpe:.4f}" if sharpe is not None else "N/A"
            n_trades = t.get("trade_count", 0)
            wr = t.get("win_rate_pct", 0.0)
            pf = t.get("profit_factor", 0.0)
            pf_s = f"{pf:.2f}" if isinstance(pf, (int, float)) else "inf"
            avg_pnl = t.get("avg_trade_pnl", 0.0)
            fees = t.get("fees_paid", 0.0)
            turnover = t.get("turnover", 0.0)

            lines.append(
                f"| {regime_name} | {ret:.2f} | {mdd:.2f} | {sharpe_s} | "
                f"{n_trades} | {wr:.1f} | {pf_s} | {avg_pnl:.2f} | "
                f"{fees:.2f} | {turnover:.0f} |"
            )
        lines.append("")

    # Key findings
    lines.append("## Key Findings")
    lines.append("")

    # Auto-detect where money is made/lost (use base scenario)
    rr_base = all_data["base"]["regime_returns"]
    ts_base = all_data["base"]["trade_stats"]

    sorted_by_ret = sorted(
        [(r, rr_base.get(r, {}).get("total_return_pct", 0.0)) for r in REGIME_ORDER],
        key=lambda x: x[1], reverse=True,
    )

    lines.append("**Where V10 makes money** (base scenario):")
    lines.append("")
    for regime_name, ret in sorted_by_ret:
        if ret > 0:
            t = ts_base.get(regime_name, {})
            lines.append(f"- **{regime_name}**: +{ret:.1f}% return, "
                         f"{t.get('trade_count', 0)} trades, "
                         f"WR={t.get('win_rate_pct', 0):.0f}%")
    lines.append("")

    lines.append("**Where V10 loses money** (base scenario):")
    lines.append("")
    for regime_name, ret in sorted_by_ret:
        if ret < 0:
            t = ts_base.get(regime_name, {})
            lines.append(f"- **{regime_name}**: {ret:.1f}% return, "
                         f"{t.get('trade_count', 0)} trades, "
                         f"WR={t.get('win_rate_pct', 0):.0f}%")
    if not any(ret < 0 for _, ret in sorted_by_ret):
        lines.append("- No regimes with negative return.")
    lines.append("")

    # Cost sensitivity
    lines.append("**Cost sensitivity across regimes:**")
    lines.append("")
    lines.append("| Regime | Smart Ret% | Base Ret% | Harsh Ret% | Harsh-Smart delta |")
    lines.append("|--------|-----------|----------|-----------|-------------------|")
    for regime_name in REGIME_ORDER:
        smart_ret = all_data["smart"]["regime_returns"].get(regime_name, {}).get("total_return_pct", 0.0)
        base_ret = all_data["base"]["regime_returns"].get(regime_name, {}).get("total_return_pct", 0.0)
        harsh_ret = all_data["harsh"]["regime_returns"].get(regime_name, {}).get("total_return_pct", 0.0)
        delta = harsh_ret - smart_ret
        lines.append(f"| {regime_name} | {smart_ret:.2f} | {base_ret:.2f} | {harsh_ret:.2f} | {delta:+.2f} |")
    lines.append("")

    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    run()
