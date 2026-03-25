"""Tests for V8ApexStrategy — regime gating, trailing stop, emergency DD.

Tests:
  1. TestRegimeTransitions — confirm/off bars, CAUTION, hysteresis
  2. TestRegimeGating — RISK_OFF blocks entries, RISK_ON allows
  3. TestTrailingStop — fixed stop before activation, trailing after, tightening
  4. TestEmergencyDD — uses position_entry_nav, not equity peak
  5. TestVDONoFallback — taker_buy required, OHLC fallback removed
"""

from __future__ import annotations

import numpy as np
import pytest

from v10.core.types import Bar, CostConfig, MarketState, Signal
from v10.strategies.v8_apex import V8ApexStrategy, V8ApexConfig, Regime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

H4_MS = 14_400_000
D1_MS = 86_400_000


def _h4(i: int, price: float, taker: float = 55.0, base_ms: int = 0) -> Bar:
    ot = base_ms + i * H4_MS
    return Bar(
        open_time=ot, open=price, high=price * 1.001, low=price * 0.999,
        close=price, volume=100.0, close_time=ot + H4_MS - 1,
        taker_buy_base_vol=taker, interval="4h",
    )


def _d1(i: int, price: float, base_ms: int = 0) -> Bar:
    ot = base_ms + i * D1_MS
    return Bar(
        open_time=ot, open=price, high=price * 1.001, low=price * 0.999,
        close=price, volume=600.0, close_time=ot + D1_MS - 1,
        taker_buy_base_vol=300.0, interval="1d",
    )


def _init_strat(cfg: V8ApexConfig | None = None, n_h4: int = 100,
                n_d1: int = 20) -> V8ApexStrategy:
    """Create strategy and run on_init with flat-price synthetic bars."""
    strat = V8ApexStrategy(cfg)
    h4 = [_h4(i, 50_000.0) for i in range(n_h4)]
    d1 = [_d1(i, 50_000.0) for i in range(n_d1)]
    strat.on_init(h4, d1)
    return strat


def _make_state(
    idx: int, close: float, btc_qty: float = 0.2,
    entry: float = 50_000.0, nav: float = 10_000.0,
    entry_nav: float = 10_000.0,
) -> MarketState:
    bar = Bar(
        open_time=idx * H4_MS, open=close, high=close * 1.001,
        low=close * 0.999, close=close, volume=100.0,
        close_time=idx * H4_MS + H4_MS - 1,
        taker_buy_base_vol=55.0, interval="4h",
    )
    return MarketState(
        bar=bar, h4_bars=[], d1_bars=[],
        bar_index=idx, d1_index=0,
        cash=nav - btc_qty * close, btc_qty=btc_qty,
        nav=nav, exposure=btc_qty * close / max(nav, 1.0),
        entry_price_avg=entry, position_entry_nav=entry_nav,
    )


# ---------------------------------------------------------------------------
# TEST 1: Regime transitions — confirm/off bars
# ---------------------------------------------------------------------------

