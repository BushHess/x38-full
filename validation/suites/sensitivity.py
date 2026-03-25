"""Sensitivity suite using configured aggr/trail/cap grids."""

from __future__ import annotations

import itertools
import time
from pathlib import Path

from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from validation.output import write_csv, write_json
from validation.strategy_factory import STRATEGY_REGISTRY, _build_config_obj
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult
from validation.suites.common import scenario_costs


_FIELD_MAP = {
    "aggr": [
        "entry_aggression",
        "cycle_late_aggression",
        "aggression",
    ],
    "trail": [
        "trail_atr_mult",
        "cycle_late_trail_mult",
        "trail_mult",
        "trail_tight",
    ],
    "cap": [
        "max_total_exposure",
        "cycle_late_max_exposure",
        "late_bull_max_exposure",
    ],
}


def _pick_field(config_obj: object | None, candidates: list[str]) -> str | None:
    if config_obj is None:
        return None
    for field in candidates:
        if hasattr(config_obj, field):
            return field
    return None


def _build_strategy_with_overrides(ctx: SuiteContext, overrides: dict[str, float]):
    strategy_name = ctx.candidate_live_config.strategy.name
    params = dict(ctx.candidate_live_config.strategy.params)
    params.update(overrides)

    config_obj = _build_config_obj(strategy_name, params)
    strategy_cls = STRATEGY_REGISTRY[strategy_name][0]
    if config_obj is None:
        return strategy_cls()
    return strategy_cls(config_obj)


class SensitivitySuite(BaseSuite):
    def name(self) -> str:
        return "sensitivity"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if not ctx.validation_config.sensitivity_grid:
            return "sensitivity grid disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        aggr_field = _pick_field(ctx.candidate_config_obj, _FIELD_MAP["aggr"])
        trail_field = _pick_field(ctx.candidate_config_obj, _FIELD_MAP["trail"])
        cap_field = _pick_field(ctx.candidate_config_obj, _FIELD_MAP["cap"])

        grid: dict[str, list[float]] = {}
        if aggr_field is not None:
            grid[aggr_field] = list(cfg.grid_aggr)
        if trail_field is not None:
            grid[trail_field] = list(cfg.grid_trail)
        if cap_field is not None:
            grid[cap_field] = list(cfg.grid_cap)

        if not grid:
            return SuiteResult(
                name=self.name(),
                status="skip",
                data={"reason": "no compatible sensitivity fields found"},
                duration_seconds=time.time() - t0,
            )

        param_names = list(grid.keys())
        combos = list(itertools.product(*(grid[name] for name in param_names)))

        costs = scenario_costs(ctx)
        scenario = "harsh" if "harsh" in costs else next(iter(costs.keys()), "base")
        cost = costs.get(scenario, SCENARIOS["base"])

        base_engine = BacktestEngine(
            feed=ctx.feed,
            strategy=ctx.candidate_factory(),
            cost=cost,
            initial_cash=cfg.initial_cash,
            warmup_days=cfg.warmup_days,
        )
        base_result = base_engine.run()
        base_score = compute_objective(base_result.summary)

        rows: list[dict] = []
        for combo in combos:
            overrides = dict(zip(param_names, combo))
            strategy = _build_strategy_with_overrides(ctx, overrides)

            engine = BacktestEngine(
                feed=ctx.feed,
                strategy=strategy,
                cost=cost,
                initial_cash=cfg.initial_cash,
                warmup_days=cfg.warmup_days,
            )
            result = engine.run()
            summary = result.summary
            score = compute_objective(summary)

            row = {**overrides}
            row.update(
                {
                    "scenario": scenario,
                    "score": round(float(score), 4),
                    "delta_vs_default": round(float(score - base_score), 4),
                    "cagr_pct": round(float(summary.get("cagr_pct", 0.0)), 4),
                    "max_drawdown_mid_pct": round(float(summary.get("max_drawdown_mid_pct", 0.0)), 4),
                    "sharpe": round(float(summary.get("sharpe") or 0.0), 6),
                    "trades": int(summary.get("trades", 0)),
                }
            )
            rows.append(row)

        fieldnames = param_names + [
            "scenario",
            "score",
            "delta_vs_default",
            "cagr_pct",
            "max_drawdown_mid_pct",
            "sharpe",
            "trades",
        ]

        csv_path = write_csv(rows, ctx.results_dir / "sensitivity_grid.csv", fieldnames)
        artifacts.append(csv_path)

        summary = {
            "grid": grid,
            "scenario": scenario,
            "n_points": len(rows),
            "default_score": round(float(base_score), 4),
            "min_score": round(min(float(r["score"]) for r in rows), 4),
            "max_score": round(max(float(r["score"]) for r in rows), 4),
        }
        json_path = write_json(
            {"summary": summary, "rows": rows},
            ctx.results_dir / "sensitivity_detail.json",
        )
        artifacts.append(json_path)

        return SuiteResult(
            name=self.name(),
            status="info",
            data={"summary": summary, "rows": rows},
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
