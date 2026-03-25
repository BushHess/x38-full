"""AccountScope — portfolio NAV/exposure scoped to BTC + USDT only.

Also provides ``reset_to_cash`` (testnet-only) to flatten the account.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from v10.exchange.filters import fetch_symbol_info
from v10.exchange.filters import round_qty_down
from v10.exchange.rest_client import BinanceSpotClient
from v10.exchange.rest_client import OrderResponse

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AccountScope
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AccountScope:
    """Portfolio snapshot scoped to BTC + USDT."""

    btc_free: float
    btc_locked: float
    usdt_free: float
    usdt_locked: float
    btc_price: float
    nav_usdt: float
    exposure: float  # BTC-value / NAV  (0.0–1.0)


def fetch_account_scope(
    client: BinanceSpotClient,
    symbol: str = "BTCUSDT",
) -> AccountScope:
    """Query account + last price, return scoped NAV and exposure."""
    balances = client.account()

    btc_free = btc_locked = 0.0
    usdt_free = usdt_locked = 0.0
    for b in balances:
        if b.asset == "BTC":
            btc_free = b.free
            btc_locked = b.locked
        elif b.asset == "USDT":
            usdt_free = b.free
            usdt_locked = b.locked

    # Last close from 1-minute kline
    klines = client.klines(symbol, "1m", limit=1)
    btc_price = float(klines[-1][4]) if klines else 0.0  # index 4 = close

    btc_total = btc_free + btc_locked
    usdt_total = usdt_free + usdt_locked
    nav = usdt_total + btc_total * btc_price
    exposure = (btc_total * btc_price) / nav if nav > 0 else 0.0

    return AccountScope(
        btc_free=btc_free,
        btc_locked=btc_locked,
        usdt_free=usdt_free,
        usdt_locked=usdt_locked,
        btc_price=btc_price,
        nav_usdt=nav,
        exposure=exposure,
    )


# ---------------------------------------------------------------------------
# Reset to cash (TESTNET ONLY)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ResetResult:
    """Summary of a reset-to-cash operation."""

    cancelled_count: int
    sold_btc: float
    sell_order: OrderResponse | None


def reset_to_cash(
    client: BinanceSpotClient,
    symbol: str = "BTCUSDT",
) -> ResetResult:
    """Cancel all open orders and market-sell all BTC to USDT.

    **TESTNET ONLY** — raises ``RuntimeError`` if the client base URL
    does not contain ``"testnet"``.
    """
    if "testnet" not in client._base_url:
        raise RuntimeError(f"reset_to_cash is restricted to testnet. Current base_url: {client._base_url}")

    # 1) Cancel all open orders
    cancelled = client.cancel_all_orders(symbol)
    cancelled_count = len(cancelled)
    if cancelled_count:
        _log.info("Cancelled %d open order(s)", cancelled_count)

    # 2) Check BTC balance
    balances = client.account()
    btc_free = 0.0
    for b in balances:
        if b.asset == "BTC":
            btc_free = b.free
            break

    # 3) Market-sell BTC if any
    sell_order: OrderResponse | None = None
    sold_btc = 0.0

    if btc_free > 0:
        info = fetch_symbol_info(client, symbol)
        qty = round_qty_down(btc_free, info)

        if qty >= float(info.min_qty):
            _log.info("Selling %.8f BTC (rounded from %.8f)", qty, btc_free)
            sell_order = client.place_order(
                symbol=symbol,
                side="SELL",
                type="MARKET",
                quantity=qty,
            )
            sold_btc = sell_order.executed_qty
        else:
            _log.info("BTC balance %.8f below minQty %s, skipping sell", btc_free, info.min_qty)

    return ResetResult(
        cancelled_count=cancelled_count,
        sold_btc=sold_btc,
        sell_order=sell_order,
    )
