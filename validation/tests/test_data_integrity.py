"""Unit tests for data-integrity suite and decision integration."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pandas as pd
from v10.core.config import load_config
from v10.core.data import DataFeed
from validation.config import ValidationConfig
from validation.decision import evaluate_decision
from validation.runner import ValidationRunner
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.data_integrity import DataIntegritySuite

ROOT = Path(__file__).resolve().parents[2]
BASELINE_CFG = ROOT / "v10" / "configs" / "baseline_legacy.live.yaml"


def _ms(dt: str) -> int:
    parsed = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


def test_data_integrity_hard_fail_reasons(tmp_path: Path) -> None:
    dataset = tmp_path / "bars.csv"
    rows = [
        {
            "open_time": _ms("2020-01-03 00:00:00"),
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
            "close_time": _ms("2020-01-03 03:59:59"),
            "interval": "4h",
        },
        {
            "open_time": _ms("2020-01-03 04:00:00"),
            "open": 101.0,
            "high": 101.5,
            "low": 100.0,
            "close": 100.5,
            "volume": 8.0,
            "close_time": _ms("2020-01-03 07:59:59"),
            "interval": "4h",
        },
        {
            "open_time": _ms("2020-01-03 04:00:00"),  # duplicate timestamp
            "open": 100.0,
            "high": 99.0,  # invalid OHLC: high < open
            "low": 101.0,  # invalid OHLC: low > open/close and high < low
            "close": 100.0,
            "volume": 5.0,
            "close_time": _ms("2020-01-03 07:59:59"),
            "interval": "4h",
        },
        {
            "open_time": _ms("2020-01-03 16:00:00"),  # gap from 04:00 -> 16:00
            "open": 101.0,
            "high": 103.0,
            "low": 100.5,
            "close": 102.5,
            "volume": 11.0,
            "close_time": _ms("2020-01-03 19:59:59"),
            "interval": "4h",
        },
        {
            "open_time": _ms("2020-01-03 00:00:00"),
            "open": 100.0,
            "high": 105.0,
            "low": 95.0,
            "close": 104.0,
            "volume": 120.0,
            "close_time": _ms("2020-01-03 23:59:59"),
            "interval": "1d",
        },
    ]
    pd.DataFrame(rows).to_csv(dataset, index=False)

    cfg = ValidationConfig(
        strategy_name="v8_apex",
        baseline_name="v8_apex",
        config_path=BASELINE_CFG,
        baseline_config_path=BASELINE_CFG,
        outdir=tmp_path / "out",
        dataset=dataset,
        start="2020-01-04",
        end="2020-01-05",
        warmup_days=3,
        suite="basic",
    )
    live_cfg = load_config(str(BASELINE_CFG))
    feed = DataFeed(str(dataset), start=cfg.start, end=cfg.end, warmup_days=cfg.warmup_days)

    ctx = SuiteContext(
        feed=feed,
        data_path=dataset,
        project_root=ROOT,
        candidate_factory=lambda: None,
        baseline_factory=lambda: None,
        candidate_live_config=live_cfg,
        baseline_live_config=live_cfg,
        candidate_config_obj=None,
        baseline_config_obj=None,
        validation_config=cfg,
        resolved_suites=["data_integrity"],
        outdir=cfg.outdir,
        results_dir=cfg.outdir / "results",
        reports_dir=cfg.outdir / "reports",
    )
    ctx.results_dir.mkdir(parents=True, exist_ok=True)
    ctx.reports_dir.mkdir(parents=True, exist_ok=True)

    result = DataIntegritySuite().run(ctx)
    reasons = set(result.data.get("hard_fail_reasons", []))

    assert result.status == "fail"
    assert "duplicate_timestamps" in reasons
    assert "ohlc_invalid_rows" in reasons
    assert "missing_bars_pct_exceeds_threshold" in reasons
    assert "warmup_missing_severe" in reasons
    assert (ctx.results_dir / "data_integrity.json").exists()
    assert (ctx.results_dir / "data_integrity_issues.csv").exists()


def test_decision_returns_exit3_on_data_integrity_hard_fail() -> None:
    verdict = evaluate_decision(
        {
            "data_integrity": SuiteResult(
                name="data_integrity",
                status="fail",
                data={
                    "hard_fail": True,
                    "hard_fail_reasons": ["duplicate_timestamps"],
                    "counts": {
                        "duplicate_timestamps": 3,
                        "ohlc_invalid_rows": 1,
                        "max_missing_bars_pct_estimated": 5.0,
                    },
                },
            )
        }
    )

    assert verdict.exit_code == 3
    assert verdict.tag == "ERROR"
    assert "duplicate_timestamps" in verdict.failures


def test_runner_short_circuits_after_data_integrity_hard_fail(tmp_path: Path) -> None:
    dataset = tmp_path / "bars_bad.csv"
    rows = [
        {
            "open_time": _ms("2020-01-03 00:00:00"),
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
            "close_time": _ms("2020-01-03 03:59:59"),
            "interval": "4h",
        },
        {
            "open_time": _ms("2020-01-03 04:00:00"),
            "open": 101.0,
            "high": 101.5,
            "low": 100.0,
            "close": 100.5,
            "volume": 8.0,
            "close_time": _ms("2020-01-03 07:59:59"),
            "interval": "4h",
        },
        {
            "open_time": _ms("2020-01-03 04:00:00"),
            "open": 100.0,
            "high": 99.0,
            "low": 101.0,
            "close": 100.0,
            "volume": 5.0,
            "close_time": _ms("2020-01-03 07:59:59"),
            "interval": "4h",
        },
    ]
    pd.DataFrame(rows).to_csv(dataset, index=False)

    cfg = ValidationConfig(
        strategy_name="v8_apex",
        baseline_name="v8_apex",
        config_path=BASELINE_CFG,
        baseline_config_path=BASELINE_CFG,
        outdir=tmp_path / "out",
        dataset=dataset,
        start="2020-01-04",
        end="2020-01-05",
        warmup_days=3,
        suite="basic",
        bootstrap=0,
        lookahead_check=False,
        data_integrity_check=True,
    )

    results, verdict = ValidationRunner(cfg).run()
    assert verdict.exit_code == 3
    assert set(results.keys()) == {"data_integrity"}
    assert results["data_integrity"].status == "fail"
    assert (cfg.outdir / "results" / "data_integrity.json").exists()
    assert not (cfg.outdir / "results" / "full_backtest_summary.csv").exists()

    decision = json.loads((cfg.outdir / "reports" / "decision.json").read_text())
    assert "warnings" in decision
    assert "errors" in decision
    assert any(str(item).startswith("data_integrity:") for item in decision["errors"])
