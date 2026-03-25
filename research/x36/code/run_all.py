"""Root convenience runner for active x36 branches."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent


def run(script_path: Path) -> None:
    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    branches = (
        THIS_DIR.parent / "branches" / "b_e5_wfo_robustness_diagnostic" / "code" / "run_b_e5_wfo_robustness_diagnostic.py",
    )
    for branch_runner in branches:
        run(branch_runner)


if __name__ == "__main__":
    main()
