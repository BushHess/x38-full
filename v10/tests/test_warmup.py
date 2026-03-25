"""Tests for warmup/reporting separation and fills.csv consistency.

Tests:
  1. FillsCsvRowCount — fills.csv row count == summary fills count
  2. WarmupNoReportedTrades — fills/trades during warmup excluded from results
  3. WarmupIndicatorInit — strategy sees warmed-up indicator state at reporting start
  4. WarmupPortfolioCarryover — portfolio state carries over from warmup to reporting
  5. FillsCsvWriteAndRead — end-to-end: write fills.csv, verify content
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pytest

from v10.core.types import (
    Bar, CostConfig, Order, Side, Signal, MarketState, EquitySnap,
    BacktestResult,
)
from v10.core.engine import BacktestEngine
from v10.core.execution import ExecutionModel
from v10.strategies.base import Strategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

H4_MS = 14_400_000  # 4 hours in milliseconds


class _FakeFeed:
    """Minimal DataFeed substitute with report_start_ms support."""

    def __init__(
        self,
        h4_bars: list[Bar],
        d1_bars: list[Bar] | None = None,
        report_start_ms: int | None = None,
    ):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars or []
        self.report_start_ms = report_start_ms


def _bar(index: int, open_: float, close: float, base_ms: int = 0) -> Bar:
    ot = base_ms + index * H4_MS
    return Bar(
        open_time=ot,
        open=open_,
        high=max(open_, close) * 1.001,
        low=min(open_, close) * 0.999,
        close=close,
        volume=100.0,
        close_time=ot + H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


def _flat_bars(n: int, price: float, base_ms: int = 0) -> list[Bar]:
    return [_bar(i, price, price, base_ms) for i in range(n)]


ZERO_COST = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.0)
FEE_ONLY = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.10)


class _ScriptedStrategy(Strategy):
    """Emits pre-defined signals at specific bar indices."""

    def __init__(self, script: dict[int, Signal]) -> None:
        self._script = script

    def on_bar(self, state: MarketState) -> Signal | None:
        return self._script.get(state.bar_index)


class _CountingStrategy(Strategy):
    """Counts on_bar calls and tracks bar indices seen."""

    def __init__(self, buy_at: int | None = None) -> None:
        self.call_count = 0
        self.bar_indices: list[int] = []
        self._buy_at = buy_at

    def on_bar(self, state: MarketState) -> Signal | None:
        self.call_count += 1
        self.bar_indices.append(state.bar_index)
        if self._buy_at is not None and state.bar_index == self._buy_at:
            return Signal(target_exposure=1.0, reason="buy")
        return None


def _write_fills_csv(fills, path: Path) -> None:
    """Replicate cli/backtest.py fills.csv writer."""
    from v10.core.formatting import ms_to_iso

    with open(path, "w") as f:
        f.write("time,ts_ms,side,qty,price,fee,notional,reason\n")
        for fl in fills:
            f.write(
                f"{ms_to_iso(fl.ts_ms)},{fl.ts_ms},"
                f"{fl.side.value},{fl.qty:.8f},"
                f"{fl.price:.2f},{fl.fee:.4f},{fl.notional:.2f},{fl.reason}\n"
            )


# ---------------------------------------------------------------------------
# TEST 1: FillsCsvRowCount — row count matches summary
# ---------------------------------------------------------------------------

class TestFillsCsvRowCount:
    """fills.csv must contain exactly the same number of rows as fills
    recorded in the backtest result (excluding header)."""

    def test_row_count_matches_result_fills(self) -> None:
        PRICE, CASH, QTY = 50_000.0, 10_000.0, 0.05

        # 20 reporting bars, buy+sell = 2 fills
        bars = _flat_bars(20, PRICE)
        strategy = _ScriptedStrategy({
            0: Signal(orders=[Order(Side.BUY, QTY)], reason="entry"),
            5: Signal(orders=[Order(Side.SELL, QTY)], reason="exit"),
        })
        feed = _FakeFeed(bars)
        engine = BacktestEngine(feed, strategy, FEE_ONLY, initial_cash=CASH)
        result = engine.run()

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fills.csv"
            _write_fills_csv(result.fills, csv_path)

            with open(csv_path) as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)

            assert header == ["time", "ts_ms", "side", "qty", "price", "fee", "notional", "reason"], (
                f"Unexpected fills.csv header: {header}")
            assert len(rows) == len(result.fills), (
                f"fills.csv rows ({len(rows)}) != result.fills ({len(result.fills)})")
            assert len(rows) == result.summary.get("fills_count", len(result.fills)), (
                f"fills.csv rows ({len(rows)}) != summary fills count")

    def test_zero_fills_produces_header_only(self) -> None:
        """Null strategy → 0 fills → CSV has header only."""
        bars = _flat_bars(10, 50_000.0)

        class _Null(Strategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                return None

        feed = _FakeFeed(bars)
        engine = BacktestEngine(feed, _Null(), ZERO_COST, initial_cash=10_000.0)
        result = engine.run()

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fills.csv"
            _write_fills_csv(result.fills, csv_path)

            with open(csv_path) as f:
                lines = f.readlines()

            assert len(lines) == 1, (
                f"Expected 1 line (header only), got {len(lines)}")
            assert len(result.fills) == 0


# ---------------------------------------------------------------------------
# TEST 2: WarmupNoReportedTrades — warmup fills/trades excluded
# ---------------------------------------------------------------------------

class TestWarmupNoReportedTrades:
    """Strategy trades during warmup, but result.fills / result.trades
    must contain ONLY fills/trades from the reporting window."""

    def test_warmup_trades_excluded(self) -> None:
        """10 warmup bars + 10 reporting bars.
        Buy at bar[2] (warmup), sell at bar[4] (warmup) → excluded.
        Buy at bar[12] (reporting), sell at bar[14] (reporting) → included.
        """
        PRICE, CASH, QTY = 50_000.0, 10_000.0, 0.05
        total_bars = 20
        bars = _flat_bars(total_bars, PRICE)

        # Warmup ends at bar[10].close_time = 10 * H4_MS - 1
        # report_start_ms = 10 * H4_MS (bar[10] is first reporting bar)
        report_start_ms = 10 * H4_MS

        strategy = _ScriptedStrategy({
            # Warmup: buy at bar[2].close → fill at bar[3].open
            2: Signal(orders=[Order(Side.BUY, QTY)], reason="warmup_buy"),
            # Warmup: sell at bar[4].close → fill at bar[5].open
            4: Signal(orders=[Order(Side.SELL, QTY)], reason="warmup_sell"),
            # Reporting: buy at bar[12].close → fill at bar[13].open
            12: Signal(orders=[Order(Side.BUY, QTY)], reason="report_buy"),
            # Reporting: sell at bar[14].close → fill at bar[15].open
            14: Signal(orders=[Order(Side.SELL, QTY)], reason="report_sell"),
        })
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(feed, strategy, ZERO_COST, initial_cash=CASH)
        result = engine.run()

        # Only reporting fills should appear
        assert len(result.fills) == 2, (
            f"Expected 2 reporting fills, got {len(result.fills)}: "
            f"{[f.reason for f in result.fills]}")
        assert result.fills[0].reason == "report_buy", (
            f"First fill should be report_buy, got {result.fills[0].reason}")
        assert result.fills[1].reason == "report_sell", (
            f"Second fill should be report_sell, got {result.fills[1].reason}")

        # Only reporting trades should appear
        assert len(result.trades) == 1, (
            f"Expected 1 reporting trade, got {len(result.trades)}")
        assert result.trades[0].entry_reason == "report_buy"
        assert result.trades[0].exit_reason == "report_sell"

        # Equity should start at reporting window
        assert len(result.equity) == 10, (
            f"Expected 10 equity snaps (reporting bars), got {len(result.equity)}")
        first_snap_time = result.equity[0].close_time
        assert first_snap_time >= report_start_ms, (
            f"First equity snap ({first_snap_time}) is before "
            f"report_start_ms ({report_start_ms})")

    def test_warmup_fills_not_in_csv(self) -> None:
        """fills.csv must contain only reporting-window fills."""
        PRICE, QTY = 40_000.0, 0.02
        bars = _flat_bars(16, PRICE)
        report_start_ms = 8 * H4_MS

        strategy = _ScriptedStrategy({
            1: Signal(orders=[Order(Side.BUY, QTY)], reason="w_buy"),
            3: Signal(orders=[Order(Side.SELL, QTY)], reason="w_sell"),
            9: Signal(orders=[Order(Side.BUY, QTY)], reason="r_buy"),
        })
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(feed, strategy, FEE_ONLY, initial_cash=10_000.0)
        result = engine.run()

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fills.csv"
            _write_fills_csv(result.fills, csv_path)

            with open(csv_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

        assert len(rows) == 1, (
            f"Expected 1 fill row (r_buy only), got {len(rows)}")
        assert rows[0]["reason"] == "r_buy", (
            f"Expected reason 'r_buy', got {rows[0]['reason']}")

        # Verify all fill timestamps are >= report_start_ms
        for row in rows:
            assert int(row["ts_ms"]) >= report_start_ms, (
                f"Fill at ts_ms={row['ts_ms']} is before report_start_ms={report_start_ms}")


# ---------------------------------------------------------------------------
# TEST 3: WarmupIndicatorInit — strategy sees full bar history
# ---------------------------------------------------------------------------

class TestWarmupIndicatorInit:
    """Strategy on_bar() receives full h4_bars (warmup + reporting).
    bar_index at reporting start should be > 0 (warmup bars precede)."""

    def test_strategy_sees_warmup_bars(self) -> None:
        """10 warmup + 10 reporting bars. Strategy should be called on ALL 20."""
        bars = _flat_bars(20, 50_000.0)
        report_start_ms = 10 * H4_MS

        counting = _CountingStrategy()
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(feed, counting, ZERO_COST, initial_cash=10_000.0)
        engine.run()

        # Strategy called on every bar (warmup + reporting)
        assert counting.call_count == 20, (
            f"Expected 20 on_bar() calls (10 warmup + 10 reporting), "
            f"got {counting.call_count}")

        # bar_indices should be 0..19
        assert counting.bar_indices == list(range(20)), (
            f"bar_indices should be 0..19, got first/last: "
            f"{counting.bar_indices[0]}..{counting.bar_indices[-1]}")

    def test_bar_index_at_report_start(self) -> None:
        """At the first reporting bar, bar_index should reflect warmup history."""
        WARMUP_N, REPORT_N = 15, 10
        bars = _flat_bars(WARMUP_N + REPORT_N, 60_000.0)
        report_start_ms = WARMUP_N * H4_MS

        indices_at_report: list[int] = []

        class _Tracker(Strategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                if state.bar.close_time >= report_start_ms:
                    indices_at_report.append(state.bar_index)
                return None

        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(feed, _Tracker(), ZERO_COST, initial_cash=10_000.0)
        engine.run()

        # First reporting bar should have bar_index == WARMUP_N
        assert indices_at_report[0] == WARMUP_N, (
            f"First reporting bar_index={indices_at_report[0]}, "
            f"expected {WARMUP_N} (warmup bars provide look-back)")
        assert len(indices_at_report) == REPORT_N


# ---------------------------------------------------------------------------
# TEST 4: WarmupPortfolioCarryover — state carries from warmup to reporting
# ---------------------------------------------------------------------------

class TestWarmupPortfolioCarryover:
    """Portfolio state (cash, btc_qty) established during warmup
    is visible in reporting-window equity snapshots."""

    def test_warmup_position_visible_in_reporting(self) -> None:
        """Buy during warmup, hold into reporting. First equity snap
        must show btc_qty > 0 and cash < initial."""
        PRICE, CASH = 50_000.0, 10_000.0
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        # Buy at bar[2] during warmup — position carries into reporting
        strategy = _ScriptedStrategy({
            2: Signal(target_exposure=1.0, reason="warmup_entry"),
        })
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, strategy, ZERO_COST, initial_cash=CASH,
            warmup_mode="allow_trade",
        )
        result = engine.run()

        # First equity snap (first reporting bar) should show position
        first = result.equity[0]
        assert first.btc_qty > 0, (
            f"Expected btc_qty > 0 from warmup buy, got {first.btc_qty}")
        assert first.cash < CASH, (
            f"Expected cash < {CASH} (warmup buy debited), got {first.cash}")
        assert first.nav_mid == pytest.approx(CASH, abs=0.01), (
            f"Zero-cost flat-price NAV should be {CASH}, got {first.nav_mid}")

        # The warmup buy fill should NOT be in result.fills
        assert len(result.fills) == 0, (
            f"Expected 0 reporting fills (buy was warmup), "
            f"got {len(result.fills)}: {[f.reason for f in result.fills]}")

    def test_report_start_nav_for_metrics(self) -> None:
        """CAGR should be computed from NAV at reporting start, not initial_cash.
        Uses allow_trade mode to test warmup position carryover."""
        PRICE_LOW, PRICE_HIGH = 50_000.0, 100_000.0
        CASH = 10_000.0

        # 10 warmup bars at low price, 10 reporting bars at high price
        warmup_bars = _flat_bars(10, PRICE_LOW)
        report_bars = _flat_bars(10, PRICE_HIGH, base_ms=10 * H4_MS)
        bars = warmup_bars + report_bars
        report_start_ms = 10 * H4_MS

        # Buy at bar[0] → fill at bar[1].open at low price
        strategy = _ScriptedStrategy({
            0: Signal(target_exposure=1.0, reason="warmup_entry"),
        })
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, strategy, ZERO_COST, initial_cash=CASH,
            warmup_mode="allow_trade",
        )
        result = engine.run()

        # NAV at reporting start: btc_qty × PRICE_HIGH
        # With zero cost: btc_qty = CASH / PRICE_LOW = 0.2
        # NAV at report start = 0.2 × PRICE_HIGH = 20_000
        expected_qty = CASH / PRICE_LOW
        nav_at_start = expected_qty * PRICE_HIGH
        assert result.equity[0].nav_mid == pytest.approx(nav_at_start, abs=1.0), (
            f"Report start NAV expected {nav_at_start}, got {result.equity[0].nav_mid}")

        # summary fields: initial_cash = actual starting cash,
        # report_start_nav = NAV at first reporting bar
        assert result.summary["initial_cash"] == CASH, (
            f"initial_cash should always be {CASH}, "
            f"got {result.summary['initial_cash']}")
        assert result.summary["report_start_nav"] == pytest.approx(
            nav_at_start, abs=1.0), (
            f"report_start_nav expected {nav_at_start}, "
            f"got {result.summary['report_start_nav']}")

        # Since all reporting bars are flat at PRICE_HIGH, CAGR ≈ 0%
        # (growth happens only during warmup, which is excluded from reporting)
        assert abs(result.summary.get("cagr_pct", 999)) < 5.0, (
            f"CAGR should be ~0% (flat during reporting), "
            f"got {result.summary.get('cagr_pct')}%")


# ---------------------------------------------------------------------------
# TEST 5: FillsCsvWriteAndRead — end-to-end content verification
# ---------------------------------------------------------------------------

class TestFillsCsvContent:
    """Verify fills.csv field values match result.fills exactly."""

    def test_csv_fields_match_fills(self) -> None:
        PRICE, CASH, QTY = 50_000.0, 10_000.0, 0.05

        bars = _flat_bars(15, PRICE)
        strategy = _ScriptedStrategy({
            0: Signal(orders=[Order(Side.BUY, QTY)], reason="buy"),
            5: Signal(orders=[Order(Side.SELL, QTY)], reason="sell"),
        })
        feed = _FakeFeed(bars)
        engine = BacktestEngine(feed, strategy, FEE_ONLY, initial_cash=CASH)
        result = engine.run()

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fills.csv"
            _write_fills_csv(result.fills, csv_path)

            with open(csv_path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

        assert len(rows) == len(result.fills)

        for i, (row, fill) in enumerate(zip(rows, result.fills)):
            assert int(row["ts_ms"]) == fill.ts_ms, (
                f"Row[{i}] ts_ms mismatch: csv={row['ts_ms']}, fill={fill.ts_ms}")
            assert row["side"] == fill.side.value, (
                f"Row[{i}] side mismatch: csv={row['side']}, fill={fill.side.value}")
            assert float(row["qty"]) == pytest.approx(fill.qty, abs=1e-6), (
                f"Row[{i}] qty mismatch")
            assert float(row["price"]) == pytest.approx(fill.price, abs=0.01), (
                f"Row[{i}] price mismatch")
            assert float(row["fee"]) == pytest.approx(fill.fee, abs=0.001), (
                f"Row[{i}] fee mismatch")
            assert row["reason"] == fill.reason, (
                f"Row[{i}] reason mismatch: csv={row['reason']}, fill={fill.reason}")


# ---------------------------------------------------------------------------
# TEST 6: WarmupModeNoTrade — default mode discards warmup signals
# ---------------------------------------------------------------------------

class TestWarmupModeNoTrade:
    """In no_trade mode (default), strategy.on_bar() is called during
    warmup for indicator computation, but signals are discarded — no fills."""

    def test_no_fills_during_warmup(self) -> None:
        """Signals emitted during warmup produce zero fills in no_trade mode."""
        PRICE, CASH, QTY = 50_000.0, 10_000.0, 0.05
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        strategy = _ScriptedStrategy({
            2: Signal(orders=[Order(Side.BUY, QTY)], reason="warmup_buy"),
            4: Signal(orders=[Order(Side.SELL, QTY)], reason="warmup_sell"),
            12: Signal(orders=[Order(Side.BUY, QTY)], reason="report_buy"),
            14: Signal(orders=[Order(Side.SELL, QTY)], reason="report_sell"),
        })
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        # Default warmup_mode="no_trade"
        engine = BacktestEngine(feed, strategy, ZERO_COST, initial_cash=CASH)
        result = engine.run()

        # Warmup signals discarded → only reporting fills
        assert len(result.fills) == 2, (
            f"Expected 2 fills (reporting only), got {len(result.fills)}: "
            f"{[f.reason for f in result.fills]}")
        assert result.fills[0].reason == "report_buy"
        assert result.fills[1].reason == "report_sell"

        # Portfolio should be flat at reporting start (no warmup trades)
        first = result.equity[0]
        assert first.btc_qty == pytest.approx(0.0, abs=1e-10), (
            f"Expected btc_qty=0 at reporting start (no_trade), got {first.btc_qty}")
        assert first.cash == pytest.approx(CASH, abs=0.01), (
            f"Expected cash={CASH} at reporting start, got {first.cash}")

    def test_strategy_still_called_during_warmup(self) -> None:
        """In no_trade mode, strategy.on_bar() IS called during warmup
        (for indicator computation), signals are just discarded."""
        bars = _flat_bars(20, 50_000.0)
        report_start_ms = 10 * H4_MS

        counting = _CountingStrategy()
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(feed, counting, ZERO_COST, initial_cash=10_000.0)
        engine.run()

        # All 20 bars see on_bar() called
        assert counting.call_count == 20, (
            f"Expected 20 on_bar() calls in no_trade mode, got {counting.call_count}")
        assert counting.bar_indices == list(range(20))

    def test_last_warmup_signal_discarded(self) -> None:
        """Signal on the last warmup bar must NOT execute at first reporting bar."""
        PRICE, CASH = 50_000.0, 10_000.0
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        # Signal on bar[9] — last warmup bar
        strategy = _ScriptedStrategy({
            9: Signal(target_exposure=1.0, reason="last_warmup"),
        })
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(feed, strategy, ZERO_COST, initial_cash=CASH)
        result = engine.run()

        # No fills at all — the bar[9] signal is discarded
        assert len(result.fills) == 0, (
            f"Expected 0 fills (last warmup signal discarded), "
            f"got {len(result.fills)}: {[f.reason for f in result.fills]}")
        # Portfolio flat
        assert result.equity[0].btc_qty == pytest.approx(0.0, abs=1e-10)

    def test_report_start_nav_equals_initial_cash(self) -> None:
        """In no_trade mode, report_start_nav == initial_cash (no warmup trades)."""
        CASH = 10_000.0
        bars = _flat_bars(20, 50_000.0)
        report_start_ms = 10 * H4_MS

        strategy = _ScriptedStrategy({
            2: Signal(target_exposure=1.0, reason="warmup_buy"),
        })
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(feed, strategy, ZERO_COST, initial_cash=CASH)
        result = engine.run()

        assert result.summary["initial_cash"] == CASH
        assert result.summary["report_start_nav"] == CASH, (
            f"In no_trade mode, report_start_nav should equal initial_cash "
            f"({CASH}), got {result.summary['report_start_nav']}")

    def test_allow_trade_vs_no_trade_divergence(self) -> None:
        """Same setup: allow_trade carries warmup position, no_trade doesn't."""
        PRICE_LOW, PRICE_HIGH = 50_000.0, 100_000.0
        CASH = 10_000.0

        warmup_bars = _flat_bars(10, PRICE_LOW)
        report_bars = _flat_bars(10, PRICE_HIGH, base_ms=10 * H4_MS)
        bars = warmup_bars + report_bars
        report_start_ms = 10 * H4_MS

        strategy_at = _ScriptedStrategy({
            0: Signal(target_exposure=1.0, reason="warmup_entry"),
        })
        strategy_nt = _ScriptedStrategy({
            0: Signal(target_exposure=1.0, reason="warmup_entry"),
        })

        feed_at = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine_at = BacktestEngine(
            feed_at, strategy_at, ZERO_COST, initial_cash=CASH,
            warmup_mode="allow_trade",
        )
        result_at = engine_at.run()

        feed_nt = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine_nt = BacktestEngine(
            feed_nt, strategy_nt, ZERO_COST, initial_cash=CASH,
            warmup_mode="no_trade",
        )
        result_nt = engine_nt.run()

        # allow_trade: price doubled → report_start_nav = 20,000
        assert result_at.summary["report_start_nav"] == pytest.approx(20_000, abs=1.0)
        # no_trade: no warmup trades → report_start_nav = 10,000
        assert result_nt.summary["report_start_nav"] == pytest.approx(CASH, abs=0.01)

        # Both have initial_cash = 10,000
        assert result_at.summary["initial_cash"] == CASH
        assert result_nt.summary["initial_cash"] == CASH

        # allow_trade: btc_qty > 0 at report start
        assert result_at.equity[0].btc_qty > 0
        # no_trade: flat at report start
        assert result_nt.equity[0].btc_qty == pytest.approx(0.0, abs=1e-10)


