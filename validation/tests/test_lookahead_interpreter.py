"""Tests for LookaheadSuite subprocess interpreter path.

Regression: LookaheadSuite used hardcoded 'python' instead of
sys.executable, causing [Errno 2] in venv environments.
"""

from __future__ import annotations

from pathlib import Path


class TestLookaheadInterpreter:
    """LookaheadSuite must use the current Python interpreter."""

    def test_uses_sys_executable(self) -> None:
        """The module must import sys and reference sys.executable."""
        import validation.suites.lookahead as mod

        source = Path(mod.__file__).read_text()
        assert "sys.executable" in source, (
            "LookaheadSuite should use sys.executable, not hardcoded 'python'"
        )
        assert "import sys" in source

    def test_no_hardcoded_python_in_cmd(self) -> None:
        """The cmd list must NOT start with bare 'python' string."""
        import validation.suites.lookahead as mod

        source = Path(mod.__file__).read_text()
        assert '[sys.executable, "-m", "pytest"' in source or \
               "[sys.executable, '-m', 'pytest'" in source, (
            "Expected cmd to use sys.executable, not 'python'"
        )
