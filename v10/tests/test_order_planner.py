"""Tests for order_planner — pure-function order planning from target exposure."""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from v10.core.types import CostConfig, SCENARIOS
from v10.exchange.filters import SymbolInfo
from v10.exchange.order_planner import OrderPlan, plan_order_from_target_exposure

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

# Realistic BTCUSDT filters (testnet values)
FILTERS = SymbolInfo(
    symbol="BTCUSDT",
    base_asset="BTC",
    quote_asset="USDT",
    tick_size=Decimal("0.01"),
    step_size=Decimal("0.00001"),
    min_qty=Decimal("0.00001"),
    max_qty=Decimal("9999.00000"),
    min_notional=Decimal("5.00"),
    price_precision=2,
    qty_precision=5,
)

# Base cost: per_side_bps = 5/2 + 3 + 0.10*100 = 15.5 bps
BASE_COST = SCENARIOS["base"]

# Portfolio: 10_000 USDT NAV, 0 BTC, mid = 67_000
NAV = 10_000.0
MID = 67_000.0


# ---------------------------------------------------------------------------
# 1) HOLD scenarios
# ---------------------------------------------------------------------------

class TestHold:
    def test_hold_below_min_notional(self) -> None:
        """Delta < min_notional (5 USDT) → HOLD."""
        # target_exposure=0.0004 → desired = 4.0, current = 0 → delta = 4.0 < 5.0
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.0004, filters=FILTERS, cost=BASE_COST,
        )
        assert plan.side == "HOLD"
        assert plan.reason == "below_min_notional"
        assert plan.qty == 0.0

    def test_hold_already_at_target(self) -> None:
        """Current exposure matches target → delta ≈ 0 → HOLD."""
        # 0.5 exposure @ NAV=10000 means 5000 in BTC → btc_qty=5000/67000
        btc_qty = 5000.0 / MID
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=btc_qty, mid_price=MID,
            target_exposure=0.5, filters=FILTERS, cost=BASE_COST,
        )
        assert plan.side == "HOLD"
        assert plan.reason == "below_min_notional"

    def test_hold_after_rounding_notional(self) -> None:
        """Qty rounds down such that notional < min_notional → HOLD."""
        # Very small filters to create edge case
        tiny_filters = SymbolInfo(
            symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT",
            tick_size=Decimal("0.01"), step_size=Decimal("0.001"),
            min_qty=Decimal("0.001"), max_qty=Decimal("9999"),
            min_notional=Decimal("5.00"),
            price_precision=2, qty_precision=3,
        )
        # delta ~= 5.5 USDT → raw_qty ~= 0.000082 → rounds to 0.000 → qty < min_qty
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.00055, filters=tiny_filters, cost=BASE_COST,
        )
        assert plan.side == "HOLD"
        assert "after_rounding" in plan.reason

    def test_hold_qty_below_min_after_rounding(self) -> None:
        """Rounded qty < min_qty → HOLD."""
        big_min_qty_filters = SymbolInfo(
            symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT",
            tick_size=Decimal("0.01"), step_size=Decimal("0.001"),
            min_qty=Decimal("0.01"), max_qty=Decimal("9999"),
            min_notional=Decimal("5.00"),
            price_precision=2, qty_precision=3,
        )
        # delta ~= 6 USDT → raw_qty ~= 0.0000895 → rounds to 0.000 < min_qty 0.01
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.0006, filters=big_min_qty_filters, cost=BASE_COST,
        )
        assert plan.side == "HOLD"
        assert "after_rounding" in plan.reason


# ---------------------------------------------------------------------------
# 2) BUY scenarios
# ---------------------------------------------------------------------------

class TestBuy:
    def test_buy_basic(self) -> None:
        """target > current → BUY with correct qty and est_fill."""
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.50, filters=FILTERS, cost=BASE_COST,
        )
        assert plan.side == "BUY"
        assert plan.qty > 0
        assert plan.est_fill_price > MID  # BUY cost increases price
        assert plan.notional == pytest.approx(plan.qty * plan.est_fill_price, rel=1e-6)
        # desired = 0.5 * 10000 = 5000
        assert plan.desired_btc_value == pytest.approx(5000.0)
        assert plan.delta_value == pytest.approx(5000.0)

    def test_buy_est_fill_uses_cost(self) -> None:
        """BUY est_fill = mid * (1 + per_side_bps/10000)."""
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.50, filters=FILTERS, cost=BASE_COST,
        )
        expected_fill = MID * (1 + BASE_COST.per_side_bps / 10_000)
        assert plan.est_fill_price == pytest.approx(expected_fill, rel=1e-9)


