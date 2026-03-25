"""Backtest suite: full-period candidate vs baseline across scenarios."""

from __future__ import annotations

import time
from pathlib import Path

from v10.core.engine import BacktestEngine
from v10.research.objective import OBJECTIVE_TERM_ORDER
from v10.research.objective import compute_objective_breakdown
from validation.output import write_csv, write_json
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult
from validation.suites.common import scenario_costs
from validation.thresholds import HARSH_SCORE_TOLERANCE


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_add_throttle_stats(summary: dict[str, object]) -> dict[str, float | int]:
    raw = summary.get("add_throttle_stats", {})
    if not isinstance(raw, dict):
        raw = {}

    attempts = _safe_int(raw.get("add_attempt_count"), default=0)
    blocked = _safe_int(raw.get("add_blocked_count"), default=0)
    return {
        "add_throttle_dd1": _safe_float(raw.get("add_throttle_dd1"), default=0.0),
        "add_throttle_dd2": _safe_float(raw.get("add_throttle_dd2"), default=0.0),
        "add_throttle_mult": _safe_float(raw.get("add_throttle_mult"), default=0.0),
        "add_attempt_count": attempts,
        "add_allowed_count": _safe_int(raw.get("add_allowed_count"), default=0),
        "add_blocked_count": blocked,
        "throttle_activation_rate": _safe_float(
            raw.get("throttle_activation_rate"),
            default=(blocked / max(attempts, 1)),
        ),
        "mean_dd_depth_when_blocked": _safe_float(raw.get("mean_dd_depth_when_blocked"), default=0.0),
        "p90_dd_depth_when_blocked": _safe_float(raw.get("p90_dd_depth_when_blocked"), default=0.0),
    }


class BacktestSuite(BaseSuite):
    def name(self) -> str:
        return "backtest"

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        artifacts: list[Path] = []

        costs = scenario_costs(ctx)
        rows: list[dict] = []
        score_breakdown_rows: list[dict[str, float | str]] = []
        detail: dict[str, dict[str, dict]] = {"candidate": {}, "baseline": {}}
        add_throttle_stats: dict[str, dict[str, dict[str, float | int]]] = {
            "candidate": {},
            "baseline": {},
        }

        for label, factory in [
            ("candidate", ctx.candidate_factory),
            ("baseline", ctx.baseline_factory),
        ]:
            for scenario_name in ctx.validation_config.scenarios:
                cost = costs.get(scenario_name)
                if cost is None:
                    continue

                ctx.logger.info("  backtest: %s x %s", label, scenario_name)
                engine = BacktestEngine(
                    feed=ctx.feed,
                    strategy=factory(),
                    cost=cost,
                    initial_cash=ctx.validation_config.initial_cash,
                    warmup_days=ctx.validation_config.warmup_days,
                )
                result = engine.run()
                ctx.backtest_cache[(label, scenario_name)] = result

                summary = dict(result.summary)
                breakdown = compute_objective_breakdown(summary)
                score = breakdown.total_score
                summary.update(
                    {
                        "label": label,
                        "scenario": scenario_name,
                        "score": round(score, 4),
                    }
                )
                rows.append(summary)
                detail[label][scenario_name] = summary
                add_throttle_stats[label][scenario_name] = _normalize_add_throttle_stats(summary)

                components = dict(breakdown.components)
                residual = float(score) - sum(float(components[name]) for name in OBJECTIVE_TERM_ORDER)
                row = {
                    "scenario": scenario_name,
                    "model": label,
                    "total_score": float(score),
                    **{name: float(components[name]) for name in OBJECTIVE_TERM_ORDER},
                    "residual": float(residual),
                }
                score_breakdown_rows.append(row)

        fieldnames = [
            "label",
            "scenario",
            "score",
            "cagr_pct",
            "max_drawdown_mid_pct",
            "sharpe",
            "sortino",
            "calmar",
            "profit_factor",
            "win_rate_pct",
            "trades",
            "avg_trade_pnl",
            "fees_total",
            "fee_drag_pct_per_year",
            "turnover_per_year",
            "avg_exposure",
            "time_in_market_pct",
            "total_return_pct",
            "initial_cash",
            "final_nav_mid",
        ]

        csv_path = write_csv(
            rows,
            ctx.results_dir / "full_backtest_summary.csv",
            fieldnames=fieldnames,
        )
        artifacts.append(csv_path)

        json_path = write_json(detail, ctx.results_dir / "full_backtest_detail.json")
        artifacts.append(json_path)

        add_throttle_path = write_json(
            add_throttle_stats,
            ctx.results_dir / "add_throttle_stats.json",
        )
        artifacts.append(add_throttle_path)

        score_breakdown_fieldnames = [
            "scenario",
            "model",
            "total_score",
            *OBJECTIVE_TERM_ORDER,
            "residual",
        ]
        score_breakdown_path = write_csv(
            score_breakdown_rows,
            ctx.results_dir / "score_breakdown_full.csv",
            fieldnames=score_breakdown_fieldnames,
        )
        artifacts.append(score_breakdown_path)

        deltas: dict[str, dict[str, float]] = {}
        for scenario_name in ctx.validation_config.scenarios:
            cand = detail.get("candidate", {}).get(scenario_name)
            base = detail.get("baseline", {}).get(scenario_name)
            if not cand or not base:
                continue
            deltas[scenario_name] = {
                "score_delta": round(float(cand.get("score", 0)) - float(base.get("score", 0)), 4),
                "cagr_delta": round(float(cand.get("cagr_pct", 0)) - float(base.get("cagr_pct", 0)), 4),
                "mdd_delta": round(
                    float(cand.get("max_drawdown_mid_pct", 0)) - float(base.get("max_drawdown_mid_pct", 0)),
                    4,
                ),
                "sharpe_delta": round(
                    float(cand.get("sharpe") or 0.0) - float(base.get("sharpe") or 0.0),
                    6,
                ),
            }

        harsh_delta = deltas.get("harsh", {}).get("score_delta", 0.0)
        tolerance = -HARSH_SCORE_TOLERANCE
        status = "pass" if harsh_delta >= tolerance else "fail"

        return SuiteResult(
            name=self.name(),
            status=status,
            data={
                "rows": rows,
                "detail": detail,
                "deltas": deltas,
                "score_breakdown_rows": score_breakdown_rows,
                "add_throttle_stats": add_throttle_stats,
            },
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
