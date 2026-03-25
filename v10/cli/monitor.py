"""Live monitoring dashboard for E5_ema21D1.

Reads from a running bot's output directory and displays:
  - Account status (NAV, exposure, balances)
  - Regime monitor (NORMAL/AMBER/RED with MDD windows)
  - Risk guard status (kill-switch, daily orders, exposure)
  - Recent orders and fills
  - System health (last bar, uptime, parity)

Usage:
    # Snapshot from bot output directory
    python -m v10.cli.monitor --outdir out/live

    # Watch mode (refresh every 30s)
    python -m v10.cli.monitor --outdir out/live --watch 30

    # With live exchange data + regime from CSV
    python -m v10.cli.monitor --outdir out/live --live --watch 30

    # With alerts on regime changes
    python -m v10.cli.monitor --outdir out/live --live --watch 30 --alerts
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── ANSI helpers ─────────────────────────────────────────────

def _mk_colors(enabled: bool):
    """Return color functions (identity if disabled)."""
    if not enabled:
        identity = lambda t: t  # noqa: E731
        return identity, identity, identity, identity, identity, identity
    def ok(t):   return f"\033[32m{t}\033[0m"
    def warn(t): return f"\033[33m{t}\033[0m"
    def err(t):  return f"\033[31m{t}\033[0m"
    def head(t): return f"\033[1;36m{t}\033[0m"
    def bold(t): return f"\033[1m{t}\033[0m"
    def dim(t):  return f"\033[2m{t}\033[0m"
    return ok, warn, err, head, bold, dim


# ── State ────────────────────────────────────────────────────

@dataclass
class DashboardState:
    timestamp: str = ""

    # Account
    nav_usdt: float | None = None
    btc_qty: float | None = None
    usdt_free: float | None = None
    exposure: float | None = None
    btc_price: float | None = None

    # Regime
    regime: str = "N/A"
    mdd_6m: float | None = None
    mdd_12m: float | None = None

    # Risk
    startup_nav: float | None = None
    kill_switch_dd: float = 0.45
    daily_orders: int = 0
    max_daily_orders: int = 5
    current_dd: float | None = None
    halted: bool = False
    halt_reason: str = ""

    # Orders
    recent_orders: list[dict[str, Any]] = field(default_factory=list)
    total_orders: int = 0
    total_fills: int = 0

    # System
    last_bar_ms: int | None = None
    mode: str = "N/A"
    strategy: str = "N/A"
    started_at: str = "N/A"

    # Parity
    parity_mismatches: int = 0
    parity_total: int = 0

    # Errors
    errors: list[str] = field(default_factory=list)


# ── Time helpers ─────────────────────────────────────────────

def _ago(ms: int) -> str:
    """Format millisecond timestamp as 'Xh Ym ago'."""
    diff_s = (time.time() * 1000 - ms) / 1000
    if diff_s < 0:
        return "future"
    if diff_s < 60:
        return f"{int(diff_s)}s ago"
    if diff_s < 3600:
        return f"{int(diff_s / 60)}m ago"
    if diff_s < 86400:
        h = int(diff_s / 3600)
        m = int((diff_s % 3600) / 60)
        return f"{h}h {m}m ago"
    return f"{int(diff_s / 86400)}d ago"


def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(
        ms / 1000, tz=timezone.utc,
    ).strftime("%Y-%m-%d %H:%M UTC")


# ── Data collection ──────────────────────────────────────────

def collect_state(
    outdir: Path,
    client: Any | None = None,
    data_path: str | None = None,
) -> DashboardState:
    """Gather dashboard state from all available sources."""
    state = DashboardState(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    # ── run_meta.json ─────────────────────────────────────
    meta_path = outdir / "run_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            state.mode = meta.get("mode", meta.get("env", "N/A"))
            state.strategy = meta.get(
                "strategy",
                meta.get("config", {}).get("strategy", "N/A"),
            )
            state.started_at = meta.get("started_at", "N/A")
            config = meta.get("config", {})
            if isinstance(config, dict) and "risk" in config:
                state.kill_switch_dd = config["risk"].get(
                    "kill_switch_dd_total", 0.45,
                )
                state.max_daily_orders = config["risk"].get(
                    "max_daily_orders", 5,
                )
        except Exception as e:
            state.errors.append(f"run_meta: {e}")

    # ── SQLite DB ─────────────────────────────────────────
    for db_name in ("bot.sqlite3", "orders.db"):
        db_path = outdir / db_name
        if not db_path.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row

            # Totals
            state.total_orders = conn.execute(
                "SELECT count(*) FROM orders",
            ).fetchone()[0]
            state.total_fills = conn.execute(
                "SELECT count(*) FROM fills",
            ).fetchone()[0]

            # Recent orders (last 10)
            rows = conn.execute(
                "SELECT client_order_id, side, quantity, price, status, "
                "reason, created_at_ms "
                "FROM orders ORDER BY created_at_ms DESC LIMIT 10",
            ).fetchall()
            for r in rows:
                fill = conn.execute(
                    "SELECT price, qty FROM fills "
                    "WHERE client_order_id = ? LIMIT 1",
                    (r["client_order_id"],),
                ).fetchone()
                state.recent_orders.append({
                    "time": _ms_to_iso(r["created_at_ms"]),
                    "side": r["side"],
                    "qty": r["quantity"],
                    "price": fill["price"] if fill else r["price"],
                    "status": r["status"],
                    "reason": r["reason"] or "",
                })

            # Daily orders (since UTC midnight)
            now = datetime.now(timezone.utc)
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            midnight_ms = int(midnight.timestamp() * 1000)
            state.daily_orders = conn.execute(
                "SELECT count(*) FROM orders WHERE created_at_ms >= ?",
                (midnight_ms,),
            ).fetchone()[0]

            # Last bar time from kv
            kv_row = conn.execute(
                "SELECT value FROM kv "
                "WHERE key = 'last_processed_signal_close_ms'",
            ).fetchone()
            if kv_row:
                state.last_bar_ms = int(kv_row[0])

            conn.close()
        except Exception as e:
            state.errors.append(f"{db_name}: {e}")
        break  # use first DB found

    # ── Parity CSV ────────────────────────────────────────
    parity_path = outdir / "live_parity.csv"
    if parity_path.exists():
        try:
            import csv
            with open(parity_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    state.parity_total += 1
                    if row.get("passed") in ("0", "False", "false"):
                        state.parity_mismatches += 1
        except Exception as e:
            state.errors.append(f"parity: {e}")

    # ── Live exchange data ────────────────────────────────
    if client is not None:
        try:
            from v10.exchange.account_scope import fetch_account_scope
            scope = fetch_account_scope(client, "BTCUSDT")
            state.nav_usdt = scope.nav_usdt
            state.btc_qty = scope.btc_free
            state.usdt_free = scope.usdt_free
            state.exposure = scope.exposure
            state.btc_price = scope.btc_price

            if state.startup_nav and state.startup_nav > 0:
                state.current_dd = 1.0 - (scope.nav_usdt / state.startup_nav)
        except Exception as e:
            state.errors.append(f"exchange: {e}")

    # ── Regime from D1 data ───────────────────────────────
    _compute_regime(state, client, data_path)

    return state


def _compute_regime(
    state: DashboardState,
    client: Any | None,
    data_path: str | None,
) -> None:
    """Compute regime status from D1 close prices."""
    try:
        import numpy as np
        from monitoring.regime_monitor import compute_regime, ALERT_NAMES
    except ImportError:
        return

    d1_close = None

    # Try CSV first
    if data_path:
        try:
            from v10.exchange.marketdata import CsvBarSource
            source = CsvBarSource(data_path)
            d1_bars = source.fetch_d1("BTCUSDT")
            if d1_bars:
                d1_close = np.array([b.close for b in d1_bars])
        except Exception as e:
            state.errors.append(f"regime(csv): {e}")

    # Fallback: exchange D1 klines
    if d1_close is None and client is not None:
        try:
            klines = client.klines("BTCUSDT", "1d", limit=400)
            if klines:
                d1_close = np.array([float(k[4]) for k in klines])
        except Exception as e:
            state.errors.append(f"regime(live): {e}")

    if d1_close is not None and len(d1_close) > 180:
        regime = compute_regime(d1_close)
        alerts = regime["alerts"]
        last_alert = int(alerts[-1])
        state.regime = ALERT_NAMES[last_alert]
        state.mdd_6m = float(regime["mdd_6m"][-1])
        state.mdd_12m = float(regime["mdd_12m"][-1])


# ── Rendering ────────────────────────────────────────────────

def render(state: DashboardState, *, no_color: bool = False) -> str:
    """Render dashboard state to terminal string."""
    ok, warn, err, head, bold, dim = _mk_colors(not no_color)

    W = 62
    lines: list[str] = []

    def sep():
        lines.append(dim("=" * W))

    def subsep():
        lines.append(dim("  " + "-" * (W - 4)))

    def section(title: str, badge: str = ""):
        lines.append("")
        badge_str = f"  [{badge}]" if badge else ""
        lines.append(f"  {head(title)}{badge_str}")
        subsep()

    # ── Header ────────────────────────────────────────────
    sep()
    lines.append(f"  {bold('E5_ema21D1 — LIVE MONITOR')}")
    lines.append(f"  {dim(state.timestamp)}")
    sep()

    # ── Account ───────────────────────────────────────────
    if state.nav_usdt is not None:
        section("ACCOUNT")
        lines.append(f"  {'NAV':16s} ${state.nav_usdt:>14,.2f}")
        if state.btc_qty is not None:
            btc_val = state.btc_qty * (state.btc_price or 0)
            lines.append(
                f"  {'BTC':16s} {state.btc_qty:>14.8f}  "
                f"(${btc_val:,.2f})"
            )
        if state.usdt_free is not None:
            lines.append(f"  {'USDT':16s} ${state.usdt_free:>14,.2f}")
        if state.exposure is not None:
            lines.append(f"  {'Exposure':16s} {state.exposure:>14.2%}")
        if state.btc_price is not None:
            lines.append(f"  {'BTC Price':16s} ${state.btc_price:>14,.2f}")

    # ── Regime ────────────────────────────────────────────
    regime_badge = state.regime
    if state.regime == "NORMAL":
        regime_badge = ok("NORMAL")
    elif state.regime == "AMBER":
        regime_badge = warn("AMBER")
    elif state.regime == "RED":
        regime_badge = err("RED")

    section("REGIME", regime_badge)
    if state.mdd_6m is not None:
        lines.append(
            f"  {'MDD 6m':16s} {state.mdd_6m:>14.1%}  "
            f"{dim('(AMBER >45% | RED >55%)')}"
        )
    else:
        lines.append(f"  {'MDD 6m':16s} {'N/A':>15s}")
    if state.mdd_12m is not None:
        lines.append(
            f"  {'MDD 12m':16s} {state.mdd_12m:>14.1%}  "
            f"{dim('(AMBER >60% | RED >70%)')}"
        )
    else:
        lines.append(f"  {'MDD 12m':16s} {'N/A':>15s}")

    # ── Risk Guards ───────────────────────────────────────
    guard_badge = err("HALTED") if state.halted else ok("ACTIVE")
    section("RISK GUARDS", guard_badge)

    # Kill-switch DD
    if state.current_dd is not None:
        dd_str = f"{state.current_dd:.1%} / {state.kill_switch_dd:.0%}"
        dd_ok = state.current_dd < state.kill_switch_dd
        dd_tag = ok("[OK]") if dd_ok else err("[HALT]")
    else:
        dd_str = f"N/A / {state.kill_switch_dd:.0%}"
        dd_tag = dim("[N/A]")
    lines.append(f"  {'Kill-switch DD':16s} {dd_str:>15s}  {dd_tag}")

    # Daily orders
    daily_str = f"{state.daily_orders} / {state.max_daily_orders}"
    daily_ok = state.daily_orders < state.max_daily_orders
    daily_tag = ok("[OK]") if daily_ok else warn("[LIMIT]")
    lines.append(f"  {'Daily orders':16s} {daily_str:>15s}  {daily_tag}")

    if state.halt_reason:
        lines.append(f"  {err('Halt reason: ' + state.halt_reason)}")

    # ── Recent Orders ─────────────────────────────────────
    section("RECENT ORDERS", f"last {len(state.recent_orders)}")
    if state.recent_orders:
        for o in state.recent_orders:
            side = o["side"]
            if side == "BUY":
                side_str = ok("BUY ")
            elif side == "SELL":
                side_str = err("SELL")
            else:
                side_str = side.ljust(4)

            price = o.get("price")
            price_str = f"${price:>10,.2f}" if price else "    MARKET"

            status = o["status"]
            if status == "FILLED":
                status_str = ok(status)
            elif status in ("CANCELED", "REJECTED", "EXPIRED"):
                status_str = err(status)
            else:
                status_str = warn(status)

            reason = o.get("reason", "")[:20]

            lines.append(
                f"  {o['time']}  {side_str}  {o['qty']:>10.5f}  "
                f"{price_str}  {status_str:>8s}  {dim(reason)}"
            )
    else:
        lines.append(f"  {dim('No orders yet')}")

    # ── Performance ───────────────────────────────────────
    section("PERFORMANCE")
    lines.append(f"  {'Total orders':16s} {state.total_orders:>15d}")
    lines.append(f"  {'Total fills':16s} {state.total_fills:>15d}")
    if state.total_orders > 0:
        fill_rate = state.total_fills / state.total_orders * 100
        lines.append(f"  {'Fill rate':16s} {fill_rate:>14.1f}%")

    # ── System ────────────────────────────────────────────
    section("SYSTEM")
    lines.append(f"  {'Strategy':16s} {state.strategy}")
    lines.append(f"  {'Mode':16s} {state.mode}")

    if state.last_bar_ms:
        bar_str = f"{_ms_to_iso(state.last_bar_ms)}  ({_ago(state.last_bar_ms)})"
        lines.append(f"  {'Last bar':16s} {bar_str}")
    else:
        lines.append(f"  {'Last bar':16s} N/A")

    lines.append(f"  {'Started':16s} {state.started_at}")

    # Parity
    if state.parity_total > 0:
        p_ok = state.parity_mismatches == 0
        p_str = (
            f"OK ({state.parity_total} checks)" if p_ok
            else f"MISMATCH ({state.parity_mismatches}/{state.parity_total})"
        )
        p_tag = ok(p_str) if p_ok else err(p_str)
        lines.append(f"  {'Parity':16s} {p_tag}")

    # ── Warnings ──────────────────────────────────────────
    if state.errors:
        section("WARNINGS")
        for e in state.errors:
            lines.append(f"  {warn(e)}")

    sep()
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="E5_ema21D1 — Live Monitoring Dashboard",
    )
    parser.add_argument(
        "--outdir", default="out/live",
        help="Bot output directory (default: out/live)",
    )
    parser.add_argument(
        "--watch", type=int, default=0, metavar="SECONDS",
        help="Refresh interval in seconds (0 = single snapshot)",
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Poll Binance exchange for live account data",
    )
    parser.add_argument(
        "--data", default=None,
        help="Path to CSV for D1 regime computation",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI colors",
    )
    parser.add_argument(
        "--alerts", action="store_true",
        help="Enable alerts (requires TELEGRAM_BOT_TOKEN/CHAT_ID "
             "or ALERT_WEBHOOK_URL)",
    )
    args = parser.parse_args(argv)

    outdir = Path(args.outdir)

    # Init exchange client if --live
    client = None
    if args.live:
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        if api_key and api_secret:
            from v10.exchange.rest_client import BinanceSpotClient
            client = BinanceSpotClient(
                api_key=api_key, api_secret=api_secret,
            )
        else:
            print(
                "WARN: --live requires BINANCE_API_KEY/SECRET env vars",
                file=sys.stderr,
            )

    # Init alerts
    alerts = None
    prev_regime: str | None = None
    if args.alerts:
        from monitoring.alerts import AlertDispatcher
        alerts = AlertDispatcher()

    # Auto-detect data path
    data_path = args.data
    if not data_path:
        default_csv = Path("data/bars_btcusdt_2016_now_h1_4h_1d.csv")
        if default_csv.exists():
            data_path = str(default_csv)

    try:
        while True:
            state = collect_state(outdir, client=client, data_path=data_path)

            # Clear screen in watch mode
            if args.watch:
                print("\033[2J\033[H", end="")

            print(render(state, no_color=args.no_color))

            # Alert on regime change
            if alerts and state.regime != "N/A":
                if prev_regime and state.regime != prev_regime:
                    alerts.regime_change(
                        prev_regime, state.regime,
                        state.mdd_6m or 0.0, state.mdd_12m or 0.0,
                    )
                prev_regime = state.regime

            if not args.watch:
                break

            time.sleep(args.watch)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


if __name__ == "__main__":
    main()
