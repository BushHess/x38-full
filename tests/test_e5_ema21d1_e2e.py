"""E2E tests for E5_ema21D1 — the PRIMARY promoted strategy.

Tests:
  1. Strategy instantiation and config binding
  2. Strategy registration in validation factory
  3. Full backtest run with real data → sane metrics
  4. Config YAML loads and produces valid strategy
  5. Backtest CLI registration gap (documents missing entry)
  6. Regime monitor integration (D1 regime filter causality)
"""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pytest

from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Config,
    VTrendE5Ema21D1Strategy,
)
from v10.core.types import Bar, MarketState, Fill

DATA_PATH = Path("data/bars_btcusdt_2016_now_h1_4h_1d.csv")
CONFIG_PATH = Path("configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml")


# =========================================================================
# Config
# =========================================================================


class TestConfig:
    def test_default_values(self):
        cfg = VTrendE5Ema21D1Config()
        assert cfg.slow_period == 120.0
        assert cfg.trail_mult == 3.0
        assert cfg.vdo_threshold == 0.0
        assert cfg.d1_ema_period == 21

    def test_robust_atr_structural_params(self):
        cfg = VTrendE5Ema21D1Config()
        assert cfg.ratr_cap_q == 0.90
        assert cfg.ratr_cap_lb == 100
        assert cfg.ratr_period == 20

    def test_no_vestigial_atr_period(self):
        """Config must NOT have atr_period (was removed in 2026-03-09 reform)."""
        cfg = VTrendE5Ema21D1Config()
        assert not hasattr(cfg, "atr_period"), "Vestigial atr_period still present!"

    def test_config_override(self):
        cfg = VTrendE5Ema21D1Config(slow_period=60, trail_mult=4.5)
        assert cfg.slow_period == 60
        assert cfg.trail_mult == 4.5


# =========================================================================
# Strategy Instantiation
# =========================================================================


class TestStrategyInstantiation:
    def test_default_init(self):
        s = VTrendE5Ema21D1Strategy()
        assert s.name() == "vtrend_e5_ema21_d1"

    def test_custom_config(self):
        cfg = VTrendE5Ema21D1Config(slow_period=60)
        s = VTrendE5Ema21D1Strategy(cfg)
        assert s._config.slow_period == 60

    def test_initial_state(self):
        s = VTrendE5Ema21D1Strategy()
        assert s._in_position is False
        assert s._peak_price == 0.0
        assert s._ema_fast is None


# =========================================================================
# Validation Factory Registration
# =========================================================================


class TestRegistration:
    def test_validation_factory_has_e5_ema21(self):
        """E5_ema21D1 must be in validation/strategy_factory.py registry."""
        from validation.strategy_factory import STRATEGY_REGISTRY
        assert "vtrend_e5_ema21_d1" in STRATEGY_REGISTRY

    def test_validation_factory_correct_class(self):
        from validation.strategy_factory import STRATEGY_REGISTRY
        cls, config_cls = STRATEGY_REGISTRY["vtrend_e5_ema21_d1"]
        assert cls is VTrendE5Ema21D1Strategy
        assert config_cls is VTrendE5Ema21D1Config

    def test_backtest_cli_has_entry(self):
        """E5_ema21D1 must be in backtest CLI registry."""
        from v10.cli.backtest import STRATEGY_REGISTRY as CLI_REGISTRY
        assert "vtrend_e5_ema21_d1" in CLI_REGISTRY

    def test_paper_cli_has_entry(self):
        """E5_ema21D1 must be in paper CLI registry."""
        from v10.cli.paper import STRATEGY_REGISTRY as PAPER_REGISTRY
        assert "vtrend_e5_ema21_d1" in PAPER_REGISTRY


# =========================================================================
# Config YAML Loading
# =========================================================================


class TestConfigYAML:
    @pytest.mark.skipif(not CONFIG_PATH.exists(), reason="Config YAML not found")
    def test_yaml_loads(self):
        from v10.core.config import load_config
        config = load_config(str(CONFIG_PATH))
        assert config.strategy.name == "vtrend_e5_ema21_d1"

    @pytest.mark.skipif(not CONFIG_PATH.exists(), reason="Config YAML not found")
    def test_yaml_params_match_defaults(self):
        from v10.core.config import load_config
        config = load_config(str(CONFIG_PATH))
        assert config.strategy.params["slow_period"] == 120.0
        assert config.strategy.params["trail_mult"] == 3.0
        assert config.strategy.params["vdo_threshold"] == 0.0
        assert config.strategy.params["d1_ema_period"] == 21

    @pytest.mark.skipif(not CONFIG_PATH.exists(), reason="Config YAML not found")
    def test_yaml_builds_strategy(self):
        from v10.core.config import load_config
        from validation.strategy_factory import build_from_config
        config = load_config(str(CONFIG_PATH))
        strategy, cfg = build_from_config(config)
        assert isinstance(strategy, VTrendE5Ema21D1Strategy)
        assert cfg.slow_period == 120.0


