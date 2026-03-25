"""Tests for v10.core.config — YAML config loader and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from v10.core.config import load_config, validate_config, config_to_dict, LiveConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_YAML = {
    "engine": {
        "symbol": "BTCUSDT",
        "warmup_days": 365,
        "warmup_mode": "no_trade",
        "scenario_eval": "base",
        "initial_cash": 10_000.0,
    },
    "strategy": {
        "name": "v8_apex",
        "emergency_ref": "pre_cost_legacy",
        "rsi_method": "wilder",
        "entry_cooldown_bars": 3,
    },
    "risk": {
        "max_total_exposure": 1.0,
        "min_notional_usdt": 10,
        "kill_switch_dd_total": 0.45,
        "max_daily_orders": 5,
    },
}


def _write_yaml(tmp_path: Path, data: dict, name: str = "test.yaml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.dump(data))
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConfig:
    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Load a valid config and verify all fields parsed correctly."""
        path = _write_yaml(tmp_path, _VALID_YAML)
        config = load_config(path)

        assert config.engine.symbol == "BTCUSDT"
        assert config.engine.warmup_days == 365
        assert config.engine.warmup_mode == "no_trade"
        assert config.engine.scenario_eval == "base"
        assert config.engine.initial_cash == 10_000.0
        assert config.strategy.name == "v8_apex"
        assert config.risk.max_total_exposure == 1.0
        assert config.risk.kill_switch_dd_total == 0.45

    def test_strategy_params_extracted(self, tmp_path: Path) -> None:
        """Strategy name separated from params dict."""
        path = _write_yaml(tmp_path, _VALID_YAML)
        config = load_config(path)

        assert config.strategy.name == "v8_apex"
        assert "name" not in config.strategy.params
        assert config.strategy.params["emergency_ref"] == "pre_cost_legacy"
        assert config.strategy.params["rsi_method"] == "wilder"
        assert config.strategy.params["entry_cooldown_bars"] == 3

    def test_reject_invalid_scenario(self, tmp_path: Path) -> None:
        """scenario_eval not in SCENARIOS -> ValueError."""
        data = {**_VALID_YAML, "engine": {**_VALID_YAML["engine"], "scenario_eval": "invalid"}}
        path = _write_yaml(tmp_path, data)

        with pytest.raises(ValueError, match="scenario_eval"):
            load_config(path)

    def test_reject_invalid_warmup_mode(self, tmp_path: Path) -> None:
        """warmup_mode not in valid set -> ValueError."""
        data = {**_VALID_YAML, "engine": {**_VALID_YAML["engine"], "warmup_mode": "bad"}}
        path = _write_yaml(tmp_path, data)

        with pytest.raises(ValueError, match="warmup_mode"):
            load_config(path)

    def test_reject_bad_risk_values(self, tmp_path: Path) -> None:
        """kill_switch_dd_total out of range -> ValueError."""
        data = {**_VALID_YAML, "risk": {**_VALID_YAML["risk"], "kill_switch_dd_total": 1.5}}
        path = _write_yaml(tmp_path, data)

        with pytest.raises(ValueError, match="kill_switch_dd_total"):
            load_config(path)

    def test_reject_unknown_strategy_param(self, tmp_path: Path) -> None:
        """Unknown field in strategy section -> ValueError."""
        data = {
            **_VALID_YAML,
            "strategy": {**_VALID_YAML["strategy"], "totally_fake_field": 42},
        }
        path = _write_yaml(tmp_path, data)

        with pytest.raises(ValueError, match="totally_fake_field"):
            load_config(path)

    def test_config_to_dict(self, tmp_path: Path) -> None:
        """config_to_dict returns a plain dict with correct structure."""
        path = _write_yaml(tmp_path, _VALID_YAML)
        config = load_config(path)
        d = config_to_dict(config)

        assert isinstance(d, dict)
        assert "engine" in d
        assert "strategy" in d
        assert "risk" in d
        assert d["engine"]["warmup_days"] == 365
        assert d["strategy"]["name"] == "v8_apex"
        assert d["strategy"]["params"]["rsi_method"] == "wilder"
        assert d["risk"]["kill_switch_dd_total"] == 0.45

    def test_load_real_config(self) -> None:
        """Load the actual baseline_legacy.live.yaml from configs/."""
        config_path = Path(__file__).resolve().parents[1] / "configs" / "baseline_legacy.live.yaml"
        if not config_path.exists():
            pytest.skip("configs/baseline_legacy.live.yaml not found")

        config = load_config(config_path)
        assert config.strategy.name == "v8_apex"
        assert config.strategy.params["emergency_ref"] == "pre_cost_legacy"
        assert config.strategy.params["rsi_method"] == "wilder"
