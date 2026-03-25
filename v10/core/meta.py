"""Run metadata — git hash, file fingerprints, run_meta.json stamping."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_git_hash() -> str:
    """Return current git HEAD hash (short), or 'unknown' on failure."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        h = out.stdout.strip()
        return h if h else "unknown"
    except Exception:
        return "unknown"


def fingerprint_file(path: str | Path) -> str:
    """Return hex SHA-256 of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stamp_run_meta(
    outdir: str | Path,
    *,
    argv: list[str] | None = None,
    config: dict[str, Any] | None = None,
    data_path: str | Path | None = None,
) -> Path:
    """Write run_meta.json to outdir.

    Parameters
    ----------
    outdir : path
        Output directory (created if needed).
    argv : list[str] | None
        Command-line arguments (defaults to sys.argv).
    config : dict | None
        Effective merged config snapshot.
    data_path : path | None
        Path to input data file for fingerprinting.

    Returns
    -------
    Path to the written run_meta.json.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    meta: dict[str, Any] = {
        "git_hash": get_git_hash(),
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "argv": argv if argv is not None else sys.argv,
    }

    if config is not None:
        meta["config"] = config

    if data_path is not None:
        p = Path(data_path)
        if p.exists():
            meta["data_fingerprint"] = fingerprint_file(p)
        else:
            meta["data_fingerprint"] = None

    path = out / "run_meta.json"
    with open(path, "w") as f:
        json.dump(meta, f, indent=2, default=str)

    return path
