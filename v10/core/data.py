"""DataFeed — loads multi-timeframe CSV, provides H4 and D1 bar lists.

Expected CSV columns (Binance kline format):
  open_time, open, high, low, close, volume, close_time,
  quote_volume, trades, taker_buy_base_vol, taker_buy_quote_vol, interval
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from v10.core.types import Bar


def _date_to_ms(date_str: str) -> int:
    """Parse 'YYYY-MM-DD' to epoch ms UTC."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _row_to_bar(row: pd.Series) -> Bar:
    return Bar(
        open_time=int(row["open_time"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
        close_time=int(row["close_time"]),
        taker_buy_base_vol=float(row.get("taker_buy_base_vol", 0.0)),
        interval=str(row["interval"]),
        quote_volume=float(row.get("quote_volume", 0.0)),
        taker_buy_quote_vol=float(row.get("taker_buy_quote_vol", 0.0)),
    )


class DataFeed:
    """Loads a multi-timeframe CSV and provides sorted H4 / D1 bar lists.

    Parameters
    ----------
    path : str | Path
        Path to the CSV file.
    start : str | None
        Start date 'YYYY-MM-DD' (inclusive).  Filters on open_time.
    end : str | None
        End date 'YYYY-MM-DD' (inclusive).  Filters on open_time.
    warmup_days : int
        Calendar days of extra data to load BEFORE *start* for indicator
        warmup.  The engine uses ``report_start_ms`` to separate the
        warmup window from the reporting window.
    """

    def __init__(
        self,
        path: str | Path,
        start: str | None = None,
        end: str | None = None,
        warmup_days: int = 0,
    ) -> None:
        df = pd.read_csv(path)

        # Reporting-window boundary (epoch ms).
        # None means "all bars are reporting" (no warmup).
        self.report_start_ms: int | None = None

        if start is not None:
            start_ms = _date_to_ms(start)
            self.report_start_ms = start_ms
            # Load extra bars before start for indicator warmup
            load_start_ms = start_ms - warmup_days * 86_400_000
            df = df[df["open_time"] >= load_start_ms]

        if end is not None:
            # end is inclusive: include bars whose open_time falls on that day
            end_ms = _date_to_ms(end) + 86_400_000 - 1
            df = df[df["open_time"] <= end_ms]

        h4_df = df[df["interval"] == "4h"].sort_values("open_time").reset_index(drop=True)
        d1_df = df[df["interval"] == "1d"].sort_values("open_time").reset_index(drop=True)

        self.h4_bars: list[Bar] = [_row_to_bar(r) for _, r in h4_df.iterrows()]
        self.d1_bars: list[Bar] = [_row_to_bar(r) for _, r in d1_df.iterrows()]

    @property
    def n_h4(self) -> int:
        return len(self.h4_bars)

    @property
    def n_d1(self) -> int:
        return len(self.d1_bars)

    def __repr__(self) -> str:
        h4_start = self.h4_bars[0].open_time if self.h4_bars else 0
        h4_end = self.h4_bars[-1].open_time if self.h4_bars else 0
        return (
            f"DataFeed(h4={self.n_h4} bars, d1={self.n_d1} bars, "
            f"range={h4_start}..{h4_end})"
        )
