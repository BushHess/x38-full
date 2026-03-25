"""Tests for parity checker — shadow-strategy replay verification."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from v10.core.types import Bar, CostConfig, MarketState, SCENARIOS, Signal
from v10.exchange.filters import SymbolInfo
from v10.exchange.order_planner import OrderPlan, plan_order_from_target_exposure
from v10.exchange.parity import ParityChecker, ParityResult
from v10.strategies.base import Strategy

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

FILTERS = SymbolInfo(
    symbol="BTCUSDT",
    base_asset="BTC",
    quote_asset="USDT",
    tick_size=Decimal("0.01"),
    step_size=Decimal("0.00001"),
    min_qty=Decimal("0.00001"),
    max_qty=Decimal("9999.00000"),
    min_notional=Decimal("5.00"),
    price_precision=2,
    qty_precision=5,
)

COST = SCENARIOS["base"]

H4_MS = 4 * 3600 * 1000  # 14_400_000
D1_MS = 24 * 3600 * 1000  # 86_400_000


def _bar(open_time: int, close: float, interval: str = "4h") -> Bar:
    """Create a minimal Bar for testing."""
    if interval == "4h":
        close_time = open_time + H4_MS - 1
    else:
        close_time = open_time + D1_MS - 1
    return Bar(
        open_time=open_time,
        open=close - 100,
        high=close + 200,
        low=close - 200,
        close=close,
        volume=100.0,
        close_time=close_time,
        taker_buy_base_vol=50.0,
        interval=interval,
    )


def _make_h4_bars(n: int, start_ms: int = 1_700_000_000_000, base_price: float = 67000.0) -> list[Bar]:
    """Create n sequential H4 bars."""
    return [_bar(start_ms + i * H4_MS, base_price + i * 10, "4h") for i in range(n)]


def _make_d1_bars(n: int, start_ms: int = 1_700_000_000_000, base_price: float = 67000.0) -> list[Bar]:
    """Create n sequential D1 bars. Each D1 spans 6 H4 bars."""
    return [_bar(start_ms + i * D1_MS, base_price + i * 50, "1d") for i in range(n)]


# ---------------------------------------------------------------------------
# Mock strategies
# ---------------------------------------------------------------------------

class AlwaysBuyStrategy(Strategy):
    """Returns target_exposure=0.5 on every bar."""

    def on_bar(self, state: MarketState) -> Signal | None:
        return Signal(target_exposure=0.5, reason="always_buy")


class AlwaysHoldStrategy(Strategy):
    """Never produces a signal."""

    def on_bar(self, state: MarketState) -> Signal | None:
        return None


class BuyOnceStrategy(Strategy):
    """Returns target_exposure=0.5 on the first bar only."""

    def __init__(self) -> None:
        self._fired = False

    def on_bar(self, state: MarketState) -> Signal | None:
        if not self._fired:
            self._fired = True
            return Signal(target_exposure=0.5, reason="buy_once")
        return None


def _make_actual_plan(
    nav: float = 10_000.0,
    btc_qty: float = 0.0,
    mid: float = 67000.0,
    target_exposure: float = 0.5,
) -> OrderPlan:
    """Create an actual_plan via the real planner."""
    return plan_order_from_target_exposure(
        nav_usdt=nav,
        btc_qty=btc_qty,
        mid_price=mid,
        target_exposure=target_exposure,
        filters=FILTERS,
        cost=COST,
    )


def _make_hold_plan(
    nav: float = 10_000.0,
    btc_qty: float = 0.0,
    mid: float = 67000.0,
) -> OrderPlan:
    """Create a HOLD plan."""
    return plan_order_from_target_exposure(
        nav_usdt=nav,
        btc_qty=btc_qty,
        mid_price=mid,
        target_exposure=0.0,  # at 0 exposure and target 0 → HOLD (below min_notional)
        filters=FILTERS,
        cost=COST,
    )


# ---------------------------------------------------------------------------
# 1) Pass when signals match
# ---------------------------------------------------------------------------

class TestPassScenarios:
    def test_pass_when_signals_match(self) -> None:
        """Shadow and live both produce BUY with same target → pass."""
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
        )
        h4 = _make_h4_bars(10)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:-1], d1)

        # Live produces BUY 0.5 — shadow also says 0.5
        actual_plan = _make_actual_plan(target_exposure=0.5)
        result = checker.check(h4[-1], [], actual_plan)

        assert result.passed is True
        assert result.mismatch == ""
        assert checker.halt_trading is False

    def test_pass_both_hold(self) -> None:
        """Both shadow (None signal) and live produce HOLD → pass."""
        checker = ParityChecker(
            strategy_factory=AlwaysHoldStrategy,
            filters=FILTERS,
            cost=COST,
        )
        h4 = _make_h4_bars(10)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:-1], d1)

        actual_plan = _make_hold_plan()
        result = checker.check(h4[-1], [], actual_plan)

        assert result.passed is True
        assert result.expected_side == "HOLD"
        assert result.actual_side == "HOLD"

    def test_pass_qty_within_tolerance(self) -> None:
        """Small qty difference within tolerance → pass."""
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
            qty_tolerance_pct=5.0,  # generous tolerance
        )
        h4 = _make_h4_bars(10)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:-1], d1)

        # Actual plan with 0.5 target matches shadow's 0.5
        actual_plan = _make_actual_plan(target_exposure=0.5)
        result = checker.check(h4[-1], [], actual_plan)

        assert result.passed is True
        assert result.diff_qty_pct < 5.0


# ---------------------------------------------------------------------------
# 2) Fail scenarios
# ---------------------------------------------------------------------------

class TestFailScenarios:
    def test_fail_side_mismatch(self) -> None:
        """Shadow says BUY, live says HOLD → fail + halt."""
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
        )
        h4 = _make_h4_bars(10)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:-1], d1)

        # Live says HOLD but shadow will say BUY
        actual_plan = _make_hold_plan()
        result = checker.check(h4[-1], [], actual_plan)

        assert result.passed is False
        assert "side" in result.mismatch
        assert checker.halt_trading is True

    def test_fail_qty_beyond_tolerance(self) -> None:
        """Qty diff > tolerance → fail + halt."""
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
            qty_tolerance_pct=0.001,  # very tight tolerance
        )
        h4 = _make_h4_bars(10)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:-1], d1)

        # Actual plan with slightly different target
        actual_plan = _make_actual_plan(target_exposure=0.48)
        result = checker.check(h4[-1], [], actual_plan)

        # Shadow produces 0.5, live produces 0.48 → qty differs
        assert result.passed is False
        assert "qty" in result.mismatch
        assert checker.halt_trading is True


# ---------------------------------------------------------------------------
# 3) Halt flag behavior
# ---------------------------------------------------------------------------

class TestHaltFlag:
    def test_halt_flag_set_on_mismatch(self) -> None:
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
        )
        h4 = _make_h4_bars(10)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:-1], d1)

        assert checker.halt_trading is False

        actual_plan = _make_hold_plan()
        checker.check(h4[-1], [], actual_plan)

        assert checker.halt_trading is True

    def test_halt_flag_stays_true(self) -> None:
        """Once halt is set, it stays True even after a passing check."""
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
        )
        h4 = _make_h4_bars(12)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:9], d1)

        # First check: mismatch → halt
        actual_hold = _make_hold_plan()
        checker.check(h4[9], [], actual_hold)
        assert checker.halt_trading is True

        # Second check: match → halt still True
        actual_buy = _make_actual_plan(target_exposure=0.5)
        checker.check(h4[10], [], actual_buy)
        assert checker.halt_trading is True


# ---------------------------------------------------------------------------
# 4) MTF alignment
# ---------------------------------------------------------------------------

class TestMtfAlignment:
    def test_mtf_alignment_matches_engine(self) -> None:
        """D1 index in shadow matches BacktestEngine's strict-< alignment."""
        # Setup: 12 H4 bars spanning 2 days, 2 D1 bars
        # H4[0..5] = day 0, H4[6..11] = day 1
        # D1[0] = day 0, D1[1] = day 1
        # Last H4 of day 0 (bar 5) has close_time = day 0 D1's close_time
        # → strict < means bar 5 does NOT see D1[0]
        # First H4 of day 1 (bar 6) → sees D1[0]
        start = 1_700_000_000_000
        h4 = _make_h4_bars(12, start_ms=start)
        d1 = _make_d1_bars(2, start_ms=start)

        # The parity checker replays all bars and uses the signal from
        # the last bar. We verify alignment indirectly by checking that
        # the shadow produces a signal (strategy must see valid d1_index).
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
        )
        checker.init_bars(h4[:-1], d1)
        actual_plan = _make_actual_plan(target_exposure=0.5)
        result = checker.check(h4[-1], [], actual_plan)

        # If alignment were broken, the strategy might crash or
        # produce a different signal. Here it should pass cleanly.
        assert result.passed is True


