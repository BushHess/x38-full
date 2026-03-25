"""Event-driven BacktestEngine — iterates H4 bars, fills at next-open.

Bar loop (per SPEC_EXECUTION.md §1):
  1. Execute pending signal at this bar's OPEN  (next-open fill)
     and call strategy.on_after_fill(...) after each applied fill.
  2. Record equity snapshot at bar CLOSE
  3. Call strategy.on_bar(state) at bar CLOSE
  4. Store returned signal as pending for next bar
"""

from __future__ import annotations

from collections.abc import MutableMapping
from collections.abc import MutableSequence
from collections.abc import MutableSet
from copy import copy as _shallow_copy

from v10.core.data import DataFeed
from v10.core.execution import ExecutionModel
from v10.core.execution import Portfolio
from v10.core.metrics import compute_metrics
from v10.core.types import BacktestResult
from v10.core.types import Bar
from v10.core.types import CostConfig
from v10.core.types import EquitySnap
from v10.core.types import Fill
from v10.core.types import MarketState
from v10.core.types import Order
from v10.core.types import Side
from v10.core.types import Signal
from v10.strategies.base import Strategy

_EXPO_THRESHOLD = 0.005  # ignore exposure deltas smaller than 0.5%


def _snapshot_attrs(d: dict[str, object]) -> dict[str, object]:
    """Copy strategy __dict__, duplicating mutable containers.

    Numpy arrays are immutable during on_bar() (set once in on_init),
    so sharing their reference is safe and avoids expensive copies.
    Lists, dicts, sets, and deques get their own shallow copy so that
    in-place mutations (append, __setitem__) don't survive rollback.
    """
    snap: dict[str, object] = {}
    for k, v in d.items():
        if isinstance(v, (MutableSequence, MutableMapping, MutableSet)):
            snap[k] = _shallow_copy(v)
        else:
            snap[k] = v
    return snap


def _extract_add_throttle_stats(strategy: Strategy) -> dict[str, object] | None:
    getter = getattr(strategy, "get_add_throttle_stats", None)
    if not callable(getter):
        return None
    try:
        payload = getter()
    except Exception:
        return None
    if isinstance(payload, dict) and payload:
        return payload
    return None


