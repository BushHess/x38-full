"""E5_ema21D1 (vtrend_e5_ema21_d1) — E5 (robust ATR trail) + D1 EMA(21) regime filter.

Combines:
  - E5 entry/exit: EMA crossover + VDO + robust ATR trailing stop + EMA cross-down
  - D1 regime filter: entry only when D1 close > D1 EMA(d1_ema_period)

Parameters (tunable):
  slow_period    -- EMA slow period (fast = slow // 4)
  trail_mult     -- robust ATR multiplier for trailing stop
  vdo_threshold  -- minimum VDO for entry confirmation
  d1_ema_period  -- EMA period on D1 bars (default: 21)

Robust ATR parameters (structural):
  ratr_cap_q     -- 0.90 (quantile for TR cap)
  ratr_cap_lb    -- 100 (lookback for rolling quantile)
  ratr_period    -- 20 (Wilder EMA period for robust ATR)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy


@dataclass
class VTrendE5Ema21D1Config:
    # Tunable (4 parameters)
    slow_period: float = 120.0
    trail_mult: float = 3.0
    vdo_threshold: float = 0.0
    d1_ema_period: int = 21

    # Structural constants
    vdo_fast: int = 12
    vdo_slow: int = 28

    # Robust ATR parameters
    ratr_cap_q: float = 0.90
    ratr_cap_lb: int = 100
    ratr_period: int = 20

    # Regime monitor (optional operational guard)
    enable_regime_monitor: bool = False


class VTrendE5Ema21D1Strategy(Strategy):
    def __init__(
        self,
        config: VTrendE5Ema21D1Config | None = None,
        monitor_alerts: np.ndarray | None = None,
    ) -> None:
        self._config = config or VTrendE5Ema21D1Config()
        self._c = self._config
        self._external_monitor_alerts = monitor_alerts

        # Precomputed indicator arrays
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._ratr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # D1 regime filter mapped to H4 index
        self._d1_regime_ok: np.ndarray | None = None

        # Regime monitor alerts mapped to H4 index (None = disabled)
        self._h4_monitor_alerts: np.ndarray | None = None
        self._monitor_exits: int = 0

        # Runtime state
        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return "vtrend_e5_ema21_d1"

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

        # Compute D1 regime filter and map to H4 bar grid
        self._d1_regime_ok = self._compute_d1_regime(h4_bars, d1_bars)

        # Regime monitor: use externally provided alerts or compute internally
        if self._external_monitor_alerts is not None:
            self._h4_monitor_alerts = self._external_monitor_alerts
        elif self._c.enable_regime_monitor:
            from monitoring.regime_monitor import compute_regime, map_d1_alert_to_h4
            d1_close_arr = np.array([b.close for b in d1_bars], dtype=np.float64)
            d1_ct_arr = np.array([b.close_time for b in d1_bars], dtype=np.int64)
            h4_ct_arr = np.array([b.close_time for b in h4_bars], dtype=np.int64)
            regime = compute_regime(d1_close_arr)
            self._h4_monitor_alerts = map_d1_alert_to_h4(
                regime["alerts"], d1_ct_arr, h4_ct_arr,
            )

    def _compute_d1_regime(self, h4_bars: list, d1_bars: list) -> np.ndarray:
        """Compute D1 EMA regime and map to H4 bar indices."""
        n_h4 = len(h4_bars)
        regime_ok = np.zeros(n_h4, dtype=np.bool_)

        if not d1_bars:
            return regime_ok

        d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
        d1_ema = _ema(d1_close, self._c.d1_ema_period)
        d1_close_times = [b.close_time for b in d1_bars]

        # For each D1 bar, determine regime_ok = close > EMA
        d1_regime = d1_close > d1_ema

        # Map D1 regime to H4 bars: each H4 bar gets the D1 regime
        # of the most recent completed D1 bar
        d1_idx = 0
        n_d1 = len(d1_bars)
        for i in range(n_h4):
            h4_ct = h4_bars[i].close_time
            # Advance D1 index to the last D1 bar completed strictly before H4 close
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

        monitor_red = (
            self._h4_monitor_alerts is not None
            and self._h4_monitor_alerts[i] == 2
        )

        if not self._in_position:
            # ENTRY: trend up AND VDO confirms AND D1 regime filter AND not RED
            regime_ok = bool(self._d1_regime_ok[i])
            if trend_up and vdo_val > self._c.vdo_threshold and regime_ok and not monitor_red:
                self._in_position = True
                self._peak_price = price
                return Signal(target_exposure=1.0, reason="vtrend_e5_ema21_d1_entry")
        else:
            self._peak_price = max(self._peak_price, price)

            # EXIT: monitor forced exit (RED while in position)
            if monitor_red:
                self._in_position = False
                self._peak_price = 0.0
                self._monitor_exits += 1
                return Signal(target_exposure=0.0, reason="vtrend_e5_ema21_d1_monitor_exit")

            # EXIT: robust-ATR trailing stop OR trend reversal
            trail_stop = self._peak_price - self._c.trail_mult * ratr_val
            if price < trail_stop:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtrend_e5_ema21_d1_trail_stop")

            if trend_down:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(target_exposure=0.0, reason="vtrend_e5_ema21_d1_trend_exit")

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
