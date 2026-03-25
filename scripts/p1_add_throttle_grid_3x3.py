#!/usr/bin/env python3
"""Run P1 add-throttle 3x3 robustness grid and write CSV/Markdown outputs."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import deque
from datetime import date
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

DD1_VALUES: tuple[float, ...] = (0.06, 0.08, 0.10)
DD2_VALUES: tuple[float, ...] = (0.14, 0.18, 0.22)
MULT: float = 0.20
SEED: int = 1505

FULL_START = "2019-01-01"
FULL_END = "2026-02-20"
HOLDOUT_FRAC = 0.20


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _fmt_cell(value: float) -> str:
    return str(value).replace(".", "p")


def _cell_slug(dd1: float, dd2: float) -> str:
    return f"dd1_{_fmt_cell(dd1)}_dd2_{_fmt_cell(dd2)}"


def _resolve_holdout_window(start: str, end: str, holdout_frac: float) -> tuple[str, str]:
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    # +1 for inclusive end date (DataFeed end is inclusive, see data.py line 78)
    total_days = max((end_date - start_date).days + 1, 1)
    holdout_days = max(int(total_days * holdout_frac), 1)
    holdout_start = end_date - timedelta(days=holdout_days)
    return holdout_start.isoformat(), end_date.isoformat()


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML object at {path}")
    return payload


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def _build_grid_config(
    *,
    template_path: Path,
    out_path: Path,
    dd1: float,
    dd2: float,
    mult: float,
) -> None:
    cfg = _load_yaml(template_path)
    strategy = cfg.setdefault("strategy", {})
    if not isinstance(strategy, dict):
        raise ValueError(f"strategy must be a dict in {template_path}")
    strategy["name"] = "v13_add_throttle"
    strategy["add_throttle_dd1"] = float(dd1)
    strategy["add_throttle_dd2"] = float(dd2)
    strategy["add_throttle_mult"] = float(mult)
    _write_yaml(out_path, cfg)


def _run_validate(
    *,
    repo_root: Path,
    config_path: Path,
    baseline_config: Path,
    out_dir: Path,
    start: str,
    end: str,
    force: bool,
    skip_existing: bool,
) -> None:
    results_dir = out_dir / "results"
    ready = (results_dir / "full_backtest_summary.csv").exists() and (results_dir / "trade_level_summary.json").exists()
    if skip_existing and ready:
        print(f"[skip] existing outputs: {out_dir}")
        return

    cmd = [
        sys.executable,
        "validate_strategy.py",
        "--strategy",
        "v13_add_throttle",
        "--baseline",
        "v8_apex",
        "--config",
        str(config_path),
        "--baseline-config",
        str(baseline_config),
        "--out",
        str(out_dir),
        "--suite",
        "trade",
        "--scenarios",
        "harsh",
        "--seed",
        str(SEED),
        "--trade-level",
        "on",
        "--start",
        start,
        "--end",
        end,
        "--bootstrap",
        "0",
        "--selection-bias",
        "none",
        "--data-integrity-check",
        "off",
        "--cost-sweep-bps",
        "",
        "--invariant-check",
        "off",
        "--churn-metrics",
        "off",
    ]
    if force:
        cmd.append("--force")

    print(f"[run] {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=repo_root, check=False)
    if completed.returncode not in {0, 1, 2}:
        raise RuntimeError(
            f"validate_strategy failed with exit code {completed.returncode} for {out_dir}"
        )


def _read_harsh_backtest_metrics(out_dir: Path) -> dict[str, float]:
    rows: dict[str, dict[str, str]] = {}
    csv_path = out_dir / "results" / "full_backtest_summary.csv"
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("scenario") == "harsh":
                label = str(row.get("label", "")).strip()
                if label:
                    rows[label] = row

    candidate = rows.get("candidate")
    baseline = rows.get("baseline")
    if not candidate or not baseline:
        raise ValueError(f"Missing harsh candidate/baseline rows in {csv_path}")

    cand_score = _safe_float(candidate.get("score"))
    base_score = _safe_float(baseline.get("score"))
    cand_nav = _safe_float(candidate.get("final_nav_mid"))
    base_nav = _safe_float(baseline.get("final_nav_mid"))
    cand_cagr = _safe_float(candidate.get("cagr_pct"))
    base_cagr = _safe_float(baseline.get("cagr_pct"))
    cand_mdd = _safe_float(candidate.get("max_drawdown_mid_pct"))
    base_mdd = _safe_float(baseline.get("max_drawdown_mid_pct"))
    cand_trades = _safe_int(candidate.get("trades"))
    base_trades = _safe_int(baseline.get("trades"))

    return {
        "delta_total_score_harsh": cand_score - base_score,
        "delta_final_nav_harsh": cand_nav - base_nav,
        "delta_cagr_harsh": cand_cagr - base_cagr,
        "delta_mdd_pp_harsh": cand_mdd - base_mdd,
        "delta_trade_count": float(cand_trades - base_trades),
    }


def _read_trade_level_metrics(out_dir: Path) -> dict[str, float]:
    payload = json.loads((out_dir / "results" / "trade_level_summary.json").read_text(encoding="utf-8"))
    bootstrap = dict(payload.get("trade_level_bootstrap", {}))
    return {
        "delta_fees_usd": _safe_float(payload.get("delta_fees_usd")),
        "delta_buy_fills_per_episode": _safe_float(payload.get("delta_buy_fills_per_episode")),
        "delta_emergency_dd_share_pp": _safe_float(payload.get("delta_emergency_dd_share_pp")),
        "bootstrap_mean_diff": _safe_float(bootstrap.get("mean_diff")),
        "ci95_low": _safe_float(bootstrap.get("ci95_low")),
        "ci95_high": _safe_float(bootstrap.get("ci95_high")),
        "p_gt_0": _safe_float(bootstrap.get("p_gt_0")),
    }


def _read_add_throttle_metrics(out_dir: Path) -> dict[str, float]:
    payload = json.loads((out_dir / "results" / "add_throttle_stats.json").read_text(encoding="utf-8"))
    candidate = dict(payload.get("candidate", {}))
    harsh = dict(candidate.get("harsh", {}))
    return {
        "add_attempt_count": float(_safe_int(harsh.get("add_attempt_count"))),
        "add_blocked_count": float(_safe_int(harsh.get("add_blocked_count"))),
        "throttle_activation_rate": _safe_float(harsh.get("throttle_activation_rate")),
    }


def _evaluate_pass_full(row: dict[str, Any]) -> tuple[bool, str]:
    failures: list[str] = []
    if _safe_float(row.get("delta_mdd_pp_harsh")) > 2.0:
        failures.append("MDD>+2pp")
    if _safe_float(row.get("ci95_high")) < 0.0:
        failures.append("CI95 strictly negative")

    improved = 0
    if _safe_float(row.get("delta_buy_fills_per_episode")) < 0.0:
        improved += 1
    if _safe_float(row.get("delta_fees_usd")) < 0.0:
        improved += 1
    if _safe_float(row.get("delta_emergency_dd_share_pp")) < 0.0:
        improved += 1
    if improved < 2:
        failures.append(f"pathology improvements={improved}/3")

    if failures:
        return False, "; ".join(failures)
    return True, "PASS"


def _evaluate_holdout_ok(row: dict[str, Any]) -> bool:
    return (_safe_float(row.get("ci95_high")) >= 0.0) and (_safe_float(row.get("delta_mdd_pp_harsh")) <= 2.0)


def _connected_components(pass_coords: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for start in sorted(pass_coords):
        if start in visited:
            continue
        queue: deque[tuple[int, int]] = deque([start])
        visited.add(start)
        comp: list[tuple[int, int]] = []
        while queue:
            i, j = queue.popleft()
            comp.append((i, j))
            for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                node = (ni, nj)
                if node in pass_coords and node not in visited:
                    visited.add(node)
                    queue.append(node)
        components.append(sorted(comp))
    return components


def _pick_largest_component(components: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    if not components:
        return []
    ranked = sorted(
        components,
        key=lambda comp: (
            len(comp),
            max((DD1_VALUES[i], DD2_VALUES[j]) for i, j in comp),
        ),
        reverse=True,
    )
    return ranked[0]


def _pick_representative(component: list[tuple[int, int]]) -> tuple[float, float] | None:
    if not component:
        return None
    row_ids = sorted({i for i, _ in component})
    col_ids = sorted({j for _, j in component})
    center = (row_ids[len(row_ids) // 2], col_ids[len(col_ids) // 2])
    if center in set(component):
        return DD1_VALUES[center[0]], DD2_VALUES[center[1]]
    mildest = max(component, key=lambda node: (DD1_VALUES[node[0]], DD2_VALUES[node[1]]))
    return DD1_VALUES[mildest[0]], DD2_VALUES[mildest[1]]


def _render_pass_map(full_rows_by_coord: dict[tuple[float, float], dict[str, Any]]) -> str:
    lines = ["| dd1 \\ dd2 | 0.14 | 0.18 | 0.22 |", "|---:|---:|---:|---:|"]
    for dd1 in DD1_VALUES:
        cells: list[str] = []
        for dd2 in DD2_VALUES:
            row = full_rows_by_coord[(dd1, dd2)]
            cells.append("PASS" if bool(row.get("pass_full")) else "FAIL")
        lines.append(f"| {dd1:.2f} | {cells[0]} | {cells[1]} | {cells[2]} |")
    return "\n".join(lines)


def _render_metric_heatmap(
    *,
    title: str,
    field: str,
    full_rows_by_coord: dict[tuple[float, float], dict[str, Any]],
    digits: int = 3,
) -> str:
    lines = [f"### {title}", "", "| dd1 \\ dd2 | 0.14 | 0.18 | 0.22 |", "|---:|---:|---:|---:|"]
    for dd1 in DD1_VALUES:
        formatted: list[str] = []
        for dd2 in DD2_VALUES:
            row = full_rows_by_coord[(dd1, dd2)]
            formatted.append(f"{_safe_float(row.get(field)):.{digits}f}")
        lines.append(f"| {dd1:.2f} | {formatted[0]} | {formatted[1]} | {formatted[2]} |")
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "dd1",
        "dd2",
        "mult",
        "period",
        "delta_total_score_harsh",
        "delta_final_nav_harsh",
        "delta_cagr_harsh",
        "delta_mdd_pp_harsh",
        "delta_trade_count",
        "delta_fees_usd",
        "delta_buy_fills_per_episode",
        "delta_emergency_dd_share_pp",
        "bootstrap_mean_diff",
        "ci95_low",
        "ci95_high",
        "p_gt_0",
        "add_attempt_count",
        "add_blocked_count",
        "throttle_activation_rate",
        "pass_full",
        "pass_full_reasons",
        "holdout_ok",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _write_markdown(
    *,
    path: Path,
    rows: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
    holdout_rows: list[dict[str, Any]],
    status: str,
    components: list[list[tuple[int, int]]],
    largest_component: list[tuple[int, int]],
    representative: tuple[float, float] | None,
) -> None:
    full_rows_by_coord = {(row["dd1"], row["dd2"]): row for row in full_rows}
    holdout_by_coord = {(row["dd1"], row["dd2"]): row for row in holdout_rows}
    largest_cells = [
        f"({DD1_VALUES[i]:.2f}, {DD2_VALUES[j]:.2f})"
        for i, j in sorted(largest_component)
    ]

    lines: list[str] = []
    lines.append("# P1 Add-Throttle Robustness Grid (3x3)")
    lines.append("")
    lines.append("Scope:")
    lines.append("- Selection uses **FULL harsh only** (`PASS_FULL`).")
    lines.append("- HOLDOUT is **reporting-only** (`HOLDOUT_OK`), not used for parameter selection.")
    lines.append(f"- Grid: dd1 in {list(DD1_VALUES)}, dd2 in {list(DD2_VALUES)}, mult fixed at {MULT:.2f}.")
    lines.append("")
    lines.append("## PASS_FULL Heatmap")
    lines.append("")
    lines.append(_render_pass_map(full_rows_by_coord))
    lines.append("")
    lines.append(_render_metric_heatmap(
        title="FULL Delta Score Heatmap (candidate - baseline)",
        field="delta_total_score_harsh",
        full_rows_by_coord=full_rows_by_coord,
        digits=3,
    ))
    lines.append("")
    lines.append(_render_metric_heatmap(
        title="FULL Delta MDD (pp) Heatmap",
        field="delta_mdd_pp_harsh",
        full_rows_by_coord=full_rows_by_coord,
        digits=3,
    ))
    lines.append("")
    lines.append("## FULL Cell Decisions (used for selection)")
    lines.append("")
    lines.append(
        "| dd1 | dd2 | PASS_FULL | reason | delta_score | delta_mdd_pp | "
        "ci95_high | delta_buy_fills/episode | delta_fees_usd | delta_emergency_dd_share_pp | "
        "add_attempt | add_blocked | activation |"
    )
    lines.append("|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in sorted(full_rows, key=lambda item: (item["dd1"], item["dd2"])):
        lines.append(
            f"| {row['dd1']:.2f} | {row['dd2']:.2f} | "
            f"{'PASS' if row.get('pass_full') else 'FAIL'} | {row.get('pass_full_reasons', '')} | "
            f"{_safe_float(row.get('delta_total_score_harsh')):.3f} | "
            f"{_safe_float(row.get('delta_mdd_pp_harsh')):.3f} | "
            f"{_safe_float(row.get('ci95_high')):.6f} | "
            f"{_safe_float(row.get('delta_buy_fills_per_episode')):.3f} | "
            f"{_safe_float(row.get('delta_fees_usd')):.2f} | "
            f"{_safe_float(row.get('delta_emergency_dd_share_pp')):.3f} | "
            f"{_safe_int(row.get('add_attempt_count'))} | "
            f"{_safe_int(row.get('add_blocked_count'))} | "
            f"{_safe_float(row.get('throttle_activation_rate')):.4f} |"
        )
    lines.append("")
    lines.append("## HOLDOUT (informational only, not used for selection)")
    lines.append("")
    lines.append(
        "| dd1 | dd2 | HOLDOUT_OK | delta_score | delta_mdd_pp | ci95_high | "
        "delta_buy_fills/episode | delta_fees_usd | delta_emergency_dd_share_pp | "
        "add_attempt | add_blocked | activation |"
    )
    lines.append("|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for dd1 in DD1_VALUES:
        for dd2 in DD2_VALUES:
            row = holdout_by_coord[(dd1, dd2)]
            lines.append(
                f"| {dd1:.2f} | {dd2:.2f} | "
                f"{'YES' if row.get('holdout_ok') else 'NO'} | "
                f"{_safe_float(row.get('delta_total_score_harsh')):.3f} | "
                f"{_safe_float(row.get('delta_mdd_pp_harsh')):.3f} | "
                f"{_safe_float(row.get('ci95_high')):.6f} | "
                f"{_safe_float(row.get('delta_buy_fills_per_episode')):.3f} | "
                f"{_safe_float(row.get('delta_fees_usd')):.2f} | "
                f"{_safe_float(row.get('delta_emergency_dd_share_pp')):.3f} | "
                f"{_safe_int(row.get('add_attempt_count'))} | "
                f"{_safe_int(row.get('add_blocked_count'))} | "
                f"{_safe_float(row.get('throttle_activation_rate')):.4f} |"
            )
    lines.append("")
    lines.append("## Component Summary (PASS_FULL map)")
    lines.append("")
    if components:
        for idx, component in enumerate(components, start=1):
            cells = ", ".join(f"({DD1_VALUES[i]:.2f},{DD2_VALUES[j]:.2f})" for i, j in component)
            lines.append(f"- Component {idx}: size={len(component)} cells={cells}")
    else:
        lines.append("- No PASS_FULL cells.")
    lines.append("")
    lines.append("## Recommended Region")
    lines.append("")
    if largest_component:
        lines.append(f"- Largest component size: {len(largest_component)}")
        lines.append(f"- Selected region cells: {', '.join(largest_cells)}")
    else:
        lines.append("- No passing region identified.")
    if representative is not None:
        rep_dd1, rep_dd2 = representative
        rep_name = f"p1_dd1_dd2_{_fmt_cell(rep_dd1)}_{_fmt_cell(rep_dd2)}.yaml"
        lines.append(
            "- Representative config: "
            f"`configs/v13/grid/{rep_name}` "
            f"(dd1={rep_dd1:.2f}, dd2={rep_dd2:.2f}, mult={MULT:.2f})"
        )
    else:
        lines.append("- Representative config: none")
    lines.append("")
    lines.append(
        f"**{status}** — "
        + (
            f"recommended region: {', '.join(largest_cells)}"
            if largest_cells
            else "decision: abandon P1 (no robust region)"
        )
    )
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="P1 add-throttle 3x3 robustness grid runner")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--force", action="store_true", help="Force rerun even when output folders exist")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip a run when expected result artifacts already exist (default: on)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    template_config = repo_root / "configs" / "v13" / "v13_add_throttle_default.yaml"
    baseline_config = repo_root / "configs" / "frozen" / "v10_baseline.yaml"
    config_grid_dir = repo_root / "configs" / "v13" / "grid"
    out_grid_root = repo_root / "out/v13_p1_grid"
    results_csv = repo_root / "results" / "p1_add_throttle_grid_3x3.csv"
    report_md = repo_root / "reports" / "p1_add_throttle_grid_3x3.md"

    holdout_start, holdout_end = _resolve_holdout_window(FULL_START, FULL_END, HOLDOUT_FRAC)

    rows: list[dict[str, Any]] = []
    for dd1 in DD1_VALUES:
        for dd2 in DD2_VALUES:
            config_name = f"p1_dd1_dd2_{_fmt_cell(dd1)}_{_fmt_cell(dd2)}.yaml"
            config_path = config_grid_dir / config_name
            _build_grid_config(
                template_path=template_config,
                out_path=config_path,
                dd1=dd1,
                dd2=dd2,
                mult=MULT,
            )

            cell_root = out_grid_root / _cell_slug(dd1, dd2)
            full_out = cell_root / "full"
            holdout_out = cell_root / "holdout"

            _run_validate(
                repo_root=repo_root,
                config_path=config_path,
                baseline_config=baseline_config,
                out_dir=full_out,
                start=FULL_START,
                end=FULL_END,
                force=args.force,
                skip_existing=args.skip_existing and not args.force,
            )
            _run_validate(
                repo_root=repo_root,
                config_path=config_path,
                baseline_config=baseline_config,
                out_dir=holdout_out,
                start=holdout_start,
                end=holdout_end,
                force=args.force,
                skip_existing=args.skip_existing and not args.force,
            )

            for period, out_dir in [("full", full_out), ("holdout", holdout_out)]:
                row: dict[str, Any] = {
                    "dd1": dd1,
                    "dd2": dd2,
                    "mult": MULT,
                    "period": period,
                }
                row.update(_read_harsh_backtest_metrics(out_dir))
                row.update(_read_trade_level_metrics(out_dir))
                row.update(_read_add_throttle_metrics(out_dir))
                row["pass_full"] = ""
                row["pass_full_reasons"] = ""
                row["holdout_ok"] = ""
                rows.append(row)

    full_rows = [row for row in rows if row["period"] == "full"]
    holdout_rows = [row for row in rows if row["period"] == "holdout"]

    for row in full_rows:
        passed, reason = _evaluate_pass_full(row)
        row["pass_full"] = bool(passed)
        row["pass_full_reasons"] = reason
        row["holdout_ok"] = ""

    for row in holdout_rows:
        row["pass_full"] = ""
        row["pass_full_reasons"] = ""
        row["holdout_ok"] = bool(_evaluate_holdout_ok(row))

    pass_coords: set[tuple[int, int]] = set()
    for row in full_rows:
        if not bool(row.get("pass_full")):
            continue
        i = DD1_VALUES.index(row["dd1"])
        j = DD2_VALUES.index(row["dd2"])
        pass_coords.add((i, j))

    components = _connected_components(pass_coords)
    largest_component = _pick_largest_component(components)
    max_size = len(largest_component)
    if max_size >= 5:
        status = "ROBUST"
    elif 3 <= max_size <= 4:
        status = "MARGINAL"
    else:
        status = "NOT_ROBUST"
    representative = _pick_representative(largest_component)

    rows_sorted = sorted(rows, key=lambda item: (item["dd1"], item["dd2"], item["period"]))
    _write_csv(results_csv, rows_sorted)
    _write_markdown(
        path=report_md,
        rows=rows_sorted,
        full_rows=full_rows,
        holdout_rows=holdout_rows,
        status=status,
        components=components,
        largest_component=largest_component,
        representative=representative,
    )

    print(f"[ok] Wrote CSV: {results_csv}")
    print(f"[ok] Wrote report: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
