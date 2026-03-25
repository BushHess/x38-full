"""Validation runner orchestrating all suites and output contracts."""

from __future__ import annotations

import dataclasses
import logging
import shutil
import time
from pathlib import Path
from typing import Any

from v10.core.config import load_config
from v10.core.data import DataFeed
from v10.core.meta import get_git_hash
from v10.core.meta import stamp_run_meta

from validation.config import ValidationConfig
from validation.config import resolve_suites
from validation.config_audit import build_effective_config_payload
from validation.config_audit import build_effective_config_report
from validation.config_audit import build_usage_payloads
from validation.config_audit import load_raw_yaml
from validation.config_audit import tracker_for_config_obj
from validation.decision import DecisionVerdict
from validation.decision import _as_dict
from validation.decision import _as_list_of_dicts
from validation.decision import _safe_int
from validation.decision import _strict_bool
from validation.decision import evaluate_decision
from validation.discovery import discover_checks
from validation.discovery import write_discovered_tests_report
from validation.output import copy_configs
from validation.output import write_decision_json
from validation.output import write_index
from validation.output import write_json
from validation.output import write_text
from validation.report import generate_quality_checks_report
from validation.report import generate_validation_report
from validation.score_decomposition import build_score_decomposition_report
from validation.strategy_factory import _build_config_obj
from validation.strategy_factory import make_factory
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult

_SUITE_CLASSES: dict[str, str] = {
    "lookahead": "validation.suites.lookahead.LookaheadSuite",
    "backtest": "validation.suites.backtest.BacktestSuite",
    "regime": "validation.suites.regime.RegimeSuite",
    "wfo": "validation.suites.wfo.WFOSuite",
    "bootstrap": "validation.suites.bootstrap.BootstrapSuite",
    "subsampling": "validation.suites.subsampling.SubsamplingSuite",
    "sensitivity": "validation.suites.sensitivity.SensitivitySuite",
    "holdout": "validation.suites.holdout.HoldoutSuite",
    "selection_bias": "validation.suites.selection_bias.SelectionBiasSuite",
    "trade_level": "validation.suites.trade_level.TradeLevelSuite",
    "dd_episodes": "validation.suites.dd_episodes.DDEpisodesSuite",
    "overlay": "validation.suites.overlay.OverlaySuite",
    "data_integrity": "validation.suites.data_integrity.DataIntegritySuite",
    "cost_sweep": "validation.suites.cost_sweep.CostSweepSuite",
    "invariants": "validation.suites.invariants.InvariantsSuite",
    "regression_guard": "validation.suites.regression_guard.RegressionGuardSuite",
    "churn_metrics": "validation.suites.churn_metrics.ChurnMetricsSuite",
}


