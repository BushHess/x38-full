"""Shared weekly instability state definitions for x35."""

from __future__ import annotations

import pandas as pd

from .common import aggregate_outer_bars

INSTABILITY_SPEC_IDS: tuple[str, ...] = (
    "wk_mixed_structure_flag",
    "wk_flip_count_8w_ge_2",
    "wk_score_range_8w_ge_2",
)


def build_weekly_instability_states(d1_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    weekly = aggregate_outer_bars(d1_df, "W1").copy()
    weekly["ema13"] = weekly["close"].ewm(span=13, adjust=False).mean()
    weekly["ema26"] = weekly["close"].ewm(span=26, adjust=False).mean()
    weekly["ema52"] = weekly["close"].ewm(span=52, adjust=False).mean()
    weekly["alignment_score"] = (
        (weekly["close"] > weekly["ema26"]).astype(int)
        + (weekly["ema13"] > weekly["ema26"]).astype(int)
        + (weekly["ema26"] > weekly["ema52"]).astype(int)
    )

    score_change = weekly["alignment_score"].diff().fillna(0).ne(0).astype(int)
    weekly["flip_count_8w"] = score_change.rolling(8, min_periods=8).sum()
    weekly["score_range_8w"] = (
        weekly["alignment_score"].rolling(8, min_periods=8).max()
        - weekly["alignment_score"].rolling(8, min_periods=8).min()
    )

    states: dict[str, pd.DataFrame] = {}

    mixed = weekly[["close_time"]].copy()
    mixed["state"] = weekly["alignment_score"].isin([1, 2]).astype(int)
    states["wk_mixed_structure_flag"] = mixed

    flip_density = weekly[["close_time", "flip_count_8w"]].copy()
    flip_density["state"] = (flip_density["flip_count_8w"] >= 2).astype(int)
    states["wk_flip_count_8w_ge_2"] = flip_density[["close_time", "state"]]

    score_range = weekly[["close_time", "score_range_8w"]].copy()
    score_range["state"] = (score_range["score_range_8w"] >= 2).astype(int)
    states["wk_score_range_8w_ge_2"] = score_range[["close_time", "state"]]

    for spec_id, frame in states.items():
        frame["state_label"] = frame["state"].map({0: "stable", 1: "unstable"})
        frame["spec_id"] = spec_id

    return states
