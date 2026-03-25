"""Bootstrap suite: paired block bootstrap for candidate vs baseline."""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from v10.research.bootstrap import paired_block_bootstrap
from validation.output import write_csv, write_json
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult
from validation.suites.common import ensure_backtest


class BootstrapSuite(BaseSuite):
    def name(self) -> str:
        return "bootstrap"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if ctx.validation_config.bootstrap <= 0:
            return "bootstrap disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        rows: list[dict] = []
        for scenario in ctx.validation_config.scenarios:
            if scenario not in {"harsh", "base", "smart"}:
                continue
            candidate = ensure_backtest(ctx, "candidate", scenario)
            baseline = ensure_backtest(ctx, "baseline", scenario)

            if not candidate.equity or not baseline.equity:
                continue

            for block_size in cfg.bootstrap_block_sizes:
                try:
                    result = paired_block_bootstrap(
                        equity_a=candidate.equity,
                        equity_b=baseline.equity,
                        n_bootstrap=cfg.bootstrap,
                        block_size=block_size,
                        seed=cfg.seed,
                    )
                except ValueError as exc:
                    ctx.logger.warning(
                        "bootstrap skipped for scenario=%s block=%s: %s",
                        scenario,
                        block_size,
                        exc,
                    )
                    continue

                row = asdict(result)
                row["scenario"] = scenario
                rows.append(row)

        csv_path = write_csv(rows, ctx.results_dir / "bootstrap_paired_test.csv")
        artifacts.append(csv_path)

        gate = {}
        harsh_primary = next(
            (
                row
                for row in rows
                if row.get("scenario") == "harsh"
                and row.get("block_size") == cfg.bootstrap_block_sizes[0]
            ),
            None,
        )
        if harsh_primary is None:
            harsh_primary = next((row for row in rows if row.get("scenario") == "harsh"), None)
        if harsh_primary is None and rows:
            harsh_primary = rows[0]

        if harsh_primary is not None:
            gate = {
                "scenario": harsh_primary.get("scenario"),
                "block_size": harsh_primary.get("block_size"),
                # Directional resampling score, NOT a p-value (Report 21, U1).
                "p_candidate_better": harsh_primary.get("p_a_better"),
                "ci_lower": harsh_primary.get("ci_lower"),
                "ci_upper": harsh_primary.get("ci_upper"),
                "observed_delta": harsh_primary.get("observed_delta"),
            }

        summary = {
            "n_rows": len(rows),
            "bootstrap": cfg.bootstrap,
            "seed": cfg.seed,
            "gate": gate,
        }

        json_path = write_json(summary, ctx.results_dir / "bootstrap_summary.json")
        artifacts.append(json_path)

        # Bootstrap is a DIAGNOSTIC, not a gate (Report 21, §1.1; Report 22B, Phase 3).
        # Gate dict is still populated for diagnostic consumption, but status is always "info".
        status = "info"

        return SuiteResult(
            name=self.name(),
            status=status,
            data={"rows": rows, "gate": gate, "summary": summary},
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