# =========================================================================
# Full Backtest (real data)
# =========================================================================


class TestFullBacktest:
    @pytest.mark.skipif(not DATA_PATH.exists(), reason="Data CSV not found")
    def test_backtest_runs_and_produces_trades(self):
        """Full E2E: load data → run strategy → check output sanity."""
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import SCENARIOS

        feed = DataFeed(
            str(DATA_PATH),
            start="2019-01-01",
            end="2026-02-20",
            warmup_days=365,
        )
        strategy = VTrendE5Ema21D1Strategy()
        cost = SCENARIOS["harsh"]  # 50 bps RT
        engine = BacktestEngine(
            feed=feed,
            strategy=strategy,
            cost=cost,
            initial_cash=10_000.0,
            warmup_mode="no_trade",
        )
        result = engine.run()

        s = result.summary
        # Sanity checks — NOT regression locks, just "did it work?"
        assert s["trades"] > 50, f"Too few trades: {s['trades']}"
        assert s["sharpe"] > 0.5, f"Sharpe too low: {s['sharpe']}"
        assert s["cagr_pct"] > 10.0, f"CAGR too low: {s['cagr_pct']}"
        assert s["max_drawdown_mid_pct"] < 80.0, f"MDD too high: {s['max_drawdown_mid_pct']}"
        assert s["avg_exposure"] > 0.1, f"Avg exposure too low: {s['avg_exposure']}"
        assert s["avg_exposure"] < 0.9, f"Avg exposure too high: {s['avg_exposure']}"

    @pytest.mark.skipif(not DATA_PATH.exists(), reason="Data CSV not found")
    def test_strategy_not_always_in_market(self):
        """D1 regime filter + VDO should prevent always-in-market behavior."""
        from v10.core.data import DataFeed
        from v10.core.engine import BacktestEngine
        from v10.core.types import SCENARIOS

        feed = DataFeed(
            str(DATA_PATH),
            start="2019-01-01",
            end="2026-02-20",
            warmup_days=365,
        )
        strategy = VTrendE5Ema21D1Strategy()
        cost = SCENARIOS["base"]
        engine = BacktestEngine(
            feed=feed,
            strategy=strategy,
            cost=cost,
            initial_cash=10_000.0,
            warmup_mode="no_trade",
        )
        result = engine.run()
        # Should have both entries and exits
        assert len(result.fills) > 10
        entry_reasons = [f.reason for f in result.fills if "entry" in f.reason]
        exit_reasons = [f.reason for f in result.fills if "exit" in f.reason or "trail" in f.reason]
        assert len(entry_reasons) > 0, "No entries!"
        assert len(exit_reasons) > 0, "No exits!"


# =========================================================================
# Strategy Logic Unit Tests (synthetic data)
# =========================================================================


def _make_bar(close, high=None, low=None, volume=100.0, taker_buy=50.0,
              close_time=0):
    """Create a minimal Bar for testing."""
    if high is None:
        high = close * 1.01
    if low is None:
        low = close * 0.99
    return Bar(
        open_time=close_time - 14400000,
        open=close,
        high=high,
        low=low,
        close=close,
        volume=volume,
        close_time=close_time,
        taker_buy_base_vol=taker_buy,
        interval="4h",
    )


class TestStrategyLogic:
    def test_no_signal_without_init(self):
        """on_bar before on_init → None."""
        s = VTrendE5Ema21D1Strategy()
        bar = _make_bar(100.0)
        state = MarketState(
            bar=bar, h4_bars=[], d1_bars=[], bar_index=0, d1_index=0,
            cash=10000.0, btc_qty=0.0, nav=10000.0, exposure=0.0,
            entry_price_avg=0.0, position_entry_nav=0.0,
        )
        assert s.on_bar(state) is None

    def test_on_init_computes_indicators(self):
        """on_init should populate indicator arrays."""
        s = VTrendE5Ema21D1Strategy()
        n = 200
        h4_bars = [_make_bar(100 + i * 0.1, close_time=i * 14400000) for i in range(n)]
        d1_bars = [_make_bar(100 + i * 0.4, close_time=i * 86400000) for i in range(n // 6)]
        s.on_init(h4_bars, d1_bars)

        assert s._ema_fast is not None
        assert s._ema_slow is not None
        assert s._ratr is not None
        assert s._vdo is not None
        assert s._d1_regime_ok is not None
        assert len(s._ema_fast) == n
        assert len(s._d1_regime_ok) == n

    def test_empty_d1_bars_regime_all_false(self):
        """No D1 data → regime filter blocks all entries."""
        s = VTrendE5Ema21D1Strategy()
        n = 200
        h4_bars = [_make_bar(100 + i * 0.1, close_time=i * 14400000) for i in range(n)]
        s.on_init(h4_bars, [])
        assert np.all(~s._d1_regime_ok)
