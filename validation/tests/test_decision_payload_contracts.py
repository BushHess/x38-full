"""Payload contract tests for authoritative decision gates (Report 30).

Tests what happens when authoritative suites produce missing, malformed,
NaN, inf, or non-numeric decisive fields.  Each test classifies the path
as fail-open (bug) or fail-closed (correct).

Test ID mapping (Report 30):
  BT1: test_backtest_missing_delta_is_contract_error
  BT2: test_backtest_nan_delta_is_contract_error
  BT3: test_backtest_inf_delta_is_contract_error
  BT4: test_backtest_neg_inf_delta_is_contract_error
  BT5: test_backtest_non_numeric_delta_is_contract_error
  HO1: test_holdout_missing_delta_is_contract_error
  HO2: test_holdout_nan_delta_is_contract_error
  HO3: test_holdout_inf_delta_is_contract_error
  HO4: test_holdout_neg_inf_delta_is_contract_error
  HO5: test_holdout_non_numeric_delta_is_contract_error
  WF1: test_wfo_empty_summary_triggers_low_power
  WF2: test_wfo_nan_win_rate_fails_gate
  TL1: test_trade_level_nan_ci_upper_no_silent_pass
  TL2: test_trade_level_bootstrap_nan_ci_under_low_power_holds
  TL3: test_trade_level_bootstrap_missing_ci_fields_under_low_power
  TL4: test_trade_level_empty_payload_normal_wfo_no_gate
  TL5: test_trade_level_empty_payload_low_power_holds
  SB1: test_selection_bias_empty_risk_statement_passes
  SB2: test_selection_bias_none_risk_statement_passes
  SB3: test_selection_bias_whitespace_risk_statement_passes
  SB4: test_selection_bias_caution_case_insensitive
  QP1: test_data_integrity_missing_hard_fail_quality_catches
  QP2: test_data_integrity_string_hard_fail_true
  QP3: test_invariants_missing_n_violations_status_fail_errors
  QP4: test_invariants_non_numeric_n_violations_status_fail
  QP5: test_regression_guard_missing_pass_falls_back_to_status
  SF1: test_safe_float_nan_returns_default
  SF2: test_safe_float_inf_returns_default
  SF3: test_safe_float_neg_inf_returns_default
  SF4: test_safe_float_non_numeric_returns_default
  RD1: test_require_decisive_float_none_returns_none
  RD2: test_require_decisive_float_nan_returns_none
  RD3: test_require_decisive_float_valid_returns_float
  RD4: test_require_decisive_float_string_returns_none
"""

from __future__ import annotations

from validation.decision import _require_decisive_float
from validation.decision import _safe_float
from validation.decision import evaluate_decision
from validation.suites.base import SuiteResult

# ── Helpers ──────────────────────────────────────────────────────────────


def _backtest_with_delta(value) -> SuiteResult:
    """Backtest with a specific score_delta value (may be non-numeric)."""
    return SuiteResult(
        name="backtest",
        status="pass",
        data={"deltas": {"harsh": {"score_delta": value}}},
    )


def _backtest_empty() -> SuiteResult:
    """Backtest that ran but produced no deltas."""
    return SuiteResult(name="backtest", status="pass", data={})


def _holdout_with_delta(value) -> SuiteResult:
    return SuiteResult(
        name="holdout",
        status="pass",
        data={"delta_harsh_score": value},
    )


def _holdout_empty() -> SuiteResult:
    return SuiteResult(name="holdout", status="pass", data={})


def _wfo_normal() -> SuiteResult:
    return SuiteResult(
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
    )


def _wfo_low_power() -> SuiteResult:
    return SuiteResult(
        name="wfo",
        status="pass",
        data={
            "summary": {
                "n_windows": 2,
                "n_windows_valid": 2,
                "positive_delta_windows": 0,
                "win_rate": 0.0,
                "low_trade_windows_count": 2,
                "stats_power_only": {"n_windows": 1},
            },
        },
    )


