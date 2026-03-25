"""Tests for VDO semantic contract: fail-closed without taker data.

Verifies that _vdo raises RuntimeError when taker_buy_base_vol is missing
or all-zero, and works correctly with real taker data.  This prevents the
old OHLC fallback from silently changing VDO's meaning from order-flow to
price-location.

P0 fix (2026-03-14): OHLC fallback removed from E0, E5, E5_ema21D1, X7.
Extended (2026-03-16): OHLC fallback removed from ALL 22 strategies with _vdo.
"""

from __future__ import annotations

import numpy as np
import pytest


# -- Helpers -----------------------------------------------------------------

def _random_ohlcv(n: int = 200, seed: int = 42) -> dict:
    """Generate synthetic OHLCV + taker_buy arrays."""
    rng = np.random.default_rng(seed)
    close = 40000.0 + np.cumsum(rng.normal(0, 100, n))
    high = close + rng.uniform(50, 200, n)
    low = close - rng.uniform(50, 200, n)
    volume = rng.uniform(10, 500, n)
    taker_buy = volume * rng.uniform(0.3, 0.7, n)
    return {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
        "taker_buy": taker_buy,
    }


# -- All strategies with _vdo (must be fail-closed) -------------------------

_VDO_MODULES = [
    "strategies.vtrend.strategy",
    "strategies.vtrend_e5.strategy",
    "strategies.vtrend_e5_ema21_d1.strategy",
    "strategies.vtrend_x7.strategy",
    "strategies.vtrend_x0.strategy",
    "strategies.vtrend_x1.strategy",
    "strategies.vtrend_x2.strategy",
    "strategies.vtrend_x3.strategy",
    "strategies.vtrend_x4b.strategy",
    "strategies.vtrend_x5.strategy",
    "strategies.vtrend_x6.strategy",
    "strategies.vtrend_x8.strategy",
    "strategies.vtrend_x0_e5exit.strategy",
    "strategies.vtrend_x0_volsize.strategy",
    "strategies.vtrend_ema21.strategy",
    "strategies.vtrend_ema21_d1.strategy",
    "strategies.vtrend_e5s_ema21_d1.strategy",
    "strategies.vtrend_sm.strategy",
    "strategies.latch.strategy",
    "strategies.vcusum.strategy",
    "strategies.vtwin.strategy",
    "strategies.vbreak.strategy",
]


def _get_vdo(module_name: str):
    """Import _vdo function from a strategy module."""
    import importlib
    mod = importlib.import_module(module_name)
    return mod._vdo


# -- Tests -------------------------------------------------------------------

class TestVdoFailClosed:
    """VDO must raise RuntimeError when taker data is absent."""

    @pytest.mark.parametrize("module", _VDO_MODULES)
    def test_raises_when_taker_buy_is_none(self, module: str) -> None:
        _vdo = _get_vdo(module)
        d = _random_ohlcv()
        with pytest.raises(RuntimeError, match="taker_buy_base_vol"):
            _vdo(d["close"], d["high"], d["low"], d["volume"],
                 None, fast=12, slow=28)

    @pytest.mark.parametrize("module", _VDO_MODULES)
    def test_raises_when_taker_buy_all_zero(self, module: str) -> None:
        _vdo = _get_vdo(module)
        d = _random_ohlcv()
        zeros = np.zeros_like(d["volume"])
        with pytest.raises(RuntimeError, match="taker_buy_base_vol"):
            _vdo(d["close"], d["high"], d["low"], d["volume"],
                 zeros, fast=12, slow=28)


class TestVdoTakerPath:
    """VDO works correctly with real taker data."""

    @pytest.mark.parametrize("module", _VDO_MODULES)
    def test_returns_array_with_valid_taker_data(self, module: str) -> None:
        _vdo = _get_vdo(module)
        d = _random_ohlcv()
        result = _vdo(d["close"], d["high"], d["low"], d["volume"],
                      d["taker_buy"], fast=12, slow=28)
        assert isinstance(result, np.ndarray)
        assert len(result) == len(d["close"])
        assert not np.any(np.isnan(result))

    @pytest.mark.parametrize("module", _VDO_MODULES)
    def test_vdo_bounded(self, module: str) -> None:
        """VDO (MACD of ratio in [-1,1]) should stay within [-2, 2]."""
        _vdo = _get_vdo(module)
        d = _random_ohlcv(n=1000)
        result = _vdo(d["close"], d["high"], d["low"], d["volume"],
                      d["taker_buy"], fast=12, slow=28)
        assert np.all(result >= -2.0)
        assert np.all(result <= 2.0)

    @pytest.mark.parametrize("module", _VDO_MODULES)
    def test_vdo_not_all_zero(self, module: str) -> None:
        """With asymmetric taker_buy, VDO should not be identically zero."""
        _vdo = _get_vdo(module)
        d = _random_ohlcv(n=500)
        result = _vdo(d["close"], d["high"], d["low"], d["volume"],
                      d["taker_buy"], fast=12, slow=28)
        assert not np.allclose(result, 0.0)
