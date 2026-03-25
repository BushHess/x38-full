#!/usr/bin/env python3
"""V10 WFO round-by-round: per-window metrics across all 3 cost scenarios.

Uses identical WFO windows as V11 validation (24m train / 6m test / 6m slide).
Only the OOS (test) windows are backtested — no optimization, fixed V10 params.

Per-round outputs:
  harsh_score, smart_score, base_score,
  BULL_return, TOPPING_return, MDD, trade_count, turnover, fees_paid,
  plus full per-scenario metrics.
"""

import csv
import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, AnalyticalRegime, compute_regime_returns
from v10.research.wfo import generate_windows
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
OUTDIR = Path(__file__).resolve().parents[1]

SCENARIO_ORDER = ["smart", "base", "harsh"]
REGIME_ORDER = ["BULL", "TOPPING", "BEAR", "SHOCK", "CHOP", "NEUTRAL"]

CSV_COLUMNS = [
    "window_id", "test_start", "test_end",
    # harsh metrics (primary)
    "harsh_score", "harsh_cagr_pct", "harsh_mdd_pct", "harsh_sharpe",
    "harsh_trades", "harsh_turnover", "harsh_fees",
    "harsh_return_pct", "harsh_profit_factor", "harsh_win_rate_pct",
    # base & smart scores
    "base_score", "smart_score",
    # regime returns (harsh scenario — worst-case view)
    "BULL_return_pct", "TOPPING_return_pct", "BEAR_return_pct",
    "SHOCK_return_pct", "CHOP_return_pct", "NEUTRAL_return_pct",
]


def backtest_window_all_scenarios(window):
    """Run V10 on one OOS window across all 3 cost scenarios + regime decomp."""
    row = {
        "window_id": window.window_id,
        "test_start": window.test_start,
        "test_end": window.test_end,
    }
    detail = {}

    for scenario_name in SCENARIO_ORDER:
        cost = SCENARIOS[scenario_name]
        strategy = V8ApexStrategy(V8ApexConfig())
        feed = DataFeed(DATA_PATH, start=window.test_start, end=window.test_end,
                        warmup_days=WARMUP_DAYS)
        engine = BacktestEngine(
            feed=feed, strategy=strategy, cost=cost,
            initial_cash=INITIAL_CASH, warmup_mode="no_trade",
        )
        result = engine.run()
        s = result.summary
        score = compute_objective(s)

        detail[scenario_name] = {
            "score": score,
            "summary": s,
        }

        prefix = scenario_name
        row[f"{prefix}_score"] = round(score, 4)
        row[f"{prefix}_cagr_pct"] = s.get("cagr_pct", 0.0)
        row[f"{prefix}_mdd_pct"] = s.get("max_drawdown_mid_pct", 0.0)
        row[f"{prefix}_sharpe"] = s.get("sharpe")
        row[f"{prefix}_trades"] = s.get("trades", 0)
        row[f"{prefix}_turnover"] = s.get("turnover_notional", 0.0)
        row[f"{prefix}_fees"] = s.get("fees_total", 0.0)
        row[f"{prefix}_return_pct"] = s.get("total_return_pct", 0.0)
        row[f"{prefix}_profit_factor"] = s.get("profit_factor", 0.0)
        row[f"{prefix}_win_rate_pct"] = s.get("win_rate_pct", 0.0)

        # Regime decomposition for harsh scenario
        if scenario_name == "harsh":
            regimes = classify_d1_regimes(feed.d1_bars)
            regime_ret = compute_regime_returns(
                result.equity, feed.d1_bars, regimes, feed.report_start_ms,
            )
            for regime_name in REGIME_ORDER:
                rr = regime_ret.get(regime_name, {})
                row[f"{regime_name}_return_pct"] = rr.get("total_return_pct", 0.0)
            detail["regime_returns_harsh"] = regime_ret

    return row, detail


