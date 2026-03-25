"""Canonical data alignment — load BTC H4 data for both engines.

Produces:
  1. pandas DataFrame suitable for standalone LATCH (run_latch)
  2. list[Bar] suitable for v10 BacktestEngine
  3. Both aligned to exact same bar set

NO modification of any production file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Allow importing from btc-spot-dev root
_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from v10.core.types import Bar

DATA_CSV = _REPO / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"


def load_h4_dataframe(path: str | Path | None = None) -> pd.DataFrame:
    """Load H4 bars as a pandas DataFrame (standalone-compatible format).

    Returns DataFrame indexed by open_time with columns:
      open, high, low, close, volume, taker_buy_base_volume, close_time
    """
    p = Path(path) if path else DATA_CSV
    df = pd.read_csv(p)
    h4 = df[df["interval"] == "4h"].copy()
    h4 = h4.sort_values("open_time").reset_index(drop=True)

    # Rename to standalone convention
    rename = {}
    if "taker_buy_base_vol" in h4.columns:
        rename["taker_buy_base_vol"] = "taker_buy_base_volume"
    if rename:
        h4 = h4.rename(columns=rename)

    # Set open_time as index for standalone compatibility
    h4 = h4.set_index("open_time")
    return h4


def load_h4_bars(path: str | Path | None = None) -> list[Bar]:
    """Load H4 bars as list[Bar] for v10 BacktestEngine."""
    p = Path(path) if path else DATA_CSV
    df = pd.read_csv(p)
    h4 = df[df["interval"] == "4h"].copy()
    h4 = h4.sort_values("open_time").reset_index(drop=True)

    bars: list[Bar] = []
    for _, row in h4.iterrows():
        bars.append(Bar(
            open_time=int(row["open_time"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            close_time=int(row["close_time"]),
            taker_buy_base_vol=float(row.get("taker_buy_base_vol", 0.0)),
            interval="4h",
        ))
    return bars


def load_aligned_pair(
    path: str | Path | None = None,
) -> tuple[pd.DataFrame, list[Bar]]:
    """Load both representations, verify alignment, return (df, bars).

    Guarantees:
      - Same number of rows
      - open_time alignment is exact
      - OHLCV values are identical
    """
    df = load_h4_dataframe(path)
    bars = load_h4_bars(path)

    assert len(df) == len(bars), (
        f"Length mismatch: DataFrame {len(df)} vs bars {len(bars)}"
    )

    # Verify open_time alignment
    df_times = df.index.to_numpy(dtype=np.int64)
    bar_times = np.array([b.open_time for b in bars], dtype=np.int64)
    assert np.array_equal(df_times, bar_times), "open_time mismatch"

    # Verify OHLC alignment
    for col, attr in [("close", "close"), ("open", "open"),
                       ("high", "high"), ("low", "low")]:
        df_vals = df[col].to_numpy(dtype=np.float64)
        bar_vals = np.array([getattr(b, attr) for b in bars], dtype=np.float64)
        assert np.allclose(df_vals, bar_vals, atol=1e-10), (
            f"{col} mismatch between DataFrame and Bar list"
        )

    return df, bars


if __name__ == "__main__":
    df, bars = load_aligned_pair()
    print(f"Loaded {len(df)} aligned H4 bars")
    print(f"Date range: {pd.Timestamp(df.index[0], unit='ms')} to "
          f"{pd.Timestamp(df.index[-1], unit='ms')}")
    print(f"Columns: {list(df.columns)}")
