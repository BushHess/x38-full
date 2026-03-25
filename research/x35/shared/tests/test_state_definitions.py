from __future__ import annotations

import pandas as pd
from research.x35.shared.common import aggregate_outer_bars
from research.x35.shared.state_definitions import FROZEN_SPECS
from research.x35.shared.state_definitions import build_state_series


def _make_d1_frame(start: str, closes: list[float]) -> pd.DataFrame:
    dt_open = pd.date_range(start=start, periods=len(closes), freq="D", tz="UTC")
    dt_close = dt_open + pd.Timedelta(hours=23, minutes=59, seconds=59)
    base_ms = (dt_open.view("int64") // 1_000_000).astype(int)
    close_ms = (dt_close.view("int64") // 1_000_000).astype(int)
    return pd.DataFrame(
        {
            "open_time": base_ms,
            "close_time": close_ms,
            "open": closes,
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [10.0] * len(closes),
            "quote_volume": [100.0] * len(closes),
            "dt_close": dt_close,
        }
    )


def test_aggregate_outer_bars_weekly_groups_calendar_weeks() -> None:
    d1_df = _make_d1_frame("2024-01-01", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    weekly = aggregate_outer_bars(d1_df, "W1")

    assert len(weekly) == 2
    assert weekly.loc[0, "close"] == 7
    assert weekly.loc[1, "close"] == 10
    assert weekly.loc[0, "volume"] == 70.0


def test_build_state_series_emits_required_columns() -> None:
    d1_df = _make_d1_frame("2023-01-01", [float(i) for i in range(1, 250)])
    spec = next(item for item in FROZEN_SPECS if item.spec_id == "wk_close_above_ema26")
    states = build_state_series(d1_df, spec, report_start_ms=0)

    assert {"state", "state_label", "spec_id", "description", "in_report"} <= set(states.columns)
    assert states["spec_id"].nunique() == 1
    assert set(states["state_label"].unique()) <= {"risk_on", "risk_off"}