def run():
    t0 = time.time()
    print("=" * 70)
    print("  V10 WFO ROUND-BY-ROUND")
    print("=" * 70)

    # Generate windows (identical to V11)
    windows = generate_windows(START, END, train_months=24, test_months=6, slide_months=6)
    print(f"\n  {len(windows)} OOS windows")
    for w in windows:
        print(f"    Window {w.window_id}: {w.test_start} → {w.test_end}")

    # Run all windows
    rows = []
    all_detail = {}

    print(f"\n{'Win':>4} {'Period':<25} {'H-Score':>8} {'B-Score':>8} {'S-Score':>8} "
          f"{'H-MDD%':>7} {'Trades':>6} {'BULL%':>8} {'TOP%':>8} {'Fees':>9}")
    print("-" * 105)

    for w in windows:
        row, detail = backtest_window_all_scenarios(w)
        rows.append(row)
        all_detail[w.window_id] = detail

        print(f"{w.window_id:>4} {w.test_start}→{w.test_end:<1} "
              f"{row['harsh_score']:>8.2f} {row['base_score']:>8.2f} {row['smart_score']:>8.2f} "
              f"{row.get('harsh_mdd_pct', 0):>7.1f} {row.get('harsh_trades', 0):>6} "
              f"{row.get('BULL_return_pct', 0):>+8.1f} {row.get('TOPPING_return_pct', 0):>+8.1f} "
              f"{row.get('harsh_fees', 0):>9.1f}")

    # --- Stability summary ---
    harsh_scores = [r["harsh_score"] for r in rows]
    base_scores = [r["base_score"] for r in rows]
    smart_scores = [r["smart_score"] for r in rows]
    harsh_mdds = [r.get("harsh_mdd_pct", 0) for r in rows]
    harsh_trades = [r.get("harsh_trades", 0) for r in rows]
    bull_rets = [r.get("BULL_return_pct", 0) for r in rows]
    top_rets = [r.get("TOPPING_return_pct", 0) for r in rows]

    print("\n" + "=" * 70)
    print("  STABILITY SUMMARY")
    print("=" * 70)

    def _stats(vals, label):
        med = statistics.median(vals)
        mn = min(vals)
        mx = max(vals)
        avg = statistics.mean(vals)
        std = statistics.stdev(vals) if len(vals) > 1 else 0.0
        print(f"  {label:<22} median={med:>8.2f}  worst={mn:>8.2f}  "
              f"best={mx:>8.2f}  mean={avg:>8.2f}  std={std:>7.2f}")

    _stats(harsh_scores, "harsh_score")
    _stats(base_scores, "base_score")
    _stats(smart_scores, "smart_score")
    _stats(harsh_mdds, "harsh_MDD%")
    _stats(harsh_trades, "harsh_trades")
    _stats(bull_rets, "BULL_return%")
    _stats(top_rets, "TOPPING_return%")

    # Positive-score rounds
    n_positive = sum(1 for s in harsh_scores if s > 0)
    print(f"\n  Positive harsh_score: {n_positive}/{len(rows)} "
          f"({n_positive/len(rows)*100:.0f}%)")

    # --- Write CSV ---
    csv_path = OUTDIR / "v10_per_round_metrics.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"\n  CSV saved: {csv_path}")

    # --- Write JSON ---
    json_path = OUTDIR / "v10_per_round_detail.json"
    with open(json_path, "w") as f:
        json.dump(all_detail, f, indent=2, default=str)

    # --- Write report ---
    _write_report(rows, harsh_scores, base_scores, smart_scores, harsh_mdds,
                  harsh_trades, bull_rets, top_rets, windows)

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")


