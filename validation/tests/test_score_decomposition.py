from __future__ import annotations

import math

from v10.research.objective import OBJECTIVE_TERM_ORDER
from v10.research.objective import compute_objective_breakdown
from validation.suites.wfo import _evaluate_window_metrics


def test_score_decomposition_terms_sum_to_total() -> None:
    summary = {
        "trades": 42,
        "cagr_pct": 18.5,
        "max_drawdown_mid_pct": 16.2,
        "sharpe": 1.35,
        "profit_factor": 1.7,
    }

    breakdown = compute_objective_breakdown(summary)
    total_from_terms = sum(float(breakdown.components[name]) for name in OBJECTIVE_TERM_ORDER)
    assert abs(float(breakdown.total_score) - total_from_terms) <= 1e-9


def test_missing_metric_marks_wfo_window_invalid() -> None:
    row = _evaluate_window_metrics(
        window_id=5,
        test_start="2024-05-01",
        test_end="2024-06-01",
        candidate_summary={
            "trades": 12,
            "cagr_pct": 9.0,
            "max_drawdown_mid_pct": 14.0,
            "profit_factor": 1.3,
            # missing sharpe -> invalid core metric
        },
        baseline_summary={
            "trades": 15,
            "cagr_pct": 8.5,
            "max_drawdown_mid_pct": 13.0,
            "sharpe": 0.9,
            "profit_factor": 1.2,
        },
        min_trades_for_power=5,
    )

    assert row["valid_window"] is False
    assert row["invalid_reason"] == "candidate_non_finite_core_metrics"
    assert math.isnan(float(row["delta_harsh_score"]))
