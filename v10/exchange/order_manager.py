"""OrderManager — crash-safe order lifecycle with SQLite persistence.

Write-ahead pattern:
  1. INSERT order intent into SQLite (status=PENDING)
  2. Send to Binance  (status→SENT)
  3. Poll until terminal  (status→FILLED/CANCELED/…)
  4. Fetch fills from myTrades

On restart, ``reconcile()`` scans non-terminal rows and resolves them
against exchange state — no duplicate sends, no lost fills.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from v10.exchange.rest_client import BinanceAPIError
from v10.exchange.rest_client import BinanceSpotClient

_log = logging.getLogger(__name__)

_TERMINAL = frozenset({"FILLED", "CANCELED", "REJECTED", "EXPIRED"})


def _is_duplicate_order_error(exc: BinanceAPIError) -> bool:
    """Check if a BinanceAPIError indicates a duplicate clientOrderId."""
    return "duplicate" in exc.msg.lower()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    client_order_id   TEXT PRIMARY KEY,
    symbol            TEXT NOT NULL,
    side              TEXT NOT NULL,
    type              TEXT NOT NULL,
    quantity          REAL NOT NULL,
    price             REAL,
    reason            TEXT NOT NULL DEFAULT '',
    status            TEXT NOT NULL DEFAULT 'PENDING',
    exchange_order_id INTEGER,
    created_at_ms     INTEGER NOT NULL,
    updated_at_ms     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    trade_id          INTEGER PRIMARY KEY,
    client_order_id   TEXT NOT NULL REFERENCES orders(client_order_id),
    symbol            TEXT NOT NULL,
    price             REAL NOT NULL,
    qty               REAL NOT NULL,
    commission        REAL NOT NULL,
    commission_asset  TEXT NOT NULL,
    time_ms           INTEGER NOT NULL,
    is_buyer          INTEGER NOT NULL,
    is_maker          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Deterministic client-order-id
# ---------------------------------------------------------------------------


def make_client_order_id(
    symbol: str,
    strategy_name: str,
    signal_close_ms: int,
    side: str,
    reason: str,
) -> str:
    """Deterministic order id from signal context.  20 hex chars (≤ 36 Binance limit)."""
    payload = f"{symbol}|{strategy_name}|{signal_close_ms}|{side}|{reason}"
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


# ---------------------------------------------------------------------------
# Crash-point simulation
# ---------------------------------------------------------------------------


class CrashPoint(str, Enum):
    BEFORE_PERSIST = "before_persist"  # before DB insert
    AFTER_DB = "after_db"  # after DB insert, before place_order
    AFTER_SEND = "after_send"  # after place_order, before polling
    AFTER_PARTIAL = "after_partial"  # after partial fill detected


class CrashSimulation(Exception):
    """Raised at a configured crash point for deterministic testing."""


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class OrderRecord:
    client_order_id: str
    symbol: str
    side: str
    type: str
    quantity: float
    price: float | None
    reason: str
    status: str
    exchange_order_id: int | None
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True, slots=True)
class FillRecord:
    trade_id: int
    client_order_id: str
    symbol: str
    price: float
    qty: float
    commission: float
    commission_asset: str
    time_ms: int
    is_buyer: bool
    is_maker: bool


# ---------------------------------------------------------------------------
# OrderManager
# ---------------------------------------------------------------------------


class OrderManager:
    """Crash-safe order lifecycle manager backed by SQLite.

    Parameters
    ----------
    client : BinanceSpotClient
        Signed REST client.
    db_path : str
        SQLite database path (use ``":memory:"`` for tests).
    symbol : str
        Trading pair (e.g. ``"BTCUSDT"``).
    crash_point : CrashPoint | None
        If set, raises :class:`CrashSimulation` at that point.
    poll_interval : float
        Seconds between order-status polls.
    max_polls : int
        Maximum poll attempts before giving up.
    """

    def __init__(
        self,
        client: BinanceSpotClient,
        db_path: str,
        symbol: str = "BTCUSDT",
        *,
        crash_point: CrashPoint | None = None,
        poll_interval: float = 1.0,
        max_polls: int = 30,
    ) -> None:
        self._client = client
        self._symbol = symbol
        self._crash_point = crash_point
        self._poll_interval = poll_interval
        self._max_polls = max_polls

        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── Order lifecycle ───────────────────────────────────────

    def submit_order(
        self,
        client_order_id: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        reason: str = "",
    ) -> OrderRecord:
        """Submit an order with write-ahead idempotency.

        If *client_order_id* already exists in the DB with a terminal
        status, the existing record is returned immediately (no resend).
        If the exchange reports a duplicate *client_order_id*, the order
        is reconciled from exchange state.
        """
        now_ms = _now_ms()

        # ── Crash point: before_persist ──
        if self._crash_point is CrashPoint.BEFORE_PERSIST:
            raise CrashSimulation("before_persist")

        # 1) Write intent — INSERT OR IGNORE makes this idempotent
        self._conn.execute(
            """INSERT OR IGNORE INTO orders
               (client_order_id, symbol, side, type, quantity, price, reason,
                status, created_at_ms, updated_at_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)""",
            (client_order_id, self._symbol, side, order_type, quantity, price, reason, now_ms, now_ms),
        )
        self._conn.commit()

        # 2) Check current state (may already be terminal from a prior run)
        rec = self.get_order(client_order_id)
        assert rec is not None
        if rec.status in _TERMINAL:
            _log.info("Order %s already %s, skipping", client_order_id, rec.status)
            return rec

        # ── Crash point: after_db ──
        if self._crash_point is CrashPoint.AFTER_DB:
            raise CrashSimulation("after_db")

        # 3) Send to exchange (only if still PENDING)
        if rec.status == "PENDING":
            try:
                resp = self._client.place_order(
                    symbol=self._symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    price=price,
                    new_client_order_id=client_order_id,
                    time_in_force="GTC" if order_type == "LIMIT" else None,
                )
            except BinanceAPIError as exc:
                if _is_duplicate_order_error(exc):
                    _log.warning(
                        "Duplicate clientOrderId %s on exchange, reconciling",
                        client_order_id,
                    )
                    return self._reconcile_duplicate(client_order_id)
                raise

            self._update_order(client_order_id, resp.status, resp.order_id)

            # ── Crash point: after_send ──
            if self._crash_point is CrashPoint.AFTER_SEND:
                raise CrashSimulation("after_send")

            # If already terminal (e.g. MARKET fills immediately)
            if resp.status in _TERMINAL:
                self._fetch_and_store_fills(client_order_id, resp.order_id)
                return self.get_order(client_order_id)  # type: ignore[return-value]

        # 4) Poll until terminal
        return self._poll_until_terminal(client_order_id)

    def _poll_until_terminal(self, client_order_id: str) -> OrderRecord:
        """Poll exchange until order reaches a terminal status."""
        rec = self.get_order(client_order_id)
        assert rec is not None

        for i in range(self._max_polls):
            try:
                resp = self._client.get_order(
                    self._symbol,
                    orig_client_order_id=client_order_id,
                )
            except BinanceAPIError:
                _log.warning("get_order failed for %s, retrying", client_order_id)
                time.sleep(self._poll_interval)
                continue

            self._update_order(client_order_id, resp.status, resp.order_id)

            if resp.status in _TERMINAL:
                self._fetch_and_store_fills(client_order_id, resp.order_id)
                return self.get_order(client_order_id)  # type: ignore[return-value]

            if resp.status == "PARTIALLY_FILLED":
                # ── Crash point: after_partial ──
                if self._crash_point is CrashPoint.AFTER_PARTIAL:
                    raise CrashSimulation("after_partial")

            time.sleep(self._poll_interval)

        # Exhausted polls — return current state
        _log.warning("Max polls (%d) exhausted for %s", self._max_polls, client_order_id)
        return self.get_order(client_order_id)  # type: ignore[return-value]

    def _reconcile_duplicate(self, client_order_id: str) -> OrderRecord:
        """Reconcile after exchange reports duplicate clientOrderId.

        Fetches the existing order from exchange, updates local DB, and
        polls until terminal if still open.
        """
        resp = self._client.get_order(
            self._symbol, orig_client_order_id=client_order_id,
        )
        self._update_order(client_order_id, resp.status, resp.order_id)
        if resp.status in _TERMINAL:
            self._fetch_and_store_fills(client_order_id, resp.order_id)
            return self.get_order(client_order_id)  # type: ignore[return-value]
        return self._poll_until_terminal(client_order_id)

    def _fetch_and_store_fills(
        self,
        client_order_id: str,
        exchange_order_id: int,
    ) -> None:
        """Fetch trades from exchange and store in fills table."""
        trades = self._client.my_trades(self._symbol, order_id=exchange_order_id)
        max_id = self._get_kv_int("last_trade_id") or 0
        for t in trades:
            self._conn.execute(
                """INSERT OR IGNORE INTO fills
                   (trade_id, client_order_id, symbol, price, qty,
                    commission, commission_asset, time_ms, is_buyer, is_maker)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    t.id,
                    client_order_id,
                    t.symbol,
                    t.price,
                    t.qty,
                    t.commission,
                    t.commission_asset,
                    t.time,
                    int(t.is_buyer),
                    int(t.is_maker),
                ),
            )
            if t.id > max_id:
                max_id = t.id
        self._set_kv("last_trade_id", str(max_id))
        self._conn.commit()

    # ── Reconciliation ────────────────────────────────────────

    def reconcile(self) -> list[OrderRecord]:
        """Reconcile all non-terminal orders against exchange state.

        Call on startup before processing new signals. Returns the
        list of orders that were updated.
        """
        updated: list[OrderRecord] = []

        rows = self._conn.execute(
            "SELECT client_order_id, status, exchange_order_id FROM orders "
            "WHERE status NOT IN ('FILLED','CANCELED','REJECTED','EXPIRED')",
        ).fetchall()

        for coid, status, exch_id in rows:
            rec = self._reconcile_one(coid, status, exch_id)
            if rec is not None:
                updated.append(rec)

        # Catch any fills we missed (incremental myTrades scan)
        self._scan_recent_trades()

        return updated

    def _reconcile_one(
        self,
        coid: str,
        status: str,
        exch_id: int | None,
    ) -> OrderRecord | None:
        """Reconcile a single non-terminal order."""
        try:
            resp = self._client.get_order(
                self._symbol,
                orig_client_order_id=coid,
            )
        except BinanceAPIError as exc:
            if exc.code == -2013:  # "Order does not exist"
                if status == "PENDING":
                    # Never reached exchange — mark expired
                    self._update_order(coid, "EXPIRED", exch_id)
                    _log.info("Order %s never reached exchange, marked EXPIRED", coid)
                    return self.get_order(coid)
                _log.warning("Order %s not found on exchange (status=%s)", coid, status)
                return None
            raise

        self._update_order(coid, resp.status, resp.order_id)
        if resp.status in _TERMINAL:
            self._fetch_and_store_fills(coid, resp.order_id)
        return self.get_order(coid)

    def _scan_recent_trades(self) -> None:
        """Fetch myTrades since last_trade_id to catch missed fills."""
        last_id = self._get_kv_int("last_trade_id")
        trades = self._client.my_trades(self._symbol)

        max_id = last_id or 0
        for t in trades:
            if last_id is not None and t.id <= last_id:
                continue
            # Try to match to a known order
            coid = self._find_client_order_id(t.order_id)
            if coid is None:
                continue
            self._conn.execute(
                """INSERT OR IGNORE INTO fills
                   (trade_id, client_order_id, symbol, price, qty,
                    commission, commission_asset, time_ms, is_buyer, is_maker)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    t.id,
                    coid,
                    t.symbol,
                    t.price,
                    t.qty,
                    t.commission,
                    t.commission_asset,
                    t.time,
                    int(t.is_buyer),
                    int(t.is_maker),
                ),
            )
            if t.id > max_id:
                max_id = t.id

        if max_id > (last_id or 0):
            self._set_kv("last_trade_id", str(max_id))
        self._conn.commit()

    # ── Queries ───────────────────────────────────────────────

    def get_order(self, client_order_id: str) -> OrderRecord | None:
        row = self._conn.execute(
            "SELECT * FROM orders WHERE client_order_id = ?",
            (client_order_id,),
        ).fetchone()
        return _row_to_order(row) if row else None

    def get_fills(self, client_order_id: str) -> list[FillRecord]:
        rows = self._conn.execute(
            "SELECT * FROM fills WHERE client_order_id = ? ORDER BY trade_id",
            (client_order_id,),
        ).fetchall()
        return [_row_to_fill(r) for r in rows]

    def get_last_trade_id(self) -> int | None:
        return self._get_kv_int("last_trade_id")

    def close(self) -> None:
        self._conn.close()

    # ── Private helpers ───────────────────────────────────────

    def _update_order(
        self,
        coid: str,
        status: str,
        exchange_order_id: int | None,
    ) -> None:
        self._conn.execute(
            "UPDATE orders SET status = ?, exchange_order_id = ?, updated_at_ms = ? WHERE client_order_id = ?",
            (status, exchange_order_id, _now_ms(), coid),
        )
        self._conn.commit()

    def _find_client_order_id(self, exchange_order_id: int) -> str | None:
        row = self._conn.execute(
            "SELECT client_order_id FROM orders WHERE exchange_order_id = ?",
            (exchange_order_id,),
        ).fetchone()
        return row[0] if row else None

    def _get_kv_int(self, key: str) -> int | None:
        row = self._conn.execute(
            "SELECT value FROM kv WHERE key = ?",
            (key,),
        ).fetchone()
        return int(row[0]) if row else None

    def _set_kv(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
            (key, value),
        )


# ---------------------------------------------------------------------------
# Row mappers
# ---------------------------------------------------------------------------


def _row_to_order(row: tuple[Any, ...]) -> OrderRecord:
    return OrderRecord(
        client_order_id=row[0],
        symbol=row[1],
        side=row[2],
        type=row[3],
        quantity=row[4],
        price=row[5],
        reason=row[6],
        status=row[7],
        exchange_order_id=row[8],
        created_at_ms=row[9],
        updated_at_ms=row[10],
    )


def _row_to_fill(row: tuple[Any, ...]) -> FillRecord:
    return FillRecord(
        trade_id=row[0],
        client_order_id=row[1],
        symbol=row[2],
        price=row[3],
        qty=row[4],
        commission=row[5],
        commission_asset=row[6],
        time_ms=row[7],
        is_buyer=bool(row[8]),
        is_maker=bool(row[9]),
    )


def _now_ms() -> int:
    return int(time.time() * 1000)
