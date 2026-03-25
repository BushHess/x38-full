"""Engine invariant tests — 6 mandatory tests with synthetic OHLCV data.

Each test constructs small (10–50 bar) synthetic datasets with known prices,
runs the engine, then asserts exact arithmetic against hand-computed values.

Invariants tested:
  1. AlwaysFlat      — No signals ⇒ NAV ≡ initial_cash, 0 fills, 0 exposure
  2. BuyHold         — Single buy (zero cost), NAV tracks price exactly
  3. SingleRoundTripFee — Buy+sell on flat price, cash loss = total fees
  4. NextOpenFill    — Fill price = bar[t+1].open, NOT bar[t].close
  5. FeeNoDoubleCount — Cash reconstructed from fills matches portfolio cash
  6. PortfolioAccounting — Balance-sheet identity + btc conservation at every snap
"""

from __future__ import annotations

import pytest

from v10.core.types import Bar, CostConfig, Order, Side, Signal, MarketState
from v10.core.engine import BacktestEngine
from v10.core.execution import ExecutionModel
from v10.strategies.base import Strategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

H4_MS = 14_400_000  # 4 hours in milliseconds


class _FakeFeed:
    """Minimal DataFeed substitute — no CSV, just lists of Bar."""

    def __init__(self, h4_bars: list[Bar], d1_bars: list[Bar] | None = None):
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars or []


def _bar(index: int, open_: float, close: float, base_ms: int = 0) -> Bar:
    ot = base_ms + index * H4_MS
    return Bar(
        open_time=ot,
        open=open_,
        high=max(open_, close) * 1.001,
        low=min(open_, close) * 0.999,
        close=close,
        volume=100.0,
        close_time=ot + H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


def _flat_bars(n: int, price: float, base_ms: int = 0) -> list[Bar]:
    return [_bar(i, price, price, base_ms) for i in range(n)]


class _NullStrategy(Strategy):
    """Never emits a signal."""

    def on_bar(self, state: MarketState) -> Signal | None:
        return None


class _ScriptedStrategy(Strategy):
    """Emits pre-defined signals at specific bar indices."""

    def __init__(self, script: dict[int, Signal]) -> None:
        self._script = script

    def on_bar(self, state: MarketState) -> Signal | None:
        return self._script.get(state.bar_index)


# Named cost configs for tests
ZERO_COST = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=0.0)
FEE_ONLY_1PCT = CostConfig(spread_bps=0.0, slippage_bps=0.0, taker_fee_pct=1.0)
BASE_COST = CostConfig(spread_bps=5.0, slippage_bps=3.0, taker_fee_pct=0.10)


def _run(bars: list[Bar], strategy: Strategy, cost: CostConfig,
         initial: float = 10_000.0):
    feed = _FakeFeed(bars)
    engine = BacktestEngine(feed, strategy, cost, initial_cash=initial,
                            warmup_days=0)
    return engine.run()


# ---------------------------------------------------------------------------
# INV-1: AlwaysFlat
# ---------------------------------------------------------------------------

class TestAlwaysFlat:
    """A strategy that never trades must leave the portfolio untouched.
    NAV ≡ initial_cash, 0 fills, 0 trades, exposure ≡ 0 at every snapshot.
    """

    def test_no_trades_constant_nav(self) -> None:
        PRICE, CASH, N = 50_000.0, 10_000.0, 20
        result = _run(_flat_bars(N, PRICE), _NullStrategy(), BASE_COST, CASH)

        assert len(result.fills) == 0, (
            f"Expected 0 fills, got {len(result.fills)}")
        assert len(result.trades) == 0, (
            f"Expected 0 trades, got {len(result.trades)}")
        assert len(result.equity) == N, (
            f"Expected {N} equity snaps, got {len(result.equity)}")

        for i, snap in enumerate(result.equity):
            assert snap.nav_mid == pytest.approx(CASH, abs=0.001), (
                f"Snap[{i}]: nav_mid expected {CASH}, got {snap.nav_mid}")
            assert snap.cash == pytest.approx(CASH, abs=0.001), (
                f"Snap[{i}]: cash expected {CASH}, got {snap.cash}")
            assert snap.btc_qty == pytest.approx(0.0, abs=1e-12), (
                f"Snap[{i}]: btc_qty expected 0, got {snap.btc_qty}")
            assert snap.exposure == pytest.approx(0.0, abs=1e-12), (
                f"Snap[{i}]: exposure expected 0, got {snap.exposure}")

    def test_no_trades_varying_price(self) -> None:
        """Even with volatile prices, a null strategy must never trade."""
        CASH = 10_000.0
        bars = [_bar(i, 40000 + i * 1000, 40500 + i * 1000) for i in range(15)]
        result = _run(bars, _NullStrategy(), ZERO_COST, CASH)

        assert len(result.fills) == 0
        for snap in result.equity:
            assert snap.nav_mid == pytest.approx(CASH, abs=0.001)
            assert snap.btc_qty == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# INV-2: BuyHold
