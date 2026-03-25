"""Consistency audit for research/x37 governance and execution guardrails."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"
README = ROOT / "README.md"
PLAN = ROOT / "PLAN.md"
RULES = ROOT / "x37_RULES.md"
SESSIONS_README = ROOT / "sessions" / "README.md"
SESSION_TEMPLATE = ROOT / "sessions" / "SESSION_TEMPLATE.md"
PROTOCOL_TEMPLATE = ROOT / "sessions" / "PROTOCOL_FREEZE_TEMPLATE.json"
RUN_ALL = ROOT / "code" / "run_all.py"
ANALYSIS_README = ROOT / "analysis" / "README.md"
RESULTS_README = ROOT / "results" / "README.md"


class AuditError(RuntimeError):
    """Raised when the x37 audit fails."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise AuditError(f"{path.name} is not valid JSON: {exc}") from exc


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit_session_statuses(manifest: dict) -> None:
    _require(
        manifest.get("session_lifecycle") == ["PLANNED", "ACTIVE", "DONE", "ABANDONED"],
        "unexpected session_lifecycle",
    )
    _require(
        manifest.get("editable_session_statuses") == ["PLANNED", "ACTIVE"],
        "editable_session_statuses must be ['PLANNED', 'ACTIVE']",
    )
    _require(
        manifest.get("closed_session_statuses") == ["DONE", "ABANDONED"],
        "closed_session_statuses must be ['DONE', 'ABANDONED']",
    )
    _require(
        manifest.get("session_entry_schema", {}).get("required_fields")
        == [
            "id",
            "path",
            "status",
            "agent",
            "prompt_version",
            "started_at",
            "phase_reached",
            "verdict",
            "notes",
        ],
        "unexpected session_entry_schema.required_fields",
    )


def _audit_root_state(manifest: dict) -> None:
    sessions = manifest.get("sessions", [])
    active = [session for session in sessions if session.get("status") == "ACTIVE"]
    study_status = manifest.get("study_status")
    study_status_definitions = manifest.get("study_status_definitions")

    _require(
        study_status_definitions == {
            "READY_NO_ACTIVE_SESSIONS": "no ACTIVE sessions are currently registered; x37 is ready for a new session or waiting between sessions",
            "ACTIVE_SESSIONS_PRESENT": "at least one ACTIVE session is currently registered",
        },
        "unexpected study_status_definitions",
    )

    if not sessions:
        _require(
            study_status == "READY_NO_ACTIVE_SESSIONS",
            "empty session registry must use study_status READY_NO_ACTIVE_SESSIONS",
        )
    if active:
        _require(
            study_status == "ACTIVE_SESSIONS_PRESENT",
            "ACTIVE sessions require study_status ACTIVE_SESSIONS_PRESENT",
        )
    if sessions and not active:
        _require(
            study_status == "READY_NO_ACTIVE_SESSIONS",
            "no ACTIVE sessions should map to study_status READY_NO_ACTIVE_SESSIONS",
        )


def _audit_phase_registry(manifest: dict, run_all_module) -> None:
    phase_order = {phase["id"]: phase for phase in manifest.get("phase_order", [])}
    expected_runnable = {"1", "3", "4", "5", "6"}

    _require(set(run_all_module.PHASES) == expected_runnable, "run_all PHASE list drifted")
    _require(phase_order["0"]["runner"] is None, "phase 0 runner must remain null")
    _require(phase_order["2"]["runner"] is None, "phase 2 runner must remain null")

    for phase_id in expected_runnable:
        manifest_runner = phase_order[phase_id]["runner"]
        runtime_runner = str(run_all_module.PHASES[phase_id]["runner"])
        _require(manifest_runner == runtime_runner, f"runner mismatch for phase {phase_id}")

    _require(
        phase_order["3"].get("required_artifact_rule") == "at least one non-figure artifact under phase3_design/results/",
        "phase 3 manifest rule must describe non-figure artifact requirement",
    )
    for phase_id in expected_runnable:
        manifest_phase = phase_order[phase_id]
        runtime_phase = run_all_module.PHASES[phase_id]
        manifest_prereqs = manifest_phase.get("prerequisites", [])
        runtime_prereqs = [str(path) for path in runtime_phase["requires"]]
        _require(manifest_prereqs == runtime_prereqs, f"prerequisite mismatch for phase {phase_id}")
        manifest_blocks = manifest_phase.get("blocking_artifacts", [])
        runtime_blocks = [str(path) for path in runtime_phase["blocks_if_exists"]]
        _require(manifest_blocks == runtime_blocks, f"blocking artifact mismatch for phase {phase_id}")


