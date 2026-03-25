"""Tests for compute_metrics — validates SPEC_METRICS.md formulas."""

from __future__ import annotations

import math

import pytest

from v10.core.types import EquitySnap, Fill, Trade, Side
from v10.core.metrics import compute_metrics, _max_drawdown_pct, _sharpe_sortino

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_equity(
    navs: list[float],
    start_ms: int = 0,
    step_ms: int = 14_400_000,  # 4 hours
) -> list[EquitySnap]:
    """Create equity snapshots from a NAV sequence (4H spacing)."""
    return [
        EquitySnap(
            close_time=start_ms + i * step_ms,
            nav_mid=n,
            nav_liq=n * 0.999,
            cash=n * 0.5,
            btc_qty=0.0,
            exposure=0.5,
        )
        for i, n in enumerate(navs)
    ]


def _make_trade(pnl: float, days: float = 10.0) -> Trade:
    return Trade(
        trade_id=0,
        entry_ts_ms=0,
        exit_ts_ms=int(days * 86_400_000),
        entry_price=100.0,
        exit_price=100.0 + pnl,
        qty=1.0,
        pnl=pnl,
        return_pct=pnl,
        days_held=days,
        entry_reason="test",
        exit_reason="test",
    )


# ---------------------------------------------------------------------------
# CAGR
# ---------------------------------------------------------------------------

class TestCAGR:
    def test_doubling_one_year(self) -> None:
        """$10k → $20k in ~1 year ≈ 100% CAGR."""
        n_bars = int(365 * 24 / 4)  # ~2190 4H bars in a year
        navs = [10_000.0 + i * (10_000.0 / n_bars) for i in range(n_bars + 1)]
        navs[-1] = 20_000.0
        m = compute_metrics(_make_equity(navs), [], [], 10_000.0)
        assert abs(m["cagr_pct"] - 100.0) < 3.0  # within 3% tolerance

    def test_flat_equity(self) -> None:
        navs = [10_000.0] * 500
        m = compute_metrics(_make_equity(navs), [], [], 10_000.0)
        assert abs(m["cagr_pct"]) < 0.01

    def test_loss(self) -> None:
        navs = [10_000.0, 9_500.0, 9_000.0, 8_500.0]
        m = compute_metrics(_make_equity(navs), [], [], 10_000.0)
        assert m["cagr_pct"] < 0


# ---------------------------------------------------------------------------
# Max Drawdown
# ---------------------------------------------------------------------------

class TestMaxDrawdown:
    def test_basic_drawdown(self) -> None:
        """Peak 110, trough 70 → DD = (110-70)/110 = 36.36%."""
        navs = [100.0, 110.0, 90.0, 70.0, 80.0, 100.0]
        dd = _max_drawdown_pct(np.array(navs))
        expected = (1.0 - 70.0 / 110.0) * 100.0
        assert dd == pytest.approx(expected, abs=0.01)

    def test_no_drawdown(self) -> None:
        navs = [100.0, 110.0, 120.0, 130.0]
        dd = _max_drawdown_pct(np.array(navs))
        assert dd == pytest.approx(0.0, abs=0.01)

    def test_monotone_decline(self) -> None:
        navs = [100.0, 80.0, 60.0, 40.0]
        dd = _max_drawdown_pct(np.array(navs))
        assert dd == pytest.approx(60.0, abs=0.01)


# ---------------------------------------------------------------------------
# Sharpe / Sortino
# ---------------------------------------------------------------------------

class TestSharpe:
    def test_positive_sharpe_for_uptrend(self) -> None:
        navs = [100.0 + i * 0.5 for i in range(200)]
        sharpe, sortino = _sharpe_sortino(np.array(navs))
        assert sharpe is not None
        assert sharpe > 0

    def test_sortino_greater_than_sharpe(self) -> None:
        """Sortino uses only downside vol → should be >= Sharpe for uptrend."""
        import random
        random.seed(42)
        navs: list[float] = [100.0]
        for _ in range(500):
            # Positive drift with genuine drawdowns
            navs.append(navs[-1] * (1 + random.gauss(0.0003, 0.005)))
        sharpe, sortino = _sharpe_sortino(np.array(navs))
        assert sharpe is not None and sortino is not None
        assert sortino >= sharpe

    def test_flat_returns(self) -> None:
        navs = [100.0] * 100
        sharpe, sortino = _sharpe_sortino(np.array(navs))
        # All returns are 0 → std=0 → Sharpe undefined
        assert sharpe is None


# ---------------------------------------------------------------------------
# Trade-level metrics
# ---------------------------------------------------------------------------

class TestTradeMetrics:
    def test_profit_factor(self) -> None:
        trades = [_make_trade(100.0), _make_trade(-50.0)]
        m = compute_metrics(_make_equity([100, 150, 100]), trades, [], 100.0)
        assert m["profit_factor"] == pytest.approx(2.0, abs=0.01)

    def test_profit_factor_no_losses(self) -> None:
        trades = [_make_trade(100.0), _make_trade(50.0)]
        # Need enough bars so CAGR doesn't overflow
        navs = [100.0 + i * 0.5 for i in range(200)]
        m = compute_metrics(_make_equity(navs), trades, [], 100.0)
        assert m["profit_factor"] == "inf"

    def test_win_rate(self) -> None:
        trades = [_make_trade(10.0), _make_trade(-5.0), _make_trade(3.0)]
        m = compute_metrics(_make_equity([100, 110, 105, 108]), trades, [], 100.0)
        assert m["win_rate_pct"] == pytest.approx(66.67, abs=0.01)

    def test_no_trades(self) -> None:
        m = compute_metrics(_make_equity([100, 110, 120]), [], [], 100.0)
        assert m["trades"] == 0
        assert m["win_rate_pct"] == 0.0
        assert m["profit_factor"] == 0.0


# ---------------------------------------------------------------------------
# Exposure & Fees
# ---------------------------------------------------------------------------

class TestExposureAndFees:
    def test_fee_drag(self) -> None:
        fills = [
            Fill(ts_ms=0, side=Side.BUY, qty=1.0, price=100.0,
                 fee=10.0, notional=100.0, reason="test"),
        ]
        # 1 year of equity at NAV=1000 with $10 fee → fee_drag = 10/1000*100 = 1%
        n_bars = int(365 * 24 / 4)
        equity = _make_equity([1000.0] * n_bars)
        m = compute_metrics(equity, [], fills, 1000.0)
        assert abs(m["fee_drag_pct_per_year"] - 1.0) < 0.15

    def test_empty_equity(self) -> None:
        m = compute_metrics([], [], [], 10_000.0)
        assert "error" in m