# ---------------------------------------------------------------------------

class TestBuyHold:
    """Buy full exposure once (zero cost). After entry:
      - NAV ≡ btc_qty × close  (cash = 0)
      - Price appreciation flows through exactly
    """

    def test_buy_hold_zero_cost_flat_then_rise(self) -> None:
        CASH, P_FLAT, P_HIGH = 10_000.0, 50_000.0, 60_000.0

        bars = _flat_bars(10, P_FLAT) + _flat_bars(5, P_HIGH,
                                                    base_ms=10 * H4_MS)
        strategy = _ScriptedStrategy({
            0: Signal(target_exposure=1.0, reason="buy"),
        })
        result = _run(bars, strategy, ZERO_COST, CASH)

        # ── 1 fill only ──
        assert len(result.fills) == 1, (
            f"Expected 1 fill, got {len(result.fills)}")
        fill = result.fills[0]
        assert fill.side == Side.BUY

        # ── fill at bar[1].open = P_FLAT, zero cost ──
        assert fill.price == pytest.approx(P_FLAT, abs=0.01), (
            f"Fill price expected {P_FLAT} (bar[1].open), got {fill.price}")

        expected_qty = CASH / P_FLAT   # 0.2 BTC
        assert fill.qty == pytest.approx(expected_qty, abs=1e-8), (
            f"Qty expected {expected_qty}, got {fill.qty}")
        assert fill.fee == pytest.approx(0.0, abs=1e-10), (
            f"Fee expected 0 (zero cost), got {fill.fee}")

        # ── snap[0]: before fill (signal bar), still flat ──
        assert result.equity[0].cash == pytest.approx(CASH, abs=0.01)
        assert result.equity[0].btc_qty == pytest.approx(0.0, abs=1e-10)

        # ── snap[1..9]: post-fill, flat price period ──
        for i in range(1, 10):
            s = result.equity[i]
            assert s.cash == pytest.approx(0.0, abs=0.01), (
                f"Snap[{i}]: cash expected 0 after full buy, got {s.cash}")
            assert s.btc_qty == pytest.approx(expected_qty, abs=1e-8)
            assert s.nav_mid == pytest.approx(CASH, abs=0.01), (
                f"Snap[{i}]: NAV should be {CASH} at flat price, "
                f"got {s.nav_mid}")

        # ── snap[10..14]: price rose, NAV must reflect it ──
        expected_nav_high = expected_qty * P_HIGH   # 0.2 × 60000 = 12000
        for i in range(10, 15):
            assert result.equity[i].nav_mid == pytest.approx(
                expected_nav_high, abs=0.01), (
                f"Snap[{i}]: NAV expected {expected_nav_high} at P={P_HIGH}, "
                f"got {result.equity[i].nav_mid}")

        # ── still holding → no trade record ──
        assert len(result.trades) == 0


# ---------------------------------------------------------------------------
# INV-3: SingleRoundTripFee
# ---------------------------------------------------------------------------

