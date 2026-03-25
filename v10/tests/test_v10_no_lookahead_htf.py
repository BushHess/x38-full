"""Lookahead sanity tests for V10 (V8ApexStrategy) HTF indicator usage.

These tests verify that V10's D1-based features (_d1_regime, _d1_vol_ann)
ONLY access the LAST COMPLETED D1 bar, never the current in-progress D1 bar.

Tests:
  1. Synthetic: V10 regime sees lagged D1 data (not today's)
  2. Synthetic: V10 D1 indicator arrays indexed by d1_index from engine
  3. Integration: Real data — d1.close_time < h4.close_time always holds
  4. Monotonicity: d1_index never decreases across bars
  5. Static code audit: No D1 access uses index > d1_index in v8_apex.py
  6. Boundary: last H4 of day N does NOT see day N's D1 regime
  7. Cross-check: V10 full backtest with/without D1 lag produces different results
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from v10.core.types import Bar, CostConfig, MarketState, Signal
from v10.core.engine import BacktestEngine
from v10.strategies.base import Strategy
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

H4_MS = 14_400_000   # 4 h in ms
D1_MS = 86_400_000   # 24 h in ms
ZERO_COST = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.0)


def _h4(day: int, slot: int, price: float = 50_000.0) -> Bar:
    """H4 bar: 6 slots per day (0-5). close_time = open + 4h - 1ms."""
    ot = day * D1_MS + slot * H4_MS
    return Bar(
        open_time=ot,
        open=price,
        high=price * 1.01,
        low=price * 0.99,
        close=price,
        volume=100.0,
        close_time=ot + H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


def _d1(day: int, price: float = 50_000.0) -> Bar:
    """D1 bar. close_time = (day+1)*D1_MS - 1 (end of calendar day)."""
    ot = day * D1_MS
    return Bar(
        open_time=ot,
        open=price * 0.99,
        high=price * 1.02,
        low=price * 0.98,
        close=price,
        volume=600.0,
        close_time=ot + D1_MS - 1,
        taker_buy_base_vol=300.0,
        interval="1d",
    )


class _FakeFeed:
    def __init__(self, h4_bars: list[Bar], d1_bars: list[Bar]):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars
        self.report_start_ms: int | None = None


# ---------------------------------------------------------------------------
# TEST 1: V10 regime sees LAGGED D1 data
# ---------------------------------------------------------------------------

class TestV10RegimeNoLookahead:
    """V10 regime (_d1_regime) is computed from D1 close/EMA50/EMA200.
    Verify it uses d1_index from engine (lagged) not current-day D1."""

    def test_regime_uses_lagged_d1(self) -> None:
        """Create synthetic data where D1 prices ramp.
        V10 regime must only see yesterday's D1, not today's."""
        WARMUP_DAYS = 250
        TOTAL_DAYS = 260

        d1_bars = []
        for d in range(TOTAL_DAYS):
            if d < WARMUP_DAYS:
                price = 50_000.0
            else:
                price = 50_000.0 + (d - WARMUP_DAYS) * 5_000.0
            d1_bars.append(_d1(d, price))

        h4_bars = []
        for d in range(WARMUP_DAYS, TOTAL_DAYS):
            for slot in range(6):
                px = 50_000.0 + (d - WARMUP_DAYS) * 5_000.0
                h4_bars.append(_h4(d, slot, px))

        d1_indices_seen: list[int] = []

        class _V10Spy(V8ApexStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices_seen.append(state.d1_index)
                return super().on_bar(state)

        v10 = _V10Spy(V8ApexConfig())

        feed = _FakeFeed(h4_bars, d1_bars)
        engine = BacktestEngine(feed, v10, ZERO_COST, dump_mtf_map=True)
        engine.run()

        # For each H4 bar on day D, d1_index should point to day D-1
        for i, (h4_ct, d1_ct) in enumerate(engine.mtf_map):
            if d1_ct is not None:
                assert d1_ct < h4_ct, (
                    f"LOOKAHEAD! Bar[{i}]: h4_close={h4_ct}, d1_close={d1_ct}. "
                    f"D1 close_time must be < H4 close_time."
                )
            d1_idx = d1_indices_seen[i]
            if d1_idx >= 0:
                used_d1 = d1_bars[d1_idx]
                assert used_d1.close_time < h4_bars[i].close_time, (
                    f"LOOKAHEAD! Bar[{i}]: V10 uses D1[{d1_idx}] with "
                    f"close={used_d1.close_time}, but H4 close={h4_bars[i].close_time}. "
                    f"V10 must only use D1 bars that closed BEFORE the H4 bar."
                )


# ---------------------------------------------------------------------------
# TEST 2: V10 D1 indicator array bounds
# ---------------------------------------------------------------------------

class TestV10IndicatorIndexing:
    """Verify V10's pre-computed D1 arrays (_d1_regime, _d1_vol_ann)
    are indexed by the same d1_index from engine, always within bounds."""

    def test_indicator_array_bounds(self) -> None:
        TOTAL_DAYS = 250
        d1_bars = [_d1(d, 50_000.0 + d * 100) for d in range(TOTAL_DAYS)]
        h4_bars = []
        for d in range(TOTAL_DAYS):
            for slot in range(6):
                h4_bars.append(_h4(d, slot, 50_000.0 + d * 100))

        d1_indices: list[int] = []

        class _IdxTracker(V8ApexStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices.append(state.d1_index)
                return super().on_bar(state)

        v10 = _IdxTracker(V8ApexConfig())

        feed = _FakeFeed(h4_bars, d1_bars)
        engine = BacktestEngine(feed, v10, ZERO_COST)
        engine.run()

        n_d1 = len(d1_bars)
        for i, d1i in enumerate(d1_indices):
            if d1i >= 0:
                assert d1i < n_d1, (
                    f"Bar[{i}]: d1_index={d1i} >= n_d1_bars={n_d1}")
                assert d1i < len(v10._d1_regime), (
                    f"Bar[{i}]: d1_index={d1i} >= len(_d1_regime)={len(v10._d1_regime)}")
                assert d1i < len(v10._d1_vol_ann), (
                    f"Bar[{i}]: d1_index={d1i} >= len(_d1_vol_ann)={len(v10._d1_vol_ann)}")


# ---------------------------------------------------------------------------
# TEST 3: Integration — real data timestamp alignment
# ---------------------------------------------------------------------------

class TestV10RealDataTimestampAlignment:
    """Run V10 on actual BTCUSDT data and verify every H4 bar uses
    a D1 bar whose close_time is strictly before the H4 bar's close_time."""

    @pytest.fixture(autouse=True)
    def _check_data_file(self):
        data_path = (Path(__file__).resolve().parents[1].parent
                     / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
        if not data_path.exists():
            pytest.skip(f"Data file not found: {data_path}")
        self.data_path = str(data_path)

    def test_d1_always_behind_h4_real_data(self) -> None:
        """For every H4 bar in the backtest, assert d1.close_time < h4.close_time."""
        from v10.core.data import DataFeed
        from v10.core.types import SCENARIOS

        v10 = V8ApexStrategy(V8ApexConfig())
        feed = DataFeed(self.data_path, start="2024-01-01", end="2025-01-01",
                        warmup_days=365)
        cost = SCENARIOS["harsh"]
        engine = BacktestEngine(feed=feed, strategy=v10, cost=cost,
                                initial_cash=10_000.0, dump_mtf_map=True)
        engine.run()

        violations = []
        for i, (h4_ct, d1_ct) in enumerate(engine.mtf_map):
            if d1_ct is not None and d1_ct >= h4_ct:
                violations.append((i, h4_ct, d1_ct))

        assert len(violations) == 0, (
            f"LOOKAHEAD DETECTED! {len(violations)} violations found.\n"
            f"First 5:\n" +
            "\n".join(
                f"  Bar[{i}]: h4_close={h4_ct} <= d1_close={d1_ct}"
                for i, h4_ct, d1_ct in violations[:5]
            )
        )

    def test_d1_index_tracks_correctly_real_data(self) -> None:
        """Verify d1_index at every bar and that the D1 bar's close_time
        is strictly before the H4 bar's close_time."""
        from v10.core.data import DataFeed
        from v10.core.types import SCENARIOS

        d1_indices: list[int] = []

        class _V10Tracker(V8ApexStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices.append(state.d1_index)
                return super().on_bar(state)

        v10 = _V10Tracker(V8ApexConfig())
        feed = DataFeed(self.data_path, start="2024-01-01", end="2025-01-01",
                        warmup_days=365)
        cost = SCENARIOS["harsh"]
        engine = BacktestEngine(feed=feed, strategy=v10, cost=cost,
                                initial_cash=10_000.0)
        engine.run()

        h4_bars = feed.h4_bars
        d1_bars = feed.d1_bars

        violations = []
        for i, d1i in enumerate(d1_indices):
            if d1i >= 0 and i < len(h4_bars):
                d1_bar = d1_bars[d1i]
                h4_bar = h4_bars[i]
                if d1_bar.close_time >= h4_bar.close_time:
                    violations.append((i, h4_bar.close_time, d1i, d1_bar.close_time))

        assert len(violations) == 0, (
            f"LOOKAHEAD! {len(violations)} bars use D1 that hasn't closed yet.\n"
            f"First 5:\n" +
            "\n".join(
                f"  H4[{i}] close={h4ct}, D1[{d1i}] close={d1ct}"
                for i, h4ct, d1i, d1ct in violations[:5]
            )
        )


# ---------------------------------------------------------------------------
# TEST 4: d1_index monotonicity
# ---------------------------------------------------------------------------

class TestV10D1IndexMonotonicity:
    """d1_index must be monotonically non-decreasing as H4 bars advance."""

    def test_d1_index_never_decreases(self) -> None:
        TOTAL_DAYS = 100
        d1_bars = [_d1(d, 50_000.0) for d in range(TOTAL_DAYS)]
        h4_bars = [_h4(d, s, 50_000.0) for d in range(TOTAL_DAYS) for s in range(6)]

        d1_indices: list[int] = []

        class _IdxTracker(V8ApexStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices.append(state.d1_index)
                return super().on_bar(state)

        v10 = _IdxTracker(V8ApexConfig())

        feed = _FakeFeed(h4_bars, d1_bars)
        engine = BacktestEngine(feed, v10, ZERO_COST)
        engine.run()

        for i in range(1, len(d1_indices)):
            assert d1_indices[i] >= d1_indices[i - 1], (
                f"d1_index DECREASED at bar {i}: "
                f"{d1_indices[i - 1]} -> {d1_indices[i]}")


# ---------------------------------------------------------------------------
# TEST 5: Static code audit — no D1 access beyond d1_index in v8_apex.py
# ---------------------------------------------------------------------------

class TestV10CodeAuditNoBeyondD1Index:
    """Verify V8ApexStrategy code never accesses D1 arrays with index > d1i.
    Also verify d1i always comes from state.d1_index."""

    def test_no_future_d1_access_pattern(self) -> None:
        src_path = Path(__file__).resolve().parents[1] / "strategies" / "v8_apex.py"
        source = src_path.read_text()

        lookahead_patterns = [
            r'd1i\s*\+\s*[1-9]',           # d1i + N (N>0)
            r'd1_index\s*\+\s*[1-9]',       # d1_index + N
            r'_d1_regime\[d1i\s*\+',         # _d1_regime[d1i + ...]
            r'_d1_vol_ann\[d1i\s*\+',        # _d1_vol_ann[d1i + ...]
        ]

        violations = []
        for pattern in lookahead_patterns:
            for m in re.finditer(pattern, source):
                line_num = source[:m.start()].count('\n') + 1
                line_text = source.split('\n')[line_num - 1].strip()
                if line_text.startswith('#'):
                    continue
                # Allow in on_init / _compute_regime (vectorized)
                preceding = source[:m.start()]
                last_def = preceding.rfind('\n    def ')
                if last_def >= 0:
                    func_line = source[last_def:last_def + 100].split('\n')[1].strip()
                    if 'on_init' in func_line or '_compute_regime' in func_line:
                        continue
                violations.append((line_num, line_text, pattern))

        assert len(violations) == 0, (
            f"Potential lookahead patterns found in v8_apex.py:\n" +
            "\n".join(
                f"  Line {ln}: '{txt}' (matched: {pat})"
                for ln, txt, pat in violations
            )
        )

    def test_d1i_comes_from_state(self) -> None:
        """Verify on_bar assigns d1i from state.d1_index."""
        src_path = Path(__file__).resolve().parents[1] / "strategies" / "v8_apex.py"
        source = src_path.read_text()

        on_bar_match = re.search(
            r'def on_bar\(self.*?\).*?:\n(.*?)(?=\n    def |\Z)',
            source, re.DOTALL)
        assert on_bar_match, "Could not find on_bar method"

        on_bar_body = on_bar_match.group(1)
        assert 'd1i = state.d1_index' in on_bar_body, (
            "on_bar must assign d1i from state.d1_index")

    def test_d1_arrays_exactly_two(self) -> None:
        """V8Apex should have exactly 2 D1 arrays: _d1_regime and _d1_vol_ann.
        If new D1 arrays are added, this test catches them for review."""
        src_path = Path(__file__).resolve().parents[1] / "strategies" / "v8_apex.py"
        source = src_path.read_text()

        # Find all self._d1_* array definitions in __init__
        d1_arrays = re.findall(r'self\.(_d1_\w+)\s*=', source)
        d1_unique = sorted(set(d1_arrays))

        expected = ['_d1_regime', '_d1_vol_ann']
        assert d1_unique == expected, (
            f"V8Apex D1 arrays changed! Expected {expected}, got {d1_unique}. "
            f"New D1 arrays must be reviewed for lookahead safety.")

    def test_all_d1_access_is_bounds_checked(self) -> None:
        """Every _d1_regime[d1i] and _d1_vol_ann[d1i] access outside on_init
        must be guarded by a bounds check: 0 <= d1i < len(...)."""
        src_path = Path(__file__).resolve().parents[1] / "strategies" / "v8_apex.py"
        source = src_path.read_text()

        # Find all _d1_regime[d1i] and _d1_vol_ann[d1i] accesses
        for arr_name in ['_d1_regime', '_d1_vol_ann']:
            for m in re.finditer(rf'self\.{arr_name}\[d1i\]', source):
                line_num = source[:m.start()].count('\n') + 1
                # Check surrounding context (±5 lines) for bounds guard
                # V8Apex uses inline conditional: `arr[d1i] if 0 <= d1i < len(arr) else ...`
                line_start = source.rfind('\n', 0, m.start()) + 1
                # Look at the statement block (up to 300 chars around the access)
                block_start = max(0, m.start() - 300)
                block_end = min(len(source), m.end() + 200)
                context = source[block_start:block_end]
                # Allow on_init (vectorized)
                preceding = source[:m.start()]
                last_def = preceding.rfind('\n    def ')
                if last_def >= 0:
                    func_line = source[last_def:last_def + 100].split('\n')[1].strip()
                    if 'on_init' in func_line or '_compute_regime' in func_line:
                        continue
                # Check for bounds guard anywhere in surrounding context
                has_guard = ('0 <= d1i' in context and 'len(' in context)
                assert has_guard, (
                    f"Line {line_num}: self.{arr_name}[d1i] lacks bounds check. "
                    f"Must have '0 <= d1i < len(...)' guard.")


# ---------------------------------------------------------------------------
# TEST 6: Boundary — last H4 of day N does NOT see day N's D1 regime
# ---------------------------------------------------------------------------

class TestV10BoundaryRegime:
    """Critical edge case: last H4 bar of day N shares close_time with D1 of day N.
    Strict '<' ensures V10 still uses day N-1's D1 regime, not day N's."""

    def test_last_h4_uses_previous_day_regime(self) -> None:
        # Construct 3 days where D1 prices change enough to flip regime
        # Day 0: price 50k (establish EMA baseline)
        # Day 1: price 50k (stable)
        # Day 2: price drops to 20k (regime should change on day 2 D1)
        # BUT: last H4 of day 2 must NOT see day 2's D1 regime
        WARMUP = 250  # enough for EMA200 warmup
        prices = [50_000.0] * WARMUP + [50_000.0, 50_000.0, 20_000.0]

        d1_bars = [_d1(d, prices[d]) for d in range(len(prices))]
        # Only test H4 bars on last 3 days
        h4_bars = []
        for d in range(WARMUP, len(prices)):
            for slot in range(6):
                h4_bars.append(_h4(d, slot, prices[d]))

        d1_indices_seen: list[int] = []
        d1_regimes_seen: list[object] = []

        class _RegimeSpy(V8ApexStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices_seen.append(state.d1_index)
                d1i = state.d1_index
                if 0 <= d1i < len(self._d1_regime):
                    d1_regimes_seen.append(self._d1_regime[d1i])
                else:
                    d1_regimes_seen.append(None)
                return super().on_bar(state)

        v10 = _RegimeSpy(V8ApexConfig())
        feed = _FakeFeed(h4_bars, d1_bars)
        engine = BacktestEngine(feed, v10, ZERO_COST, dump_mtf_map=True)
        engine.run()

        # All H4 bars on the last day (day WARMUP+2, slots 0-5 = bars 12-17)
        # must see d1_index pointing to day WARMUP+1 (not day WARMUP+2)
        last_day_start = 12  # 3rd day * 6 slots/day
        for i in range(last_day_start, min(last_day_start + 6, len(d1_indices_seen))):
            d1i = d1_indices_seen[i]
            if d1i >= 0:
                used_d1 = d1_bars[d1i]
                h4_bar = h4_bars[i]
                assert used_d1.close_time < h4_bar.close_time, (
                    f"LOOKAHEAD! Last-day bar[{i}]: V10 sees D1[{d1i}] "
                    f"(close={used_d1.close_time}) which is NOT < "
                    f"H4 close={h4_bar.close_time}")


# ---------------------------------------------------------------------------
# TEST 7: V10 results change when D1 lag is removed (proves D1 matters)
# ---------------------------------------------------------------------------

class TestV10D1LagMatters:
    """V10 uses D1 regime gating to block/allow trades.
    Prove this by running on real data with/without D1 bars."""

    @pytest.fixture(autouse=True)
    def _check_data_file(self):
        data_path = (Path(__file__).resolve().parents[1].parent
                     / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
        if not data_path.exists():
            pytest.skip(f"Data file not found: {data_path}")
        self.data_path = str(data_path)

    def test_removing_d1_changes_behavior(self) -> None:
        """Run V10 with normal D1 vs. forced RISK_OFF regime (d1_index=-1).
        If results differ, D1 is used and its alignment matters."""
        from v10.core.data import DataFeed
        from v10.core.types import SCENARIOS

        # Run 1: normal V10
        v10_normal = V8ApexStrategy(V8ApexConfig())
        feed1 = DataFeed(self.data_path, start="2024-01-01", end="2025-01-01",
                         warmup_days=365)
        engine1 = BacktestEngine(feed=feed1, strategy=v10_normal,
                                 cost=SCENARIOS["harsh"], initial_cash=10_000.0)
        result1 = engine1.run()

        # Run 2: V10 that forces regime=RISK_OFF by overriding d1_index
        class _NoD1V10(V8ApexStrategy):
            """Forces d1_index to -1, simulating no D1 data."""
            def on_bar(self, state: MarketState) -> Signal | None:
                # Monkey-patch d1_index to -1 so regime falls through to RISK_OFF
                import copy
                fake = copy.copy(state)
                fake.d1_index = -1
                return super().on_bar(fake)

        v10_nod1 = _NoD1V10(V8ApexConfig())
        feed2 = DataFeed(self.data_path, start="2024-01-01", end="2025-01-01",
                         warmup_days=365)
        engine2 = BacktestEngine(feed=feed2, strategy=v10_nod1,
                                 cost=SCENARIOS["harsh"], initial_cash=10_000.0)
        result2 = engine2.run()

        nav_normal = result1.equity[-1].nav_mid if result1.equity else 10_000
        nav_nod1 = result2.equity[-1].nav_mid if result2.equity else 10_000
        trades_normal = result1.summary.get("trades", 0)
        trades_nod1 = result2.summary.get("trades", 0)

        # Must differ: D1 regime gating materially affects behavior
        differs = (nav_normal != pytest.approx(nav_nod1, rel=1e-6) or
                   trades_normal != trades_nod1)
        assert differs, (
            f"V10 normal (NAV={nav_normal:.2f}, trades={trades_normal}) == "
            f"V10 no-D1 (NAV={nav_nod1:.2f}, trades={trades_nod1}). "
            f"D1 regime gating has no effect!")
