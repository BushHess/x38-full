"""Parity checker — shadow-strategy replay for live signal verification.

For each processed signal_bar the checker:
  1. Replays the full bar history through a fresh shadow strategy
  2. Compares the shadow's expected order with the actual live order
  3. Logs every result to ``live_parity.csv``
  4. Sets ``halt_trading`` on side/qty mismatch

The replay mirrors :class:`BacktestEngine`'s bar loop exactly
(strict MTF alignment, next-open fills, same exposure threshold).
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from v10.core.execution import ExecutionModel, Portfolio
from v10.core.types import Bar, CostConfig, MarketState, SCENARIOS, Signal
from v10.exchange.filters import SymbolInfo
from v10.exchange.order_planner import OrderPlan, plan_order_from_target_exposure
from v10.strategies.base import Strategy

_log = logging.getLogger(__name__)

_EXPO_THRESHOLD = 0.005  # mirrors engine.py

_CSV_FIELDS = [
    "timestamp_iso",
    "signal_close_ms",
    "passed",
    "expected_side",
    "expected_qty",
    "expected_target_exposure",
    "actual_side",
    "actual_qty",
    "actual_target_exposure",
    "diff_qty_pct",
    "mismatch",
]


# ---------------------------------------------------------------------------
# ParityResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParityResult:
    """Result of a single parity check."""

    passed: bool
    signal_close_ms: int
    expected_side: str
    expected_qty: float
    expected_target_exposure: float | None
    actual_side: str
    actual_qty: float
    actual_target_exposure: float | None
    diff_qty_pct: float
    mismatch: str  # "" if passed, description if failed


# ---------------------------------------------------------------------------
# Shadow execution helper (mirrors engine._apply_target_exposure)
# ---------------------------------------------------------------------------

def _exec_target_exposure(
    pf: Portfolio,
    target: float,
    mid: float,
    ts_ms: int,
) -> None:
    """Apply target_exposure to a Portfolio — mirrors engine logic."""
    target = max(0.0, min(1.0, target))
    current = pf.exposure(mid)
    delta = target - current

    if target < _EXPO_THRESHOLD and pf.btc_qty > 1e-8:
        pf.sell(pf.btc_qty, mid, ts_ms, "shadow")
    elif delta > _EXPO_THRESHOLD:
        qty = delta * pf.nav(mid) / mid
        pf.buy(qty, mid, ts_ms, "shadow")
    elif delta < -_EXPO_THRESHOLD:
        qty = min(abs(delta) * pf.nav(mid) / mid, pf.btc_qty)
        pf.sell(qty, mid, ts_ms, "shadow")


# ---------------------------------------------------------------------------
# ParityChecker
# ---------------------------------------------------------------------------

class ParityChecker:
    """Shadow-strategy parity checker for live trading.

    Creates a fresh shadow strategy instance for each check and replays
    the full bar history through the backtest engine's bar loop.
    Compares the shadow's expected order with the actual live order.

    Parameters
    ----------
    strategy_factory : Callable[[], Strategy]
        Factory that returns a fresh strategy instance (same class/config
        as the live strategy).
    filters : SymbolInfo
        Exchange filters for the planner.
    cost : CostConfig | None
        Execution cost model (default ``SCENARIOS["base"]``).
    initial_cash : float
        Starting capital for the shadow portfolio.
    max_total_exposure : float
        Upper clamp for target_exposure in the planner.
    csv_path : str | Path | None
        Path for ``live_parity.csv``.  ``None`` disables CSV logging.
    qty_tolerance_pct : float
        Maximum allowed qty difference (percent).
    """

    def __init__(
        self,
        strategy_factory: Callable[[], Strategy],
        filters: SymbolInfo,
        cost: CostConfig | None = None,
        initial_cash: float = 10_000.0,
        max_total_exposure: float = 1.0,
        csv_path: str | Path | None = None,
        qty_tolerance_pct: float = 2.0,
    ) -> None:
        self._factory = strategy_factory
        self._filters = filters
        self._cost = cost or SCENARIOS["base"]
        self._initial_cash = initial_cash
        self._max_exposure = max_total_exposure
        self._csv_path = Path(csv_path) if csv_path else None
        self._qty_tol = qty_tolerance_pct
        self._h4: list[Bar] = []
        self._d1: list[Bar] = []
        self._halt_trading = False

        # Ensure CSV has header
        if self._csv_path is not None:
            self._csv_path.parent.mkdir(parents=True, exist_ok=True)
            if not self._csv_path.exists() or self._csv_path.stat().st_size == 0:
                with open(self._csv_path, "w", newline="") as f:
                    csv.writer(f).writerow(_CSV_FIELDS)

    @property
    def halt_trading(self) -> bool:
        """True if any parity check has failed."""
        return self._halt_trading

    def init_bars(self, h4_bars: list[Bar], d1_bars: list[Bar]) -> None:
        """Load historical bars for replay warmup."""
        self._h4 = list(h4_bars)
        self._d1 = list(d1_bars)

    def check(
        self,
        signal_bar: Bar,
        new_d1_bars: list[Bar],
        actual_plan: OrderPlan,
    ) -> ParityResult:
        """Run shadow replay and compare with actual live plan.

        Parameters
        ----------
        signal_bar : Bar
            The newly closed H4 bar (appended to history).
        new_d1_bars : list[Bar]
            Any new D1 bars since the last check.
        actual_plan : OrderPlan
            The order plan the live system is about to execute.
        """
        # 1. Update accumulated bars
        self._h4.append(signal_bar)
        self._d1.extend(new_d1_bars)

        # 2. Full shadow replay
        expected_signal = self._replay()

        # 3. Compute expected plan using live portfolio values
        expected_te = (
            expected_signal.target_exposure
            if expected_signal is not None
            else None
        )

        if expected_te is not None:
            expected_plan = plan_order_from_target_exposure(
                nav_usdt=actual_plan.nav_usdt,
                btc_qty=actual_plan.btc_qty,
                mid_price=actual_plan.mid_price,
                target_exposure=expected_te,
                filters=self._filters,
                max_total_exposure=self._max_exposure,
                cost=self._cost,
            )
        else:
            expected_plan = OrderPlan(
                side="HOLD", qty=0.0,
                est_fill_price=actual_plan.mid_price,
                notional=0.0, reason="no_signal",
                nav_usdt=actual_plan.nav_usdt,
                btc_qty=actual_plan.btc_qty,
                mid_price=actual_plan.mid_price,
                target_exposure=0.0, clamped_exposure=0.0,
                current_exposure=actual_plan.current_exposure,
                desired_btc_value=0.0,
                current_btc_value=actual_plan.current_btc_value,
                delta_value=0.0,
            )

        # 4. Compare
        actual_te = actual_plan.target_exposure if actual_plan.side != "HOLD" else None
        result = self._compare(
            signal_bar.close_time,
            expected_plan, expected_te,
            actual_plan, actual_te,
        )

        # 5. Log + halt
        if not result.passed:
            self._halt_trading = True
            _log.warning(
                "PARITY FAIL: %s | expected %s %.5f | actual %s %.5f",
                result.mismatch,
                result.expected_side, result.expected_qty,
                result.actual_side, result.actual_qty,
            )
        else:
            _log.info(
                "Parity OK: %s %.5f (signal_close=%d)",
                result.actual_side, result.actual_qty,
                result.signal_close_ms,
            )

        self._log_csv(result)
        return result

    # ── Private helpers ───────────────────────────────────────

    def _replay(self) -> Signal | None:
        """Replay all bars through a fresh shadow strategy + portfolio.

        Returns the signal produced by the shadow at the LAST bar.
        """
        shadow = self._factory()
        shadow.on_init(self._h4, self._d1)

        pf = Portfolio(self._initial_cash, ExecutionModel(self._cost))
        d1_idx = -1
        pending: Signal | None = None
        last_signal: Signal | None = None

        for i, bar in enumerate(self._h4):
            # Strict MTF alignment (identical to BacktestEngine)
            while (
                d1_idx + 1 < len(self._d1)
                and self._d1[d1_idx + 1].close_time < bar.close_time
            ):
                d1_idx += 1

            # Execute pending signal at bar OPEN (next-open fill)
            if pending is not None:
                if pending.target_exposure is not None:
                    _exec_target_exposure(
                        pf, pending.target_exposure,
                        bar.open, bar.open_time,
                    )
                pending = None

            # Build MarketState at bar CLOSE
            mid = bar.close
            state = MarketState(
                bar=bar,
                h4_bars=self._h4,
                d1_bars=self._d1,
                bar_index=i,
                d1_index=d1_idx,
                cash=pf.cash,
                btc_qty=pf.btc_qty,
                nav=pf.nav(mid),
                exposure=pf.exposure(mid),
                entry_price_avg=pf.entry_price_avg,
                position_entry_nav=pf.position_entry_nav,
            )

            sig = shadow.on_bar(state)
            if sig is not None:
                pending = sig
            last_signal = sig

        return last_signal

    def _compare(
        self,
        signal_close_ms: int,
        expected: OrderPlan,
        expected_te: float | None,
        actual: OrderPlan,
        actual_te: float | None,
    ) -> ParityResult:
        """Compare expected vs actual plan and return ParityResult."""
        side_match = expected.side == actual.side

        # Qty comparison
        max_qty = max(expected.qty, actual.qty)
        if max_qty < 1e-10:
            diff_pct = 0.0
        else:
            diff_pct = abs(expected.qty - actual.qty) / max_qty * 100.0

        both_hold = expected.side == "HOLD" and actual.side == "HOLD"
        qty_ok = both_hold or diff_pct <= self._qty_tol

        passed = side_match and qty_ok

        mismatch = ""
        if not side_match:
            mismatch = f"side: expected={expected.side} actual={actual.side}"
        elif not qty_ok:
            mismatch = f"qty: expected={expected.qty:.5f} actual={actual.qty:.5f} diff={diff_pct:.2f}%"

        return ParityResult(
            passed=passed,
            signal_close_ms=signal_close_ms,
            expected_side=expected.side,
            expected_qty=expected.qty,
            expected_target_exposure=expected_te,
            actual_side=actual.side,
            actual_qty=actual.qty,
            actual_target_exposure=actual_te,
            diff_qty_pct=diff_pct,
            mismatch=mismatch,
        )

    def _log_csv(self, result: ParityResult) -> None:
        if self._csv_path is None:
            return
        with open(self._csv_path, "a", newline="") as f:
            csv.writer(f).writerow([
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                result.signal_close_ms,
                result.passed,
                result.expected_side,
                f"{result.expected_qty:.8f}",
                f"{result.expected_target_exposure:.6f}" if result.expected_target_exposure is not None else "",
                result.actual_side,
                f"{result.actual_qty:.8f}",
                f"{result.actual_target_exposure:.6f}" if result.actual_target_exposure is not None else "",
                f"{result.diff_qty_pct:.2f}",
                result.mismatch,
            ])
