"""Tests proving single-source-of-truth for authority-bearing thresholds (Report 33).

Verifies that producer suites and the decision consumer share the same constants
from validation.thresholds, and that changing the constant in one place would
affect both sides consistently.

Test IDs (Report 33):
  TS1-TS3:  DecisionPolicy defaults match shared constants
  TS4-TS5:  Producer modules import shared constants (source inspection)
  TS6-TS7:  WFO producer uses shared constants (source inspection)
  TS8:      Decision boundary at HARSH_SCORE_TOLERANCE
  TS9:      Decision boundary at WFO_WIN_RATE_THRESHOLD
  TS10:     WFO small-sample branching at WFO_SMALL_SAMPLE_CUTOFF
  TS11:     Threshold values unchanged (regression guard)
  TS12:     Zero-authority suites remain zero-authority
"""

from __future__ import annotations

import inspect

from validation.decision import DecisionPolicy
from validation.decision import evaluate_decision
from validation.suites.base import SuiteResult
from validation.thresholds import HARSH_SCORE_TOLERANCE
from validation.thresholds import WFO_SMALL_SAMPLE_CUTOFF
from validation.thresholds import WFO_WIN_RATE_THRESHOLD


# ── TS1-TS3: DecisionPolicy defaults ────────────────────────────────


class TestDecisionPolicyDefaults:
    def test_harsh_score_tolerance_matches_shared_constant(self) -> None:
        """TS1: harsh_score_tolerance default == HARSH_SCORE_TOLERANCE."""
        policy = DecisionPolicy()
        assert policy.harsh_score_tolerance == HARSH_SCORE_TOLERANCE

    def test_holdout_score_tolerance_matches_shared_constant(self) -> None:
        """TS2: holdout_score_tolerance default == HARSH_SCORE_TOLERANCE."""
        policy = DecisionPolicy()
        assert policy.holdout_score_tolerance == HARSH_SCORE_TOLERANCE

    def test_wfo_win_rate_threshold_matches_shared_constant(self) -> None:
        """TS3: wfo_win_rate_threshold default == WFO_WIN_RATE_THRESHOLD."""
        policy = DecisionPolicy()
        assert policy.wfo_win_rate_threshold == WFO_WIN_RATE_THRESHOLD


# ── TS4-TS7: Producer modules reference shared constants ─────────────


class TestProducerImports:
    def test_backtest_uses_shared_tolerance(self) -> None:
        """TS4: backtest.py source references HARSH_SCORE_TOLERANCE."""
        import validation.suites.backtest as mod
        source = inspect.getsource(mod)
        assert "HARSH_SCORE_TOLERANCE" in source
        assert "tolerance = -0.2" not in source

    def test_holdout_uses_shared_tolerance(self) -> None:
        """TS5: holdout.py source references HARSH_SCORE_TOLERANCE."""
        import validation.suites.holdout as mod
        source = inspect.getsource(mod)
        assert "HARSH_SCORE_TOLERANCE" in source
        assert "delta >= -0.2" not in source

    def test_wfo_uses_shared_win_rate(self) -> None:
        """TS6: wfo.py source references WFO_WIN_RATE_THRESHOLD."""
        import validation.suites.wfo as mod
        source = inspect.getsource(mod)
        assert "WFO_WIN_RATE_THRESHOLD" in source
        # The old hardcoded 0.6 multiplier should be replaced
        assert "0.6 * n_windows" not in source

    def test_wfo_uses_shared_small_sample_cutoff(self) -> None:
        """TS7: wfo.py source references WFO_SMALL_SAMPLE_CUTOFF."""
        import validation.suites.wfo as mod
        source = inspect.getsource(mod)
        assert "WFO_SMALL_SAMPLE_CUTOFF" in source
        assert "n_windows <= 5" not in source


# ── TS8-TS10: Decision boundary behavior ─────────────────────────────


def _make_bt(delta: float) -> SuiteResult:
    return SuiteResult(
        name="backtest",
        status="pass",
        data={"deltas": {"harsh": {"score_delta": delta}}},
    )


def _make_wfo(n_windows: int, positive: int, win_rate: float) -> SuiteResult:
    return SuiteResult(
        name="wfo",
        status="pass",
        data={"summary": {
            "n_windows": n_windows,
            "positive_delta_windows": positive,
            "win_rate": win_rate,
            "n_windows_valid": n_windows,
            "stats_power_only": {"n_windows": n_windows},
            "low_trade_windows_count": 0,
        }},
    )


