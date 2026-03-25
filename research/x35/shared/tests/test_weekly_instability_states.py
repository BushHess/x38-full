from __future__ import annotations

import pandas as pd
from research.x35.shared.weekly_instability_states import INSTABILITY_SPEC_IDS
from research.x35.shared.weekly_instability_states import build_weekly_instability_states


def _make_d1_frame(n_days: int = 240) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D", tz="UTC")
    close = pd.Series(range(n_days), dtype=float)
    close.iloc[60:120] = close.iloc[60:120].iloc[::-1].to_numpy()
    close.iloc[120:180] = close.iloc[120:180].to_numpy() + 20.0
    close.iloc[180:] = close.iloc[180:].iloc[::-1].to_numpy() + 40.0

    return pd.DataFrame(
        {
            "open_time": ((dates - pd.Timedelta(days=1)).view("int64") // 1_000_000).astype(int),
            "close_time": (dates.view("int64") // 1_000_000).astype(int),
            "open": close.to_numpy(),
            "high": (close + 1.0).to_numpy(),
            "low": (close - 1.0).to_numpy(),
            "close": close.to_numpy(),
            "volume": 1.0,
            "quote_volume": 1.0,
            "dt_close": dates,
        }
    )


def test_build_weekly_instability_states_returns_expected_specs() -> None:
    states = build_weekly_instability_states(_make_d1_frame())
    assert tuple(states.keys()) == INSTABILITY_SPEC_IDS


def test_weekly_instability_states_are_binary_with_labels() -> None:
    states = build_weekly_instability_states(_make_d1_frame())
    for frame in states.values():
        assert {"close_time", "state", "state_label", "spec_id"} <= set(frame.columns)
        assert set(frame["state"].dropna().unique()).issubset({0, 1})
        assert set(frame["state_label"].dropna().unique()).issubset({"stable", "unstable"})
