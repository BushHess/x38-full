"""Tests for drawdown episode detection and recovery table."""

from __future__ import annotations

import pytest

from v10.core.types import EquitySnap
from v10.research.drawdown import detect_drawdown_episodes, recovery_table


def _snap(close_time_ms: int, nav: float) -> EquitySnap:
    return EquitySnap(
        close_time=close_time_ms,
        nav_mid=nav,
        nav_liq=nav * 0.99,
        cash=nav * 0.5,
        btc_qty=0.001,
        exposure=0.5,
    )


# 4 hours in ms
H4_MS = 4 * 3600 * 1000


class TestDetectDrawdownEpisodes:
    def test_no_drawdown(self) -> None:
        """Monotonically rising equity → 0 episodes."""
        equity = [_snap(i * H4_MS, 10_000.0 + i * 100) for i in range(20)]
        eps = detect_drawdown_episodes(equity, min_dd_pct=5.0)
        assert len(eps) == 0

    def test_single_episode_with_recovery(self) -> None:
        """Peak=100, trough=90 (-10%), recovery back to 100."""
        navs = [100] * 5 + [95, 92, 90, 93, 97, 100, 102]
        equity = [_snap(i * H4_MS, n) for i, n in enumerate(navs)]
        eps = detect_drawdown_episodes(equity, min_dd_pct=5.0)
        assert len(eps) == 1
        ep = eps[0]
        assert ep.drawdown_pct == pytest.approx(10.0, abs=0.1)
        assert ep.recovery_ms is not None
        assert ep.bars_to_recovery is not None
        assert ep.trough_nav == 90.0

    def test_ongoing_episode(self) -> None:
        """Drawdown that never recovers → recovery_ms=None."""
        navs = [100] * 3 + [90, 85, 88]
        equity = [_snap(i * H4_MS, n) for i, n in enumerate(navs)]
        eps = detect_drawdown_episodes(equity, min_dd_pct=5.0)
        assert len(eps) == 1
        assert eps[0].recovery_ms is None
        assert eps[0].bars_to_recovery is None

    def test_min_threshold_filters(self) -> None:
        """4% dip should NOT appear at min_dd_pct=5.0."""
        navs = [100] * 3 + [96, 97, 100, 101]
        equity = [_snap(i * H4_MS, n) for i, n in enumerate(navs)]
        eps = detect_drawdown_episodes(equity, min_dd_pct=5.0)
        assert len(eps) == 0

    def test_multiple_episodes(self) -> None:
        """Two separate drawdowns with recovery in between."""
        navs = [100, 100, 90, 85, 90, 100, 105, 100, 92, 88, 95, 105, 110]
        equity = [_snap(i * H4_MS, n) for i, n in enumerate(navs)]
        eps = detect_drawdown_episodes(equity, min_dd_pct=5.0)
        assert len(eps) == 2

    def test_empty_equity(self) -> None:
        assert detect_drawdown_episodes([], min_dd_pct=5.0) == []

    def test_single_bar(self) -> None:
        equity = [_snap(0, 100)]
        assert detect_drawdown_episodes(equity, min_dd_pct=5.0) == []


class TestRecoveryTable:
    def test_round_trip(self) -> None:
        """recovery_table produces dicts with expected keys."""
        navs = [100] * 3 + [90, 85, 90, 100, 105]
        equity = [_snap(i * H4_MS, n) for i, n in enumerate(navs)]
        eps = detect_drawdown_episodes(equity, min_dd_pct=5.0)
        table = recovery_table(eps)
        assert len(table) == 1
        row = table[0]
        assert "peak_date" in row
        assert "trough_date" in row
        assert "recovery_date" in row
        assert "drawdown_pct" in row
        assert row["drawdown_pct"] == pytest.approx(15.0, abs=0.1)

    def test_ongoing_recovery_null(self) -> None:
        navs = [100] * 3 + [90, 85]
        equity = [_snap(i * H4_MS, n) for i, n in enumerate(navs)]
        eps = detect_drawdown_episodes(equity, min_dd_pct=5.0)
        table = recovery_table(eps)
        assert table[0]["recovery_date"] is None
        assert table[0]["days_to_recovery"] is None