# ---------------------------------------------------------------------------
# 3) SELL scenarios
# ---------------------------------------------------------------------------

class TestSell:
    def test_sell_basic(self) -> None:
        """target < current → SELL."""
        # Current: 0.5 exposure → btc_qty = 5000/67000
        btc_qty = 5000.0 / MID
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=btc_qty, mid_price=MID,
            target_exposure=0.0, filters=FILTERS, cost=BASE_COST,
        )
        assert plan.side == "SELL"
        assert plan.qty > 0
        assert plan.est_fill_price < MID  # SELL cost decreases price

    def test_sell_capped_at_holdings(self) -> None:
        """SELL qty cannot exceed btc_qty."""
        btc_qty = 0.01  # small position
        plan = plan_order_from_target_exposure(
            nav_usdt=100_000.0, btc_qty=btc_qty, mid_price=MID,
            target_exposure=0.0, filters=FILTERS, cost=BASE_COST,
        )
        assert plan.side == "SELL"
        assert plan.qty <= btc_qty

    def test_sell_est_fill_uses_cost(self) -> None:
        """SELL est_fill = mid * (1 - per_side_bps/10000)."""
        btc_qty = 5000.0 / MID
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=btc_qty, mid_price=MID,
            target_exposure=0.0, filters=FILTERS, cost=BASE_COST,
        )
        expected_fill = MID * (1 - BASE_COST.per_side_bps / 10_000)
        assert plan.est_fill_price == pytest.approx(expected_fill, rel=1e-9)


# ---------------------------------------------------------------------------
# 4) Clamping
# ---------------------------------------------------------------------------

class TestClamp:
    def test_clamp_above_max(self) -> None:
        """target > max_total_exposure → clamped down."""
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=1.5, filters=FILTERS,
            max_total_exposure=0.8, cost=BASE_COST,
        )
        assert plan.clamped_exposure == 0.8
        assert plan.target_exposure == 1.5
        assert plan.desired_btc_value == pytest.approx(0.8 * NAV)

    def test_clamp_below_zero(self) -> None:
        """target < 0 → clamped to 0."""
        btc_qty = 5000.0 / MID
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=btc_qty, mid_price=MID,
            target_exposure=-0.5, filters=FILTERS, cost=BASE_COST,
        )
        assert plan.clamped_exposure == 0.0
        assert plan.side == "SELL"


# ---------------------------------------------------------------------------
# 5) Cost model
# ---------------------------------------------------------------------------

class TestCostModel:
    def test_default_cost_is_base(self) -> None:
        """No cost arg → uses SCENARIOS['base']."""
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.50, filters=FILTERS,
        )
        expected_fill = MID * (1 + SCENARIOS["base"].per_side_bps / 10_000)
        assert plan.est_fill_price == pytest.approx(expected_fill, rel=1e-9)

    def test_cost_model_affects_fill_price(self) -> None:
        """Different cost configs produce different est_fill prices."""
        plan_smart = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.50, filters=FILTERS, cost=SCENARIOS["smart"],
        )
        plan_harsh = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.50, filters=FILTERS, cost=SCENARIOS["harsh"],
        )
        # Harsh cost → higher est_fill (more expensive) → slightly less qty
        assert plan_harsh.est_fill_price > plan_smart.est_fill_price
        assert plan_harsh.qty < plan_smart.qty


# ---------------------------------------------------------------------------
# 6) CSV logging
# ---------------------------------------------------------------------------

class TestCsvLogging:
    def test_csv_row_appended(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "live_plan.csv"
        plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.50, filters=FILTERS, cost=BASE_COST,
            csv_path=csv_file,
        )
        with open(csv_file) as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2  # header + 1 data row
        assert rows[0][0] == "timestamp_iso"
        assert rows[1][1] == "BUY"

    def test_csv_appends_multiple(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "live_plan.csv"
        for _ in range(3):
            plan_order_from_target_exposure(
                nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
                target_exposure=0.50, filters=FILTERS, cost=BASE_COST,
                csv_path=csv_file,
            )
        with open(csv_file) as f:
            rows = list(csv.reader(f))
        assert len(rows) == 4  # header + 3 data rows

    def test_no_csv_when_path_none(self) -> None:
        """csv_path=None → no crash, no file created."""
        plan = plan_order_from_target_exposure(
            nav_usdt=NAV, btc_qty=0.0, mid_price=MID,
            target_exposure=0.50, filters=FILTERS, cost=BASE_COST,
            csv_path=None,
        )
        assert plan.side == "BUY"
