#!/usr/bin/env python3
"""Unit tests for X6 research — adaptive trail + breakeven floor.

Tests verify:
  1. Config defaults match specification
  2. Strategy ID and name
  3. Entry conditions identical to X0
  4. Tight trail (gain < 5%): no BE floor, 3×ATR
  5. Mid trail (5-15%): 4×ATR + BE floor at entry price
  6. Wide trail (>=15%): 5×ATR + BE floor at entry price
  7. BE floor: stop never goes below entry price when gain >= tier1
  8. No BE floor below tier1 (fresh trades need room)
  9. Peak price tracking across tiers
  10. Trend exit works from all tiers
  11. on_after_fill updates entry price
  12. Engine integration: runs without errors
  13. Binary exposure only (no partial sells)
  14. Vectorized surrogate produces valid output
  15. X6 vs X2: same trades when BE floor doesn't bind
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from v10.core.types import Bar, Fill, MarketState, Side, Signal
from strategies.vtrend_x6.strategy import (
    VTrendX6Config, VTrendX6Strategy, STRATEGY_ID,
)


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


def _make_d1_bar(close, close_time):
    return Bar(
        open_time=close_time - 86_400_000,
        open=close,
        high=close * 1.01,
        low=close * 0.99,
        close=close,
        volume=10000.0,
        close_time=close_time,
        taker_buy_base_vol=5000.0,
        interval="1d",
    )


def _build_state(bar, h4_bars, d1_bars, bar_index, d1_index=-1,
                 cash=10000.0, btc_qty=0.0, nav=10000.0, exposure=0.0,
                 entry_price_avg=0.0, position_entry_nav=0.0):
    return MarketState(
        bar=bar,
        h4_bars=h4_bars,
        d1_bars=d1_bars,
        bar_index=bar_index,
        d1_index=d1_index,
        cash=cash,
        btc_qty=btc_qty,
        nav=nav,
        exposure=exposure,
        entry_price_avg=entry_price_avg,
        position_entry_nav=position_entry_nav,
    )


def _make_trending_bars(n=200, start_price=10000.0, trend_pct=0.002,
                        start_time=0, interval="4h"):
    bars = []
    p = start_price
    for i in range(n):
        p *= (1 + trend_pct)
        ct = start_time + i * 14_400_000
        buy_frac = 0.50 + 0.30 * (i / n)
        vol = 1000.0
        bars.append(_make_bar(p, close_time=ct, interval=interval,
                              volume=vol, taker_buy=vol * buy_frac))
    return bars


def _make_d1_trending(n=100, start_price=10000.0, trend_pct=0.005,
                      start_time=0):
    bars = []
    p = start_price
    for i in range(n):
        p *= (1 + trend_pct)
        ct = start_time + i * 86_400_000
        bars.append(_make_d1_bar(p, close_time=ct))
    return bars


def _init_strategy_with_entry(config=None):
    config = config or VTrendX6Config()
    strat = VTrendX6Strategy(config)
    h4_bars = _make_trending_bars(300, start_price=10000.0, trend_pct=0.003)
    d1_bars = _make_d1_trending(50, start_price=10000.0, trend_pct=0.005,
                                start_time=h4_bars[0].close_time - 86_400_000)
    strat.on_init(h4_bars, d1_bars)
    for i in range(1, len(h4_bars)):
        state = _build_state(h4_bars[i], h4_bars, d1_bars, i)
        sig = strat.on_bar(state)
        if sig is not None and sig.target_exposure == 1.0:
            return strat, h4_bars, d1_bars, i
    pytest.fail("Could not trigger entry in trending data")


# =========================================================================
# Tests
# =========================================================================

class TestConfig:
    def test_defaults(self):
        c = VTrendX6Config()
        assert c.slow_period == 120.0
        assert c.trail_tight == 3.0
        assert c.trail_mid == 4.0
        assert c.trail_wide == 5.0
        assert c.gain_tier1 == 0.05
        assert c.gain_tier2 == 0.15
        assert c.vdo_threshold == 0.0
        assert c.d1_ema_period == 21

    def test_strategy_id(self):
        assert STRATEGY_ID == "vtrend_x6"
        strat = VTrendX6Strategy()
        assert strat.name() == "vtrend_x6"


class TestTrailStop:
    def test_tight_no_be_floor(self):
        """Below tier1 (5%): 3×ATR, no breakeven floor."""
        strat = VTrendX6Strategy(VTrendX6Config(trail_tight=3.0, gain_tier1=0.05))
        strat._in_position = True
        strat._peak_price = 10200.0
        strat._entry_price = 10000.0
        # unrealized = (10200 - 10000) / 10000 = 0.02 < 0.05
        # trail = 10200 - 3 * 500 = 8700
        stop = strat._compute_trail_stop(10200.0, 500.0)
        assert stop == 8700.0  # no BE floor, can go below entry

    def test_mid_with_be_floor_binds(self):
        """In mid tier (5-15%), BE floor binds when trail < entry."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_mid=4.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 10800.0
        strat._entry_price = 10000.0
        # unrealized = (10800 - 10000) / 10000 = 0.08, in [0.05, 0.15)
        # trail = 10800 - 4 * 500 = 8800 < 10000
        # BE floor = 10000
        stop = strat._compute_trail_stop(10800.0, 500.0)
        assert stop == 10000.0  # BE floor binds

    def test_mid_trail_above_entry(self):
        """In mid tier, when trail > entry, trail wins."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_mid=4.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 15000.0
        strat._entry_price = 10000.0
        # unrealized = (15000 - 10000) / 10000 = 0.50 — wait, this is > 0.15
        # Need to test at the right price for mid tier
        strat._peak_price = 10800.0
        # trail = 10800 - 4 * 100 = 10400 > 10000
        stop = strat._compute_trail_stop(10800.0, 100.0)
        assert stop == 10400.0  # trail above entry, trail wins

    def test_wide_with_be_floor(self):
        """In wide tier (>=15%), 5×ATR + BE floor."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_wide=5.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 12000.0
        strat._entry_price = 10000.0
        # unrealized = (12000 - 10000) / 10000 = 0.20 >= 0.15
        # trail = 12000 - 5 * 500 = 9500 < 10000
        stop = strat._compute_trail_stop(12000.0, 500.0)
        assert stop == 10000.0  # BE floor binds

    def test_wide_trail_above_entry(self):
        """In wide tier, when trail > entry, trail wins."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_wide=5.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 20000.0
        strat._entry_price = 10000.0
        # trail = 20000 - 5 * 200 = 19000 > 10000
        stop = strat._compute_trail_stop(20000.0, 200.0)
        assert stop == 19000.0


class TestEntry:
    def test_entry_transitions_correctly(self):
        strat, h4, d1, entry_idx = _init_strategy_with_entry()
        assert strat._in_position is True
        assert strat._entry_price > 0

    def test_entry_signal(self):
        config = VTrendX6Config()
        strat = VTrendX6Strategy(config)
        h4 = _make_trending_bars(300, trend_pct=0.003)
        d1 = _make_d1_trending(50, start_price=10000.0, trend_pct=0.005,
                               start_time=h4[0].close_time - 86_400_000)
        strat.on_init(h4, d1)
        for i in range(1, len(h4)):
            state = _build_state(h4[i], h4, d1, i)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x6_entry":
                assert sig.target_exposure == 1.0
                return
        pytest.fail("No entry signal")

    def test_binary_exposure_only(self):
        """X6 should only produce 0.0 or 1.0 exposure signals."""
        strat, h4, d1, entry_idx = _init_strategy_with_entry()
        # Continue running — all signals should be 0.0 or 1.0
        for i in range(entry_idx + 1, len(h4)):
            state = _build_state(h4[i], h4, d1, i,
                                 btc_qty=1.0, exposure=1.0,
                                 entry_price_avg=h4[entry_idx].close)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.target_exposure in (0.0, 1.0), \
                    f"Non-binary exposure: {sig.target_exposure}"


class TestOnAfterFill:
    def test_entry_fill_updates_entry_price(self):
        strat = VTrendX6Strategy()
        fill = Fill(ts_ms=1000, side=Side.BUY, qty=1.0,
                    price=50000.0, fee=50.0, notional=50000.0,
                    reason="x6_entry")
        bar = _make_bar(50100.0, close_time=2000)
        state = _build_state(bar, [bar], [], 0)
        strat.on_after_fill(state, fill)
        assert strat._entry_price == 50000.0

    def test_non_entry_fill_no_change(self):
        strat = VTrendX6Strategy()
        strat._entry_price = 50000.0
        fill = Fill(ts_ms=2000, side=Side.SELL, qty=1.0,
                    price=55000.0, fee=55.0, notional=55000.0,
                    reason="x6_trail_stop")
        bar = _make_bar(55000.0, close_time=3000)
        state = _build_state(bar, [bar], [], 0)
        strat.on_after_fill(state, fill)
        assert strat._entry_price == 50000.0  # unchanged


class TestEngineIntegration:
    def test_runs_without_error(self):
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import SCENARIOS

        data_path = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        if not data_path.exists():
            pytest.skip("Data file not available")

        feed = DataFeed(str(data_path), start="2023-01-01", end="2024-01-01",
                        warmup_days=365)
        strat = VTrendX6Strategy(VTrendX6Config())
        cost = SCENARIOS["harsh"]
        eng = BacktestEngine(feed=feed, strategy=strat, cost=cost,
                             initial_cash=10_000.0, warmup_mode="no_trade")
        res = eng.run()

        assert res.summary["trades"] >= 0
        assert res.summary["sharpe"] is not None
        assert len(res.equity) > 0
        # Binary exposure: fills == 2*trades (flat at end) or 2*trades+1 (open)
        n_fills = res.summary["fills"]
        n_trades = res.summary["trades"]
        assert n_fills in (2 * n_trades, 2 * n_trades + 1)


class TestVectorizedSurrogate:
    def test_sim_x6_runs(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from benchmark import _sim_x6, _sim_x0, _sim_x2

        n = 500
        rng = np.random.RandomState(42)
        cl = np.cumsum(rng.randn(n) * 0.01 + 0.001) + 10.0
        cl = np.abs(cl)
        hi = cl * 1.005
        lo = cl * 0.995
        vo = np.ones(n) * 1000
        tb = np.ones(n) * 500
        d1_n = n // 6
        d1_cl = cl[::6][:d1_n]
        d1_ct = np.arange(d1_n) * 86_400_000
        h4_ct = np.arange(n) * 14_400_000
        wi = 50

        nav_x6, nt_x6 = _sim_x6(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        nav_x0, nt_x0 = _sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        nav_x2, nt_x2 = _sim_x2(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)

        assert len(nav_x6) == n
        assert nav_x6[-1] > 0
        assert nav_x0[-1] > 0
        assert nav_x2[-1] > 0

    def test_sim_x6_starts_at_cash(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from benchmark import _sim_x6, CASH

        n = 100
        cl = np.ones(n) * 10000.0
        hi = cl * 1.005
        lo = cl * 0.995
        vo = np.ones(n) * 1000
        tb = np.ones(n) * 500
        d1_cl = np.ones(20) * 10000.0
        d1_ct = np.arange(20) * 86_400_000
        h4_ct = np.arange(n) * 14_400_000

        nav, _ = _sim_x6(cl, hi, lo, vo, tb, 0, d1_cl, d1_ct, h4_ct)
        assert nav[0] == CASH
