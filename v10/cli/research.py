"""CLI entry point for V10 research: candidate matrix and walk-forward optimization.

Usage:
    python -m v10.cli.research \\
        --data data/bars_btcusdt_2016_now_h1_4h_1d.csv \\
        --candidates candidates_example.yaml \\
        --start 2019-01-01 --end 2026-02-20 \\
        --warmup-days 365 --outdir out_research \\
        --mode matrix

Modes:
    matrix   — run all candidates × smart/base/harsh, compute regime returns + DD episodes
    wfo      — walk-forward optimization for each candidate with param_ranges
    decision — run decision gate on existing outdir (requires prior matrix run)
    full     — matrix + wfo + decision
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

from v10.core.data import DataFeed
from v10.core.meta import stamp_run_meta
from v10.core.types import SCENARIOS
from v10.research.candidates import (
    CandidateSpec,
    load_candidates,
    run_candidate_matrix,
    write_matrix_outputs,
)
from v10.research.decision import evaluate, write_decision_report, write_decision_json
from v10.research.wfo import generate_windows, run_wfo


def _run_matrix(
    candidates: list[CandidateSpec],
    feed: DataFeed,
    initial_cash: float,
    outdir: str,
) -> None:
    print(f"Running candidate matrix ({len(candidates)} candidates × "
          f"{len(SCENARIOS)} scenarios) ...")

    results = run_candidate_matrix(
        candidates, feed, initial_cash=initial_cash,
    )
    out = write_matrix_outputs(results, feed.d1_bars, outdir)
    print(f"Matrix results written to {out}/")

    # Print summary table
    print()
    print("=" * 80)
    print("  Candidate Matrix Summary")
    print("=" * 80)
    header = f"  {'Candidate':<20} {'Scenario':<8} {'CAGR%':>8} {'MDD%':>8} {'Sharpe':>8} {'Score':>8}"
    print(header)
    print("  " + "-" * 74)
    for cr in results:
        s = cr.result.summary
        sharpe = s.get("sharpe")
        sharpe_str = f"{sharpe:8.2f}" if sharpe else "     N/A"
        print(f"  {cr.candidate_name:<20} {cr.scenario:<8} "
              f"{s.get('cagr_pct', 0):8.2f} "
              f"{s.get('max_drawdown_mid_pct', 0):8.2f} "
              f"{sharpe_str} "
              f"{cr.score:8.2f}")
    print("=" * 80)


def _run_wfo(
    candidates: list[CandidateSpec],
    data_path: str,
    start: str,
    end: str,
    outdir: str,
    train_months: int,
    test_months: int,
    slide_months: int,
    top_k: int,
    warmup_days: int,
    wfo_scenario: str,
    initial_cash: float,
) -> None:
    wfo_dir = Path(outdir) / "wfo"
    wfo_dir.mkdir(parents=True, exist_ok=True)

    wfo_candidates = [c for c in candidates if c.param_ranges]
    if not wfo_candidates:
        print("No candidates with param_ranges — skipping WFO.")
        return

    for spec in wfo_candidates:
        print(f"\nWFO: {spec.name} ({len(spec.param_ranges)} range keys) ...")
        windows, survivors = run_wfo(
            candidate=spec,
            data_path=data_path,
            start=start,
            end=end,
            train_months=train_months,
            test_months=test_months,
            slide_months=slide_months,
            top_k=top_k,
            warmup_days=warmup_days,
            scenario=wfo_scenario,
            initial_cash=initial_cash,
        )

        cand_wfo_dir = wfo_dir / spec.name
        cand_wfo_dir.mkdir(parents=True, exist_ok=True)

        # Write windows
        with open(cand_wfo_dir / "windows.json", "w") as f:
            json.dump(
                [dataclasses.asdict(w) for w in windows],
                f, indent=2,
            )

        # Write survivors
        survivor_dicts = []
        for s in survivors:
            d = {
                "params": s.params,
                "windows_tested": s.windows_tested,
                "windows_passed": s.windows_passed,
                "pass_rate": round(s.pass_rate, 4),
                "median_test_score": round(s.median_test_score, 2),
                "window_details": [
                    {
                        "window_id": wr.window_id,
                        "train_score": round(wr.train_score, 2),
                        "test_score": round(wr.test_score, 2) if wr.test_score is not None else None,
                        "test_return_pct": round(wr.test_return_pct, 2) if wr.test_return_pct is not None else None,
                        "test_mdd_pct": round(wr.test_mdd_pct, 2) if wr.test_mdd_pct is not None else None,
                        "passed": wr.passed,
                    }
                    for wr in s.window_details
                ],
            }
            survivor_dicts.append(d)

        with open(cand_wfo_dir / "survivors.json", "w") as f:
            json.dump(survivor_dicts, f, indent=2)

        # Write best params
        if survivors:
            with open(cand_wfo_dir / "best_params.json", "w") as f:
                json.dump(survivors[0].params, f, indent=2)

        print(f"  Windows: {len(windows)}, Survivors: {len(survivors)}")
        if survivors:
            best = survivors[0]
            print(f"  Best: pass_rate={best.pass_rate:.0%}, "
                  f"median_score={best.median_test_score:.1f}, "
                  f"params={best.params}")


def _run_decision(outdir: str, baseline_name: str) -> None:
    out = Path(outdir)
    if not (out / "scenario_table.csv").exists():
        print("No scenario_table.csv found — skipping decision gate.")
        return

    print(f"\nRunning decision gate (baseline: {baseline_name}) ...")
    try:
        result = evaluate(outdir, baseline_name=baseline_name)
    except ValueError as e:
        print(f"  Decision gate error: {e}")
        return

    report_path = write_decision_report(result, outdir)
    json_path = write_decision_json(result, outdir)

    print(f"  Decision report: {report_path}")
    print(f"  Decision JSON:   {json_path}")
    print(f"  Selected: {result.selected}")
    for g in result.gates:
        print(f"    {g.name}: [{g.tag}]" +
              (f" — {'; '.join(g.reasons)}" if g.reasons else ""))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="V10 Research: candidate matrix + walk-forward optimization",
    )
    parser.add_argument("--data", required=True, help="Path to multi-TF CSV")
    parser.add_argument("--config", default=None, help="Path to YAML config file")
    parser.add_argument("--candidates", required=True, help="Path to candidates YAML")
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--warmup-days", type=int, default=None)
    parser.add_argument("--initial-cash", type=float, default=None)
    parser.add_argument("--outdir", default="out/research", help="Output directory")
    parser.add_argument(
        "--mode", default="matrix", choices=["matrix", "wfo", "decision", "full"],
        help="Run mode (default: matrix)",
    )
    parser.add_argument(
        "--baseline", default=None,
        help="Baseline candidate name for decision gate (default: baseline_legacy)",
    )
    # WFO-specific options
    parser.add_argument("--train-months", type=int, default=24)
    parser.add_argument("--test-months", type=int, default=6)
    parser.add_argument("--slide-months", type=int, default=6)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--wfo-scenario", default="base", choices=list(SCENARIOS),
        help="Cost scenario for WFO (default: base)",
    )
    args = parser.parse_args(argv)

    # Merge config file defaults
    config_dict = None
    if args.config:
        from v10.core.config import load_config, config_to_dict
        config = load_config(args.config)
        config_dict = config_to_dict(config)
        if args.warmup_days is None:
            args.warmup_days = config.engine.warmup_days
        if args.initial_cash is None:
            args.initial_cash = config.engine.initial_cash

    # Final hardcoded defaults
    args.warmup_days = args.warmup_days or 365
    args.initial_cash = args.initial_cash or 10_000.0
    args.baseline = args.baseline or "baseline_legacy"

    print(f"Loading data from {args.data} ...")
    feed = DataFeed(
        args.data,
        start=args.start,
        end=args.end,
        warmup_days=args.warmup_days,
    )
    print(f"  {feed}")

    specs = load_candidates(args.candidates)
    print(f"Loaded {len(specs)} candidates from {args.candidates}")

    # Stamp run metadata
    config_snap: dict[str, Any] = {
        "mode": args.mode,
        "candidates_file": args.candidates,
        "candidate_names": [s.name for s in specs],
        "scenarios": list(SCENARIOS),
        "initial_cash": args.initial_cash,
        "warmup_days": args.warmup_days,
        "baseline": args.baseline,
        "start": args.start,
        "end": args.end,
    }
    if args.config:
        config_snap["config_file"] = args.config
        config_snap["config"] = config_dict
    if args.mode in ("wfo", "full"):
        config_snap["wfo"] = {
            "train_months": args.train_months,
            "test_months": args.test_months,
            "slide_months": args.slide_months,
            "top_k": args.top_k,
            "wfo_scenario": args.wfo_scenario,
        }
    stamp_run_meta(
        args.outdir, argv=sys.argv, config=config_snap, data_path=args.data,
    )

    if args.mode in ("matrix", "full"):
        _run_matrix(specs, feed, args.initial_cash, args.outdir)

    if args.mode in ("wfo", "full"):
        _run_wfo(
            candidates=specs,
            data_path=args.data,
            start=args.start or "",
            end=args.end or "",
            outdir=args.outdir,
            train_months=args.train_months,
            test_months=args.test_months,
            slide_months=args.slide_months,
            top_k=args.top_k,
            warmup_days=args.warmup_days,
            wfo_scenario=args.wfo_scenario,
            initial_cash=args.initial_cash,
        )

    if args.mode in ("matrix", "decision", "full"):
        _run_decision(args.outdir, args.baseline)

    print("\nDone.")


if __name__ == "__main__":
    main()