class TestSingleRoundTripFee:
    """Buy 0.1 BTC + sell 0.1 BTC on flat price with fee-only cost (1%).
    Zero spread, zero slippage  ⇒  fill_px = mid.
    On flat price: cash loss must equal total fees exactly.
    """

    def test_round_trip_fee_exact(self) -> None:
        PRICE, CASH, QTY = 40_000.0, 10_000.0, 0.1
        FEE_PCT = 1.0          # 1 %
        FEE_RATE = FEE_PCT / 100.0   # 0.01

        bars = _flat_bars(10, PRICE)
        strategy = _ScriptedStrategy({
            0: Signal(orders=[Order(Side.BUY, QTY)], reason="open"),
            4: Signal(orders=[Order(Side.SELL, QTY)], reason="close"),
        })
        result = _run(bars, strategy, FEE_ONLY_1PCT, CASH)

        # ── exactly 2 fills ──
        assert len(result.fills) == 2
        buy, sell = result.fills[0], result.fills[1]
        assert buy.side == Side.BUY
        assert sell.side == Side.SELL

        # ── fill_px = mid (zero spread / zero slip) ──
        assert buy.price == pytest.approx(PRICE, abs=0.01), (
            f"Buy fill_px expected {PRICE}, got {buy.price}")
        assert sell.price == pytest.approx(PRICE, abs=0.01), (
            f"Sell fill_px expected {PRICE}, got {sell.price}")

        # ── fee per fill = 1% × notional ──
        notional = QTY * PRICE          # 4000
        expected_fee = notional * FEE_RATE   # 40
        assert buy.fee == pytest.approx(expected_fee, abs=0.001), (
            f"Buy fee expected {expected_fee}, got {buy.fee}")
        assert sell.fee == pytest.approx(expected_fee, abs=0.001), (
            f"Sell fee expected {expected_fee}, got {sell.fee}")

        # ── total fees ──
        total_fees = buy.fee + sell.fee
        expected_total = 2 * expected_fee   # 80
        assert total_fees == pytest.approx(expected_total, abs=0.001), (
            f"Total fees expected {expected_total}, got {total_fees}")

        # ── KEY INVARIANT: on flat price + no spread/slip,
        #    cash loss = total fees ──
        final_cash = result.equity[-1].cash
        cash_loss = CASH - final_cash
        assert cash_loss == pytest.approx(expected_total, abs=0.001), (
            f"Cash loss ({cash_loss:.4f}) must equal total fees "
            f"({expected_total:.4f}) on flat price with fee-only cost")

        # ── exact final cash ──
        assert final_cash == pytest.approx(CASH - expected_total, abs=0.001), (
            f"Final cash expected {CASH - expected_total}, got {final_cash}")

        # ── 1 closed trade ──
        assert len(result.trades) == 1
        t = result.trades[0]
        # trade.pnl = net PnL (all fees included)
        #   sell_proceeds = QTY×PRICE − fee_sell = 4000−40 = 3960
        #   total_cost    = QTY×PRICE + fee_buy  = 4000+40 = 4040
        #   pnl = 3960 − 4040 = −80  (both buy-side and sell-side fees)
        expected_pnl = -2 * expected_fee   # −80
        assert t.pnl == pytest.approx(expected_pnl, abs=0.001), (
            f"Trade PnL expected {expected_pnl}, got {t.pnl}. "
            f"trade.pnl must be net of ALL fees (buy + sell).")


# ---------------------------------------------------------------------------
# INV-4: NextOpenFill
# ---------------------------------------------------------------------------

