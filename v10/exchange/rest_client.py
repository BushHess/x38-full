"""Binance Spot Testnet REST client with HMAC-SHA256 signing.

Supports public and signed endpoints with:
  - Automatic time synchronisation via /api/v3/time
  - Exponential-backoff retry for 429 / 418 / 5xx
  - Credentials from env vars BINANCE_API_KEY / BINANCE_API_SECRET
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import random
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any

import requests

_log = logging.getLogger(__name__)

TESTNET_BASE_URL = "https://testnet.binance.vision/api"

_RECV_WINDOW = 5000
_DEFAULT_TIMEOUT = 10.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_BASE_DELAY = 0.5
_DEFAULT_TIME_SYNC_TTL = 30.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BinanceAPIError(Exception):
    """Raised when Binance returns an error JSON body."""

    def __init__(self, status_code: int, code: int, msg: str) -> None:
        self.status_code = status_code
        self.code = code
        self.msg = msg
        super().__init__(f"HTTP {status_code} | code={code} | {msg}")


# ---------------------------------------------------------------------------
# Response dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AccountBalance:
    """Single asset balance from GET /api/v3/account."""

    asset: str
    free: float
    locked: float


@dataclass(frozen=True, slots=True)
class OrderResponse:
    """Response from POST /api/v3/order or GET /api/v3/order."""

    symbol: str
    order_id: int
    client_order_id: str
    price: float
    orig_qty: float
    executed_qty: float
    status: str
    side: str
    type: str
    time_in_force: str
    transact_time: int | None = None


@dataclass(frozen=True, slots=True)
class TradeResponse:
    """Single trade from GET /api/v3/myTrades."""

    id: int
    order_id: int
    symbol: str
    price: float
    qty: float
    commission: float
    commission_asset: str
    time: int
    is_buyer: bool
    is_maker: bool


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class BinanceSpotClient:
    """Binance Spot REST client with HMAC-SHA256 signing.

    Parameters
    ----------
    base_url : str
        API base URL.  Defaults to Binance Spot Testnet.
    api_key / api_secret : str | None
        Override env vars ``BINANCE_API_KEY`` / ``BINANCE_API_SECRET``.
    recv_window : int
        ``recvWindow`` for signed requests (ms).
    timeout : float
        HTTP request timeout (seconds).
    max_retries : int
        Maximum retry attempts for retryable errors.
    retry_base_delay : float
        Base delay for exponential backoff (seconds).
    time_sync_ttl : float
        Seconds before the server-time offset is re-synced.
    """

    def __init__(
        self,
        base_url: str = TESTNET_BASE_URL,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        recv_window: int = _RECV_WINDOW,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_base_delay: float = _DEFAULT_RETRY_BASE_DELAY,
        time_sync_ttl: float = _DEFAULT_TIME_SYNC_TTL,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self._api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
        if not self._api_key or not self._api_secret:
            raise ValueError(
                "BINANCE_API_KEY and BINANCE_API_SECRET must be set "
                "via constructor args or environment variables"
            )
        self._recv_window = recv_window
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._time_sync_ttl = time_sync_ttl

        self._session = requests.Session()
        self._session.headers["X-MBX-APIKEY"] = self._api_key
        self._session.headers["User-Agent"] = "v10-spot-client/1.0"

        # Time-sync state
        self._time_offset_ms: int = 0
        self._time_synced_at: float = 0.0  # monotonic clock

    # ── Time synchronisation ──────────────────────────────────

    def _sync_time(self) -> None:
        """Fetch server time and compute local→server offset."""
        local_before = int(time.time() * 1000)
        data = self._request("GET", "/v3/time", signed=False)
        local_after = int(time.time() * 1000)
        server_time = int(data["serverTime"])
        local_mid = (local_before + local_after) // 2
        self._time_offset_ms = server_time - local_mid
        self._time_synced_at = time.monotonic()

    def _server_timestamp_ms(self) -> int:
        """Return estimated server time (local_ms + offset).

        Re-syncs when the cached offset is older than *time_sync_ttl*.
        """
        elapsed = time.monotonic() - self._time_synced_at
        if self._time_synced_at == 0.0 or elapsed > self._time_sync_ttl:
            self._sync_time()
        return int(time.time() * 1000) + self._time_offset_ms

    # ── Signing ───────────────────────────────────────────────

    @staticmethod
    def _sign(query_string: str, secret: str) -> str:
        """HMAC-SHA256 hex digest of *query_string*."""
        return hmac.new(
            secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _build_signed_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add ``timestamp``, ``recvWindow``, and ``signature`` to *params*."""
        params = dict(params)
        params["timestamp"] = self._server_timestamp_ms()
        params["recvWindow"] = self._recv_window
        query_string = urllib.parse.urlencode(params, doseq=False)
        params["signature"] = self._sign(query_string, self._api_secret)
        return params

    # ── HTTP transport ────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
    ) -> Any:
        """Send request with retry on 429 / 418 / 5xx / connection errors.

        Returns parsed JSON.  Raises :class:`BinanceAPIError` on
        non-retryable API errors or after retries are exhausted.
        """
        url = f"{self._base_url}{path}"
        params = dict(params) if params else {}

        if signed:
            params = self._build_signed_params(params)

        last_exc: Exception | None = None
        _retried_timestamp = False

        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.request(
                    method, url, params=params, timeout=self._timeout,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_base_delay * (2 ** attempt)
                    jitter = random.uniform(0, delay * 0.5)
                    _log.warning(
                        "%s (attempt %d/%d), sleeping %.2fs",
                        type(exc).__name__, attempt + 1,
                        self._max_retries + 1, delay + jitter,
                    )
                    time.sleep(delay + jitter)
                    continue
                raise

            # ── Parse error body ──────────────────────────────
            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    code = int(body.get("code", -1))
                    msg = str(body.get("msg", resp.text))
                except (ValueError, KeyError):
                    code, msg = -1, resp.text

                # Timestamp error → re-sync once
                if code == -1021 and signed and not _retried_timestamp:
                    _log.warning("Timestamp error (-1021), re-syncing time")
                    _retried_timestamp = True
                    self._sync_time()
                    base_params = {
                        k: v for k, v in params.items()
                        if k not in ("timestamp", "recvWindow", "signature")
                    }
                    params = self._build_signed_params(base_params)
                    continue

                # Retryable status codes
                if resp.status_code in (429, 418) or resp.status_code >= 500:
                    last_exc = BinanceAPIError(resp.status_code, code, msg)
                    if attempt < self._max_retries:
                        delay = self._retry_base_delay * (2 ** attempt)
                        jitter = random.uniform(0, delay * 0.5)
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after:
                            delay = max(delay, float(retry_after))
                        _log.warning(
                            "Retryable %d (attempt %d/%d), sleeping %.2fs",
                            resp.status_code, attempt + 1,
                            self._max_retries + 1, delay + jitter,
                        )
                        time.sleep(delay + jitter)
                        continue
                    raise BinanceAPIError(resp.status_code, code, msg)

                # Non-retryable client error
                raise BinanceAPIError(resp.status_code, code, msg)

            return resp.json()

        # All retries exhausted (should not normally reach here)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Retry loop exited without returning or raising")  # pragma: no cover

    # ── Public endpoints ──────────────────────────────────────

    @property
    def base_url(self) -> str:
        """Configured API base URL."""
        return self._base_url

    def time(self) -> int:
        """GET /api/v3/time → server time in milliseconds."""
        data = self._request("GET", "/v3/time")
        return int(data["serverTime"])

    def exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        """GET /api/v3/exchangeInfo.

        Returns raw JSON dict (complex nested structure).
        """
        params: dict[str, Any] = {}
        if symbol is not None:
            params["symbol"] = symbol
        return self._request("GET", "/v3/exchangeInfo", params=params)

    def klines(
        self,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[list[Any]]:
        """GET /api/v3/klines → raw kline arrays."""
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return self._request("GET", "/v3/klines", params=params)

    # ── Signed endpoints ──────────────────────────────────────

    def account(self) -> list[AccountBalance]:
        """GET /api/v3/account → non-zero balances."""
        data = self._request("GET", "/v3/account", signed=True)
        return [
            AccountBalance(
                asset=b["asset"],
                free=float(b["free"]),
                locked=float(b["locked"]),
            )
            for b in data["balances"]
            if float(b["free"]) > 0 or float(b["locked"]) > 0
        ]

    def open_orders(self, symbol: str | None = None) -> list[OrderResponse]:
        """GET /api/v3/openOrders."""
        params: dict[str, Any] = {}
        if symbol is not None:
            params["symbol"] = symbol
        data = self._request("GET", "/v3/openOrders", params=params, signed=True)
        return [self._parse_order(o) for o in data]

    def cancel_all_orders(self, symbol: str) -> list[OrderResponse]:
        """DELETE /api/v3/openOrders — cancel all open orders for *symbol*."""
        try:
            data = self._request("DELETE", "/v3/openOrders", params={"symbol": symbol}, signed=True)
        except BinanceAPIError as exc:
            if exc.code == -2011:  # "Unknown order" = no open orders
                return []
            raise
        return [self._parse_order(o) for o in data]

    def place_order(
        self,
        symbol: str,
        side: str,
        type: str,
        *,
        quantity: float | str | None = None,
        quote_order_qty: float | None = None,
        price: float | None = None,
        time_in_force: str | None = None,
        new_client_order_id: str | None = None,
        new_order_resp_type: str = "FULL",
    ) -> OrderResponse:
        """POST /api/v3/order."""
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "newOrderRespType": new_order_resp_type,
        }
        if quantity is not None:
            if isinstance(quantity, str):
                params["quantity"] = quantity
            else:
                params["quantity"] = f"{quantity:.8f}"
        if quote_order_qty is not None:
            params["quoteOrderQty"] = f"{quote_order_qty:.2f}"
        if price is not None:
            params["price"] = f"{price:.8f}"
        if time_in_force is not None:
            params["timeInForce"] = time_in_force
        if new_client_order_id is not None:
            params["newClientOrderId"] = new_client_order_id
        return self._parse_order(
            self._request("POST", "/v3/order", params=params, signed=True),
        )

    def get_order(
        self,
        symbol: str,
        order_id: int | None = None,
        orig_client_order_id: str | None = None,
    ) -> OrderResponse:
        """GET /api/v3/order.  Provide *order_id* or *orig_client_order_id*."""
        params: dict[str, Any] = {"symbol": symbol}
        if order_id is not None:
            params["orderId"] = order_id
        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id
        return self._parse_order(
            self._request("GET", "/v3/order", params=params, signed=True),
        )

    def my_trades(
        self,
        symbol: str,
        order_id: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 500,
    ) -> list[TradeResponse]:
        """GET /api/v3/myTrades."""
        params: dict[str, Any] = {"symbol": symbol, "limit": limit}
        if order_id is not None:
            params["orderId"] = order_id
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        data = self._request("GET", "/v3/myTrades", params=params, signed=True)
        return [
            TradeResponse(
                id=t["id"],
                order_id=t["orderId"],
                symbol=t["symbol"],
                price=float(t["price"]),
                qty=float(t["qty"]),
                commission=float(t["commission"]),
                commission_asset=t["commissionAsset"],
                time=t["time"],
                is_buyer=t["isBuyer"],
                is_maker=t["isMaker"],
            )
            for t in data
        ]

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _parse_order(data: dict[str, Any]) -> OrderResponse:
        return OrderResponse(
            symbol=data["symbol"],
            order_id=data["orderId"],
            client_order_id=data["clientOrderId"],
            price=float(data.get("price", 0)),
            orig_qty=float(data["origQty"]),
            executed_qty=float(data["executedQty"]),
            status=data["status"],
            side=data["side"],
            type=data["type"],
            time_in_force=data.get("timeInForce", ""),
            transact_time=data.get("transactTime"),
        )
