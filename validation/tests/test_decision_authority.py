"""Regression tests for decision gate authority (Report 27).

Tests all gate-to-verdict paths that were previously untested:
- Hard gates: lookahead, full_harsh_delta, holdout_harsh_delta → REJECT(2)
- Soft gates: wfo_robustness, trade_level_bootstrap, trade_level_matched_delta,
  selection_bias → HOLD(1)
- Error paths: suite error → ERROR(3)
- Trade-level truth table paths (A1, B1, C1, E1 and wfo_low_power=F variants)

Test ID mapping (Report 27 §3.3.1 truth table):
  HA1: test_lookahead_hard_gate_reject
  HA2: test_full_harsh_delta_hard_gate_reject
  HA3: test_holdout_harsh_delta_hard_gate_reject
  SO1: test_wfo_robustness_soft_gate_hold
  SO2: test_trade_level_bootstrap_inconclusive_hold          (path A1)
  SO3: test_trade_level_matched_delta_negative_hold          (path B1)
  SO4: test_selection_bias_caution_hold
  SO5: test_wfo_low_power_missing_tl_bootstrap_hold          (path E1)
  SO6: test_trade_level_ci_upper_neg_without_wfo_low_power   (path B1, wfo normal)
  SO7: test_trade_level_bootstrap_present_wfo_normal_promote (paths A5-A8)
  ER1: test_suite_error_returns_error
  PR1: test_all_gates_pass_promote
"""

from __future__ import annotations

from validation.decision import evaluate_decision
from validation.suites.base import SuiteResult

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_backtest_result(harsh_delta: float) -> SuiteResult:
    return SuiteResult(
        name="backtest",
        status="pass",
        data={"deltas": {"harsh": {"score_delta": harsh_delta}}},
    )


def _make_holdout_result(delta: float) -> SuiteResult:
    return SuiteResult(
        name="holdout",
        status="pass",
        data={"delta_harsh_score": delta},
    )


def _make_wfo_result(
    *,
    win_rate: float,
    n_windows: int,
    positive_windows: int,
    power_windows: int = 10,
    low_trade_windows: int = 0,
) -> SuiteResult:
    return SuiteResult(
        name="wfo",
        status="pass",
        data={
            "summary": {
                "n_windows": n_windows,
                "n_windows_valid": n_windows,
                "positive_delta_windows": positive_windows,
                "win_rate": win_rate,
                "low_trade_windows_count": low_trade_windows,
                "stats_power_only": {"n_windows": power_windows},
            },
        },
    )


def _make_trade_level_result(
    *,
    p_pos: float | None = None,
    ci_upper: float | None = None,
    trade_level_bootstrap: dict | None = None,
) -> SuiteResult:
    data: dict = {}
    if p_pos is not None:
        data["matched_p_positive"] = p_pos
    if ci_upper is not None:
        data["matched_block_bootstrap_ci_upper"] = ci_upper
    if trade_level_bootstrap is not None:
        data["trade_level_bootstrap"] = trade_level_bootstrap
    return SuiteResult(name="trade_level", status="info", data=data)


def _make_selection_bias_result(risk_statement: str) -> SuiteResult:
    return SuiteResult(
        name="selection_bias",
        status="pass",
        data={"risk_statement": risk_statement},
    )


def _wfo_low_power() -> SuiteResult:
    """WFO result that triggers wfo_low_power=True (power_windows=1, ratio=1.0)."""
    return _make_wfo_result(
        win_rate=0.0,
        n_windows=2,
        positive_windows=0,
        power_windows=1,
        low_trade_windows=2,
    )


def _wfo_normal() -> SuiteResult:
    """WFO result with normal power, passing win_rate threshold."""
    return _make_wfo_result(
        win_rate=0.80,
        n_windows=10,
        positive_windows=8,
        power_windows=10,
        low_trade_windows=0,
    )


# ── Hard Gates → REJECT(2) ──────────────────────────────────────────────


