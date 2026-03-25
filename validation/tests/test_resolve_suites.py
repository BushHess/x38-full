"""Tests for resolve_suites() suite-membership contract.

Verifies that quality suites (data_integrity, cost_sweep, invariants,
churn_metrics) are NOT auto-added to suite groups that don't include them,
even when their corresponding config toggles default to True/truthy.
"""

from __future__ import annotations

from pathlib import Path

from validation.config import SUITE_GROUPS, ValidationConfig, resolve_suites


def _cfg(**overrides) -> ValidationConfig:
    """Build a minimal ValidationConfig with defaults."""
    base = dict(
        strategy_name="vtrend",
        baseline_name="vtrend",
        config_path=Path("/tmp/a.yaml"),
        baseline_config_path=Path("/tmp/b.yaml"),
        outdir=Path("/tmp/out"),
        dataset=Path("/tmp/data.csv"),
    )
    base.update(overrides)
    return ValidationConfig(**base)


class TestBasicSuiteDoesNotAutoAdd:
    """Suite='basic' must resolve to exactly its group definition."""

    def test_basic_suite_matches_group(self) -> None:
        cfg = _cfg(suite="basic")
        resolved = resolve_suites(cfg)
        assert set(resolved) == set(SUITE_GROUPS["basic"])

    def test_basic_excludes_data_integrity(self) -> None:
        cfg = _cfg(suite="basic")
        resolved = resolve_suites(cfg)
        assert "data_integrity" not in resolved

    def test_basic_excludes_cost_sweep(self) -> None:
        cfg = _cfg(suite="basic")
        resolved = resolve_suites(cfg)
        assert "cost_sweep" not in resolved

    def test_basic_excludes_invariants(self) -> None:
        cfg = _cfg(suite="basic")
        resolved = resolve_suites(cfg)
        assert "invariants" not in resolved

    def test_basic_excludes_churn_metrics(self) -> None:
        cfg = _cfg(suite="basic")
        resolved = resolve_suites(cfg)
        assert "churn_metrics" not in resolved


class TestFullSuiteDoesNotAutoAdd:
    """Suite='full' must resolve to its group minus disabled toggles."""

    def test_full_suite_subset_of_group(self) -> None:
        cfg = _cfg(suite="full")
        resolved = resolve_suites(cfg)
        # sensitivity_grid defaults False → "sensitivity" is removed from group.
        expected = set(SUITE_GROUPS["full"]) - {"sensitivity"}
        assert set(resolved) == expected

    def test_full_excludes_data_integrity(self) -> None:
        cfg = _cfg(suite="full")
        resolved = resolve_suites(cfg)
        assert "data_integrity" not in resolved


class TestTradeSuiteDoesNotAutoAdd:
    """Suite='trade' must resolve to exactly its group definition."""

    def test_trade_suite_matches_group(self) -> None:
        cfg = _cfg(suite="trade")
        resolved = resolve_suites(cfg)
        assert set(resolved) == set(SUITE_GROUPS["trade"])


class TestAllSuiteIncludesQuality:
    """Suite='all' includes quality suites when toggles are on (default)."""

    def test_all_includes_data_integrity(self) -> None:
        cfg = _cfg(suite="all")
        resolved = resolve_suites(cfg)
        assert "data_integrity" in resolved

    def test_all_includes_invariants(self) -> None:
        cfg = _cfg(suite="all")
        resolved = resolve_suites(cfg)
        assert "invariants" in resolved

    def test_all_includes_cost_sweep(self) -> None:
        cfg = _cfg(suite="all")
        resolved = resolve_suites(cfg)
        assert "cost_sweep" in resolved

    def test_all_includes_churn_metrics(self) -> None:
        cfg = _cfg(suite="all")
        resolved = resolve_suites(cfg)
        assert "churn_metrics" in resolved

    def test_all_can_remove_data_integrity(self) -> None:
        cfg = _cfg(suite="all", data_integrity_check=False)
        resolved = resolve_suites(cfg)
        assert "data_integrity" not in resolved

    def test_all_can_remove_invariants(self) -> None:
        cfg = _cfg(suite="all", invariant_check=False)
        resolved = resolve_suites(cfg)
        assert "invariants" not in resolved


class TestExplicitOptIn:
    """Opt-in suites (default=False) CAN add beyond group."""

    def test_trade_level_adds_to_basic(self) -> None:
        cfg = _cfg(suite="basic", trade_level=True)
        resolved = resolve_suites(cfg)
        assert "trade_level" in resolved
        assert "backtest" in resolved

    def test_regression_guard_adds_to_basic(self) -> None:
        cfg = _cfg(suite="basic", regression_guard=True)
        resolved = resolve_suites(cfg)
        assert "regression_guard" in resolved

    def test_dd_episodes_adds_to_basic(self) -> None:
        cfg = _cfg(suite="basic", dd_episodes=True)
        resolved = resolve_suites(cfg)
        assert "dd_episodes" in resolved

    def test_overlay_adds_to_basic(self) -> None:
        cfg = _cfg(suite="basic", overlay_test=True)
        resolved = resolve_suites(cfg)
        assert "overlay" in resolved


class TestTriStateQualityToggles:
    """Tri-state quality toggles: None=follow group, True=force add, False=force remove."""

    def test_none_follows_basic_group_no_data_integrity(self) -> None:
        cfg = _cfg(suite="basic", data_integrity_check=None)
        resolved = resolve_suites(cfg)
        assert "data_integrity" not in resolved

    def test_none_follows_all_group_has_data_integrity(self) -> None:
        cfg = _cfg(suite="all", data_integrity_check=None)
        resolved = resolve_suites(cfg)
        assert "data_integrity" in resolved

    def test_true_forces_add_to_basic(self) -> None:
        cfg = _cfg(suite="basic", data_integrity_check=True)
        resolved = resolve_suites(cfg)
        assert "data_integrity" in resolved

    def test_false_forces_remove_from_all(self) -> None:
        cfg = _cfg(suite="all", data_integrity_check=False)
        resolved = resolve_suites(cfg)
        assert "data_integrity" not in resolved

    def test_invariant_true_adds_to_basic(self) -> None:
        cfg = _cfg(suite="basic", invariant_check=True)
        resolved = resolve_suites(cfg)
        assert "invariants" in resolved

    def test_churn_true_adds_to_basic(self) -> None:
        cfg = _cfg(suite="basic", churn_metrics=True)
        resolved = resolve_suites(cfg)
        assert "churn_metrics" in resolved

    def test_churn_false_removes_from_all(self) -> None:
        cfg = _cfg(suite="all", churn_metrics=False)
        resolved = resolve_suites(cfg)
        assert "churn_metrics" not in resolved


class TestOrderPreserved:
    """Resolved list follows SUITE_ORDER."""

    def test_all_suite_order(self) -> None:
        from validation.config import SUITE_ORDER

        cfg = _cfg(suite="all")
        resolved = resolve_suites(cfg)
        order_indices = [SUITE_ORDER.index(s) for s in resolved]
        assert order_indices == sorted(order_indices)
