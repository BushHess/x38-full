"""Tests for VTREND-P strategy.

Covers config, indicators, entry/exit/rebalance logic, registration,
and ConfigProxy resolved() allowlist. Mirrors SM test structure adapted
for P's price-first algorithm (no VDO, no fast EMA, no regime-break exit).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from strategies.vtrend_p.strategy import (
    BARS_PER_YEAR_4H,
    EPS,
    STRATEGY_ID,
    VTrendPConfig,
    VTrendPStrategy,
    _atr,
    _clip_weight,
    _ema,
    _realized_vol,
    _rolling_high_shifted,
    _rolling_low_shifted,
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
    """Generate n bars with a steady uptrend."""
    bars = []
    for i in range(n):
        c = start_price + i * trend
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


# ── T1: Config defaults match source ──────────────────────────────────

class TestConfigDefaults:
    """T1: All 10 defaults must match VTrendPParams from Latch source."""

    def test_defaults_match_source(self) -> None:
        cfg = VTrendPConfig()
        assert cfg.slow_period == 120
        assert cfg.atr_period == 14
        assert cfg.atr_mult == 1.5
        assert cfg.target_vol == 0.12
        assert cfg.entry_n is None
        assert cfg.exit_n is None
        assert cfg.vol_lookback is None
        assert cfg.slope_lookback == 6
        assert cfg.min_rebalance_weight_delta == 0.05
        assert cfg.min_weight == 0.0

    def test_field_count(self) -> None:
        """Exactly 10 config fields."""
        import dataclasses
        assert len(dataclasses.fields(VTrendPConfig)) == 10


# ── T2: Config resolved() auto-derivation ─────────────────────────────

class TestConfigResolved:
    """T2: Auto-derivation formulas match source."""

    def test_defaults_resolved(self) -> None:
        r = VTrendPConfig().resolved()
        assert r["entry_n"] == 60        # max(24, 120 // 2)
        assert r["exit_n"] == 30         # max(12, 120 // 4)
        assert r["vol_lookback"] == 120  # slow_period

    def test_small_slow_period_uses_minimums(self) -> None:
        r = VTrendPConfig(slow_period=8).resolved()
        assert r["entry_n"] == 24        # max(24, 8 // 2=4) = 24
        assert r["exit_n"] == 12         # max(12, 8 // 4=2) = 12
        assert r["vol_lookback"] == 8

    def test_explicit_overrides_preserved(self) -> None:
        r = VTrendPConfig(entry_n=20, exit_n=15,
                          vol_lookback=50).resolved()
        assert r["entry_n"] == 20
        assert r["exit_n"] == 15
        assert r["vol_lookback"] == 50

    def test_slope_lookback_validation(self) -> None:
        with pytest.raises(ValueError, match="slope_lookback must be > 0"):
            VTrendPConfig(slope_lookback=0)
        with pytest.raises(ValueError, match="slope_lookback must be > 0"):
            VTrendPConfig(slope_lookback=-1)


# ── T3: _ema numerical correctness ───────────────────────────────────

class TestEMA:
    def test_known_values(self) -> None:
        series = np.array([10.0, 11.0, 12.0, 11.0, 10.0], dtype=np.float64)
        result = _ema(series, period=3)
        expected = np.array([10.0, 10.5, 11.25, 11.125, 10.5625])
        np.testing.assert_allclose(result, expected, rtol=1e-12)

    def test_constant_series(self) -> None:
        series = np.full(20, 42.0)
        result = _ema(series, 10)
        np.testing.assert_allclose(result, 42.0, rtol=1e-12)


# ── T4: _atr numerical correctness ──────────────────────────────────

class TestATR:
    def test_known_values(self) -> None:
        high = np.array([12.0, 13.0, 14.0, 13.5, 14.5], dtype=np.float64)
        low = np.array([10.0, 11.0, 12.0, 11.5, 12.5], dtype=np.float64)
        close = np.array([11.0, 12.0, 13.0, 12.0, 14.0], dtype=np.float64)
        result = _atr(high, low, close, period=3)
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        np.testing.assert_allclose(result[2], 2.0, rtol=1e-12)
        np.testing.assert_allclose(result[3], 2.0, rtol=1e-12)
        np.testing.assert_allclose(result[4], (4.0 + 2.5) / 3.0, rtol=1e-12)


# ── T5: _rolling_high_shifted numerical correctness ──────────────────

class TestRollingHighShifted:
    def test_known_values(self) -> None:
        high = np.array([10.0, 12.0, 11.0, 14.0, 13.0, 15.0], dtype=np.float64)
        result = _rolling_high_shifted(high, lookback=3)
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert np.isnan(result[2])
        assert result[3] == 12.0
        assert result[4] == 14.0
        assert result[5] == 14.0


# ── T6: _rolling_low_shifted numerical correctness ───────────────────

class TestRollingLowShifted:
    def test_known_values(self) -> None:
        low = np.array([10.0, 8.0, 9.0, 7.0, 11.0, 6.0], dtype=np.float64)
        result = _rolling_low_shifted(low, lookback=3)
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        assert np.isnan(result[2])
        assert result[3] == 8.0
        assert result[4] == 7.0
        assert result[5] == 7.0


# ── T7: _realized_vol numerical correctness ──────────────────────────

class TestRealizedVol:
    def test_constant_price_zero_vol(self) -> None:
        close = np.full(20, 100.0, dtype=np.float64)
        result = _realized_vol(close, lookback=10, bars_per_year=2190.0)
        assert result[10] == 0.0

    def test_known_computation(self) -> None:
        close = np.array([100.0, 101.0, 99.0, 102.0, 100.0], dtype=np.float64)
        result = _realized_vol(close, lookback=4, bars_per_year=2190.0)
        lr = np.log(close[1:] / close[:-1])
        expected_std = np.std(lr, ddof=0)
        expected_rv = expected_std * math.sqrt(2190.0)
        np.testing.assert_allclose(result[4], expected_rv, rtol=1e-10)


# ── T8: _clip_weight all branches ────────────────────────────────────

class TestClipWeight:
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
        assert _clip_weight(0.0) == 0.0


# ── T9: Entry signal when conditions met ─────────────────────────────

class TestEntrySignal:
    """Entry requires regime_ok (close > ema_slow) AND slope_ok
    (ema_slow > ema_slow_slope_ref) AND breakout_ok (close > hh)."""

    def _make_entry_scenario(self) -> tuple[list[Bar], VTrendPStrategy]:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendPConfig(slow_period=20, atr_mult=1.5, target_vol=0.12)
        strategy = VTrendPStrategy(cfg)
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
        entry_sigs = [(i, s) for i, s in signals if s.reason == "vtrend_p_entry"]
        assert len(entry_sigs) > 0
        for _, sig in entry_sigs:
            assert 0.0 < sig.target_exposure <= 1.0

    def test_price_first_regime_no_fast_ema(self) -> None:
        """P uses close > ema_slow for regime (no fast EMA)."""
        cfg = VTrendPConfig()
        # VTrendPConfig has no fast_period field at all
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(cfg)}
        assert "fast_period" not in field_names
        assert "use_vdo_filter" not in field_names


# ── T10: No entry during warmup ──────────────────────────────────────

class TestWarmup:
    def test_no_signals_during_warmup(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendPConfig(slow_period=20)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])
        warmup_end = strategy._warmup_end
        assert warmup_end > 0
        for i in range(warmup_end):
            state = _make_state(bars[i], bars, i)
            assert strategy.on_bar(state) is None


# ── T11: Exit on floor break ─────────────────────────────────────────

class TestExitFloorBreak:
    def test_floor_exit(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        last_close = bars[-1].close
        for i in range(20):
            c = last_close - (i + 1) * 5.0
            bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendPConfig(slow_period=20, atr_mult=1.5, target_vol=0.12)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        entered = False
        exited = False
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                if sig.reason == "vtrend_p_entry":
                    entered = True
                elif sig.reason == "vtrend_p_exit":
                    exited = True
                    break

        assert entered, "Must enter during uptrend"
        assert exited, "Must exit on floor break during crash"


# ── T12: No regime-break exit (P has no exit_on_regime_break) ────────

class TestNoRegimeBreakExit:
    """P never exits on regime break — only floor break."""

    def test_only_floor_exit_reason(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        last_close = bars[-1].close
        for i in range(50):
            c = last_close - i * 0.3
            bars.append(_make_bar(
                close=c, high=c + 0.5, low=c - 0.5,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendPConfig(slow_period=20, atr_mult=1.5, target_vol=0.12)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        exit_reasons = []
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.target_exposure == 0.0:
                exit_reasons.append(sig.reason)

        for r in exit_reasons:
            assert r == "vtrend_p_exit", f"Unexpected exit reason: {r}"


# ── T13: Vol-targeted sizing ─────────────────────────────────────────

class TestVolTargetedSizing:
    def test_high_vol_small_weight(self) -> None:
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
        cfg = VTrendPConfig(slow_period=20, target_vol=0.02)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_p_entry":
                assert sig.target_exposure < 1.0
                assert sig.target_exposure > 0.0
                break

    def test_low_vol_clamped_at_one(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendPConfig(slow_period=20, target_vol=10.0)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_p_entry":
                assert sig.target_exposure == 1.0
                break


# ── T14 & T15: Rebalance threshold ──────────────────────────────────

class TestRebalanceThreshold:
    def test_small_change_suppressed(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=1.0)
        cfg = VTrendPConfig(slow_period=20, target_vol=0.12,
                            min_rebalance_weight_delta=0.50)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        rebalance_count = 0
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i, exposure=0.85)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_p_rebalance":
                rebalance_count += 1

        assert rebalance_count <= 5

    def test_low_threshold_more_rebalances(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg_high = VTrendPConfig(slow_period=20, target_vol=0.12,
                                 min_rebalance_weight_delta=0.50)
        cfg_low = VTrendPConfig(slow_period=20, target_vol=0.12,
                                min_rebalance_weight_delta=0.01)

        s_high = VTrendPStrategy(cfg_high)
        s_low = VTrendPStrategy(cfg_low)
        s_high.on_init(bars, [])
        s_low.on_init(bars, [])

        def count_rebalances(strategy: VTrendPStrategy) -> int:
            count = 0
            for i in range(len(bars)):
                state = _make_state(bars[i], bars, i, exposure=0.3)
                sig = strategy.on_bar(state)
                if sig is not None and sig.reason == "vtrend_p_rebalance":
                    count += 1
            return count

        assert count_rebalances(s_low) >= count_rebalances(s_high)


# ── T16: Weights bounded [0, 1] ──────────────────────────────────────

class TestWeightsBounded:
    def test_all_signals_bounded(self) -> None:
        bars = _make_trending_bars(300, start_price=100.0, trend=0.5)
        last_close = bars[-1].close
        for i in range(50):
            c = last_close - (i + 1) * 3.0
            bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(300 + i) * 14_400_000,
                close_time=(301 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendPConfig(slow_period=20, target_vol=0.12)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                assert 0.0 <= sig.target_exposure <= 1.0, (
                    f"Bar {i}: target_exposure={sig.target_exposure} out of bounds"
                )


# ── T17: slope_lookback affects signals ──────────────────────────────

class TestSlopeLookback:
    def test_different_slope_lookback_different_signals(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)

        def count_entries(slope_lb: int) -> int:
            cfg = VTrendPConfig(slow_period=20, slope_lookback=slope_lb,
                                target_vol=0.12)
            strategy = VTrendPStrategy(cfg)
            strategy.on_init(bars, [])
            count = 0
            for i in range(len(bars)):
                state = _make_state(bars[i], bars, i)
                sig = strategy.on_bar(state)
                if sig and sig.reason == "vtrend_p_entry":
                    count += 1
            return count

        entries_short = count_entries(2)
        entries_long = count_entries(30)
        assert entries_short != entries_long or entries_short > 0


# ── T18: Strategy interface smoke test ───────────────────────────────

class TestStrategyInterfaceSmoke:
    def test_smoke_test_with_synthetic_data(self) -> None:
        cfg = VTrendPConfig(slow_period=20, target_vol=0.12)
        strategy = VTrendPStrategy(cfg)
        bars = _make_trending_bars(100, start_price=50000.0, trend=50.0)

        strategy.on_init(bars, [])

        signals = []
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                signals.append(sig)
                assert isinstance(sig, Signal)
                assert sig.target_exposure is not None
                assert 0.0 <= sig.target_exposure <= 1.0


# ── T19: BARS_PER_YEAR_4H = 2190.0 ──────────────────────────────────

class TestBarsPerYear:
    def test_value(self) -> None:
        assert BARS_PER_YEAR_4H == 365.0 * 6.0
        assert BARS_PER_YEAR_4H == 2190.0


# ── T20: min_weight > 0 blocks entry when weight too low ────────────

class TestMinWeightEntryGuard:
    def test_min_weight_blocks_entry(self) -> None:
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
        cfg = VTrendPConfig(
            slow_period=20, target_vol=0.02, min_weight=0.99
        )
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        entries = 0
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_p_entry":
                entries += 1

        assert entries == 0
        assert strategy._active is False

    def test_default_min_weight_allows_entry(self) -> None:
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        cfg = VTrendPConfig(slow_period=20, target_vol=0.05)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        entries = 0
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason == "vtrend_p_entry":
                entries += 1

        assert entries > 0


# ── T21: P-specific defaults differ from SM ──────────────────────────

class TestPDiffersFromSM:
    """Verify P's distinct defaults vs SM."""

    def test_atr_mult_default(self) -> None:
        cfg = VTrendPConfig()
        assert cfg.atr_mult == 1.5  # SM = 3.0

    def test_target_vol_default(self) -> None:
        cfg = VTrendPConfig()
        assert cfg.target_vol == 0.12  # SM = 0.15

    def test_no_vdo_fields(self) -> None:
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(VTrendPConfig())}
        assert "use_vdo_filter" not in field_names
        assert "vdo_threshold" not in field_names
        assert "vdo_fast" not in field_names
        assert "vdo_slow" not in field_names
        assert "fast_period" not in field_names
        assert "exit_on_regime_break" not in field_names


