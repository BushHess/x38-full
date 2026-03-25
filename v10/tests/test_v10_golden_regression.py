"""Regression guard: V10 baseline must match frozen out_golden snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from validation.strategy_factory import make_factory

from v10.core.config import load_config
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS


def test_v10_baseline_matches_out_golden_snapshot() -> None:
    root = Path(__file__).resolve().parents[2]
    golden_dir = root / "out/golden" / "v10_baseline_frozen" / "2026-02-24"
    dataset = root / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
    config_path = root / "configs" / "frozen" / "v10_baseline.yaml"
    detail_path = golden_dir / "results" / "full_backtest_detail.json"

    if not detail_path.exists() or not dataset.exists() or not config_path.exists():
        pytest.skip("golden snapshot, dataset, or config is missing")

    golden = json.loads(detail_path.read_text(encoding="utf-8"))
    expected = golden["baseline"]

    cfg = load_config(config_path)
    factory = make_factory(cfg)
    feed = DataFeed(
        str(dataset),
        start="2019-01-01",
        end="2026-02-20",
        warmup_days=365,
    )

    for scenario in ("smart", "base", "harsh"):
        engine = BacktestEngine(
            feed=feed,
            strategy=factory(),
            cost=SCENARIOS[scenario],
            initial_cash=10_000.0,
            warmup_days=365,
            warmup_mode="no_trade",
            entry_nav_pre_cost=True,
        )
        result = engine.run()
        summary = result.summary
        target = expected[scenario]

        assert summary["final_nav_mid"] == pytest.approx(target["final_nav_mid"], abs=0.01)
        assert summary["max_drawdown_mid_pct"] == pytest.approx(target["max_drawdown_mid_pct"], abs=0.01)
        assert int(summary["trades"]) == int(target["trades"])
        assert len(result.fills) == int(target["fills"])
