#!/usr/bin/env python3
"""Sensitivity Grid: 27-point grid for V11 cycle_late params vs V10 baseline.

Grid axes:
  - cycle_late_aggression:    [0.85, 0.90, 0.95]
  - cycle_late_trail_mult:    [2.7, 3.0, 3.3]
  - cycle_late_max_exposure:  [0.75, 0.90, 0.95]

For each of 27 grid points, run full backtest under harsh/base/smart scenarios.
Compare each point to V10 baseline.

Output:
  - sensitivity_grid.csv       (27 rows × deltas)
  - sensitivity_grid_full.csv  (27 × 3 scenarios detail)
  - sign_test_grid.json        (aggregate stats)
"""

import csv
import json
import itertools
import sys
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
OUTDIR = Path("out_v11_validation_stepwise")

# Grid axes
AGGRESSION_VALS = [0.85, 0.90, 0.95]
TRAIL_VALS = [2.7, 3.0, 3.3]
CAP_VALS = [0.75, 0.90, 0.95]

SCENARIO_NAMES = ["harsh", "base", "smart"]


def run_backtest(strategy, scenario_name):
    """Run full-period backtest, return summary dict."""
    cost = SCENARIOS[scenario_name]
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result.summary


def make_v11(aggr, trail, cap):
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = aggr
    cfg.cycle_late_trail_mult = trail
    cfg.cycle_late_max_exposure = cap
    return V11HybridStrategy(cfg)


def extract(summary):
    score = compute_objective(summary)
    return {
        "score": score,
        "cagr_pct": summary.get("cagr_pct", 0.0),
        "mdd_pct": summary.get("max_drawdown_mid_pct", 0.0),
        "sharpe": summary.get("sharpe") or 0.0,
        "trades": summary.get("trades", 0),
        "turnover_per_year": summary.get("turnover_per_year", 0.0),
        "total_return_pct": summary.get("total_return_pct", 0.0),
    }


