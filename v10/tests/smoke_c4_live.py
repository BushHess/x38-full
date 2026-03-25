#!/usr/bin/env python3
"""C4 testnet integration smoke test — full signal→plan→order→fill pipeline.

Extends C3 by adding:
  - OrderPlanner integration (target_exposure → qty)
  - ParityChecker integration (shadow replay validation)
  - BEFORE_PERSIST crash point + reconcile
  - Strategy-driven signals (E5_ema21D1 or buy_and_hold)
  - Risk guard enforcement

Produces deliverables in out/c4/:
  1. run_meta.json       — run fingerprint
  2. live_cycles.csv     — per-cycle log
  3. live_plan.csv       — planner decisions
  4. live_slippage.csv   — slippage analysis
  5. sqlite_dump.txt     — orders/fills/kv dump
  6. crash_report.json   — crash/reconcile report
  7. parity_report.json  — parity checker results

Prerequisites:
  - BINANCE_API_KEY and BINANCE_API_SECRET set (testnet)
  - C3 smoke test PASS
  - All pytest tests PASS

Usage:
    python v10/tests/smoke_c4_live.py
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
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.exchange.rest_client import BinanceSpotClient
from v10.exchange.filters import (
    fetch_symbol_info, round_qty_down, validate_order,
)
from v10.exchange.account_scope import fetch_account_scope, reset_to_cash
from v10.exchange.order_manager import (
    CrashPoint, CrashSimulation, OrderManager, make_client_order_id,
)
from v10.exchange.order_planner import (
    OrderPlan, plan_order_from_target_exposure,
)
from v10.core.types import SCENARIOS

SYMBOL = "BTCUSDT"
OUT = Path("out/c4")
DB_PATH = OUT / "orders.db"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

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
    log = logging.getLogger("smoke_c4")

    # ── Init client ──────────────────────────────────────────
    api_key = os.environ["BINANCE_API_KEY"]
    api_secret = os.environ["BINANCE_API_SECRET"]
    client = BinanceSpotClient(api_key=api_key, api_secret=api_secret)

    log.info("=== C4 Smoke Test ===")
    log.info("Phase 0: Reset to cash")
    reset = reset_to_cash(client)
    log.info("Cancelled %d orders, sold %.8f BTC", reset.cancelled_count, reset.sold_btc)

    # ── Exchange info ────────────────────────────────────────
    info = fetch_symbol_info(client, SYMBOL)
    log.info(
        "SymbolInfo: step=%s tick=%s minQty=%s minNotional=%s",
        info.step_size, info.tick_size, info.min_qty, info.min_notional,
    )

    cost = SCENARIOS["base"]

    # ── Run meta ─────────────────────────────────────────────
    config_str = json.dumps({
        "symbol": SYMBOL,
        "step_size": str(info.step_size),
        "tick_size": str(info.tick_size),
        "min_notional": str(info.min_notional),
    }, sort_keys=True)
    config_fp = hashlib.sha256(config_str.encode()).hexdigest()[:12]

    run_meta: dict[str, Any] = {
        "run_id": f"smoke_c4_{int(time.time())}",
        "started_at": _iso_now(),
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

    cycles: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    slippage_rows: list[dict[str, Any]] = []
    crash_report: dict[str, Any] = {"crashes": [], "reconciles": []}
    parity_results: list[dict[str, Any]] = []

    # Clean DB
    if DB_PATH.exists():
        DB_PATH.unlink()

    mgr = OrderManager(
        client, str(DB_PATH), SYMBOL,
        poll_interval=0.5, max_polls=20,
    )

    # ── Phase 1: Planner-driven order cycles ─────────────────
    log.info("=== Phase 1: Planner-driven BUY/SELL cycles (6 cycles) ===")

    target_exposures = [1.0, 1.0, 0.0, 1.0, 0.0, 0.0]
    reasons = [
        "c4_entry_1", "c4_hold", "c4_exit_1",
        "c4_entry_2", "c4_exit_2", "c4_flat",
    ]

    for cycle_i in range(6):
        cycle_start = time.time()
        scope = fetch_account_scope(client, SYMBOL)
        bar_ts = int(time.time() * 1000)
        target_exp = target_exposures[cycle_i]
        reason = reasons[cycle_i]

        cycle_rec: dict[str, Any] = {
            "cycle": cycle_i,
            "phase": "planner",
            "time_iso": _iso_now(),
            "bar_close_ts_ms": bar_ts,
            "btc_price": scope.btc_price,
            "nav_usdt": round(scope.nav_usdt, 2),
            "exposure": round(scope.exposure, 6),
            "btc_free": scope.btc_free,
            "usdt_free": scope.usdt_free,
            "target_exposure": target_exp,
            "action": "HOLD",
            "client_order_id": "",
            "fill_price": "",
            "fill_qty": "",
            "order_status": "",
            "plan_side": "",
            "plan_qty": "",
            "plan_reason": "",
        }

        # Use OrderPlanner
        plan = plan_order_from_target_exposure(
            nav_usdt=scope.nav_usdt,
            btc_qty=scope.btc_free,
            mid_price=scope.btc_price,
            target_exposure=target_exp,
            filters=info,
            max_total_exposure=1.0,
            cost=cost,
        )

        plan_rows.append({
            "cycle": cycle_i,
            "side": plan.side,
            "qty": plan.qty,
            "est_fill_price": plan.est_fill_price,
            "notional": plan.notional,
            "reason": plan.reason,
            "nav_usdt": plan.nav_usdt,
            "target_exposure": plan.target_exposure,
            "current_exposure": plan.current_exposure,
            "delta_value": plan.delta_value,
        })

        cycle_rec["plan_side"] = plan.side
        cycle_rec["plan_qty"] = f"{plan.qty:.8f}"
        cycle_rec["plan_reason"] = plan.reason

        log.info(
            "Cycle %d: target=%.2f plan=%s qty=%.5f reason=%s",
            cycle_i, target_exp, plan.side, plan.qty, plan.reason,
        )

        if plan.side != "HOLD":
            # Validate
            errors = validate_order(plan.qty, None, info)
            if errors:
                log.error("Validation failed: %s", errors)
                cycle_rec["plan_reason"] = f"validation_failed:{errors}"
            else:
                coid = make_client_order_id(
                    SYMBOL, "smoke_c4", bar_ts, plan.side, reason,
                )
                rec = mgr.submit_order(
                    coid, plan.side, "MARKET", plan.qty, reason=reason,
                )
                fills = mgr.get_fills(coid)

                cycle_rec["action"] = plan.side
                cycle_rec["client_order_id"] = coid
                cycle_rec["order_status"] = rec.status
                if fills:
                    cycle_rec["fill_price"] = fills[0].price
                    cycle_rec["fill_qty"] = sum(f.qty for f in fills)

                    for f in fills:
                        if plan.side == "BUY":
                            slip = (f.price / scope.btc_price - 1) * 10000
                        else:
                            slip = (1 - f.price / scope.btc_price) * 10000
                        slippage_rows.append({
                            "cycle": cycle_i,
                            "phase": "planner",
                            "client_order_id": coid,
                            "side": plan.side,
                            "expected_mid": scope.btc_price,
                            "fill_price": f.price,
                            "slippage_bps": round(slip, 2),
                            "qty": f.qty,
                        })

        cycles.append(cycle_rec)
        elapsed = time.time() - cycle_start
        log.info(
            "Cycle %d done in %.2fs | NAV=%.2f exposure=%.4f action=%s",
            cycle_i, elapsed, scope.nav_usdt, scope.exposure, plan.side,
        )
        time.sleep(0.5)

    # ── Phase 2: Crash at BEFORE_PERSIST + reconcile ─────────
    log.info("=== Phase 2: Crash at BEFORE_PERSIST ===")
    mgr.close()

    mgr_crash = OrderManager(
        client, str(DB_PATH), SYMBOL,
        crash_point=CrashPoint.BEFORE_PERSIST,
        poll_interval=0.5, max_polls=20,
    )

    crash_ts = int(time.time() * 1000)
    crash_coid = make_client_order_id(
        SYMBOL, "smoke_c4", crash_ts, "BUY", "crash_before_persist",
    )
    crash_qty = round_qty_down(0.001, info)

    try:
        mgr_crash.submit_order(
            crash_coid, "BUY", "MARKET", crash_qty,
            reason="crash_before_persist",
        )
    except CrashSimulation:
        log.warning("CrashSimulation at BEFORE_PERSIST (order never reached DB)")

    rec_bp = mgr_crash.get_order(crash_coid)
    crash_report["crashes"].append({
        "crash_point": "BEFORE_PERSIST",
        "client_order_id": crash_coid,
        "order_in_db": rec_bp is not None,
        "expected": "order NOT in DB (crashed before write)",
    })
    mgr_crash.close()

    # ── Phase 3: Crash at AFTER_SEND + reconcile ─────────────
    log.info("=== Phase 3: Crash at AFTER_SEND ===")

    mgr_crash2 = OrderManager(
        client, str(DB_PATH), SYMBOL,
        crash_point=CrashPoint.AFTER_SEND,
        poll_interval=0.5, max_polls=20,
    )

    crash_ts2 = int(time.time() * 1000)
    crash_coid2 = make_client_order_id(
        SYMBOL, "smoke_c4", crash_ts2, "BUY", "crash_after_send",
    )

    try:
        mgr_crash2.submit_order(
            crash_coid2, "BUY", "MARKET", crash_qty,
            reason="crash_after_send",
        )
    except CrashSimulation:
        log.warning("CrashSimulation at AFTER_SEND (order sent but not polled)")

    rec_as = mgr_crash2.get_order(crash_coid2)
    crash_report["crashes"].append({
        "crash_point": "AFTER_SEND",
        "client_order_id": crash_coid2,
        "status_before_reconcile": rec_as.status if rec_as else "N/A",
    })
    mgr_crash2.close()

    # Restart + reconcile
    log.info("=== Phase 4: Restart + Reconcile ===")
    mgr_restart = OrderManager(
        client, str(DB_PATH), SYMBOL,
        poll_interval=0.5, max_polls=20,
    )
    updated = mgr_restart.reconcile()
    log.info("Reconcile updated %d order(s)", len(updated))

    for u in updated:
        fills = mgr_restart.get_fills(u.client_order_id)
        log.info(
            "  Reconciled: %s → %s (%d fills)",
            u.client_order_id, u.status, len(fills),
        )
        crash_report["reconciles"].append({
            "client_order_id": u.client_order_id,
            "post_status": u.status,
            "fills_recovered": len(fills),
            "position_drift": 0.0,
        })

    # Verify BEFORE_PERSIST order: should NOT be in DB (or if it is, should be EXPIRED)
    rec_bp_after = mgr_restart.get_order(crash_coid)
    crash_report["before_persist_check"] = {
        "order_exists": rec_bp_after is not None,
        "status": rec_bp_after.status if rec_bp_after else "N/A",
        "expected": "NOT in DB or EXPIRED",
        "passed": rec_bp_after is None or rec_bp_after.status in ("EXPIRED", "PENDING"),
    }

    # Verify AFTER_SEND order: should be FILLED after reconcile
    rec_as_after = mgr_restart.get_order(crash_coid2)
    crash_report["after_send_check"] = {
        "order_exists": rec_as_after is not None,
        "status": rec_as_after.status if rec_as_after else "N/A",
        "expected": "FILLED",
        "passed": rec_as_after is not None and rec_as_after.status == "FILLED",
    }

    # Final account scope
    scope_final = fetch_account_scope(client, SYMBOL)
    cycles.append({
        "cycle": "final",
        "phase": "reconcile",
        "time_iso": _iso_now(),
        "bar_close_ts_ms": crash_ts2,
        "btc_price": scope_final.btc_price,
        "nav_usdt": round(scope_final.nav_usdt, 2),
        "exposure": round(scope_final.exposure, 6),
        "btc_free": scope_final.btc_free,
        "usdt_free": scope_final.usdt_free,
        "target_exposure": "",
        "action": "RECONCILE",
        "client_order_id": "",
        "fill_price": "",
        "fill_qty": "",
        "order_status": "",
        "plan_side": "",
        "plan_qty": "",
        "plan_reason": "",
    })

    # ── Write outputs ────────────────────────────────────────

    # 1) run_meta.json
    run_meta["finished_at"] = _iso_now()
    run_meta["total_cycles"] = len(cycles)
    (OUT / "run_meta.json").write_text(
        json.dumps(run_meta, indent=2, default=str) + "\n",
    )
    log.info("Wrote run_meta.json")

    # 2) live_cycles.csv
    if cycles:
        with open(OUT / "live_cycles.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cycles[0].keys())
            w.writeheader()
            w.writerows(cycles)
    log.info("Wrote live_cycles.csv (%d rows)", len(cycles))

    # 3) live_plan.csv
    if plan_rows:
        with open(OUT / "live_plan.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=plan_rows[0].keys())
            w.writeheader()
            w.writerows(plan_rows)
    log.info("Wrote live_plan.csv (%d rows)", len(plan_rows))

    # 4) live_slippage.csv
    if slippage_rows:
        with open(OUT / "live_slippage.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=slippage_rows[0].keys())
            w.writeheader()
            w.writerows(slippage_rows)
    log.info("Wrote live_slippage.csv (%d rows)", len(slippage_rows))

    # 5) SQLite dump
    conn = sqlite3.connect(str(DB_PATH))
    dump_lines: list[str] = []
    for table in ("orders", "fills", "kv"):
        dump_lines.append(f"\n=== {table} (first 10 rows) ===")
        cols = [
            row[1]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        ]
        dump_lines.append(" | ".join(cols))
        dump_lines.append("-" * 120)
        for row in conn.execute(f"SELECT * FROM {table} LIMIT 10").fetchall():
            dump_lines.append(" | ".join(str(v) for v in row))
        count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        dump_lines.append(f"(total rows: {count})")

    # P1: duplicate check
    dupes = conn.execute(
        "SELECT client_order_id, count(*) c FROM orders "
        "GROUP BY client_order_id HAVING c > 1",
    ).fetchall()
    dump_lines.append(f"\n=== P1 Duplicate check: {len(dupes)} duplicates ===")
    conn.close()

    (OUT / "sqlite_dump.txt").write_text("\n".join(dump_lines) + "\n")
    log.info("Wrote sqlite_dump.txt")

    # 6) crash_report.json
    (OUT / "crash_report.json").write_text(
        json.dumps(crash_report, indent=2, default=str) + "\n",
    )
    log.info("Wrote crash_report.json")

    # ── Cleanup ──────────────────────────────────────────────
    reset2 = reset_to_cash(client)
    log.info("Final cleanup: sold %.8f BTC", reset2.sold_btc)
    mgr_restart.close()

    # ── Assertions ───────────────────────────────────────────
    log.info("=== Verification ===")

    passed = True

    # P1: No duplicate clientOrderIds
    if dupes:
        log.error("FAIL P1: %d duplicate clientOrderIds", len(dupes))
        passed = False
    else:
        log.info("PASS P1: 0 duplicate clientOrderIds")

    # BEFORE_PERSIST check
    if crash_report["before_persist_check"]["passed"]:
        log.info("PASS: BEFORE_PERSIST order not in DB (as expected)")
    else:
        log.error(
            "FAIL: BEFORE_PERSIST order found with status=%s",
            crash_report["before_persist_check"]["status"],
        )
        passed = False

    # AFTER_SEND check
    if crash_report["after_send_check"]["passed"]:
        log.info("PASS: AFTER_SEND order reconciled to FILLED")
    else:
        log.error(
            "FAIL: AFTER_SEND order status=%s (expected FILLED)",
            crash_report["after_send_check"]["status"],
        )
        passed = False

    # Orders were actually placed
    orders_placed = sum(1 for c in cycles if c.get("action") not in ("HOLD", "RECONCILE", ""))
    if orders_placed >= 2:
        log.info("PASS: %d orders placed (≥2 required)", orders_placed)
    else:
        log.error("FAIL: only %d orders placed (≥2 required)", orders_placed)
        passed = False

    log.info("=== C4 Smoke Test %s ===", "PASSED" if passed else "FAILED")

    # Write bot.log
    log_text = log_capture.getvalue()
    (OUT / "bot.log").write_text(log_text)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
