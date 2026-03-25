from __future__ import annotations

from types import SimpleNamespace

from validation.suites.holdout import _resolve_holdout_window


def test_resolve_holdout_window_uses_exact_inclusive_day_count() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-01-10",
        holdout_frac=0.2,
        holdout_start=None,
        holdout_end=None,
    )

    holdout_start, holdout_end = _resolve_holdout_window(cfg)

    assert (holdout_start, holdout_end) == ("2020-01-09", "2020-01-10")


def test_resolve_holdout_window_preserves_explicit_dates() -> None:
    cfg = SimpleNamespace(
        start="2020-01-01",
        end="2020-01-10",
        holdout_frac=0.2,
        holdout_start="2020-01-04",
        holdout_end="2020-01-06",
    )

    assert _resolve_holdout_window(cfg) == ("2020-01-04", "2020-01-06")