class TestNextOpenFill:
    """Fill price MUST come from bar[t+1].open, not bar[t].close.
    Uses bars where open ≠ close to disambiguate.
    """

    def test_fill_price_is_next_bar_open(self) -> None:
        bars = [
            #       open    close   (distinct values)
            _bar(0, 40_000, 41_000),   # signal bar for BUY
            _bar(1, 42_000, 43_000),   # fill bar for BUY  → 42000
            _bar(2, 44_000, 45_000),   # signal bar for SELL
            _bar(3, 46_000, 47_000),   # fill bar for SELL → 46000
        ] + _flat_bars(6, 50_000, base_ms=4 * H4_MS)

        QTY = 0.1
        strategy = _ScriptedStrategy({
            0: Signal(orders=[Order(Side.BUY, QTY)], reason="buy"),
            2: Signal(orders=[Order(Side.SELL, QTY)], reason="sell"),
        })
        result = _run(bars, strategy, ZERO_COST, 10_000.0)

        assert len(result.fills) == 2
        buy_fill, sell_fill = result.fills

        # ── BUY: signal at bar[0].close=41000 → fill at bar[1].open=42000 ──
        assert buy_fill.price == pytest.approx(42_000.0, abs=0.01), (
            f"BUY fill_px={buy_fill.price:.2f}. "
            f"Expected 42000 (bar[1].open). "
            f"If ≈41000 → BUG: filled at signal-bar close. "
            f"If ≈40000 → BUG: filled at signal-bar open.")

        # ── SELL: signal at bar[2].close=45000 → fill at bar[3].open=46000 ──
        assert sell_fill.price == pytest.approx(46_000.0, abs=0.01), (
            f"SELL fill_px={sell_fill.price:.2f}. "
            f"Expected 46000 (bar[3].open). "
            f"If ≈45000 → BUG: filled at signal-bar close. "
            f"If ≈44000 → BUG: filled at signal-bar open.")

        # ── timestamp = bar[t+1].open_time ──
        assert buy_fill.ts_ms == bars[1].open_time, (
            f"BUY ts_ms={buy_fill.ts_ms}, "
            f"expected bar[1].open_time={bars[1].open_time}")
        assert sell_fill.ts_ms == bars[3].open_time, (
            f"SELL ts_ms={sell_fill.ts_ms}, "
            f"expected bar[3].open_time={bars[3].open_time}")

        # ── PnL: bought at 42000, sold at 46000 (zero cost) ──
        assert len(result.trades) == 1
        expected_pnl = QTY * (46_000.0 - 42_000.0)   # +400
        assert result.trades[0].pnl == pytest.approx(expected_pnl, abs=0.01), (
            f"PnL expected {expected_pnl}, got {result.trades[0].pnl}")

    def test_signal_bar_close_is_not_used(self) -> None:
        """Second confirmation: if prices are crafted so that
        close-based fill would yield different NAV than open-based fill,
        the NAV must match open-based fill."""
        # bar[0].close=100000 (absurdly high), bar[1].open=50000 (sane)
        bars = [
            _bar(0, 50_000, 100_000),
            _bar(1, 50_000, 50_000),
        ] + _flat_bars(3, 50_000, base_ms=2 * H4_MS)

        strategy = _ScriptedStrategy({
            0: Signal(target_exposure=1.0, reason="buy"),
        })
        result = _run(bars, strategy, ZERO_COST, 10_000.0)
        fill = result.fills[0]

        # Must fill at bar[1].open=50000, NOT bar[0].close=100000
        assert fill.price == pytest.approx(50_000.0, abs=0.01), (
            f"Fill at {fill.price}. If ≈100000 → engine used signal-bar close!")


# ---------------------------------------------------------------------------
# INV-5: FeeNoDoubleCount
# ---------------------------------------------------------------------------

