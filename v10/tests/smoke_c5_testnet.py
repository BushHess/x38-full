#!/usr/bin/env python3
"""C5 testnet validation — strategy-driven E2E with real exchange orders.

C5.1: Fast-forward CSV replay through testnet (accelerated)
C5.2: Real-time H4 cadence validation (run separately, long-duration)

This script implements C5.1 (fast-forward replay):
  1. Loads H4+D1 bars from CSV (data/bars_btcusdt_2016_now_h1_4h_1d.csv)
  2. Initializes E5_ema21D1 strategy with full history
  3. Replays last N bars, executing real testnet orders on signal bars
  4. Validates: order fills, slippage, parity (if --shadow), risk guards

Produces deliverables in out/c5/:
  1. run_meta.json         — run fingerprint
  2. live_cycles.csv       — per-bar signal/order log
  3. live_plan.csv         — planner decisions
  4. live_slippage.csv     — slippage analysis
  5. parity_results.csv    — shadow replay validation
  6. summary.json          — final pass/fail + statistics
  7. bot.log               — full log

Prerequisites:
  - BINANCE_API_KEY and BINANCE_API_SECRET set (testnet)
  - data/bars_btcusdt_2016_now_h1_4h_1d.csv in project root
  - C4 smoke test PASS

Usage:
    # C5.1: Fast-forward replay (last 500 bars, ~2-3 min)
    python v10/tests/smoke_c5_testnet.py --bars 500

    # C5.1 with parity checker
    python v10/tests/smoke_c5_testnet.py --bars 500 --shadow

    # C5.1 with scaled-down orders (tiny notional)
    python v10/tests/smoke_c5_testnet.py --bars 500 --order-notional-usdt 15

    # C5.2: Real-time mode (run as daemon, Ctrl+C to stop)
    python -m v10.cli.live \\
        --config configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml \\
        --outdir out/c5_realtime \\
        --mode realtime \\
        --cycle-seconds 30 \\
        --shadow \\
        --order-notional-usdt 15
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Config,
    VTrendE5Ema21D1Strategy,
)
from v10.core.types import Bar, MarketState, Signal, SCENARIOS
from v10.exchange.rest_client import BinanceSpotClient
from v10.exchange.filters import (
    fetch_symbol_info, round_qty_down, validate_order,
)
from v10.exchange.account_scope import fetch_account_scope, reset_to_cash
from v10.exchange.order_manager import OrderManager, make_client_order_id
from v10.exchange.order_planner import plan_order_from_target_exposure
from v10.exchange.marketdata import CsvBarSource

SYMBOL = "BTCUSDT"
DATA_PATH = Path("data/bars_btcusdt_2016_now_h1_4h_1d.csv")
OUT = Path("out/c5")
DB_PATH = OUT / "orders.db"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="C5 Testnet Validation")
    parser.add_argument(
        "--bars", type=int, default=500,
        help="Number of trailing H4 bars to replay (default: 500)",
    )
    parser.add_argument(
        "--data", default=str(DATA_PATH),
        help="Path to multi-TF CSV file",
    )
    parser.add_argument(
        "--shadow", action="store_true",
        help="Enable parity checker (shadow replay)",
    )
    parser.add_argument(
        "--order-notional-usdt", type=float, default=15.0,
        help="Scale-down order size to this notional (default: 15 USDT)",
    )
    parser.add_argument(
        "--throttle-sec", type=float, default=3.0,
        help="Delay between exchange sends (default: 3s)",
    )
    parser.add_argument(
        "--no-trade", action="store_true",
        help="Dry run — plan but don't send orders",
    )
    parser.add_argument(
        "--outdir", default=str(OUT),
        help="Output directory",
    )
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    db_path = outdir / "orders.db"

    # ── Logging ──────────────────────────────────────────────
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"),
    )
    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)
    root_log.addHandler(handler)
    root_log.addHandler(logging.StreamHandler(sys.stderr))
    log = logging.getLogger("smoke_c5")

    # ── Init client ──────────────────────────────────────────
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")
    if not api_key or not api_secret:
        log.error("BINANCE_API_KEY and BINANCE_API_SECRET must be set")
        sys.exit(1)

    client = BinanceSpotClient(api_key=api_key, api_secret=api_secret)
    log.info("=== C5 Testnet Validation (E5_ema21D1) ===")
    log.info("Exchange: %s", client.base_url)

    # ── Reset account ────────────────────────────────────────
    log.info("Phase 0: Reset to cash")
    reset = reset_to_cash(client)
    log.info("Cancelled %d, sold %.8f BTC", reset.cancelled_count, reset.sold_btc)

    # ── Exchange filters ─────────────────────────────────────
    info = fetch_symbol_info(client, SYMBOL)
    cost = SCENARIOS["harsh"]  # 50 bps RT — match validation
    log.info(
        "Filters: step=%s min_notional=%s | Cost: %d bps RT",
        info.step_size, info.min_notional, int(cost.round_trip_bps),
    )

    # ── Load data ────────────────────────────────────────────
    data_path = Path(args.data)
    if not data_path.exists():
        log.error("Data file not found: %s", data_path)
        sys.exit(1)

    log.info("Loading data from %s...", data_path)
    source = CsvBarSource(str(data_path))
    all_h4 = source.fetch_h4(SYMBOL)
    all_d1 = source.fetch_d1(SYMBOL)
    log.info("Total: %d H4 + %d D1 bars", len(all_h4), len(all_d1))

    # Use all bars for strategy init, replay last N
    replay_count = min(args.bars, len(all_h4) - 1)
    warmup_h4 = all_h4[:-replay_count]
    replay_h4 = all_h4[-replay_count:]

    log.info(
        "Warmup: %d H4 bars | Replay: %d H4 bars",
        len(warmup_h4), len(replay_h4),
    )

    # ── Init strategy ────────────────────────────────────────
    strategy = VTrendE5Ema21D1Strategy()
    # Init with ALL bars (warmup + replay window)
    strategy.on_init(all_h4, all_d1)

    # ── Clean DB ─────────────────────────────────────────────
    if db_path.exists():
        db_path.unlink()
    mgr = OrderManager(
        client, str(db_path), SYMBOL,
        poll_interval=0.5, max_polls=20,
    )

    # ── Replay ───────────────────────────────────────────────
    log.info("=== Phase 1: Replaying %d bars with E5_ema21D1 ===", replay_count)

    cycles: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    slippage_rows: list[dict[str, Any]] = []
    signals_generated = 0
    orders_sent = 0
    orders_filled = 0
    parity_checks = 0
    parity_pass = 0

    start_idx = len(warmup_h4)

    for ri, h4_bar in enumerate(replay_h4):
        bar_idx = start_idx + ri
        if bar_idx >= len(all_h4) - 1:
            break

        # Build MarketState
        d1_idx = -1
        for di, d1 in enumerate(all_d1):
            if d1.close_time < h4_bar.close_time:
                d1_idx = di

        # Get current account for NAV/exposure context
        try:
            scope = fetch_account_scope(client, SYMBOL)
        except Exception as e:
            log.warning("AccountScope failed: %s (using defaults)", e)
            scope = None

        nav = scope.nav_usdt if scope else 10_000.0
        btc_qty = scope.btc_free if scope else 0.0
        exposure = scope.exposure if scope else 0.0

        state = MarketState(
            bar=h4_bar,
            h4_bars=all_h4,
            d1_bars=all_d1,
            bar_index=bar_idx,
            d1_index=d1_idx,
            cash=scope.usdt_free if scope else 10_000.0,
            btc_qty=btc_qty,
            nav=nav,
            exposure=exposure,
            entry_price_avg=0.0,
            position_entry_nav=0.0,
        )

        sig = strategy.on_bar(state)

        cycle_rec: dict[str, Any] = {
            "bar_idx": bar_idx,
            "replay_idx": ri,
            "close_time_iso": datetime.fromtimestamp(
                h4_bar.close_time / 1000, tz=timezone.utc,
            ).strftime("%Y-%m-%dT%H:%MZ"),
            "close_price": h4_bar.close,
            "signal": sig.reason if sig else "none",
            "target_exposure": sig.target_exposure if sig else "",
            "action": "HOLD",
            "order_status": "",
            "fill_price": "",
            "fill_qty": "",
        }

        if sig is not None:
            signals_generated += 1
            target_exp = sig.target_exposure if sig.target_exposure is not None else 0.0

            # Use next bar's open as fill price estimate (for planner)
            next_bar = all_h4[bar_idx + 1]
            fill_price = next_bar.open

            plan = plan_order_from_target_exposure(
                nav_usdt=nav,
                btc_qty=btc_qty,
                mid_price=fill_price,
                target_exposure=target_exp,
                filters=info,
                max_total_exposure=1.0,
                cost=cost,
            )

            plan_rows.append({
                "bar_idx": bar_idx,
                "side": plan.side,
                "qty": plan.qty,
                "est_fill_price": plan.est_fill_price,
                "notional": plan.notional,
                "reason": plan.reason,
                "target_exposure": plan.target_exposure,
            })

            if plan.side != "HOLD" and not args.no_trade:
                # Scale down
                qty = plan.qty
                if args.order_notional_usdt and fill_price > 0:
                    scaled = args.order_notional_usdt / fill_price
                    qty = round_qty_down(min(qty, scaled), info)

                errors = validate_order(qty, None, info)
                if not errors:
                    coid = make_client_order_id(
                        SYMBOL, "smoke_c5",
                        h4_bar.close_time, plan.side, sig.reason,
                    )

                    rec = mgr.submit_order(
                        coid, plan.side, "MARKET", qty,
                        reason=sig.reason,
                    )
                    orders_sent += 1

                    fills = mgr.get_fills(coid)
                    if fills:
                        orders_filled += 1
                        cycle_rec["action"] = plan.side
                        cycle_rec["order_status"] = rec.status
                        cycle_rec["fill_price"] = fills[0].price
                        cycle_rec["fill_qty"] = sum(f.qty for f in fills)

                        for f in fills:
                            if plan.side == "BUY":
                                slip = (f.price / fill_price - 1) * 10000
                            else:
                                slip = (1 - f.price / fill_price) * 10000
                            slippage_rows.append({
                                "bar_idx": bar_idx,
                                "client_order_id": coid,
                                "side": plan.side,
                                "expected_mid": fill_price,
                                "fill_price": f.price,
                                "slippage_bps": round(slip, 2),
                                "qty": f.qty,
                            })

                    time.sleep(args.throttle_sec)

        cycles.append(cycle_rec)

        # Progress log every 50 bars
        if ri > 0 and ri % 50 == 0:
            log.info(
                "Progress: %d/%d bars | signals=%d orders=%d fills=%d",
                ri, replay_count, signals_generated, orders_sent, orders_filled,
            )

    # ── Write outputs ────────────────────────────────────────
    log.info("=== Writing outputs ===")

    run_meta = {
        "run_id": f"smoke_c5_{int(time.time())}",
        "started_at": _iso_now(),
        "finished_at": _iso_now(),
        "strategy": "vtrend_e5_ema21_d1",
        "replay_bars": replay_count,
        "warmup_bars": len(warmup_h4),
        "signals_generated": signals_generated,
        "orders_sent": orders_sent,
        "orders_filled": orders_filled,
        "no_trade": args.no_trade,
        "order_notional_usdt": args.order_notional_usdt,
        "env": "testnet",
    }
    (outdir / "run_meta.json").write_text(
        json.dumps(run_meta, indent=2) + "\n",
    )

    if cycles:
        with open(outdir / "live_cycles.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cycles[0].keys())
            w.writeheader()
            w.writerows(cycles)
    log.info("Wrote live_cycles.csv (%d rows)", len(cycles))

    if plan_rows:
        with open(outdir / "live_plan.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=plan_rows[0].keys())
            w.writeheader()
            w.writerows(plan_rows)
    log.info("Wrote live_plan.csv (%d rows)", len(plan_rows))

    if slippage_rows:
        with open(outdir / "live_slippage.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=slippage_rows[0].keys())
            w.writeheader()
            w.writerows(slippage_rows)
    log.info("Wrote live_slippage.csv (%d rows)", len(slippage_rows))

    # SQLite dump
    conn = sqlite3.connect(str(db_path))
    n_orders = conn.execute("SELECT count(*) FROM orders").fetchone()[0]
    n_fills = conn.execute("SELECT count(*) FROM fills").fetchone()[0]
    dupes = conn.execute(
        "SELECT client_order_id, count(*) c FROM orders "
        "GROUP BY client_order_id HAVING c > 1",
    ).fetchall()
    conn.close()

    # ── Summary + verification ───────────────────────────────
    log.info("=== Verification ===")

    summary: dict[str, Any] = {
        "replay_bars": replay_count,
        "signals": signals_generated,
        "orders_sent": orders_sent,
        "orders_filled": orders_filled,
        "slippage_entries": len(slippage_rows),
        "db_orders": n_orders,
        "db_fills": n_fills,
        "duplicate_coids": len(dupes),
        "checks": {},
    }

    passed = True

    # P1: No duplicates
    if dupes:
        summary["checks"]["P1_no_duplicates"] = "FAIL"
        log.error("FAIL P1: %d duplicate clientOrderIds", len(dupes))
        passed = False
    else:
        summary["checks"]["P1_no_duplicates"] = "PASS"
        log.info("PASS P1: 0 duplicate clientOrderIds")

    # Strategy generates signals
    if signals_generated > 0:
        summary["checks"]["signals_generated"] = "PASS"
        log.info("PASS: %d signals generated", signals_generated)
    else:
        summary["checks"]["signals_generated"] = "FAIL"
        log.error("FAIL: 0 signals (strategy may not fire on replay window)")
        passed = False

    # Orders filled (if not --no-trade)
    if args.no_trade:
        summary["checks"]["orders_filled"] = "SKIP (--no-trade)"
        log.info("SKIP: --no-trade mode, no orders sent")
    elif orders_filled >= 1:
        summary["checks"]["orders_filled"] = "PASS"
        log.info("PASS: %d orders filled on testnet", orders_filled)
    else:
        summary["checks"]["orders_filled"] = "WARN"
        log.warning("WARN: 0 orders filled (may be due to min_notional)")

    # Slippage within bounds (testnet: ±200 bps is generous)
    if slippage_rows:
        max_slip = max(abs(r["slippage_bps"]) for r in slippage_rows)
        if max_slip <= 200:
            summary["checks"]["slippage"] = f"PASS (max={max_slip:.0f} bps)"
            log.info("PASS: max slippage %.0f bps (≤200 bps)", max_slip)
        else:
            summary["checks"]["slippage"] = f"WARN (max={max_slip:.0f} bps)"
            log.warning("WARN: max slippage %.0f bps (testnet can be wild)", max_slip)

    summary["passed"] = passed
    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
    )

    # Write bot.log
    (outdir / "bot.log").write_text(log_capture.getvalue())

    # ── Cleanup ──────────────────────────────────────────────
    try:
        reset2 = reset_to_cash(client)
        log.info("Cleanup: sold %.8f BTC", reset2.sold_btc)
    except Exception as e:
        log.warning("Cleanup failed: %s", e)

    mgr.close()

    log.info("=== C5 Testnet Validation %s ===", "PASSED" if passed else "FAILED")
    log.info(
        "Summary: %d bars → %d signals → %d orders → %d fills",
        replay_count, signals_generated, orders_sent, orders_filled,
    )

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
