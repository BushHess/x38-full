"""VTREND-SM: State-machine trend-following strategy.

Ported from Latch/research/vtrend_variants.py (run_vtrend_state_machine).
"""

from strategies.vtrend_sm.strategy import (
    STRATEGY_ID,
    VTrendSMConfig,
    VTrendSMStrategy,
)

__all__ = ["STRATEGY_ID", "VTrendSMConfig", "VTrendSMStrategy"]
