"""V11 Hybrid — Momentum + Mean-Reversion + Macro Cycle strategy.

Extends V8 Apex (VDO absorption-momentum) with three configurable layers:
  A. Mean-Reversion Defensive — D1 RSI extreme + price-to-MA200 distance gating
  B. Macro Cycle Phase — early/mid/late bull detection, per-phase adjustments
  C. ADX Trend Strength — entry gating and sizing based on trend strength

All layers default to disabled (enable_* = False), making V11 with no
overrides produce identical results to V10 V8 Apex.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from v10.core.types import MarketState, Signal
from v10.strategies.base import Strategy
from v10.strategies.v8_apex import V8ApexConfig


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Regime(str, Enum):
    RISK_ON = "RISK_ON"
    CAUTION = "CAUTION"
    RISK_OFF = "RISK_OFF"


class CyclePhase(str, Enum):
    EARLY_BULL = "EARLY_BULL"
    MID_BULL = "MID_BULL"
    LATE_BULL = "LATE_BULL"
    BEAR = "BEAR"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class V11HybridConfig(V8ApexConfig):
    """V8 Apex core + MR defensive + cycle phase + ADX gating."""

    # ── Feature A: Mean-Reversion Defensive ─────────────────────────
    enable_mr_defensive: bool = False

    # D1 RSI extreme detection
    d1_rsi_period: int = 14
    d1_rsi_extreme_high: float = 80.0       # sizing reduction starts
    d1_rsi_entry_block: float = 85.0        # hard entry block
    d1_rsi_exit_trigger: float = 88.0       # partial exit trigger
    d1_rsi_exit_fraction: float = 0.50      # fraction to exit

    # Price-to-MA200 distance gate
    ma200_dist_reduce: float = 0.40         # price/ema200 > 1.40 → reduce
    ma200_dist_block: float = 0.60          # price/ema200 > 1.60 → block
    ma200_dist_floor: float = 0.30          # min sizing multiplier

    # MR trailing override
    mr_trail_tighten_mult: float = 2.0      # tighter trail in MR extreme

    # ── Feature B: Macro Cycle Phase Detection ──────────────────────
    enable_cycle_phase: bool = False

    # Phase classification thresholds
    cycle_early_max_dist: float = 0.15      # EARLY_BULL: dist < 15%
    cycle_late_min_dist: float = 0.40       # LATE_BULL: dist > 40%
    cycle_late_rsi_min: float = 70.0        # + RSI > 70
    cycle_hysteresis_bars: int = 5          # bars to confirm transition

    # Per-phase adjustments
    cycle_early_aggression: float = 1.20    # entry aggression in early bull
    cycle_early_trail_mult: float = 4.0     # wider trail (don't cut winners)
    cycle_late_aggression: float = 0.60     # reduced in late bull
    cycle_late_trail_mult: float = 2.5      # tighter trail (protect gains)
    cycle_late_max_exposure: float = 0.70   # cap exposure in late bull

    # ── Feature C: ADX Trend Strength Gating ────────────────────────
    enable_adx_gating: bool = False

    adx_period: int = 14
    adx_source: str = "d1"                  # "d1" or "h4"
    adx_min_trend: float = 20.0             # block entry below this
    adx_strong_trend: float = 30.0          # boost sizing above this
    adx_weak_sizing_mult: float = 0.40      # sizing when ADX 20-30
    adx_strong_sizing_mult: float = 1.15    # sizing when ADX > 30

    # ── Overlay 1: Late-Bull Pyramid Ban + Extra Trail ────────────────
    enable_overlay_pyramid_ban: bool = False
    ov1_block_add_in_late: bool = True      # block new adds in LATE_BULL
    ov1_late_trail_mult: float = 2.0        # extra-tight trail in LATE_BULL

    # ── Overlay 2: Position Peak-to-Trough Stop ──────────────────────
    enable_overlay_peak_dd_stop: bool = False
    ov2_max_pos_dd_pct: float = 0.08        # exit if position DD > 8%
    ov2_max_pos_dd_atr: float = 3.0         # or if DD > 3*ATR from peak
    ov2_use_pct: bool = True                # percentage-based trigger
    ov2_use_atr: bool = True                # ATR-based trigger

    # ── Overlay 3: Deceleration Tightening ────────────────────────────
    enable_overlay_decel: bool = False
    ov3_accel_neg_bars: int = 5             # consecutive H4 bars with accel<0
    ov3_require_hma_break: bool = True      # also require price < HMA
    ov3_trail_tighten_mult: float = 2.0     # tighten trail when decel active
    ov3_sizing_mult: float = 0.50           # reduce new adds by 50%


# ---------------------------------------------------------------------------
# Indicator helpers (vectorized, numpy) — same as v8_apex.py
# ---------------------------------------------------------------------------

def _ema(a: np.ndarray, p: int) -> np.ndarray:
    alpha = 2.0 / (p + 1)
    out = np.empty(len(a), dtype=np.float64)
    out[0] = a[0]
    for i in range(1, len(a)):
        out[i] = alpha * a[i] + (1 - alpha) * out[i - 1]
    return out


def _ema_wilder(a: np.ndarray, p: int) -> np.ndarray:
    """EMA with Wilder's smoothing: alpha = 1/p."""
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
# ADX — ported from v10/research/regime.py (Wilder's method)
# ---------------------------------------------------------------------------

