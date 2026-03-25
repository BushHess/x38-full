"""Tests for VTREND-X0-E5EXIT (E0_ema21D1 entry + E5 robust ATR exit, ≈ E5_ema21D1).

Required tests:
  1. D1 regime uses completed D1 bars only (no future leak)
  2. Config loads from YAML without error
  3. Entry logic identical to E0_ema21D1 (vtrend_x0)
  4. Exit uses robust ATR (E5 semantics)
  5. Registration in all integration points
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from v10.core.types import Bar, MarketState, Signal
from v10.strategies.base import Strategy
from strategies.vtrend_x0_e5exit.strategy import (
    STRATEGY_ID,
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
    _ema,
    _robust_atr,
)


# -- Helpers (shared with vtrend_x0 tests) ---------------------------------

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


def _make_d1_bars(n: int, start: float = 100.0,
                   trend: float = 3.0) -> list[Bar]:
    bars = []
    for i in range(n):
        c = start + i * trend
        spread = c * 0.002
        bars.append(_make_bar(
            close=c, high=c + spread, low=c - spread,
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
            _make_bar(close=100.0, open_time=0, close_time=86_399_999, interval="1d"),
            _make_bar(close=200.0, open_time=86_400_000, close_time=172_799_999, interval="1d"),
        ]
        h4_bars = [
            _make_bar(close=50.0, open_time=0, close_time=14_399_999),
            _make_bar(close=150.0, open_time=86_400_000, close_time=100_799_999),
            _make_bar(close=160.0, open_time=100_800_000, close_time=115_199_999),
            _make_bar(close=190.0, open_time=172_800_000, close_time=187_199_999),
        ]

        strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig(d1_ema_period=1))
        strat.on_init(h4_bars, d1_bars)
        regime = strat._d1_regime_ok
        assert regime is not None
        assert regime[0] == False
        assert regime[1] == False
        assert regime[2] == False

    def test_no_d1_bars_yields_all_false(self):
        h4_bars = [_make_bar(close=100.0 + i, open_time=i * 14_400_000,
                             close_time=(i + 1) * 14_400_000 - 1) for i in range(50)]
        strat = VTrendX0E5ExitStrategy()
        strat.on_init(h4_bars, [])
        assert strat._d1_regime_ok is not None
        assert not np.any(strat._d1_regime_ok)


# -- Test 2: Config & identity ---------------------------------------------

class TestConfigLoad:

    def test_config_loads_from_yaml(self):
        from v10.core.config import load_config
        cfg = load_config("configs/vtrend_x0_e5exit/vtrend_x0_e5exit_default.yaml")
        assert cfg.strategy.name == "vtrend_x0_e5exit"
        assert cfg.strategy.params["slow_period"] == 120.0
        assert cfg.strategy.params["trail_mult"] == 3.0

    def test_config_defaults_match_spec(self):
        cfg = VTrendX0E5ExitConfig()
        # Tunable (same as E0_ema21D1 / vtrend_x0)
        assert cfg.slow_period == 120.0
        assert cfg.trail_mult == 3.0
        assert cfg.vdo_threshold == 0.0
        assert cfg.d1_ema_period == 21
        # Structural (E5-style: no atr_period, uses ratr_period instead)
        assert cfg.vdo_fast == 12
        assert cfg.vdo_slow == 28
        # NEW: Robust ATR params (from E5)
        assert cfg.ratr_cap_q == 0.90
        assert cfg.ratr_cap_lb == 100
        assert cfg.ratr_period == 20

    def test_strategy_id(self):
        assert STRATEGY_ID == "vtrend_x0_e5exit"
        s = VTrendX0E5ExitStrategy()
        assert s.name() == "vtrend_x0_e5exit"

    def test_subclass_of_strategy(self):
        assert issubclass(VTrendX0E5ExitStrategy, Strategy)

    def test_field_count(self):
        assert len(dataclasses.fields(VTrendX0E5ExitConfig)) == 9


# -- Test 3: Entry logic identical to E0_ema21D1 (vtrend_x0) ---------------

class TestEntryParity:
    """Entry conditions must be identical to E0_ema21D1 (vtrend_x0)."""

    def test_entry_requires_regime_and_trend_and_vdo(self):
        """Entry fires only when all 3 conditions met: regime + trend + VDO."""
        d1_bars = _make_d1_bars(60, start=80.0, trend=5.0)
        h4_bars = []
        for i in range(300):
            c = 100.0 + i * 0.5
            spread = c * 0.001
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))

        strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig(slow_period=20))
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

    def test_no_entry_without_regime(self):
        """When D1 regime is off, no entry should occur."""
        d1_bars = _make_d1_bars(60, start=500.0, trend=-5.0)
        h4_bars = []
        for i in range(200):
            c = 100.0 + i * 0.5
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c * 1.001, low=c * 0.999,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))

        strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        entries = 0
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x0_entry":
                entries += 1

        assert entries == 0

    def test_signal_reasons_use_x0_prefix(self):
        """All signal reasons must start with 'x0_'."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = []
        for i in range(200):
            c = 100.0 + i * 0.5
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c * 1.001, low=c * 0.999,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))
        # Crash
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 5.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_=c + 2.0, volume=100.0, taker_buy=20.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                assert sig.reason.startswith("x0_"), \
                    f"Signal reason '{sig.reason}' must start with 'x0_'"


