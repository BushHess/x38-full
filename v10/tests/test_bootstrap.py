"""Tests for block bootstrap confidence intervals."""

from __future__ import annotations

import numpy as np
import pytest

from v10.core.types import EquitySnap
from v10.research.bootstrap import BootstrapResult
from v10.research.bootstrap import block_bootstrap
from v10.research.bootstrap import paired_block_bootstrap
from v10.research.bootstrap import calc_cagr
from v10.research.bootstrap import calc_max_drawdown
from v10.research.bootstrap import calc_sharpe
from v10.research.bootstrap import run_bootstrap_suite


def _make_equity(n_bars: int = 500, drift: float = 0.0001, seed: int = 42) -> list[EquitySnap]:
    """Generate synthetic equity curve with known drift."""
    rng = np.random.default_rng(seed)
    returns = drift + 0.01 * rng.standard_normal(n_bars)
    navs = 10_000.0 * np.cumprod(1.0 + returns)
    navs = np.insert(navs, 0, 10_000.0)  # prepend initial
    equity = []
    for i, nav in enumerate(navs):
        equity.append(
            EquitySnap(
                close_time=i * 4 * 3600 * 1000,  # 4H bars
                nav_mid=float(nav),
                nav_liq=float(nav),
                cash=float(nav) * 0.5,
                btc_qty=0.0,
                exposure=0.5,
            )
        )
    return equity


class TestCalcSharpe:
    def test_positive_drift(self) -> None:
        rng = np.random.default_rng(42)
        returns = 0.001 + 0.01 * rng.standard_normal(1000)
        s = calc_sharpe(returns)
        assert s > 0

    def test_zero_vol(self) -> None:
        returns = np.full(100, 0.001)
        assert calc_sharpe(returns) == 0.0  # sigma < 1e-12

    def test_empty(self) -> None:
        assert calc_sharpe(np.array([])) == 0.0


class TestCalcCagr:
    def test_positive_drift(self) -> None:
        rng = np.random.default_rng(42)
        returns = 0.001 + 0.01 * rng.standard_normal(1000)
        c = calc_cagr(returns)
        assert c > 0

    def test_empty(self) -> None:
        assert calc_cagr(np.array([])) == 0.0


class TestCalcMaxDrawdown:
    def test_known_dd(self) -> None:
        # Returns: +10%, -20% → equity: 1.1, 0.88 → DD from 1.1 to 0.88 = 20%
        returns = np.array([0.10, -0.20])
        dd = calc_max_drawdown(returns)
        assert abs(dd - 20.0) < 0.01

    def test_empty(self) -> None:
        assert calc_max_drawdown(np.array([])) == 0.0


class TestBlockBootstrap:
    def test_basic_result_shape(self) -> None:
        equity = _make_equity(n_bars=500, drift=0.0001)
        result = block_bootstrap(equity, n_bootstrap=100, block_size=10)
        assert isinstance(result, BootstrapResult)
        assert result.metric_name == "sharpe"
        assert result.n_bootstrap == 100
        assert result.block_size == 10

    def test_ci_bounds_ordering(self) -> None:
        equity = _make_equity(n_bars=1000, drift=0.0002)
        result = block_bootstrap(equity, n_bootstrap=500)
        assert result.ci_lower < result.ci_upper

    def test_positive_drift_high_p_positive(self) -> None:
        """Strong positive drift → P(Sharpe > 0) should be high."""
        equity = _make_equity(n_bars=2000, drift=0.002)
        result = block_bootstrap(equity, n_bootstrap=500)
        assert result.p_positive > 0.90

    def test_reproducible_with_seed(self) -> None:
        equity = _make_equity(n_bars=500)
        r1 = block_bootstrap(equity, seed=123)
        r2 = block_bootstrap(equity, seed=123)
        assert r1.mean == r2.mean
        assert r1.ci_lower == r2.ci_lower

    def test_different_seeds_differ(self) -> None:
        equity = _make_equity(n_bars=500)
        r1 = block_bootstrap(equity, seed=1)
        r2 = block_bootstrap(equity, seed=2)
        assert r1.mean != r2.mean

    def test_too_short_raises(self) -> None:
        equity = _make_equity(n_bars=10)
        with pytest.raises(ValueError, match="too short"):
            block_bootstrap(equity, block_size=20)

    def test_custom_metric(self) -> None:
        equity = _make_equity(n_bars=500)
        result = block_bootstrap(equity, metric_fn=calc_cagr, metric_name="cagr_pct")
        assert result.metric_name == "cagr_pct"

    def test_p_positive_range(self) -> None:
        equity = _make_equity(n_bars=500)
        result = block_bootstrap(equity, n_bootstrap=200)
        assert 0.0 <= result.p_positive <= 1.0


class TestPairedBlockBootstrap:
    def test_paired_bootstrap_raises_on_length_mismatch(self) -> None:
        """Phase 1A: misaligned equity curves must raise ValueError."""
        equity_a = _make_equity(n_bars=500, seed=1)
        equity_b = _make_equity(n_bars=400, seed=2)
        with pytest.raises(ValueError, match="different lengths"):
            paired_block_bootstrap(equity_a, equity_b)

    def test_paired_bootstrap_raises_on_interior_timestamp_mismatch(self) -> None:
        """Regression: interior timestamp mismatches must be caught.

        Previously only first/last timestamps were checked, so curves with
        reordered interior timestamps (e.g., [0,2,1,3,4] vs [0,1,2,3,4])
        passed silently.
        """
        equity_a = _make_equity(n_bars=100, seed=1)
        equity_b = list(equity_a)  # same length, same first/last

        # Swap two interior elements to create a mismatch
        equity_b[10], equity_b[11] = equity_b[11], equity_b[10]

        # First and last timestamps still match
        assert equity_a[0].close_time == equity_b[0].close_time
        assert equity_a[-1].close_time == equity_b[-1].close_time

        with pytest.raises(ValueError, match="misaligned timestamps"):
            paired_block_bootstrap(equity_a, equity_b)


class TestRunBootstrapSuite:
    def test_returns_three_results(self) -> None:
        equity = _make_equity(n_bars=500)
        results = run_bootstrap_suite(equity, n_bootstrap=50)
        assert len(results) == 3
        names = {r.metric_name for r in results}
        assert names == {"sharpe", "cagr_pct", "max_drawdown_pct"}
