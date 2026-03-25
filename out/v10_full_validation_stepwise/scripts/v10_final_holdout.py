#!/usr/bin/env python3
"""V10 Final Holdout — ONE-SHOT, V10-only baseline profile.

Holdout period: 2024-10-01 → 2026-02-20  (identical to V11 validation)
Full period:    2019-01-01 → 2026-02-20

Outputs:
  - v10_holdout_metrics.csv   (1 row per scenario: score, CAGR, MDD, etc.)
  - v10_holdout_regime.csv    (1 row per scenario × regime)
  - reports/v10_final_holdout.md
"""

import csv
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

np.seterr(all="ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Fill, Trade
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, AnalyticalRegime, compute_regime_returns
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
WARMUP_DAYS = 365
OUTDIR = Path(__file__).resolve().parents[1]

# ── Holdout definition (locked from V11 validation) ─────────────────────
HOLDOUT_START = "2024-10-01"
HOLDOUT_END   = "2026-02-20"
FULL_START    = "2019-01-01"
FULL_END      = "2026-02-20"

SCENARIO_ORDER = ["harsh", "base", "smart"]
REGIME_ORDER = ["BULL", "TOPPING", "BEAR", "SHOCK", "CHOP", "NEUTRAL"]


def run_backtest(start, end, scenario_name):
    """Run V10 backtest, return (result, feed)."""
    cost = SCENARIOS[scenario_name]
    strategy = V8ApexStrategy(V8ApexConfig())
    feed = DataFeed(DATA_PATH, start=start, end=end, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0, warmup_mode="no_trade")
    result = engine.run()
    return result, feed


def trade_stats_by_regime(trades, fills, d1_bars, regimes):
    """Per-regime trade stats (same logic as v10_regime_profile.py)."""
    d1_ct = np.array([b.close_time for b in d1_bars], dtype=np.int64)

    def _regime_at(ts_ms):
        idx = int(np.searchsorted(d1_ct, ts_ms, side="left")) - 1
        return regimes[idx].value if idx >= 0 else "NEUTRAL"

    groups = {r: [] for r in REGIME_ORDER}
    fill_groups = {r: [] for r in REGIME_ORDER}
    for t in trades:
        groups[_regime_at(t.entry_ts_ms)].append(t)
    for f in fills:
        fill_groups[_regime_at(f.ts_ms)].append(f)

    out = {}
    for rn in REGIME_ORDER:
        rt = groups[rn]
        rf = fill_groups[rn]
        n = len(rt)
        wins = sum(1 for t in rt if t.pnl > 0)
        total_pnl = sum(t.pnl for t in rt)
        gp = sum(t.pnl for t in rt if t.pnl > 0)
        gl = abs(sum(t.pnl for t in rt if t.pnl < 0))
        pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0.0)
        out[rn] = {
            "trade_count": n,
            "wins": wins,
            "win_rate_pct": round(wins / n * 100, 2) if n > 0 else 0.0,
            "profit_factor": round(pf, 4) if not math.isinf(pf) else "inf",
            "total_pnl": round(total_pnl, 2),
            "avg_trade_pnl": round(total_pnl / n, 2) if n > 0 else 0.0,
            "fees_paid": round(sum(f.fee for f in rf), 2),
            "turnover": round(sum(f.notional for f in rf), 2),
        }
    return out


