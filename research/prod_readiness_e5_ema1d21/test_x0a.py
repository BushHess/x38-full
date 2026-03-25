#!/usr/bin/env python3
"""Tests for X0A Runtime Regime Monitor."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.prod_readiness_e5_ema1d21.rejected.regime_monitor_v1_REJECTED import (
    rolling_mdd,
    rolling_atr_percentile,
    compute_training_mean,
    classify_alerts,
    extract_episodes,
    _atr_d1,
    AMBER_MDD, AMBER_ATR_RATIO, RED_MDD, RED_ATR_RATIO,
)


# =========================================================================
# rolling_mdd
# =========================================================================


class TestRollingMDD:
    def test_constant_price_zero_mdd(self):
        """Constant price → MDD = 0 everywhere."""
        close = np.full(200, 100.0)
        mdd = rolling_mdd(close, window=50)
        assert np.all(np.isnan(mdd[:49]))
        assert np.allclose(mdd[49:], 0.0)

    def test_monotonic_up_zero_mdd(self):
        """Monotonically increasing price → MDD = 0."""
        close = np.arange(1, 201, dtype=np.float64)
        mdd = rolling_mdd(close, window=50)
        assert np.allclose(mdd[49:], 0.0, atol=1e-12)

    def test_single_drop(self):
        """Price drops 50% then stays flat — MDD should be 0.50."""
        close = np.concatenate([
            np.full(100, 100.0),
            np.full(100, 50.0),
        ])
        mdd = rolling_mdd(close, window=180)
        # At bar 199 (end), window covers bars 20-199
        # Contains 100→50 drop = 50% MDD
        assert mdd[199] == pytest.approx(0.50, abs=1e-10)

    def test_nan_before_window(self):
        """First window-1 values should be NaN."""
        close = np.arange(1, 51, dtype=np.float64)
        mdd = rolling_mdd(close, window=20)
        assert np.all(np.isnan(mdd[:19]))
        assert not np.isnan(mdd[19])

    def test_known_drawdown(self):
        """Price: 100, 120, 80, 90 → MDD in that segment = 1 - 80/120 = 33.3%."""
        close = np.array([100.0, 120.0, 80.0, 90.0])
        mdd = rolling_mdd(close, window=4)
        expected = 1.0 - 80.0 / 120.0  # 0.3333...
        assert mdd[3] == pytest.approx(expected, abs=1e-10)


# =========================================================================
# rolling_atr_percentile
# =========================================================================


class TestRollingATRPercentile:
    def test_constant_atr(self):
        """Constant ATR → Q90 = constant."""
        atr = np.full(200, 500.0)
        q90 = rolling_atr_percentile(atr, window=50, q=90)
        assert np.all(np.isnan(q90[:49]))
        assert np.allclose(q90[49:], 500.0)

    def test_nan_handling(self):
        """NaN values in ATR should be skipped."""
        atr = np.full(200, 500.0)
        atr[:14] = np.nan  # ATR warmup
        q90 = rolling_atr_percentile(atr, window=50, q=90)
        # Should still compute valid Q90 where enough non-NaN values exist
        assert not np.isnan(q90[49])  # 36 valid values > 25 (half window)

    def test_increasing_atr(self):
        """Increasing ATR → Q90 increases."""
        atr = np.arange(1, 201, dtype=np.float64)
        q90 = rolling_atr_percentile(atr, window=50, q=90)
        # Q90 should increase monotonically once window is filled
        valid = q90[49:]
        diffs = np.diff(valid)
        assert np.all(diffs >= 0)


# =========================================================================
# compute_training_mean
# =========================================================================


class TestTrainingMean:
    def test_basic(self):
        """Training mean of constant array = that constant."""
        q90 = np.full(500, 1000.0)
        q90[:50] = np.nan
        mean, start, end = compute_training_mean(q90, train_days=100)
        assert mean == pytest.approx(1000.0)
        assert start == 50
        assert end == 150

    def test_all_nan(self):
        """All NaN → returns nan."""
        q90 = np.full(100, np.nan)
        mean, start, end = compute_training_mean(q90, train_days=50)
        assert np.isnan(mean)

    def test_short_array(self):
        """Array shorter than train_days → uses what's available."""
        q90 = np.array([100.0, 200.0, 300.0])
        mean, start, end = compute_training_mean(q90, train_days=100)
        assert mean == pytest.approx(200.0)
        assert start == 0
        assert end == 3