def _audit_protocol_template(run_all_module) -> None:
    protocol = _load_json(PROTOCOL_TEMPLATE)
    _require(protocol["walk_forward"]["windows"] == [], "protocol template windows must start empty")
    _require(
        protocol["execution"]["d1_h4_alignment"]["allow_exact_matches"] is None,
        "protocol template allow_exact_matches must start as null",
    )

    errors = run_all_module._validate_protocol(PROTOCOL_TEMPLATE)
    expected = {
        "protocol_freeze.json must define at least 4 walk-forward windows",
        "execution.d1_h4_alignment.allow_exact_matches must be a boolean",
    }
    _require(expected.issubset(set(errors)), "protocol template must fail on empty windows and null allow_exact_matches")
    # Template has all required sections, so only windows + alignment should fail
    section_errors = [e for e in errors if "must contain a" in e]
    _require(len(section_errors) == 0, "protocol template must have all required top-level sections")


def _audit_frozen_resources(manifest: dict) -> None:
    for resource in manifest.get("frozen_resources", []):
        resource_path = ROOT / resource
        _require(resource_path.exists(), f"frozen resource missing: {resource}")


def _audit_text(manifest: dict) -> None:
    readme = README.read_text()
    plan = PLAN.read_text()
    rules = RULES.read_text()
    sessions_readme = SESSIONS_README.read_text()
    session_template = SESSION_TEMPLATE.read_text()
    analysis_readme = ANALYSIS_README.read_text()
    results_readme = RESULTS_README.read_text()

    _require("READY_NO_ACTIVE_SESSIONS" in readme, "README missing current empty-state status")
    _require("READY_NO_ACTIVE_SESSIONS" in plan, "PLAN missing current empty-state status")
    _require("source of truth" in readme, "README must declare session-registry authority")
    _require("source of truth" in rules, "rules must declare manifest authority")
    _require("Session `PLANNED` vẫn writable." in rules, "rules must explicitly keep PLANNED sessions writable")
    _require("phase5_freeze/frozen_spec.md" in rules, "rules must mention frozen_spec.md in phase 6 gating")
    _require("`prerequisites`" in rules and "`blocking_artifacts`" in rules, "rules must explain manifest phase gating keys")
    _require("Appendix A benchmark specs are embargoed" in session_template, "session template missing benchmark embargo acknowledgement")
    _require("--phase 1" in sessions_readme, "sessions README missing safe runner usage")
    _require('"phase_reached": 0' in sessions_readme, "sessions README missing manifest session entry example")
    _require("analysis/" in analysis_readme, "analysis README missing analysis scope")
    _require("Final deliverables của session nằm trong `sessions/sNN_*/verdict/`." in results_readme, "results README must explain final deliverables location")
    _require("không chứa canonical outputs" in results_readme, "results README must keep root results index-only")
    _require(manifest.get("current_prompt_version") == "V4", "manifest current_prompt_version must remain V4")


def _audit_session_registry(manifest: dict) -> None:
    session_dirs = sorted(
        path.name
        for path in (ROOT / "sessions").iterdir()
        if path.is_dir() and path.name.startswith("s")
    )
    registered = sorted(session.get("id") for session in manifest.get("sessions", []))
    _require(session_dirs == registered, "session directories and manifest sessions array are out of sync")
    valid_statuses = set(manifest.get("session_lifecycle", []))
    valid_verdicts = {None, "SUPERIOR", "COMPETITIVE", "NO_ROBUST_IMPROVEMENT", "ABANDONED"}
    for session in manifest.get("sessions", []):
        for field in manifest["session_entry_schema"]["required_fields"]:
            _require(field in session, f"session entry missing required field: {field}")
        sid = session["id"]
        _require(session["path"] == f"sessions/{sid}/", f"session {sid} has wrong path field")
        _require(session["status"] in valid_statuses, f"session {sid} has invalid status")
        _require(session["prompt_version"] == manifest["current_prompt_version"], f"session {sid} prompt_version drifted from root")
        _require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", session["started_at"]) is not None, f"session {sid} started_at must be YYYY-MM-DD")
        _require(session["phase_reached"] in [0, 1, 2, 3, 4, 5, 6], f"session {sid} has invalid phase_reached")
        _require(session["verdict"] in valid_verdicts, f"session {sid} has invalid verdict")
        _require(isinstance(session["agent"], str) and session["agent"], f"session {sid} agent must be a non-empty string")
        _require(session["notes"] is None or isinstance(session["notes"], str), f"session {sid} notes must be string or null")


