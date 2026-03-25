"""Lookahead sanity suite based on HTF no-lookahead tests.

Uses auto-discovery to find strategy-specific lookahead/causality tests
in tests/, supplementing the static engine-level test list.  Any test
file in tests/ whose content contains ``TestD1RegimeNoLookahead`` or
the substring ``lookahead`` (case-insensitive) is automatically included.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from validation.output import write_text
from validation.suites.base import BaseSuite, SuiteContext, SuiteResult


# Static engine-level HTF alignment tests (always included).
_STATIC_TEST_FILES = [
    "v10/tests/test_no_lookahead_htf.py",
    "v10/tests/test_v10_no_lookahead_htf.py",
    "v10/tests/test_mtf_alignment.py",
]


def _discover_lookahead_tests(project_root: Path) -> list[str]:
    """Auto-discover strategy-specific lookahead test files from tests/.

    Scans tests/test_*.py and matches on:
      1. Filename contains ``lookahead`` (case-insensitive), OR
      2. File content contains ``TestD1RegimeNoLookahead``, OR
      3. File content contains ``lookahead`` (case-insensitive).

    Returns paths relative to *project_root*.
    """
    discovered: list[str] = []
    tests_dir = project_root / "tests"
    if not tests_dir.is_dir():
        return discovered
    for test_file in sorted(tests_dir.glob("test_*.py")):
        # Match on filename first (avoids reading content unnecessarily).
        if "lookahead" in test_file.name.lower():
            discovered.append(str(test_file.relative_to(project_root)))
            continue
        try:
            content = test_file.read_text(errors="ignore")
        except OSError:
            continue
        if "TestD1RegimeNoLookahead" in content or "lookahead" in content.lower():
            discovered.append(str(test_file.relative_to(project_root)))
    return discovered


class LookaheadSuite(BaseSuite):
    def name(self) -> str:
        return "lookahead"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if not ctx.validation_config.lookahead_check:
            return "lookahead check disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        artifacts: list[Path] = []

        # Merge static engine tests + auto-discovered strategy tests (deduplicated).
        discovered = _discover_lookahead_tests(ctx.project_root)
        all_rel_paths = list(dict.fromkeys(_STATIC_TEST_FILES + discovered))
        test_files = [
            str(ctx.project_root / rel)
            for rel in all_rel_paths
            if (ctx.project_root / rel).exists()
        ]

        if not test_files:
            out = (
                "FAIL\n"
                "No lookahead test files found. When lookahead_check is enabled,\n"
                "at least one test must exist to verify causality.\n"
                f"Searched static: {_STATIC_TEST_FILES}\n"
                f"Discovered: {discovered}\n"
            )
            txt_path = write_text(out, ctx.results_dir / "lookahead_check.txt")
            artifacts.append(txt_path)
            return SuiteResult(
                name=self.name(),
                status="fail",
                data={"test_files": [], "reason": "no_tests_found"},
                artifacts=artifacts,
                duration_seconds=time.time() - t0,
            )

        cmd = [sys.executable, "-m", "pytest", "-q", *test_files]
        ctx.logger.info("  lookahead: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(ctx.project_root),
                capture_output=True,
                text=True,
                timeout=600,
            )
            exit_code = int(proc.returncode)
            output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        except subprocess.TimeoutExpired as exc:
            exit_code = -1
            output = f"pytest timeout: {exc}"
        except Exception as exc:
            exit_code = -1
            output = f"pytest failed: {exc}"

        status = "pass" if exit_code == 0 else "fail"
        header = "PASS" if status == "pass" else "FAIL"

        body = [
            header,
            f"exit_code={exit_code}",
            f"tests={len(test_files)}",
            "",
            output.strip(),
            "",
        ]
        txt_path = write_text("\n".join(body), ctx.results_dir / "lookahead_check.txt")
        artifacts.append(txt_path)

        return SuiteResult(
            name=self.name(),
            status=status,
            data={"exit_code": exit_code, "test_files": test_files},
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
