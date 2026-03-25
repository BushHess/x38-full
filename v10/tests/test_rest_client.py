"""Tests for BinanceSpotClient — signing, encoding, time sync, retry."""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from v10.exchange.rest_client import BinanceAPIError
from v10.exchange.rest_client import BinanceSpotClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(**kwargs: object) -> BinanceSpotClient:
    """Create client with test keys (no real network)."""
    return BinanceSpotClient(
        api_key=kwargs.pop("api_key", "test_key_abc123"),  # type: ignore[arg-type]
        api_secret=kwargs.pop("api_secret", "test_secret_xyz789"),  # type: ignore[arg-type]
        **kwargs,  # type: ignore[arg-type]
    )


def _ok_response(body: dict | list) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    return resp


def _err_response(status: int, code: int = -1, msg: str = "error") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {"code": code, "msg": msg}
    resp.text = msg
    resp.headers = {}
    return resp


# ---------------------------------------------------------------------------
# 1) Query-string signing stability
# ---------------------------------------------------------------------------

class TestSigning:
    """Verify HMAC-SHA256 signature is correct and deterministic."""

    def test_sign_known_vector(self) -> None:
        """Compare against hand-computed HMAC-SHA256."""
        secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
        query = (
            "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC"
            "&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"
        )
        expected = hmac.new(
            secret.encode(), query.encode(), hashlib.sha256,
        ).hexdigest()
        assert BinanceSpotClient._sign(query, secret) == expected

    def test_sign_deterministic(self) -> None:
        """Same input → same signature, always."""
        secret = "my_secret"
        query = "symbol=BTCUSDT&timestamp=1700000000000&recvWindow=5000"
        assert BinanceSpotClient._sign(query, secret) == BinanceSpotClient._sign(query, secret)

    def test_sign_different_secrets_differ(self) -> None:
        query = "symbol=BTCUSDT&timestamp=1700000000000"
        assert BinanceSpotClient._sign(query, "secret_a") != BinanceSpotClient._sign(query, "secret_b")

    def test_build_signed_params_includes_required_fields(self) -> None:
        client = _make_client()
        client._time_offset_ms = 0
        client._time_synced_at = time.monotonic()

        params = client._build_signed_params({"symbol": "BTCUSDT"})

        assert "timestamp" in params
        assert params["recvWindow"] == 5000
        assert isinstance(params["signature"], str)
        assert len(params["signature"]) == 64  # SHA-256 hex length

    def test_signature_excludes_itself(self) -> None:
        """Signature must be over the query string *without* the signature key."""
        client = _make_client(api_secret="known_secret")
        client._time_offset_ms = 0
        client._time_synced_at = time.monotonic()

        params = client._build_signed_params({"symbol": "ETHBTC", "side": "BUY"})

        verify_params = {k: v for k, v in params.items() if k != "signature"}
        expected_qs = urllib.parse.urlencode(verify_params, doseq=False)
        expected_sig = hmac.new(
            b"known_secret", expected_qs.encode(), hashlib.sha256,
        ).hexdigest()
        assert params["signature"] == expected_sig


# ---------------------------------------------------------------------------
# 2) Percent-encoding correctness
# ---------------------------------------------------------------------------

class TestPercentEncoding:
    """Verify that special characters are correctly URL-encoded."""

    def test_spaces_encoded(self) -> None:
        params = {"newClientOrderId": "my order 1"}
        qs = urllib.parse.urlencode(params, doseq=False)
        assert " " not in qs
        assert "my+order+1" in qs or "my%20order%201" in qs

    def test_ampersand_in_value(self) -> None:
        params = {"key": "a=b&c=d"}
        qs = urllib.parse.urlencode(params, doseq=False)
        parts = qs.split("&")
        # The '&' inside the value must be encoded, so only one top-level pair
        assert len(parts) == 1
        assert parts[0].startswith("key=")

    def test_float_precision_preserved(self) -> None:
        params = {"quantity": "0.00100000", "price": "50000.10000000"}
        qs = urllib.parse.urlencode(params, doseq=False)
        assert "0.00100000" in qs
        assert "50000.10000000" in qs

    def test_param_insertion_order(self) -> None:
        """urlencode preserves insertion order (Python 3.7+)."""
        params = {"symbol": "BTCUSDT", "side": "BUY", "timestamp": "1700000000000"}
        qs = urllib.parse.urlencode(params, doseq=False)
        assert qs == "symbol=BTCUSDT&side=BUY&timestamp=1700000000000"


# ---------------------------------------------------------------------------
# 3) Timestamp offset logic
# ---------------------------------------------------------------------------