def _import_suite(dotted_path: str) -> type[BaseSuite]:
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class ValidationRunner:
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.logger = logging.getLogger("validation")

    def run(self) -> tuple[dict[str, SuiteResult], DecisionVerdict]:
        t0 = time.time()
        cfg = self.config
        project_root = Path.cwd()
        if not (project_root / "v10").exists():
            for parent in cfg.config_path.parents:
                if (parent / "v10").exists():
                    project_root = parent
                    break

        outdir = cfg.outdir
        if outdir.exists() and cfg.force:
            shutil.rmtree(outdir)

        outdir.mkdir(parents=True, exist_ok=True)
        logs_dir = outdir / "logs"
        results_dir = outdir / "results"
        reports_dir = outdir / "reports"
        for folder in [logs_dir, results_dir, reports_dir]:
            folder.mkdir(parents=True, exist_ok=True)

        log_path = logs_dir / "run.log"
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        self.logger.handlers.clear()
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.DEBUG)

        try:
            return self._run_inner(cfg, file_handler, t0, outdir, results_dir, reports_dir, project_root)
        finally:
            self.logger.removeHandler(file_handler)
            file_handler.close()

    def _run_inner(
        self,
        cfg: ValidationConfig,
        file_handler: logging.Handler,
        t0: float,
        outdir: Path,
        results_dir: Path,
        reports_dir: Path,
        project_root: Path,
    ) -> tuple[dict[str, SuiteResult], DecisionVerdict]:
        git_hash = get_git_hash()
        self.logger.info("Validation run started")
        self.logger.info("command=%s", " ".join(cfg.command))
        self.logger.info("seed=%s", cfg.seed)
        self.logger.info("git_hash=%s", git_hash)
        self.logger.info("candidate=%s config=%s", cfg.strategy_name, cfg.config_path)
        self.logger.info("baseline=%s config=%s", cfg.baseline_name, cfg.baseline_config_path)
        self.logger.info("dataset=%s", cfg.dataset)
        self.logger.info("period=%s -> %s", cfg.start, cfg.end)

        config_dict = dataclasses.asdict(cfg)
        for key, value in list(config_dict.items()):
            if isinstance(value, Path):
                config_dict[key] = str(value)

        stamp_run_meta(
            outdir,
            argv=cfg.command,
            config={**config_dict, "git_hash": git_hash},
            data_path=cfg.dataset,
        )

        copy_configs(cfg, outdir)

        # Load YAML configs and validate CLI labels BEFORE expensive data
        # loading.  This fails fast on mislabelling (CLI says strategy A
        # but YAML defines strategy B).
        candidate_live = load_config(str(cfg.config_path))
        baseline_live = load_config(str(cfg.baseline_config_path))

        if cfg.strategy_name != candidate_live.strategy.name:
            raise ValueError(
                f"CLI --strategy={cfg.strategy_name!r} does not match "
                f"candidate config strategy.name={candidate_live.strategy.name!r} "
                f"in {cfg.config_path.name}. "
                f"Fix the CLI argument or the YAML config."
            )
        if cfg.baseline_name != baseline_live.strategy.name:
            raise ValueError(
                f"CLI --baseline={cfg.baseline_name!r} does not match "
                f"baseline config strategy.name={baseline_live.strategy.name!r} "
                f"in {cfg.baseline_config_path.name}. "
                f"Fix the CLI argument or the YAML config."
            )

        try:
            feed = DataFeed(
                str(cfg.dataset),
                start=cfg.start,
                end=cfg.end,
                warmup_days=cfg.warmup_days,
            )
        except (KeyError, ValueError) as exc:
            error_msg = (
                f"DataFeed construction failed: {exc}. "
                f"This is a data schema error (e.g., missing 'interval' column), "
                f"not a pipeline bug. Fix the dataset CSV and re-run."
            )
            self.logger.error(error_msg)
            di_result = SuiteResult(
                name="data_integrity",
                status="fail",
                data={
                    "status": "fail",
                    "hard_fail": True,
                    "hard_fail_reasons": [
                        f"feed_construction_failed:{type(exc).__name__}:{exc}",
                    ],
                    "error": error_msg,
                },
            )
            decision = DecisionVerdict(
                tag="ERROR",
                exit_code=3,
                reasons=["DataFeed construction failed — data schema error"],
                failures=[f"data_schema:{type(exc).__name__}:{exc}"],
                errors=[error_msg],
            )
            schema_results: dict[str, SuiteResult] = {"data_integrity": di_result}
            write_decision_json(decision, outdir)
            return schema_results, decision

        candidate_config_obj = _build_config_obj(
            candidate_live.strategy.name,
            candidate_live.strategy.params,
        )
        baseline_config_obj = _build_config_obj(
            baseline_live.strategy.name,
            baseline_live.strategy.params,
        )
        candidate_tracker = tracker_for_config_obj(
            candidate_config_obj,
            label="candidate",
        )
        baseline_tracker = tracker_for_config_obj(
            baseline_config_obj,
            label="baseline",
        )

        candidate_factory = make_factory(candidate_live, access_tracker=candidate_tracker)
        baseline_factory = make_factory(baseline_live, access_tracker=baseline_tracker)

        raw_candidate_yaml = load_raw_yaml(cfg.config_path)
        raw_baseline_yaml = load_raw_yaml(cfg.baseline_config_path)

        effective_candidate = build_effective_config_payload(
            role="candidate",
            config_path=cfg.config_path,
            live_config=candidate_live,
            strategy_config_obj=candidate_config_obj,
            validation_config=cfg,
            raw_yaml=raw_candidate_yaml,
        )
        effective_baseline = build_effective_config_payload(
            role="baseline",
            config_path=cfg.baseline_config_path,
            live_config=baseline_live,
            strategy_config_obj=baseline_config_obj,
            validation_config=cfg,
            raw_yaml=raw_baseline_yaml,
        )

        write_json(effective_candidate, results_dir / "effective_config_candidate.json")
        write_json(effective_baseline, results_dir / "effective_config_baseline.json")

        suite_queue = resolve_suites(cfg)
        ctx = SuiteContext(
            feed=feed,
            data_path=cfg.dataset,
            project_root=project_root,
            candidate_factory=candidate_factory,
            baseline_factory=baseline_factory,
            candidate_live_config=candidate_live,
            baseline_live_config=baseline_live,
            candidate_config_obj=candidate_config_obj,
            baseline_config_obj=baseline_config_obj,
            validation_config=cfg,
            resolved_suites=suite_queue,
            outdir=outdir,
            results_dir=results_dir,
            reports_dir=reports_dir,
            logger=self.logger,
        )

        results: dict[str, SuiteResult] = {}

        i = 0
        while i < len(suite_queue):
            suite_name = suite_queue[i]
            i += 1

            dotted = _SUITE_CLASSES.get(suite_name)
            if dotted is None:
                results[suite_name] = SuiteResult(
                    name=suite_name,
                    status="error",
                    error_message=f"unknown suite: {suite_name}",
                )
                continue

            try:
                suite_cls = _import_suite(dotted)
                suite = suite_cls()
            except Exception as exc:
                results[suite_name] = SuiteResult(
                    name=suite_name,
                    status="error",
                    error_message=f"import failed: {exc}",
                )
                continue

            skip_reason = suite.skip_reason(ctx)
            if skip_reason:
                self.logger.info("suite %s skipped: %s", suite_name, skip_reason)
                results[suite_name] = SuiteResult(
                    name=suite_name,
                    status="skip",
                    data={"skip_reason": skip_reason},
                )
                continue

            try:
                self.logger.info("suite %s started", suite_name)
                result = suite.run(ctx)
                results[suite_name] = result
                self.logger.info(
                    "suite %s finished: %s (%.2fs)",
                    suite_name,
                    result.status,
                    result.duration_seconds,
                )
            except Exception as exc:
                self.logger.exception("suite %s crashed", suite_name)
                results[suite_name] = SuiteResult(
                    name=suite_name,
                    status="error",
                    error_message=str(exc),
                )
                continue

            if suite_name == "data_integrity":
                hard_fail = _strict_bool(_as_dict(result.data).get("hard_fail"))
                if result.status == "fail" and hard_fail:
                    warning = "Data integrity hard-fail detected; skipping remaining suites."
                    ctx.run_warnings.append(warning)
                    self.logger.error(warning)
                    break

            # Acceptance rule E: low-power WFO auto-enables trade-level inference.
            if suite_name == "wfo":
                summary = _as_dict(_as_dict(result.data).get("summary"))
                power_stats = _as_dict(summary.get("stats_power_only"))
                power_windows = _safe_int(power_stats.get("n_windows", 0))
                low_trade_windows = _safe_int(
                    summary.get("low_trade_windows_count", summary.get("low_trade_windows", 0))
                )
                valid_windows = _safe_int(summary.get("n_windows_valid", summary.get("n_windows", 0)))
                low_trade_ratio = (
                    (low_trade_windows / valid_windows)
                    if valid_windows > 0
                    else 1.0
                )
                low_power = power_windows < 3 or low_trade_ratio > 0.5

                if low_power:
                    low_power_warning = (
                        "Low-power WFO detected "
                        f"(power_windows={power_windows}, "
                        f"low_trade_ratio={low_trade_ratio:.3f}); "
                        "trade-level bootstrap is primary evidence"
                    )
                    ctx.run_warnings.append(low_power_warning)
                    self.logger.warning(low_power_warning)

                    if "trade_level" not in suite_queue and "trade_level" not in results:
                        cfg.auto_trade_level = True
                        suite_queue.append("trade_level")
                        ctx.run_warnings.append("trade-level suite auto-enabled")
                        self.logger.warning("trade-level suite auto-enabled")

        used_payload, unused_payload, has_unused_fields = build_usage_payloads(
            candidate_tracker=candidate_tracker,
            baseline_tracker=baseline_tracker,
            candidate_config_obj=candidate_config_obj,
            baseline_config_obj=baseline_config_obj,
        )
        write_json(used_payload, results_dir / "config_used_fields.json")
        write_json(unused_payload, results_dir / "config_unused_fields.json")

        effective_report = build_effective_config_report(
            baseline_payload=effective_baseline,
            candidate_payload=effective_candidate,
            unused_payload=unused_payload,
            unknown_status="PASS",
        )
        write_text(effective_report, reports_dir / "audit_effective_config.md")

        full_breakdown_rows = list(
            _as_dict(results.get("backtest", SuiteResult("backtest", "skip")).data).get(
                "score_breakdown_rows", []
            )
        )
        holdout_breakdown_rows = list(
            _as_dict(results.get("holdout", SuiteResult("holdout", "skip")).data).get(
                "score_breakdown_rows", []
            )
        )
        score_report = build_score_decomposition_report(
            full_rows=full_breakdown_rows,
            holdout_rows=holdout_breakdown_rows,
            tolerance=1e-6,
        )
        write_text(score_report, reports_dir / "audit_score_decomposition.md")

        decision = evaluate_decision(results)
        decision = self._apply_quality_policy(results, decision)
        decision = self._apply_config_usage_policy(
            decision,
            unused_payload=unused_payload,
            has_unused_fields=has_unused_fields,
        )
        decision.warnings = self._collect_decision_warnings(results, ctx.run_warnings, decision)
        decision.errors = self._collect_decision_errors(results, decision)

        discovered = discover_checks(project_root, set(suite_queue) | set(results.keys()))
        write_discovered_tests_report(discovered, reports_dir / "discovered_tests.md")

        generate_validation_report(results, decision, cfg, outdir, discovered=discovered)
        generate_quality_checks_report(results, cfg, outdir)
        write_decision_json(decision, outdir)
        write_index(outdir, results, decision, cfg)

        missing = self._verify_output_contract(cfg, results, outdir)
        if missing:
            missing_failures = [f"missing: {item}" for item in missing]
            decision = DecisionVerdict(
                tag="ERROR",
                exit_code=3,
                reasons=["Output contract verification failed"],
                failures=missing_failures,
                warnings=decision.warnings,
                errors=self._unique_messages([*decision.errors, *missing_failures]),
                key_links=decision.key_links,
                deltas=decision.deltas,
                metadata={"missing_count": len(missing)},
            )
            write_decision_json(decision, outdir)
            generate_validation_report(results, decision, cfg, outdir, discovered=discovered)
            generate_quality_checks_report(results, cfg, outdir)
            write_index(outdir, results, decision, cfg)
            self.logger.error("Output contract missing files: %s", missing)

        elapsed = time.time() - t0
        self.logger.info("Validation run complete in %.2fs", elapsed)

        return results, decision

    def _verify_output_contract(
        self,
        cfg: ValidationConfig,
        results: dict[str, SuiteResult],
        outdir: Path,
    ) -> list[str]:
        required: list[str] = [
            "logs/run.log",
            "reports/validation_report.md",
            "reports/quality_checks.md",
            "reports/decision.json",
            "reports/discovered_tests.md",
            "reports/audit_effective_config.md",
            "reports/audit_score_decomposition.md",
            "index.txt",
            f"configs/candidate_{cfg.config_path.name}",
            f"configs/baseline_{cfg.baseline_config_path.name}",
            "results/effective_config_baseline.json",
            "results/effective_config_candidate.json",
            "results/config_used_fields.json",
            "results/config_unused_fields.json",
        ]

        if "backtest" in results and results["backtest"].status != "skip":
            required.extend(
                [
                    "results/full_backtest_summary.csv",
                    "results/score_breakdown_full.csv",
                    "results/add_throttle_stats.json",
                ]
            )

        if "regime" in results and results["regime"].status != "skip":
            required.append("results/regime_decomposition.csv")

        if "wfo" in results and results["wfo"].status != "skip":
            required.extend([
                "results/wfo_per_round_metrics.csv",
                "results/wfo_summary.json",
                "reports/audit_wfo_invalid_windows.md",
            ])

        if cfg.bootstrap > 0 and "bootstrap" in results and results["bootstrap"].status != "skip":
            required.append("results/bootstrap_paired_test.csv")

        if cfg.subsampling and "subsampling" in results and results["subsampling"].status != "skip":
            required.append("results/subsampling_paired_test.csv")

        if cfg.sensitivity_grid and "sensitivity" in results and results["sensitivity"].status != "skip":
            required.append("results/sensitivity_grid.csv")

        if "holdout" in results and results["holdout"].status != "skip":
            required.extend(
                [
                    "results/final_holdout_metrics.csv",
                    "results/score_breakdown_holdout.csv",
                ]
            )

        if cfg.selection_bias != "none" and "selection_bias" in results and results["selection_bias"].status != "skip":
            required.append("results/selection_bias.json")

        if cfg.lookahead_check and "lookahead" in results and results["lookahead"].status != "skip":
            required.append("results/lookahead_check.txt")

        tl_active = cfg.trade_level or cfg.auto_trade_level or "trade_level" in results
        tl_status = results.get("trade_level", SuiteResult("trade_level", "skip")).status
        if tl_active and tl_status != "skip":
            required.extend([
                "results/trades_candidate.csv",
                "results/trades_baseline.csv",
                "results/matched_trades.csv",
                "results/regime_trade_summary.csv",
                "results/window_trade_counts.csv",
                "results/bootstrap_return_diff.json",
                "reports/trade_level_analysis.md",
            ])

        dd_active = cfg.dd_episodes or "dd_episodes" in results
        dd_status = results.get("dd_episodes", SuiteResult("dd_episodes", "skip")).status
        if dd_active and dd_status != "skip":
            required.extend([
                "results/dd_episodes_candidate.csv",
                "results/dd_episodes_baseline.csv",
            ])

        di_status = results.get("data_integrity", SuiteResult("data_integrity", "skip")).status
        if di_status != "skip":
            required.extend([
                "results/data_integrity.json",
                "results/data_integrity_issues.csv",
            ])

        cs_status = results.get("cost_sweep", SuiteResult("cost_sweep", "skip")).status
        if cfg.cost_sweep_bps and cs_status != "skip":
            required.append("results/cost_sweep.csv")

        inv_status = results.get("invariants", SuiteResult("invariants", "skip")).status
        if inv_status != "skip":
            required.append("results/invariant_violations.csv")

        rg_status = results.get("regression_guard", SuiteResult("regression_guard", "skip")).status
        if cfg.regression_guard and rg_status != "skip":
            required.append("results/regression_guard.json")

        cm_status = results.get("churn_metrics", SuiteResult("churn_metrics", "skip")).status
        if cm_status != "skip":
            required.append("results/churn_metrics.csv")

        missing = [path for path in required if not (outdir / path).exists()]
        return missing

    def _apply_config_usage_policy(
        self,
        decision: DecisionVerdict,
        *,
        unused_payload: dict[str, Any],
        has_unused_fields: bool,
    ) -> DecisionVerdict:
        if not has_unused_fields:
            return decision

        failures: list[str] = []
        for model in ["candidate", "baseline"]:
            fields = [
                str(item)
                for item in _as_dict(unused_payload.get(model, {})).get("unused_fields", [])
            ]
            failures.extend(f"unused_config:{model}:{field}" for field in fields)

        if not failures:
            failures = ["unused_config_fields_detected"]

        decision.tag = "ERROR"
        decision.exit_code = 3
        decision.reasons = self._unique_messages(
            [*decision.reasons, "Unused strategy config fields detected"]
        )
        decision.failures = self._unique_messages([*decision.failures, *failures])
        decision.errors = self._unique_messages([*decision.errors, *failures])
        decision.metadata = {
            **dict(decision.metadata),
            "unused_config_status": unused_payload.get("status", "FAIL"),
        }
        return decision

    @staticmethod
    def _unique_messages(items: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for raw in items:
            msg = str(raw).strip()
            if not msg or msg in seen:
                continue
            out.append(msg)
            seen.add(msg)
        return out

    def _apply_quality_policy(
        self,
        results: dict[str, SuiteResult],
        decision: DecisionVerdict,
    ) -> DecisionVerdict:
        reasons: list[str] = []
        failures: list[str] = []

        data_integrity = results.get("data_integrity")
        if data_integrity is not None and data_integrity.status == "fail":
            reasons.append("Data integrity check failed")
            hard_reasons = list(_as_dict(data_integrity.data).get("hard_fail_reasons", []))
            if hard_reasons:
                failures.extend(f"data_integrity:{item}" for item in hard_reasons)
            else:
                failures.append("data_integrity:failed")

        invariants = results.get("invariants")
        if invariants is not None and invariants.status != "skip":
            _inv_data = _as_dict(invariants.data)
            n_violations = _safe_int(_inv_data.get("n_violations", 0))
            if invariants.status == "fail" or n_violations > 0:
                reasons.append("Invariant checks failed")
                counts = _as_dict(_inv_data.get("counts_by_invariant"))
                if counts:
                    failures.extend(
                        f"invariants:{name}:{_safe_int(value)}"
                        for name, value in sorted(counts.items())
                    )
                elif n_violations > 0:
                    failures.append(f"invariants:n_violations:{n_violations}")
                else:
                    failures.append("invariants:failed")

        regression_guard = results.get("regression_guard")
        if regression_guard is not None and regression_guard.status != "skip":
            _rg_data = _as_dict(regression_guard.data)
            guard_pass = _strict_bool(_rg_data.get("pass", regression_guard.status == "pass"))
            if regression_guard.status in {"fail", "error"} or not guard_pass:
                # Chosen policy: regression-guard fail is ERROR(3), not REJECT.
                reasons.append("Regression guard failed")
                violated = _as_list_of_dicts(_rg_data.get("violated_metrics", []))
                violated_meta = _as_list_of_dicts(_rg_data.get("violated_metadata", []))
                if violated:
                    failures.extend(
                        f"regression_guard:{item.get('metric') or item.get('field') or 'unknown'}"
                        for item in violated
                    )
                if violated_meta:
                    failures.extend(
                        f"regression_guard:metadata:{item.get('field') or 'unknown'}"
                        for item in violated_meta
                    )
                if not violated and not violated_meta:
                    failures.append("regression_guard:failed")

        if not reasons:
            return decision

        decision.tag = "ERROR"
        decision.exit_code = 3
        decision.reasons = self._unique_messages([*decision.reasons, *reasons])
        decision.failures = self._unique_messages([*decision.failures, *failures])
        return decision

    def _collect_decision_warnings(
        self,
        results: dict[str, SuiteResult],
        run_warnings: list[str],
        decision: DecisionVerdict | None = None,
    ) -> list[str]:
        warnings: list[str] = list(run_warnings)

        # Include overlap warnings from decision deltas (computed in evaluate_decision)
        if decision is not None:
            overlap_warnings = decision.deltas.get("holdout_wfo_overlap_warnings")
            if isinstance(overlap_warnings, list):
                warnings.extend(str(w) for w in overlap_warnings)

        cost_sweep = results.get("cost_sweep")
        if cost_sweep is not None and cost_sweep.status != "skip":
            issues = [str(item) for item in _as_dict(cost_sweep.data).get("issues", [])]
            if issues:
                warnings.append(
                    f"Cost sweep reported {len(issues)} issue(s); treated as warning only."
                )
                warnings.extend(f"cost_sweep:{item}" for item in issues[:10])

        churn = results.get("churn_metrics")
        if churn is not None and churn.status != "skip":
            _churn_data = _as_dict(churn.data)
            churn_warnings = [str(item) for item in _churn_data.get("warnings", [])]
            warnings.extend(churn_warnings)
            churn_issues = [str(item) for item in _churn_data.get("issues", [])]
            if churn_issues:
                warnings.append(
                    f"Churn metrics reported {len(churn_issues)} issue(s); treated as warning only."
                )
                warnings.extend(f"churn_metrics:{item}" for item in churn_issues[:10])

        return self._unique_messages(warnings)

    def _collect_decision_errors(
        self,
        results: dict[str, SuiteResult],
        decision: DecisionVerdict,
    ) -> list[str]:
        errors = list(decision.errors)

        for suite_name, suite_result in results.items():
            if suite_result.status == "error":
                msg = suite_result.error_message or "suite error"
                errors.append(f"{suite_name}:{msg}")

        data_integrity = results.get("data_integrity")
        if data_integrity is not None and data_integrity.status == "fail":
            hard_reasons = list(_as_dict(data_integrity.data).get("hard_fail_reasons", []))
            if hard_reasons:
                errors.extend(f"data_integrity:{item}" for item in hard_reasons)
            else:
                errors.append("data_integrity:failed")

        invariants = results.get("invariants")
        if invariants is not None and invariants.status != "skip":
            _inv_data = _as_dict(invariants.data)
            n_violations = _safe_int(_inv_data.get("n_violations", 0))
            if invariants.status == "fail" or n_violations > 0:
                counts = _as_dict(_inv_data.get("counts_by_invariant"))
                if counts:
                    errors.extend(
                        f"invariants:{name}:{_safe_int(value)}"
                        for name, value in sorted(counts.items())
                    )
                elif n_violations > 0:
                    errors.append(f"invariants:n_violations:{n_violations}")
                else:
                    errors.append("invariants:failed")

        regression_guard = results.get("regression_guard")
        if regression_guard is not None and regression_guard.status != "skip":
            _rg_data = _as_dict(regression_guard.data)
            guard_pass = _strict_bool(_rg_data.get("pass", regression_guard.status == "pass"))
            if regression_guard.status in {"fail", "error"} or not guard_pass:
                violated = _as_list_of_dicts(_rg_data.get("violated_metrics", []))
                violated_meta = _as_list_of_dicts(_rg_data.get("violated_metadata", []))
                errors.extend(
                    f"regression_guard:{item.get('metric') or item.get('field') or 'unknown'}"
                    for item in violated
                )
                errors.extend(
                    f"regression_guard:metadata:{item.get('field') or 'unknown'}"
                    for item in violated_meta
                )
                if not violated and not violated_meta:
                    errors.append("regression_guard:failed")

        return self._unique_messages(errors)
