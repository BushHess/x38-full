"""Test paper-vs-backtest parity tool.

Runs both BacktestEngine and PaperRunner on an identical tiny dataset,
exports their outputs, then verifies the compare tool finds them equivalent.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from v10.core.types import Bar, CostConfig, SCENARIOS, Signal
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.execution import ExecutionModel, Portfolio
from v10.strategies.base import Strategy

H4_MS = 14_400_000  # 4h in ms
D1_MS = 86_400_000  # 1d in ms


# ---------------------------------------------------------------------------
# Deterministic test data generator
# ---------------------------------------------------------------------------

def _make_test_csv(path: Path, n_days: int = 400) -> None:
    """Generate deterministic multi-TF CSV with n_days of data."""
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


# ---------------------------------------------------------------------------
# Signal-logging wrapper strategy
# ---------------------------------------------------------------------------

class _SignalLogger(Strategy):
    """Wraps a strategy and logs all signals with their timestamps."""

    def __init__(self, inner: Strategy) -> None:
        self._inner = inner
        self.signals: list[tuple[int, Signal]] = []

    def name(self) -> str:
        return self._inner.name()

    def on_init(self, h4_bars: list[Bar], d1_bars: list[Bar]) -> None:
        self._inner.on_init(h4_bars, d1_bars)

    def on_bar(self, state) -> Signal | None:
        sig = self._inner.on_bar(state)
        if sig is not None:
            self.signals.append((state.bar.close_time, sig))
        return sig


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCompare:
    """Paper-vs-backtest parity tests using the compare tool."""

    def test_paper_backtest_signal_parity(self, tmp_path: Path) -> None:
        """Run same v8_apex strategy through both engines, compare equity.

        Uses internal APIs directly to ensure both engines get identical
        warmup_days parameter (the backtest CLI doesn't always propagate
        warmup_days to the engine constructor).
        """
        csv_path = tmp_path / "test_bars.csv"
        _make_test_csv(csv_path, n_days=400)

        cost = SCENARIOS["base"]
        warmup_days = 365
        initial_cash = 10_000.0

        # Load data once, share between both engines
        feed = DataFeed(str(csv_path))

        # ----- Run backtest engine -----
        from v10.strategies.v8_apex import V8ApexStrategy

        bt_strategy = V8ApexStrategy()
        bt_engine = BacktestEngine(
            feed=feed,
            strategy=bt_strategy,
            cost=cost,
            initial_cash=initial_cash,
            warmup_days=warmup_days,
            warmup_mode="no_trade",
        )
        bt_result = bt_engine.run()

        # Write backtest equity CSV
        bt_dir = tmp_path / "bt_out"
        bt_dir.mkdir()
        from v10.cli.backtest import _write_outputs
        _write_outputs(bt_result, str(bt_dir))

        # ----- Run paper trader -----
        from v10.cli.paper import (
            PaperRunner, PaperStateDB,
            _write_signals_csv, _write_equity_csv,
        )

        paper_strategy = V8ApexStrategy()
        db = PaperStateDB(tmp_path / "paper_state.db")
        db.clear()

        runner = PaperRunner(
            h4_bars=feed.h4_bars,
            d1_bars=feed.d1_bars,
            strategy=paper_strategy,
            cost=cost,
            scenario_name="base",
            initial_cash=initial_cash,
            warmup_days=warmup_days,
            db=db,
        )
        runner.run()
        db.close()

        # Write paper outputs
        paper_dir = tmp_path / "paper_out"
        paper_dir.mkdir()
        _write_signals_csv(runner.signal_rows, paper_dir / "paper_signals.csv")
        _write_equity_csv(runner.equity_rows, paper_dir / "paper_equity.csv")

        # ----- Compare equity curves -----
        from v10.cli.compare import (
            _load_paper_equity,
            _load_backtest_equity,
            check_equity_curve,
        )

        paper_eq = _load_paper_equity(paper_dir / "paper_equity.csv")
        bt_eq = _load_backtest_equity(bt_dir / "equity.csv")

        assert len(paper_eq) == len(bt_eq), (
            f"Equity snapshot count mismatch: "
            f"paper={len(paper_eq)}, backtest={len(bt_eq)}"
        )

        # Timestamps must match exactly
        for i, (pe, be) in enumerate(zip(paper_eq, bt_eq)):
            assert pe.close_time_ms == be.close_time_ms, (
                f"Equity timestamp mismatch at index {i}: "
                f"paper={pe.close_time_ms}, backtest={be.close_time_ms}"
            )

        # NAV values must match within tolerance (accounting for CSV rounding)
        tol = 0.02  # 2 cents tolerance for float→str→float round-trip
        m = check_equity_curve(paper_eq, bt_eq, tol)
        assert m is None, (
            f"Equity curve mismatch: {m.check} at index {m.index}: "
            f"{m.detail}"
        )

    def test_compare_cli_pass(self, tmp_path: Path) -> None:
        """Compare CLI returns exit code 0 on matching signals."""
        # Create identical paper_signals.csv and backtest_signals.csv
        header = "time_iso,h4_close_ms,d1_close_ms,target_exposure,entry_reason,exit_reason,flags_json\n"
        row1 = '2020-01-01T00:00:00Z,1577836799999,1577750399999,0.500000,entry,,{}\n'
        row2 = '2020-01-02T00:00:00Z,1577923199999,1577836799999,0.000000,,full_exit,{}\n'

        paper_sig = tmp_path / "paper_signals.csv"
        paper_sig.write_text(header + row1 + row2)

        bt_sig = tmp_path / "bt_signals.csv"
        bt_sig.write_text(header + row1 + row2)

        from v10.cli.compare import main as compare_main

        rc = compare_main([
            "--paper-signals", str(paper_sig),
            "--backtest-signals", str(bt_sig),
        ])
        assert rc == 0

    def test_compare_cli_mismatch(self, tmp_path: Path) -> None:
        """Compare CLI returns exit code 2 on mismatched signals."""
        header = "time_iso,h4_close_ms,d1_close_ms,target_exposure,entry_reason,exit_reason,flags_json\n"
        row1 = '2020-01-01T00:00:00Z,1577836799999,1577750399999,0.500000,entry,,{}\n'
        row2_paper = '2020-01-02T00:00:00Z,1577923199999,1577836799999,0.300000,,partial_exit,{}\n'
        row2_bt = '2020-01-02T00:00:00Z,1577923199999,1577836799999,0.000000,,full_exit,{}\n'

        paper_sig = tmp_path / "paper_signals.csv"
        paper_sig.write_text(header + row1 + row2_paper)

        bt_sig = tmp_path / "bt_signals.csv"
        bt_sig.write_text(header + row1 + row2_bt)

        from v10.cli.compare import main as compare_main

        rc = compare_main([
            "--paper-signals", str(paper_sig),
            "--backtest-signals", str(bt_sig),
        ])
        assert rc == 2

    def test_compare_timestamp_mismatch(self, tmp_path: Path) -> None:
        """Compare detects timestamp count mismatch."""
        header = "time_iso,h4_close_ms,d1_close_ms,target_exposure,entry_reason,exit_reason,flags_json\n"
        row1 = '2020-01-01T00:00:00Z,1577836799999,1577750399999,0.500000,entry,,{}\n'

        paper_sig = tmp_path / "paper_signals.csv"
        paper_sig.write_text(header + row1)

        bt_sig = tmp_path / "bt_signals.csv"
        bt_sig.write_text(header)  # no data rows

        from v10.cli.compare import main as compare_main

        rc = compare_main([
            "--paper-signals", str(paper_sig),
            "--backtest-signals", str(bt_sig),
        ])
        assert rc == 2

    def test_derive_signals_from_equity(self) -> None:
        """Test signal derivation from equity exposure transitions."""
        from v10.cli.compare import EquityRow, _derive_signals_from_equity

        equity = [
            EquityRow(close_time_ms=1000, nav_mid=10000, cash=10000,
                      btc_qty=0.0, exposure=0.0),
            EquityRow(close_time_ms=2000, nav_mid=10000, cash=5000,
                      btc_qty=0.5, exposure=0.5),
            EquityRow(close_time_ms=3000, nav_mid=10100, cash=5000,
                      btc_qty=0.5, exposure=0.5),
            EquityRow(close_time_ms=4000, nav_mid=10000, cash=10000,
                      btc_qty=0.0, exposure=0.0),
        ]

        sigs = _derive_signals_from_equity(equity)

        # Should detect: entry at 2000, exit at 4000 (no change at 3000)
        assert len(sigs) == 2
        assert sigs[0].h4_close_ms == 2000
        assert sigs[0].entry_reason == "entry"
        assert sigs[1].h4_close_ms == 4000
        assert sigs[1].exit_reason == "full_exit"
