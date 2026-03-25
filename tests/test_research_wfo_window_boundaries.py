from research.eval_e5_ema1d21.src.run_jackknife_wfo import generate_windows
from research.prod_readiness_e5_ema1d21.e5s_validation import generate_wfo_windows


def _assert_non_overlapping_windows(windows):
    assert windows
    for i, window in enumerate(windows):
        start = window["test_start"]
        end = window["test_end"]
        assert start <= end
        if i == 0:
            continue
        assert windows[i - 1]["test_end"] < start


def test_jackknife_wfo_windows_use_inclusive_boundaries():
    windows = generate_windows("2019-01-01", "2026-02-20")

    assert windows[0] == {
        "window_id": 0,
        "train_start": "2019-01-01",
        "train_end": "2020-12-31",
        "test_start": "2021-01-01",
        "test_end": "2021-06-30",
    }
    assert windows[1]["test_start"] == "2021-07-01"
    assert windows[1]["test_end"] == "2021-12-31"
    _assert_non_overlapping_windows(windows)


def test_e5s_wfo_windows_use_inclusive_boundaries():
    windows = generate_wfo_windows("2019-01-01", "2026-02-20")

    assert windows[0] == {
        "window_id": 0,
        "test_start": "2021-01-01",
        "test_end": "2021-06-30",
    }
    assert windows[1]["test_start"] == "2021-07-01"
    assert windows[1]["test_end"] == "2021-12-31"
    _assert_non_overlapping_windows(windows)
