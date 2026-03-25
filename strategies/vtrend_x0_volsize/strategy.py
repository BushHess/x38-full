"""VTREND-X0-VOLSIZE -- E0_ema21D1 with E5 exit + frozen entry-time vol sizing.

Identical entry/exit TIMING to vtrend_x0_e5exit (≈ E5_ema21D1),
but entry position size is scaled by realized volatility at entry time.

Entry (when flat, timing identical to vtrend_x0_e5exit):
  1. D1 regime: last completed D1 close > EMA(d1_ema_period) on D1
  2. EMA crossover: ema_fast(H4) > ema_slow(H4)
  3. VDO confirmation: vdo > vdo_threshold
  => weight = target_vol / max(realized_vol, vol_floor), clipped [0, 1]
  => if realized_vol is NaN: weight = 1.0 (vtrend_x0_e5exit fallback)
  => target_exposure = weight

Exit (when long, identical to vtrend_x0_e5exit):
  1. Trail stop: close < peak_price - trail_mult * robust_ATR
  2. Trend reversal: ema_fast(H4) < ema_slow(H4)

Weight is FROZEN from entry to exit — no rebalance.

New parameters (3):
  target_vol    -- annualized vol target (default 0.15, from SM)
  vol_lookback  -- lookback for realized vol (default 120, from SM)
  vol_floor     -- minimum realized vol floor (default 0.08, from LATCH)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy

STRATEGY_ID = "vtrend_x0_volsize"

BARS_PER_YEAR_4H = 365.0 * 6.0  # 2190.0


@dataclass
class VTrendX0VolsizeConfig:
    # Tunable (4 parameters, same as vtrend_x0_e5exit)
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21

    # Structural constants
    vdo_fast: int = 12
    vdo_slow: int = 28

    # Robust ATR parameters (from E5)
    ratr_cap_q: float = 0.90
    ratr_cap_lb: int = 100
    ratr_period: int = 20

    # Vol-sizing parameters (NEW in vtrend_x0_volsize)
    target_vol: float = 0.15
    vol_lookback: int = 120
    vol_floor: float = 0.08


class VTrendX0VolsizeStrategy(Strategy):
    def __init__(self, config: VTrendX0VolsizeConfig | None = None) -> None:
        self._config = config or VTrendX0VolsizeConfig()
        self._c = self._config

        # Precomputed indicator arrays
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._ratr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None
        self._rv: np.ndarray | None = None

        # D1 regime filter mapped to H4 index
        self._d1_regime_ok: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return STRATEGY_ID

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        taker_buy = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)

        slow_p = int(self._c.slow_period)
        fast_p = max(5, slow_p // 4)

        self._ema_fast = _ema(close, fast_p)
        self._ema_slow = _ema(close, slow_p)
        self._ratr = _robust_atr(
            high, low, close,
            cap_q=self._c.ratr_cap_q,
            cap_lb=self._c.ratr_cap_lb,
            period=self._c.ratr_period,
        )
        self._vdo = _vdo(close, high, low, volume, taker_buy,
                         self._c.vdo_fast, self._c.vdo_slow)

        # NEW: realized volatility for position sizing
        self._rv = _realized_vol(close, self._c.vol_lookback, BARS_PER_YEAR_4H)

        # Compute D1 regime filter and map to H4 bar grid
        self._d1_regime_ok = self._compute_d1_regime(h4_bars, d1_bars)

    def _compute_d1_regime(self, h4_bars: list, d1_bars: list) -> np.ndarray:
        """Compute D1 EMA regime and map to H4 bar indices.

        Uses only completed D1 bars -- no lookahead.
        """
        n_h4 = len(h4_bars)
        regime_ok = np.zeros(n_h4, dtype=np.bool_)

        if not d1_bars:
            return regime_ok

        d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
        d1_ema = _ema(d1_close, self._c.d1_ema_period)
        d1_close_times = [b.close_time for b in d1_bars]

        d1_regime = d1_close > d1_ema

        d1_idx = 0
        n_d1 = len(d1_bars)
        for i in range(n_h4):
            h4_ct = h4_bars[i].close_time
            while d1_idx + 1 < n_d1 and d1_close_times[d1_idx + 1] < h4_ct:
                d1_idx += 1
            if d1_close_times[d1_idx] < h4_ct:
                regime_ok[i] = d1_regime[d1_idx]

        return regime_ok

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._ratr is None or
                self._vdo is None or self._d1_regime_ok is None or i < 1):
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        ratr_val = self._ratr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        if math.isnan(ratr_val) or math.isnan(ema_f) or math.isnan(ema_s):
            return None

        trend_up = ema_f > ema_s
        trend_down = ema_f < ema_s

        if not self._in_position:
            # ENTRY: trend up AND VDO confirms AND D1 regime filter
            # (timing identical to vtrend_x0_e5exit)
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok:
                # Compute vol-sized weight (NEW in vtrend_x0_volsize)
                rv_val = self._rv[i] if self._rv is not None else float('nan')
                if math.isnan(rv_val):
                    weight = 1.0  # fallback: vtrend_x0_e5exit behavior
                else:
                    weight = self._c.target_vol / max(rv_val, self._c.vol_floor)
                    weight = max(0.0, min(1.0, weight))

                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=weight, reason="x0_entry")
        else:
            self._peak_price = max(self._peak_price, price)

            # EXIT: robust-ATR trailing stop OR trend reversal
            # (identical to vtrend_x0_e5exit)
            trail_stop = self._peak_price - self._c.trail_mult * ratr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x0_trail_stop")

            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="x0_trend_exit")

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


# -- Vectorized indicator helpers -------------------------------------------

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _robust_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                cap_q: float = 0.90, cap_lb: int = 100,
                period: int = 20) -> np.ndarray:
    """Robust ATR: cap TR at rolling quantile, then Wilder EMA.

    - TR_cap = min(TR, Q(cap_q) of prior cap_lb bars of TR)
    - rATR = WilderEMA(TR_cap, period)
    """
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


def _vdo(close: np.ndarray, high: np.ndarray, low: np.ndarray,
         volume: np.ndarray, taker_buy: np.ndarray,
         fast: int, slow: int) -> np.ndarray:
    """Volume Delta Oscillator: EMA(vdr, fast) - EMA(vdr, slow).

    Requires real taker_buy data.  Raises RuntimeError if taker data is
    missing or all-zero — VDO must always represent taker-imbalance,
    never an OHLC price-location proxy.
    """
    n = len(close)
    has_taker = taker_buy is not None and np.any(taker_buy > 0)

    if not has_taker:
        raise RuntimeError(
            "VDO requires taker_buy_base_vol data. Cannot compute VDO "
            "without real taker flow data — OHLC fallback has been removed "
            "to prevent semantic confusion (price-location != order-flow)."
        )

    taker_sell = volume - taker_buy
    vdr = np.zeros(n)
    mask = volume > 0
    vdr[mask] = (taker_buy[mask] - taker_sell[mask]) / volume[mask]

    return _ema(vdr, fast) - _ema(vdr, slow)


def _realized_vol(close: np.ndarray, lookback: int,
                  bars_per_year: float) -> np.ndarray:
    """Rolling realized volatility (annualized).

    Population std(ddof=0) of log returns over lookback window,
    multiplied by sqrt(bars_per_year) for annualization.
    Copied from SM/LATCH _realized_vol (identical formula).
    """
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    lr = np.full(n, np.nan, dtype=np.float64)
    ratio = np.full(n - 1, np.nan, dtype=np.float64)
    mask = close[:-1] > 0.0
    np.divide(close[1:], close[:-1], out=ratio, where=mask)
    np.log(ratio, out=ratio, where=np.isfinite(ratio) & (ratio > 0.0))
    lr[1:] = ratio
    ann_factor = math.sqrt(bars_per_year)
    for i in range(lookback, n):
        window = lr[i - lookback + 1:i + 1]
        if np.all(np.isfinite(window)):
            out[i] = float(np.std(window, ddof=0)) * ann_factor
    return out
