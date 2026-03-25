"""Tests for holdout / WFO overlap detection and correlated-failure handling.

Scenarios:
  OV1: No overlap → no warning, gates independent
  OV2: Overlap 45 days (>30) → WARNING logged, but gates still independent
  OV3: Both fail + overlap >50% → WFO downgraded to info (correlated)
  OV4: Only holdout fails + overlap >50% → WFO stays soft (no correlation)
  OV5: Only WFO fails + overlap >50% → WFO stays soft (no correlation)
  OV6: Overlap helper with no holdout dates → graceful zero
"""

from __future__ import annotations

from validation.decision import (
    _compute_holdout_wfo_overlap,
    evaluate_decision,
)
from validation.suites.base import SuiteResult


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_holdout(*, delta: float, start: str, end: str) -> SuiteResult:
    return SuiteResult(
        name="holdout",
        status="pass" if delta >= -0.2 else "fail",
        data={
            "holdout_start": start,
            "holdout_end": end,
            "delta_harsh_score": delta,
        },
    )


def _make_wfo(
    *,
    status: str = "pass",
    windows: list[dict] | None = None,
    n_windows: int = 8,
    positive_windows: int = 6,
    win_rate: float = 0.75,
    power_windows: int = 8,
) -> SuiteResult:
    if windows is None:
        windows = []
    return SuiteResult(
        name="wfo",
        status=status,
        data={
            "summary": {
                "n_windows": n_windows,
                "n_windows_valid": n_windows,
                "positive_delta_windows": positive_windows,
                "win_rate": win_rate,
                "low_trade_windows_count": 0,
                "stats_power_only": {"n_windows": power_windows},
                "wilcoxon": {
                    "p_value": 0.07 if status == "pass" else 0.40,
                    "statistic": 29.0,
                    "n_nonzero": 8,
                    "sufficient": True,
                },
                "bootstrap_ci": {
                    "ci_lower": 1.0 if status == "pass" else -5.0,
                    "ci_upper": 20.0,
                    "mean_delta": 10.0,
                    "excludes_zero": status == "pass",
                    "n": 8,
                },
            },
            "windows": windows,
        },
    )


WFO_WINDOWS_NO_OVERLAP = [
    {"window_id": i, "test_start": f"202{i}-01-01", "test_end": f"202{i}-07-01", "valid_window": True}
    for i in range(2, 6)
]

WFO_WINDOWS_PARTIAL_OVERLAP = [
    {"window_id": 0, "test_start": "2022-01-01", "test_end": "2022-07-01", "valid_window": True},
    {"window_id": 1, "test_start": "2022-07-01", "test_end": "2023-01-01", "valid_window": True},
    {"window_id": 2, "test_start": "2025-06-01", "test_end": "2025-12-01", "valid_window": True},
    # ↑ overlaps holdout 2025-07-15→2026-02-15 by ~139 days (Jun 1→Dec 1 ∩ Jul 15→Feb 15)
    # Actually: overlap = max(Jul15, Jun1)=Jul15 → min(Dec1, Feb15)=Dec1 = 139 days
]

WFO_WINDOWS_MAJOR_OVERLAP = [
    {"window_id": 0, "test_start": "2022-01-01", "test_end": "2022-07-01", "valid_window": True},
    {"window_id": 1, "test_start": "2025-07-01", "test_end": "2026-01-01", "valid_window": True},
    # ↑ overlaps holdout 2025-07-15→2026-02-15: Jul15→Jan1 = 170 days
    # holdout = 215 days, so 170/215 = 79.1%
]


# ── OV1: no overlap ─────────────────────────────────────────────────────


