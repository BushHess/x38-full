"""Tests for Overlay A v2 — Escalating Cooldown.

Deterministic tests that verify the two-tier cooldown state machine:
  1. Isolated ED exit → short cooldown applied
  2. Two ED exits within lookback → long cooldown activated
  3. Lookback window expiry resets cascade counter
  4. Cascade trigger resets counter (next ED gets short cooldown)
  5. escalating_cooldown=False → original v1 behavior unchanged
  6. InstrumentedV8Apex returns "short_cooldown" / "long_cooldown" reasons
  7. Counter never goes negative; cooldown never goes negative

Uses the same test helpers as test_overlayA_cooldown.py.
"""

from __future__ import annotations

import numpy as np
import pytest

from v10.core.types import Bar, MarketState, Signal
from v10.strategies.v8_apex import V8ApexStrategy, V8ApexConfig, Regime


# ---------------------------------------------------------------------------
# Helpers (same pattern as test_overlayA_cooldown.py)
# ---------------------------------------------------------------------------

H4_MS = 14_400_000
D1_MS = 86_400_000
PRICE = 50_000.0


def _h4(i: int, price: float = PRICE) -> Bar:
    ot = i * H4_MS
    return Bar(
        open_time=ot, open=price, high=price * 1.001, low=price * 0.999,
        close=price, volume=100.0, close_time=ot + H4_MS - 1,
        taker_buy_base_vol=55.0, interval="4h",
    )


def _d1(i: int, price: float = PRICE) -> Bar:
    ot = i * D1_MS
    return Bar(
        open_time=ot, open=price, high=price * 1.001, low=price * 0.999,
        close=price, volume=600.0, close_time=ot + D1_MS - 1,
        taker_buy_base_vol=300.0, interval="1d",
    )


def _init_strat(
    short: int = 3, long: int = 8, lookback: int = 20,
    trigger: int = 2, n_h4: int = 300, n_d1: int = 60,
) -> V8ApexStrategy:
    """Create strategy with v2 escalating cooldown enabled."""
    cfg = V8ApexConfig(
        escalating_cooldown=True,
        short_cooldown_bars=short,
        long_cooldown_bars=long,
        escalating_lookback_bars=lookback,
        cascade_trigger_count=trigger,
        cooldown_after_emergency_dd_bars=0,  # v1 disabled
    )
    strat = V8ApexStrategy(cfg)
    h4 = [_h4(i) for i in range(n_h4)]
    d1 = [_d1(i) for i in range(n_d1)]
    strat.on_init(h4, d1)
    return strat


def _init_strat_v1(cooldown_bars: int = 12, n_h4: int = 300,
                   n_d1: int = 60) -> V8ApexStrategy:
    """Create strategy with v1 flat cooldown (escalating disabled)."""
    cfg = V8ApexConfig(
        escalating_cooldown=False,
        cooldown_after_emergency_dd_bars=cooldown_bars,
    )
    strat = V8ApexStrategy(cfg)
    h4 = [_h4(i) for i in range(n_h4)]
    d1 = [_d1(i) for i in range(n_d1)]
    strat.on_init(h4, d1)
    return strat


def _state_in_pos(
    idx: int, nav: float = 10_000.0, entry_nav: float = 10_000.0,
    btc_qty: float = 0.2, close: float = PRICE,
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
        entry_price_avg=close, position_entry_nav=entry_nav,
    )


def _state_flat(idx: int, nav: float = 10_000.0) -> MarketState:
    bar = Bar(
        open_time=idx * H4_MS, open=PRICE, high=PRICE * 1.001,
        low=PRICE * 0.999, close=PRICE, volume=100.0,
        close_time=idx * H4_MS + H4_MS - 1,
        taker_buy_base_vol=55.0, interval="4h",
    )
    return MarketState(
        bar=bar, h4_bars=[], d1_bars=[],
        bar_index=idx, d1_index=0,
        cash=nav, btc_qty=0.0,
        nav=nav, exposure=0.0,
        entry_price_avg=0.0, position_entry_nav=0.0,
    )


