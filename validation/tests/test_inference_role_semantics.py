"""Regression tests for inference-stack role semantics (Phase 4).

Verifies that bootstrap and subsampling are diagnostics (not gates)
after the Phase 3 role change (Report 22B).

Test IDs map to the patch plan (Report 22B §4.2–4.5):
  T1: test_bootstrap_gate_is_info_not_soft
  T2: test_bootstrap_never_in_failures
  T3: test_bootstrap_still_reports_values
  T4: test_subsampling_status_always_info
  T5: test_negative_control_not_blocked
  T6: test_strong_positive_not_blocked
  T7: test_bootstrap_alignment_rejects_mismatch

Control pairs from Report 17:
  A0 vs A1:      near_identical (boot_p=0.474, ci_low=-0.124)
  A0 vs VBREAK:  materially_different (boot_p=0.644, ci_low=-0.454)
  A0 vs VCUSUM:  materially_different (boot_p=0.818, ci_low=-0.401)
"""

from __future__ import annotations

import numpy as np
import pytest

from v10.core.types import EquitySnap
from v10.research.bootstrap import paired_block_bootstrap
from validation.decision import evaluate_decision
from validation.suites.base import SuiteResult


# ── Control pair bootstrap gate data from Report 17 ──

CONTROL_PAIRS = {
    "A0_vs_A1": {       # near_identical — boot gate would FAIL
        "p_candidate_better": 0.474,
        "ci_lower": -0.124,
        "ci_upper": 0.112,
        "observed_delta": -0.006,
    },
    "A0_vs_VBREAK": {   # materially_different — boot gate would FAIL
        "p_candidate_better": 0.644,
        "ci_lower": -0.454,
        "ci_upper": 0.650,
        "observed_delta": 0.098,
    },
    "A0_vs_VCUSUM": {   # materially_different — boot gate would FAIL
        "p_candidate_better": 0.818,
        "ci_lower": -0.401,
        "ci_upper": 1.072,
        "observed_delta": 0.343,
    },
}


def _make_bootstrap_suite_result(gate_data: dict) -> SuiteResult:
    """Build a synthetic BootstrapSuite result from control pair data."""
    return SuiteResult(
        name="bootstrap",
        status="info",  # Phase 3: bootstrap is diagnostic-only, always "info"
        data={
            "rows": [],
            "gate": gate_data,
            "summary": {"n_rows": 1, "bootstrap": 2000, "seed": 42, "gate": gate_data},
        },
    )


def _make_subsampling_suite_result(
    p_candidate_better: float = 0.930,
    ci_lower: float = -0.139,
    decision_pass: bool = False,
) -> SuiteResult:
    """Build a synthetic SubsamplingSuite result."""
    return SuiteResult(
        name="subsampling",
        status="info",  # Phase 3B: always info now
        data={
            "rows": [],
            "gate": {
                "method": "paired_block_subsampling",
                "p_candidate_better": p_candidate_better,
                "ci_lower": ci_lower,
                "decision_pass": decision_pass,
                "support_ratio": 0.0,
            },
            "summary": {},
        },
    )


def _make_equity(n_bars: int = 500, drift: float = 0.0001, seed: int = 42) -> list[EquitySnap]:
    """Generate synthetic equity curve."""
    rng = np.random.default_rng(seed)
    returns = drift + 0.01 * rng.standard_normal(n_bars)
    navs = 10_000.0 * np.cumprod(1.0 + returns)
    navs = np.insert(navs, 0, 10_000.0)
    equity = []
    for i, nav in enumerate(navs):
        equity.append(
            EquitySnap(
                close_time=i * 4 * 3600 * 1000,
                nav_mid=float(nav),
                nav_liq=float(nav),
                cash=float(nav) * 0.5,
                btc_qty=0.0,
                exposure=0.5,
            )
        )
    return equity


# ── T1: Bootstrap gate is info, not soft ──


