"""Tests for strict MTF (multi-timeframe) alignment.

Rule: at H4 bar with close_time t, the D1 bar used must satisfy
    d1.close_time < t   (STRICTLY earlier — no same-candle lookahead).

Synthetic data layout per day:
    H4 slots 0-5 → close at  4h, 8h, 12h, 16h, 20h, 24h  (minus 1 ms)
    D1 slot   0  → close at 24h  (minus 1 ms, same as last H4)

Key invariant: the last H4 of day N and the D1 of day N share the
same close_time.  Strict '<' ensures that H4 bar does NOT see day N's
D1 — only day N-1's.
"""

from __future__ import annotations

import pytest

from v10.core.types import Bar, CostConfig, MarketState, Signal
from v10.core.engine import BacktestEngine
from v10.strategies.base import Strategy


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

H4_MS = 14_400_000   # 4 h
D1_MS = 86_400_000   # 24 h
ZERO_COST = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.0)


def _h4(day: int, slot: int, price: float = 50_000.0) -> Bar:
    """H4 bar: 6 slots per day (0-5).  close_time = open + 4h - 1ms."""
    ot = day * D1_MS + slot * H4_MS
    return Bar(
        open_time=ot,
        open=price,
        high=price * 1.001,
        low=price * 0.999,
        close=price,
        volume=100.0,
        close_time=ot + H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


def _d1(day: int, price: float = 50_000.0) -> Bar:
    """D1 bar.  close_time = (day+1)*D1_MS - 1  (end of that calendar day)."""
    ot = day * D1_MS
    return Bar(
        open_time=ot,
        open=price,
        high=price * 1.001,
        low=price * 0.999,
        close=price,
        volume=600.0,
        close_time=ot + D1_MS - 1,
        taker_buy_base_vol=300.0,
        interval="1d",
    )


class _FakeFeed:
    """Minimal DataFeed substitute."""

    def __init__(self, h4_bars: list[Bar], d1_bars: list[Bar]):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars
        self.report_start_ms: int | None = None


class _D1Recorder(Strategy):
    """Records d1_index seen at each bar and the D1 close price used."""

    def __init__(self) -> None:
        self.records: list[tuple[int, int, int | None, float | None]] = []
        # Each entry: (h4_bar_index, h4_close_time, d1_close_time, d1_close_price)

    def on_bar(self, state: MarketState) -> Signal | None:
        d1_ct: int | None = None
        d1_px: float | None = None
        if state.d1_index >= 0:
            d1_bar = state.d1_bars[state.d1_index]
            d1_ct = d1_bar.close_time
            d1_px = d1_bar.close
        self.records.append((state.bar_index, state.bar.close_time, d1_ct, d1_px))
        return None


# ---------------------------------------------------------------------------
# TEST 1: No D1 available on first day
# ---------------------------------------------------------------------------

class TestNoD1BeforeFirstClose:
    """On day 0, no D1 bar has closed yet → d1_index must be -1."""

    def test_day0_all_slots(self) -> None:
        h4 = [_h4(0, s) for s in range(6)]
        d1 = [_d1(0)]

        recorder = _D1Recorder()
        feed = _FakeFeed(h4, d1)
        engine = BacktestEngine(feed, recorder, ZERO_COST)
        engine.run()

        for idx, h4_ct, d1_ct, _ in recorder.records:
            assert d1_ct is None, (
                f"H4 bar[{idx}] (close={h4_ct}) sees D1 close={d1_ct}, "
                f"but NO D1 should be available on day 0. "
                f"d1[0].close_time={d1[0].close_time} is NOT < {h4_ct}."
            )

    def test_d1_index_is_minus_one(self) -> None:
        """Verify d1_index=-1 explicitly via mtf_map (None for all day-0 bars)."""
        h4 = [_h4(0, s) for s in range(6)]
        d1 = [_d1(0)]

        feed = _FakeFeed(h4, d1)
        engine = BacktestEngine(feed, _D1Recorder(), ZERO_COST, dump_mtf_map=True)
        engine.run()

        for h4_ct, d1_ct in engine.mtf_map:
            assert d1_ct is None, (
                f"mtf_map: H4 close={h4_ct} -> D1 close={d1_ct}. "
                f"Expected None (no D1 available yet)."
            )


# ---------------------------------------------------------------------------
# TEST 2: Day boundary — last H4 of day N must NOT see D1 of day N
# ---------------------------------------------------------------------------

class TestDayBoundaryNoLookahead:
    """Critical: last H4 bar of day N has close_time == D1 bar of day N.
    Strict '<' means it must still use D1 of day N-1."""

    def test_last_h4_uses_previous_day_d1(self) -> None:
        # 3 days: day 0, 1, 2
        D1_PRICES = [40_000.0, 50_000.0, 60_000.0]
        h4 = [_h4(d, s) for d in range(3) for s in range(6)]  # 18 bars
        d1 = [_d1(d, D1_PRICES[d]) for d in range(3)]

        recorder = _D1Recorder()
        feed = _FakeFeed(h4, d1)
        engine = BacktestEngine(feed, recorder, ZERO_COST)
        engine.run()

        # day 0 (bars 0-5): no D1 available
        for idx in range(6):
            _, h4_ct, d1_ct, d1_px = recorder.records[idx]
            assert d1_ct is None, (
                f"Day 0 bar[{idx}]: expected no D1, got d1_close={d1_ct}")

        # day 1 (bars 6-11): must use D1 of day 0 (price=40k)
        for idx in range(6, 12):
            _, h4_ct, d1_ct, d1_px = recorder.records[idx]
            assert d1_ct == d1[0].close_time, (
                f"Day 1 bar[{idx}]: expected D1 day 0 (close={d1[0].close_time}), "
                f"got d1_close={d1_ct}")
            assert d1_px == pytest.approx(40_000.0), (
                f"Day 1 bar[{idx}]: expected D1 price 40000, got {d1_px}")

        # day 2 (bars 12-17): must use D1 of day 1 (price=50k)
        for idx in range(12, 18):
            _, h4_ct, d1_ct, d1_px = recorder.records[idx]
            assert d1_ct == d1[1].close_time, (
                f"Day 2 bar[{idx}]: expected D1 day 1 (close={d1[1].close_time}), "
                f"got d1_close={d1_ct}")
            assert d1_px == pytest.approx(50_000.0), (
                f"Day 2 bar[{idx}]: expected D1 price 50000, got {d1_px}")

    def test_boundary_exact_timestamps(self) -> None:
        """Verify the exact timestamp comparison at the boundary.
        Last H4 of day 0: close_time = 6*H4_MS - 1 = D1_MS - 1 = d1[0].close_time.
        Strict '<' means d1[0] is NOT visible here.
        First H4 of day 1: close_time = D1_MS + H4_MS - 1 > d1[0].close_time.
        d1[0] IS visible.
        """
        h4 = [_h4(0, 5), _h4(1, 0)]   # last bar of day 0, first bar of day 1
        d1 = [_d1(0, 99_999.0)]

        recorder = _D1Recorder()
        feed = _FakeFeed(h4, d1)
        engine = BacktestEngine(feed, recorder, ZERO_COST)
        engine.run()

        # bar[0]: close_time = 6*H4_MS - 1 = D1_MS - 1 = d1[0].close_time
        _, h4_ct_0, d1_ct_0, _ = recorder.records[0]
        assert h4_ct_0 == d1[0].close_time, (
            f"Sanity: H4 close={h4_ct_0} should equal D1 close={d1[0].close_time}")
        assert d1_ct_0 is None, (
            f"LOOKAHEAD BUG: last H4 of day 0 (close={h4_ct_0}) sees "
            f"D1 day 0 (close={d1[0].close_time}). "
            f"Strict '<' should prevent this.")

        # bar[1]: close_time = D1_MS + H4_MS - 1 > d1[0].close_time
        _, h4_ct_1, d1_ct_1, d1_px_1 = recorder.records[1]
        assert d1_ct_1 == d1[0].close_time, (
            f"First H4 of day 1 (close={h4_ct_1}) should see D1 day 0 "
            f"(close={d1[0].close_time}), got d1_close={d1_ct_1}")
        assert d1_px_1 == pytest.approx(99_999.0)


# ---------------------------------------------------------------------------
# TEST 3: Full d1_index mapping across multiple days
# ---------------------------------------------------------------------------

class TestD1IndexMapping:
    """Verify the exact d1_index value at each H4 bar across 4 days."""

    def test_expected_d1_index_sequence(self) -> None:
        DAYS = 4
        h4 = [_h4(d, s) for d in range(DAYS) for s in range(6)]  # 24 bars
        d1 = [_d1(d) for d in range(DAYS)]

        recorder = _D1Recorder()
        feed = _FakeFeed(h4, d1)
        engine = BacktestEngine(feed, recorder, ZERO_COST, dump_mtf_map=True)
        engine.run()

        # Expected d1_index per bar:
        # day 0 (6 bars): -1 (no D1 yet)
        # day 1 (6 bars): 0  (D1 day 0 available)
        # day 2 (6 bars): 1  (D1 day 1 available)
        # day 3 (6 bars): 2  (D1 day 2 available)
        expected = [-1] * 6 + [0] * 6 + [1] * 6 + [2] * 6

        actual = []
        for _, _, d1_ct, _ in recorder.records:
            if d1_ct is None:
                actual.append(-1)
            else:
                # Find which d1 index this close_time corresponds to
                idx = next(i for i, b in enumerate(d1) if b.close_time == d1_ct)
                actual.append(idx)

        assert actual == expected, (
            f"D1 index mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            f"First diff at bar {next(i for i, (a, e) in enumerate(zip(actual, expected)) if a != e)}"
        )


# ---------------------------------------------------------------------------
# TEST 4: mtf_map output consistency
# ---------------------------------------------------------------------------

class TestMtfMapOutput:
    """Verify engine.mtf_map matches what the strategy observes."""

    def test_mtf_map_matches_strategy_view(self) -> None:
        DAYS = 3
        h4 = [_h4(d, s) for d in range(DAYS) for s in range(6)]
        d1 = [_d1(d) for d in range(DAYS)]

        recorder = _D1Recorder()
        feed = _FakeFeed(h4, d1)
        engine = BacktestEngine(feed, recorder, ZERO_COST, dump_mtf_map=True)
        engine.run()

        assert len(engine.mtf_map) == len(recorder.records), (
            f"mtf_map length {len(engine.mtf_map)} != "
            f"strategy records {len(recorder.records)}")

        for i, ((map_h4, map_d1), (_, rec_h4, rec_d1, _)) in enumerate(
            zip(engine.mtf_map, recorder.records)
        ):
            assert map_h4 == rec_h4, (
                f"Bar[{i}]: mtf_map h4_close={map_h4} != strategy h4_close={rec_h4}")
            assert map_d1 == rec_d1, (
                f"Bar[{i}]: mtf_map d1_close={map_d1} != strategy d1_close={rec_d1}")

    def test_mtf_map_disabled_by_default(self) -> None:
        h4 = [_h4(0, s) for s in range(6)]
        feed = _FakeFeed(h4, [])

        class _Null(Strategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                return None

        engine = BacktestEngine(feed, _Null(), ZERO_COST)
        engine.run()
        assert engine.mtf_map == [], "mtf_map should be empty when dump_mtf_map=False"


# ---------------------------------------------------------------------------
# TEST 5: No D1 bars at all — graceful handling
# ---------------------------------------------------------------------------

class TestNoD1Bars:
    """Engine must work without D1 bars (d1_index stays -1 throughout)."""

    def test_no_d1_bars(self) -> None:
        h4 = [_h4(0, s) for s in range(6)]

        recorder = _D1Recorder()
        feed = _FakeFeed(h4, [])
        engine = BacktestEngine(feed, recorder, ZERO_COST, dump_mtf_map=True)
        engine.run()

        for idx, h4_ct, d1_ct, _ in recorder.records:
            assert d1_ct is None, (
                f"No D1 bars loaded, but bar[{idx}] sees d1_close={d1_ct}")

        for h4_ct, d1_ct in engine.mtf_map:
            assert d1_ct is None


# ---------------------------------------------------------------------------
# TEST 6: Lookahead-sensitive strategy — proves D1 data is lagged
# ---------------------------------------------------------------------------

class TestLookaheadSensitiveStrategy:
    """Use D1 bars with distinct prices per day.  A strategy reading
    d1_bars[d1_index].close must see yesterday's price, never today's."""

    def test_strategy_sees_lagged_d1_close(self) -> None:
        D1_PRICES = {0: 10_000.0, 1: 20_000.0, 2: 30_000.0, 3: 40_000.0}

        h4 = [_h4(d, s) for d in range(4) for s in range(6)]
        d1 = [_d1(d, D1_PRICES[d]) for d in range(4)]

        d1_prices_seen: list[float | None] = []

        class _PriceReader(Strategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                if state.d1_index >= 0:
                    d1_prices_seen.append(state.d1_bars[state.d1_index].close)
                else:
                    d1_prices_seen.append(None)
                return None

        feed = _FakeFeed(h4, d1)
        engine = BacktestEngine(feed, _PriceReader(), ZERO_COST)
        engine.run()

        # day 0: 6 × None
        for i in range(6):
            assert d1_prices_seen[i] is None, (
                f"Day 0 bar[{i}]: expected None, got {d1_prices_seen[i]}")

        # day 1: 6 × 10_000 (day 0's D1, NOT day 1's 20_000)
        for i in range(6, 12):
            assert d1_prices_seen[i] == pytest.approx(10_000.0), (
                f"Day 1 bar[{i}]: expected 10000 (D1 day 0), "
                f"got {d1_prices_seen[i]}. "
                f"If 20000 → LOOKAHEAD: seeing today's D1!")

        # day 2: 6 × 20_000 (day 1's D1, NOT day 2's 30_000)
        for i in range(12, 18):
            assert d1_prices_seen[i] == pytest.approx(20_000.0), (
                f"Day 2 bar[{i}]: expected 20000 (D1 day 1), "
                f"got {d1_prices_seen[i]}. "
                f"If 30000 → LOOKAHEAD: seeing today's D1!")

        # day 3: 6 × 30_000 (day 2's D1, NOT day 3's 40_000)
        for i in range(18, 24):
            assert d1_prices_seen[i] == pytest.approx(30_000.0), (
                f"Day 3 bar[{i}]: expected 30000 (D1 day 2), "
                f"got {d1_prices_seen[i]}. "
                f"If 40000 → LOOKAHEAD: seeing today's D1!")