def _passing_baseline() -> dict[str, SuiteResult]:
    """Minimal passing results: backtest(+5) + wfo(normal)."""
    return {
        "backtest": _backtest_with_delta(5.0),
        "wfo": _wfo_normal(),
    }


# ── BT: Backtest Contract ───────────────────────────────────────────────


class TestBacktestContract:
    def test_backtest_missing_delta_is_contract_error(self) -> None:
        """BT1: backtest present but no score_delta → ERROR(3)."""
        results = {"backtest": _backtest_empty(), "wfo": _wfo_normal()}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "backtest_payload_contract_breach" in v.failures

    def test_backtest_nan_delta_is_contract_error(self) -> None:
        """BT2: score_delta=NaN → ERROR(3)."""
        results = {"backtest": _backtest_with_delta(float("nan")), "wfo": _wfo_normal()}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "backtest_payload_contract_breach" in v.failures

    def test_backtest_inf_delta_is_contract_error(self) -> None:
        """BT3: score_delta=inf → ERROR(3)."""
        results = {"backtest": _backtest_with_delta(float("inf")), "wfo": _wfo_normal()}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "backtest_payload_contract_breach" in v.failures

    def test_backtest_neg_inf_delta_is_contract_error(self) -> None:
        """BT4: score_delta=-inf → ERROR(3)."""
        results = {"backtest": _backtest_with_delta(float("-inf")), "wfo": _wfo_normal()}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "backtest_payload_contract_breach" in v.failures

    def test_backtest_non_numeric_delta_is_contract_error(self) -> None:
        """BT5: score_delta='abc' → ERROR(3)."""
        results = {"backtest": _backtest_with_delta("abc"), "wfo": _wfo_normal()}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "backtest_payload_contract_breach" in v.failures

    def test_backtest_valid_negative_delta_rejects(self) -> None:
        """Genuine policy failure: valid delta=-5.0 → REJECT (not ERROR)."""
        results = {"backtest": _backtest_with_delta(-5.0), "wfo": _wfo_normal()}
        v = evaluate_decision(results)
        assert v.tag == "REJECT"
        assert v.exit_code == 2
        assert "full_harsh_delta_below_tolerance" in v.failures


# ── HO: Holdout Contract ────────────────────────────────────────────────


class TestHoldoutContract:
    def test_holdout_missing_delta_is_contract_error(self) -> None:
        """HO1: holdout present but no delta_harsh_score → ERROR(3)."""
        results = {**_passing_baseline(), "holdout": _holdout_empty()}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "holdout_payload_contract_breach" in v.failures

    def test_holdout_nan_delta_is_contract_error(self) -> None:
        """HO2: delta=NaN → ERROR(3)."""
        results = {**_passing_baseline(), "holdout": _holdout_with_delta(float("nan"))}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "holdout_payload_contract_breach" in v.failures

    def test_holdout_inf_delta_is_contract_error(self) -> None:
        """HO3: delta=inf → ERROR(3)."""
        results = {**_passing_baseline(), "holdout": _holdout_with_delta(float("inf"))}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "holdout_payload_contract_breach" in v.failures

    def test_holdout_neg_inf_delta_is_contract_error(self) -> None:
        """HO4: delta=-inf → ERROR(3)."""
        results = {**_passing_baseline(), "holdout": _holdout_with_delta(float("-inf"))}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "holdout_payload_contract_breach" in v.failures

    def test_holdout_non_numeric_delta_is_contract_error(self) -> None:
        """HO5: delta='abc' → ERROR(3)."""
        results = {**_passing_baseline(), "holdout": _holdout_with_delta("abc")}
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "holdout_payload_contract_breach" in v.failures

    def test_holdout_skip_status_not_checked(self) -> None:
        """Holdout with status=skip is NOT evaluated — no contract breach."""
        results = {
            **_passing_baseline(),
            "holdout": SuiteResult(name="holdout", status="skip", data={}),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"
        assert "holdout_payload_contract_breach" not in v.failures


# ── WF: WFO Contract ────────────────────────────────────────────────────


class TestWFOContract:
    def test_wfo_empty_summary_triggers_low_power(self) -> None:
        """WF1: WFO with empty summary → low_power (all zeros → power_windows < 3)."""
        results = {
            **_passing_baseline(),
            "wfo": SuiteResult(name="wfo", status="pass", data={"summary": {}}),
        }
        v = evaluate_decision(results)
        assert v.metadata.get("wfo_low_power") is True
        # Should NOT be PROMOTE — either HOLD (missing tl_bootstrap) or something
        # WFO gate itself passes (low_power → passed=True), but fallback fires
        assert "wfo_low_power_missing_trade_level_bootstrap" in v.failures
        assert v.tag == "HOLD"

    def test_wfo_nan_win_rate_fails_gate(self) -> None:
        """WF2: NaN win_rate → _safe_float→0.0 → fails gate (0.0 < 0.6)."""
        results = {
            **_passing_baseline(),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={
                    "summary": {
                        "n_windows": 10,
                        "n_windows_valid": 10,
                        "positive_delta_windows": 3,
                        "win_rate": float("nan"),
                        "low_trade_windows_count": 0,
                        "stats_power_only": {"n_windows": 10},
                    },
                },
            ),
        }
        v = evaluate_decision(results)
        assert "wfo_robustness_failed" in v.failures