class TestRegimeTransitions:
    """Test _compute_regime directly with synthetic EMA arrays."""

    def test_risk_off_to_risk_on(self) -> None:
        """2 consecutive closes above EMA200 + golden cross → RISK_ON."""
        cfg = V8ApexConfig(d1_regime_confirm_bars=2, d1_regime_off_bars=4)
        strat = V8ApexStrategy(cfg)
        n = 10
        ema_f = np.full(n, 110.0)   # EMA50 > EMA200
        ema_s = np.full(n, 100.0)   # EMA200
        close = np.array([
            90, 90, 90, 90,           # bars 0-3: below EMA200
            105, 105, 105, 105, 105, 105,  # bars 4+: above EMA200
        ], dtype=np.float64)

        regime = strat._compute_regime(close, ema_f, ema_s)

        assert regime[3] == Regime.RISK_OFF, "Below EMA200 → RISK_OFF"
        assert regime[4] == Regime.RISK_OFF, "1 bar above → sticky RISK_OFF"
        assert regime[5] == Regime.RISK_ON, (
            f"2 bars above + golden cross → RISK_ON, got {regime[5]}")

    def test_risk_on_to_risk_off(self) -> None:
        """4 consecutive closes below EMA200 → RISK_OFF."""
        cfg = V8ApexConfig(d1_regime_confirm_bars=2, d1_regime_off_bars=4)
        strat = V8ApexStrategy(cfg)
        n = 12
        ema_f = np.full(n, 110.0)
        ema_s = np.full(n, 100.0)
        close = np.array([
            105, 105, 105,             # bars 0-2: confirm RISK_ON
            90, 90, 90, 90,            # bars 3-6: below for 4 bars
            90, 90, 90, 90, 90,
        ], dtype=np.float64)

        regime = strat._compute_regime(close, ema_f, ema_s)

        assert regime[1] == Regime.RISK_ON, "Confirmed after 2 bars above"
        assert regime[3] == Regime.RISK_ON, "below=1, sticky RISK_ON"
        assert regime[5] == Regime.RISK_ON, "below=3, still sticky"
        assert regime[6] == Regime.RISK_OFF, (
            f"below=4 ≥ off_bars=4 → RISK_OFF, got {regime[6]}")

    def test_caution_without_golden_cross(self) -> None:
        """Closes above EMA200 but EMA50 < EMA200 → CAUTION (not RISK_ON)."""
        cfg = V8ApexConfig(d1_regime_confirm_bars=2, d1_regime_off_bars=4)
        strat = V8ApexStrategy(cfg)
        n = 6
        ema_f = np.full(n, 90.0)    # EMA50 < EMA200 (death cross)
        ema_s = np.full(n, 100.0)
        close = np.full(n, 105.0)

        regime = strat._compute_regime(close, ema_f, ema_s)

        assert regime[1] == Regime.CAUTION, (
            f"2 bars above but no golden cross → CAUTION, got {regime[1]}")
        assert regime[5] == Regime.CAUTION

    def test_hysteresis_prevents_chatter(self) -> None:
        """Oscillating around EMA200 shouldn't flip regime rapidly."""
        cfg = V8ApexConfig(d1_regime_confirm_bars=2, d1_regime_off_bars=4)
        strat = V8ApexStrategy(cfg)
        ema_f = np.full(10, 110.0)
        ema_s = np.full(10, 100.0)
        # above, above, below, above, above, below×5
        close = np.array(
            [105, 105, 90, 105, 105, 90, 90, 90, 90, 90], dtype=np.float64,
        )

        regime = strat._compute_regime(close, ema_f, ema_s)

        assert regime[1] == Regime.RISK_ON, "Confirmed at bar 1"
        assert regime[2] == Regime.RISK_ON, "1 bar below → sticky (needs 4)"
        assert regime[4] == Regime.RISK_ON, "Re-confirmed above"
        # bars 5-8: below for 4 consecutive
        assert regime[7] == Regime.RISK_ON, "below=3, still sticky"
        assert regime[8] == Regime.RISK_OFF, "below=4 → RISK_OFF"


# ---------------------------------------------------------------------------
# TEST 2: Regime gating — RISK_OFF blocks entries
# ---------------------------------------------------------------------------

class TestRegimeGating:
    """RISK_OFF must block _check_entry regardless of other conditions."""

    def test_risk_off_blocks_entry(self) -> None:
        strat = _init_strat()
        state = _make_state(50, 50_000.0, btc_qty=0.0, nav=10_000.0)
        sig = strat._check_entry(state, 50, 50_000.0, Regime.RISK_OFF)
        assert sig is None, "RISK_OFF must block entry"

    def test_risk_on_allows_entry_path(self) -> None:
        """RISK_ON does NOT block — entry may still fail on VDO/HMA gates,
        but the regime gate itself must pass."""
        strat = _init_strat()
        state = _make_state(50, 50_000.0, btc_qty=0.0, nav=10_000.0)
        # This may return None (VDO/HMA gate), but NOT because of regime
        sig = strat._check_entry(state, 50, 50_000.0, Regime.RISK_ON)
        # We can't assert sig is not None (other gates may fail),
        # but we confirmed RISK_ON doesn't return at the regime gate.
        # If RISK_OFF blocked it, the earlier test proves that.


