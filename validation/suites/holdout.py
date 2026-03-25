"""Holdout suite with lock-file enforcement."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.research.objective import OBJECTIVE_TERM_ORDER
from v10.research.objective import compute_objective_breakdown
from validation.output import write_csv, write_json
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult
from validation.suites.common import scenario_costs
from validation.thresholds import HARSH_SCORE_TOLERANCE


def _resolve_holdout_window(cfg) -> tuple[str, str]:
    has_start = bool(cfg.holdout_start)
    has_end = bool(cfg.holdout_end)

    if has_start != has_end:
        raise ValueError(
            f"holdout_start and holdout_end must both be set or both be None; "
            f"got holdout_start={cfg.holdout_start!r}, holdout_end={cfg.holdout_end!r}"
        )

    start = date.fromisoformat(cfg.start)
    end = date.fromisoformat(cfg.end)

    if has_start and has_end:
        h_start = date.fromisoformat(cfg.holdout_start)
        h_end = date.fromisoformat(cfg.holdout_end)
        if h_start > h_end:
            raise ValueError(
                f"holdout_start ({cfg.holdout_start}) > holdout_end ({cfg.holdout_end})"
            )
        if h_start < start or h_end > end:
            raise ValueError(
                f"holdout window [{cfg.holdout_start}, {cfg.holdout_end}] "
                f"outside data range [{cfg.start}, {cfg.end}]"
            )
        return cfg.holdout_start, cfg.holdout_end

    frac = cfg.holdout_frac
    if not (0.0 < frac <= 1.0):
        raise ValueError(
            f"holdout_frac must be in (0, 1], got {frac}"
        )

    # +1 for inclusive end date (DataFeed end is inclusive, see data.py line 78)
    total_days = max((end - start).days + 1, 1)
    holdout_days = max(int(total_days * frac), 1)
    # -1 because end is inclusive: e.g. holdout_days=2 from end=Jan-10
    # → Jan-09..Jan-10 (2 days), not Jan-08..Jan-10 (3 days).
    holdout_start = end - timedelta(days=holdout_days - 1)
    if holdout_start < start:
        raise ValueError(
            f"holdout_frac={frac} produces holdout_start={holdout_start.isoformat()} "
            f"before data start={cfg.start}"
        )
    return holdout_start.isoformat(), end.isoformat()


class HoldoutSuite(BaseSuite):
    def name(self) -> str:
        return "holdout"

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        lock_path = ctx.results_dir / "holdout_lock.json"
        if lock_path.exists() and not cfg.force_holdout:
            return SuiteResult(
                name=self.name(),
                status="error",
                error_message=(
                    "holdout lock exists; rerun blocked unless --force-holdout is set"
                ),
                data={"lock_path": str(lock_path)},
                duration_seconds=time.time() - t0,
            )

        holdout_start, holdout_end = _resolve_holdout_window(cfg)
        feed = DataFeed(
            str(ctx.data_path),
            start=holdout_start,
            end=holdout_end,
            warmup_days=cfg.warmup_days,
        )

        costs = scenario_costs(ctx)
        rows: list[dict] = []
        score_breakdown_rows: list[dict[str, float | str]] = []
        detail: dict[str, dict[str, dict]] = {"candidate": {}, "baseline": {}}

        for label, factory in [
            ("candidate", ctx.candidate_factory),
            ("baseline", ctx.baseline_factory),
        ]:
            for scenario in cfg.scenarios:
                cost = costs.get(scenario)
                if cost is None:
                    continue

                engine = BacktestEngine(
                    feed=feed,
                    strategy=factory(),
                    cost=cost,
                    initial_cash=cfg.initial_cash,
                    warmup_days=cfg.warmup_days,
                )
                result = engine.run()
                summary = dict(result.summary)
                breakdown = compute_objective_breakdown(summary)
                score = breakdown.total_score

                summary.update(
                    {
                        "label": label,
                        "scenario": scenario,
                        "score": round(float(score), 4),
                    }
                )
                rows.append(summary)
                detail[label][scenario] = summary

                components = dict(breakdown.components)
                residual = float(score) - sum(float(components[name]) for name in OBJECTIVE_TERM_ORDER)
                score_breakdown_rows.append(
                    {
                        "scenario": scenario,
                        "model": label,
                        "total_score": float(score),
                        **{name: float(components[name]) for name in OBJECTIVE_TERM_ORDER},
                        "residual": float(residual),
                    }
                )

        fieldnames = [
            "label",
            "scenario",
            "score",
            "cagr_pct",
            "max_drawdown_mid_pct",
            "sharpe",
            "sortino",
            "calmar",
            "trades",
            "win_rate_pct",
            "profit_factor",
            "total_return_pct",
        ]

        csv_path = write_csv(
            rows,
            ctx.results_dir / "final_holdout_metrics.csv",
            fieldnames=fieldnames,
        )
        artifacts.append(csv_path)

        score_breakdown_fieldnames = [
            "scenario",
            "model",
            "total_score",
            *OBJECTIVE_TERM_ORDER,
            "residual",
        ]
        score_breakdown_path = write_csv(
            score_breakdown_rows,
            ctx.results_dir / "score_breakdown_holdout.csv",
            fieldnames=score_breakdown_fieldnames,
        )
        artifacts.append(score_breakdown_path)

        detail_path = write_json(
            {
                "holdout_start": holdout_start,
                "holdout_end": holdout_end,
                "detail": detail,
            },
            ctx.results_dir / "holdout_detail.json",
        )
        artifacts.append(detail_path)

        # Verify harsh scenario data exists before computing verdict.
        # Without harsh, the delta defaults to 0.0 which falsely passes.
        candidate_harsh_data = detail.get("candidate", {}).get("harsh")
        baseline_harsh_data = detail.get("baseline", {}).get("harsh")
        if candidate_harsh_data is None or baseline_harsh_data is None:
            return SuiteResult(
                name=self.name(),
                status="error",
                error_message=(
                    "holdout requires 'harsh' scenario but it is missing from results; "
                    "ensure --scenarios includes 'harsh'"
                ),
                data={
                    "holdout_start": holdout_start,
                    "holdout_end": holdout_end,
                    "detail": detail,
                    "score_breakdown_rows": score_breakdown_rows,
                },
                artifacts=artifacts,
                duration_seconds=time.time() - t0,
            )

        candidate_harsh = float(candidate_harsh_data.get("score", 0.0))
        baseline_harsh = float(baseline_harsh_data.get("score", 0.0))
        delta = round(candidate_harsh - baseline_harsh, 4)

        status = "pass" if delta >= -HARSH_SCORE_TOLERANCE else "fail"

        # Write lock AFTER successful verdict computation.
        # Previously, lock was written before verdict, so a false-pass
        # (e.g. missing harsh → delta=0.0) would still lock the holdout.
        lock_payload = {
            "holdout_start": holdout_start,
            "holdout_end": holdout_end,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_json(lock_payload, lock_path)
        artifacts.append(lock_path)

        return SuiteResult(
            name=self.name(),
            status=status,
            data={
                "holdout_start": holdout_start,
                "holdout_end": holdout_end,
                "candidate_harsh_score": round(candidate_harsh, 4),
                "baseline_harsh_score": round(baseline_harsh, 4),
                "delta_harsh_score": delta,
                "detail": detail,
                "score_breakdown_rows": score_breakdown_rows,
            },
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
