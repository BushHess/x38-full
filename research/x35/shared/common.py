"""Shared helpers for x35_long_horizon_regime."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
STUDY_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"

DEFAULT_START = "2019-01-01"
DEFAULT_END = "2026-02-20"
DEFAULT_WARMUP_DAYS = 365

sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed  # noqa: E402


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_feed(
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    warmup_days: int = DEFAULT_WARMUP_DAYS,
) -> DataFeed:
    return DataFeed(str(DATA_PATH), start=start, end=end, warmup_days=warmup_days)


def bars_to_frame(bars: list[Any], report_start_ms: int | None) -> pd.DataFrame:
    rows = []
    for bar in bars:
        rows.append(
            {
                "open_time": int(bar.open_time),
                "close_time": int(bar.close_time),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
                "quote_volume": float(getattr(bar, "quote_volume", 0.0)),
                "taker_buy_base_vol": float(bar.taker_buy_base_vol),
                "taker_buy_quote_vol": float(getattr(bar, "taker_buy_quote_vol", 0.0)),
                "interval": str(bar.interval),
            }
        )

    frame = pd.DataFrame(rows)
    frame["dt_open"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    frame["dt_close"] = pd.to_datetime(frame["close_time"], unit="ms", utc=True)
    frame["in_report"] = True if report_start_ms is None else frame["close_time"] >= int(report_start_ms)
    return frame


def aggregate_outer_bars(d1_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe not in {"W1", "M1"}:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    naive_close = d1_df["dt_close"].dt.tz_convert(None)
    period_id = (
        naive_close.dt.to_period("W-SUN").astype(str)
        if timeframe == "W1"
        else naive_close.dt.to_period("M").astype(str)
    )

    grouped = d1_df.assign(period_id=period_id).groupby("period_id", sort=True, as_index=False)
    outer = grouped.agg(
        open_time=("open_time", "first"),
        close_time=("close_time", "last"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        quote_volume=("quote_volume", "sum"),
        dt_close=("dt_close", "last"),
    )
    outer["timeframe"] = timeframe
    return outer


def attach_state_to_events(
    events_df: pd.DataFrame,
    states_df: pd.DataFrame,
    *,
    event_time_col: str,
) -> pd.DataFrame:
    left = events_df.sort_values(event_time_col).copy()
    right = states_df.sort_values("close_time").copy()
    return pd.merge_asof(
        left,
        right,
        left_on=event_time_col,
        right_on="close_time",
        direction="backward",
        allow_exact_matches=True,
    )


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


def safe_div(num: float, den: float) -> float:
    return 0.0 if den == 0 else num / den


def pct(value: float) -> float:
    return round(value * 100.0, 2)


def ts_to_date(ts_ms: int) -> str:
    return pd.to_datetime(ts_ms, unit="ms", utc=True).strftime("%Y-%m-%d")