# =========================================================================
# classify_alerts
# =========================================================================


class TestClassifyAlerts:
    def test_all_normal(self):
        """Low MDD and low ATR ratio → all NORMAL."""
        mdd = np.full(10, 0.10)
        atr_ratio = np.full(10, 0.80)
        alerts = classify_alerts(mdd, atr_ratio)
        assert np.all(alerts == 0)

    def test_amber_mdd(self):
        """MDD just above AMBER threshold → AMBER."""
        mdd = np.full(10, 0.56)
        atr_ratio = np.full(10, 1.0)
        alerts = classify_alerts(mdd, atr_ratio)
        assert np.all(alerts == 1)

    def test_amber_atr(self):
        """ATR ratio just above AMBER threshold → AMBER."""
        mdd = np.full(10, 0.10)
        atr_ratio = np.full(10, 1.41)
        alerts = classify_alerts(mdd, atr_ratio)
        assert np.all(alerts == 1)

    def test_red_mdd(self):
        """MDD above RED threshold → RED (supersedes AMBER)."""
        mdd = np.full(10, 0.66)
        atr_ratio = np.full(10, 1.0)
        alerts = classify_alerts(mdd, atr_ratio)
        assert np.all(alerts == 2)

    def test_red_atr(self):
        """ATR ratio above RED threshold → RED."""
        mdd = np.full(10, 0.10)
        atr_ratio = np.full(10, 1.61)
        alerts = classify_alerts(mdd, atr_ratio)
        assert np.all(alerts == 2)

    def test_red_supersedes_amber(self):
        """Both AMBER MDD and RED ATR → RED wins."""
        mdd = np.full(10, 0.56)      # AMBER-level MDD
        atr_ratio = np.full(10, 1.61)  # RED-level ATR
        alerts = classify_alerts(mdd, atr_ratio)
        assert np.all(alerts == 2)

    def test_nan_inputs_normal(self):
        """NaN values → NORMAL."""
        mdd = np.full(10, np.nan)
        atr_ratio = np.full(10, np.nan)
        alerts = classify_alerts(mdd, atr_ratio)
        assert np.all(alerts == 0)

    def test_mixed(self):
        """Mixed: NORMAL, AMBER, RED sequence."""
        mdd = np.array([0.10, 0.56, 0.66, 0.30, 0.10])
        atr_ratio = np.array([1.0, 1.0, 1.0, 1.41, 1.61])
        alerts = classify_alerts(mdd, atr_ratio)
        assert list(alerts) == [0, 1, 2, 1, 2]

    def test_boundary_exactly_at_threshold(self):
        """Exactly at threshold → should NOT trigger (strict >)."""
        mdd = np.array([AMBER_MDD, RED_MDD])
        atr_ratio = np.array([1.0, 1.0])
        alerts = classify_alerts(mdd, atr_ratio)
        assert alerts[0] == 0  # exactly 0.55 → not > 0.55
        assert alerts[1] == 1  # exactly 0.65 → not > 0.65, but > 0.55 → AMBER


# =========================================================================
# extract_episodes
# =========================================================================