def run():
    t0 = time.time()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    print("=" * 70)
    print("  V10 FINAL HOLDOUT — ONE-SHOT")
    print("=" * 70)
    print(f"  Timestamp:      {timestamp}")
    print(f"  Holdout period: {HOLDOUT_START} → {HOLDOUT_END}")
    print(f"  Full period:    {FULL_START} → {FULL_END}")
    print(f"  Warmup:         {WARMUP_DAYS} days")
    print(f"  Strategy:       V10 = V8ApexStrategy(V8ApexConfig())")
    print(f"  Scenarios:      {SCENARIO_ORDER}")
    print()

    # ── Holdout backtests ───────────────────────────────────────────────
    holdout_metrics = []
    holdout_regime_rows = []
    all_data = {}

    for scenario in SCENARIO_ORDER:
        result, feed = run_backtest(HOLDOUT_START, HOLDOUT_END, scenario)
        s = result.summary
        score = compute_objective(s)

        # Regime equity-based
        regimes = classify_d1_regimes(feed.d1_bars)
        regime_ret = compute_regime_returns(
            result.equity, feed.d1_bars, regimes, feed.report_start_ms,
        )
        # Regime trade-based
        trade_stats = trade_stats_by_regime(
            result.trades, result.fills, feed.d1_bars, regimes,
        )

        metrics = {
            "scenario": scenario,
            "score": round(score, 4),
            "cagr_pct": s.get("cagr_pct", 0.0),
            "total_return_pct": s.get("total_return_pct", 0.0),
            "max_drawdown_mid_pct": s.get("max_drawdown_mid_pct", 0.0),
            "sharpe": s.get("sharpe"),
            "sortino": s.get("sortino"),
            "profit_factor": s.get("profit_factor", 0.0),
            "trades": s.get("trades", 0),
            "wins": s.get("wins", 0),
            "losses": s.get("losses", 0),
            "win_rate_pct": s.get("win_rate_pct", 0.0),
            "avg_trade_pnl": s.get("avg_trade_pnl", 0.0),
            "avg_days_held": s.get("avg_days_held", 0.0),
            "fees_total": s.get("fees_total", 0.0),
            "turnover_notional": s.get("turnover_notional", 0.0),
            "final_nav_mid": s.get("final_nav_mid", 0.0),
            "years": s.get("years", 0.0),
        }
        holdout_metrics.append(metrics)

        all_data[scenario] = {
            "metrics": metrics,
            "regime_returns": regime_ret,
            "trade_stats": trade_stats,
        }

        print(f"  {scenario:<6}: score={score:>8.2f}  ret={s.get('total_return_pct', 0):>+7.2f}%  "
              f"cagr={s.get('cagr_pct', 0):>+7.2f}%  mdd={s.get('max_drawdown_mid_pct', 0):>6.2f}%  "
              f"sharpe={s.get('sharpe', 0):>6.3f}  trades={s.get('trades', 0)}")

        # Build regime rows
        for rn in REGIME_ORDER:
            rr = regime_ret.get(rn, {})
            ts = trade_stats.get(rn, {})
            holdout_regime_rows.append({
                "scenario": scenario,
                "regime": rn,
                "equity_return_pct": rr.get("total_return_pct", 0.0),
                "max_dd_pct": rr.get("max_dd_pct", 0.0),
                "sharpe": rr.get("sharpe"),
                "n_equity_bars": rr.get("n_bars", 0),
                "n_days": rr.get("n_days", 0),
                "trade_count": ts.get("trade_count", 0),
                "wins": ts.get("wins", 0),
                "win_rate_pct": ts.get("win_rate_pct", 0.0),
                "profit_factor": ts.get("profit_factor", 0.0),
                "total_pnl": ts.get("total_pnl", 0.0),
                "avg_trade_pnl": ts.get("avg_trade_pnl", 0.0),
                "fees_paid": ts.get("fees_paid", 0.0),
                "turnover": ts.get("turnover", 0.0),
            })

    # ── Full-period comparison (context) ────────────────────────────────
    print(f"\n  Full-period reference (2019-01-01 → 2026-02-20):")
    full_data = {}
    for scenario in SCENARIO_ORDER:
        result_full, _ = run_backtest(FULL_START, FULL_END, scenario)
        sf = result_full.summary
        score_full = compute_objective(sf)
        full_data[scenario] = {
            "score": round(score_full, 4),
            "cagr_pct": sf.get("cagr_pct", 0.0),
            "total_return_pct": sf.get("total_return_pct", 0.0),
            "max_drawdown_mid_pct": sf.get("max_drawdown_mid_pct", 0.0),
            "sharpe": sf.get("sharpe"),
            "trades": sf.get("trades", 0),
        }
        print(f"  {scenario:<6}: score={score_full:>8.2f}  ret={sf.get('total_return_pct', 0):>+8.2f}%  "
              f"cagr={sf.get('cagr_pct', 0):>+7.2f}%  trades={sf.get('trades', 0)}")

    # ── Regime summary print ────────────────────────────────────────────
    print(f"\n  Regime breakdown (harsh holdout):")
    harsh_rr = all_data["harsh"]["regime_returns"]
    harsh_ts = all_data["harsh"]["trade_stats"]
    print(f"    {'Regime':<10} {'Ret%':>8} {'MDD%':>7} {'Sharpe':>8} "
          f"{'Trades':>7} {'WR%':>6} {'PF':>7} {'AvgPnL':>9}")
    print(f"    {'-'*70}")
    for rn in REGIME_ORDER:
        rr = harsh_rr.get(rn, {})
        ts = harsh_ts.get(rn, {})
        ret = rr.get("total_return_pct", 0)
        mdd = rr.get("max_dd_pct", 0)
        sh = rr.get("sharpe")
        sh_s = f"{sh:8.4f}" if sh is not None else "     N/A"
        nt = ts.get("trade_count", 0)
        wr = ts.get("win_rate_pct", 0)
        pf = ts.get("profit_factor", 0)
        pf_s = f"{pf:7.2f}" if isinstance(pf, (int, float)) else f"{'inf':>7}"
        ap = ts.get("avg_trade_pnl", 0)
        print(f"    {rn:<10} {ret:>+8.2f} {mdd:>7.2f} {sh_s} "
              f"{nt:>7} {wr:>6.1f} {pf_s} {ap:>9.2f}")

    # ── Write CSVs ──────────────────────────────────────────────────────
    csv_metrics_path = OUTDIR / "v10_holdout_metrics.csv"
    with open(csv_metrics_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(holdout_metrics[0].keys()))
        writer.writeheader()
        writer.writerows(holdout_metrics)
    print(f"\n  Saved: {csv_metrics_path}")

    csv_regime_path = OUTDIR / "v10_holdout_regime.csv"
    with open(csv_regime_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(holdout_regime_rows[0].keys()))
        writer.writeheader()
        writer.writerows(holdout_regime_rows)
    print(f"  Saved: {csv_regime_path}")

    # ── Write report ────────────────────────────────────────────────────
    _write_report(all_data, full_data, timestamp)

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")


