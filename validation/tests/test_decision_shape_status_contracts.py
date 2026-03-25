"""Shape/status semantics contract tests for decision engine (Report 31).

Tests container-shape robustness (.data=None, non-dict, chained .get on
non-dict intermediates) and type-coercion safety (int("abc"), dict("str"),
list("str"), bool("false")) for all authority-bearing consumer paths.

Test IDs (Report 31):
  AD1-AD6: _as_dict helper
  SI1-SI9: _safe_int helper
  AL1-AL6: _as_list_of_dicts helper
  SB1-SB8: _strict_bool helper
  DN1-DN9: .data is None (one per authority-bearing suite)
  ND1-ND5: .data is non-dict (string/list/int)
  IC1-IC6: int() crash prevention (non-numeric strings)
  DC1-DC6: dict()/list() coercion crash prevention
  BL1-BL4: bool("false") semantics
  IR1-IR2: Iteration over non-dict rows filtered
"""

from __future__ import annotations

from validation.decision import (
    _as_dict,
    _as_list_of_dicts,
    _safe_int,
    _strict_bool,
    evaluate_decision,
)
from validation.suites.base import SuiteResult


# ── Helpers ──────────────────────────────────────────────────────────────


def _backtest_with_delta(value) -> SuiteResult:
    return SuiteResult(
        name="backtest",
        status="pass",
        data={"deltas": {"harsh": {"score_delta": value}}},
    )


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


def _passing_baseline() -> dict[str, SuiteResult]:
    return {
        "backtest": _backtest_with_delta(5.0),
        "wfo": _wfo_normal(),
    }


def _make_sr(name: str, status: str = "pass", data: object = None) -> SuiteResult:
    """Build SuiteResult, then override .data to any type (even None)."""
    sr = SuiteResult(name=name, status=status, data={})
    sr.data = data  # type: ignore[assignment]
    return sr


# ── AD: _as_dict tests ──────────────────────────────────────────────────


class TestAsDict:
    def test_returns_dict_unchanged(self) -> None:
        """AD1."""
        d = {"a": 1}
        assert _as_dict(d) is d

    def test_none_returns_empty(self) -> None:
        """AD2."""
        assert _as_dict(None) == {}

    def test_string_returns_empty(self) -> None:
        """AD3."""
        assert _as_dict("abc") == {}

    def test_list_returns_empty(self) -> None:
        """AD4."""
        assert _as_dict([1, 2]) == {}

    def test_int_returns_empty(self) -> None:
        """AD5."""
        assert _as_dict(42) == {}

    def test_custom_default(self) -> None:
        """AD6."""
        d = {"fallback": True}
        assert _as_dict(None, default=d) is d


# ── SI: _safe_int tests ─────────────────────────────────────────────────


class TestSafeInt:
    def test_valid_int(self) -> None:
        """SI1."""
        assert _safe_int(5) == 5

    def test_valid_float(self) -> None:
        """SI2."""
        assert _safe_int(3.7) == 3

    def test_valid_string(self) -> None:
        """SI3."""
        assert _safe_int("5") == 5

    def test_none_returns_default(self) -> None:
        """SI4."""
        assert _safe_int(None) == 0

    def test_non_numeric_string(self) -> None:
        """SI5."""
        assert _safe_int("abc") == 0

    def test_nan_returns_default(self) -> None:
        """SI6."""
        assert _safe_int(float("nan")) == 0

    def test_inf_returns_default(self) -> None:
        """SI7."""
        assert _safe_int(float("inf")) == 0

    def test_list_returns_default(self) -> None:
        """SI8."""
        assert _safe_int([1]) == 0

    def test_custom_default(self) -> None:
        """SI9."""
        assert _safe_int("abc", default=99) == 99


# ── AL: _as_list_of_dicts tests ─────────────────────────────────────────


class TestAsListOfDicts:
    def test_valid_list(self) -> None:
        """AL1."""
        data = [{"a": 1}]
        assert _as_list_of_dicts(data) == [{"a": 1}]

    def test_filters_non_dicts(self) -> None:
        """AL2."""
        data = [{"a": 1}, "x", 3, None, {"b": 2}]
        assert _as_list_of_dicts(data) == [{"a": 1}, {"b": 2}]

    def test_string_returns_empty(self) -> None:
        """AL3."""
        assert _as_list_of_dicts("abc") == []

    def test_none_returns_empty(self) -> None:
        """AL4."""
        assert _as_list_of_dicts(None) == []

    def test_int_returns_empty(self) -> None:
        """AL5."""
        assert _as_list_of_dicts(42) == []

    def test_empty_list(self) -> None:
        """AL6."""
        assert _as_list_of_dicts([]) == []


