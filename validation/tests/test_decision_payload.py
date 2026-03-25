"""Unit tests for decision payload warnings/errors and quality policy overrides."""

from __future__ import annotations

import json
from pathlib import Path

from validation.config import ValidationConfig
from validation.decision import evaluate_decision
from validation.output import write_decision_json
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


def test_cost_and_churn_are_warnings_not_failures(tmp_path: Path) -> None:
    runner = _build_runner(tmp_path)
    results = {
        "cost_sweep": SuiteResult(
            name="cost_sweep",
            status="fail",
            data={"issues": ["row_count_mismatch: expected=12, got=10"]},
        ),
        "churn_metrics": SuiteResult(
            name="churn_metrics",
            status="pass",
            data={
                "warnings": ["WARNING candidate/base: fee_drag_pct=25.000 >= 20.000"],
                "issues": [],
            },
        ),
    }

    decision = evaluate_decision({})
    decision = runner._apply_quality_policy(results, decision)
    decision.warnings = runner._collect_decision_warnings(results, [])
    decision.errors = runner._collect_decision_errors(results, decision)
    write_decision_json(decision, runner.config.outdir)

    payload = json.loads((runner.config.outdir / "reports" / "decision.json").read_text())
    assert payload["verdict"] == "PROMOTE"
    assert payload["exit_code"] == 0
    assert len(payload["warnings"]) >= 2
    assert any("Cost sweep reported" in item for item in payload["warnings"])
    assert any("fee_drag_pct" in item for item in payload["warnings"])
    assert payload["errors"] == []


def test_regression_guard_fail_forces_error_exit3(tmp_path: Path) -> None:
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
        )
    }

    decision = evaluate_decision({})
    decision = runner._apply_quality_policy(results, decision)
    decision.errors = runner._collect_decision_errors(results, decision)

    assert decision.tag == "ERROR"
    assert decision.exit_code == 3
    assert any(item == "regression_guard:CAGR" for item in decision.errors)
    assert any(item == "regression_guard:metadata:dataset_id" for item in decision.errors)
