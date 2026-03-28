"""PF0_E5_EMA21D1 — Self-contained H4+D1 strategy simulator.

Faithful reimplementation of E5_ema21D1 from:
  strategies/vtrend_e5_ema21_d1/strategy.py

Lineage: verified against strategies/vtrend_e5_ema21_d1/strategy.py
  SHA256: d9d1a10bd1b6bc9ec14e6cbee12f8f52a68905b83deb39d6411901bdaa49b4d9
  Parity confirmed on 2026-03-28 (trade count exact, signal timing identical).

Uses Pattern B (vectorized indicators + sequential position loop).
Cost model: simple per-side fraction (same model as OH0_D1_TREND40).
Default cost: 10 bps/side = 20 bps RT.

Entry conditions (ALL must be true, not in position):
  1. EMA(close, 30) > EMA(close, 120)  — H4 trend up
  2. VDO > 0.0                          — taker buy pressure
  3. D1_close > D1_EMA(21)              — D1 regime filter
Exit conditions (ANY triggers, in position):
  1. close < peak_price - 3.0 * robust_ATR  — trail stop
  2. EMA(close, 30) < EMA(close, 120)       — trend reversal
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

import numpy as np

_DEFAULT_REPORT_START_MS = int(
    datetime(2019, 1, 1, tzinfo=UTC).timestamp() * 1000
)
"""Default report start: 2019-01-01 UTC.

