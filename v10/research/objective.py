"""Optimizer objective function — per SPEC_METRICS §8.

score = 2.5*cagr - 0.60*max_dd + 8.0*max(0, sharpe)
      + 5.0*max(0, min(pf, 3.0) - 1.0)
      + min(n_trades/50, 1.0)*5.0

Returns -1_000_000 if n_trades < 10 (rejection threshold).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

_REJECT = -1_000_000.0

OBJECTIVE_TERM_ORDER: tuple[str, ...] = (
    "return_term",
    "mdd_penalty",
    "sharpe_term",
    "profit_factor_term",
    "trade_count_term",
    "reject_term",
)


@dataclass(frozen=True)
class ObjectiveBreakdown:
    total_score: float
    components: dict[str, float]
    rejected: bool
    reject_reason: str | None = None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def compute_objective_breakdown(summary: dict) -> ObjectiveBreakdown:
    """Compute objective score and named additive components."""
    n_trades = _to_float(summary.get("trades", 0), default=0.0)
    cagr = _to_float(summary.get("cagr_pct", 0.0), default=0.0)
    max_dd = _to_float(summary.get("max_drawdown_mid_pct", 0.0), default=0.0)
    sharpe = _to_float(summary.get("sharpe", 0.0), default=0.0)

    pf_raw = summary.get("profit_factor", 0.0)
    if isinstance(pf_raw, str):
        pf_text = pf_raw.strip().lower()
        if pf_text == "inf":
            pf = 3.0
        else:
            pf = _to_float(pf_raw, default=0.0)
    else:
        pf = _to_float(pf_raw, default=0.0)
        if math.isinf(pf):
            pf = 3.0

    components = {
        "return_term": 2.5 * cagr,
        "mdd_penalty": -0.60 * max_dd,
        "sharpe_term": 8.0 * max(0.0, sharpe),
        "profit_factor_term": 5.0 * max(0.0, min(pf, 3.0) - 1.0),
        "trade_count_term": min(n_trades / 50.0, 1.0) * 5.0,
        "reject_term": 0.0,
    }

    if n_trades < 10:
        components["reject_term"] = _REJECT
        components["return_term"] = 0.0
        components["mdd_penalty"] = 0.0
        components["sharpe_term"] = 0.0
        components["profit_factor_term"] = 0.0
        components["trade_count_term"] = 0.0
        return ObjectiveBreakdown(
            total_score=_REJECT,
            components=components,
            rejected=True,
            reject_reason="n_trades_below_minimum",
        )

    total_score = sum(components[name] for name in OBJECTIVE_TERM_ORDER)
    return ObjectiveBreakdown(
        total_score=total_score,
        components=components,
        rejected=False,
        reject_reason=None,
    )


def compute_objective(summary: dict) -> float:
    """Compute scalar objective score from a backtest summary dict.

    Keys used: cagr_pct, max_drawdown_mid_pct, sharpe, profit_factor, trades.
    """
    return compute_objective_breakdown(summary).total_score
