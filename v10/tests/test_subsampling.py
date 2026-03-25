"""Tests for paired block subsampling on aligned equity curves."""

from __future__ import annotations

import numpy as np
import pytest

from v10.core.types import EquitySnap
from v10.research.subsampling import AlignmentError
from v10.research.subsampling import BlockGridSummary
from v10.research.subsampling import PairedBlockSubsamplingResult
from v10.research.subsampling import paired_block_subsampling
from v10.research.subsampling import summarize_block_grid

FOUR_H_MS = 4 * 3600 * 1000


def _make_equity_from_log_returns(log_returns: np.ndarray, *, seed_nav: float = 10_000.0) -> list[EquitySnap]:
    """Build an equity curve compatible with the repo's EquitySnap type."""
    navs = np.empty(log_returns.size + 1, dtype=np.float64)
    navs[0] = seed_nav
    navs[1:] = seed_nav * np.exp(np.cumsum(log_returns))
    equity: list[EquitySnap] = []
    for i, nav in enumerate(navs):
        equity.append(
            EquitySnap(
                close_time=i * FOUR_H_MS,
                nav_mid=float(nav),
                nav_liq=float(nav),
                cash=float(nav),
                btc_qty=0.0,
                exposure=1.0,
            )
        )
    return equity


def _ar1_series(n: int, mean: float, phi: float, sigma: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, sigma, size=n)
    out = np.empty(n, dtype=np.float64)
    out[0] = mean + eps[0]
    for i in range(1, n):
        out[i] = mean + phi * (out[i - 1] - mean) + eps[i]
    return out


def _make_aligned_equity_pair(
    *,
    n_bars: int = 2200,
    market_mean: float = 0.00015,
    market_phi: float = 0.12,
    market_sigma: float = 0.01,
    edge_mean: float = 0.00010,
    edge_phi: float = 0.35,
    edge_sigma: float = 0.0012,
    market_seed: int = 11,
    edge_seed: int = 17,
) -> tuple[list[EquitySnap], list[EquitySnap]]:
    """Create baseline/candidate curves with the same timestamps and a controlled excess edge."""
    market = _ar1_series(n_bars, mean=market_mean, phi=market_phi, sigma=market_sigma, seed=market_seed)
    edge = _ar1_series(n_bars, mean=edge_mean, phi=edge_phi, sigma=edge_sigma, seed=edge_seed)
    baseline = _make_equity_from_log_returns(market)
    candidate = _make_equity_from_log_returns(market + edge)
    return candidate, baseline


class TestPairedBlockSubsampling:
    def test_basic_result_shape(self) -> None:
        candidate, baseline = _make_aligned_equity_pair()
        result = paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=24)
        assert isinstance(result, PairedBlockSubsamplingResult)
        assert result.method == "paired_block_subsampling"
        assert result.statistic_name == "annualized_excess_geometric_growth"
        assert result.block_size == 24
        assert result.n_obs == len(candidate) - 1
        assert result.n_blocks_used > 0

    def test_ci_bounds_ordering(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(edge_mean=0.00008)
        result = paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=48)
        assert result.ci_lower < result.ci_upper
        assert result.terminal_ci_lower < result.terminal_ci_upper

    def test_positive_edge_high_confidence(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(edge_mean=0.00012)
        result = paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=24)
        assert result.observed_delta > 0.0
        assert result.ci_lower > 0.0
        assert result.p_a_better > 0.95

    def test_deterministic_for_same_input(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(edge_mean=0.00010)
        r1 = paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=24)
        r2 = paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=24)
        assert r1.observed_delta == r2.observed_delta
        assert r1.ci_lower == r2.ci_lower
        assert r1.p_a_better == r2.p_a_better

    def test_alignment_error_on_length_mismatch(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(n_bars=200)
        with pytest.raises(AlignmentError, match="same number of points"):
            paired_block_subsampling(equity_a=candidate[:-1], equity_b=baseline, block_size=24)

    def test_alignment_error_on_timestamp_mismatch(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(n_bars=200)
        candidate[10] = EquitySnap(
            close_time=999999,
            nav_mid=candidate[10].nav_mid,
            nav_liq=candidate[10].nav_liq,
            cash=candidate[10].cash,
            btc_qty=candidate[10].btc_qty,
            exposure=candidate[10].exposure,
        )
        with pytest.raises(AlignmentError, match="timestamps do not align"):
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=24)

    def test_block_size_too_large_raises(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(n_bars=60)
        with pytest.raises(ValueError, match="must be smaller than number of returns"):
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=60)


class TestSummarizeBlockGrid:
    def test_positive_edge_passes_stability_gate(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(edge_mean=0.00010)
        results = [
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=12),
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=24),
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=48),
        ]
        summary = summarize_block_grid(results)
        assert isinstance(summary, BlockGridSummary)
        assert summary.decision_pass is True
        assert summary.support_ratio >= (2.0 / 3.0)
        assert summary.median_ci_lower > 0.0

    def test_no_edge_does_not_pass(self) -> None:
        candidate, baseline = _make_aligned_equity_pair(edge_mean=0.0, edge_seed=29, market_seed=23)
        results = [
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=24),
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=48),
            paired_block_subsampling(equity_a=candidate, equity_b=baseline, block_size=72),
        ]
        summary = summarize_block_grid(results)
        assert summary.decision_pass is False
        assert summary.median_ci_lower <= 0.0
        assert summary.support_ratio == 0.0
