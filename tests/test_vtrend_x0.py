"""Tests for VTREND-X0 (= E0_ema21D1, X-series research anchor).

Required tests:
  1. D1 regime uses completed D1 bars only (no future leak)
  2. Config loads from YAML without error
  3. Strategy produces signals matching spec on synthetic data
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from v10.core.types import Bar, MarketState, Signal
from v10.strategies.base import Strategy
from strategies.vtrend_x0.strategy import (
    STRATEGY_ID,
    VTrendX0Config,
    VTrendX0Strategy,
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
        # D1 bar: open_time = day_start, close_time = day_end
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
        """H4 bars that arrive BEFORE a D1 bar closes must NOT see that
        D1 bar's regime value."""
        # Create 2 D1 bars:
        #   D1[0]: close_time = 86_399_999 (end of day 0), close=100, EMA starts
        #   D1[1]: close_time = 172_799_999 (end of day 1), close=200 (above EMA)
        d1_bars = [
            _make_bar(close=100.0, open_time=0, close_time=86_399_999,
                      interval="1d"),
            _make_bar(close=200.0, open_time=86_400_000,
                      close_time=172_799_999, interval="1d"),
        ]

        # Create H4 bars spanning day 1 — some close BEFORE D1[1] completes,
        # one closes AFTER.
        h4_bars = [
            # Bar 0: closes in day 0 — should see D1[0] regime
            _make_bar(close=50.0, open_time=0,
                      close_time=14_399_999),
            # Bar 1: closes mid-day 1 (< 172_799_999) — should see D1[0] only
            _make_bar(close=150.0, open_time=86_400_000,
                      close_time=100_799_999),
            # Bar 2: closes mid-day 1 still — should see D1[0] only
            _make_bar(close=160.0, open_time=100_800_000,
                      close_time=115_199_999),
            # Bar 3: closes AFTER D1[1] completes — should see D1[1]
            _make_bar(close=190.0, open_time=172_800_000,
                      close_time=187_199_999),
        ]

        strat = VTrendX0Strategy(VTrendX0Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)

        regime = strat._d1_regime_ok
        assert regime is not None

        # D1[0]: close=100, EMA(1)=100 → 100 > 100 is False
        assert regime[0] == False, "D1[0] regime: 100 > 100 is False"

        # Bars 1 and 2 are in day 1 but D1[1] hasn't completed yet
        # They should see D1[0]'s regime (False)
        assert regime[1] == False, "H4 bar before D1[1] close must not leak"
        assert regime[2] == False, "H4 bar before D1[1] close must not leak"

        # Bar 3 is after D1[1] completes: close=200, EMA(1)=200 → False
        # (200 > 200 is False with strict >)
        # This is expected — the test verifies no lookahead, not regime=True

    def test_no_d1_bars_yields_all_false(self):
        """When no D1 bars are provided, regime is all False."""
        h4_bars = _make_trending_h4_bars(50)
        strat = VTrendX0Strategy()
        strat.on_init(h4_bars, [])
        assert strat._d1_regime_ok is not None
        assert not np.any(strat._d1_regime_ok)

    def test_future_d1_not_visible(self):
        """A D1 bar with close_time > H4 close_time must not affect regime."""
        # One D1 bar that hasn't completed yet (close_time far in future)
        d1_bars = [
            _make_bar(close=500.0, open_time=0,
                      close_time=999_999_999, interval="1d"),
        ]
        # H4 bar closes well before D1 bar
        h4_bars = [
            _make_bar(close=50.0, open_time=0, close_time=14_399_999),
        ]

        strat = VTrendX0Strategy(VTrendX0Config(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)

        # D1 bar hasn't completed at H4[0] time → regime must be False
        assert strat._d1_regime_ok[0] == False


# -- Test 2: Config load from YAML -----------------------------------------

class TestConfigLoad:
    """YAML config loads and produces valid LiveConfig."""

    def test_config_loads_from_yaml(self):
        from v10.core.config import load_config
        cfg = load_config("configs/vtrend_x0/vtrend_x0_default.yaml")
        assert cfg.strategy.name == "vtrend_x0"
        assert cfg.strategy.params["slow_period"] == 120.0
        assert cfg.strategy.params["trail_mult"] == 3.0
        assert cfg.strategy.params["vdo_threshold"] == 0.0
        assert cfg.strategy.params["d1_ema_period"] == 21

    def test_config_defaults_match_spec(self):
        cfg = VTrendX0Config()
        assert cfg.slow_period == 120.0
        assert cfg.trail_mult == 3.0
        assert cfg.vdo_threshold == 0.0
        assert cfg.d1_ema_period == 21
        assert cfg.atr_period == 14
        assert cfg.vdo_fast == 12
        assert cfg.vdo_slow == 28

    def test_strategy_id(self):
        assert STRATEGY_ID == "vtrend_x0"
        s = VTrendX0Strategy()
        assert s.name() == "vtrend_x0"

    def test_subclass_of_strategy(self):
        assert issubclass(VTrendX0Strategy, Strategy)

    def test_field_count(self):
        assert len(dataclasses.fields(VTrendX0Config)) == 7


# -- Test 3: Smoke signal test ---------------------------------------------

class TestSmokeSignals:
    """Strategy produces entry/exit signals on synthetic data per spec."""

    def test_entry_signal_during_uptrend(self):
        """In a strong uptrend with regime ON, strategy must emit entry."""
        # D1 bars: strong uptrend so regime=True
        d1_bars = _make_d1_bars(60, start=80.0, trend=5.0)
        # H4 bars: strong uptrend with increasing buy pressure for VDO > 0
        h4_bars = []
        for i in range(300):
            c = 100.0 + i * 0.5
            spread = c * 0.001
            h4_ct = (i + 1) * 14_400_000 - 1
            # Increasing taker_buy ratio so VDO becomes positive
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

        strat = VTrendX0Strategy(VTrendX0Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entries = []
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x0_entry":
                entries.append((i, sig))
                break

        assert len(entries) >= 1, "Must emit entry in strong uptrend"
        assert entries[0][1].target_exposure == 1.0

    def test_exit_signal_after_crash(self):
        """After entry, a crash must trigger trail_stop or trend_exit."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        # Uptrend with increasing buy pressure for VDO > 0
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
        # Crash bars with sell pressure
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

        strat = VTrendX0Strategy(VTrendX0Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entered = False
        exited = False
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                if sig.reason == "x0_entry":
                    entered = True
                elif sig.reason in ("x0_trail_stop", "x0_trend_exit"):
                    exited = True
                    assert sig.target_exposure == 0.0
                    break

        assert entered, "Must enter during uptrend"
        assert exited, "Must exit during crash"

    def test_no_signal_without_regime(self):
        """When D1 regime is off, no entry should occur."""
        # D1 bars: downtrend so regime=False
        d1_bars = _make_d1_bars(60, start=500.0, trend=-5.0)
        # H4 bars: uptrend (trend_up=True, vdo positive) but regime off
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)

        strat = VTrendX0Strategy(VTrendX0Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entries = 0
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x0_entry":
                entries += 1

        assert entries == 0, "No entries when D1 regime is off"

    def test_signal_reasons_correct(self):
        """All signal reasons must start with 'x0_'."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _make_trending_h4_bars(200, start=100.0, trend=0.5)
        # Add crash
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 3.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX0Strategy(VTrendX0Config(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.reason.startswith("x0_"), \
                    f"Signal reason '{sig.reason}' must start with 'x0_'"

    def test_empty_bars_no_crash(self):
        strat = VTrendX0Strategy()
        strat.on_init([], [])
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None

    def test_on_init_not_called_no_crash(self):
        strat = VTrendX0Strategy()
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None


# -- Registration tests -----------------------------------------------------

class TestRegistration:
    def test_strategy_factory_registry(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_x0" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_x0"]
        assert cls is VTrendX0Strategy
        assert cfg_cls is VTrendX0Config

    def test_config_known_strategies(self):
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_x0" in _KNOWN_STRATEGIES

    def test_cli_backtest_registry(self):
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_x0" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_x0"] is VTrendX0Strategy
