#!/usr/bin/env python3
"""P0.2 -- Benchmark simple event-gated floor exits."""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.e0_exit_event_gate.lib import EventGateConfig, EventGatedFloorStrategy
from research.e0_exit_floor.p0_1_exit_floor_benchmark import (
    END,
    HOLDOUT_START,
    INITIAL_CASH,
    START,
    WARMUP,
    ExitFloorConfig,
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
    X0ExitFloorStrategy,
)
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS


OUTDIR = Path(__file__).resolve().parent
DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")


def make_reference():
    return VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig())


def make_raw_floor():
    return X0ExitFloorStrategy(
        ExitFloorConfig(
            strategy_id="x0e5_floor_latch",
            floor_mode="floor",
            floor_atr_mult=2.0,
        )
    )


def make_bslow():
    return EventGatedFloorStrategy(
        EventGateConfig(
            strategy_id="x0e5_floor_bslow",
            floor_mode="floor",
            floor_atr_mult=2.0,
            gate_mode="below_slow",
        )
    )


def make_peak3():
    return EventGatedFloorStrategy(
        EventGateConfig(
            strategy_id="x0e5_floor_peak3",
            floor_mode="floor",
            floor_atr_mult=2.0,
            gate_mode="peak_age_ge_3",
            peak_age_bars=3,
        )
    )


SPECS = [
    ("X0_E5EXIT", "anchor", make_reference),
    ("X0E5_FLOOR_LATCH", "raw_floor", make_raw_floor),
    ("X0E5_FLOOR_BSLOW", "event_gate", make_bslow),
    ("X0E5_FLOOR_PEAK3", "event_gate", make_peak3),
]


def run_one(factory, start: str, end: str, scenario: str):
    feed = DataFeed(DATA, start=start, end=end, warmup_days=WARMUP)
    engine = BacktestEngine(
        feed=feed,
        strategy=factory(),
        cost=SCENARIOS[scenario],
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP,
        warmup_mode="no_trade",
    )
    return engine.run(), engine.strategy


