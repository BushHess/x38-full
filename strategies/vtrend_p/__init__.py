"""VTREND-P: Price-first trend-following strategy.

Ported from Latch/research/vtrend_variants.py (run_vtrend_p).
"""

from strategies.vtrend_p.strategy import (
    STRATEGY_ID,
    VTrendPConfig,
    VTrendPStrategy,
)

__all__ = ["STRATEGY_ID", "VTrendPConfig", "VTrendPStrategy"]
