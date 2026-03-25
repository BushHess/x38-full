from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

BARS_PER_YEAR_4H = (24.0 / 4.0) * 365.0  # 2190
_MIN_EXP_ARG = -700.0
_MAX_EXP_ARG = 700.0
_TIMESTAMP_KEYS = (
    "timestamp",
    "ts",
    "ts_ms",
    "time",
    "open_time",
    "close_time",
    "bar_time",
)


@dataclass(frozen=True)
class PairedBlockSubsamplingResult:
    method: str
    statistic_name: str
    null_hypothesis: str
    block_size: int
    bars_per_year: float
    n_obs: int
    n_blocks_total: int
    n_blocks_used: int
    block_selection_mode: str
    observed_candidate_growth: float
    observed_baseline_growth: float
    observed_mean_log_diff: float
    observed_delta: float
    ci_lower: float
    ci_upper: float
    observed_terminal_delta: float
    terminal_ci_lower: float
    terminal_ci_upper: float
    p_a_better: float
    p_value_one_sided: float
    stderr_mean_log_diff: float


@dataclass(frozen=True)
class BlockGridSummary:
    method: str
    statistic_name: str
    gate_mode: str
    n_block_sizes: int
    block_sizes: list[int]
    median_observed_delta: float
    median_ci_lower: float
    median_ci_upper: float
    min_ci_lower: float
    max_ci_upper: float
    median_p_a_better: float
    min_p_a_better: float
    support_ratio: float
    p_threshold: float
    ci_lower_threshold: float
    support_ratio_threshold: float
    decision_pass: bool


class AlignmentError(ValueError):
    pass


def _safe_expm1(x: np.ndarray | float) -> np.ndarray | float:
    return np.expm1(np.clip(x, _MIN_EXP_ARG, _MAX_EXP_ARG))


def _is_mapping_like(value: Any) -> bool:
    return hasattr(value, "get") and callable(value.get)


def _extract_nav(item: Any) -> float:
    if hasattr(item, "nav_mid"):
        return float(item.nav_mid)
    if _is_mapping_like(item) and "nav_mid" in item:
        return float(item["nav_mid"])
    return float(item)


def _extract_timestamp(item: Any) -> Any | None:
    for key in _TIMESTAMP_KEYS:
        if hasattr(item, key):
            return getattr(item, key)
        if _is_mapping_like(item) and key in item:
            return item[key]
    return None


def _as_nav_array_and_timestamps(equity: Sequence[Any], *, name: str) -> tuple[np.ndarray, list[Any | None]]:
    if len(equity) < 3:
        raise ValueError(f"{name} must contain at least 3 equity points")
    navs = np.asarray([_extract_nav(item) for item in equity], dtype=np.float64)
    if navs.ndim != 1:
        raise ValueError(f"{name} must be 1-dimensional after nav extraction")
    if not np.all(np.isfinite(navs)):
        raise ValueError(f"{name} contains non-finite nav values")
    if np.any(navs <= 0.0):
        raise ValueError(f"{name} contains non-positive nav values")
    timestamps = [_extract_timestamp(item) for item in equity]
    return navs, timestamps


def _validate_pair_alignment(equity_a: Sequence[Any], equity_b: Sequence[Any]) -> tuple[np.ndarray, np.ndarray]:
    navs_a, ts_a = _as_nav_array_and_timestamps(equity_a, name="equity_a")
    navs_b, ts_b = _as_nav_array_and_timestamps(equity_b, name="equity_b")
    if navs_a.size != navs_b.size:
        raise AlignmentError(
            f"candidate and baseline equity must have the same number of points (got {navs_a.size} vs {navs_b.size})"
        )
    has_ts_a = any(ts is not None for ts in ts_a)
    has_ts_b = any(ts is not None for ts in ts_b)
    if has_ts_a != has_ts_b:
        raise AlignmentError("timestamp metadata is present for only one equity curve")
    if has_ts_a and has_ts_b and ts_a != ts_b:
        raise AlignmentError("candidate and baseline timestamps do not align exactly")
    return navs_a, navs_b