Matches DataFeed(start="2019-01-01", warmup_days=365) used by v10 validation.
The warmup loads data from ~2018-01-01; reporting (live) starts at 2019-01-01.
OH0 uses 2020-01-01 (its frozen spec), but PF0's lineage target has 2019-01-01.
Cross-baseline comparison uses A01 eras which start at 2020-01-01.
"""

# Frozen strategy parameters
_SLOW_PERIOD = 120
_FAST_PERIOD = 30  # max(5, slow_period // 4)
_TRAIL_MULT = 3.0
_VDO_THRESHOLD = 0.0
_D1_EMA_PERIOD = 21
_VDO_FAST = 12
_VDO_SLOW = 28
_RATR_CAP_Q = 0.90
_RATR_CAP_LB = 100
_RATR_PERIOD = 20

# Metric domain: H4 periods per year (matching v10 SPEC_METRICS)
_PERIODS_PER_YEAR = 2190.0  # (24/4) * 365


@dataclass
class PF0Result:
    """Result container for PF0 H4 sim."""

    # Live period arrays
    navs: np.ndarray
    h4_close_times: np.ndarray
    positions: np.ndarray
    exposures: np.ndarray

    # Trade-level
    n_trades: int
    trade_returns: list[float]
    trade_entry_ts: list[int]
    trade_pnl: list[float]

    # Summary metrics (H4 domain, ddof=0)
    sharpe: float
    cagr_pct: float
    max_dd_pct: float
    final_nav: float
    win_rate_pct: float
    avg_exposure: float
    profit_factor: float

    # Full arrays (warmup + live) for segment splitting
    all_navs: np.ndarray | None = None
    all_positions: np.ndarray | None = None
    all_h4_close_times: np.ndarray | None = None


def run_pf0_sim(
    h4_close: np.ndarray,
    h4_high: np.ndarray,
    h4_low: np.ndarray,
    h4_open: np.ndarray,
    h4_volume: np.ndarray,
    h4_taker_buy: np.ndarray,
    h4_close_time: np.ndarray,
    h4_open_time: np.ndarray,
    d1_close: np.ndarray,
    d1_close_time: np.ndarray,
    cost_per_side: float = 0.001,
    initial_cash: float = 10_000.0,
    report_start_ms: int | None = None,
) -> PF0Result:
    """Run PF0 E5_ema21D1 H4+D1 simulation.

    Parameters
    ----------
    h4_close, h4_high, h4_low, h4_open : H4 price arrays
    h4_volume, h4_taker_buy : H4 volume arrays (taker data required)
    h4_close_time, h4_open_time : H4 timestamp arrays (epoch ms)
    d1_close, d1_close_time : D1 close prices and timestamps
    cost_per_side : cost per side as fraction (0.001 = 10 bps)
    initial_cash : starting capital
    report_start_ms : epoch ms for live-period start (None = 2019-01-01 UTC)
    """
    n = len(h4_close)
    c = cost_per_side
    live_start = report_start_ms if report_start_ms is not None else _DEFAULT_REPORT_START_MS

    # ── 1. Indicators (vectorized) ────────────────────────────────────────

    ema_f = _ema(h4_close, _FAST_PERIOD)
    ema_s = _ema(h4_close, _SLOW_PERIOD)
    ratr = _robust_atr(
        h4_high, h4_low, h4_close,
        _RATR_CAP_Q, _RATR_CAP_LB, _RATR_PERIOD,
    )
    vdo = _vdo(h4_volume, h4_taker_buy, _VDO_FAST, _VDO_SLOW)
    d1_regime = _map_d1_regime(
        h4_close_time, d1_close, d1_close_time, _D1_EMA_PERIOD,
    )

    # ── 2. Signal generation (strategy logic at bar close) ────────────────
    #
    # Matches v10 engine: on_bar at close → pending signal → next-open fill.
    # During warmup (close_time < live_start): no signals (v10 rolls back
    # strategy state, so _in_position stays False throughout warmup).
    #
    # NOTE: regime monitor exit (enable_regime_monitor) intentionally omitted.
    # Frozen config has enable_regime_monitor=False — monitor path is dead code
    # in the original. If monitors are ever needed, add both entry guard and
    # exit path here.

    signal = np.zeros(n, dtype=np.int8)  # 0=hold, 1=entry, -1=exit
    in_pos = False
    peak_px = 0.0

    for i in range(1, n):  # skip i=0 (strategy guard: bar_index < 1)
        if h4_close_time[i] < live_start:
            continue

        ef = ema_f[i]
        es = ema_s[i]
        rv = ratr[i]

        if math.isnan(ef) or math.isnan(es) or math.isnan(rv):
            continue

        if not in_pos:
            if ef > es and vdo[i] > _VDO_THRESHOLD and d1_regime[i]:
                signal[i] = 1
                in_pos = True
                peak_px = h4_close[i]
        else:
            peak_px = max(peak_px, h4_close[i])
            trail = peak_px - _TRAIL_MULT * rv
            if h4_close[i] < trail:
                signal[i] = -1
                in_pos = False
                peak_px = 0.0
            elif ef < es:  # trend reversal (checked after trail stop)
                signal[i] = -1
                in_pos = False
                peak_px = 0.0

    # ── 3. Position array (next-open execution) ───────────────────────────

    position = np.zeros(n, dtype=np.int8)
    for i in range(1, n):
        if signal[i - 1] == 1:
            position[i] = 1
        elif signal[i - 1] == -1:
            position[i] = 0
        else:
            position[i] = position[i - 1]

    # ── 4. NAV and trade tracking ─────────────────────────────────────────

    cash = initial_cash
    btc = 0.0
    navs = np.zeros(n)
    expo = np.zeros(n)
    navs[0] = initial_cash

    trade_list: list[tuple[float, float, int]] = []  # (return, pnl, entry_ts)
    entry_cash = 0.0
    entry_ts = 0

    for i in range(n):
        prev = position[i - 1] if i > 0 else 0
        cur = position[i]

        if prev == 0 and cur == 1:
            # Entry at bar open: invest cash minus per-side cost
            invest = cash * (1.0 - c)
            btc = invest / h4_open[i]
            entry_cash = cash
            entry_ts = int(h4_open_time[i])
            cash = 0.0
        elif prev == 1 and cur == 0:
            # Exit at bar open: sell BTC minus per-side cost
            proceeds = btc * h4_open[i] * (1.0 - c)
            pnl = proceeds - entry_cash
            ret = proceeds / entry_cash - 1.0 if entry_cash > 0 else 0.0
            trade_list.append((ret, pnl, entry_ts))
            cash = proceeds
            btc = 0.0

        navs[i] = cash + btc * h4_close[i]
        expo[i] = (btc * h4_close[i]) / navs[i] if navs[i] > 1e-12 else 0.0

    # ── 5. Metrics (live period) ──────────────────────────────────────────

    live_mask = h4_close_time >= live_start
    live_navs = navs[live_mask]
    live_ct = h4_close_time[live_mask]
    live_pos = position[live_mask].astype(np.float64)
    live_expo = expo[live_mask]

    # H4 returns from NAV series
    rets = np.diff(live_navs) / live_navs[:-1]

    # Sharpe (H4, ddof=0, sqrt(2190)) — matches v10 metric domain
    sharpe = 0.0
    if len(rets) > 1 and np.std(rets, ddof=0) > 1e-12:
        sharpe = float(
            np.mean(rets) / np.std(rets, ddof=0) * math.sqrt(_PERIODS_PER_YEAR)
        )

    # CAGR
    final_nav = float(live_navs[-1])
    start_nav = float(live_navs[0])
    years = (int(live_ct[-1]) - int(live_ct[0])) / (365.25 * 24 * 3600 * 1000)
    cagr = 0.0
    if years > 1e-6 and final_nav > 0 and start_nav > 0:
        cagr = (pow(final_nav / start_nav, 1.0 / years) - 1.0) * 100.0

    # Max drawdown
    peak = np.maximum.accumulate(live_navs)
    dd = 1.0 - live_navs / peak
    max_dd = float(dd.max()) * 100.0

    # Trade stats
    n_trades = len(trade_list)
    trade_rets = [t[0] for t in trade_list]
    trade_pnls = [t[1] for t in trade_list]
    trade_tss = [t[2] for t in trade_list]

    wins = sum(1 for r in trade_rets if r > 0)
    win_rate = (wins / n_trades * 100.0) if n_trades > 0 else 0.0

    gp = sum(p for p in trade_pnls if p > 0)
    gl = abs(sum(p for p in trade_pnls if p < 0))
    pf = gp / gl if gl > 1e-12 else (float("inf") if gp > 0 else 0.0)

    avg_expo_val = float(np.mean(live_expo))

    return PF0Result(
        navs=live_navs,
        h4_close_times=live_ct,
        positions=live_pos,
        exposures=live_expo,
        n_trades=n_trades,
        trade_returns=trade_rets,
        trade_entry_ts=trade_tss,
        trade_pnl=trade_pnls,
        sharpe=sharpe,
        cagr_pct=cagr,
        max_dd_pct=max_dd,
        final_nav=final_nav,
        win_rate_pct=win_rate,
        avg_exposure=avg_expo_val,
        profit_factor=pf,
        all_navs=navs,
        all_positions=position.astype(np.float64),
        all_h4_close_times=h4_close_time,
    )


# ── Segment metrics (for A01 era analysis) ────────────────────────────────


@dataclass
class SegmentMetrics:
    """Per-segment metrics for era analysis."""

    name: str
    start_date: str
    end_date: str
    n_bars: int
    sharpe: float           # native H4 domain (ddof=0, sqrt(2190))
    sharpe_common: float    # common: daily UTC, ddof=0, sqrt(365)
    cagr_pct: float
    max_dd_pct: float
    exposure_pct: float
    n_trades: int
    expectancy: float       # mean PnL per trade in segment


def compute_segment_metrics(
    result: PF0Result,
    segment_name: str,
    start_ms: int,
    end_ms: int,
) -> SegmentMetrics:
    """Compute metrics for a time window from PF0 result arrays.

    Uses the full arrays (all_navs, all_h4_close_times, all_positions)
    which include warmup + live bars. The segment boundaries define
    which bars to include.
    """
    assert result.all_navs is not None
    navs = result.all_navs
    pos = result.all_positions
    ct = result.all_h4_close_times
    assert navs is not None and pos is not None and ct is not None

    _z = SegmentMetrics(
        segment_name, _fmt_ms(start_ms), _fmt_ms(end_ms),
        0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0,
    )

    mask = (ct >= start_ms) & (ct <= end_ms)
    seg_navs = navs[mask]
    seg_ct = ct[mask]
    seg_pos = pos[mask]

    if len(seg_navs) < 2:
        return _z

    # H4 returns
    rets = np.diff(seg_navs) / seg_navs[:-1]

    # Native H4 Sharpe (ddof=0, sqrt(2190))
    ann_h4 = math.sqrt(_PERIODS_PER_YEAR)
    sharpe = 0.0
    if len(rets) > 1 and np.std(rets, ddof=0) > 1e-12:
        sharpe = float(np.mean(rets) / np.std(rets, ddof=0) * ann_h4)

    # Common-domain Sharpe: compound H4 returns to daily UTC
    daily_groups: dict[int, list[float]] = {}
    for i, r in enumerate(rets):
        day_ms = (int(seg_ct[i + 1]) // 86_400_000) * 86_400_000
        daily_groups.setdefault(day_ms, []).append(float(r))
    daily_rets = np.array([
        float(np.prod([1.0 + r for r in rs]) - 1.0)
        for rs in daily_groups.values()
    ])
    sharpe_c = 0.0
    if len(daily_rets) > 1 and np.std(daily_rets, ddof=0) > 1e-12:
        sharpe_c = float(
            np.mean(daily_rets) / np.std(daily_rets, ddof=0) * math.sqrt(365)
        )

    # CAGR
    years = (int(seg_ct[-1]) - int(seg_ct[0])) / (365.25 * 24 * 3600 * 1000)
    mult = seg_navs[-1] / seg_navs[0]
    cagr = (pow(mult, 1.0 / years) - 1.0) * 100.0 if years > 0.01 else 0.0

    # MDD
    peak = np.maximum.accumulate(seg_navs)
    dd = 1.0 - seg_navs / peak
    max_dd = float(dd.max()) * 100.0

    # Exposure
    seg_expo_values = []
    for i in range(len(seg_navs)):
        if seg_navs[i] > 1e-12:
            seg_expo_values.append(seg_pos[i])
        else:
            seg_expo_values.append(0.0)
    avg_expo = float(np.mean(seg_expo_values)) * 100.0

    # Trades in this segment
    seg_trades = [
        (ret, pnl)
        for ret, pnl, ts in zip(
            result.trade_returns, result.trade_pnl, result.trade_entry_ts,
        )
        if start_ms <= ts <= end_ms
    ]
    n_trades = len(seg_trades)
    expectancy = float(np.mean([p for _, p in seg_trades])) if seg_trades else 0.0

    return SegmentMetrics(
        name=segment_name,
        start_date=_fmt_ms(start_ms),
        end_date=_fmt_ms(end_ms),
        n_bars=int(np.sum(mask)),
        sharpe=round(sharpe, 4),
        sharpe_common=round(sharpe_c, 4),
        cagr_pct=round(cagr, 2),
        max_dd_pct=round(max_dd, 2),
        exposure_pct=round(avg_expo, 2),
        n_trades=n_trades,
        expectancy=round(expectancy, 2),
    )


def _fmt_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d")


# ── Indicator helpers ─────────────────────────────────────────────────────
# Copied from strategies/vtrend_e5_ema21_d1/strategy.py for self-containment.
# Do NOT import from strategies/ — x40 is self-contained.


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average (standard EMA)."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _robust_atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    cap_q: float,
    cap_lb: int,
    period: int,
) -> np.ndarray:
    """Robust ATR: cap TR at rolling quantile, then Wilder EMA."""
    prev_cl = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_cl), np.abs(low - prev_cl)),
    )

    n = len(tr)
    tr_cap = np.full(n, np.nan)

    for i in range(cap_lb, n):
        q = np.percentile(tr[i - cap_lb:i], cap_q * 100)
        tr_cap[i] = min(tr[i], q)

    ratr = np.full(n, np.nan)
    s = cap_lb
    if s + period <= n:
        ratr[s + period - 1] = np.mean(tr_cap[s:s + period])
        for i in range(s + period, n):
            ratr[i] = (ratr[i - 1] * (period - 1) + tr_cap[i]) / period

    return ratr


def _vdo(
    volume: np.ndarray,
    taker_buy: np.ndarray,
    fast: int,
    slow: int,
) -> np.ndarray:
    """Volume Delta Oscillator: EMA(vdr, fast) - EMA(vdr, slow).

    Requires real taker_buy_base_vol. Raises RuntimeError if missing
    (fail-closed — no OHLC proxy).
    """
    if taker_buy is None or not np.any(taker_buy > 0):
        raise RuntimeError(
            "VDO requires taker_buy_base_vol data. Cannot compute VDO "
            "without real taker flow data."
        )

    n = len(volume)
    taker_sell = volume - taker_buy
    vdr = np.zeros(n)
    mask = volume > 0
    vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]

    return _ema(vdr, fast) - _ema(vdr, slow)


def _map_d1_regime(
    h4_close_time: np.ndarray,
    d1_close: np.ndarray,
    d1_close_time: np.ndarray,
    ema_period: int,
) -> np.ndarray:
    """Map D1 EMA regime filter to H4 bar grid.

    For each H4 bar, finds the most recent D1 bar whose close_time
    is strictly before the H4 bar's close_time (no lookahead).
    Returns boolean array: True = D1 close > D1 EMA (bullish regime).
    """
    n_h4 = len(h4_close_time)
    n_d1 = len(d1_close)

    d1_ema = _ema(d1_close, ema_period)
    d1_bullish = d1_close > d1_ema

    regime_ok = np.zeros(n_h4, dtype=np.bool_)
    d1_idx = 0

    for i in range(n_h4):
        h4_ct = h4_close_time[i]
        while d1_idx + 1 < n_d1 and d1_close_time[d1_idx + 1] < h4_ct:
            d1_idx += 1
        if d1_close_time[d1_idx] < h4_ct:
            regime_ok[i] = d1_bullish[d1_idx]

    return regime_ok
