"""Regression tests: V8 vs V9 golden fixtures from data_export_v6_v8_v9.md.

Golden fixtures are the first 20 trades exported from the canonical V8 and V9
backtest runs.  Tests document and assert:
  1. Trades 1-8 converge (same exit_reason, timestamps within 1 H4 bar).
  2. Trade #9 is the FIRST divergence point — V8=emergency_dd, V9=trailing_stop.
  3. Cascading divergence pattern: V8 churns via emergency_dd (31 total),
     V9 holds to fixed_stop/trailing_stop (0 emergency_dd in first 20).
  4. Compatibility flags (--rsi_method, --emergency_ref) produce different outputs.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from v10.core.types import Bar, CostConfig, MarketState
from v10.core.execution import ExecutionModel, Portfolio
from v10.strategies.v8_apex import (
    V8ApexConfig, V8ApexStrategy, Regime, _rsi, _ema, _ema_wilder,
)

# ---------------------------------------------------------------------------
# Golden fixtures — extracted from data_export_v6_v8_v9.md §5–§6
# Format: (trade_id, entry_time, exit_time, entry_reason, exit_reason, pnl)
# ---------------------------------------------------------------------------

V8_GOLDEN_20 = [
    (1,  "2019-04-10 19:59", "2019-04-28 03:59", "vdo_trend_accel",  "trailing_stop",  88.66),
    (2,  "2019-04-28 23:59", "2019-05-17 03:59", "vdo_trend_accel",  "trailing_stop",  3838.43),
    (3,  "2019-05-19 03:59", "2019-06-03 23:59", "vdo_trend_accel",  "trailing_stop",  209.41),
    (4,  "2019-06-06 03:59", "2019-06-27 15:59", "vdo_trend_accel",  "trailing_stop",  6801.03),
    (5,  "2019-07-03 03:59", "2019-07-12 03:59", "vdo_trend_accel",  "trailing_stop",  -362.85),
    (6,  "2019-07-18 07:59", "2019-07-28 20:59", "vdo_trend_accel",  "trailing_stop",  -1193.76),
    (7,  "2019-07-29 07:59", "2019-08-10 11:59", "vdo_trend_accel",  "trailing_stop",  2939.73),
    (8,  "2019-08-16 15:59", "2019-08-21 15:59", "vdo_trend_accel",  "trailing_stop",  -821.68),
    (9,  "2019-08-23 15:59", "2019-08-28 19:59", "vdo_trend_accel",  "emergency_dd",   -965.14),
    (10, "2019-08-30 23:59", "2019-09-09 03:59", "vdo_trend_accel",  "trailing_stop",  1362.63),
    (11, "2019-09-11 23:59", "2019-09-19 03:59", "vdo_trend_accel",  "emergency_dd",   -899.92),
    (12, "2019-09-19 23:59", "2019-09-23 23:59", "vdo_trend_accel",  "emergency_dd",   -607.00),
    (13, "2019-09-25 23:59", "2019-11-01 03:59", "vdo_dip_buy",      "trailing_stop",  1847.76),
    (14, "2019-11-01 23:59", "2019-11-15 15:59", "vdo_trend",        "emergency_dd",   -1668.61),
    (15, "2019-11-17 03:59", "2019-11-21 15:59", "vdo_trend_accel",  "emergency_dd",   -728.00),
    (16, "2020-01-17 07:59", "2020-02-16 19:59", "vdo_trend_accel",  "trailing_stop",  1092.02),
    (17, "2020-02-18 15:59", "2020-02-26 03:59", "vdo_trend_accel",  "emergency_dd",   -1433.65),
    (18, "2020-02-28 23:59", "2020-03-08 11:59", "vdo_trend_accel",  "trailing_stop",  48.47),
    (19, "2020-03-11 03:59", "2020-03-12 11:59", "vdo_trend_accel",  "fixed_stop",     -1592.14),
    (20, "2020-05-01 07:59", "2020-05-10 03:59", "vdo_trend",        "trailing_stop",  -95.76),
]

V9_GOLDEN_20 = [
    (1,  "2019-04-10 19:59", "2019-04-28 03:59", "apex_vdo_trend_accel", "trailing_stop",  152.75),
    (2,  "2019-04-28 23:59", "2019-05-17 03:59", "apex_vdo_trend_accel", "trailing_stop",  3925.00),
    (3,  "2019-05-19 03:59", "2019-06-03 23:59", "apex_vdo_trend_accel", "trailing_stop",  233.54),
    (4,  "2019-06-06 03:59", "2019-06-27 15:59", "apex_vdo_trend_accel", "trailing_stop",  6885.28),
    (5,  "2019-07-03 03:59", "2019-07-12 03:59", "apex_vdo_trend_accel", "trailing_stop",  -367.35),
    (6,  "2019-07-18 07:59", "2019-07-28 20:59", "apex_vdo_trend_accel", "trailing_stop",  -1208.55),
    (7,  "2019-07-29 07:59", "2019-08-10 11:59", "apex_vdo_trend_accel", "trailing_stop",  2923.65),
    (8,  "2019-08-16 15:59", "2019-08-21 15:59", "apex_vdo_trend_accel", "trailing_stop",  -829.93),
    (9,  "2019-08-23 15:59", "2019-09-09 03:59", "apex_vdo_trend_accel", "trailing_stop",  353.86),
    (10, "2019-09-11 23:59", "2019-09-24 19:59", "apex_vdo_trend_accel", "fixed_stop",     -3962.58),
    (11, "2019-09-25 23:59", "2019-11-01 03:59", "apex_vdo_dip_buy",     "trailing_stop",  1240.93),
    (12, "2019-11-01 23:59", "2019-11-21 15:59", "apex_vdo_trend",       "fixed_stop",     -3076.81),
    (13, "2020-01-17 07:59", "2020-02-16 19:59", "apex_vdo_trend_accel", "trailing_stop",  980.14),
    (14, "2020-02-18 15:59", "2020-03-08 19:59", "apex_vdo_trend_accel", "fixed_stop",     -2716.53),
    (15, "2020-03-11 03:59", "2020-03-12 11:59", "apex_vdo_trend_accel", "fixed_stop",     -1183.22),
    (16, "2020-05-01 07:59", "2020-05-10 03:59", "apex_vdo_trend",       "trailing_stop",  -126.44),
    (17, "2020-05-17 15:59", "2020-06-04 07:59", "apex_vdo_trend_accel", "trailing_stop",  39.91),
    (18, "2020-06-04 19:59", "2020-08-02 23:59", "apex_vdo_trend",       "trailing_stop",  1877.87),
    (19, "2020-08-10 03:59", "2020-09-05 19:59", "apex_vdo_trend_accel", "fixed_stop",     -2382.60),
    (20, "2020-09-06 07:59", "2020-09-21 15:59", "apex_vdo_trend_accel", "trailing_stop",  153.90),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

H4_BAR_SECS = 4 * 3600  # 14400 seconds — one H4 bar
H4_MS = 14_400_000
D1_MS = 86_400_000


def _parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def _h4(i: int, price: float, taker: float = 55.0) -> Bar:
    ot = i * H4_MS
    return Bar(
        open_time=ot, open=price, high=price * 1.001, low=price * 0.999,
        close=price, volume=100.0, close_time=ot + H4_MS - 1,
        taker_buy_base_vol=taker, interval="4h",
    )


def _d1(i: int, price: float) -> Bar:
    ot = i * D1_MS
    return Bar(
        open_time=ot, open=price, high=price * 1.001, low=price * 0.999,
        close=price, volume=600.0, close_time=ot + D1_MS - 1,
        taker_buy_base_vol=300.0, interval="1d",
    )


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


def _init_strat(cfg: V8ApexConfig | None = None) -> V8ApexStrategy:
    strat = V8ApexStrategy(cfg)
    h4 = [_h4(i, 50_000.0) for i in range(100)]
    d1 = [_d1(i, 50_000.0) for i in range(20)]
    strat.on_init(h4, d1)
    return strat


# ---------------------------------------------------------------------------
# TEST 1: Golden fixture integrity
# ---------------------------------------------------------------------------

class TestGoldenFixtureIntegrity:
    """Verify golden fixture data is self-consistent."""

    def test_v8_has_20_trades(self) -> None:
        assert len(V8_GOLDEN_20) == 20

    def test_v9_has_20_trades(self) -> None:
        assert len(V9_GOLDEN_20) == 20

    def test_v8_trade_ids_sequential(self) -> None:
        for i, t in enumerate(V8_GOLDEN_20):
            assert t[0] == i + 1

    def test_v9_trade_ids_sequential(self) -> None:
        for i, t in enumerate(V9_GOLDEN_20):
            assert t[0] == i + 1

    def test_v8_exit_after_entry(self) -> None:
        for t in V8_GOLDEN_20:
            assert _parse_ts(t[2]) > _parse_ts(t[1]), f"Trade {t[0]}"

    def test_v9_exit_after_entry(self) -> None:
        for t in V9_GOLDEN_20:
            assert _parse_ts(t[2]) > _parse_ts(t[1]), f"Trade {t[0]}"


# ---------------------------------------------------------------------------
# TEST 2: Trades 1-8 converge
# ---------------------------------------------------------------------------

class TestTradesConverge1to8:
    """Trades 1-8 should have matching timestamps and exit reasons."""

    def test_exit_reasons_match(self) -> None:
        """V8 and V9 have the same exit_reason for trades 1-8."""
        for i in range(8):
            v8_reason = V8_GOLDEN_20[i][4]
            v9_reason = V9_GOLDEN_20[i][4]
            assert v8_reason == v9_reason, (
                f"Trade {i + 1}: V8={v8_reason}, V9={v9_reason}")

    def test_entry_timestamps_within_1_bar(self) -> None:
        """Entry timestamps match within 1 H4 bar (4 hours)."""
        for i in range(8):
            v8_t = _parse_ts(V8_GOLDEN_20[i][1])
            v9_t = _parse_ts(V9_GOLDEN_20[i][1])
            diff = abs((v8_t - v9_t).total_seconds())
            assert diff <= H4_BAR_SECS, (
                f"Trade {i + 1}: entry diff {diff}s > {H4_BAR_SECS}s")

    def test_exit_timestamps_within_1_bar(self) -> None:
        """Exit timestamps match within 1 H4 bar (4 hours)."""
        for i in range(8):
            v8_t = _parse_ts(V8_GOLDEN_20[i][2])
            v9_t = _parse_ts(V9_GOLDEN_20[i][2])
            diff = abs((v8_t - v9_t).total_seconds())
            assert diff <= H4_BAR_SECS, (
                f"Trade {i + 1}: exit diff {diff}s > {H4_BAR_SECS}s")

    def test_pnl_sign_matches(self) -> None:
        """Winning/losing classification matches for trades 1-8."""
        for i in range(8):
            v8_pnl = V8_GOLDEN_20[i][5]
            v9_pnl = V9_GOLDEN_20[i][5]
            assert (v8_pnl > 0) == (v9_pnl > 0), (
                f"Trade {i + 1}: V8 pnl={v8_pnl:.2f}, V9 pnl={v9_pnl:.2f}")


# ---------------------------------------------------------------------------
# TEST 3: Trade #9 — first divergence point
# ---------------------------------------------------------------------------

class TestDivergenceAtTrade9:
    """Trade #9 is the first major divergence between V8 and V9."""

    def test_same_entry_time(self) -> None:
        """Both versions enter trade #9 at the same time."""
        v8_entry = _parse_ts(V8_GOLDEN_20[8][1])
        v9_entry = _parse_ts(V9_GOLDEN_20[8][1])
        assert v8_entry == v9_entry

    def test_v8_trade9_emergency_dd(self) -> None:
        assert V8_GOLDEN_20[8][4] == "emergency_dd"

    def test_v9_trade9_trailing_stop(self) -> None:
        assert V9_GOLDEN_20[8][4] == "trailing_stop"

    def test_v8_exits_earlier_than_v9(self) -> None:
        """V8 emergency_dd fires early (08-28), V9 holds to trailing_stop (09-09)."""
        v8_exit = _parse_ts(V8_GOLDEN_20[8][2])
        v9_exit = _parse_ts(V9_GOLDEN_20[8][2])
        assert v8_exit < v9_exit
        # V8 exits ~12 days earlier
        diff_days = (v9_exit - v8_exit).total_seconds() / 86400
        assert diff_days > 10, f"Expected >10 day gap, got {diff_days:.1f}"

    def test_v8_loss_v9_profit(self) -> None:
        """V8 emergency_dd causes a loss; V9 holds through and profits."""
        assert V8_GOLDEN_20[8][5] < 0, "V8 trade 9 should be a loss"
        assert V9_GOLDEN_20[8][5] > 0, "V9 trade 9 should be a profit"

    def test_no_divergence_before_trade_9(self) -> None:
        """Trades 1-8 have identical exit reasons (the divergence is EXACTLY #9)."""
        for i in range(8):
            assert V8_GOLDEN_20[i][4] == V9_GOLDEN_20[i][4]
        # Trade 9 is different
        assert V8_GOLDEN_20[8][4] != V9_GOLDEN_20[8][4]


