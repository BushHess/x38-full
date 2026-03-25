"""Smoke tests for V12 EMDD reference-fix strategy wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from strategies.v12_emdd_ref_fix.strategy import STRATEGY_ID
from strategies.v12_emdd_ref_fix.strategy import Regime
from strategies.v12_emdd_ref_fix.strategy import V12EMDDRefFixConfig
from strategies.v12_emdd_ref_fix.strategy import V12EMDDRefFixStrategy
from v10.core.config import load_config
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.core.types import Bar
from v10.core.types import Fill
from v10.core.types import MarketState
from v10.core.types import Side
from v10.core.types import Signal
from v10.strategies.v8_apex import Regime as V8Regime
from v10.strategies.v8_apex import V8ApexConfig
from v10.strategies.v8_apex import V8ApexStrategy
from validation.strategy_factory import STRATEGY_REGISTRY
from validation.strategy_factory import make_factory

H4_MS = 14_400_000


class _FakeFeed:
    def __init__(self, h4_bars: list[Bar], d1_bars: list[Bar] | None = None):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars or []


def _bar(index: int, open_: float, close: float, base_ms: int = 0) -> Bar:
    ot = base_ms + index * H4_MS
    return Bar(
        open_time=ot,
        open=open_,
        high=max(open_, close),
        low=min(open_, close),
        close=close,
        volume=100.0,
        close_time=ot + H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


class _EntryOnceV12(V12EMDDRefFixStrategy):
    """Minimal harness to force a single entry so on_after_fill can be verified."""

    def on_bar(self, state: MarketState) -> Signal | None:
        if state.bar_index == 0:
            return Signal(target_exposure=1.0, reason="entry")
        return None


def test_strategy_id_and_name_are_stable() -> None:
    strategy = V12EMDDRefFixStrategy(V12EMDDRefFixConfig())
    assert STRATEGY_ID == "v12_emdd_ref_fix"
    assert strategy.name() == "v12_emdd_ref_fix"


def test_validation_registry_contains_v12() -> None:
    assert "v12_emdd_ref_fix" in STRATEGY_REGISTRY
    strategy_cls, config_cls = STRATEGY_REGISTRY["v12_emdd_ref_fix"]
    assert strategy_cls is V12EMDDRefFixStrategy
    assert config_cls is V12EMDDRefFixConfig


def test_factory_builds_v12_strategy_from_config() -> None:
    root = Path(__file__).resolve().parents[2]
    cfg = load_config(root / "configs" / "v12" / "v12_emdd_ref_fix.yaml")
    factory = make_factory(cfg)
    strategy = factory()
    assert isinstance(strategy, V12EMDDRefFixStrategy)
    assert strategy.cfg.emdd_ref_mode == "legacy"
    assert strategy.cfg.rsi_method == "wilder"


def test_invalid_emdd_ref_mode_raises() -> None:
    try:
        V12EMDDRefFixConfig(emdd_ref_mode="invalid")
    except ValueError as exc:
        assert "emdd_ref_mode" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid emdd_ref_mode")


def test_emdd_ref_nav_true_is_set_from_post_fill_nav() -> None:
    bars = [
        _bar(0, 100.0, 100.0),
        _bar(1, 100.0, 100.0),  # entry fill happens at this bar open
        _bar(2, 100.0, 100.0),
        _bar(3, 100.0, 100.0),
    ]
    strategy = _EntryOnceV12(V12EMDDRefFixConfig())
    engine = BacktestEngine(
        feed=_FakeFeed(bars),
        strategy=strategy,
        cost=SCENARIOS["base"],
        initial_cash=10_000.0,
    )
    result = engine.run()

    assert len(result.fills) == 1
    assert result.fills[0].side == Side.BUY
    assert strategy._emdd_ref_nav_true > 0.0

    nav_after_entry = result.equity[1].nav_mid
    assert nav_after_entry < 10_000.0  # confirms post-cost NAV, not pre-cost legacy NAV
    assert strategy._emdd_ref_nav_true == pytest.approx(nav_after_entry, abs=1e-9)

    dd_at_entry = 1.0 - nav_after_entry / strategy._emdd_ref_nav_true
    assert dd_at_entry == pytest.approx(0.0, abs=1e-9)


def test_dd_starts_at_zero() -> None:
    bars = [
        _bar(0, 100.0, 100.0),
        _bar(1, 100.0, 100.0),  # opening BUY fill at this bar open
        _bar(2, 100.0, 100.0),
    ]
    strategy = _EntryOnceV12(
        V12EMDDRefFixConfig(
            emergency_dd_pct=1.0,
            enable_trail=False,
            enable_fixed_stop=False,
        ),
    )
    engine = BacktestEngine(
        feed=_FakeFeed(bars),
        strategy=strategy,
        cost=SCENARIOS["base"],
        initial_cash=10_000.0,
    )
    result = engine.run()

    assert len(result.fills) == 1
    nav_after_fill = result.equity[1].nav_mid
    dd_after_fill = 1.0 - nav_after_fill / strategy._emdd_ref_nav_true
    assert abs(dd_after_fill) <= 1e-6


def test_dd_scales_reasonably_with_price_move() -> None:
    bars = [
        _bar(0, 100.0, 100.0),
        _bar(1, 100.0, 100.0),  # opening BUY fill at this bar open
        _bar(2, 100.0, 95.0),   # hold constant position, price drops 5%
        _bar(3, 95.0, 95.0),
    ]
    strategy = _EntryOnceV12(
        V12EMDDRefFixConfig(
            emergency_dd_pct=1.0,
            enable_trail=False,
            enable_fixed_stop=False,
        ),
    )
    engine = BacktestEngine(
        feed=_FakeFeed(bars),
        strategy=strategy,
        cost=SCENARIOS["base"],
        initial_cash=10_000.0,
    )
    result = engine.run()

    assert len(result.fills) == 1
    entry_exposure = result.equity[1].exposure
    nav_after_drop = result.equity[2].nav_mid

    dd = 1.0 - nav_after_drop / strategy._emdd_ref_nav_true
    expected_dd = entry_exposure * 0.05
    assert dd == pytest.approx(expected_dd, abs=0.01)


def test_v10_baseline_unchanged_matches_out_golden_snapshot_identical() -> None:
    root = Path(__file__).resolve().parents[2]
    golden_dir = root / "out/golden" / "v10_baseline_frozen" / "2026-02-24"
    dataset = root / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
    config_path = root / "configs" / "frozen" / "v10_baseline.yaml"
    detail_path = golden_dir / "results" / "full_backtest_detail.json"

    if not detail_path.exists() or not dataset.exists() or not config_path.exists():
        pytest.skip("golden snapshot, dataset, or config is missing")

    golden = json.loads(detail_path.read_text(encoding="utf-8"))
    expected = golden["baseline"]

    cfg = load_config(config_path)
    factory = make_factory(cfg)
    feed = DataFeed(
        str(dataset),
        start="2019-01-01",
        end="2026-02-20",
        warmup_days=365,
    )

    for scenario in ("smart", "base", "harsh"):
        engine = BacktestEngine(
            feed=feed,
            strategy=factory(),
            cost=SCENARIOS[scenario],
            initial_cash=10_000.0,
            warmup_days=365,
            warmup_mode="no_trade",
            entry_nav_pre_cost=True,
        )
        result = engine.run()
        summary = result.summary
        target = expected[scenario]

        for key, value in summary.items():
            assert key in target
            assert value == target[key]
        assert len(result.fills) == int(target["fills"])


def test_emergency_dd_uses_emdd_ref_nav_true() -> None:
    cfg = V12EMDDRefFixConfig(
        emergency_dd_pct=0.05,
        enable_trail=False,
        enable_fixed_stop=False,
        emdd_ref_mode="fixed",
    )
    strategy = V12EMDDRefFixStrategy(cfg)
    strategy._emdd_ref_nav_true = 100.0

    bar = _bar(0, 100.0, 100.0)
    base_kwargs = dict(
        bar=bar,
        h4_bars=[bar],
        d1_bars=[],
        bar_index=0,
        d1_index=-1,
        cash=0.0,
        btc_qty=1.0,
        exposure=1.0,
        entry_price_avg=100.0,
        position_entry_nav=130.0,  # would false-trigger if legacy ref was used
    )

    state_no_trigger = MarketState(nav=97.0, **base_kwargs)
    signal = strategy._check_exit(
        state_no_trigger, idx=0, mid=100.0, regime=Regime.RISK_ON,
    )
    assert signal is None

    state_trigger = MarketState(nav=94.0, **base_kwargs)
    signal = strategy._check_exit(
        state_trigger, idx=0, mid=100.0, regime=Regime.RISK_ON,
    )
    assert signal is not None
    assert signal.reason == "emergency_dd"


def test_emdd_ref_mode_switch_changes_emergency_dd_behavior() -> None:
    legacy = V12EMDDRefFixStrategy(
        V12EMDDRefFixConfig(
            emergency_dd_pct=0.05,
            enable_trail=False,
            enable_fixed_stop=False,
            emdd_ref_mode="legacy",
        )
    )
    fixed = V12EMDDRefFixStrategy(
        V12EMDDRefFixConfig(
            emergency_dd_pct=0.05,
            enable_trail=False,
            enable_fixed_stop=False,
            emdd_ref_mode="fixed",
        )
    )
    legacy._emdd_ref_nav_true = 100.0
    fixed._emdd_ref_nav_true = 100.0

    bar = _bar(0, 100.0, 100.0)
    state = MarketState(
        bar=bar,
        h4_bars=[bar],
        d1_bars=[],
        bar_index=0,
        d1_index=-1,
        cash=0.0,
        btc_qty=1.0,
        nav=96.0,
        exposure=1.0,
        entry_price_avg=100.0,
        position_entry_nav=130.0,
    )

    legacy_signal = legacy._check_exit(state, idx=0, mid=100.0, regime=Regime.RISK_ON)
    fixed_signal = fixed._check_exit(state, idx=0, mid=100.0, regime=Regime.RISK_ON)
    assert legacy_signal is not None
    assert legacy_signal.reason == "emergency_dd"
    assert fixed_signal is None


def test_legacy_mode_matches_v10_pre_cost_emergency_reference_logic() -> None:
    v8 = V8ApexStrategy(
        V8ApexConfig(
            emergency_dd_pct=0.10,
            enable_trail=False,
            enable_fixed_stop=False,
            emergency_ref="pre_cost_legacy",
        )
    )
    v12 = V12EMDDRefFixStrategy(
        V12EMDDRefFixConfig(
            emergency_dd_pct=0.10,
            enable_trail=False,
            enable_fixed_stop=False,
            emdd_ref_mode="legacy",
        )
    )
    # Ensure any fixed-reference value would disagree if selected.
    v12._emdd_ref_nav_true = 10.0

    bar = _bar(0, 100.0, 100.0)
    base_kwargs = dict(
        bar=bar,
        h4_bars=[bar],
        d1_bars=[],
        bar_index=0,
        d1_index=-1,
        cash=0.0,
        btc_qty=1.0,
        exposure=1.0,
        entry_price_avg=100.0,
        position_entry_nav=100.0,
    )

    state_no_trigger = MarketState(nav=95.0, **base_kwargs)
    v8_sig = v8._check_exit(state_no_trigger, idx=0, mid=100.0, regime=V8Regime.RISK_ON)
    v12_sig = v12._check_exit(state_no_trigger, idx=0, mid=100.0, regime=Regime.RISK_ON)
    assert (v8_sig is None) == (v12_sig is None)

    state_trigger = MarketState(nav=89.9, **base_kwargs)
    v8_sig = v8._check_exit(state_trigger, idx=0, mid=100.0, regime=V8Regime.RISK_ON)
    v12_sig = v12._check_exit(state_trigger, idx=0, mid=100.0, regime=Regime.RISK_ON)
    assert v8_sig is not None and v8_sig.reason == "emergency_dd"
    assert v12_sig is not None and v12_sig.reason == "emergency_dd"


def test_on_after_fill_sets_ref_only_on_opening_buy() -> None:
    strategy = V12EMDDRefFixStrategy(V12EMDDRefFixConfig())
    bar = _bar(0, 100.0, 100.0)
    state = MarketState(
        bar=bar,
        h4_bars=[bar],
        d1_bars=[],
        bar_index=0,
        d1_index=-1,
        cash=1_000.0,
        btc_qty=0.5,
        nav=1_050.0,
        exposure=0.05,
        entry_price_avg=100.0,
        position_entry_nav=1_100.0,
    )
    buy_fill = Fill(
        ts_ms=bar.open_time,
        side=Side.BUY,
        qty=0.5,
        price=100.0,
        fee=0.1,
        notional=50.0,
        reason="entry",
    )
    strategy.on_after_fill(state, buy_fill)
    assert strategy._emdd_ref_nav_true == pytest.approx(1_050.0, abs=1e-9)

    later_buy_fill = Fill(
        ts_ms=bar.open_time + 1,
        side=Side.BUY,
        qty=0.1,
        price=101.0,
        fee=0.1,
        notional=10.1,
        reason="add",
    )
    strategy.on_after_fill(state, later_buy_fill)
    assert strategy._emdd_ref_nav_true == pytest.approx(1_050.0, abs=1e-9)
