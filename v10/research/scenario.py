"""Scenario runner — execute a strategy across smart / base / harsh cost scenarios.

Usage:
    from v10.research.scenario import run_scenarios
    results = run_scenarios(feed, strategy_cls, initial_cash=10_000)
    for name, result in results.items():
        print(name, result.summary["cagr_pct"])
"""

from __future__ import annotations

from typing import Type

from v10.core.types import SCENARIOS, BacktestResult, CostConfig
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.strategies.base import Strategy


def run_scenarios(
    feed: DataFeed,
    strategy_factory: callable,
    initial_cash: float = 10_000.0,
    warmup_days: int = 365,
    scenarios: dict[str, CostConfig] | None = None,
) -> dict[str, BacktestResult]:
    """Run the same strategy under multiple cost scenarios.

    Parameters
    ----------
    feed : DataFeed
        Pre-loaded market data.
    strategy_factory : callable
        A zero-argument callable that returns a fresh Strategy instance.
        Must be a factory (not an instance) because each run needs its own state.
    initial_cash : float
        Starting capital.
    warmup_days : int
        Warmup period for the engine.
    scenarios : dict | None
        Override scenarios.  Defaults to SCENARIOS (smart/base/harsh).

    Returns
    -------
    dict mapping scenario name -> BacktestResult
    """
    if scenarios is None:
        scenarios = SCENARIOS

    results: dict[str, BacktestResult] = {}

    for name, cost in scenarios.items():
        strategy = strategy_factory()
        engine = BacktestEngine(
            feed=feed,
            strategy=strategy,
            cost=cost,
            initial_cash=initial_cash,
            warmup_days=warmup_days,
        )
        results[name] = engine.run()

    return results


def print_scenario_comparison(results: dict[str, BacktestResult]) -> None:
    """Print a side-by-side comparison table of scenario results."""
    header = f"{'Metric':<26}"
    for name in results:
        header += f"  {name:>12}"
    print(header)
    print("-" * len(header))

    keys = [
        ("cagr_pct", "CAGR %"),
        ("max_drawdown_mid_pct", "Max DD %"),
        ("sharpe", "Sharpe"),
        ("sortino", "Sortino"),
        ("calmar", "Calmar"),
        ("profit_factor", "Profit Factor"),
        ("win_rate_pct", "Win Rate %"),
        ("avg_trade_pnl", "Avg Trade PnL"),
        ("trades", "Trades"),
        ("fees_total", "Total Fees"),
        ("fee_drag_pct_per_year", "Fee Drag %/yr"),
        ("turnover_per_year", "Turnover/yr"),
        ("avg_exposure", "Avg Exposure"),
        ("time_in_market_pct", "Time in Market %"),
    ]

    for key, label in keys:
        row = f"{label:<26}"
        for name, result in results.items():
            val = result.summary.get(key, "N/A")
            if isinstance(val, float):
                row += f"  {val:>12.2f}"
            elif isinstance(val, int):
                row += f"  {val:>12d}"
            else:
                row += f"  {str(val):>12}"
        print(row)
