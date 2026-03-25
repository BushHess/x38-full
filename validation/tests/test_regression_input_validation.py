"""Regression tests for input validation bugs found 2026-03-16.

Bug 1: make_factory() silently accepted typo params via setattr without hasattr guard.
Bug 2: generate_windows() accepted slide_months=0 (infinite loop) and test_months=0.
Bug 3: _resolve_holdout_window() silently ignored partial explicit dates, no frac validation.
Bug 5: InvariantsSuite only checked one scenario instead of all configured.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from v10.research.wfo import generate_windows
from validation.suites.holdout import _resolve_holdout_window


# ---------------------------------------------------------------------------
# Bug 1: make_factory() must reject unknown params
# ---------------------------------------------------------------------------


def test_make_factory_rejects_typo_param() -> None:
    """make_factory() must raise ValueError for params not on the config dataclass."""
    from v10.core.config import load_config
    from validation.strategy_factory import make_factory

    # Use a real config as base, then inject a typo param.
    live_cfg = load_config(
        str(
            __import__("pathlib").Path(__file__).resolve().parents[2]
            / "configs"
            / "vtrend_e5_ema21_d1"
            / "vtrend_e5_ema21_d1_default.yaml"
        )
    )
    live_cfg.strategy.params["slow_period_typo"] = 123

    with pytest.raises(ValueError, match="no field.*slow_period_typo"):
        make_factory(live_cfg)


# ---------------------------------------------------------------------------
# Bug 2: generate_windows() must reject non-positive month params
# ---------------------------------------------------------------------------


def test_generate_windows_rejects_zero_slide_months() -> None:
    with pytest.raises(ValueError, match="slide_months must be > 0"):
        generate_windows("2020-01-01", "2023-01-01", slide_months=0)


def test_generate_windows_rejects_zero_test_months() -> None:
    with pytest.raises(ValueError, match="test_months must be > 0"):
        generate_windows("2020-01-01", "2023-01-01", test_months=0)


def test_generate_windows_rejects_zero_train_months() -> None:
    with pytest.raises(ValueError, match="train_months must be > 0"):
        generate_windows("2020-01-01", "2023-01-01", train_months=0)


def test_generate_windows_rejects_negative_months() -> None:
    with pytest.raises(ValueError, match="slide_months must be > 0"):
        generate_windows("2020-01-01", "2023-01-01", slide_months=-3)


# ---------------------------------------------------------------------------
# Bug 3: _resolve_holdout_window() validation
# ---------------------------------------------------------------------------


def test_holdout_rejects_partial_explicit_dates_start_only() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=0.2,
        holdout_start="2020-10-01",
        holdout_end=None,
    )
    with pytest.raises(ValueError, match="both be set or both be None"):
        _resolve_holdout_window(cfg)


def test_holdout_rejects_partial_explicit_dates_end_only() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=0.2,
        holdout_start=None,
        holdout_end="2020-12-31",
    )
    with pytest.raises(ValueError, match="both be set or both be None"):
        _resolve_holdout_window(cfg)


def test_holdout_rejects_frac_above_one() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=1.5,
        holdout_start=None,
        holdout_end=None,
    )
    with pytest.raises(ValueError, match="holdout_frac must be in"):
        _resolve_holdout_window(cfg)


def test_holdout_rejects_frac_zero() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=0.0,
        holdout_start=None,
        holdout_end=None,
    )
    with pytest.raises(ValueError, match="holdout_frac must be in"):
        _resolve_holdout_window(cfg)


def test_holdout_rejects_negative_frac() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=-0.1,
        holdout_start=None,
        holdout_end=None,
    )
    with pytest.raises(ValueError, match="holdout_frac must be in"):
        _resolve_holdout_window(cfg)


def test_holdout_rejects_explicit_window_outside_data_range() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=0.2,
        holdout_start="2019-06-01",
        holdout_end="2020-12-31",
    )
    with pytest.raises(ValueError, match="outside data range"):
        _resolve_holdout_window(cfg)


def test_holdout_rejects_explicit_start_after_end() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=0.2,
        holdout_start="2020-11-01",
        holdout_end="2020-10-01",
    )
    with pytest.raises(ValueError, match="holdout_start .* > holdout_end"):
        _resolve_holdout_window(cfg)


def test_holdout_valid_frac_still_works() -> None:
    """Existing behavior preserved for valid fraction-based holdout."""
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-01-10",
        holdout_frac=0.2,
        holdout_start=None,
        holdout_end=None,
    )
    assert _resolve_holdout_window(cfg) == ("2020-01-09", "2020-01-10")


def test_holdout_valid_explicit_still_works() -> None:
    """Existing behavior preserved for valid explicit holdout."""
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-12-31",
        holdout_frac=0.2,
        holdout_start="2020-10-01",
        holdout_end="2020-12-31",
    )
    assert _resolve_holdout_window(cfg) == ("2020-10-01", "2020-12-31")
