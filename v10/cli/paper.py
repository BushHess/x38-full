"""Paper/shadow trading runner — CLI entry point.

Usage:
    # Replay from CSV (fast):
    python -m v10.cli.paper \\
        --source csv --data bars.csv \\
        --config configs/baseline_legacy.live.yaml \\
        --outdir out_paper

    # Live shadow from Binance REST:
    python -m v10.cli.paper \\
        --source binance --env mainnet \\
        --config configs/baseline_legacy.live.yaml \\
        --outdir out_paper

    # Deterministic replay from cached klines:
    python -m v10.cli.paper \\
        --replay paper_kline_cache/ \\
        --config configs/baseline_legacy.live.yaml \\
        --outdir out_paper

Outputs:
    paper_signals.csv  — decision log
    paper_orders.csv   — simulated fills
    paper_equity.csv   — equity curve
    paper_state.db     — SQLite state persistence
    run_meta.json      — run metadata
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v10.core.formatting import ms_to_iso
from v10.core.config import load_config, config_to_dict
from v10.core.execution import ExecutionModel, Portfolio
from v10.core.meta import stamp_run_meta
from v10.core.types import (
    Bar,
    CostConfig,
    Fill,
    MarketState,
    Order,
    Side,
    Signal,
    SCENARIOS,
)
from v10.exchange.marketdata import (
    BinanceBarSource,
    CsvBarSource,
    cache_bars,
    load_cached_bars,
)
from v10.strategies.base import Strategy
from v10.strategies.buy_and_hold import BuyAndHold
from v10.strategies.v8_apex import V8ApexStrategy
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy
from strategies.vtrend_ema21_d1.strategy import VTrendEma21D1Strategy


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: dict[str, type[Strategy]] = {
    "buy_and_hold": BuyAndHold,
    "v8_apex": V8ApexStrategy,
    "vtrend_e5_ema21_d1": VTrendE5Ema21D1Strategy,
    "vtrend_ema21_d1": VTrendEma21D1Strategy,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


_EXPO_THRESHOLD = 0.005  # same as engine.py


# ---------------------------------------------------------------------------
# SQLite state persistence
# ---------------------------------------------------------------------------

class PaperStateDB:
    """SQLite wrapper for paper trading state persistence."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        c = self._conn
        c.execute("""
            CREATE TABLE IF NOT EXISTS state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_h4_close_ms INTEGER NOT NULL,
                last_d1_close_ms INTEGER
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS planned_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_h4_close_ms INTEGER NOT NULL,
                target_exposure REAL,
                reason TEXT NOT NULL,
                executed INTEGER DEFAULT 0,
                fill_h4_open_ms INTEGER,
                fill_side TEXT,
                fill_qty REAL,
                fill_price REAL,
                scenario TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_iso TEXT NOT NULL,
                h4_close_ms INTEGER NOT NULL,
                d1_close_ms INTEGER,
                target_exposure REAL,
                entry_reason TEXT DEFAULT '',
                exit_reason TEXT DEFAULT '',
                flags_json TEXT DEFAULT '{}'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS equity_snaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_iso TEXT NOT NULL,
                close_time_ms INTEGER NOT NULL,
                nav_mid REAL NOT NULL,
                cash REAL NOT NULL,
                btc_qty REAL NOT NULL,
                exposure REAL NOT NULL
            )
        """)
        c.commit()

    def get_last_state(self) -> tuple[int | None, int | None]:
        """Return (last_h4_close_ms, last_d1_close_ms) or (None, None)."""
        row = self._conn.execute(
            "SELECT last_h4_close_ms, last_d1_close_ms FROM state WHERE id = 1",
        ).fetchone()
        if row:
            return row[0], row[1]
        return None, None

    def update_state(self, h4_close_ms: int, d1_close_ms: int | None) -> None:
        self._conn.execute(
            """
            INSERT INTO state (id, last_h4_close_ms, last_d1_close_ms)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                last_h4_close_ms = excluded.last_h4_close_ms,
                last_d1_close_ms = excluded.last_d1_close_ms
            """,
            (h4_close_ms, d1_close_ms),
        )
        self._conn.commit()

    def insert_signal(
        self,
        time_iso: str,
        h4_close_ms: int,
        d1_close_ms: int | None,
        target_exposure: float | None,
        entry_reason: str,
        exit_reason: str,
        flags_json: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO signals (time_iso, h4_close_ms, d1_close_ms,
                                 target_exposure, entry_reason, exit_reason,
                                 flags_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (time_iso, h4_close_ms, d1_close_ms, target_exposure,
             entry_reason, exit_reason, flags_json),
        )
        self._conn.commit()

    def insert_planned_order(
        self,
        signal_h4_close_ms: int,
        target_exposure: float | None,
        reason: str,
        scenario: str,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO planned_orders (signal_h4_close_ms, target_exposure,
                                        reason, scenario)
            VALUES (?, ?, ?, ?)
            """,
            (signal_h4_close_ms, target_exposure, reason, scenario),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def mark_order_executed(
        self,
        order_id: int,
        fill_h4_open_ms: int,
        side: str,
        qty: float,
        price: float,
    ) -> None:
        self._conn.execute(
            """
            UPDATE planned_orders SET executed = 1,
                fill_h4_open_ms = ?, fill_side = ?,
                fill_qty = ?, fill_price = ?
            WHERE id = ?
            """,
            (fill_h4_open_ms, side, qty, price, order_id),
        )
        self._conn.commit()

    def insert_equity_snap(
        self,
        time_iso: str,
        close_time_ms: int,
        nav_mid: float,
        cash: float,
        btc_qty: float,
        exposure: float,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO equity_snaps (time_iso, close_time_ms, nav_mid,
                                      cash, btc_qty, exposure)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (time_iso, close_time_ms, nav_mid, cash, btc_qty, exposure),
        )
        self._conn.commit()

    def clear(self) -> None:
        """Clear all data (for fresh runs)."""
        for table in ("state", "planned_orders", "signals", "equity_snaps"):
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Paper runner
# ---------------------------------------------------------------------------

class PaperRunner:
    """Paper/shadow trading runner.

    Processes H4 bars with the same next-open fill logic as BacktestEngine.
    Records signals, orders, and equity to SQLite and CSV.
    """

    def __init__(
        self,
        h4_bars: list[Bar],
        d1_bars: list[Bar],
        strategy: Strategy,
        cost: CostConfig,
        scenario_name: str,
        initial_cash: float,
        warmup_days: int,
        db: PaperStateDB,
        entry_nav_pre_cost: bool = True,
    ) -> None:
        self.h4_bars = h4_bars
        self.d1_bars = d1_bars
        self.strategy = strategy
        self.cost = cost
        self.scenario_name = scenario_name
        self.initial_cash = initial_cash
        self.warmup_days = warmup_days
        self.db = db
        self.portfolio = Portfolio(
            initial_cash, ExecutionModel(cost), entry_nav_pre_cost,
        )
        # Collected output rows
        self.signal_rows: list[dict[str, Any]] = []
        self.order_rows: list[dict[str, Any]] = []
        self.equity_rows: list[dict[str, Any]] = []

    def run(self) -> None:
        """Run the paper trading loop (matches BacktestEngine bar loop)."""
        h4 = self.h4_bars
        d1 = self.d1_bars
        if not h4:
            raise ValueError("No H4 bars to process")

        self.strategy.on_init(h4, d1)

        # Determine warmup boundary
        report_start_ms: int | None = None
        if self.warmup_days > 0:
            report_start_ms = (
                h4[0].open_time + self.warmup_days * 86_400_000
            )

        pending: Signal | None = None
        pending_order_id: int | None = None
        d1_idx = -1

        for i, bar in enumerate(h4):
            # Strict MTF alignment: latest D1 bar whose close_time
            # is STRICTLY BEFORE this H4 bar's close_time.
            while (
                d1_idx + 1 < len(d1)
                and d1[d1_idx + 1].close_time < bar.close_time
            ):
                d1_idx += 1

            is_warmup = (
                report_start_ms is not None
                and bar.close_time < report_start_ms
            )

            # --- Step 1: execute pending signal at bar OPEN ---------------
            if pending is not None:
                fills = self._apply_signal(pending, bar.open, bar.open_time)
                if fills and not is_warmup:
                    for f in fills:
                        row = {
                            "time_iso": ms_to_iso(f.ts_ms),
                            "side": f.side.value,
                            "qty": f.qty,
                            "est_fill_price": f.price,
                            "scenario": self.scenario_name,
                            "reason": f.reason,
                        }
                        self.order_rows.append(row)
                        if pending_order_id is not None:
                            self.db.mark_order_executed(
                                pending_order_id, f.ts_ms,
                                f.side.value, f.qty, f.price,
                            )
                pending = None
                pending_order_id = None

            # --- Step 2: equity snapshot at bar CLOSE ---------------------
            if not is_warmup:
                mid = bar.close
                pf = self.portfolio
                snap = {
                    "time_iso": ms_to_iso(bar.close_time),
                    "close_time_ms": bar.close_time,
                    "nav_mid": pf.nav(mid),
                    "cash": pf.cash,
                    "btc_qty": pf.btc_qty,
                    "exposure": pf.exposure(mid),
                }
                self.equity_rows.append(snap)
                self.db.insert_equity_snap(
                    snap["time_iso"], bar.close_time,
                    snap["nav_mid"], snap["cash"],
                    snap["btc_qty"], snap["exposure"],
                )

            # --- Step 3: call strategy at bar CLOSE -----------------------
            state = self._build_state(bar, h4, d1, i, d1_idx)
            signal = self.strategy.on_bar(state)

            if signal is not None and not is_warmup:
                d1_close_ms = (
                    d1[d1_idx].close_time if d1_idx >= 0 else None
                )

                # Classify entry vs exit reason
                entry_reason, exit_reason = self._classify_signal(
                    signal, bar.close,
                )

                sig_row = {
                    "time_iso": ms_to_iso(bar.close_time),
                    "h4_close_ms": bar.close_time,
                    "d1_close_ms": d1_close_ms,
                    "target_exposure": signal.target_exposure,
                    "entry_reason": entry_reason,
                    "exit_reason": exit_reason,
                    "flags_json": json.dumps(
                        {
                            "signal_reason": signal.reason,
                            "has_orders": bool(signal.orders),
                        },
                        sort_keys=True,
                    ),
                }
                self.signal_rows.append(sig_row)
                self.db.insert_signal(
                    sig_row["time_iso"],
                    sig_row["h4_close_ms"],
                    sig_row["d1_close_ms"],
                    sig_row["target_exposure"],
                    sig_row["entry_reason"],
                    sig_row["exit_reason"],
                    sig_row["flags_json"],
                )

                # Store as pending for next-bar fill
                pending = signal
                pending_order_id = self.db.insert_planned_order(
                    bar.close_time,
                    signal.target_exposure,
                    signal.reason,
                    self.scenario_name,
                )

            # Update state tracking
            if not is_warmup:
                d1_close_ms = (
                    d1[d1_idx].close_time if d1_idx >= 0 else None
                )
                self.db.update_state(bar.close_time, d1_close_ms)

    # -- internals ---------------------------------------------------------

    def _classify_signal(
        self, signal: Signal, mid: float,
    ) -> tuple[str, str]:
        """Return (entry_reason, exit_reason) from a signal."""
        current_exp = self.portfolio.exposure(mid)

        if signal.orders:
            has_buy = any(o.side == Side.BUY for o in signal.orders)
            has_sell = any(o.side == Side.SELL for o in signal.orders)
            entry = signal.reason if has_buy else ""
            exit_ = signal.reason if has_sell else ""
            return entry, exit_

        if signal.target_exposure is not None:
            target = signal.target_exposure
            if target > current_exp + _EXPO_THRESHOLD:
                return signal.reason, ""
            if target < current_exp - _EXPO_THRESHOLD:
                return "", signal.reason
        return "", ""

    def _build_state(
        self,
        bar: Bar,
        h4: list[Bar],
        d1: list[Bar],
        h4_idx: int,
        d1_idx: int,
    ) -> MarketState:
        pf = self.portfolio
        mid = bar.close
        return MarketState(
            bar=bar,
            h4_bars=h4,
            d1_bars=d1,
            bar_index=h4_idx,
            d1_index=d1_idx,
            cash=pf.cash,
            btc_qty=pf.btc_qty,
            nav=pf.nav(mid),
            exposure=pf.exposure(mid),
            entry_price_avg=pf.entry_price_avg,
            position_entry_nav=pf.position_entry_nav,
        )

    def _apply_signal(
        self, signal: Signal, mid: float, ts_ms: int,
    ) -> list[Fill]:
        """Convert a Signal into portfolio buy/sell actions.

        Returns list of Fill objects generated.
        """
        fills: list[Fill] = []
        pf = self.portfolio

        # Mode 1: explicit orders take priority
        if signal.orders:
            for order in signal.orders:
                reason = order.reason or signal.reason
                if order.side == Side.BUY:
                    f = pf.buy(order.qty, mid, ts_ms, reason)
                else:
                    f = pf.sell(order.qty, mid, ts_ms, reason)
                if f:
                    fills.append(f)
            return fills

        # Mode 2: target_exposure
        if signal.target_exposure is not None:
            target = max(0.0, min(1.0, signal.target_exposure))
            current = pf.exposure(mid)
            delta = target - current

            if target < _EXPO_THRESHOLD and pf.btc_qty > 1e-8:
                f = pf.sell(pf.btc_qty, mid, ts_ms, signal.reason)
                if f:
                    fills.append(f)
            elif delta > _EXPO_THRESHOLD:
                nav = pf.nav(mid)
                buy_value = delta * nav
                qty = buy_value / mid
                f = pf.buy(qty, mid, ts_ms, signal.reason)
                if f:
                    fills.append(f)
            elif delta < -_EXPO_THRESHOLD:
                nav = pf.nav(mid)
                sell_value = abs(delta) * nav
                qty = min(sell_value / mid, pf.btc_qty)
                f = pf.sell(qty, mid, ts_ms, signal.reason)
                if f:
                    fills.append(f)

        return fills


# ---------------------------------------------------------------------------
# CSV output writers
# ---------------------------------------------------------------------------

def _write_signals_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "time_iso", "h4_close_ms", "d1_close_ms", "target_exposure",
            "entry_reason", "exit_reason", "flags_json",
        ])
        for r in rows:
            te = r["target_exposure"]
            te_str = f"{te:.6f}" if te is not None else ""
            d1 = r["d1_close_ms"]
            d1_str = str(d1) if d1 is not None else ""
            w.writerow([
                r["time_iso"], r["h4_close_ms"], d1_str,
                te_str, r["entry_reason"], r["exit_reason"],
                r["flags_json"],
            ])


def _write_orders_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "time_iso", "side", "qty", "est_fill_price", "scenario", "reason",
        ])
        for r in rows:
            w.writerow([
                r["time_iso"], r["side"], f"{r['qty']:.8f}",
                f"{r['est_fill_price']:.2f}", r["scenario"], r["reason"],
            ])


def _write_equity_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_iso", "close_time_ms", "nav_mid", "cash", "btc_qty", "exposure"])
        for r in rows:
            w.writerow([
                r["time_iso"], r["close_time_ms"],
                f"{r['nav_mid']:.2f}", f"{r['cash']:.2f}",
                f"{r['btc_qty']:.8f}", f"{r['exposure']:.6f}",
            ])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="V10 Paper/Shadow Trading Runner",
    )
    # Source selection
    parser.add_argument(
        "--source", choices=["csv", "binance"], default=None,
        help="Data source: csv (replay) or binance (REST klines)",
    )
    parser.add_argument(
        "--data", default=None,
        help="Path to CSV data file (required when --source=csv)",
    )
    parser.add_argument(
        "--env", default="mainnet",
        help="Binance environment (default: mainnet)",
    )
    parser.add_argument(
        "--safety-buffer-ms", type=int, default=5000,
        help="Candle completeness buffer in ms (default: 5000)",
    )

    # Replay
    parser.add_argument(
        "--replay", default=None, metavar="CACHE_DIR",
        help="Replay from cached klines directory (deterministic)",
    )

    # Config and output
    parser.add_argument(
        "--config", required=True,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--outdir", default="out/paper",
        help="Output directory (default: out_paper)",
    )
    parser.add_argument(
        "--cache-dir", default=None,
        help="Kline cache directory (default: <outdir>/paper_kline_cache)",
    )
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD")

    args = parser.parse_args(argv)

    # Validate source args
    if args.replay is None and args.source is None:
        parser.error("Either --source or --replay is required")
    if args.source == "csv" and args.data is None:
        parser.error("--data is required when --source=csv")

    # Load config
    config = load_config(args.config)
    symbol = config.engine.symbol
    warmup_days = config.engine.warmup_days
    initial_cash = config.engine.initial_cash
    scenario_name = config.engine.scenario_eval
    cost = SCENARIOS[scenario_name]

    print(f"Config: {args.config}")
    print(f"Scenario: {scenario_name} ({cost.round_trip_bps:.0f} bps RT)")

    # Setup output directory
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ----- Fetch bars from source -----
    if args.replay:
        cache_dir = Path(args.replay)
        print(f"Replaying from cache: {cache_dir}")
        h4_bars = load_cached_bars(cache_dir / f"{symbol}_4h.csv")
        d1_bars = load_cached_bars(cache_dir / f"{symbol}_1d.csv")

    elif args.source == "csv":
        print(f"Loading CSV: {args.data}")
        source = CsvBarSource(args.data)
        start_ms = (
            _date_to_ms(args.start) - warmup_days * 86_400_000
            if args.start else None
        )
        end_ms = (
            _date_to_ms(args.end) + 86_400_000 - 1
            if args.end else None
        )
        h4_bars = source.fetch_h4(symbol, start_ms, end_ms)
        d1_bars = source.fetch_d1(symbol, start_ms, end_ms)

    else:
        # Binance REST
        print(f"Fetching from Binance ({args.env})...")
        source = BinanceBarSource(args.env, args.safety_buffer_ms)
        if args.start:
            start_ms = _date_to_ms(args.start) - warmup_days * 86_400_000
        else:
            import time
            now_ms = int(time.time() * 1000)
            start_ms = now_ms - (warmup_days + 30) * 86_400_000
        end_ms = (
            _date_to_ms(args.end) + 86_400_000 - 1
            if args.end else None
        )
        h4_bars = source.fetch_h4(symbol, start_ms, end_ms)
        d1_bars = source.fetch_d1(symbol, start_ms, end_ms)

    print(f"  H4 bars: {len(h4_bars)}, D1 bars: {len(d1_bars)}")
    if not h4_bars:
        print("ERROR: No H4 bars available", file=sys.stderr)
        sys.exit(1)

    # Cache klines (unless replaying)
    if args.replay is None:
        kline_cache = (
            Path(args.cache_dir) if args.cache_dir
            else outdir / "paper_kline_cache"
        )
        cache_bars(h4_bars, kline_cache / f"{symbol}_4h.csv")
        cache_bars(d1_bars, kline_cache / f"{symbol}_1d.csv")
        print(f"  Cached klines to {kline_cache}/")

    # ----- Initialize strategy -----
    strategy_name = config.strategy.name
    cls = STRATEGY_REGISTRY.get(strategy_name)
    if cls is None:
        print(
            f"Unknown strategy '{strategy_name}'. "
            f"Available: {', '.join(sorted(STRATEGY_REGISTRY))}",
            file=sys.stderr,
        )
        sys.exit(1)
    # Build strategy with config params (generic for all strategies).
    if config.strategy.params:
        from validation.strategy_factory import _build_config_obj
        cfg = _build_config_obj(strategy_name, config.strategy.params)
        if cfg is not None:
            strategy = cls(cfg)
        else:
            strategy = cls()
    else:
        strategy = cls()

    print(f"Strategy: {strategy.name()}")

    # ----- Initialize SQLite state -----
    db = PaperStateDB(outdir / "paper_state.db")
    db.clear()  # Fresh run — replay from start for correct state rebuild

    entry_nav_pre_cost = (
        config.strategy.params.get("emergency_ref", "pre_cost_legacy")
        != "post_cost"
    )

    # ----- Run paper trader -----
    runner = PaperRunner(
        h4_bars=h4_bars,
        d1_bars=d1_bars,
        strategy=strategy,
        cost=cost,
        scenario_name=scenario_name,
        initial_cash=initial_cash,
        warmup_days=warmup_days,
        db=db,
        entry_nav_pre_cost=entry_nav_pre_cost,
    )

    print("Running paper trader...")
    runner.run()

    # ----- Write CSV outputs -----
    _write_signals_csv(runner.signal_rows, outdir / "paper_signals.csv")
    _write_orders_csv(runner.order_rows, outdir / "paper_orders.csv")
    _write_equity_csv(runner.equity_rows, outdir / "paper_equity.csv")

    db.close()

    # ----- Stamp run metadata -----
    config_snap = config_to_dict(config)
    config_snap["paper"] = {
        "source": args.source or "replay",
        "replay": args.replay,
        "scenario": scenario_name,
        "cost": dataclasses.asdict(cost),
    }
    stamp_run_meta(
        args.outdir,
        argv=sys.argv if argv is None else ["paper"] + list(argv),
        config=config_snap,
        data_path=args.data,
    )

    # ----- Print summary -----
    print(f"\nResults written to {outdir}/")
    print(f"  Signals: {len(runner.signal_rows)}")
    print(f"  Orders:  {len(runner.order_rows)}")
    print(f"  Equity:  {len(runner.equity_rows)} snapshots")
    if runner.equity_rows:
        first = runner.equity_rows[0]
        last = runner.equity_rows[-1]
        print(f"  NAV: {first['nav_mid']:.2f} -> {last['nav_mid']:.2f}")


if __name__ == "__main__":
    main()