class TestHardGateReject:
    def test_lookahead_hard_gate_reject(self) -> None:
        """HA1: lookahead status=fail → REJECT(2)."""
        results = {
            "lookahead": SuiteResult(name="lookahead", status="fail", data={}),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "REJECT"
        assert verdict.exit_code == 2
        assert "lookahead_check_failed" in verdict.failures

        gate = next(g for g in verdict.gates if g.gate_name == "lookahead")
        assert gate.severity == "hard"
        assert gate.passed is False

    def test_full_harsh_delta_hard_gate_reject(self) -> None:
        """HA2: backtest harsh delta < -0.2 → REJECT(2)."""
        results = {"backtest": _make_backtest_result(harsh_delta=-0.3)}
        verdict = evaluate_decision(results)

        assert verdict.tag == "REJECT"
        assert verdict.exit_code == 2
        assert "full_harsh_delta_below_tolerance" in verdict.failures

        gate = next(g for g in verdict.gates if g.gate_name == "full_harsh_delta")
        assert gate.severity == "hard"
        assert gate.passed is False

    def test_holdout_harsh_delta_hard_gate_reject(self) -> None:
        """HA3: holdout harsh delta < -0.2 → REJECT(2)."""
        results = {"holdout": _make_holdout_result(delta=-0.3)}
        verdict = evaluate_decision(results)

        assert verdict.tag == "REJECT"
        assert verdict.exit_code == 2
        assert "holdout_harsh_delta_below_tolerance" in verdict.failures

        gate = next(g for g in verdict.gates if g.gate_name == "holdout_harsh_delta")
        assert gate.severity == "hard"
        assert gate.passed is False


# ── Soft Gates → HOLD(1) ────────────────────────────────────────────────


class TestSoftGateHold:
    def test_wfo_robustness_soft_gate_hold(self) -> None:
        """SO1: WFO win_rate < 60% with N > 5 → HOLD(1)."""
        results = {
            "wfo": _make_wfo_result(
                win_rate=0.40,
                n_windows=10,
                positive_windows=4,
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "HOLD"
        assert verdict.exit_code == 1
        assert "wfo_robustness_failed" in verdict.failures

        gate = next(g for g in verdict.gates if g.gate_name == "wfo_robustness")
        assert gate.severity == "soft"
        assert gate.passed is False

    def test_trade_level_bootstrap_inconclusive_hold(self) -> None:
        """SO2 (path A1): WFO low-power + ci crosses zero + small improvement → HOLD(1)."""
        results = {
            "wfo": _wfo_low_power(),
            "trade_level": _make_trade_level_result(
                trade_level_bootstrap={
                    "ci95_low": -0.001,
                    "ci95_high": 0.001,
                    "mean_diff": 0.00005,
                    "p_gt_0": 0.52,
                    "block_len": 10,
                    "small_improvement_threshold": 0.0002,
                },
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "HOLD"
        assert verdict.exit_code == 1
        assert "trade_level_bootstrap_inconclusive" in verdict.failures

        gate = next(
            g for g in verdict.gates if g.gate_name == "trade_level_bootstrap" and not g.passed
        )
        assert gate.severity == "soft"

    def test_trade_level_matched_delta_negative_hold(self) -> None:
        """SO3 (path B1): ci_upper < 0, no bootstrap payload → HOLD(1)."""
        results = {
            "trade_level": _make_trade_level_result(p_pos=0.3, ci_upper=-0.01),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "HOLD"
        assert verdict.exit_code == 1
        assert "trade_level_delta_negative" in verdict.failures

        gate = next(g for g in verdict.gates if g.gate_name == "trade_level_matched_delta")
        assert gate.severity == "soft"
        assert gate.passed is False

    def test_selection_bias_caution_diagnostic_only(self) -> None:
        """SO4: risk_statement contains CAUTION → PROMOTE (PSR is diagnostic, no veto).

        PSR was demoted from binding soft gate to info diagnostic (2026-03-16).
        PSR treats sr_benchmark as known constant — anti-conservative for
        2-strategy comparison.  Paired evidence from WFO Wilcoxon + Bootstrap CI
        is the binding authority for "candidate beats baseline".
        """
        results = {
            "selection_bias": _make_selection_bias_result(
                "CAUTION - deflated Sharpe fails for at least one trial level"
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0
        assert "selection_bias_caution" not in verdict.failures

        gate = next(g for g in verdict.gates if g.gate_name == "selection_bias")
        assert gate.severity == "info"
        assert gate.passed is True

    def test_wfo_low_power_missing_tl_bootstrap_hold(self) -> None:
        """SO5 (path E1): WFO low-power + trade_level present but no bootstrap payload → HOLD(1)."""
        results = {
            "wfo": _wfo_low_power(),
            "trade_level": _make_trade_level_result(p_pos=0.6, ci_upper=0.01),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "HOLD"
        assert verdict.exit_code == 1
        assert "wfo_low_power_missing_trade_level_bootstrap" in verdict.failures

    def test_trade_level_ci_upper_neg_without_wfo_low_power(self) -> None:
        """SO6 (path B1 + wfo normal): ci_upper < 0 vetoes regardless of WFO state.

        This is the key test proving the Report 27 §2.2 row 15 contradiction:
        trade_level_matched_delta can FAIL even when WFO is NOT low-power.
        """
        results = {
            "wfo": _wfo_normal(),
            "trade_level": _make_trade_level_result(p_pos=0.3, ci_upper=-0.05),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "HOLD"
        assert verdict.exit_code == 1
        assert "trade_level_delta_negative" in verdict.failures

        gate = next(g for g in verdict.gates if g.gate_name == "trade_level_matched_delta")
        assert gate.severity == "soft"
        assert gate.passed is False


# ── Trade-Level Pass + Promote ──────────────────────────────────────────


class TestTradeLevePromote:
    def test_trade_level_bootstrap_present_wfo_normal_promote(self) -> None:
        """SO7 (paths A5-A8): WFO normal + bootstrap present + healthy CI → PROMOTE(0)."""
        results = {
            "wfo": _wfo_normal(),
            "trade_level": _make_trade_level_result(
                trade_level_bootstrap={
                    "ci95_low": 0.001,
                    "ci95_high": 0.005,
                    "mean_diff": 0.003,
                    "p_gt_0": 0.95,
                    "block_len": 10,
                },
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0

        gate = next(g for g in verdict.gates if g.gate_name == "trade_level_bootstrap")
        assert gate.passed is True
        assert gate.severity == "soft"


# ── Error Path ──────────────────────────────────────────────────────────


class TestErrorPath:
    def test_suite_error_returns_error(self) -> None:
        """ER1: Any suite with status=error → ERROR(3)."""
        results = {
            "backtest": SuiteResult(
                name="backtest",
                status="error",
                error_message="engine crash",
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "ERROR"
        assert verdict.exit_code == 3


# ── Full Promote Path ──────────────────────────────────────────────────


class TestPromotePath:
    def test_all_gates_pass_promote(self) -> None:
        """PR1: All gates pass → PROMOTE(0), no failures."""
        results = {
            "backtest": _make_backtest_result(harsh_delta=0.5),
            "holdout": _make_holdout_result(delta=0.3),
            "wfo": _wfo_normal(),
            "trade_level": _make_trade_level_result(p_pos=0.7, ci_upper=0.05),
            "selection_bias": _make_selection_bias_result(
                "PASS - deflated Sharpe robust across tested trials"
            ),
            "bootstrap": SuiteResult(
                name="bootstrap",
                status="info",
                data={
                    "gate": {
                        "p_candidate_better": 0.85,
                        "ci_lower": 0.01,
                    },
                },
            ),
        }
        verdict = evaluate_decision(results)

        assert verdict.tag == "PROMOTE"
        assert verdict.exit_code == 0
        assert verdict.failures == []

        hard_fails = [g for g in verdict.gates if g.severity == "hard" and not g.passed]
        soft_fails = [g for g in verdict.gates if g.severity == "soft" and not g.passed]
        assert len(hard_fails) == 0
        assert len(soft_fails) == 0
