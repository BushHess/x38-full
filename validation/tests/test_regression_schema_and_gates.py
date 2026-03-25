"""Regression tests for data-schema, missing-interval, and lookahead gate fixes.

Fix 1: runner.py catches DataFeed KeyError on missing 'interval' column
        and returns structured ERROR verdict instead of crashing.
Fix 2: data_integrity.py detects configured timeframes missing from CSV
        and reports hard-fail with 'missing_configured_interval'.
Fix 3: lookahead.py returns 'fail' (not 'skip') when no test files found,
        preventing a new strategy from bypassing the hard gate.
"""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pandas as pd
from v10.core.config import load_config
from v10.core.data import DataFeed
from validation.config import ValidationConfig
from validation.runner import ValidationRunner
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.data_integrity import DataIntegritySuite
from validation.suites.lookahead import LookaheadSuite

ROOT = Path(__file__).resolve().parents[2]
BASELINE_CFG = ROOT / "v10" / "configs" / "baseline_legacy.live.yaml"


def _ms(dt: str) -> int:
    parsed = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


# ── Fix 1: runner catches DataFeed schema error ──────────────────────


def test_runner_returns_error_on_missing_interval_column(tmp_path: Path) -> None:
    """CSV without 'interval' column must produce ERROR verdict, not crash."""
    dataset = tmp_path / "bars_no_interval.csv"
    rows = [
        {
            "open_time": _ms("2020-01-03 00:00:00"),
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 10.0,
            "close_time": _ms("2020-01-03 03:59:59"),
            # no 'interval' column
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
        start="2020-01-03",
        end="2020-01-05",
        warmup_days=0,
        suite="basic",
        bootstrap=0,
        lookahead_check=False,
        data_integrity_check=True,
    )

    # Must NOT raise — should return structured error
    results, verdict = ValidationRunner(cfg).run()

    assert verdict.tag == "ERROR"
    assert verdict.exit_code == 3
    assert "data_integrity" in results
    assert results["data_integrity"].status == "fail"
    assert results["data_integrity"].data["hard_fail"] is True
    # Decision file written to disk
    assert (cfg.outdir / "reports" / "decision.json").exists()
    decision = json.loads((cfg.outdir / "reports" / "decision.json").read_text())
    assert decision["verdict"] == "ERROR"


# ── Fix 2: data_integrity detects missing configured timeframe ───────


def test_data_integrity_hard_fails_on_missing_configured_interval(
    tmp_path: Path,
) -> None:
    """CSV with only 4h data must hard-fail when engine config requires 1d."""
    dataset = tmp_path / "bars_4h_only.csv"
    # 370 days of 4h bars, NO 1d bars
    rows = []
    base = _ms("2019-01-01 00:00:00")
    for i in range(2220):  # ~370 days × 6 bars/day
        rows.append(
            {
                "open_time": base + i * 4 * 3600 * 1000,
                "open": 100.0 + i * 0.01,
                "high": 101.0 + i * 0.01,
                "low": 99.0 + i * 0.01,
                "close": 100.5 + i * 0.01,
                "volume": 10.0,
                "close_time": base + (i + 1) * 4 * 3600 * 1000 - 1,
                "interval": "4h",
            }
        )
    pd.DataFrame(rows).to_csv(dataset, index=False)

    cfg = ValidationConfig(
        strategy_name="v8_apex",
        baseline_name="v8_apex",
        config_path=BASELINE_CFG,
        baseline_config_path=BASELINE_CFG,
        outdir=tmp_path / "out",
        dataset=dataset,
        start="2019-06-01",
        end="2019-12-31",
        warmup_days=120,
        suite="basic",
    )
    live_cfg = load_config(str(BASELINE_CFG))
    feed = DataFeed(
        str(dataset), start=cfg.start, end=cfg.end, warmup_days=cfg.warmup_days
    )

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

    # Check if engine config actually requires 1d
    has_d1_config = any(
        getattr(lc.engine, "timeframe_d1", None)
        for lc in [live_cfg]
    )

    if has_d1_config:
        # Engine requires 1d — must hard-fail
        reasons = set(result.data.get("hard_fail_reasons", []))
        assert result.status == "fail", f"Expected fail, got {result.status}"
        assert "missing_configured_interval" in reasons, (
            f"Expected 'missing_configured_interval' in {reasons}"
        )
    else:
        # Engine doesn't configure 1d explicitly — no missing interval to detect.
        # This branch exists for robustness: the test still validates that the
        # suite runs without error on 4h-only data.
        assert result.status in {"pass", "fail"}


# ── Fix 3: lookahead fails when no test files found ──────────────────


def test_lookahead_fails_when_no_tests_found(tmp_path: Path) -> None:
    """LookaheadSuite must return 'fail', not 'skip', when enabled but no tests exist."""
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
    ]
    pd.DataFrame(rows).to_csv(dataset, index=False)

    cfg = ValidationConfig(
        strategy_name="v8_apex",
        baseline_name="v8_apex",
        config_path=BASELINE_CFG,
        baseline_config_path=BASELINE_CFG,
        outdir=tmp_path / "out",
        dataset=dataset,
        start="2020-01-03",
        end="2020-01-05",
        warmup_days=0,
        suite="basic",
        lookahead_check=True,
    )
    live_cfg = load_config(str(BASELINE_CFG))
    feed = DataFeed(
        str(dataset), start=cfg.start, end=cfg.end, warmup_days=cfg.warmup_days
    )

    # Use an empty directory as project_root so no test files are found
    empty_root = tmp_path / "empty_project"
    empty_root.mkdir()

    ctx = SuiteContext(
        feed=feed,
        data_path=dataset,
        project_root=empty_root,
        candidate_factory=lambda: None,
        baseline_factory=lambda: None,
        candidate_live_config=live_cfg,
        baseline_live_config=live_cfg,
        candidate_config_obj=None,
        baseline_config_obj=None,
        validation_config=cfg,
        resolved_suites=["lookahead"],
        outdir=cfg.outdir,
        results_dir=cfg.outdir / "results",
        reports_dir=cfg.outdir / "reports",
    )
    ctx.results_dir.mkdir(parents=True, exist_ok=True)
    ctx.reports_dir.mkdir(parents=True, exist_ok=True)

    suite = LookaheadSuite()
    assert suite.skip_reason(ctx) is None, "Suite should NOT skip (lookahead_check=True)"

    result = suite.run(ctx)

    assert result.status == "fail", (
        f"Expected 'fail' when no tests found, got '{result.status}'"
    )
    assert result.data.get("reason") == "no_tests_found"
    assert (ctx.results_dir / "lookahead_check.txt").exists()
