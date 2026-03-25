"""Unit tests for WFO invalid-window and low-trade handling."""

from __future__ import annotations

import math

from validation.suites.wfo import _evaluate_window_metrics


def _summary(
    *,
    trades: int,
    cagr_pct: float = 12.0,
    max_drawdown_mid_pct: float = 18.0,
    sharpe: float = 1.1,
    profit_factor: float = 1.4,
) -> dict[str, float | int]:
    return {
        "trades": trades,
        "cagr_pct": cagr_pct,
        "max_drawdown_mid_pct": max_drawdown_mid_pct,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
    }


def test_wfo_window_both_zero_trades_is_invalid_without_extreme_delta() -> None:
    row = _evaluate_window_metrics(
        window_id=0,
        test_start="2024-01-01",
        test_end="2024-02-01",
        candidate_summary=_summary(trades=0, sharpe=0.0, profit_factor=0.0),
        baseline_summary=_summary(trades=0, sharpe=0.0, profit_factor=0.0),
        min_trades_for_power=5,
    )

    assert row["valid_window"] is False
    assert row["invalid_reason"] == "both_zero_trade_counts"
    delta = float(row["delta_harsh_score"])
    assert math.isnan(delta)
    assert not (math.isfinite(delta) and abs(delta) > 100_000.0)


def test_wfo_window_one_zero_trade_side_is_invalid_with_explicit_reason() -> None:
    row = _evaluate_window_metrics(
        window_id=1,
        test_start="2024-02-01",
        test_end="2024-03-01",
        candidate_summary=_summary(trades=0, sharpe=0.0, profit_factor=0.0),
        baseline_summary=_summary(trades=9, cagr_pct=14.0, max_drawdown_mid_pct=15.0, sharpe=1.2),
        min_trades_for_power=5,
    )

    assert row["valid_window"] is False
    assert row["invalid_reason"] == "candidate_zero_trade_count"
    assert math.isnan(float(row["delta_harsh_score"]))


def test_wfo_window_low_trade_is_valid_and_flagged_low_trade() -> None:
    row = _evaluate_window_metrics(
        window_id=2,
        test_start="2024-03-01",
        test_end="2024-04-01",
        candidate_summary=_summary(trades=3, cagr_pct=8.0, max_drawdown_mid_pct=12.0, sharpe=0.8),
        baseline_summary=_summary(trades=7, cagr_pct=7.5, max_drawdown_mid_pct=12.5, sharpe=0.75),
        min_trades_for_power=5,
    )

    assert row["valid_window"] is True
    assert row["invalid_reason"] == "none"
    assert row["low_trade_window"] is True
    assert row["low_trade_reason"] == "candidate_below_min_trades_for_power"
    assert math.isfinite(float(row["delta_harsh_score"]))
