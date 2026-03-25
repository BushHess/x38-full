"""Drawdown episode suite."""

from __future__ import annotations

import time
from pathlib import Path

from v10.research.drawdown import detect_drawdown_episodes, recovery_table
from validation.output import write_csv, write_json
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult
from validation.suites.common import ensure_backtest


class DDEpisodesSuite(BaseSuite):
    def name(self) -> str:
        return "dd_episodes"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        cfg = ctx.validation_config
        if not cfg.dd_episodes and cfg.suite not in {"dd", "all"}:
            return "dd-episodes disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        artifacts: list[Path] = []

        scenario = "harsh" if "harsh" in ctx.validation_config.scenarios else "base"
        summary: dict[str, dict] = {}

        for label in ["candidate", "baseline"]:
            result = ensure_backtest(ctx, label, scenario)
            episodes = detect_drawdown_episodes(result.equity or [], min_dd_pct=5.0)
            rows = recovery_table(episodes)

            fieldnames = [
                "peak_date",
                "peak_nav",
                "trough_date",
                "trough_nav",
                "recovery_date",
                "drawdown_pct",
                "bars_to_trough",
                "bars_to_recovery",
                "days_to_trough",
                "days_to_recovery",
            ]
            csv_path = write_csv(
                rows,
                ctx.results_dir / f"dd_episodes_{label}.csv",
                fieldnames=fieldnames,
            )
            artifacts.append(csv_path)

            dd_values = [float(ep.drawdown_pct) for ep in episodes]
            summary[label] = {
                "scenario": scenario,
                "n_episodes": len(episodes),
                "worst_dd_pct": round(max(dd_values), 6) if dd_values else 0.0,
                "mean_dd_pct": round(sum(dd_values) / len(dd_values), 6) if dd_values else 0.0,
            }

        json_path = write_json(summary, ctx.results_dir / "dd_episodes_summary.json")
        artifacts.append(json_path)

        return SuiteResult(
            name=self.name(),
            status="info",
            data=summary,
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