def _simulate_ed_exit_and_close(strat: V8ApexStrategy,
                                exit_bar: int, close_bar: int,
                                nav: float = 10_000.0) -> None:
    """Simulate: in_pos at exit_bar (emergency_dd fires), flat at close_bar."""
    # Bar exit_bar: in position, NAV dropped → emergency_dd
    sig = strat.on_bar(_state_in_pos(exit_bar, nav=7100, entry_nav=10_000))
    assert sig is not None and sig.reason == "emergency_dd"
    # Bar close_bar: position closed (fill executed) → just_closed
    strat.on_bar(_state_flat(close_bar, nav=7100))


# ---------------------------------------------------------------------------
# TEST 1: Isolated ED → short cooldown
# ---------------------------------------------------------------------------

class TestIsolatedEDShortCooldown:
    """Single ED exit should apply short_cooldown_bars, not long."""

    def test_short_cooldown_applied(self):
        strat = _init_strat(short=3, long=8, lookback=20, trigger=2)

        # In position at bar 60
        strat.on_bar(_state_in_pos(60))

        # Bar 61: emergency_dd exit signal
        sig = strat.on_bar(_state_in_pos(61, nav=7100, entry_nav=10_000))
        assert sig is not None
        assert sig.reason == "emergency_dd"

        # Bar 62: position closed → just_closed → short cooldown set
        strat.on_bar(_state_flat(62, nav=7100))
        # short=3, set then decremented once → 3-1=2
        assert strat._emergency_dd_cooldown_remaining == 2
        assert strat._active_cooldown_type == "short_cooldown"
        assert strat._cascade_ed_count == 1

    def test_short_cooldown_expires_correctly(self):
        strat = _init_strat(short=3, long=8)

        strat.on_bar(_state_in_pos(60))
        sig = strat.on_bar(_state_in_pos(61, nav=7100, entry_nav=10_000))
        strat.on_bar(_state_flat(62, nav=7100))  # remaining=2

        strat.on_bar(_state_flat(63, nav=7100))  # remaining=1
        strat.on_bar(_state_flat(64, nav=7100))  # remaining=0
        assert strat._emergency_dd_cooldown_remaining == 0

        # Bar 65: cooldown expired, Gate 0 should not block
        strat.on_bar(_state_flat(65, nav=7100))
        assert strat._emergency_dd_cooldown_remaining == 0


# ---------------------------------------------------------------------------
# TEST 2: Two EDs within lookback → long cooldown
# ---------------------------------------------------------------------------

class TestCascadeTwoEDsLongCooldown:
    """Two ED exits within lookback_bars should trigger long cooldown."""

    def test_cascade_activates_long_cooldown(self):
        strat = _init_strat(short=3, long=8, lookback=20, trigger=2)

        # --- ED exit #1 ---
        strat.on_bar(_state_in_pos(60))
        sig = strat.on_bar(_state_in_pos(61, nav=7100, entry_nav=10_000))
        assert sig.reason == "emergency_dd"
        strat.on_bar(_state_flat(62, nav=7100))  # short cooldown set
        assert strat._active_cooldown_type == "short_cooldown"
        assert strat._cascade_ed_count == 1

        # Burn short cooldown
        strat.on_bar(_state_flat(63, nav=7100))
        strat.on_bar(_state_flat(64, nav=7100))
        assert strat._emergency_dd_cooldown_remaining == 0

        # --- New trade enters at bar 70, then ED exit #2 ---
        strat.on_bar(_state_flat(70, nav=7100))   # entry signal bar
        strat.on_bar(_state_in_pos(71, nav=7100, entry_nav=7100))  # fill
        # Bar 72: emergency_dd again (within lookback: 72-62=10 ≤ 20)
        sig = strat.on_bar(_state_in_pos(72, nav=5100, entry_nav=7100))
        assert sig.reason == "emergency_dd"

        # Bar 73: just_closed → cascade detected
        strat.on_bar(_state_flat(73, nav=5100))
        # long=8, set then decremented once → 8-1=7
        assert strat._emergency_dd_cooldown_remaining == 7
        assert strat._active_cooldown_type == "long_cooldown"
        # Counter reset after cascade trigger
        assert strat._cascade_ed_count == 0

    def test_long_cooldown_duration(self):
        """Long cooldown should last exactly long_cooldown_bars."""
        strat = _init_strat(short=3, long=8, lookback=20, trigger=2)

        # Set up cascade state directly
        strat._was_in_position = True
        strat._last_exit_reason = "emergency_dd"
        strat._last_emergency_dd_bar_idx = 50  # previous ED
        strat._cascade_ed_count = 1  # one ED already counted

        # Bar 60: just_closed, within lookback (60-50=10 ≤ 20) → cascade
        strat.on_bar(_state_flat(60, nav=7100))
        assert strat._active_cooldown_type == "long_cooldown"
        # long=8 set then decremented → 7
        assert strat._emergency_dd_cooldown_remaining == 7

        # Burn 7 bars of cooldown
        for i in range(7):
            strat.on_bar(_state_flat(61 + i, nav=7100))
        assert strat._emergency_dd_cooldown_remaining == 0