def _write_report(rows, harsh_scores, base_scores, smart_scores, harsh_mdds,
                  harsh_trades, bull_rets, top_rets, windows):
    report_path = OUTDIR / "reports" / "v10_wfo_round_by_round.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# V10 WFO Round-by-Round Analysis")
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append("- Strategy: `V8ApexStrategy(V8ApexConfig())` — fixed params, no optimization")
    lines.append("- WFO: 24m train / 6m test / 6m slide (train window unused — V10 has no per-window tuning)")
    lines.append(f"- Windows: {len(windows)} OOS periods (2021-01 → 2026-01)")
    lines.append("- Cost scenarios: smart (13 bps), base (31 bps), harsh (50 bps RT)")
    lines.append("- Regime classifier: `v10/research/regime.py::classify_d1_regimes()`")
    lines.append("")

    # Main table
    lines.append("## Per-Round Metrics")
    lines.append("")
    lines.append("| Win | Period | Harsh Score | Base Score | Smart Score | "
                 "Harsh MDD% | Trades | BULL Ret% | TOP Ret% | Fees |")
    lines.append("|-----|--------|-------------|------------|-------------|"
                 "------------|--------|-----------|----------|------|")
    for r in rows:
        lines.append(
            f"| {r['window_id']} | {r['test_start']}→{r['test_end']} | "
            f"{r['harsh_score']:.2f} | {r['base_score']:.2f} | {r['smart_score']:.2f} | "
            f"{r.get('harsh_mdd_pct', 0):.1f} | {r.get('harsh_trades', 0)} | "
            f"{r.get('BULL_return_pct', 0):+.1f} | {r.get('TOPPING_return_pct', 0):+.1f} | "
            f"{r.get('harsh_fees', 0):.0f} |"
        )
    lines.append("")

    # Full regime breakdown table
    lines.append("## Per-Round Regime Returns (harsh scenario)")
    lines.append("")
    lines.append("| Win | BULL% | TOPPING% | BEAR% | SHOCK% | CHOP% | NEUTRAL% |")
    lines.append("|-----|-------|----------|-------|--------|-------|----------|")
    for r in rows:
        lines.append(
            f"| {r['window_id']} | "
            f"{r.get('BULL_return_pct', 0):+.1f} | "
            f"{r.get('TOPPING_return_pct', 0):+.1f} | "
            f"{r.get('BEAR_return_pct', 0):+.1f} | "
            f"{r.get('SHOCK_return_pct', 0):+.1f} | "
            f"{r.get('CHOP_return_pct', 0):+.1f} | "
            f"{r.get('NEUTRAL_return_pct', 0):+.1f} |"
        )
    lines.append("")

    # Stability summary
    def _fmt(vals):
        med = statistics.median(vals)
        worst = min(vals)
        best = max(vals)
        avg = statistics.mean(vals)
        std = statistics.stdev(vals) if len(vals) > 1 else 0.0
        return med, worst, best, avg, std

    lines.append("## Stability Summary")
    lines.append("")
    lines.append("| Metric | Median | Worst | Best | Mean | Std |")
    lines.append("|--------|--------|-------|------|------|-----|")

    for label, vals in [
        ("Harsh Score", harsh_scores),
        ("Base Score", base_scores),
        ("Smart Score", smart_scores),
        ("Harsh MDD%", harsh_mdds),
        ("Harsh Trades", harsh_trades),
        ("BULL Return%", bull_rets),
        ("TOPPING Return%", top_rets),
    ]:
        med, worst, best, avg, std = _fmt(vals)
        lines.append(f"| {label} | {med:.2f} | {worst:.2f} | {best:.2f} | "
                     f"{avg:.2f} | {std:.2f} |")
    lines.append("")

    # Observations
    n_positive = sum(1 for s in harsh_scores if s > 0)
    worst_idx = harsh_scores.index(min(harsh_scores))
    best_idx = harsh_scores.index(max(harsh_scores))

    lines.append("## Key Observations")
    lines.append("")
    lines.append(f"- **Positive harsh_score:** {n_positive}/{len(rows)} rounds "
                 f"({n_positive/len(rows)*100:.0f}%)")
    lines.append(f"- **Best round:** Window {best_idx} "
                 f"({rows[best_idx]['test_start']}→{rows[best_idx]['test_end']}) "
                 f"— harsh_score={harsh_scores[best_idx]:.2f}")
    lines.append(f"- **Worst round:** Window {worst_idx} "
                 f"({rows[worst_idx]['test_start']}→{rows[worst_idx]['test_end']}) "
                 f"— harsh_score={harsh_scores[worst_idx]:.2f}")

    # TOPPING damage summary
    top_neg = [t for t in top_rets if t < 0]
    if top_neg:
        lines.append(f"- **TOPPING damage:** {len(top_neg)}/{len(rows)} rounds with negative "
                     f"TOPPING return (worst={min(top_rets):+.1f}%)")
    else:
        lines.append("- **TOPPING damage:** No rounds with negative TOPPING return")

    # MDD analysis
    harsh_30 = sum(1 for m in harsh_mdds if m > 30)
    lines.append(f"- **MDD > 30%:** {harsh_30}/{len(rows)} rounds under harsh costs")
    lines.append("")

    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Report saved: {report_path}")


if __name__ == "__main__":
    run()
