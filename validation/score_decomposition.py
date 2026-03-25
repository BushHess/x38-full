"""Score-decomposition report helpers."""

from __future__ import annotations

from typing import Any
from typing import Iterable
from typing import Mapping

from v10.research.objective import OBJECTIVE_TERM_ORDER


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def residual_max_abs(rows: Iterable[Mapping[str, Any]]) -> float:
    max_abs = 0.0
    for row in rows:
        residual = abs(_to_float(row.get("residual"), default=0.0))
        max_abs = max(max_abs, residual)
    return max_abs


def residual_within_tolerance(
    rows: Iterable[Mapping[str, Any]],
    *,
    tolerance: float = 1e-6,
) -> bool:
    return residual_max_abs(rows) <= tolerance


def build_score_decomposition_report(
    *,
    full_rows: list[Mapping[str, Any]],
    holdout_rows: list[Mapping[str, Any]],
    tolerance: float = 1e-6,
) -> str:
    lines: list[str] = [
        "# Score decomposition audit",
        "",
    ]

    full_max = residual_max_abs(full_rows)
    holdout_max = residual_max_abs(holdout_rows)
    full_ok = full_max <= tolerance
    holdout_ok = holdout_max <= tolerance

    lines.extend(
        [
            "## Residual check",
            "",
            f"- Full period residual max abs: `{full_max:.12f}` "
            f"(tol `{tolerance:.1e}`) -> **{'PASS' if full_ok else 'FAIL'}**",
            f"- Holdout residual max abs: `{holdout_max:.12f}` "
            f"(tol `{tolerance:.1e}`) -> **{'PASS' if holdout_ok else 'FAIL'}**",
            "",
        ]
    )

    lines.extend(
        [
            "## Top delta terms (candidate - baseline)",
            "",
            "| period | scenario | total_delta | term_1 | delta_1 | term_2 | delta_2 |",
            "|---|---|---:|---|---:|---|---:|",
        ]
    )

    for period, rows in [("full", full_rows), ("holdout", holdout_rows)]:
        by_scenario: dict[str, dict[str, Mapping[str, Any]]] = {}
        for row in rows:
            scenario = str(row.get("scenario", ""))
            model = str(row.get("model", ""))
            if not scenario or not model:
                continue
            by_scenario.setdefault(scenario, {})[model] = row

        for scenario in sorted(by_scenario):
            models = by_scenario[scenario]
            candidate = models.get("candidate")
            baseline = models.get("baseline")
            if candidate is None or baseline is None:
                lines.append(f"| {period} | {scenario} | n/a | n/a | n/a | n/a | n/a |")
                continue

            total_delta = _to_float(candidate.get("total_score")) - _to_float(
                baseline.get("total_score")
            )

            deltas = []
            for term_name in OBJECTIVE_TERM_ORDER:
                delta = _to_float(candidate.get(term_name)) - _to_float(
                    baseline.get(term_name)
                )
                deltas.append((term_name, delta))
            deltas.sort(key=lambda item: abs(item[1]), reverse=True)
            top = deltas[:2] if len(deltas) >= 2 else deltas + [("n/a", 0.0)]

            lines.append(
                "| "
                f"{period} | {scenario} | {total_delta:.8f} | "
                f"{top[0][0]} | {top[0][1]:.8f} | "
                f"{top[1][0]} | {top[1][1]:.8f} |"
            )

    return "\n".join(lines) + "\n"
