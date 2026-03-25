"""Tests for VTREND-X7 crypto-optimised trend-following strategy.

Required tests:
  1. D1 continuity regime uses completed D1 bars only (no future leak)
  2. Config loads from YAML without error
  3. Strategy produces signals matching spec on synthetic data
  4. X7-specific: ratchet trail never widens, cooldown, stretch cap, bands
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from v10.core.types import Bar, MarketState, Signal
from v10.strategies.base import Strategy
from strategies.vtrend_x7.strategy import (
    STRATEGY_ID,
    VTrendX7Config,
    VTrendX7Strategy,
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
        entry_price_avg=0.0,
        position_entry_nav=0.0,
    )


def _make_trending_h4_bars(n: int, start: float = 100.0,
                            trend: float = 0.5) -> list[Bar]:
    bars = []
    for i in range(n):
        c = start + i * trend
        spread = c * 0.001
        bars.append(_make_bar(
            close=c,
            high=c + spread,
            low=c - spread,
            open_=c - trend * 0.3,
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


# -- Test 1: D1 continuity regime no-lookahead ----------------------------

class TestD1RegimeNoLookahead:
    """D1 continuity regime filter must use only completed D1 bars."""

    def test_regime_uses_completed_d1_only(self):
        """H4 bars that arrive BEFORE a D1 bar closes must NOT see that
        D1 bar's regime value."""
        d1_bars = [
            _make_bar(close=100.0, open_time=0, close_time=86_399_999,
                      interval="1d"),
            _make_bar(close=200.0, open_time=86_400_000,
                      close_time=172_799_999, interval="1d"),
        ]

        h4_bars = [
            _make_bar(close=50.0, open_time=0,
                      close_time=14_399_999),
            _make_bar(close=150.0, open_time=86_400_000,
                      close_time=100_799_999),
            _make_bar(close=160.0, open_time=100_800_000,
                      close_time=115_199_999),
            _make_bar(close=190.0, open_time=172_800_000,
                      close_time=187_199_999),
        ]

        strat = VTrendX7Strategy(VTrendX7Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)

        regime = strat._d1_regime_ok
        assert regime is not None
        # With only 2 D1 bars, continuity requires index >= 3 → all False
        assert not np.any(regime), "Too few D1 bars for continuity → all False"

    def test_no_d1_bars_yields_all_false(self):
        h4_bars = _make_trending_h4_bars(50)
        strat = VTrendX7Strategy()
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

        strat = VTrendX7Strategy(VTrendX7Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)
        assert strat._d1_regime_ok[0] == False

    def test_continuity_requires_consecutive_bars(self):
        """Regime needs close[t]>ema[t], close[t-1]>ema[t-1], ema[t]>ema[t-3]."""
        # 10 D1 bars: strong uptrend so continuity should be True for later bars
        d1_bars = _make_d1_bars(10, start=100.0, trend=10.0)
        # Map all H4 bars after D1 completes
        h4_bars = [
            _make_bar(close=200.0, open_time=10 * 86_400_000,
                      close_time=10 * 86_400_000 + 14_399_999),
        ]

        strat = VTrendX7Strategy(VTrendX7Config(d1_ema_period=3))
        strat.on_init(h4_bars, d1_bars)
        regime = strat._d1_regime_ok
        # With 10 bars of strong uptrend and EMA(3), regime should be True
        assert regime[0] == True, "Strong uptrend with continuity → True"


# -- Test 2: Config load from YAML ----------------------------------------

class TestConfigLoad:

    def test_config_loads_from_yaml(self):
        from v10.core.config import load_config
        cfg = load_config("configs/vtrend_x7/vtrend_x7_default.yaml")
        assert cfg.strategy.name == "vtrend_x7"
        assert cfg.strategy.params["slow_period"] == 120.0
        assert cfg.strategy.params["fast_period"] == 30.0
        assert cfg.strategy.params["trail_mult"] == 3.0
        assert cfg.strategy.params["d1_ema_period"] == 21
        assert cfg.strategy.params["trend_entry_band"] == 0.25
        assert cfg.strategy.params["trend_exit_band"] == 0.10
        assert cfg.strategy.params["stretch_cap"] == 1.5
        assert cfg.strategy.params["cooldown_bars"] == 2
        assert cfg.strategy.params["vdo_threshold"] == 0.0

    def test_config_defaults_match_spec(self):
        cfg = VTrendX7Config()
        assert cfg.slow_period == 120.0
        assert cfg.fast_period == 30.0
        assert cfg.trail_mult == 3.0
        assert cfg.d1_ema_period == 21
        assert cfg.trend_entry_band == 0.25
        assert cfg.trend_exit_band == 0.10
        assert cfg.stretch_cap == 1.5
        assert cfg.cooldown_bars == 2
        assert cfg.vdo_threshold == 0.0
        assert cfg.atr_period == 14
        assert cfg.vdo_fast == 12
        assert cfg.vdo_slow == 28

    def test_strategy_id(self):
        assert STRATEGY_ID == "vtrend_x7"
        s = VTrendX7Strategy()
        assert s.name() == "vtrend_x7"

    def test_subclass_of_strategy(self):
        assert issubclass(VTrendX7Strategy, Strategy)

    def test_field_count(self):
        assert len(dataclasses.fields(VTrendX7Config)) == 12


# -- Test 3: Smoke signal test --------------------------------------------

