"""Tests for CLI --strategy/--baseline label vs YAML strategy name guard.

Regression: previously, --strategy and --baseline were labels only — they
were stored in ValidationConfig but never validated against the YAML config.
This could cause the report to say "candidate=X" while actually running Y.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from validation.config import ValidationConfig
from validation.runner import ValidationRunner


def _write_yaml(path: Path, strategy_name: str) -> None:
    config = {
        "strategy": {"name": strategy_name},
        "engine": {"warmup_mode": "no_trade"},
    }
    path.write_text(yaml.dump(config))


class TestCLILabelGuard:
    """ValidationRunner must fail fast if CLI label != YAML strategy name."""

    def test_matching_labels_accepted(self) -> None:
        """No error when CLI label matches YAML strategy name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            cand_yaml = tmpdir / "candidate.yaml"
            base_yaml = tmpdir / "baseline.yaml"
            _write_yaml(cand_yaml, "vtrend")
            _write_yaml(base_yaml, "vtrend")

            config = ValidationConfig(
                strategy_name="vtrend",
                baseline_name="vtrend",
                config_path=cand_yaml,
                baseline_config_path=base_yaml,
                outdir=tmpdir / "out",
                dataset=tmpdir / "data.csv",
                start="2020-01-01",
                end="2021-01-01",
                warmup_days=30,
                initial_cash=10_000.0,
                suite="basic",
                scenarios=["harsh"],
            )
            runner = ValidationRunner(config)
            # Should not raise during label check.
            # It will fail later (no data file), but the label check passes.
            with pytest.raises(Exception) as exc_info:
                runner.run()
            # Must NOT be our label mismatch error
            assert "does not match" not in str(exc_info.value)

    def test_candidate_label_mismatch_raises(self) -> None:
        """CLI --strategy=buy_and_hold but YAML says vtrend → ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            cand_yaml = tmpdir / "candidate.yaml"
            base_yaml = tmpdir / "baseline.yaml"
            _write_yaml(cand_yaml, "vtrend")
            _write_yaml(base_yaml, "vtrend")

            config = ValidationConfig(
                strategy_name="buy_and_hold",  # MISMATCH
                baseline_name="vtrend",
                config_path=cand_yaml,
                baseline_config_path=base_yaml,
                outdir=tmpdir / "out",
                dataset=tmpdir / "data.csv",
                start="2020-01-01",
                end="2021-01-01",
                warmup_days=30,
                initial_cash=10_000.0,
                suite="basic",
                scenarios=["harsh"],
            )
            runner = ValidationRunner(config)
            with pytest.raises(ValueError, match="does not match"):
                runner.run()

    def test_baseline_label_mismatch_raises(self) -> None:
        """CLI --baseline=buy_and_hold but YAML says vtrend → ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            cand_yaml = tmpdir / "candidate.yaml"
            base_yaml = tmpdir / "baseline.yaml"
            _write_yaml(cand_yaml, "vtrend")
            _write_yaml(base_yaml, "vtrend")

            config = ValidationConfig(
                strategy_name="vtrend",
                baseline_name="buy_and_hold",  # MISMATCH
                config_path=cand_yaml,
                baseline_config_path=base_yaml,
                outdir=tmpdir / "out",
                dataset=tmpdir / "data.csv",
                start="2020-01-01",
                end="2021-01-01",
                warmup_days=30,
                initial_cash=10_000.0,
                suite="basic",
                scenarios=["harsh"],
            )
            runner = ValidationRunner(config)
            with pytest.raises(ValueError, match="does not match"):
                runner.run()
