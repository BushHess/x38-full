"""Strategy abstract base class.

Every strategy must implement on_bar() which receives the current
MarketState and returns a Signal (or None to hold current position).
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from v10.core.types import Fill
from v10.core.types import MarketState
from v10.core.types import Signal


class Strategy(ABC):
    """Base class for all V10 trading strategies.

    Return modes (see Signal docs):
      1. target_exposure mode — set signal.target_exposure to desired
         fraction of NAV in BTC (0.0 = flat, 1.0 = fully invested).
      2. orders mode — set signal.orders to a list of explicit Orders.
      3. None — engine holds current position, no action.
    """

    @abstractmethod
    def on_bar(self, state: MarketState) -> Signal | None:
        """Called at each H4 bar close.  Return Signal or None."""
        ...

    def on_init(self, h4_bars: list, d1_bars: list) -> None:
        """Optional hook: called once before backtest starts.

        Can be used to pre-compute indicators on full bar arrays.
        """
        return None

    def on_after_fill(self, state: MarketState, fill: Fill) -> None:
        """Optional hook: called right after each fill is applied.

        ``state`` is post-fill portfolio state with NAV computed at the same
        mid price used for the fill bar open.
        """
        return None

    def name(self) -> str:
        return self.__class__.__name__
