"""Tests for analytical regime classification and return decomposition."""

from __future__ import annotations

import pytest

from v10.core.types import Bar, EquitySnap
from v10.research.regime import AnalyticalRegime, classify_d1_regimes, compute_regime_returns


D1_MS = 86_400_000
BASE_OT = 1_000_000_000_000  # ~2001 epoch-ms


def _d1_bar(day: int, close: float, high: float | None = None, low: float | None = None) -> Bar:
    ot = BASE_OT + day * D1_MS
    h = high if high is not None else close * 1.01
    lo = low if low is not None else close * 0.99
    return Bar(
        open_time=ot,
        open=close,
        high=h,
        low=lo,
        close=close,
        volume=1000.0,
        close_time=ot + D1_MS - 1,
        taker_buy_base_vol=500.0,
        interval="1d",
    )


class TestClassifyD1Regimes:
    def test_empty(self) -> None:
        assert classify_d1_regimes([]) == []

    def test_length_matches(self) -> None:
        bars = [_d1_bar(i, 50000 + i * 100) for i in range(100)]
        regimes = classify_d1_regimes(bars)
        assert len(regimes) == len(bars)

    def test_all_enums_valid(self) -> None:
        """All returned values must be AnalyticalRegime members."""
        bars = [_d1_bar(i, 50000 + i * 100) for i in range(300)]
        regimes = classify_d1_regimes(bars)
        for r in regimes:
            assert isinstance(r, AnalyticalRegime)

    def test_shock_on_large_move(self) -> None:
        """A >8% daily move should classify as SHOCK."""
        bars = [_d1_bar(0, 50000)]
        # Day 1: +10% move
        bars.append(_d1_bar(1, 55000, high=55500, low=54000))
        regimes = classify_d1_regimes(bars)
        assert regimes[1] == AnalyticalRegime.SHOCK

    def test_bull_regime(self) -> None:
        """Steadily rising prices above EMA_slow → BULL after warmup."""
        # Create 250 bars of steady uptrend to warm up EMAs
        bars = [_d1_bar(i, 30000 + i * 200) for i in range(250)]
        regimes = classify_d1_regimes(bars)
        # Last bars should be BULL (close > EMA_slow, EMA_fast > EMA_slow)
        assert regimes[-1] == AnalyticalRegime.BULL

    def test_bear_regime(self) -> None:
        """Falling prices below EMA_slow → BEAR after warmup."""
        # Rise then fall
        bars = [_d1_bar(i, 50000 + i * 100) for i in range(250)]
        # Sharp decline for 100 bars
        for i in range(100):
            bars.append(_d1_bar(250 + i, 75000 - i * 400))
        regimes = classify_d1_regimes(bars)
        # Late bars should be BEAR
        bear_count = sum(1 for r in regimes[-30:] if r == AnalyticalRegime.BEAR)
        assert bear_count > 10, f"Expected many BEAR bars in decline, got {bear_count}"


class TestComputeRegimeReturns:
    def test_empty(self) -> None:
        assert compute_regime_returns([], [], []) == {}

    def test_has_expected_keys(self) -> None:
        """Return dict should have regime names as keys with stats."""
        bars = [_d1_bar(i, 50000 + i * 100) for i in range(250)]
        regimes = classify_d1_regimes(bars)

        # Create matching equity (H4 = 6 bars per D1)
        H4_MS = 4 * 3600 * 1000
        equity = []
        for i in range(len(bars)):
            for j in range(6):
                idx = i * 6 + j
                t = BASE_OT + i * D1_MS + j * H4_MS + H4_MS - 1
                nav = 10000 + idx * 5
                equity.append(EquitySnap(
                    close_time=t, nav_mid=nav, nav_liq=nav * 0.99,
                    cash=nav * 0.5, btc_qty=0.001, exposure=0.5,
                ))

        result = compute_regime_returns(equity, bars, regimes)
        assert len(result) > 0
        for regime_name, stats in result.items():
            assert regime_name in [r.value for r in AnalyticalRegime]
            assert "total_return_pct" in stats
            assert "max_dd_pct" in stats
            assert "n_bars" in stats
            assert "n_days" in stats