# ── TL: Trade-Level Contract ────────────────────────────────────────────


class TestTradeLevelContract:
    def test_trade_level_nan_ci_upper_no_silent_pass(self) -> None:
        """TL1: NaN ci_upper → _safe_float→0.0 → 0.0 < 0 is False → no gate fired.
        Under normal WFO this is acceptable (trade_level is supplementary)."""
        results = {
            **_passing_baseline(),
            "trade_level": SuiteResult(
                name="trade_level",
                status="info",
                data={
                    "matched_p_positive": 0.55,
                    "matched_block_bootstrap_ci_upper": float("nan"),
                },
            ),
        }
        v = evaluate_decision(results)
        # Should NOT have trade_level_delta_negative (NaN is not < 0)
        assert "trade_level_delta_negative" not in v.failures
        # The p_pos branch fires instead (passed=True)
        tl_gates = [g for g in v.gates if "trade_level" in g.gate_name]
        assert len(tl_gates) == 1
        assert tl_gates[0].passed is True

    def test_trade_level_bootstrap_nan_ci_under_low_power_holds(self) -> None:
        """TL2: NaN ci95 → _safe_float→0.0 → ci_crosses_zero, is_small → HOLD."""
        results = {
            **_passing_baseline(),
            "wfo": _wfo_low_power(),
            "trade_level": SuiteResult(
                name="trade_level",
                status="info",
                data={
                    "trade_level_bootstrap": {
                        "ci95_low": float("nan"),
                        "ci95_high": float("nan"),
                        "mean_diff": float("nan"),
                        "p_gt_0": 0.5,
                        "block_len": 168,
                    },
                },
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "HOLD"
        assert "trade_level_bootstrap_inconclusive" in v.failures

    def test_trade_level_bootstrap_missing_ci_fields_under_low_power(self) -> None:
        """TL3: Missing ci95 fields → _safe_float(None)→0.0 → same as TL2."""
        results = {
            **_passing_baseline(),
            "wfo": _wfo_low_power(),
            "trade_level": SuiteResult(
                name="trade_level",
                status="info",
                data={
                    "trade_level_bootstrap": {
                        # ci95_low, ci95_high, mean_diff all absent
                        "p_gt_0": 0.5,
                        "block_len": 168,
                    },
                },
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "HOLD"
        assert "trade_level_bootstrap_inconclusive" in v.failures

    def test_trade_level_empty_payload_normal_wfo_no_gate(self) -> None:
        """TL4: Empty trade_level data, normal WFO → no trade_level gate emitted."""
        results = {
            **_passing_baseline(),
            "trade_level": SuiteResult(
                name="trade_level", status="info", data={}
            ),
        }
        v = evaluate_decision(results)
        tl_gates = [g for g in v.gates if "trade_level" in g.gate_name]
        assert len(tl_gates) == 0
        # Overall still PROMOTE (no trade_level gate = no failure)
        assert v.tag == "PROMOTE"

    def test_trade_level_empty_payload_low_power_holds(self) -> None:
        """TL5: Empty trade_level data under low-power → fallback HOLD."""
        results = {
            **_passing_baseline(),
            "wfo": _wfo_low_power(),
            "trade_level": SuiteResult(
                name="trade_level", status="info", data={}
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "HOLD"
        assert "wfo_low_power_missing_trade_level_bootstrap" in v.failures


# ── SB: Selection Bias Contract ──────────────────────────────────────────


class TestSelectionBiasContract:
    def test_selection_bias_empty_risk_statement_passes(self) -> None:
        """SB1: Empty string → no CAUTION → passes."""
        results = {
            **_passing_baseline(),
            "selection_bias": SuiteResult(
                name="selection_bias", status="pass", data={"risk_statement": ""}
            ),
        }
        v = evaluate_decision(results)
        assert "selection_bias_caution" not in v.failures

    def test_selection_bias_none_risk_statement_passes(self) -> None:
        """SB2: None risk_statement → str(None)='None', no CAUTION → passes."""
        results = {
            **_passing_baseline(),
            "selection_bias": SuiteResult(
                name="selection_bias", status="pass", data={"risk_statement": None}
            ),
        }
        v = evaluate_decision(results)
        assert "selection_bias_caution" not in v.failures

    def test_selection_bias_whitespace_risk_statement_passes(self) -> None:
        """SB3: Whitespace → no CAUTION/fallback → passes."""
        results = {
            **_passing_baseline(),
            "selection_bias": SuiteResult(
                name="selection_bias", status="pass", data={"risk_statement": "   "}
            ),
        }
        v = evaluate_decision(results)
        assert "selection_bias_caution" not in v.failures

    def test_selection_bias_caution_diagnostic_only(self) -> None:
        """SB4: 'caution' in risk_statement → PROMOTE (PSR is diagnostic, no veto).

        PSR was demoted from binding soft gate to info diagnostic (2026-03-16).
        Legacy CAUTION path no longer gates PROMOTE/HOLD.
        """
        results = {
            **_passing_baseline(),
            "selection_bias": SuiteResult(
                name="selection_bias",
                status="pass",
                data={"risk_statement": "Caution: possible bias"},
            ),
        }
        v = evaluate_decision(results)
        assert "selection_bias_caution" not in v.failures
        assert v.tag == "PROMOTE"


# ── QP: Quality-Policy Authoritative Suites ──────────────────────────────


class TestQualityPolicySuites:
    def test_data_integrity_missing_hard_fail_quality_catches(self) -> None:
        """QP1: data_integrity status='fail' but data={} → evaluate_decision sees
        hard_fail=bool(None)=False → no early exit. Runner quality policy catches
        status='fail' → ERROR(3)."""
        results = {
            **_passing_baseline(),
            "data_integrity": SuiteResult(
                name="data_integrity", status="fail", data={}
            ),
        }
        v = evaluate_decision(results)
        # evaluate_decision does NOT early-exit (hard_fail absent → bool(None)→False)
        # but the data_integrity gate is not a gate in the gate section.
        # The quality policy in the runner catches this. Here we just prove
        # evaluate_decision does not crash and proceeds.
        assert v.tag in {"PROMOTE", "HOLD", "REJECT"}  # not ERROR from evaluate_decision
        # The actual ERROR elevation happens in runner._apply_quality_policy

    def test_data_integrity_string_hard_fail_true(self) -> None:
        """QP2: hard_fail='true' (string) → _strict_bool('true')=False.

        String is not a real boolean; evaluate_decision() does not early-exit.
        Normal gates pass (baseline passes) → PROMOTE. Runner quality policy
        catches status='fail' independently as defense-in-depth.
        """
        results = {
            **_passing_baseline(),
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="fail",
                data={"hard_fail": "true", "hard_fail_reasons": ["test"]},
            ),
        }
        v = evaluate_decision(results)
        # _strict_bool("true") → False → no early exit; normal gates → PROMOTE
        assert v.tag == "PROMOTE"
        assert v.exit_code == 0

    def test_invariants_missing_n_violations_status_fail_errors(self) -> None:
        """QP3: invariants status='fail', n_violations absent → ERROR via status check."""
        results = {
            **_passing_baseline(),
            "invariants": SuiteResult(
                name="invariants", status="fail", data={}
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3

    def test_invariants_non_numeric_n_violations_status_fail(self) -> None:
        """QP4: n_violations='abc', status='fail' → ERROR via status check.
        int('abc') would throw but 'abc' or 0 → 'abc' is truthy → int('abc')
        raises. However status='fail' already matches the OR condition."""
        results = {
            **_passing_baseline(),
            "invariants": SuiteResult(
                name="invariants",
                status="fail",
                data={"n_violations": "abc"},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3

    def test_regression_guard_missing_pass_falls_back_to_status(self) -> None:
        """QP5: No 'pass' key in data → falls back to status=='pass' check."""
        results = {
            **_passing_baseline(),
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={"violated_metrics": [{"metric": "sharpe"}]},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3


# ── SF: _safe_float Tests ────────────────────────────────────────────────


class TestSafeFloat:
    def test_safe_float_nan_returns_default(self) -> None:
        """SF1: NaN → default."""
        assert _safe_float(float("nan")) == 0.0
        assert _safe_float(float("nan"), 42.0) == 42.0

    def test_safe_float_inf_returns_default(self) -> None:
        """SF2: inf → default."""
        assert _safe_float(float("inf")) == 0.0
        assert _safe_float(float("inf"), 99.0) == 99.0

    def test_safe_float_neg_inf_returns_default(self) -> None:
        """SF3: -inf → default."""
        assert _safe_float(float("-inf")) == 0.0

    def test_safe_float_non_numeric_returns_default(self) -> None:
        """SF4: non-numeric string → default."""
        assert _safe_float("abc") == 0.0
        assert _safe_float("abc", 5.0) == 5.0

    def test_safe_float_none_returns_default(self) -> None:
        assert _safe_float(None) == 0.0
        assert _safe_float(None, -1.0) == -1.0

    def test_safe_float_valid_number(self) -> None:
        assert _safe_float(3.14) == 3.14
        assert _safe_float("2.5") == 2.5
        assert _safe_float(0) == 0.0


# ── RD: _require_decisive_float Tests ────────────────────────────────────


class TestRequireDecisiveFloat:
    def test_require_decisive_float_none_returns_none(self) -> None:
        """RD1: None → None."""
        assert _require_decisive_float(None) is None

    def test_require_decisive_float_nan_returns_none(self) -> None:
        """RD2: NaN → None."""
        assert _require_decisive_float(float("nan")) is None

    def test_require_decisive_float_valid_returns_float(self) -> None:
        """RD3: Valid number → float."""
        assert _require_decisive_float(3.14) == 3.14
        assert _require_decisive_float(0.0) == 0.0
        assert _require_decisive_float(-5.0) == -5.0
        assert _require_decisive_float("2.5") == 2.5

    def test_require_decisive_float_string_returns_none(self) -> None:
        """RD4: Non-numeric string → None."""
        assert _require_decisive_float("abc") is None

    def test_require_decisive_float_inf_returns_none(self) -> None:
        assert _require_decisive_float(float("inf")) is None
        assert _require_decisive_float(float("-inf")) is None