class TestTimeSync:
    """Verify offset computation and TTL-based refresh."""

    def test_offset_computation(self) -> None:
        client = _make_client()
        server_time = 1_700_000_005_000

        client._request = MagicMock(return_value={"serverTime": server_time})  # type: ignore[assignment]
        with patch("v10.exchange.rest_client.time") as mock_time:
            mock_time.time.return_value = 1_700_000_000.0
            mock_time.monotonic.return_value = 100.0
            client._sync_time()

        # local_mid = 1700000000000; offset = 5000
        assert client._time_offset_ms == 5000

    def test_server_timestamp_applies_offset(self) -> None:
        client = _make_client()
        client._time_offset_ms = 3000
        client._time_synced_at = time.monotonic()

        with patch("v10.exchange.rest_client.time") as mock_time:
            mock_time.time.return_value = 1_700_000_000.0
            mock_time.monotonic.return_value = time.monotonic()
            ts = client._server_timestamp_ms()

        assert ts == 1_700_000_000_000 + 3000

    def test_stale_offset_triggers_resync(self) -> None:
        client = _make_client(time_sync_ttl=10.0)
        client._time_synced_at = time.monotonic() - 30.0
        client._time_offset_ms = 1000

        client._sync_time = MagicMock()  # type: ignore[assignment]
        client._server_timestamp_ms()
        client._sync_time.assert_called_once()

    def test_fresh_offset_skips_resync(self) -> None:
        client = _make_client(time_sync_ttl=60.0)
        client._time_synced_at = time.monotonic()
        client._time_offset_ms = 500

        client._sync_time = MagicMock()  # type: ignore[assignment]
        client._server_timestamp_ms()
        client._sync_time.assert_not_called()

    def test_first_call_triggers_sync(self) -> None:
        client = _make_client()
        assert client._time_synced_at == 0.0

        client._sync_time = MagicMock()  # type: ignore[assignment]
        client._server_timestamp_ms()
        client._sync_time.assert_called_once()


# ---------------------------------------------------------------------------
# 4) Retry logic
# ---------------------------------------------------------------------------

class TestRetry:
    """Verify exponential backoff on retryable status codes."""

    def test_429_retried(self) -> None:
        client = _make_client(max_retries=2, retry_base_delay=0.001)
        client._session.request = MagicMock(side_effect=[
            _err_response(429, msg="rate limited"),
            _err_response(429, msg="rate limited"),
            _ok_response({"serverTime": 123}),
        ])
        result = client._request("GET", "/v3/time")
        assert result == {"serverTime": 123}
        assert client._session.request.call_count == 3

    def test_5xx_retried(self) -> None:
        client = _make_client(max_retries=1, retry_base_delay=0.001)
        client._session.request = MagicMock(side_effect=[
            _err_response(502, msg="bad gateway"),
            _ok_response({"result": "ok"}),
        ])
        result = client._request("GET", "/v3/time")
        assert result == {"result": "ok"}
        assert client._session.request.call_count == 2

    def test_400_not_retried(self) -> None:
        client = _make_client(max_retries=3, retry_base_delay=0.001)
        client._session.request = MagicMock(return_value=_err_response(400, -1100, "bad param"))

        with pytest.raises(BinanceAPIError) as exc_info:
            client._request("GET", "/v3/order")
        assert exc_info.value.code == -1100
        assert client._session.request.call_count == 1

    def test_max_retries_exhausted_raises(self) -> None:
        client = _make_client(max_retries=2, retry_base_delay=0.001)
        client._session.request = MagicMock(return_value=_err_response(503, msg="unavailable"))

        with pytest.raises(BinanceAPIError):
            client._request("GET", "/v3/time")
        assert client._session.request.call_count == 3  # initial + 2 retries


# ---------------------------------------------------------------------------
# 5) Constructor / env-var loading
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_missing_keys_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="BINANCE_API_KEY"):
                BinanceSpotClient()

    def test_env_vars_loaded(self) -> None:
        with patch.dict("os.environ", {
            "BINANCE_API_KEY": "env_key",
            "BINANCE_API_SECRET": "env_secret",
        }):
            client = BinanceSpotClient()
            assert client._api_key == "env_key"
            assert client._api_secret == "env_secret"

    def test_explicit_keys_override_env(self) -> None:
        with patch.dict("os.environ", {
            "BINANCE_API_KEY": "env_key",
            "BINANCE_API_SECRET": "env_secret",
        }):
            client = BinanceSpotClient(api_key="explicit_key", api_secret="explicit_secret")
            assert client._api_key == "explicit_key"
            assert client._api_secret == "explicit_secret"

    def test_default_base_url_is_testnet(self) -> None:
        client = _make_client()
        assert "testnet.binance.vision" in client._base_url

    def test_base_url_property_returns_trimmed_url(self) -> None:
        client = _make_client(base_url="https://example.com/api/")
        assert client.base_url == "https://example.com/api"


class TestOrders:
    def test_place_order_allows_preformatted_quantity_string(self) -> None:
        client = _make_client()
        client._request = MagicMock(return_value={
            "symbol": "BTCUSDT",
            "orderId": 12345,
            "clientOrderId": "cid-1",
            "price": "0",
            "origQty": "0.12345000",
            "executedQty": "0.12345000",
            "status": "FILLED",
            "side": "SELL",
            "type": "MARKET",
            "timeInForce": "",
        })  # type: ignore[assignment]

        order = client.place_order(
            symbol="BTCUSDT",
            side="SELL",
            type="MARKET",
            quantity="0.12345000",
        )

        assert order.executed_qty == 0.12345
        called_params = client._request.call_args.kwargs["params"]
        assert called_params["quantity"] == "0.12345000"