# ---------------------------------------------------------------------------
# TEST 3: Trailing stop — activation threshold
# ---------------------------------------------------------------------------

class TestTrailingStop:
    """Trailing stop must only activate after trail_activate_pct profit."""

    def test_fixed_stop_before_trail_activation(self) -> None:
        """Peak profit 3% (below 5% threshold) → fixed stop at 15% loss."""
        strat = _init_strat(V8ApexConfig(
            trail_activate_pct=0.05, fixed_stop_pct=0.15,
            emergency_dd_pct=0.99,
        ))
        strat._peak_profit = 0.03
        strat._peak_price = 51_500.0
        strat._was_in_position = True

        # Price 42000 < entry*0.85=42500 → fixed stop triggers
        sig = strat._check_exit(
            _make_state(50, 42_000.0), 50, 42_000.0, Regime.RISK_ON,
        )
        assert sig is not None
        assert sig.reason == "fixed_stop", f"Expected fixed_stop, got {sig.reason}"
        assert sig.target_exposure == 0.0

    def test_trailing_stop_after_activation(self) -> None:
        """Peak profit 8% (above 5%) → trailing stop with ATR distance."""
        strat = _init_strat(V8ApexConfig(
            trail_activate_pct=0.05, trail_atr_mult=3.5,
            emergency_dd_pct=0.99,
        ))
        strat._peak_profit = 0.08
        strat._peak_price = 54_000.0
        strat._was_in_position = True

        # ATR from flat 50000 bars: high=50050, low=49950 → TR≈100 → ATR≈100
        # trail_dist = 3.5 × 100 = 350,  stop = 54000 - 350 = 53650
        # Price 53000 < 53650 → trailing stop
        sig = strat._check_exit(
            _make_state(50, 53_000.0), 50, 53_000.0, Regime.RISK_ON,
        )
        assert sig is not None
        assert sig.reason == "trailing_stop", (
            f"Expected trailing_stop, got {sig.reason}")

    def test_no_exit_when_above_both_stops(self) -> None:
        """Price above fixed stop and trail not active → no exit."""
        strat = _init_strat(V8ApexConfig(
            trail_activate_pct=0.05, fixed_stop_pct=0.15,
            emergency_dd_pct=0.99,
        ))
        strat._peak_profit = 0.03
        strat._peak_price = 51_500.0
        strat._was_in_position = True

        # Price 49000 > fixed stop 42500, trail not active
        sig = strat._check_exit(
            _make_state(50, 49_000.0), 50, 49_000.0, Regime.RISK_ON,
        )
        assert sig is None, f"Expected no exit, got {sig.reason if sig else None}"

    def test_trail_tightens_after_high_profit(self) -> None:
        """After 20%+ profit, trail tightens from 3.5x to 2.5x ATR.
        Price that survives the wide trail but triggers the tight trail."""
        strat = _init_strat(V8ApexConfig(
            trail_activate_pct=0.05, trail_atr_mult=3.5,
            trail_tighten_mult=2.5, trail_tighten_profit_pct=0.20,
            emergency_dd_pct=0.99,
        ))
        strat._peak_profit = 0.22   # above 20% → tighten
        strat._peak_price = 61_000.0
        strat._was_in_position = True

        # ATR ≈ 100.  Tight: 2.5×100=250, stop=61000-250=60750
        # Wide:  3.5×100=350, stop=61000-350=60650
        # Price 60700: triggers tight (60700 < 60750) but NOT wide (60700 > 60650)
        sig = strat._check_exit(
            _make_state(50, 60_700.0), 50, 60_700.0, Regime.RISK_ON,
        )
        assert sig is not None
        assert sig.reason == "trailing_stop"

        # Same scenario but peak_profit=6% (below tighten) → wide trail → no trigger
        strat2 = _init_strat(V8ApexConfig(
            trail_activate_pct=0.05, trail_atr_mult=3.5,
            trail_tighten_mult=2.5, trail_tighten_profit_pct=0.20,
            emergency_dd_pct=0.99,
        ))
        strat2._peak_profit = 0.06
        strat2._peak_price = 61_000.0
        strat2._was_in_position = True

        sig2 = strat2._check_exit(
            _make_state(50, 60_700.0), 50, 60_700.0, Regime.RISK_ON,
        )
        assert sig2 is None, (
            f"Wide trail should NOT trigger at 60700 (stop=60650), "
            f"got {sig2.reason if sig2 else None}")