# ---------------------------------------------------------------------------
# TEST 3: Lookback expires → counter resets
# ---------------------------------------------------------------------------

class TestLookbackExpiresResetsCounter:
    """If lookback_bars pass without another ED, cascade counter resets."""

    def test_counter_resets_after_lookback(self):
        strat = _init_strat(short=3, long=8, lookback=20, trigger=2)

        # ED exit #1 at bar 62
        strat.on_bar(_state_in_pos(60))
        strat.on_bar(_state_in_pos(61, nav=7100, entry_nav=10_000))
        strat.on_bar(_state_flat(62, nav=7100))
        assert strat._cascade_ed_count == 1
        assert strat._last_emergency_dd_bar_idx == 62

        # Burn bars past lookback window (62 + 20 = 82)
        for i in range(63, 84):
            strat.on_bar(_state_flat(i, nav=7100))

        # Counter should be reset (83 - 62 = 21 > 20)
        assert strat._cascade_ed_count == 0

    def test_ed_after_lookback_is_new_isolated(self):
        """ED exit beyond lookback window should get short cooldown, not long."""
        strat = _init_strat(short=3, long=8, lookback=20, trigger=2)

        # ED #1
        strat.on_bar(_state_in_pos(60))
        strat.on_bar(_state_in_pos(61, nav=7100, entry_nav=10_000))
        strat.on_bar(_state_flat(62, nav=7100))

        # Burn past lookback
        for i in range(63, 90):
            strat.on_bar(_state_flat(i, nav=7100))

        # ED #2, well outside lookback (90 - 62 = 28 > 20)
        strat.on_bar(_state_in_pos(90, nav=7100, entry_nav=7100))
        sig = strat.on_bar(_state_in_pos(91, nav=5100, entry_nav=7100))
        assert sig.reason == "emergency_dd"
        strat.on_bar(_state_flat(92, nav=5100))

        # Should be short cooldown (new isolated, not cascade)
        assert strat._active_cooldown_type == "short_cooldown"
        assert strat._cascade_ed_count == 1  # fresh count


# ---------------------------------------------------------------------------
# TEST 4: Cascade resets counter — next ED gets short cooldown
# ---------------------------------------------------------------------------

class TestCascadeResetsCounter:

    def test_next_ed_after_cascade_gets_short(self):
        strat = _init_strat(short=3, long=8, lookback=20, trigger=2)

        # Directly set up: cascade was triggered, counter is 0
        strat._cascade_ed_count = 0
        strat._last_emergency_dd_bar_idx = 50
        strat._active_cooldown_type = "long_cooldown"
        strat._emergency_dd_cooldown_remaining = 0  # long cooldown expired

        # Burn bars past lookback to clear any state
        for i in range(80, 85):
            strat.on_bar(_state_flat(i))

        # New trade → ED exit #3 (fresh start)
        strat.on_bar(_state_in_pos(90, nav=7100, entry_nav=7100))
        sig = strat.on_bar(_state_in_pos(91, nav=5100, entry_nav=7100))
        assert sig.reason == "emergency_dd"
        strat.on_bar(_state_flat(92, nav=5100))

        # Should be short cooldown (count=1, fresh after cascade reset)
        assert strat._active_cooldown_type == "short_cooldown"
        assert strat._cascade_ed_count == 1


# ---------------------------------------------------------------------------
# TEST 5: escalating_cooldown=False → v1 behavior unchanged
# ---------------------------------------------------------------------------

