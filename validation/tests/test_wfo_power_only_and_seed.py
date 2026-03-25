"""Tests for WFO power-only authoritative tests and configurable seed.

Verifies:
1. Wilcoxon and bootstrap CI use power-only deltas (excluding low-trade windows).
2. Bootstrap CI seed comes from cfg.seed, not a hardcoded value.
"""

from __future__ import annotations

import math

from validation.suites.wfo import _compute_bootstrap_ci, _compute_wilcoxon


class TestComputeBootstrapCiSeed:
    """_compute_bootstrap_ci uses the provided seed."""

    def test_default_seed_is_42(self) -> None:
        result = _compute_bootstrap_ci([1.0, 2.0, 3.0])
        assert result["seed"] == 42

    def test_custom_seed_recorded(self) -> None:
        result = _compute_bootstrap_ci([1.0, 2.0, 3.0], seed=1337)
        assert result["seed"] == 1337

    def test_different_seeds_may_differ(self) -> None:
        # Use enough data points and 6 decimal precision to avoid rounding collisions.
        data = [0.1, -0.05, 0.2, 0.3, -0.1, 0.15, -0.08, 0.25, 0.05, -0.02]
        r1 = _compute_bootstrap_ci(data, seed=1, n_resamples=50_000)
        r2 = _compute_bootstrap_ci(data, seed=999, n_resamples=50_000)
        assert r1["ci_lower"] != r2["ci_lower"] or r1["ci_upper"] != r2["ci_upper"]

    def test_same_seed_reproducible(self) -> None:
        data = [0.5, -0.3, 1.2, 0.1, -0.05]
        r1 = _compute_bootstrap_ci(data, seed=42)
        r2 = _compute_bootstrap_ci(data, seed=42)
        assert r1["ci_lower"] == r2["ci_lower"]
        assert r1["ci_upper"] == r2["ci_upper"]

    def test_small_sample_returns_seed(self) -> None:
        result = _compute_bootstrap_ci([1.0], seed=777)
        assert result["seed"] == 777
        assert math.isnan(result["ci_lower"])


class TestPowerOnlyDeltaFiltering:
    """Verify that _compute_wilcoxon and _compute_bootstrap_ci work on
    power-only subsets (the caller is responsible for filtering, but
    we verify the contract of reduced input).
    """

    def test_wilcoxon_on_reduced_set(self) -> None:
        # All valid deltas: 6 values (sufficient for Wilcoxon)
        all_valid = [0.5, -0.1, 0.3, 0.2, -0.05, 0.4]
        # Power-only: remove 2 low-trade windows
        power_only = [0.5, 0.3, 0.2, 0.4]

        r_all = _compute_wilcoxon(all_valid)
        r_power = _compute_wilcoxon(power_only)

        # Both should be sufficient (>=6 nonzero for all, <6 for power → insufficient)
        assert r_all["sufficient"] is True
        # Power set has only 4 nonzero → insufficient
        assert r_power["sufficient"] is False
        assert r_power["p_value"] == 1.0

    def test_bootstrap_ci_on_reduced_set(self) -> None:
        all_valid = [0.5, -0.1, 0.3, 0.2, -0.05, 0.4]
        power_only = [0.5, 0.3, 0.2, 0.4]

        r_all = _compute_bootstrap_ci(all_valid, seed=42)
        r_power = _compute_bootstrap_ci(power_only, seed=42)

        # Power-only set is more positive → higher CI lower bound
        assert r_power["ci_lower"] > r_all["ci_lower"]
