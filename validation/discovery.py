"""Repository discovery for legacy/ad-hoc validation checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from validation.output import write_text


_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("dd_episode", "drawdown", "mdd"), "dd_episodes"),
    (("bootstrap", "block_bootstrap"), "bootstrap"),
    (("wfo", "walkforward"), "wfo"),
    (("holdout",), "holdout"),
    (("lookahead", "no_lookahead", "mtf_alignment"), "lookahead"),
    (("overlay", "cooldown", "decel", "exposure_cap", "peak_to_trough"), "overlay"),
    (("trade_level", "matched_trades", "window_trade", "reentry"), "trade_level"),
    (("selection_bias", "deflated", "pbo"), "selection_bias"),
    (("regime", "topping", "late_bull"), "regime"),
    (("sensitivity", "grid", "trail_tighten"), "sensitivity"),
    (("decision", "verdict"), "decision"),
]


def _map_module(name: str) -> str:
    lname = name.lower()
    for keywords, module in _KEYWORD_MAP:
        if any(keyword in lname for keyword in keywords):
            return module
    return "additional"


def _should_scan(path: Path) -> bool:
    text = str(path)
    if "/.git/" in text or "/__pycache__/" in text:
        return False
    if text.endswith(".pyc"):
        return False
    return True


def discover_checks(project_root: Path, executed_suites: set[str]) -> list[dict[str, Any]]:
    """Scan repo outputs/scripts and map checks to suites."""
    discovered: list[dict[str, Any]] = []

    for path in project_root.rglob("*"):
        if not path.is_file() or not _should_scan(path):
            continue

        rel = path.relative_to(project_root)
        rel_str = str(rel)
        lower = rel_str.lower()

        in_output = rel.parts and (rel.parts[0] == "out" or rel.parts[0].startswith("out_"))
        in_scripts = "scripts" in rel.parts

        is_candidate = False
        if in_scripts and path.suffix == ".py":
            is_candidate = True
        if in_output and path.suffix in {".py", ".csv", ".json", ".md", ".txt"}:
            if any(k in lower for k in [
                "dd_episode", "bootstrap", "wfo", "walkforward", "decision",
                "regime", "trail_tighten", "lookahead", "holdout", "overlay",
                "trade", "matched", "verdict", "selection_bias", "deflated", "pbo",
            ]):
                is_candidate = True

        if not is_candidate:
            continue

        mapped = _map_module(rel_str)
        discovered.append(
            {
                "path": rel_str,
                "mapped_module": mapped,
                "integrated": mapped in executed_suites,
                "source_type": "script" if path.suffix == ".py" else "artifact",
            }
        )

    discovered.sort(key=lambda row: row["path"])
    return discovered


def write_discovered_tests_report(
    discovered: list[dict[str, Any]],
    output_path: Path,
) -> Path:
    lines: list[str] = []
    lines.append("# Discovered Tests")
    lines.append("")
    lines.append("| Path | Type | Mapped Module | Integrated |")
    lines.append("|---|---|---|---|")

    for row in discovered:
        integrated = "yes" if row.get("integrated") else "no"
        lines.append(
            f"| `{row.get('path')}` | {row.get('source_type')} | "
            f"`{row.get('mapped_module')}` | {integrated} |"
        )

    if not discovered:
        lines.append("| (none) | - | - | - |")

    return write_text("\n".join(lines), output_path)
