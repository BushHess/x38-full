"""Market data sources for paper/shadow trading.

Two sources:
  A) CsvBarSource    — replay from multi-TF CSV file (fast)
  B) BinanceBarSource — fetch klines from Binance REST API

Candle completeness (Binance):
  Only returns bars where server_time_ms > bar.close_time + safety_buffer_ms.

Kline caching utilities for deterministic replay.
"""

from __future__ import annotations

import csv
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Any

import requests

from v10.core.types import Bar

# ---------------------------------------------------------------------------
# Abstract source
# ---------------------------------------------------------------------------

class BarSource(ABC):
    """Abstract bar source — provides H4 and D1 bars."""

    @abstractmethod
    def fetch_h4(
        self,
        symbol: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[Bar]:
        ...

    @abstractmethod
    def fetch_d1(
        self,
        symbol: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[Bar]:
        ...


# ---------------------------------------------------------------------------
# CSV replay source
# ---------------------------------------------------------------------------

class CsvBarSource(BarSource):
    """Replay bars from a multi-TF CSV file.

    CSV must have columns: open_time, open, high, low, close, volume,
    close_time, taker_buy_base_vol, interval (at minimum).
    """

    def __init__(self, csv_path: str | Path) -> None:
        self._path = Path(csv_path)
        if not self._path.exists():
            raise FileNotFoundError(f"CSV file not found: {self._path}")
        self._h4_bars: list[Bar] = []
        self._d1_bars: list[Bar] = []
        self._load()

    def _load(self) -> None:
        import pandas as pd

        df = pd.read_csv(self._path)
        has_tbv = "taker_buy_base_vol" in df.columns

        for interval, attr in [("4h", "_h4_bars"), ("1d", "_d1_bars")]:
            sub = df[df["interval"] == interval].sort_values("open_time")
            bars: list[Bar] = []
            for _, row in sub.iterrows():
                bars.append(Bar(
                    open_time=int(row["open_time"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    close_time=int(row["close_time"]),
                    taker_buy_base_vol=(
                        float(row["taker_buy_base_vol"]) if has_tbv else 0.0
                    ),
                    interval=interval,
                ))
            setattr(self, attr, bars)

    @staticmethod
    def _filter(
        bars: list[Bar],
        start_ms: int | None,
        end_ms: int | None,
    ) -> list[Bar]:
        result = bars
        if start_ms is not None:
            result = [b for b in result if b.open_time >= start_ms]
        if end_ms is not None:
            result = [b for b in result if b.open_time <= end_ms]
        return result

    def fetch_h4(self, symbol: str, start_ms=None, end_ms=None) -> list[Bar]:
        return self._filter(self._h4_bars, start_ms, end_ms)

    def fetch_d1(self, symbol: str, start_ms=None, end_ms=None) -> list[Bar]:
        return self._filter(self._d1_bars, start_ms, end_ms)


# ---------------------------------------------------------------------------
# Binance REST source
# ---------------------------------------------------------------------------

_BINANCE_URLS: dict[str, str] = {
    "mainnet": "https://api.binance.com",
    "testnet": "https://testnet.binance.vision",
}


class BinanceBarSource(BarSource):
    """Fetch klines from Binance REST API (/api/v3/klines).

    Candle completeness: only returns bars where
    server_time_ms > bar.close_time + safety_buffer_ms.
    """

    def __init__(
        self,
        env: str = "mainnet",
        safety_buffer_ms: int = 5000,
    ) -> None:
        if env not in _BINANCE_URLS:
            raise ValueError(
                f"Unknown env '{env}', expected: {sorted(_BINANCE_URLS)}"
            )
        self._base_url = _BINANCE_URLS[env]
        self._safety_buffer_ms = safety_buffer_ms
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "v10-paper-trader/1.0"

    def server_time_ms(self) -> int:
        """Get Binance server time via /api/v3/time."""
        resp = self._session.get(
            f"{self._base_url}/api/v3/time", timeout=10,
        )
        resp.raise_for_status()
        return int(resp.json()["serverTime"])

    def _fetch_klines_raw(
        self,
        symbol: str,
        interval: str,
        start_ms: int | None = None,
        end_ms: int | None = None,
    ) -> list[Bar]:
        """Fetch all klines, paginating as needed (1000 per request)."""
        all_bars: list[Bar] = []
        cursor = start_ms

        while True:
            params: dict[str, Any] = {
                "symbol": symbol,
                "interval": interval,
                "limit": 1000,
            }
            if cursor is not None:
                params["startTime"] = cursor
            if end_ms is not None:
                params["endTime"] = end_ms

            resp = self._session.get(
                f"{self._base_url}/api/v3/klines",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            for k in data:
                all_bars.append(Bar(
                    open_time=int(k[0]),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                    close_time=int(k[6]),
                    taker_buy_base_vol=float(k[9]),
                    interval=interval,
                ))

            if len(data) < 1000:
                break
            cursor = int(data[-1][0]) + 1
            if end_ms is not None and cursor > end_ms:
                break

        return all_bars

    def _filter_closed(self, bars: list[Bar]) -> list[Bar]:
        """Keep only bars whose close_time + safety_buffer < server_time."""
        if not bars:
            return bars
        server_time = self.server_time_ms()
        cutoff = server_time - self._safety_buffer_ms
        return [b for b in bars if b.close_time < cutoff]

    def fetch_h4(self, symbol: str, start_ms=None, end_ms=None) -> list[Bar]:
        bars = self._fetch_klines_raw(symbol, "4h", start_ms, end_ms)
        return self._filter_closed(bars)

    def fetch_d1(self, symbol: str, start_ms=None, end_ms=None) -> list[Bar]:
        bars = self._fetch_klines_raw(symbol, "1d", start_ms, end_ms)
        return self._filter_closed(bars)


# ---------------------------------------------------------------------------
# Kline caching (for deterministic replay)
# ---------------------------------------------------------------------------

def cache_bars(bars: list[Bar], path: Path) -> None:
    """Write bars to a CSV cache file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "taker_buy_base_vol", "interval",
        ])
        for b in bars:
            w.writerow([
                b.open_time, b.open, b.high, b.low, b.close,
                b.volume, b.close_time, b.taker_buy_base_vol, b.interval,
            ])


def load_cached_bars(path: Path) -> list[Bar]:
    """Load bars from a CSV cache file."""
    if not path.exists():
        return []
    bars: list[Bar] = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            bars.append(Bar(
                open_time=int(row["open_time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                close_time=int(row["close_time"]),
                taker_buy_base_vol=float(row["taker_buy_base_vol"]),
                interval=row["interval"],
            ))
    return bars
