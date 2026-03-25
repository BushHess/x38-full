"""Extended data alignment — load BTC H4 + D1 data for 6-strategy evaluation.

Extends data_align.py to also provide:
  - D1 close prices and close_times for E0_plus_EMA1D21 regime mapping
  - H4-to-D1 index mapping

NO modification of any production file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from v10.core.types import Bar
from data_align import load_h4_dataframe, load_h4_bars, load_aligned_pair

DATA_CSV = _REPO / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"


def load_d1_data(path: str | Path | None = None) -> dict:
    """Load D1 bars: close prices, close_times, open_times."""
    p = Path(path) if path else DATA_CSV
    df = pd.read_csv(p)
    d1 = df[df["interval"] == "1d"].copy()
    d1 = d1.sort_values("open_time").reset_index(drop=True)

    return {
        "close": d1["close"].to_numpy(dtype=np.float64),
        "close_time": d1["close_time"].to_numpy(dtype=np.int64),
        "open_time": d1["open_time"].to_numpy(dtype=np.int64),
        "high": d1["high"].to_numpy(dtype=np.float64),
        "low": d1["low"].to_numpy(dtype=np.float64),
        "n": len(d1),
    }


def load_all(path: str | Path | None = None) -> dict:
    """Load H4 (DataFrame + Bar list) and D1 data, verify alignment.

    Returns dict with keys:
      df: H4 DataFrame
      bars: list[Bar]
      d1: dict with close, close_time, etc.
      h4_close_times: int64 array
    """
    df, bars = load_aligned_pair(path)
    d1 = load_d1_data(path)

    # H4 close times for D1 mapping
    h4_ct = df["close_time"].to_numpy(dtype=np.int64)

    return {
        "df": df,
        "bars": bars,
        "d1": d1,
        "h4_close_times": h4_ct,
        "n_h4": len(bars),
        "n_d1": d1["n"],
    }


if __name__ == "__main__":
    data = load_all()
    print(f"H4: {data['n_h4']} bars")
    print(f"D1: {data['n_d1']} bars")
    print(f"H4 date range: {pd.Timestamp(data['df'].index[0], unit='ms')} to "
          f"{pd.Timestamp(data['df'].index[-1], unit='ms')}")
