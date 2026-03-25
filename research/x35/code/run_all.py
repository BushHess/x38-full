"""Root convenience runner for x35."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent


def run(script_path: Path) -> None:
    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    branches = (
        THIS_DIR.parent / "branches" / "a_state_diagnostic" / "code" / "run_a_state_diagnostic.py",
        THIS_DIR.parent / "branches" / "c_stress_state_diagnostic" / "code" / "run_c_stress_state_diagnostic.py",
        THIS_DIR.parent / "branches" / "d_multi_horizon_trend_diagnostic" / "code" / "run_d_multi_horizon_trend_diagnostic.py",
        THIS_DIR.parent / "branches" / "e_transition_instability_diagnostic" / "code" / "run_e_transition_instability_diagnostic.py",
        THIS_DIR.parent / "branches" / "f_price_level_state_diagnostic" / "code" / "run_f_price_level_state_diagnostic.py",
        THIS_DIR.parent / "branches" / "g_mid_trade_hazard_diagnostic" / "code" / "run_g_mid_trade_hazard_diagnostic.py",
    )
    for branch_runner in branches:
        run(branch_runner)


if __name__ == "__main__":
    main()