# ---------------------------------------------------------------------------
# TEST 4: Cascading divergence pattern
# ---------------------------------------------------------------------------

class TestDivergenceCascade:
    """V8 emergency_dd churn vs V9 hold-to-stop pattern."""

    def test_v8_emergency_dd_count(self) -> None:
        """V8 has 6 emergency_dd exits in first 20 trades."""
        count = sum(1 for t in V8_GOLDEN_20 if t[4] == "emergency_dd")
        assert count == 6, f"Expected 6 emergency_dd, got {count}"

    def test_v9_zero_emergency_dd(self) -> None:
        """V9 has 0 emergency_dd exits in first 20 trades."""
        count = sum(1 for t in V9_GOLDEN_20 if t[4] == "emergency_dd")
        assert count == 0, f"Expected 0 emergency_dd, got {count}"

    def test_v8_no_emergency_dd_before_trade_9(self) -> None:
        """All 6 emergency_dd exits occur at trade #9 or later."""
        for i in range(8):
            assert V8_GOLDEN_20[i][4] != "emergency_dd", f"Trade {i + 1}"

    def test_v8_churn_trades_10_12(self) -> None:
        """V8 trades 10-12 span ~same period as V9 trade 10.
        V8: 3 trades (net -$140) vs V9: 1 trade (-$3963)."""
        # V8 trades 10, 11, 12 exit reasons
        assert V8_GOLDEN_20[9][4] == "trailing_stop"    # trade 10
        assert V8_GOLDEN_20[10][4] == "emergency_dd"    # trade 11
        assert V8_GOLDEN_20[11][4] == "emergency_dd"    # trade 12

        # V9 trade 10 is a single fixed_stop
        assert V9_GOLDEN_20[9][4] == "fixed_stop"

        # V8 trade 12 exit and V9 trade 10 exit within ~24h
        v8_t12_exit = _parse_ts(V8_GOLDEN_20[11][2])  # trade 12 exit
        v9_t10_exit = _parse_ts(V9_GOLDEN_20[9][2])    # trade 10 exit
        diff_h = abs((v8_t12_exit - v9_t10_exit).total_seconds()) / 3600
        assert diff_h <= 24, f"V8 #12 exit vs V9 #10 exit: {diff_h:.0f}h apart"

    def test_v8_covid_churn(self) -> None:
        """V8 trades 17-18 (pre-COVID) vs V9 trade 14: emergency_dd splits."""
        # V8 #17: emergency_dd, V8 #18: trailing_stop
        assert V8_GOLDEN_20[16][4] == "emergency_dd"     # trade 17
        assert V8_GOLDEN_20[17][4] == "trailing_stop"    # trade 18
        # V9 #14: holds through to fixed_stop
        assert V9_GOLDEN_20[13][4] == "fixed_stop"       # trade 14

    def test_v9_exit_reason_distribution(self) -> None:
        """V9 uses only trailing_stop and fixed_stop (no emergency_dd)."""
        reasons = {t[4] for t in V9_GOLDEN_20}
        assert reasons == {"trailing_stop", "fixed_stop"}