# ---------------------------------------------------------------------------
# TEST 7: WarmupStateRollback — no_trade mode rolls back strategy mutations
# ---------------------------------------------------------------------------

class _MutatingStrategy(Strategy):
    """Strategy that sets _in_position before returning Signal.

    Reproduces the pattern in VTrend/VTrendE5Ema21D1/BuyAndHold where
    on_bar() mutates internal state before returning a Signal.
    """

    def __init__(self) -> None:
        self._in_position = False
        self._peak_price = 0.0

    def on_bar(self, state: MarketState) -> Signal | None:
        if not self._in_position:
            # Entry: set state BEFORE return — the bug pattern
            self._in_position = True
            self._peak_price = state.bar.close
            return Signal(target_exposure=1.0, reason="entry")
        return None


class TestWarmupStateRollback:
    """In no_trade mode, strategy state mutations must be rolled back
    when signals are discarded during warmup.  Without rollback, the
    strategy 'thinks' it entered a position but the portfolio is flat,
    causing desynchronisation that can suppress all future trades."""

    def test_mutating_strategy_generates_fills_after_warmup(self) -> None:
        """A strategy that mutates _in_position before returning Signal
        must still produce fills after warmup in no_trade mode."""
        PRICE, CASH = 50_000.0, 10_000.0
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        strategy = _MutatingStrategy()
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, strategy, ZERO_COST, initial_cash=CASH,
            warmup_mode="no_trade",
        )
        result = engine.run()

        # Strategy should enter after warmup — at least 1 fill
        assert len(result.fills) >= 1, (
            f"Expected >=1 fill after warmup (state rollback), "
            f"got {len(result.fills)}")
        assert result.fills[0].reason == "entry"

    def test_buy_and_hold_works_in_no_trade_mode(self) -> None:
        """BuyAndHold must produce a fill after warmup in no_trade mode.
        Regression: _entered was set during warmup, blocking all future signals."""
        from v10.strategies.buy_and_hold import BuyAndHold

        PRICE, CASH = 50_000.0, 10_000.0
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        strategy = BuyAndHold()
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, strategy, ZERO_COST, initial_cash=CASH,
            warmup_mode="no_trade",
        )
        result = engine.run()

        assert len(result.fills) == 1, (
            f"BuyAndHold should produce exactly 1 fill after warmup, "
            f"got {len(result.fills)}")
        assert result.summary["report_start_nav"] == pytest.approx(CASH, abs=0.01)
        # After the buy, final NAV should reflect holdings
        assert result.equity[-1].btc_qty > 0

    def test_no_trade_strategy_state_not_corrupted(self) -> None:
        """After warmup, _in_position must be False (matching flat portfolio)."""
        PRICE = 50_000.0
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        strategy = _MutatingStrategy()
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, strategy, ZERO_COST, initial_cash=10_000.0,
            warmup_mode="no_trade",
        )

        # Run just to the end of warmup to inspect strategy state
        # by running the full engine and checking the first fill
        result = engine.run()

        # The first fill must be an entry (state was rolled back correctly)
        assert result.fills[0].reason == "entry", (
            f"First fill should be 'entry', got {result.fills[0].reason}")

    def test_is_warmup_field_in_market_state(self) -> None:
        """MarketState.is_warmup must be True during warmup, False after."""
        bars = _flat_bars(20, 50_000.0)
        report_start_ms = 10 * H4_MS
        warmup_flags: list[bool] = []

        class _WarmupTracker(Strategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                warmup_flags.append(state.is_warmup)
                return None

        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, _WarmupTracker(), ZERO_COST, initial_cash=10_000.0,
            warmup_mode="no_trade",
        )
        engine.run()

        assert len(warmup_flags) == 20
        # First 10 bars are warmup
        assert all(warmup_flags[:10]), (
            f"First 10 bars should have is_warmup=True, got {warmup_flags[:10]}")
        # Last 10 bars are reporting
        assert not any(warmup_flags[10:]), (
            f"Last 10 bars should have is_warmup=False, got {warmup_flags[10:]}")

    def test_mutable_container_rollback(self) -> None:
        """Mutable containers (list, deque) must be rolled back correctly.

        Regression: shallow dict copy shared list/deque references, so
        in-place mutations (append) survived the rollback.
        """
        from collections import deque

        PRICE = 50_000.0
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        class _ListMutator(Strategy):
            def __init__(self) -> None:
                self._in_position = False
                self._log: list[int] = []
                self._ring: deque[float] = deque(maxlen=5)

            def on_bar(self, state: MarketState) -> Signal | None:
                self._log.append(state.bar_index)
                self._ring.append(state.bar.close)
                if not self._in_position:
                    self._in_position = True
                    return Signal(target_exposure=1.0, reason="entry")
                return None

        strategy = _ListMutator()
        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, strategy, ZERO_COST, initial_cash=10_000.0,
            warmup_mode="no_trade",
        )
        engine.run()

        # After warmup rollback, the list and deque should NOT contain
        # entries from warmup bars where a signal was returned.
        # Bar 0: signal returned → rollback (list/deque restored)
        # Bar 1: _in_position=False again → signal returned → rollback
        # ... repeats every warmup bar
        # Bar 10 (first reporting): enters for real
        # The list should contain bar 10 onward (reporting),
        # NOT bars 0-9 (rolled back during warmup).
        assert strategy._log[0] == 10, (
            f"First persisted log entry should be bar 10, got {strategy._log[0]}"
        )

    def test_on_after_fill_receives_correct_is_warmup(self) -> None:
        """on_after_fill must receive is_warmup=True for warmup fills
        and is_warmup=False for reporting fills."""
        PRICE, CASH, QTY = 50_000.0, 10_000.0, 0.05
        bars = _flat_bars(20, PRICE)
        report_start_ms = 10 * H4_MS

        fill_warmup_flags: list[bool] = []

        class _FillTracker(Strategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                if state.bar_index == 2:
                    return Signal(orders=[Order(Side.BUY, QTY)], reason="w_buy")
                if state.bar_index == 4:
                    return Signal(orders=[Order(Side.SELL, QTY)], reason="w_sell")
                if state.bar_index == 12:
                    return Signal(orders=[Order(Side.BUY, QTY)], reason="r_buy")
                return None

            def on_after_fill(self, state: MarketState, fill: Fill) -> None:
                fill_warmup_flags.append(state.is_warmup)

        feed = _FakeFeed(bars, report_start_ms=report_start_ms)
        engine = BacktestEngine(
            feed, _FillTracker(), ZERO_COST, initial_cash=CASH,
            warmup_mode="allow_trade",
        )
        engine.run()

        # 3 fills: w_buy (bar 3), w_sell (bar 5), r_buy (bar 13)
        assert len(fill_warmup_flags) == 3, (
            f"Expected 3 fills, got {len(fill_warmup_flags)}")
        # First two fills are during warmup
        assert fill_warmup_flags[0] is True, (
            "w_buy fill should have is_warmup=True")
        assert fill_warmup_flags[1] is True, (
            "w_sell fill should have is_warmup=True")
        # Third fill is during reporting
        assert fill_warmup_flags[2] is False, (
            "r_buy fill should have is_warmup=False")
