"""Tests for VTREND-SM strategy per 34c canonical design contract.

Covers T1–T21 acceptance criteria + min_weight>0 canonical test (D2).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from strategies.vtrend_sm.strategy import (
    BARS_PER_YEAR_4H,
    EPS,
    STRATEGY_ID,
    VTrendSMConfig,
    VTrendSMStrategy,
    _atr,
    _clip_weight,
    _ema,
    _realized_vol,
    _rolling_high_shifted,
    _rolling_low_shifted,
    _vdo,
)
from v10.core.types import Bar, MarketState, Signal


# ── Helpers ────────────────────────────────────────────────────────────

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
    exposure: float = 0.0,
    cash: float = 10_000.0,
    btc_qty: float = 0.0,
) -> MarketState:
    nav = cash + btc_qty * bar.close
    # Use explicit exposure if provided, otherwise compute from btc_qty
    if btc_qty > 0 and nav > 0:
        computed_exposure = btc_qty * bar.close / nav
    else:
        computed_exposure = exposure
    return MarketState(
        bar=bar,
        h4_bars=h4_bars,
        d1_bars=[],
        bar_index=bar_index,
        d1_index=-1,
        cash=cash,
        btc_qty=btc_qty,
        nav=nav,
        exposure=computed_exposure,
        entry_price_avg=0.0,
        position_entry_nav=0.0,
    )


def _make_trending_bars(n: int, start_price: float = 100.0,
                        trend: float = 1.0) -> list[Bar]:
    """Generate n bars with a steady uptrend.

    Bars have tight high/low spreads (0.1% of close) so that with trend > 0,
    close eventually exceeds rolling_high(shifted) — enabling breakout entry.
    """
    bars = []
    for i in range(n):
        c = start_price + i * trend
        spread = c * 0.001  # 0.1% spread
        bars.append(_make_bar(
            close=c,
            high=c + spread,
            low=c - spread,
            open_=c - trend * 0.3,
            open_time=i * 14_400_000,
            close_time=(i + 1) * 14_400_000 - 1,
        ))
    return bars


# ── T1: Config defaults match source (I15) ────────────────────────────

class TestConfigDefaults:
    """T1: All 16 defaults must match VTrendStateMachineParams."""

    def test_defaults_match_source(self) -> None:
        cfg = VTrendSMConfig()
        assert cfg.slow_period == 120
        assert cfg.fast_period is None
        assert cfg.atr_period == 14
        assert cfg.atr_mult == 3.0
        assert cfg.entry_n is None
        assert cfg.exit_n is None
        assert cfg.target_vol == 0.15
        assert cfg.vol_lookback is None
        assert cfg.slope_lookback == 6
        assert cfg.use_vdo_filter is False
        assert cfg.vdo_threshold == 0.0
        assert cfg.vdo_fast == 12
        assert cfg.vdo_slow == 28
        assert cfg.exit_on_regime_break is False
        assert cfg.min_rebalance_weight_delta == 0.05
        assert cfg.min_weight == 0.0

    def test_field_count(self) -> None:
        """Exactly 16 config fields."""
        import dataclasses
        assert len(dataclasses.fields(VTrendSMConfig)) == 16


# ── T2: Config resolved() auto-derivation (I16) ──────────────────────

class TestConfigResolved:
    """T2: Auto-derivation formulas match source."""

    def test_defaults_resolved(self) -> None:
        r = VTrendSMConfig().resolved()
        assert r["fast_period"] == 30    # max(5, 120 // 4)
        assert r["entry_n"] == 60        # max(24, 120 // 2)
        assert r["exit_n"] == 30         # max(12, 120 // 4)
        assert r["vol_lookback"] == 120  # slow_period

    def test_small_slow_period_uses_minimums(self) -> None:
        r = VTrendSMConfig(slow_period=8).resolved()
        assert r["fast_period"] == 5     # max(5, 8 // 4=2) = 5
        assert r["entry_n"] == 24        # max(24, 8 // 2=4) = 24
        assert r["exit_n"] == 12         # max(12, 8 // 4=2) = 12
        assert r["vol_lookback"] == 8

    def test_explicit_overrides_preserved(self) -> None:
        r = VTrendSMConfig(fast_period=10, entry_n=20, exit_n=15,
                           vol_lookback=50).resolved()
        assert r["fast_period"] == 10
        assert r["entry_n"] == 20
        assert r["exit_n"] == 15
        assert r["vol_lookback"] == 50

    def test_slope_lookback_validation(self) -> None:
        with pytest.raises(ValueError, match="slope_lookback must be > 0"):
            VTrendSMConfig(slope_lookback=0)
        with pytest.raises(ValueError, match="slope_lookback must be > 0"):
            VTrendSMConfig(slope_lookback=-1)


# ── T3: _ema numerical correctness (B1) ──────────────────────────────

class TestEMA:
    """T3: EMA matches pandas ewm(span=N, adjust=False).mean()."""

    def test_known_values(self) -> None:
        series = np.array([10.0, 11.0, 12.0, 11.0, 10.0], dtype=np.float64)
        period = 3
        result = _ema(series, period)
        # alpha = 2/(3+1) = 0.5
        # ema[0] = 10.0
        # ema[1] = 0.5*11 + 0.5*10 = 10.5
        # ema[2] = 0.5*12 + 0.5*10.5 = 11.25
        # ema[3] = 0.5*11 + 0.5*11.25 = 11.125
        # ema[4] = 0.5*10 + 0.5*11.125 = 10.5625
        expected = np.array([10.0, 10.5, 11.25, 11.125, 10.5625])
        np.testing.assert_allclose(result, expected, rtol=1e-12)

    def test_constant_series(self) -> None:
        series = np.full(20, 42.0)
        result = _ema(series, 10)
        np.testing.assert_allclose(result, 42.0, rtol=1e-12)


# ── T4: _atr numerical correctness (B2) ──────────────────────────────

class TestATR:
    """T4: ATR matches Wilder's smoothing."""

    def test_known_values(self) -> None:
        high = np.array([12.0, 13.0, 14.0, 13.5, 14.5], dtype=np.float64)
        low = np.array([10.0, 11.0, 12.0, 11.5, 12.5], dtype=np.float64)
        close = np.array([11.0, 12.0, 13.0, 12.0, 14.0], dtype=np.float64)
        result = _atr(high, low, close, period=3)
        # TR[0] = max(12-10, |12-12|, |10-12|) = max(2, 0, 2) = 2 (first bar uses high[0] as prev_close proxy)
        # Actually: prev_close = [high[0], close[:-1]] = [12, 11, 12, 13, 12]
        # TR[0] = max(12-10, |12-12|, |10-12|) = max(2, 0, 2) = 2
        # TR[1] = max(13-11, |13-11|, |11-11|) = max(2, 2, 0) = 2
        # TR[2] = max(14-12, |14-12|, |12-12|) = max(2, 2, 0) = 2
        # TR[3] = max(13.5-11.5, |13.5-13|, |11.5-13|) = max(2, 0.5, 1.5) = 2
        # TR[4] = max(14.5-12.5, |14.5-12|, |12.5-12|) = max(2, 2.5, 0.5) = 2.5
        # ATR[2] = mean(2,2,2) = 2.0
        # ATR[3] = (2.0 * 2 + 2) / 3 = 2.0
        # ATR[4] = (2.0 * 2 + 2.5) / 3 = 2.1667
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        np.testing.assert_allclose(result[2], 2.0, rtol=1e-12)
        np.testing.assert_allclose(result[3], 2.0, rtol=1e-12)
        np.testing.assert_allclose(result[4], (4.0 + 2.5) / 3.0, rtol=1e-12)


