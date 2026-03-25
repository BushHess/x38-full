"""ExecutionModel and Portfolio — per SPEC_EXECUTION.md §2.

Cost formula (per-side, applied at each fill):
  BUY:  ask = mid*(1 + spread_bps/20000)
        fill_px = ask*(1 + slippage_bps/10000)
        fee = qty*fill_px*(taker_fee_pct/100)
        total_cost = qty*fill_px + fee

  SELL: bid = mid*(1 - spread_bps/20000)
        fill_px = bid*(1 - slippage_bps/10000)
        fee = qty*fill_px*(taker_fee_pct/100)
        proceeds = qty*fill_px - fee
"""

from __future__ import annotations

from v10.core.types import CostConfig, Fill, Side, Trade

_EPS = 1e-12


class ExecutionModel:
    """Stateless fill-price and fee calculator."""

    def __init__(self, cost: CostConfig) -> None:
        self.cost = cost

    # -- price helpers -------------------------------------------------------

    def bid_ask(self, mid: float) -> tuple[float, float]:
        """Return (bid, ask) from mid price."""
        half = self.cost.spread_bps / 2.0 / 10_000.0
        return mid * (1.0 - half), mid * (1.0 + half)

    def fill_buy_price(self, mid: float) -> float:
        """Fill price for a BUY: ask + slippage."""
        _, ask = self.bid_ask(mid)
        return ask * (1.0 + self.cost.slippage_bps / 10_000.0)

    def fill_sell_price(self, mid: float) -> float:
        """Fill price for a SELL: bid - slippage."""
        bid, _ = self.bid_ask(mid)
        return bid * (1.0 - self.cost.slippage_bps / 10_000.0)

    @property
    def fee_rate(self) -> float:
        """Fee as a decimal (e.g. 0.001 for 0.10%)."""
        return self.cost.taker_fee_pct / 100.0


