"""Core data types for V10 backtest framework.

All cost formulas follow SPEC_EXECUTION.md.
Timestamps are epoch-milliseconds UTC throughout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Bar:
    """Single OHLCV bar (any timeframe)."""
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    taker_buy_base_vol: float
    interval: str  # '1h', '4h', '1d'
    quote_volume: float = 0.0
    taker_buy_quote_vol: float = 0.0


# ---------------------------------------------------------------------------
# Cost configuration
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CostConfig:
    """Execution cost parameters — per SPEC_EXECUTION.md §2."""
    spread_bps: float = 5.0
    slippage_bps: float = 3.0
    taker_fee_pct: float = 0.10  # percent (0.10 = 0.10%)

    @property
    def per_side_bps(self) -> float:
        """spread/2 + slippage + fee (all in bps)."""
        return self.spread_bps / 2.0 + self.slippage_bps + self.taker_fee_pct * 100.0

    @property
    def round_trip_bps(self) -> float:
        return self.per_side_bps * 2.0

    @property
    def round_trip_pct(self) -> float:
        return self.round_trip_bps / 100.0


SCENARIOS: dict[str, CostConfig] = {
    "smart": CostConfig(spread_bps=3.0, slippage_bps=1.5, taker_fee_pct=0.035),
    "base":  CostConfig(spread_bps=5.0, slippage_bps=3.0, taker_fee_pct=0.100),
    "harsh": CostConfig(spread_bps=10.0, slippage_bps=5.0, taker_fee_pct=0.150),
}
"""
Canonical round-trip costs (formula: 2 * (spread/2 + slip + fee_pct*100)):
  smart  = 13.0 bps  (0.13%)
  base   = 31.0 bps  (0.31%)
  harsh  = 50.0 bps  (0.50%)
See SPEC_EXECUTION.md §3 for full derivation.
"""


# ---------------------------------------------------------------------------
# Execution records
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Fill:
    ts_ms: int
    side: Side
    qty: float
    price: float
    fee: float
    notional: float
    reason: str


@dataclass(slots=True)
class Trade:
    trade_id: int
    entry_ts_ms: int
    exit_ts_ms: int
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    return_pct: float
    days_held: float
    entry_reason: str
    exit_reason: str


# ---------------------------------------------------------------------------
# Strategy interface types
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Order:
    """Explicit order for advanced strategies."""
    side: Side
    qty: float
    reason: str = ""


@dataclass
class Signal:
    """Strategy output — either target_exposure OR explicit orders.

    - target_exposure: float 0.0–1.0 (fraction of NAV in BTC).
      Engine computes required buy/sell delta.
    - orders: list of explicit Order objects.
      Engine executes them directly.
    At least one must be set. If both set, orders take priority.
    """
    target_exposure: float | None = None
    orders: list[Order] | None = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Engine state passed to strategy
# ---------------------------------------------------------------------------

@dataclass
class MarketState:
    """Snapshot of market + portfolio state at bar close.

    h4_bars / d1_bars are the FULL pre-loaded lists.
    Use bar_index / d1_index to bound look-back window.
    """
    bar: Bar
    h4_bars: list[Bar]
    d1_bars: list[Bar]
    bar_index: int
    d1_index: int
    cash: float
    btc_qty: float
    nav: float
    exposure: float
    entry_price_avg: float
    position_entry_nav: float
    is_warmup: bool = False


# ---------------------------------------------------------------------------
# Equity curve snapshot
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EquitySnap:
    close_time: int
    nav_mid: float
    nav_liq: float
    cash: float
    btc_qty: float
    exposure: float


# ---------------------------------------------------------------------------
# Backtest result container
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    equity: list[EquitySnap]
    fills: list[Fill]
    trades: list[Trade]
    summary: dict[str, Any]
