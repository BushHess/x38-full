"""BarClock — H4 bar timing layer for live trading.

Polls Binance klines and detects new closed H4 bars.  Returns a
:class:`BarEvent` containing the **signal_bar** (last closed H4) and the
**fill_bar** open price (current bar whose open is fixed).

Ensures each signal_bar is processed exactly once — even across restarts —
by persisting ``last_processed_signal_close_ms`` in a SQLite ``kv`` table.
"""

from __future__ import annotations

import csv
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from v10.core.formatting import ms_to_iso
from v10.core.types import Bar
from v10.exchange.rest_client import BinanceSpotClient

_log = logging.getLogger(__name__)

_KV_KEY = "last_processed_signal_close_ms"

_KV_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_CSV_FIELDS = [
    "signal_close_iso",
    "fill_open_iso",
    "signal_close_ms",
    "fill_open_ms",
    "signal_open",
    "signal_high",
    "signal_low",
    "signal_close",
    "fill_open_price",
]


# ---------------------------------------------------------------------------
# BarEvent
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BarEvent:
    """A new H4 bar-close event ready for strategy evaluation."""

    signal_bar: Bar         # last CLOSED H4 bar (evaluate strategy here)
    fill_bar_open: float    # current bar open price (fill target)
    fill_bar_open_time: int # current bar open_time (ms)


# ---------------------------------------------------------------------------
# BarClock
# ---------------------------------------------------------------------------

class BarClock:
    """Polls H4 klines and emits :class:`BarEvent` on new bar closes.

    Parameters
    ----------
    client : BinanceSpotClient
        REST client for kline + server-time queries.
    db_path : str
        SQLite database path (can share with OrderManager).
    symbol : str
        Trading pair.
    interval : str
        Kline interval (default ``"4h"``).
    safety_buffer_ms : int
        Milliseconds after ``close_time`` before a bar is deemed closed.
    csv_path : str | Path | None
        Path for ``live_bar_events.csv``.  ``None`` disables CSV logging.
    """

    def __init__(
        self,
        client: BinanceSpotClient,
        db_path: str,
        symbol: str = "BTCUSDT",
        interval: str = "4h",
        *,
        safety_buffer_ms: int = 5000,
        csv_path: str | Path | None = None,
    ) -> None:
        self._client = client
        self._symbol = symbol
        self._interval = interval
        self._safety_buffer_ms = safety_buffer_ms
        self._csv_path = Path(csv_path) if csv_path else None

        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_KV_SCHEMA)
        self._conn.commit()

        self._last_processed_ms = self._get_kv_int(_KV_KEY)

        # Ensure CSV has header
        if self._csv_path is not None:
            self._csv_path.parent.mkdir(parents=True, exist_ok=True)
            if not self._csv_path.exists() or self._csv_path.stat().st_size == 0:
                with open(self._csv_path, "w", newline="") as f:
                    csv.writer(f).writerow(_CSV_FIELDS)

    # ── Public API ────────────────────────────────────────────

    def poll(self) -> BarEvent | None:
        """Check for a new closed H4 bar.

        Returns a :class:`BarEvent` if a new signal bar is available,
        or ``None`` if no new bar or the bar is not yet complete.
        """
        raw = self._client.klines(self._symbol, self._interval, limit=3)
        if len(raw) < 2:
            _log.debug("Not enough klines returned (%d)", len(raw))
            return None

        signal_raw = raw[-2]
        fill_raw = raw[-1]

        signal_bar = _parse_bar(signal_raw, self._interval)

        # Completeness: server time must exceed signal_bar.close_time + buffer
        server_time = self._client.time()
        if server_time <= signal_bar.close_time + self._safety_buffer_ms:
            _log.debug(
                "Signal bar not yet complete: server=%d, close+buf=%d",
                server_time, signal_bar.close_time + self._safety_buffer_ms,
            )
            return None

        # Dedup: skip if already processed
        if (
            self._last_processed_ms is not None
            and signal_bar.close_time <= self._last_processed_ms
        ):
            _log.debug(
                "Signal bar %d already processed (last=%d)",
                signal_bar.close_time, self._last_processed_ms,
            )
            return None

        fill_open = float(fill_raw[1])
        fill_open_time = int(fill_raw[0])

        event = BarEvent(
            signal_bar=signal_bar,
            fill_bar_open=fill_open,
            fill_bar_open_time=fill_open_time,
        )

        # Persist
        self._last_processed_ms = signal_bar.close_time
        self._set_kv(_KV_KEY, str(signal_bar.close_time))
        self._conn.commit()

        # CSV
        self._append_csv(event)

        _log.info(
            "BarEvent: signal_close=%s fill_open=%s price=%.2f→%.2f",
            ms_to_iso(signal_bar.close_time),
            ms_to_iso(fill_open_time),
            signal_bar.close,
            fill_open,
        )
        return event

    def last_processed_ms(self) -> int | None:
        """Return the close_time of the last processed signal bar."""
        return self._last_processed_ms

    def close(self) -> None:
        self._conn.close()

    # ── Private helpers ───────────────────────────────────────

    def _append_csv(self, event: BarEvent) -> None:
        if self._csv_path is None:
            return
        with open(self._csv_path, "a", newline="") as f:
            csv.writer(f).writerow([
                ms_to_iso(event.signal_bar.close_time),
                ms_to_iso(event.fill_bar_open_time),
                event.signal_bar.close_time,
                event.fill_bar_open_time,
                f"{event.signal_bar.open:.2f}",
                f"{event.signal_bar.high:.2f}",
                f"{event.signal_bar.low:.2f}",
                f"{event.signal_bar.close:.2f}",
                f"{event.fill_bar_open:.2f}",
            ])

    def _get_kv_int(self, key: str) -> int | None:
        row = self._conn.execute(
            "SELECT value FROM kv WHERE key = ?", (key,),
        ).fetchone()
        return int(row[0]) if row else None

    def _set_kv(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
            (key, value),
        )


# ---------------------------------------------------------------------------
# Kline parser
# ---------------------------------------------------------------------------

def _parse_bar(raw: list[Any], interval: str) -> Bar:
    """Parse a single raw Binance kline array into a Bar."""
    return Bar(
        open_time=int(raw[0]),
        open=float(raw[1]),
        high=float(raw[2]),
        low=float(raw[3]),
        close=float(raw[4]),
        volume=float(raw[5]),
        close_time=int(raw[6]),
        taker_buy_base_vol=float(raw[9]),
        interval=interval,
    )
