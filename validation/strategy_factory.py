"""Strategy-agnostic factory: YAML config → Strategy instances."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from v10.core.config import LiveConfig
from v10.strategies.base import Strategy
from v10.strategies.buy_and_hold import BuyAndHold
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy
from validation.config_audit import AccessTracker
from validation.config_audit import ConfigProxy
from strategies.v12_emdd_ref_fix.strategy import (
    V12EMDDRefFixConfig,
    V12EMDDRefFixStrategy,
)
from strategies.v13_add_throttle.strategy import (
    V13AddThrottleConfig,
    V13AddThrottleStrategy,
)
from strategies.vtrend.strategy import (
    VTrendConfig,
    VTrendStrategy,
)
from strategies.vtrend_sm.strategy import (
    VTrendSMConfig,
    VTrendSMStrategy,
)
from strategies.vtrend_p.strategy import (
    VTrendPConfig,
    VTrendPStrategy,
)
from strategies.latch.strategy import (
    LatchConfig,
    LatchStrategy,
)
from strategies.vtrend_e5.strategy import (
    VTrendE5Config,
    VTrendE5Strategy,
)
from strategies.vtrend_ema21.strategy import (
    VTrendEma21Config,
    VTrendEma21Strategy,
)
from strategies.vtrend_ema21_d1.strategy import (
    VTrendEma21D1Config,
    VTrendEma21D1Strategy,
)
from strategies.vtrend_e5_ema21_d1.strategy import (
    VTrendE5Ema21D1Config,
    VTrendE5Ema21D1Strategy,
)
from strategies.vtrend_x0.strategy import (
    VTrendX0Config,
    VTrendX0Strategy,
)
from strategies.vtrend_x0_e5exit.strategy import (
    VTrendX0E5ExitConfig,
    VTrendX0E5ExitStrategy,
)
from strategies.vtrend_x0_volsize.strategy import (
    VTrendX0VolsizeConfig,
    VTrendX0VolsizeStrategy,
)
from strategies.vtrend_x2.strategy import (
    VTrendX2Config,
    VTrendX2Strategy,
)
from strategies.vtrend_x6.strategy import (
    VTrendX6Config,
    VTrendX6Strategy,
)
from strategies.vtrend_x7.strategy import (
    VTrendX7Config,
    VTrendX7Strategy,
)
from strategies.vtrend_x8.strategy import (
    VTrendX8Config,
    VTrendX8Strategy,
)
from strategies.vtrend_vp1.strategy import (
    VP1Config,
    VP1Strategy,
)
from strategies.vtrend_vp1_e5exit.strategy import (
    VP1E5ExitConfig,
    VP1E5ExitStrategy,
)
from strategies.vtrend_vp1_full.strategy import (
    VP1FullConfig,
    VP1FullStrategy,
)
from strategies.vtrend_qvdo.strategy import (
    VTrendQVDOConfig,
    VTrendQVDOStrategy,
)
from strategies.vtrend_x5.strategy import (
    VTrendX5Config,
    VTrendX5Strategy,
)
from strategies.vtrend_e5_ema21_d1_vc.strategy import (
    VTrendE5Ema21D1VCConfig,
    VTrendE5Ema21D1VCStrategy,
)

# Registry: strategy_name → (StrategyClass, ConfigClass_or_None)
STRATEGY_REGISTRY: dict[str, tuple[type[Strategy], type | None]] = {
    "v8_apex": (V8ApexStrategy, V8ApexConfig),
    "v11_hybrid": (V11HybridStrategy, V11HybridConfig),
    "v12_emdd_ref_fix": (V12EMDDRefFixStrategy, V12EMDDRefFixConfig),
    "v13_add_throttle": (V13AddThrottleStrategy, V13AddThrottleConfig),
    "vtrend": (VTrendStrategy, VTrendConfig),
    "vtrend_e5": (VTrendE5Strategy, VTrendE5Config),
    "vtrend_ema21": (VTrendEma21Strategy, VTrendEma21Config),
    "vtrend_ema21_d1": (VTrendEma21D1Strategy, VTrendEma21D1Config),
    "vtrend_e5_ema21_d1": (VTrendE5Ema21D1Strategy, VTrendE5Ema21D1Config),
    "vtrend_sm": (VTrendSMStrategy, VTrendSMConfig),
    "vtrend_p": (VTrendPStrategy, VTrendPConfig),
    "latch": (LatchStrategy, LatchConfig),
    "vtrend_x0": (VTrendX0Strategy, VTrendX0Config),
    "vtrend_x0_e5exit": (VTrendX0E5ExitStrategy, VTrendX0E5ExitConfig),
    "vtrend_x0_volsize": (VTrendX0VolsizeStrategy, VTrendX0VolsizeConfig),
    "vtrend_x2": (VTrendX2Strategy, VTrendX2Config),
    "vtrend_x6": (VTrendX6Strategy, VTrendX6Config),
    "vtrend_x7": (VTrendX7Strategy, VTrendX7Config),
    "vtrend_x8": (VTrendX8Strategy, VTrendX8Config),
    "vtrend_vp1": (VP1Strategy, VP1Config),
    "vtrend_vp1_e5exit": (VP1E5ExitStrategy, VP1E5ExitConfig),
    "vtrend_vp1_full": (VP1FullStrategy, VP1FullConfig),
    "vtrend_qvdo": (VTrendQVDOStrategy, VTrendQVDOConfig),
    "vtrend_x5": (VTrendX5Strategy, VTrendX5Config),
    "vtrend_e5_ema21_d1_vc": (VTrendE5Ema21D1VCStrategy, VTrendE5Ema21D1VCConfig),
    "buy_and_hold": (BuyAndHold, None),
}


def _build_config_obj(strategy_name: str, params: dict[str, Any]) -> Any:
    """Build a strategy config dataclass from name + param overrides."""
    entry = STRATEGY_REGISTRY.get(strategy_name)
    if entry is None:
        raise ValueError(f"Unknown strategy: {strategy_name!r}. "
                         f"Known: {sorted(STRATEGY_REGISTRY)}")
    _, config_cls = entry
    if config_cls is None:
        return None
    cfg = config_cls()
    for k, v in params.items():
        if not hasattr(cfg, k):
            raise ValueError(f"{config_cls.__name__} has no field {k!r}")
        setattr(cfg, k, v)
    return cfg


def build_from_config(live_config: LiveConfig) -> tuple[Strategy, Any]:
    """Build a (Strategy, config_dataclass) pair from a LiveConfig."""
    name = live_config.strategy.name
    params = live_config.strategy.params
    entry = STRATEGY_REGISTRY.get(name)
    if entry is None:
        raise ValueError(f"Unknown strategy: {name!r}")
    strategy_cls, _ = entry
    cfg = _build_config_obj(name, params)
    if cfg is not None:
        strategy = strategy_cls(cfg)
    else:
        strategy = strategy_cls()
    return strategy, cfg


def make_factory(
    live_config: LiveConfig,
    *,
    access_tracker: AccessTracker | None = None,
) -> Callable[[], Strategy]:
    """Return a zero-arg callable that produces fresh Strategy instances.

    Each call returns a new instance (required because BacktestEngine
    mutates strategy state during run()).
    """
    name = live_config.strategy.name
    params = dict(live_config.strategy.params)
    entry = STRATEGY_REGISTRY.get(name)
    if entry is None:
        raise ValueError(f"Unknown strategy: {name!r}")
    strategy_cls, _ = entry

    # Validate params eagerly (fail-fast on typos).
    # _build_config_obj raises ValueError for unknown fields.
    _build_config_obj(name, params)

    def _factory() -> Strategy:
        cfg = _build_config_obj(name, params)
        if cfg is not None:
            if access_tracker is not None:
                cfg = ConfigProxy(cfg, access_tracker)
            return strategy_cls(cfg)
        return strategy_cls()

    return _factory