# ---------------------------------------------------------------------------
# TEST 5: Compatibility flags — rsi_method
# ---------------------------------------------------------------------------

class TestRsiMethod:
    """--rsi_method {wilder, ewm_span} produces different RSI values."""

    def test_wilder_differs_from_ewm_span(self) -> None:
        """Wilder's RSI (alpha=1/p) differs from EWM span (alpha=2/(p+1))."""
        prices = np.array([
            100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
            111, 110, 112, 114, 113, 115, 117, 116, 118, 120,
        ], dtype=np.float64)
        rsi_ewm = _rsi(prices, 14, method="ewm_span")
        rsi_wilder = _rsi(prices, 14, method="wilder")
        assert not np.allclose(rsi_ewm, rsi_wilder), \
            "Wilder and EWM span should produce different RSI values"

    def test_wilder_smoother_than_ewm(self) -> None:
        """Wilder (alpha=1/14≈0.071) is smoother than EWM (alpha=2/15≈0.133)."""
        prices = np.array([
            100, 105, 100, 105, 100, 105, 100, 105, 100, 105,
            100, 105, 100, 105, 100, 105, 100, 105, 100, 105,
        ], dtype=np.float64)
        rsi_ewm = _rsi(prices, 14, method="ewm_span")
        rsi_wilder = _rsi(prices, 14, method="wilder")
        # Wilder should have lower variance (more smoothing)
        assert np.std(rsi_wilder[14:]) < np.std(rsi_ewm[14:])

    def test_strategy_uses_config_rsi_method(self) -> None:
        """V8ApexStrategy respects rsi_method in config."""
        cfg_ewm = V8ApexConfig(rsi_method="ewm_span")
        cfg_wilder = V8ApexConfig(rsi_method="wilder")

        strat_ewm = V8ApexStrategy(cfg_ewm)
        strat_wilder = V8ApexStrategy(cfg_wilder)

        # Oscillating prices so RSI actually differs between methods
        prices = [50_000 + (-1)**i * 500 * (i % 7) for i in range(100)]
        h4 = [_h4(i, prices[i]) for i in range(100)]
        d1 = [_d1(i, 50_000.0) for i in range(20)]

        strat_ewm.on_init(h4, d1)
        strat_wilder.on_init(h4, d1)

        assert not np.allclose(strat_ewm._h4_rsi, strat_wilder._h4_rsi), \
            "Strategy RSI arrays should differ between methods"


