"""Tests for ExecutionModel and Portfolio — validates SPEC_EXECUTION.md formulas."""

from __future__ import annotations

import math

import pytest

from v10.core.types import CostConfig, SCENARIOS, Side
from v10.core.execution import ExecutionModel, Portfolio


# ---------------------------------------------------------------------------
# ExecutionModel — price calculations
# ---------------------------------------------------------------------------

class TestExecutionModel:
    def test_bid_ask_base(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        bid, ask = em.bid_ask(65_000.0)
        # spread_bps=5.0 → half=2.5bps=0.00025
        assert bid == pytest.approx(65_000 * (1 - 0.00025), rel=1e-9)
        assert ask == pytest.approx(65_000 * (1 + 0.00025), rel=1e-9)

    def test_fill_buy_price_base(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        fp = em.fill_buy_price(65_000.0)
        # ask = 65000*1.00025,  fill = ask*1.0003
        expected = 65_000 * (1 + 0.00025) * (1 + 0.0003)
        assert fp == pytest.approx(expected, rel=1e-9)

    def test_fill_sell_price_base(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        fp = em.fill_sell_price(65_000.0)
        expected = 65_000 * (1 - 0.00025) * (1 - 0.0003)
        assert fp == pytest.approx(expected, rel=1e-9)

    def test_fee_rate(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        assert em.fee_rate == pytest.approx(0.001, rel=1e-9)

    def test_fee_rate_smart(self) -> None:
        em = ExecutionModel(SCENARIOS["smart"])
        assert em.fee_rate == pytest.approx(0.00035, rel=1e-9)


# ---------------------------------------------------------------------------
# CostConfig — round-trip costs per SPEC
# ---------------------------------------------------------------------------

class TestCostScenarios:
    """Verify canonical RT costs — base=31bps, NOT 26bps (label mismatch)."""

    def test_base_per_side(self) -> None:
        cfg = SCENARIOS["base"]
        # 2.5 + 3.0 + 10.0 = 15.5 bps per side
        assert cfg.per_side_bps == pytest.approx(15.5)

    def test_base_round_trip(self) -> None:
        cfg = SCENARIOS["base"]
        assert cfg.round_trip_bps == pytest.approx(31.0)

    def test_smart_round_trip(self) -> None:
        cfg = SCENARIOS["smart"]
        # spread/2=1.5 + slip=1.5 + fee=3.5bps = 6.5 per side → 13 RT
        assert cfg.per_side_bps == pytest.approx(6.5)
        assert cfg.round_trip_bps == pytest.approx(13.0)

    def test_harsh_round_trip(self) -> None:
        cfg = SCENARIOS["harsh"]
        # 10/2 + 5 + 0.15*100 = 5+5+15 = 25 per side → 50 RT
        assert cfg.round_trip_bps == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Portfolio — buy / sell / cash constraint
# ---------------------------------------------------------------------------

class TestPortfolioBuy:
    def test_buy_basic(self) -> None:
        pf = Portfolio(10_000.0, ExecutionModel(SCENARIOS["base"]))
        fill = pf.buy(0.1, 65_000.0, 1000, "test_buy")
        assert fill is not None
        assert fill.side == Side.BUY
        assert fill.qty == pytest.approx(0.1, abs=1e-8)
        assert pf.btc_qty == pytest.approx(0.1, abs=1e-8)
        assert pf.cash < 10_000.0

    def test_buy_cost_accounting(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        pf = Portfolio(10_000.0, em)
        fill = pf.buy(0.1, 65_000.0, 1000, "test")
        expected_fp = em.fill_buy_price(65_000.0)
        expected_notional = 0.1 * expected_fp
        expected_fee = expected_notional * em.fee_rate
        expected_total = expected_notional + expected_fee
        assert pf.cash == pytest.approx(10_000.0 - expected_total, abs=0.01)

    def test_buy_cash_constraint(self) -> None:
        """With only $100, cannot buy 1 BTC at $65k — qty must be reduced."""
        pf = Portfolio(100.0, ExecutionModel(SCENARIOS["base"]))
        fill = pf.buy(1.0, 65_000.0, 1000, "test")
        assert fill is not None
        assert fill.qty < 1.0
        assert fill.qty > 0
        assert pf.cash >= -0.01  # should not go significantly negative

    def test_buy_zero_qty(self) -> None:
        pf = Portfolio(10_000.0, ExecutionModel(SCENARIOS["base"]))
        fill = pf.buy(0.0, 65_000.0, 1000, "test")
        assert fill is None
        assert pf.btc_qty == 0.0


class TestPortfolioSell:
    def test_sell_basic(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        pf = Portfolio(10_000.0, em)
        pf.buy(0.1, 65_000.0, 1000, "buy")
        cash_after_buy = pf.cash
        fill = pf.sell(0.1, 67_000.0, 2000, "sell")
        assert fill is not None
        assert fill.side == Side.SELL
        assert pf.btc_qty == 0.0
        assert pf.cash > cash_after_buy  # got proceeds

    def test_sell_proceeds_accounting(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        pf = Portfolio(10_000.0, em)
        pf.buy(0.1, 65_000.0, 1000, "buy")
        cash_before_sell = pf.cash
        pf.sell(0.1, 67_000.0, 2000, "sell")
        expected_fp = em.fill_sell_price(67_000.0)
        expected_notional = 0.1 * expected_fp
        expected_fee = expected_notional * em.fee_rate
        expected_proceeds = expected_notional - expected_fee
        assert pf.cash == pytest.approx(cash_before_sell + expected_proceeds, abs=0.01)

    def test_sell_caps_at_holdings(self) -> None:
        pf = Portfolio(10_000.0, ExecutionModel(SCENARIOS["base"]))
        pf.buy(0.1, 65_000.0, 1000, "buy")
        fill = pf.sell(999.0, 65_000.0, 2000, "sell")  # try to sell way more
        assert fill is not None
        assert fill.qty == pytest.approx(0.1, abs=1e-8)
        assert pf.btc_qty == 0.0

    def test_sell_nothing(self) -> None:
        pf = Portfolio(10_000.0, ExecutionModel(SCENARIOS["base"]))
        fill = pf.sell(1.0, 65_000.0, 1000, "sell")
        assert fill is None


class TestPortfolioTradeRecord:
    def test_trade_created_on_close(self) -> None:
        pf = Portfolio(10_000.0, ExecutionModel(SCENARIOS["base"]))
        pf.buy(0.1, 65_000.0, 1000, "entry")
        assert len(pf.trades) == 0
        pf.sell(0.1, 67_000.0, 2000, "exit")
        assert len(pf.trades) == 1
        t = pf.trades[0]
        assert t.entry_ts_ms == 1000
        assert t.exit_ts_ms == 2000
        assert t.entry_reason == "entry"
        assert t.exit_reason == "exit"
        assert t.pnl != 0  # should have some PnL

    def test_weighted_avg_entry(self) -> None:
        em = ExecutionModel(SCENARIOS["base"])
        pf = Portfolio(100_000.0, em)
        pf.buy(0.1, 60_000.0, 1000, "buy1")
        pf.buy(0.1, 70_000.0, 2000, "buy2")
        # Weighted avg should be between the two fill prices
        fp1 = em.fill_buy_price(60_000.0)
        fp2 = em.fill_buy_price(70_000.0)
        expected_avg = (0.1 * fp1 + 0.1 * fp2) / 0.2
        assert pf.entry_price_avg == pytest.approx(expected_avg, rel=1e-6)
