"""V4 macroHystB strategy — rebuilt as v10 Strategy subclass.

Source: research/x37/resource/gen1/v4_macroHystB/Spec2_System_Specification_new_final_flow.md
Frozen params: research/x37/resource/gen1/v4_macroHystB/research/final_practical_system.json

Features:
  d1_ret_60      -- 60-day return on D1 close (macro regime gate)
  h4_trendq_84   -- H4 84-bar trend quality (risk-adjusted momentum)
  h4_buyimb_12   -- H4 12-bar taker buy imbalance (flow confirmation)

State machine:
  FLAT -> LONG when: macro_on AND entry_on AND flow_on
  LONG -> FLAT when: NOT hold_on

Threshold calibration:
  macro/entry/hold: expanding quantile from calibration_start to year boundary
  flow: trailing 365-day quantile
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy


@dataclass
class V4MacroHystBConfig:
    # Feature lookbacks
    d1_ret_lookback: int = 60
    h4_trend_lookback: int = 84
    h4_buyimb_lookback: int = 12

    # Quantile levels
    macro_quantile: float = 0.50
    entry_quantile: float = 0.60
    hold_quantile: float = 0.50
    flow_quantile: float = 0.55

    # Calibration modes
    flow_mode: str = "trailing_365"  # "expanding" or "trailing_365"
    calibration_start: str = "2019-01-01"  # expanding window anchor

    # D1->H4 alignment
    allow_exact_matches: bool = True  # spec-exact: d1_close_time <= h4_close_time

    # Trade start (no trades before this date)
    trade_start: str = "2020-01-01"


def _date_str_to_ms(s: str) -> int:
    d = dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp() * 1000)


class V4MacroHystBStrategy(Strategy):
    def __init__(self, config: V4MacroHystBConfig | None = None) -> None:
        self._c = config or V4MacroHystBConfig()

        # Precomputed arrays (set in on_init)
        self._h4_d1_ret_60: np.ndarray | None = None
        self._h4_trendq: np.ndarray | None = None
        self._h4_buyimb: np.ndarray | None = None

        # Yearly thresholds: {year: (macro, entry, hold, flow)}
        self._thresholds: dict[int, tuple[float, float, float, float]] = {}

        # Runtime state
        self._state = "FLAT"
        self._trade_start_ms = _date_str_to_ms(self._c.trade_start)

    def name(self) -> str:
        return "v4_macro_hystb"

    # ------------------------------------------------------------------
    # on_init: precompute features + calibrate thresholds
    # ------------------------------------------------------------------

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n_h4 = len(h4_bars)
        if n_h4 == 0:
            return

        # ---- extract H4 arrays ----
        h4_close = np.array([b.close for b in h4_bars], dtype=np.float64)
        h4_volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        h4_taker_buy = np.array(
            [b.taker_buy_base_vol for b in h4_bars], dtype=np.float64,
        )
        h4_close_times = np.array(
            [b.close_time for b in h4_bars], dtype=np.int64,
        )

        # ---- D1 features ----
        d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
        d1_close_times = np.array(
            [b.close_time for b in d1_bars], dtype=np.int64,
        )

        # d1_ret_60
        lb = self._c.d1_ret_lookback
        d1_ret_60 = np.full(len(d1_close), np.nan)
        for i in range(lb, len(d1_close)):
            d1_ret_60[i] = d1_close[i] / d1_close[i - lb] - 1

        # ---- D1->H4 alignment ----
        h4_d1_ret_60 = np.full(n_h4, np.nan)
        d1_idx = 0
        n_d1 = len(d1_bars)
        for i in range(n_h4):
            h4_ct = h4_close_times[i]
            while (
                d1_idx + 1 < n_d1
                and self._d1_visible_at_h4_close(d1_close_times[d1_idx + 1], h4_ct)
            ):
                d1_idx += 1
            if self._d1_visible_at_h4_close(d1_close_times[d1_idx], h4_ct):
                h4_d1_ret_60[i] = d1_ret_60[d1_idx]
        self._h4_d1_ret_60 = h4_d1_ret_60

        # ---- H4 trend quality (h4_trendq_84) ----
        tlb = self._c.h4_trend_lookback
        logret = np.full(n_h4, np.nan)
        logret[1:] = np.log(h4_close[1:] / h4_close[:-1])

        trendq = np.full(n_h4, np.nan)
        sqrt_tlb = np.sqrt(tlb)
        for i in range(tlb, n_h4):
            ret_n = h4_close[i] / h4_close[i - tlb] - 1
            window = logret[i - tlb + 1: i + 1]
            std_val = np.std(window, ddof=1)
            if std_val > 0:
                trendq[i] = ret_n / (std_val * sqrt_tlb)
            else:
                trendq[i] = 0.0
        self._h4_trendq = trendq

        # ---- H4 buy imbalance (h4_buyimb_12) ----
        blb = self._c.h4_buyimb_lookback
        buyimb = np.full(n_h4, np.nan)
        tb_cs = np.cumsum(h4_taker_buy)
        vol_cs = np.cumsum(h4_volume)
        for i in range(blb - 1, n_h4):
            if i < blb:
                tb_sum = tb_cs[i]
                vol_sum = vol_cs[i]
            else:
                tb_sum = tb_cs[i] - tb_cs[i - blb]
                vol_sum = vol_cs[i] - vol_cs[i - blb]
            if vol_sum > 0:
                buyimb[i] = 2.0 * (tb_sum / vol_sum) - 1.0
        self._h4_buyimb = buyimb

        # ---- yearly threshold calibration ----
        self._calibrate_thresholds(
            h4_close_times, h4_d1_ret_60, trendq, buyimb,
        )

    def _d1_visible_at_h4_close(self, d1_close_time: int, h4_close_time: int) -> bool:
        if self._c.allow_exact_matches:
            return d1_close_time <= h4_close_time
        return d1_close_time < h4_close_time

    def _calibrate_thresholds(
        self,
        h4_close_times: np.ndarray,
        h4_d1_ret_60: np.ndarray,
        trendq: np.ndarray,
        buyimb: np.ndarray,
    ) -> None:
        cal_start_ms = _date_str_to_ms(self._c.calibration_start)

        # Determine years present in data
        years: set[int] = set()
        for ct in h4_close_times:
            y = dt.datetime.fromtimestamp(ct / 1000, tz=dt.timezone.utc).year
            years.add(y)

        for year in sorted(years):
            year_start_ms = int(
                dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc).timestamp()
                * 1000
            )

            # Expanding mask: [calibration_start, year_start)
            exp_mask = (
                (h4_close_times >= cal_start_ms)
                & (h4_close_times < year_start_ms)
            )
            if not np.any(exp_mask):
                continue

            # Expanding quantiles (NaN-safe)
            macro_vals = h4_d1_ret_60[exp_mask]
            macro_vals = macro_vals[~np.isnan(macro_vals)]
            if len(macro_vals) == 0:
                continue
            macro_thr = float(np.quantile(macro_vals, self._c.macro_quantile))

            tq_vals = trendq[exp_mask]
            tq_vals = tq_vals[~np.isnan(tq_vals)]
            if len(tq_vals) == 0:
                continue
            entry_thr = float(np.quantile(tq_vals, self._c.entry_quantile))
            hold_thr = float(np.quantile(tq_vals, self._c.hold_quantile))

            # Flow threshold: trailing 365 days or expanding
            if self._c.flow_mode == "trailing_365":
                trail_start_ms = year_start_ms - 365 * 86_400_000
                flow_mask = (
                    (h4_close_times >= trail_start_ms)
                    & (h4_close_times < year_start_ms)
                )
            else:
                flow_mask = exp_mask

            flow_vals = buyimb[flow_mask]
            flow_vals = flow_vals[~np.isnan(flow_vals)]
            if len(flow_vals) == 0:
                continue
            flow_thr = float(np.quantile(flow_vals, self._c.flow_quantile))

            self._thresholds[year] = (macro_thr, entry_thr, hold_thr, flow_thr)

    # ------------------------------------------------------------------
    # on_bar: state machine
    # ------------------------------------------------------------------

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index
        if (
            self._h4_d1_ret_60 is None
            or self._h4_trendq is None
            or self._h4_buyimb is None
        ):
            return None

        # No trades before trade_start
        if state.bar.open_time < self._trade_start_ms:
            return None

        # Get year from bar open_time
        year = dt.datetime.fromtimestamp(
            state.bar.open_time / 1000, tz=dt.timezone.utc,
        ).year

        # Look up thresholds (fall back to most recent available year)
        thresholds = self._thresholds.get(year)
        if thresholds is None:
            available = [y for y in sorted(self._thresholds) if y <= year]
            if not available:
                return None
            thresholds = self._thresholds[available[-1]]

        macro_thr, entry_thr, hold_thr, flow_thr = thresholds

        # Feature values
        d1_ret = self._h4_d1_ret_60[i]
        tq = self._h4_trendq[i]
        bi = self._h4_buyimb[i]

        # NaN -> condition is False
        macro_on = not np.isnan(d1_ret) and d1_ret > macro_thr
        entry_on = not np.isnan(tq) and tq > entry_thr
        flow_on = not np.isnan(bi) and bi > flow_thr
        hold_on = not np.isnan(tq) and tq > hold_thr

        if self._state == "FLAT":
            if macro_on and entry_on and flow_on:
                self._state = "LONG"
                return Signal(target_exposure=1.0, reason="v4_entry")
        elif self._state == "LONG":
            if not hold_on:
                self._state = "FLAT"
                return Signal(target_exposure=0.0, reason="v4_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass
