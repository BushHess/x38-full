"""Tests for BarClock — polling, dedup, persistence, CSV logging."""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from v10.exchange.bar_clock import BarClock, BarEvent
from v10.exchange.rest_client import BinanceSpotClient

# ---------------------------------------------------------------------------
# Constants — H4 bar boundaries (ms)
# ---------------------------------------------------------------------------

# Three consecutive H4 bars:
#   bar A: open 1700000000000 .. close 1700014399999
#   bar B: open 1700014400000 .. close 1700028799999  ← signal_bar
#   bar C: open 1700028800000 .. close 1700043199999  ← fill_bar (open)

H4_MS = 4 * 3600 * 1000  # 14_400_000

BAR_A_OPEN = 1_700_000_000_000
BAR_A_CLOSE = BAR_A_OPEN + H4_MS - 1  # 1700014399999

BAR_B_OPEN = BAR_A_OPEN + H4_MS       # 1700014400000
BAR_B_CLOSE = BAR_B_OPEN + H4_MS - 1  # 1700028799999

BAR_C_OPEN = BAR_B_OPEN + H4_MS       # 1700028800000
BAR_C_CLOSE = BAR_C_OPEN + H4_MS - 1  # 1700043199999

BAR_D_OPEN = BAR_C_OPEN + H4_MS
BAR_D_CLOSE = BAR_D_OPEN + H4_MS - 1


def _raw_kline(open_time: int, close_time: int, o: float, h: float, l: float, c: float) -> list:
    return [
        open_time, str(o), str(h), str(l), str(c),
        "100.0", close_time, "6500000", 500,
        "50.0", "3250000", "0",
    ]


THREE_KLINES = [
    _raw_kline(BAR_A_OPEN, BAR_A_CLOSE, 65000, 66000, 64500, 65500),
    _raw_kline(BAR_B_OPEN, BAR_B_CLOSE, 65500, 67000, 65000, 66800),  # signal
    _raw_kline(BAR_C_OPEN, BAR_C_CLOSE, 66900, 67200, 66700, 67100),  # fill
]

NEXT_THREE_KLINES = [
    _raw_kline(BAR_B_OPEN, BAR_B_CLOSE, 65500, 67000, 65000, 66800),
    _raw_kline(BAR_C_OPEN, BAR_C_CLOSE, 66900, 67200, 66700, 67100),  # new signal
    _raw_kline(BAR_D_OPEN, BAR_D_CLOSE, 67100, 67500, 66900, 67300),  # new fill
]

SERVER_AFTER_B = BAR_B_CLOSE + 6000  # > close + 5000 safety buffer
SERVER_BEFORE_B = BAR_B_CLOSE + 3000  # < close + 5000 (incomplete)
SERVER_AFTER_C = BAR_C_CLOSE + 6000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> BinanceSpotClient:
    return BinanceSpotClient(api_key="k", api_secret="s")


def _make_clock(
    client: BinanceSpotClient,
    tmp_path: Path,
    csv: bool = True,
) -> BarClock:
    csv_path = tmp_path / "live_bar_events.csv" if csv else None
    return BarClock(
        client,
        str(tmp_path / "clock.db"),
        symbol="BTCUSDT",
        interval="4h",
        safety_buffer_ms=5000,
        csv_path=csv_path,
    )


# ---------------------------------------------------------------------------
# 1) BarEvent parsing
# ---------------------------------------------------------------------------

class TestBarEvent:
    def test_signal_bar_fields(self, tmp_path: Path) -> None:
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        event = clock.poll()

        assert event is not None
        assert event.signal_bar.open_time == BAR_B_OPEN
        assert event.signal_bar.close_time == BAR_B_CLOSE
        assert event.signal_bar.close == 66800.0
        assert event.signal_bar.interval == "4h"

    def test_fill_bar_open(self, tmp_path: Path) -> None:
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        event = clock.poll()

        assert event is not None
        assert event.fill_bar_open == 66900.0
        assert event.fill_bar_open_time == BAR_C_OPEN


# ---------------------------------------------------------------------------
# 2) Polling logic
# ---------------------------------------------------------------------------

class TestPoll:
    def test_new_bar_detected(self, tmp_path: Path) -> None:
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        event = clock.poll()
        assert event is not None

    def test_same_bar_returns_none(self, tmp_path: Path) -> None:
        """Second poll with same klines returns None (dedup)."""
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        event1 = clock.poll()
        assert event1 is not None

        event2 = clock.poll()
        assert event2 is None

    def test_incomplete_bar_returns_none(self, tmp_path: Path) -> None:
        """Bar not yet closed (server time < close + buffer)."""
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_BEFORE_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        event = clock.poll()
        assert event is None

    def test_next_bar_detected_after_advance(self, tmp_path: Path) -> None:
        """After processing bar B, advancing to bar C produces a new event."""
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        event1 = clock.poll()
        assert event1 is not None

        # Time advances, klines shift
        client.klines = MagicMock(return_value=NEXT_THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_C)  # type: ignore[assignment]

        event2 = clock.poll()
        assert event2 is not None
        assert event2.signal_bar.close_time == BAR_C_CLOSE

    def test_csv_row_appended(self, tmp_path: Path) -> None:
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path, csv=True)

        clock.poll()

        csv_path = tmp_path / "live_bar_events.csv"
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        assert len(reader) == 2  # header + 1 data row
        header = reader[0]
        assert header[0] == "signal_close_iso"
        assert header[1] == "fill_open_iso"
        data = reader[1]
        assert data[2] == str(BAR_B_CLOSE)  # signal_close_ms
        assert data[3] == str(BAR_C_OPEN)   # fill_open_ms

    def test_not_enough_klines(self, tmp_path: Path) -> None:
        client = _make_client()
        client.klines = MagicMock(return_value=[THREE_KLINES[0]])  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        event = clock.poll()
        assert event is None


# ---------------------------------------------------------------------------
# 3) Persistence across restarts
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_kv_written_after_poll(self, tmp_path: Path) -> None:
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        clock.poll()
        assert clock.last_processed_ms() == BAR_B_CLOSE

    def test_restart_skips_processed(self, tmp_path: Path) -> None:
        """New BarClock on same DB skips already-processed bar."""
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]

        clock1 = _make_clock(client, tmp_path)
        event1 = clock1.poll()
        assert event1 is not None
        clock1.close()

        # "Restart" — new clock, same DB
        clock2 = BarClock(
            client,
            str(tmp_path / "clock.db"),
            symbol="BTCUSDT",
            interval="4h",
            safety_buffer_ms=5000,
        )
        assert clock2.last_processed_ms() == BAR_B_CLOSE

        event2 = clock2.poll()
        assert event2 is None  # already processed
        clock2.close()

    def test_multiple_polls_increment(self, tmp_path: Path) -> None:
        client = _make_client()
        client.klines = MagicMock(return_value=THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_B)  # type: ignore[assignment]
        clock = _make_clock(client, tmp_path)

        clock.poll()
        assert clock.last_processed_ms() == BAR_B_CLOSE

        # Advance
        client.klines = MagicMock(return_value=NEXT_THREE_KLINES)  # type: ignore[assignment]
        client.time = MagicMock(return_value=SERVER_AFTER_C)  # type: ignore[assignment]

        clock.poll()
        assert clock.last_processed_ms() == BAR_C_CLOSE
