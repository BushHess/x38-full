"""Integration tests for runner-level authority (Report 28).

Tests all post-decision runner policies that can modify the final verdict:
- Quality policy: _apply_quality_policy → can elevate to ERROR(3)
- Config usage policy: _apply_config_usage_policy → can elevate to ERROR(3)
- Output contract: _verify_output_contract → detects missing output files
- Warning/error collection: _collect_decision_warnings, _collect_decision_errors
- Precedence: no runner policy can downgrade a verdict
- WFO auto-enable: wfo_low_power detection consistent between runner and decision

Test ID mapping (Report 28):
  QP1: test_quality_policy_data_integrity_soft_fail_elevates_error
  QP2: test_quality_policy_invariants_fail_elevates_error
  QP3: test_quality_policy_regression_guard_fail_elevates_error
  QP4: test_quality_policy_clean_preserves_promote
  QP5: test_quality_policy_elevates_reject_to_error
  QP6: test_quality_policy_data_integrity_hard_fail_also_caught
  CU1: test_config_usage_unused_fields_elevates_error
  CU2: test_config_usage_clean_preserves_verdict
  CU3: test_config_usage_elevates_hold_to_error
  OC1: test_output_contract_detects_missing_base_files
  OC2: test_output_contract_passes_when_base_complete
  OC3: test_output_contract_includes_suite_specific_files
  WA1: test_cost_sweep_issues_are_warnings_only
  WA2: test_churn_metrics_issues_are_warnings_only
  WA3: test_run_warnings_propagated
  EC1: test_error_collection_populates_list_not_verdict
  EC2: test_error_collection_includes_regression_guard
  PR1: test_no_runner_policy_downgrades_error
  PR2: test_no_runner_policy_downgrades_reject
  PR3: test_quality_then_config_cumulative_error
  PR4: test_quality_policy_only_elevates_to_error (parametrized x4)
  PR5: test_config_policy_only_elevates_to_error (parametrized x4)
  WF1: test_wfo_low_power_condition_detected
  WF2: test_wfo_normal_power_not_low_power
  WF3: test_wfo_low_trade_ratio_triggers_low_power
  ZA1: test_zero_authority_cost_sweep_never_vetoes
  ZA2: test_zero_authority_churn_never_vetoes
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validation.config import ValidationConfig
from validation.decision import DecisionVerdict
from validation.decision import evaluate_decision
from validation.runner import ValidationRunner
from validation.suites.base import SuiteResult

ROOT = Path(__file__).resolve().parents[2]
BASELINE_CFG = ROOT / "v10" / "configs" / "baseline_legacy.live.yaml"


def _build_runner(tmp_path: Path) -> ValidationRunner:
    cfg = ValidationConfig(
        strategy_name="v8_apex",
        baseline_name="v8_apex",
        config_path=BASELINE_CFG,
        baseline_config_path=BASELINE_CFG,
        outdir=tmp_path / "out",
        dataset=ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv",
        suite="basic",
    )
    return ValidationRunner(cfg)


def _promote_verdict(**kwargs) -> DecisionVerdict:
    return DecisionVerdict(tag="PROMOTE", exit_code=0, **kwargs)


def _hold_verdict(**kwargs) -> DecisionVerdict:
    return DecisionVerdict(tag="HOLD", exit_code=1, **kwargs)


def _reject_verdict(**kwargs) -> DecisionVerdict:
    return DecisionVerdict(tag="REJECT", exit_code=2, **kwargs)


def _error_verdict(**kwargs) -> DecisionVerdict:
    return DecisionVerdict(tag="ERROR", exit_code=3, **kwargs)


# ── Quality Policy Tests ──────────────────────────────────────────────


class TestQualityPolicy:
    def test_quality_policy_data_integrity_soft_fail_elevates_error(
        self, tmp_path: Path
    ) -> None:
        """QP1: data_integrity status=fail (no hard_fail) → ERROR(3).

        Key finding: evaluate_decision() only ERRORs on hard_fail=True,
        but _apply_quality_policy catches ALL status=fail.
        """
        runner = _build_runner(tmp_path)
        results = {
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="fail",
                data={"hard_fail": False},
            ),
        }
        # evaluate_decision does NOT catch soft-fail (hard_fail=False)
        decision = evaluate_decision(results)
        assert decision.tag == "PROMOTE"

        # Quality policy catches it
        decision = runner._apply_quality_policy(results, decision)
        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert any("data_integrity" in f for f in decision.failures)

    def test_quality_policy_invariants_fail_elevates_error(
        self, tmp_path: Path
    ) -> None:
        """QP2: invariants with violations → ERROR(3)."""
        runner = _build_runner(tmp_path)
        results = {
            "invariants": SuiteResult(
                name="invariants",
                status="fail",
                data={
                    "n_violations": 3,
                    "counts_by_invariant": {"nav_monotone": 2, "exposure_bounds": 1},
                },
            ),
        }
        decision = _promote_verdict()
        decision = runner._apply_quality_policy(results, decision)

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert any("invariants:nav_monotone" in f for f in decision.failures)
        assert any("invariants:exposure_bounds" in f for f in decision.failures)

    def test_quality_policy_regression_guard_fail_elevates_error(
        self, tmp_path: Path
    ) -> None:
        """QP3: regression_guard fail → ERROR(3)."""
        runner = _build_runner(tmp_path)
        results = {
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={
                    "pass": False,
                    "violated_metrics": [{"metric": "CAGR"}, {"metric": "Sharpe"}],
                },
            ),
        }
        decision = _promote_verdict()
        decision = runner._apply_quality_policy(results, decision)

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert any("regression_guard:CAGR" in f for f in decision.failures)
        assert any("regression_guard:Sharpe" in f for f in decision.failures)

    def test_quality_policy_clean_preserves_promote(self, tmp_path: Path) -> None:
        """QP4: No quality issues → PROMOTE preserved."""
        runner = _build_runner(tmp_path)
        results = {
            "data_integrity": SuiteResult(
                name="data_integrity", status="pass", data={}
            ),
            "invariants": SuiteResult(
                name="invariants",
                status="pass",
                data={"n_violations": 0},
            ),
        }
        decision = _promote_verdict()
        decision = runner._apply_quality_policy(results, decision)

        assert decision.tag == "PROMOTE"
        assert decision.exit_code == 0

    def test_quality_policy_elevates_reject_to_error(self, tmp_path: Path) -> None:
        """QP5: REJECT + quality failure → ERROR(3). Original failures preserved."""
        runner = _build_runner(tmp_path)
        results = {
            "invariants": SuiteResult(
                name="invariants",
                status="fail",
                data={"n_violations": 1, "counts_by_invariant": {"nav_monotone": 1}},
            ),
        }
        decision = _reject_verdict(failures=["full_harsh_delta_below_tolerance"])
        decision = runner._apply_quality_policy(results, decision)

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert "full_harsh_delta_below_tolerance" in decision.failures
        assert any("invariants:nav_monotone" in f for f in decision.failures)

    def test_quality_policy_data_integrity_hard_fail_also_caught(
        self, tmp_path: Path
    ) -> None:
        """QP6: data_integrity with hard_fail_reasons populates specific failures."""
        runner = _build_runner(tmp_path)
        results = {
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="fail",
                data={
                    "hard_fail": True,
                    "hard_fail_reasons": ["missing_bars_exceed_threshold"],
                },
            ),
        }
        decision = _promote_verdict()
        decision = runner._apply_quality_policy(results, decision)

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert "data_integrity:missing_bars_exceed_threshold" in decision.failures


# ── Config Usage Policy Tests ─────────────────────────────────────────


class TestConfigUsagePolicy:
    def test_config_usage_unused_fields_elevates_error(self, tmp_path: Path) -> None:
        """CU1: unused config fields → ERROR(3)."""
        runner = _build_runner(tmp_path)
        unused_payload = {
            "candidate": {"unused_fields": ["momentum.lookback", "risk.max_dd"]},
            "baseline": {"unused_fields": []},
        }
        decision = _promote_verdict()
        decision = runner._apply_config_usage_policy(
            decision, unused_payload=unused_payload, has_unused_fields=True
        )

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert any("unused_config:candidate:momentum.lookback" in f for f in decision.failures)
        assert any("unused_config:candidate:risk.max_dd" in f for f in decision.failures)

    def test_config_usage_clean_preserves_verdict(self, tmp_path: Path) -> None:
        """CU2: no unused fields → verdict preserved."""
        runner = _build_runner(tmp_path)
        decision = _promote_verdict()
        decision = runner._apply_config_usage_policy(
            decision, unused_payload={}, has_unused_fields=False
        )

        assert decision.tag == "PROMOTE"
        assert decision.exit_code == 0

    def test_config_usage_elevates_hold_to_error(self, tmp_path: Path) -> None:
        """CU3: HOLD + unused fields → ERROR(3). Original failures preserved."""
        runner = _build_runner(tmp_path)
        unused_payload = {
            "candidate": {"unused_fields": ["stale_param"]},
        }
        decision = _hold_verdict(failures=["wfo_robustness_failed"])
        decision = runner._apply_config_usage_policy(
            decision, unused_payload=unused_payload, has_unused_fields=True
        )

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert "wfo_robustness_failed" in decision.failures
        assert any("unused_config:candidate:stale_param" in f for f in decision.failures)


# ── Output Contract Tests ─────────────────────────────────────────────


class TestOutputContract:
    def test_output_contract_detects_missing_base_files(self, tmp_path: Path) -> None:
        """OC1: empty outdir → all base files reported missing."""
        runner = _build_runner(tmp_path)
        outdir = tmp_path / "out"
        outdir.mkdir(parents=True, exist_ok=True)

        missing = runner._verify_output_contract(runner.config, {}, outdir)

        assert len(missing) > 0
        assert "logs/run.log" in missing
        assert "reports/decision.json" in missing
        assert "index.txt" in missing

    def test_output_contract_passes_when_base_complete(self, tmp_path: Path) -> None:
        """OC2: all base required files present → empty missing list."""
        runner = _build_runner(tmp_path)
        outdir = tmp_path / "out"
        cfg = runner.config

        base_files = [
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
        for f in base_files:
            path = outdir / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")

        # No suite results → only base files needed
        missing = runner._verify_output_contract(cfg, {}, outdir)
        assert missing == [], f"Unexpected missing: {missing}"

    def test_output_contract_includes_suite_specific_files(
        self, tmp_path: Path
    ) -> None:
        """OC3: when backtest ran, its outputs are required."""
        runner = _build_runner(tmp_path)
        outdir = tmp_path / "out"
        outdir.mkdir(parents=True, exist_ok=True)

        results = {
            "backtest": SuiteResult(name="backtest", status="pass", data={}),
        }
        missing = runner._verify_output_contract(runner.config, results, outdir)

        assert "results/full_backtest_summary.csv" in missing
        assert "results/score_breakdown_full.csv" in missing


# ── Warning Collection Tests ──────────────────────────────────────────


class TestWarningCollection:
    def test_cost_sweep_issues_are_warnings_only(self, tmp_path: Path) -> None:
        """WA1: cost_sweep issues → warnings only, never decision failures."""
        runner = _build_runner(tmp_path)
        results = {
            "cost_sweep": SuiteResult(
                name="cost_sweep",
                status="fail",
                data={"issues": ["row_count_mismatch: expected=12, got=10"]},
            ),
        }
        warnings = runner._collect_decision_warnings(results, [])

        assert any("Cost sweep" in w for w in warnings)
        assert any("row_count_mismatch" in w for w in warnings)

    def test_churn_metrics_issues_are_warnings_only(self, tmp_path: Path) -> None:
        """WA2: churn_metrics warnings are propagated."""
        runner = _build_runner(tmp_path)
        results = {
            "churn_metrics": SuiteResult(
                name="churn_metrics",
                status="pass",
                data={
                    "warnings": ["WARNING: fee_drag_pct=25.0 >= 20.0"],
                    "issues": [],
                },
            ),
        }
        warnings = runner._collect_decision_warnings(results, [])
        assert any("fee_drag_pct" in w for w in warnings)

    def test_run_warnings_propagated(self, tmp_path: Path) -> None:
        """WA3: run_warnings from context are included in decision warnings."""
        runner = _build_runner(tmp_path)
        run_warnings = ["Low-power WFO detected (power_windows=1)"]
        warnings = runner._collect_decision_warnings({}, run_warnings)
        assert "Low-power WFO detected (power_windows=1)" in warnings


# ── Error Collection Tests ────────────────────────────────────────────


class TestErrorCollection:
    def test_error_collection_populates_list_not_verdict(
        self, tmp_path: Path
    ) -> None:
        """EC1: _collect_decision_errors populates errors list but does NOT change verdict."""
        runner = _build_runner(tmp_path)
        results = {
            "backtest": SuiteResult(
                name="backtest",
                status="error",
                error_message="engine crash",
            ),
        }
        decision = _promote_verdict()
        errors = runner._collect_decision_errors(results, decision)

        assert any("backtest:engine crash" in e for e in errors)
        # Decision tag/exit_code untouched by _collect_decision_errors
        assert decision.tag == "PROMOTE"
        assert decision.exit_code == 0

    def test_error_collection_includes_regression_guard(
        self, tmp_path: Path
    ) -> None:
        """EC2: regression_guard violations appear in error collection."""
        runner = _build_runner(tmp_path)
        results = {
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={
                    "pass": False,
                    "violated_metrics": [{"metric": "CAGR"}],
                    "violated_metadata": [{"field": "dataset_id"}],
                },
            ),
        }
        decision = _error_verdict()
        errors = runner._collect_decision_errors(results, decision)

        assert any("regression_guard:CAGR" in e for e in errors)
        assert any("regression_guard:metadata:dataset_id" in e for e in errors)


# ── Precedence Tests ──────────────────────────────────────────────────


class TestPrecedence:
    def test_no_runner_policy_downgrades_error(self, tmp_path: Path) -> None:
        """PR1: ERROR(3) stays ERROR(3) through all clean runner policies."""
        runner = _build_runner(tmp_path)
        clean_results: dict[str, SuiteResult] = {}

        decision = _error_verdict(
            reasons=["suite error"],
            failures=["backtest:engine crash"],
        )
        decision = runner._apply_quality_policy(clean_results, decision)
        decision = runner._apply_config_usage_policy(
            decision, unused_payload={}, has_unused_fields=False
        )

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3

    def test_no_runner_policy_downgrades_reject(self, tmp_path: Path) -> None:
        """PR2: REJECT(2) stays REJECT when policies are clean."""
        runner = _build_runner(tmp_path)
        clean_results: dict[str, SuiteResult] = {}

        decision = _reject_verdict(failures=["full_harsh_delta_below_tolerance"])
        decision = runner._apply_quality_policy(clean_results, decision)
        decision = runner._apply_config_usage_policy(
            decision, unused_payload={}, has_unused_fields=False
        )

        assert decision.tag == "REJECT"
        assert decision.exit_code == 2

    def test_quality_then_config_cumulative_error(self, tmp_path: Path) -> None:
        """PR3: quality + config both fail → ERROR with failures from both sources."""
        runner = _build_runner(tmp_path)
        results = {
            "invariants": SuiteResult(
                name="invariants",
                status="fail",
                data={"n_violations": 1, "counts_by_invariant": {"nav_monotone": 1}},
            ),
        }
        unused_payload = {
            "candidate": {"unused_fields": ["stale_param"]},
        }

        decision = _promote_verdict()
        decision = runner._apply_quality_policy(results, decision)
        assert decision.tag == "ERROR"

        decision = runner._apply_config_usage_policy(
            decision, unused_payload=unused_payload, has_unused_fields=True
        )
        assert decision.tag == "ERROR"
        assert decision.exit_code == 3
        assert any("invariants:" in f for f in decision.failures)
        assert any("unused_config:" in f for f in decision.failures)

    @pytest.mark.parametrize(
        "initial_tag,initial_exit",
        [("PROMOTE", 0), ("HOLD", 1), ("REJECT", 2), ("ERROR", 3)],
    )
    def test_quality_policy_only_elevates_to_error(
        self, tmp_path: Path, initial_tag: str, initial_exit: int
    ) -> None:
        """PR4: Quality policy can only elevate to ERROR(3), regardless of starting verdict."""
        runner = _build_runner(tmp_path)
        results = {
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="fail",
                data={"hard_fail": False},
            ),
        }
        decision = DecisionVerdict(tag=initial_tag, exit_code=initial_exit)
        decision = runner._apply_quality_policy(results, decision)

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3

    @pytest.mark.parametrize(
        "initial_tag,initial_exit",
        [("PROMOTE", 0), ("HOLD", 1), ("REJECT", 2), ("ERROR", 3)],
    )
    def test_config_policy_only_elevates_to_error(
        self, tmp_path: Path, initial_tag: str, initial_exit: int
    ) -> None:
        """PR5: Config usage policy can only elevate to ERROR(3), regardless of starting verdict."""
        runner = _build_runner(tmp_path)
        unused_payload = {
            "candidate": {"unused_fields": ["dead_param"]},
        }
        decision = DecisionVerdict(tag=initial_tag, exit_code=initial_exit)
        decision = runner._apply_config_usage_policy(
            decision, unused_payload=unused_payload, has_unused_fields=True
        )

        assert decision.tag == "ERROR"
        assert decision.exit_code == 3


# ── WFO Auto-Enable Tests ────────────────────────────────────────────


class TestWFOAutoEnable:
    def test_wfo_low_power_condition_detected(self) -> None:
        """WF1: power_windows < 3 triggers wfo_low_power=True in decision metadata."""
        results = {
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={
                    "summary": {
                        "n_windows": 5,
                        "n_windows_valid": 5,
                        "positive_delta_windows": 3,
                        "win_rate": 0.60,
                        "low_trade_windows_count": 0,
                        "stats_power_only": {"n_windows": 2},
                    },
                },
            ),
        }
        verdict = evaluate_decision(results)
        assert verdict.metadata.get("wfo_low_power") is True

    def test_wfo_normal_power_not_low_power(self) -> None:
        """WF2: WFO with normal power → wfo_low_power=False."""
        results = {
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={
                    "summary": {
                        "n_windows": 10,
                        "n_windows_valid": 10,
                        "positive_delta_windows": 8,
                        "win_rate": 0.80,
                        "low_trade_windows_count": 0,
                        "stats_power_only": {"n_windows": 10},
                    },
                },
            ),
        }
        verdict = evaluate_decision(results)
        assert verdict.metadata.get("wfo_low_power") is False

    def test_wfo_low_trade_ratio_triggers_low_power(self) -> None:
        """WF3: low_trade_ratio > 0.5 triggers wfo_low_power even with enough power windows."""
        results = {
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={
                    "summary": {
                        "n_windows": 10,
                        "n_windows_valid": 10,
                        "positive_delta_windows": 8,
                        "win_rate": 0.80,
                        "low_trade_windows_count": 6,  # 6/10 = 0.6 > 0.5
                        "stats_power_only": {"n_windows": 10},
                    },
                },
            ),
        }
        verdict = evaluate_decision(results)
        assert verdict.metadata.get("wfo_low_power") is True


# ── Zero-Authority Suite Tests ────────────────────────────────────────


class TestZeroAuthoritySuites:
    def test_zero_authority_cost_sweep_never_vetoes(self) -> None:
        """ZA1: cost_sweep status=fail does NOT appear in decision failures."""
        results = {
            "cost_sweep": SuiteResult(
                name="cost_sweep",
                status="fail",
                data={"issues": ["row_count_mismatch"]},
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0
        assert not any("cost_sweep" in f for f in verdict.failures)

    def test_zero_authority_churn_never_vetoes(self) -> None:
        """ZA2: churn_metrics status=fail does NOT appear in decision failures."""
        results = {
            "churn_metrics": SuiteResult(
                name="churn_metrics",
                status="fail",
                data={"warnings": ["high fee drag"], "issues": ["churn detected"]},
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0
        assert not any("churn" in f for f in verdict.failures)
