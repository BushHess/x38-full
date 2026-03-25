#!/usr/bin/env python3
"""C2+C3 testnet integration smoke test.

Produces deliverables:
  1. out_c3/run_meta.json
  2. out_c3/live_cycles.csv
  3. out_c3/live_slippage.csv
  4. out_c3/sqlite_dump.txt   (orders, fills, kv — 10 rows each)
  5. out_c3/restart_log.txt   (50 lines around reconciliation)
  6. (pytest -q run separately)
"""

from __future__ import annotations

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

# Ensure v10 importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.exchange.rest_client import BinanceSpotClient
from v10.exchange.filters import fetch_symbol_info, round_qty_down, round_price, validate_order
from v10.exchange.account_scope import fetch_account_scope, reset_to_cash
from v10.exchange.order_manager import (
    OrderManager, CrashPoint, CrashSimulation, make_client_order_id,
)

SYMBOL = "BTCUSDT"
OUT = Path("out/c3")
DB_PATH = OUT / "orders.db"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    OUT.mkdir(exist_ok=True)

    # ── Setup logging (capture for restart_log) ───────────────
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)
    root_log.addHandler(handler)
    # Also print to stderr
    root_log.addHandler(logging.StreamHandler(sys.stderr))
    log = logging.getLogger("smoke_c3")

    # ── Init client ───────────────────────────────────────────
    api_key = os.environ["BINANCE_API_KEY"]
    api_secret = os.environ["BINANCE_API_SECRET"]
    client = BinanceSpotClient(api_key=api_key, api_secret=api_secret)

    log.info("=== Phase 0: Reset to cash ===")
    reset = reset_to_cash(client)
    log.info("Cancelled %d orders, sold %.8f BTC", reset.cancelled_count, reset.sold_btc)

    # ── Fetch exchange info ───────────────────────────────────
    info = fetch_symbol_info(client, SYMBOL)
    log.info("SymbolInfo: step=%s tick=%s minQty=%s minNotional=%s",
             info.step_size, info.tick_size, info.min_qty, info.min_notional)

    # ── Config fingerprint ────────────────────────────────────
    config_str = json.dumps({
        "symbol": SYMBOL, "step_size": str(info.step_size),
        "tick_size": str(info.tick_size), "min_notional": str(info.min_notional),
    }, sort_keys=True)
    config_fp = hashlib.sha256(config_str.encode()).hexdigest()[:12]

    # ── 1) run_meta.json ──────────────────────────────────────
    run_meta = {
        "run_id": f"smoke_c3_{int(time.time())}",
        "started_at": _iso_now(),
        "git_hash": "c74c650",
        "config_fingerprint": config_fp,
        "symbol": SYMBOL,
        "env": "testnet",
        "exchange_info": {
            "step_size": str(info.step_size),
            "tick_size": str(info.tick_size),
            "min_qty": str(info.min_qty),
            "min_notional": str(info.min_notional),
        },
    }

    # ── 2) Live cycles + 3) Slippage ─────────────────────────
    cycles: list[dict] = []
    slippage_rows: list[dict] = []

    # Remove old DB for clean run
    if DB_PATH.exists():
        DB_PATH.unlink()

    mgr = OrderManager(client, str(DB_PATH), SYMBOL, poll_interval=0.5, max_polls=20)

    log.info("=== Phase 1: Run 5 cycles (3 with orders) ===")

    for cycle_i in range(5):
        cycle_start = time.time()
        scope = fetch_account_scope(client, SYMBOL)
        bar_ts = int(time.time() * 1000)

        cycle_rec = {
            "cycle": cycle_i,
            "time_iso": _iso_now(),
            "bar_close_ts_ms": bar_ts,
            "btc_price": scope.btc_price,
            "nav_usdt": round(scope.nav_usdt, 2),
            "exposure": round(scope.exposure, 6),
            "btc_free": scope.btc_free,
            "usdt_free": scope.usdt_free,
            "action": "HOLD",
            "client_order_id": "",
            "fill_price": "",
            "fill_qty": "",
            "order_status": "",
        }

        # Place orders on cycles 1, 2 (BUY), 4 (SELL)
        if cycle_i in (1, 2):
            side = "BUY"
            qty_raw = 0.001
            qty = round_qty_down(qty_raw, info)
            reason = f"smoke_buy_{cycle_i}"
            coid = make_client_order_id(SYMBOL, "smoke", bar_ts, side, reason)

            log.info("Cycle %d: placing %s %.5f @ MARKET (coid=%s)", cycle_i, side, qty, coid)
            rec = mgr.submit_order(coid, side, "MARKET", qty, reason=reason)

            fills = mgr.get_fills(coid)
            fill_price = fills[0].price if fills else 0.0
            fill_qty = sum(f.qty for f in fills)

            cycle_rec.update({
                "action": side,
                "client_order_id": coid,
                "fill_price": fill_price,
                "fill_qty": fill_qty,
                "order_status": rec.status,
            })

            # Slippage: compare mid (scope.btc_price) vs fill
            if fills:
                for f in fills:
                    slippage_rows.append({
                        "cycle": cycle_i,
                        "time_iso": _iso_now(),
                        "client_order_id": coid,
                        "side": side,
                        "expected_mid": scope.btc_price,
                        "fill_price": f.price,
                        "slippage_bps": round((f.price / scope.btc_price - 1) * 10000, 2),
                        "qty": f.qty,
                        "commission": f.commission,
                        "commission_asset": f.commission_asset,
                    })

        elif cycle_i == 4:
            # SELL back whatever BTC we have
            scope2 = fetch_account_scope(client, SYMBOL)
            if scope2.btc_free > 0:
                side = "SELL"
                qty = round_qty_down(scope2.btc_free, info)
                reason = "smoke_sell_final"
                coid = make_client_order_id(SYMBOL, "smoke", bar_ts, side, reason)

                if qty >= float(info.min_qty):
                    log.info("Cycle %d: placing %s %.5f @ MARKET (coid=%s)", cycle_i, side, qty, coid)
                    rec = mgr.submit_order(coid, side, "MARKET", qty, reason=reason)
                    fills = mgr.get_fills(coid)
                    fill_price = fills[0].price if fills else 0.0
                    fill_qty = sum(f.qty for f in fills)

                    cycle_rec.update({
                        "action": side,
                        "client_order_id": coid,
                        "fill_price": fill_price,
                        "fill_qty": fill_qty,
                        "order_status": rec.status,
                    })

                    if fills:
                        for f in fills:
                            slippage_rows.append({
                                "cycle": cycle_i,
                                "time_iso": _iso_now(),
                                "client_order_id": coid,
                                "side": side,
                                "expected_mid": scope2.btc_price,
                                "fill_price": f.price,
                                "slippage_bps": round((1 - f.price / scope2.btc_price) * 10000, 2),
                                "qty": f.qty,
                                "commission": f.commission,
                                "commission_asset": f.commission_asset,
                            })

        cycles.append(cycle_rec)
        elapsed = time.time() - cycle_start
        log.info("Cycle %d done in %.2fs | NAV=%.2f exposure=%.4f action=%s",
                 cycle_i, elapsed, scope.nav_usdt, scope.exposure, cycle_rec["action"])
        time.sleep(0.3)

    # ── Phase 2: Crash simulation + restart reconciliation ────
    log.info("=== Phase 2: Crash simulation (AFTER_SEND) ===")
    mgr.close()

    # New manager with crash_point
    mgr_crash = OrderManager(
        client, str(DB_PATH), SYMBOL,
        crash_point=CrashPoint.AFTER_SEND,
        poll_interval=0.5, max_polls=20,
    )

    crash_bar_ts = int(time.time() * 1000)
    crash_coid = make_client_order_id(SYMBOL, "smoke", crash_bar_ts, "BUY", "crash_test")
    crash_qty = round_qty_down(0.001, info)

    try:
        log.info("Submitting crash-test order coid=%s", crash_coid)
        mgr_crash.submit_order(crash_coid, "BUY", "MARKET", crash_qty, reason="crash_test")
    except CrashSimulation:
        log.warning("!!! CrashSimulation raised at AFTER_SEND — simulating process death !!!")

    rec_before = mgr_crash.get_order(crash_coid)
    log.info("Order state before restart: %s (status=%s)", crash_coid, rec_before.status if rec_before else "None")
    mgr_crash.close()

    # Restart: new manager, reconcile
    log.info("=== Phase 3: Restart + Reconcile ===")
    mgr_restart = OrderManager(
        client, str(DB_PATH), SYMBOL,
        poll_interval=0.5, max_polls=20,
    )
    log.info("Running reconcile()...")
    updated = mgr_restart.reconcile()
    log.info("Reconcile updated %d order(s)", len(updated))

    for u in updated:
        log.info("  → %s status=%s exchange_id=%s", u.client_order_id, u.status, u.exchange_order_id)
        fills = mgr_restart.get_fills(u.client_order_id)
        for f in fills:
            log.info("    fill: trade_id=%d price=%.2f qty=%.5f", f.trade_id, f.price, f.qty)

    rec_after = mgr_restart.get_order(crash_coid)
    log.info("Order state after reconcile: %s (status=%s)", crash_coid, rec_after.status if rec_after else "None")

    # Add reconcile cycle to CSV
    scope_final = fetch_account_scope(client, SYMBOL)
    cycles.append({
        "cycle": "reconcile",
        "time_iso": _iso_now(),
        "bar_close_ts_ms": crash_bar_ts,
        "btc_price": scope_final.btc_price,
        "nav_usdt": round(scope_final.nav_usdt, 2),
        "exposure": round(scope_final.exposure, 6),
        "btc_free": scope_final.btc_free,
        "usdt_free": scope_final.usdt_free,
        "action": "RECONCILE",
        "client_order_id": crash_coid,
        "fill_price": "",
        "fill_qty": "",
        "order_status": rec_after.status if rec_after else "",
    })

    # ── Write outputs ─────────────────────────────────────────
    # 1) run_meta.json
    run_meta["finished_at"] = _iso_now()
    run_meta["total_cycles"] = len(cycles)
    (OUT / "run_meta.json").write_text(json.dumps(run_meta, indent=2) + "\n")
    log.info("Wrote run_meta.json")

    # 2) live_cycles.csv
    if cycles:
        with open(OUT / "live_cycles.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cycles[0].keys())
            w.writeheader()
            w.writerows(cycles)
    log.info("Wrote live_cycles.csv (%d rows)", len(cycles))

    # 3) live_slippage.csv
    if slippage_rows:
        with open(OUT / "live_slippage.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=slippage_rows[0].keys())
            w.writeheader()
            w.writerows(slippage_rows)
    log.info("Wrote live_slippage.csv (%d rows)", len(slippage_rows))

    # 4) SQLite dump
    conn = sqlite3.connect(str(DB_PATH))
    dump_lines: list[str] = []
    for table in ("orders", "fills", "kv"):
        dump_lines.append(f"\n=== {table} (first 10 rows) ===")
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        dump_lines.append(" | ".join(cols))
        dump_lines.append("-" * 120)
        for row in conn.execute(f"SELECT * FROM {table} LIMIT 10").fetchall():
            dump_lines.append(" | ".join(str(v) for v in row))
        count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        dump_lines.append(f"(total rows: {count})")
    conn.close()
    (OUT / "sqlite_dump.txt").write_text("\n".join(dump_lines) + "\n")
    log.info("Wrote sqlite_dump.txt")

    # 5) restart_log.txt (capture from StringIO)
    log_text = log_capture.getvalue()
    (OUT / "restart_log.txt").write_text(log_text)
    log.info("Wrote restart_log.txt")

    # Sell remaining BTC to clean up
    reset2 = reset_to_cash(client)
    log.info("Final cleanup: sold %.8f BTC", reset2.sold_btc)
    mgr_restart.close()

    log.info("=== Smoke test complete ===")


if __name__ == "__main__":
    main()