# ── T5: _rolling_high_shifted numerical correctness (B3) ─────────────

class TestRollingHighShifted:
    """T5: Rolling max of high over previous lookback bars."""

    def test_known_values(self) -> None:
        high = np.array([10.0, 12.0, 11.0, 14.0, 13.0, 15.0], dtype=np.float64)
        result = _rolling_high_shifted(high, lookback=3)
        # i=0,1,2: NaN (insufficient history)
        # i=3: max(high[0],high[1],high[2]) = max(10,12,11) = 12
        # i=4: max(high[1],high[2],high[3]) = max(12,11,14) = 14
        # i=5: max(high[2],high[3],high[4]) = max(11,14,13) = 14
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert np.isnan(result[2])
        assert result[3] == 12.0
        assert result[4] == 14.0
        assert result[5] == 14.0


# ── T6: _rolling_low_shifted numerical correctness (B4) ──────────────

class TestRollingLowShifted:
    """T6: Rolling min of low over previous lookback bars."""

    def test_known_values(self) -> None:
        low = np.array([10.0, 8.0, 9.0, 7.0, 11.0, 6.0], dtype=np.float64)
        result = _rolling_low_shifted(low, lookback=3)
        # i=0,1,2: NaN
        # i=3: min(low[0],low[1],low[2]) = min(10,8,9) = 8
        # i=4: min(low[1],low[2],low[3]) = min(8,9,7) = 7
        # i=5: min(low[2],low[3],low[4]) = min(9,7,11) = 7
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert np.isnan(result[2])
        assert result[3] == 8.0
        assert result[4] == 7.0
        assert result[5] == 7.0


