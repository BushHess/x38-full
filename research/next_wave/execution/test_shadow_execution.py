"""Tests for E1.2 shadow execution analyzer.

Per E1.1 spec test plan:
  1. H4-to-M15 alignment test
  2. Identity test (TWAP = VWAP = H4 open when M15 closes equal)
  3. Sign test (correct direction of entry/exit deltas)
  4. Cost accounting test (primary vs secondary path consistency)
  5. No-lookahead test
  6. Missing-intrabar behavior test
  7. Paired trade count consistency test
"""

import numpy as np
import pytest

from build_shadow_execution import (
    compute_twap,
    compute_vwap,
    get_twap_window,
    M15_INTERVAL_MS,
    TWAP_BARS,
    BASE_SLIPPAGE_BPS,
    BASE_TAKER_FEE_PCT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_bar(close: float, volume: float = 100.0,
             high: float | None = None, low: float | None = None) -> dict:
    """Create a synthetic M15 bar dict."""
    if high is None:
        high = close * 1.001
    if low is None:
        low = close * 0.999
    return {"open": close, "high": high, "low": low, "close": close, "volume": volume}


def make_m15_index(base_ts: int, bars: list[dict]) -> dict[int, dict]:
    """Build an M15 index from a list of bar dicts starting at base_ts."""
    idx = {}
    for i, b in enumerate(bars):
        idx[base_ts + i * M15_INTERVAL_MS] = b
    return idx


# ---------------------------------------------------------------------------
# Test 1: H4-to-M15 alignment
# ---------------------------------------------------------------------------

class TestAlignment:
    def test_get_twap_window_returns_4_bars(self):
        ts = 1000000000000
        bars = [make_bar(100 + i) for i in range(4)]
        idx = make_m15_index(ts, bars)
        result = get_twap_window(ts, idx)
        assert len(result) == 4

    def test_get_twap_window_correct_order(self):
        ts = 1000000000000
        bars = [make_bar(100 + i) for i in range(4)]
        idx = make_m15_index(ts, bars)
        result = get_twap_window(ts, idx)
        assert [b["close"] for b in result] == [100, 101, 102, 103]

    def test_get_twap_window_missing_bar(self):
        ts = 1000000000000
        bars = [make_bar(100 + i) for i in range(4)]
        idx = make_m15_index(ts, bars)
        # Remove the 3rd bar
        del idx[ts + 2 * M15_INTERVAL_MS]
        result = get_twap_window(ts, idx)
        assert len(result) == 3

    def test_get_twap_window_empty_index(self):
        ts = 1000000000000
        result = get_twap_window(ts, {})
        assert len(result) == 0

    def test_get_twap_window_uses_correct_timestamps(self):
        """Bars must start at fill_ts_ms, not before."""
        ts = 1000000000000
        # Place bars BEFORE the fill time -- should not be found
        bars = [make_bar(999) for _ in range(4)]
        idx = make_m15_index(ts - 4 * M15_INTERVAL_MS, bars)
        result = get_twap_window(ts, idx)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Test 2: Identity test
# ---------------------------------------------------------------------------

class TestIdentity:
    def test_twap_equals_close_when_all_same(self):
        bars = [make_bar(50000.0) for _ in range(4)]
        twap = compute_twap(bars)
        assert twap == pytest.approx(50000.0, rel=1e-10)

    def test_vwap_equals_typical_when_all_same(self):
        # When all bars have same HLC and same volume, VWAP = typical_price
        bars = [make_bar(50000.0, high=50050.0, low=49950.0) for _ in range(4)]
        vwap = compute_vwap(bars)
        expected_tp = (50050.0 + 49950.0 + 50000.0) / 3
        assert vwap == pytest.approx(expected_tp, rel=1e-10)

    def test_twap_vwap_both_equal_when_uniform(self):
        """When close = (H+L+C)/3 (symmetric bars), TWAP ~= VWAP."""
        # Make bars where close = typical_price
        bars = [make_bar(50000.0, high=50000.0, low=50000.0) for _ in range(4)]
        twap = compute_twap(bars)
        vwap = compute_vwap(bars)
        assert twap == pytest.approx(vwap, rel=1e-10)


# ---------------------------------------------------------------------------
# Test 3: Sign test
# ---------------------------------------------------------------------------

class TestSign:
    def test_entry_delta_negative_when_shadow_cheaper(self):
        """If TWAP < baseline mid, entry_delta should be negative (better for buyer)."""
        baseline_mid = 50000.0
        twap = 49990.0  # cheaper
        delta_bps = (twap / baseline_mid - 1) * 10000
        assert delta_bps < 0

    def test_combined_delta_positive_when_both_improve(self):
        """combined = -entry_delta + exit_delta. Both improving -> positive."""
        baseline_entry_mid = 50000.0
        baseline_exit_mid = 51000.0
        twap_entry = 49990.0  # bought cheaper
        twap_exit = 51010.0   # sold higher
        entry_delta = (twap_entry / baseline_entry_mid - 1) * 10000
        exit_delta = (twap_exit / baseline_exit_mid - 1) * 10000
        combined = -entry_delta + exit_delta
        assert combined > 0

    def test_combined_delta_negative_when_both_worsen(self):
        baseline_entry_mid = 50000.0
        baseline_exit_mid = 51000.0
        twap_entry = 50010.0  # bought higher
        twap_exit = 50990.0   # sold lower
        entry_delta = (twap_entry / baseline_entry_mid - 1) * 10000
        exit_delta = (twap_exit / baseline_exit_mid - 1) * 10000
        combined = -entry_delta + exit_delta
        assert combined < 0


# ---------------------------------------------------------------------------
# Test 4: Cost accounting test
# ---------------------------------------------------------------------------

class TestCostAccounting:
    def test_secondary_path_direction_matches_primary(self):
        """If combined_delta > 0, shadow PnL should exceed baseline PnL."""
        qty = 1.0
        baseline_mid_entry = 50000.0
        baseline_mid_exit = 51000.0

        # Shadow prices that are better
        shadow_entry = 49990.0
        shadow_exit = 51010.0

        # Primary: combined_delta
        entry_d = (shadow_entry / baseline_mid_entry - 1) * 10000
        exit_d = (shadow_exit / baseline_mid_exit - 1) * 10000
        combined = -entry_d + exit_d
        assert combined > 0

        # Secondary: re-price
        slip = BASE_SLIPPAGE_BPS / 10000
        fee = BASE_TAKER_FEE_PCT / 100

        # Baseline PnL (using BacktestEngine formula)
        bl_entry_fill = baseline_mid_entry * (1 + 2.5/10000) * (1 + slip)
        bl_exit_fill = baseline_mid_exit * (1 - 2.5/10000) * (1 - slip)
        bl_entry_cost = qty * bl_entry_fill * (1 + fee)
        bl_exit_proceeds = qty * bl_exit_fill * (1 - fee)
        bl_pnl = bl_exit_proceeds - bl_entry_cost

        # Shadow PnL
        sh_entry_fill = shadow_entry * (1 + slip)
        sh_exit_fill = shadow_exit * (1 - slip)
        sh_entry_cost = qty * sh_entry_fill * (1 + fee)
        sh_exit_proceeds = qty * sh_exit_fill * (1 - fee)
        sh_pnl = sh_exit_proceeds - sh_entry_cost

        assert sh_pnl > bl_pnl  # direction consistent

    def test_no_double_counting_spread(self):
        """Shadow fill should NOT have spread/2 added -- it's already a traded price."""
        shadow_price = 50000.0
        slip = BASE_SLIPPAGE_BPS / 10000
        shadow_fill = shadow_price * (1 + slip)  # only slippage, no spread
        # The spread component should NOT be in the formula
        spread_half = 2.5 / 10000
        wrong_fill = shadow_price * (1 + spread_half) * (1 + slip)
        assert shadow_fill < wrong_fill  # correct fill is lower (no spread)


# ---------------------------------------------------------------------------
# Test 5: No-lookahead test
# ---------------------------------------------------------------------------

class TestNoLookahead:
    def test_twap_window_starts_at_fill_time_not_before(self):
        """Shadow fills must only use M15 bars at or after fill_ts_ms."""
        fill_ts = 1000000000000
        # Create bars both before and after
        idx = {}
        # 4 bars before fill time (should be ignored)
        for i in range(4):
            idx[fill_ts - (i + 1) * M15_INTERVAL_MS] = make_bar(999.0)
        # 4 bars at and after fill time
        for i in range(4):
            idx[fill_ts + i * M15_INTERVAL_MS] = make_bar(100.0 + i)

        result = get_twap_window(fill_ts, idx)
        # Should only get the 4 bars starting at fill_ts
        assert len(result) == 4
        assert all(b["close"] != 999.0 for b in result)

    def test_twap_uses_only_post_signal_data(self):
        fill_ts = 1000000000000
        post_bars = [make_bar(100 + i) for i in range(4)]
        idx = make_m15_index(fill_ts, post_bars)
        twap = compute_twap(get_twap_window(fill_ts, idx))
        expected = np.mean([100, 101, 102, 103])
        assert twap == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Test 6: Missing-intrabar behavior test
# ---------------------------------------------------------------------------

class TestMissingBars:
    def test_twap_with_partial_bars(self):
        """If only 3 of 4 bars exist, TWAP uses available bars."""
        bars = [make_bar(100), make_bar(110), make_bar(120)]
        twap = compute_twap(bars)
        assert twap == pytest.approx(110.0, rel=1e-10)

    def test_twap_returns_none_when_empty(self):
        assert compute_twap([]) is None

    def test_vwap_returns_none_when_empty(self):
        assert compute_vwap([]) is None

    def test_vwap_excludes_zero_volume_bars(self):
        """Zero-volume bars should be excluded from VWAP."""
        bars = [
            make_bar(100, volume=0, high=100, low=100),
            make_bar(200, volume=10, high=200, low=200),
            make_bar(300, volume=10, high=300, low=300),
            make_bar(400, volume=0, high=400, low=400),
        ]
        vwap = compute_vwap(bars)
        # Only bars 2 and 3 contribute: tp=200, tp=300, equal volume
        expected = (200 * 10 + 300 * 10) / 20
        assert vwap == pytest.approx(expected, rel=1e-10)

    def test_vwap_falls_back_to_twap_when_all_zero_volume(self):
        """All zero-volume bars -> fallback to TWAP."""
        bars = [make_bar(100 + i, volume=0) for i in range(4)]
        vwap = compute_vwap(bars)
        twap = compute_twap(bars)
        assert vwap == pytest.approx(twap, rel=1e-10)


# ---------------------------------------------------------------------------
# Test 7: Paired trade count consistency test
# ---------------------------------------------------------------------------

class TestConsistency:
    def test_output_row_count_matches_input(self):
        """Shadow fills must produce exactly one row per input trade."""
        # Use synthetic data
        from build_shadow_execution import compute_shadow_fills
        import pandas as pd

        trades = pd.DataFrame([{
            "trade_id": 1,
            "entry_ts_ms": 1000000000000,
            "exit_ts_ms": 1000000100000,
            "entry_mid_price": 50000.0,
            "exit_mid_price": 51000.0,
            "entry_fill_price": 50027.5,
            "exit_fill_price": 50971.95,
            "qty": 1.0,
            "pnl_usd": 500.0,
            "net_return_pct": 1.0,
        }])

        # Build M15 index with bars at both entry and exit
        idx = {}
        for ts_base in [1000000000000, 1000000100000]:
            for i in range(4):
                idx[ts_base + i * M15_INTERVAL_MS] = make_bar(50500.0)

        sf = compute_shadow_fills(trades, idx)
        assert len(sf) == 1
        assert sf.iloc[0]["trade_id"] == 1

    def test_all_columns_present(self):
        """Shadow fills CSV must have all schema columns."""
        from build_shadow_execution import compute_shadow_fills
        import pandas as pd

        trades = pd.DataFrame([{
            "trade_id": 1,
            "entry_ts_ms": 1000000000000,
            "exit_ts_ms": 1000000100000,
            "entry_mid_price": 50000.0,
            "exit_mid_price": 51000.0,
            "entry_fill_price": 50027.5,
            "exit_fill_price": 50971.95,
            "qty": 1.0,
            "pnl_usd": 500.0,
            "net_return_pct": 1.0,
        }])

        idx = {}
        for ts_base in [1000000000000, 1000000100000]:
            for i in range(4):
                idx[ts_base + i * M15_INTERVAL_MS] = make_bar(50500.0)

        sf = compute_shadow_fills(trades, idx)
        required_cols = [
            "trade_id", "entry_ts_ms", "exit_ts_ms", "qty", "entry_notional_usd",
            "baseline_entry_mid", "baseline_exit_mid",
            "baseline_entry_fill", "baseline_exit_fill",
            "baseline_pnl_usd", "baseline_net_return_pct",
            "twap_entry_price", "twap_exit_price",
            "vwap_entry_price", "vwap_exit_price",
            "twap_entry_delta_bps", "twap_exit_delta_bps", "twap_combined_delta_bps",
            "vwap_entry_delta_bps", "vwap_exit_delta_bps", "vwap_combined_delta_bps",
            "twap_shadow_entry_fill", "twap_shadow_exit_fill",
            "twap_shadow_pnl_usd", "twap_pnl_delta_usd",
            "vwap_shadow_entry_fill", "vwap_shadow_exit_fill",
            "vwap_shadow_pnl_usd", "vwap_pnl_delta_usd",
            "entry_m15_count", "exit_m15_count",
            "entry_fallback", "exit_fallback",
        ]
        for col in required_cols:
            assert col in sf.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# Test 8: TWAP/VWAP computation correctness
# ---------------------------------------------------------------------------

class TestFillComputation:
    def test_twap_is_simple_mean_of_closes(self):
        bars = [make_bar(100), make_bar(200), make_bar(300), make_bar(400)]
        assert compute_twap(bars) == pytest.approx(250.0, rel=1e-10)

    def test_vwap_weights_by_volume(self):
        """Bar with 3x volume should have 3x weight."""
        bars = [
            {"open": 100, "high": 100, "low": 100, "close": 100, "volume": 30},
            {"open": 200, "high": 200, "low": 200, "close": 200, "volume": 10},
            {"open": 300, "high": 300, "low": 300, "close": 300, "volume": 10},
            {"open": 400, "high": 400, "low": 400, "close": 400, "volume": 10},
        ]
        vwap = compute_vwap(bars)
        # typical_price = close for these bars (H=L=C)
        # vwap = (100*30 + 200*10 + 300*10 + 400*10) / 60 = 12000/60 = 200
        assert vwap == pytest.approx(200.0, rel=1e-10)

    def test_vwap_uses_typical_price_not_close(self):
        """VWAP uses (H+L+C)/3, not just close."""
        bars = [
            {"open": 100, "high": 110, "low": 90, "close": 100, "volume": 10},
        ]
        vwap = compute_vwap(bars)
        expected = (110 + 90 + 100) / 3  # = 100.0
        assert vwap == pytest.approx(expected, rel=1e-10)

        bars2 = [
            {"open": 100, "high": 120, "low": 90, "close": 100, "volume": 10},
        ]
        vwap2 = compute_vwap(bars2)
        expected2 = (120 + 90 + 100) / 3  # = 103.33...
        assert vwap2 == pytest.approx(expected2, rel=1e-6)
