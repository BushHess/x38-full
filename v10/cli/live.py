"""Live trading runner — full signal → plan → order → fill pipeline.

Wires: Config → Strategy → BarClock → OrderPlanner → ParityChecker → OrderManager

Modes:
  soak_orders  — force BUY/SELL each cycle for order-path stress testing (C4.1)
  soak_notrade — poll-only, no orders, tests BarClock scheduling (C4.2)
  replay       — fast-forward CSV bars through real testnet orders (C5.1)
  realtime     — real-time H4 cadence with live strategy signals (C5.2)

Usage:
    python -m v10.cli.live \\
        --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \\
        --outdir out_live \\
        --mode realtime \\
        --cycle-seconds 30 \\
        --shadow
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import signal
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v10.core.config import load_config, config_to_dict
from v10.core.formatting import ms_to_iso
from v10.core.meta import stamp_run_meta
from v10.core.types import Bar, CostConfig, MarketState, Signal, SCENARIOS
from v10.exchange.account_scope import fetch_account_scope, reset_to_cash
from v10.exchange.bar_clock import BarClock, BarEvent
from v10.exchange.filters import (
    SymbolInfo, fetch_symbol_info, round_qty_down, validate_order,
)
from v10.exchange.marketdata import CsvBarSource, load_cached_bars
from v10.exchange.order_manager import (
    CrashPoint, CrashSimulation, OrderManager, make_client_order_id,
)
from v10.exchange.order_planner import OrderPlan, plan_order_from_target_exposure
from v10.exchange.parity import ParityChecker
from v10.exchange.rest_client import BinanceSpotClient
from v10.strategies.base import Strategy
from monitoring.alerts import AlertDispatcher
from validation.strategy_factory import STRATEGY_REGISTRY, build_from_config

_log = logging.getLogger("live_runner")

SYMBOL = "BTCUSDT"
_EXPO_THRESHOLD = 0.005


# ---------------------------------------------------------------------------
# Risk guards
# ---------------------------------------------------------------------------

class RiskGuards:
    """Runtime risk guards — enforces kill-switch and daily order limits."""

    def __init__(
        self,
        kill_switch_dd: float = 0.45,
        max_daily_orders: int = 5,
        max_total_exposure: float = 1.0,
        min_notional_usdt: float = 10.0,
    ) -> None:
        self.kill_switch_dd = kill_switch_dd
        self.max_daily_orders = max_daily_orders
        self.max_total_exposure = max_total_exposure
        self.min_notional_usdt = min_notional_usdt

        self._startup_nav: float | None = None
        self._orders_today = 0
        self._today_date: str = ""
        self._halted = False
        self._halt_reason = ""

    def set_startup_nav(self, nav: float) -> None:
        self._startup_nav = nav

    def check(self, nav: float, mid_price: float) -> tuple[bool, str]:
        """Returns (ok, reason). If not ok, trading must halt."""
        if self._halted:
            return False, self._halt_reason

        # Kill-switch: total DD from startup
        if self._startup_nav is not None and self._startup_nav > 0:
            dd = 1.0 - nav / self._startup_nav
            if dd > self.kill_switch_dd:
                self._halted = True
                self._halt_reason = (
                    f"kill_switch: DD {dd:.2%} > {self.kill_switch_dd:.2%}"
                )
                return False, self._halt_reason

        # Daily order count
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._today_date:
            self._today_date = today
            self._orders_today = 0

        if self._orders_today >= self.max_daily_orders:
            return False, f"max_daily_orders: {self._orders_today} >= {self.max_daily_orders}"

        return True, ""

    def record_order(self) -> None:
        self._orders_today += 1

    @property
    def halted(self) -> bool:
        return self._halted


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def _csv_append(path: Path, fields: list[str], row: list[Any]) -> None:
    """Append a row to a CSV file, creating header if needed."""
    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(fields)
        w.writerow(row)


_ORDER_FIELDS = [
    "timestamp_iso", "client_order_id", "side", "qty", "type",
    "status", "exchange_order_id", "reason",
]

_FILL_FIELDS = [
    "timestamp_iso", "trade_id", "client_order_id", "price",
    "qty", "commission", "commission_asset", "slippage_bps",
]

_SLIPPAGE_FIELDS = [
    "timestamp_iso", "client_order_id", "side", "expected_mid",
    "fill_price", "slippage_bps", "qty",
]


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# LiveRunner
# ---------------------------------------------------------------------------

class LiveRunner:
    """Orchestrates the full live trading pipeline.

    BarClock → Strategy.on_bar() → OrderPlanner → ParityChecker → OrderManager
    """

    def __init__(
        self,
        client: BinanceSpotClient,
        strategy: Strategy,
        strategy_factory: callable,
        config: Any,
        cost: CostConfig,
        filters: SymbolInfo,
        outdir: Path,
        *,
        mode: str = "realtime",
        max_cycles: int = 0,
        cycle_seconds: float = 30.0,
        throttle_sec: float = 2.0,
        no_trade: bool = False,
        shadow: bool = False,
        fault_inject_rate: float = 0.0,
        fault_points: list[str] | None = None,
        order_notional_usdt: float | None = None,
        qty_tolerance_pct: float = 2.0,
        warmup_days: int = 365,
        initial_cash: float = 10_000.0,
        risk_guards: RiskGuards | None = None,
        alerts: AlertDispatcher | None = None,
    ) -> None:
        self._client = client
        self._strategy = strategy
        self._strategy_factory = strategy_factory
        self._config = config
        self._cost = cost
        self._filters = filters
        self._outdir = outdir
        self._mode = mode
        self._max_cycles = max_cycles
        self._cycle_seconds = cycle_seconds
        self._throttle_sec = throttle_sec
        self._no_trade = no_trade
        self._shadow = shadow
        self._fault_inject_rate = fault_inject_rate
        self._fault_points = fault_points or ["AFTER_SEND"]
        self._order_notional = order_notional_usdt
        self._qty_tol = qty_tolerance_pct
        self._warmup_days = warmup_days
        self._initial_cash = initial_cash
        self._guards = risk_guards or RiskGuards()
        self._alerts = alerts
        self._shutdown = False

        # State
        self._h4_bars: list[Bar] = []
        self._d1_bars: list[Bar] = []
        self._d1_last_close_ms: int = 0
        self._cycles = 0
        self._soak_side = "BUY"

        # File paths
        self._db_path = outdir / "bot.sqlite3"
        self._bar_csv = outdir / "live_bar_events.csv"
        self._plan_csv = outdir / "live_plan.csv"
        self._order_csv = outdir / "live_orders.csv"
        self._fill_csv = outdir / "live_fills.csv"
        self._slippage_csv = outdir / "live_slippage.csv"
        self._parity_csv = outdir / "live_parity.csv"

        outdir.mkdir(parents=True, exist_ok=True)

        # Components
        self._bar_clock = BarClock(
            client, str(self._db_path), SYMBOL,
            csv_path=str(self._bar_csv),
        )
        self._mgr = OrderManager(
            client, str(self._db_path), SYMBOL,
            poll_interval=1.0, max_polls=30,
        )
        self._parity: ParityChecker | None = None
        if shadow:
            self._parity = ParityChecker(
                strategy_factory=strategy_factory,
                filters=filters,
                cost=cost,
                initial_cash=initial_cash,
                max_total_exposure=self._guards.max_total_exposure,
                csv_path=str(self._parity_csv),
                qty_tolerance_pct=qty_tolerance_pct,
            )

    def run(self) -> dict[str, Any]:
        """Main loop. Returns run summary dict."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        _log.info("=== LiveRunner starting (mode=%s) ===", self._mode)
        if self._alerts:
            self._alerts.bot_started(self._mode, self._strategy.name())

        # Startup reconciliation
        reconcile_report = self._startup_reconcile()

        # Fetch initial account state
        scope = fetch_account_scope(self._client, SYMBOL)
        self._guards.set_startup_nav(scope.nav_usdt)
        _log.info(
            "Startup: NAV=%.2f USDT, exposure=%.4f, BTC=%.8f",
            scope.nav_usdt, scope.exposure, scope.btc_free,
        )

        # Load warmup bars
        if self._mode == "replay":
            self._load_replay_bars()
        else:
            self._load_warmup_bars()

        # Init strategy with warmup bars
        if self._h4_bars:
            self._strategy.on_init(self._h4_bars, self._d1_bars)
            if self._parity:
                self._parity.init_bars(
                    list(self._h4_bars), list(self._d1_bars),
                )

        exit_reason = "completed"
        try:
            if self._mode == "replay":
                self._run_replay()
            else:
                self._run_polling()
        except KeyboardInterrupt:
            exit_reason = "keyboard_interrupt"
        except CrashSimulation as e:
            exit_reason = f"crash_simulation:{e}"
            _log.warning("CrashSimulation: %s", e)

        if self._guards.halted:
            exit_reason = f"risk_halt:{self._guards._halt_reason}"
        if self._shutdown:
            exit_reason = "signal_shutdown"

        _log.info(
            "=== LiveRunner finished: %d cycles, exit=%s ===",
            self._cycles, exit_reason,
        )
        if self._alerts:
            self._alerts.bot_stopped(exit_reason, self._cycles)

        # Write reconcile report
        reconcile_report["exit_reason"] = exit_reason
        reconcile_report["total_cycles"] = self._cycles
        (self._outdir / "reconcile_report.json").write_text(
            json.dumps(reconcile_report, indent=2, default=str) + "\n"
        )

        self._bar_clock.close()
        self._mgr.close()

        return {"exit_reason": exit_reason, "cycles": self._cycles}

    # ── Polling loop (soak_orders, soak_notrade, realtime) ────

    def _run_polling(self) -> None:
        while not self._should_stop():
            event = self._bar_clock.poll()

            if event is None:
                time.sleep(self._cycle_seconds)
                continue

            _log.info(
                "BarEvent: signal_close=%s price=%.2f",
                ms_to_iso(event.signal_bar.close_time),
                event.signal_bar.close,
            )

            self._process_bar_event(event)
            self._cycles += 1

    # ── Replay loop (C5.1) ───────────────────────────────────

    def _run_replay(self) -> None:
        """Fast-forward CSV bars through the live pipeline."""
        if len(self._h4_bars) < 2:
            _log.error("Not enough H4 bars for replay")
            return

        # We already loaded and init'd strategy with all bars.
        # Now replay bar-by-bar, simulating BarEvents.
        for i in range(len(self._h4_bars) - 1):
            if self._should_stop():
                break

            signal_bar = self._h4_bars[i]
            fill_open = self._h4_bars[i + 1].open
            fill_open_time = self._h4_bars[i + 1].open_time

            event = BarEvent(
                signal_bar=signal_bar,
                fill_bar_open=fill_open,
                fill_bar_open_time=fill_open_time,
            )

            self._process_bar_event_replay(event, i)
            self._cycles += 1

            if self._throttle_sec > 0:
                time.sleep(self._throttle_sec)

    # ── Bar processing (real-time) ───────────────────────────

    def _process_bar_event(self, event: BarEvent) -> None:
        """Process a single bar event from BarClock."""
        scope = fetch_account_scope(self._client, SYMBOL)

        # Risk check
        ok, reason = self._guards.check(scope.nav_usdt, event.signal_bar.close)
        if not ok:
            _log.critical("RISK HALT: %s", reason)
            if self._alerts:
                dd = 1.0 - scope.nav_usdt / (self._guards._startup_nav or scope.nav_usdt)
                self._alerts.risk_halt(reason, scope.nav_usdt, dd)
            return

        # Accumulate bars
        self._h4_bars.append(event.signal_bar)
        new_d1 = self._fetch_new_d1()

        # Re-init strategy (stateless — replay all bars)
        self._strategy.on_init(self._h4_bars, self._d1_bars)

        # Build market state at last bar
        d1_idx = len(self._d1_bars) - 1
        h4_idx = len(self._h4_bars) - 1
        mid = event.signal_bar.close
        state = MarketState(
            bar=event.signal_bar,
            h4_bars=self._h4_bars,
            d1_bars=self._d1_bars,
            bar_index=h4_idx,
            d1_index=d1_idx,
            cash=scope.usdt_free,
            btc_qty=scope.btc_free,
            nav=scope.nav_usdt,
            exposure=scope.exposure,
            entry_price_avg=0.0,
            position_entry_nav=0.0,
        )

        # Mode-specific signal
        if self._mode == "soak_orders":
            sig = self._soak_signal(scope)
        elif self._mode == "soak_notrade":
            _log.info("soak_notrade: poll OK, no signal")
            return
        else:
            sig = self._strategy.on_bar(state)

        if sig is None:
            _log.info("No signal at bar %s", ms_to_iso(event.signal_bar.close_time))
            return

        # Plan order
        target_exp = sig.target_exposure if sig.target_exposure is not None else 0.0
        plan = plan_order_from_target_exposure(
            nav_usdt=scope.nav_usdt,
            btc_qty=scope.btc_free,
            mid_price=event.fill_bar_open,
            target_exposure=target_exp,
            filters=self._filters,
            max_total_exposure=self._guards.max_total_exposure,
            cost=self._cost,
            csv_path=str(self._plan_csv),
        )

        # Parity check
        if self._parity:
            result = self._parity.check(event.signal_bar, new_d1, plan)
            if not result.passed and self._alerts:
                self._alerts.parity_mismatch(
                    result.expected_side, result.actual_side, result.diff_qty_pct,
                )
            if self._parity.halt_trading:
                _log.critical("PARITY HALT — aborting")
                self._shutdown = True
                return

        # Submit order
        if plan.side != "HOLD" and not self._no_trade:
            self._submit_order(
                plan, event.signal_bar.close_time,
                sig.reason, event.fill_bar_open,
            )

        # Fault injection
        if self._fault_inject_rate > 0 and random.random() < self._fault_inject_rate:
            point = random.choice(self._fault_points)
            _log.warning("FAULT INJECTION: %s", point)
            raise CrashSimulation(point)

    # ── Bar processing (replay) ──────────────────────────────

    def _process_bar_event_replay(self, event: BarEvent, bar_idx: int) -> None:
        """Process a bar during CSV replay (C5.1)."""
        scope = fetch_account_scope(self._client, SYMBOL)

        ok, reason = self._guards.check(scope.nav_usdt, event.signal_bar.close)
        if not ok:
            _log.critical("RISK HALT: %s", reason)
            return

        # Strategy already initialized with full bars.
        # Build state at bar_idx.
        d1_idx = -1
        for di, d1 in enumerate(self._d1_bars):
            if d1.close_time < event.signal_bar.close_time:
                d1_idx = di

        mid = event.signal_bar.close
        state = MarketState(
            bar=event.signal_bar,
            h4_bars=self._h4_bars,
            d1_bars=self._d1_bars,
            bar_index=bar_idx,
            d1_index=d1_idx,
            cash=scope.usdt_free,
            btc_qty=scope.btc_free,
            nav=scope.nav_usdt,
            exposure=scope.exposure,
            entry_price_avg=0.0,
            position_entry_nav=0.0,
        )

        sig = self._strategy.on_bar(state)
        if sig is None:
            return

        target_exp = sig.target_exposure if sig.target_exposure is not None else 0.0
        plan = plan_order_from_target_exposure(
            nav_usdt=scope.nav_usdt,
            btc_qty=scope.btc_free,
            mid_price=event.fill_bar_open,
            target_exposure=target_exp,
            filters=self._filters,
            max_total_exposure=self._guards.max_total_exposure,
            cost=self._cost,
            csv_path=str(self._plan_csv),
        )

        if plan.side != "HOLD" and not self._no_trade:
            self._submit_order(
                plan, event.signal_bar.close_time,
                sig.reason, event.fill_bar_open,
            )

    # ── Order submission ─────────────────────────────────────

    def _submit_order(
        self,
        plan: OrderPlan,
        signal_close_ms: int,
        reason: str,
        mid_price: float,
    ) -> None:
        """Submit order via OrderManager with full CSV logging."""
        # Scale down notional if configured
        qty = plan.qty
        if self._order_notional is not None and mid_price > 0:
            scaled_qty = self._order_notional / mid_price
            qty = round_qty_down(min(qty, scaled_qty), self._filters)

        # Validate
        errors = validate_order(qty, None, self._filters)
        if errors:
            _log.error("Order validation failed: %s", errors)
            return

        coid = make_client_order_id(
            SYMBOL, self._strategy.name(),
            signal_close_ms, plan.side, reason,
        )

        _log.info(
            "Submitting %s %.8f BTC @ MARKET (coid=%s, reason=%s)",
            plan.side, qty, coid, reason,
        )

        rec = self._mgr.submit_order(
            coid, plan.side, "MARKET", qty, reason=reason,
        )

        # Log order
        _csv_append(self._order_csv, _ORDER_FIELDS, [
            _iso_now(), coid, plan.side, f"{qty:.8f}", "MARKET",
            rec.status, rec.exchange_order_id or "", reason,
        ])

        # Log fills + slippage
        fills = self._mgr.get_fills(coid)
        for f in fills:
            if plan.side == "BUY":
                slippage_bps = (f.price / mid_price - 1) * 10000
            else:
                slippage_bps = (1 - f.price / mid_price) * 10000

            _csv_append(self._fill_csv, _FILL_FIELDS, [
                _iso_now(), f.trade_id, coid, f"{f.price:.2f}",
                f"{f.qty:.8f}", f"{f.commission:.8f}",
                f.commission_asset, f"{slippage_bps:.2f}",
            ])
            _csv_append(self._slippage_csv, _SLIPPAGE_FIELDS, [
                _iso_now(), coid, plan.side, f"{mid_price:.2f}",
                f"{f.price:.2f}", f"{slippage_bps:.2f}", f"{f.qty:.8f}",
            ])

        self._guards.record_order()
        _log.info(
            "Order %s: status=%s, %d fills",
            coid, rec.status, len(fills),
        )
        if self._alerts and fills:
            self._alerts.order_filled(
                plan.side, qty, fills[0].price, reason,
            )

        # Throttle
        if self._throttle_sec > 0:
            time.sleep(self._throttle_sec)

    # ── Soak signal generator ────────────────────────────────

    def _soak_signal(self, scope) -> Signal:
        """Generate alternating BUY/SELL for order-path soak testing."""
        if self._soak_side == "BUY":
            self._soak_side = "SELL"
            return Signal(target_exposure=1.0, reason="soak_buy")
        else:
            self._soak_side = "BUY"
            return Signal(target_exposure=0.0, reason="soak_sell")

    # ── D1 bar fetching ──────────────────────────────────────

    def _fetch_new_d1(self) -> list[Bar]:
        """Fetch new D1 bars from Binance since last known."""
        try:
            start_ms = self._d1_last_close_ms + 1 if self._d1_last_close_ms > 0 else None
            raw = self._client.klines(SYMBOL, "1d", start_time=start_ms, limit=10)
        except Exception as e:
            _log.warning("D1 fetch failed: %s", e)
            return []

        new_bars: list[Bar] = []
        server_time = self._client.time()

        for k in raw:
            close_time = int(k[6])
            # Only include completed D1 bars
            if close_time + 5000 < server_time:
                bar = Bar(
                    open_time=int(k[0]),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                    close_time=close_time,
                    taker_buy_base_vol=float(k[9]),
                    interval="1d",
                )
                if close_time > self._d1_last_close_ms:
                    self._d1_bars.append(bar)
                    self._d1_last_close_ms = close_time
                    new_bars.append(bar)

        if new_bars:
            _log.info("Fetched %d new D1 bar(s)", len(new_bars))

        return new_bars

    # ── Warmup bar loading ───────────────────────────────────

    def _load_warmup_bars(self) -> None:
        """Fetch historical bars from Binance for strategy warmup."""
        _log.info("Loading warmup bars (%d days)...", self._warmup_days)
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - (self._warmup_days + 30) * 86_400_000

        try:
            from v10.exchange.marketdata import BinanceBarSource
            source = BinanceBarSource("testnet")
            self._h4_bars = source.fetch_h4(SYMBOL, start_ms)
            self._d1_bars = source.fetch_d1(SYMBOL, start_ms)
        except Exception as e:
            _log.warning(
                "Binance warmup fetch failed (%s), trying mainnet...", e,
            )
            from v10.exchange.marketdata import BinanceBarSource
            source = BinanceBarSource("mainnet")
            self._h4_bars = source.fetch_h4(SYMBOL, start_ms)
            self._d1_bars = source.fetch_d1(SYMBOL, start_ms)

        if self._d1_bars:
            self._d1_last_close_ms = self._d1_bars[-1].close_time

        _log.info(
            "Loaded %d H4 + %d D1 warmup bars",
            len(self._h4_bars), len(self._d1_bars),
        )

    def _load_replay_bars(self) -> None:
        """Load bars from CSV for replay mode."""
        _log.info("Loading replay bars from CSV...")
        # Bars should be pre-loaded via --data flag (handled in main())

    # ── Startup reconciliation ───────────────────────────────

    def _startup_reconcile(self) -> dict:
        """Run OrderManager.reconcile() on startup."""
        _log.info("Running startup reconciliation...")
        updated = self._mgr.reconcile()
        report: dict[str, Any] = {
            "startup_time": _iso_now(),
            "orders_reconciled": len(updated),
            "restarts": [],
        }
        for u in updated:
            fills = self._mgr.get_fills(u.client_order_id)
            entry = {
                "client_order_id": u.client_order_id,
                "pre_status": "non_terminal",
                "post_status": u.status,
                "fills_recovered": len(fills),
                "position_drift": 0.0,
            }
            report["restarts"].append(entry)
            _log.info(
                "Reconciled: %s → %s (%d fills)",
                u.client_order_id, u.status, len(fills),
            )
        return report

    # ── Helpers ───────────────────────────────────────────────

    def _should_stop(self) -> bool:
        if self._shutdown:
            return True
        if self._guards.halted:
            return True
        if self._max_cycles > 0 and self._cycles >= self._max_cycles:
            return True
        return False

    def _handle_signal(self, signum, frame):
        _log.info("Received signal %d, shutting down...", signum)
        self._shutdown = True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="V10 Live Trading Runner (E5_ema21D1)",
    )
    parser.add_argument(
        "--config", required=True,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--outdir", default="out/live",
        help="Output directory",
    )
    parser.add_argument(
        "--mode", default="realtime",
        choices=["soak_orders", "soak_notrade", "replay", "realtime"],
        help="Operating mode",
    )
    parser.add_argument(
        "--data", default=None,
        help="CSV data file for replay mode",
    )
    parser.add_argument("--max-cycles", type=int, default=0,
                        help="Max cycles (0=unlimited)")
    parser.add_argument("--cycle-seconds", type=float, default=30.0,
                        help="Sleep between polls (seconds)")
    parser.add_argument("--throttle-sec", type=float, default=2.0,
                        help="Min delay between exchange sends")
    parser.add_argument("--no-trade", action="store_true",
                        help="Dry run — plan but don't send orders")
    parser.add_argument("--shadow", action="store_true",
                        help="Enable parity checker (shadow replay)")
    parser.add_argument("--fault-inject-rate", type=float, default=0.0,
                        help="Crash probability per order (0.0-1.0)")
    parser.add_argument("--fault-points", default="AFTER_SEND",
                        help="Comma-separated crash points")
    parser.add_argument("--order-notional-usdt", type=float, default=None,
                        help="Scale-down order size to this notional")
    parser.add_argument("--qty-tolerance-pct", type=float, default=2.0,
                        help="Parity checker qty tolerance (%)")
    parser.add_argument("--alerts", action="store_true",
                        help="Enable alerts (Telegram/webhook if env vars set)")

    args = parser.parse_args(argv)

    # Setup logging
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(outdir / "bot.log"),
            logging.StreamHandler(sys.stderr),
        ],
    )

    # Load config
    config = load_config(args.config)
    strategy_name = config.strategy.name
    scenario_name = config.engine.scenario_eval
    cost = SCENARIOS[scenario_name]
    warmup_days = config.engine.warmup_days
    initial_cash = config.engine.initial_cash

    _log.info("Config: %s", args.config)
    _log.info("Strategy: %s | Scenario: %s (%d bps RT)",
              strategy_name, scenario_name, int(cost.round_trip_bps))

    # Build strategy
    entry = STRATEGY_REGISTRY.get(strategy_name)
    if entry is None:
        _log.error("Unknown strategy: %s", strategy_name)
        sys.exit(1)

    strategy, cfg = build_from_config(config)

    def strategy_factory():
        s, _ = build_from_config(config)
        return s

    # Init exchange client
    client = BinanceSpotClient()
    _log.info("Exchange: %s", client.base_url)

    # Fetch exchange filters
    filters = fetch_symbol_info(client, SYMBOL)
    _log.info(
        "Filters: step=%s min_qty=%s min_notional=%s",
        filters.step_size, filters.min_qty, filters.min_notional,
    )

    # Risk guards from config
    risk_params = config.risk if hasattr(config, "risk") else None
    guards = RiskGuards(
        kill_switch_dd=getattr(risk_params, "kill_switch_dd_total", 0.45) if risk_params else 0.45,
        max_daily_orders=getattr(risk_params, "max_daily_orders", 5) if risk_params else 5,
        max_total_exposure=getattr(risk_params, "max_total_exposure", 1.0) if risk_params else 1.0,
        min_notional_usdt=getattr(risk_params, "min_notional_usdt", 10.0) if risk_params else 10.0,
    )

    # Alerts
    alerts = AlertDispatcher() if args.alerts else None

    # Build runner
    runner = LiveRunner(
        client=client,
        strategy=strategy,
        strategy_factory=strategy_factory,
        config=config,
        cost=cost,
        filters=filters,
        outdir=outdir,
        mode=args.mode,
        max_cycles=args.max_cycles,
        cycle_seconds=args.cycle_seconds,
        throttle_sec=args.throttle_sec,
        no_trade=args.no_trade,
        shadow=args.shadow,
        fault_inject_rate=args.fault_inject_rate,
        fault_points=args.fault_points.split(","),
        order_notional_usdt=args.order_notional_usdt,
        qty_tolerance_pct=args.qty_tolerance_pct,
        warmup_days=warmup_days,
        initial_cash=initial_cash,
        risk_guards=guards,
        alerts=alerts,
    )

    # Load CSV data for replay mode
    if args.mode == "replay":
        if not args.data:
            _log.error("--data required for replay mode")
            sys.exit(1)
        source = CsvBarSource(args.data)
        runner._h4_bars = source.fetch_h4(SYMBOL)
        runner._d1_bars = source.fetch_d1(SYMBOL)
        if runner._d1_bars:
            runner._d1_last_close_ms = runner._d1_bars[-1].close_time
        _log.info(
            "Replay: %d H4 + %d D1 bars",
            len(runner._h4_bars), len(runner._d1_bars),
        )

    # Run
    result = runner.run()

    # Stamp run metadata
    config_snap = config_to_dict(config)
    config_snap["live"] = {
        "mode": args.mode,
        "shadow": args.shadow,
        "no_trade": args.no_trade,
        "fault_inject_rate": args.fault_inject_rate,
    }
    stamp_run_meta(
        str(outdir),
        argv=sys.argv if argv is None else ["live"] + list(argv),
        config=config_snap,
        data_path=args.data,
    )

    _log.info("Exit: %s (%d cycles)", result["exit_reason"], result["cycles"])


if __name__ == "__main__":
    main()
