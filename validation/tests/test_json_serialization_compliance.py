"""Tests for JSON serialization standards compliance (Report 33).

Verifies that write_json() produces strict RFC 8259-compliant JSON with no
NaN, Infinity, or -Infinity tokens. Also verifies that the holdout lock file
now uses the sanitized serialization path.

Test IDs (Report 33):
  JS1: NaN replaced with null
  JS2: Infinity replaced with null
  JS3: -Infinity replaced with null
  JS4: Nested NaN/Inf in dict/list all sanitized
  JS5: Holdout lock payload through write_json is strict JSON
  JS6: numpy NaN/Inf through write_json are strict JSON
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from validation.output import write_json


def _strict_json_loads(text: str) -> dict:
    """Load JSON rejecting non-standard constants (NaN, Infinity)."""
    def _raise_constant(value: str) -> None:
        raise ValueError(f"non-strict JSON constant: {value}")

    return json.loads(text, parse_constant=_raise_constant)


class TestJsonStrictCompliance:
    def test_nan_replaced_with_null(self, tmp_path) -> None:
        """JS1: write_json converts NaN to null."""
        path = write_json({"value": float("nan")}, tmp_path / "test.json")
        loaded = _strict_json_loads(path.read_text())
        assert loaded["value"] is None

    def test_infinity_replaced_with_null(self, tmp_path) -> None:
        """JS2: write_json converts Infinity to null."""
        path = write_json({"value": float("inf")}, tmp_path / "test.json")
        loaded = _strict_json_loads(path.read_text())
        assert loaded["value"] is None

    def test_neg_infinity_replaced_with_null(self, tmp_path) -> None:
        """JS3: write_json converts -Infinity to null."""
        path = write_json({"value": float("-inf")}, tmp_path / "test.json")
        loaded = _strict_json_loads(path.read_text())
        assert loaded["value"] is None

    def test_nested_non_finite_all_sanitized(self, tmp_path) -> None:
        """JS4: Nested NaN/Inf in dict/list all replaced with null."""
        payload = {
            "outer": {
                "nan_val": float("nan"),
                "inf_val": float("inf"),
                "list_val": [1.0, float("-inf"), float("nan"), 3.0],
            },
            "top_nan": float("nan"),
        }
        path = write_json(payload, tmp_path / "test.json")
        loaded = _strict_json_loads(path.read_text())
        assert loaded["outer"]["nan_val"] is None
        assert loaded["outer"]["inf_val"] is None
        assert loaded["outer"]["list_val"] == [1.0, None, None, 3.0]
        assert loaded["top_nan"] is None

    def test_holdout_lock_payload_strict_json(self, tmp_path) -> None:
        """JS5: Holdout lock payload through write_json produces strict JSON."""
        from datetime import datetime, timezone

        lock_payload = {
            "holdout_start": "2025-06-01",
            "holdout_end": "2026-02-20",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        path = write_json(lock_payload, tmp_path / "holdout_lock.json")
        loaded = _strict_json_loads(path.read_text())
        assert loaded["holdout_start"] == "2025-06-01"
        assert loaded["holdout_end"] == "2026-02-20"
        assert "created_at_utc" in loaded

    def test_numpy_non_finite_sanitized(self, tmp_path) -> None:
        """JS6: numpy NaN/Inf through write_json are strict JSON."""
        payload = {
            "np_nan": np.float64("nan"),
            "np_inf": np.float64("inf"),
            "np_neg_inf": np.float64("-inf"),
            "np_normal": np.float64(3.14),
            "np_int": np.int64(42),
        }
        path = write_json(payload, tmp_path / "test.json")
        loaded = _strict_json_loads(path.read_text())
        assert loaded["np_nan"] is None
        assert loaded["np_inf"] is None
        assert loaded["np_neg_inf"] is None
        assert loaded["np_normal"] == pytest.approx(3.14)
        assert loaded["np_int"] == 42


class TestHoldoutLockNoRawJsonDump:
    def test_holdout_source_no_raw_json_dump(self) -> None:
        """JS7: holdout.py no longer uses raw json.dump for lock file."""
        import inspect
        import validation.suites.holdout as mod
        source = inspect.getsource(mod)
        # Should not contain json.dump( pattern (raw serialization)
        assert "json.dump(" not in source
        # Should not import json module
        assert "import json" not in source
