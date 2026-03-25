"""Unified YAML config loader — single source-of-truth for all CLIs.

Loads any strategy config YAML (e.g. configs/vtrend_e5_ema21_d1/vtrend_e5_ema21_d1_default.yaml)
into typed dataclasses with validation. Strategy params are validated against
the configured strategy dataclass fields.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from v10.core.types import SCENARIOS
from v10.strategies.v8_apex import V8ApexConfig
from v10.strategies.v11_hybrid import V11HybridConfig
from strategies.v12_emdd_ref_fix.strategy import V12EMDDRefFixConfig
from strategies.v13_add_throttle.strategy import V13AddThrottleConfig
from strategies.vtrend.strategy import VTrendConfig
from strategies.vtrend_sm.strategy import VTrendSMConfig
from strategies.vtrend_p.strategy import VTrendPConfig
from strategies.latch.strategy import LatchConfig
from strategies.vtrend_e5.strategy import VTrendE5Config
from strategies.vtrend_ema21.strategy import VTrendEma21Config
from strategies.vtrend_ema21_d1.strategy import VTrendEma21D1Config
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Config
from strategies.vtrend_x0.strategy import VTrendX0Config
from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig
from strategies.vtrend_x0_volsize.strategy import VTrendX0VolsizeConfig
from strategies.vtrend_x2.strategy import VTrendX2Config
from strategies.vtrend_x5.strategy import VTrendX5Config
from strategies.vtrend_x6.strategy import VTrendX6Config
from strategies.vtrend_x7.strategy import VTrendX7Config
from strategies.vtrend_x8.strategy import VTrendX8Config
from strategies.vtrend_vp1.strategy import VP1Config
from strategies.vtrend_vp1_e5exit.strategy import VP1E5ExitConfig
from strategies.vtrend_vp1_full.strategy import VP1FullConfig
from strategies.vtrend_qvdo.strategy import VTrendQVDOConfig


# ---------------------------------------------------------------------------
# Valid strategy param names (computed once)
# ---------------------------------------------------------------------------

_V8_FIELDS = {f.name for f in dataclasses.fields(V8ApexConfig)}
_V11_FIELDS = {f.name for f in dataclasses.fields(V11HybridConfig)}
_V12_FIELDS = {f.name for f in dataclasses.fields(V12EMDDRefFixConfig)}
_V13_FIELDS = {f.name for f in dataclasses.fields(V13AddThrottleConfig)}
_VTREND_FIELDS = {f.name for f in dataclasses.fields(VTrendConfig)}
_VTREND_E5_FIELDS = {f.name for f in dataclasses.fields(VTrendE5Config)}
_VTREND_EMA21_FIELDS = {f.name for f in dataclasses.fields(VTrendEma21Config)}
_VTREND_EMA21_D1_FIELDS = {f.name for f in dataclasses.fields(VTrendEma21D1Config)}
_VTREND_E5_EMA21_D1_FIELDS = {f.name for f in dataclasses.fields(VTrendE5Ema21D1Config)}
_VTREND_SM_FIELDS = {f.name for f in dataclasses.fields(VTrendSMConfig)}
_VTREND_P_FIELDS = {f.name for f in dataclasses.fields(VTrendPConfig)}
_LATCH_FIELDS = {f.name for f in dataclasses.fields(LatchConfig)}
_VTREND_X0_FIELDS = {f.name for f in dataclasses.fields(VTrendX0Config)}
_VTREND_X0_E5EXIT_FIELDS = {f.name for f in dataclasses.fields(VTrendX0E5ExitConfig)}
_VTREND_X0_VOLSIZE_FIELDS = {f.name for f in dataclasses.fields(VTrendX0VolsizeConfig)}
_VTREND_X2_FIELDS = {f.name for f in dataclasses.fields(VTrendX2Config)}
_VTREND_X5_FIELDS = {f.name for f in dataclasses.fields(VTrendX5Config)}
_VTREND_X6_FIELDS = {f.name for f in dataclasses.fields(VTrendX6Config)}
_VTREND_X7_FIELDS = {f.name for f in dataclasses.fields(VTrendX7Config)}
_VTREND_X8_FIELDS = {f.name for f in dataclasses.fields(VTrendX8Config)}
_VP1_FIELDS = {f.name for f in dataclasses.fields(VP1Config)}
_VP1_E5EXIT_FIELDS = {f.name for f in dataclasses.fields(VP1E5ExitConfig)}
_VP1_FULL_FIELDS = {f.name for f in dataclasses.fields(VP1FullConfig)}
_VTREND_QVDO_FIELDS = {f.name for f in dataclasses.fields(VTrendQVDOConfig)}
_KNOWN_STRATEGIES = {
    "v8_apex",
    "buy_and_hold",
    "v11_hybrid",
    "v12_emdd_ref_fix",
    "v13_add_throttle",
    "vtrend",
    "vtrend_e5",
    "vtrend_ema21",
    "vtrend_ema21_d1",
    "vtrend_sm",
    "vtrend_p",
    "latch",
    "vtrend_e5_ema21_d1",
    "vtrend_x0",
    "vtrend_x0_e5exit",
    "vtrend_x0_volsize",
    "vtrend_x2",
    "vtrend_x5",
    "vtrend_x6",
    "vtrend_x7",
    "vtrend_x8",
    "vtrend_vp1",
    "vtrend_vp1_e5exit",
    "vtrend_vp1_full",
    "vtrend_qvdo",
}
_TOP_LEVEL_FIELDS = {"engine", "strategy", "risk"}


# ---------------------------------------------------------------------------
# Config dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EngineConfig:
    symbol: str = "BTCUSDT"
    timeframe_h4: str = "4h"
    timeframe_d1: str = "1d"
    warmup_days: int = 365
    warmup_mode: str = "no_trade"
    scenario_eval: str = "base"
    initial_cash: float = 10_000.0


@dataclass
class StrategyConfig:
    name: str = "v8_apex"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskConfig:
    max_total_exposure: float = 1.0
    min_notional_usdt: float = 10.0
    kill_switch_dd_total: float = 0.45
    max_daily_orders: int = 5


@dataclass
class LiveConfig:
    engine: EngineConfig = field(default_factory=EngineConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)


_ENGINE_FIELDS = {f.name for f in dataclasses.fields(EngineConfig)}
_RISK_FIELDS = {f.name for f in dataclasses.fields(RiskConfig)}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_config(path: str | Path) -> LiveConfig:
    """Load a YAML config file and return a validated LiveConfig."""
    path = Path(path)
    with open(path) as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Config file must be a YAML mapping, got {type(raw).__name__}")

    unknown_keys = _unknown_yaml_keys(raw)
    if unknown_keys:
        keys = "\n  - ".join(unknown_keys)
        raise ValueError(
            "Config contains unknown keys:\n"
            f"  - {keys}"
        )

    # Engine
    eng_raw = raw.get("engine", {})
    engine = EngineConfig(**{k: v for k, v in eng_raw.items() if k in _ENGINE_FIELDS})

    # Strategy — split name from params
    strat_raw = dict(raw.get("strategy", {}))
    strat_name = strat_raw.pop("name", "v8_apex")
    strategy = StrategyConfig(name=strat_name, params=strat_raw)

    # Risk
    risk_raw = raw.get("risk", {})
    risk = RiskConfig(**{k: v for k, v in risk_raw.items() if k in _RISK_FIELDS})

    config = LiveConfig(engine=engine, strategy=strategy, risk=risk)

    errors = validate_config(config)
    if errors:
        raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))

    return config


def _unknown_yaml_keys(raw: dict[str, Any]) -> list[str]:
    unknown: list[str] = []

    for key in sorted(set(raw) - _TOP_LEVEL_FIELDS):
        unknown.append(str(key))

    engine_raw = raw.get("engine", {}) or {}
    if isinstance(engine_raw, dict):
        for key in sorted(set(engine_raw) - _ENGINE_FIELDS):
            unknown.append(f"engine.{key}")

    risk_raw = raw.get("risk", {}) or {}
    if isinstance(risk_raw, dict):
        for key in sorted(set(risk_raw) - _RISK_FIELDS):
            unknown.append(f"risk.{key}")

    strategy_raw = raw.get("strategy", {}) or {}
    if isinstance(strategy_raw, dict):
        strategy_name = strategy_raw.get("name", "v8_apex")
        strategy_fields_by_name = {
            "v8_apex": _V8_FIELDS,
            "v11_hybrid": _V11_FIELDS,
            "v12_emdd_ref_fix": _V12_FIELDS,
            "v13_add_throttle": _V13_FIELDS,
            "vtrend": _VTREND_FIELDS,
            "vtrend_e5": _VTREND_E5_FIELDS,
            "vtrend_ema21": _VTREND_EMA21_FIELDS,
            "vtrend_ema21_d1": _VTREND_EMA21_D1_FIELDS,
            "vtrend_e5_ema21_d1": _VTREND_E5_EMA21_D1_FIELDS,
            "vtrend_sm": _VTREND_SM_FIELDS,
            "vtrend_p": _VTREND_P_FIELDS,
            "latch": _LATCH_FIELDS,
            "vtrend_x0": _VTREND_X0_FIELDS,
            "vtrend_x0_e5exit": _VTREND_X0_E5EXIT_FIELDS,
            "vtrend_x0_volsize": _VTREND_X0_VOLSIZE_FIELDS,
            "vtrend_x2": _VTREND_X2_FIELDS,
            "vtrend_x5": _VTREND_X5_FIELDS,
            "vtrend_x6": _VTREND_X6_FIELDS,
            "vtrend_x7": _VTREND_X7_FIELDS,
            "vtrend_x8": _VTREND_X8_FIELDS,
            "vtrend_vp1": _VP1_FIELDS,
            "vtrend_vp1_e5exit": _VP1_E5EXIT_FIELDS,
            "vtrend_vp1_full": _VP1_FULL_FIELDS,
            "vtrend_qvdo": _VTREND_QVDO_FIELDS,
            "buy_and_hold": set(),
        }
        allowed_strategy_fields = {"name"} | strategy_fields_by_name.get(
            strategy_name, set()
        )
        for key in sorted(set(strategy_raw) - allowed_strategy_fields):
            unknown.append(f"strategy.{key}")

    return unknown


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config(config: LiveConfig) -> list[str]:
    """Validate config values. Returns list of error strings (empty = valid)."""
    errors: list[str] = []

    # Engine
    if config.engine.warmup_mode not in ("no_trade", "allow_trade"):
        errors.append(
            f"engine.warmup_mode must be 'no_trade' or 'allow_trade', "
            f"got '{config.engine.warmup_mode}'"
        )
    if config.engine.scenario_eval not in SCENARIOS:
        errors.append(
            f"engine.scenario_eval must be one of {sorted(SCENARIOS)}, "
            f"got '{config.engine.scenario_eval}'"
        )
    if config.engine.warmup_days < 1:
        errors.append(f"engine.warmup_days must be >= 1, got {config.engine.warmup_days}")
    if config.engine.initial_cash <= 0:
        errors.append(f"engine.initial_cash must be > 0, got {config.engine.initial_cash}")

    # Strategy
    if config.strategy.name not in _KNOWN_STRATEGIES:
        errors.append(
            f"strategy.name must be one of {sorted(_KNOWN_STRATEGIES)}, "
            f"got '{config.strategy.name}'"
        )

    # Validate strategy params against config fields
    if config.strategy.name == "v8_apex":
        for key in config.strategy.params:
            if key not in _V8_FIELDS:
                errors.append(f"strategy.{key} is not a valid V8ApexConfig field")
    elif config.strategy.name == "v11_hybrid":
        for key in config.strategy.params:
            if key not in _V11_FIELDS:
                errors.append(f"strategy.{key} is not a valid V11HybridConfig field")
    elif config.strategy.name == "v12_emdd_ref_fix":
        for key in config.strategy.params:
            if key not in _V12_FIELDS:
                errors.append(f"strategy.{key} is not a valid V12EMDDRefFixConfig field")
    elif config.strategy.name == "v13_add_throttle":
        for key in config.strategy.params:
            if key not in _V13_FIELDS:
                errors.append(f"strategy.{key} is not a valid V13AddThrottleConfig field")
    elif config.strategy.name == "vtrend":
        for key in config.strategy.params:
            if key not in _VTREND_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendConfig field")
    elif config.strategy.name == "vtrend_e5":
        for key in config.strategy.params:
            if key not in _VTREND_E5_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendE5Config field")
    elif config.strategy.name == "vtrend_ema21":
        for key in config.strategy.params:
            if key not in _VTREND_EMA21_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendEma21Config field")
    elif config.strategy.name == "vtrend_ema21_d1":
        for key in config.strategy.params:
            if key not in _VTREND_EMA21_D1_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendEma21D1Config field")
    elif config.strategy.name == "vtrend_e5_ema21_d1":
        for key in config.strategy.params:
            if key not in _VTREND_E5_EMA21_D1_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendE5Ema21D1Config field")
    elif config.strategy.name == "vtrend_sm":
        for key in config.strategy.params:
            if key not in _VTREND_SM_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendSMConfig field")
    elif config.strategy.name == "vtrend_p":
        for key in config.strategy.params:
            if key not in _VTREND_P_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendPConfig field")
    elif config.strategy.name == "latch":
        for key in config.strategy.params:
            if key not in _LATCH_FIELDS:
                errors.append(f"strategy.{key} is not a valid LatchConfig field")
    elif config.strategy.name == "vtrend_x0":
        for key in config.strategy.params:
            if key not in _VTREND_X0_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX0Config field")
    elif config.strategy.name == "vtrend_x0_e5exit":
        for key in config.strategy.params:
            if key not in _VTREND_X0_E5EXIT_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX0E5ExitConfig field")
    elif config.strategy.name == "vtrend_x0_volsize":
        for key in config.strategy.params:
            if key not in _VTREND_X0_VOLSIZE_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX0VolsizeConfig field")
    elif config.strategy.name == "vtrend_x2":
        for key in config.strategy.params:
            if key not in _VTREND_X2_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX2Config field")
    elif config.strategy.name == "vtrend_x5":
        for key in config.strategy.params:
            if key not in _VTREND_X5_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX5Config field")
    elif config.strategy.name == "vtrend_x6":
        for key in config.strategy.params:
            if key not in _VTREND_X6_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX6Config field")
    elif config.strategy.name == "vtrend_x7":
        for key in config.strategy.params:
            if key not in _VTREND_X7_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX7Config field")
    elif config.strategy.name == "vtrend_x8":
        for key in config.strategy.params:
            if key not in _VTREND_X8_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendX8Config field")
    elif config.strategy.name == "vtrend_vp1":
        for key in config.strategy.params:
            if key not in _VP1_FIELDS:
                errors.append(f"strategy.{key} is not a valid VP1Config field")
    elif config.strategy.name == "vtrend_vp1_e5exit":
        for key in config.strategy.params:
            if key not in _VP1_E5EXIT_FIELDS:
                errors.append(f"strategy.{key} is not a valid VP1E5ExitConfig field")
    elif config.strategy.name == "vtrend_vp1_full":
        for key in config.strategy.params:
            if key not in _VP1_FULL_FIELDS:
                errors.append(f"strategy.{key} is not a valid VP1FullConfig field")
    elif config.strategy.name == "vtrend_qvdo":
        for key in config.strategy.params:
            if key not in _VTREND_QVDO_FIELDS:
                errors.append(f"strategy.{key} is not a valid VTrendQVDOConfig field")

    # Risk
    if not (0 < config.risk.max_total_exposure <= 1.0):
        errors.append(
            f"risk.max_total_exposure must be in (0, 1.0], "
            f"got {config.risk.max_total_exposure}"
        )
    if not (0 < config.risk.kill_switch_dd_total < 1.0):
        errors.append(
            f"risk.kill_switch_dd_total must be in (0, 1.0), "
            f"got {config.risk.kill_switch_dd_total}"
        )
    if config.risk.min_notional_usdt <= 0:
        errors.append(
            f"risk.min_notional_usdt must be > 0, got {config.risk.min_notional_usdt}"
        )
    if config.risk.max_daily_orders < 1:
        errors.append(
            f"risk.max_daily_orders must be >= 1, got {config.risk.max_daily_orders}"
        )

    return errors


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def config_to_dict(config: LiveConfig) -> dict[str, Any]:
    """Convert LiveConfig to a plain dict for JSON serialization."""
    return dataclasses.asdict(config)
