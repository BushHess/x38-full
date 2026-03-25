"""Tests for lookahead test auto-discovery logic.

Regression: _discover_lookahead_tests() previously only checked file content
for keywords, missing test files whose names contained 'lookahead' but whose
content did not (e.g., tests/test_d1_regime_lookahead.py).
"""

from __future__ import annotations

from pathlib import Path

from validation.suites.lookahead import _discover_lookahead_tests


def test_discovers_file_by_filename(tmp_path: Path) -> None:
    """Files with 'lookahead' in the filename are discovered even if
    the content does not contain the keyword."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    # File with 'lookahead' in name but NOT in content
    (tests_dir / "test_d1_regime_lookahead.py").write_text(
        "def test_regime_uses_only_completed_bar(): pass\n"
    )

    discovered = _discover_lookahead_tests(tmp_path)
    assert "tests/test_d1_regime_lookahead.py" in discovered


def test_discovers_file_by_content_keyword(tmp_path: Path) -> None:
    """Files with 'lookahead' in content are discovered."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_something.py").write_text(
        "class TestNoLookahead:\n    pass\n"
    )

    discovered = _discover_lookahead_tests(tmp_path)
    assert "tests/test_something.py" in discovered


def test_discovers_file_by_class_name(tmp_path: Path) -> None:
    """Files with TestD1RegimeNoLookahead class are discovered."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_vtrend_x0.py").write_text(
        "class TestD1RegimeNoLookahead:\n    pass\n"
    )

    discovered = _discover_lookahead_tests(tmp_path)
    assert "tests/test_vtrend_x0.py" in discovered


def test_no_false_positives(tmp_path: Path) -> None:
    """Files without any lookahead keyword in name or content are excluded."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_engine.py").write_text(
        "def test_engine_runs(): pass\n"
    )

    discovered = _discover_lookahead_tests(tmp_path)
    assert discovered == []


def test_no_duplicates_when_both_match(tmp_path: Path) -> None:
    """A file matching both filename and content appears only once."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "test_lookahead_check.py").write_text(
        "# Tests for lookahead validation\ndef test_no_lookahead(): pass\n"
    )

    discovered = _discover_lookahead_tests(tmp_path)
    assert discovered.count("tests/test_lookahead_check.py") == 1
