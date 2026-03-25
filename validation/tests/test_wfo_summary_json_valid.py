from __future__ import annotations

import json
import math

from validation.output import write_json
from validation.suites.wfo import _aggregate_deltas


def _strict_json_loads(text: str) -> dict:
    def _raise_constant(value: str) -> None:
        raise ValueError(f"non-strict JSON constant: {value}")

    return json.loads(text, parse_constant=_raise_constant)


def test_wfo_summary_json_is_strict_and_non_finite_values_are_null(tmp_path) -> None:
    stats = _aggregate_deltas([], include_window=lambda _row: True)
    payload = {
        "summary": {"stats_power_only": stats},
        "windows": [
            {
                "window_id": 0,
                "valid_window": False,
                "invalid_reason": "candidate_non_finite_core_metrics",
                "delta_harsh_score": math.nan,
            }
        ],
    }

    path = write_json(payload, tmp_path / "wfo_summary.json")
    loaded = _strict_json_loads(path.read_text())

    assert loaded["summary"]["stats_power_only"]["mean_delta"] is None
    assert loaded["summary"]["stats_power_only"]["win_rate"] is None
    assert loaded["windows"][0]["delta_harsh_score"] is None
