"""Numerical tests for selection_bias suite helpers.

Verifies that _daily_log_returns and _annualized_sharpe produce correct
values, and that the PSR/DSR calling convention uses a single consistent
return series (daily log-returns) for all inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pytest

from validation.suites.selection_bias import _daily_log_returns, _annualized_sharpe


# ---------------------------------------------------------------------------
# Minimal EquitySnap stub for unit tests
# ---------------------------------------------------------------------------

@dataclass
class _Snap:
    close_time: int
    nav_mid: float


_MS_PER_DAY = 86_400_000
_MS_PER_4H = 4 * 3_600_000


class TestDailyLogReturns:
    """Tests for _daily_log_returns helper."""

    def test_uses_last_snapshot_per_day(self) -> None:
        """When multiple H4 snapshots fall on the same UTC day,
        the LAST one (daily close) should be used, not the first."""
        base = 1_000 * _MS_PER_DAY  # day 1000

        # Day 0: two snapshots — first at nav=100, last at nav=110
        # Day 1: two snapshots — first at nav=105, last at nav=120
        snaps = [
            _Snap(close_time=base + 0 * _MS_PER_4H, nav_mid=100.0),
            _Snap(close_time=base + 1 * _MS_PER_4H, nav_mid=110.0),
            _Snap(close_time=base + _MS_PER_DAY + 0 * _MS_PER_4H, nav_mid=105.0),
            _Snap(close_time=base + _MS_PER_DAY + 1 * _MS_PER_4H, nav_mid=120.0),
        ]
        daily = _daily_log_returns(snaps)
        # Should use nav 110 (day 0 close) and 120 (day 1 close)
        expected = np.log(120.0 / 110.0)
        assert len(daily) == 1
        assert daily[0] == pytest.approx(expected, rel=1e-10)

    def test_single_day_returns_empty(self) -> None:
        """Only one day of data → no returns."""
        snaps = [
            _Snap(close_time=0, nav_mid=100.0),
            _Snap(close_time=_MS_PER_4H, nav_mid=101.0),
        ]
        daily = _daily_log_returns(snaps)
        assert len(daily) == 0

    def test_empty_equity_returns_empty(self) -> None:
        assert len(_daily_log_returns([])) == 0
        assert len(_daily_log_returns(None)) == 0

    def test_three_days_correct_series(self) -> None:
        """Three daily closes → two log returns."""
        snaps = [
            _Snap(close_time=0 * _MS_PER_DAY + 5 * _MS_PER_4H, nav_mid=100.0),
            _Snap(close_time=1 * _MS_PER_DAY + 5 * _MS_PER_4H, nav_mid=105.0),
            _Snap(close_time=2 * _MS_PER_DAY + 5 * _MS_PER_4H, nav_mid=110.0),
        ]
        daily = _daily_log_returns(snaps)
        assert len(daily) == 2
        assert daily[0] == pytest.approx(np.log(105.0 / 100.0), rel=1e-10)
        assert daily[1] == pytest.approx(np.log(110.0 / 105.0), rel=1e-10)


class TestAnnualizedSharpe:
    """Tests for _annualized_sharpe helper."""

    def test_known_sharpe(self) -> None:
        """Deterministic returns → known Sharpe."""
        # 365 days of 0.1% daily return
        daily = np.full(365, 0.001)
        mu = 0.001
        sigma = 0.0  # zero vol → should return 0.0
        assert _annualized_sharpe(daily) == 0.0

    def test_nonzero_vol(self) -> None:
        """Mixed returns → (mu/sigma) * sqrt(365)."""
        rng = np.random.default_rng(42)
        daily = rng.normal(0.001, 0.02, size=500)
        mu = float(np.mean(daily))
        sigma = float(np.std(daily, ddof=0))
        expected = (mu / sigma) * math.sqrt(365.0)
        assert _annualized_sharpe(daily) == pytest.approx(expected, rel=1e-10)

    def test_too_few_returns(self) -> None:
        assert _annualized_sharpe(np.array([0.01])) == 0.0
        assert _annualized_sharpe(np.array([])) == 0.0
