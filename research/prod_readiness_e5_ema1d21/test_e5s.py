#!/usr/bin/env python3
"""Tests for E5S strategy and validation pipeline."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from strategies.vtrend_e5s_ema21_d1.strategy import (
    VTrendE5SEma21D1Config, VTrendE5SEma21D1Strategy, _ema, _atr, _vdo,
)
from research.prod_readiness_e5_ema1d21.e5s_validation import (
    sim_x0, sim_e5, sim_e5s, _metrics, _objective,
)


# =========================================================================
# Strategy config
# =========================================================================

class TestE5SConfig:
    def test_default_atr_period_is_20(self):
        cfg = VTrendE5SEma21D1Config()
        assert cfg.atr_period == 20

    def test_no_robust_atr_params(self):
        cfg = VTrendE5SEma21D1Config()
        assert not hasattr(cfg, "ratr_cap_q")
        assert not hasattr(cfg, "ratr_cap_lb")
        assert not hasattr(cfg, "ratr_period")

    def test_tunable_params_match_e5(self):
        cfg = VTrendE5SEma21D1Config()
        assert cfg.slow_period == 120.0
        assert cfg.trail_mult == 3.0
        assert cfg.vdo_threshold == 0.0
        assert cfg.d1_ema_period == 21


# =========================================================================
# Indicator parity
# =========================================================================

class TestIndicators:
    def test_atr20_vs_atr14_different(self):
        """ATR(20) and ATR(14) should produce different values."""
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(200) * 2)
        high = close + np.abs(np.random.randn(200))
        low = close - np.abs(np.random.randn(200))

        atr14 = _atr(high, low, close, 14)
        atr20 = _atr(high, low, close, 20)

        # Different warmup periods
        assert np.isnan(atr14[12])
        assert not np.isnan(atr14[13])
        assert np.isnan(atr20[18])
        assert not np.isnan(atr20[19])

        # Values should differ where both are valid
        valid = ~np.isnan(atr14) & ~np.isnan(atr20)
        assert not np.allclose(atr14[valid], atr20[valid])

    def test_ema_basic(self):
        """EMA of constant = constant."""
        arr = np.full(100, 50.0)
        out = _ema(arr, 20)
        assert np.allclose(out, 50.0)


# =========================================================================
# Sim parity: E5S uses ATR(20), E5 uses robust ATR
# =========================================================================

class TestSimParity:
    @pytest.fixture(scope="class")
    def data(self):
        from v10.core.data import DataFeed
        DATA = str(ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
        feed = DataFeed(DATA, start="2019-01-01", end="2026-02-20", warmup_days=365)
        cl = np.array([b.close for b in feed.h4_bars], dtype=np.float64)
        hi = np.array([b.high for b in feed.h4_bars], dtype=np.float64)
        lo = np.array([b.low for b in feed.h4_bars], dtype=np.float64)
        vo = np.array([b.volume for b in feed.h4_bars], dtype=np.float64)
        tb = np.array([b.taker_buy_base_vol for b in feed.h4_bars], dtype=np.float64)
        h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)
        d1_cl = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
        d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)
        wi = 0
        if feed.report_start_ms is not None:
            for j, b in enumerate(feed.h4_bars):
                if b.close_time >= feed.report_start_ms:
                    wi = j
                    break
        return cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct

    def test_e5s_differs_from_e5(self, data):
        """E5S (standard ATR(20)) should differ from E5 (robust ATR)."""
        cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct = data
        nav_e5, nt_e5 = sim_e5(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        nav_e5s, nt_e5s = sim_e5s(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        # Trade counts should differ (robust ATR gives different trail)
        assert nt_e5 != nt_e5s or not np.allclose(nav_e5, nav_e5s)

    def test_e5s_differs_from_x0(self, data):
        """E5S (ATR(20)) should differ from X0 (ATR(14))."""
        cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct = data
        nav_x0, nt_x0 = sim_x0(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        nav_e5s, nt_e5s = sim_e5s(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        assert nt_x0 != nt_e5s or not np.allclose(nav_x0, nav_e5s)

    def test_e5s_positive_sharpe(self, data):
        """E5S should produce positive Sharpe (sanity check)."""
        cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct = data
        nav, nt = sim_e5s(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct)
        m = _metrics(nav, wi)
        assert m["sharpe"] > 0.5, f"E5S Sharpe too low: {m['sharpe']}"
        assert m["cagr"] > 0, "E5S CAGR should be positive"
        assert nt > 50, f"Too few trades: {nt}"

    def test_e5s_trade_tracking(self, data):
        """Trade tracking should work correctly."""
        cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct = data
        nav, nt, trades = sim_e5s(cl, hi, lo, vo, tb, wi, d1_cl, d1_ct, h4_ct,
                                   return_trades=True)
        assert len(trades) == nt
        assert all("pnl_usd" in t for t in trades)
        assert all("return_pct" in t for t in trades)


# =========================================================================
# Metrics
# =========================================================================

class TestMetrics:
    def test_constant_nav(self):
        """Constant NAV → Sharpe=0, CAGR=0, MDD=0."""
        nav = np.full(1000, 10000.0)
        m = _metrics(nav, 0)
        assert m["sharpe"] == 0.0
        assert m["cagr"] == pytest.approx(0.0, abs=0.01)
        assert m["mdd"] == pytest.approx(0.0, abs=0.01)

    def test_growing_nav(self):
        """Growing NAV → positive Sharpe and CAGR."""
        nav = np.linspace(10000, 20000, 2190)  # ~1 year of H4
        m = _metrics(nav, 0)
        assert m["sharpe"] > 0
        assert m["cagr"] > 0
        assert m["mdd"] == pytest.approx(0.0, abs=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
