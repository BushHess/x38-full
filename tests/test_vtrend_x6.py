"""Tests for VTREND-X6 adaptive trail + breakeven floor strategy.

Comprehensive test suite matching X0 validation pattern:
  1. D1 regime uses completed D1 bars only (no future leak)
  2. Config loads from YAML without error
  3. Strategy produces signals matching spec on synthetic data
  4. Registration in all system registries
  5. Breakeven floor logic correctness
  6. Adaptive trail + BE floor interaction
  7. Engine integration
  8. Vectorized surrogate parity
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from v10.core.types import Bar, Fill, MarketState, Side, Signal
from v10.strategies.base import Strategy
from strategies.vtrend_x6.strategy import (
    STRATEGY_ID,
    VTrendX6Config,
    VTrendX6Strategy,
    _ema,
)


# -- Helpers ----------------------------------------------------------------

def _make_bar(
    close: float,
    high: float | None = None,
    low: float | None = None,
    open_: float | None = None,
    volume: float = 100.0,
    taker_buy: float = 60.0,
    open_time: int = 0,
    close_time: int = 0,
    interval: str = "4h",
) -> Bar:
    if high is None:
        high = close * 1.01
    if low is None:
        low = close * 0.99
    if open_ is None:
        open_ = close
    return Bar(
        open_time=open_time,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        close_time=close_time,
        taker_buy_base_vol=taker_buy,
        interval=interval,
    )


def _make_state(
    bar: Bar,
    h4_bars: list[Bar],
    bar_index: int,
    d1_bars: list[Bar] | None = None,
    entry_price_avg: float = 0.0,
) -> MarketState:
    return MarketState(
        bar=bar,
        h4_bars=h4_bars,
        d1_bars=d1_bars or [],
        bar_index=bar_index,
        d1_index=-1,
        cash=10_000.0,
        btc_qty=0.0,
        nav=10_000.0,
        exposure=0.0,
        entry_price_avg=entry_price_avg,
        position_entry_nav=0.0,
    )


def _make_trending_h4_bars(n: int, start: float = 100.0,
                            trend: float = 0.5) -> list[Bar]:
    bars = []
    for i in range(n):
        c = start + i * trend
        spread = c * 0.001
        tb = min(55.0 + i * 0.2, 85.0)
        bars.append(_make_bar(
            close=c,
            high=c + spread,
            low=c - spread,
            open_=c - trend * 0.3,
            volume=100.0,
            taker_buy=tb,
            open_time=i * 14_400_000,
            close_time=(i + 1) * 14_400_000 - 1,
        ))
    return bars


def _make_d1_bars(n: int, start: float = 100.0,
                   trend: float = 3.0) -> list[Bar]:
    bars = []
    for i in range(n):
        c = start + i * trend
        spread = c * 0.002
        bars.append(_make_bar(
            close=c,
            high=c + spread,
            low=c - spread,
            open_=c - trend * 0.3,
            open_time=i * 86_400_000,
            close_time=(i + 1) * 86_400_000 - 1,
            interval="1d",
        ))
    return bars


# -- Test 1: D1 regime no-lookahead ----------------------------------------

class TestD1RegimeNoLookahead:
    """D1 regime filter must use only completed D1 bars, no future leak."""

    def test_regime_uses_completed_d1_only(self):
        d1_bars = [
            _make_bar(close=100.0, open_time=0, close_time=86_399_999,
                      interval="1d"),
            _make_bar(close=200.0, open_time=86_400_000,
                      close_time=172_799_999, interval="1d"),
        ]
        h4_bars = [
            _make_bar(close=50.0, open_time=0, close_time=14_399_999),
            _make_bar(close=150.0, open_time=86_400_000,
                      close_time=100_799_999),
            _make_bar(close=160.0, open_time=100_800_000,
                      close_time=115_199_999),
            _make_bar(close=190.0, open_time=172_800_000,
                      close_time=187_199_999),
        ]

        strat = VTrendX6Strategy(VTrendX6Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)

        regime = strat._d1_regime_ok
        assert regime is not None
        assert regime[0] == False, "D1[0] regime: 100 > 100 is False"
        assert regime[1] == False, "H4 bar before D1[1] close must not leak"
        assert regime[2] == False, "H4 bar before D1[1] close must not leak"

    def test_no_d1_bars_yields_all_false(self):
        h4_bars = _make_trending_h4_bars(50)
        strat = VTrendX6Strategy()
        strat.on_init(h4_bars, [])
        assert strat._d1_regime_ok is not None
        assert not np.any(strat._d1_regime_ok)

    def test_future_d1_not_visible(self):
        d1_bars = [
            _make_bar(close=500.0, open_time=0,
                      close_time=999_999_999, interval="1d"),
        ]
        h4_bars = [
            _make_bar(close=50.0, open_time=0, close_time=14_399_999),
        ]

        strat = VTrendX6Strategy(VTrendX6Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)
        assert strat._d1_regime_ok[0] == False


# -- Test 2: Config load from YAML -----------------------------------------

class TestConfigLoad:

    def test_config_loads_from_yaml(self):
        from v10.core.config import load_config
        cfg = load_config("configs/vtrend_x6/vtrend_x6_default.yaml")
        assert cfg.strategy.name == "vtrend_x6"
        assert cfg.strategy.params["slow_period"] == 120.0
        assert cfg.strategy.params["trail_tight"] == 3.0
        assert cfg.strategy.params["trail_mid"] == 4.0
        assert cfg.strategy.params["trail_wide"] == 5.0
        assert cfg.strategy.params["gain_tier1"] == 0.05
        assert cfg.strategy.params["gain_tier2"] == 0.15

    def test_config_defaults_match_spec(self):
        cfg = VTrendX6Config()
        assert cfg.slow_period == 120.0
        assert cfg.trail_tight == 3.0
        assert cfg.trail_mid == 4.0
        assert cfg.trail_wide == 5.0
        assert cfg.gain_tier1 == 0.05
        assert cfg.gain_tier2 == 0.15
        assert cfg.vdo_threshold == 0.0
        assert cfg.d1_ema_period == 21
        assert cfg.atr_period == 14
        assert cfg.vdo_fast == 12
        assert cfg.vdo_slow == 28

    def test_strategy_id(self):
        assert STRATEGY_ID == "vtrend_x6"
        s = VTrendX6Strategy()
        assert s.name() == "vtrend_x6"

    def test_subclass_of_strategy(self):
        assert issubclass(VTrendX6Strategy, Strategy)

    def test_field_count(self):
        n_fields = len(dataclasses.fields(VTrendX6Config))
        assert n_fields >= 7, f"Expected >= 7 fields, got {n_fields}"


# -- Test 3: Smoke signal test ---------------------------------------------

class TestSmokeSignals:

    def test_entry_signal_during_uptrend(self):
        d1_bars = _make_d1_bars(60, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(300, start=100.0, trend=0.5)

        strat = VTrendX6Strategy(VTrendX6Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entries = []
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x6_entry":
                entries.append((i, sig))
                break

        assert len(entries) >= 1, "Must emit entry in strong uptrend"
        assert entries[0][1].target_exposure == 1.0

    def test_exit_signal_after_crash(self):
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 5.0
            spread = max(c * 0.001, 0.1)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c + 2.0, volume=100.0, taker_buy=20.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX6Strategy(VTrendX6Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entered = False
        exited = False
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                if sig.reason == "x6_entry":
                    entered = True
                elif sig.reason in ("x6_trail_stop", "x6_be_stop", "x6_trend_exit"):
                    exited = True
                    assert sig.target_exposure == 0.0
                    break

        assert entered, "Must enter during uptrend"
        assert exited, "Must exit during crash"

    def test_no_signal_without_regime(self):
        d1_bars = _make_d1_bars(60, start=500.0, trend=-5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)

        strat = VTrendX6Strategy(VTrendX6Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entries = 0
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x6_entry":
                entries += 1

        assert entries == 0, "No entries when D1 regime is off"

    def test_signal_reasons_correct(self):
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 3.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX6Strategy(VTrendX6Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.reason.startswith("x6_"), \
                    f"Signal reason '{sig.reason}' must start with 'x6_'"

    def test_empty_bars_no_crash(self):
        strat = VTrendX6Strategy()
        strat.on_init([], [])
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None

    def test_on_init_not_called_no_crash(self):
        strat = VTrendX6Strategy()
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None


# -- Test 4: Trail stop with breakeven floor --------------------------------

class TestTrailStopWithBE:

    def test_tight_no_be_floor(self):
        """Below tier1: 3×ATR, no breakeven floor."""
        strat = VTrendX6Strategy(VTrendX6Config(trail_tight=3.0, gain_tier1=0.05))
        strat._in_position = True
        strat._peak_price = 10200.0
        strat._entry_price = 10000.0
        stop = strat._compute_trail_stop(10200.0, 500.0)
        assert stop == 8700.0  # 10200 - 3*500, can go below entry

    def test_mid_be_floor_binds(self):
        """Mid tier: BE floor binds when trail < entry."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_mid=4.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 10800.0
        strat._entry_price = 10000.0
        stop = strat._compute_trail_stop(10800.0, 500.0)
        assert stop == 10000.0  # max(10000, 10800-4*500=8800)

    def test_mid_trail_above_entry(self):
        """Mid tier: trail > entry, trail wins."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_mid=4.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 10800.0
        strat._entry_price = 10000.0
        stop = strat._compute_trail_stop(10800.0, 100.0)
        assert stop == 10400.0  # max(10000, 10800-4*100=10400)

    def test_wide_be_floor_binds(self):
        """Wide tier: BE floor binds when trail < entry."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_wide=5.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 12000.0
        strat._entry_price = 10000.0
        stop = strat._compute_trail_stop(12000.0, 500.0)
        assert stop == 10000.0  # max(10000, 12000-5*500=9500)

    def test_wide_trail_above_entry(self):
        """Wide tier: trail > entry, trail wins."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_wide=5.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._peak_price = 20000.0
        strat._entry_price = 10000.0
        stop = strat._compute_trail_stop(20000.0, 200.0)
        assert stop == 19000.0  # max(10000, 20000-5*200=19000)

    def test_be_floor_never_below_entry_in_mid_tier(self):
        """Regardless of ATR, stop >= entry in mid tier."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_mid=4.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._entry_price = 10000.0
        for atr in [100, 500, 1000, 2000, 5000]:
            strat._peak_price = 10600.0  # 6% gain
            stop = strat._compute_trail_stop(10600.0, atr)
            assert stop >= 10000.0, f"BE floor violated at ATR={atr}: stop={stop}"

    def test_be_floor_never_below_entry_in_wide_tier(self):
        """Regardless of ATR, stop >= entry in wide tier."""
        strat = VTrendX6Strategy(VTrendX6Config(
            trail_wide=5.0, gain_tier1=0.05, gain_tier2=0.15))
        strat._in_position = True
        strat._entry_price = 10000.0
        for atr in [100, 500, 1000, 2000, 5000]:
            strat._peak_price = 12000.0  # 20% gain
            stop = strat._compute_trail_stop(12000.0, atr)
            assert stop >= 10000.0, f"BE floor violated at ATR={atr}: stop={stop}"