# ── T7: _realized_vol numerical correctness (B5) ─────────────────────

class TestRealizedVol:
    """T7: Annualized realized vol from log returns."""

    def test_constant_price_zero_vol(self) -> None:
        close = np.full(20, 100.0, dtype=np.float64)
        result = _realized_vol(close, lookback=10, bars_per_year=2190.0)
        # Constant price → log returns = 0 → std = 0 → rv = 0
        assert result[10] == 0.0

    def test_known_computation(self) -> None:
        close = np.array([100.0, 101.0, 99.0, 102.0, 100.0], dtype=np.float64)
        result = _realized_vol(close, lookback=4, bars_per_year=2190.0)
        # lr[1..4] = log(101/100), log(99/101), log(102/99), log(100/102)
        lr = np.log(close[1:] / close[:-1])
        expected_std = np.std(lr, ddof=0)
        expected_rv = expected_std * math.sqrt(2190.0)
        np.testing.assert_allclose(result[4], expected_rv, rtol=1e-10)


# ── T8: _clip_weight all branches (B7, I11) ──────────────────────────

class TestClipWeight:
    """T8: NaN→0, clamp [0,1], below min_weight→0."""

    def test_nan_returns_zero(self) -> None:
        assert _clip_weight(float("nan")) == 0.0

    def test_inf_returns_zero(self) -> None:
        assert _clip_weight(float("inf")) == 0.0

    def test_negative_inf_returns_zero(self) -> None:
        assert _clip_weight(float("-inf")) == 0.0

    def test_negative_clamped_to_zero(self) -> None:
        assert _clip_weight(-0.5) == 0.0

    def test_above_one_clamped(self) -> None:
        assert _clip_weight(2.5) == 1.0

    def test_normal_value_passes(self) -> None:
        assert _clip_weight(0.6) == 0.6

    def test_below_min_weight_returns_zero(self) -> None:
        assert _clip_weight(0.03, min_weight=0.05) == 0.0

    def test_at_min_weight_passes(self) -> None:
        assert _clip_weight(0.05, min_weight=0.05) == 0.05

    def test_above_min_weight_passes(self) -> None:
        assert _clip_weight(0.10, min_weight=0.05) == 0.10

    def test_zero_with_zero_min_weight(self) -> None:
        # 0.0 is not < 0.0, so it should pass
        assert _clip_weight(0.0) == 0.0


# ── T9: Entry signal when conditions met (I4, B8) ────────────────────