class TestNoOverlap:
    def test_no_overlap_no_warning(self) -> None:
        """OV1: Disjoint periods → no overlap warning."""
        results = {
            "holdout": _make_holdout(delta=0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(windows=WFO_WINDOWS_NO_OVERLAP),
        }
        verdict = evaluate_decision(results)
        assert verdict.deltas.get("holdout_wfo_max_overlap_days", 0) == 0
        assert "holdout_wfo_overlap_warnings" not in verdict.deltas

    def test_no_overlap_gates_independent(self) -> None:
        """OV1: Gates remain at original severity."""
        results = {
            "holdout": _make_holdout(delta=0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="fail", windows=WFO_WINDOWS_NO_OVERLAP,
                             positive_windows=3, win_rate=0.375),
        }
        verdict = evaluate_decision(results)
        wfo_gate = next(g for g in verdict.gates if g.gate_name == "wfo_robustness")
        assert wfo_gate.severity == "soft"
        assert not wfo_gate.passed


# ── OV2: overlap >30d but <50%, both pass ────────────────────────────────


class TestPartialOverlapWarning:
    def test_overlap_warning_logged(self) -> None:
        """OV2: Overlap >30d → warning in deltas."""
        results = {
            "holdout": _make_holdout(delta=0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(windows=WFO_WINDOWS_PARTIAL_OVERLAP),
        }
        verdict = evaluate_decision(results)
        assert verdict.deltas["holdout_wfo_max_overlap_days"] > 30
        assert "holdout_wfo_overlap_warnings" in verdict.deltas
        warnings = verdict.deltas["holdout_wfo_overlap_warnings"]
        assert any("overlap detected" in w.lower() for w in warnings)

    def test_overlap_warning_gates_independent_when_both_pass(self) -> None:
        """OV2: Both pass → no correlation note even with overlap."""
        results = {
            "holdout": _make_holdout(delta=0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(windows=WFO_WINDOWS_PARTIAL_OVERLAP),
        }
        verdict = evaluate_decision(results)
        warnings = verdict.deltas.get("holdout_wfo_overlap_warnings", [])
        assert not any("NOT independent" in w for w in warnings)


# ── OV3: both fail + overlap >50% → correlated ──────────────────────────


class TestCorrelatedFailures:
    def test_wfo_downgraded_to_info(self) -> None:
        """OV3: Both fail + overlap >50% → WFO severity=info."""
        results = {
            "holdout": _make_holdout(delta=-0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="fail", windows=WFO_WINDOWS_MAJOR_OVERLAP,
                             positive_windows=3, win_rate=0.375),
        }
        verdict = evaluate_decision(results)
        wfo_gate = next(g for g in verdict.gates if g.gate_name == "wfo_robustness")
        assert wfo_gate.severity == "info"
        assert "CORRELATED" in wfo_gate.detail

    def test_wfo_removed_from_failures(self) -> None:
        """OV3: WFO failure not in failures list (not double-counted)."""
        results = {
            "holdout": _make_holdout(delta=-0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="fail", windows=WFO_WINDOWS_MAJOR_OVERLAP,
                             positive_windows=3, win_rate=0.375),
        }
        verdict = evaluate_decision(results)
        assert "wfo_robustness_failed" not in verdict.failures

    def test_correlation_note_in_warnings(self) -> None:
        """OV3: Correlation note present in deltas."""
        results = {
            "holdout": _make_holdout(delta=-0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="fail", windows=WFO_WINDOWS_MAJOR_OVERLAP,
                             positive_windows=3, win_rate=0.375),
        }
        verdict = evaluate_decision(results)
        warnings = verdict.deltas["holdout_wfo_overlap_warnings"]
        assert any("NOT independent" in w for w in warnings)
        assert any("same market event" in w for w in warnings)

    def test_metadata_correlated_flag(self) -> None:
        """OV3: metadata.holdout_wfo_correlated = True."""
        results = {
            "holdout": _make_holdout(delta=-0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="fail", windows=WFO_WINDOWS_MAJOR_OVERLAP,
                             positive_windows=3, win_rate=0.375),
        }
        verdict = evaluate_decision(results)
        assert verdict.metadata["holdout_wfo_correlated"] is True

    def test_tag_still_reject_from_holdout(self) -> None:
        """OV3: Holdout hard-fail still drives REJECT (not demoted)."""
        results = {
            "holdout": _make_holdout(delta=-0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="fail", windows=WFO_WINDOWS_MAJOR_OVERLAP,
                             positive_windows=3, win_rate=0.375),
        }
        verdict = evaluate_decision(results)
        assert verdict.tag == "REJECT"
        # But only 1 hard failure, not 1 hard + 1 soft
        assert verdict.metadata["n_soft_fail"] == 0


# ── OV4: only holdout fails + overlap >50% → no correlation ─────────────


class TestOnlyHoldoutFails:
    def test_wfo_stays_soft_when_it_passes(self) -> None:
        """OV4: WFO passes → no downgrade even with overlap."""
        results = {
            "holdout": _make_holdout(delta=-0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="pass", windows=WFO_WINDOWS_MAJOR_OVERLAP),
        }
        verdict = evaluate_decision(results)
        wfo_gate = next(g for g in verdict.gates if g.gate_name == "wfo_robustness")
        assert wfo_gate.passed is True
        assert verdict.metadata["holdout_wfo_correlated"] is False


# ── OV5: only WFO fails + overlap >50% → no correlation ─────────────────


class TestOnlyWfoFails:
    def test_wfo_stays_soft_when_holdout_passes(self) -> None:
        """OV5: Holdout passes → WFO failure stays independent."""
        results = {
            "holdout": _make_holdout(delta=0.5, start="2025-07-15", end="2026-02-15"),
            "wfo": _make_wfo(status="fail", windows=WFO_WINDOWS_MAJOR_OVERLAP,
                             positive_windows=3, win_rate=0.375),
        }
        verdict = evaluate_decision(results)
        wfo_gate = next(g for g in verdict.gates if g.gate_name == "wfo_robustness")
        assert wfo_gate.severity == "soft"
        assert not wfo_gate.passed
        assert verdict.metadata["holdout_wfo_correlated"] is False
        assert verdict.tag == "HOLD"


# ── OV6: overlap helper edge cases ──────────────────────────────────────


class TestOverlapHelper:
    def test_missing_holdout_dates(self) -> None:
        """OV6: No holdout dates → zero overlap."""
        result = _compute_holdout_wfo_overlap({}, {"windows": WFO_WINDOWS_MAJOR_OVERLAP})
        assert result["max_overlap_days"] == 0

    def test_missing_wfo_windows(self) -> None:
        """OV6: No WFO windows → zero overlap."""
        result = _compute_holdout_wfo_overlap(
            {"holdout_start": "2025-07-15", "holdout_end": "2026-02-15"},
            {"windows": []},
        )
        assert result["max_overlap_days"] == 0

    def test_exact_overlap_calculation(self) -> None:
        """OV6: Verify exact overlap days (inclusive end dates)."""
        result = _compute_holdout_wfo_overlap(
            {"holdout_start": "2025-07-15", "holdout_end": "2026-02-15"},
            {"windows": [
                {"test_start": "2025-07-01", "test_end": "2026-01-01"},
            ]},
        )
        # overlap: max(Jul15, Jul1)=Jul15 → min(Feb15, Jan1)=Jan1 = 171 days (inclusive)
        assert result["max_overlap_days"] == 171
        # holdout = Jul15→Feb15 inclusive = 216 days, pct = 171/216 = 79.2%
        assert result["holdout_days"] == 216
        assert abs(result["max_overlap_pct"] - 79.2) < 0.2

    def test_exact_boundary_31_days(self) -> None:
        """OV6: 31 inclusive days must exceed >30 threshold."""
        result = _compute_holdout_wfo_overlap(
            {"holdout_start": "2020-01-01", "holdout_end": "2020-01-31"},
            {"windows": [
                {"test_start": "2020-01-01", "test_end": "2020-01-31"},
            ]},
        )
        # Jan 1 through Jan 31 inclusive = 31 days
        assert result["max_overlap_days"] == 31
        assert result["holdout_days"] == 31
