"""Tests for ISO-8601 UTC timestamp formatting in CSV outputs.

Verifies that every timestamp emitted in equity.csv, trades.csv,
fills.csv, paper_signals.csv, paper_orders.csv, and paper_equity.csv
is parseable as ISO-8601 UTC, never contains '24:', and round-trips
back to the original epoch-millisecond value.
"""

from __future__ import annotations

import csv
import math
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from v10.core.formatting import ms_to_iso
from v10.cli.backtest import _write_outputs
from v10.core.types import (
    BacktestResult,
    CostConfig,
    EquitySnap,
    Fill,
    Side,
    Trade,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Epoch-ms for 2024-01-15 08:00:00 UTC
_TS1 = 1705305600000
# Epoch-ms for 2024-03-20 16:00:00 UTC
_TS2 = 1710950400000
# Epoch-ms for 2024-06-01 00:00:00 UTC  (midnight — the "24:00" edge case)
_TS3 = 1717200000000


def _sample_result() -> BacktestResult:
    """Build a minimal BacktestResult with known timestamps."""
    equity = [
        EquitySnap(close_time=_TS1, nav_mid=10000.0, nav_liq=9990.0,
                   cash=5000.0, btc_qty=0.1, exposure=0.5),
        EquitySnap(close_time=_TS2, nav_mid=11000.0, nav_liq=10980.0,
                   cash=5000.0, btc_qty=0.1, exposure=0.5454),
        EquitySnap(close_time=_TS3, nav_mid=12000.0, nav_liq=11970.0,
                   cash=12000.0, btc_qty=0.0, exposure=0.0),
    ]
    fills = [
        Fill(ts_ms=_TS1, side=Side.BUY, qty=0.1, price=50000.0,
             fee=5.0, notional=5000.0, reason="entry"),
        Fill(ts_ms=_TS2, side=Side.SELL, qty=0.1, price=60000.0,
             fee=6.0, notional=6000.0, reason="trail_stop"),
    ]
    trades = [
        Trade(trade_id=1, entry_ts_ms=_TS1, exit_ts_ms=_TS2,
              entry_price=50000.0, exit_price=60000.0, qty=0.1,
              pnl=989.0, return_pct=19.78, days_held=65.33,
              entry_reason="entry", exit_reason="trail_stop"),
    ]
    summary = {
        "initial_cash": 10000.0,
        "final_nav_mid": 12000.0,
        "trades": 1,
    }
    return BacktestResult(equity=equity, fills=fills, trades=trades,
                          summary=summary)


def _parse_iso(s: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp string. Raises on failure."""
    # strptime with explicit Z-suffix format
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMsToIso:
    """Unit tests for the ms_to_iso helper."""

    def test_known_timestamp(self) -> None:
        assert ms_to_iso(_TS1) == "2024-01-15T08:00:00Z"

    def test_midnight_no_2400(self) -> None:
        # Midnight should be 00:00:00, never 24:00:00
        iso = ms_to_iso(_TS3)
        assert "24:00" not in iso
        assert iso == "2024-06-01T00:00:00Z"

    def test_round_trip(self) -> None:
        iso = ms_to_iso(_TS2)
        dt = _parse_iso(iso)
        recovered_ms = int(dt.timestamp() * 1000)
        assert recovered_ms == _TS2


class TestCsvTimestamps:
    """Integration test: write CSVs, parse every timestamp field."""

    def test_all_timestamps_parseable(self) -> None:
        result = _sample_result()

        with tempfile.TemporaryDirectory() as tmpdir:
            _write_outputs(result, tmpdir)
            out = Path(tmpdir)

            # --- equity.csv ---
            with open(out / "equity.csv") as f:
                reader = csv.DictReader(f)
                equity_rows = list(reader)

            assert len(equity_rows) == 3
            for row in equity_rows:
                iso = row["close_time"]
                assert "24:00" not in iso, f"equity.csv contains '24:00': {iso}"
                dt = _parse_iso(iso)
                # Round-trip check
                ms = int(row["close_time_ms"])
                assert int(dt.timestamp() * 1000) == ms

            # --- fills.csv ---
            with open(out / "fills.csv") as f:
                reader = csv.DictReader(f)
                fills_rows = list(reader)

            assert len(fills_rows) == 2
            for row in fills_rows:
                iso = row["time"]
                assert "24:00" not in iso, f"fills.csv contains '24:00': {iso}"
                dt = _parse_iso(iso)
                ms = int(row["ts_ms"])
                assert int(dt.timestamp() * 1000) == ms

            # --- trades.csv ---
            with open(out / "trades.csv") as f:
                reader = csv.DictReader(f)
                trades_rows = list(reader)

            assert len(trades_rows) == 1
            for row in trades_rows:
                for col_iso, col_ms in [
                    ("entry_time", "entry_ts_ms"),
                    ("exit_time", "exit_ts_ms"),
                ]:
                    iso = row[col_iso]
                    assert "24:00" not in iso, f"trades.csv {col_iso} contains '24:00': {iso}"
                    dt = _parse_iso(iso)
                    ms = int(row[col_ms])
                    assert int(dt.timestamp() * 1000) == ms

    def test_csv_headers_match_spec(self) -> None:
        """Verify exact column order in each CSV."""
        result = _sample_result()

        with tempfile.TemporaryDirectory() as tmpdir:
            _write_outputs(result, tmpdir)
            out = Path(tmpdir)

            with open(out / "equity.csv") as f:
                header = next(csv.reader(f))
            assert header == [
                "close_time", "close_time_ms",
                "nav_mid", "nav_liq", "cash", "btc_qty", "exposure",
            ]

            with open(out / "fills.csv") as f:
                header = next(csv.reader(f))
            assert header == [
                "time", "ts_ms", "side", "qty", "price", "fee", "notional", "reason",
            ]

            with open(out / "trades.csv") as f:
                header = next(csv.reader(f))
            assert header == [
                "trade_id", "entry_time", "exit_time",
                "entry_ts_ms", "exit_ts_ms",
                "entry_price", "exit_price", "qty",
                "pnl", "return_pct", "days_held",
                "entry_reason", "exit_reason",
            ]


# ---------------------------------------------------------------------------
# ISO pattern used by the comprehensive scan
# ---------------------------------------------------------------------------

_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"

H4_MS = 14_400_000
D1_MS = 86_400_000


def _make_scan_csv(path: Path, n_days: int = 400) -> None:
    """Generate deterministic multi-TF CSV for timestamp scan test."""
    rows: list[dict[str, object]] = []
    base_price = 30_000.0
    base_ms = 1577836800000  # 2020-01-01T00:00:00Z

    for d in range(n_days):
        for h in range(6):
            idx = d * 6 + h
            ot = base_ms + idx * H4_MS
            ct = ot + H4_MS - 1
            trend = base_price * (1.0 + d * 0.002)
            cycle = 2000.0 * math.sin(d * 2.0 * math.pi / 60.0)
            noise = 500.0 * math.sin(idx * 0.7)
            p_open = trend + cycle + noise
            p_close = p_open + 50.0 * math.sin(idx * 0.3)
            p_high = max(p_open, p_close) * 1.005
            p_low = min(p_open, p_close) * 0.995
            vol = 100.0 + 30.0 * abs(math.sin(idx * 0.5))
            tbv = vol * (0.5 + 0.1 * math.sin(idx * 0.4))
            rows.append({
                "open_time": ot, "open": round(p_open, 2),
                "high": round(p_high, 2), "low": round(p_low, 2),
                "close": round(p_close, 2), "volume": round(vol, 4),
                "close_time": ct, "quote_volume": round(p_open * vol, 2),
                "trades": 50, "taker_buy_base_vol": round(tbv, 4),
                "taker_buy_quote_vol": round(p_open * tbv, 2),
                "interval": "4h",
            })

    for d in range(n_days):
        ot = base_ms + d * D1_MS
        ct = ot + D1_MS - 1
        trend = base_price * (1.0 + d * 0.002)
        cycle = 2000.0 * math.sin(d * 2.0 * math.pi / 60.0)
        p_open = trend + cycle
        p_close = p_open + 50.0
        p_high = max(p_open, p_close) * 1.01
        p_low = min(p_open, p_close) * 0.99
        vol = 600.0 + 100.0 * abs(math.sin(d * 0.3))
        tbv = vol * (0.5 + 0.1 * math.sin(d * 0.4))
        rows.append({
            "open_time": ot, "open": round(p_open, 2),
            "high": round(p_high, 2), "low": round(p_low, 2),
            "close": round(p_close, 2), "volume": round(vol, 4),
            "close_time": ct, "quote_volume": round(p_open * vol, 2),
            "trades": 300, "taker_buy_base_vol": round(tbv, 4),
            "taker_buy_quote_vol": round(p_open * tbv, 2),
            "interval": "1d",
        })

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


class TestScanAllCsvTimestamps:
    """Scan every CSV emitted by backtest + paper for ISO-8601 validity.

    Finds all values matching YYYY-MM-DDTHH:MM:SSZ in every .csv file
    under the output directories, parses them with strptime, and fails
    if any contains '24:'.
    """

    def test_no_24_in_any_csv(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "bars.csv"
        _make_scan_csv(csv_path, n_days=400)

        config_path = tmp_path / "cfg.yaml"
        config_path.write_text(
            "engine:\n"
            "  symbol: BTCUSDT\n"
            "  warmup_days: 365\n"
            "  warmup_mode: no_trade\n"
            "  scenario_eval: base\n"
            "  initial_cash: 10000.0\n"
            "strategy:\n"
            "  name: v8_apex\n"
            "risk:\n"
            "  max_total_exposure: 1.0\n"
            "  min_notional_usdt: 10\n"
            "  kill_switch_dd_total: 0.45\n"
            "  max_daily_orders: 5\n"
        )

        # ----- Run backtest -----
        from v10.cli.backtest import main as bt_main
        bt_dir = tmp_path / "bt"
        bt_main([
            "--data", str(csv_path),
            "--config", str(config_path),
            "--outdir", str(bt_dir),
        ])

        # ----- Run paper -----
        from v10.cli.paper import main as paper_main
        paper_dir = tmp_path / "paper"
        paper_main([
            "--source", "csv",
            "--data", str(csv_path),
            "--config", str(config_path),
            "--outdir", str(paper_dir),
        ])

        # ----- Scan every .csv -----
        all_csvs = list(bt_dir.glob("*.csv")) + list(paper_dir.glob("*.csv"))
        assert len(all_csvs) >= 6, (
            f"Expected >=6 CSVs, found {len(all_csvs)}: "
            f"{[p.name for p in all_csvs]}"
        )

        total_timestamps = 0
        for csv_file in all_csvs:
            with open(csv_file) as f:
                content = f.read()

            for match in _ISO_RE.finditer(content):
                ts_str = match.group()
                total_timestamps += 1

                # Must not contain 24:
                assert "24:" not in ts_str, (
                    f"{csv_file.name} contains '24:' timestamp: {ts_str}"
                )

                # Must be parseable
                try:
                    datetime.strptime(ts_str, _ISO_FMT)
                except ValueError:
                    pytest.fail(
                        f"{csv_file.name} has unparseable timestamp: {ts_str}"
                    )

        assert total_timestamps > 0, "No ISO timestamps found in any CSV"
