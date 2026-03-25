from __future__ import annotations

import pytest

from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Config,
    VTrendE5Ema21D1Strategy,
)
from strategies.vtrend_ema21_d1.strategy import (
    VTrendEma21D1Config,
    VTrendEma21D1Strategy,
)
from v10.core.types import Bar


def _make_bar(
    *,
    close: float,
    open_time: int,
    close_time: int,
    interval: str = "4h",
) -> Bar:
    return Bar(
        open_time=open_time,
        open=close,
        high=close * 1.01,
        low=close * 0.99,
        close=close,
        volume=100.0,
        close_time=close_time,
        taker_buy_base_vol=50.0,
        interval=interval,
    )


@pytest.mark.parametrize(
    ("strategy_cls", "config"),
    [
        (VTrendEma21D1Strategy, VTrendEma21D1Config(d1_ema_period=1)),
        (VTrendE5Ema21D1Strategy, VTrendE5Ema21D1Config(d1_ema_period=1)),
    ],
)
def test_d1_regime_uses_only_completed_daily_bar(strategy_cls, config) -> None:
    d1_bars = [
        _make_bar(close=100.0, open_time=0, close_time=86_399_999, interval="1d"),
        _make_bar(
            close=200.0,
            open_time=86_400_000,
            close_time=172_799_999,
            interval="1d",
        ),
    ]
    h4_bars = [
        _make_bar(close=50.0, open_time=0, close_time=14_399_999),
        _make_bar(close=150.0, open_time=86_400_000, close_time=100_799_999),
        _make_bar(close=160.0, open_time=100_800_000, close_time=115_199_999),
        _make_bar(close=190.0, open_time=172_800_000, close_time=187_199_999),
    ]

    strategy = strategy_cls(config)
    strategy.on_init(h4_bars, d1_bars)

    regime = strategy._d1_regime_ok
    assert regime is not None
    assert bool(regime[0]) is False
    assert bool(regime[1]) is False
    assert bool(regime[2]) is False


@pytest.mark.parametrize(
    ("strategy_cls", "config"),
    [
        (VTrendEma21D1Strategy, VTrendEma21D1Config(d1_ema_period=1)),
        (VTrendE5Ema21D1Strategy, VTrendE5Ema21D1Config(d1_ema_period=1)),
    ],
)
def test_future_daily_bar_is_not_visible(strategy_cls, config) -> None:
    d1_bars = [
        _make_bar(
            close=500.0,
            open_time=0,
            close_time=999_999_999,
            interval="1d",
        ),
    ]
    h4_bars = [
        _make_bar(close=50.0, open_time=0, close_time=14_399_999),
    ]

    strategy = strategy_cls(config)
    strategy.on_init(h4_bars, d1_bars)

    assert bool(strategy._d1_regime_ok[0]) is False
