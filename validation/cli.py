"""CLI entrypoint for the unified validation pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from v10.core.config import load_config

from validation.config import ValidationConfig
from validation.runner import ValidationRunner

_DATASET_IDS = {
    "default": Path("data/bars_btcusdt_2016_now_h1_4h_1d.csv"),
    "btc_2016_now": Path("data/bars_btcusdt_2016_now_h1_4h_1d.csv"),
    "btcspot": Path("data/bars_btcusdt_2016_now_h1_4h_1d.csv"),
}


def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _csv_float_list(value: str) -> list[float]:
    out: list[float] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        out.append(float(item))
    return out


def _on_off_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value == "on"


def _on_off_to_tristate(value: str | None) -> bool | None:
    """Convert CLI on/off to bool|None.  None means 'follow suite group'."""
    if value is None:
        return None
    return value == "on"


def _resolve_dataset(dataset_arg: str | None) -> tuple[Path, str | None]:
    if not dataset_arg:
        p = _DATASET_IDS["default"]
        return p.resolve() if p.exists() else p, "default"

    if dataset_arg in _DATASET_IDS:
        p = _DATASET_IDS[dataset_arg]
        return p.resolve() if p.exists() else p, dataset_arg

    p = Path(dataset_arg)
    if p.exists():
        return p.resolve(), None

    raise ValueError(
        f"Unknown dataset id/path: {dataset_arg!r}. "
        f"Known ids: {sorted(_DATASET_IDS)}"
    )


def _hint_wfo_windows(config_path: Path) -> int | None:
    """Best-effort read of wfo_windows default from YAML custom fields."""
    try:
        raw = json.loads(json.dumps(load_config(str(config_path)), default=lambda o: o.__dict__))
        # No native field today; keep hook for future compatibility.
        _ = raw
    except Exception:
        pass
    return None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate_strategy.py",
        description="Unified strategy validation CLI",
    )

    # Required
    p.add_argument("--strategy", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--baseline-config", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)

    # Optional (spec)
    p.add_argument("--dataset", type=str, default=None,
                   help="Dataset id or path")
    p.add_argument("--scenarios", type=str, default="smart,base,harsh")
    p.add_argument("--harsh-cost-bps", type=float, default=50.0)
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--bootstrap", type=int, default=2000,
                   help="0 disables bootstrap")

    p.add_argument("--wfo-windows", type=int, default=None)
    p.add_argument("--wfo-mode", choices=["rolling", "fixed"], default="rolling")

    p.add_argument("--holdout-frac", type=float, default=0.2)
    p.add_argument("--holdout-start", type=str, default=None)
    p.add_argument("--holdout-end", type=str, default=None)

    p.add_argument("--force", action="store_true")
    p.add_argument("--force-holdout", action="store_true")

    p.add_argument(
        "--suite",
        choices=["basic", "full", "trade", "dd", "overlay", "all"],
        default="full",
    )

    p.add_argument("--sensitivity-grid", action="store_true")
    p.add_argument("--grid-aggr", type=str, default="0.85,0.90,0.95")
    p.add_argument("--grid-trail", type=str, default="2.7,3.0,3.3")
    p.add_argument("--grid-cap", type=str, default="0.75,0.90,0.95")

    p.add_argument(
        "--selection-bias",
        choices=["none", "pbo", "deflated"],
        default="deflated",
    )

    p.add_argument("--lookahead-check", choices=["on", "off"], default="on")
    p.add_argument("--trade-level", choices=["on", "off"], default=None)
    p.add_argument("--dd-episodes", choices=["on", "off"], default=None)
    p.add_argument("--overlay-test", choices=["on", "off"], default=None)
    p.add_argument("--data-integrity-check", choices=["on", "off"], default=None)
    p.add_argument(
        "--data-integrity-missing-bars-fail-pct",
        type=float,
        default=0.5,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--data-integrity-gap-multiplier",
        type=float,
        default=1.5,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--data-integrity-warmup-fail-coverage-pct",
        type=float,
        default=50.0,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--data-integrity-issues-limit",
        type=int,
        default=200,
        help=argparse.SUPPRESS,
    )
    p.add_argument("--cost-sweep-bps", type=str, default="0,10,25,50,75,100")
    p.add_argument("--cost-sweep-mode", choices=["quick", "full"], default="quick")
    p.add_argument("--invariant-check", choices=["on", "off"], default=None)
    p.add_argument("--regression-guard", choices=["on", "off"], default="off")
    p.add_argument("--golden", type=Path, default=None)
    p.add_argument("--churn-metrics", choices=["on", "off"], default=None)
    p.add_argument(
        "--churn-warning-fee-drag-pct",
        type=float,
        default=20.0,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--churn-warning-cascade-leq3-pct",
        type=float,
        default=30.0,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--churn-warning-cascade-leq6-pct",
        type=float,
        default=50.0,
        help=argparse.SUPPRESS,
    )

    # Extra controls kept for quick smoke/demo runs.
    p.add_argument("--start", type=str, default="2019-01-01", help=argparse.SUPPRESS)
    p.add_argument("--end", type=str, default="2026-02-20", help=argparse.SUPPRESS)
    p.add_argument("--warmup-days", type=int, default=365, help=argparse.SUPPRESS)
    p.add_argument("--initial-cash", type=float, default=10_000.0, help=argparse.SUPPRESS)
    p.add_argument("--wfo-train-months", type=int, default=24, help=argparse.SUPPRESS)
    p.add_argument("--wfo-test-months", type=int, default=6, help=argparse.SUPPRESS)
    p.add_argument("--wfo-slide-months", type=int, default=6, help=argparse.SUPPRESS)
    p.add_argument(
        "--min-trades-for-power",
        type=int,
        default=None,
        help=argparse.SUPPRESS,
    )
    p.add_argument("--low-trade-threshold", type=int, default=5, help=argparse.SUPPRESS)
    p.add_argument("--bootstrap-block-sizes", type=str, default="10,20,40", help=argparse.SUPPRESS)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        dataset_path, dataset_id = _resolve_dataset(args.dataset)
    except ValueError as exc:
        parser.error(str(exc))

    scenarios = _csv_list(args.scenarios)
    if not scenarios:
        parser.error("--scenarios cannot be empty")

    _VALID_SCENARIOS = {"smart", "base", "harsh"}
    invalid_scenarios = set(scenarios) - _VALID_SCENARIOS
    if invalid_scenarios:
        parser.error(
            f"Unknown scenario(s): {sorted(invalid_scenarios)}. "
            f"Valid scenarios: {sorted(_VALID_SCENARIOS)}"
        )

    # Suites that contribute to verdict (holdout, backtest gates) require harsh.
    _VERDICT_SUITES = {"full", "all"}
    if args.suite in _VERDICT_SUITES and "harsh" not in scenarios:
        parser.error(
            f"--suite {args.suite} requires 'harsh' in --scenarios "
            f"(harsh is authoritative for holdout and backtest gates)"
        )

    if args.wfo_train_months <= 0:
        parser.error("--wfo-train-months must be > 0")
    if args.wfo_test_months <= 0:
        parser.error("--wfo-test-months must be > 0")
    if args.wfo_slide_months <= 0:
        parser.error("--wfo-slide-months must be > 0")

    wfo_windows = args.wfo_windows
    if wfo_windows is None:
        wfo_windows = _hint_wfo_windows(args.config) or 8

    trade_default = args.suite in {"trade", "all"}
    dd_default = args.suite in {"dd", "all"}
    overlay_default = args.suite in {"overlay", "all"}
    regression_guard = _on_off_to_bool(args.regression_guard, default=False)

    if regression_guard and args.golden is None:
        parser.error("--golden is required when --regression-guard on")
    if regression_guard and args.golden is not None and not args.golden.exists():
        parser.error(f"--golden file not found: {args.golden}")

    cost_sweep_bps = _csv_float_list(args.cost_sweep_bps)
    min_trades_for_power = (
        int(args.min_trades_for_power)
        if args.min_trades_for_power is not None
        else int(args.low_trade_threshold)
    )

    config = ValidationConfig(
        strategy_name=args.strategy,
        baseline_name=args.baseline,
        config_path=args.config.resolve(),
        baseline_config_path=args.baseline_config.resolve(),
        outdir=args.out.resolve(),
        dataset=dataset_path,
        dataset_id=dataset_id,
        start=args.start,
        end=args.end,
        warmup_days=args.warmup_days,
        initial_cash=args.initial_cash,
        suite=args.suite,
        scenarios=scenarios,
        harsh_cost_bps=args.harsh_cost_bps,
        seed=args.seed,
        command=["python", "validate_strategy.py", *(argv if argv is not None else sys.argv[1:])],
        force=args.force,
        force_holdout=args.force_holdout,
        bootstrap=args.bootstrap,
        bootstrap_block_sizes=[int(x) for x in _csv_list(args.bootstrap_block_sizes)],
        wfo_windows=wfo_windows,
        wfo_mode=args.wfo_mode,
        wfo_train_months=args.wfo_train_months,
        wfo_test_months=args.wfo_test_months,
        wfo_slide_months=args.wfo_slide_months,
        low_trade_threshold=args.low_trade_threshold,
        min_trades_for_power=min_trades_for_power,
        holdout_frac=args.holdout_frac,
        holdout_start=args.holdout_start,
        holdout_end=args.holdout_end,
        sensitivity_grid=args.sensitivity_grid,
        grid_aggr=_csv_float_list(args.grid_aggr),
        grid_trail=_csv_float_list(args.grid_trail),
        grid_cap=_csv_float_list(args.grid_cap),
        selection_bias=args.selection_bias,
        lookahead_check=_on_off_to_bool(args.lookahead_check, default=True),
        trade_level=_on_off_to_bool(args.trade_level, default=trade_default),
        dd_episodes=_on_off_to_bool(args.dd_episodes, default=dd_default),
        overlay_test=_on_off_to_bool(args.overlay_test, default=overlay_default),
        data_integrity_check=_on_off_to_tristate(args.data_integrity_check),
        data_integrity_missing_bars_fail_pct=args.data_integrity_missing_bars_fail_pct,
        data_integrity_gap_multiplier=args.data_integrity_gap_multiplier,
        data_integrity_warmup_fail_coverage_pct=args.data_integrity_warmup_fail_coverage_pct,
        data_integrity_issues_limit=max(1, int(args.data_integrity_issues_limit)),
        cost_sweep_bps=cost_sweep_bps,
        cost_sweep_mode=args.cost_sweep_mode,
        invariant_check=_on_off_to_tristate(args.invariant_check),
        regression_guard=regression_guard,
        golden_path=args.golden.resolve() if args.golden is not None else None,
        churn_metrics=_on_off_to_tristate(args.churn_metrics),
        churn_warning_fee_drag_pct=float(args.churn_warning_fee_drag_pct),
        churn_warning_cascade_leq3_pct=float(args.churn_warning_cascade_leq3_pct),
        churn_warning_cascade_leq6_pct=float(args.churn_warning_cascade_leq6_pct),
    )

    runner = ValidationRunner(config)
    results, decision = runner.run()

    print(f"\n{'=' * 72}")
    print(f"VERDICT: {decision.tag} (exit code {decision.exit_code})")
    print(f"{'=' * 72}")
    for suite_name, result in results.items():
        err = f" — {result.error_message}" if result.error_message else ""
        print(f"{suite_name:18s} {result.status.upper()}{err}")
    print("\nReasons:")
    for reason in decision.reasons:
        print(f"- {reason}")
    print(f"\nOutput: {config.outdir}")

    return decision.exit_code
