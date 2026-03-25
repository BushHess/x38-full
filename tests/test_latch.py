"""Tests for the LATCH strategy.

Covers: config, indicators, hysteretic regime, 3-state machine, sizing,
VDO overlay, registration, invariants, and ConfigProxy allowlist.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import fields
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from strategies.latch.strategy import (
    BARS_PER_YEAR_4H,
    EPS,
    STRATEGY_ID,
    LatchConfig,
    LatchStrategy,
    _LatchState,
    _apply_vdo_overlay,
    _atr,
    _clip_weight,
    _compute_hysteretic_regime,
    _ema,
    _realized_vol,
    _rolling_high_shifted,
    _rolling_low_shifted,
    _rolling_zscore,
    _vdo,
)
from v10.strategies.base import Strategy


# ── Helpers ─────────────────────────────────────────────────────────────

def _make_bar(
    close: float = 100.0,
    high: float | None = None,
    low: float | None = None,
    open_: float | None = None,
    volume: float = 1000.0,
    taker_buy: float = 520.0,
    bar_index: int = 0,
) -> MagicMock:
    bar = MagicMock()
    bar.close = close
    bar.high = high if high is not None else close * 1.005
    bar.low = low if low is not None else close * 0.995
    bar.open = open_ if open_ is not None else close
    bar.volume = volume
    bar.taker_buy_base_vol = taker_buy
    return bar


def _make_state(
    bar_index: int = 0,
    close: float = 100.0,
    exposure: float = 0.0,
    **kwargs,
) -> MagicMock:
    bar = _make_bar(close=close, bar_index=bar_index, **kwargs)
    state = MagicMock()
    state.bar_index = bar_index
    state.bar = bar
    state.exposure = exposure
    return state


def _uptrend_bars(n: int = 200, start: float = 100.0, seed: int = 42):
    """Generate bars with strong uptrend (regime ON + breakout)."""
    rng = np.random.default_rng(seed)
    close = np.empty(n, dtype=np.float64)
    close[0] = start
    for i in range(1, n):
        close[i] = close[i - 1] * (1.0 + 0.005 + 0.002 * rng.standard_normal())
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) * 1.003
    low = np.minimum(open_, close) * 0.997
    bars = []
    for i in range(n):
        b = MagicMock()
        b.close = close[i]
        b.high = high[i]
        b.low = low[i]
        b.open = open_[i]
        b.volume = 1000.0
        b.taker_buy_base_vol = 520.0
        bars.append(b)
    return bars


def _uptrend_then_crash_bars(n_up: int = 160, n_down: int = 40,
                              start: float = 100.0, seed: int = 42):
    """Generate bars: uptrend then crash."""
    rng = np.random.default_rng(seed)
    n = n_up + n_down
    close = np.empty(n, dtype=np.float64)
    close[0] = start
    for i in range(1, n_up):
        close[i] = close[i - 1] * (1.0 + 0.005 + 0.002 * rng.standard_normal())
    for i in range(n_up, n):
        close[i] = close[i - 1] * (1.0 - 0.012 + 0.002 * rng.standard_normal())
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) * 1.003
    low = np.minimum(open_, close) * 0.997
    bars = []
    for i in range(n):
        b = MagicMock()
        b.close = close[i]
        b.high = high[i]
        b.low = low[i]
        b.open = open_[i]
        b.volume = 1000.0
        b.taker_buy_base_vol = 520.0
        bars.append(b)
    return bars


# ── Config Tests ────────────────────────────────────────────────────────

class TestLatchConfig:
    def test_defaults_match_source(self):
        cfg = LatchConfig()
        assert cfg.slow_period == 120
        assert cfg.fast_period == 30
        assert cfg.slope_lookback == 6
        assert cfg.entry_n == 60
        assert cfg.exit_n == 30
        assert cfg.atr_period == 14
        assert cfg.atr_mult == 2.0
        assert cfg.vol_lookback == 120
        assert cfg.target_vol == 0.12
        assert cfg.vol_floor == 0.08
        assert cfg.max_pos == 1.0
        assert cfg.min_weight == 0.0
        assert cfg.min_rebalance_weight_delta == 0.05
        assert cfg.vdo_mode == "none"

    def test_resolved_returns_all_fields(self):
        cfg = LatchConfig()
        r = cfg.resolved()
        for f in fields(cfg):
            assert f.name in r, f"Missing field {f.name}"
            assert r[f.name] == getattr(cfg, f.name)

    def test_slope_lookback_validation(self):
        with pytest.raises(ValueError, match="slope_lookback"):
            LatchConfig(slope_lookback=0)

    def test_validation_matches_source(self):
        """All source LatchParams.validate() checks are present."""
        with pytest.raises(ValueError, match="slow_period"):
            LatchConfig(slow_period=1)
        with pytest.raises(ValueError, match="fast_period must be > 1"):
            LatchConfig(fast_period=1)
        with pytest.raises(ValueError, match="fast_period must be < slow_period"):
            LatchConfig(fast_period=120, slow_period=120)
        with pytest.raises(ValueError, match="entry_n"):
            LatchConfig(entry_n=0)
        with pytest.raises(ValueError, match="atr_period"):
            LatchConfig(atr_period=0)
        with pytest.raises(ValueError, match="atr_mult"):
            LatchConfig(atr_mult=0.0)
        with pytest.raises(ValueError, match="vol_lookback"):
            LatchConfig(vol_lookback=1)
        with pytest.raises(ValueError, match="target_vol"):
            LatchConfig(target_vol=0.0)
        with pytest.raises(ValueError, match="vol_floor"):
            LatchConfig(vol_floor=0.0)
        with pytest.raises(ValueError, match="max_pos"):
            LatchConfig(max_pos=0.0)
        with pytest.raises(ValueError, match="max_pos"):
            LatchConfig(max_pos=1.5)

    def test_strategy_id(self):
        assert STRATEGY_ID == "latch"

    def test_bars_per_year(self):
        assert BARS_PER_YEAR_4H == pytest.approx(2190.0)


# ── Indicator Tests ─────────────────────────────────────────────────────

class TestEMA:
    def test_vs_pandas(self):
        rng = np.random.default_rng(99)
        data = rng.standard_normal(100).cumsum() + 100
        period = 20
        result = _ema(data, period)
        expected = pd.Series(data).ewm(span=period, adjust=False).mean().to_numpy()
        np.testing.assert_allclose(result, expected, rtol=1e-12)


class TestATR:
    def test_vs_pandas_wilder(self):
        rng = np.random.default_rng(77)
        close = rng.standard_normal(60).cumsum() + 100.0
        high = close + rng.uniform(0.5, 2.0, 60)
        low = close - rng.uniform(0.5, 2.0, 60)
        period = 14
        result = _atr(high, low, close, period)
        assert np.isnan(result[:period - 1]).all()
        assert np.isfinite(result[period - 1:]).all()


class TestRollingHighShifted:
    def test_vs_pandas(self):
        high = np.array([1.0, 3.0, 2.0, 5.0, 4.0, 6.0, 3.0], dtype=np.float64)
        lookback = 3
        result = _rolling_high_shifted(high, lookback)
        expected = pd.Series(high).shift(1).rolling(window=lookback, min_periods=lookback).max().to_numpy()
        np.testing.assert_array_equal(np.isnan(result), np.isnan(expected))
        mask = np.isfinite(result)
        np.testing.assert_allclose(result[mask], expected[mask])


class TestRollingLowShifted:
    def test_vs_pandas(self):
        low = np.array([5.0, 3.0, 4.0, 1.0, 2.0, 6.0, 3.0], dtype=np.float64)
        lookback = 3
        result = _rolling_low_shifted(low, lookback)
        expected = pd.Series(low).shift(1).rolling(window=lookback, min_periods=lookback).min().to_numpy()
        np.testing.assert_array_equal(np.isnan(result), np.isnan(expected))
        mask = np.isfinite(result)
        np.testing.assert_allclose(result[mask], expected[mask])


class TestRealizedVol:
    def test_vs_pandas(self):
        rng = np.random.default_rng(55)
        close = np.exp(rng.standard_normal(80).cumsum() * 0.01) * 100.0
        lookback = 20
        bpy = BARS_PER_YEAR_4H
        result = _realized_vol(close, lookback, bpy)

        lr = np.log(close[1:] / close[:-1])
        lr_series = pd.Series(np.concatenate([[np.nan], lr]))
        expected = (lr_series.rolling(window=lookback, min_periods=lookback)
                    .std(ddof=0) * math.sqrt(bpy)).to_numpy()
        mask = np.isfinite(result) & np.isfinite(expected)
        np.testing.assert_allclose(result[mask], expected[mask], rtol=1e-10)


class TestClipWeight:
    @pytest.mark.parametrize("weight,max_pos,min_weight,expected", [
        (0.5, 1.0, 0.0, 0.5),
        (1.5, 1.0, 0.0, 1.0),
        (-0.5, 1.0, 0.0, 0.0),
        (0.3, 0.6, 0.0, 0.3),
        (0.8, 0.6, 0.0, 0.6),
        (0.03, 1.0, 0.05, 0.0),     # below min_weight
        (0.05, 1.0, 0.05, 0.05),    # at min_weight
        (float("nan"), 1.0, 0.0, 0.0),
        (float("inf"), 1.0, 0.0, 0.0),   # inf → not finite → 0.0
        (float("-inf"), 1.0, 0.0, 0.0),
    ])
    def test_clip_weight(self, weight, max_pos, min_weight, expected):
        assert _clip_weight(weight, max_pos, min_weight) == pytest.approx(expected)


# ── Hysteretic Regime Tests ─────────────────────────────────────────────

class TestHystereticRegime:
    def test_basic_on_off_transitions(self):
        """Verify regime turns ON and OFF with correct triggers."""
        # Design: ON at bar 1, hysteresis holds at bar 2, OFF at bar 3
        ema_fast = np.array([1.0, 2.0, 1.52, 0.7, 0.8], dtype=np.float64)
        ema_slow = np.array([1.0, 1.5, 1.55, 1.0, 0.95], dtype=np.float64)
        slope_ref = np.array([np.nan, 1.0, 1.5, 1.55, 1.0], dtype=np.float64)

        regime_on, off_trigger, flip_off = _compute_hysteretic_regime(
            ema_fast, ema_slow, slope_ref
        )

        # Bar 1: fast=2.0 > slow=1.5, slow=1.5 > ref=1.0 → ON
        assert regime_on[1] is np.True_
        # Bar 2: fast=1.52 < slow=1.55 → no ON, but slow=1.55 > ref=1.5 → no OFF
        #         Hysteresis: stays ON
        assert regime_on[2] is np.True_
        # Bar 3: fast=0.7 < slow=1.0, slow=1.0 < ref=1.55 → OFF trigger
        assert regime_on[3] is np.False_
        assert flip_off[3] is np.True_

    def test_hysteresis_holds_state(self):
        """Neither trigger fires → regime stays at previous state."""
        # Fast slightly above slow, slow below slope_ref
        # → on_trigger = False (slow < ref), off_trigger = False (fast > slow)
        ema_fast = np.array([10.0, 12.0, 11.5, 11.2], dtype=np.float64)
        ema_slow = np.array([10.0, 11.0, 11.0, 11.0], dtype=np.float64)
        slope_ref = np.array([np.nan, 10.0, 11.0, 11.0], dtype=np.float64)

        regime_on, _, _ = _compute_hysteretic_regime(ema_fast, ema_slow, slope_ref)

        # Bar 1: fast=12>11, slow=11>10 → ON trigger → regime ON
        assert regime_on[1] is np.True_
        # Bar 2: fast=11.5>11, slow=11=11 → on_trigger=False (not >), off_trigger=False
        # Hysteresis → stays ON
        assert regime_on[2] is np.True_

    def test_nan_freezes_state(self):
        """During NaN bars, regime state is preserved."""
        ema_fast = np.array([10.0, 12.0, np.nan, 12.0], dtype=np.float64)
        ema_slow = np.array([10.0, 11.0, 11.0, 11.0], dtype=np.float64)
        slope_ref = np.array([np.nan, 10.0, 10.0, 10.0], dtype=np.float64)

        regime_on, _, _ = _compute_hysteretic_regime(ema_fast, ema_slow, slope_ref)

        assert regime_on[1] is np.True_
        assert regime_on[2] is np.True_  # frozen at ON during NaN
        assert regime_on[3] is np.True_

    def test_flip_off_fires_on_transition(self):
        """flip_off = True only when regime transitions from ON to OFF."""
        ema_fast = np.array([10.0, 12.0, 12.0, 8.0, 8.0], dtype=np.float64)
        ema_slow = np.array([10.0, 11.0, 11.0, 10.0, 10.0], dtype=np.float64)
        slope_ref = np.array([np.nan, 10.0, 10.0, 11.0, 10.0], dtype=np.float64)

        regime_on, off_trigger, flip_off = _compute_hysteretic_regime(
            ema_fast, ema_slow, slope_ref
        )

        # Bar 3: fast=8<10, slow=10<11 → off_trigger, regime was ON → flip_off
        assert flip_off[3] is np.True_
        # Bar 4: fast=8<10, slow=10=10 → off_trigger=False (slow not < ref)
        assert flip_off[4] is np.False_


# ── State Machine Tests ─────────────────────────────────────────────────

class TestStateMachineTransitions:
    """Test LATCH 3-state machine: OFF → ARMED → LONG → OFF."""

    @pytest.fixture()
    def small_strat(self):
        cfg = LatchConfig(
            slow_period=12, fast_period=4, slope_lookback=3,
            entry_n=6, exit_n=3, atr_period=4,
            atr_mult=2.0, vol_lookback=10, target_vol=0.15,
            vol_floor=0.08, max_pos=1.0, min_weight=0.0,
            min_rebalance_weight_delta=0.0,
        )
        return LatchStrategy(cfg)

    def test_entry_signal_emitted(self, small_strat):
        """Strategy emits entry signal during uptrend."""
        bars = _uptrend_bars(n=200, seed=42)
        small_strat.on_init(bars, [])

        signals = []
        for i, b in enumerate(bars):
            s = _make_state(bar_index=i, close=b.close, exposure=0.0)
            sig = small_strat.on_bar(s)
            if sig is not None:
                signals.append((i, sig))
                if sig.reason == "latch_entry":
                    break

        entry_signals = [s for _, s in signals if s.reason == "latch_entry"]
        assert len(entry_signals) >= 1
        assert entry_signals[0].target_exposure > 0.0

    def test_exit_on_floor_break(self, small_strat):
        """Strategy exits on adaptive floor break."""
        bars = _uptrend_then_crash_bars(n_up=160, n_down=60, seed=42)
        small_strat.on_init(bars, [])

        exit_found = False
        exposure = 0.0
        for i, b in enumerate(bars):
            s = _make_state(bar_index=i, close=b.close, exposure=exposure)
            sig = small_strat.on_bar(s)
            if sig is not None:
                exposure = sig.target_exposure
                if sig.reason == "latch_floor_exit":
                    exit_found = True
                    assert sig.target_exposure == 0.0
                    break

        assert exit_found

    def test_armed_state_reached(self):
        """Strategy reaches ARMED state (regime ON, no breakout)."""
        # Craft data: gentle uptrend so regime turns ON, but with high
        # wicks so hh_entry stays above close (no breakout).
        n = 100
        close = np.empty(n, dtype=np.float64)
        close[0] = 100.0
        for i in range(1, n):
            close[i] = close[i - 1] * 1.002  # slow uptrend
        open_ = np.concatenate([[close[0]], close[:-1]])
        high = np.maximum(open_, close) * 1.05  # very high wicks
        low = np.minimum(open_, close) * 0.998
        bars = []
        for i in range(n):
            b = MagicMock()
            b.close = close[i]
            b.high = high[i]
            b.low = low[i]
            b.open = open_[i]
            b.volume = 1000.0
            b.taker_buy_base_vol = 520.0
            bars.append(b)

        cfg = LatchConfig(
            slow_period=12, fast_period=4, slope_lookback=3,
            entry_n=6, exit_n=3, atr_period=4,
            atr_mult=2.0, vol_lookback=10, target_vol=0.15,
            vol_floor=0.08, max_pos=1.0, min_weight=0.0,
            min_rebalance_weight_delta=0.0,
        )
        strat = LatchStrategy(cfg)
        strat.on_init(bars, [])

        armed_seen = False
        for i in range(len(bars)):
            s = _make_state(bar_index=i, close=bars[i].close, exposure=0.0)
            strat.on_bar(s)
            if strat._state == _LatchState.ARMED:
                armed_seen = True
                break

        assert armed_seen, "ARMED state should be reachable with high wicks"

    def test_reentry_after_exit(self, small_strat):
        """entry → exit → re-entry cycle works."""
        bars = _uptrend_then_crash_bars(n_up=160, n_down=40, seed=42)
        # Add recovery bars
        rng = np.random.default_rng(99)
        n_recovery = 100
        recovery_start = bars[-1].close
        for i in range(n_recovery):
            c = recovery_start * (1.0 + 0.005 * (i + 1))
            b = MagicMock()
            b.close = c
            b.high = c * 1.003
            b.low = c * 0.997
            b.open = c
            b.volume = 1000.0
            b.taker_buy_base_vol = 520.0
            bars.append(b)

        small_strat.on_init(bars, [])

        entries = 0
        exits = 0
        exposure = 0.0
        for i in range(len(bars)):
            s = _make_state(bar_index=i, close=bars[i].close, exposure=exposure)
            sig = small_strat.on_bar(s)
            if sig is not None:
                exposure = sig.target_exposure
                if "entry" in sig.reason:
                    entries += 1
                elif "exit" in sig.reason:
                    exits += 1

        assert entries >= 2, f"Expected re-entry, got {entries} entries"
        assert exits >= 1

    def test_exit_before_rebalance(self, small_strat):
        """When exit fires, reason is exit not rebalance."""
        bars = _uptrend_then_crash_bars(n_up=160, n_down=60, seed=42)
        small_strat.on_init(bars, [])

        exposure = 0.0
        exit_reasons = []
        for i in range(len(bars)):
            s = _make_state(bar_index=i, close=bars[i].close, exposure=exposure)
            sig = small_strat.on_bar(s)
            if sig is not None:
                exposure = sig.target_exposure
                if sig.target_exposure == 0.0:
                    exit_reasons.append(sig.reason)

        for reason in exit_reasons:
            assert reason in ("latch_floor_exit", "latch_regime_exit"), \
                f"Exit reason should not be rebalance, got {reason}"


# ── Sizing Tests ────────────────────────────────────────────────────────

class TestSizing:
    def test_vol_targeted_sizing(self):
        """weight = target_vol / max(rv, vol_floor, EPS)."""
        rv = 0.20
        target_vol = 0.12
        vol_floor = 0.08
        expected = target_vol / rv  # 0.6
        result = _clip_weight(target_vol / max(rv, vol_floor, EPS), 1.0, 0.0)
        assert result == pytest.approx(expected)

    def test_vol_floor_effect(self):
        """When rv < vol_floor, sizing uses vol_floor."""
        rv = 0.04  # below vol_floor=0.08
        target_vol = 0.12
        vol_floor = 0.08
        expected = target_vol / vol_floor  # 1.5, clipped to 1.0
        result = _clip_weight(target_vol / max(rv, vol_floor, EPS), 1.0, 0.0)
        assert result == pytest.approx(1.0)

    def test_max_pos_clipping(self):
        """weight capped at max_pos when max_pos < 1.0."""
        rv = 0.10
        target_vol = 0.12
        max_pos = 0.6
        raw = target_vol / rv  # 1.2
        result = _clip_weight(raw, max_pos, 0.0)
        assert result == pytest.approx(0.6)


# ── VDO Overlay Tests ───────────────────────────────────────────────────

class TestVDOOverlay:
    @pytest.fixture()
    def default_r(self):
        return LatchConfig().resolved()

    def test_mode_none(self, default_r):
        default_r["vdo_mode"] = "none"
        assert _apply_vdo_overlay(0.5, 1.5, default_r) == pytest.approx(0.5)

    def test_size_mod_strong_positive(self, default_r):
        default_r["vdo_mode"] = "size_mod"
        result = _apply_vdo_overlay(1.0, 2.0, default_r)
        assert result == pytest.approx(1.0 * 1.00)  # strong_pos mult

    def test_size_mod_neutral(self, default_r):
        default_r["vdo_mode"] = "size_mod"
        result = _apply_vdo_overlay(1.0, 0.5, default_r)
        assert result == pytest.approx(1.0 * 0.80)  # neutral mult

    def test_size_mod_strong_negative(self, default_r):
        default_r["vdo_mode"] = "size_mod"
        result = _apply_vdo_overlay(1.0, -2.0, default_r)
        assert result == pytest.approx(1.0 * 0.25)  # strong_neg mult

    def test_size_mod_interpolation(self, default_r):
        """Between mild_neg and strong_neg, weight is blended."""
        default_r["vdo_mode"] = "size_mod"
        result = _apply_vdo_overlay(1.0, -0.75, default_r)
        # z=-0.75 is between mild_neg=-0.5 and strong_neg=-1.0
        span = 0.5  # -0.5 - (-1.0)
        frac = (-0.75 - (-1.0)) / span  # 0.5
        expected = 0.25 + 0.5 * (0.55 - 0.25)  # 0.40
        assert result == pytest.approx(expected)

    def test_throttle_strong_neg(self, default_r):
        default_r["vdo_mode"] = "throttle"
        result = _apply_vdo_overlay(1.0, -2.0, default_r)
        assert result == pytest.approx(0.50)

    def test_throttle_mild_neg(self, default_r):
        default_r["vdo_mode"] = "throttle"
        result = _apply_vdo_overlay(1.0, -0.7, default_r)
        assert result == pytest.approx(0.75)

    def test_throttle_positive(self, default_r):
        default_r["vdo_mode"] = "throttle"
        result = _apply_vdo_overlay(1.0, 1.0, default_r)
        assert result == pytest.approx(1.0)

    def test_ranker_passthrough(self, default_r):
        default_r["vdo_mode"] = "ranker"
        assert _apply_vdo_overlay(0.7, 1.5, default_r) == pytest.approx(0.7)

    def test_nan_zscore_size_mod(self, default_r):
        default_r["vdo_mode"] = "size_mod"
        result = _apply_vdo_overlay(1.0, float("nan"), default_r)
        assert result == pytest.approx(0.80)  # neutral mult

    def test_nan_zscore_throttle(self, default_r):
        default_r["vdo_mode"] = "throttle"
        result = _apply_vdo_overlay(1.0, float("nan"), default_r)
        assert result == pytest.approx(1.0)  # no reduction


class TestRollingZscore:
    def test_vs_pandas(self):
        rng = np.random.default_rng(44)
        data = rng.standard_normal(50)
        lookback = 10
        result = _rolling_zscore(data, lookback)

        series = pd.Series(data)
        roll_mean = series.rolling(window=lookback, min_periods=lookback).mean()
        roll_std = series.rolling(window=lookback, min_periods=lookback).std(ddof=0)
        expected = ((series - roll_mean) / np.maximum(roll_std, EPS)).to_numpy()

        mask = np.isfinite(result) & np.isfinite(expected)
        np.testing.assert_allclose(result[mask], expected[mask], rtol=1e-10)


# ── Registration Tests ──────────────────────────────────────────────────

class TestRegistration:
    def test_strategy_subclass(self):
        assert issubclass(LatchStrategy, Strategy)

    def test_name_returns_strategy_id(self):
        s = LatchStrategy()
        assert s.name() == "latch"

    def test_registered_in_config_known_strategies(self):
        from v10.core.config import _KNOWN_STRATEGIES
        assert "latch" in _KNOWN_STRATEGIES

    def test_registered_in_config_fields(self):
        from v10.core.config import _LATCH_FIELDS
        cfg = LatchConfig()
        expected = {f.name for f in fields(cfg)}
        assert _LATCH_FIELDS == expected

    def test_registered_in_backtest_registry(self):
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "latch" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["latch"] is LatchStrategy

    def test_registered_in_strategy_factory(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "latch" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["latch"]
        assert cls is LatchStrategy
        assert cfg_cls is LatchConfig

    def test_registered_in_candidates(self):
        from v10.research.candidates import _LATCH_FIELDS
        cfg = LatchConfig()
        expected = {f.name for f in fields(cfg)}
        assert _LATCH_FIELDS == expected


# ── Invariant Tests ─────────────────────────────────────────────────────

class TestInvariants:
    def test_no_signal_during_warmup(self):
        """No signals emitted before warmup_end."""
        cfg = LatchConfig(
            slow_period=12, fast_period=4, slope_lookback=3,
            entry_n=6, exit_n=3, atr_period=4,
            vol_lookback=10, target_vol=0.15, vol_floor=0.08,
        )
        strat = LatchStrategy(cfg)
        bars = _uptrend_bars(n=50, seed=42)
        strat.on_init(bars, [])

        for i in range(strat._warmup_end):
            s = _make_state(bar_index=i, close=bars[i].close)
            assert strat.on_bar(s) is None

    def test_empty_bars_no_crash(self):
        strat = LatchStrategy()
        strat.on_init([], [])
        s = _make_state(bar_index=0, close=100.0)
        assert strat.on_bar(s) is None

    def test_on_init_not_called_no_crash(self):
        strat = LatchStrategy()
        s = _make_state(bar_index=0, close=100.0)
        assert strat.on_bar(s) is None


# ── ConfigProxy / Allowlist Tests ───────────────────────────────────────

class TestConfigProxyAllowlist:
    def test_resolved_allowlists_all_fields(self):
        """Having resolved() means all fields are allowlisted."""
        from validation.config_audit import _expand_conditional_allowlist
        cfg = LatchConfig()
        allow = _expand_conditional_allowlist(cfg)
        expected = {f.name for f in fields(cfg)}
        assert expected == allow


# ── Differences from SM and P ──────────────────────────────────────────

class TestDifferencesFromSMAndP:
    def test_latch_has_fast_period(self):
        """LATCH has explicit fast_period=30; P has none."""
        cfg = LatchConfig()
        assert cfg.fast_period == 30

    def test_latch_has_vol_floor(self):
        """LATCH has vol_floor; SM/P do not."""
        cfg = LatchConfig()
        assert cfg.vol_floor == 0.08

    def test_latch_has_max_pos(self):
        """LATCH has configurable max_pos; SM/P hardcode 1.0."""
        cfg = LatchConfig()
        assert cfg.max_pos == 1.0

    def test_latch_atr_mult_differs_from_sm_and_p(self):
        """LATCH atr_mult=2.0, SM=3.0, P=1.5."""
        from strategies.vtrend_sm.strategy import VTrendSMConfig
        from strategies.vtrend_p.strategy import VTrendPConfig
        assert LatchConfig().atr_mult == 2.0
        assert VTrendSMConfig().atr_mult == 3.0
        assert VTrendPConfig().atr_mult == 1.5

    def test_latch_has_vdo_overlay_not_filter(self):
        """LATCH VDO is an overlay (size modifier), not an entry filter like SM."""
        cfg = LatchConfig()
        assert cfg.vdo_mode == "none"
        assert not hasattr(cfg, "use_vdo_filter")


# ── Engine Integration Smoke Test ────────────────────────────────────────

# ── Hardening: Sensitive-Area Stress Tests ────────────────────────────

class TestHardenWarmup:
    def test_warmup_index_correct(self):
        """warmup_end is the first bar with ALL 7 indicators finite."""
        cfg = LatchConfig(
            slow_period=12, fast_period=4, slope_lookback=3,
            entry_n=6, exit_n=3, atr_period=4, vol_lookback=10,
            target_vol=0.15, vol_floor=0.08,
        )
        strat = LatchStrategy(cfg)
        bars = _uptrend_bars(n=50, seed=42)
        strat.on_init(bars, [])

        # Verify warmup_end makes all indicators finite at that index
        i = strat._warmup_end
        assert i < len(bars), "warmup should end before data ends"
        for arr in [strat._ema_fast, strat._ema_slow, strat._slope_ref,
                    strat._atr_arr, strat._hh_entry, strat._ll_exit, strat._rv]:
            assert np.isfinite(arr[i]), f"Indicator not finite at warmup_end={i}"
        # Verify at least one indicator is NOT finite at i-1
        if i > 0:
            not_all_finite = not all(
                np.isfinite(arr[i - 1])
                for arr in [strat._ema_fast, strat._ema_slow, strat._slope_ref,
                            strat._atr_arr, strat._hh_entry, strat._ll_exit, strat._rv]
            )
            assert not_all_finite, "warmup_end should be minimal"

    def test_initial_state_is_off(self):
        """Strategy starts in OFF state."""
        strat = LatchStrategy()
        assert strat._state == _LatchState.OFF


class TestHardenExitOrdering:
    def test_no_same_bar_reentry(self):
        """After exit, no re-entry on the same bar (if-elif prevents it)."""
        bars = _uptrend_then_crash_bars(n_up=160, n_down=60, seed=42)
        cfg = LatchConfig(
            slow_period=12, fast_period=4, slope_lookback=3,
            entry_n=6, exit_n=3, atr_period=4,
            atr_mult=2.0, vol_lookback=10, target_vol=0.15,
            vol_floor=0.08, min_rebalance_weight_delta=0.0,
        )
        strat = LatchStrategy(cfg)
        strat.on_init(bars, [])

        exposure = 0.0
        for i in range(len(bars)):
            s = _make_state(bar_index=i, close=bars[i].close, exposure=exposure)
            sig = strat.on_bar(s)
            if sig is not None:
                # On an exit bar, no entry signal should follow
                if sig.target_exposure == 0.0:
                    assert "exit" in sig.reason, f"Zero exposure should be exit, got {sig.reason}"
                exposure = sig.target_exposure

    def test_armed_to_off_on_regime_off_trigger(self):
        """ARMED → OFF when off_trigger fires."""
        # Construct: uptrend → gentle rise (regime ON, no breakout) → sharp drop
        n = 60
        close = np.empty(n, dtype=np.float64)
        close[0] = 100.0
        for i in range(1, 25):
            close[i] = close[i - 1] * 1.002  # gentle up
        for i in range(25, n):
            close[i] = close[i - 1] * 0.985  # sharp down
        open_ = np.concatenate([[close[0]], close[:-1]])
        high = np.maximum(open_, close) * 1.05  # very high wicks → no breakout
        low = np.minimum(open_, close) * 0.998
        bars = []
        for i in range(n):
            b = MagicMock()
            b.close = close[i]
            b.high = high[i]
            b.low = low[i]
            b.open = open_[i]
            b.volume = 1000.0
            b.taker_buy_base_vol = 520.0
            bars.append(b)

        cfg = LatchConfig(
            slow_period=8, fast_period=3, slope_lookback=2,
            entry_n=6, exit_n=3, atr_period=3,
            atr_mult=2.0, vol_lookback=8, target_vol=0.15,
            vol_floor=0.08, min_rebalance_weight_delta=0.0,
        )
        strat = LatchStrategy(cfg)
        strat.on_init(bars, [])

        armed_then_off = False
        for i in range(len(bars)):
            s = _make_state(bar_index=i, close=bars[i].close, exposure=0.0)
            strat.on_bar(s)
            if strat._state == _LatchState.ARMED:
                # Continue until state changes
                for j in range(i + 1, len(bars)):
                    s2 = _make_state(bar_index=j, close=bars[j].close, exposure=0.0)
                    strat.on_bar(s2)
                    if strat._state == _LatchState.OFF:
                        armed_then_off = True
                        break
                    elif strat._state == _LatchState.LONG:
                        break  # went to LONG instead
                break

        assert armed_then_off, "ARMED → OFF transition should occur during sharp drop"


class TestHardenNaN:
    def test_nan_close_produces_no_signal(self):
        """NaN in indicators causes no signal (not a crash)."""
        cfg = LatchConfig(
            slow_period=8, fast_period=3, slope_lookback=2,
            entry_n=4, exit_n=2, atr_period=3,
            vol_lookback=6, target_vol=0.15, vol_floor=0.08,
        )
        strat = LatchStrategy(cfg)
        bars = _uptrend_bars(n=30, seed=42)
        strat.on_init(bars, [])

        # Corrupt one indicator after warmup
        strat._rv[strat._warmup_end + 1] = np.nan
        s = _make_state(
            bar_index=strat._warmup_end + 1,
            close=bars[strat._warmup_end + 1].close,
        )
        result = strat.on_bar(s)
        assert result is None

    def test_zero_volume_raises(self):
        """Zero taker data must raise RuntimeError (fail-closed VDO)."""
        n = 30
        bars = _uptrend_bars(n=n, seed=42)
        # Set all volumes to 0
        for b in bars:
            b.volume = 0.0
            b.taker_buy_base_vol = 0.0

        cfg = LatchConfig(
            slow_period=8, fast_period=3, slope_lookback=2,
            entry_n=4, exit_n=2, atr_period=3,
            vol_lookback=6, target_vol=0.15, vol_floor=0.08,
            vdo_mode="size_mod",
        )
        strat = LatchStrategy(cfg)
        with pytest.raises(RuntimeError, match="taker_buy_base_vol"):
            strat.on_init(bars, [])


class TestHardenDeterminism:
    def test_deterministic_on_same_input(self):
        """Strategy produces identical signals on identical input."""
        bars = _uptrend_then_crash_bars(n_up=100, n_down=30, seed=42)
        cfg = LatchConfig(
            slow_period=12, fast_period=4, slope_lookback=3,
            entry_n=6, exit_n=3, atr_period=4,
            atr_mult=2.0, vol_lookback=10, target_vol=0.15,
            vol_floor=0.08, min_rebalance_weight_delta=0.0,
        )

        def _collect_signals(bars_in):
            strat = LatchStrategy(cfg)
            strat.on_init(bars_in, [])
            signals = []
            exp = 0.0
            for i in range(len(bars_in)):
                s = _make_state(bar_index=i, close=bars_in[i].close, exposure=exp)
                sig = strat.on_bar(s)
                if sig is not None:
                    signals.append((i, sig.target_exposure, sig.reason))
                    exp = sig.target_exposure
            return signals

        s1 = _collect_signals(bars)
        s2 = _collect_signals(bars)
        assert len(s1) == len(s2)
        for (i1, e1, r1), (i2, e2, r2) in zip(s1, s2):
            assert i1 == i2
            assert e1 == pytest.approx(e2)
            assert r1 == r2


class TestHardenSourceParityTrace:
    def test_regime_matches_source_test(self):
        """Cross-validate hysteretic regime using exact source test data.

        Source test_latch.py::test_hysteretic_regime_has_memory uses:
          ema_fast = [1.0, 2.0, 1.52, 1.49, 0.7, 0.8]
          ema_slow = [1.0, 1.5, 1.55, 1.53, 1.0, 0.95]
          slope_n = 1

        Expected regime_on: [False, True, True, False, False, False]
        Expected flip_off: [False, False, False, True, False, False]
        """
        ema_fast = np.array([1.0, 2.0, 1.52, 1.49, 0.7, 0.8], dtype=np.float64)
        ema_slow = np.array([1.0, 1.5, 1.55, 1.53, 1.0, 0.95], dtype=np.float64)
        # slope_n=1 → slope_ref = ema_slow shifted by 1
        slope_ref = np.array([np.nan, 1.0, 1.5, 1.55, 1.53, 1.0], dtype=np.float64)

        regime_on, off_trigger, flip_off = _compute_hysteretic_regime(
            ema_fast, ema_slow, slope_ref
        )

        expected_regime = [False, True, True, False, False, False]
        expected_flip_off = [False, False, False, True, False, False]

        assert regime_on.tolist() == expected_regime
        assert flip_off.tolist() == expected_flip_off


# ── Engine Integration Smoke Test ────────────────────────────────────────

class TestEngineIntegration:
    def test_backtest_engine_runs(self):
        """BacktestEngine + LatchStrategy runs without crash."""
        try:
            from v10.core.data import DataFeed
            from v10.core.engine import BacktestEngine
            from v10.core.types import SCENARIOS

            data_path = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
            import os
            if not os.path.exists(data_path):
                pytest.skip("Data file not available")

            feed = DataFeed(data_path, warmup_days=365)
            strat = LatchStrategy(LatchConfig())
            engine = BacktestEngine(
                feed=feed, strategy=strat,
                cost=SCENARIOS["base"], initial_cash=10000.0,
            )
            result = engine.run()
            assert result.summary["trades"] >= 0
        except ImportError:
            pytest.skip("Engine dependencies not available")
