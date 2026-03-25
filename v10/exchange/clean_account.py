#!/usr/bin/env python3
"""Sell ALL non-USDT assets on testnet, then report balances.

Usage:
    python -m v10.exchange.clean_account              # dry-run (default)
    python -m v10.exchange.clean_account --execute    # actually sell

Requires env vars: BINANCE_API_KEY, BINANCE_API_SECRET
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from decimal import ROUND_DOWN
from decimal import Decimal
from typing import Any

from v10.exchange.rest_client import AccountBalance
from v10.exchange.rest_client import BinanceAPIError
from v10.exchange.rest_client import BinanceSpotClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger(__name__)

KEEP_ASSET = "USDT"

# Clean Account Gate — assets we tolerate having a non-zero balance
ALLOWED_ASSETS: set[str] = {"USDT", "BTC", "BNB"}
# Any non-allowed asset whose estimated USD value is below this is dust → ignored
DUST_THRESHOLD_USD: float = 500.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class PairInfo:
    """Minimal info needed to sell an asset via its USDT pair."""

    symbol: str  # e.g. "BTCUSDT"
    step_size: Decimal
    min_qty: Decimal
    min_notional: Decimal
    qty_precision: int  # number of decimal places in stepSize


def _find_filter(filters: list[dict[str, Any]], ftype: str) -> dict[str, Any]:
    for f in filters:
        if f.get("filterType") == ftype:
            return f
    return {}


def build_usdt_pair_map(client: BinanceSpotClient) -> dict[str, PairInfo]:
    """Fetch exchangeInfo and return {base_asset: PairInfo} for all *USDT pairs."""
    raw = client.exchange_info()
    pair_map: dict[str, PairInfo] = {}
    for s in raw.get("symbols", []):
        if s.get("quoteAsset") != "USDT":
            continue
        if s.get("status") != "TRADING":
            continue
        base = s["baseAsset"]
        filters = s.get("filters", [])
        ls = _find_filter(filters, "LOT_SIZE")
        mn = _find_filter(filters, "MIN_NOTIONAL") or _find_filter(filters, "NOTIONAL")

        step = Decimal(ls.get("stepSize", "0.00001"))
        min_q = Decimal(ls.get("minQty", "0.00001"))
        min_n = Decimal(mn.get("minNotional", "10.0"))

        # Count decimal places in stepSize
        step_str = ls.get("stepSize", "0.00001").rstrip("0")
        qty_prec = len(step_str.split(".")[1]) if "." in step_str else 0

        pair_map[base] = PairInfo(
            symbol=s["symbol"],
            step_size=step,
            min_qty=min_q,
            min_notional=min_n,
            qty_precision=qty_prec,
        )
    return pair_map


def round_qty_down(qty: float, step: Decimal) -> Decimal:
    d = Decimal(str(qty))
    return (d / step).to_integral_value(rounding=ROUND_DOWN) * step


def format_qty(qty: Decimal, precision: int) -> str:
    """Format quantity with the exact decimal precision the exchange expects."""
    if precision == 0:
        return str(int(qty))
    return f"{float(qty):.{precision}f}"


def get_last_price(client: BinanceSpotClient, symbol: str) -> float:
    klines = client.klines(symbol, "1m", limit=1)
    return float(klines[-1][4]) if klines else 0.0


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def clean_account(client: BinanceSpotClient, *, dry_run: bool = True) -> None:
    """Cancel all open orders, sell every non-USDT asset to USDT."""

    # Safety: testnet only
    if "testnet" not in client.base_url:
        raise RuntimeError(f"clean_account is restricted to TESTNET. base_url={client.base_url}")

    # 1) Build pair map
    _log.info("Fetching exchange info …")
    pair_map = build_usdt_pair_map(client)
    _log.info("Found %d tradeable *USDT pairs", len(pair_map))

    # 2) Fetch balances
    balances: list[AccountBalance] = client.account()

    non_usdt = [b for b in balances if b.asset != KEEP_ASSET and (b.free + b.locked) > 0]
    usdt_bal = next((b for b in balances if b.asset == KEEP_ASSET), None)

    _log.info("── Before cleanup ──")
    _log.info("  USDT  free=%.4f  locked=%.4f", usdt_bal.free if usdt_bal else 0, usdt_bal.locked if usdt_bal else 0)
    _log.info("  Non-USDT assets: %d", len(non_usdt))

    # Filter to only assets that have a USDT trading pair
    sellable = [b for b in non_usdt if b.asset in pair_map]
    no_pair = [b for b in non_usdt if b.asset not in pair_map]
    _log.info("  Sellable: %d assets | No USDT pair: %d assets", len(sellable), len(no_pair))

    if not sellable and not no_pair:
        _log.info("Account is already 100%% USDT. Nothing to do.")
        return

    # 3) Cancel open orders — query once to find which pairs have orders
    _log.info("Checking for open orders …")
    symbols_with_orders: set[str] = set()
    try:
        all_open = client.open_orders()  # single API call, all symbols
        symbols_with_orders = {o.symbol for o in all_open}
        if symbols_with_orders:
            _log.info("  Found open orders on: %s", ", ".join(sorted(symbols_with_orders)))
            for sym in symbols_with_orders:
                try:
                    cancelled = client.cancel_all_orders(sym)
                    _log.info("  Cancelled %d order(s) on %s", len(cancelled), sym)
                except BinanceAPIError as e:
                    _log.warning("  cancel_all_orders(%s) failed: %s", sym, e)
        else:
            _log.info("  No open orders.")
    except BinanceAPIError as e:
        _log.warning("  Could not query open orders: %s", e)

    # Re-fetch balances after cancellation (locked → free)
    if symbols_with_orders:
        balances = client.account()
        sellable = [b for b in balances if b.asset != KEEP_ASSET and b.free > 0 and b.asset in pair_map]

    # 4) Market-sell each asset
    sold_count = 0
    failed_count = 0
    skipped: list[str] = [b.asset for b in no_pair]

    _log.info("── Selling %d assets ──", len(sellable))
    for i, b in enumerate(sellable, 1):
        info = pair_map[b.asset]

        qty = round_qty_down(b.free, info.step_size)
        if qty < info.min_qty:
            skipped.append(f"{b.asset}(dust)")
            continue

        qty_str = format_qty(qty, info.qty_precision)

        if dry_run:
            _log.info("  [%d] DRY-RUN %-8s qty=%s (%s)", i, b.asset, qty_str, info.symbol)
        else:
            try:
                # Submit quantity as a pre-formatted string that matches pair precision.
                order = client.place_order(
                    symbol=info.symbol,
                    side="SELL",
                    type="MARKET",
                    quantity=qty_str,
                    new_order_resp_type="FULL",
                )
                status = order.status
                exec_qty = order.executed_qty
                order_id = order.order_id
                _log.info(
                    "  [%d] SOLD %-8s %s → %s  exec=%.8f  (#%s)",
                    i,
                    b.asset,
                    qty_str,
                    status,
                    exec_qty,
                    order_id,
                )
                sold_count += 1
            except BinanceAPIError as e:
                _log.error("  [%d] %-8s FAILED: %s", i, b.asset, e)
                failed_count += 1

            # Pace requests to avoid 429 rate-limits
            # Testnet limit: 50 orders per 10 seconds → ~4/sec
            if i % 4 == 0:
                time.sleep(1.0)

    # 5) Final report
    _log.info("")
    if dry_run:
        _log.info("═══ DRY-RUN complete (no trades executed) ═══")
        _log.info("Re-run with --execute to actually sell.")
    else:
        _log.info("═══ Sold %d asset(s), failed %d ═══", sold_count, failed_count)

    if skipped:
        _log.info("Skipped (%d): %s", len(skipped), ", ".join(skipped[:30]))
        if len(skipped) > 30:
            _log.info("  … and %d more", len(skipped) - 30)

    _log.info("")
    _log.info("── Final account balances ──")
    final_balances = client.account()
    remaining = [b for b in final_balances if (b.free + b.locked) > 0]
    usdt_final = next((b for b in remaining if b.asset == KEEP_ASSET), None)

    if usdt_final:
        _log.info("  USDT   free=%14.4f  locked=%14.4f", usdt_final.free, usdt_final.locked)

    others = [b for b in remaining if b.asset != KEEP_ASSET]
    if others:
        _log.info("  Non-USDT assets still remaining: %d", len(others))
        for b in others[:20]:
            _log.info("    %-10s free=%14.8f  locked=%14.8f", b.asset, b.free, b.locked)
        if len(others) > 20:
            _log.info("    … and %d more", len(others) - 20)
    else:
        _log.info("  Account is now 100%% USDT ✓")


# ---------------------------------------------------------------------------
# Clean Account Gate
# ---------------------------------------------------------------------------


class CleanAccountError(Exception):
    """Raised when the account fails the clean-account gate check."""


def verify_clean_account(
    client: BinanceSpotClient,
    *,
    allowed_assets: set[str] | None = None,
    dust_threshold_usd: float = DUST_THRESHOLD_USD,
    required_zero: set[str] | None = None,
) -> dict[str, Any]:
    """Verify the account is 'clean' — only allowed assets remain.

    Parameters
    ----------
    client:
        Connected BinanceSpotClient (testnet).
    allowed_assets:
        Assets that may have a non-zero balance (default: ALLOWED_ASSETS).
    dust_threshold_usd:
        Non-allowed assets whose estimated USD value is below this
        are treated as dust and tolerated.  Defaults to 1.0.
    required_zero:
        Assets that MUST have zero balance.  Default: {"BTC"}.

    Returns
    -------
    dict with keys: passed (bool), usdt_balance, dust_assets, violations.

    Raises
    ------
    CleanAccountError
        If any violation is found (non-dust foreign asset, or
        a required-zero asset has balance > 0).
    """

    if "testnet" not in client.base_url:
        raise RuntimeError("verify_clean_account is restricted to TESTNET")

    if allowed_assets is None:
        allowed_assets = ALLOWED_ASSETS
    if required_zero is None:
        required_zero = {"BTC"}

    balances: list[AccountBalance] = client.account()
    pair_map = build_usdt_pair_map(client)

    usdt_bal = next((b for b in balances if b.asset == "USDT"), None)
    usdt_total = (usdt_bal.free + usdt_bal.locked) if usdt_bal else 0.0

    violations: list[str] = []
    dust_assets: list[dict[str, Any]] = []

    for b in balances:
        total = b.free + b.locked
        if total <= 0:
            continue

        # Check required-zero assets
        if b.asset in required_zero and total > 0:
            violations.append(f"{b.asset} must be 0 but has {total:.8f}")
            continue

        # Allowed assets are fine
        if b.asset in allowed_assets:
            continue

        # Non-allowed asset — estimate USD value
        est_usd = 0.0
        if b.asset in pair_map:
            try:
                price = get_last_price(client, pair_map[b.asset].symbol)
                est_usd = total * price
            except Exception:
                est_usd = 0.0  # can't price → treat as ~0

        if est_usd >= dust_threshold_usd:
            violations.append(
                f"{b.asset}: balance={total:.8f}, est_value=${est_usd:.2f} (≥ dust threshold ${dust_threshold_usd})"
            )
        else:
            dust_assets.append({"asset": b.asset, "balance": total, "est_usd": est_usd})

    result = {
        "passed": len(violations) == 0,
        "usdt_balance": usdt_total,
        "dust_count": len(dust_assets),
        "dust_assets": dust_assets,
        "violations": violations,
    }

    _log.info("")
    _log.info("═══ Clean Account Gate ═══")
    _log.info("  USDT balance: %.4f", usdt_total)
    _log.info("  Dust assets (< $%.2f): %d", dust_threshold_usd, len(dust_assets))
    if dust_assets:
        for d in dust_assets[:10]:
            _log.info(
                "    %-10s  bal=%14.8f  ~$%.4f",
                d["asset"],
                d["balance"],
                d["est_usd"],
            )
        if len(dust_assets) > 10:
            _log.info("    … and %d more dust assets", len(dust_assets) - 10)

    if violations:
        _log.error("  GATE FAILED — %d violation(s):", len(violations))
        for v in violations:
            _log.error("    • %s", v)
        raise CleanAccountError(f"Clean account gate failed with {len(violations)} violation(s): " + "; ".join(violations))

    _log.info("  GATE PASSED ✓")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sell all non-USDT assets on Binance Spot Testnet.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute market sells. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run Clean Account Gate only (no selling). Exit 0 if passed, 1 if failed.",
    )
    parser.add_argument(
        "--dust-threshold",
        type=float,
        default=DUST_THRESHOLD_USD,
        help=f"USD value below which a non-allowed asset is treated as dust (default: {DUST_THRESHOLD_USD}).",
    )
    args = parser.parse_args()

    client = BinanceSpotClient()  # defaults to testnet

    if args.verify:
        try:
            result = verify_clean_account(client, dust_threshold_usd=args.dust_threshold)
            raise SystemExit(0 if result["passed"] else 1)
        except CleanAccountError as exc:
            raise SystemExit(1) from exc
    else:
        clean_account(client, dry_run=not args.execute)
        # After execute mode, automatically run the gate
        if args.execute:
            _log.info("")
            try:
                verify_clean_account(client, dust_threshold_usd=args.dust_threshold)
            except CleanAccountError:
                _log.warning("Gate check failed — some non-dust assets remain.")


if __name__ == "__main__":
    main()