class TestV1BehaviorUnchanged:

    def test_v1_flat_cooldown_still_works(self):
        K = 12
        strat = _init_strat_v1(cooldown_bars=K)

        strat.on_bar(_state_in_pos(60))
        sig = strat.on_bar(_state_in_pos(61, nav=7100, entry_nav=10_000))
        assert sig.reason == "emergency_dd"

        strat.on_bar(_state_flat(62, nav=7100))
        # V1: K=12, set then decremented → 11
        assert strat._emergency_dd_cooldown_remaining == K - 1
        # V2 state should be untouched
        assert strat._cascade_ed_count == 0
        assert strat._active_cooldown_type == ""

    def test_v1_gate0_blocks(self):
        strat = _init_strat_v1(cooldown_bars=12)
        strat._emergency_dd_cooldown_remaining = 5

        result = strat._check_entry(
            _state_flat(80), 80, PRICE, Regime.RISK_ON,
        )
        assert result is None


# ---------------------------------------------------------------------------
# TEST 6: InstrumentedV8Apex logging reasons
# ---------------------------------------------------------------------------

class TestDiagnoseBlockReasons:

    def test_short_cooldown_reason(self):
        """_diagnose_block should return 'short_cooldown' during v2 short cooldown."""
        # Import InstrumentedV8Apex
        from experiments.overlayA.step1_export import InstrumentedV8Apex

        cfg = V8ApexConfig(
            escalating_cooldown=True,
            short_cooldown_bars=3,
            long_cooldown_bars=8,
            escalating_lookback_bars=20,
            cascade_trigger_count=2,
            cooldown_after_emergency_dd_bars=0,
        )
        strat = InstrumentedV8Apex(cfg)
        h4 = [_h4(i) for i in range(300)]
        d1 = [_d1(i) for i in range(60)]
        strat.on_init(h4, d1)

        # Manually set state: short cooldown active
        strat._emergency_dd_cooldown_remaining = 2
        strat._active_cooldown_type = "short_cooldown"

        reason = strat._diagnose_block(
            _state_flat(80), 80, PRICE, Regime.RISK_ON,
        )
        assert reason == "short_cooldown"

    def test_long_cooldown_reason(self):
        """_diagnose_block should return 'long_cooldown' during v2 long cooldown."""
        from experiments.overlayA.step1_export import InstrumentedV8Apex

        cfg = V8ApexConfig(
            escalating_cooldown=True,
            short_cooldown_bars=3,
            long_cooldown_bars=8,
            escalating_lookback_bars=20,
            cascade_trigger_count=2,
            cooldown_after_emergency_dd_bars=0,
        )
        strat = InstrumentedV8Apex(cfg)
        h4 = [_h4(i) for i in range(300)]
        d1 = [_d1(i) for i in range(60)]
        strat.on_init(h4, d1)

        # Manually set state: long cooldown active
        strat._emergency_dd_cooldown_remaining = 5
        strat._active_cooldown_type = "long_cooldown"

        reason = strat._diagnose_block(
            _state_flat(80), 80, PRICE, Regime.RISK_ON,
        )
        assert reason == "long_cooldown"

    def test_v1_reason_unchanged(self):
        """When escalating_cooldown=False, reason should be 'cooldown_after_emergency_dd'."""
        from experiments.overlayA.step1_export import InstrumentedV8Apex

        cfg = V8ApexConfig(
            escalating_cooldown=False,
            cooldown_after_emergency_dd_bars=12,
        )
        strat = InstrumentedV8Apex(cfg)
        h4 = [_h4(i) for i in range(300)]
        d1 = [_d1(i) for i in range(60)]
        strat.on_init(h4, d1)

        strat._emergency_dd_cooldown_remaining = 5

        reason = strat._diagnose_block(
            _state_flat(80), 80, PRICE, Regime.RISK_ON,
        )
        assert reason == "cooldown_after_emergency_dd"


# ---------------------------------------------------------------------------
# TEST 7: Config defaults
# ---------------------------------------------------------------------------

class TestConfigDefaults:

    def test_escalating_disabled_by_default(self):
        cfg = V8ApexConfig()
        assert cfg.escalating_cooldown is False

    def test_custom_v2_config(self):
        cfg = V8ApexConfig(
            escalating_cooldown=True,
            short_cooldown_bars=5,
            long_cooldown_bars=15,
            escalating_lookback_bars=30,
            cascade_trigger_count=3,
        )
        assert cfg.escalating_cooldown is True
        assert cfg.short_cooldown_bars == 5
        assert cfg.long_cooldown_bars == 15
        assert cfg.escalating_lookback_bars == 30
        assert cfg.cascade_trigger_count == 3