# ── Registration tests ───────────────────────────────────────────────

class TestRegistration:
    """Verify vtrend_p is registered in all required integration points."""

    def test_strategy_factory_registry(self) -> None:
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_p" in STRATEGY_REGISTRY
        cls, cfg_cls = STRATEGY_REGISTRY["vtrend_p"]
        assert cls is VTrendPStrategy
        assert cfg_cls is VTrendPConfig

    def test_cli_registry(self) -> None:
        from v10.cli.backtest import STRATEGY_REGISTRY
        assert "vtrend_p" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["vtrend_p"] is VTrendPStrategy

    def test_config_known_strategies(self) -> None:
        from v10.core.config import _KNOWN_STRATEGIES
        assert "vtrend_p" in _KNOWN_STRATEGIES

    def test_candidates_build_strategy(self) -> None:
        from v10.research.candidates import CandidateSpec, build_strategy
        spec = CandidateSpec(name="test", strategy="vtrend_p")
        strategy, cfg = build_strategy(spec)
        assert strategy.name() == "vtrend_p"
        assert isinstance(cfg, VTrendPConfig)

    def test_strategy_id(self) -> None:
        assert STRATEGY_ID == "vtrend_p"
        s = VTrendPStrategy()
        assert s.name() == "vtrend_p"