# ── SB: _strict_bool tests ──────────────────────────────────────────────


class TestStrictBool:
    def test_true(self) -> None:
        """SB1."""
        assert _strict_bool(True) is True

    def test_false(self) -> None:
        """SB2."""
        assert _strict_bool(False) is False

    def test_none(self) -> None:
        """SB3."""
        assert _strict_bool(None) is False

    def test_string_true(self) -> None:
        """SB4."""
        assert _strict_bool("true") is False

    def test_string_false(self) -> None:
        """SB5."""
        assert _strict_bool("false") is False

    def test_one(self) -> None:
        """SB6."""
        assert _strict_bool(1) is True

    def test_zero(self) -> None:
        """SB7."""
        assert _strict_bool(0) is False

    def test_nonempty_list(self) -> None:
        """SB8."""
        assert _strict_bool([1]) is False


# ── DN: .data is None tests ─────────────────────────────────────────────


class TestDataNone:
    def test_data_integrity_data_none_no_crash(self) -> None:
        """DN1: data_integrity.data=None, status='fail' → no crash."""
        results = {
            **_passing_baseline(),
            "data_integrity": _make_sr("data_integrity", "fail", data=None),
        }
        v = evaluate_decision(results)
        # _strict_bool(None.get(...)) would crash; _as_dict(None) → {} → no hard_fail
        # Normal gates pass → PROMOTE
        assert v.tag == "PROMOTE"

    def test_invariants_data_none_no_crash(self) -> None:
        """DN2: invariants.data=None, status='fail' → no crash, ERROR via status."""
        results = {
            **_passing_baseline(),
            "invariants": _make_sr("invariants", "fail", data=None),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3

    def test_regression_guard_data_none_no_crash(self) -> None:
        """DN3: regression_guard.data=None, status='fail' → no crash, ERROR."""
        results = {
            **_passing_baseline(),
            "regression_guard": _make_sr("regression_guard", "fail", data=None),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert "regression_guard_failed" in v.failures

    def test_backtest_data_none_contract_error(self) -> None:
        """DN4: backtest.data=None → _as_dict(None)={} → missing delta → ERROR(3)."""
        results = {
            "backtest": _make_sr("backtest", "pass", data=None),
            "wfo": _wfo_normal(),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3
        assert "backtest_payload_contract_breach" in v.failures

    def test_holdout_data_none_contract_error(self) -> None:
        """DN5: holdout.data=None → ERROR(3)."""
        results = {
            **_passing_baseline(),
            "holdout": _make_sr("holdout", "pass", data=None),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert "holdout_payload_contract_breach" in v.failures

    def test_wfo_data_none_no_crash(self) -> None:
        """DN6: wfo.data=None → _as_dict(None)={} → all zeros → low_power."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": _make_sr("wfo", "pass", data=None),
        }
        v = evaluate_decision(results)
        # low_power triggers wfo_low_power_missing_trade_level_bootstrap → HOLD
        assert v.tag == "HOLD"
        assert v.metadata.get("wfo_low_power") is True

    def test_bootstrap_data_none_no_crash(self) -> None:
        """DN7: bootstrap.data=None → no crash (diagnostic only)."""
        results = {
            **_passing_baseline(),
            "bootstrap": _make_sr("bootstrap", "info", data=None),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_trade_level_data_none_no_crash(self) -> None:
        """DN8: trade_level.data=None → no crash."""
        results = {
            **_passing_baseline(),
            "trade_level": _make_sr("trade_level", "info", data=None),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_selection_bias_data_none_no_crash(self) -> None:
        """DN9: selection_bias.data=None → no crash."""
        results = {
            **_passing_baseline(),
            "selection_bias": _make_sr("selection_bias", "pass", data=None),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"


# ── ND: .data is non-dict tests ─────────────────────────────────────────


class TestDataNonDict:
    def test_data_integrity_data_string_no_crash(self) -> None:
        """ND1: data_integrity.data='corrupted' → no crash."""
        results = {
            **_passing_baseline(),
            "data_integrity": _make_sr("data_integrity", "fail", data="corrupted"),
        }
        v = evaluate_decision(results)
        # _as_dict("corrupted") → {} → no hard_fail → falls through
        assert v.tag == "PROMOTE"

    def test_invariants_data_list_no_crash(self) -> None:
        """ND2: invariants.data=[1,2,3] → no crash, ERROR via status."""
        results = {
            **_passing_baseline(),
            "invariants": _make_sr("invariants", "fail", data=[1, 2, 3]),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"

    def test_regression_guard_data_string_no_crash(self) -> None:
        """ND3: regression_guard.data='corrupted' → no crash, ERROR."""
        results = {
            **_passing_baseline(),
            "regression_guard": _make_sr("regression_guard", "fail", data="corrupted"),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert "regression_guard_failed" in v.failures

    def test_wfo_data_string_no_crash(self) -> None:
        """ND4: wfo.data='corrupted' → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": _make_sr("wfo", "pass", data="corrupted"),
        }
        v = evaluate_decision(results)
        # _as_dict("corrupted") → {} → all zeros → low_power → HOLD
        assert v.tag == "HOLD"

    def test_trade_level_data_int_no_crash(self) -> None:
        """ND5: trade_level.data=42 → no crash."""
        results = {
            **_passing_baseline(),
            "trade_level": _make_sr("trade_level", "info", data=42),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"


# ── IC: int() crash prevention tests ────────────────────────────────────


class TestIntCrashPrevention:
    def test_wfo_n_windows_non_numeric(self) -> None:
        """IC1: n_windows='abc' → _safe_int → 0 → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={"summary": {
                    "n_windows": "abc",
                    "positive_delta_windows": 0,
                    "win_rate": 0.0,
                    "stats_power_only": {"n_windows": 0},
                }},
            ),
        }
        v = evaluate_decision(results)
        assert v.metadata.get("wfo_low_power") is True

    def test_wfo_positive_delta_windows_non_numeric(self) -> None:
        """IC2: positive_delta_windows='abc' → _safe_int → 0 → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={"summary": {
                    "n_windows": 10,
                    "n_windows_valid": 10,
                    "positive_delta_windows": "abc",
                    "win_rate": 0.80,
                    "low_trade_windows_count": 0,
                    "stats_power_only": {"n_windows": 10},
                }},
            ),
        }
        v = evaluate_decision(results)
        # positive_windows=0 < required → wfo gate fails → HOLD
        assert v.tag in {"HOLD", "PROMOTE"}  # no crash is the key assertion

    def test_wfo_power_windows_non_numeric(self) -> None:
        """IC3: stats_power_only.n_windows='abc' → _safe_int → 0 → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={"summary": {
                    "n_windows": 10,
                    "n_windows_valid": 10,
                    "positive_delta_windows": 8,
                    "win_rate": 0.80,
                    "low_trade_windows_count": 0,
                    "stats_power_only": {"n_windows": "abc"},
                }},
            ),
        }
        v = evaluate_decision(results)
        # power_windows=0 → low_power=True
        assert v.metadata.get("wfo_low_power") is True

    def test_wfo_valid_windows_non_numeric(self) -> None:
        """IC4: n_windows_valid='abc' → _safe_int → 0 → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={"summary": {
                    "n_windows": 10,
                    "n_windows_valid": "abc",
                    "positive_delta_windows": 8,
                    "win_rate": 0.80,
                    "low_trade_windows_count": 0,
                    "stats_power_only": {"n_windows": 10},
                }},
            ),
        }
        v = evaluate_decision(results)
        # valid_windows=0 → low_trade_ratio=1.0 → low_power
        assert v.metadata.get("wfo_low_power") is True

    def test_wfo_low_trade_windows_non_numeric(self) -> None:
        """IC5: low_trade_windows_count='abc' → _safe_int → 0 → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={"summary": {
                    "n_windows": 10,
                    "n_windows_valid": 10,
                    "positive_delta_windows": 8,
                    "win_rate": 0.80,
                    "low_trade_windows_count": "abc",
                    "stats_power_only": {"n_windows": 10},
                }},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_trade_level_block_len_non_numeric(self) -> None:
        """IC6: block_len='abc' → _safe_int → 0 → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={"summary": {
                    "n_windows": 2,
                    "n_windows_valid": 2,
                    "positive_delta_windows": 0,
                    "win_rate": 0.0,
                    "low_trade_windows_count": 2,
                    "stats_power_only": {"n_windows": 1},
                }},
            ),
            "trade_level": SuiteResult(
                name="trade_level",
                status="info",
                data={
                    "trade_level_bootstrap": {
                        "ci95_low": -0.001,
                        "ci95_high": 0.001,
                        "mean_diff": 0.00001,
                        "p_gt_0": 0.51,
                        "block_len": "abc",
                        "small_improvement_threshold": 0.0002,
                    },
                },
            ),
        }
        v = evaluate_decision(results)
        # No crash; low_power + ci_crosses_zero + small → HOLD
        assert v.tag == "HOLD"


