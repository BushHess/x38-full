"""Shared helpers for isolated x36 diagnostics."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from dataclasses import fields
from pathlib import Path
from statistics import median
from typing import Any
from typing import Callable

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies.vtrend.strategy import VTrendConfig
from strategies.vtrend.strategy import VTrendStrategy
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Config
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import BacktestResult
from v10.core.types import SCENARIOS
from v10.core.types import Trade
from v10.research.wfo import WFOWindowSpec
from v10.research.wfo import generate_windows
from validation.thresholds import WFO_BOOTSTRAP_CI_ALPHA
from validation.thresholds import WFO_BOOTSTRAP_N_RESAMPLES
from validation.thresholds import WFO_WILCOXON_ALPHA


@dataclass(frozen=True)
class FrozenWFOConfig:
    tag: str
    train_months: int
    test_months: int
    slide_months: int
    max_windows: int | None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _to_float_or_nan(value: Any) -> float:
    try:
        if value is None:
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round_or_none(value: float, ndigits: int) -> float | None:
    return round(float(value), ndigits) if math.isfinite(float(value)) else None


def load_strategy_kwargs(path: Path, config_cls: type[Any]) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    strategy_payload = payload.get("strategy", {})
    allowed = {f.name for f in fields(config_cls)}
    return {
        key: value
        for key, value in strategy_payload.items()
        if key in allowed
    }


def make_candidate_factory(root: Path) -> Callable[[], VTrendE5Ema21D1Strategy]:
    config_path = root / "configs" / "vtrend_e5_ema21_d1" / "vtrend_e5_ema21_d1_default.yaml"
    kwargs = load_strategy_kwargs(config_path, VTrendE5Ema21D1Config)

    def factory() -> VTrendE5Ema21D1Strategy:
        return VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config(**kwargs))

    return factory


def make_baseline_factory(root: Path) -> Callable[[], VTrendStrategy]:
    config_path = root / "configs" / "vtrend" / "vtrend_default.yaml"
    kwargs = load_strategy_kwargs(config_path, VTrendConfig)

    def factory() -> VTrendStrategy:
        return VTrendStrategy(VTrendConfig(**kwargs))

    return factory


def limited_windows(
    *,
    start: str,
    end: str,
    spec: FrozenWFOConfig,
) -> list[WFOWindowSpec]:
    windows = generate_windows(
        start=start,
        end=end,
        train_months=spec.train_months,
        test_months=spec.test_months,
        slide_months=spec.slide_months,
    )
    if spec.max_windows is not None and len(windows) > spec.max_windows:
        windows = windows[-spec.max_windows :]
    return windows


def run_window_backtest(
    *,
    root: Path,
    factory: Callable[[], Any],
    start: str,
    end: str,
    warmup_days: int,
    initial_cash: float,
    scenario: str,
) -> BacktestResult:
    feed = DataFeed(
        str(root / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv"),
        start=start,
        end=end,
        warmup_days=warmup_days,
    )
    engine = BacktestEngine(
        feed=feed,
        strategy=factory(),
        cost=SCENARIOS[scenario],
        initial_cash=initial_cash,
        warmup_mode="no_trade",
    )
    return engine.run()


def summarize_trades(trades: list[Trade]) -> dict[str, Any]:
    if not trades:
        return {
            "count": 0,
            "win_rate_pct": 0.0,
            "avg_return_pct": 0.0,
            "median_return_pct": 0.0,
            "avg_days_held": 0.0,
            "median_days_held": 0.0,
            "max_return_pct": 0.0,
            "min_return_pct": 0.0,
            "long_hold_count_gt30bars": 0,
            "profit_share_long_holds_pct": 0.0,
        }

    returns = [float(t.return_pct) for t in trades]
    holds = [float(t.days_held) for t in trades]
    wins = sum(1 for t in trades if t.pnl > 0.0)
    profit_total = sum(max(float(t.pnl), 0.0) for t in trades)
    long_holds = [t for t in trades if float(t.days_held) > 5.0]
    long_hold_profit = sum(max(float(t.pnl), 0.0) for t in long_holds)
    profit_share = 0.0 if profit_total <= 0.0 else 100.0 * long_hold_profit / profit_total
    return {
        "count": len(trades),
        "win_rate_pct": round(100.0 * wins / len(trades), 2),
        "avg_return_pct": round(sum(returns) / len(returns), 4),
        "median_return_pct": round(float(median(returns)), 4),
        "avg_days_held": round(sum(holds) / len(holds), 4),
        "median_days_held": round(float(median(holds)), 4),
        "max_return_pct": round(max(returns), 4),
        "min_return_pct": round(min(returns), 4),
        "long_hold_count_gt30bars": len(long_holds),
        "profit_share_long_holds_pct": round(profit_share, 2),
    }


def top_trade_table(trades: list[Trade], *, reverse: bool, limit: int = 3) -> list[dict[str, Any]]:
    ranked = sorted(trades, key=lambda trade: float(trade.pnl), reverse=reverse)[:limit]
    return [
        {
            "trade_id": int(trade.trade_id),
            "entry_ts_ms": int(trade.entry_ts_ms),
            "exit_ts_ms": int(trade.exit_ts_ms),
            "return_pct": round(float(trade.return_pct), 4),
            "pnl_usd": round(float(trade.pnl), 2),
            "days_held": round(float(trade.days_held), 4),
            "exit_reason": str(trade.exit_reason),
        }
        for trade in ranked
    ]


def safe_wfo_objective_score(summary: dict[str, Any]) -> float:
    """Mirror validation.suites.wfo._objective_without_reject with NaN on invalid input."""
    trades = _to_float_or_nan(summary.get("trades", 0.0))
    cagr = _to_float_or_nan(summary.get("cagr_pct", 0.0))
    max_dd = _to_float_or_nan(summary.get("max_drawdown_mid_pct", 0.0))
    sharpe = _to_float_or_nan(summary.get("sharpe", 0.0))

    raw_pf = summary.get("profit_factor", 0.0)
    if isinstance(raw_pf, str) and raw_pf.strip().lower() == "inf":
        pf = 3.0
    else:
        pf = _to_float_or_nan(raw_pf)
        if math.isinf(pf):
            pf = 3.0

    metrics = (trades, cagr, max_dd, sharpe, pf)
    if any(not math.isfinite(value) for value in metrics):
        return math.nan

    score = (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
        + min(trades / 50.0, 1.0) * 5.0
    )
    return float(score) if math.isfinite(score) else math.nan


def evaluate_wfo_window(
    *,
    window_id: int,
    test_start: str,
    test_end: str,
    candidate_summary: dict[str, Any],
    baseline_summary: dict[str, Any],
    min_trades_for_power: int,
) -> dict[str, Any]:
    """Mirror validation.suites.wfo window validity + low-power semantics."""
    candidate_score = safe_wfo_objective_score(candidate_summary)
    baseline_score = safe_wfo_objective_score(baseline_summary)

    candidate_cagr = _to_float_or_nan(candidate_summary.get("cagr_pct"))
    baseline_cagr = _to_float_or_nan(baseline_summary.get("cagr_pct"))
    candidate_max_dd = _to_float_or_nan(candidate_summary.get("max_drawdown_mid_pct"))
    baseline_max_dd = _to_float_or_nan(baseline_summary.get("max_drawdown_mid_pct"))
    candidate_sharpe = _to_float_or_nan(candidate_summary.get("sharpe"))
    baseline_sharpe = _to_float_or_nan(baseline_summary.get("sharpe"))

    trade_count_candidate = _to_int(candidate_summary.get("trades", 0), default=0)
    trade_count_baseline = _to_int(baseline_summary.get("trades", 0), default=0)

    invalid_reason = "none"
    if trade_count_candidate <= 0 and trade_count_baseline <= 0:
        invalid_reason = "both_zero_trade_counts"
    elif trade_count_candidate <= 0:
        invalid_reason = "candidate_zero_trade_count"
    elif trade_count_baseline <= 0:
        invalid_reason = "baseline_zero_trade_count"
    elif any(
        not math.isfinite(value)
        for value in (candidate_score, candidate_cagr, candidate_max_dd, candidate_sharpe)
    ):
        invalid_reason = "candidate_non_finite_core_metrics"
    elif any(
        not math.isfinite(value)
        for value in (baseline_score, baseline_cagr, baseline_max_dd, baseline_sharpe)
    ):
        invalid_reason = "baseline_non_finite_core_metrics"

    valid_window = invalid_reason == "none"
    low_trade_reason = "none"
    low_trade_window = False
    if valid_window:
        candidate_low = 0 < trade_count_candidate < max(1, int(min_trades_for_power))
        baseline_low = 0 < trade_count_baseline < max(1, int(min_trades_for_power))
        if candidate_low and baseline_low:
            low_trade_window = True
            low_trade_reason = "both_below_min_trades_for_power"
        elif candidate_low:
            low_trade_window = True
            low_trade_reason = "candidate_below_min_trades_for_power"
        elif baseline_low:
            low_trade_window = True
            low_trade_reason = "baseline_below_min_trades_for_power"

    delta_harsh_score = candidate_score - baseline_score if valid_window else math.nan
    if valid_window and not math.isfinite(delta_harsh_score):
        valid_window = False
        low_trade_window = False
        low_trade_reason = "none"
        invalid_reason = "delta_non_finite"

    return {
        "window_id": int(window_id),
        "test_start": str(test_start),
        "test_end": str(test_end),
        "candidate_score": _round_or_none(candidate_score, 4),
        "baseline_score": _round_or_none(baseline_score, 4),
        "delta_harsh_score": _round_or_none(delta_harsh_score, 4),
        "candidate_cagr_pct": _round_or_none(candidate_cagr, 4),
        "baseline_cagr_pct": _round_or_none(baseline_cagr, 4),
        "candidate_max_dd_pct": _round_or_none(candidate_max_dd, 4),
        "baseline_max_dd_pct": _round_or_none(baseline_max_dd, 4),
        "candidate_sharpe": _round_or_none(candidate_sharpe, 6),
        "baseline_sharpe": _round_or_none(baseline_sharpe, 6),
        "candidate_trades": int(trade_count_candidate),
        "baseline_trades": int(trade_count_baseline),
        "trade_count_candidate": int(trade_count_candidate),
        "trade_count_baseline": int(trade_count_baseline),
        "valid_window": bool(valid_window),
        "invalid_reason": str(invalid_reason),
        "low_trade_window": bool(low_trade_window),
        "low_trade_reason": str(low_trade_reason),
    }


def compute_wilcoxon(deltas: list[float]) -> dict[str, Any]:
    from scipy.stats import wilcoxon as scipy_wilcoxon

    nonzero = [delta for delta in deltas if delta != 0.0]
    if len(nonzero) < 6:
        return {
            "statistic": None,
            "p_value": 1.0,
            "n_nonzero": len(nonzero),
            "sufficient": False,
        }
    try:
        stat, p_value = scipy_wilcoxon(deltas, alternative="greater")
    except ValueError:
        return {
            "statistic": None,
            "p_value": 1.0,
            "n_nonzero": len(nonzero),
            "sufficient": False,
        }
    return {
        "statistic": round(float(stat), 4),
        "p_value": round(float(p_value), 6),
        "n_nonzero": len(nonzero),
        "sufficient": True,
    }


def compute_bootstrap_ci(
    deltas: list[float],
    *,
    seed: int,
    alpha: float = 0.05,
    n_resamples: int = 10000,
) -> dict[str, Any]:
    if len(deltas) < 2:
        return {
            "ci_lower": None,
            "ci_upper": None,
            "mean_delta": None,
            "excludes_zero": False,
            "n": len(deltas),
            "seed": seed,
        }
    rng = np.random.default_rng(seed=seed)
    arr = np.array(deltas, dtype=np.float64)
    means = np.empty(n_resamples, dtype=np.float64)
    for idx in range(n_resamples):
        sample_idx = rng.integers(0, len(arr), size=len(arr))
        means[idx] = arr[sample_idx].mean()
    ci_lower = float(np.percentile(means, 100 * alpha / 2))
    ci_upper = float(np.percentile(means, 100 * (1 - alpha / 2)))
    mean_delta = float(arr.mean())
    return {
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "mean_delta": round(mean_delta, 4),
        "excludes_zero": bool(ci_lower > 0.0),
        "n": len(deltas),
        "seed": seed,
    }


def summarize_wfo_deltas(deltas: list[float], *, seed: int) -> dict[str, Any]:
    n_windows = len(deltas)
    if n_windows == 0:
        return {
            "n_windows": 0,
            "positive_windows": 0,
            "win_rate": 0.0,
            "mean_delta_score": None,
            "median_delta_score": None,
            "worst_delta_score": None,
            "best_delta_score": None,
            "wilcoxon": compute_wilcoxon([]),
            "bootstrap_ci": compute_bootstrap_ci([], seed=seed),
            "pass": False,
        }
    positives = sum(1 for delta in deltas if delta > 0.0)
    wilcoxon_result = compute_wilcoxon(deltas)
    bootstrap_result = compute_bootstrap_ci(deltas, seed=seed)
    passed = (
        bool(wilcoxon_result["sufficient"]) and float(wilcoxon_result["p_value"]) <= 0.10
    ) or bool(bootstrap_result["excludes_zero"])
    return {
        "n_windows": n_windows,
        "positive_windows": positives,
        "win_rate": round(positives / n_windows, 4),
        "mean_delta_score": round(sum(deltas) / n_windows, 4),
        "median_delta_score": round(float(median(deltas)), 4),
        "worst_delta_score": round(min(deltas), 4),
        "best_delta_score": round(max(deltas), 4),
        "wilcoxon": wilcoxon_result,
        "bootstrap_ci": bootstrap_result,
        "pass": passed,
    }


def summarize_wfo_rows(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    min_trades_for_power: int,
) -> dict[str, Any]:
    """Branch-local WFO summary aligned with validation.suites.wfo + decision policy."""

    def _aggregate(include_window: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
        deltas: list[float] = []
        for row in rows:
            if not include_window(row):
                continue
            value = row.get("delta_harsh_score")
            if value is None:
                continue
            delta = float(value)
            if math.isfinite(delta):
                deltas.append(delta)

        if not deltas:
            return {
                "n_windows": 0,
                "win_count": 0,
                "win_rate": 0.0,
                "mean_delta": None,
                "median_delta": None,
                "worst_delta": None,
                "best_delta": None,
            }

        n_windows = len(deltas)
        win_count = sum(1 for value in deltas if value > 0.0)
        return {
            "n_windows": int(n_windows),
            "win_count": int(win_count),
            "win_rate": round(win_count / n_windows, 6),
            "mean_delta": round(sum(deltas) / n_windows, 6),
            "median_delta": round(float(median(deltas)), 6),
            "worst_delta": round(min(deltas), 6),
            "best_delta": round(max(deltas), 6),
        }

    invalid_windows_count = sum(1 for row in rows if not bool(row.get("valid_window")))
    low_trade_windows_count = sum(1 for row in rows if bool(row.get("low_trade_window")))
    valid_windows_count = len(rows) - invalid_windows_count
    power_windows_count = sum(
        1
        for row in rows
        if bool(row.get("valid_window")) and not bool(row.get("low_trade_window"))
    )

    stats_all_valid = _aggregate(lambda row: bool(row.get("valid_window")))
    stats_power_only = _aggregate(
        lambda row: bool(row.get("valid_window")) and not bool(row.get("low_trade_window"))
    )
    power_deltas = [
        float(row["delta_harsh_score"])
        for row in rows
        if bool(row.get("valid_window"))
        and not bool(row.get("low_trade_window"))
        and row.get("delta_harsh_score") is not None
    ]

    wilcoxon_result = compute_wilcoxon(power_deltas)
    bootstrap_result = compute_bootstrap_ci(
        power_deltas,
        seed=seed,
        alpha=WFO_BOOTSTRAP_CI_ALPHA,
        n_resamples=WFO_BOOTSTRAP_N_RESAMPLES,
    )

    low_trade_ratio = (
        low_trade_windows_count / valid_windows_count if valid_windows_count > 0 else 1.0
    )
    wfo_low_power = power_windows_count < 3 or low_trade_ratio > 0.5
    if wfo_low_power:
        passed: bool | None = None
        pass_detail = (
            "low_power=true; validation authority would delegate to trade_level_bootstrap"
        )
    else:
        wilcoxon_pass = (
            bool(wilcoxon_result["sufficient"])
            and float(wilcoxon_result["p_value"]) <= WFO_WILCOXON_ALPHA
        )
        bootstrap_pass = bool(bootstrap_result["excludes_zero"])
        passed = wilcoxon_pass or bootstrap_pass
        pass_detail = (
            f"wilcoxon_p={wilcoxon_result['p_value']:.6f}; "
            f"bootstrap_ci_lower={bootstrap_result['ci_lower']}; "
            f"pass={'true' if passed else 'false'}"
        )

    return {
        "n_windows_total": int(len(rows)),
        "n_windows_valid": int(valid_windows_count),
        "n_windows_power_only": int(power_windows_count),
        "n_windows": int(stats_all_valid["n_windows"]),
        "positive_delta_windows": int(stats_all_valid["win_count"]),
        "win_rate": stats_all_valid["win_rate"],
        "mean_delta_score": stats_all_valid["mean_delta"],
        "median_delta_score": stats_all_valid["median_delta"],
        "worst_delta_score": stats_all_valid["worst_delta"],
        "best_delta_score": stats_all_valid["best_delta"],
        "invalid_windows_count": int(invalid_windows_count),
        "low_trade_windows_count": int(low_trade_windows_count),
        "low_trade_windows": int(low_trade_windows_count),
        "min_trades_for_power": int(min_trades_for_power),
        "low_trade_threshold": int(min_trades_for_power),
        "stats_all_valid": stats_all_valid,
        "stats_power_only": stats_power_only,
        "wilcoxon": wilcoxon_result,
        "bootstrap_ci": bootstrap_result,
        "low_trade_ratio": round(low_trade_ratio, 6),
        "wfo_low_power": bool(wfo_low_power),
        "pass": passed,
        "pass_detail": pass_detail,
    }


def wfo_objective_score(summary: dict[str, Any]) -> float:
    """Mirror validation.suites.wfo._objective_without_reject for local reproduction."""
    trades = float(summary.get("trades", 0.0))
    cagr = float(summary.get("cagr_pct", 0.0))
    max_dd = float(summary.get("max_drawdown_mid_pct", 0.0))
    sharpe = float(summary.get("sharpe", 0.0))

    raw_pf = summary.get("profit_factor", 0.0)
    if isinstance(raw_pf, str) and raw_pf.strip().lower() == "inf":
        pf = 3.0
    else:
        pf = float(raw_pf)
        if math.isinf(pf):
            pf = 3.0

    metrics = (trades, cagr, max_dd, sharpe, pf)
    if any(not math.isfinite(value) for value in metrics):
        raise ValueError("WFO objective inputs must be finite.")

    score = (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
        + min(trades / 50.0, 1.0) * 5.0
    )
    if not math.isfinite(score):
        raise ValueError("WFO objective score is non-finite.")
    return float(score)