# -- Test 4: Exit uses robust ATR (E5 semantics) ---------------------------

class TestRobustATRExit:
    """Exit trail must use _robust_atr, not standard _atr."""

    def test_robust_atr_produces_valid_output(self):
        """_robust_atr returns NaN[:119] and valid values after."""
        n = 300
        close = 100.0 + np.arange(n, dtype=np.float64) * 0.5
        high = close * 1.01
        low = close * 0.99
        ratr = _robust_atr(high, low, close, cap_q=0.90, cap_lb=100, period=20)
        assert len(ratr) == n
        # First 119 bars should be NaN (cap_lb + period - 1 = 119)
        assert np.all(np.isnan(ratr[:119]))
        # Bar 119 onward should be valid
        assert not np.isnan(ratr[119])
        assert np.all(np.isfinite(ratr[119:]))

    def test_strategy_uses_ratr_not_atr(self):
        """Strategy must have _ratr attribute, not _atr."""
        d1_bars = _make_d1_bars(60, start=80.0, trend=5.0)
        h4_bars = []
        for i in range(200):
            c = 100.0 + i * 0.5
            h4_bars.append(_make_bar(
                close=c, high=c * 1.01, low=c * 0.99,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))

        strat = VTrendX0E5ExitStrategy()
        strat.on_init(h4_bars, d1_bars)

        assert strat._ratr is not None
        assert not hasattr(strat, '_atr') or strat.__dict__.get('_atr') is None

    def test_exit_after_crash(self):
        """Trail stop or trend exit fires after crash."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = []
        for i in range(200):
            c = 100.0 + i * 0.5
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c * 1.001, low=c * 0.999,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 5.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_=c + 2.0, volume=100.0, taker_buy=20.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig(slow_period=20))
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

    def test_empty_bars_no_crash(self):
        strat = VTrendX0E5ExitStrategy()
        strat.on_init([], [])
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strat.on_bar(state) is None


# -- Test 5: Registration --------------------------------------------------

class TestRegistration:
    def test_strategy_factory_registry(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_x0_e5exit" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_x0_e5exit"]
        assert cls is VTrendX0E5ExitStrategy
        assert cfg_cls is VTrendX0E5ExitConfig

    def test_config_known_strategies(self):
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_x0_e5exit" in _KNOWN_STRATEGIES

    def test_cli_backtest_registry(self):
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_x0_e5exit" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_x0_e5exit"] is VTrendX0E5ExitStrategy
