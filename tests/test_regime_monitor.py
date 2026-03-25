"""Tests for production monitoring/regime_monitor.py (PROMOTED 2026-03-09).

Covers all 5 public functions:
  - rolling_mdd: rolling max-drawdown
  - classify_alerts: MDD → NORMAL/AMBER/RED
  - extract_episodes: contiguous alert episodes
  - map_d1_alert_to_h4: causal D1→H4 mapping
  - compute_regime: top-level orchestrator
  - is_red: bar-level query
"""

import numpy as np
import pytest

from monitoring.regime_monitor import (
    ALERT_NAMES,
    AMBER_MDD_6M,
    AMBER_MDD_12M,
    RED_MDD_6M,
    RED_MDD_12M,
    ROLL_6M,
    ROLL_12M,
    rolling_mdd,
    classify_alerts,
    extract_episodes,
    map_d1_alert_to_h4,
    compute_regime,
    is_red,
)


# =========================================================================
# Constants
# =========================================================================


class TestConstants:
    def test_alert_names_complete(self):
        assert ALERT_NAMES == {0: "NORMAL", 1: "AMBER", 2: "RED"}

    def test_thresholds_ordered(self):
        """AMBER thresholds must be strictly below RED."""
        assert AMBER_MDD_6M < RED_MDD_6M
        assert AMBER_MDD_12M < RED_MDD_12M

    def test_window_sizes(self):
        assert ROLL_6M == 180
        assert ROLL_12M == 360


# =========================================================================
# rolling_mdd
# =========================================================================


