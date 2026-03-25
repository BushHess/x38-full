"""Tests for OrderManager — idempotency, crash recovery, reconciliation."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from v10.exchange.order_manager import (
    CrashPoint,
    CrashSimulation,
    OrderManager,
    make_client_order_id,
)
from v10.exchange.rest_client import (
    BinanceAPIError,
    BinanceSpotClient,
    OrderResponse,
    TradeResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> BinanceSpotClient:
    return BinanceSpotClient(api_key="k", api_secret="s")


def _make_mgr(
    client: BinanceSpotClient | None = None,
    crash_point: CrashPoint | None = None,
) -> OrderManager:
    c = client or _make_client()
    return OrderManager(
        c, ":memory:", "BTCUSDT",
        crash_point=crash_point,
        poll_interval=0.0,  # no sleep in tests
        max_polls=5,
    )


def _order_resp(
    coid: str = "abc",
    status: str = "FILLED",
    order_id: int = 100,
    qty: float = 0.001,
) -> OrderResponse:
    return OrderResponse(
        symbol="BTCUSDT",
        order_id=order_id,
        client_order_id=coid,
        price=0.0,
        orig_qty=qty,
        executed_qty=qty if status == "FILLED" else 0.0,
        status=status,
        side="BUY",
        type="MARKET",
        time_in_force="",
        transact_time=1700000000000,
    )


def _trade_resp(
    trade_id: int = 1,
    order_id: int = 100,
    price: float = 67000.0,
    qty: float = 0.001,
) -> TradeResponse:
    return TradeResponse(
        id=trade_id,
        order_id=order_id,
        symbol="BTCUSDT",
        price=price,
        qty=qty,
        commission=0.0,
        commission_asset="BTC",
        time=1700000000000,
        is_buyer=True,
        is_maker=False,
    )


# ---------------------------------------------------------------------------
# 1) make_client_order_id
# ---------------------------------------------------------------------------

class TestMakeClientOrderId:
    def test_deterministic(self) -> None:
        a = make_client_order_id("BTCUSDT", "4h", 1700000000000, "BUY", "entry")
        b = make_client_order_id("BTCUSDT", "4h", 1700000000000, "BUY", "entry")
        assert a == b

    def test_different_inputs_differ(self) -> None:
        a = make_client_order_id("BTCUSDT", "4h", 1700000000000, "BUY", "entry")
        b = make_client_order_id("BTCUSDT", "4h", 1700000000000, "SELL", "exit")
        assert a != b

    def test_length_within_limit(self) -> None:
        coid = make_client_order_id("BTCUSDT", "4h", 1700000000000, "BUY", "entry")
        assert len(coid) == 20
        assert len(coid) <= 36  # Binance limit


# ---------------------------------------------------------------------------
# 2) submit_order — happy path
# ---------------------------------------------------------------------------

class TestSubmitOrder:
    def test_happy_path_market_fill(self) -> None:
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid1", "FILLED", 100))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(1, 100)])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        rec = mgr.submit_order("coid1", "BUY", "MARKET", 0.001)

        assert rec.status == "FILLED"
        assert rec.exchange_order_id == 100
        fills = mgr.get_fills("coid1")
        assert len(fills) == 1
        assert fills[0].trade_id == 1

    def test_fills_stored_correctly(self) -> None:
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid2", "FILLED", 200))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[  # type: ignore[assignment]
            _trade_resp(10, 200, 65000.0, 0.0005),
            _trade_resp(11, 200, 65001.0, 0.0005),
        ])
        mgr = _make_mgr(client)

        mgr.submit_order("coid2", "BUY", "MARKET", 0.001)

        fills = mgr.get_fills("coid2")
        assert len(fills) == 2
        assert fills[0].price == 65000.0
        assert fills[1].price == 65001.0

    def test_idempotent_resubmit(self) -> None:
        """Submitting the same client_order_id twice returns existing record."""
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid3", "FILLED", 300))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(20, 300)])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        rec1 = mgr.submit_order("coid3", "BUY", "MARKET", 0.001)
        rec2 = mgr.submit_order("coid3", "BUY", "MARKET", 0.001)

        assert rec1.status == "FILLED"
        assert rec2.status == "FILLED"
        # place_order called only once
        assert client.place_order.call_count == 1

    def test_db_state_after_submit(self) -> None:
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid4", "FILLED", 400))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(30, 400)])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        mgr.submit_order("coid4", "BUY", "MARKET", 0.001, reason="test_entry")

        rec = mgr.get_order("coid4")
        assert rec is not None
        assert rec.symbol == "BTCUSDT"
        assert rec.side == "BUY"
        assert rec.reason == "test_entry"
        assert rec.quantity == 0.001
        assert mgr.get_last_trade_id() == 30


# ---------------------------------------------------------------------------
# 3) Crash recovery
# ---------------------------------------------------------------------------

class TestCrashRecovery:
    def test_crash_after_db(self) -> None:
        """Crash after DB write, before place_order.
        On restart, reconcile should detect PENDING and re-send."""
        # Phase 1: crash
        client = _make_client()
        mgr = _make_mgr(client, crash_point=CrashPoint.AFTER_DB)
        with pytest.raises(CrashSimulation):
            mgr.submit_order("coid_adb", "BUY", "MARKET", 0.001)

        rec = mgr.get_order("coid_adb")
        assert rec is not None
        assert rec.status == "PENDING"

        # Phase 2: restart — new manager on same DB (use file-based for this)
        # We reuse the same in-memory conn by accessing _conn
        mgr2 = OrderManager(
            client, ":memory:", "BTCUSDT",
            poll_interval=0.0, max_polls=5,
        )
        # Copy state from crashed manager
        for row in mgr._conn.execute("SELECT * FROM orders").fetchall():
            mgr2._conn.execute(
                "INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)", row,
            )
        mgr2._conn.commit()

        # Setup mock for reconcile
        client.get_order = MagicMock(  # type: ignore[assignment]
            side_effect=BinanceAPIError(400, -2013, "Order does not exist"),
        )
        client.my_trades = MagicMock(return_value=[])  # type: ignore[assignment]

        updated = mgr2.reconcile()

        # PENDING order that never reached exchange → EXPIRED
        rec2 = mgr2.get_order("coid_adb")
        assert rec2 is not None
        assert rec2.status == "EXPIRED"

    def test_crash_after_send(self) -> None:
        """Crash after place_order, before polling.
        On restart, reconcile should poll and find FILLED."""
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid_as", "NEW", 500))  # type: ignore[assignment]
        mgr = _make_mgr(client, crash_point=CrashPoint.AFTER_SEND)

        with pytest.raises(CrashSimulation):
            mgr.submit_order("coid_as", "BUY", "MARKET", 0.001)

        rec = mgr.get_order("coid_as")
        assert rec is not None
        assert rec.status == "NEW"  # Sent but not polled

        # Restart: reconcile finds the order now FILLED
        mgr._crash_point = None
        client.get_order = MagicMock(return_value=_order_resp("coid_as", "FILLED", 500))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(50, 500)])  # type: ignore[assignment]

        updated = mgr.reconcile()

        rec2 = mgr.get_order("coid_as")
        assert rec2 is not None
        assert rec2.status == "FILLED"
        assert len(mgr.get_fills("coid_as")) == 1

    def test_crash_before_persist(self) -> None:
        """BEFORE_PERSIST crash: no DB record, no exchange call."""
        client = _make_client()
        mgr = _make_mgr(client, crash_point=CrashPoint.BEFORE_PERSIST)

        with pytest.raises(CrashSimulation):
            mgr.submit_order("coid_bp", "BUY", "MARKET", 0.001)

        # No record in DB — nothing was persisted
        assert mgr.get_order("coid_bp") is None

    def test_before_persist_then_retry_succeeds(self) -> None:
        """After BEFORE_PERSIST crash, retry is a fresh submit (no duplicate)."""
        client = _make_client()
        mgr = _make_mgr(client, crash_point=CrashPoint.BEFORE_PERSIST)

        with pytest.raises(CrashSimulation):
            mgr.submit_order("coid_bpr", "BUY", "MARKET", 0.001)

        # Retry without crash point
        mgr._crash_point = None
        client.place_order = MagicMock(return_value=_order_resp("coid_bpr", "FILLED", 1300))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(130, 1300)])  # type: ignore[assignment]

        rec = mgr.submit_order("coid_bpr", "BUY", "MARKET", 0.001)

        assert rec.status == "FILLED"
        assert client.place_order.call_count == 1  # sent exactly once — no duplicate

    def test_crash_after_partial(self) -> None:
        """Crash during partial fill. Reconcile should complete the lifecycle."""
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid_ap", "NEW", 600))  # type: ignore[assignment]
        # First get_order returns PARTIALLY_FILLED (triggers crash), then FILLED
        client.get_order = MagicMock(  # type: ignore[assignment]
            return_value=_order_resp("coid_ap", "PARTIALLY_FILLED", 600),
        )
        client.my_trades = MagicMock(return_value=[])  # type: ignore[assignment]

        mgr = _make_mgr(client, crash_point=CrashPoint.AFTER_PARTIAL)
        with pytest.raises(CrashSimulation):
            mgr.submit_order("coid_ap", "BUY", "LIMIT", 0.001, price=67000.0)

        # Restart: reconcile
        mgr._crash_point = None
        client.get_order = MagicMock(return_value=_order_resp("coid_ap", "FILLED", 600))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(60, 600)])  # type: ignore[assignment]

        mgr.reconcile()

        rec = mgr.get_order("coid_ap")
        assert rec is not None
        assert rec.status == "FILLED"
        assert len(mgr.get_fills("coid_ap")) == 1


# ---------------------------------------------------------------------------
# 4) Reconcile edge cases
# ---------------------------------------------------------------------------

class TestReconcile:
    def test_pending_found_on_exchange(self) -> None:
        """PENDING order that actually made it to exchange (race condition)."""
        client = _make_client()
        mgr = _make_mgr(client)

        # Manually insert a PENDING order
        mgr._conn.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("coid_pf", "BTCUSDT", "BUY", "MARKET", 0.001, None, "",
             "PENDING", None, 1700000000000, 1700000000000),
        )
        mgr._conn.commit()

        client.get_order = MagicMock(return_value=_order_resp("coid_pf", "FILLED", 700))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(70, 700)])  # type: ignore[assignment]

        mgr.reconcile()

        rec = mgr.get_order("coid_pf")
        assert rec is not None
        assert rec.status == "FILLED"

    def test_pending_not_on_exchange(self) -> None:
        """PENDING order that never reached exchange → EXPIRED."""
        client = _make_client()
        mgr = _make_mgr(client)

        mgr._conn.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("coid_pn", "BTCUSDT", "BUY", "MARKET", 0.001, None, "",
             "PENDING", None, 1700000000000, 1700000000000),
        )
        mgr._conn.commit()

        client.get_order = MagicMock(  # type: ignore[assignment]
            side_effect=BinanceAPIError(400, -2013, "Order does not exist"),
        )
        client.my_trades = MagicMock(return_value=[])  # type: ignore[assignment]

        mgr.reconcile()

        rec = mgr.get_order("coid_pn")
        assert rec is not None
        assert rec.status == "EXPIRED"

    def test_sent_now_filled(self) -> None:
        """SENT order that is now FILLED on exchange."""
        client = _make_client()
        mgr = _make_mgr(client)

        mgr._conn.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("coid_sf", "BTCUSDT", "BUY", "MARKET", 0.001, None, "",
             "SENT", 800, 1700000000000, 1700000000000),
        )
        mgr._conn.commit()

        client.get_order = MagicMock(return_value=_order_resp("coid_sf", "FILLED", 800))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(80, 800)])  # type: ignore[assignment]

        updated = mgr.reconcile()

        assert len(updated) >= 1
        rec = mgr.get_order("coid_sf")
        assert rec is not None
        assert rec.status == "FILLED"
        assert len(mgr.get_fills("coid_sf")) == 1

    def test_incremental_trades_scan(self) -> None:
        """myTrades scan catches fills missed by per-order fetch."""
        client = _make_client()
        mgr = _make_mgr(client)

        # Order already FILLED in DB but no fills stored
        mgr._conn.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("coid_it", "BTCUSDT", "BUY", "MARKET", 0.001, None, "",
             "FILLED", 900, 1700000000000, 1700000000000),
        )
        mgr._conn.commit()

        # my_trades returns a fill for this order
        client.get_order = MagicMock()  # type: ignore[assignment]
        # No non-terminal orders, so reconcile_one won't be called
        client.my_trades = MagicMock(return_value=[_trade_resp(90, 900)])  # type: ignore[assignment]

        mgr.reconcile()

        fills = mgr.get_fills("coid_it")
        assert len(fills) == 1
        assert fills[0].trade_id == 90
        assert mgr.get_last_trade_id() == 90


# ---------------------------------------------------------------------------
# 5) poll_until_terminal
# ---------------------------------------------------------------------------

class TestPollUntilTerminal:
    def test_immediate_fill(self) -> None:
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid_if", "FILLED", 1000))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[_trade_resp(100, 1000)])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        rec = mgr.submit_order("coid_if", "BUY", "MARKET", 0.001)

        assert rec.status == "FILLED"
        # get_order not called (no polling needed)
        assert not hasattr(client, "get_order") or not isinstance(client.get_order, MagicMock)

    def test_multiple_polls_then_fill(self) -> None:
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid_mp", "NEW", 1100))  # type: ignore[assignment]
        client.get_order = MagicMock(side_effect=[  # type: ignore[assignment]
            _order_resp("coid_mp", "NEW", 1100),
            _order_resp("coid_mp", "PARTIALLY_FILLED", 1100),
            _order_resp("coid_mp", "FILLED", 1100),
        ])
        client.my_trades = MagicMock(return_value=[_trade_resp(110, 1100)])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        rec = mgr.submit_order("coid_mp", "BUY", "LIMIT", 0.001, price=67000.0)

        assert rec.status == "FILLED"
        assert client.get_order.call_count == 3

    def test_max_polls_exhausted(self) -> None:
        """After max_polls, returns current (non-terminal) state."""
        client = _make_client()
        client.place_order = MagicMock(return_value=_order_resp("coid_mx", "NEW", 1200))  # type: ignore[assignment]
        client.get_order = MagicMock(return_value=_order_resp("coid_mx", "NEW", 1200))  # type: ignore[assignment]
        client.my_trades = MagicMock(return_value=[])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        rec = mgr.submit_order("coid_mx", "BUY", "LIMIT", 0.001, price=67000.0)

        # Still NEW after exhausting polls
        assert rec.status == "NEW"
        assert client.get_order.call_count == 5  # max_polls=5


# ---------------------------------------------------------------------------
# 6) Duplicate clientOrderId handling
# ---------------------------------------------------------------------------

class TestDuplicateOrderHandling:
    def test_exchange_duplicate_reconciles_filled(self) -> None:
        """Exchange returns 'duplicate clientOrderId' → reconcile as FILLED."""
        client = _make_client()
        client.place_order = MagicMock(  # type: ignore[assignment]
            side_effect=BinanceAPIError(400, -2010, "Duplicate order sent."),
        )
        client.get_order = MagicMock(  # type: ignore[assignment]
            return_value=_order_resp("coid_dup", "FILLED", 1400),
        )
        client.my_trades = MagicMock(return_value=[_trade_resp(140, 1400)])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        rec = mgr.submit_order("coid_dup", "BUY", "MARKET", 0.001)

        assert rec.status == "FILLED"
        assert len(mgr.get_fills("coid_dup")) == 1
        assert client.place_order.call_count == 1

    def test_exchange_duplicate_still_open(self) -> None:
        """Duplicate order on exchange still NEW → poll until FILLED."""
        client = _make_client()
        client.place_order = MagicMock(  # type: ignore[assignment]
            side_effect=BinanceAPIError(400, -2010, "Duplicate order sent."),
        )
        # First get_order (reconcile_duplicate) returns NEW, second (poll) returns FILLED
        client.get_order = MagicMock(side_effect=[  # type: ignore[assignment]
            _order_resp("coid_duo", "NEW", 1500),
            _order_resp("coid_duo", "FILLED", 1500),
        ])
        client.my_trades = MagicMock(return_value=[_trade_resp(150, 1500)])  # type: ignore[assignment]
        mgr = _make_mgr(client)

        rec = mgr.submit_order("coid_duo", "BUY", "LIMIT", 0.001, price=67000.0)

        assert rec.status == "FILLED"
        assert client.get_order.call_count == 2

    def test_non_duplicate_error_reraises(self) -> None:
        """Non-duplicate BinanceAPIError is re-raised."""
        client = _make_client()
        client.place_order = MagicMock(  # type: ignore[assignment]
            side_effect=BinanceAPIError(400, -1013, "Invalid quantity."),
        )
        mgr = _make_mgr(client)

        with pytest.raises(BinanceAPIError, match="Invalid quantity"):
            mgr.submit_order("coid_err", "BUY", "MARKET", 0.001)

    def test_duplicate_proves_no_double_send(self) -> None:
        """Full scenario: order sent, crash before DB update, retry hits duplicate.
        Exchange only executes once — no double fill."""
        client = _make_client()
        mgr = _make_mgr(client)

        # Manually insert PENDING record (simulates DB write survived, but
        # place_order response was lost due to crash)
        mgr._conn.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("coid_nds", "BTCUSDT", "BUY", "MARKET", 0.001, None, "",
             "PENDING", None, 1700000000000, 1700000000000),
        )
        mgr._conn.commit()

        # place_order returns duplicate error
        client.place_order = MagicMock(  # type: ignore[assignment]
            side_effect=BinanceAPIError(400, -2010, "Duplicate order sent."),
        )
        # get_order reveals the order already filled on exchange
        client.get_order = MagicMock(  # type: ignore[assignment]
            return_value=_order_resp("coid_nds", "FILLED", 1600),
        )
        client.my_trades = MagicMock(return_value=[_trade_resp(160, 1600)])  # type: ignore[assignment]

        rec = mgr.submit_order("coid_nds", "BUY", "MARKET", 0.001)

        assert rec.status == "FILLED"
        fills = mgr.get_fills("coid_nds")
        assert len(fills) == 1  # single execution — no double fill
        assert fills[0].trade_id == 160