class BacktestEngine:
    """Main backtest engine.

    Parameters
    ----------
    feed : DataFeed
        Pre-loaded H4 and D1 bars.
    strategy : Strategy
        Trading strategy instance.
    cost : CostConfig
        Execution cost scenario.
    initial_cash : float
        Starting capital in quote currency.
    warmup_days : int
        Fallback warmup: calendar days from the first bar.
        Ignored when ``feed.report_start_ms`` is set (preferred).
    dump_mtf_map : bool
        If True, collect (h4_close_time, d1_close_time_used) pairs
        accessible via ``engine.mtf_map`` after ``run()``.
    warmup_mode : str
        ``"no_trade"`` (default): strategy.on_bar() is called during
        warmup for indicator state, but signals are discarded (no fills).
        ``"allow_trade"``: legacy behavior — signals execute during warmup,
        fills/trades are sliced out of reporting results.
    """

    def __init__(
        self,
        feed: DataFeed,
        strategy: Strategy,
        cost: CostConfig,
        initial_cash: float = 10_000.0,
        warmup_days: int = 0,
        dump_mtf_map: bool = False,
        entry_nav_pre_cost: bool = True,
        warmup_mode: str = "no_trade",
    ) -> None:
        if warmup_mode not in ("no_trade", "allow_trade"):
            raise ValueError(f"warmup_mode must be 'no_trade' or 'allow_trade', got '{warmup_mode}'")
        self.feed = feed
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.warmup_days = warmup_days
        self.warmup_mode = warmup_mode
        self.dump_mtf_map = dump_mtf_map
        self.mtf_map: list[tuple[int, int | None]] = []
        self.portfolio = Portfolio(
            initial_cash, ExecutionModel(cost), entry_nav_pre_cost,
        )
        self.equity: list[EquitySnap] = []

    # -- public API ----------------------------------------------------------

    def run(self) -> BacktestResult:
        """Execute the full backtest and return results."""
        h4 = self.feed.h4_bars
        d1 = self.feed.d1_bars
        if not h4:
            raise ValueError("DataFeed contains no H4 bars")

        self.strategy.on_init(h4, d1)

        # Determine reporting-window boundary.
        # Prefer feed.report_start_ms (set by DataFeed when --start + warmup_days).
        # Fallback: old-style warmup_days offset from first bar.
        report_start_ms: int | None = getattr(self.feed, "report_start_ms", None)
        if report_start_ms is None and self.warmup_days > 0:
            report_start_ms = h4[0].open_time + self.warmup_days * 86_400_000

        pending: Signal | None = None
        d1_idx = -1  # -1 = no D1 bar available yet
        reporting_started = False
        warmup_fills_count = 0
        warmup_trades_count = 0
        report_start_nav = self.initial_cash
        no_trade_warmup = self.warmup_mode == "no_trade"

        for i, bar in enumerate(h4):
            # Strict MTF alignment: latest D1 bar whose close_time is
            # STRICTLY BEFORE this H4 bar's close_time (no lookahead).
            while (
                d1_idx + 1 < len(d1)
                and d1[d1_idx + 1].close_time < bar.close_time
            ):
                d1_idx += 1

            if self.dump_mtf_map:
                d1_ct = d1[d1_idx].close_time if d1_idx >= 0 else None
                self.mtf_map.append((bar.close_time, d1_ct))

            # Determine warmup status for this bar (needed before step 1).
            is_warmup = (
                report_start_ms is not None
                and bar.close_time < report_start_ms
            )

            # --- Step 1: execute pending signal at bar OPEN ----------------
            if pending is not None:
                self._apply_signal(
                    pending, bar, h4, d1, i, d1_idx, bar.open_time,
                    is_warmup=is_warmup,
                )
                pending = None

            # --- Step 2: detect warmup → reporting transition --------------
            if not is_warmup and not reporting_started:
                reporting_started = True
                pf = self.portfolio
                warmup_fills_count = len(pf.fills)
                warmup_trades_count = len(pf.trades)
                report_start_nav = pf.nav(bar.close)

            # --- Step 3: equity snapshot at bar CLOSE ----------------------
            if not is_warmup:
                mid = bar.close
                pf = self.portfolio
                self.equity.append(EquitySnap(
                    close_time=bar.close_time,
                    nav_mid=pf.nav(mid),
                    nav_liq=pf.nav_liq(mid),
                    cash=pf.cash,
                    btc_qty=pf.btc_qty,
                    exposure=pf.exposure(mid),
                ))

            # --- Step 4: call strategy at bar CLOSE ------------------------
            state = self._build_state(bar, h4, d1, i, d1_idx, is_warmup=is_warmup)
            if no_trade_warmup and is_warmup:
                # Snapshot strategy state so we can rollback position-tracking
                # mutations if the strategy returns a signal.  Indicators are
                # precomputed in on_init() and stored in arrays (shared refs),
                # so sharing them is safe.  Mutable containers (list, deque)
                # get their own shallow copy so in-place mutations don't
                # survive the rollback.
                snapshot = _snapshot_attrs(self.strategy.__dict__)
                signal = self.strategy.on_bar(state)
                if signal is not None:
                    # Rollback: strategy set _in_position/_entered etc.
                    # before returning Signal, but the signal is discarded
                    # so portfolio stays flat — strategy state must match.
                    self.strategy.__dict__.update(snapshot)
            else:
                signal = self.strategy.on_bar(state)
                if signal is not None:
                    pending = signal

        # Slice to reporting-window fills / trades only
        pf = self.portfolio
        report_fills = pf.fills[warmup_fills_count:]
        report_trades = pf.trades[warmup_trades_count:]

        summary = compute_metrics(
            self.equity, report_trades, report_fills,
            initial_cash=self.initial_cash,
            report_start_nav=report_start_nav,
        )
        add_throttle_stats = _extract_add_throttle_stats(self.strategy)
        if add_throttle_stats is not None:
            summary["add_throttle_stats"] = add_throttle_stats
        return BacktestResult(
            equity=self.equity,
            fills=report_fills,
            trades=report_trades,
            summary=summary,
        )

    # -- internals -----------------------------------------------------------

    def _build_state(
        self,
        bar: Bar,
        h4: list[Bar],
        d1: list[Bar],
        h4_idx: int,
        d1_idx: int,
        mid: float | None = None,
        is_warmup: bool = False,
    ) -> MarketState:
        pf = self.portfolio
        nav_mid = bar.close if mid is None else mid
        return MarketState(
            bar=bar,
            h4_bars=h4,
            d1_bars=d1,
            bar_index=h4_idx,
            d1_index=d1_idx,
            cash=pf.cash,
            btc_qty=pf.btc_qty,
            nav=pf.nav(nav_mid),
            exposure=pf.exposure(nav_mid),
            entry_price_avg=pf.entry_price_avg,
            position_entry_nav=pf.position_entry_nav,
            is_warmup=is_warmup,
        )

    def _apply_signal(
        self,
        signal: Signal,
        bar: Bar,
        h4: list[Bar],
        d1: list[Bar],
        h4_idx: int,
        d1_idx: int,
        ts_ms: int,
        is_warmup: bool = False,
    ) -> None:
        """Convert a Signal into portfolio buy/sell actions."""
        # Mode 1: explicit orders take priority
        if signal.orders:
            self._execute_orders(
                signal.orders, bar, h4, d1, h4_idx, d1_idx, ts_ms, signal.reason,
                is_warmup=is_warmup,
            )
            return

        # Mode 2: target_exposure
        if signal.target_exposure is not None:
            self._apply_target_exposure(
                signal.target_exposure,
                bar,
                h4,
                d1,
                h4_idx,
                d1_idx,
                ts_ms,
                signal.reason,
                is_warmup=is_warmup,
            )

    def _execute_orders(
        self,
        orders: list[Order],
        bar: Bar,
        h4: list[Bar],
        d1: list[Bar],
        h4_idx: int,
        d1_idx: int,
        ts_ms: int,
        fallback_reason: str,
        is_warmup: bool = False,
    ) -> None:
        mid = bar.open
        pf = self.portfolio
        for order in orders:
            reason = order.reason or fallback_reason
            if order.side == Side.BUY:
                fill = pf.buy(order.qty, mid, ts_ms, reason)
            else:
                fill = pf.sell(order.qty, mid, ts_ms, reason)
            if fill is not None:
                self._notify_after_fill(
                    bar, h4, d1, h4_idx, d1_idx, fill,
                    is_warmup=is_warmup,
                )

    def _apply_target_exposure(
        self,
        target: float,
        bar: Bar,
        h4: list[Bar],
        d1: list[Bar],
        h4_idx: int,
        d1_idx: int,
        ts_ms: int,
        reason: str,
        is_warmup: bool = False,
    ) -> None:
        mid = bar.open
        target = max(0.0, min(1.0, target))
        pf = self.portfolio
        current = pf.exposure(mid)
        delta = target - current

        if target < _EXPO_THRESHOLD and pf.btc_qty > 1e-8:
            # Close entire position
            fill = pf.sell(pf.btc_qty, mid, ts_ms, reason)
            if fill is not None:
                self._notify_after_fill(
                    bar, h4, d1, h4_idx, d1_idx, fill,
                    is_warmup=is_warmup,
                )
        elif delta > _EXPO_THRESHOLD:
            # Buy more
            nav = pf.nav(mid)
            buy_value = delta * nav
            qty = buy_value / mid
            fill = pf.buy(qty, mid, ts_ms, reason)
            if fill is not None:
                self._notify_after_fill(
                    bar, h4, d1, h4_idx, d1_idx, fill,
                    is_warmup=is_warmup,
                )
        elif delta < -_EXPO_THRESHOLD:
            # Sell some
            nav = pf.nav(mid)
            sell_value = abs(delta) * nav
            qty = min(sell_value / mid, pf.btc_qty)
            fill = pf.sell(qty, mid, ts_ms, reason)
            if fill is not None:
                self._notify_after_fill(
                    bar, h4, d1, h4_idx, d1_idx, fill,
                    is_warmup=is_warmup,
                )

    def _notify_after_fill(
        self,
        bar: Bar,
        h4: list[Bar],
        d1: list[Bar],
        h4_idx: int,
        d1_idx: int,
        fill: Fill,
        is_warmup: bool = False,
    ) -> None:
        """Call strategy post-fill hook with post-fill state at bar OPEN mid."""
        state = self._build_state(
            bar, h4, d1, h4_idx, d1_idx, mid=bar.open,
            is_warmup=is_warmup,
        )
        self.strategy.on_after_fill(state, fill)