def main():
    print("=" * 70)
    print("  SENSITIVITY GRID: V11 cycle_late params (27 points × 3 scenarios)")
    print("=" * 70)
    print(f"  Aggression: {AGGRESSION_VALS}")
    print(f"  Trail mult: {TRAIL_VALS}")
    print(f"  Max exposure: {CAP_VALS}")
    print(f"  Total: {len(AGGRESSION_VALS) * len(TRAIL_VALS) * len(CAP_VALS)} grid points")
    print()

    # ── Run V10 baseline (once per scenario) ─────────────────────────────
    print("  Running V10 baseline...")
    baseline = {}
    for sc in SCENARIO_NAMES:
        v10 = V8ApexStrategy(V8ApexConfig())
        s = run_backtest(v10, sc)
        baseline[sc] = extract(s)
        print(f"    {sc}: score={baseline[sc]['score']:.2f}  "
              f"cagr={baseline[sc]['cagr_pct']:.2f}%  "
              f"mdd={baseline[sc]['mdd_pct']:.2f}%")
    print()

    # ── Run grid ─────────────────────────────────────────────────────────
    grid_points = list(itertools.product(AGGRESSION_VALS, TRAIL_VALS, CAP_VALS))
    csv_rows = []
    full_rows = []

    for i, (aggr, trail, cap) in enumerate(grid_points):
        label = f"({aggr:.2f}, {trail:.1f}, {cap:.2f})"
        print(f"  [{i+1:2d}/27] aggr={aggr:.2f} trail={trail:.1f} cap={cap:.2f}", end="")

        row = {
            "grid_id": i,
            "aggression": aggr,
            "trail_mult": trail,
            "max_exposure": cap,
        }

        for sc in SCENARIO_NAMES:
            v11 = make_v11(aggr, trail, cap)
            s = run_backtest(v11, sc)
            m = extract(s)

            b = baseline[sc]
            d_score = m["score"] - b["score"]
            d_cagr = m["cagr_pct"] - b["cagr_pct"]
            d_mdd = m["mdd_pct"] - b["mdd_pct"]
            d_turnover = m["turnover_per_year"] - b["turnover_per_year"]
            d_sharpe = m["sharpe"] - b["sharpe"]
            d_return = m["total_return_pct"] - b["total_return_pct"]

            row[f"score_{sc}"] = round(m["score"], 4)
            row[f"delta_score_{sc}"] = round(d_score, 4)
            row[f"delta_cagr_{sc}"] = round(d_cagr, 4)
            row[f"delta_mdd_{sc}"] = round(d_mdd, 4)
            row[f"delta_turnover_{sc}"] = round(d_turnover, 4)
            row[f"delta_sharpe_{sc}"] = round(d_sharpe, 4)
            row[f"delta_return_{sc}"] = round(d_return, 4)

            # Full detail row
            full_rows.append({
                "grid_id": i,
                "aggression": aggr,
                "trail_mult": trail,
                "max_exposure": cap,
                "scenario": sc,
                "v11_score": round(m["score"], 4),
                "v10_score": round(b["score"], 4),
                "delta_score": round(d_score, 4),
                "v11_cagr": round(m["cagr_pct"], 4),
                "v10_cagr": round(b["cagr_pct"], 4),
                "delta_cagr": round(d_cagr, 4),
                "v11_mdd": round(m["mdd_pct"], 4),
                "v10_mdd": round(b["mdd_pct"], 4),
                "delta_mdd": round(d_mdd, 4),
                "v11_sharpe": round(m["sharpe"], 4),
                "v10_sharpe": round(b["sharpe"], 4),
                "delta_sharpe": round(d_sharpe, 4),
                "v11_turnover": round(m["turnover_per_year"], 4),
                "delta_turnover": round(d_turnover, 4),
                "v11_trades": m["trades"],
                "v11_return": round(m["total_return_pct"], 4),
                "delta_return": round(d_return, 4),
            })

        csv_rows.append(row)

        # Print harsh delta
        dh = row["delta_score_harsh"]
        sign = "+" if dh > 0.01 else ("-" if dh < -0.01 else "=")
        print(f"  → Δharsh={dh:+.2f} [{sign}]  "
              f"Δbase={row['delta_score_base']:+.2f}  "
              f"Δsmart={row['delta_score_smart']:+.2f}")

    # ── Write CSVs ───────────────────────────────────────────────────────
    # Main grid CSV (27 rows)
    csv_path = OUTDIR / "sensitivity_grid.csv"
    fieldnames = ["grid_id", "aggression", "trail_mult", "max_exposure"]
    for sc in SCENARIO_NAMES:
        fieldnames += [f"score_{sc}", f"delta_score_{sc}", f"delta_cagr_{sc}",
                       f"delta_mdd_{sc}", f"delta_turnover_{sc}",
                       f"delta_sharpe_{sc}", f"delta_return_{sc}"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\n  Saved: {csv_path}")

    # Full detail CSV
    full_path = OUTDIR / "sensitivity_grid_full.csv"
    full_fields = list(full_rows[0].keys())
    with open(full_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=full_fields)
        writer.writeheader()
        writer.writerows(full_rows)
    print(f"  Saved: {full_path}")

    # ── Aggregate statistics ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SENSITIVITY GRID SUMMARY")
    print("=" * 70)

    summary = {}
    for sc in SCENARIO_NAMES:
        deltas = [r[f"delta_score_{sc}"] for r in csv_rows]
        n_beat = sum(1 for d in deltas if d > 0.01)
        n_tie = sum(1 for d in deltas if abs(d) <= 0.01)
        n_lose = sum(1 for d in deltas if d < -0.01)
        best = max(deltas)
        worst = min(deltas)
        mean_d = sum(deltas) / len(deltas)
        median_d = sorted(deltas)[len(deltas) // 2]

        best_idx = deltas.index(best)
        worst_idx = deltas.index(worst)
        best_pt = csv_rows[best_idx]
        worst_pt = csv_rows[worst_idx]

        summary[sc] = {
            "n_beat": n_beat,
            "n_tie": n_tie,
            "n_lose": n_lose,
            "pct_beat": round(n_beat / 27 * 100, 1),
            "best_delta": round(best, 4),
            "best_point": f"({best_pt['aggression']}, {best_pt['trail_mult']}, {best_pt['max_exposure']})",
            "worst_delta": round(worst, 4),
            "worst_point": f"({worst_pt['aggression']}, {worst_pt['trail_mult']}, {worst_pt['max_exposure']})",
            "mean_delta": round(mean_d, 4),
            "median_delta": round(median_d, 4),
        }

        print(f"\n  ── {sc} scenario ──")
        print(f"  Beat baseline: {n_beat}/27 ({n_beat/27*100:.0f}%)")
        print(f"  Tie:           {n_tie}/27")
        print(f"  Lose:          {n_lose}/27")
        print(f"  Best Δ:  {best:+.2f} at {summary[sc]['best_point']}")
        print(f"  Worst Δ: {worst:+.2f} at {summary[sc]['worst_point']}")
        print(f"  Mean Δ:  {mean_d:+.4f}")
        print(f"  Median Δ: {median_d:+.4f}")

    # ── Cliff risk analysis ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  CLIFF RISK ANALYSIS (harsh scenario)")
    print("=" * 70)

    harsh_deltas = [r["delta_score_harsh"] for r in csv_rows]
    beat_mask = [d > 0.01 for d in harsh_deltas]

    # Check adjacency: for each point that beats baseline, count how many
    # of its grid neighbors also beat baseline
    neighbor_counts = []
    for i, (aggr, trail, cap) in enumerate(grid_points):
        if not beat_mask[i]:
            continue
        # Find neighbors (differ by 1 step in exactly 1 dimension)
        neighbors_beat = 0
        neighbors_total = 0
        for j, (a2, t2, c2) in enumerate(grid_points):
            if i == j:
                continue
            diffs = (abs(AGGRESSION_VALS.index(aggr) - AGGRESSION_VALS.index(a2))
                     + abs(TRAIL_VALS.index(trail) - TRAIL_VALS.index(t2))
                     + abs(CAP_VALS.index(cap) - CAP_VALS.index(c2)))
            if diffs == 1:  # adjacent in exactly 1 dimension
                neighbors_total += 1
                if beat_mask[j]:
                    neighbors_beat += 1
        neighbor_counts.append((i, aggr, trail, cap, neighbors_beat, neighbors_total))

    if neighbor_counts:
        avg_neighbor_beat = sum(nc[4] for nc in neighbor_counts) / len(neighbor_counts)
        avg_neighbor_total = sum(nc[5] for nc in neighbor_counts) / len(neighbor_counts)
        print(f"  Points that beat baseline: {sum(beat_mask)}/27")
        print(f"  Avg neighbors also beating: {avg_neighbor_beat:.1f}/{avg_neighbor_total:.1f}")
        cliff_risk = avg_neighbor_beat / avg_neighbor_total < 0.50 if avg_neighbor_total > 0 else True
    else:
        avg_neighbor_beat = 0
        cliff_risk = True
        print(f"  Points that beat baseline: 0/27")
        print(f"  No winning points → cliff risk = N/A")

    # Heatmap: for each aggression level, show trail×cap matrix
    print("\n  HEATMAP (harsh Δscore, rows=trail, cols=cap):")
    for aggr in AGGRESSION_VALS:
        print(f"\n  aggression = {aggr:.2f}")
        print(f"  {'trail\\cap':>10s}", end="")
        for cap in CAP_VALS:
            print(f"  {cap:>7.2f}", end="")
        print()
        for trail in TRAIL_VALS:
            print(f"  {trail:>10.1f}", end="")
            for cap in CAP_VALS:
                idx = grid_points.index((aggr, trail, cap))
                d = harsh_deltas[idx]
                marker = "+" if d > 0.01 else ("-" if d < -0.01 else "=")
                print(f"  {d:+7.2f}{marker}", end="")
            print()

    # ── Overall conclusion ───────────────────────────────────────────────
    h = summary["harsh"]
    pct_beat = h["pct_beat"]

    if pct_beat >= 60:
        if not cliff_risk:
            verdict = "PASS — broad winning region, no cliff"
        else:
            verdict = "PASS (marginal) — broad winning region but some cliff risk"
    elif pct_beat >= 30:
        verdict = "MARGINAL — moderate winning region"
    elif pct_beat > 0:
        verdict = "FAIL — narrow winning region (cliff risk)"
    else:
        verdict = "FAIL — no grid point beats baseline"

    print(f"\n  {'=' * 50}")
    print(f"  VERDICT (harsh): {verdict}")
    print(f"  {pct_beat:.0f}% beat baseline, cliff_risk={'YES' if cliff_risk else 'NO'}")
    print(f"  {'=' * 50}")

    # ── Save JSON ────────────────────────────────────────────────────────
    json_data = {
        "description": "Sensitivity grid: 27-point for V11 cycle_late params",
        "grid_axes": {
            "aggression": AGGRESSION_VALS,
            "trail_mult": TRAIL_VALS,
            "max_exposure": CAP_VALS,
        },
        "baseline": {sc: baseline[sc] for sc in SCENARIO_NAMES},
        "summary_by_scenario": summary,
        "cliff_risk_analysis": {
            "n_beat_harsh": sum(beat_mask),
            "avg_neighbor_beat_rate": round(avg_neighbor_beat / avg_neighbor_total, 4) if avg_neighbor_beat > 0 else 0,
            "cliff_risk": cliff_risk,
        },
        "verdict": verdict,
        "pass_criteria": {
            "pct_beat_threshold": ">=60% for PASS",
            "cliff_definition": "avg neighbor beat rate < 50%",
        },
    }

    json_path = OUTDIR / "sensitivity_grid.json"

    def _convert(obj):
        """Convert numpy types for JSON serialization."""
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_convert(v) for v in obj]
        return obj

    with open(json_path, "w") as f:
        json.dump(_convert(json_data), f, indent=2)
    print(f"\n  Saved: {json_path}")
    print(f"  Saved: {csv_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
