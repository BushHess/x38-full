"""Tests for AccountScope and reset_to_cash — all mocked, no network."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from v10.exchange.account_scope import AccountScope, ResetResult, fetch_account_scope, reset_to_cash
from v10.exchange.filters import SymbolInfo
from v10.exchange.rest_client import AccountBalance, BinanceSpotClient, OrderResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(base_url: str = "https://testnet.binance.vision/api") -> BinanceSpotClient:
    return BinanceSpotClient(base_url=base_url, api_key="k", api_secret="s")


def _mock_balances(*pairs: tuple[str, float, float]) -> list[AccountBalance]:
    return [AccountBalance(asset=a, free=f, locked=l) for a, f, l in pairs]


_BTCUSDT_INFO = SymbolInfo(
    symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT",
    tick_size=Decimal("0.01"), step_size=Decimal("0.00001"),
    min_qty=Decimal("0.00001"), max_qty=Decimal("9000"),
    min_notional=Decimal("10"), price_precision=2, qty_precision=5,
)

_SELL_ORDER = OrderResponse(
    symbol="BTCUSDT", order_id=999, client_order_id="x",
    price=0.0, orig_qty=0.5, executed_qty=0.5,
    status="FILLED", side="SELL", type="MARKET", time_in_force="",
)


# ---------------------------------------------------------------------------
# 1) fetch_account_scope
# ---------------------------------------------------------------------------

class TestFetchAccountScope:
    def test_nav_with_btc_and_usdt(self) -> None:
        client = _make_client()
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("BTC", 0.5, 0.0), ("USDT", 5000.0, 0.0), ("ETH", 10.0, 0.0),
        ))
        client.klines = MagicMock(return_value=[  # type: ignore[assignment]
            [0, "0", "0", "0", "60000.00", "0", 0, "0", 0, "0", "0", "0"],
        ])

        scope = fetch_account_scope(client)

        assert scope.btc_free == 0.5
        assert scope.usdt_free == 5000.0
        assert scope.btc_price == 60000.0
        # NAV = 5000 + 0.5*60000 = 35000
        assert scope.nav_usdt == pytest.approx(35000.0)
        # exposure = 30000 / 35000
        assert scope.exposure == pytest.approx(30000.0 / 35000.0)

    def test_zero_btc(self) -> None:
        client = _make_client()
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("USDT", 10000.0, 0.0),
        ))
        client.klines = MagicMock(return_value=[  # type: ignore[assignment]
            [0, "0", "0", "0", "67000.00", "0", 0, "0", 0, "0", "0", "0"],
        ])

        scope = fetch_account_scope(client)

        assert scope.btc_free == 0.0
        assert scope.nav_usdt == pytest.approx(10000.0)
        assert scope.exposure == pytest.approx(0.0)

    def test_zero_usdt(self) -> None:
        client = _make_client()
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("BTC", 1.0, 0.0),
        ))
        client.klines = MagicMock(return_value=[  # type: ignore[assignment]
            [0, "0", "0", "0", "50000.00", "0", 0, "0", 0, "0", "0", "0"],
        ])

        scope = fetch_account_scope(client)

        assert scope.usdt_free == 0.0
        assert scope.nav_usdt == pytest.approx(50000.0)
        assert scope.exposure == pytest.approx(1.0)

    def test_ignores_other_assets(self) -> None:
        client = _make_client()
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("BTC", 0.1, 0.0), ("USDT", 1000.0, 0.0),
            ("ETH", 100.0, 0.0), ("SOL", 500.0, 0.0),
        ))
        client.klines = MagicMock(return_value=[  # type: ignore[assignment]
            [0, "0", "0", "0", "60000.00", "0", 0, "0", 0, "0", "0", "0"],
        ])

        scope = fetch_account_scope(client)

        # NAV only counts BTC+USDT: 1000 + 0.1*60000 = 7000
        assert scope.nav_usdt == pytest.approx(7000.0)

    def test_locked_balances_included(self) -> None:
        client = _make_client()
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("BTC", 0.3, 0.2), ("USDT", 4000.0, 1000.0),
        ))
        client.klines = MagicMock(return_value=[  # type: ignore[assignment]
            [0, "0", "0", "0", "50000.00", "0", 0, "0", 0, "0", "0", "0"],
        ])

        scope = fetch_account_scope(client)

        # btc_total=0.5, usdt_total=5000, NAV=5000+0.5*50000=30000
        assert scope.nav_usdt == pytest.approx(30000.0)
        assert scope.exposure == pytest.approx(25000.0 / 30000.0)


# ---------------------------------------------------------------------------
# 2) reset_to_cash
# ---------------------------------------------------------------------------

class TestResetToCash:
    def test_mainnet_guard_raises(self) -> None:
        client = _make_client(base_url="https://api.binance.com/api")
        with pytest.raises(RuntimeError, match="testnet"):
            reset_to_cash(client)

    def test_cancels_orders_and_sells_btc(self) -> None:
        client = _make_client()
        client.cancel_all_orders = MagicMock(return_value=[MagicMock(), MagicMock()])  # type: ignore[assignment]
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("BTC", 0.5, 0.0), ("USDT", 5000.0, 0.0),
        ))
        client.place_order = MagicMock(return_value=_SELL_ORDER)  # type: ignore[assignment]

        with patch("v10.exchange.account_scope.fetch_symbol_info", return_value=_BTCUSDT_INFO):
            result = reset_to_cash(client)

        assert result.cancelled_count == 2
        assert result.sold_btc == 0.5
        assert result.sell_order is not None
        client.place_order.assert_called_once()
        call_kwargs = client.place_order.call_args
        assert call_kwargs[1]["side"] == "SELL"
        assert call_kwargs[1]["type"] == "MARKET"

    def test_no_btc_skips_sell(self) -> None:
        client = _make_client()
        client.cancel_all_orders = MagicMock(return_value=[])  # type: ignore[assignment]
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("USDT", 10000.0, 0.0),
        ))

        result = reset_to_cash(client)

        assert result.cancelled_count == 0
        assert result.sold_btc == 0.0
        assert result.sell_order is None

    def test_tiny_btc_below_min_qty_skips_sell(self) -> None:
        client = _make_client()
        client.cancel_all_orders = MagicMock(return_value=[])  # type: ignore[assignment]
        # BTC balance that rounds down to 0 (below step_size)
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("BTC", 0.000001, 0.0), ("USDT", 5000.0, 0.0),
        ))

        with patch("v10.exchange.account_scope.fetch_symbol_info", return_value=_BTCUSDT_INFO):
            result = reset_to_cash(client)

        assert result.sold_btc == 0.0
        assert result.sell_order is None

    def test_qty_rounded_down(self) -> None:
        client = _make_client()
        client.cancel_all_orders = MagicMock(return_value=[])  # type: ignore[assignment]
        # BTC with trailing digits beyond step_size
        client.account = MagicMock(return_value=_mock_balances(  # type: ignore[assignment]
            ("BTC", 0.123456789, 0.0), ("USDT", 5000.0, 0.0),
        ))
        client.place_order = MagicMock(return_value=OrderResponse(  # type: ignore[assignment]
            symbol="BTCUSDT", order_id=1, client_order_id="x",
            price=0.0, orig_qty=0.12345, executed_qty=0.12345,
            status="FILLED", side="SELL", type="MARKET", time_in_force="",
        ))

        with patch("v10.exchange.account_scope.fetch_symbol_info", return_value=_BTCUSDT_INFO):
            result = reset_to_cash(client)

        # Should have rounded 0.123456789 → 0.12345
        call_kwargs = client.place_order.call_args
        assert call_kwargs[1]["quantity"] == pytest.approx(0.12345)
