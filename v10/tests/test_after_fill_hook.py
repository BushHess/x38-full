"""Tests for BacktestEngine on_after_fill hook semantics."""

from __future__ import annotations

import pytest

from v10.core.engine import BacktestEngine
from v10.core.types import Bar
from v10.core.types import CostConfig
from v10.core.types import Fill
from v10.core.types import MarketState
from v10.core.types import Side
from v10.core.types import Signal
from v10.strategies.base import Strategy

H4_MS = 14_400_000
ZERO_COST = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.0)


class _FakeFeed:
    def __init__(self, h4_bars: list[Bar], d1_bars: list[Bar] | None = None):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars or []


def _bar(index: int, open_: float, close: float, base_ms: int = 0) -> Bar:
    ot = base_ms + index * H4_MS
    return Bar(
        open_time=ot,
        open=open_,
        high=max(open_, close),
        low=min(open_, close),
        close=close,
        volume=100.0,
        close_time=ot + H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


class _HookSpyStrategy(Strategy):
    def __init__(self) -> None:
        self.after_fill: list[tuple[int, float, float, float, Side, str]] = []

    def on_bar(self, state: MarketState) -> Signal | None:
        if state.bar_index == 0:
            return Signal(target_exposure=1.0, reason="entry")
        if state.bar_index == 2:
            return Signal(target_exposure=0.0, reason="exit")
        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        self.after_fill.append(
            (
                state.bar_index,
                state.nav,
                state.cash,
                state.btc_qty,
                fill.side,
                fill.reason,
            ),
        )


def test_after_fill_hook_receives_post_fill_state_at_bar_open_mid() -> None:
    bars = [
        _bar(0, 100.0, 100.0),  # entry signal emitted at close
        _bar(1, 100.0, 101.0),  # BUY fill at open=100
        _bar(2, 102.0, 102.0),  # exit signal emitted at close
        _bar(3, 103.0, 103.0),  # SELL fill at open=103
        _bar(4, 103.0, 103.0),
    ]
    strategy = _HookSpyStrategy()
    engine = BacktestEngine(
        feed=_FakeFeed(bars),
        strategy=strategy,
        cost=ZERO_COST,
        initial_cash=10_000.0,
    )
    result = engine.run()

    assert len(result.fills) == 2
    assert len(strategy.after_fill) == 2

    buy_idx, buy_nav, buy_cash, buy_qty, buy_side, buy_reason = strategy.after_fill[0]
    assert buy_idx == 1
    assert buy_side == Side.BUY
    assert buy_reason == "entry"
    assert buy_qty == pytest.approx(100.0, abs=1e-9)
    assert buy_cash == pytest.approx(0.0, abs=1e-9)
    assert buy_nav == pytest.approx(10_000.0, abs=1e-9)

    sell_idx, sell_nav, sell_cash, sell_qty, sell_side, sell_reason = strategy.after_fill[1]
    assert sell_idx == 3
    assert sell_side == Side.SELL
    assert sell_reason == "exit"
    assert sell_qty == pytest.approx(0.0, abs=1e-9)
    assert sell_cash == pytest.approx(10_300.0, abs=1e-9)
    assert sell_nav == pytest.approx(10_300.0, abs=1e-9)