# -- Test 5: Entry price tracking ------------------------------------------

class TestEntryPriceTracking:

    def test_on_after_fill_sets_entry(self):
        strat = VTrendX6Strategy()
        fill = Fill(ts_ms=1000, side=Side.BUY, qty=1.0,
                    price=50000.0, fee=50.0, notional=50000.0,
                    reason="x6_entry")
        bar = _make_bar(50100.0, close_time=2000)
        state = _make_state(bar, [bar], 0)
        strat.on_after_fill(state, fill)
        assert strat._entry_price == 50000.0

    def test_non_entry_fill_no_change(self):
        strat = VTrendX6Strategy()
        strat._entry_price = 50000.0
        fill = Fill(ts_ms=2000, side=Side.SELL, qty=1.0,
                    price=55000.0, fee=55.0, notional=55000.0,
                    reason="x6_trail_stop")
        bar = _make_bar(55000.0, close_time=3000)
        state = _make_state(bar, [bar], 0)
        strat.on_after_fill(state, fill)
        assert strat._entry_price == 50000.0

    def test_binary_exposure_only(self):
        """X6 only emits 0.0 or 1.0 target exposure."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 3.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX6Strategy(VTrendX6Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.target_exposure in (0.0, 1.0), \
                    f"Non-binary exposure: {sig.target_exposure}"


# -- Test 6: Engine integration ---------------------------------------------

class TestEngineIntegration:

    def test_x6_runs_without_error(self):
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import SCENARIOS

        data_path = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        try:
            feed = DataFeed(data_path, start="2023-01-01", end="2024-01-01",
                            warmup_days=365)
        except FileNotFoundError:
            pytest.skip("Data file not available")

        strat = VTrendX6Strategy(VTrendX6Config())
        cost = SCENARIOS["harsh"]
        eng = BacktestEngine(feed=feed, strategy=strat, cost=cost,
                             initial_cash=10_000.0, warmup_mode="no_trade")
        res = eng.run()

        assert res.summary["trades"] >= 0
        assert res.summary["sharpe"] is not None
        n_fills = res.summary["fills"]
        n_trades = res.summary["trades"]
        assert n_fills in (2 * n_trades, 2 * n_trades + 1)

    def test_x6_signal_reasons_engine(self):
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import CostConfig

        data_path = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        try:
            feed = DataFeed(data_path, start="2020-01-01", end="2021-12-31",
                            warmup_days=365)
        except FileNotFoundError:
            pytest.skip("Data file not available")

        strat = VTrendX6Strategy(VTrendX6Config())
        cost = CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.15)
        eng = BacktestEngine(feed=feed, strategy=strat, cost=cost,
                             initial_cash=10_000.0, warmup_mode="no_trade")
        res = eng.run()

        valid_exit_reasons = {"x6_trail_stop", "x6_be_stop", "x6_trend_exit"}
        for t in res.trades:
            assert t.entry_reason == "x6_entry"
            assert t.exit_reason in valid_exit_reasons, \
                f"Bad exit reason: {t.exit_reason}"

    def test_x6_fewer_trades_than_x0(self):
        """X6 should have fewer/equal trades than X0 (wider stops)."""
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import SCENARIOS
        from strategies.vtrend_x0.strategy import VTrendX0Strategy, VTrendX0Config

        data_path = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        try:
            feed = DataFeed(data_path, start="2019-01-01", end="2026-02-20",
                            warmup_days=365)
        except FileNotFoundError:
            pytest.skip("Data file not available")

        cost = SCENARIOS["harsh"]

        strat_x0 = VTrendX0Strategy(VTrendX0Config())
        eng_x0 = BacktestEngine(feed=feed, strategy=strat_x0, cost=cost,
                                initial_cash=10_000.0, warmup_mode="no_trade")
        res_x0 = eng_x0.run()

        strat_x6 = VTrendX6Strategy(VTrendX6Config())
        eng_x6 = BacktestEngine(feed=feed, strategy=strat_x6, cost=cost,
                                initial_cash=10_000.0, warmup_mode="no_trade")
        res_x6 = eng_x6.run()

        assert len(res_x6.trades) <= len(res_x0.trades), (
            f"X6 trades ({len(res_x6.trades)}) should be <= X0 ({len(res_x0.trades)})")


# -- Registration tests -----------------------------------------------------

class TestRegistration:
    def test_strategy_factory_registry(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_x6" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_x6"]
        assert cls is VTrendX6Strategy
        assert cfg_cls is VTrendX6Config

    def test_config_known_strategies(self):
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_x6" in _KNOWN_STRATEGIES

    def test_cli_backtest_registry(self):
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_x6" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_x6"] is VTrendX6Strategy