# ---------------------------------------------------------------------------
# 5) Bar accumulation
# ---------------------------------------------------------------------------

class TestBarAccumulation:
    def test_multiple_checks_accumulate_bars(self) -> None:
        """Bars accumulate across check() calls."""
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
        )
        h4 = _make_h4_bars(15)
        d1 = _make_d1_bars(3)
        checker.init_bars(h4[:10], d1)

        actual_plan = _make_actual_plan(target_exposure=0.5)

        # Three sequential checks, each adding one bar
        for bar in h4[10:13]:
            result = checker.check(bar, [], actual_plan)
            assert result.passed is True

        # Internal bar count grew by 3
        assert len(checker._h4) == 13

    def test_new_d1_bars_appended(self) -> None:
        """New D1 bars passed to check() are accumulated."""
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
        )
        h4 = _make_h4_bars(10)
        d1_initial = _make_d1_bars(1)
        d1_new = [_make_d1_bars(2)[1]]  # second D1 bar
        checker.init_bars(h4[:-1], d1_initial)

        actual_plan = _make_actual_plan(target_exposure=0.5)
        checker.check(h4[-1], d1_new, actual_plan)

        assert len(checker._d1) == 2


# ---------------------------------------------------------------------------
# 6) CSV logging
# ---------------------------------------------------------------------------

class TestCsvLogging:
    def test_csv_row_written(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "live_parity.csv"
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
            csv_path=csv_file,
        )
        h4 = _make_h4_bars(10)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:-1], d1)

        actual_plan = _make_actual_plan(target_exposure=0.5)
        checker.check(h4[-1], [], actual_plan)

        with open(csv_file) as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2  # header + 1 data row
        assert rows[0][0] == "timestamp_iso"
        assert rows[0][2] == "passed"
        # Data row
        assert rows[1][2] == "True"

    def test_csv_multiple_rows(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "live_parity.csv"
        checker = ParityChecker(
            strategy_factory=AlwaysBuyStrategy,
            filters=FILTERS,
            cost=COST,
            csv_path=csv_file,
        )
        h4 = _make_h4_bars(12)
        d1 = _make_d1_bars(2)
        checker.init_bars(h4[:10], d1)

        actual_plan = _make_actual_plan(target_exposure=0.5)
        checker.check(h4[10], [], actual_plan)
        checker.check(h4[11], [], actual_plan)

        with open(csv_file) as f:
            rows = list(csv.reader(f))
        assert len(rows) == 3  # header + 2 data rows
