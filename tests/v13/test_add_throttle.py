"""Unit tests for v13 add-throttle behavior."""

from __future__ import annotations

import pytest

from strategies.v13_add_throttle.strategy import V13AddThrottleConfig
from strategies.v13_add_throttle.strategy import V13AddThrottleStrategy
from validation.config_audit import ConfigProxy
from validation.config_audit import tracker_for_config_obj
from validation.strategy_factory import STRATEGY_REGISTRY


def test_validation_registry_contains_v13_add_throttle() -> None:
    assert "v13_add_throttle" in STRATEGY_REGISTRY
    strategy_cls, config_cls = STRATEGY_REGISTRY["v13_add_throttle"]
    assert strategy_cls is V13AddThrottleStrategy
    assert config_cls is V13AddThrottleConfig


def test_flat_first_entry_not_throttled_even_when_dd_depth_high() -> None:
    strategy = V13AddThrottleStrategy(
        V13AddThrottleConfig(
            max_add_per_bar=0.35,
            add_throttle_dd1=0.08,
            add_throttle_dd2=0.18,
            add_throttle_mult=0.20,
        )
    )
    allowed_add = strategy._add_cap_with_throttle(
        position_exposure=0.0,
        dd_depth=0.30,
    )
    assert allowed_add == 0.35


def test_in_position_add_cap_is_scaled_between_dd1_and_dd2() -> None:
    strategy = V13AddThrottleStrategy(
        V13AddThrottleConfig(
            max_add_per_bar=0.40,
            add_throttle_dd1=0.08,
            add_throttle_dd2=0.18,
            add_throttle_mult=0.25,
        )
    )
    allowed_add = strategy._add_cap_with_throttle(
        position_exposure=0.50,
        dd_depth=0.12,
    )
    assert allowed_add == 0.10


def test_in_position_adds_blocked_when_dd_depth_reaches_dd2() -> None:
    strategy = V13AddThrottleStrategy(
        V13AddThrottleConfig(
            max_add_per_bar=0.40,
            add_throttle_dd1=0.08,
            add_throttle_dd2=0.18,
            add_throttle_mult=0.25,
        )
    )
    allowed_add = strategy._add_cap_with_throttle(
        position_exposure=0.30,
        dd_depth=0.20,
    )
    assert allowed_add == 0.0


def test_config_tracking_marks_new_throttle_fields_as_used() -> None:
    cfg = V13AddThrottleConfig()
    tracker = tracker_for_config_obj(cfg, label="v13")
    assert tracker is not None

    strategy = V13AddThrottleStrategy(ConfigProxy(cfg, tracker))
    _ = strategy._add_cap_with_throttle(
        position_exposure=0.50,
        dd_depth=0.12,
    )

    assert "add_throttle_dd1" in tracker.used_fields
    assert "add_throttle_dd2" in tracker.used_fields
    assert "add_throttle_mult" in tracker.used_fields


def test_add_throttle_stats_default_zero_without_attempts() -> None:
    strategy = V13AddThrottleStrategy(V13AddThrottleConfig())
    stats = strategy.get_add_throttle_stats()

    assert stats["add_attempt_count"] == 0
    assert stats["add_allowed_count"] == 0
    assert stats["add_blocked_count"] == 0
    assert stats["throttle_activation_rate"] == 0.0
    assert stats["mean_dd_depth_when_blocked"] == 0.0
    assert stats["p90_dd_depth_when_blocked"] == 0.0


def test_add_throttle_stats_compute_blocked_depth_summary() -> None:
    strategy = V13AddThrottleStrategy(V13AddThrottleConfig())
    strategy._add_attempt_count = 5
    strategy._add_allowed_count = 2
    strategy._add_blocked_count = 3
    strategy._blocked_dd_depths = [0.10, 0.20, 0.30]

    stats = strategy.get_add_throttle_stats()

    assert stats["add_attempt_count"] == 5
    assert stats["add_allowed_count"] == 2
    assert stats["add_blocked_count"] == 3
    assert stats["throttle_activation_rate"] == pytest.approx(0.6)
    assert stats["mean_dd_depth_when_blocked"] == pytest.approx(0.2)
    assert stats["p90_dd_depth_when_blocked"] == pytest.approx(0.28)
