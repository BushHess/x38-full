"""Shared timestamp formatting for all CSV writers.

Single source of truth: ISO-8601 UTC exactly YYYY-MM-DDTHH:MM:SSZ.
Guarantees no 24:00 formatting (Python's strftime already prevents this,
but this module centralises the contract so it can be tested once).
"""

from __future__ import annotations

from datetime import datetime, timezone


def ms_to_iso(ts_ms: int) -> str:
    """Convert epoch-milliseconds to ISO-8601 UTC string.

    Format: YYYY-MM-DDTHH:MM:SSZ  (24-hour clock, 00–23 range).
    """
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
