"""VP1 (VTREND-P1) — Phase 1 performance-dominant leader.

Rebuild from frozen spec v1.1:
  research/x32/resource/06_final_audited_rebuild_spec_v1.1.md

Key structural differences vs E5_ema21D1:
  - Standard Wilder ATR(20) — no quantile capping (E5 uses robust ATR)
  - D1 regime: strict prevday date mapping (H4 date d → D1 date d-1)
  - VDO: per-bar auto path selection + EMA_nan_carry
  - Anomaly bars: volume <= 0 → no entry, no exit, no peak update
  - Parameters: slow=140, fast=35, trail=2.5, d1_ema=28

4 tunable parameters:
  slow_period    -- EMA slow period (default: 140; fast = floor(slow/4))
  trail_mult     -- ATR multiplier for trailing stop (default: 2.5)
  vdo_threshold  -- minimum VDO for entry confirmation (default: 0.0, strict >)
  d1_ema_period  -- D1 EMA period for regime filter (default: 28)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

import numpy as np

from v10.core.types import Fill, MarketState, Signal
from v10.strategies.base import Strategy


@dataclass
class VP1Config:
    # Tunable (4 parameters — matches spec §2)
    slow_period: float = 140.0
    trail_mult: float = 2.5
    vdo_threshold: float = 0.0
    d1_ema_period: int = 28

    # Structural constants (frozen in spec §5)
    vdo_fast: int = 12
    vdo_slow: int = 28
    atr_period: int = 20       # standard Wilder ATR period
    warmup_days: int = 365     # calendar days, no-trade


class VP1Strategy(Strategy):
    def __init__(self, config: VP1Config | None = None) -> None:
        self._config = config or VP1Config()
        self._c = self._config

        # Precomputed indicator arrays (set in on_init)
        self._ema_fast: np.ndarray | None = None
        self._ema_slow: np.ndarray | None = None
        self._atr: np.ndarray | None = None
        self._vdo: np.ndarray | None = None

        # D1 regime filter mapped to H4 index (prevday mapping)
        self._d1_regime_ok: np.ndarray | None = None

        # Anomaly flag per H4 bar
        self._anomaly: np.ndarray | None = None

        # Runtime state
        self._in_position = False
        self._peak_price = 0.0

    def name(self) -> str:
        return "vtrend_vp1"

    # ------------------------------------------------------------------
    # on_init — precompute all indicators (spec §5)
    # ------------------------------------------------------------------

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        n = len(h4_bars)
        if n == 0:
            return

        close = np.array([b.close for b in h4_bars], dtype=np.float64)
        high = np.array([b.high for b in h4_bars], dtype=np.float64)
        low = np.array([b.low for b in h4_bars], dtype=np.float64)
        volume = np.array([b.volume for b in h4_bars], dtype=np.float64)
        taker_buy = np.array(
            [b.taker_buy_base_vol for b in h4_bars], dtype=np.float64,
        )

        slow_p = int(self._c.slow_period)
        fast_p = max(5, slow_p // 4)  # spec §2: fast = max(5, floor(slow/4))

        # §5.1 — EMA fast / slow
        self._ema_fast = _ema(close, fast_p)
        self._ema_slow = _ema(close, slow_p)

        # §5.2 — Standard Wilder ATR(20)
        self._atr = _standard_wilder_atr(high, low, close, self._c.atr_period)

        # §5.3 — VDO with per-bar auto path + EMA_nan_carry
        self._vdo = _vdo_auto(
            close, high, low, volume, taker_buy,
            self._c.vdo_fast, self._c.vdo_slow,
        )

        # §5.4 — D1 regime (prevday mapping)
        self._d1_regime_ok = _d1_prevday_regime(
            h4_bars, d1_bars, self._c.d1_ema_period,
        )

        # §6.4 — Anomaly flag (volume <= 0)
        # Note: full spec also checks num_trades <= 0, but Bar doesn't
        # carry num_trades. For BTCUSDT data this is equivalent.
        self._anomaly = volume <= 0

    # ------------------------------------------------------------------
    # on_bar — state machine (spec §6, §7, §8)
    # ------------------------------------------------------------------

    def on_bar(self, state: MarketState) -> Signal | None:
        i = state.bar_index

        if (self._ema_fast is None or self._atr is None
                or self._vdo is None or self._d1_regime_ok is None
                or i < 1):
            return None

        # §6.4 — anomaly bar: no decisions, no peak update
        if self._anomaly is not None and self._anomaly[i]:
            return None

        ema_f = self._ema_fast[i]
        ema_s = self._ema_slow[i]
        atr_val = self._atr[i]
        vdo_val = self._vdo[i]
        price = state.bar.close

        # §7 condition 5: ema_fast and ema_slow must be finite
        if math.isnan(ema_f) or math.isnan(ema_s):
            return None

        if not self._in_position:
            # ---- ENTRY (spec §7) ----
            # condition 6: VDO must be finite
            if math.isnan(vdo_val):
                return None
            # condition 7: D1 regime true
            regime_ok = bool(self._d1_regime_ok[i])
            # condition 8: ema_fast > ema_slow (strict, == → no entry)
            trend_up = ema_f > ema_s
            # condition 9: VDO > 0.0 (strict, == → no entry)
            vdo_ok = vdo_val > self._c.vdo_threshold

            if trend_up and vdo_ok and regime_ok:
                self._in_position = True
                self._peak_price = price  # §7: peak_seed = close[decision_bar]
                return Signal(
                    target_exposure=1.0,
                    reason="vp1_entry",
                )
        else:
            # ---- IN POSITION: update peak, check exits (spec §8) ----

            # Step 1: update peak price
            self._peak_price = max(self._peak_price, price)

            # Step 2: trailing stop (requires finite ATR)
            if not math.isnan(atr_val):
                trail_stop = self._peak_price - self._c.trail_mult * atr_val
                # §8: close < trail_stop (strict, == → no exit)
                if price < trail_stop:
                    self._in_position = False
                    self._peak_price = 0.0
                    return Signal(
                        target_exposure=0.0,
                        reason="vp1_trailing_stop",
                    )

            # Step 3: trend reversal
            # §8: ema_fast < ema_slow (strict, == → no exit)
            if ema_f < ema_s:
                self._in_position = False
                self._peak_price = 0.0
                return Signal(
                    target_exposure=0.0,
                    reason="vp1_trend_reversal",
                )

        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        pass


# ======================================================================
# Vectorized indicator helpers — faithful to spec v1.1
# ======================================================================

def _ema(series: np.ndarray, period: int) -> np.ndarray:
    """Standard EMA (spec §5.1).

    alpha = 2 / (period + 1)
    ema[0] = series[0]
    ema[i] = alpha * series[i] + (1 - alpha) * ema[i-1]
    """
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _standard_wilder_atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 20,
) -> np.ndarray:
    """Standard Wilder ATR (spec §5.2).

    TR[0] = NaN
    TR[i] = max(H-L, |H-C_{i-1}|, |L-C_{i-1}|)  for i > 0
    ATR[period-1] = nanmean(TR[0:period])
    ATR[i] = (ATR[i-1] * (period-1) + TR[i]) / period  for i >= period
    """
    n = len(high)
    tr = np.full(n, np.nan)
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    atr = np.full(n, np.nan)
    if period <= n:
        # Seed: nanmean of TR[0:period] (TR[0] is NaN, so effectively mean of TR[1:period])
        atr[period - 1] = np.nanmean(tr[:period])
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return atr


def _ema_nan_carry(series: np.ndarray, period: int) -> np.ndarray:
    """EMA with NaN-carry semantics (spec §5.3).

    - Find first finite input index k; ema[k] = input[k]
    - For i > k:
      - if input[i] is finite: ordinary EMA update
      - else: ema[i] = ema[i-1]  (carry forward)
    - If no finite input ever appeared: ema stays NaN
    """
    n = len(series)
    alpha = 2.0 / (period + 1)
    out = np.full(n, np.nan)

    # Find first finite value
    k = -1
    for i in range(n):
        if np.isfinite(series[i]):
            k = i
            break

    if k < 0:
        return out  # all NaN

    out[k] = series[k]
    for i in range(k + 1, n):
        if np.isfinite(series[i]):
            out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
        else:
            out[i] = out[i - 1]

    return out


def _vdo_auto(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    taker_buy: np.ndarray,
    fast: int = 12,
    slow: int = 28,
) -> np.ndarray:
    """VDO with per-bar auto path selection + EMA_nan_carry (spec §5.3).

    Per bar:
      - Primary: if taker_buy finite AND volume > 0:
          vdr = (2 * taker_buy - volume) / volume
      - Fallback: elif high > low:
          vdr = ((close - low) / (high - low)) * 2 - 1
      - Else: vdr = NaN

    VDO = EMA_nan_carry(vdr, fast) - EMA_nan_carry(vdr, slow)
    """
    n = len(close)
    vdr = np.full(n, np.nan)

    for i in range(n):
        # Primary path
        if np.isfinite(taker_buy[i]) and volume[i] > 0:
            vdr[i] = (2.0 * taker_buy[i] - volume[i]) / volume[i]
        # Fallback path
        elif high[i] > low[i]:
            vdr[i] = ((close[i] - low[i]) / (high[i] - low[i])) * 2.0 - 1.0
        # Else: remains NaN

    vdo_fast = _ema_nan_carry(vdr, fast)
    vdo_slow = _ema_nan_carry(vdr, slow)

    # VDO = fast - slow; if either is NaN, result is NaN
    return vdo_fast - vdo_slow


def _d1_prevday_regime(
    h4_bars: list,
    d1_bars: list,
    d1_ema_period: int,
) -> np.ndarray:
    """D1 EMA regime with strict prevday mapping (spec §5.4, §4.2).

    For each H4 bar:
      h4_date = floor_utc_day(h4.open_time)
      d1_key = h4_date - 1 day
      regime = d1_close[d1_key] > d1_ema[d1_key]
      If no D1 row for d1_key: regime = False
    """
    n_h4 = len(h4_bars)
    regime_ok = np.zeros(n_h4, dtype=np.bool_)

    if not d1_bars:
        return regime_ok

    # Compute D1 EMA and regime
    d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
    d1_ema = _ema(d1_close, d1_ema_period)
    d1_regime = d1_close > d1_ema  # bool array

    # Build D1 lookup: UTC date (as days since epoch) → index
    d1_date_to_idx: dict[int, int] = {}
    for j, b in enumerate(d1_bars):
        # floor_utc_day: epoch_ms → days since epoch
        d1_date = b.open_time // 86_400_000
        d1_date_to_idx[d1_date] = j

    # Map each H4 bar to prevday D1
    for i, b in enumerate(h4_bars):
        h4_date = b.open_time // 86_400_000   # floor_utc_day
        d1_key = h4_date - 1                   # prevday
        d1_idx = d1_date_to_idx.get(d1_key)
        if d1_idx is not None:
            regime_ok[i] = d1_regime[d1_idx]
        # else: regime = False (spec §3.6)

    return regime_ok