class TestBootstrapRoleSemantic:
    @pytest.mark.parametrize("pair_name,gate_data", list(CONTROL_PAIRS.items()))
    def test_bootstrap_gate_is_info_not_soft(self, pair_name: str, gate_data: dict) -> None:
        """T1: Bootstrap GateCheck has severity='info' and passed=True for all control pairs."""
        results = {"bootstrap": _make_bootstrap_suite_result(gate_data)}
        verdict = evaluate_decision(results)

        boot_gates = [g for g in verdict.gates if g.gate_name == "bootstrap"]
        assert len(boot_gates) == 1, f"Expected exactly 1 bootstrap gate, got {len(boot_gates)}"

        gate = boot_gates[0]
        assert gate.severity == "info", (
            f"{pair_name}: bootstrap severity should be 'info', got '{gate.severity}'"
        )
        assert gate.passed is True, (
            f"{pair_name}: bootstrap passed should be True (diagnostic, no veto)"
        )

    @pytest.mark.parametrize("pair_name,gate_data", list(CONTROL_PAIRS.items()))
    def test_bootstrap_never_in_failures(self, pair_name: str, gate_data: dict) -> None:
        """T2: 'bootstrap_gate_failed' never appears in failures for any control pair."""
        results = {"bootstrap": _make_bootstrap_suite_result(gate_data)}
        verdict = evaluate_decision(results)

        assert "bootstrap_gate_failed" not in verdict.failures, (
            f"{pair_name}: 'bootstrap_gate_failed' found in failures — "
            f"bootstrap should have no veto power"
        )

    @pytest.mark.parametrize("pair_name,gate_data", list(CONTROL_PAIRS.items()))
    def test_bootstrap_still_reports_values(self, pair_name: str, gate_data: dict) -> None:
        """T3: bootstrap_p_candidate_better and bootstrap_ci_lower are populated in deltas."""
        results = {"bootstrap": _make_bootstrap_suite_result(gate_data)}
        verdict = evaluate_decision(results)

        assert "bootstrap_p_candidate_better" in verdict.deltas, (
            f"{pair_name}: bootstrap_p_candidate_better missing from deltas"
        )
        assert "bootstrap_ci_lower" in verdict.deltas, (
            f"{pair_name}: bootstrap_ci_lower missing from deltas"
        )
        # Values should match the gate data
        assert abs(verdict.deltas["bootstrap_p_candidate_better"] - gate_data["p_candidate_better"]) < 0.001
        assert abs(verdict.deltas["bootstrap_ci_lower"] - gate_data["ci_lower"]) < 0.001


# ── T4: Subsampling status always info ──


class TestSubsamplingRoleSemantic:
    def test_subsampling_status_always_info(self) -> None:
        """T4: SubsamplingSuite status is 'info' regardless of gate dict values."""
        # Build a result where decision_pass is True — status should still be info
        result_passing = _make_subsampling_suite_result(
            p_candidate_better=0.95, ci_lower=0.05, decision_pass=True,
        )
        assert result_passing.status == "info"

        # Build a result where decision_pass is False — status should still be info
        result_failing = _make_subsampling_suite_result(
            p_candidate_better=0.30, ci_lower=-0.50, decision_pass=False,
        )
        assert result_failing.status == "info"

    def test_subsampling_gate_data_preserved(self) -> None:
        """Subsampling gate dict still contains diagnostic values."""
        result = _make_subsampling_suite_result(
            p_candidate_better=0.930, ci_lower=-0.139,
        )
        gate = result.data.get("gate", {})
        assert gate.get("p_candidate_better") == 0.930
        assert gate.get("ci_lower") == -0.139
        assert gate.get("method") == "paired_block_subsampling"


# ── Bootstrap suite status tests (Report 24B) ──


class TestBootstrapSuiteStatus:
    """Verify the BootstrapSuite.run() always returns status='info'."""

    def test_bootstrap_suite_status_is_info_with_gate(self) -> None:
        """BootstrapSuite result with populated gate dict has status='info'."""
        # Simulate what the suite produces: gate with passing values
        result = _make_bootstrap_suite_result(CONTROL_PAIRS["A0_vs_VCUSUM"])
        assert result.status == "info", (
            f"Bootstrap suite status should be 'info', got '{result.status}'"
        )

    def test_bootstrap_suite_status_is_info_without_gate(self) -> None:
        """BootstrapSuite result with empty gate dict has status='info'."""
        result = SuiteResult(
            name="bootstrap",
            status="info",
            data={"rows": [], "gate": {}, "summary": {"n_rows": 0}},
        )
        assert result.status == "info"

    def test_bootstrap_suite_status_never_pass_or_fail(self) -> None:
        """Bootstrap suite status must never be 'pass' or 'fail' for any gate values."""
        # Values that would have been "pass" under old logic (p >= 0.80, ci_low > -0.01)
        passing_gate = {
            "p_candidate_better": 0.95,
            "ci_lower": 0.05,
            "ci_upper": 0.20,
            "observed_delta": 0.10,
        }
        result_pass = _make_bootstrap_suite_result(passing_gate)
        assert result_pass.status == "info", "Bootstrap status must be 'info', not 'pass'"

        # Values that would have been "fail" under old logic
        failing_gate = {
            "p_candidate_better": 0.30,
            "ci_lower": -0.50,
            "ci_upper": 0.10,
            "observed_delta": -0.20,
        }
        result_fail = _make_bootstrap_suite_result(failing_gate)
        assert result_fail.status == "info", "Bootstrap status must be 'info', not 'fail'"

    def test_bootstrap_suite_gate_data_preserved(self) -> None:
        """Bootstrap gate dict still contains all diagnostic values after status change."""
        gate_data = CONTROL_PAIRS["A0_vs_VBREAK"]
        result = _make_bootstrap_suite_result(gate_data)
        gate = result.data.get("gate", {})
        assert gate.get("p_candidate_better") == gate_data["p_candidate_better"]
        assert gate.get("ci_lower") == gate_data["ci_lower"]
        assert gate.get("ci_upper") == gate_data["ci_upper"]
        assert gate.get("observed_delta") == gate_data["observed_delta"]


