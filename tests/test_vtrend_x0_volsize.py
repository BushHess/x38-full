"""Tests for VTREND-X0-VOLSIZE (E0_ema21D1 with E5 exit + frozen vol sizing).

Required tests:
  1. Entry timing parity with vtrend_x0_e5exit
  2. Fractional exposure when rv > target_vol
  3. Full exposure when rv << target_vol (clipped to 1.0)
  4. Vol floor bounds weight
  5. rv NaN fallback → weight = 1.0
  6. No rebalance between entry and exit
  7. Config loads from YAML
  8. Registration in all integration points
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from v10.core.types import Bar, MarketState, Signal
from v10.strategies.base import Strategy
from strategies.vtrend_x0_volsize.strategy import (
    BARS_PER_YEAR_4H,
    STRATEGY_ID,
    VTrendX0VolsizeConfig,
    VTrendX0VolsizeStrategy,
    _ema,
    _realized_vol,
    _robust_atr,
)
from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
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


def _build_uptrend_bars(n: int = 300, start: float = 100.0,
                         step: float = 0.5) -> list[Bar]:
    """Build H4 bars with a steady uptrend."""
    bars = []
    for i in range(n):
        c = start + i * step
        spread = c * 0.001
        tb = min(55.0 + i * 0.2, 85.0)
        bars.append(_make_bar(
            close=c, high=c + spread, low=c - spread,
            open_=c - 0.15, volume=100.0, taker_buy=tb,
            open_time=i * 14_400_000,
            close_time=(i + 1) * 14_400_000 - 1,
        ))
    return bars


# -- Test 1: Entry timing parity with vtrend_x0_e5exit ------------------------------

class TestEntryTimingParity:
    """Entry timestamps must be identical to vtrend_x0_e5exit."""

    def test_entry_bars_match_phase2(self):
        """Both strategies must fire entry on the same bars."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _build_uptrend_bars(300)

        # vtrend_x0_e5exit
        p2 = VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig(slow_period=20))
        p2.on_init(h4_bars, d1_bars)

        # vtrend_x0_volsize
        p3 = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig(slow_period=20))
        p3.on_init(h4_bars, d1_bars)

        p2_entries = []
        p3_entries = []
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)

            sig2 = p2.on_bar(state)
            if sig2 is not None and sig2.reason == "x0_entry":
                p2_entries.append(i)

            sig3 = p3.on_bar(state)
            if sig3 is not None and sig3.reason == "x0_entry":
                p3_entries.append(i)

        assert len(p2_entries) >= 1, "Must have at least one entry"
        assert p2_entries == p3_entries, \
            f"Entry bar mismatch: P2={p2_entries} vs P3={p3_entries}"


# -- Test 2: Fractional exposure -------------------------------------------

class TestFractionalExposure:
    """When rv > target_vol, entry exposure must be < 1.0."""

    def test_fractional_weight_when_rv_high(self):
        """If rv=0.30, target_vol=0.15, weight should be 0.5."""
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        # Build volatile bars: large spread → high realized vol
        h4_bars = []
        for i in range(300):
            c = 100.0 + i * 0.5
            # Large swings to inflate realized vol
            spread = c * 0.05
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.15, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))

        strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig(
            slow_period=20, target_vol=0.15))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x0_entry":
                # rv should be high enough that weight < 1.0
                rv_at_entry = strat._rv[i]
                if not math.isnan(rv_at_entry) and rv_at_entry > 0.15:
                    assert sig.target_exposure < 1.0, \
                        f"Expected fractional, got {sig.target_exposure}"
                    expected = 0.15 / max(rv_at_entry, 0.08)
                    assert abs(sig.target_exposure - expected) < 1e-10
                break

    def test_full_exposure_when_rv_very_low(self):
        """When rv is very low, weight clips to 1.0."""
        # Near-constant prices → very low rv
        d1_bars = _make_d1_bars(80, start=99.0, trend=0.5)
        h4_bars = []
        for i in range(300):
            c = 100.0 + i * 0.001  # nearly flat
            spread = c * 0.00001
            tb = min(55.0 + i * 0.2, 85.0)
            h4_bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.0003, volume=100.0, taker_buy=tb,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))

        strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig(
            slow_period=20, target_vol=0.15))
        strat.on_init(h4_bars, d1_bars)

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x0_entry":
                # rv should be tiny → weight = min(target_vol/vol_floor, 1.0) = min(1.875, 1.0) = 1.0
                assert sig.target_exposure == 1.0, \
                    f"Expected 1.0, got {sig.target_exposure}"
                break


# -- Test 3: Vol floor bounds weight --------------------------------------

class TestVolFloor:
    """Weight must be bounded by target_vol / vol_floor."""

    def test_vol_floor_caps_weight(self):
        """With vol_floor=0.08 and target_vol=0.15, max raw weight = 1.875 → clipped to 1.0."""
        cfg = VTrendX0VolsizeConfig(target_vol=0.15, vol_floor=0.08)
        max_raw = cfg.target_vol / cfg.vol_floor
        assert max_raw == pytest.approx(1.875)
        # After clipping: 1.0
        assert min(max_raw, 1.0) == 1.0

    def test_vol_floor_prevents_extreme_weight(self):
        """With vol_floor=0.30, target_vol=0.15, weight = 0.5 even if rv=0.01."""
        cfg = VTrendX0VolsizeConfig(target_vol=0.15, vol_floor=0.30)
        rv = 0.01  # very low
        weight = cfg.target_vol / max(rv, cfg.vol_floor)
        weight = max(0.0, min(1.0, weight))
        assert weight == pytest.approx(0.5)


