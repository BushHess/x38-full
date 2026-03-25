"""Standalone Pattern A runner for X34 c_ablation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import BacktestResult, SCENARIOS
from strategies.vtrend.strategy import VTrendConfig, VTrendStrategy
from strategies.vtrend_qvdo.strategy import VTrendQVDOConfig, VTrendQVDOStrategy
from research.x34.branches.c_ablation.code.smoke_checks import run_smoke_checks
from research.x34.branches.c_ablation.code.strategy_a3 import VTrendA3Config
from research.x34.branches.c_ablation.code.strategy_a3 import VTrendA3Strategy
from research.x34.branches.c_ablation.code.strategy_a5 import VTrendA5Config
from research.x34.branches.c_ablation.code.strategy_a5 import VTrendA5Strategy


DATA_PATH = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
RAW_DIR = RESULTS_DIR / "raw"
DELTA_EQUIV = 0.03


@dataclass(frozen=True)
class StrategySpec:
    key: str
    label: str
    make_config: Callable[[], object]
    make_strategy: Callable[[object], object]


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec(
        key="e0",
        label="E0 VTREND baseline",
        make_config=VTrendConfig,
        make_strategy=lambda config: VTrendStrategy(config),
    ),
    StrategySpec(
        key="full",
        label="Full Q-VDO-RH",
        make_config=VTrendQVDOConfig,
        make_strategy=lambda config: VTrendQVDOStrategy(config),
    ),
    StrategySpec(
        key="a5",
        label="A5 VDO + adaptive theta",
        make_config=VTrendA5Config,
        make_strategy=lambda config: VTrendA5Strategy(config),
    ),
    StrategySpec(
        key="a3",
        label="A3 ratio mode + adaptive theta",
        make_config=VTrendA3Config,
        make_strategy=lambda config: VTrendA3Strategy(config),
    ),
)


def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default="2026-02-20")
    parser.add_argument("--warmup-days", type=int, default=365)
    parser.add_argument("--initial-cash", type=float, default=10_000.0)
    parser.add_argument("--scenario", default="harsh", choices=tuple(SCENARIOS.keys()))
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    return parser.parse_args()


def run_strategy(
    spec: StrategySpec,
    *,
    start: str,
    end: str,
    warmup_days: int,
    initial_cash: float,
    scenario_name: str,
) -> tuple[dict[str, object], BacktestResult]:
    feed = DataFeed(str(DATA_PATH), start=start, end=end, warmup_days=warmup_days)
    config = spec.make_config()
    strategy = spec.make_strategy(config)
    t0 = time.time()
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=SCENARIOS[scenario_name],
        initial_cash=initial_cash,
        warmup_mode="no_trade",
    )
    result = engine.run()
    runtime_sec = time.time() - t0
    meta = {
        "key": spec.key,
        "label": spec.label,
        "config": asdict(config),
        "scenario": scenario_name,
        "start": start,
        "end": end,
        "warmup_days": warmup_days,
        "initial_cash": initial_cash,
        "runtime_sec": runtime_sec,
    }
    return meta, result


def _summary_row(meta: dict[str, object], result: BacktestResult) -> dict[str, object]:
    summary = result.summary
    return {
        "key": meta["key"],
        "label": meta["label"],
        "scenario": meta["scenario"],
        "start": meta["start"],
        "end": meta["end"],
        "runtime_sec": round(float(meta["runtime_sec"]), 3),
        "sharpe": summary.get("sharpe"),
        "cagr_pct": summary.get("cagr_pct"),
        "max_drawdown_mid_pct": summary.get("max_drawdown_mid_pct"),
        "trades": summary.get("trades"),
        "win_rate_pct": summary.get("win_rate_pct"),
        "profit_factor": summary.get("profit_factor"),
        "avg_exposure": summary.get("avg_exposure"),
        "total_return_pct": summary.get("total_return_pct"),
        "final_nav_mid": summary.get("final_nav_mid"),
        "fees_total": summary.get("fees_total"),
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_equity_csv(path: Path, result: BacktestResult) -> None:
    rows = [
        {
            "close_time": ms_to_iso(snap.close_time),
            "nav_mid": snap.nav_mid,
            "nav_liq": snap.nav_liq,
            "cash": snap.cash,
            "btc_qty": snap.btc_qty,
            "exposure": snap.exposure,
        }
        for snap in result.equity
    ]
    _write_csv(path, rows)


def _write_trades_csv(path: Path, result: BacktestResult) -> None:
    rows = [
        {
            "trade_id": trade.trade_id,
            "entry_time": ms_to_iso(trade.entry_ts_ms),
            "exit_time": ms_to_iso(trade.exit_ts_ms),
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "qty": trade.qty,
            "pnl": trade.pnl,
            "return_pct": trade.return_pct,
            "days_held": trade.days_held,
            "entry_reason": trade.entry_reason,
            "exit_reason": trade.exit_reason,
        }
        for trade in result.trades
    ]
    _write_csv(path, rows)


def _delta(current: float, reference: float) -> float:
    return current - reference


def _relation(delta: float) -> str:
    if math.isnan(delta):
        return "n/a"
    if delta >= DELTA_EQUIV:
        return ">>"
    if delta <= -DELTA_EQUIV:
        return "<<"
    return "≈"


def _metric(summary_map: dict[str, dict[str, object]], key: str, metric: str) -> float:
    value = summary_map[key].get(metric)
    return float(value) if value is not None else math.nan


def _build_attribution(summary_map: dict[str, dict[str, object]]) -> dict[str, object]:
    sharpe = {key: _metric(summary_map, key, "sharpe") for key in summary_map}

    a5_vs_full = _delta(sharpe["a5"], sharpe["full"])
    a3_vs_full = _delta(sharpe["a3"], sharpe["full"])
    a5_vs_e0 = _delta(sharpe["a5"], sharpe["e0"])
    a3_vs_e0 = _delta(sharpe["a3"], sharpe["e0"])
    full_vs_e0 = _delta(sharpe["full"], sharpe["e0"])

    verdict = "INCONCLUSIVE"
    next_action = "Manual review."

    if (
        _relation(a5_vs_full) == "≈"
        and _relation(a3_vs_full) == "≈"
        and _relation(a5_vs_e0) == "<<"
    ):
        verdict = "CLOSE Q-VDO-RH family"
        next_action = "Theta is the main failure mode; do not open d_ or e_."
    elif (
        _relation(a5_vs_full) == ">>"
        and _relation(a3_vs_full) == ">>"
        and _relation(a5_vs_e0) == "≈"
        and _relation(a3_vs_e0) == "≈"
    ):
        verdict = "CLOSE Q-VDO-RH family"
        next_action = (
            "Full Q-VDO-RH loses mainly from normalized input; A5 and A3 only recover "
            "back toward E0, so do not open d_ or e_."
        )
    elif _relation(a3_vs_full) == "≈":
        verdict = "CLOSE normalized-input direction"
        next_action = "Magnitude/EMA normalization adds no value; stop downstream work on that component."
    elif _relation(a5_vs_full) == ">>" and _relation(a5_vs_e0) == "<<":
        verdict = "CLOSE Q-VDO-RH family"
        next_action = "Input normalization hurts and adaptive theta also hurts."
    elif _relation(a5_vs_full) == ">>" and _relation(a5_vs_e0) == "≈":
        verdict = "CLOSE Q-VDO-RH family"
        next_action = "Input normalization hurts while adaptive theta is neutral."
    elif (
        (a5_vs_full >= DELTA_EQUIV and a5_vs_e0 >= -DELTA_EQUIV)
        or (a3_vs_full >= DELTA_EQUIV and a3_vs_e0 >= -DELTA_EQUIV)
    ):
        verdict = "GO d_regime_switch gate passed"
        next_action = "At least one component improves on full Q-VDO-RH without losing materially to E0."

    return {
        "delta_sharpe": {
            "a5_vs_full": a5_vs_full,
            "a3_vs_full": a3_vs_full,
            "a5_vs_e0": a5_vs_e0,
            "a3_vs_e0": a3_vs_e0,
            "full_vs_e0": full_vs_e0,
        },
        "relation": {
            "a5_vs_full": _relation(a5_vs_full),
            "a3_vs_full": _relation(a3_vs_full),
            "a5_vs_e0": _relation(a5_vs_e0),
            "a3_vs_e0": _relation(a3_vs_e0),
            "full_vs_e0": _relation(full_vs_e0),
        },
        "verdict": verdict,
        "next_action": next_action,
    }


def _render_variant_report(
    *,
    candidate_key: str,
    candidate_label: str,
    summary_map: dict[str, dict[str, object]],
    attribution: dict[str, object],
    warmup_days: int,
) -> str:
    candidate = summary_map[candidate_key]
    full = summary_map["full"]
    e0 = summary_map["e0"]
    delta_key = f"{candidate_key}_vs_full"
    e0_delta_key = f"{candidate_key}_vs_e0"
    return (
        f"# {candidate_label}\n\n"
        f"Scenario: `{candidate['scenario']}`  \n"
        f"Window: `{candidate['start']}` -> `{candidate['end']}`  \n"
        f"Warmup: `{warmup_days}` days\n\n"
        "## Metrics\n\n"
        "| Variant | Sharpe | CAGR % | MDD % | Trades |\n"
        "|---|---:|---:|---:|---:|\n"
        f"| {candidate['label']} | {candidate['sharpe']:.4f} | {candidate['cagr_pct']:.2f} | {candidate['max_drawdown_mid_pct']:.2f} | {int(candidate['trades'])} |\n"
        f"| Full Q-VDO-RH | {full['sharpe']:.4f} | {full['cagr_pct']:.2f} | {full['max_drawdown_mid_pct']:.2f} | {int(full['trades'])} |\n"
        f"| E0 baseline | {e0['sharpe']:.4f} | {e0['cagr_pct']:.2f} | {e0['max_drawdown_mid_pct']:.2f} | {int(e0['trades'])} |\n\n"
        "## Deltas\n\n"
        f"- Delta Sharpe vs Full Q-VDO-RH: `{attribution['delta_sharpe'][delta_key]:+.4f}` ({attribution['relation'][delta_key]})\n"
        f"- Delta Sharpe vs E0: `{attribution['delta_sharpe'][e0_delta_key]:+.4f}` ({attribution['relation'][e0_delta_key]})\n\n"
        "## Readout\n\n"
        f"- Verdict context: `{attribution['verdict']}`\n"
        f"- Next action: {attribution['next_action']}\n"
    )


def _render_attribution_report(
    *,
    summary_rows: list[dict[str, object]],
    attribution: dict[str, object],
    args: argparse.Namespace,
) -> str:
    lines = [
        "# c_ablation Attribution Matrix",
        "",
        f"Scenario: `{args.scenario}`",
        f"Window: `{args.start}` -> `{args.end}`",
        f"Warmup: `{args.warmup_days}` days",
        "",
        "## Strategy Metrics",
        "",
        "| Key | Variant | Sharpe | CAGR % | MDD % | Trades | Win Rate % | Avg Exposure |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['key']} | {row['label']} | {float(row['sharpe']):.4f} | "
            f"{float(row['cagr_pct']):.2f} | {float(row['max_drawdown_mid_pct']):.2f} | "
            f"{int(row['trades'])} | {float(row['win_rate_pct']):.2f} | {float(row['avg_exposure']):.4f} |"
        )

    lines.extend(
        [
            "",
            "## Delta Sharpe Matrix",
            "",
            "| Comparison | Delta Sharpe | Relation |",
            "|---|---:|---|",
            f"| A5 vs Full | {attribution['delta_sharpe']['a5_vs_full']:+.4f} | {attribution['relation']['a5_vs_full']} |",
            f"| A3 vs Full | {attribution['delta_sharpe']['a3_vs_full']:+.4f} | {attribution['relation']['a3_vs_full']} |",
            f"| A5 vs E0 | {attribution['delta_sharpe']['a5_vs_e0']:+.4f} | {attribution['relation']['a5_vs_e0']} |",
            f"| A3 vs E0 | {attribution['delta_sharpe']['a3_vs_e0']:+.4f} | {attribution['relation']['a3_vs_e0']} |",
            f"| Full vs E0 | {attribution['delta_sharpe']['full_vs_e0']:+.4f} | {attribution['relation']['full_vs_e0']} |",
            "",
            "## Verdict",
            "",
            f"- Verdict: `{attribution['verdict']}`",
            f"- Next action: {attribution['next_action']}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = get_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    smoke_results = run_smoke_checks() if not args.skip_smoke else []
    if smoke_results:
        smoke_payload = [
            {"name": result.name, "passed": result.passed, "detail": result.detail}
            for result in smoke_results
        ]
        _write_json(RAW_DIR / "smoke_checks.json", smoke_payload)
        failed = [result for result in smoke_results if not result.passed]
        if failed:
            for result in smoke_results:
                status = "PASS" if result.passed else "FAIL"
                print(f"{status} {result.name}: {result.detail}")
            return 1
        print(f"Smoke checks passed: {len(smoke_results)}")
        if args.smoke_only:
            return 0

    run_meta = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_path": str(DATA_PATH),
        "scenario": args.scenario,
        "start": args.start,
        "end": args.end,
        "warmup_days": args.warmup_days,
        "initial_cash": args.initial_cash,
        "root": str(ROOT),
    }
    _write_json(RAW_DIR / "run_meta.json", run_meta)

    raw_payload: dict[str, object] = {}
    summary_rows: list[dict[str, object]] = []
    summary_map: dict[str, dict[str, object]] = {}

    for spec in STRATEGIES:
        print(f"Running {spec.key} ({spec.label})...")
        meta, result = run_strategy(
            spec,
            start=args.start,
            end=args.end,
            warmup_days=args.warmup_days,
            initial_cash=args.initial_cash,
            scenario_name=args.scenario,
        )
        row = _summary_row(meta, result)
        summary_rows.append(row)
        summary_map[spec.key] = row
        raw_payload[spec.key] = {
            "meta": meta,
            "summary": result.summary,
        }
        _write_json(RAW_DIR / f"{spec.key}_summary.json", {"meta": meta, "summary": result.summary})
        _write_equity_csv(RAW_DIR / f"{spec.key}_equity.csv", result)
        _write_trades_csv(RAW_DIR / f"{spec.key}_trades.csv", result)

    _write_json(RAW_DIR / "all_summaries.json", raw_payload)
    _write_csv(RAW_DIR / "summary_table.csv", summary_rows)

    attribution = _build_attribution(summary_map)
    _write_json(RAW_DIR / "attribution_matrix.json", attribution)

    (RESULTS_DIR / "a5_validation_report.md").write_text(
        _render_variant_report(
            candidate_key="a5",
            candidate_label="A5 Validation Report",
            summary_map=summary_map,
            attribution=attribution,
            warmup_days=args.warmup_days,
        )
    )
    (RESULTS_DIR / "a3_validation_report.md").write_text(
        _render_variant_report(
            candidate_key="a3",
            candidate_label="A3 Validation Report",
            summary_map=summary_map,
            attribution=attribution,
            warmup_days=args.warmup_days,
        )
    )
    (RESULTS_DIR / "attribution_matrix.md").write_text(
        _render_attribution_report(
            summary_rows=summary_rows,
            attribution=attribution,
            args=args,
        )
    )

    print("Completed c_ablation standalone run.")
    print(f"Results: {RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
