"""Tests for exchange filters — parsing, rounding, order validation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from v10.exchange.filters import (
    SymbolInfo,
    parse_symbol_info,
    round_price,
    round_qty_down,
    validate_order,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _btcusdt_exchange_data() -> dict:
    """Realistic BTCUSDT symbol entry from exchangeInfo."""
    return {
        "symbol": "BTCUSDT",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01000000", "minPrice": "0.01", "maxPrice": "1000000"},
            {"filterType": "LOT_SIZE", "stepSize": "0.00001000", "minQty": "0.00001000", "maxQty": "9000.00000000"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "10.00000000"},
            {"filterType": "ICEBERG_PARTS", "limit": 10},
        ],
    }


def _btcusdt_info() -> SymbolInfo:
    return parse_symbol_info(_btcusdt_exchange_data())


# ---------------------------------------------------------------------------
# 1) Parsing
# ---------------------------------------------------------------------------

class TestParseSymbolInfo:
    def test_parse_basic_fields(self) -> None:
        info = _btcusdt_info()
        assert info.symbol == "BTCUSDT"
        assert info.base_asset == "BTC"
        assert info.quote_asset == "USDT"

    def test_parse_filter_values(self) -> None:
        info = _btcusdt_info()
        assert info.tick_size == Decimal("0.01")
        assert info.step_size == Decimal("0.00001")
        assert info.min_qty == Decimal("0.00001")
        assert info.max_qty == Decimal("9000")
        assert info.min_notional == Decimal("10")

    def test_parse_precision(self) -> None:
        info = _btcusdt_info()
        assert info.price_precision == 2
        assert info.qty_precision == 5

    def test_missing_filters_use_defaults(self) -> None:
        data = {"symbol": "FOOBAR", "baseAsset": "FOO", "quoteAsset": "BAR", "filters": []}
        info = parse_symbol_info(data)
        # Should use fallback defaults, not crash
        assert info.tick_size == Decimal("0.01")
        assert info.step_size == Decimal("0.00001")
        assert info.min_notional == Decimal("10.0")

    def test_notional_filter_variant(self) -> None:
        """Binance sometimes uses 'NOTIONAL' instead of 'MIN_NOTIONAL'."""
        data = {
            "symbol": "ETHUSDT",
            "baseAsset": "ETH",
            "quoteAsset": "USDT",
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                {"filterType": "LOT_SIZE", "stepSize": "0.0001", "minQty": "0.0001", "maxQty": "9000"},
                {"filterType": "NOTIONAL", "minNotional": "5.00"},
            ],
        }
        info = parse_symbol_info(data)
        assert info.min_notional == Decimal("5.00")


# ---------------------------------------------------------------------------
# 2) round_qty_down
# ---------------------------------------------------------------------------

class TestRoundQtyDown:
    def test_exact_step(self) -> None:
        info = _btcusdt_info()  # step=0.00001
        assert round_qty_down(0.12345, info) == 0.12345

    def test_truncates_excess(self) -> None:
        info = _btcusdt_info()
        assert round_qty_down(0.123456789, info) == 0.12345

    def test_tiny_qty_floors_to_zero(self) -> None:
        info = _btcusdt_info()
        assert round_qty_down(0.000001, info) == 0.0

    def test_large_qty(self) -> None:
        info = _btcusdt_info()
        assert round_qty_down(123.456789, info) == 123.45678

    def test_step_size_one(self) -> None:
        info = SymbolInfo(
            symbol="TEST", base_asset="T", quote_asset="U",
            tick_size=Decimal("1"), step_size=Decimal("1"),
            min_qty=Decimal("1"), max_qty=Decimal("100"),
            min_notional=Decimal("10"), price_precision=0, qty_precision=0,
        )
        assert round_qty_down(5.9, info) == 5.0

    def test_never_rounds_up(self) -> None:
        info = _btcusdt_info()
        # 0.000019999 should floor to 0.00001, not 0.00002
        assert round_qty_down(0.000019999, info) == 0.00001


# ---------------------------------------------------------------------------
# 3) round_price
# ---------------------------------------------------------------------------

class TestRoundPrice:
    def test_exact_tick(self) -> None:
        info = _btcusdt_info()  # tick=0.01
        assert round_price(67389.01, info) == 67389.01

    def test_rounds_up(self) -> None:
        info = _btcusdt_info()
        assert round_price(67389.005, info) == 67389.01

    def test_rounds_down(self) -> None:
        info = _btcusdt_info()
        assert round_price(67389.004, info) == 67389.0

    def test_tick_size_0_1(self) -> None:
        info = SymbolInfo(
            symbol="TEST", base_asset="T", quote_asset="U",
            tick_size=Decimal("0.1"), step_size=Decimal("0.001"),
            min_qty=Decimal("0.001"), max_qty=Decimal("9000"),
            min_notional=Decimal("10"), price_precision=1, qty_precision=3,
        )
        assert round_price(123.45, info) == 123.5
        assert round_price(123.44, info) == 123.4


# ---------------------------------------------------------------------------
# 4) validate_order
# ---------------------------------------------------------------------------

class TestValidateOrder:
    def test_valid_order(self) -> None:
        info = _btcusdt_info()
        errors = validate_order(qty=0.001, price=67000.0, info=info)
        assert errors == []

    def test_qty_below_min(self) -> None:
        info = _btcusdt_info()
        errors = validate_order(qty=0.000001, price=67000.0, info=info)
        assert any("minQty" in e for e in errors)

    def test_qty_above_max(self) -> None:
        info = _btcusdt_info()
        errors = validate_order(qty=10000.0, price=67000.0, info=info)
        assert any("maxQty" in e for e in errors)

    def test_qty_not_on_step(self) -> None:
        info = _btcusdt_info()
        errors = validate_order(qty=0.000012, price=67000.0, info=info)
        assert any("stepSize" in e for e in errors)

    def test_price_not_on_tick(self) -> None:
        info = _btcusdt_info()
        errors = validate_order(qty=0.001, price=67000.005, info=info)
        assert any("tickSize" in e for e in errors)

    def test_notional_below_min(self) -> None:
        info = _btcusdt_info()  # min_notional=10
        # 0.00001 * 67000 = 0.67 < 10
        errors = validate_order(qty=0.00001, price=67000.0, info=info)
        assert any("minNotional" in e for e in errors)

    def test_no_price_skips_tick_and_notional(self) -> None:
        info = _btcusdt_info()
        errors = validate_order(qty=0.001, price=None, info=info)
        assert errors == []

    def test_multiple_errors(self) -> None:
        info = _btcusdt_info()
        # qty too small, not on step, notional too low
        errors = validate_order(qty=0.0000001, price=67000.005, info=info)
        assert len(errors) >= 2