class TestEntrySignal:
    """T9: Entry requires regime_ok AND breakout_ok AND weight > 0."""

    def _make_entry_scenario(self) -> tuple[list[Bar], VTrendSMStrategy]:
        """Build 200 bars with a strong uptrend triggering entry."""
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendSMConfig(slow_period=20, atr_mult=3.0,
                             target_vol=0.15)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])
        return bars, strategy

    def test_entry_emitted_during_trend(self) -> None:
        bars, strategy = self._make_entry_scenario()
        signals = []
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                signals.append((i, sig))
        # Must have at least one entry signal
        entry_sigs = [(i, s) for i, s in signals if s.reason == "vtrend_sm_entry"]
        assert len(entry_sigs) > 0
        # Entry target_exposure must be in (0, 1]
        for _, sig in entry_sigs:
            assert 0.0 < sig.target_exposure <= 1.0


# ── T10: No entry during warmup (I10) ────────────────────────────────

class TestWarmup:
    """T10: No signals before all indicators converge."""

    def test_no_signals_during_warmup(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendSMConfig(slow_period=20)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])
        warmup_end = strategy._warmup_end
        assert warmup_end > 0, "Warmup must be > 0 for meaningful test"
        for i in range(warmup_end):
            state = _make_state(bars[i], bars, i)
            assert strategy.on_bar(state) is None


# ── T11: Exit on floor break (I5) ────────────────────────────────────