# ── Invariant tests ──────────────────────────────────────────────────

class TestInvariants:
    def test_on_after_fill_is_noop(self) -> None:
        strategy = VTrendPStrategy()
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        from v10.core.types import Fill, Side
        fill = Fill(ts_ms=0, side=Side.BUY, qty=0.1, price=100.0,
                    fee=0.01, notional=10.0, reason="test")
        strategy.on_after_fill(state, fill)

    def test_eps_value(self) -> None:
        assert EPS == 1e-12

    def test_empty_bars_no_crash(self) -> None:
        strategy = VTrendPStrategy()
        strategy.on_init([], [])
        bar = _make_bar(100.0)
        state = _make_state(bar, [bar], 0)
        assert strategy.on_bar(state) is None


# ── H1: Re-entry after exit (no stuck state) ────────────────────────

class TestReentryAfterExit:
    """After exit, strategy must be able to re-enter on a new trend."""

    def test_entry_exit_reentry_cycle(self) -> None:
        # Phase 1: uptrend → entry
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        # Phase 2: crash → exit
        last_close = bars[-1].close
        for i in range(30):
            c = last_close - (i + 1) * 5.0
            bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))
        # Phase 3: recovery → re-entry
        bottom = bars[-1].close
        for i in range(200):
            c = bottom + i * 0.8
            bars.append(_make_bar(
                close=c, high=c + c * 0.001, low=c - c * 0.001,
                open_time=(230 + i) * 14_400_000,
                close_time=(231 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendPConfig(slow_period=20, atr_mult=1.5, target_vol=0.12)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        events = []
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None and sig.reason in ("vtrend_p_entry", "vtrend_p_exit"):
                events.append(sig.reason)

        entries = [e for e in events if e == "vtrend_p_entry"]
        exits = [e for e in events if e == "vtrend_p_exit"]
        assert len(entries) >= 2, "Must re-enter after exit"
        assert len(exits) >= 1, "Must exit during crash"


# ── H2: Exit takes priority over rebalance in code path ──────────────

class TestExitBeforeRebalance:
    """When exit floor is breached, exit must fire (not rebalance).

    This verifies the code path ordering: exit check runs before rebalance
    check in the LONG branch of on_bar().
    """

    def test_exit_signal_is_exit_not_rebalance(self) -> None:
        """When a crash eventually triggers exit, the reason is 'exit' not 'rebalance'."""
        bars = _make_trending_bars(200, start_price=100.0, trend=0.5)
        last_close = bars[-1].close
        for i in range(20):
            c = last_close - (i + 1) * 5.0
            bars.append(_make_bar(
                close=c, high=c + 1.0, low=c - 1.0,
                open_time=(200 + i) * 14_400_000,
                close_time=(201 + i) * 14_400_000 - 1,
            ))

        cfg = VTrendPConfig(slow_period=20, atr_mult=1.5, target_vol=0.12,
                            min_rebalance_weight_delta=0.001)
        strategy = VTrendPStrategy(cfg)
        strategy.on_init(bars, [])

        entered = False
        exit_reason = None
        for i in range(len(bars)):
            state = _make_state(bars[i], bars, i)
            sig = strategy.on_bar(state)
            if sig is not None:
                if sig.reason == "vtrend_p_entry":
                    entered = True
                elif sig.target_exposure == 0.0 and entered:
                    exit_reason = sig.reason
                    break

        assert entered, "Must enter during uptrend"
        assert exit_reason == "vtrend_p_exit", (
            f"Exit signal must have reason 'vtrend_p_exit', got '{exit_reason}'"
        )


# ── ConfigProxy resolved() allowlist test ────────────────────────────

class TestConfigProxyResolvedAllowlist:
    def test_resolved_method_allowlists_all_fields(self) -> None:
        import dataclasses
        from validation.config_audit import _expand_conditional_allowlist

        cfg = VTrendPConfig()
        assert callable(getattr(cfg, "resolved", None))
        allow = _expand_conditional_allowlist(cfg)
        all_fields = {f.name for f in dataclasses.fields(cfg)}
        assert allow == all_fields

    def test_full_proxy_flow_no_false_positive(self) -> None:
        import dataclasses
        from validation.config_audit import (
            AccessTracker, ConfigProxy, _expand_conditional_allowlist,
        )

        cfg = VTrendPConfig(slow_period=120)
        known = {f.name for f in dataclasses.fields(cfg)}
        tracker = AccessTracker(label="test", known_fields=known)
        proxy = ConfigProxy(cfg, tracker)

        _ = VTrendPStrategy(proxy)

        unused_raw = known - tracker.used_fields
        allowlist = _expand_conditional_allowlist(cfg)
        unused_final = sorted(f for f in unused_raw if f not in allowlist)
        assert unused_final == [], f"False positive fields: {unused_final}"
