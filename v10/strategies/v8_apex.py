"""V8 Apex (VDO Absorption-Momentum) strategy — V10 port.

Long-only, H4 bar frequency.  D1 regime gating with EMA50/200
hysteresis.  VDO (Volume Delta Oscillator) as leading signal.
Exit stack: trailing stop (ATR), fixed stop, emergency DD,
optional structural & HMA cross exits, vol brake.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from enum import Enum

import numpy as np

from v10.core.types import MarketState
from v10.core.types import Signal
from v10.strategies.base import Strategy

# ---------------------------------------------------------------------------
# Regime
# ---------------------------------------------------------------------------


class Regime(str, Enum):
    RISK_ON = "RISK_ON"
    CAUTION = "CAUTION"
    RISK_OFF = "RISK_OFF"


# ---------------------------------------------------------------------------
# Configuration — Apex profile defaults
# ---------------------------------------------------------------------------


@dataclass
class V8ApexConfig:
    """All parameters with Apex-profile defaults."""

    # D1 regime
    d1_ema_fast: int = 50
    d1_ema_slow: int = 200
    d1_regime_confirm_bars: int = 2
    d1_regime_off_bars: int = 4
    regime_exit_immediate: bool = False

    # VDO
    vdr_fast_period: int = 12
    vdr_slow_period: int = 28
    vdo_entry_threshold: float = 0.004
    vdo_scale: float = 0.016

    # Momentum
    hma_period: int = 55
    roc_period: int = 8
    accel_smooth_period: int = 3

    # Volatility
    atr_fast_period: int = 14
    atr_slow_period: int = 50
    compression_ratio: float = 0.75

    # RSI
    rsi_period: int = 14
    rsi_overbought: float = 75.0
    rsi_oversold: float = 30.0

    # Entry sizing
    max_total_exposure: float = 1.0
    target_vol_annual: float = 0.85
    max_add_per_bar: float = 0.35
    entry_aggression: float = 0.85
    entry_cooldown_bars: int = 3
    compression_boost: float = 1.0
    caution_mult: float = 0.50
    min_target_to_add: float = 0.05

    # Exit
    exit_cooldown_bars: int = 3
    enable_structural_exit: bool = False
    structural_exit_bars: int = 5
    exit_on_hma_cross: bool = False
    hma_exit_bars: int = 2

    # Trailing stop
    enable_trail: bool = True
    trail_atr_mult: float = 3.5
    trail_activate_pct: float = 0.05
    trail_tighten_mult: float = 2.5
    trail_tighten_profit_pct: float = 0.25

    # Fixed stop
    enable_fixed_stop: bool = True
    fixed_stop_pct: float = 0.15

    # Emergency DD
    emergency_dd_pct: float = 0.28

    # Overlay A: post-emergency-DD cooldown (H4 bars, 0 = disabled)
    cooldown_after_emergency_dd_bars: int = 12

    # Overlay A v2: Escalating cooldown (replaces v1 when enabled)
    escalating_cooldown: bool = False  # True = v2, False = v1
    short_cooldown_bars: int = 3  # after isolated ED exit
    long_cooldown_bars: int = 12  # after cascade detected
    escalating_lookback_bars: int = 24  # window to count ED exits (H4 bars)
    cascade_trigger_count: int = 2  # ED exits needed for long cooldown

    # Vol brake
    enable_vol_brake: bool = True
    vol_brake_atr_ratio: float = 0.035
    vol_brake_mult: float = 0.40

    # DD adaptive
    enable_dd_adaptive: bool = False
    dd_adaptive_start: float = 0.16
    dd_adaptive_floor: float = 0.35

    # Equity Brake overlay (Proposal B)
    enable_equity_brake: bool = False
    brake_window_bars: int = 90
    brake_dd_threshold: float | None = None  # None → auto = emergency_dd_pct / 2

    # Compatibility flags
    rsi_method: str = "ewm_span"  # "ewm_span" | "wilder"
    emergency_ref: str = "pre_cost_legacy"  # "pre_cost_legacy" | "post_cost" | "peak"


# ---------------------------------------------------------------------------
# Indicator helpers (vectorized, numpy)
# ---------------------------------------------------------------------------


def _ema(a: np.ndarray, p: int) -> np.ndarray:
    alpha = 2.0 / (p + 1)
    out = np.empty(len(a), dtype=np.float64)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = alpha * a[i] + (1 - alpha) * out[i - 1]
    return out


def _ema_wilder(a: np.ndarray, p: int) -> np.ndarray:
    """EMA with Wilder's smoothing: alpha = 1/p (more smoothing than standard)."""
    alpha = 1.0 / p
    out = np.empty(len(a), dtype=np.float64)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = alpha * a[i] + (1 - alpha) * out[i - 1]
    return out