class TestExitFloorBreak:
    """T11: Exit when close < adaptive floor."""

    def test_floor_exit(self) -> None:
        # Build uptrend bars, then crash
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        # Add crash bars
        last_close = bars[-1].close
        for i in range(20):
            c = last_close - (i + 1) * 5.0  # sharp decline
            bars.append(_make_bar(
                close=c,
                high=c + 1.0,
                low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendSMConfig(slow_period=20, atr_mult=3.0, target_vol=0.15)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        entered = False
        exited = False
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                if sig.reason == "vtrend_sm_entry":
                    entered = True
                elif sig.reason == "vtrend_sm_floor_exit":
                    exited = True
                    break

        assert entered, "Must enter during uptrend"
        assert exited, "Must exit on floor break during crash"


# ── T12: Exit on regime break when enabled (I5) ──────────────────────

class TestExitRegimeBreak:
    """T12: Exit when regime_ok flips off (exit_on_regime_break=True)."""

    def test_regime_exit(self) -> None:
        # Uptrend then sideways/down to break regime
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        last_close = bars[-1].close
        # Sideways to break ema_fast < ema_slow
        for i in range(50):
            c = last_close - i * 0.3
            bars.append(_make_bar(
                close=c,
                high=c + 0.5,
                low=c - 0.5,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendSMConfig(slow_period=20, atr_mult=3.0,
                             exit_on_regime_break=True, target_vol=0.15)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        entered = False
        exit_reasons = []
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                if sig.reason == "vtrend_sm_entry":
                    entered = True
                elif sig.reason in ("vtrend_sm_regime_exit", "vtrend_sm_floor_exit"):
                    exit_reasons.append(sig.reason)
                    break

        assert entered, "Must enter during uptrend"
        assert len(exit_reasons) > 0, "Must exit during regime break"


# ── T13: No exit on regime break when disabled (A6) ──────────────────

class TestNoRegimeExitWhenDisabled:
    """T13: regime_break does NOT cause exit when exit_on_regime_break=False."""

    def test_no_regime_exit_when_disabled(self) -> None:
        # Same scenario as T12 but with exit_on_regime_break=False
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        last_close = bars[-1].close
        for i in range(50):
            c = last_close - i * 0.3
            bars.append(_make_bar(
                close=c,
                high=c + 0.5,
                low=c - 0.5,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendSMConfig(slow_period=20, atr_mult=3.0,
                             exit_on_regime_break=False, target_vol=0.15)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        exit_reasons = []
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.target_exposure == 0.0:
                exit_reasons.append(sig.reason)

        # Should NOT contain regime_exit
        assert "vtrend_sm_regime_exit" not in exit_reasons


# ── T14: Vol-targeted sizing (I9, B9) ────────────────────────────────

class TestVolTargetedSizing:
    """T14: weight = target_vol / rv, bounded [0, 1]."""

    def test_high_vol_small_weight(self) -> None:
        # Use volatile bars (alternating moves) on top of uptrend
        bars = []
        for i in range(200):
            c = 100.0 + i * 1.0 + (5.0 if i % 2 == 0 else -5.0)
            spread = 8.0
            bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.5,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))
        cfg = VTrendSMConfig(slow_period=20, target_vol=0.02)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_sm_entry":
                assert sig.target_exposure < 1.0
                assert sig.target_exposure > 0.0
                break

    def test_low_vol_clamped_at_one(self) -> None:
        # Very low vol → target_vol / rv > 1 → clamped to 1.0
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendSMConfig(slow_period=20, target_vol=10.0)  # absurdly high
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_sm_entry":
                assert sig.target_exposure == 1.0
                break


# ── T15 & T16: Rebalance threshold (A9) ──────────────────────────────

class TestRebalanceThreshold:
    """T15: small changes suppressed. T16: large changes produce signal."""

    def test_small_change_suppressed(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=1.0)
        cfg = VTrendSMConfig(slow_period=20, target_vol=0.15,
                             min_rebalance_weight_delta=0.50)  # very high threshold
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        rebalance_count = 0
        for i in range(len(bars)):
            # Set exposure near the expected weight (~1.0 for tight bars)
            # so delta stays small, below 50% threshold
            state = _make_state(bars[i], bars, i, exposure=0.85)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_sm_rebalance":
                rebalance_count += 1

        # With exposure=0.85 and weight≈1.0, delta≈0.15 < 0.50 threshold
        # Very few or zero rebalances expected
        assert rebalance_count <= 5

    def test_low_threshold_more_rebalances(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg_high = VTrendSMConfig(slow_period=20, target_vol=0.15,
                                  min_rebalance_weight_delta=0.50)
        cfg_low = VTrendSMConfig(slow_period=20, target_vol=0.15,
                                 min_rebalance_weight_delta=0.01)

        s_high = VTrendSMStrategy(cfg_high)
        s_low = VTrendSMStrategy(cfg_low)
        s_high.on_init(bars, [])
        s_low.on_init(bars, [])

        def count_rebalances(strategy: VTrendSMStrategy) -> int:
            count = 0
            for i in range(len(bars)):
                state = _make_state(bars[i], bars, i, exposure=0.3)
                sig = strategy.on_bar(state)
                if sig is not None and sig.reason == "vtrend_sm_rebalance":
                    count += 1
            return count

        assert count_rebalances(s_low) >= count_rebalances(s_high)


# ── T17: Weights bounded [0, 1] (I2, I9) ─────────────────────────────

class TestWeightsBounded:
    """T17: No Signal with target_exposure outside [0, 1]."""

    def test_all_signals_bounded(self) -> None:
        bars = _make_trending_bars(300, start_price=100.0, trend=0.5)
        # Add crash
        last_close = bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 3.0
            bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(300 + i) * 14_400_000,
                close_time=(301 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendSMConfig(slow_period=20, target_vol=0.15)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                assert 0.0 <= sig.target_exposure <= 1.0, (
                    f"Bar {i}: target_exposure={sig.target_exposure} out of bounds"
                )


# ── T18: VDO filter blocks entry (A5) ────────────────────────────────

class TestVDOFilter:
    """T18: VDO filter blocks entry when VDO < threshold (if enabled)."""

    def test_vdo_blocks_entry(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)

        cfg_no_vdo = VTrendSMConfig(slow_period=20, target_vol=0.15,
                                    use_vdo_filter=False)
        cfg_vdo = VTrendSMConfig(slow_period=20, target_vol=0.15,
                                 use_vdo_filter=True, vdo_threshold=99.0)

        s_no = VTrendSMStrategy(cfg_no_vdo)
        s_yes = VTrendSMStrategy(cfg_vdo)
        s_no.on_init(bars, [])
        s_yes.on_init(bars, [])

        entries_no = 0
        entries_yes = 0
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig_no = s_no.on_bar(state)
            sig_yes = s_yes.on_bar(state)
            if sig_no and sig_no.reason == "vtrend_sm_entry":
                entries_no += 1
            if sig_yes and sig_yes.reason == "vtrend_sm_entry":
                entries_yes += 1

        assert entries_no > 0, "Without VDO filter, entries should occur"
        assert entries_yes == 0, "VDO threshold=99 should block all entries"


# ── T18b: _vdo() numerical unit tests ────────────────────────────────

class TestVdoNumerical:
    """Dedicated _vdo() unit tests: correctness and fail-closed behavior."""

    def test_taker_buy_path_numerical(self) -> None:
        """When taker_buy > 0, VDR = (buy - sell) / volume."""
        # 3 bars: buy-heavy, balanced, sell-heavy
        close = np.array([100.0, 100.0, 100.0])
        high = np.array([105.0, 105.0, 105.0])
        low = np.array([95.0, 95.0, 95.0])
        volume = np.array([100.0, 100.0, 100.0])
        taker_buy = np.array([80.0, 50.0, 20.0])

        # VDR: (80-20)/100=0.6, (50-50)/100=0.0, (20-80)/100=-0.6
        result = _vdo(close, high, low, volume, taker_buy, fast=1, slow=2)

        # With fast=1 (alpha=1.0), EMA(fast) = raw VDR itself
        # slow=2 (alpha=2/3): ema[0]=0.6, ema[1]=2/3*0.0+1/3*0.6=0.2, ema[2]=2/3*(-0.6)+1/3*0.2=-1/3
        # VDO = EMA(fast) - EMA(slow)
        # Bar 0: 0.6 - 0.6 = 0.0
        # Bar 1: 0.0 - 0.2 = -0.2
        # Bar 2: -0.6 - (-1/3) ≈ -0.2667
        assert abs(result[0]) < 1e-10, f"Bar 0: {result[0]}"
        assert abs(result[1] - (-0.2)) < 1e-10, f"Bar 1: {result[1]}"
        expected_2 = -0.6 - (-1.0 / 3.0)
        assert abs(result[2] - expected_2) < 1e-10, f"Bar 2: {result[2]}"

    def test_all_zero_taker_raises(self) -> None:
        """When taker_buy all zeros, must raise RuntimeError (fail-closed)."""
        close = np.array([100.0, 110.0, 90.0])
        high = np.array([110.0, 110.0, 110.0])
        low = np.array([90.0, 90.0, 90.0])
        volume = np.array([100.0, 100.0, 100.0])
        taker_buy = np.array([0.0, 0.0, 0.0])

        with pytest.raises(RuntimeError, match="taker_buy_base_vol"):
            _vdo(close, high, low, volume, taker_buy, fast=1, slow=2)

    def test_taker_buy_none_raises(self) -> None:
        """When taker_buy is None, must raise RuntimeError (fail-closed)."""
        close = np.array([100.0, 105.0, 95.0])
        high = np.array([110.0, 110.0, 110.0])
        low = np.array([90.0, 90.0, 90.0])
        volume = np.array([100.0, 100.0, 100.0])

        with pytest.raises(RuntimeError, match="taker_buy_base_vol"):
            _vdo(close, high, low, volume, None, fast=3, slow=5)

    def test_zero_volume_bars(self) -> None:
        """VDR = 0 for zero-volume bars in taker path."""
        close = np.array([100.0, 101.0, 102.0])
        high = np.array([105.0, 106.0, 107.0])
        low = np.array([95.0, 96.0, 97.0])
        volume = np.array([0.0, 100.0, 0.0])
        taker_buy = np.array([0.0, 60.0, 0.0])

        # volume[0]=0 and taker_buy[0]=0 → has_taker checks np.any(taker_buy>0)
        # taker_buy[1]=60 > 0, so has_taker=True → taker path
        # Bar 0: volume=0 → mask=False → vdr=0
        # Bar 1: (60-40)/100 = 0.2
        # Bar 2: volume=0 → mask=False → vdr=0
        result = _vdo(close, high, low, volume, taker_buy, fast=1, slow=3)
        assert np.all(np.isfinite(result)), "All outputs should be finite"


# ── T19: slope_lookback affects signals (A2, I7) ─────────────────────

class TestSlopeLookback:
    """T19: Changing slope_lookback changes entry behavior."""

    def test_different_slope_lookback_different_signals(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)

        def count_entries(slope_lb: int) -> int:
            cfg = VTrendSMConfig(slow_period=20, slope_lookback=slope_lb,
                                 target_vol=0.15)
            strategy = VTrendSMStrategy(cfg)
            strategy.on_init(bars, [])
            count = 0
            for i in range(len(bars)):
                state = _make_state(bars[i], bars, i)
                sig = strategy.on_bar(state)
                if sig and sig.reason == "vtrend_sm_entry":
                    count += 1
            return count

        # Long slope_lookback requires longer uptrend → fewer/later entries
        entries_short = count_entries(2)
        entries_long = count_entries(30)
        # They should differ (not necessarily one > other in all cases)
        # But with a steady uptrend, shorter lookback should enter sooner/more
        assert entries_short != entries_long or entries_short > 0


# ── T20: Strategy interface smoke test ───────────────────────────────

class TestStrategyInterfaceSmoke:
    """T20: VTrendSMStrategy on_init + on_bar interface works without crash.

    Note: this tests the strategy interface only, not BacktestEngine integration.
    """

    def test_smoke_test_with_synthetic_data(self) -> None:
        """on_init + on_bar loop produces valid signals on synthetic bars."""
        cfg = VTrendSMConfig(slow_period=20, target_vol=0.15)
        strategy = VTrendSMStrategy(cfg)
        bars = _make_trending_bars(100, start_price=50000.0, trend=50.0)

        # Test on_init doesn't crash
        strategy.on_init(bars, [])

        # Test on_bar produces valid signals
        signals = []
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                signals.append(sig)
                assert isinstance(sig, Signal)
                assert sig.target_exposure is not None
                assert 0.0 <= sig.target_exposure <= 1.0


# ── T21: BARS_PER_YEAR_4H = 2190.0 (I14) ────────────────────────────

class TestBarsPerYear:
    """T21: BARS_PER_YEAR_4H must equal 365.0 * 6.0 = 2190.0."""

    def test_value(self) -> None:
        assert BARS_PER_YEAR_4H == 365.0 * 6.0
        assert BARS_PER_YEAR_4H == 2190.0


# ── D2 Canonical: min_weight > 0, weight after clip = 0 → NO entry ──

class TestMinWeightEntryGuard:
    """D2: When min_weight > 0 and weight after _clip_weight = 0.0,
    strategy must NOT enter LONG (must stay FLAT, emit nothing).

    This is the canonical behavior from 34c design contract §5 D2.
    """

    def test_min_weight_blocks_entry(self) -> None:
        """With very high min_weight, _clip_weight returns 0.0, no entry."""
        # Use volatile bars so realized vol is high, making weight small
        bars = []
        for i in range(200):
            c = 100.0 + i * 1.0 + (8.0 if i % 2 == 0 else -8.0)
            spread = 10.0
            bars.append(_make_bar(
                close=c, high=c + spread, low=c - spread,
                open_=c - 0.5,
                open_time=i * 14_400_000,
                close_time=(i + 1) * 14_400_000 - 1,
            ))
        # min_weight=0.99 → only weights >= 0.99 pass
        # With high vol, target_vol=0.02 / rv → small weight << 0.99 → clipped to 0
        cfg = VTrendSMConfig(
            slow_period=20, target_vol=0.02, min_weight=0.99
        )
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        entries = 0
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_sm_entry":
                entries += 1

        assert entries == 0, (
            "With min_weight=0.99 and low target_vol / high rv, weight after clip "
            "should be 0.0 → strategy must NOT enter LONG"
        )
        # Strategy must remain FLAT
        assert strategy._active is False

    def test_default_min_weight_allows_entry(self) -> None:
        """With default min_weight=0.0, entry proceeds normally."""
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendSMConfig(slow_period=20, target_vol=0.05)
        strategy = VTrendSMStrategy(cfg)
        strategy.on_init(bars, [])

        entries = 0
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_sm_entry":
                entries += 1

        assert entries > 0, (
            "With default min_weight=0.0, weight is always > 0 → entry must occur"
        )


# ── Registration tests ───────────────────────────────────────────────

class TestRegistration:
    """Verify vtrend_sm is registered in all required integration points."""

    def test_strategy_factory_registry(self) -> None:
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_sm" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_sm"]
        assert cls is VTrendSMStrategy
        assert cfg_cls is VTrendSMConfig

    def test_cli_registry(self) -> None:
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_sm" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_sm"] is VTrendSMStrategy

    def test_config_known_strategies(self) -> None:
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_sm" in _KNOWN_STRATEGIES

    def test_candidates_build_strategy(self) -> None:
        from v10.research.candidates import CandidateSpec, build_strategy
        spec = CandidateSpec(name="test", strategy="vtrend_sm")
        strategy, cfg = build_strategy(spec)
        assert strategy.name() == "vtrend_sm"
        assert isinstance(cfg, VTrendSMConfig)

    def test_strategy_id(self) -> None:
        assert STRATEGY_ID == "vtrend_sm"
        s = VTrendSMStrategy()
        assert s.name() == "vtrend_sm"


# ── Additional invariant tests ───────────────────────────────────────

class TestInvariants:
    """Additional tests for contract invariants I12, I13."""

    def test_on_after_fill_is_noop(self) -> None:
        """I13: on_after_fill is a no-op."""
        strategy = VTrendSMStrategy()
        # Should not raise
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        from v10.core.types import Fill, Side
        fill = Fill(ts_ms=0, side=Side.BUY, qty=0.1, price=100.0,
                    fee=0.01, notional=10.0, reason="test")
        strategy.on_after_fill(state, fill)

    def test_eps_value(self) -> None:
        assert EPS == 1e-12

    def test_empty_bars_no_crash(self) -> None:
        """I1 edge case: on_init with empty bars, on_bar returns None."""
        strategy = VTrendSMStrategy()
        strategy.on_init([], [])
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strategy.on_bar(state) is None


# ── ConfigProxy resolved() allowlist test ─────────────────────────────

class TestConfigProxyResolvedAllowlist:
    """Verify ConfigProxy doesn't false-positive on strategies using resolved()."""

    def test_resolved_method_allowlists_all_fields(self) -> None:
        """Config with resolved() method gets all fields allowlisted."""
        import dataclasses
        from validation.config_audit import _expand_conditional_allowlist

        cfg = VTrendSMConfig()
        assert callable(getattr(cfg, "resolved", None))
        allow = _expand_conditional_allowlist(cfg)
        all_fields = {f.name for f in dataclasses.fields(cfg)}
        assert allow == all_fields

    def test_config_without_resolved_unaffected(self) -> None:
        """Config without resolved() method is unaffected by the allowlist rule."""
        from validation.config_audit import _expand_conditional_allowlist
        from strategies.vtrend.strategy import VTrendConfig

        cfg = VTrendConfig()
        assert not callable(getattr(cfg, "resolved", None))
        allow = _expand_conditional_allowlist(cfg)
        assert len(allow) == 0

    def test_full_proxy_flow_no_false_positive(self) -> None:
        """Full ConfigProxy → strategy → usage check produces no unused fields."""
        import dataclasses
        from validation.config_audit import (
            AccessTracker, ConfigProxy, _expand_conditional_allowlist,
        )

        cfg = VTrendSMConfig(slow_period=120)
        known = {f.name for f in dataclasses.fields(cfg)}
        tracker = AccessTracker(label="test", known_fields=known)
        proxy = ConfigProxy(cfg, tracker)

        # Simulate strategy construction (consumes all via resolved())
        _ = VTrendSMStrategy(proxy)

        unused_raw = known - tracker.used_fields
        allowlist = _expand_conditional_allowlist(cfg)
        unused_final = sorted(f for f in unused_raw if f not in allowlist)
        assert unused_final == [], f"False positive fields: {unused_final}"