# ── DC: dict()/list() coercion crash prevention ─────────────────────────


class TestDictListCoercionCrash:
    def test_invariants_counts_string_no_crash(self) -> None:
        """DC1: counts_by_invariant='corrupted' → _as_dict → {} → no crash."""
        results = {
            **_passing_baseline(),
            "invariants": SuiteResult(
                name="invariants",
                status="fail",
                data={"n_violations": 5, "counts_by_invariant": "corrupted"},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3

    def test_regression_guard_violated_metrics_string_no_crash(self) -> None:
        """DC2: violated_metrics='abc' → _as_list_of_dicts → [] → no crash."""
        results = {
            **_passing_baseline(),
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={"pass": False, "violated_metrics": "abc"},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert "regression_guard_failed" in v.failures

    def test_regression_guard_violated_metrics_with_non_dict_items(self) -> None:
        """DC3: violated_metrics=['abc', 42, None] → filtered to [] → no crash."""
        results = {
            **_passing_baseline(),
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={"pass": False, "violated_metrics": ["abc", 42, None]},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert "regression_guard_failed" in v.failures

    def test_trade_level_bootstrap_string_no_crash(self) -> None:
        """DC4: trade_level_bootstrap='corrupted' → _as_dict → {} → no crash."""
        results = {
            **_passing_baseline(),
            "trade_level": SuiteResult(
                name="trade_level",
                status="info",
                data={"trade_level_bootstrap": "corrupted"},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_data_integrity_counts_string_no_crash(self) -> None:
        """DC5: counts='corrupted' inside data_integrity → no crash."""
        results = {
            **_passing_baseline(),
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="pass",
                data={"hard_fail": True, "hard_fail_reasons": ["test"], "counts": "corrupted"},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3

    def test_wfo_stats_power_only_string_no_crash(self) -> None:
        """DC6: stats_power_only='corrupted' → _as_dict → {} → no crash."""
        results = {
            "backtest": _backtest_with_delta(5.0),
            "wfo": SuiteResult(
                name="wfo",
                status="pass",
                data={"summary": {
                    "n_windows": 10,
                    "n_windows_valid": 10,
                    "positive_delta_windows": 8,
                    "win_rate": 0.80,
                    "low_trade_windows_count": 0,
                    "stats_power_only": "corrupted",
                }},
            ),
        }
        v = evaluate_decision(results)
        # _as_dict("corrupted") → {} → power_windows=0 → low_power=True
        assert v.metadata.get("wfo_low_power") is True


# ── BL: bool("false") semantics tests ───────────────────────────────────


class TestBoolSemantics:
    def test_data_integrity_hard_fail_string_false_is_false(self) -> None:
        """BL1: hard_fail='false' → _strict_bool → False → no early exit."""
        results = {
            **_passing_baseline(),
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="pass",
                data={"hard_fail": "false"},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_data_integrity_hard_fail_string_true_is_false(self) -> None:
        """BL2: hard_fail='true' → _strict_bool → False → no early exit."""
        results = {
            **_passing_baseline(),
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="pass",
                data={"hard_fail": "true"},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_data_integrity_hard_fail_bool_true_exits(self) -> None:
        """BL3: hard_fail=True → _strict_bool → True → early exit ERROR."""
        results = {
            **_passing_baseline(),
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="fail",
                data={"hard_fail": True, "hard_fail_reasons": ["test"]},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert v.exit_code == 3

    def test_regression_guard_pass_string_false_not_pass(self) -> None:
        """BL4: pass='false' → _strict_bool → False → guard fails."""
        results = {
            **_passing_baseline(),
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={"pass": "false", "violated_metrics": [{"metric": "x"}]},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"


# ── IR: Iteration over non-dict rows ────────────────────────────────────


class TestIterationFiltering:
    def test_regression_guard_mixed_types_filtered(self) -> None:
        """IR1: violated_metrics=[dict, 'y', 3] → only dict items used."""
        results = {
            **_passing_baseline(),
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={
                    "pass": False,
                    "violated_metrics": [{"metric": "x"}, "y", 3, None],
                },
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert "x" in v.failures

    def test_regression_guard_violated_metadata_none_items_filtered(self) -> None:
        """IR2: violated_metadata=[None, {field: 'x'}] → only dict items."""
        results = {
            **_passing_baseline(),
            "regression_guard": SuiteResult(
                name="regression_guard",
                status="fail",
                data={
                    "pass": False,
                    "violated_metadata": [None, {"field": "x"}],
                },
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "ERROR"
        assert "metadata:x" in v.failures
