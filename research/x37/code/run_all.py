"""Safe root runner for x37 sessions.

Unlike x35/x36, x37 may not auto-advance through every discovered phase runner.
The caller must explicitly choose one ACTIVE session and one phase to run.

Usage:
    python research/x37/code/run_all.py
    python research/x37/code/run_all.py --session s01_codex_v4
    python research/x37/code/run_all.py --session s01_codex_v4 --phase 1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

THIS_DIR = Path(__file__).resolve().parent
X37_DIR = THIS_DIR.parent
MANIFEST = X37_DIR / "manifest.json"

PHASES: dict[str, dict[str, object]] = {
    "1": {
        "name": "phase1_decomposition",
        "runner": Path("phase1_decomposition/code/run_phase1.py"),
        "requires": [Path("phase0_protocol/protocol_freeze.json")],
        "blocks_if_exists": [
            Path("phase2_hypotheses/hypotheses.md"),
            Path("phase4_parameters/results/search_results.csv"),
            Path("phase4_parameters/results/plateau_test.csv"),
            Path("phase5_freeze/frozen_spec.json"),
            Path("phase6_benchmark/results/benchmark_comparison.csv"),
            Path("verdict/verdict.json"),
        ],
    },
    "3": {
        "name": "phase3_design",
        "runner": Path("phase3_design/code/run_phase3.py"),
        "requires": [
            Path("phase1_decomposition/results/measurements.csv"),
            Path("phase1_decomposition/results/channel_report.md"),
            Path("phase1_decomposition/results/d1_h4_alignment.json"),
            Path("phase2_hypotheses/hypotheses.md"),
        ],
        "blocks_if_exists": [
            Path("phase4_parameters/results/search_results.csv"),
            Path("phase4_parameters/results/plateau_test.csv"),
            Path("phase5_freeze/frozen_spec.json"),
            Path("phase6_benchmark/results/benchmark_comparison.csv"),
            Path("verdict/verdict.json"),
        ],
    },
    "4": {
        "name": "phase4_parameters",
        "runner": Path("phase4_parameters/code/run_phase4.py"),
        "requires": [
            Path("phase1_decomposition/results/measurements.csv"),
            Path("phase1_decomposition/results/channel_report.md"),
            Path("phase1_decomposition/results/d1_h4_alignment.json"),
            Path("phase2_hypotheses/hypotheses.md"),
        ],
        "blocks_if_exists": [
            Path("phase5_freeze/frozen_spec.md"),
            Path("phase5_freeze/frozen_spec.json"),
            Path("phase5_freeze/results/holdout_results.csv"),
            Path("phase6_benchmark/results/benchmark_comparison.csv"),
            Path("verdict/verdict.json"),
        ],
    },
    "5": {
        "name": "phase5_freeze",
        "runner": Path("phase5_freeze/code/run_phase5.py"),
        "requires": [
            Path("phase1_decomposition/results/measurements.csv"),
            Path("phase1_decomposition/results/channel_report.md"),
            Path("phase1_decomposition/results/d1_h4_alignment.json"),
            Path("phase2_hypotheses/hypotheses.md"),
            Path("phase4_parameters/results/search_results.csv"),
            Path("phase4_parameters/results/plateau_test.csv"),
        ],
        "blocks_if_exists": [
            Path("phase5_freeze/frozen_spec.md"),
            Path("phase5_freeze/frozen_spec.json"),
            Path("phase5_freeze/results/holdout_results.csv"),
            Path("phase6_benchmark/results/benchmark_comparison.csv"),
            Path("verdict/verdict.json"),
        ],
    },
    "6": {
        "name": "phase6_benchmark",
        "runner": Path("phase6_benchmark/code/run_phase6.py"),
        "requires": [
            Path("phase1_decomposition/results/measurements.csv"),
            Path("phase1_decomposition/results/channel_report.md"),
            Path("phase1_decomposition/results/d1_h4_alignment.json"),
            Path("phase2_hypotheses/hypotheses.md"),
            Path("phase4_parameters/results/search_results.csv"),
            Path("phase4_parameters/results/plateau_test.csv"),
            Path("phase5_freeze/frozen_spec.md"),
            Path("phase5_freeze/frozen_spec.json"),
            Path("phase5_freeze/results/holdout_results.csv"),
            Path("phase5_freeze/results/regime_decomposition.csv"),
            Path("phase5_freeze/results/cost_sensitivity.csv"),
            Path("phase5_freeze/results/bootstrap_summary.csv"),
            Path("phase5_freeze/results/trade_distribution.csv"),
        ],
        "blocks_if_exists": [
            Path("phase6_benchmark/results/benchmark_comparison.csv"),
            Path("phase6_benchmark/results/paired_bootstrap.csv"),
            Path("verdict/verdict.json"),
        ],
    },
}


def _load_manifest() -> dict:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"manifest.json not found at {MANIFEST}")
    return json.loads(MANIFEST.read_text())


def _session_map(manifest: dict) -> dict[str, dict]:
    return {session.get("id", ""): session for session in manifest.get("sessions", [])}


def _validate_protocol(protocol_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        protocol = json.loads(protocol_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"invalid JSON in {protocol_path}: {exc}"]

    # Required top-level sections (prevent starting with near-empty protocol)
    required_sections = ["data", "splits", "cost", "execution", "evaluation", "hard_criteria"]
    for section in required_sections:
        if section not in protocol or not isinstance(protocol[section], dict):
            errors.append(f"protocol_freeze.json must contain a '{section}' object")

    # Walk-forward windows
    windows = protocol.get("walk_forward", {}).get("windows")
    allow_exact_matches = (
        protocol.get("execution", {})
        .get("d1_h4_alignment", {})
        .get("allow_exact_matches")
    )

    if not isinstance(windows, list) or len(windows) < 4:
        errors.append("protocol_freeze.json must define at least 4 walk-forward windows")
    else:
        for index, window in enumerate(windows, start=1):
            if not isinstance(window, dict):
                errors.append(f"walk_forward.windows[{index}] must be an object")
                continue
            test_start = window.get("test_start")
            test_end = window.get("test_end")
            if not test_start or not test_end:
                errors.append(f"walk_forward.windows[{index}] must include test_start and test_end")
            if isinstance(test_start, str) and "YYYY" in test_start:
                errors.append(f"walk_forward.windows[{index}].test_start still has placeholder value")
            if isinstance(test_end, str) and "YYYY" in test_end:
                errors.append(f"walk_forward.windows[{index}].test_end still has placeholder value")

    if not isinstance(allow_exact_matches, bool):
        errors.append("execution.d1_h4_alignment.allow_exact_matches must be a boolean")

    # Splits validation
    splits = protocol.get("splits", {})
    for split_name in ["warmup", "development", "holdout"]:
        split = splits.get(split_name, {})
        if not isinstance(split, dict) or "start" not in split or "end" not in split:
            errors.append(f"splits.{split_name} must have 'start' and 'end' dates")

    return errors


def _missing_paths(session_dir: Path, paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if not (session_dir / path).exists()]


def _has_non_figure_artifact(results_dir: Path) -> bool:
    if not results_dir.is_dir():
        return False
    for path in results_dir.rglob("*"):
        if path.is_file() and "figures" not in path.parts:
            return True
    return False


def _list_active_sessions(manifest: dict) -> list[dict]:
    return [session for session in manifest.get("sessions", []) if session.get("status") == "ACTIVE"]


def _describe_session(session_dir: Path) -> str:
    protocol = session_dir / "phase0_protocol/protocol_freeze.json"
    phase1_measurements = session_dir / "phase1_decomposition/results/measurements.csv"
    phase1_report = session_dir / "phase1_decomposition/results/channel_report.md"
    phase2 = session_dir / "phase2_hypotheses/hypotheses.md"
    phase4_search = session_dir / "phase4_parameters/results/search_results.csv"
    phase4_plateau = session_dir / "phase4_parameters/results/plateau_test.csv"
    phase5 = session_dir / "phase5_freeze/frozen_spec.json"
    phase6 = session_dir / "verdict/verdict.json"

    if phase6.exists():
        return "phase6 complete"
    if phase5.exists():
        return "phase5 touched/frozen"
    if phase4_search.exists() and phase4_plateau.exists():
        return "ready for phase5"
    if phase2.exists() and _has_non_figure_artifact(session_dir / "phase3_design/results"):
        return "ready for phase4"
    if phase2.exists():
        return "ready for phase3"
    if protocol.exists() and phase1_measurements.exists() and phase1_report.exists():
        return "ready for phase2"
    if protocol.exists():
        return "ready for phase1"
    return "protocol not frozen"


def run(script_path: Path) -> None:
    print(f">>> Running: {script_path.relative_to(X37_DIR)}")
    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one explicit phase for one ACTIVE x37 session")
    parser.add_argument("--session", type=str, default=None,
                        help="Inspect or run a specific session (e.g. s01_codex_v4)")
    parser.add_argument("--phase", choices=sorted(PHASES), default=None,
                        help="Run one explicit phase: 1, 3, 4, 5, or 6")
    args = parser.parse_args()

    try:
        manifest = _load_manifest()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    sessions = _session_map(manifest)

    if not sessions:
        print("No sessions registered in manifest.json.")
        return

    if args.session is None:
        active_sessions = _list_active_sessions(manifest)
        if not active_sessions:
            print("No ACTIVE sessions registered.")
            return
        for session in active_sessions:
            sid = session["id"]
            session_dir = X37_DIR / "sessions" / sid
            state = _describe_session(session_dir)
            print(f"{sid}: {state}")
        return

    if args.session not in sessions:
        print(f"ERROR: Session '{args.session}' not found in manifest.json")
        sys.exit(1)

    session = sessions[args.session]
    status = session.get("status", "")
    session_dir = X37_DIR / "sessions" / args.session

    if not session_dir.is_dir():
        print(f"ERROR: Session directory not found: {session_dir}")
        sys.exit(1)

    if args.phase is None:
        print(f"{args.session}: status={status}, state={_describe_session(session_dir)}")
        for phase_id, meta in PHASES.items():
            runner = session_dir / meta["runner"]  # type: ignore[index]
            available = "yes" if runner.exists() else "no"
            print(f"phase {phase_id}: runner={runner.relative_to(session_dir)} exists={available}")
        return

    if status != "ACTIVE":
        print(f"ERROR: Session '{args.session}' is not ACTIVE (status={status})")
        sys.exit(1)

    session_plan = session_dir / "PLAN.md"
    if not session_plan.exists():
        print(f"ERROR: Session PLAN.md not found at {session_plan} (preregistration required before execution)")
        sys.exit(1)

    meta = PHASES[args.phase]
    runner = session_dir / meta["runner"]  # type: ignore[index]
    if not runner.exists():
        print(f"ERROR: Runner not found for phase {args.phase}: {runner}")
        sys.exit(1)

    missing = _missing_paths(session_dir, meta["requires"])  # type: ignore[arg-type]
    if missing:
        print(f"ERROR: phase {args.phase} is gated by missing artifacts:")
        for path in missing:
            print(f"  - {path}")
        sys.exit(1)

    if args.phase in {"4", "5", "6"}:
        phase3_results = session_dir / "phase3_design/results"
        if not _has_non_figure_artifact(phase3_results):
            print(f"ERROR: phase {args.phase} requires at least one non-figure artifact in phase3_design/results/")
            sys.exit(1)

    blocked = [path for path in meta["blocks_if_exists"] if (session_dir / path).exists()]  # type: ignore[index]
    if blocked:
        print(f"ERROR: phase {args.phase} is blocked because later or irreversible artifacts already exist:")
        for path in blocked:
            print(f"  - {path}")
        sys.exit(1)

    if args.phase == "1":
        protocol_errors = _validate_protocol(session_dir / "phase0_protocol/protocol_freeze.json")
        if protocol_errors:
            print("ERROR: protocol_freeze.json is not valid for Phase 1:")
            for message in protocol_errors:
                print(f"  - {message}")
            sys.exit(1)

    run(runner)


if __name__ == "__main__":
    main()