def _wma(a: np.ndarray, p: int) -> np.ndarray:
    w = np.arange(1, p + 1, dtype=np.float64)
    ws = w.sum()
    out = np.full(len(a), np.nan)
    for i in range(p - 1, len(a)):
        out[i] = np.dot(a[i - p + 1 : i + 1], w) / ws
    return out


def _hma(a: np.ndarray, p: int) -> np.ndarray:
    half = max(p // 2, 1)
    sq = max(int(math.sqrt(p)), 1)
    return _wma(2.0 * _wma(a, half) - _wma(a, p), sq)


def _rsi(c: np.ndarray, p: int, method: str = "ewm_span") -> np.ndarray:
    delta = np.diff(c, prepend=c[0])
    g = np.where(delta > 0, delta, 0.0)
    l_ = np.where(delta < 0, -delta, 0.0)
    smoother = _ema_wilder if method == "wilder" else _ema
    ag, al = smoother(g, p), smoother(l_, p)
    rs = np.full_like(ag, 100.0)
    np.divide(ag, al, out=rs, where=al > 1e-12)
    return 100.0 - 100.0 / (1.0 + rs)


def _atr(h: np.ndarray, lo: np.ndarray, c: np.ndarray, p: int) -> np.ndarray:
    pc = np.roll(c, 1)
    pc[0] = c[0]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    return _ema(tr, p)


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------


class V8ApexStrategy(Strategy):
    """V8 Apex — VDO absorption-momentum, long-only 0..1 exposure."""

    def __init__(self, cfg: V8ApexConfig | None = None) -> None:
        self.cfg = cfg or V8ApexConfig()
        # Derive brake_dd_threshold if not explicitly set
        if self.cfg.brake_dd_threshold is None:
            self.cfg.brake_dd_threshold = self.cfg.emergency_dd_pct / 2
        # Equity brake state (Proposal B)
        self._nav_ring_buffer: deque[float] = deque(maxlen=self.cfg.brake_window_bars)
        self._equity_brake_active: bool = False
        # Tracking state
        self._peak_price: float = 0.0
        self._peak_profit: float = 0.0
        self._last_add_idx: int = -999
        self._last_exit_idx: int = -999
        self._equity_peak: float = 0.0
        self._was_in_position: bool = False
        self._structural_below: int = 0
        self._hma_below: int = 0
        self._vdo_source: str = "taker_buy"  # always taker; fallback removed
        self._position_nav_peak: float = 0.0
        # Overlay A: post-emergency-DD cooldown state
        self._emergency_dd_cooldown_remaining: int = 0
        self._last_exit_reason: str = ""
        # Overlay A v2: escalating cooldown state
        self._cascade_ed_count: int = 0
        self._last_emergency_dd_bar_idx: int = -1
        self._active_cooldown_type: str = ""
        # Pre-computed arrays (set in on_init)
        self._h4_vdo = np.array([])
        self._h4_hma = np.array([])
        self._h4_rsi = np.array([])
        self._h4_atr_f = np.array([])
        self._h4_atr_s = np.array([])
        self._h4_accel = np.array([])
        self._h4_ema200 = np.array([])
        self._d1_regime = np.array([])
        self._d1_vol_ann = np.array([])

    # -- on_init: pre-compute all indicators --------------------------------

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        c = self.cfg
        if not h4_bars:
            return
        cl = np.array([b.close for b in h4_bars], dtype=np.float64)
        hi = np.array([b.high for b in h4_bars], dtype=np.float64)
        lo = np.array([b.low for b in h4_bars], dtype=np.float64)
        tbv = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)
        vol = np.array([b.volume for b in h4_bars], dtype=np.float64)

        self._h4_hma = _hma(cl, c.hma_period)
        self._h4_rsi = _rsi(cl, c.rsi_period, method=c.rsi_method)
        self._h4_atr_f = _atr(hi, lo, cl, c.atr_fast_period)
        self._h4_atr_s = _atr(hi, lo, cl, c.atr_slow_period)
        self._h4_ema200 = _ema(cl, 200)

        # VDO — requires real taker_buy data (OHLC fallback removed)
        if np.sum(tbv) < 1e-10:
            raise RuntimeError(
                "VDO requires taker_buy_base_vol data. Cannot compute VDO "
                "without real taker flow data — OHLC fallback has been removed "
                "to prevent semantic confusion (price-location != order-flow)."
            )
        sv = np.where(vol > 0, vol, 1.0)
        vdr = tbv / sv
        self._h4_vdo = _ema(vdr, c.vdr_fast_period) - _ema(vdr, c.vdr_slow_period)

        # Acceleration: smoothed diff(ROC)
        prev = np.roll(cl, c.roc_period)
        prev[: c.roc_period] = cl[: c.roc_period]
        roc = np.where(prev > 0, (cl - prev) / prev, 0.0)
        self._h4_accel = _ema(np.diff(roc, prepend=0.0), c.accel_smooth_period)

        # D1 indicators
        if d1_bars:
            d1c = np.array([b.close for b in d1_bars], dtype=np.float64)
            ef = _ema(d1c, c.d1_ema_fast)
            es = _ema(d1c, c.d1_ema_slow)
            self._d1_regime = self._compute_regime(d1c, ef, es)
            lr = np.diff(np.log(np.maximum(d1c, 1e-10)), prepend=0.0)
            lr[0] = 0.0
            em, em2 = _ema(lr, 30), _ema(lr**2, 30)
            sig = np.sqrt(np.maximum(em2 - em**2, 0.0))
            self._d1_vol_ann = np.clip(sig * math.sqrt(365), 0.10, 3.00)

    # -- D1 regime state machine --------------------------------------------

    def _compute_regime(
        self,
        close: np.ndarray,
        ema_f: np.ndarray,
        ema_s: np.ndarray,
    ) -> np.ndarray:
        """Regime with hysteresis: confirm_bars above → ON, off_bars below → OFF."""
        c = self.cfg
        n = len(close)
        out = np.empty(n, dtype=object)
        above = below = 0
        cur = Regime.RISK_OFF
        for i in range(n):
            if close[i] > ema_s[i]:
                above = min(above + 1, c.d1_regime_confirm_bars + 2)
                below = 0
            else:
                below = min(below + 1, c.d1_regime_off_bars + 2)
                above = 0
            if below >= c.d1_regime_off_bars:
                cur = Regime.RISK_OFF
            elif above >= c.d1_regime_confirm_bars:
                cur = Regime.RISK_ON if ema_f[i] > ema_s[i] else Regime.CAUTION
            out[i] = cur
        return out

    # -- on_bar: main decision logic ----------------------------------------

    def on_bar(self, state: MarketState) -> Signal | None:
        idx = state.bar_index
        mid = state.bar.close
        in_pos = state.btc_qty > 1e-8

        # Equity brake: update NAV ring buffer and brake state (every bar)
        if self.cfg.enable_equity_brake:
            self._nav_ring_buffer.append(state.nav)
            peak = max(self._nav_ring_buffer)
            rolling_dd = 1.0 - state.nav / peak if peak > 0 else 0.0
            self._equity_brake_active = rolling_dd >= self.cfg.brake_dd_threshold

        # Detect position transitions
        just_closed = self._was_in_position and not in_pos
        just_opened = not self._was_in_position and in_pos

        if just_closed:
            self._last_exit_idx = idx
            self._peak_price = self._peak_profit = 0.0
            self._position_nav_peak = 0.0
            self._structural_below = self._hma_below = 0
            # Overlay A: activate cooldown if last exit was emergency_dd
            if self._last_exit_reason == "emergency_dd":
                if self.cfg.escalating_cooldown:
                    # V2: escalating cooldown
                    if (
                        self._last_emergency_dd_bar_idx >= 0
                        and idx - self._last_emergency_dd_bar_idx <= self.cfg.escalating_lookback_bars
                    ):
                        self._cascade_ed_count += 1
                    else:
                        self._cascade_ed_count = 1
                    self._last_emergency_dd_bar_idx = idx
                    if self._cascade_ed_count >= self.cfg.cascade_trigger_count:
                        self._emergency_dd_cooldown_remaining = self.cfg.long_cooldown_bars
                        self._active_cooldown_type = "long_cooldown"
                        self._cascade_ed_count = 0  # reset after trigger
                    else:
                        self._emergency_dd_cooldown_remaining = self.cfg.short_cooldown_bars
                        self._active_cooldown_type = "short_cooldown"
                else:
                    # V1: flat cooldown
                    self._emergency_dd_cooldown_remaining = self.cfg.cooldown_after_emergency_dd_bars
        if just_opened:
            self._position_nav_peak = state.nav
            self._last_exit_reason = ""
        self._was_in_position = in_pos

        # Overlay A: decrement cooldown counter every bar
        if self._emergency_dd_cooldown_remaining > 0:
            self._emergency_dd_cooldown_remaining -= 1

        # Overlay A v2: reset cascade counter if lookback window expired
        if (
            self.cfg.escalating_cooldown
            and self._cascade_ed_count > 0
            and self._last_emergency_dd_bar_idx >= 0
            and idx - self._last_emergency_dd_bar_idx > self.cfg.escalating_lookback_bars
        ):
            self._cascade_ed_count = 0

        # Update peak tracking
        if in_pos and state.entry_price_avg > 0:
            self._peak_price = max(self._peak_price, mid)
            p = (mid - state.entry_price_avg) / state.entry_price_avg
            self._peak_profit = max(self._peak_profit, p)
        if in_pos:
            self._position_nav_peak = max(self._position_nav_peak, state.nav)
        self._equity_peak = max(self._equity_peak, state.nav)

        # Resolve D1 regime
        d1i = state.d1_index
        regime = self._d1_regime[d1i] if 0 <= d1i < len(self._d1_regime) else Regime.RISK_OFF

        if in_pos:
            sig = self._check_exit(state, idx, mid, regime)
            if sig is not None:
                self._last_exit_reason = sig.reason
                return sig
        return self._check_entry(state, idx, mid, regime)

    # -- exits ---------------------------------------------------------------

    def _check_exit(
        self,
        state: MarketState,
        idx: int,
        mid: float,
        regime: Regime,
    ) -> Signal | None:
        c = self.cfg

        # 1. Emergency DD — reference NAV depends on emergency_ref flag
        if c.emergency_ref == "peak":
            ref_nav = self._position_nav_peak
        else:  # "pre_cost_legacy" or "post_cost" (handled in Portfolio)
            ref_nav = state.position_entry_nav
        if ref_nav > 0:
            dd = 1.0 - state.nav / ref_nav
            if dd >= c.emergency_dd_pct:
                return Signal(target_exposure=0.0, reason="emergency_dd")

        # 2. Regime exit (optional, disabled by default)
        if c.regime_exit_immediate and regime == Regime.RISK_OFF:
            return Signal(target_exposure=0.0, reason="regime_off")

        # 3a. Trailing stop (after profit threshold)
        atr_val = self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
        if c.enable_trail and self._peak_profit >= c.trail_activate_pct:
            mult = c.trail_tighten_mult if self._peak_profit >= c.trail_tighten_profit_pct else c.trail_atr_mult
            stop = self._peak_price - mult * atr_val
            if mid <= stop:
                return Signal(target_exposure=0.0, reason="trailing_stop")

        # 3b. Fixed stop (safety net before trailing activates)
        elif c.enable_fixed_stop and state.entry_price_avg > 0:
            stop = state.entry_price_avg * (1.0 - c.fixed_stop_pct)
            if mid <= stop:
                return Signal(target_exposure=0.0, reason="fixed_stop")

        # 4. Structural exit (disabled by default)
        if c.enable_structural_exit and idx < len(self._h4_ema200):
            if mid < self._h4_ema200[idx]:
                self._structural_below += 1
            else:
                self._structural_below = 0
            if self._structural_below >= c.structural_exit_bars:
                return Signal(target_exposure=0.0, reason="structural_breakdown")

        # 5. HMA cross exit (disabled by default)
        if c.exit_on_hma_cross and idx < len(self._h4_hma):
            hma_v = self._h4_hma[idx]
            vdo_v = self._h4_vdo[idx] if idx < len(self._h4_vdo) else 0.0
            if not np.isnan(hma_v) and mid < hma_v and vdo_v < 0:
                self._hma_below += 1
            else:
                self._hma_below = 0
            if self._hma_below >= c.hma_exit_bars:
                return Signal(target_exposure=0.0, reason="hma_breakdown")

        return None

    # -- entries -------------------------------------------------------------

    def _check_entry(
        self,
        state: MarketState,
        idx: int,
        mid: float,
        regime: Regime,
    ) -> Signal | None:
        c = self.cfg

        # Gate 0: Overlay A — post-emergency-DD cooldown
        if self._emergency_dd_cooldown_remaining > 0:
            return None

        # Gate 0.5: Equity Brake — block adds (not initial entries)
        if c.enable_equity_brake and state.exposure > 0.01 and self._equity_brake_active:
            return None

        # Gate 1: Regime
        if regime == Regime.RISK_OFF:
            return None
        # Gate 2: Cooldowns
        if idx - self._last_add_idx < c.entry_cooldown_bars:
            return None
        if idx - self._last_exit_idx < c.exit_cooldown_bars:
            return None

        # Gate 3: VDO threshold
        vdo = self._h4_vdo[idx] if idx < len(self._h4_vdo) else 0.0
        if vdo <= c.vdo_entry_threshold:
            return None

        # Gate 4: Trend confirmation (above HMA OR oversold)
        hma_v = self._h4_hma[idx] if idx < len(self._h4_hma) else mid
        rsi_v = self._h4_rsi[idx] if idx < len(self._h4_rsi) else 50.0
        above_hma = not np.isnan(hma_v) and mid > hma_v
        oversold = rsi_v < c.rsi_oversold
        if not above_hma and not oversold:
            return None

        # Target exposure (vol-sized)
        d1i = state.d1_index
        va = self._d1_vol_ann[d1i] if 0 <= d1i < len(self._d1_vol_ann) else 1.0
        base = min(c.max_total_exposure, c.target_vol_annual / va)
        if regime == Regime.CAUTION:
            base *= c.caution_mult

        # Vol brake
        if c.enable_vol_brake and mid > 0:
            atr_f = self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
            if atr_f / mid > c.vol_brake_atr_ratio:
                base *= c.vol_brake_mult

        # DD adaptive (disabled for apex)
        if c.enable_dd_adaptive and self._equity_peak > 0 and state.nav < self._equity_peak:
            dd = 1.0 - state.nav / self._equity_peak
            if dd > c.dd_adaptive_start:
                prog = min(
                    (dd - c.dd_adaptive_start) / max(c.emergency_dd_pct - c.dd_adaptive_start, 0.01),
                    1.0,
                )
                base *= 1.0 - prog * (1.0 - c.dd_adaptive_floor)

        base = min(base, c.max_total_exposure)
        gap = base - state.exposure
        if gap < c.min_target_to_add:
            return None

        # Entry sizing
        vc = max(0.3, min(2.0, vdo / max(c.vdo_scale, 0.001)))
        sz = gap * c.entry_aggression * vc

        accel = self._h4_accel[idx] if idx < len(self._h4_accel) else 0.0
        accel_pos = accel >= 0.0
        if accel_pos:
            sz *= 1.15

        atr_f = self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
        atr_s = self._h4_atr_s[idx] if idx < len(self._h4_atr_s) else mid * 0.02
        is_comp = atr_s > 0 and (atr_f / atr_s) < c.compression_ratio
        if is_comp:
            sz *= c.compression_boost

        if rsi_v > c.rsi_overbought:
            sz *= 0.50
        elif oversold:
            sz *= 1.30
        if regime == Regime.CAUTION:
            sz *= c.caution_mult

        sz = min(sz, c.max_add_per_bar, gap)
        if sz < 0.01:
            return None

        # Entry reason
        if is_comp and vdo > c.vdo_scale:
            reason = "vdo_compression"
        elif oversold:
            reason = "vdo_dip_buy"
        elif above_hma and accel_pos:
            reason = "vdo_trend_accel"
        else:
            reason = "vdo_trend"

        self._last_add_idx = idx
        return Signal(
            target_exposure=min(state.exposure + sz, c.max_total_exposure),
            reason=reason,
        )

    def name(self) -> str:
        return "V8Apex[vdo=taker_buy]"
