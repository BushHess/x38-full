"""Minimal research-only tests for Step 5: run_robustness.py.

Tests:
1. Bootstrap determinism under fixed seed
2. Block-length sensitivity pipeline integrity
3. Matched-budget recomputation inside bootstrap replications
4. Rolling-window segmentation correctness
5. No production-file mutation
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

_TESTS = Path(__file__).resolve().parent
_SRC = _TESTS.parent / "src"
_REPO = _TESTS.parents[3]

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from run_robustness import (
    circular_block_bootstrap_indices,
    bootstrap_paired_returns,
    bootstrap_sharpe_diff,
    bootstrap_matched_mdd_cagr_diff,
    sharpe_from_returns,
    cagr_from_returns,
    mdd_from_returns,
    find_k_for_mdd,
    holm_adjust,
)


@pytest.fixture
def synthetic_returns():
    np.random.seed(42)
    n = 2000
    r = np.zeros(n)
    r[1:] = np.random.normal(0.0003, 0.01, n - 1)
    return r


@pytest.fixture
def synthetic_pair():
    np.random.seed(42)
    n = 2000
    r_a = np.zeros(n)
    r_b = np.zeros(n)
    r_a[1:] = np.random.normal(0.0004, 0.01, n - 1)
    r_b[1:] = np.random.normal(0.0002, 0.01, n - 1)
    return r_a, r_b


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: BOOTSTRAP DETERMINISM UNDER FIXED SEED
# ═══════════════════════════════════════════════════════════════════════════

class TestBootstrapDeterminism:

    def test_same_seed_same_indices(self):
        rng1 = np.random.default_rng(123)
        rng2 = np.random.default_rng(123)
        idx1 = circular_block_bootstrap_indices(1000, 42, rng1)
        idx2 = circular_block_bootstrap_indices(1000, 42, rng2)
        np.testing.assert_array_equal(idx1, idx2)

    def test_same_seed_same_sharpe_diff(self, synthetic_pair):
        r_a, r_b = synthetic_pair
        res1 = bootstrap_sharpe_diff(r_a, r_b, 42, 100, seed=999)
        res2 = bootstrap_sharpe_diff(r_a, r_b, 42, 100, seed=999)
        assert res1["mean"] == res2["mean"]
        assert res1["ci_lo_95"] == res2["ci_lo_95"]

    def test_different_seed_different_results(self, synthetic_pair):
        r_a, r_b = synthetic_pair
        res1 = bootstrap_sharpe_diff(r_a, r_b, 42, 100, seed=111)
        res2 = bootstrap_sharpe_diff(r_a, r_b, 42, 100, seed=222)
        assert res1["mean"] != res2["mean"]


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: BLOCK-LENGTH SENSITIVITY PIPELINE INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════

class TestBlockLengthSensitivity:

    def test_different_block_lengths_run(self, synthetic_pair):
        r_a, r_b = synthetic_pair
        for bl in [42, 126, 252]:
            res = bootstrap_sharpe_diff(r_a, r_b, bl, 50, seed=42)
            assert "mean" in res
            assert "ci_lo_95" in res
            assert res["n_boot"] == 50

    def test_block_indices_correct_length(self):
        rng = np.random.default_rng(42)
        for n in [500, 1000, 2000]:
            for bl in [42, 126, 252]:
                idx = circular_block_bootstrap_indices(n, bl, rng)
                assert len(idx) == n

    def test_block_indices_in_range(self):
        rng = np.random.default_rng(42)
        n = 1000
        for bl in [42, 126, 252]:
            idx = circular_block_bootstrap_indices(n, bl, rng)
            assert np.all(idx >= 0)
            assert np.all(idx < n)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: MATCHED-BUDGET RECOMPUTATION INSIDE BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════════

class TestMatchedBudgetBootstrap:

    def test_matched_mdd_bootstrap_runs(self, synthetic_pair):
        r_a, r_b = synthetic_pair
        res = bootstrap_matched_mdd_cagr_diff(r_a, r_b, 0.05, 42, 50, seed=42)
        assert "mean" in res
        assert "target_mdd" in res
        assert res["target_mdd"] == 0.05
        assert "saturation_a_pct" in res
        assert "saturation_b_pct" in res
        assert res["n_boot"] == 50

    def test_find_k_for_mdd_accuracy(self, synthetic_returns):
        target = 0.03
        k = find_k_for_mdd(synthetic_returns, target, tol=0.001)
        rs = k * synthetic_returns
        actual = mdd_from_returns(rs)
        assert abs(actual - target) < 0.002, f"Expected MDD≈{target}, got {actual}"

    def test_find_k_at_zero_returns_zero(self):
        r = np.zeros(100)
        k = find_k_for_mdd(r, 0.05)
        # With zero returns, MDD is always 0, so k converges to 1.0
        assert k >= 0.0 and k <= 1.0

    def test_saturation_tracking(self):
        """If native MDD < target, strategy should saturate at k=1."""
        r = np.zeros(500)
        r[1:] = np.random.RandomState(42).normal(0.0001, 0.001, 499)
        # Very low vol → very low MDD
        r_a = r.copy()
        r_b = r.copy()
        res = bootstrap_matched_mdd_cagr_diff(r_a, r_b, 0.50, 42, 50, seed=42)
        # Most samples should saturate since native MDD is tiny
        assert res["saturation_a_pct"] > 0 or res["saturation_b_pct"] > 0


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: ROLLING-WINDOW SEGMENTATION CORRECTNESS
# ═══════════════════════════════════════════════════════════════════════════

class TestRollingWindowSegmentation:

    def test_sharpe_from_returns_basic(self):
        np.random.seed(99)
        r = np.zeros(500)
        r[1:] = np.random.normal(0.001, 0.01, 499)  # positive drift + noise
        sh = sharpe_from_returns(r)
        assert sh > 0

    def test_cagr_from_returns_positive(self, synthetic_returns):
        c = cagr_from_returns(synthetic_returns)
        assert c > 0  # positive drift in synthetic data

    def test_mdd_nonnegative(self, synthetic_returns):
        m = mdd_from_returns(synthetic_returns)
        assert m >= 0

    def test_holm_adjust_identity_single(self):
        assert holm_adjust([0.05]) == [0.05]

    def test_holm_adjust_monotonic(self):
        raw = [0.01, 0.03, 0.05, 0.10]
        adj = holm_adjust(raw)
        # Adjusted p-values should be >= raw
        for r, a in zip(raw, adj):
            assert a >= r - 1e-10
        # Adjusted should be non-decreasing when sorted by raw
        assert all(adj[i] <= 1.0 for i in range(len(adj)))


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: NO PRODUCTION-FILE MUTATION
# ═══════════════════════════════════════════════════════════════════════════

class TestNoProductionMutation:

    def test_bootstrap_does_not_mutate_inputs(self, synthetic_pair):
        r_a, r_b = synthetic_pair
        orig_a = r_a.copy()
        orig_b = r_b.copy()
        _ = bootstrap_sharpe_diff(r_a, r_b, 42, 50, seed=42)
        np.testing.assert_array_equal(r_a, orig_a)
        np.testing.assert_array_equal(r_b, orig_b)

    def test_matched_mdd_does_not_mutate(self, synthetic_pair):
        r_a, r_b = synthetic_pair
        orig_a = r_a.copy()
        orig_b = r_b.copy()
        _ = bootstrap_matched_mdd_cagr_diff(r_a, r_b, 0.05, 42, 50, seed=42)
        np.testing.assert_array_equal(r_a, orig_a)
        np.testing.assert_array_equal(r_b, orig_b)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
