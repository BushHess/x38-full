"""Run the current canonical diagnostic branch for x35."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent


def _run(script_name: str) -> None:
    subprocess.run([sys.executable, str(THIS_DIR / script_name)], check=True)


def main() -> None:
    _run("phase0_data_audit.py")
    _run("phase1_regime_decomposition.py")


if __name__ == "__main__":
    main()