class TestRollingMDD:
    def test_flat_price_zero_drawdown(self):
        """Constant price → zero drawdown."""
        close = np.full(200, 100.0)
        mdd = rolling_mdd(close, window=180)
        # First 179 bars should be NaN
        assert np.all(np.isnan(mdd[:179]))
        # Bar 179 onward: 0.0
        assert np.allclose(mdd[179:], 0.0)

    def test_monotonic_up_zero_drawdown(self):
        """Monotonically increasing price → zero drawdown."""
        close = np.arange(1.0, 201.0)
        mdd = rolling_mdd(close, window=50)
        valid = mdd[49:]
        assert np.allclose(valid, 0.0)

    def test_known_drawdown_50pct(self):
        """Price 100 → 50 → known 50% drawdown."""
        n = 50
        close = np.full(n, 100.0)
        close[n // 2 :] = 50.0
        mdd = rolling_mdd(close, window=n)
        assert mdd[-1] == pytest.approx(0.50, abs=1e-10)

    def test_drawdown_recovers(self):
        """If price drops then recovers within window, MDD reflects the worst."""
        close = np.full(100, 100.0)
        close[30] = 60.0  # 40% drawdown
        close[31:] = 100.0  # immediate recovery
        mdd = rolling_mdd(close, window=50)
        # At bar 50+ the drop at bar 30 is still inside window
        assert mdd[50] == pytest.approx(0.40, abs=1e-10)

    def test_output_length(self):
        close = np.random.default_rng(42).uniform(90, 110, size=500)
        mdd = rolling_mdd(close, window=180)
        assert len(mdd) == 500

    def test_nan_prefix_correct_length(self):
        close = np.random.default_rng(42).uniform(90, 110, size=300)
        mdd = rolling_mdd(close, window=180)
        assert np.sum(np.isnan(mdd)) == 179

    def test_mdd_non_negative(self):
        close = np.random.default_rng(42).uniform(50, 150, size=500)
        mdd = rolling_mdd(close, window=100)
        valid = mdd[~np.isnan(mdd)]
        assert np.all(valid >= 0.0)
        assert np.all(valid <= 1.0)

    def test_short_array_all_nan(self):
        """Array shorter than window → all NaN."""
        close = np.full(10, 100.0)
        mdd = rolling_mdd(close, window=20)
        assert np.all(np.isnan(mdd))


# =========================================================================
# classify_alerts
# =========================================================================


class TestClassifyAlerts:
    def test_normal_below_all_thresholds(self):
        mdd_6m = np.array([0.10, 0.20, 0.44])
        mdd_12m = np.array([0.10, 0.30, 0.59])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert np.all(alerts == 0)

    def test_amber_6m_trigger(self):
        """6m MDD just above AMBER threshold → AMBER."""
        mdd_6m = np.array([0.46])
        mdd_12m = np.array([0.30])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert alerts[0] == 1

    def test_amber_12m_trigger(self):
        """12m MDD just above AMBER threshold → AMBER."""
        mdd_6m = np.array([0.20])
        mdd_12m = np.array([0.61])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert alerts[0] == 1

    def test_red_6m_trigger(self):
        """6m MDD just above RED threshold → RED."""
        mdd_6m = np.array([0.56])
        mdd_12m = np.array([0.30])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert alerts[0] == 2

    def test_red_12m_trigger(self):
        """12m MDD just above RED threshold → RED."""
        mdd_6m = np.array([0.20])
        mdd_12m = np.array([0.71])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert alerts[0] == 2

    def test_red_overrides_amber(self):
        """Both RED and AMBER thresholds crossed → RED wins."""
        mdd_6m = np.array([0.56])  # RED
        mdd_12m = np.array([0.65])  # AMBER
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert alerts[0] == 2

    def test_nan_treated_as_zero(self):
        """NaN MDD values should be treated as 0 → NORMAL."""
        mdd_6m = np.array([np.nan])
        mdd_12m = np.array([np.nan])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert alerts[0] == 0

    def test_exact_threshold_not_triggered(self):
        """Threshold is strict > (not >=). At exactly 0.45 → NORMAL."""
        mdd_6m = np.array([AMBER_MDD_6M])
        mdd_12m = np.array([0.0])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        assert alerts[0] == 0  # exactly at threshold → not triggered

    def test_mixed_sequence(self):
        mdd_6m = np.array([0.10, 0.46, 0.56, 0.30, 0.10])
        mdd_12m = np.array([0.10, 0.30, 0.30, 0.61, 0.10])
        alerts = classify_alerts(mdd_6m, mdd_12m)
        expected = np.array([0, 1, 2, 1, 0], dtype=np.int8)
        np.testing.assert_array_equal(alerts, expected)


# =========================================================================
# extract_episodes
# =========================================================================


class TestExtractEpisodes:
    def test_no_episodes(self):
        alerts = np.array([0, 0, 0, 0], dtype=np.int8)
        assert extract_episodes(alerts, level=1) == []

    def test_single_episode(self):
        alerts = np.array([0, 1, 1, 1, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=1)
        assert eps == [(1, 3)]

    def test_episode_at_end(self):
        """Episode that runs to the end of the array."""
        alerts = np.array([0, 0, 2, 2], dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == [(2, 3)]

    def test_episode_at_start(self):
        alerts = np.array([2, 2, 0, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == [(0, 1)]

    def test_multiple_episodes(self):
        alerts = np.array([0, 1, 1, 0, 0, 1, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=1)
        assert eps == [(1, 2), (5, 5)]

    def test_level_filters(self):
        """Level 2 ignores AMBER (1), only picks up RED (2)."""
        alerts = np.array([0, 1, 1, 2, 2, 1, 0], dtype=np.int8)
        eps_red = extract_episodes(alerts, level=2)
        assert eps_red == [(3, 4)]

    def test_level_1_includes_red(self):
        """Level 1 includes both AMBER and RED (>= 1)."""
        alerts = np.array([0, 1, 2, 1, 0], dtype=np.int8)
        eps = extract_episodes(alerts, level=1)
        assert eps == [(1, 3)]

    def test_full_array_episode(self):
        alerts = np.array([2, 2, 2], dtype=np.int8)
        eps = extract_episodes(alerts, level=2)
        assert eps == [(0, 2)]


# =========================================================================
# map_d1_alert_to_h4
# =========================================================================


class TestMapD1AlertToH4:
    def test_basic_mapping(self):
        """Each H4 bar gets the latest D1 alert closed strictly before it."""
        d1_alerts = np.array([0, 1, 2], dtype=np.int8)
        d1_ct = np.array([100, 200, 300])
        h4_ct = np.array([50, 100, 150, 200, 250, 300, 350])
        h4_alerts = map_d1_alert_to_h4(d1_alerts, d1_ct, h4_ct)
        # h4  50 → before d1[0] → 0 (default)
        # h4 100 → d1[0].ct == h4, not strictly before → 0 (default)
        # h4 150 → d1[0].ct=100 < 150 → d1[0] → 0
        # h4 200 → d1[1].ct == h4, stays d1[0] → 0
        # h4 250 → d1[1].ct=200 < 250 → d1[1] → 1
        # h4 300 → d1[2].ct == h4, stays d1[1] → 1
        # h4 350 → d1[2].ct=300 < 350 → d1[2] → 2
        expected = np.array([0, 0, 0, 0, 1, 1, 2], dtype=np.int8)
        np.testing.assert_array_equal(h4_alerts, expected)

    def test_output_length(self):
        d1_alerts = np.array([0, 1], dtype=np.int8)
        d1_ct = np.array([100, 200])
        h4_ct = np.arange(50, 300, 10)
        result = map_d1_alert_to_h4(d1_alerts, d1_ct, h4_ct)
        assert len(result) == len(h4_ct)

    def test_causal_no_future_leak(self):
        """H4 bar before any D1 close → should be 0 (default)."""
        d1_alerts = np.array([2], dtype=np.int8)
        d1_ct = np.array([200])
        h4_ct = np.array([50, 100, 150])
        result = map_d1_alert_to_h4(d1_alerts, d1_ct, h4_ct)
        np.testing.assert_array_equal(result, np.array([0, 0, 0], dtype=np.int8))


# =========================================================================
# compute_regime
# =========================================================================


class TestComputeRegime:
    def test_output_keys(self):
        close = np.full(400, 100.0)
        result = compute_regime(close)
        assert set(result.keys()) == {"mdd_6m", "mdd_12m", "alerts", "alert_counts"}

    def test_flat_price_all_normal(self):
        """Flat price → no drawdown → all NORMAL."""
        close = np.full(400, 100.0)
        result = compute_regime(close)
        assert result["alert_counts"]["red"] == 0
        assert result["alert_counts"]["amber"] == 0

    def test_alert_counts_sum(self):
        close = np.random.default_rng(42).uniform(50, 150, size=500)
        result = compute_regime(close)
        counts = result["alert_counts"]
        assert counts["normal"] + counts["amber"] + counts["red"] == counts["total"]
        assert counts["total"] == 500

    def test_arrays_correct_length(self):
        close = np.full(400, 100.0)
        result = compute_regime(close)
        assert len(result["mdd_6m"]) == 400
        assert len(result["mdd_12m"]) == 400
        assert len(result["alerts"]) == 400

    def test_crash_triggers_red(self):
        """80% price crash should trigger RED."""
        close = np.full(400, 100.0)
        close[200:] = 20.0  # 80% drop
        result = compute_regime(close)
        # After the crash, 6m MDD should be 80% → RED
        assert result["alert_counts"]["red"] > 0


# =========================================================================
# is_red
# =========================================================================


class TestIsRed:
    def test_red_true(self):
        alerts = np.array([0, 1, 2, 0], dtype=np.int8)
        assert is_red(alerts, 2) is True

    def test_not_red(self):
        alerts = np.array([0, 1, 2, 0], dtype=np.int8)
        assert is_red(alerts, 0) is False
        assert is_red(alerts, 1) is False


# =========================================================================
# Integration: rolling_mdd → classify_alerts → extract_episodes
# =========================================================================


class TestIntegration:
    def test_bear_market_pipeline(self):
        """Simulate a bear market and verify full pipeline."""
        n = 500
        close = np.full(n, 100.0)
        # Bull: bars 0-249, Bear: bars 250-349 (drop to 30), Recovery: 350+
        close[250:350] = np.linspace(100, 30, 100)
        close[350:] = np.linspace(30, 90, n - 350)

        mdd_6m = rolling_mdd(close, ROLL_6M)
        mdd_12m = rolling_mdd(close, ROLL_12M)
        alerts = classify_alerts(mdd_6m, mdd_12m)

        red_episodes = extract_episodes(alerts, level=2)
        # Should have at least one RED episode during the crash
        assert len(red_episodes) >= 1
        # RED episode should start after bar 250 (when crash begins)
        first_red_start = red_episodes[0][0]
        assert first_red_start >= ROLL_6M  # needs history

    def test_no_crash_no_alerts(self):
        """Gently rising price → no AMBER or RED."""
        close = np.linspace(100, 200, 500)
        result = compute_regime(close)
        assert result["alert_counts"]["red"] == 0
        assert result["alert_counts"]["amber"] == 0
