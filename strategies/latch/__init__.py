"""LATCH: Hysteretic trend-following strategy with 3-state machine.

Ported from Latch/research/Latch/ package.
"""

from strategies.latch.strategy import (
    STRATEGY_ID,
    LatchConfig,
    LatchStrategy,
)

__all__ = ["STRATEGY_ID", "LatchConfig", "LatchStrategy"]