class TestFeeNoDoubleCount:
    """Execute 2 full round trips with BASE_COST.
    Reconstruct final cash from initial_cash + Σ fill cash flows.
    Any double-count or missing fee breaks the identity.
    """

    def test_cash_reconstruction_2_round_trips(self) -> None:
        PRICE, CASH, QTY = 50_000.0, 10_000.0, 0.03
        bars = _flat_bars(20, PRICE)

        strategy = _ScriptedStrategy({
            0:  Signal(orders=[Order(Side.BUY, QTY)], reason="rt1_buy"),
            3:  Signal(orders=[Order(Side.SELL, QTY)], reason="rt1_sell"),
            6:  Signal(orders=[Order(Side.BUY, QTY)], reason="rt2_buy"),
            9:  Signal(orders=[Order(Side.SELL, QTY)], reason="rt2_sell"),
        })
        result = _run(bars, strategy, BASE_COST, CASH)

        assert len(result.fills) == 4, (
            f"Expected 4 fills, got {len(result.fills)}")
        assert len(result.trades) == 2, (
            f"Expected 2 trades, got {len(result.trades)}")

        # ── INVARIANT: reconstruct cash from fills ──
        reconstructed = CASH
        for f in result.fills:
            if f.side == Side.BUY:
                reconstructed -= f.notional + f.fee
            else:
                reconstructed += f.notional - f.fee

        actual_cash = result.equity[-1].cash
        assert actual_cash == pytest.approx(reconstructed, abs=1e-6), (
            f"Cash reconstruction MISMATCH: "
            f"reconstructed={reconstructed:.8f}, actual={actual_cash:.8f}, "
            f"delta={abs(actual_cash - reconstructed):.12f}. "
            f"This means fees are double-counted or missing in fills.")

        # ── each fill.fee = fill.notional × fee_rate ──
        em = ExecutionModel(BASE_COST)
        for i, f in enumerate(result.fills):
            expected_fee = f.notional * em.fee_rate
            assert f.fee == pytest.approx(expected_fee, abs=1e-6), (
                f"Fill[{i}].fee={f.fee:.8f} != "
                f"notional({f.notional:.4f})×rate({em.fee_rate})="
                f"{expected_fee:.8f}")

        # ── each fill.notional = fill.qty × fill.price ──
        for i, f in enumerate(result.fills):
            expected_not = f.qty * f.price
            assert f.notional == pytest.approx(expected_not, abs=1e-6), (
                f"Fill[{i}].notional={f.notional:.6f} != "
                f"qty({f.qty:.8f})×price({f.price:.4f})="
                f"{expected_not:.6f}")

        # ── cash loss decomposition: loss = price_impact + total_fees ──
        total_fees = sum(f.fee for f in result.fills)
        buy_notional = sum(f.notional for f in result.fills
                          if f.side == Side.BUY)
        sell_notional = sum(f.notional for f in result.fills
                           if f.side == Side.SELL)
        price_impact = buy_notional - sell_notional
        cash_loss = CASH - actual_cash
        assert cash_loss == pytest.approx(price_impact + total_fees, abs=1e-6), (
            f"Cash loss decomposition: loss={cash_loss:.8f}, "
            f"price_impact={price_impact:.8f}, fees={total_fees:.8f}, "
            f"price_impact+fees={price_impact + total_fees:.8f}")

    def test_fees_symmetric_on_flat_price(self) -> None:
        """With only fees (no spread/slip), buy fee ≈ sell fee on flat price."""
        PRICE, CASH, QTY = 60_000.0, 10_000.0, 0.05
        bars = _flat_bars(10, PRICE)
        strategy = _ScriptedStrategy({
            0: Signal(orders=[Order(Side.BUY, QTY)], reason="buy"),
            4: Signal(orders=[Order(Side.SELL, QTY)], reason="sell"),
        })
        result = _run(bars, strategy, FEE_ONLY_1PCT, CASH)

        buy_fee = result.fills[0].fee
        sell_fee = result.fills[1].fee
        assert buy_fee == pytest.approx(sell_fee, abs=0.01), (
            f"Fee-only on flat price: buy_fee={buy_fee:.4f} vs "
            f"sell_fee={sell_fee:.4f} should be equal")


# ---------------------------------------------------------------------------
# INV-6: PortfolioAccounting
# ---------------------------------------------------------------------------