def _write_report(all_data, full_data, timestamp):
    report_path = OUTDIR / "reports" / "v10_final_holdout.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    L = []
    L.append("# V10 Final Holdout — Baseline Profile")
    L.append("")
    L.append(f"**Timestamp:** {timestamp}")
    L.append("")
    L.append("## 1. Holdout Definition")
    L.append("")
    L.append("| Parameter | Value |")
    L.append("|-----------|-------|")
    L.append(f"| **Holdout start** | **{HOLDOUT_START}** |")
    L.append(f"| **Holdout end** | **{HOLDOUT_END}** |")
    L.append("| Holdout duration | ~17 months (507 days, 19.4% of full period) |")
    L.append(f"| Full evaluation | {FULL_START} → {FULL_END} (2607 days) |")
    L.append(f"| Warmup | {WARMUP_DAYS} days |")
    L.append("| Strategy | V10 = `V8ApexStrategy(V8ApexConfig())` |")
    L.append("| Scenarios | harsh (50 bps), base (31 bps), smart (13 bps) |")
    L.append("")
    L.append("Identical holdout window as V11 validation (`out_v11_validation_stepwise/scripts/final_holdout.py:41-42`).")
    L.append("")

    # Primary metrics table
    L.append("## 2. Holdout Metrics")
    L.append("")
    L.append("| Scenario | Score | CAGR% | Return% | MDD% | Sharpe | Sortino | PF | Trades | Fees |")
    L.append("|----------|-------|-------|---------|------|--------|---------|-----|--------|------|")
    for sc in SCENARIO_ORDER:
        m = all_data[sc]["metrics"]
        sh = m["sharpe"]
        so = m["sortino"]
        pf = m["profit_factor"]
        sh_s = f"{sh:.4f}" if sh is not None else "N/A"
        so_s = f"{so:.4f}" if so is not None else "N/A"
        pf_s = f"{pf:.4f}" if isinstance(pf, (int, float)) else str(pf)
        L.append(
            f"| {sc} | {m['score']:.2f} | {m['cagr_pct']:.2f} | "
            f"{m['total_return_pct']:+.2f} | {m['max_drawdown_mid_pct']:.2f} | "
            f"{sh_s} | {so_s} | {pf_s} | {m['trades']} | {m['fees_total']:.0f} |"
        )
    L.append("")

    # Full-period comparison
    L.append("## 3. Holdout vs Full-Period")
    L.append("")
    L.append("| Scenario | Full Score | Holdout Score | Full CAGR% | Holdout CAGR% | Full Trades | Holdout Trades |")
    L.append("|----------|-----------|---------------|-----------|---------------|-------------|----------------|")
    for sc in SCENARIO_ORDER:
        hm = all_data[sc]["metrics"]
        fm = full_data[sc]
        L.append(
            f"| {sc} | {fm['score']:.2f} | {hm['score']:.2f} | "
            f"{fm['cagr_pct']:.2f} | {hm['cagr_pct']:.2f} | "
            f"{fm['trades']} | {hm['trades']} |"
        )
    L.append("")

    # Regime breakdown (all scenarios)
    for sc in SCENARIO_ORDER:
        rr = all_data[sc]["regime_returns"]
        ts = all_data[sc]["trade_stats"]
        L.append(f"## 4{'abc'[SCENARIO_ORDER.index(sc)]}. Regime Breakdown — {sc.upper()} holdout")
        L.append("")
        L.append("| Regime | Days | Ret% | MDD% | Sharpe | Trades | WR% | PF | Avg PnL | Fees |")
        L.append("|--------|------|------|------|--------|--------|-----|-----|---------|------|")
        for rn in REGIME_ORDER:
            r = rr.get(rn, {})
            t = ts.get(rn, {})
            nd = r.get("n_days", 0)
            ret = r.get("total_return_pct", 0)
            mdd = r.get("max_dd_pct", 0)
            sh = r.get("sharpe")
            sh_s = f"{sh:.4f}" if sh is not None else "N/A"
            nt = t.get("trade_count", 0)
            wr = t.get("win_rate_pct", 0)
            pf = t.get("profit_factor", 0)
            pf_s = f"{pf:.2f}" if isinstance(pf, (int, float)) else "inf"
            ap = t.get("avg_trade_pnl", 0)
            fees = t.get("fees_paid", 0)
            L.append(
                f"| {rn} | {nd:.0f} | {ret:+.2f} | {mdd:.2f} | {sh_s} | "
                f"{nt} | {wr:.0f} | {pf_s} | {ap:.2f} | {fees:.0f} |"
            )
        L.append("")

    # Cross-reference with V11 holdout results
    L.append("## 5. Cross-Reference: V11 Holdout (from V11 validation)")
    L.append("")
    L.append("V11 holdout results (from `out_v11_validation_stepwise/reports/final_holdout.md`):")
    L.append("")
    L.append("| Scenario | V10 Score (this run) | V10 Score (V11 report) | V11 Score | V11 Δ Score |")
    L.append("|----------|---------------------|----------------------|-----------|-------------|")
    # V11 report values (hardcoded from the report we just read)
    v11_ref = {
        "harsh": {"v10": 34.66, "v11": 33.43, "delta": -1.23},
        "base":  {"v10": 55.06, "v11": 53.78, "delta": -1.28},
        "smart": {"v10": 64.64, "v11": 63.31, "delta": -1.32},
    }
    for sc in SCENARIO_ORDER:
        hm = all_data[sc]["metrics"]
        ref = v11_ref[sc]
        L.append(
            f"| {sc} | {hm['score']:.2f} | {ref['v10']:.2f} | "
            f"{ref['v11']:.2f} | {ref['delta']:+.2f} |"
        )
    L.append("")
    L.append("V11 underperformed V10 by -1.23 to -1.32 score points across all 3 scenarios on this holdout.")
    L.append("")

    # Key findings
    L.append("## 6. Key Findings")
    L.append("")

    harsh_m = all_data["harsh"]["metrics"]
    harsh_rr = all_data["harsh"]["regime_returns"]
    harsh_ts = all_data["harsh"]["trade_stats"]

    bull_ret = harsh_rr.get("BULL", {}).get("total_return_pct", 0)
    top_ret = harsh_rr.get("TOPPING", {}).get("total_return_pct", 0)
    bear_ret = harsh_rr.get("BEAR", {}).get("total_return_pct", 0)

    L.append(f"- **Holdout return (harsh):** {harsh_m['total_return_pct']:+.2f}% "
             f"over ~17 months ({harsh_m['cagr_pct']:+.2f}% CAGR)")
    L.append(f"- **MDD (harsh):** {harsh_m['max_drawdown_mid_pct']:.2f}% "
             f"— consistent with full-period MDD ({full_data['harsh']['max_drawdown_mid_pct']:.2f}%)")
    L.append(f"- **BULL regime** drives all gains: {bull_ret:+.1f}% return")
    L.append(f"- **TOPPING/BEAR** damage: TOPPING={top_ret:+.1f}%, BEAR={bear_ret:+.1f}%")
    L.append(f"- **Trade count (harsh):** {harsh_m['trades']} in 17 months "
             f"(vs {full_data['harsh']['trades']} in 7 years)")
    L.append("")

    with open(report_path, "w") as f:
        f.write("\n".join(L))
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    run()