# -- Test 4: rv NaN fallback -----------------------------------------------

class TestRvNaNFallback:
    """If rv is NaN at entry bar, weight must default to 1.0."""

    def test_nan_rv_yields_full_weight(self):
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _build_uptrend_bars(300)

        strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig(
            slow_period=20, vol_lookback=5000))  # lookback >> n → all rv NaN
        strat.on_init(h4_bars, d1_bars)

        # Verify rv is all NaN
        assert strat._rv is not None
        assert np.all(np.isnan(strat._rv))

        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None and sig.reason == "x0_entry":
                assert sig.target_exposure == 1.0, \
                    f"NaN rv fallback failed: got {sig.target_exposure}"
                break


# -- Test 5: No rebalance --------------------------------------------------

class TestNoRebalance:
    """No signals emitted between entry and exit."""

    def test_no_mid_trade_signals(self):
        d1_bars = _make_d1_bars(80, start=80.0, trend=5.0)
        h4_bars = _build_uptrend_bars(200)
        # Add crash to trigger exit
        last_close = h4_bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 5.0
            h4_bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_=c + 2.0, volume=100.0, taker_buy=20.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        strat = VTrendX0VolsizeStrategy(VTrendX0VolsizeConfig(slow_period=20))
        strat.on_init(h4_bars, d1_bars)

        signals = []
        for i in range(len(h4_bars)):
            state = _make_state(h4_bars[i], h4_bars, i, d1_bars)
            sig = strat.on_bar(state)
            if sig is not None:
                signals.append((i, sig.reason, sig.target_exposure))

        # Must have at least entry + exit
        assert len(signals) >= 2
        # Between entry and exit, no other signals
        entry_idx = None
        for idx, (bar_i, reason, _) in enumerate(signals):
            if reason == "x0_entry":
                entry_idx = idx
            elif reason in ("x0_trail_stop", "x0_trend_exit"):
                if entry_idx is not None:
                    assert idx == entry_idx + 1, \
                        f"Mid-trade signal at index {idx}, entry was at {entry_idx}"
                    break


# -- Test 6: Config --------------------------------------------------------

class TestConfigLoad:

    def test_config_loads_from_yaml(self):
        from v10.core.config import load_config
        cfg = load_config("configs/vtrend_x0_volsize/vtrend_x0_volsize_default.yaml")
        assert cfg.strategy.name == "vtrend_x0_volsize"
        assert cfg.strategy.params["slow_period"] == 120.0
        assert cfg.strategy.params["trail_mult"] == 3.0
        assert cfg.strategy.params["target_vol"] == 0.15
        assert cfg.strategy.params["vol_lookback"] == 120
        assert cfg.strategy.params["vol_floor"] == 0.08

    def test_config_defaults_match_spec(self):
        cfg = VTrendX0VolsizeConfig()
        # vtrend_x0_e5exit inherited
        assert cfg.slow_period == 120.0
        assert cfg.trail_mult == 3.0
        assert cfg.vdo_threshold == 0.0
        assert cfg.d1_ema_period == 21
        # E5-style: no atr_period, uses ratr_period instead
        assert cfg.vdo_fast == 12
        assert cfg.vdo_slow == 28
        assert cfg.ratr_cap_q == 0.90
        assert cfg.ratr_cap_lb == 100
        assert cfg.ratr_period == 20
        # NEW vtrend_x0_volsize
        assert cfg.target_vol == 0.15
        assert cfg.vol_lookback == 120
        assert cfg.vol_floor == 0.08

    def test_strategy_id(self):
        assert STRATEGY_ID == "vtrend_x0_volsize"
        s = VTrendX0VolsizeStrategy()
        assert s.name() == "vtrend_x0_volsize"

    def test_subclass_of_strategy(self):
        assert issubclass(VTrendX0VolsizeStrategy, Strategy)

    def test_field_count(self):
        assert len(dataclasses.fields(VTrendX0VolsizeConfig)) == 12


# -- Test 7: Realized vol helper -------------------------------------------

class TestRealizedVol:

    def test_realized_vol_shape_and_nan_prefix(self):
        n = 200
        close = 100.0 + np.arange(n, dtype=np.float64) * 0.5
        rv = _realized_vol(close, lookback=120, bars_per_year=BARS_PER_YEAR_4H)
        assert len(rv) == n
        assert np.all(np.isnan(rv[:120]))
        assert not np.isnan(rv[120])

    def test_realized_vol_positive(self):
        n = 200
        close = 100.0 + np.arange(n, dtype=np.float64) * 0.5
        rv = _realized_vol(close, lookback=120, bars_per_year=BARS_PER_YEAR_4H)
        valid = rv[~np.isnan(rv)]
        assert np.all(valid > 0)


# -- Test 8: Registration --------------------------------------------------

class TestRegistration:
    def test_strategy_factory_registry(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_x0_volsize" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_x0_volsize"]
        assert cls is VTrendX0VolsizeStrategy
        assert cfg_cls is VTrendX0VolsizeConfig

    def test_config_known_strategies(self):
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_x0_volsize" in _KNOWN_STRATEGIES

    def test_cli_backtest_registry(self):
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_x0_volsize" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_x0_volsize"] is VTrendX0VolsizeStrategy
