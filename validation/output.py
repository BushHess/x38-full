"""Output helpers for the validation pipeline."""

from __future__ import annotations

import csv
import json
import math
import shutil
from dataclasses import asdict
from dataclasses import is_dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from validation.config import ValidationConfig


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return str(obj)


def _sanitize_for_json(value: Any) -> Any:
    """Recursively normalize values to strict-JSON-safe primitives."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (np.floating,)):
        f = float(value)
        return f if math.isfinite(f) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.ndarray):
        return [_sanitize_for_json(item) for item in value.tolist()]
    if is_dataclass(value) and not isinstance(value, type):
        return _sanitize_for_json(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_for_json(item) for item in value]
    return value


def write_json(data: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _sanitize_for_json(data)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=_json_default, allow_nan=False)
    return path


def write_csv(rows: list[dict[str, Any]], path: Path,
              fieldnames: list[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and fieldnames is None:
        path.write_text("")
        return path

    if fieldnames is None:
        first = rows[0] if rows else {}
        fieldnames = list(first.keys())

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    return path


def write_text(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def copy_configs(config: ValidationConfig, outdir: Path) -> list[Path]:
    """Copy candidate/baseline YAML into outdir/configs."""
    configs_dir = outdir / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[Path] = []
    mapping = [
        (config.config_path, f"candidate_{config.config_path.name}"),
        (config.baseline_config_path, f"baseline_{config.baseline_config_path.name}"),
    ]
    for source, name in mapping:
        target = configs_dir / name
        if source.exists():
            shutil.copy2(source, target)
            artifacts.append(target)

    return artifacts


def write_decision_json(decision: Any, outdir: Path) -> Path:
    """Write decision payload to reports/decision.json."""
    payload = {
        "verdict": decision.tag,
        "exit_code": decision.exit_code,
        "deltas": decision.deltas,
        "trade_level_bootstrap": decision.trade_level_bootstrap,
        "failures": decision.failures,
        "warnings": decision.warnings,
        "errors": decision.errors,
        "reasons": decision.reasons,
        "key_links": decision.key_links,
        "gates": [
            {
                "name": gate.gate_name,
                "passed": gate.passed,
                "severity": gate.severity,
                "detail": gate.detail,
            }
            for gate in decision.gates
        ],
        "metadata": decision.metadata,
    }
    return write_json(payload, outdir / "reports" / "decision.json")


def write_index(
    outdir: Path,
    results: dict[str, Any],
    decision: Any,
    config: ValidationConfig,
) -> Path:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "VALIDATION OUTPUT INDEX",
        "=" * 48,
        f"Generated: {now}",
        f"Candidate: {config.strategy_name}",
        f"Baseline: {config.baseline_name}",
        f"Suite: {config.suite}",
        f"Scenarios: {','.join(config.scenarios)}",
        f"Seed: {config.seed}",
        "",
    ]

    for label, subdir in [
        ("logs", "logs"),
        ("configs", "configs"),
        ("results", "results"),
        ("reports", "reports"),
    ]:
        lines.append(f"[{label}]")
        folder = outdir / subdir
        if folder.exists():
            for file in sorted(folder.rglob("*")):
                if file.is_file():
                    lines.append(str(file.relative_to(outdir)))
        lines.append("")

    lines.append("[suite_status]")
    for suite_name, suite_result in results.items():
        detail = f" ({suite_result.error_message})" if suite_result.error_message else ""
        lines.append(f"{suite_name}: {suite_result.status}{detail}")

    lines.append("")
    lines.append("[decision]")
    lines.append(f"verdict={decision.tag}")
    lines.append(f"exit_code={decision.exit_code}")
    for reason in decision.reasons:
        lines.append(f"- {reason}")

    path = outdir / "index.txt"
    path.write_text("\n".join(lines))
    return path