def save_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    t0 = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    full_rows: list[dict] = []
    holdout_rows: list[dict] = []
    gate_rows: list[dict] = []
    full_metrics: dict[str, dict] = {}
    hold_metrics: dict[str, dict] = {}

    for sid, family, factory in SPECS:
        full_metrics[sid] = {}
        hold_metrics[sid] = {}
        for scenario in ("smart", "base", "harsh"):
            res, strat = run_one(factory, START, END, scenario)
            s = res.summary
            full_metrics[sid][scenario] = s
            full_rows.append({
                "strategy_id": sid,
                "family": family,
                "scenario": scenario,
                "sharpe": s["sharpe"],
                "cagr_pct": s["cagr_pct"],
                "mdd_pct": s["max_drawdown_mid_pct"],
                "calmar": s["calmar"],
                "trades": s["trades"],
                "win_rate_pct": s["win_rate_pct"],
                "profit_factor": s["profit_factor"],
                "avg_exposure": s["avg_exposure"],
                "total_return_pct": s["total_return_pct"],
            })
            if scenario == "harsh" and hasattr(strat, "get_gate_stats"):
                gate_rows.append({
                    "strategy_id": sid,
                    **strat.get_gate_stats(),
                })

        res, _ = run_one(factory, HOLDOUT_START, END, "harsh")
        s = res.summary
        hold_metrics[sid]["harsh"] = s
        holdout_rows.append({
            "strategy_id": sid,
            "scenario": "harsh",
            "start": HOLDOUT_START,
            "end": END,
            "sharpe": s["sharpe"],
            "cagr_pct": s["cagr_pct"],
            "mdd_pct": s["max_drawdown_mid_pct"],
            "calmar": s["calmar"],
            "trades": s["trades"],
            "win_rate_pct": s["win_rate_pct"],
            "profit_factor": s["profit_factor"],
            "avg_exposure": s["avg_exposure"],
            "total_return_pct": s["total_return_pct"],
        })

    ref = full_metrics["X0_E5EXIT"]["harsh"]
    raw_floor = full_metrics["X0E5_FLOOR_LATCH"]["harsh"]
    ref_hold = hold_metrics["X0_E5EXIT"]["harsh"]
    raw_hold = hold_metrics["X0E5_FLOOR_LATCH"]["harsh"]

    delta_rows: list[dict] = []
    for sid, _, _ in SPECS:
        if sid == "X0_E5EXIT":
            continue
        cur = full_metrics[sid]["harsh"]
        cur_hold = hold_metrics[sid]["harsh"]
        delta_rows.append({
            "strategy_id": sid,
            "vs_anchor_d_sharpe": round(cur["sharpe"] - ref["sharpe"], 4),
            "vs_anchor_d_cagr_pct": round(cur["cagr_pct"] - ref["cagr_pct"], 2),
            "vs_anchor_d_mdd_pct": round(cur["max_drawdown_mid_pct"] - ref["max_drawdown_mid_pct"], 2),
            "vs_anchor_d_calmar": round(cur["calmar"] - ref["calmar"], 4),
            "vs_raw_floor_d_sharpe": round(cur["sharpe"] - raw_floor["sharpe"], 4),
            "vs_raw_floor_d_cagr_pct": round(cur["cagr_pct"] - raw_floor["cagr_pct"], 2),
            "vs_raw_floor_d_mdd_pct": round(cur["max_drawdown_mid_pct"] - raw_floor["max_drawdown_mid_pct"], 2),
            "vs_raw_floor_d_calmar": round(cur["calmar"] - raw_floor["calmar"], 4),
            "holdout_vs_anchor_d_sharpe": round(cur_hold["sharpe"] - ref_hold["sharpe"], 4),
            "holdout_vs_anchor_d_cagr_pct": round(cur_hold["cagr_pct"] - ref_hold["cagr_pct"], 2),
            "holdout_vs_anchor_d_mdd_pct": round(cur_hold["max_drawdown_mid_pct"] - ref_hold["max_drawdown_mid_pct"], 2),
            "holdout_vs_anchor_d_calmar": round(cur_hold["calmar"] - ref_hold["calmar"], 4),
            "holdout_vs_raw_floor_d_sharpe": round(cur_hold["sharpe"] - raw_hold["sharpe"], 4),
            "holdout_vs_raw_floor_d_cagr_pct": round(cur_hold["cagr_pct"] - raw_hold["cagr_pct"], 2),
            "holdout_vs_raw_floor_d_mdd_pct": round(cur_hold["max_drawdown_mid_pct"] - raw_hold["max_drawdown_mid_pct"], 2),
            "holdout_vs_raw_floor_d_calmar": round(cur_hold["calmar"] - raw_hold["calmar"], 4),
        })

    survivors = []
    for row in delta_rows:
        if row["strategy_id"] == "X0E5_FLOOR_LATCH":
            continue
        if (
            row["vs_anchor_d_calmar"] > 0.0
            and row["vs_raw_floor_d_calmar"] > 0.0
            and row["holdout_vs_anchor_d_calmar"] >= -0.02
            and row["holdout_vs_raw_floor_d_calmar"] >= -0.02
        ):
            survivors.append(row["strategy_id"])

    verdict = "PROMOTE_TO_VALIDATION" if survivors else "KILL_EVENT_GATE"
    top_candidate = survivors[0] if survivors else ""

    report_lines = [
        "# P0.2 Event-Gate Benchmark Report",
        "",
        "## Verdict",
        "",
        f"- `{verdict}`",
        "",
        "## Survivors",
        "",
    ]
    if survivors:
        for sid in survivors:
            report_lines.append(f"- `{sid}`")
    else:
        report_lines.append("- none")

    report_lines.extend([
        "",
        "## Full Period (harsh)",
        "",
    ])
    for sid in ("X0_E5EXIT", "X0E5_FLOOR_LATCH", "X0E5_FLOOR_BSLOW", "X0E5_FLOOR_PEAK3"):
        s = full_metrics[sid]["harsh"]
        report_lines.append(
            f"- `{sid}`: Sharpe={s['sharpe']:.4f}, CAGR={s['cagr_pct']:.2f}%, MDD={s['max_drawdown_mid_pct']:.2f}%, Calmar={s['calmar']:.4f}, Trades={s['trades']}"
        )

    report_lines.extend([
        "",
        "## Holdout (harsh)",
        "",
    ])
    for sid in ("X0_E5EXIT", "X0E5_FLOOR_LATCH", "X0E5_FLOOR_BSLOW", "X0E5_FLOOR_PEAK3"):
        s = hold_metrics[sid]["harsh"]
        report_lines.append(
            f"- `{sid}`: Sharpe={s['sharpe']:.4f}, CAGR={s['cagr_pct']:.2f}%, MDD={s['max_drawdown_mid_pct']:.2f}%, Calmar={s['calmar']:.4f}, Trades={s['trades']}"
        )

    report_lines.extend([
        "",
        "## Interpretation",
        "",
    ])
    if survivors:
        report_lines.append(f"- Candidate chosen for validation: `{top_candidate}`")
    else:
        report_lines.append("- No simple event gate improved both the anchor and the raw floor variant cleanly enough.")

    (OUTDIR / "P0_2_BENCHMARK_REPORT.md").write_text("\n".join(report_lines) + "\n")
    with (OUTDIR / "p0_2_results.json").open("w") as f:
        json.dump(
            {
                "verdict": verdict,
                "survivors": survivors,
                "top_candidate": top_candidate,
                "runtime_seconds": round(time.time() - t0, 2),
            },
            f,
            indent=2,
        )
    save_csv(OUTDIR / "p0_2_backtest_table.csv", full_rows)
    save_csv(OUTDIR / "p0_2_holdout_table.csv", holdout_rows)
    save_csv(OUTDIR / "p0_2_delta_table.csv", delta_rows)
    save_csv(OUTDIR / "p0_2_gate_stats.csv", gate_rows)
    print(f"Saved event-gate benchmark artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
