"""Regression tests for validation report generation.

Covers:
- WFO low-power warning must not appear when WFO suite did not run
- Quality checks must reflect resolve_suites(), not raw config truthiness
- selection_bias import must not trigger research package warning
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from validation.config import ValidationConfig
from validation.decision import DecisionVerdict
from validation.report import generate_quality_checks_report
from validation.report import generate_validation_report
from validation.suites.base import SuiteResult


def _cfg(**overrides) -> ValidationConfig:
    base = dict(
        strategy_name="vtrend",
        baseline_name="vtrend",
        config_path=Path("/tmp/a.yaml"),
        baseline_config_path=Path("/tmp/b.yaml"),
        outdir=Path("/tmp/out"),
        dataset=Path("/tmp/data.csv"),
    )
    base.update(overrides)
    return ValidationConfig(**base)


class TestWFOWarningGuard:
    """WFO low-power warning must only appear when WFO actually ran."""

    def test_no_wfo_warning_when_suite_trade(self) -> None:
        """suite='trade' has no WFO — report must not emit WFO warning."""
        results = {
            "backtest": SuiteResult("backtest", "pass", data={"rows": []}),
            "trade_level": SuiteResult("trade_level", "pass", data={}),
        }
        config = _cfg(suite="trade")
        decision = DecisionVerdict(tag="PROMOTE", exit_code=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            content = path.read_text()
            assert "WFO low-power detected" not in content

    def test_no_wfo_warning_when_wfo_skipped(self) -> None:
        """WFO present but status='skip' — no warning."""
        results = {
            "backtest": SuiteResult("backtest", "pass", data={"rows": []}),
            "wfo": SuiteResult("wfo", "skip", data={}),
        }
        config = _cfg(suite="basic")
        decision = DecisionVerdict(tag="PROMOTE", exit_code=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            content = path.read_text()
            assert "WFO low-power detected" not in content

    def test_wfo_warning_shown_when_low_power(self) -> None:
        """WFO ran with low power — warning should appear via decision.warnings."""
        results = {
            "backtest": SuiteResult("backtest", "pass", data={"rows": []}),
            "wfo": SuiteResult("wfo", "pass", data={
                "summary": {
                    "n_windows_valid": 4,
                    "low_trade_windows_count": 0,
                    "stats_power_only": {"n_windows": 1},
                },
            }),
        }
        config = _cfg(suite="basic")
        # Low-power warning now flows through decision.warnings (set by runner)
        decision = DecisionVerdict(
            tag="PROMOTE",
            exit_code=0,
            warnings=[
                "Low-power WFO detected (power_windows=1, low_trade_ratio=0.000); "
                "trade-level bootstrap is primary evidence",
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            content = path.read_text()
            assert "Low-power WFO detected" in content

    def test_no_wfo_warning_when_sufficient_power(self) -> None:
        """WFO ran with sufficient power — no warning."""
        results = {
            "backtest": SuiteResult("backtest", "pass", data={"rows": []}),
            "wfo": SuiteResult("wfo", "pass", data={
                "summary": {
                    "n_windows_valid": 8,
                    "low_trade_windows_count": 0,
                    "stats_power_only": {"n_windows": 6},
                },
            }),
        }
        config = _cfg(suite="basic")
        decision = DecisionVerdict(tag="PROMOTE", exit_code=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_validation_report(results, decision, config, Path(tmpdir))
            content = path.read_text()
            assert "WFO low-power detected" not in content


class TestQualityChecksTriState:
    """Quality checks report must use resolved suite membership, not raw config truthiness."""

    def _parse_enabled(self, content: str) -> dict[str, str]:
        """Parse quality checks table → {label: 'on'|'off'}."""
        result = {}
        for line in content.split("\n"):
            if not line.startswith("|") or "---" in line or "Group" in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                label = parts[1]
                enabled = parts[2]
                if enabled in ("on", "off"):
                    result[label] = enabled
        return result

    def test_basic_suite_all_quality_off(self) -> None:
        """suite='basic' does not include quality suites — all should show 'off'."""
        config = _cfg(suite="basic")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_quality_checks_report({}, config, Path(tmpdir))
            enabled = self._parse_enabled(path.read_text())
            assert enabled.get("Data Integrity") == "off"
            assert enabled.get("Cost Sweep") == "off"
            assert enabled.get("Invariants") == "off"
            assert enabled.get("Churn Metrics") == "off"
            assert enabled.get("Regression Guard") == "off"

    def test_trade_suite_all_quality_off(self) -> None:
        """suite='trade' does not include quality suites — all should show 'off'."""
        config = _cfg(suite="trade")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_quality_checks_report({}, config, Path(tmpdir))
            enabled = self._parse_enabled(path.read_text())
            assert enabled.get("Data Integrity") == "off"
            assert enabled.get("Cost Sweep") == "off"
            assert enabled.get("Invariants") == "off"
            assert enabled.get("Churn Metrics") == "off"

    def test_all_suite_quality_on(self) -> None:
        """suite='all' includes quality suites — should show 'on'."""
        config = _cfg(suite="all")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_quality_checks_report({}, config, Path(tmpdir))
            enabled = self._parse_enabled(path.read_text())
            assert enabled.get("Data Integrity") == "on"
            assert enabled.get("Cost Sweep") == "on"
            assert enabled.get("Invariants") == "on"
            assert enabled.get("Churn Metrics") == "on"

    def test_basic_with_forced_data_integrity(self) -> None:
        """suite='basic' + data_integrity_check=True → Data Integrity shows 'on'."""
        config = _cfg(suite="basic", data_integrity_check=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_quality_checks_report({}, config, Path(tmpdir))
            enabled = self._parse_enabled(path.read_text())
            assert enabled.get("Data Integrity") == "on"
            # Others still off
            assert enabled.get("Cost Sweep") == "off"

    def test_all_with_forced_remove(self) -> None:
        """suite='all' + data_integrity_check=False → Data Integrity shows 'off'."""
        config = _cfg(suite="all", data_integrity_check=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_quality_checks_report({}, config, Path(tmpdir))
            enabled = self._parse_enabled(path.read_text())
            assert enabled.get("Data Integrity") == "off"
            # Others still on
            assert enabled.get("Cost Sweep") == "on"


class TestSelectionBiasImportBoundary:
    """selection_bias import must not pull research package."""

    def test_import_selection_bias_no_research_warning(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-W", "error::UserWarning",
                "-c",
                "from validation.suites.selection_bias import SelectionBiasSuite",
            ],
            capture_output=True,
            text=True,
            cwd="/var/www/trading-bots/btc-spot-dev",
            env={**__import__("os").environ, "_RESEARCH_CONTEXT": ""},
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Import triggered research warning.\nstderr: {result.stderr}\nstdout: {result.stdout}"
        )
