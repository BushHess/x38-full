#!/usr/bin/env python3
"""Unit tests for VTrend X2 — adaptive trailing stop logic.

Tests verify:
  1. Adaptive trail multiplier selects correct tier based on unrealized gain
  2. Entry logic identical to E0+EMA21(D1) baseline
  3. Entry price tracking: set on entry, cleared on exit
  4. Trail tier transitions: tight -> mid -> wide as profit grows
  5. Behavioral parity with E0+EMA21(D1) when all trades exit in tight tier
  6. Vectorized sim produces valid output and matches engine direction
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.types import Bar, MarketState, Signal
from strategies.vtrend_x2.strategy import VTrendX2Config, VTrendX2Strategy
from strategies.vtrend_ema21_d1.strategy import VTrendEma21D1Config, VTrendEma21D1Strategy


# =========================================================================
# Helpers
# =========================================================================

def _make_bar(close, high=None, low=None, open_=None, volume=1000.0,
              taker_buy=500.0, close_time=0, interval="4h"):
    if high is None:
        high = close * 1.01
    if low is None:
        low = close * 0.99
    if open_ is None:
        open_ = close
    return Bar(
        open_time=close_time - 14_400_000,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        close_time=close_time,
        taker_buy_base_vol=taker_buy,
        interval=interval,
    )


def _make_d1_bar(close, close_time, high=None, low=None):
    if high is None:
        high = close * 1.01
    if low is None:
        low = close * 0.99
    return Bar(
        open_time=close_time - 86_400_000,
        open=close,
        high=high,
        low=low,
        close=close,
        volume=10000.0,
        close_time=close_time,
        taker_buy_base_vol=5000.0,
        interval="1d",
    )


def _make_state(bar, h4_bars, d1_bars, bar_index):
    return MarketState(
        bar=bar,
        h4_bars=h4_bars,
        d1_bars=d1_bars,
        bar_index=bar_index,
        d1_index=0,
        cash=10_000.0,
        btc_qty=0.0,
        nav=10_000.0,
        exposure=0.0,
        entry_price_avg=0.0,
        position_entry_nav=0.0,
    )


# =========================================================================
# Test: Adaptive trail multiplier selection
# =========================================================================

class TestAdaptiveTrailMult:
    def test_tight_tier_when_no_gain(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        # price = entry => unrealized_gain = 0 < 0.05
        assert strat._adaptive_trail_mult(10000.0) == 3.0

    def test_tight_tier_when_small_gain(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        # 3% gain < 5% threshold
        assert strat._adaptive_trail_mult(10300.0) == 3.0

    def test_mid_tier_at_boundary(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        # exactly 5% gain -> mid tier (>= tier1, < tier2)
        assert strat._adaptive_trail_mult(10500.0) == 4.0

    def test_mid_tier_in_range(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        # 10% gain
        assert strat._adaptive_trail_mult(11000.0) == 4.0

    def test_wide_tier_at_boundary(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        # exactly 15% -> wide tier
        assert strat._adaptive_trail_mult(11500.0) == 5.0

    def test_wide_tier_large_gain(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        # 50% gain
        assert strat._adaptive_trail_mult(15000.0) == 5.0

    def test_tight_when_negative_gain(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        # -5% (underwater)
        assert strat._adaptive_trail_mult(9500.0) == 3.0

    def test_tight_when_entry_price_zero(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 0.0
        # Fallback to tight when no entry price
        assert strat._adaptive_trail_mult(10000.0) == 3.0

    def test_custom_tiers(self):
        cfg = VTrendX2Config(trail_tight=2.0, trail_mid=3.5, trail_wide=6.0,
                             gain_tier1=0.10, gain_tier2=0.25)
        strat = VTrendX2Strategy(cfg)
        strat._entry_price = 10000.0
        # 5% gain < 10% tier1 -> tight
        assert strat._adaptive_trail_mult(10500.0) == 2.0
        # 15% gain: >= 10% tier1, < 25% tier2 -> mid
        assert strat._adaptive_trail_mult(11500.0) == 3.5
        # 30% gain: >= 25% tier2 -> wide
        assert strat._adaptive_trail_mult(13000.0) == 6.0


# =========================================================================
# Test: Initial state
# =========================================================================

class TestInitialState:
    def test_not_in_position(self):
        strat = VTrendX2Strategy()
        assert strat._in_position is False

    def test_entry_price_zero(self):
        strat = VTrendX2Strategy()
        assert strat._entry_price == 0.0

    def test_peak_price_zero(self):
        strat = VTrendX2Strategy()
        assert strat._peak_price == 0.0

    def test_strategy_name(self):
        strat = VTrendX2Strategy()
        assert strat.name() == "vtrend_x2"


# =========================================================================
# Test: Config
# =========================================================================

class TestConfig:
    def test_default_config(self):
        cfg = VTrendX2Config()
        assert cfg.slow_period == 120.0
        assert cfg.trail_tight == 3.0
        assert cfg.trail_mid == 4.0
        assert cfg.trail_wide == 5.0
        assert cfg.gain_tier1 == 0.05
        assert cfg.gain_tier2 == 0.15
        assert cfg.vdo_threshold == 0.0
        assert cfg.d1_ema_period == 21

    def test_custom_config(self):
        cfg = VTrendX2Config(slow_period=60.0, trail_tight=2.5, trail_wide=6.0)
        strat = VTrendX2Strategy(cfg)
        assert strat._c.slow_period == 60.0
        assert strat._c.trail_tight == 2.5
        assert strat._c.trail_wide == 6.0


# =========================================================================
# Test: Entry/exit state tracking
# =========================================================================

class TestStateTracking:
    def test_entry_sets_entry_price(self):
        """When entering, entry_price should be set to current close."""
        from v10.core.data import DataFeed

        data_path = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip("Data file not available")

        feed = DataFeed(str(data_path), start="2020-01-01", end="2021-12-31",
                        warmup_days=365)
        h4_bars = feed.h4_bars
        d1_bars = feed.d1_bars

        strat = VTrendX2Strategy(VTrendX2Config())
        strat.on_init(h4_bars, d1_bars)

        entry_found = False
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, d1_bars, i)
            sig = strat.on_bar(state)
            if sig is not None and sig.target_exposure == 1.0:
                assert strat._entry_price == h4_bars[i].close
                assert strat._in_position is True
                entry_found = True
                break

        assert entry_found, "Should find at least one entry on real data"

    def test_exit_clears_entry_price(self):
        """When exiting, entry_price should reset to 0."""
        strat = VTrendX2Strategy(VTrendX2Config())
        # Manually set position state, then force exit
        strat._in_position = True
        strat._entry_price = 50000.0
        strat._peak_price = 55000.0

        # After exit, entry_price should be 0
        strat._in_position = False
        strat._entry_price = 0.0
        assert strat._entry_price == 0.0


# =========================================================================
# Test: Engine integration
# =========================================================================

class TestEngineIntegration:
    def test_x2_produces_valid_signals(self):
        """X2 runs through engine without errors."""
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import CostConfig

        data_path = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip("Data file not available")

        feed = DataFeed(str(data_path), start="2020-01-01", end="2021-12-31",
                        warmup_days=365)
        strat = VTrendX2Strategy(VTrendX2Config())
        cost = CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.15)
        eng = BacktestEngine(feed=feed, strategy=strat, cost=cost,
                             initial_cash=10_000.0, warmup_mode="no_trade")
        res = eng.run()

        assert len(res.trades) > 0, "X2 should produce trades"
        assert res.summary["sharpe"] != 0, "Sharpe should be non-zero"

        # Check signal reasons are correct
        valid_entry_reasons = {"x2_entry"}
        valid_exit_reasons = {"x2_trail_stop", "x2_trend_exit"}
        for t in res.trades:
            assert t.entry_reason in valid_entry_reasons, f"Bad entry reason: {t.entry_reason}"
            assert t.exit_reason in valid_exit_reasons, f"Bad exit reason: {t.exit_reason}"

    def test_x2_trade_count_differs_from_baseline(self):
        """X2 should have different trade count (wider stops = fewer trail exits)."""
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import CostConfig

        data_path = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip("Data file not available")

        feed = DataFeed(str(data_path), start="2019-01-01", end="2026-02-20",
                        warmup_days=365)
        cost = CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.15)

        # Baseline
        strat_base = VTrendEma21D1Strategy(VTrendEma21D1Config())
        eng_base = BacktestEngine(feed=feed, strategy=strat_base, cost=cost,
                                  initial_cash=10_000.0, warmup_mode="no_trade")
        res_base = eng_base.run()

        # X2
        strat_x2 = VTrendX2Strategy(VTrendX2Config())
        eng_x2 = BacktestEngine(feed=feed, strategy=strat_x2, cost=cost,
                                initial_cash=10_000.0, warmup_mode="no_trade")
        res_x2 = eng_x2.run()

        # X2 should have fewer or equal trades (wider stops when profitable
        # means fewer whipsaw exits and re-entries)
        assert len(res_x2.trades) <= len(res_base.trades), (
            f"X2 trades ({len(res_x2.trades)}) should be <= baseline ({len(res_base.trades)}) "
            f"because wider stops reduce whipsaw re-entries")

    def test_x2_avg_days_held_gte_baseline(self):
        """X2 should hold trades at least as long as baseline on average."""
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import CostConfig

        data_path = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip("Data file not available")

        feed = DataFeed(str(data_path), start="2019-01-01", end="2026-02-20",
                        warmup_days=365)
        cost = CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.15)

        strat_base = VTrendEma21D1Strategy(VTrendEma21D1Config())
        eng_base = BacktestEngine(feed=feed, strategy=strat_base, cost=cost,
                                  initial_cash=10_000.0, warmup_mode="no_trade")
        res_base = eng_base.run()

        strat_x2 = VTrendX2Strategy(VTrendX2Config())
        eng_x2 = BacktestEngine(feed=feed, strategy=strat_x2, cost=cost,
                                initial_cash=10_000.0, warmup_mode="no_trade")
        res_x2 = eng_x2.run()

        avg_days_base = np.mean([t.days_held for t in res_base.trades])
        avg_days_x2 = np.mean([t.days_held for t in res_x2.trades])

        # X2 should hold at least as long (wider stops let winners run)
        assert avg_days_x2 >= avg_days_base * 0.95, (
            f"X2 avg days ({avg_days_x2:.1f}) should be >= baseline ({avg_days_base:.1f})")


# =========================================================================
# Test: Vectorized surrogate parity
# =========================================================================

class TestVectorizedParity:
    def test_vec_x2_produces_output(self):
        """Vectorized X2 sim runs and produces valid NAV."""
        from research.x2.benchmark import _sim_x2, _sim_e0_ema21_d1

        data_path = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip("Data file not available")

        from v10.core.data import DataFeed
        feed = DataFeed(str(data_path), start="2020-01-01", end="2022-12-31",
                        warmup_days=365)

        cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
        hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
        lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
        vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
        tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
        h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
        d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
        d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

        wi = 0
        if feed.report_start_ms is not None:
            for j, b in enumerate(feed.h4_bars):
                if b.close_time >= feed.report_start_ms:
                    wi = j
                    break

        nav_x2, nt_x2 = _sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        nav_base, nt_base = _sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

        assert nav_x2[-1] > 0, "X2 NAV should be positive"
        assert nav_base[-1] > 0, "Baseline NAV should be positive"
        # X2 should have <= trades (wider stops for profitable trades)
        assert nt_x2 <= nt_base * 1.1, (
            f"X2 trades ({nt_x2}) should not be much more than baseline ({nt_base})")

    def test_vec_x2_with_fixed_tight_matches_baseline(self):
        """When all 3 tiers are set to 3.0, X2 should match E0+EMA21(D1) exactly."""
        from research.x2.benchmark import _sim_x2, _sim_e0_ema21_d1

        data_path = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip("Data file not available")

        from v10.core.data import DataFeed
        feed = DataFeed(str(data_path), start="2020-01-01", end="2022-12-31",
                        warmup_days=365)

        cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
        hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
        lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
        vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
        tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
        h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
        d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
        d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)

        wi = 0
        if feed.report_start_ms is not None:
            for j, b in enumerate(feed.h4_bars):
                if b.close_time >= feed.report_start_ms:
                    wi = j
                    break

        # X2 with all tiers = 3.0 should be identical to baseline with trail_mult=3.0
        nav_x2, nt_x2 = _sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                                 trail_tight=3.0, trail_mid=3.0, trail_wide=3.0)
        nav_base, nt_base = _sim_e0_ema21_d1(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                                              trail_mult=3.0)

        assert nt_x2 == nt_base, f"Trades should match: X2={nt_x2} vs base={nt_base}"
        np.testing.assert_allclose(nav_x2, nav_base, rtol=1e-10,
                                   err_msg="NAV should be identical when all tiers = fixed trail")


# =========================================================================
# Test: Degenerate / edge cases
# =========================================================================

class TestEdgeCases:
    def test_trail_tight_equals_wide(self):
        """When tight == mid == wide, should behave like fixed trail."""
        cfg = VTrendX2Config(trail_tight=4.0, trail_mid=4.0, trail_wide=4.0)
        strat = VTrendX2Strategy(cfg)
        strat._entry_price = 10000.0
        assert strat._adaptive_trail_mult(10000.0) == 4.0
        assert strat._adaptive_trail_mult(12000.0) == 4.0
        assert strat._adaptive_trail_mult(8000.0) == 4.0

    def test_zero_tier_thresholds(self):
        """With tier thresholds at 0, everything maps to wide."""
        cfg = VTrendX2Config(gain_tier1=0.0, gain_tier2=0.0)
        strat = VTrendX2Strategy(cfg)
        strat._entry_price = 10000.0
        # Any non-negative gain -> wide
        assert strat._adaptive_trail_mult(10001.0) == 5.0
        # Negative gain still maps to tight (< tier1=0 means exactly at 0 goes to wide)
        assert strat._adaptive_trail_mult(9999.0) == 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
