"""Tests for YAML candidate loading, config builder, and matrix runner."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from v10.research.candidates import (
    CandidateSpec,
    build_config,
    load_candidates,
)
from v10.strategies.v8_apex import V8ApexConfig


class TestLoadCandidates:
    def _write_yaml(self, data: dict, tmpdir: Path) -> Path:
        p = tmpdir / "candidates.yaml"
        with open(p, "w") as f:
            yaml.dump(data, f)
        return p

    def test_load_basic(self, tmp_path: Path) -> None:
        data = {
            "candidates": [
                {"name": "apex_default", "description": "defaults", "params": {}},
                {
                    "name": "wide_trail",
                    "description": "Wide trail",
                    "params": {"trail_atr_mult": 5.0, "vdr_fast_period": 12},
                },
            ]
        }
        p = self._write_yaml(data, tmp_path)
        specs = load_candidates(p)
        assert len(specs) == 2
        assert specs[0].name == "apex_default"
        assert specs[1].params["trail_atr_mult"] == 5.0

    def test_invalid_param_name(self, tmp_path: Path) -> None:
        data = {
            "candidates": [
                {"name": "bad", "params": {"nonexistent_field": 99}},
            ]
        }
        p = self._write_yaml(data, tmp_path)
        with pytest.raises(ValueError, match="unknown param"):
            load_candidates(p)

    def test_param_ranges_too_many(self, tmp_path: Path) -> None:
        """param_ranges with > 8 keys should be rejected."""
        ranges = {f"d1_ema_fast": [50]}  # will add 8 more
        # Create 9 unique valid field names
        fields = [
            "d1_ema_fast", "d1_ema_slow", "vdr_fast_period", "vdr_slow_period",
            "hma_period", "roc_period", "atr_fast_period", "atr_slow_period",
            "rsi_period",
        ]
        ranges = {f: [1, 2] for f in fields}
        data = {
            "candidates": [
                {"name": "big", "params": {}, "param_ranges": ranges},
            ]
        }
        p = self._write_yaml(data, tmp_path)
        with pytest.raises(ValueError, match="max 8"):
            load_candidates(p)

    def test_empty_candidates_raises(self, tmp_path: Path) -> None:
        data = {"candidates": []}
        p = self._write_yaml(data, tmp_path)
        with pytest.raises(ValueError, match="No candidates"):
            load_candidates(p)

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        data = {"candidates": [{"params": {}}]}
        p = self._write_yaml(data, tmp_path)
        with pytest.raises(ValueError, match="name"):
            load_candidates(p)


class TestBuildConfig:
    def test_default(self) -> None:
        cfg = build_config({})
        assert cfg.trail_atr_mult == V8ApexConfig().trail_atr_mult

    def test_override(self) -> None:
        cfg = build_config({"trail_atr_mult": 6.0, "vdr_fast_period": 10})
        assert cfg.trail_atr_mult == 6.0
        assert cfg.vdr_fast_period == 10

    def test_invalid_field_raises(self) -> None:
        with pytest.raises(ValueError, match="no field"):
            build_config({"fake_field": 1})
