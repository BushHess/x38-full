"""Minimal research-only tests for Step 4: run_frontier.py.

Tests:
1. Deterministic regeneration — same input → same output
2. Linearity check — Sharpe quasi-constant, MDD/CAGR monotonic
3. No leverage — k ∈ [0, 1] enforced
4. Correct interpolation — scaled returns match k * original
5. No production mutation — no imports that modify external state
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# ── Path setup ────────────────────────────────────────────────────────────
_TESTS = Path(__file__).resolve().parent
_SRC = _TESTS.parent / "src"
_REPO = _TESTS.parents[3]

for p in [str(_SRC), str(_REPO)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from run_frontier import (
    scale_returns,
    returns_to_equity,
    equity_to_returns,
    compute_metrics,
    linearity_check,
    find_k_for_target_mdd,
)


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def synthetic_returns():
    """Synthetic return stream with known properties."""
    np.random.seed(42)
    n = 2000
    r = np.zeros(n)
    r[1:] = np.random.normal(0.0003, 0.01, n - 1)  # ~7% annual, ~47% vol
    return r


@pytest.fixture
def synthetic_equity(synthetic_returns):
    """Equity curve from synthetic returns."""
    return returns_to_equity(synthetic_returns)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: DETERMINISTIC REGENERATION
# ═══════════════════════════════════════════════════════════════════════════

class TestDeterministicRegeneration:

    def test_returns_to_equity_roundtrip(self, synthetic_equity):
        """eq → returns → eq must be bit-identical."""
        r = equity_to_returns(synthetic_equity)
        eq2 = returns_to_equity(r)
        np.testing.assert_allclose(eq2, synthetic_equity, rtol=1e-12)

    def test_scaled_returns_deterministic(self, synthetic_returns):
        """Same k must produce identical scaled returns."""
        r1 = scale_returns(synthetic_returns, 0.5)
        r2 = scale_returns(synthetic_returns, 0.5)
        np.testing.assert_array_equal(r1, r2)

    def test_metrics_deterministic(self, synthetic_returns):
        """Same input must produce identical metrics."""
        rs = scale_returns(synthetic_returns, 0.5)
        eq = returns_to_equity(rs)
        m1 = compute_metrics(eq, rs, 0.5, 0.5, 100.0, 0.05)
        m2 = compute_metrics(eq, rs, 0.5, 0.5, 100.0, 0.05)
        for key in m1:
            if isinstance(m1[key], float):
                if math.isnan(m1[key]):
                    assert math.isnan(m2[key]), f"{key} NaN mismatch"
                else:
                    assert m1[key] == m2[key], f"{key}: {m1[key]} != {m2[key]}"


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: LINEARITY CHECK
# ═══════════════════════════════════════════════════════════════════════════

class TestLinearityCheck:

    def test_sharpe_quasi_constant(self, synthetic_returns):
        """Sharpe should be approximately constant across k (compound effect small)."""
        lc = linearity_check(synthetic_returns, 0.5, 100.0, 0.05)
        assert lc["sharpe_quasi_constant"], (
            f"Sharpe range too large: {lc['sharpe_pct_range']:.1f}%"
        )

    def test_mdd_monotonic(self, synthetic_returns):
        """MDD must be monotonically increasing with k."""
        lc = linearity_check(synthetic_returns, 0.5, 100.0, 0.05)
        assert lc["mdd_monotonic"], f"MDD not monotonic: {lc['mdds']}"

    def test_cagr_monotonic(self, synthetic_returns):
        """CAGR must be monotonically increasing with k for positive-return streams."""
        lc = linearity_check(synthetic_returns, 0.5, 100.0, 0.05)
        assert lc["cagr_monotonic"], f"CAGR not monotonic: {lc['cagrs']}"

    def test_scaled_sharpe_equals_original(self, synthetic_returns):
        """For pure scaling, Sharpe(k*r) ≈ Sharpe(r) because mean/std ratio is constant."""
        eq_full = returns_to_equity(synthetic_returns)
        m_full = compute_metrics(eq_full, synthetic_returns, 1.0, 0.5, 100.0, 0.05)

        rs_half = scale_returns(synthetic_returns, 0.5)
        eq_half = returns_to_equity(rs_half)
        m_half = compute_metrics(eq_half, rs_half, 0.5, 0.5, 100.0, 0.05)

        # Sharpe should be exactly equal for simple returns scaling
        # (mean and std both scale by k, ratio preserved)
        assert abs(m_full["sharpe"] - m_half["sharpe"]) < 0.001, (
            f"Sharpe diverged: full={m_full['sharpe']:.6f} half={m_half['sharpe']:.6f}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: NO LEVERAGE
# ═══════════════════════════════════════════════════════════════════════════

class TestNoLeverage:

    def test_k_zero(self, synthetic_returns):
        """k=0 must produce flat equity (all cash)."""
        rs = scale_returns(synthetic_returns, 0.0)
        eq = returns_to_equity(rs)
        np.testing.assert_allclose(eq, np.ones_like(eq), atol=1e-14)

    def test_k_one(self, synthetic_returns):
        """k=1 must reproduce original equity."""
        eq_orig = returns_to_equity(synthetic_returns)
        rs = scale_returns(synthetic_returns, 1.0)
        eq_scaled = returns_to_equity(rs)
        np.testing.assert_allclose(eq_scaled, eq_orig, rtol=1e-14)

    def test_k_above_one_raises(self, synthetic_returns):
        """k > 1 must raise AssertionError."""
        with pytest.raises(AssertionError):
            scale_returns(synthetic_returns, 1.5)

    def test_k_negative_raises(self, synthetic_returns):
        """k < 0 must raise AssertionError."""
        with pytest.raises(AssertionError):
            scale_returns(synthetic_returns, -0.1)

    def test_mdd_at_k_zero(self, synthetic_returns):
        """MDD at k=0 must be 0 (no drawdown on flat equity)."""
        rs = scale_returns(synthetic_returns, 0.0)
        eq = returns_to_equity(rs)
        m = compute_metrics(eq, rs, 0.0, 0.5, 100.0, 0.05)
        assert m["mdd"] < 1e-10


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: CORRECT INTERPOLATION
# ═══════════════════════════════════════════════════════════════════════════

class TestCorrectInterpolation:

    def test_scaled_returns_are_k_times_original(self, synthetic_returns):
        """r_scaled must equal k * r_original exactly."""
        k = 0.37
        rs = scale_returns(synthetic_returns, k)
        expected = k * synthetic_returns
        np.testing.assert_array_equal(rs, expected)

    def test_find_k_for_target_mdd_accuracy(self, synthetic_returns):
        """Binary search must find k within tolerance."""
        target = 0.05
        k = find_k_for_target_mdd(synthetic_returns, target, tol=0.001)
        rs = scale_returns(synthetic_returns, k)
        eq = returns_to_equity(rs)
        rm = np.maximum.accumulate(eq)
        dd = 1.0 - eq / np.maximum(rm, 1e-12)
        actual_mdd = float(np.max(dd))
        assert abs(actual_mdd - target) < 0.002, (
            f"MDD target={target}, actual={actual_mdd}, k={k}"
        )

    def test_k_half_mdd_less_than_full(self, synthetic_returns):
        """MDD at k=0.5 must be less than MDD at k=1.0."""
        eq_full = returns_to_equity(synthetic_returns)
        rs_half = scale_returns(synthetic_returns, 0.5)
        eq_half = returns_to_equity(rs_half)

        rm_full = np.maximum.accumulate(eq_full)
        mdd_full = float(np.max(1.0 - eq_full / np.maximum(rm_full, 1e-12)))
        rm_half = np.maximum.accumulate(eq_half)
        mdd_half = float(np.max(1.0 - eq_half / np.maximum(rm_half, 1e-12)))

        assert mdd_half < mdd_full


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: NO PRODUCTION MUTATION
# ═══════════════════════════════════════════════════════════════════════════

class TestNoProductionMutation:

    def test_scale_does_not_mutate_input(self, synthetic_returns):
        """scale_returns must not modify the input array."""
        orig = synthetic_returns.copy()
        _ = scale_returns(synthetic_returns, 0.5)
        np.testing.assert_array_equal(synthetic_returns, orig)

    def test_equity_to_returns_does_not_mutate(self, synthetic_equity):
        """equity_to_returns must not modify the input array."""
        orig = synthetic_equity.copy()
        _ = equity_to_returns(synthetic_equity)
        np.testing.assert_array_equal(synthetic_equity, orig)

    def test_metrics_returns_only_scalars(self, synthetic_returns):
        """compute_metrics must return only scalar values (no arrays)."""
        eq = returns_to_equity(synthetic_returns)
        m = compute_metrics(eq, synthetic_returns, 1.0, 0.5, 100.0, 0.05)
        for k, v in m.items():
            assert isinstance(v, (int, float, str, bool, type(None))), (
                f"Key {k} has non-scalar type {type(v)}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