def _navs_to_log_returns(navs: np.ndarray) -> np.ndarray:
    rel = navs[1:] / navs[:-1]
    if np.any(rel <= 0.0) or not np.all(np.isfinite(rel)):
        raise ValueError("invalid relative returns implied by equity navs")
    return np.log(rel)


def _overlapping_block_means(series: np.ndarray, block_size: int) -> np.ndarray:
    n = int(series.size)
    if block_size < 2:
        raise ValueError("block_size must be at least 2")
    if block_size >= n:
        raise ValueError(f"block_size={block_size} must be smaller than number of returns n={n}")
    csum = np.cumsum(np.insert(series, 0, 0.0))
    sums = csum[block_size:] - csum[:-block_size]
    return sums / float(block_size)


def _choose_blocks(block_means: np.ndarray, max_blocks: int | None) -> tuple[np.ndarray, str]:
    total = int(block_means.size)
    if max_blocks is None or max_blocks <= 0 or total <= max_blocks:
        return block_means, "all_overlapping"
    idx = np.linspace(0, total - 1, num=max_blocks, dtype=np.int64)
    idx = np.unique(idx)
    return block_means[idx], "evenly_spaced_overlapping"


def _annualized_simple_from_mean_log(mean_log: float, bars_per_year: float) -> float:
    return float(_safe_expm1(bars_per_year * mean_log))


def _terminal_simple_from_mean_log(mean_log: float, horizon_bars: int) -> float:
    return float(_safe_expm1(horizon_bars * mean_log))


def paired_block_subsampling(
    *,
    equity_a: Sequence[Any],
    equity_b: Sequence[Any],
    block_size: int,
    bars_per_year: float = BARS_PER_YEAR_4H,
    ci_level: float = 0.95,
    max_subsamples: int | None = None,
    min_blocks_used: int = 20,
) -> PairedBlockSubsamplingResult:
    """Paired block subsampling for strategy comparison (Politis-Romano-Wolf).

    CAVEAT: When the near-equality rate (|diff| < 1bp) of the differential
    return series exceeds ~80%, block means become degenerate and the
    subsampling CI may collapse. In this regime, p_a_better is NOT
    calibrated and should not be interpreted as a probability.
    See Report 19, section 4 and Report 21, U5.
    """
    if not (0.0 < ci_level < 1.0):
        raise ValueError("ci_level must lie strictly between 0 and 1")
    if bars_per_year <= 0.0:
        raise ValueError("bars_per_year must be positive")

    navs_a, navs_b = _validate_pair_alignment(equity_a, equity_b)
    log_a = _navs_to_log_returns(navs_a)
    log_b = _navs_to_log_returns(navs_b)
    diff = log_a - log_b
    if not np.all(np.isfinite(diff)):
        raise ValueError("differential log-return series contains non-finite values")
    n_obs = int(diff.size)
    if n_obs < 30:
        raise ValueError(f"need at least 30 returns for stable inference; got {n_obs}")

    full_mean = float(np.mean(diff))
    block_means_all = _overlapping_block_means(diff, int(block_size))
    block_means, selection_mode = _choose_blocks(block_means_all, max_subsamples)
    if int(block_means.size) < int(min_blocks_used):
        raise ValueError(
            f"too few subsampling blocks ({block_means.size}) for block_size={block_size}; need at least {min_blocks_used}"
        )

    root = math.sqrt(block_size) * (block_means - full_mean)
    alpha = 1.0 - ci_level
    q_low = float(np.quantile(root, alpha / 2.0))
    q_high = float(np.quantile(root, 1.0 - alpha / 2.0))
    sqrt_n = math.sqrt(n_obs)

    mean_ci_lower = full_mean - q_high / sqrt_n
    mean_ci_upper = full_mean - q_low / sqrt_n

    test_stat = sqrt_n * full_mean
    p_value_one_sided = float(np.mean(root >= test_stat))
    p_a_better = float(max(0.0, min(1.0, 1.0 - p_value_one_sided)))

    observed_delta = _annualized_simple_from_mean_log(full_mean, bars_per_year)
    ci_lower = _annualized_simple_from_mean_log(mean_ci_lower, bars_per_year)
    ci_upper = _annualized_simple_from_mean_log(mean_ci_upper, bars_per_year)
    observed_terminal_delta = _terminal_simple_from_mean_log(full_mean, n_obs)
    terminal_ci_lower = _terminal_simple_from_mean_log(mean_ci_lower, n_obs)
    terminal_ci_upper = _terminal_simple_from_mean_log(mean_ci_upper, n_obs)
    observed_a_growth = _annualized_simple_from_mean_log(float(np.mean(log_a)), bars_per_year)
    observed_b_growth = _annualized_simple_from_mean_log(float(np.mean(log_b)), bars_per_year)
    stderr_mean = float(np.std(root, ddof=1) / sqrt_n)

    return PairedBlockSubsamplingResult(
        method="paired_block_subsampling",
        statistic_name="annualized_excess_geometric_growth",
        null_hypothesis="annualized_excess_geometric_growth <= 0",
        block_size=int(block_size),
        bars_per_year=float(bars_per_year),
        n_obs=n_obs,
        n_blocks_total=int(block_means_all.size),
        n_blocks_used=int(block_means.size),
        block_selection_mode=selection_mode,
        observed_candidate_growth=float(observed_a_growth),
        observed_baseline_growth=float(observed_b_growth),
        observed_mean_log_diff=float(full_mean),
        observed_delta=float(observed_delta),
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        observed_terminal_delta=float(observed_terminal_delta),
        terminal_ci_lower=float(terminal_ci_lower),
        terminal_ci_upper=float(terminal_ci_upper),
        p_a_better=float(p_a_better),
        p_value_one_sided=float(p_value_one_sided),
        stderr_mean_log_diff=float(stderr_mean),
    )


