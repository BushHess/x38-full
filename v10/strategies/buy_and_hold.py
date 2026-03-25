"""BuyAndHold — reference strategy for framework validation.

Goes to max exposure on first bar after warmup and holds indefinitely.
Useful as a benchmark to compare active strategies against.
"""

from __future__ import annotations

from v10.core.types import MarketState, Signal
from v10.strategies.base import Strategy


class BuyAndHold(Strategy):
    """Buy once to target exposure and hold forever.

    Parameters
    ----------
    target : float
        Desired exposure fraction (default 1.0 = fully invested).
    """

    def __init__(self, target: float = 1.0) -> None:
        self._target = max(0.0, min(1.0, target))
        self._entered = False

    def on_bar(self, state: MarketState) -> Signal | None:
        if self._entered:
            return None
        self._entered = True
        return Signal(target_exposure=self._target, reason="buy_and_hold")
