from __future__ import annotations

from datetime import date, timedelta

from v10.research.wfo import generate_windows


def test_generate_windows_returns_inclusive_non_overlapping_ranges() -> None:
    windows = generate_windows(
        "2019-01-01",
        "2022-01-01",
        train_months=24,
        test_months=6,
        slide_months=6,
    )

    assert len(windows) == 2

    first = windows[0]
    second = windows[1]

    assert first.train_start == "2019-01-01"
    assert first.train_end == "2020-12-31"
    assert first.test_start == "2021-01-01"
    assert first.test_end == "2021-06-30"

    assert second.train_start == "2019-07-01"
    assert second.train_end == "2021-06-30"
    assert second.test_start == "2021-07-01"
    assert second.test_end == "2021-12-31"

    assert date.fromisoformat(first.train_end) + timedelta(days=1) == date.fromisoformat(
        first.test_start
    )
    assert date.fromisoformat(first.test_end) + timedelta(days=1) == date.fromisoformat(
        second.test_start
    )


def test_generate_windows_respects_inclusive_dataset_end() -> None:
    windows = generate_windows(
        "2020-01-01",
        "2021-12-31",
        train_months=12,
        test_months=6,
        slide_months=6,
    )

    assert [window.test_end for window in windows] == ["2021-06-30", "2021-12-31"]
