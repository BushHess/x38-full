"""Regression tests for four fixes (2026-03-16).

Fix 1: selection_bias fallback bypass — method fallback must HOLD regardless of PSR.
Fix 2: PBO proxy sentinel — rejected windows excluded from negative_delta_ratio.
Fix 3: Overlap off-by-one — inclusive end dates (+1 day).
Fix 4: Warnings/errors rendered in validation_report.md.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from validation.config import ValidationConfig
from validation.decision import DecisionVerdict
from validation.decision import GateCheck
from validation.decision import _compute_holdout_wfo_overlap
from validation.decision import evaluate_decision
from validation.report import generate_validation_report
from validation.suites.base import SuiteResult

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_sb_psr_with_fallback(
    *,
    requested_method: str = "pbo",
    method: str = "none",
    fallback_reason: str = "no_wfo_windows_for_pbo",
    psr_pass: bool = True,
    psr_value: float = 0.9999,
    risk_statement: str = "CAUTION — fallback to none: PBO requires valid WFO windows",
) -> SuiteResult:
    """Selection-bias suite result where PBO fell back but PSR passes."""
    return SuiteResult(
        name="selection_bias",
        status="info",
        data={
            "requested_method": requested_method,
            "method": method,
            "fallback_reason": fallback_reason,
            "risk_statement": risk_statement,
            "psr": {"psr": psr_value},
            "psr_pass": psr_pass,
            "sr_observed": 1.5,
            "sr_baseline": 0.5,
            "dsr_advisory": "DSR robust across tested trials",
        },
    )


def _make_sb_psr_no_fallback(*, psr_pass: bool, psr_value: float = 0.9999) -> SuiteResult:
    """Selection-bias suite result with PSR, no fallback."""
    return SuiteResult(
        name="selection_bias",
        status="pass" if psr_pass else "info",
        data={
            "requested_method": "deflated",
            "method": "deflated",
            "risk_statement": f"PASS — PSR={psr_value:.3f}",
            "psr": {"psr": psr_value},
            "psr_pass": psr_pass,
            "sr_observed": 1.5,
            "sr_baseline": 0.5,
            "dsr_advisory": "DSR robust across tested trials",
        },
    )


def _minimal_config() -> ValidationConfig:
    """Minimal ValidationConfig for report rendering tests."""
    return ValidationConfig(
        config_path=Path("/tmp/candidate.yaml"),
        baseline_config_path=Path("/tmp/baseline.yaml"),
        strategy_name="test_cand",
        baseline_name="test_base",
        dataset=Path("/tmp/data.csv"),
        start="2019-01-01",
        end="2026-02-20",
        outdir=Path("/tmp/out"),
        suite="basic",
        scenarios=["base", "harsh"],
        command=["validate_strategy.py"],
        seed=42,
    )


# ── Fix 1: selection_bias fallback bypass ────────────────────────────────


class TestSelectionBiasFallbackBypass:
    def test_pbo_fallback_holds_despite_psr_pass(self) -> None:
        """Fix 1: method fallback → HOLD even when PSR passes."""
        results = {"selection_bias": _make_sb_psr_with_fallback(psr_pass=True)}
        verdict = evaluate_decision(results)

        assert verdict.tag == "HOLD"
        assert verdict.exit_code == 1
        gate = next(g for g in verdict.gates if g.gate_name == "selection_bias")
        assert gate.passed is False
        assert "selection_bias_method_fallback" in verdict.failures
        assert "fallback" in gate.detail.lower()

    def test_no_fallback_psr_pass_promotes(self) -> None:
        """Fix 1 baseline: no fallback + PSR pass → PROMOTE (diagnostic, info)."""
        results = {"selection_bias": _make_sb_psr_no_fallback(psr_pass=True)}
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE"
        gate = next(g for g in verdict.gates if g.gate_name == "selection_bias")
        assert gate.passed is True
        assert gate.severity == "info"

    def test_no_fallback_psr_fail_diagnostic_only(self) -> None:
        """Fix 1 baseline: no fallback + PSR fail → PROMOTE (PSR is diagnostic).

        PSR was demoted from binding soft gate to info diagnostic (2026-03-16).
        PSR treats sr_benchmark as known constant — anti-conservative for
        2-strategy comparison.  PSR fail without method_fallback does not block
        PROMOTE; WFO Wilcoxon + Bootstrap CI are the binding authority.
        """
        results = {
            "selection_bias": _make_sb_psr_no_fallback(psr_pass=False, psr_value=0.80),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE"
        assert "selection_bias_psr_insufficient" not in verdict.failures
        gate = next(g for g in verdict.gates if g.gate_name == "selection_bias")
        assert gate.severity == "info"
        assert gate.passed is True
        assert "warning" in gate.detail  # PSR=0.80 < 0.90 → "warning" level

    def test_method_mismatch_without_fallback_reason_holds(self) -> None:
        """Fix 1: requested != actual method (even without explicit fallback_reason) → HOLD."""
        results = {
            "selection_bias": SuiteResult(
                name="selection_bias",
                status="info",
                data={
                    "requested_method": "pbo",
                    "method": "none",
                    # No fallback_reason key — detected via method mismatch
                    "risk_statement": "CAUTION — some fallback",
                    "psr": {"psr": 0.9999},
                    "psr_pass": True,
                    "sr_observed": 1.5,
                    "sr_baseline": 0.5,
                },
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "HOLD"
        assert "selection_bias_method_fallback" in verdict.failures

    def test_strict_bool_string_true_diagnostic_correct(self) -> None:
        """Fix 1: psr_pass='True' (string) → _strict_bool→False in diagnostics.

        PSR is now diagnostic (info, no veto), so gate.passed is always True
        (no method_fallback, no PBO fail).  But the diagnostic detail should
        reflect the correct _strict_bool interpretation of psr_pass.
        """
        results = {
            "selection_bias": SuiteResult(
                name="selection_bias",
                status="pass",
                data={
                    "requested_method": "deflated",
                    "method": "deflated",
                    "risk_statement": "PASS",
                    "psr": {"psr": 0.9999},
                    "psr_pass": "True",  # string, not bool
                    "sr_observed": 1.5,
                    "sr_baseline": 0.5,
                },
            ),
        }
        verdict = evaluate_decision(results)

        gate = next(g for g in verdict.gates if g.gate_name == "selection_bias")
        # PSR is diagnostic — gate always passes (no veto power)
        assert gate.passed is True
        assert gate.severity == "info"
        # _strict_bool("True") → False → psr_pass recorded as False in deltas
        assert verdict.deltas.get("selection_bias_psr_pass") is False


# ── Fix 2: PBO proxy sentinel filtering ──────────────────────────────────


class TestPBOSentinelFiltering:
    """Fix 2: Rejected windows (score ≤ -999,999) excluded from PBO deltas."""

    def test_sentinel_threshold_catches_reject(self) -> None:
        """Fix 2: The threshold -999,999 correctly catches -1,000,000."""
        from validation.suites.selection_bias import _OBJECTIVE_REJECT_THRESHOLD

        assert -1_000_000.0 <= _OBJECTIVE_REJECT_THRESHOLD

    def test_all_windows_rejected_triggers_fallback(self) -> None:
        """Fix 2: When PBO has n_windows=0 (all rejected), decision sees fallback."""
        results = {
            "selection_bias": SuiteResult(
                name="selection_bias",
                status="info",
                data={
                    "requested_method": "pbo",
                    "method": "none",
                    "fallback_reason": "no_wfo_windows_for_pbo",
                    "risk_statement": "CAUTION — fallback to none: PBO requires valid WFO windows",
                    "psr": {"psr": 0.9999},
                    "psr_pass": True,
                    "sr_observed": 1.5,
                    "sr_baseline": 0.5,
                    "pbo_proxy": {
                        "n_windows": 0,
                        "n_windows_rejected": 4,
                        "negative_delta_ratio": None,
                    },
                },
            ),
        }
        verdict = evaluate_decision(results)
        # Fallback detected → HOLD regardless of PSR
        assert verdict.tag == "HOLD"
        assert "selection_bias_method_fallback" in verdict.failures

    def test_pbo_overfitting_holds_without_psr(self) -> None:
        """PBO overfitting gate: PBO > 0.5 → HOLD even when PSR passes.

        PBO overfitting is a binding soft gate independent of PSR.
        PSR is diagnostic only — PBO alone can block PROMOTE.
        """
        results = {
            "selection_bias": SuiteResult(
                name="selection_bias",
                status="info",
                data={
                    "requested_method": "pbo",
                    "method": "pbo",
                    "risk_statement": "PBO FAIL",
                    "psr": {"psr": 0.9999},
                    "psr_pass": True,
                    "sr_observed": 1.5,
                    "sr_baseline": 0.5,
                    "pbo_proxy": {
                        "n_windows": 8,
                        "n_windows_rejected": 0,
                        "negative_delta_ratio": 0.625,  # > 0.50 → FAIL
                    },
                },
            ),
        }
        verdict = evaluate_decision(results)
        assert verdict.tag == "HOLD"
        assert "selection_bias_pbo_overfitting" in verdict.failures
        gate = next(g for g in verdict.gates if g.gate_name == "selection_bias")
        assert gate.severity == "soft"
        assert gate.passed is False

    def test_partial_rejection_uses_valid_windows(self) -> None:
        """Fix 2: PBO with some rejected windows still computes from valid ones."""
        results = {
            "selection_bias": SuiteResult(
                name="selection_bias",
                status="pass",
                data={
                    "requested_method": "pbo",
                    "method": "pbo",
                    # No fallback — PBO ran successfully with some windows
                    "risk_statement": "PASS — PSR=0.999 (relative ranking), PBO acceptable",
                    "psr": {"psr": 0.9999},
                    "psr_pass": True,
                    "sr_observed": 1.5,
                    "sr_baseline": 0.5,
                    "pbo_proxy": {
                        "n_windows": 4,
                        "n_windows_rejected": 2,
                        "negative_delta_ratio": 0.25,
                    },
                },
            ),
        }
        verdict = evaluate_decision(results)
        # No fallback, PSR passes, PBO acceptable → PROMOTE
        assert verdict.tag == "PROMOTE"


# ── Fix 3: overlap off-by-one ────────────────────────────────────────────


class TestOverlapInclusiveDays:
    def test_same_day_overlap_is_one(self) -> None:
        """Fix 3: If overlap_start == overlap_end, overlap = 1 day (inclusive)."""
        result = _compute_holdout_wfo_overlap(
            {"holdout_start": "2020-06-15", "holdout_end": "2020-06-15"},
            {"windows": [{"test_start": "2020-06-15", "test_end": "2020-06-15"}]},
        )
        assert result["max_overlap_days"] == 1
        assert result["holdout_days"] == 1

    def test_jan_full_month_is_31(self) -> None:
        """Fix 3: Jan 1 through Jan 31 inclusive = 31 days, exceeds >30 threshold."""
        result = _compute_holdout_wfo_overlap(
            {"holdout_start": "2020-01-01", "holdout_end": "2020-01-31"},
            {"windows": [{"test_start": "2020-01-01", "test_end": "2020-01-31"}]},
        )
        assert result["max_overlap_days"] == 31
        assert result["holdout_days"] == 31

    def test_no_overlap_is_zero(self) -> None:
        """Fix 3: Disjoint periods still produce 0."""
        result = _compute_holdout_wfo_overlap(
            {"holdout_start": "2020-06-01", "holdout_end": "2020-06-30"},
            {"windows": [{"test_start": "2020-07-01", "test_end": "2020-07-31"}]},
        )
        assert result["max_overlap_days"] == 0

    def test_adjacent_days_no_overlap(self) -> None:
        """Fix 3: holdout ends day before window starts → 0 overlap."""
        result = _compute_holdout_wfo_overlap(
            {"holdout_start": "2020-01-01", "holdout_end": "2020-01-15"},
            {"windows": [{"test_start": "2020-01-16", "test_end": "2020-01-31"}]},
        )
        assert result["max_overlap_days"] == 0


# ── Fix 4: warnings/errors rendered in report ────────────────────────────


class TestReportRendersWarningsErrors:
    def test_warnings_rendered(self) -> None:
        """Fix 4: decision.warnings appear in validation_report.md."""
        decision = DecisionVerdict(
            tag="PROMOTE",
            exit_code=0,
            warnings=["overlap-detected-42-days", "some-other-warning"],
            errors=[],
            reasons=["All configured decision gates passed"],
        )
        results: dict[str, SuiteResult] = {}
        config = _minimal_config()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            text = path.read_text()

        assert "overlap-detected-42-days" in text
        assert "some-other-warning" in text
        assert "### Warnings" in text

    def test_errors_rendered(self) -> None:
        """Fix 4: decision.errors appear in validation_report.md."""
        decision = DecisionVerdict(
            tag="ERROR",
            exit_code=3,
            warnings=[],
            errors=["regression_guard:sharpe", "invariants:nav_negative:1"],
            reasons=["Validation failed"],
        )
        results: dict[str, SuiteResult] = {}
        config = _minimal_config()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            text = path.read_text()

        assert "regression_guard:sharpe" in text
        assert "### Errors" in text

    def test_no_warnings_no_section(self) -> None:
        """Fix 4: empty warnings/errors → no spurious section."""
        decision = DecisionVerdict(
            tag="PROMOTE",
            exit_code=0,
            warnings=[],
            errors=[],
            reasons=["All configured decision gates passed"],
        )
        results: dict[str, SuiteResult] = {}
        config = _minimal_config()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            text = path.read_text()

        assert "### Warnings" not in text
        assert "### Errors" not in text

    def test_gate_detail_pipe_escaped(self) -> None:
        """Audit: pipe characters in gate detail must be escaped for markdown table."""
        decision = DecisionVerdict(
            tag="HOLD",
            exit_code=1,
            gates=[
                GateCheck(
                    gate_name="test_gate",
                    passed=False,
                    severity="soft",
                    detail="field_a|field_b=True",
                ),
            ],
            warnings=[],
            errors=[],
            reasons=["gate failed"],
        )
        results: dict[str, SuiteResult] = {}
        config = _minimal_config()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            text = path.read_text()

        # The pipe should be escaped so the table renders correctly.
        # In the raw markdown text, \\| is a literal backslash + pipe which
        # markdown renderers treat as an escaped (non-structural) pipe.
        assert "field_a\\|field_b=True" in text
        # Verify the raw pipe is NOT present unescaped (which would break
        # the table into extra columns for a markdown parser).
        gate_lines = [
            line for line in text.split("\n")
            if "test_gate" in line and line.startswith("|")
        ]
        assert len(gate_lines) == 1
        # The escaped pipe \| counts as a literal char in the string, so raw
        # count is 6 (5 structural + 1 escaped).  Confirm the escaped form
        # is present rather than an unescaped bare pipe.
        assert "\\|" in gate_lines[0]
