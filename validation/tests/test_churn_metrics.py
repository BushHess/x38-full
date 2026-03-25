"""Unit tests for churn-metrics suite outputs and reporting."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from v10.core.config import load_config
from v10.core.types import BacktestResult
from v10.core.types import Bar
from v10.core.types import EquitySnap
from v10.core.types import Fill
from v10.core.types import Side
from v10.core.types import Trade
from validation.config import ValidationConfig
from validation.report import generate_quality_checks_report
from validation.suites.base import SuiteContext
from validation.suites.churn_metrics import ChurnMetricsSuite

ROOT = Path(__file__).resolve().parents[2]
BASELINE_CFG = ROOT / "v10" / "configs" / "baseline_legacy.live.yaml"

_H4_MS = 14_400_000
_D1_MS = 86_400_000


def _h4_bar(idx: int, price: float = 50_000.0) -> Bar:
    open_time = idx * _H4_MS
    return Bar(
        open_time=open_time,
        open=price,
        high=price * 1.01,
        low=price * 0.99,
        close=price,
        volume=100.0,
        close_time=open_time + _H4_MS - 1,
        taker_buy_base_vol=50.0,
        interval="4h",
    )


def _d1_bar(idx: int, price: float = 50_000.0) -> Bar:
    open_time = idx * _D1_MS
    return Bar(
        open_time=open_time,
        open=price,
        high=price * 1.01,
        low=price * 0.99,
        close=price,
        volume=500.0,
        close_time=open_time + _D1_MS - 1,
        taker_buy_base_vol=250.0,
        interval="1d",
    )


class _FakeFeed:
    def __init__(self) -> None:
        self.h4_bars = [_h4_bar(i) for i in range(24)]
        self.d1_bars = [_d1_bar(0), _d1_bar(1), _d1_bar(2), _d1_bar(3)]
        self.report_start_ms: int | None = self.h4_bars[0].open_time


def _make_backtest_result(trades: list[Trade], fills: list[Fill]) -> BacktestResult:
    equity = [
        EquitySnap(
            close_time=i * _H4_MS + _H4_MS - 1,
            nav_mid=10_000.0 + i,
            nav_liq=10_000.0 + i,
            cash=10_000.0,
            btc_qty=0.0,
            exposure=0.0,
        )
        for i in range(24)
    ]
    return BacktestResult(
        equity=equity,
        fills=fills,
        trades=trades,
        summary={},
    )


def _build_ctx(tmp_path: Path) -> SuiteContext:
    outdir = tmp_path / "out"
    results_dir = outdir / "results"
    reports_dir = outdir / "reports"
    results_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    cfg = ValidationConfig(
        strategy_name="candidate",
        baseline_name="baseline",
        config_path=BASELINE_CFG,
        baseline_config_path=BASELINE_CFG,
        outdir=outdir,
        dataset=ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv",
        suite="basic",
        scenarios=["base"],
        lookahead_check=False,
        bootstrap=0,
        churn_metrics=True,
        churn_warning_fee_drag_pct=10.0,
        churn_warning_cascade_leq3_pct=10.0,
        churn_warning_cascade_leq6_pct=20.0,
    )
    live_cfg = load_config(str(BASELINE_CFG))
    feed = _FakeFeed()

    ctx = SuiteContext(
        feed=feed,
        data_path=cfg.dataset,
        project_root=ROOT,
        candidate_factory=lambda: None,
        baseline_factory=lambda: None,
        candidate_live_config=live_cfg,
        baseline_live_config=live_cfg,
        candidate_config_obj=None,
        baseline_config_obj=None,
        validation_config=cfg,
        resolved_suites=["churn_metrics"],
        outdir=outdir,
        results_dir=results_dir,
        reports_dir=reports_dir,
    )

    candidate_trades = [
        Trade(
            trade_id=1,
            entry_ts_ms=2 * _H4_MS,
            exit_ts_ms=4 * _H4_MS,
            entry_price=50_000.0,
            exit_price=49_000.0,
            qty=1.0,
            pnl=-50.0,
            return_pct=-2.0,
            days_held=2 * _H4_MS / 86_400_000.0,
            entry_reason="vdo_trend",
            exit_reason="emergency_dd",
        ),
        Trade(
            trade_id=2,
            entry_ts_ms=5 * _H4_MS,
            exit_ts_ms=8 * _H4_MS,
            entry_price=49_500.0,
            exit_price=50_500.0,
            qty=1.0,
            pnl=80.0,
            return_pct=2.02,
            days_held=3 * _H4_MS / 86_400_000.0,
            entry_reason="vdo_dip_buy",
            exit_reason="trailing_stop",
        ),
        Trade(
            trade_id=3,
            entry_ts_ms=10 * _H4_MS,
            exit_ts_ms=12 * _H4_MS,
            entry_price=50_300.0,
            exit_price=50_700.0,
            qty=1.0,
            pnl=20.0,
            return_pct=0.79,
            days_held=2 * _H4_MS / 86_400_000.0,
            entry_reason="vdo_trend_accel",
            exit_reason="fixed_stop",
        ),
    ]
    candidate_fills = [
        Fill(ts_ms=2 * _H4_MS, side=Side.BUY, qty=1.0, price=50_000.0, fee=7.5, notional=50_000.0, reason="entry"),
        Fill(ts_ms=4 * _H4_MS, side=Side.SELL, qty=1.0, price=49_000.0, fee=7.5, notional=49_000.0, reason="exit"),
        Fill(ts_ms=5 * _H4_MS, side=Side.BUY, qty=1.0, price=49_500.0, fee=7.5, notional=49_500.0, reason="entry"),
        Fill(ts_ms=8 * _H4_MS, side=Side.SELL, qty=1.0, price=50_500.0, fee=7.5, notional=50_500.0, reason="exit"),
        Fill(ts_ms=10 * _H4_MS, side=Side.BUY, qty=1.0, price=50_300.0, fee=7.5, notional=50_300.0, reason="entry"),
        Fill(ts_ms=12 * _H4_MS, side=Side.SELL, qty=1.0, price=50_700.0, fee=7.5, notional=50_700.0, reason="exit"),
    ]

    baseline_trades = [
        Trade(
            trade_id=1,
            entry_ts_ms=2 * _H4_MS,
            exit_ts_ms=7 * _H4_MS,
            entry_price=50_000.0,
            exit_price=50_300.0,
            qty=1.0,
            pnl=30.0,
            return_pct=0.6,
            days_held=5 * _H4_MS / 86_400_000.0,
            entry_reason="vdo_trend",
            exit_reason="trailing_stop",
        )
    ]
    baseline_fills = [
        Fill(ts_ms=2 * _H4_MS, side=Side.BUY, qty=1.0, price=50_000.0, fee=1.0, notional=50_000.0, reason="entry"),
        Fill(ts_ms=7 * _H4_MS, side=Side.SELL, qty=1.0, price=50_300.0, fee=1.0, notional=50_300.0, reason="exit"),
    ]

    ctx.backtest_cache[("candidate", "base")] = _make_backtest_result(candidate_trades, candidate_fills)
    ctx.backtest_cache[("baseline", "base")] = _make_backtest_result(baseline_trades, baseline_fills)
    return ctx


def test_churn_metrics_csv_has_required_columns_and_no_nan(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    result = ChurnMetricsSuite().run(ctx)

    assert result.status == "pass"
    csv_path = ctx.results_dir / "churn_metrics.csv"
    assert csv_path.exists()

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        required = {
            "strategy_id",
            "scenario",
            "period_start",
            "period_end",
            "trades",
            "trades_per_month",
            "entries_per_week",
            "avg_hold_bars",
            "avg_hold_days",
            "total_fees",
            "fee_drag_pct",
            "turnover",
            "turnover_per_month",
            "share_emergency_dd",
            "share_trailing_stop",
            "share_fixed_stop",
            "reentry_median_bars",
            "reentry_p90_bars",
            "cascade_leq3",
            "cascade_leq6",
            "cascade_leq12",
            "buy_sell_ratio",
        }
        assert required.issubset(set(reader.fieldnames))

        rows = list(reader)
        assert len(rows) == 2
        for row in rows:
            assert row["period_start"]
            assert row["period_end"]
            for field in reader.fieldnames:
                value = row.get(field, "")
                assert value != ""
                if field in {"strategy_id", "scenario", "period_start", "period_end"}:
                    continue
                num = float(value)
                assert not math.isnan(num)
                assert math.isfinite(num)


def test_quality_checks_report_includes_churn_section_and_warnings(tmp_path: Path) -> None:
    ctx = _build_ctx(tmp_path)
    result = ChurnMetricsSuite().run(ctx)
    assert len(result.data.get("warnings", [])) > 0

    report_path = generate_quality_checks_report(
        {"churn_metrics": result},
        ctx.validation_config,
        ctx.outdir,
    )
    text = report_path.read_text()

    assert "## Churn & Fee Drag" in text
    assert "WARNING count" in text
    assert "fee_drag_pct>=" in text
    assert "`results/churn_metrics.csv`" in text