def summarize_block_grid(
    results: Sequence[PairedBlockSubsamplingResult],
    *,
    p_threshold: float = 0.80,
    ci_lower_threshold: float = 0.0,
    support_ratio_threshold: float = 0.60,
) -> BlockGridSummary:
    if not results:
        raise ValueError("results must not be empty")
    ordered = sorted(results, key=lambda item: item.block_size)
    observed = np.asarray([r.observed_delta for r in ordered], dtype=np.float64)
    ci_lowers = np.asarray([r.ci_lower for r in ordered], dtype=np.float64)
    ci_uppers = np.asarray([r.ci_upper for r in ordered], dtype=np.float64)
    probs = np.asarray([r.p_a_better for r in ordered], dtype=np.float64)
    support = (probs >= p_threshold) & (ci_lowers > ci_lower_threshold)
    support_ratio = float(np.mean(support))
    decision_pass = bool(
        np.median(probs) >= p_threshold
        and np.median(ci_lowers) > ci_lower_threshold
        and support_ratio >= support_ratio_threshold
    )
    return BlockGridSummary(
        method=ordered[0].method,
        statistic_name=ordered[0].statistic_name,
        gate_mode="median_and_support_over_block_sizes",
        n_block_sizes=len(ordered),
        block_sizes=[int(r.block_size) for r in ordered],
        median_observed_delta=float(np.median(observed)),
        median_ci_lower=float(np.median(ci_lowers)),
        median_ci_upper=float(np.median(ci_uppers)),
        min_ci_lower=float(np.min(ci_lowers)),
        max_ci_upper=float(np.max(ci_uppers)),
        median_p_a_better=float(np.median(probs)),
        min_p_a_better=float(np.min(probs)),
        support_ratio=float(support_ratio),
        p_threshold=float(p_threshold),
        ci_lower_threshold=float(ci_lower_threshold),
        support_ratio_threshold=float(support_ratio_threshold),
        decision_pass=decision_pass,
    )