# ---------------------------------------------------------------------------
# TEST 6: Compatibility flags — emergency_ref
# ---------------------------------------------------------------------------

class TestEmergencyRef:
    """--emergency_ref {pre_cost_legacy, post_cost, peak} changes DD behavior."""

    def test_peak_more_aggressive_than_entry_nav(self) -> None:
        """With emergency_ref=peak, DD triggers when nav drops from position
        peak even if position_entry_nav would show smaller drawdown."""
        cfg = V8ApexConfig(
            emergency_dd_pct=0.20,
            enable_trail=False, enable_fixed_stop=False,
            emergency_ref="peak",
        )
        strat = _init_strat(cfg)
        strat._was_in_position = True
        # Position opened at nav=10000, peaked at nav=12000, now at 9500
        strat._position_nav_peak = 12_000.0

        # DD from peak: 1 - 9500/12000 = 20.8% ≥ 20% → triggers
        sig = strat._check_exit(
            _make_state(50, 47_500.0, nav=9_500.0, entry_nav=10_000.0),
            50, 47_500.0, Regime.RISK_ON,
        )
        assert sig is not None
        assert sig.reason == "emergency_dd"

    def test_entry_nav_would_not_trigger_same_scenario(self) -> None:
        """Same scenario as above but with pre_cost_legacy — no trigger."""
        cfg = V8ApexConfig(
            emergency_dd_pct=0.20,
            enable_trail=False, enable_fixed_stop=False,
            emergency_ref="pre_cost_legacy",
        )
        strat = _init_strat(cfg)
        strat._was_in_position = True
        strat._position_nav_peak = 12_000.0  # ignored in pre_cost_legacy

        # DD from entry: 1 - 9500/10000 = 5% < 20% → no trigger
        sig = strat._check_exit(
            _make_state(50, 47_500.0, nav=9_500.0, entry_nav=10_000.0),
            50, 47_500.0, Regime.RISK_ON,
        )
        assert sig is None

    def test_post_cost_portfolio_stores_lower_nav(self) -> None:
        """Portfolio with entry_nav_pre_cost=False stores lower position_entry_nav."""
        cost = CostConfig(spread_bps=5.0, slippage_bps=3.0, taker_fee_pct=0.10)
        pf_pre = Portfolio(10_000.0, ExecutionModel(cost), entry_nav_pre_cost=True)
        pf_post = Portfolio(10_000.0, ExecutionModel(cost), entry_nav_pre_cost=False)

        pf_pre.buy(0.1, 50_000.0, 1000, "test")
        pf_post.buy(0.1, 50_000.0, 1000, "test")

        # Pre-cost = true pre-fill NAV (initial cash when entering from flat).
        # Post-cost = NAV after fill (cash reduced, BTC added).
        assert pf_pre.position_entry_nav > pf_post.position_entry_nav
        diff = pf_pre.position_entry_nav - pf_post.position_entry_nav
        assert diff > 0, "pre_cost should produce higher entry NAV"

        # Absolute value checks: pre-cost should equal initial cash (entering
        # from flat), post-cost should equal nav(mid) after fill.
        assert pf_pre.position_entry_nav == pytest.approx(10_000.0, abs=0.01)
        assert pf_post.position_entry_nav == pytest.approx(pf_post.nav(50_000.0), abs=0.01)

    def test_peak_tracks_max_nav_during_position(self) -> None:
        """_position_nav_peak correctly tracks max NAV while in position."""
        cfg = V8ApexConfig(emergency_ref="peak")
        strat = V8ApexStrategy(cfg)
        h4 = [_h4(i, 50_000.0) for i in range(100)]
        d1 = [_d1(i, 50_000.0) for i in range(20)]
        strat.on_init(h4, d1)

        # Simulate position open
        s1 = _make_state(10, 50_000.0, btc_qty=0.2, nav=10_000.0)
        strat.on_bar(s1)
        assert strat._position_nav_peak == 10_000.0

        # NAV rises
        s2 = _make_state(11, 55_000.0, btc_qty=0.2, nav=11_000.0)
        strat.on_bar(s2)
        assert strat._position_nav_peak == 11_000.0

        # NAV drops — peak stays
        s3 = _make_state(12, 48_000.0, btc_qty=0.2, nav=9_600.0)
        strat.on_bar(s3)
        assert strat._position_nav_peak == 11_000.0

    def test_peak_resets_on_position_close(self) -> None:
        """_position_nav_peak resets to 0 when position fully closes."""
        cfg = V8ApexConfig(emergency_ref="peak")
        strat = V8ApexStrategy(cfg)
        h4 = [_h4(i, 50_000.0) for i in range(100)]
        d1 = [_d1(i, 50_000.0) for i in range(20)]
        strat.on_init(h4, d1)

        # Open position, build peak
        strat.on_bar(_make_state(10, 50_000.0, btc_qty=0.2, nav=10_000.0))
        strat.on_bar(_make_state(11, 55_000.0, btc_qty=0.2, nav=11_000.0))
        assert strat._position_nav_peak == 11_000.0

        # Close position (btc_qty = 0)
        strat.on_bar(_make_state(12, 50_000.0, btc_qty=0.0, nav=10_000.0))
        assert strat._position_nav_peak == 0.0


# ---------------------------------------------------------------------------
# TEST 7: _ema_wilder helper
# ---------------------------------------------------------------------------

class TestEmaWilder:
    """Verify _ema_wilder uses alpha=1/p (distinct from standard _ema)."""

    def test_different_from_standard_ema(self) -> None:
        a = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
        assert not np.allclose(_ema(a, 5), _ema_wilder(a, 5))

    def test_wilder_alpha_equals_1_over_p(self) -> None:
        """_ema_wilder(p=10) should use alpha=0.1 exactly."""
        a = np.array([10.0, 20.0], dtype=np.float64)
        result = _ema_wilder(a, 10)
        # out[0] = 10.0
        # out[1] = 0.1 * 20 + 0.9 * 10 = 2 + 9 = 11.0
        assert result[0] == 10.0
        assert result[1] == pytest.approx(11.0)