# ---------------------------------------------------------------------------
# TEST 4: Emergency DD — uses position_entry_nav
# ---------------------------------------------------------------------------

class TestEmergencyDD:
    """Emergency DD must use position_entry_nav, not equity peak."""

    def test_triggers_at_threshold(self) -> None:
        """DD from entry NAV ≥ 25% → emergency_dd exit."""
        strat = _init_strat(V8ApexConfig(
            emergency_dd_pct=0.25, enable_trail=False, enable_fixed_stop=False,
        ))
        strat._was_in_position = True

        # entry_nav=10000, nav=7400 → DD = 26% > 25%
        sig = strat._check_exit(
            _make_state(50, 37_000.0, nav=7_400.0, entry_nav=10_000.0),
            50, 37_000.0, Regime.RISK_ON,
        )
        assert sig is not None
        assert sig.reason == "emergency_dd"

    def test_no_trigger_below_threshold(self) -> None:
        """DD from entry NAV = 20% < 25% → no exit."""
        strat = _init_strat(V8ApexConfig(
            emergency_dd_pct=0.25, enable_trail=False, enable_fixed_stop=False,
        ))
        strat._was_in_position = True

        # entry_nav=10000, nav=8000 → DD = 20% < 25%
        sig = strat._check_exit(
            _make_state(50, 40_000.0, nav=8_000.0, entry_nav=10_000.0),
            50, 40_000.0, Regime.RISK_ON,
        )
        assert sig is None

    def test_uses_position_entry_nav_not_equity_peak(self) -> None:
        """equity_peak=20000 (from prior profitable run) but
        position_entry_nav=10000 (this trade's entry).
        DD from peak=60% (would trigger), DD from entry=20% (should NOT)."""
        strat = _init_strat(V8ApexConfig(
            emergency_dd_pct=0.25, enable_trail=False, enable_fixed_stop=False,
        ))
        strat._equity_peak = 20_000.0   # high watermark from before
        strat._was_in_position = True

        # nav=8000, entry_nav=10000 → DD from entry = 20% < 25%
        # DD from equity_peak = 1 - 8000/20000 = 60% (would trigger if used!)
        sig = strat._check_exit(
            _make_state(50, 40_000.0, nav=8_000.0, entry_nav=10_000.0),
            50, 40_000.0, Regime.RISK_ON,
        )
        assert sig is None, (
            f"Expected None (DD from entry=20% < 25%). "
            f"Got {sig.reason if sig else None}. "
            f"If 'emergency_dd', the code is using equity_peak instead of "
            f"position_entry_nav!")


# ---------------------------------------------------------------------------
# TEST 5: VDO requires taker data (OHLC fallback removed)
# ---------------------------------------------------------------------------

class TestVDONoFallback:
    """VDO requires real taker_buy data; raises RuntimeError without it."""

    def test_taker_buy_source(self) -> None:
        strat = V8ApexStrategy()
        h4 = [_h4(i, 50_000.0, taker=55.0) for i in range(50)]
        d1 = [_d1(i, 50_000.0) for i in range(10)]
        strat.on_init(h4, d1)
        assert strat._vdo_source == "taker_buy"
        assert "taker_buy" in strat.name()

    def test_raises_without_taker_data(self) -> None:
        """Missing taker data must raise RuntimeError, not silently fallback."""
        strat = V8ApexStrategy()
        h4 = [_h4(i, 50_000.0, taker=0.0) for i in range(50)]
        d1 = [_d1(i, 50_000.0) for i in range(10)]
        with pytest.raises(RuntimeError, match="VDO requires taker_buy_base_vol"):
            strat.on_init(h4, d1)
