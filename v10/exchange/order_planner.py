"""Order planner — compute side/qty from target exposure.

Pure function that bridges strategy signals (target_exposure) to
exchange-valid orders by applying the SPEC_EXECUTION cost model,
exchange filters (step_size, min_notional), and clamping logic.

The returned :class:`OrderPlan` is ready for
``OrderManager.submit_order()``.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from v10.core.types import CostConfig, SCENARIOS
from v10.exchange.filters import SymbolInfo, round_qty_down

_log = logging.getLogger(__name__)

_CSV_FIELDS = [
    "timestamp_iso",
    "side",
    "qty",
    "est_fill_price",
    "notional",
    "reason",
    "nav_usdt",
    "btc_qty",
    "mid_price",
    "target_exposure",
    "clamped_exposure",
    "current_exposure",
    "desired_btc_value",
    "current_btc_value",
    "delta_value",
]


# ---------------------------------------------------------------------------
# OrderPlan
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OrderPlan:
    """Result of order planning — ready for submission or logging."""

    side: str               # "BUY" | "SELL" | "HOLD"
    qty: float              # rounded to step_size (0.0 if HOLD)
    est_fill_price: float   # mid adjusted by per_side_bps
    notional: float         # qty * est_fill_price
    reason: str             # why this action (or why HOLD)
    # Context fields
    nav_usdt: float
    btc_qty: float
    mid_price: float
    target_exposure: float
    clamped_exposure: float
    current_exposure: float
    desired_btc_value: float
    current_btc_value: float
    delta_value: float


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def plan_order_from_target_exposure(
    nav_usdt: float,
    btc_qty: float,
    mid_price: float,
    target_exposure: float,
    filters: SymbolInfo,
    max_total_exposure: float = 1.0,
    cost: CostConfig | None = None,
    csv_path: str | Path | None = None,
) -> OrderPlan:
    """Compute an order plan from portfolio state and target exposure.

    Parameters
    ----------
    nav_usdt : float
        Total portfolio NAV in USDT.
    btc_qty : float
        Current BTC holdings (base asset quantity).
    mid_price : float
        Current mid/market price of BTC.
    target_exposure : float
        Desired exposure fraction (0.0–1.0+).
    filters : SymbolInfo
        Exchange filters (step_size, min_notional, min_qty).
    max_total_exposure : float
        Upper clamp for target_exposure.
    cost : CostConfig | None
        Execution cost model.  Defaults to ``SCENARIOS["base"]``.
    csv_path : str | Path | None
        Path for ``live_plan.csv``.  ``None`` disables CSV logging.
    """
    if cost is None:
        cost = SCENARIOS["base"]

    # 1) Clamp target exposure
    clamped = max(0.0, min(target_exposure, max_total_exposure))

    # 2) Compute values
    desired_btc_value = clamped * nav_usdt
    current_btc_value = btc_qty * mid_price
    delta_value = desired_btc_value - current_btc_value

    current_exposure = current_btc_value / nav_usdt if nav_usdt > 0 else 0.0

    # Common context for all return paths
    ctx = dict(
        nav_usdt=nav_usdt,
        btc_qty=btc_qty,
        mid_price=mid_price,
        target_exposure=target_exposure,
        clamped_exposure=clamped,
        current_exposure=current_exposure,
        desired_btc_value=desired_btc_value,
        current_btc_value=current_btc_value,
        delta_value=delta_value,
    )

    min_notional = float(filters.min_notional)

    # 3) Below min_notional → HOLD
    if abs(delta_value) < min_notional:
        plan = OrderPlan(
            side="HOLD", qty=0.0, est_fill_price=mid_price,
            notional=0.0, reason="below_min_notional", **ctx,
        )
        _log_csv(plan, csv_path)
        return plan

    # 4) Compute side, est_fill_price, raw qty
    per_side_frac = cost.per_side_bps / 10_000

    if delta_value > 0:
        side = "BUY"
        est_fill = mid_price * (1 + per_side_frac)
        raw_qty = delta_value / est_fill
    else:
        side = "SELL"
        est_fill = mid_price * (1 - per_side_frac)
        raw_qty = min(btc_qty, abs(delta_value) / est_fill)

    # 5) Round qty down to step_size
    qty = round_qty_down(raw_qty, filters)

    # 6) Re-check notional after rounding
    notional = qty * est_fill

    if qty < float(filters.min_qty):
        plan = OrderPlan(
            side="HOLD", qty=0.0, est_fill_price=est_fill,
            notional=0.0, reason="qty_below_min_after_rounding", **ctx,
        )
        _log_csv(plan, csv_path)
        return plan

    if notional < min_notional:
        plan = OrderPlan(
            side="HOLD", qty=0.0, est_fill_price=est_fill,
            notional=0.0, reason="notional_below_min_after_rounding", **ctx,
        )
        _log_csv(plan, csv_path)
        return plan

    plan = OrderPlan(
        side=side, qty=qty, est_fill_price=est_fill,
        notional=notional, reason=side.lower(), **ctx,
    )
    _log_csv(plan, csv_path)

    _log.info(
        "OrderPlan: %s %.5f @ %.2f (notional=%.2f) exposure %.4f→%.4f",
        plan.side, plan.qty, plan.est_fill_price, plan.notional,
        plan.current_exposure, plan.clamped_exposure,
    )
    return plan


# ---------------------------------------------------------------------------
# CSV logging
# ---------------------------------------------------------------------------

def _log_csv(plan: OrderPlan, csv_path: str | Path | None) -> None:
    if csv_path is None:
        return
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(_CSV_FIELDS)
        w.writerow([
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            plan.side,
            f"{plan.qty:.8f}",
            f"{plan.est_fill_price:.2f}",
            f"{plan.notional:.2f}",
            plan.reason,
            f"{plan.nav_usdt:.2f}",
            f"{plan.btc_qty:.8f}",
            f"{plan.mid_price:.2f}",
            f"{plan.target_exposure:.6f}",
            f"{plan.clamped_exposure:.6f}",
            f"{plan.current_exposure:.6f}",
            f"{plan.desired_btc_value:.2f}",
            f"{plan.current_btc_value:.2f}",
            f"{plan.delta_value:.2f}",
        ])