class TestExtractEpisodes:
    def test_no_episodes(self):
        """All NORMAL → no episodes."""
        alerts = np.zeros(10, dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == []

    def test_single_episode(self):
        """Single RED block."""
        alerts = np.array([0, 0, 2, 2, 2, 0, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == [(2, 4)]

    def test_multiple_episodes(self):
        """Two separate RED blocks."""
        alerts = np.array([0, 2, 2, 0, 0, 2, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == [(1, 2), (5, 5)]

    def test_episode_at_end(self):
        """RED block extending to array end."""
        alerts = np.array([0, 0, 2, 2, 2], dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == [(2, 4)]

    def test_amber_level_includes_red(self):
        """Level=1 (AMBER) should include RED bars too (>= level)."""
        alerts = np.array([0, 1, 2, 2, 1, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=1)
        assert eps == [(1, 4)]

    def test_red_level_excludes_amber(self):
        """Level=2 (RED) should NOT include AMBER-only bars."""
        alerts = np.array([0, 1, 1, 2, 2, 1, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == [(3, 4)]


# =========================================================================
# ATR D1 computation
# =========================================================================


class TestATRD1:
    def test_constant_bars(self):
        """Constant OHLC → ATR = 0 (no range)."""
        n = 50
        close = np.full(n, 100.0)
        high = np.full(n, 100.0)
        low = np.full(n, 100.0)
        atr = _atr_d1(high, low, close, period=14)
        # After warmup, ATR should be 0
        assert atr[13] == pytest.approx(0.0, abs=1e-10)
        assert atr[49] == pytest.approx(0.0, abs=1e-10)

    def test_atr_positive_for_volatile(self):
        """Volatile data → ATR > 0."""
        np.random.seed(42)
        close = 100.0 + np.cumsum(np.random.randn(100) * 5)
        high = close + np.abs(np.random.randn(100) * 2)
        low = close - np.abs(np.random.randn(100) * 2)
        atr = _atr_d1(high, low, close, period=14)
        assert np.all(np.isnan(atr[:13]))
        assert np.all(atr[13:] > 0)

    def test_atr_nan_before_period(self):
        """First period-1 bars should be NaN."""
        close = np.arange(1, 31, dtype=np.float64)
        high = close + 1
        low = close - 1
        atr = _atr_d1(high, low, close, period=14)
        assert np.all(np.isnan(atr[:13]))
        assert not np.isnan(atr[13])


# =========================================================================
# Integration: end-to-end on synthetic data
# =========================================================================


class TestIntegrationSynthetic:
    def test_crash_triggers_red(self):
        """A 70% crash should trigger RED via MDD channel."""
        n = 400
        # Stable for 200 days, then crash 70%, then recover
        close = np.concatenate([
            np.full(200, 100.0),
            np.linspace(100, 30, 50),     # crash
            np.linspace(30, 60, 150),      # partial recovery
        ])
        high = close * 1.01
        low = close * 0.99

        atr = _atr_d1(high, low, close, 14)
        r_mdd = rolling_mdd(close, window=180)
        r_q90 = rolling_atr_percentile(atr, window=180, q=90)
        train_mean, _, _ = compute_training_mean(r_q90, train_days=180)

        atr_ratio = np.full(n, np.nan)
        valid = ~np.isnan(r_q90) & (train_mean > 0)
        atr_ratio[valid] = r_q90[valid] / train_mean

        alerts = classify_alerts(r_mdd, atr_ratio)

        # During/after the crash, should see RED alerts
        # The crash reaches 70% MDD which is > 65% RED threshold
        assert np.any(alerts == 2), "Expected RED alert during 70% crash"

    def test_mild_drop_no_red(self):
        """A 30% drop should NOT trigger RED (below 55% AMBER)."""
        n = 400
        close = np.concatenate([
            np.full(200, 100.0),
            np.linspace(100, 70, 50),
            np.full(150, 70.0),
        ])
        high = close * 1.005
        low = close * 0.995

        atr = _atr_d1(high, low, close, 14)
        r_mdd = rolling_mdd(close, window=180)
        r_q90 = rolling_atr_percentile(atr, window=180, q=90)
        train_mean, _, _ = compute_training_mean(r_q90, train_days=180)

        atr_ratio = np.full(n, np.nan)
        valid = ~np.isnan(r_q90) & (train_mean > 0)
        atr_ratio[valid] = r_q90[valid] / train_mean

        alerts = classify_alerts(r_mdd, atr_ratio)

        # 30% drop → MDD ≈ 0.30, well below AMBER 0.55
        assert not np.any(alerts == 2), "Should not trigger RED for 30% drop"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
