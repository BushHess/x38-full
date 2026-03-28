"""OH0_D1_TREND40 — Vectorized D1 momentum strategy.

Faithful reimplementation of S_D1_TREND from:
  research/x37/resource/gen1/v8_sd1trebd/spec/spec_2_system_S_D1_TREND.md

Native D1, long-only, long/flat. Single signal: D1_MOM_RET(40) > 0.
No H4 dependency. Uses Pattern B (vectorized sim).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np


_LIVE_START_MS = int(
    datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
)


@dataclass
class OH0Result:
    """Result container for OH0 D1 sim."""

    daily_returns: np.ndarray
    open_times: np.ndarray
    positions: np.ndarray
    mom40: np.ndarray
    n_transitions: int
    n_completed_trades: int
    trade_returns: list[float]
    sharpe: float
    cagr_pct: float
    max_dd_pct: float
    final_equity: float
    # Full arrays (all bars, not just live) for segment splitting
    all_positions: np.ndarray | None = None
    all_daily_ret: np.ndarray | None = None
    all_open_times: np.ndarray | None = None


def run_oh0_sim(
    d1_close: np.ndarray,
    d1_open: np.ndarray,
    d1_open_time: np.ndarray,
    cost_per_side: float = 0.001,
) -> OH0Result:
    """Run OH0 D1_TREND40 vectorized simulation.

    Parameters
    ----------
    d1_close : array of D1 close prices
    d1_open : array of D1 open prices (for next-open execution)
    d1_open_time : array of D1 open_time (epoch ms, for live-start filter)
    cost_per_side : cost per side as fraction (0.001 = 10 bps)
    """
    n = len(d1_close)
    c = cost_per_side

    # Compute momentum signal
    mom40 = np.full(n, np.nan)
    signal = np.full(n, np.nan)
    for i in range(40, n):
        mom40[i] = d1_close[i] / d1_close[i - 40] - 1.0
        signal[i] = 1.0 if mom40[i] > 0.0 else 0.0

    # Position: next-open execution, no trades before 2020-01-01
    position = np.zeros(n)
    for i in range(1, n):
        if d1_open_time[i] < _LIVE_START_MS:
            position[i] = 0.0
        elif not np.isnan(signal[i - 1]):
            position[i] = signal[i - 1]
        else:
            position[i] = 0.0

    # Compute open-to-open interval returns with cost
    # position[i] is held from open_i to open_{i+1}
    # We need next_open = open[i+1] for the return computation
    daily_ret = np.zeros(n)
    for i in range(n - 1):
        prev_pos = position[i - 1] if i > 0 else 0.0
        cur_pos = position[i]
        next_open = d1_open[i + 1]
        cur_open = d1_open[i]

        if prev_pos == 0 and cur_pos == 0:
            # flat to flat
            daily_ret[i] = 0.0
        elif prev_pos == 0 and cur_pos == 1:
            # entry
            daily_ret[i] = (1 - c) * (next_open / cur_open) - 1.0
        elif prev_pos == 1 and cur_pos == 1:
            # stay long
            daily_ret[i] = next_open / cur_open - 1.0
        elif prev_pos == 1 and cur_pos == 0:
            # exit (cost deducted, no market exposure)
            daily_ret[i] = -c

    # Count state transitions and completed trades
    n_transitions = 0
    trade_returns: list[float] = []
    entry_open = 0.0
    in_trade = False

    for i in range(1, n):
        prev_pos = position[i - 1] if i > 0 else 0.0
        if position[i] != prev_pos:
            n_transitions += 1
            if position[i] == 1.0 and not in_trade:
                # entry
                entry_open = d1_open[i]
                in_trade = True
            elif position[i] == 0.0 and in_trade:
                # exit
                exit_open = d1_open[i]
                net = (exit_open / entry_open) * (1 - c) * (1 - c) - 1.0
                trade_returns.append(net)
                in_trade = False

    # Metrics on the live period
    live_mask = d1_open_time >= _LIVE_START_MS
    # Exclude last bar (no next_open return)
    live_mask[-1] = False
    live_ret = daily_ret[live_mask]

    # Sharpe (daily, ddof=1, annualized sqrt(365))
    if len(live_ret) > 1 and np.std(live_ret, ddof=1) > 0:
        sharpe = float(
            np.mean(live_ret) / np.std(live_ret, ddof=1) * np.sqrt(365)
        )
    else:
        sharpe = 0.0

    # Equity curve and CAGR
    equity = np.cumprod(1.0 + live_ret)
    final_eq = float(equity[-1]) if len(equity) > 0 else 1.0
    n_days = int(np.sum(live_mask))
    if n_days > 0 and final_eq > 0:
        cagr = (final_eq ** (365.0 / n_days) - 1.0) * 100.0
    else:
        cagr = 0.0

    # Max drawdown
    running_peak = np.maximum.accumulate(equity)
    drawdown = (equity - running_peak) / running_peak
    max_dd = float(np.min(drawdown)) * 100.0  # negative percentage

    return OH0Result(
        daily_returns=live_ret,
        open_times=d1_open_time[live_mask],
        positions=position[live_mask],
        mom40=mom40,
        n_transitions=n_transitions,
        n_completed_trades=len(trade_returns),
        trade_returns=trade_returns,
        sharpe=sharpe,
        cagr_pct=cagr,
        max_dd_pct=abs(max_dd),
        final_equity=final_eq,
        all_positions=position,
        all_daily_ret=daily_ret,
        all_open_times=d1_open_time,
    )


@dataclass
class SegmentMetrics:
    """Per-segment metrics for parity verification."""

    name: str
    start_date: str
    end_date: str
    n_transitions: int
    sharpe: float
    cagr_pct: float
    max_dd_pct: float


def compute_segment_metrics(
    result: OH0Result,
    segment_name: str,
    start_date_ms: int,
    end_date_ms: int,
) -> SegmentMetrics:
    """Compute OH0 metrics for a specific segment.

    Uses the full arrays from the sim result. The segment boundaries
    define which bars' returns are included. Transition counts include
    the boundary transition (comparing against the bar immediately
    before the segment start).

    Metrics match the frozen spec domain:
      Sharpe = mean/std(ddof=1) * sqrt(365)
      CAGR = equity_end ** (365/N_days) - 1
      MDD = peak-to-trough on cumulative equity
    """
    assert result.all_positions is not None
    pos = result.all_positions
    ret = result.all_daily_ret
    ot = result.all_open_times

    # Select bars in this segment
    mask = (ot >= start_date_ms) & (ot <= end_date_ms)
    # Exclude last bar of the ENTIRE array (no next_open), not just segment
    n_total = len(ot)
    if mask[n_total - 1]:
        mask[n_total - 1] = False

    seg_ret = ret[mask]
    seg_ot = ot[mask]

    # Count state transitions within the segment, including the
    # boundary transition (position at first segment bar vs bar before it)
    seg_indices = np.where(mask)[0]
    n_trans = 0
    for idx in seg_indices:
        prev = pos[idx - 1] if idx > 0 else 0.0
        if pos[idx] != prev:
            n_trans += 1

    # Sharpe (daily, ddof=1, annualized sqrt(365)) per frozen spec §9
    if len(seg_ret) > 1 and np.std(seg_ret, ddof=1) > 0:
        sharpe = float(np.mean(seg_ret) / np.std(seg_ret, ddof=1) * np.sqrt(365))
    else:
        sharpe = 0.0

    # Equity curve and CAGR
    eq = np.cumprod(1.0 + seg_ret)
    final = float(eq[-1]) if len(eq) > 0 else 1.0
    n_days = len(seg_ret)
    if n_days > 0 and final > 0:
        cagr = (final ** (365.0 / n_days) - 1.0) * 100.0
    else:
        cagr = 0.0

    # Max drawdown
    if len(eq) > 0:
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / peak
        max_dd = abs(float(np.min(dd))) * 100.0
    else:
        max_dd = 0.0

    def _fmt(ms: int) -> str:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    return SegmentMetrics(
        name=segment_name,
        start_date=_fmt(start_date_ms),
        end_date=_fmt(end_date_ms),
        n_transitions=n_trans,
        sharpe=round(sharpe, 4),
        cagr_pct=round(cagr, 1),
        max_dd_pct=round(max_dd, 1),
    )
