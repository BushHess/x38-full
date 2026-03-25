"""Walk-forward optimization: windowing, grid search, survivor ranking.

Per window:
  1. Expand param_ranges into cartesian grid (budget ≤ 8 keys)
  2. Score all grid points on train period
  3. Take top-K, test OOS on test period
  4. Pass criteria: test_return > -5% AND test_mdd < 35%

Survivors: tested in 2+ windows, ranked by pass_rate then median_test_score.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, timezone

from v10.core.data import DataFeed
from v10.core.types import SCENARIOS, CostConfig
from v10.core.engine import BacktestEngine
from v10.research.candidates import CandidateSpec, build_config, build_strategy
from v10.research.objective import compute_objective


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class WFOWindowSpec:
    """Train/test window specification."""
    window_id: int
    train_start: str  # YYYY-MM-DD
    train_end: str
    test_start: str
    test_end: str


@dataclass
class WFOWindowResult:
    """Result of one param set in one window."""
    window_id: int
    params: dict[str, Any]
    train_score: float
    test_score: float | None  # None if not selected for OOS test
    test_return_pct: float | None
    test_mdd_pct: float | None
    passed: bool


@dataclass
class WFOSurvivor:
    """A param set that survived across multiple windows."""
    params: dict[str, Any]
    windows_tested: int
    windows_passed: int
    pass_rate: float
    median_test_score: float
    window_details: list[WFOWindowResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Window generation
# ---------------------------------------------------------------------------

def generate_windows(
    start: str,
    end: str,
    train_months: int = 24,
    test_months: int = 6,
    slide_months: int = 6,
) -> list[WFOWindowSpec]:
    """Generate sliding train/test windows.

    Boundaries are returned as inclusive dates because ``DataFeed`` treats
    ``end`` inclusively. Each phase therefore ends on the day before the
    next phase starts so train/test and test/test windows do not overlap.

    Parameters
    ----------
    start, end : str
        Date range in YYYY-MM-DD format.
    train_months : int
        Training window length in months.
    test_months : int
        Testing window length in months.
    slide_months : int
        Slide step between windows in months.
    """
    if train_months <= 0:
        raise ValueError(f"train_months must be > 0, got {train_months}")
    if test_months <= 0:
        raise ValueError(f"test_months must be > 0, got {test_months}")
    if slide_months <= 0:
        raise ValueError(f"slide_months must be > 0, got {slide_months}")

    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    windows: list[WFOWindowSpec] = []
    window_id = 0
    train_start = start_dt

    while True:
        train_end = train_start + relativedelta(months=train_months) - timedelta(days=1)
        test_start = train_end + timedelta(days=1)
        test_end = test_start + relativedelta(months=test_months) - timedelta(days=1)

        if test_end > end_dt:
            break

        windows.append(WFOWindowSpec(
            window_id=window_id,
            train_start=train_start.strftime("%Y-%m-%d"),
            train_end=train_end.strftime("%Y-%m-%d"),
            test_start=test_start.strftime("%Y-%m-%d"),
            test_end=test_end.strftime("%Y-%m-%d"),
        ))
        window_id += 1
        train_start += relativedelta(months=slide_months)

    return windows


# ---------------------------------------------------------------------------
# Grid expansion
# ---------------------------------------------------------------------------

def expand_param_grid(candidate: CandidateSpec) -> list[dict[str, Any]]:
    """Expand param_ranges into cartesian product grid.

    Each grid point is the base params merged with one combination from ranges.
    """
    if not candidate.param_ranges:
        return [dict(candidate.params)]

    keys = sorted(candidate.param_ranges.keys())
    values = [candidate.param_ranges[k] for k in keys]

    grid: list[dict[str, Any]] = []
    for combo in itertools.product(*values):
        point = dict(candidate.params)
        for k, v in zip(keys, combo):
            point[k] = v
        grid.append(point)

    return grid


# ---------------------------------------------------------------------------
# WFO runner
# ---------------------------------------------------------------------------

def run_wfo(
    candidate: CandidateSpec,
    data_path: str,
    start: str,
    end: str,
    train_months: int = 24,
    test_months: int = 6,
    slide_months: int = 6,
    top_k: int = 3,
    warmup_days: int = 365,
    scenario: str = "base",
    initial_cash: float = 10_000.0,
) -> tuple[list[WFOWindowSpec], list[WFOSurvivor]]:
    """Run walk-forward optimization for a single candidate.

    Returns (windows, survivors) where survivors are ranked by
    pass_rate then median_test_score.
    """
    windows = generate_windows(start, end, train_months, test_months, slide_months)
    if not windows:
        return [], []

    grid = expand_param_grid(candidate)
    cost = SCENARIOS.get(scenario, SCENARIOS["base"])

    # Track per-param results across windows
    # Key: tuple of sorted param items (hashable)
    param_results: dict[tuple, list[WFOWindowResult]] = {}

    for window in windows:
        # --- Train phase: score all grid points ---
        train_scores: list[tuple[dict, float]] = []

        for params in grid:
            spec = CandidateSpec(name="wfo", params=params,
                                 strategy=candidate.strategy)
            strategy, _ = build_strategy(spec)
            feed = DataFeed(
                data_path,
                start=window.train_start,
                end=window.train_end,
                warmup_days=warmup_days,
            )
            engine = BacktestEngine(
                feed=feed,
                strategy=strategy,
                cost=cost,
                initial_cash=initial_cash,
            )
            result = engine.run()
            score = compute_objective(result.summary)
            train_scores.append((params, score))

        # Sort by score descending, take top-K
        train_scores.sort(key=lambda x: x[1], reverse=True)
        top_params = train_scores[:top_k]

        # --- Test phase: evaluate top-K on OOS period ---
        for params, train_score in top_params:
            spec = CandidateSpec(name="wfo", params=params,
                                 strategy=candidate.strategy)
            strategy, _ = build_strategy(spec)
            feed = DataFeed(
                data_path,
                start=window.test_start,
                end=window.test_end,
                warmup_days=warmup_days,
            )
            engine = BacktestEngine(
                feed=feed,
                strategy=strategy,
                cost=cost,
                initial_cash=initial_cash,
            )
            result = engine.run()
            test_score = compute_objective(result.summary)
            test_ret = result.summary.get("total_return_pct", 0.0)
            test_mdd = result.summary.get("max_drawdown_mid_pct", 0.0)

            passed = test_ret > -5.0 and test_mdd < 35.0

            wr = WFOWindowResult(
                window_id=window.window_id,
                params=params,
                train_score=train_score,
                test_score=test_score,
                test_return_pct=test_ret,
                test_mdd_pct=test_mdd,
                passed=passed,
            )

            key = tuple(sorted(params.items()))
            param_results.setdefault(key, []).append(wr)

    # --- Build survivors: tested in 2+ windows ---
    survivors: list[WFOSurvivor] = []
    for key, window_results in param_results.items():
        if len(window_results) < 2:
            continue

        n_tested = len(window_results)
        n_passed = sum(1 for wr in window_results if wr.passed)
        pass_rate = n_passed / n_tested

        test_scores = [
            wr.test_score for wr in window_results
            if wr.test_score is not None
        ]
        test_scores.sort()
        median_score = test_scores[len(test_scores) // 2] if test_scores else 0.0

        survivors.append(WFOSurvivor(
            params=dict(key),
            windows_tested=n_tested,
            windows_passed=n_passed,
            pass_rate=pass_rate,
            median_test_score=median_score,
            window_details=window_results,
        ))

    # Rank: pass_rate desc, then median_test_score desc
    survivors.sort(key=lambda s: (s.pass_rate, s.median_test_score), reverse=True)

    return windows, survivors