def _adx(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Average Directional Index (Wilder's method)."""
    n = len(closes)
    if n < 2:
        return np.zeros(n)

    # +DM / -DM
    pdm = np.zeros(n)
    ndm = np.zeros(n)
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        if up > down and up > 0:
            pdm[i] = up
        if down > up and down > 0:
            ndm[i] = down

    atr_arr = np.empty(n)
    tr = np.empty(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    atr_arr[0] = tr[0]
    alpha = 1.0 / period
    for i in range(1, n):
        atr_arr[i] = alpha * tr[i] + (1.0 - alpha) * atr_arr[i - 1]

    # Smooth +DM, -DM with Wilder
    s_pdm = np.empty(n)
    s_ndm = np.empty(n)
    s_pdm[0] = pdm[0]
    s_ndm[0] = ndm[0]
    for i in range(1, n):
        s_pdm[i] = alpha * pdm[i] + (1.0 - alpha) * s_pdm[i - 1]
        s_ndm[i] = alpha * ndm[i] + (1.0 - alpha) * s_ndm[i - 1]

    # +DI / -DI
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = np.where(atr_arr > 1e-12, 100.0 * s_pdm / atr_arr, 0.0)
        ndi = np.where(atr_arr > 1e-12, 100.0 * s_ndm / atr_arr, 0.0)

    # DX
    di_sum = pdi + ndi
    with np.errstate(divide="ignore", invalid="ignore"):
        dx = np.where(di_sum > 1e-12, 100.0 * np.abs(pdi - ndi) / di_sum, 0.0)

    # ADX = Wilder smoothed DX
    adx_out = np.empty(n)
    adx_out[0] = dx[0]
    for i in range(1, n):
        adx_out[i] = alpha * dx[i] + (1.0 - alpha) * adx_out[i - 1]

    return adx_out


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

class V11HybridStrategy(Strategy):
    """V11 Hybrid — VDO momentum + MR defensive + cycle phase + ADX gating."""

    def __init__(self, cfg: V11HybridConfig | None = None) -> None:
        self.cfg = cfg or V11HybridConfig()

        # ── V8 Apex tracking state ──
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

        # ── V11 tracking state ──
        self._mr_exit_fired: bool = False
        self._adx_chop_count: int = 0
        self._decel_neg_count: int = 0         # Overlay 3: consecutive accel<0 bars

        # ── Pre-computed arrays (set in on_init) ──
        self._h4_vdo = np.array([])
        self._h4_hma = np.array([])
        self._h4_rsi = np.array([])
        self._h4_atr_f = np.array([])
        self._h4_atr_s = np.array([])
        self._h4_accel = np.array([])
        self._h4_ema200 = np.array([])
        self._d1_regime = np.array([])
        self._d1_vol_ann = np.array([])
        # V11 arrays
        self._d1_rsi = np.array([])
        self._d1_ema200 = np.array([])
        self._d1_adx = np.array([])
        self._h4_adx = np.array([])
        self._d1_cycle_phase = np.array([])

    # -- on_init: pre-compute all indicators -----------------------------------

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        c = self.cfg
        if not h4_bars:
            return

        # ── H4 indicators (identical to V8 Apex) ──
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

        # Acceleration
        prev = np.roll(cl, c.roc_period)
        prev[: c.roc_period] = cl[: c.roc_period]
        roc = np.where(prev > 0, (cl - prev) / prev, 0.0)
        self._h4_accel = _ema(np.diff(roc, prepend=0.0), c.accel_smooth_period)

        # ── D1 indicators (regime + vol — identical to V8) ──
        if d1_bars:
            d1c = np.array([b.close for b in d1_bars], dtype=np.float64)
            d1h = np.array([b.high for b in d1_bars], dtype=np.float64)
            d1l = np.array([b.low for b in d1_bars], dtype=np.float64)

            ef = _ema(d1c, c.d1_ema_fast)
            es = _ema(d1c, c.d1_ema_slow)
            self._d1_regime = self._compute_regime(d1c, ef, es)
            lr = np.diff(np.log(np.maximum(d1c, 1e-10)), prepend=0.0)
            lr[0] = 0.0
            em, em2 = _ema(lr, 30), _ema(lr ** 2, 30)
            sig = np.sqrt(np.maximum(em2 - em ** 2, 0.0))
            self._d1_vol_ann = np.clip(sig * math.sqrt(365), 0.10, 3.00)

            # ── V11 D1 indicators ──
            if c.enable_mr_defensive:
                self._d1_rsi = _rsi(d1c, c.d1_rsi_period, method=c.rsi_method)
                self._d1_ema200 = _ema(d1c, 200)

            if c.enable_adx_gating or c.enable_cycle_phase:
                self._d1_adx = _adx(d1h, d1l, d1c, c.adx_period)

            if c.enable_cycle_phase:
                self._d1_cycle_phase = self._compute_cycle_phases(d1c, d1h, d1l)

        # ── H4 ADX (optional) ──
        if c.enable_adx_gating and c.adx_source == "h4":
            self._h4_adx = _adx(hi, lo, cl, c.adx_period)

    # -- D1 regime state machine (identical to V8) -----------------------------

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

    # -- V11: Cycle phase detection --------------------------------------------

    def _compute_cycle_phases(
        self,
        d1c: np.ndarray,
        d1h: np.ndarray,
        d1l: np.ndarray,
    ) -> np.ndarray:
        """Classify each D1 bar into a macro cycle phase with hysteresis."""
        c = self.cfg
        n = len(d1c)
        out = np.empty(n, dtype=object)

        ema_s = _ema(d1c, c.d1_ema_slow)
        ema_f = _ema(d1c, c.d1_ema_fast)
        rsi_arr = _rsi(d1c, c.d1_rsi_period if c.enable_mr_defensive else 14,
                       method=c.rsi_method)

        pending_phase = CyclePhase.BEAR
        confirmed_phase = CyclePhase.BEAR
        pending_count = 0

        for i in range(n):
            price = d1c[i]
            ema200 = ema_s[i]
            ema50 = ema_f[i]
            rsi = rsi_arr[i]

            # Distance from EMA200
            dist = (price - ema200) / ema200 if ema200 > 1e-12 else 0.0

            # Raw phase classification
            if price < ema200 and ema50 < ema200:
                raw = CyclePhase.BEAR
            elif dist < c.cycle_early_max_dist and ema50 > ema200 and price > ema200:
                raw = CyclePhase.EARLY_BULL
            elif dist >= c.cycle_late_min_dist and rsi >= c.cycle_late_rsi_min:
                raw = CyclePhase.LATE_BULL
            elif price > ema200:
                raw = CyclePhase.MID_BULL
            else:
                raw = CyclePhase.BEAR

            # Hysteresis: N consecutive bars to confirm transition
            if raw == pending_phase:
                pending_count += 1
            else:
                pending_phase = raw
                pending_count = 1

            if pending_count >= c.cycle_hysteresis_bars:
                confirmed_phase = pending_phase

            out[i] = confirmed_phase

        return out

    # -- V11: MR state assessment ----------------------------------------------

    def _assess_mr_state(self, d1i: int, mid: float) -> dict[str, Any]:
        """Evaluate MR conditions from D1 RSI and price-to-MA200 distance."""
        c = self.cfg
        result: dict[str, Any] = {
            "d1_rsi": 50.0,
            "ma200_dist": 0.0,
            "entry_blocked": False,
            "sizing_mult": 1.0,
            "should_partial_exit": False,
            "trail_override_mult": None,
        }

        if not c.enable_mr_defensive:
            return result

        # D1 RSI
        if 0 <= d1i < len(self._d1_rsi):
            result["d1_rsi"] = float(self._d1_rsi[d1i])

        # Price-to-MA200 distance
        if 0 <= d1i < len(self._d1_ema200) and self._d1_ema200[d1i] > 1e-12:
            result["ma200_dist"] = (mid - self._d1_ema200[d1i]) / self._d1_ema200[d1i]

        rsi = result["d1_rsi"]
        dist = result["ma200_dist"]

        # Entry blocking
        if rsi >= c.d1_rsi_entry_block:
            result["entry_blocked"] = True
        if dist >= c.ma200_dist_block:
            result["entry_blocked"] = True

        # Sizing reduction (continuous interpolation)
        rsi_mult = 1.0
        if rsi >= c.d1_rsi_extreme_high:
            rsi_range = max(c.d1_rsi_entry_block - c.d1_rsi_extreme_high, 1.0)
            progress = min((rsi - c.d1_rsi_extreme_high) / rsi_range, 1.0)
            rsi_mult = 1.0 - progress * 0.50  # 1.0 → 0.50

        dist_mult = 1.0
        if dist >= c.ma200_dist_reduce:
            dist_range = max(c.ma200_dist_block - c.ma200_dist_reduce, 0.01)
            progress = min((dist - c.ma200_dist_reduce) / dist_range, 1.0)
            dist_mult = 1.0 - progress * (1.0 - c.ma200_dist_floor)

        result["sizing_mult"] = min(rsi_mult, dist_mult)

        # Partial exit triggers
        if rsi >= c.d1_rsi_exit_trigger:
            result["should_partial_exit"] = True
        if dist >= c.ma200_dist_block:  # reuse block threshold for exit too
            result["should_partial_exit"] = True

        # Trail tightening override
        if rsi >= c.d1_rsi_extreme_high or dist >= c.ma200_dist_reduce:
            result["trail_override_mult"] = c.mr_trail_tighten_mult

        return result

    # -- V11: ADX lookup -------------------------------------------------------

    def _get_adx(self, d1i: int, h4_idx: int) -> float:
        """Get ADX value from configured source."""
        c = self.cfg
        if c.adx_source == "h4" and h4_idx < len(self._h4_adx):
            return float(self._h4_adx[h4_idx])
        if 0 <= d1i < len(self._d1_adx):
            return float(self._d1_adx[d1i])
        return 25.0  # safe default

    # -- Overlay 3 helper ------------------------------------------------------

    def _decel_active(self, idx: int, mid: float) -> bool:
        """Return True when deceleration conditions are met."""
        c = self.cfg
        if self._decel_neg_count < c.ov3_accel_neg_bars:
            return False
        if c.ov3_require_hma_break:
            hma_v = self._h4_hma[idx] if idx < len(self._h4_hma) else mid
            if np.isnan(hma_v) or mid >= hma_v:
                return False
        return True

    # -- on_bar: main decision logic -------------------------------------------

    def on_bar(self, state: MarketState) -> Signal | None:
        c = self.cfg
        idx = state.bar_index
        mid = state.bar.close
        in_pos = state.btc_qty > 1e-8

        # Detect position transitions
        just_closed = self._was_in_position and not in_pos
        just_opened = not self._was_in_position and in_pos

        if just_closed:
            self._last_exit_idx = idx
            self._peak_price = self._peak_profit = 0.0
            self._position_nav_peak = 0.0
            self._structural_below = self._hma_below = 0
            self._mr_exit_fired = False
            self._adx_chop_count = 0
            self._decel_neg_count = 0
        if just_opened:
            self._position_nav_peak = state.nav
        self._was_in_position = in_pos

        # Update peak tracking
        if in_pos and state.entry_price_avg > 0:
            self._peak_price = max(self._peak_price, mid)
            p = (mid - state.entry_price_avg) / state.entry_price_avg
            self._peak_profit = max(self._peak_profit, p)
        if in_pos:
            self._position_nav_peak = max(self._position_nav_peak, state.nav)
        self._equity_peak = max(self._equity_peak, state.nav)

        # Overlay 3: update deceleration counter
        if c.enable_overlay_decel:
            accel_v = self._h4_accel[idx] if idx < len(self._h4_accel) else 0.0
            if accel_v < 0:
                self._decel_neg_count += 1
            else:
                self._decel_neg_count = 0

        # Resolve D1 regime
        d1i = state.d1_index
        regime = (
            self._d1_regime[d1i]
            if 0 <= d1i < len(self._d1_regime)
            else Regime.RISK_OFF
        )

        if in_pos:
            sig = self._check_exit(state, idx, mid, regime)
            if sig is not None:
                return sig
        return self._check_entry(state, idx, mid, regime)

    # -- exits -----------------------------------------------------------------

    def _check_exit(
        self, state: MarketState, idx: int, mid: float, regime: Regime,
    ) -> Signal | None:
        c = self.cfg
        d1i = state.d1_index

        # 1. Emergency DD (identical to V8)
        if c.emergency_ref == "peak":
            ref_nav = self._position_nav_peak
        else:
            ref_nav = state.position_entry_nav
        if ref_nav > 0:
            dd = 1.0 - state.nav / ref_nav
            if dd >= c.emergency_dd_pct:
                return Signal(target_exposure=0.0, reason="emergency_dd")

        # 1.25: Overlay 2 — Position peak-to-trough stop
        if c.enable_overlay_peak_dd_stop and self._position_nav_peak > 0:
            atr_val_ov2 = (
                self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
            )
            pos_dd_pct = 1.0 - state.nav / self._position_nav_peak
            pos_dd_abs = self._peak_price - mid
            triggered = False
            if c.ov2_use_pct and pos_dd_pct >= c.ov2_max_pos_dd_pct:
                triggered = True
            if (c.ov2_use_atr and atr_val_ov2 > 0
                    and pos_dd_abs >= c.ov2_max_pos_dd_atr * atr_val_ov2):
                triggered = True
            if triggered:
                return Signal(target_exposure=0.0, reason="peak_dd_stop")

        # 1.5: MR defensive partial exit (V11)
        if c.enable_mr_defensive and state.exposure > 0.05 and not self._mr_exit_fired:
            mr = self._assess_mr_state(d1i, mid)
            if mr["should_partial_exit"]:
                self._mr_exit_fired = True
                new_expo = state.exposure * (1.0 - c.d1_rsi_exit_fraction)
                return Signal(target_exposure=max(new_expo, 0.0),
                              reason="mr_defensive_exit")

        # 2. Regime exit (disabled by default)
        if c.regime_exit_immediate and regime == Regime.RISK_OFF:
            return Signal(target_exposure=0.0, reason="regime_off")

        # 3a. Trailing stop
        atr_val = (
            self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
        )
        if c.enable_trail and self._peak_profit >= c.trail_activate_pct:
            mult = (
                c.trail_tighten_mult
                if self._peak_profit >= c.trail_tighten_profit_pct
                else c.trail_atr_mult
            )

            # V11: MR trail tightening
            if c.enable_mr_defensive:
                mr = self._assess_mr_state(d1i, mid)
                if mr["trail_override_mult"] is not None:
                    mult = min(mult, mr["trail_override_mult"])

            # V11: Cycle phase trail override
            if c.enable_cycle_phase and 0 <= d1i < len(self._d1_cycle_phase):
                phase = self._d1_cycle_phase[d1i]
                if phase == CyclePhase.EARLY_BULL:
                    mult = max(mult, c.cycle_early_trail_mult)  # wider
                elif phase == CyclePhase.LATE_BULL:
                    # Overlay 1 overrides cycle_late_trail_mult with tighter value
                    late_mult = (c.ov1_late_trail_mult
                                 if c.enable_overlay_pyramid_ban
                                 else c.cycle_late_trail_mult)
                    mult = min(mult, late_mult)                 # tighter

            # Overlay 3: Deceleration trail tightening
            if c.enable_overlay_decel and self._decel_active(idx, mid):
                mult = min(mult, c.ov3_trail_tighten_mult)

            stop = self._peak_price - mult * atr_val
            if mid <= stop:
                return Signal(target_exposure=0.0, reason="trailing_stop")

        # 3b. Fixed stop
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

    # -- entries ---------------------------------------------------------------

    def _check_entry(
        self, state: MarketState, idx: int, mid: float, regime: Regime,
    ) -> Signal | None:
        c = self.cfg
        d1i = state.d1_index

        # Gate 1: Regime
        if regime == Regime.RISK_OFF:
            return None

        # Gate 2: Cooldowns
        if idx - self._last_add_idx < c.entry_cooldown_bars:
            return None
        if idx - self._last_exit_idx < c.exit_cooldown_bars:
            return None

        # Gate 2.5: MR defensive entry block (V11)
        mr: dict[str, Any] | None = None
        if c.enable_mr_defensive:
            mr = self._assess_mr_state(d1i, mid)
            if mr["entry_blocked"]:
                return None

        # Gate 3: VDO threshold
        vdo = self._h4_vdo[idx] if idx < len(self._h4_vdo) else 0.0
        if vdo <= c.vdo_entry_threshold:
            return None

        # Gate 3.5: ADX trend strength (V11)
        if c.enable_adx_gating:
            adx_val = self._get_adx(d1i, idx)
            if adx_val < c.adx_min_trend:
                return None

        # Gate 4: Trend confirmation (above HMA OR oversold)
        hma_v = self._h4_hma[idx] if idx < len(self._h4_hma) else mid
        rsi_v = self._h4_rsi[idx] if idx < len(self._h4_rsi) else 50.0
        above_hma = not np.isnan(hma_v) and mid > hma_v
        oversold = rsi_v < c.rsi_oversold
        if not above_hma and not oversold:
            return None

        # Target exposure (vol-sized)
        va = (
            self._d1_vol_ann[d1i]
            if 0 <= d1i < len(self._d1_vol_ann)
            else 1.0
        )
        base = min(c.max_total_exposure, c.target_vol_annual / va)
        if regime == Regime.CAUTION:
            base *= c.caution_mult

        # Vol brake
        if c.enable_vol_brake and mid > 0:
            atr_f = (
                self._h4_atr_f[idx] if idx < len(self._h4_atr_f) else mid * 0.02
            )
            if atr_f / mid > c.vol_brake_atr_ratio:
                base *= c.vol_brake_mult

        # DD adaptive (disabled for apex)
        if (
            c.enable_dd_adaptive
            and self._equity_peak > 0
            and state.nav < self._equity_peak
        ):
            dd = 1.0 - state.nav / self._equity_peak
            if dd > c.dd_adaptive_start:
                prog = min(
                    (dd - c.dd_adaptive_start)
                    / max(c.emergency_dd_pct - c.dd_adaptive_start, 0.01),
                    1.0,
                )
                base *= 1.0 - prog * (1.0 - c.dd_adaptive_floor)

        # V11: MR sizing reduction
        if mr is not None and mr["sizing_mult"] < 1.0:
            base *= mr["sizing_mult"]

        # V11: Cycle phase max exposure cap
        if c.enable_cycle_phase and 0 <= d1i < len(self._d1_cycle_phase):
            phase = self._d1_cycle_phase[d1i]
            if phase == CyclePhase.LATE_BULL:
                base = min(base, c.cycle_late_max_exposure)

        # Overlay 1: Block pyramiding adds in LATE_BULL (allow fresh entries)
        if (c.enable_overlay_pyramid_ban and c.ov1_block_add_in_late
                and c.enable_cycle_phase and 0 <= d1i < len(self._d1_cycle_phase)):
            if self._d1_cycle_phase[d1i] == CyclePhase.LATE_BULL:
                if state.exposure > 0.01:
                    return None  # block add, keep existing position

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

        # V11: ADX sizing adjustment
        if c.enable_adx_gating:
            adx_val = self._get_adx(d1i, idx)
            if adx_val >= c.adx_strong_trend:
                sz *= c.adx_strong_sizing_mult
            elif adx_val >= c.adx_min_trend:
                sz *= c.adx_weak_sizing_mult

        # V11: Cycle phase aggression
        if c.enable_cycle_phase and 0 <= d1i < len(self._d1_cycle_phase):
            phase = self._d1_cycle_phase[d1i]
            if phase == CyclePhase.EARLY_BULL:
                sz *= c.cycle_early_aggression
            elif phase == CyclePhase.LATE_BULL:
                sz *= c.cycle_late_aggression

        # Overlay 3: Deceleration sizing reduction
        if c.enable_overlay_decel and self._decel_active(idx, mid):
            sz *= c.ov3_sizing_mult

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
        features = []
        if self.cfg.enable_mr_defensive:
            features.append("MR")
        if self.cfg.enable_cycle_phase:
            features.append("Cycle")
        if self.cfg.enable_adx_gating:
            features.append("ADX")
        if self.cfg.enable_overlay_pyramid_ban:
            features.append("OV1")
        if self.cfg.enable_overlay_peak_dd_stop:
            features.append("OV2")
        if self.cfg.enable_overlay_decel:
            features.append("OV3")
        tag = "+".join(features) if features else "base"
        return f"V11Hybrid[{tag}|vdo=taker_buy]"