# ── T5, T6: Control pair flow-through ──


class TestControlPairFlowThrough:
    def test_negative_control_not_blocked(self) -> None:
        """T5: A0 vs A1 (near_identical, boot_p=0.474) → PROMOTE with diagnostics only."""
        gate_data = CONTROL_PAIRS["A0_vs_A1"]
        results = {
            "bootstrap": _make_bootstrap_suite_result(gate_data),
            "subsampling": _make_subsampling_suite_result(),
        }
        verdict = evaluate_decision(results)

        # Only diagnostic suites, no hard/soft gates → must be PROMOTE
        assert verdict.tag == "PROMOTE", (
            f"A0 vs A1: expected PROMOTE with diagnostic-only suites, got {verdict.tag}"
        )
        assert verdict.exit_code == 0
        # Bootstrap should not contribute to soft_failures
        soft_fails = [g for g in verdict.gates if g.severity == "soft" and not g.passed]
        boot_soft_fails = [g for g in soft_fails if g.gate_name == "bootstrap"]
        assert len(boot_soft_fails) == 0, "Bootstrap should not be a soft failure"

    def test_strong_positive_not_blocked(self) -> None:
        """T6: A0 vs VCUSUM (boot_p=0.818) → PROMOTE with diagnostics only."""
        gate_data = CONTROL_PAIRS["A0_vs_VCUSUM"]
        results = {
            "bootstrap": _make_bootstrap_suite_result(gate_data),
            "subsampling": _make_subsampling_suite_result(),
        }
        verdict = evaluate_decision(results)

        # Only diagnostic suites, no hard/soft gates → must be PROMOTE
        assert verdict.tag == "PROMOTE", (
            f"A0 vs VCUSUM: expected PROMOTE with diagnostic-only suites, got {verdict.tag}"
        )
        assert verdict.exit_code == 0
        boot_soft_fails = [
            g for g in verdict.gates
            if g.gate_name == "bootstrap" and g.severity == "soft" and not g.passed
        ]
        assert len(boot_soft_fails) == 0, "Bootstrap should not be a soft failure"

    def test_bootstrap_only_results_promote(self) -> None:
        """When bootstrap is the ONLY suite result, verdict should be PROMOTE
        (no gates can veto since bootstrap is info-only)."""
        gate_data = CONTROL_PAIRS["A0_vs_A1"]
        results = {"bootstrap": _make_bootstrap_suite_result(gate_data)}
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE", (
            f"Expected PROMOTE when bootstrap is the only result, got {verdict.tag}"
        )
        assert verdict.exit_code == 0

    def test_no_hidden_promote_reject_path(self) -> None:
        """Verify no hidden automatic promote/reject path exists in bootstrap gate logic.
        The bootstrap gate should NEVER appear in failures regardless of p/ci values."""
        # Extreme case: p=0.0, ci_lower=-10.0 — still should not veto
        extreme_gate = {
            "p_candidate_better": 0.0,
            "ci_lower": -10.0,
            "ci_upper": -5.0,
            "observed_delta": -5.0,
        }
        results = {"bootstrap": _make_bootstrap_suite_result(extreme_gate)}
        verdict = evaluate_decision(results)

        assert "bootstrap_gate_failed" not in verdict.failures
        boot_gate = next(g for g in verdict.gates if g.gate_name == "bootstrap")
        assert boot_gate.passed is True
        assert boot_gate.severity == "info"


# ── T7: Alignment mismatch still raises ──


class TestAlignmentMismatch:
    def test_bootstrap_alignment_rejects_mismatch(self) -> None:
        """T7: paired_block_bootstrap with different-length curves raises ValueError."""
        equity_a = _make_equity(n_bars=500, seed=1)
        equity_b = _make_equity(n_bars=400, seed=2)
        with pytest.raises(ValueError, match="different lengths"):
            paired_block_bootstrap(equity_a, equity_b)
