"""ExchangeInfo filter parsing, quantity/price rounding, order validation.

Uses ``decimal.Decimal`` internally to avoid float rounding errors when
snapping quantities to ``stepSize`` and prices to ``tickSize``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Any

from v10.exchange.rest_client import BinanceSpotClient


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SymbolInfo:
    """Parsed exchange filters for a single trading pair."""

    symbol: str
    base_asset: str
    quote_asset: str
    tick_size: Decimal       # PRICE_FILTER.tickSize
    step_size: Decimal       # LOT_SIZE.stepSize
    min_qty: Decimal         # LOT_SIZE.minQty
    max_qty: Decimal         # LOT_SIZE.maxQty
    min_notional: Decimal    # MIN_NOTIONAL / NOTIONAL .minNotional
    price_precision: int     # decimal places in tick_size
    qty_precision: int       # decimal places in step_size


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _count_decimals(val: str) -> int:
    """Count decimal places in a numeric string like '0.01000000'."""
    val = val.rstrip("0") or "0"
    if "." not in val:
        return 0
    return len(val.split(".")[1])


def _find_filter(filters: list[dict[str, Any]], filter_type: str) -> dict[str, Any]:
    for f in filters:
        if f.get("filterType") == filter_type:
            return f
    return {}


def parse_symbol_info(data: dict[str, Any]) -> SymbolInfo:
    """Parse a single element from ``exchangeInfo["symbols"]``."""
    filters = data.get("filters", [])

    pf = _find_filter(filters, "PRICE_FILTER")
    ls = _find_filter(filters, "LOT_SIZE")

    # MIN_NOTIONAL or NOTIONAL (Binance renamed it at some point)
    mn = _find_filter(filters, "MIN_NOTIONAL") or _find_filter(filters, "NOTIONAL")

    tick_str = pf.get("tickSize", "0.01")
    step_str = ls.get("stepSize", "0.00001")
    min_qty_str = ls.get("minQty", "0.00001")
    max_qty_str = ls.get("maxQty", "9999999")
    min_notional_str = mn.get("minNotional", "10.0")

    return SymbolInfo(
        symbol=data["symbol"],
        base_asset=data.get("baseAsset", ""),
        quote_asset=data.get("quoteAsset", ""),
        tick_size=Decimal(tick_str),
        step_size=Decimal(step_str),
        min_qty=Decimal(min_qty_str),
        max_qty=Decimal(max_qty_str),
        min_notional=Decimal(min_notional_str),
        price_precision=_count_decimals(tick_str),
        qty_precision=_count_decimals(step_str),
    )


def fetch_symbol_info(client: BinanceSpotClient, symbol: str) -> SymbolInfo:
    """Fetch and parse filters for *symbol* from the exchange."""
    raw = client.exchange_info(symbol=symbol)
    symbols = raw.get("symbols", [])
    if not symbols:
        raise ValueError(f"Symbol {symbol!r} not found in exchangeInfo")
    return parse_symbol_info(symbols[0])


# ---------------------------------------------------------------------------
# Rounding helpers
# ---------------------------------------------------------------------------

def round_qty_down(qty: float, info: SymbolInfo) -> float:
    """Floor *qty* to the nearest ``stepSize`` (truncate, never round up)."""
    d_qty = Decimal(str(qty))
    step = info.step_size
    result = (d_qty / step).to_integral_value(rounding=ROUND_DOWN) * step
    return float(result)


def round_price(price: float, info: SymbolInfo) -> float:
    """Round *price* to the nearest ``tickSize``."""
    d_price = Decimal(str(price))
    tick = info.tick_size
    result = (d_price / tick).to_integral_value(rounding=ROUND_HALF_UP) * tick
    return float(result)


# ---------------------------------------------------------------------------
# Order validation
# ---------------------------------------------------------------------------

def validate_order(
    qty: float,
    price: float | None,
    info: SymbolInfo,
) -> list[str]:
    """Validate *qty* and *price* against symbol filters.

    Returns a list of error strings.  Empty list = valid.
    """
    errors: list[str] = []
    d_qty = Decimal(str(qty))

    if d_qty < info.min_qty:
        errors.append(f"qty {qty} < minQty {info.min_qty}")
    if d_qty > info.max_qty:
        errors.append(f"qty {qty} > maxQty {info.max_qty}")

    # Step-size alignment
    remainder = d_qty % info.step_size
    if remainder != 0:
        errors.append(f"qty {qty} not aligned to stepSize {info.step_size}")

    if price is not None:
        d_price = Decimal(str(price))
        tick_rem = d_price % info.tick_size
        if tick_rem != 0:
            errors.append(f"price {price} not aligned to tickSize {info.tick_size}")

        notional = d_qty * d_price
        if notional < info.min_notional:
            errors.append(f"notional {float(notional):.2f} < minNotional {info.min_notional}")

    return errors
