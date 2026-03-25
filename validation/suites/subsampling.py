"""Subsampling suite — paired block subsampling for candidate vs baseline.

Runs alongside bootstrap to provide a complementary, non-resampling-based
inference method (Politis, Romano & Wolf, 1999).  Unlike circular block
bootstrap, subsampling uses overlapping sub-blocks of the *original* data
and is deterministic (no random seed required).
"""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path

from v10.research.subsampling import paired_block_subsampling
from v10.research.subsampling import summarize_block_grid

from validation.output import write_csv
from validation.output import write_json
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.common import ensure_backtest


class SubsamplingSuite(BaseSuite):
    def name(self) -> str:
        return "subsampling"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if not ctx.validation_config.subsampling:
            return "subsampling disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        ci_level = cfg.subsampling_ci_level
        max_subsamples = cfg.subsampling_max_blocks
        if max_subsamples <= 0:
            max_subsamples = None

        p_threshold = cfg.subsampling_p_threshold
        ci_lower_threshold = cfg.subsampling_ci_lower_threshold
        support_ratio_threshold = cfg.subsampling_support_ratio_threshold

        rows: list[dict] = []
        scenario_summaries: dict[str, dict] = {}

        for scenario in cfg.scenarios:
            if scenario not in {"harsh", "base", "smart"}:
                continue
            candidate = ensure_backtest(ctx, "candidate", scenario)
            baseline = ensure_backtest(ctx, "baseline", scenario)
            if not candidate.equity or not baseline.equity:
                continue

            scenario_results = []
            for block_size in cfg.bootstrap_block_sizes:
                try:
                    result = paired_block_subsampling(
                        equity_a=candidate.equity,
                        equity_b=baseline.equity,
                        block_size=int(block_size),
                        ci_level=ci_level,
                        max_subsamples=max_subsamples,
                    )
                except ValueError as exc:
                    ctx.logger.warning(
                        "subsampling skipped for scenario=%s block=%s: %s",
                        scenario,
                        block_size,
                        exc,
                    )
                    continue

                scenario_results.append(result)
                row = asdict(result)
                row["scenario"] = scenario
                rows.append(row)

            if scenario_results:
                summary = summarize_block_grid(
                    scenario_results,
                    p_threshold=p_threshold,
                    ci_lower_threshold=ci_lower_threshold,
                    support_ratio_threshold=support_ratio_threshold,
                )
                scenario_summaries[scenario] = asdict(summary)

        csv_path = write_csv(rows, ctx.results_dir / "subsampling_paired_test.csv")
        artifacts.append(csv_path)

        gate: dict[str, object] = {}
        chosen_scenario = None
        for preferred in ("harsh", "base", "smart"):
            if preferred in scenario_summaries:
                chosen_scenario = preferred
                break

        if chosen_scenario is not None:
            chosen = scenario_summaries[chosen_scenario]
            gate = {
                "method": "paired_block_subsampling",
                "statistic_name": chosen.get("statistic_name"),
                "scenario": chosen_scenario,
                "gate_mode": chosen.get("gate_mode"),
                "block_sizes": chosen.get("block_sizes"),
                "n_block_sizes": chosen.get("n_block_sizes"),
                # Subsampling directional score. NOT a posterior probability.
                # Miscalibrated when differential series has high near-equality rate
                # (Report 19, §4; Report 21, U5).
                "p_candidate_better": chosen.get("median_p_a_better"),
                "ci_lower": chosen.get("median_ci_lower"),
                "ci_upper": chosen.get("median_ci_upper"),
                "observed_delta": chosen.get("median_observed_delta"),
                "support_ratio": chosen.get("support_ratio"),
                "min_ci_lower": chosen.get("min_ci_lower"),
                "min_p_candidate_better": chosen.get("min_p_a_better"),
                "decision_pass": chosen.get("decision_pass"),
                "thresholds": {
                    "p_threshold": p_threshold,
                    "ci_lower_threshold": ci_lower_threshold,
                    "support_ratio_threshold": support_ratio_threshold,
                },
            }

        summary = {
            "method": "paired_block_subsampling",
            "n_rows": len(rows),
            "ci_level": ci_level,
            "max_subsamples": max_subsamples,
            "scenario_summaries": scenario_summaries,
            "gate": gate,
        }

        json_path = write_json(summary, ctx.results_dir / "subsampling_summary.json")
        artifacts.append(json_path)

        # Subsampling is a DIAGNOSTIC, not a gate (Report 21, §1.1; Report 22B, Phase 3B).
        # Gate dict is still populated for diagnostic consumption, but status is always "info".
        status = "info"

        return SuiteResult(
            name=self.name(),
            status=status,
            data={"rows": rows, "gate": gate, "summary": summary},
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