class TestDecisionBoundaries:
    def test_harsh_delta_at_exact_tolerance_passes(self) -> None:
        """TS8a: delta exactly at -HARSH_SCORE_TOLERANCE passes hard gate."""
        results = {"backtest": _make_bt(-HARSH_SCORE_TOLERANCE)}
        v = evaluate_decision(results)
        gate = next(g for g in v.gates if g.gate_name == "full_harsh_delta")
        assert gate.passed is True

    def test_harsh_delta_below_tolerance_fails(self) -> None:
        """TS8b: delta 0.001 below -HARSH_SCORE_TOLERANCE fails hard gate."""
        results = {"backtest": _make_bt(-HARSH_SCORE_TOLERANCE - 0.001)}
        v = evaluate_decision(results)
        gate = next(g for g in v.gates if g.gate_name == "full_harsh_delta")
        assert gate.passed is False
        assert v.tag == "REJECT"

    def test_wfo_win_rate_at_exact_threshold_passes(self) -> None:
        """TS9a: win_rate at WFO_WIN_RATE_THRESHOLD passes soft gate."""
        # Use n_windows > WFO_SMALL_SAMPLE_CUTOFF to enter the win-rate branch
        n = WFO_SMALL_SAMPLE_CUTOFF + 1
        results = {
            "backtest": _make_bt(5.0),
            "wfo": _make_wfo(n, n, WFO_WIN_RATE_THRESHOLD),
        }
        v = evaluate_decision(results)
        gate = next(g for g in v.gates if g.gate_name == "wfo_robustness")
        assert gate.passed is True

    def test_wfo_win_rate_below_threshold_fails(self) -> None:
        """TS9b: win_rate below WFO_WIN_RATE_THRESHOLD fails soft gate."""
        n = WFO_SMALL_SAMPLE_CUTOFF + 1
        results = {
            "backtest": _make_bt(5.0),
            "wfo": _make_wfo(n, 0, WFO_WIN_RATE_THRESHOLD - 0.001),
        }
        v = evaluate_decision(results)
        gate = next(g for g in v.gates if g.gate_name == "wfo_robustness")
        assert gate.passed is False

    def test_wfo_small_sample_at_cutoff_uses_n_minus_1_rule(self) -> None:
        """TS10a: n_windows == WFO_SMALL_SAMPLE_CUTOFF uses N-1 positive rule."""
        n = WFO_SMALL_SAMPLE_CUTOFF
        # N-1 positive windows should pass
        results = {
            "backtest": _make_bt(5.0),
            "wfo": _make_wfo(n, n - 1, (n - 1) / n),
        }
        v = evaluate_decision(results)
        gate = next(g for g in v.gates if g.gate_name == "wfo_robustness")
        assert gate.passed is True
        # Verify the detail string shows positive/N format (N-1 rule)
        assert "positive=" in gate.detail

    def test_wfo_above_cutoff_uses_win_rate_rule(self) -> None:
        """TS10b: n_windows == WFO_SMALL_SAMPLE_CUTOFF+1 uses win-rate rule."""
        n = WFO_SMALL_SAMPLE_CUTOFF + 1
        results = {
            "backtest": _make_bt(5.0),
            "wfo": _make_wfo(n, n, 1.0),
        }
        v = evaluate_decision(results)
        gate = next(g for g in v.gates if g.gate_name == "wfo_robustness")
        assert gate.passed is True
        # Verify the detail string shows win_rate format (win-rate rule)
        assert "win_rate=" in gate.detail


# ── TS11: Threshold values unchanged ─────────────────────────────────


class TestThresholdValues:
    def test_harsh_score_tolerance_is_0_2(self) -> None:
        """TS11a: HARSH_SCORE_TOLERANCE has not changed from 0.2."""
        assert HARSH_SCORE_TOLERANCE == 0.2

    def test_wfo_win_rate_threshold_is_0_60(self) -> None:
        """TS11b: WFO_WIN_RATE_THRESHOLD has not changed from 0.60."""
        assert WFO_WIN_RATE_THRESHOLD == 0.60

    def test_wfo_small_sample_cutoff_is_5(self) -> None:
        """TS11c: WFO_SMALL_SAMPLE_CUTOFF has not changed from 5."""
        assert WFO_SMALL_SAMPLE_CUTOFF == 5


# ── TS12: Zero-authority suites remain zero-authority ─────────────────


class TestZeroAuthority:
    def test_cost_sweep_fail_does_not_veto(self) -> None:
        """TS12a: cost_sweep fail cannot cause REJECT or HOLD."""
        results = {
            "backtest": _make_bt(5.0),
            "cost_sweep": SuiteResult(name="cost_sweep", status="fail", data={}),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_churn_fail_does_not_veto(self) -> None:
        """TS12b: churn_metrics fail cannot cause REJECT or HOLD."""
        results = {
            "backtest": _make_bt(5.0),
            "churn_metrics": SuiteResult(name="churn_metrics", status="fail", data={}),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"

    def test_bootstrap_always_info_no_veto(self) -> None:
        """TS12c: bootstrap gate has severity=info and passed=True always."""
        results = {
            "backtest": _make_bt(5.0),
            "bootstrap": SuiteResult(
                name="bootstrap",
                status="info",
                data={"gate": {"p_candidate_better": 0.1, "ci_lower": -5.0}},
            ),
        }
        v = evaluate_decision(results)
        assert v.tag == "PROMOTE"
        gate = next(g for g in v.gates if g.gate_name == "bootstrap")
        assert gate.passed is True
        assert gate.severity == "info"
