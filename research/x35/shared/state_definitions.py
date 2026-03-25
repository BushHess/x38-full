"""Frozen state definitions for x35_long_horizon_regime."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .common import aggregate_outer_bars


@dataclass(frozen=True)
class OuterRegimeSpec:
    spec_id: str
    timeframe: str
    family: str
    fast_period: int | None
    slow_period: int
    description: str

    @property
    def required_warmup_bars(self) -> int:
        return self.slow_period


FROZEN_SPECS: tuple[OuterRegimeSpec, ...] = (
    OuterRegimeSpec(
        spec_id="wk_close_above_ema26",
        timeframe="W1",
        family="close_above_ema",
        fast_period=None,
        slow_period=26,
        description="risk_on if completed W1 close > W1 EMA(26)",
    ),
    OuterRegimeSpec(
        spec_id="wk_ema13_above_ema26",
        timeframe="W1",
        family="ema_cross",
        fast_period=13,
        slow_period=26,
        description="risk_on if completed W1 EMA(13) > EMA(26)",
    ),
    OuterRegimeSpec(
        spec_id="mo_close_above_ema6",
        timeframe="M1",
        family="close_above_ema",
        fast_period=None,
        slow_period=6,
        description="risk_on if completed M1 close > M1 EMA(6)",
    ),
)


def build_state_series(d1_df: pd.DataFrame, spec: OuterRegimeSpec, report_start_ms: int) -> pd.DataFrame:
    outer = aggregate_outer_bars(d1_df, spec.timeframe).copy()
    outer["ema_slow"] = outer["close"].ewm(span=spec.slow_period, adjust=False).mean()

    if spec.family == "close_above_ema":
        outer["state"] = (outer["close"] > outer["ema_slow"]).astype(int)
        outer["signal_value"] = outer["close"]
    elif spec.family == "ema_cross":
        if spec.fast_period is None:
            raise ValueError(f"{spec.spec_id} requires a fast EMA period")
        outer["ema_fast"] = outer["close"].ewm(span=spec.fast_period, adjust=False).mean()
        outer["state"] = (outer["ema_fast"] > outer["ema_slow"]).astype(int)
        outer["signal_value"] = outer["ema_fast"] - outer["ema_slow"]
    else:
        raise ValueError(f"Unsupported family: {spec.family}")

    outer["state_label"] = outer["state"].map({1: "risk_on", 0: "risk_off"})
    outer["in_report"] = outer["close_time"] >= int(report_start_ms)
    outer["spec_id"] = spec.spec_id
    outer["description"] = spec.description
    return outer
