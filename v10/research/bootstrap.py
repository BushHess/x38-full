"""Block bootstrap confidence intervals for strategy performance metrics.

Implements circular block bootstrap (Politis & Romano, 1994) on equity
curve 4H returns to estimate distributional properties of Sharpe ratio
and other metrics without assuming i.i.d. returns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import EquitySnap

PERIODS_PER_YEAR_4H = (24.0 / 4.0) * 365.0  # 2190


@dataclass
class BootstrapResult:
    """Result of block bootstrap analysis."""

    metric_name: str  # e.g. "sharpe"
    observed: float  # observed metric value
    mean: float  # bootstrap mean
    std: float  # bootstrap std
    ci_lower: float  # 2.5th percentile
    ci_upper: float  # 97.5th percentile
    p_positive: float  # P(metric > 0)
    n_bootstrap: int  # number of resamples
    block_size: int  # block length used


def calc_sharpe(returns: np.ndarray) -> float:
    """Annualized Sharpe from 4H pct returns (ddof=0, no risk-free)."""
    if len(returns) < 2:
        return 0.0
    mu = returns.mean()
    sigma = returns.std(ddof=0)
    if sigma < 1e-12:
        return 0.0
    return float(mu / sigma * math.sqrt(PERIODS_PER_YEAR_4H))


def calc_cagr(returns: np.ndarray) -> float:
    """CAGR from 4H pct returns."""
    if len(returns) < 2:
        return 0.0
    cumulative = np.prod(1.0 + returns)
    years = len(returns) / PERIODS_PER_YEAR_4H
    if years < 1e-6 or cumulative <= 0:
        return 0.0
    return float((cumulative ** (1.0 / years) - 1.0) * 100.0)


def calc_max_drawdown(returns: np.ndarray) -> float:
    """Max drawdown % from 4H pct returns."""
    if len(returns) < 2:
        return 0.0
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = 1.0 - equity / peak
    return float(dd.max()) * 100.0


def block_bootstrap(
    equity: list[EquitySnap],
    metric_fn: callable = calc_sharpe,
    metric_name: str = "sharpe",
    n_bootstrap: int = 1000,
    block_size: int = 20,
    seed: int | None = 42,
    ci_level: float = 0.95,
) -> BootstrapResult:
    """Run circular block bootstrap on equity curve returns.

    Parameters
    ----------
    equity : list[EquitySnap]
        Full equity curve from BacktestResult.equity.
    metric_fn : callable
        Function that takes np.ndarray of 4H pct returns → float.
        Default: calc_sharpe.
    metric_name : str
        Label for the metric (used in BootstrapResult).
    n_bootstrap : int
        Number of resamples (default: 1000).
    block_size : int
        Block length for circular block bootstrap (default: 20 bars = ~3.3 days).
        Preserves autocorrelation within blocks.
    seed : int | None
        Random seed for reproducibility.
    ci_level : float
        Confidence interval level (default: 0.95 → 2.5th/97.5th percentile).

    Returns
    -------
    BootstrapResult

    Notes
    -----
    Circular block bootstrap: blocks wrap around the end of the series,
    preserving all observations with equal probability.
    """
    navs = np.array([e.nav_mid for e in equity], dtype=np.float64)
    returns = np.diff(navs) / navs[:-1]  # 4H pct returns
    n = len(returns)

    if n < block_size * 2:
        raise ValueError(
            f"Equity curve too short ({n} returns) for block_size={block_size}. Need at least {block_size * 2} returns."
        )

    observed = metric_fn(returns)

    rng = np.random.default_rng(seed)
    alpha = 1.0 - ci_level
    metrics = np.empty(n_bootstrap, dtype=np.float64)

    n_blocks = int(np.ceil(n / block_size))

    for i in range(n_bootstrap):
        # Circular block bootstrap: random start indices, wrap around
        starts = rng.integers(0, n, size=n_blocks)
        indices = np.concatenate([np.arange(s, s + block_size) % n for s in starts])[:n]
        resampled = returns[indices]
        metrics[i] = metric_fn(resampled)

    return BootstrapResult(
        metric_name=metric_name,
        observed=observed,
        mean=float(metrics.mean()),
        std=float(metrics.std(ddof=1)),
        ci_lower=float(np.percentile(metrics, alpha / 2 * 100)),
        ci_upper=float(np.percentile(metrics, (1 - alpha / 2) * 100)),
        p_positive=float((metrics > 0).mean()),
        n_bootstrap=n_bootstrap,
        block_size=block_size,
    )


@dataclass
class PairedBootstrapResult:
    """Result of paired block bootstrap (A vs B)."""

    metric_name: str
    observed_a: float
    observed_b: float
    observed_delta: float  # A - B
    mean_delta: float
    std_delta: float
    ci_lower: float
    ci_upper: float
    p_a_better: float  # P(metric_A > metric_B)
    n_bootstrap: int
    block_size: int


def paired_block_bootstrap(
    equity_a: list[EquitySnap],
    equity_b: list[EquitySnap],
    metric_fn: callable = calc_sharpe,
    metric_name: str = "sharpe",
    n_bootstrap: int = 2000,
    block_size: int = 20,
    seed: int | None = 42,
    ci_level: float = 0.95,
) -> PairedBootstrapResult:
    """Paired block bootstrap: resample same block indices from both curves.

    Computes metric(A) - metric(B) for each resample to test whether A
    is significantly different from B while preserving temporal correlation.

    Both equity curves must span the same time period (same length and
    identical timestamps at each index).

    NOTE: The returned ``p_a_better`` is the fraction of bootstrap resamples
    where the candidate's metric exceeds the baseline's. It is a
    *directional resampling score*, NOT a calibrated p-value. It does not
    test H0: metric(A) <= metric(B) and should not be compared to
    significance levels (alpha = 0.05, etc.). See Report 21, U1-U2.
    """
    if len(equity_a) != len(equity_b):
        raise ValueError(
            f"paired_block_bootstrap: equity curves have different lengths "
            f"({len(equity_a)} vs {len(equity_b)}). "
            f"Ensure both curves cover the same time range."
        )

    # Verify timestamp alignment — paired bootstrap requires identical time grids.
    # Check ALL timestamps, not just first/last, to catch interior mismatches.
    if equity_a and equity_b:
        ts_a = np.array([e.close_time for e in equity_a], dtype=np.int64)
        ts_b = np.array([e.close_time for e in equity_b], dtype=np.int64)
        mismatches = np.where(ts_a != ts_b)[0]
        if mismatches.size > 0:
            idx = int(mismatches[0])
            raise ValueError(
                f"paired_block_bootstrap: equity curves have misaligned timestamps "
                f"at index {idx}: {ts_a[idx]} vs {ts_b[idx]} "
                f"({mismatches.size} total mismatches). "
                f"Ensure both curves use the same bar timestamps."
            )

    navs_a = np.array([e.nav_mid for e in equity_a], dtype=np.float64)
    navs_b = np.array([e.nav_mid for e in equity_b], dtype=np.float64)
    returns_a = np.diff(navs_a) / navs_a[:-1]
    returns_b = np.diff(navs_b) / navs_b[:-1]
    n = len(returns_a)

    if n < block_size * 2:
        raise ValueError(
            f"Equity curves too short ({n} returns) for block_size={block_size}."
        )

    observed_a = metric_fn(returns_a)
    observed_b = metric_fn(returns_b)
    observed_delta = observed_a - observed_b

    rng = np.random.default_rng(seed)
    alpha = 1.0 - ci_level
    deltas = np.empty(n_bootstrap, dtype=np.float64)
    n_blocks = int(np.ceil(n / block_size))

    for i in range(n_bootstrap):
        starts = rng.integers(0, n, size=n_blocks)
        indices = np.concatenate(
            [np.arange(s, s + block_size) % n for s in starts]
        )[:n]
        deltas[i] = metric_fn(returns_a[indices]) - metric_fn(returns_b[indices])

    return PairedBootstrapResult(
        metric_name=metric_name,
        observed_a=float(observed_a),
        observed_b=float(observed_b),
        observed_delta=float(observed_delta),
        mean_delta=float(deltas.mean()),
        std_delta=float(deltas.std(ddof=1)),
        ci_lower=float(np.percentile(deltas, alpha / 2 * 100)),
        ci_upper=float(np.percentile(deltas, (1 - alpha / 2) * 100)),
        p_a_better=float((deltas > 0).mean()),
        n_bootstrap=n_bootstrap,
        block_size=block_size,
    )


def run_bootstrap_suite(
    equity: list[EquitySnap],
    n_bootstrap: int = 1000,
    block_size: int = 20,
    seed: int | None = 42,
) -> list[BootstrapResult]:
    """Run bootstrap for Sharpe, CAGR, and MaxDD.

    Convenience function that returns a list of BootstrapResult for
    the three standard metrics.
    """
    results = []
    for fn, name in [
        (calc_sharpe, "sharpe"),
        (calc_cagr, "cagr_pct"),
        (calc_max_drawdown, "max_drawdown_pct"),
    ]:
        results.append(
            block_bootstrap(
                equity=equity,
                metric_fn=fn,
                metric_name=name,
                n_bootstrap=n_bootstrap,
                block_size=block_size,
                seed=seed,
            )
        )
    return results