class TestPortfolioAccounting:
    """Multi-fill scenario: buy, add, partial sell, close.
    At every equity snapshot the balance-sheet identity must hold,
    and final state must be reconstructable from fills.
    """

    def test_balance_sheet_and_reconstruction(self) -> None:
        # 15 bars with distinct, varying prices
        price_schedule = [
            (50000, 51000), (52000, 53000), (54000, 55000),
            (56000, 57000), (58000, 59000), (55000, 53000),
            (51000, 50000), (48000, 47000), (46000, 45000),
            (44000, 43000), (42000, 44000), (45000, 47000),
            (48000, 50000), (51000, 52000), (53000, 54000),
        ]
        bars = [_bar(i, o, c) for i, (o, c) in enumerate(price_schedule)]
        N = len(bars)
        CASH, QTY = 10_000.0, 0.04

        strategy = _ScriptedStrategy({
            0:  Signal(orders=[Order(Side.BUY, QTY)], reason="entry"),
            3:  Signal(orders=[Order(Side.BUY, QTY)], reason="add"),
            7:  Signal(orders=[Order(Side.SELL, QTY)], reason="trim"),
            11: Signal(orders=[Order(Side.SELL, QTY)], reason="close"),
        })
        result = _run(bars, strategy, BASE_COST, CASH)

        assert len(result.equity) == N, (
            f"Expected {N} snaps, got {len(result.equity)}")

        # ── INV 6a: nav_mid = cash + btc_qty × close at every bar ──
        for i in range(N):
            snap = result.equity[i]
            close_px = bars[i].close
            expected = snap.cash + snap.btc_qty * close_px
            assert snap.nav_mid == pytest.approx(expected, abs=0.01), (
                f"Snap[{i}]: nav_mid={snap.nav_mid:.4f} ≠ "
                f"cash({snap.cash:.4f}) + "
                f"btc({snap.btc_qty:.8f})×close({close_px:.2f})"
                f" = {expected:.4f}")

        # ── INV 6b: cash reconstruction from fills ──
        reconstructed_cash = CASH
        for f in result.fills:
            if f.side == Side.BUY:
                reconstructed_cash -= f.notional + f.fee
            else:
                reconstructed_cash += f.notional - f.fee

        final_cash = result.equity[-1].cash
        assert final_cash == pytest.approx(reconstructed_cash, abs=1e-6), (
            f"Cash reconstruction: expected={reconstructed_cash:.8f}, "
            f"actual={final_cash:.8f}")

        # ── INV 6c: btc_qty reconstruction from fills ──
        reconstructed_btc = 0.0
        for f in result.fills:
            if f.side == Side.BUY:
                reconstructed_btc += f.qty
            else:
                reconstructed_btc -= f.qty

        final_btc = result.equity[-1].btc_qty
        assert final_btc == pytest.approx(reconstructed_btc, abs=1e-10), (
            f"BTC reconstruction: expected={reconstructed_btc:.10f}, "
            f"actual={final_btc:.10f}")

        # ── INV 6d: btc_qty ≥ 0 at all times (long-only) ──
        for i, snap in enumerate(result.equity):
            assert snap.btc_qty >= -1e-10, (
                f"Snap[{i}]: btc_qty={snap.btc_qty:.10f} is negative!")

        # ── INV 6e: exposure ∈ [0, 1] at all times ──
        for i, snap in enumerate(result.equity):
            assert -1e-6 <= snap.exposure <= 1.0 + 1e-6, (
                f"Snap[{i}]: exposure={snap.exposure:.6f} outside [0, 1]")

    def test_no_value_leak_zero_cost(self) -> None:
        """With zero cost and flat price, any sequence of buys and sells
        that returns to flat must leave cash = initial_cash exactly."""
        PRICE, CASH, QTY = 45_000.0, 10_000.0, 0.05
        bars = _flat_bars(20, PRICE)

        strategy = _ScriptedStrategy({
            0:  Signal(orders=[Order(Side.BUY, QTY)], reason="b1"),
            2:  Signal(orders=[Order(Side.BUY, QTY)], reason="b2"),
            5:  Signal(orders=[Order(Side.SELL, QTY)], reason="s1"),
            8:  Signal(orders=[Order(Side.SELL, QTY)], reason="s2"),
        })
        result = _run(bars, strategy, ZERO_COST, CASH)

        final_cash = result.equity[-1].cash
        final_btc = result.equity[-1].btc_qty
        assert final_btc == pytest.approx(0.0, abs=1e-10), (
            f"Position should be flat, btc_qty={final_btc}")
        assert final_cash == pytest.approx(CASH, abs=0.001), (
            f"Zero cost + flat price + flat position → cash must equal "
            f"initial ({CASH}). Got {final_cash}. "
            f"Delta={abs(final_cash - CASH):.8f} = value leak!")
