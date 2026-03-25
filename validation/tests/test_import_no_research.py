"""Test that importing validation.config does NOT pull research/ code.

Fix 3 verification: the import chain validation → runner → strategy_factory →
vtrend_qvdo → research.x34 is broken by (a) lazy-loading ValidationRunner
and (b) moving q_vdo_rh into the strategy directory.
"""

from __future__ import annotations

import subprocess
import sys


def test_validation_config_import_does_not_load_research() -> None:
    """Importing validation.config must not trigger research package init."""
    result = subprocess.run(
        [
            sys.executable,
            "-W", "error::UserWarning",
            "-c",
            "from validation.config import ValidationConfig",
        ],
        capture_output=True,
        text=True,
        cwd="/var/www/trading-bots/btc-spot-dev",
        env={**__import__("os").environ, "_RESEARCH_CONTEXT": ""},
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Import raised a warning or error.\nstderr: {result.stderr}\nstdout: {result.stdout}"
    )


def test_vtrend_qvdo_strategy_does_not_import_research() -> None:
    """strategies/vtrend_qvdo now imports q_vdo_rh locally, not from research/."""
    result = subprocess.run(
        [
            sys.executable,
            "-W", "error::UserWarning",
            "-c",
            "from strategies.vtrend_qvdo.strategy import VTrendQVDOStrategy",
        ],
        capture_output=True,
        text=True,
        cwd="/var/www/trading-bots/btc-spot-dev",
        env={**__import__("os").environ, "_RESEARCH_CONTEXT": ""},
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Import triggered research warning.\nstderr: {result.stderr}\nstdout: {result.stdout}"
    )
