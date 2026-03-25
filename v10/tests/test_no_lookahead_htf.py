"""Lookahead sanity tests for V11 Hybrid strategy HTF indicator usage.

These tests verify that V11's D1-based features (cycle phase, RSI, EMA200, ADX)
ONLY access the LAST COMPLETED D1 bar, never the current in-progress D1 bar.

Tests:
  1. Synthetic: V11 cycle phase sees lagged D1 data (not today's)
  2. Synthetic: V11 indicator arrays are indexed by d1_index from engine
  3. Integration: Real data — for every H4 bar, assert d1.close_time < h4.close_time
  4. Integration: V11 on_bar receives d1_index strictly behind H4 bar
  5. Code audit: No D1 access uses index > d1_index

Tests 1-4 are automated. Test 5 is a static assertion on code patterns.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Ensure v10 is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from v10.core.types import Bar, CostConfig, MarketState, Signal
from v10.core.engine import BacktestEngine
from v10.strategies.base import Strategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy


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
# TEST 1: V11 cycle phase sees LAGGED D1 data
# ---------------------------------------------------------------------------

class TestV11CyclePhaseNoLookahead:
    """V11 cycle phase is computed from D1 close/high/low arrays.
    Verify it uses d1_index from engine (lagged) not current-day D1."""

    def test_cycle_phase_uses_lagged_d1(self) -> None:
        """Create synthetic data where D1 prices change drastically per day.
        V11 cycle phase must only see yesterday's D1, not today's.
        """
        # Need enough D1 bars for EMA200 warmup + cycle phase computation
        # Use 250 days with stable price, then price changes on last 5 days
        WARMUP_DAYS = 250
        TOTAL_DAYS = 260

        # Build D1 bars with stable price for warmup
        d1_bars = []
        for d in range(TOTAL_DAYS):
            if d < WARMUP_DAYS:
                price = 50_000.0
            else:
                # Ramp up prices to trigger different cycle phases
                price = 50_000.0 + (d - WARMUP_DAYS) * 5_000.0
            d1_bars.append(_d1(d, price))

        # Build H4 bars only for the last 5 days (after warmup)
        h4_bars = []
        for d in range(WARMUP_DAYS, TOTAL_DAYS):
            for slot in range(6):
                # H4 price matches D1 close of that day
                px = 50_000.0 + (d - WARMUP_DAYS) * 5_000.0
                h4_bars.append(_h4(d, slot, px))

        # Track what d1_index V11 sees at each bar
        d1_indices_seen: list[int] = []

        class _V11Spy(V11HybridStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices_seen.append(state.d1_index)
                return super().on_bar(state)

        cfg = V11HybridConfig()
        cfg.enable_cycle_phase = True
        v11 = _V11Spy(cfg)

        feed = _FakeFeed(h4_bars, d1_bars)
        engine = BacktestEngine(feed, v11, ZERO_COST, dump_mtf_map=True)
        engine.run()

        # Verify: for each H4 bar on day D, d1_index should point to day D-1
        for i, (h4_ct, d1_ct) in enumerate(engine.mtf_map):
            if d1_ct is not None:
                # d1_ct must be STRICTLY BEFORE h4_ct
                assert d1_ct < h4_ct, (
                    f"LOOKAHEAD! Bar[{i}]: h4_close={h4_ct}, d1_close={d1_ct}. "
                    f"D1 close_time must be < H4 close_time."
                )
            d1_idx = d1_indices_seen[i]
            if d1_idx >= 0:
                used_d1 = d1_bars[d1_idx]
                assert used_d1.close_time < h4_bars[i].close_time, (
                    f"LOOKAHEAD! Bar[{i}]: V11 uses D1[{d1_idx}] with "
                    f"close={used_d1.close_time}, but H4 close={h4_bars[i].close_time}. "
                    f"V11 must only use D1 bars that closed BEFORE the H4 bar."
                )


# ---------------------------------------------------------------------------
# TEST 2: V11 indicator array indexing consistency
# ---------------------------------------------------------------------------

class TestV11IndicatorIndexing:
    """Verify V11's pre-computed D1 arrays (_d1_rsi, _d1_ema200,
    _d1_cycle_phase) are indexed by the same d1_index from engine."""

    def test_indicator_array_bounds(self) -> None:
        """d1_index from engine must always be within indicator array bounds."""
        TOTAL_DAYS = 250
        d1_bars = [_d1(d, 50_000.0 + d * 100) for d in range(TOTAL_DAYS)]
        h4_bars = []
        for d in range(TOTAL_DAYS):
            for slot in range(6):
                h4_bars.append(_h4(d, slot, 50_000.0 + d * 100))

        d1_indices: list[int] = []

        class _IdxTracker(V11HybridStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices.append(state.d1_index)
                return super().on_bar(state)

        cfg = V11HybridConfig()
        cfg.enable_cycle_phase = True
        cfg.enable_mr_defensive = True
        cfg.enable_adx_gating = True
        v11 = _IdxTracker(cfg)

        feed = _FakeFeed(h4_bars, d1_bars)
        engine = BacktestEngine(feed, v11, ZERO_COST)
        engine.run()

        # Check all d1_indices are within bounds of indicator arrays
        n_d1 = len(d1_bars)
        for i, d1i in enumerate(d1_indices):
            if d1i >= 0:
                assert d1i < n_d1, (
                    f"Bar[{i}]: d1_index={d1i} >= n_d1_bars={n_d1}")
                assert d1i < len(v11._d1_rsi), (
                    f"Bar[{i}]: d1_index={d1i} >= len(_d1_rsi)={len(v11._d1_rsi)}")
                assert d1i < len(v11._d1_ema200), (
                    f"Bar[{i}]: d1_index={d1i} >= len(_d1_ema200)={len(v11._d1_ema200)}")
                assert d1i < len(v11._d1_cycle_phase), (
                    f"Bar[{i}]: d1_index={d1i} >= len(_d1_cycle_phase)={len(v11._d1_cycle_phase)}")
                assert d1i < len(v11._d1_adx), (
                    f"Bar[{i}]: d1_index={d1i} >= len(_d1_adx)={len(v11._d1_adx)}")


# ---------------------------------------------------------------------------
# TEST 3: Integration — real data timestamp alignment
# ---------------------------------------------------------------------------

class TestRealDataTimestampAlignment:
    """Run V11 on actual BTCUSDT data and verify every signal uses
    a D1 bar whose close_time is strictly before the H4 bar's close_time."""

    @pytest.fixture(autouse=True)
    def _check_data_file(self):
        data_path = Path(__file__).resolve().parents[1].parent / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip(f"Data file not found: {data_path}")
        self.data_path = str(data_path)

    def test_d1_always_behind_h4_real_data(self) -> None:
        """For every H4 bar in the backtest, assert d1.close_time < h4.close_time."""
        from v10.core.data import DataFeed
        from v10.core.types import SCENARIOS

        cfg = V11HybridConfig()
        cfg.enable_cycle_phase = True
        cfg.cycle_late_aggression = 0.95
        cfg.cycle_late_trail_mult = 2.8
        cfg.cycle_late_max_exposure = 0.90
        v11 = V11HybridStrategy(cfg)

        feed = DataFeed(self.data_path, start="2024-01-01", end="2025-01-01",
                        warmup_days=365)
        cost = SCENARIOS["harsh"]
        engine = BacktestEngine(feed=feed, strategy=v11, cost=cost,
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
                f"  Bar[{i}]: h4_close={h4_ct} <= d1_close={d1_ct} "
                f"(d1 should be STRICTLY before h4)"
                for i, h4_ct, d1_ct in violations[:5]
            )
        )

    def test_d1_index_never_exceeds_current_day(self) -> None:
        """Track d1_index at every bar and verify the D1 bar's open_time
        is at least 1 day before the H4 bar's close_time."""
        from v10.core.data import DataFeed
        from v10.core.types import SCENARIOS

        d1_indices: list[int] = []

        class _V11Tracker(V11HybridStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices.append(state.d1_index)
                return super().on_bar(state)

        cfg = V11HybridConfig()
        cfg.enable_cycle_phase = True
        v11 = _V11Tracker(cfg)

        feed = DataFeed(self.data_path, start="2024-01-01", end="2025-01-01",
                        warmup_days=365)
        cost = SCENARIOS["harsh"]
        engine = BacktestEngine(feed=feed, strategy=v11, cost=cost,
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
# TEST 4: V11 on_bar d1_index monotonicity
# ---------------------------------------------------------------------------

class TestD1IndexMonotonicity:
    """d1_index must be monotonically non-decreasing as H4 bars advance."""

    def test_d1_index_never_decreases(self) -> None:
        TOTAL_DAYS = 100
        d1_bars = [_d1(d, 50_000.0) for d in range(TOTAL_DAYS)]
        h4_bars = [_h4(d, s, 50_000.0) for d in range(TOTAL_DAYS) for s in range(6)]

        d1_indices: list[int] = []

        class _IdxTracker(V11HybridStrategy):
            def on_bar(self, state: MarketState) -> Signal | None:
                d1_indices.append(state.d1_index)
                return super().on_bar(state)

        cfg = V11HybridConfig()
        cfg.enable_cycle_phase = True
        v11 = _IdxTracker(cfg)

        feed = _FakeFeed(h4_bars, d1_bars)
        engine = BacktestEngine(feed, v11, ZERO_COST)
        engine.run()

        for i in range(1, len(d1_indices)):
            assert d1_indices[i] >= d1_indices[i - 1], (
                f"d1_index DECREASED at bar {i}: "
                f"{d1_indices[i - 1]} -> {d1_indices[i]}")


# ---------------------------------------------------------------------------
# TEST 5: Static code audit — no D1 access beyond d1_index
# ---------------------------------------------------------------------------

class TestCodeAuditNoBeyondD1Index:
    """Verify V11 code never accesses D1 arrays with index > d1i.

    This is a static check: read v11_hybrid.py source and ensure no
    d1_index+1, d1_index+N, or future-looking index patterns exist
    in the on_bar / _check_entry / _check_exit methods.
    """

    def test_no_future_d1_access_pattern(self) -> None:
        import re

        src_path = Path(__file__).resolve().parents[1] / "strategies" / "v11_hybrid.py"
        source = src_path.read_text()

        # Patterns that would indicate lookahead:
        # d1i + 1, d1i+1, d1_index + 1, etc. when used as array index
        lookahead_patterns = [
            r'd1i\s*\+\s*[1-9]',           # d1i + N (N>0)
            r'd1_index\s*\+\s*[1-9]',       # d1_index + N
            r'_d1_rsi\[d1i\s*\+',           # _d1_rsi[d1i + ...]
            r'_d1_ema200\[d1i\s*\+',        # _d1_ema200[d1i + ...]
            r'_d1_cycle_phase\[d1i\s*\+',   # _d1_cycle_phase[d1i + ...]
            r'_d1_adx\[d1i\s*\+',           # _d1_adx[d1i + ...]
            r'_d1_regime\[d1i\s*\+',        # _d1_regime[d1i + ...]
            r'_d1_vol_ann\[d1i\s*\+',       # _d1_vol_ann[d1i + ...]
        ]

        violations = []
        for pattern in lookahead_patterns:
            matches = list(re.finditer(pattern, source))
            for m in matches:
                # Find line number
                line_num = source[:m.start()].count('\n') + 1
                line_text = source.split('\n')[line_num - 1].strip()
                # Exclude comments and on_init (where vectorized computation is OK)
                if line_text.startswith('#'):
                    continue
                # Check if inside on_init (where full-array access is expected)
                # Find the function context
                preceding = source[:m.start()]
                last_def = preceding.rfind('\n    def ')
                if last_def >= 0:
                    func_line = source[last_def:last_def + 100].split('\n')[1].strip()
                    if 'on_init' in func_line or '_compute_cycle' in func_line:
                        continue  # Vectorized computation in on_init is fine
                violations.append((line_num, line_text, pattern))

        assert len(violations) == 0, (
            f"Potential lookahead patterns found in v11_hybrid.py:\n" +
            "\n".join(
                f"  Line {ln}: '{txt}' (matched: {pat})"
                for ln, txt, pat in violations
            )
        )

    def test_all_d1_accesses_use_d1i_from_state(self) -> None:
        """Verify that on_bar and its callees use d1i = state.d1_index,
        not any independently computed index."""
        import re

        src_path = Path(__file__).resolve().parents[1] / "strategies" / "v11_hybrid.py"
        source = src_path.read_text()

        # Find on_bar method — it should assign d1i = state.d1_index
        on_bar_match = re.search(r'def on_bar\(self.*?\).*?:\n(.*?)(?=\n    def |\Z)',
                                 source, re.DOTALL)
        assert on_bar_match, "Could not find on_bar method"

        on_bar_body = on_bar_match.group(1)
        # Must contain: d1i = state.d1_index
        assert 'd1i = state.d1_index' in on_bar_body, (
            "on_bar must assign d1i from state.d1_index")

        # Check that d1i is passed to helper methods, not recomputed
        # _assess_mr_state, _get_adx should receive d1i as parameter
        for method in ['_assess_mr_state', '_get_adx']:
            method_match = re.search(
                rf'def {method}\(self,\s*d1i:\s*int',
                source
            )
            assert method_match, (
                f"{method} must accept d1i: int as parameter (from state.d1_index)")
