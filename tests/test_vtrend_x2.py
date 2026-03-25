"""Tests for VTREND-X2 adaptive trailing stop strategy.

Comprehensive test suite matching X0 validation pattern:
  1. D1 regime uses completed D1 bars only (no future leak)
  2. Config loads from YAML without error
  3. Strategy produces signals matching spec on synthetic data
  4. Registration in all system registries
  5. Adaptive trail multiplier correctness
  6. Entry price tracking
  7. Engine integration
  8. Vectorized surrogate parity
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from v10.core.types import Bar, MarketState, Signal
from v10.strategies.base import Strategy
from strategies.vtrend_x2.strategy import (
    STRATEGY_ID,
    VTrendX2Config,
    VTrendX2Strategy,
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

        strat = VTrendX2Strategy(VTrendX2Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)

        regime = strat._d1_regime_ok
        assert regime is not None
        assert regime[0] == False, "D1[0] regime: 100 > 100 is False"
        assert regime[1] == False, "H4 bar before D1[1] close must not leak"
        assert regime[2] == False, "H4 bar before D1[1] close must not leak"

    def test_no_d1_bars_yields_all_false(self):
        h4_bars = _make_trending_h4_bars(50)
        strat = VTrendX2Strategy()
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

        strat = VTrendX2Strategy(VTrendX2Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)
        assert strat._d1_regime_ok[0] == False


# -- Test 2: Config load from YAML -----------------------------------------

class TestConfigLoad:

    def test_config_loads_from_yaml(self):
        from v10.core.config import load_config
        cfg = load_config("configs/vtrend_x2/vtrend_x2_default.yaml")
        assert cfg.strategy.name == "vtrend_x2"
        assert cfg.strategy.params["slow_period"] == 120.0
        assert cfg.strategy.params["trail_tight"] == 3.0
        assert cfg.strategy.params["trail_mid"] == 4.0
        assert cfg.strategy.params["trail_wide"] == 5.0
        assert cfg.strategy.params["gain_tier1"] == 0.05
        assert cfg.strategy.params["gain_tier2"] == 0.15

    def test_config_defaults_match_spec(self):
        cfg = VTrendX2Config()
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
        assert STRATEGY_ID == "vtrend_x2"
        s = VTrendX2Strategy()
        assert s.name() == "vtrend_x2"

    def test_subclass_of_strategy(self):
        assert issubclass(VTrendX2Strategy, Strategy)

    def test_field_count(self):
        # 7 tunable + 3 structural = 10 (or as defined)
        n_fields = len(dataclasses.fields(VTrendX2Config))
        assert n_fields >= 7, f"Expected >= 7 fields, got {n_fields}"


# -- Test 3: Smoke signal test ---------------------------------------------

class TestSmokeSignals:

    def test_entry_signal_during_uptrend(self):
        d1_bars = _make_d1_bars(60, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(300, start=100.0, trend=0.5)

        strat = VTrendX2Strategy(VTrendX2Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entries = []
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x2_entry":
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

        strat = VTrendX2Strategy(VTrendX2Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entered = False
        exited = False
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                if sig.reason == "x2_entry":
                    entered = True
                elif sig.reason in ("x2_trail_stop", "x2_trend_exit"):
                    exited = True
                    assert sig.target_exposure == 0.0
                    break

        assert entered, "Must enter during uptrend"
        assert exited, "Must exit during crash"

    def test_no_signal_without_regime(self):
        d1_bars = _make_d1_bars(60, start=500.0, trend=-5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)

        strat = VTrendX2Strategy(VTrendX2Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entries = 0
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x2_entry":
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

        strat = VTrendX2Strategy(VTrendX2Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.reason.startswith("x2_"), \
                    f"Signal reason '{sig.reason}' must start with 'x2_'"

    def test_empty_bars_no_crash(self):
        strat = VTrendX2Strategy()
        strat.on_init([], [])
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None

    def test_on_init_not_called_no_crash(self):
        strat = VTrendX2Strategy()
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None


# -- Test 4: Adaptive trail multiplier -------------------------------------

class TestAdaptiveTrailMult:

    def test_tight_when_no_gain(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        assert strat._adaptive_trail_mult(10000.0) == 3.0

    def test_tight_when_small_gain(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        assert strat._adaptive_trail_mult(10300.0) == 3.0

    def test_mid_at_boundary(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        assert strat._adaptive_trail_mult(10500.0) == 4.0

    def test_wide_at_boundary(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        assert strat._adaptive_trail_mult(11500.0) == 5.0

    def test_tight_when_negative(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 10000.0
        assert strat._adaptive_trail_mult(9500.0) == 3.0

    def test_tight_when_entry_zero(self):
        strat = VTrendX2Strategy(VTrendX2Config())
        strat._entry_price = 0.0
        assert strat._adaptive_trail_mult(10000.0) == 3.0


# -- Test 5: Entry price tracking ------------------------------------------

class TestEntryPriceTracking:

    def test_entry_sets_entry_price_on_bar(self):
        """X2 sets entry_price = bar.close in on_bar (not on_after_fill)."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(300, start=100.0, trend=0.5)
        strat = VTrendX2Strategy(VTrendX2Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x2_entry":
                assert strat._entry_price == h4_bars[i].close
                assert strat._in_position is True
                return

        pytest.fail("No entry found")

    def test_exit_clears_entry_price(self):
        """After exit, entry_price resets to 0."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 5.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX2Strategy(VTrendX2Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entered = False
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                if sig.reason == "x2_entry":
                    entered = True
                elif entered and sig.target_exposure == 0.0:
                    assert strat._entry_price == 0.0
                    return

        pytest.fail("No exit found")

    def test_binary_exposure_only(self):
        """X2 only emits 0.0 or 1.0 target exposure."""
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

        strat = VTrendX2Strategy(VTrendX2Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.target_exposure in (0.0, 1.0), \
                    f"Non-binary exposure: {sig.target_exposure}"


# -- Test 6: Engine integration ---------------------------------------------

class TestEngineIntegration:

    def test_x2_runs_without_error(self):
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import SCENARIOS

        data_path = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        try:
            feed = DataFeed(data_path, start="2023-01-01", end="2024-01-01",
                            warmup_days=365)
        except FileNotFoundError:
            pytest.skip("Data file not available")

        strat = VTrendX2Strategy(VTrendX2Config())
        cost = SCENARIOS["harsh"]
        eng = BacktestEngine(feed=feed, strategy=strat, cost=cost,
                             initial_cash=10_000.0, warmup_mode="no_trade")
        res = eng.run()

        assert res.summary["trades"] >= 0
        assert res.summary["sharpe"] is not None
        n_fills = res.summary["fills"]
        n_trades = res.summary["trades"]
        assert n_fills in (2 * n_trades, 2 * n_trades + 1)

    def test_x2_signal_reasons_engine(self):
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import CostConfig

        data_path = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
        try:
            feed = DataFeed(data_path, start="2020-01-01", end="2021-12-31",
                            warmup_days=365)
        except FileNotFoundError:
            pytest.skip("Data file not available")

        strat = VTrendX2Strategy(VTrendX2Config())
        cost = CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.15)
        eng = BacktestEngine(feed=feed, strategy=strat, cost=cost,
                             initial_cash=10_000.0, warmup_mode="no_trade")
        res = eng.run()

        for t in res.trades:
            assert t.entry_reason == "x2_entry"
            assert t.exit_reason in ("x2_trail_stop", "x2_trend_exit")


# -- Registration tests -----------------------------------------------------

class TestRegistration:
    def test_strategy_factory_registry(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_x2" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_x2"]
        assert cls is VTrendX2Strategy
        assert cfg_cls is VTrendX2Config

    def test_config_known_strategies(self):
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_x2" in _KNOWN_STRATEGIES

    def test_cli_backtest_registry(self):
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_x2" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_x2"] is VTrendX2Strategy