def _audit_runner_behavior() -> None:
    source_runner = RUN_ALL

    def write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def make_manifest(status: str = "ACTIVE") -> dict:
        return {"sessions": [{"id": "s01_mock", "status": status}]}

    def valid_protocol() -> dict:
        return {
            "data": {"file": "data/bars.csv", "cutoff": "2026-02-20", "timeframes": ["H4", "D1"]},
            "splits": {
                "warmup": {"start": "2017-08-17", "end": "2018-12-31"},
                "development": {"start": "2019-01-01", "end": "2023-12-31"},
                "holdout": {"start": "2024-01-01", "end": "2026-02-20"},
            },
            "walk_forward": {
                "windows": [
                    {"test_start": "2019-01-01", "test_end": "2019-06-30"},
                    {"test_start": "2020-01-01", "test_end": "2020-06-30"},
                    {"test_start": "2021-01-01", "test_end": "2021-06-30"},
                    {"test_start": "2022-01-01", "test_end": "2022-06-30"},
                ]
            },
            "cost": {"per_side_bps": 10, "round_trip_bps": 20},
            "execution": {"d1_h4_alignment": {"allow_exact_matches": True}},
            "evaluation": {"metrics": ["sharpe", "cagr", "mdd"]},
            "hard_criteria": {"positive_edge_after_cost": True},
        }

    def stub_runner(message: str) -> str:
        return (
            "from pathlib import Path\n"
            f"print('{message}')\n"
            f"Path('runner_touched.txt').write_text('{message}')\n"
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "x37"
        (root / "code").mkdir(parents=True)
        shutil.copy2(source_runner, root / "code" / "run_all.py")

        write(root / "manifest.json", json.dumps(make_manifest(), indent=2))
        write(root / "sessions" / "s01_mock" / "PLAN.md", "# s01_mock PLAN")
        write(
            root / "sessions" / "s01_mock" / "phase0_protocol" / "protocol_freeze.json",
            json.dumps(
                {
                    "walk_forward": {"windows": []},
                    "execution": {"d1_h4_alignment": {"allow_exact_matches": None}},
                },
                indent=2,
            ),
        )
        write(
            root / "sessions" / "s01_mock" / "phase1_decomposition" / "code" / "run_phase1.py",
            stub_runner("phase1"),
        )

        # --- Test: reject invalid protocol ---
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "code" / "run_all.py"),
                "--session",
                "s01_mock",
                "--phase",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _require(proc.returncode == 1, "runner must reject invalid phase 1 protocol")
        _require(
            "protocol_freeze.json is not valid for Phase 1" in proc.stdout,
            "runner must explain invalid phase 1 protocol",
        )

        # --- Test: reject PLANNED session ---
        write(root / "manifest.json", json.dumps(make_manifest(status="PLANNED"), indent=2))
        write(
            root / "sessions" / "s01_mock" / "phase0_protocol" / "protocol_freeze.json",
            json.dumps(valid_protocol(), indent=2),
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "code" / "run_all.py"),
                "--session",
                "s01_mock",
                "--phase",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _require(proc.returncode == 1, "runner must reject PLANNED session (not ACTIVE)")
        _require(
            "is not ACTIVE" in proc.stdout,
            "runner must explain PLANNED session rejection",
        )

        # --- Test: reject missing PLAN.md ---
        write(root / "manifest.json", json.dumps(make_manifest(), indent=2))
        (root / "sessions" / "s01_mock" / "PLAN.md").unlink()
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "code" / "run_all.py"),
                "--session",
                "s01_mock",
                "--phase",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _require(proc.returncode == 1, "runner must reject session without PLAN.md")
        _require(
            "PLAN.md not found" in proc.stdout,
            "runner must explain missing PLAN.md rejection",
        )
        write(root / "sessions" / "s01_mock" / "PLAN.md", "# s01_mock PLAN")

        # --- Test: valid phase 1 execution ---
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "code" / "run_all.py"),
                "--session",
                "s01_mock",
                "--phase",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _require(proc.returncode == 0, "runner must allow valid phase 1 execution")
        _require(
            ">>> Running: sessions/s01_mock/phase1_decomposition/code/run_phase1.py" in proc.stdout,
            "runner must execute phase 1 script when protocol is valid",
        )

        # --- Setup for higher phases ---
        write(root / "sessions" / "s01_mock" / "phase1_decomposition" / "results" / "measurements.csv", "a\n1\n")
        write(root / "sessions" / "s01_mock" / "phase1_decomposition" / "results" / "channel_report.md", "# report")
        write(root / "sessions" / "s01_mock" / "phase1_decomposition" / "results" / "d1_h4_alignment.json", '{"status":"PASS"}')
        write(root / "sessions" / "s01_mock" / "phase2_hypotheses" / "hypotheses.md", "# hypotheses")

        # --- Test: phase 4 rejected when phase3 has only figures ---
        (root / "sessions" / "s01_mock" / "phase3_design" / "results" / "figures").mkdir(parents=True, exist_ok=True)
        write(root / "sessions" / "s01_mock" / "phase3_design" / "results" / "figures" / "chart.png", "fake")
        write(root / "sessions" / "s01_mock" / "phase4_parameters" / "code" / "run_phase4.py", stub_runner("phase4"))
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "code" / "run_all.py"),
                "--session",
                "s01_mock",
                "--phase",
                "4",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _require(proc.returncode == 1, "runner must reject phase 4 when phase3 has only figure artifacts")
        _require(
            "non-figure artifact" in proc.stdout,
            "runner must explain missing non-figure artifact for phase 4",
        )

        # --- Test: phase 4 allowed with non-figure artifact ---
        write(root / "sessions" / "s01_mock" / "phase3_design" / "results" / "ablation.md", "ok")
        write(root / "sessions" / "s01_mock" / "phase4_parameters" / "results" / "search_results.csv", "a,b\n1,2\n")
        write(root / "sessions" / "s01_mock" / "phase4_parameters" / "results" / "plateau_test.csv", "a,b\n1,2\n")

        # --- Test: phase 5 blocked after freeze artifacts ---
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "code" / "run_phase5.py", stub_runner("phase5"))
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "frozen_spec.md", "# frozen spec")
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "frozen_spec.json", "{}")
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "code" / "run_all.py"),
                "--session",
                "s01_mock",
                "--phase",
                "5",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _require(proc.returncode == 1, "runner must block phase 5 after freeze artifacts exist")
        _require(
            "blocked because later or irreversible artifacts already exist" in proc.stdout,
            "runner must explain blocked phase 5 rerun",
        )

        # --- Test: phase 6 allowed after all phase 5 artifacts ---
        write(root / "sessions" / "s01_mock" / "phase6_benchmark" / "code" / "run_phase6.py", stub_runner("phase6"))
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "results" / "holdout_results.csv", "a\n1\n")
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "results" / "regime_decomposition.csv", "a\n1\n")
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "results" / "cost_sensitivity.csv", "a\n1\n")
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "results" / "bootstrap_summary.csv", "a\n1\n")
        write(root / "sessions" / "s01_mock" / "phase5_freeze" / "results" / "trade_distribution.csv", "a\n1\n")
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "code" / "run_all.py"),
                "--session",
                "s01_mock",
                "--phase",
                "6",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        _require(proc.returncode == 0, "runner must allow phase 6 only after all phase 5 artifacts exist")
        _require(
            ">>> Running: sessions/s01_mock/phase6_benchmark/code/run_phase6.py" in proc.stdout,
            "runner must execute phase 6 script after prerequisites are satisfied",
        )


def main() -> None:
    required_files = [
        MANIFEST,
        README,
        PLAN,
        RULES,
        SESSIONS_README,
        SESSION_TEMPLATE,
        PROTOCOL_TEMPLATE,
        RUN_ALL,
        ANALYSIS_README,
        RESULTS_README,
    ]
    for path in required_files:
        _require(path.exists(), f"missing required x37 file: {path}")

    manifest = _load_json(MANIFEST)
    run_all_module = _load_module(RUN_ALL, "x37_run_all_audit")

    _audit_session_statuses(manifest)
    _audit_root_state(manifest)
    _audit_phase_registry(manifest, run_all_module)
    _audit_protocol_template(run_all_module)
    _audit_frozen_resources(manifest)
    _audit_text(manifest)
    _audit_session_registry(manifest)
    _audit_runner_behavior()

    print("x37 audit: PASS")


if __name__ == "__main__":
    try:
        main()
    except AuditError as exc:
        print(f"x37 audit: FAIL - {exc}")
        sys.exit(1)
