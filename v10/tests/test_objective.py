"""Tests for the objective scoring function (SPEC_METRICS §8)."""

from __future__ import annotations

import pytest

from v10.research.objective import compute_objective


def _summary(
    cagr: float = 30.0,
    max_dd: float = 25.0,
    sharpe: float = 1.5,
    pf: float = 2.0,
    trades: int = 40,
) -> dict:
    return {
        "cagr_pct": cagr,
        "max_drawdown_mid_pct": max_dd,
        "sharpe": sharpe,
        "profit_factor": pf,
        "trades": trades,
    }


class TestComputeObjective:
    def test_reject_few_trades(self) -> None:
        s = _summary(trades=9)
        assert compute_objective(s) == -1_000_000.0

    def test_reject_zero_trades(self) -> None:
        assert compute_objective({"trades": 0}) == -1_000_000.0

    def test_known_score(self) -> None:
        """Manual calculation: cagr=30, dd=25, sharpe=1.5, pf=2.0, trades=40."""
        s = _summary()
        expected = (
            2.5 * 30.0
            - 0.60 * 25.0
            + 8.0 * 1.5
            + 5.0 * (2.0 - 1.0)
            + min(40 / 50.0, 1.0) * 5.0
        )
        assert compute_objective(s) == pytest.approx(expected, abs=0.01)

    def test_pf_capped_at_3(self) -> None:
        """PF = 5.0 should be capped at 3.0 in the formula."""
        s = _summary(pf=5.0)
        score_5 = compute_objective(s)
        s["profit_factor"] = 3.0
        score_3 = compute_objective(s)
        assert score_5 == pytest.approx(score_3, abs=0.01)

    def test_pf_inf_string(self) -> None:
        """profit_factor can be 'inf' string — treated as 3.0 cap."""
        s = _summary()
        s["profit_factor"] = "inf"
        score = compute_objective(s)
        s["profit_factor"] = 3.0
        assert score == pytest.approx(compute_objective(s), abs=0.01)

    def test_negative_sharpe_zeroed(self) -> None:
        """Negative sharpe should contribute 0 (max(0, sharpe))."""
        s = _summary(sharpe=-0.5)
        score = compute_objective(s)
        s2 = _summary(sharpe=0.0)
        assert score == pytest.approx(compute_objective(s2), abs=0.01)

    def test_trade_bonus_saturates_at_50(self) -> None:
        """50 trades = full 5.0 bonus; 100 trades = same 5.0."""
        s50 = _summary(trades=50)
        s100 = _summary(trades=100)
        assert compute_objective(s50) == pytest.approx(compute_objective(s100), abs=0.01)

    def test_none_sharpe(self) -> None:
        """sharpe=None should be treated as 0."""
        s = _summary()
        s["sharpe"] = None
        score = compute_objective(s)
        s["sharpe"] = 0.0
        assert score == pytest.approx(compute_objective(s), abs=0.01)

    def test_exactly_10_trades_not_rejected(self) -> None:
        s = _summary(trades=10)
        assert compute_objective(s) > -1_000_000.0
