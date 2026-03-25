"""Common helpers shared across validation suites."""

from __future__ import annotations

from datetime import datetime, timezone

from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, CostConfig
from validation.suites.base import SuiteContext


def scenario_costs(ctx: SuiteContext) -> dict[str, CostConfig]:
    cfg = ctx.validation_config
    costs: dict[str, CostConfig] = {}

    for scenario in cfg.scenarios:
        if scenario in SCENARIOS:
            costs[scenario] = SCENARIOS[scenario]

    if "harsh" in costs:
        base = SCENARIOS["harsh"]
        if abs(cfg.harsh_cost_bps - base.round_trip_bps) > 1e-9:
            scale = cfg.harsh_cost_bps / base.round_trip_bps
            costs["harsh"] = CostConfig(
                spread_bps=base.spread_bps * scale,
                slippage_bps=base.slippage_bps * scale,
                taker_fee_pct=base.taker_fee_pct * scale,
            )

    return costs


def ensure_backtest(ctx: SuiteContext, label: str, scenario: str):
    key = (label, scenario)
    if key in ctx.backtest_cache:
        return ctx.backtest_cache[key]

    costs = scenario_costs(ctx)
    cost = costs.get(scenario, SCENARIOS["base"])
    factory = ctx.candidate_factory if label == "candidate" else ctx.baseline_factory

    engine = BacktestEngine(
        feed=ctx.feed,
        strategy=factory(),
        cost=cost,
        initial_cash=ctx.validation_config.initial_cash,
        warmup_days=ctx.validation_config.warmup_days,
    )
    result = engine.run()
    ctx.backtest_cache[key] = result
    return result


def iso_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)
