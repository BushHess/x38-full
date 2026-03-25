"""Tests for the machine-only Pair Diagnostic Harness (Phase 2).

Test IDs map to the patch plan (Report 22B):
  T8:  test_diagnostic_result_schema_no_decision
  T9:  test_json_output_schema_no_decision_key
  T10: test_pair_profile_tolerance_not_exact
  T11: test_classify_a0_vs_a1_near_identical
  T12: test_classify_a0_vs_vbreak_materially_different
  T13: test_classify_borderline_case
  T14: test_route_near_identical_no_action
  T15: test_route_near_identical_escalate
  T16: test_route_borderline_always_escalate
  T17: test_route_materially_different_consensus_fail
  T18: test_markdown_template_has_blank_human_section

Additional tests beyond the plan:
  test_subsampling_unreliable_when_1bp_above_80
  test_subsampling_reliable_when_1bp_below_80
  test_route_materially_different_many_caveats
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, fields

import numpy as np
import pytest

from research.lib.pair_diagnostic import (
    ROUTE_ESCALATE_EVENT,
    ROUTE_ESCALATE_FULL,
    ROUTE_INCONCLUSIVE,
    ROUTE_NO_ACTION,
    PairClassification,
    PairDiagnosticResult,
    PairProfile,
    classify_pair,
    compute_pair_profile,
    render_review_template,
    suggest_review_route,
)

# ── Helpers ──


def _make_profile(
    *,
    near_equal_1bp_rate: float = 0.50,
    return_correlation: float = 0.50,
    n_bars: int = 1000,
    equal_rate_tol: float = 0.0,
    near_equal_10bp_rate: float = 0.50,
    same_direction_rate: float = 0.50,
    exposure_agreement_rate: float = float("nan"),
) -> PairProfile:
    """Create a PairProfile with specified values for testing."""
    return PairProfile(
        n_bars=n_bars,
        equal_rate_tol=equal_rate_tol,
        near_equal_1bp_rate=near_equal_1bp_rate,
        near_equal_10bp_rate=near_equal_10bp_rate,
        same_direction_rate=same_direction_rate,
        return_correlation=return_correlation,
        exposure_agreement_rate=exposure_agreement_rate,
    )


def _make_diagnostic(
    *,
    pair_class: str = "materially_different",
    near_equal_1bp_rate: float = 0.50,
    return_correlation: float = 0.50,
    boot_sharpe_p: float = 0.60,
    boot_geo_p: float = 0.60,
    sub_p: float = 0.60,
    consensus_ok: bool = True,
    caveats: list[str] | None = None,
    suggested_route: str = ROUTE_INCONCLUSIVE,
    route_reason: str = "test",
) -> PairDiagnosticResult:
    """Create a PairDiagnosticResult with specified values for testing."""
    profile = _make_profile(
        near_equal_1bp_rate=near_equal_1bp_rate,
        return_correlation=return_correlation,
    )
    classification = PairClassification(
        pair_class=pair_class,
        subsampling_reliable=near_equal_1bp_rate <= 0.80,
        primary_reason="test",
    )
    return PairDiagnosticResult(
        label_a="A",
        label_b="B",
        profile=profile,
        classification=classification,
        boot_sharpe_p=boot_sharpe_p,
        boot_sharpe_ci_lower=-0.5,
        boot_sharpe_ci_upper=0.5,
        boot_sharpe_ci_width=1.0,
        boot_sharpe_observed_delta=0.1,
        boot_geo_p=boot_geo_p,
        boot_geo_ci_lower=-0.01,
        boot_geo_ci_upper=0.01,
        sub_p=sub_p,
        sub_ci_lower=-0.1,
        sub_ci_upper=0.1,
        sub_support=0.0,
        consensus_gap_pp=abs(boot_geo_p - sub_p) * 100.0,
        consensus_ok=consensus_ok,
        dsr_a={27: 0.95, 54: 0.90},
        dsr_b={27: 0.85, 54: 0.80},
        caveats=caveats or [],
        suggested_route=suggested_route,
        route_reason=route_reason,
        bootstrap_config={"n_bootstrap": 100, "block_sizes": [10], "seed": 42},
        timestamp_utc="2026-03-03T00:00:00+00:00",
    )


# ── T8: Schema validation — no decision field ──


class TestDiagnosticSchema:
    def test_diagnostic_result_schema_no_decision(self) -> None:
        """T8: PairDiagnosticResult has no decision/promote/reject/verdict/recommendation."""
        forbidden = {"decision", "promote", "reject", "verdict",
                      "recommendation", "decision_reasoning"}
        field_names = {f.name for f in fields(PairDiagnosticResult)}
        overlap = forbidden & field_names
        assert overlap == set(), f"Forbidden fields found: {overlap}"

    def test_json_output_schema_no_decision_key(self) -> None:
        """T9: JSON serialization has no key matching decision/promote/reject/verdict."""
        diag = _make_diagnostic()
        d = asdict(diag)
        json_str = str(d)
        forbidden_pattern = re.compile(
            r"'(decision|promote|reject|verdict|recommendation)'", re.IGNORECASE
        )
        matches = forbidden_pattern.findall(json_str)
        assert matches == [], f"Forbidden keys in JSON: {matches}"


# ── T10: Tolerance-based profile ──


class TestPairProfile:
    def test_pair_profile_tolerance_not_exact(self) -> None:
        """T10: compute_pair_profile uses |diff| < tol, never diff == 0."""
        rng = np.random.default_rng(42)
        n = 1000
        base = rng.standard_normal(n) * 0.01
        # Add tiny noise: most diffs are ~1e-8 (below 1bp but above exact)
        returns_a = base.copy()
        returns_b = base + rng.standard_normal(n) * 1e-8

        # With default tolerances
        profile_default = compute_pair_profile(returns_a, returns_b)
        # near_equal_1bp should be ~1.0 (diffs << 1bp)
        assert profile_default.near_equal_1bp_rate > 0.99

        # With custom tight tolerance: 1e-12 (tighter than noise)
        profile_tight = compute_pair_profile(
            returns_a, returns_b, tol_1bp=1e-12,
        )
        # With 1e-12 tolerance, almost nothing should match
        assert profile_tight.near_equal_1bp_rate < 0.10

        # Verify that the rates differ (proving tolerance is used, not raw ==)
        assert profile_default.near_equal_1bp_rate != profile_tight.near_equal_1bp_rate

    def test_subsampling_unreliable_when_1bp_above_80(self) -> None:
        """1bp_rate=0.95 → subsampling_reliable=False."""
        profile = _make_profile(near_equal_1bp_rate=0.95, return_correlation=0.50)
        classification = classify_pair(profile)
        assert classification.subsampling_reliable is False

    def test_subsampling_reliable_when_1bp_below_80(self) -> None:
        """1bp_rate=0.73 → subsampling_reliable=True."""
        profile = _make_profile(near_equal_1bp_rate=0.73, return_correlation=0.50)
        classification = classify_pair(profile)
        assert classification.subsampling_reliable is True


# ── T11–T13: Pair classification ──


class TestClassifyPair:
    def test_classify_a0_vs_a1_near_identical(self) -> None:
        """T11: 1bp=0.989, corr=0.987 → near_identical."""
        profile = _make_profile(near_equal_1bp_rate=0.989, return_correlation=0.987)
        result = classify_pair(profile)
        assert result.pair_class == "near_identical"

    def test_classify_a0_vs_vbreak_materially_different(self) -> None:
        """T12: 1bp=0.735, corr=0.735 → materially_different."""
        profile = _make_profile(near_equal_1bp_rate=0.735, return_correlation=0.735)
        result = classify_pair(profile)
        assert result.pair_class == "materially_different"

    def test_classify_borderline_case(self) -> None:
        """T13: 1bp=0.83, corr=0.60 → borderline (1bp > 0.80 triggers)."""
        profile = _make_profile(near_equal_1bp_rate=0.83, return_correlation=0.60)
        result = classify_pair(profile)
        assert result.pair_class == "borderline"

    def test_classify_borderline_by_corr(self) -> None:
        """Corr=0.92 with low 1bp still triggers borderline."""
        profile = _make_profile(near_equal_1bp_rate=0.50, return_correlation=0.92)
        result = classify_pair(profile)
        assert result.pair_class == "borderline"


# ── T14–T17: Review routes ──


class TestSuggestReviewRoute:
    def test_route_near_identical_no_action(self) -> None:
        """T14: near_identical + boot_p≈0.5 → no_action_default."""
        classification = PairClassification(
            pair_class="near_identical",
            subsampling_reliable=False,
            primary_reason="test",
        )
        route, _ = suggest_review_route(classification, boot_sharpe_p=0.47,
                                         consensus_ok=True, caveats=[])
        assert route == ROUTE_NO_ACTION

    def test_route_near_identical_escalate(self) -> None:
        """T15: near_identical + boot_p=0.72 → escalate_event_review (anomalous)."""
        classification = PairClassification(
            pair_class="near_identical",
            subsampling_reliable=False,
            primary_reason="test",
        )
        route, _ = suggest_review_route(classification, boot_sharpe_p=0.72,
                                         consensus_ok=True, caveats=[])
        assert route == ROUTE_ESCALATE_EVENT

    def test_route_borderline_always_escalate(self) -> None:
        """T16: borderline → escalate_full regardless of diagnostics."""
        classification = PairClassification(
            pair_class="borderline",
            subsampling_reliable=True,
            primary_reason="test",
        )
        route, _ = suggest_review_route(classification, boot_sharpe_p=0.50,
                                         consensus_ok=True, caveats=[])
        assert route == ROUTE_ESCALATE_FULL

    def test_route_materially_different_consensus_fail(self) -> None:
        """T17: materially_different + consensus_ok=False → escalate_event."""
        classification = PairClassification(
            pair_class="materially_different",
            subsampling_reliable=True,
            primary_reason="test",
        )
        route, _ = suggest_review_route(classification, boot_sharpe_p=0.80,
                                         consensus_ok=False, caveats=[])
        assert route == ROUTE_ESCALATE_EVENT

    def test_route_materially_different_many_caveats(self) -> None:
        """materially_different + >2 caveats → escalate_full."""
        classification = PairClassification(
            pair_class="materially_different",
            subsampling_reliable=True,
            primary_reason="test",
        )
        route, _ = suggest_review_route(
            classification, boot_sharpe_p=0.80, consensus_ok=True,
            caveats=["a", "b", "c"],
        )
        assert route == ROUTE_ESCALATE_FULL

    def test_route_materially_different_inconclusive(self) -> None:
        """materially_different + consensus OK + <=2 caveats → inconclusive."""
        classification = PairClassification(
            pair_class="materially_different",
            subsampling_reliable=True,
            primary_reason="test",
        )
        route, _ = suggest_review_route(
            classification, boot_sharpe_p=0.80, consensus_ok=True,
            caveats=["a"],
        )
        assert route == ROUTE_INCONCLUSIVE


# ── T18: Markdown template ──


class TestRenderReviewTemplate:
    def test_markdown_template_has_blank_human_section(self) -> None:
        """T18: Template has blank Section 2 with no pre-filled decision."""
        diag = _make_diagnostic()
        template = render_review_template(diag)

        # Section 2 header exists
        assert "## Section 2: Human Review Note" in template

        # Decision field is blank (markdown bold: **Decision**)
        assert "**Decision**: ___" in template

        # Reasoning field has placeholder
        assert "[Explain which diagnostics" in template

        # No pre-filled decision value in Section 2
        section2_start = template.index("## Section 2")
        section2 = template[section2_start:]
        for forbidden in ["PROMOTE", "REJECT", "NO_ACTION", "INCONCLUSIVE"]:
            # These should NOT appear after Section 2 header (they're options text)
            # But the "Options:" line lists them as choices — that's OK
            # Check that they don't appear as a filled-in Decision value
            pass

        # The Decision line should have blanks, not a filled value
        decision_line = [
            line for line in section2.split("\n")
            if line.startswith("**Decision**:")
        ]
        assert len(decision_line) == 1
        assert "___" in decision_line[0]

    def test_markdown_template_has_section1_filled(self) -> None:
        """Section 1 should contain auto-filled diagnostic values."""
        diag = _make_diagnostic(boot_sharpe_p=0.818)
        template = render_review_template(diag)

        assert "## Section 1: Machine Diagnostic" in template
        assert "0.818" in template
        assert "**Classification**:" in template
        assert "**Bootstrap (Sharpe)**:" in template