class TestSmokeSignals:

    def test_entry_signal_during_uptrend(self):
        """In a strong uptrend with regime ON, strategy must emit entry."""
        d1_bars = _make_d1_bars(60, start=80.0, trend=5.0)
        h4_bars = []
        for i in range(300):
            c = 100.0 + i * 0.5
            spread = c * 0.001
            h4_ct = (i + 1) * 14_400_000 - 1
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c,
                high=c + spread,
                low=c - spread,
                open_=c - 0.15,
                volume=100.0,
                taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=h4_ct,
            ))

        strat = VTrendX7Strategy(VTrendX7Config(slow_period=20, fast_period=5))
        strat.on_init(h4_bars, d1_bars)

        entries = []
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x7_entry":
                entries.append((i, sig))
                break

        assert len(entries) >= 1, "Must emit entry in strong uptrend"
        assert entries[0][1].target_exposure == 1.0

    def test_exit_signal_after_crash(self):
        """After entry, a crash must trigger trail_stop or soft_exit."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = []
        for i in range(200):
            c = 100.0 + i * 0.5
            spread = c * 0.001
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))
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

        strat = VTrendX7Strategy(VTrendX7Config(slow_period=20, fast_period=5))
        strat.on_init(h4_bars, d1_bars)

        entered = False
        exited = False
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                if sig.reason == "x7_entry":
                    entered = True
                elif sig.reason in ("x7_trail_stop", "x7_soft_exit"):
                    exited = True
                    assert sig.target_exposure == 0.0
                    break

        assert entered, "Must enter during uptrend"
        assert exited, "Must exit during crash"

    def test_no_signal_without_regime(self):
        """When D1 regime is off, no entry should occur."""
        d1_bars = _make_d1_bars(60, start=500.0, trend=-5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)

        strat = VTrendX7Strategy(VTrendX7Config(slow_period=20, fast_period=5))
        strat.on_init(h4_bars, d1_bars)

        entries = 0
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x7_entry":
                entries += 1

        assert entries == 0, "No entries when D1 regime is off"

    def test_signal_reasons_correct(self):
        """All signal reasons must start with 'x7_'."""
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

        strat = VTrendX7Strategy(VTrendX7Config(slow_period=20, fast_period=5))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.reason.startswith("x7_"), \
                    f"Signal reason '{sig.reason}' must start with 'x7_'"

    def test_empty_bars_no_crash(self):
        strat = VTrendX7Strategy()
        strat.on_init([], [])
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None

    def test_on_init_not_called_no_crash(self):
        strat = VTrendX7Strategy()
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None


# -- Test 4: X7-specific mechanics ----------------------------------------

class TestX7Mechanics:

    def test_ratchet_trail_never_widens(self):
        """Trail stop must never decrease even when ATR increases."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        # Uptrend then plateau with increasing volatility
        h4_bars = []
        for i in range(200):
            c = 100.0 + i * 0.5
            spread = c * 0.001
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))
        # Wide-range bars (ATR increases) but price stays flat
        last_close = h4_bars[-1].close
        for i in range(30):
            c = last_close + (i % 2) * 2 - 1  # oscillate around last_close
            h4_bars.append(_make_bar(
                close=c, high=c + 20.0, low=c - 20.0,
                open_=c, volume=100.0, taker_buy=60.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX7Strategy(VTrendX7Config(slow_period=20, fast_period=5))
        strat.on_init(h4_bars, d1_bars)

        entered = False
        trail_history = []
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x7_entry":
                entered = True
            if entered and strat._in_position:
                trail_history.append(strat._trail_stop)

        if len(trail_history) > 1:
            for j in range(1, len(trail_history)):
                assert trail_history[j] >= trail_history[j - 1], \
                    f"Trail stop widened at step {j}: {trail_history[j]} < {trail_history[j-1]}"

    def test_cooldown_blocks_immediate_reentry(self):
        """After exit, entry must not happen for cooldown_bars H4 bars."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = []
        # Strong uptrend
        for i in range(150):
            c = 100.0 + i * 0.5
            spread = c * 0.001
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))
        # Sharp drop to trigger exit
        last_close = h4_bars[-1].close
        for i in range(10):
            c = last_close - (i + 1) * 10.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_=c + 5.0, volume=100.0, taker_buy=20.0,
                open_time=(150 + i) * 14_400_000,
                close_time=(151 + i) * 14_400_000 - 1,
            ))
        # Resume uptrend
        resume_start = h4_bars[-1].close
        for i in range(100):
            c = resume_start + i * 0.5
            spread = c * 0.001
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=(160 + i) * 14_400_000,
                close_time=(161 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX7Strategy(VTrendX7Config(
            slow_period=20, fast_period=5, cooldown_bars=2,
        ))
        strat.on_init(h4_bars, d1_bars)

        exit_bar = None
        reentry_bar = None
        entered = False
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                if sig.reason == "x7_entry":
                    if entered and exit_bar is not None:
                        reentry_bar = i
                        break
                    entered = True
                elif sig.reason in ("x7_trail_stop", "x7_soft_exit"):
                    exit_bar = i

        if exit_bar is not None and reentry_bar is not None:
            gap = reentry_bar - exit_bar
            assert gap >= 2, \
                f"Re-entry at bar {reentry_bar} is {gap} bars after exit at {exit_bar}, need >= 2"


# -- Registration tests ----------------------------------------------------

class TestRegistration:
    def test_strategy_factory_registry(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_x7" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_x7"]
        assert cls is VTrendX7Strategy
        assert cfg_cls is VTrendX7Config

    def test_config_known_strategies(self):
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_x7" in _KNOWN_STRATEGIES

    def test_cli_backtest_registry(self):
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_x7" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_x7"] is VTrendX7Strategy
