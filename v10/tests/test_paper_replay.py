"""Test paper runner deterministic replay.

Verifies that replaying from cached klines produces identical
paper_signals.csv, paper_orders.csv, and paper_equity.csv output
(same SHA-256 hash).
"""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

import pytest


H4_MS = 14_400_000  # 4h in ms
D1_MS = 86_400_000  # 1d in ms


def _make_test_csv(path: Path, n_days: int = 400) -> None:
    """Generate a deterministic multi-TF CSV with n_days of data.

    Price: uptrend with 60-day oscillation cycle.
    Volume: variable with oscillating taker-buy ratio for VDO variation.
    """
    rows: list[dict[str, object]] = []
    base_price = 30_000.0
    base_ms = 1577836800000  # 2020-01-01T00:00:00Z

    # H4 bars: 6 per day
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
                "open_time": ot,
                "open": round(p_open, 2),
                "high": round(p_high, 2),
                "low": round(p_low, 2),
                "close": round(p_close, 2),
                "volume": round(vol, 4),
                "close_time": ct,
                "quote_volume": round(p_open * vol, 2),
                "trades": 50,
                "taker_buy_base_vol": round(tbv, 4),
                "taker_buy_quote_vol": round(p_open * tbv, 2),
                "interval": "4h",
            })

    # D1 bars: 1 per day
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
            "open_time": ot,
            "open": round(p_open, 2),
            "high": round(p_high, 2),
            "low": round(p_low, 2),
            "close": round(p_close, 2),
            "volume": round(vol, 4),
            "close_time": ct,
            "quote_volume": round(p_open * vol, 2),
            "trades": 300,
            "taker_buy_base_vol": round(tbv, 4),
            "taker_buy_quote_vol": round(p_open * tbv, 2),
            "interval": "1d",
        })

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class TestPaperReplay:
    """Deterministic replay produces identical output CSV hashes."""

    def test_replay_identical_output_hash(self, tmp_path: Path) -> None:
        """Run paper trader from CSV, cache klines, replay from cache.
        paper_signals.csv, paper_orders.csv, paper_equity.csv must be
        byte-identical (same SHA-256).
        """
        # Generate deterministic test data
        csv_path = tmp_path / "test_bars.csv"
        _make_test_csv(csv_path, n_days=400)

        # Minimal config for v8_apex with warmup
        config_path = tmp_path / "test_config.yaml"
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

        from v10.cli.paper import main as paper_main

        # Run 1: from CSV
        outdir1 = tmp_path / "run1"
        paper_main([
            "--source", "csv",
            "--data", str(csv_path),
            "--config", str(config_path),
            "--outdir", str(outdir1),
        ])

        # Verify all outputs exist
        for name in (
            "paper_signals.csv", "paper_orders.csv", "paper_equity.csv",
            "paper_state.db", "run_meta.json",
        ):
            assert (outdir1 / name).exists(), f"Missing {name} in run1"

        # Cache must exist
        cache_dir = outdir1 / "paper_kline_cache"
        assert (cache_dir / "BTCUSDT_4h.csv").exists()
        assert (cache_dir / "BTCUSDT_1d.csv").exists()

        # Run 2: deterministic replay from cache
        outdir2 = tmp_path / "run2"
        paper_main([
            "--replay", str(cache_dir),
            "--config", str(config_path),
            "--outdir", str(outdir2),
        ])

        # Compare SHA-256 hashes for all output CSVs
        for name in ("paper_signals.csv", "paper_orders.csv",
                      "paper_equity.csv"):
            hash1 = _sha256(outdir1 / name)
            hash2 = _sha256(outdir2 / name)
            assert hash1 == hash2, (
                f"Replay produced different {name}!\n"
                f"  Run 1 hash: {hash1}\n"
                f"  Run 2 hash: {hash2}"
            )

    def test_outputs_have_content(self, tmp_path: Path) -> None:
        """Verify paper runner produces non-empty equity output."""
        csv_path = tmp_path / "test_bars.csv"
        _make_test_csv(csv_path, n_days=400)

        config_path = tmp_path / "test_config.yaml"
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

        from v10.cli.paper import main as paper_main

        outdir = tmp_path / "out"
        paper_main([
            "--source", "csv",
            "--data", str(csv_path),
            "--config", str(config_path),
            "--outdir", str(outdir),
        ])

        # Equity CSV must have header + data rows
        # With 400 days and 365 warmup, expect ~210 equity snaps (35 days × 6)
        with open(outdir / "paper_equity.csv") as f:
            lines = f.readlines()
        assert len(lines) > 1, "paper_equity.csv has no data rows"
        assert len(lines) >= 100, (
            f"Expected ~210 equity snaps, got {len(lines) - 1}"
        )

    def test_sqlite_state_persisted(self, tmp_path: Path) -> None:
        """Verify SQLite state is written correctly."""
        csv_path = tmp_path / "test_bars.csv"
        _make_test_csv(csv_path, n_days=400)

        config_path = tmp_path / "test_config.yaml"
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

        from v10.cli.paper import main as paper_main

        outdir = tmp_path / "out"
        paper_main([
            "--source", "csv",
            "--data", str(csv_path),
            "--config", str(config_path),
            "--outdir", str(outdir),
        ])

        import sqlite3
        conn = sqlite3.connect(str(outdir / "paper_state.db"))

        # State table must have exactly one row
        row = conn.execute(
            "SELECT last_h4_close_ms FROM state WHERE id = 1"
        ).fetchone()
        assert row is not None, "state table is empty"
        assert row[0] > 0, "last_h4_close_ms should be positive"

        # equity_snaps table must have rows
        count = conn.execute(
            "SELECT COUNT(*) FROM equity_snaps"
        ).fetchone()[0]
        assert count > 0, "equity_snaps table is empty"

        conn.close()
