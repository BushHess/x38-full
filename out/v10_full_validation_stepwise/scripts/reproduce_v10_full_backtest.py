#!/usr/bin/env python3
"""Reproduce V10 baseline full backtest across 3 cost scenarios.

Outputs:
  - v10_full_backtest_summary.csv   (one row per scenario)
  - v10_full_backtest_detail.json   (full metrics per scenario)

Determinism: no randomness; two identical runs produce bit-identical results.
"""

import csv
import json
import sys
import time
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

# --- Constants (locked to V11 validation parity) ---
DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
OUTDIR = Path(__file__).resolve().parents[1]  # out_v10_full_validation_stepwise/

SCENARIO_ORDER = ["smart", "base", "harsh"]

CSV_COLUMNS = [
    "scenario",
    "score",
    "cagr_pct",
    "max_drawdown_mid_pct",
    "sharpe",
    "sortino",
    "calmar",
    "profit_factor",
    "trades",
    "wins",
    "losses",
    "win_rate_pct",
    "total_return_pct",
    "final_nav_mid",
    "avg_trade_pnl",
    "avg_days_held",
    "avg_exposure",
    "time_in_market_pct",
    "fees_total",
    "fee_drag_pct_per_year",
    "turnover_per_year",
    "fills",
    "years",
    "initial_cash",
    "report_start_nav",
]


def run():
    t0 = time.time()

    print("=" * 70)
    print("  V10 BASELINE — FULL BACKTEST REPRODUCTION")
    print("=" * 70)
    print(f"\n  Data:    {DATA_PATH}")
    print(f"  Period:  {START} → {END}  (warmup={WARMUP_DAYS}d)")
    print(f"  Cash:    ${INITIAL_CASH:,.0f}")
    print(f"  Strategy: V8ApexStrategy(V8ApexConfig()) — all defaults")
    print(f"  Output:  {OUTDIR}")

    # Load data once (shared across scenarios — DataFeed is read-only)
    print("\nLoading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    print(f"  H4 bars: {len(feed.h4_bars)}")
    print(f"  D1 bars: {len(feed.d1_bars)}")

    results = {}
    detail = {}

    print(f"\n{'Scenario':<10} {'Score':>10} {'CAGR%':>10} {'MDD%':>10} "
          f"{'Sharpe':>10} {'Sortino':>10} {'PF':>10} {'Trades':>8}")
    print("-" * 80)

    for scenario_name in SCENARIO_ORDER:
        cost = SCENARIOS[scenario_name]

        # Fresh strategy instance per run (stateful indicators)
        strategy = V8ApexStrategy(V8ApexConfig())
        engine = BacktestEngine(
            feed=feed,
            strategy=strategy,
            cost=cost,
            initial_cash=INITIAL_CASH,
            warmup_mode="no_trade",
        )
        result = engine.run()
        summary = result.summary
        score = compute_objective(summary)

        results[scenario_name] = {"score": score, **summary}
        detail[scenario_name] = {"score": score, **summary}

        sharpe = summary.get("sharpe")
        sortino = summary.get("sortino")
        pf = summary.get("profit_factor", 0)
        sharpe_s = f"{sharpe:10.4f}" if sharpe is not None else "       N/A"
        sortino_s = f"{sortino:10.4f}" if sortino is not None else "       N/A"
        pf_s = f"{pf:10.4f}" if isinstance(pf, (int, float)) else f"{'inf':>10}"

        print(f"{scenario_name:<10} {score:10.2f} "
              f"{summary.get('cagr_pct', 0):10.2f} "
              f"{summary.get('max_drawdown_mid_pct', 0):10.2f} "
              f"{sharpe_s} {sortino_s} {pf_s} "
              f"{summary.get('trades', 0):>8}")

    # --- Write CSV ---
    csv_path = OUTDIR / "v10_full_backtest_summary.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for scenario_name in SCENARIO_ORDER:
            row = {col: results[scenario_name].get(col, "") for col in CSV_COLUMNS}
            row["scenario"] = scenario_name
            writer.writerow(row)
    print(f"\nCSV saved: {csv_path}")

    # --- Write JSON detail ---
    json_path = OUTDIR / "v10_full_backtest_detail.json"
    with open(json_path, "w") as f:
        json.dump(detail, f, indent=2, default=str)
    print(f"JSON saved: {json_path}")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")

    return results


if __name__ == "__main__":
    run()
