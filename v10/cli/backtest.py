"""CLI entry point for running V10 backtests.

Usage:
    python -m v10.cli.backtest \\
        --data data/bars_btcusdt_2016_now_h1_4h_1d.csv \\
        --strategy buy_and_hold \\
        --scenario base \\
        --initial-cash 10000 \\
        --start 2019-01-01 \\
        --end 2026-02-20 \\
        --warmup-days 365 \\
        --outdir out_v10

Outputs:
    outdir/equity.csv
    outdir/trades.csv
    outdir/fills.csv
    outdir/summary.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

from v10.core.formatting import ms_to_iso
from v10.core.meta import stamp_run_meta
from v10.core.types import SCENARIOS, BacktestResult
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.strategies.base import Strategy
from v10.strategies.buy_and_hold import BuyAndHold
from v10.strategies.v8_apex import V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridStrategy
from strategies.vtrend_sm.strategy import VTrendSMStrategy
from strategies.vtrend_p.strategy import VTrendPStrategy
from strategies.latch.strategy import LatchStrategy
from strategies.vtrend_x0.strategy import VTrendX0Strategy
from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitStrategy
from strategies.vtrend_x0_volsize.strategy import VTrendX0VolsizeStrategy
from strategies.vtrend_x2.strategy import VTrendX2Strategy
from strategies.vtrend_x6.strategy import VTrendX6Strategy
from strategies.vtrend_x7.strategy import VTrendX7Strategy
from strategies.vtrend_x8.strategy import VTrendX8Strategy
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy
from strategies.vtrend_vp1.strategy import VP1Strategy
from strategies.vtrend_vp1_e5exit.strategy import VP1E5ExitStrategy
from strategies.vtrend_vp1_full.strategy import VP1FullStrategy
from strategies.vtrend_ema21_d1.strategy import VTrendEma21D1Strategy
from strategies.vtrend_e5.strategy import VTrendE5Strategy
from strategies.vtrend.strategy import VTrendStrategy
from strategies.vtrend_ema21.strategy import VTrendEma21Strategy
from strategies.vtrend_qvdo.strategy import VTrendQVDOStrategy
from strategies.vtrend_x5.strategy import VTrendX5Strategy
from strategies.v12_emdd_ref_fix.strategy import V12EMDDRefFixStrategy
from strategies.v13_add_throttle.strategy import V13AddThrottleStrategy


# ---------------------------------------------------------------------------
# Strategy registry — add new strategies here
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "buy_and_hold": BuyAndHold,
    "v8_apex": V8ApexStrategy,
    "v11_hybrid": V11HybridStrategy,
    "v12_emdd_ref_fix": V12EMDDRefFixStrategy,
    "v13_add_throttle": V13AddThrottleStrategy,
    "vtrend": VTrendStrategy,
    "vtrend_e5": VTrendE5Strategy,
    "vtrend_e5_ema21_d1": VTrendE5Ema21D1Strategy,
    "vtrend_ema21": VTrendEma21Strategy,
    "vtrend_ema21_d1": VTrendEma21D1Strategy,
    "vtrend_sm": VTrendSMStrategy,
    "vtrend_p": VTrendPStrategy,
    "latch": LatchStrategy,
    "vtrend_x0": VTrendX0Strategy,
    "vtrend_x0_e5exit": VTrendX0E5ExitStrategy,
    "vtrend_x0_volsize": VTrendX0VolsizeStrategy,
    "vtrend_x2": VTrendX2Strategy,
    "vtrend_x5": VTrendX5Strategy,
    "vtrend_x6": VTrendX6Strategy,
    "vtrend_x7": VTrendX7Strategy,
    "vtrend_x8": VTrendX8Strategy,
    "vtrend_qvdo": VTrendQVDOStrategy,
    "vtrend_vp1": VP1Strategy,
    "vtrend_vp1_e5exit": VP1E5ExitStrategy,
    "vtrend_vp1_full": VP1FullStrategy,
}


def _load_strategy(name: str) -> Strategy:
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(STRATEGY_REGISTRY))
        print(f"Unknown strategy '{name}'. Available: {available}", file=sys.stderr)
        sys.exit(1)
    return cls()


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _write_outputs(result: BacktestResult, outdir: str) -> Path:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    # equity.csv
    with open(out / "equity.csv", "w") as f:
        f.write("close_time,close_time_ms,nav_mid,nav_liq,cash,btc_qty,exposure\n")
        for e in result.equity:
            f.write(
                f"{ms_to_iso(e.close_time)},{e.close_time},"
                f"{e.nav_mid:.2f},{e.nav_liq:.2f},"
                f"{e.cash:.2f},{e.btc_qty:.8f},{e.exposure:.6f}\n"
            )

    # trades.csv
    with open(out / "trades.csv", "w") as f:
        f.write(
            "trade_id,entry_time,exit_time,entry_ts_ms,exit_ts_ms,"
            "entry_price,exit_price,qty,pnl,return_pct,days_held,"
            "entry_reason,exit_reason\n"
        )
        for t in result.trades:
            f.write(
                f"{t.trade_id},{ms_to_iso(t.entry_ts_ms)},"
                f"{ms_to_iso(t.exit_ts_ms)},"
                f"{t.entry_ts_ms},{t.exit_ts_ms},"
                f"{t.entry_price:.2f},{t.exit_price:.2f},{t.qty:.8f},"
                f"{t.pnl:.2f},{t.return_pct:.2f},{t.days_held:.2f},"
                f"{t.entry_reason},{t.exit_reason}\n"
            )

    # fills.csv
    with open(out / "fills.csv", "w") as f:
        f.write("time,ts_ms,side,qty,price,fee,notional,reason\n")
        for fl in result.fills:
            f.write(
                f"{ms_to_iso(fl.ts_ms)},{fl.ts_ms},"
                f"{fl.side.value},{fl.qty:.8f},"
                f"{fl.price:.2f},{fl.fee:.4f},{fl.notional:.2f},{fl.reason}\n"
            )

    # summary.json
    with open(out / "summary.json", "w") as f:
        json.dump(result.summary, f, indent=2, default=str)

    return out


def _print_summary(s: dict[str, Any]) -> None:
    print()
    print("=" * 60)
    print("  V10 Backtest Summary")
    print("=" * 60)
    print(f"  Initial Capital:    ${s.get('initial_cash', 0):>12,.2f}")
    rsn = s.get("report_start_nav", s.get("initial_cash", 0))
    print(f"  Report Start NAV:   ${rsn:>12,.2f}")
    print(f"  Final NAV (mid):    ${s.get('final_nav_mid', 0):>12,.2f}")
    print(f"  Total Return:       {s.get('total_return_pct', 0):>11.2f}%")
    print(f"  CAGR:               {s.get('cagr_pct', 0):>11.2f}%")
    print(f"  Max Drawdown (mid): {s.get('max_drawdown_mid_pct', 0):>11.2f}%")
    sharpe = s.get("sharpe")
    sortino = s.get("sortino")
    calmar = s.get("calmar")
    print(f"  Sharpe:             {sharpe:>11.4f}" if sharpe else "  Sharpe:                   N/A")
    print(f"  Sortino:            {sortino:>11.4f}" if sortino else "  Sortino:                  N/A")
    print(f"  Calmar:             {calmar:>11.4f}" if calmar else "  Calmar:                   N/A")
    print(f"  {'─' * 40}")
    print(f"  Trades:             {s.get('trades', 0):>11d}")
    print(f"  Win Rate:           {s.get('win_rate_pct', 0):>11.2f}%")
    pf = s.get("profit_factor", 0)
    print(f"  Profit Factor:      {pf:>11}" if isinstance(pf, str) else f"  Profit Factor:      {pf:>11.4f}")
    print(f"  Avg Trade PnL:      ${s.get('avg_trade_pnl', 0):>10.2f}")
    print(f"  Avg Days Held:      {s.get('avg_days_held', 0):>11.2f}")
    print(f"  {'─' * 40}")
    print(f"  Avg Exposure:       {s.get('avg_exposure', 0):>11.4f}")
    print(f"  Time in Market:     {s.get('time_in_market_pct', 0):>11.2f}%")
    print(f"  Total Fees:         ${s.get('fees_total', 0):>10.2f}")
    print(f"  Fee Drag %/yr:      {s.get('fee_drag_pct_per_year', 0):>11.2f}%")
    print(f"  Turnover/yr:        {s.get('turnover_per_year', 0):>11.2f}x")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _apply_config(args: argparse.Namespace) -> dict[str, Any] | None:
    """If --config given, load and merge into args. Returns config dict or None."""
    if not args.config:
        return None

    from v10.core.config import load_config, config_to_dict

    config = load_config(args.config)

    # Apply config values as defaults (only when CLI arg was not explicit)
    if args.strategy is None:
        args.strategy = config.strategy.name
    if args.scenario is None:
        args.scenario = config.engine.scenario_eval
    if args.initial_cash is None:
        args.initial_cash = config.engine.initial_cash
    if args.warmup_days is None:
        args.warmup_days = config.engine.warmup_days
    if args.warmup_mode is None:
        args.warmup_mode = config.engine.warmup_mode
    if args.rsi_method is None:
        args.rsi_method = config.strategy.params.get("rsi_method")
    if args.emergency_ref is None:
        args.emergency_ref = config.strategy.params.get("emergency_ref")

    # Apply strategy params to V8ApexConfig after strategy is loaded
    args._config_strategy_params = config.strategy.params

    return config_to_dict(config)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="V10 BTCUSDT Spot Long-Only Backtest",
    )
    parser.add_argument("--data", required=True, help="Path to multi-TF CSV")
    parser.add_argument("--config", default=None, help="Path to YAML config file")
    parser.add_argument(
        "--strategy", default=None,
        help=f"Strategy name ({', '.join(sorted(STRATEGY_REGISTRY))})",
    )
    parser.add_argument(
        "--scenario", default=None, choices=list(SCENARIOS),
        help="Cost scenario (default: base = 31 bps RT)",
    )
    parser.add_argument("--initial-cash", type=float, default=None)
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--warmup-days", type=int, default=None)
    parser.add_argument("--outdir", default="out/v10", help="Output directory")
    parser.add_argument(
        "--dump-mtf-map", action="store_true",
        help="Print (h4_close -> d1_close_used) mapping for MTF alignment audit",
    )
    parser.add_argument(
        "--rsi_method", default=None, choices=["wilder", "ewm_span"],
        help="RSI smoothing method: wilder (alpha=1/p) or ewm_span (alpha=2/(p+1))",
    )
    parser.add_argument(
        "--emergency_ref", default=None,
        choices=["pre_cost_legacy", "post_cost", "peak"],
        help="Emergency DD reference NAV: pre_cost_legacy, post_cost, or peak",
    )
    parser.add_argument(
        "--warmup_mode", default=None,
        choices=["no_trade", "allow_trade"],
        help="Warmup mode: no_trade (default, indicators only) or allow_trade (legacy)",
    )
    args = parser.parse_args(argv)

    # Merge config file defaults, then apply final hardcoded defaults
    config_dict = _apply_config(args)
    args.strategy = args.strategy or "buy_and_hold"
    args.scenario = args.scenario or "base"
    args.initial_cash = args.initial_cash or 10_000.0
    args.warmup_days = args.warmup_days or 365
    args.warmup_mode = args.warmup_mode or "no_trade"
    args.rsi_method = args.rsi_method or "ewm_span"
    args.emergency_ref = args.emergency_ref or "pre_cost_legacy"

    print(f"Loading data from {args.data} ...")
    feed = DataFeed(
        args.data,
        start=args.start,
        end=args.end,
        warmup_days=args.warmup_days,
    )
    print(f"  {feed}")

    # Build strategy with config params (generic for all strategies).
    if hasattr(args, "_config_strategy_params") and args._config_strategy_params:
        from validation.strategy_factory import _build_config_obj
        cfg = _build_config_obj(args.strategy, args._config_strategy_params)
        if cfg is not None:
            strategy = STRATEGY_REGISTRY[args.strategy](cfg)
        else:
            strategy = _load_strategy(args.strategy)
    else:
        strategy = _load_strategy(args.strategy)

    # V8/V11-specific CLI overrides (rsi_method, emergency_ref)
    if isinstance(strategy, (V8ApexStrategy, V11HybridStrategy)):
        strategy.cfg.rsi_method = args.rsi_method
        strategy.cfg.emergency_ref = args.emergency_ref

    cost = SCENARIOS[args.scenario]
    print(f"Strategy: {strategy.name()}  |  Scenario: {args.scenario} "
          f"({cost.round_trip_bps:.0f} bps RT)")

    entry_nav_pre_cost = args.emergency_ref != "post_cost"
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=cost,
        initial_cash=args.initial_cash,
        dump_mtf_map=args.dump_mtf_map,
        entry_nav_pre_cost=entry_nav_pre_cost,
        warmup_mode=args.warmup_mode,
    )

    print("Running backtest ...")
    result = engine.run()

    out = _write_outputs(result, args.outdir)

    # Stamp run metadata
    config_snap: dict[str, Any] = {
        "strategy": args.strategy,
        "scenario": args.scenario,
        "cost": dataclasses.asdict(cost),
        "initial_cash": args.initial_cash,
        "warmup_days": args.warmup_days,
        "warmup_mode": args.warmup_mode,
        "rsi_method": args.rsi_method,
        "emergency_ref": args.emergency_ref,
    }
    if args.config:
        config_snap["config_file"] = args.config
        config_snap["config"] = config_dict
    if isinstance(strategy, V11HybridStrategy):
        config_snap["v11_hybrid"] = dataclasses.asdict(strategy.cfg)
    elif isinstance(strategy, V8ApexStrategy):
        config_snap["v8_apex"] = dataclasses.asdict(strategy.cfg)
    stamp_run_meta(
        args.outdir, argv=sys.argv, config=config_snap, data_path=args.data,
    )

    print(f"Results written to {out}/")

    _print_summary(result.summary)

    if args.dump_mtf_map and engine.mtf_map:
        print(f"\n{'─' * 60}")
        print("  MTF Alignment Map (h4_close -> d1_close_used)")
        print(f"{'─' * 60}")
        for h4_ct, d1_ct in engine.mtf_map:
            d1_str = str(d1_ct) if d1_ct is not None else "N/A (no D1 yet)"
            print(f"  {h4_ct}  ->  {d1_str}")


if __name__ == "__main__":
    main()