class Portfolio:
    """Manages cash, BTC holdings, fills, and trades.

    Uses ExecutionModel for price/fee computation.
    Tracks weighted-average entry price and position-entry NAV
    per SPEC_EXECUTION.md §4–§6.
    """

    def __init__(
        self,
        initial_cash: float,
        exec_model: ExecutionModel,
        entry_nav_pre_cost: bool = True,
    ) -> None:
        self.cash: float = initial_cash
        self.btc_qty: float = 0.0
        self.entry_price_avg: float = 0.0
        self.position_entry_nav: float = 0.0
        self.exec: ExecutionModel = exec_model
        self._entry_nav_pre_cost = entry_nav_pre_cost
        self.fills: list[Fill] = []
        self.trades: list[Trade] = []

        # Open-trade tracking
        self._trade_seq: int = 0
        self._open_entry_ts: int = 0
        self._open_entry_reason: str = ""
        self._open_entry_qty: float = 0.0
        self._open_entry_notional: float = 0.0
        self._cumulative_rpnl: float = 0.0
        self._open_buy_fees: float = 0.0

    # -- queries -------------------------------------------------------------

    def nav(self, mid: float) -> float:
        """Net asset value at mid price."""
        return self.cash + self.btc_qty * mid

    def nav_liq(self, mid: float) -> float:
        """Conservative NAV at liquidation (bid - slippage - fee)."""
        if self.btc_qty < _EPS:
            return self.cash
        fp = self.exec.fill_sell_price(mid)
        notional = self.btc_qty * fp
        fee = notional * self.exec.fee_rate
        return self.cash + notional - fee

    def exposure(self, mid: float) -> float:
        """Fraction of NAV held in BTC."""
        n = self.nav(mid)
        if n < _EPS:
            return 0.0
        return (self.btc_qty * mid) / n

    # -- actions -------------------------------------------------------------

    def buy(self, qty: float, mid: float, ts_ms: int, reason: str) -> Fill | None:
        """Execute a BUY fill at *mid* (next-bar open).

        Reduces qty if insufficient cash.  Returns the Fill or None.
        """
        if qty < _EPS:
            return None

        fill_px = self.exec.fill_buy_price(mid)
        fee_r = self.exec.fee_rate
        notional = qty * fill_px
        fee = notional * fee_r
        total_cost = notional + fee

        # Cash constraint — reduce qty to fit (SPEC §7)
        if total_cost > self.cash + 0.01:
            max_notional = self.cash / (1.0 + fee_r)
            qty = max_notional / fill_px
            if qty < _EPS:
                return None
            notional = qty * fill_px
            fee = notional * fee_r
            total_cost = notional + fee

        # Weighted-average entry price (SPEC §4)
        old_value = self.btc_qty * self.entry_price_avg
        self.cash -= total_cost
        self.btc_qty += qty
        new_value = old_value + qty * fill_px
        self.entry_price_avg = new_value / self.btc_qty

        # Position entry NAV — set once when opening from flat (SPEC §6)
        if self._open_entry_ts == 0:
            self._trade_seq += 1
            self._open_entry_ts = ts_ms
            self._open_entry_reason = reason
            self._open_entry_qty = 0.0
            self._open_entry_notional = 0.0
            self._cumulative_rpnl = 0.0
            # pre_cost: true pre-fill NAV (undo cash deduction and BTC addition)
            # post_cost: NAV after fill (cash already deducted, BTC already added)
            if self._entry_nav_pre_cost:
                self.position_entry_nav = (
                    (self.cash + total_cost) + (self.btc_qty - qty) * mid
                )
            else:
                self.position_entry_nav = self.nav(mid)

        self._open_entry_qty += qty
        self._open_entry_notional += notional
        self._open_buy_fees += fee

        fill = Fill(
            ts_ms=ts_ms, side=Side.BUY, qty=qty,
            price=fill_px, fee=fee, notional=notional, reason=reason,
        )
        self.fills.append(fill)
        return fill

    def sell(self, qty: float, mid: float, ts_ms: int, reason: str) -> Fill | None:
        """Execute a SELL fill at *mid* (next-bar open).

        qty is capped at current holdings.  Returns the Fill or None.
        """
        qty = min(qty, self.btc_qty)
        if qty < _EPS:
            return None

        fill_px = self.exec.fill_sell_price(mid)
        fee_r = self.exec.fee_rate
        notional = qty * fill_px
        fee = notional * fee_r
        proceeds = notional - fee

        # Realized PnL on this slice (SPEC §5)
        cost_basis = self.entry_price_avg * qty
        rpnl = proceeds - cost_basis
        self._cumulative_rpnl += rpnl

        self.cash += proceeds
        self.btc_qty -= qty

        fill = Fill(
            ts_ms=ts_ms, side=Side.SELL, qty=qty,
            price=fill_px, fee=fee, notional=notional, reason=reason,
        )
        self.fills.append(fill)

        # Position fully closed → record Trade
        if self.btc_qty < _EPS:
            self.btc_qty = 0.0
            self._close_trade(fill_px, ts_ms, reason)

        return fill

    # -- internals -----------------------------------------------------------

    def _close_trade(self, exit_px: float, exit_ts: int, exit_reason: str) -> None:
        entry_avg = (
            self._open_entry_notional / self._open_entry_qty
            if self._open_entry_qty > _EPS
            else exit_px
        )
        # Net PnL: includes ALL fees (buy-side + sell-side).
        # _cumulative_rpnl = Σ(sell_proceeds - cost_basis) already includes sell fees
        # but cost_basis uses entry_price_avg (fill price only, no buy fee).
        # Subtract accumulated buy fees to get true net PnL.
        net_pnl = self._cumulative_rpnl - self._open_buy_fees

        # Net return on total invested capital (notional + buy fees).
        total_cost_basis = self._open_entry_notional + self._open_buy_fees
        ret_pct = (net_pnl / total_cost_basis) * 100.0 if total_cost_basis > _EPS else 0.0

        days = (exit_ts - self._open_entry_ts) / (86_400.0 * 1_000.0)

        self.trades.append(Trade(
            trade_id=self._trade_seq,
            entry_ts_ms=self._open_entry_ts,
            exit_ts_ms=exit_ts,
            entry_price=entry_avg,
            exit_price=exit_px,
            qty=self._open_entry_qty,
            pnl=net_pnl,
            return_pct=ret_pct,
            days_held=max(days, 0.0),
            entry_reason=self._open_entry_reason,
            exit_reason=exit_reason,
        ))

        # Reset open-trade state
        self._open_entry_ts = 0
        self._open_entry_reason = ""
        self._open_entry_qty = 0.0
        self._open_entry_notional = 0.0
        self._cumulative_rpnl = 0.0
        self._open_buy_fees = 0.0
        self.entry_price_avg = 0.0
        self.position_entry_nav = 0.0
