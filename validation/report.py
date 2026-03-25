"""Markdown reporting for unified validation outputs."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from validation.config import ValidationConfig, resolve_suites
from validation.decision import DecisionVerdict
from validation.suites.base import SuiteResult


def generate_validation_report(
    results: dict[str, SuiteResult],
    decision: DecisionVerdict,
    config: ValidationConfig,
    outdir: Path,
    discovered: list[dict[str, Any]] | None = None,
) -> Path:
    lines: list[str] = []

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"- Generated: {now}")
    lines.append(f"- Candidate: `{config.strategy_name}`")
    lines.append(f"- Baseline: `{config.baseline_name}`")
    lines.append(f"- Dataset: `{config.dataset}`")
    lines.append(f"- Period: {config.start} -> {config.end}")
    lines.append(f"- Suite: `{config.suite}`")
    lines.append(f"- Seed: `{config.seed}`")
    lines.append("")

    lines.append(f"## Decision: **{decision.tag}** (exit `{decision.exit_code}`)")
    lines.append("")
    for reason in decision.reasons:
        lines.append(f"- {reason}")
    lines.append("")

    if decision.gates:
        lines.append("### Gate Summary")
        lines.append("")
        lines.append("| Gate | Status | Severity | Detail |")
        lines.append("|---|---|---|---|")
        for gate in decision.gates:
            status = "PASS" if gate.passed else "FAIL"
            # Escape pipe characters in detail to prevent markdown table breakage.
            safe_detail = str(gate.detail).replace("|", "\\|")
            lines.append(f"| {gate.gate_name} | {status} | {gate.severity} | {safe_detail} |")
        lines.append("")

    if decision.deltas:
        lines.append("### Key Deltas")
        lines.append("")
        for key, value in decision.deltas.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")

    # Warnings and errors are rendered as bullet lists (not tables),
    # so pipe characters in their text are harmless for markdown.
    if decision.warnings:
        lines.append("### Warnings")
        lines.append("")
        for warning in decision.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    if decision.errors:
        lines.append("### Errors")
        lines.append("")
        for error in decision.errors:
            lines.append(f"- {error}")
        lines.append("")

    lines.append("## Suite Results")
    lines.append("")
    for suite_name, suite_result in results.items():
        lines.append(f"### {suite_name}")
        lines.append("")
        lines.append(f"- Status: `{suite_result.status}`")
        lines.append(f"- Duration: {suite_result.duration_seconds:.2f}s")
        if suite_result.error_message:
            lines.append(f"- Error: {suite_result.error_message}")

        if suite_name == "backtest":
            _append_backtest(lines, suite_result)
        elif suite_name == "wfo":
            _append_wfo(lines, suite_result)
        elif suite_name == "bootstrap":
            _append_bootstrap(lines, suite_result)
        elif suite_name == "trade_level":
            _append_trade_level(lines, suite_result)
        elif suite_name == "churn_metrics":
            _append_churn_metrics(lines, suite_result)

        if suite_result.artifacts:
            lines.append("- Artifacts:")
            for artifact in suite_result.artifacts:
                lines.append(f"  - `{artifact.name}`")
        lines.append("")

    lines.append("## Additional checks found in repo")
    lines.append("")
    if discovered:
        for item in discovered:
            extra = "integrated" if item.get("integrated") else "not integrated"
            lines.append(
                f"- `{item.get('path')}` -> `{item.get('mapped_module')}` ({extra})"
            )
    else:
        lines.append("- No additional checks discovered.")

    path = outdir / "reports" / "validation_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def generate_quality_checks_report(
    results: dict[str, SuiteResult],
    config: ValidationConfig,
    outdir: Path,
) -> Path:
    """Write a compact summary for quality-check suites."""
    lines: list[str] = []
    lines.append("# Quality Checks")
    lines.append("")
    lines.append("| Group | Enabled | Status | Key Artifacts |")
    lines.append("|---|---|---|---|")

    resolved = set(resolve_suites(config))
    groups = [
        (
            "data_integrity",
            "Data Integrity",
            "data_integrity" in resolved,
            ["results/data_integrity.json", "results/data_integrity_issues.csv"],
        ),
        (
            "cost_sweep",
            "Cost Sweep",
            "cost_sweep" in resolved,
            ["results/cost_sweep.csv"],
        ),
        (
            "invariants",
            "Invariants",
            "invariants" in resolved,
            ["results/invariant_violations.csv"],
        ),
        (
            "regression_guard",
            "Regression Guard",
            "regression_guard" in resolved,
            ["results/regression_guard.json"],
        ),
        (
            "churn_metrics",
            "Churn Metrics",
            "churn_metrics" in resolved,
            ["results/churn_metrics.csv"],
        ),
    ]

    for suite_name, label, enabled, expected_artifacts in groups:
        if not enabled:
            status = "disabled"
        else:
            status = results.get(suite_name, SuiteResult(suite_name, "skip")).status

        present = [path for path in expected_artifacts if (outdir / path).exists()]
        artifact_text = ", ".join(f"`{path}`" for path in present) if present else "-"
        lines.append(
            f"| {label} | {'on' if enabled else 'off'} | `{status}` | {artifact_text} |"
        )

    data_integrity = results.get("data_integrity")
    if data_integrity is not None and data_integrity.status != "skip":
        summary = data_integrity.data or {}
        counts = summary.get("counts", {})
        policy = summary.get("policy", {})
        hard_reasons = list(summary.get("hard_fail_reasons", []))
        intervals = list(summary.get("intervals", []))

        lines.append("")
        lines.append("## Data Integrity")
        lines.append("")
        lines.append(f"- Status: `{data_integrity.status}`")
        lines.append(f"- Hard fail: `{bool(summary.get('hard_fail'))}`")
        if hard_reasons:
            lines.append(f"- Hard-fail reasons: `{', '.join(str(x) for x in hard_reasons)}`")
        lines.append(f"- Duplicate timestamps: `{int(counts.get('duplicate_timestamps', 0))}`")
        lines.append(f"- Non-monotonic timestamps: `{int(counts.get('timestamp_not_increasing', 0))}`")
        lines.append(f"- OHLC invalid rows: `{int(counts.get('ohlc_invalid_rows', 0))}`")
        lines.append(
            "- Max missing bars (estimated): "
            f"`{float(counts.get('max_missing_bars_pct_estimated', 0.0)):.6f}%`"
        )
        lines.append(
            "- Missing-bars fail threshold: "
            f"`{float(policy.get('missing_bars_fail_pct', 0.5)):.6f}%`"
        )
        lines.append(
            "- Warmup severe fail if coverage < "
            f"`{float(policy.get('warmup_fail_coverage_pct', 50.0)):.2f}%`"
        )

        if intervals:
            lines.append("")
            lines.append("| Timeframe | Bar Seconds | Source | Gaps | Missing % (est) | OHLC Invalid | Warmup |")
            lines.append("|---|---:|---|---:|---:|---:|---|")
            for item in intervals:
                warmup = _as_dict(item.get("warmup"))
                lines.append(
                    "| "
                    f"{item.get('timeframe', '')} | "
                    f"{_safe_number(item.get('bar_seconds'))} | "
                    f"{item.get('bar_seconds_source', '')} | "
                    f"{int(item.get('gap_count', 0))} | "
                    f"{float(item.get('missing_bars_pct_estimated', 0.0)):.6f} | "
                    f"{int(item.get('ohlc_invalid_rows', 0))} | "
                    f"{warmup.get('severity', 'ok')} "
                    f"({float(warmup.get('coverage_pct', 0.0) or 0.0):.2f}%) |"
                )

    cost_sweep = results.get("cost_sweep")
    if cost_sweep is not None and cost_sweep.status != "skip":
        summary = cost_sweep.data or {}
        rows = list(summary.get("rows", []))
        mode_requested = str(summary.get("mode_requested", config.cost_sweep_mode))
        mode_used = str(summary.get("mode_used", "unknown"))
        report_years = _safe_float(summary.get("report_years_estimated"))
        score_note = str(summary.get("score_primary_note", "")).strip()
        issues = list(summary.get("issues", []))
        n_rows = int(summary.get("n_rows", len(rows)))
        expected_rows = int(summary.get("expected_rows", n_rows))

        lines.append("")
        lines.append("## Cost Sweep")
        lines.append("")
        lines.append(f"- Status: `{cost_sweep.status}`")
        lines.append(f"- Rows: `{n_rows}/{expected_rows}`")
        lines.append(f"- Mode requested: `{mode_requested}`")
        lines.append(f"- Mode used: `{mode_used}`")
        if report_years is not None:
            lines.append(f"- Estimated report span: `{report_years:.2f}` years")
        if mode_requested == "quick":
            if mode_used == "quick":
                lines.append("- Quick mode note: backtest ran on recent subset for faster runtime.")
            else:
                lines.append(
                    "- Quick mode note: requested quick but runner fell back to full-history slice."
                )
        if score_note:
            lines.append(f"- score_primary note: {score_note}")
        lines.append("- Breakeven rule: first bps where `CAGR <= 0` or `score_primary <= 0`.")

        strategy_rows = _group_cost_sweep_rows(rows)
        if strategy_rows:
            lines.append("")
            lines.append("| strategy_id | breakeven_bps | slope_0_to_50 | slope_50_to_100 |")
            lines.append("|---|---:|---:|---:|")
            for strategy_id in sorted(strategy_rows):
                grouped = strategy_rows[strategy_id]
                breakeven = _find_breakeven_bps(grouped, score_threshold=0.0)
                score_points = _score_points(grouped)
                slope_0_50 = _slope_between(score_points, 0.0, 50.0)
                slope_50_100 = _slope_between(score_points, 50.0, 100.0)
                lines.append(
                    f"| {strategy_id} | "
                    f"{_fmt_num(breakeven, 2)} | "
                    f"{_fmt_num(slope_0_50, 6)} | "
                    f"{_fmt_num(slope_50_100, 6)} |"
                )

        if issues:
            lines.append("")
            lines.append(f"- Consistency issues: `{len(issues)}`")
            for item in issues[:5]:
                lines.append(f"- Issue: `{item}`")

    invariants = results.get("invariants")
    if invariants is not None and invariants.status != "skip":
        summary = invariants.data or {}
        n_violations = int(summary.get("n_violations", 0) or 0)
        violation_limit = int(summary.get("violation_limit", 0) or 0)
        limit_reached = bool(summary.get("limit_reached", False))
        counts = _as_dict(summary.get("counts_by_invariant"))

        lines.append("")
        lines.append("## Invariants")
        lines.append("")
        lines.append(f"- Status: `{invariants.status}`")
        lines.append(f"- Violation count: `{n_violations}`")
        if violation_limit > 0:
            lines.append(f"- Collection limit: `{violation_limit}`")
        if limit_reached:
            lines.append("- Collection note: limit reached, additional violations were truncated.")

        if counts:
            lines.append("")
            lines.append("| Invariant | Count |")
            lines.append("|---|---:|")
            for invariant_name, count in sorted(counts.items()):
                lines.append(f"| {invariant_name} | {int(count)} |")

    regression_guard = results.get("regression_guard")
    if regression_guard is not None and regression_guard.status != "skip":
        summary = regression_guard.data or {}
        checked_metrics = list(summary.get("checked_metrics", []))
        violated = list(summary.get("violated_metrics", []))
        violated_meta = list(summary.get("violated_metadata", []))
        metadata_checks = list(summary.get("metadata_checks", []))

        lines.append("")
        lines.append("## Regression Guard")
        lines.append("")
        lines.append(f"- Status: `{regression_guard.status}`")
        lines.append(f"- Pass: `{bool(summary.get('pass', False))}`")
        lines.append(f"- Golden file: `{summary.get('golden_path', '-')}`")
        lines.append(f"- Scenario: `{summary.get('scenario', '-')}`")
        lines.append(f"- Checked metrics: `{len(checked_metrics)}`")
        lines.append(f"- Metric violations: `{len(violated)}`")
        lines.append(f"- Metadata violations: `{len(violated_meta)}`")

        if metadata_checks:
            lines.append("")
            lines.append("| Metadata | Expected | Observed | Pass |")
            lines.append("|---|---|---|---|")
            for row in metadata_checks:
                lines.append(
                    f"| {row.get('field', '')} | "
                    f"{row.get('expected', '')} | "
                    f"{row.get('observed', '')} | "
                    f"{'PASS' if row.get('pass') else 'FAIL'} |"
                )

        if checked_metrics:
            lines.append("")
            lines.append("| Metric | Expected | Observed | Delta | Tolerance | Pass |")
            lines.append("|---|---:|---:|---:|---|---|")
            for row in checked_metrics:
                tolerance = row.get("tolerance", {})
                lines.append(
                    f"| {row.get('metric', '')} | "
                    f"{_fmt_num(_safe_float(row.get('expected')), 6)} | "
                    f"{_fmt_num(_safe_float(row.get('observed')), 6)} | "
                    f"{_fmt_num(_safe_float(row.get('delta')), 6)} | "
                    f"`{tolerance}` | "
                    f"{'PASS' if row.get('pass') else 'FAIL'} |"
                )

        if violated:
            lines.append("")
            lines.append("- Violated metrics:")
            for row in violated:
                name = row.get("metric") or row.get("field") or "unknown"
                lines.append(f"- `{name}`")

        if violated_meta:
            lines.append("")
            lines.append("- Violated metadata:")
            for row in violated_meta:
                name = row.get("field") or "unknown"
                lines.append(f"- `{name}`")

    churn = results.get("churn_metrics")
    if churn is not None and churn.status != "skip":
        summary = churn.data or {}
        rows = list(summary.get("rows", []))
        warnings = list(summary.get("warnings", []))
        thresholds = _as_dict(summary.get("warning_thresholds"))

        lines.append("")
        lines.append("## Churn & Fee Drag")
        lines.append("")
        lines.append(f"- Status: `{churn.status}`")
        lines.append(f"- Rows: `{len(rows)}`")
        lines.append(f"- Event source: `{summary.get('event_source', '-')}`")
        lines.append(f"- Definition: `{summary.get('fee_drag_definition', 'fee_drag_pct = total_fees / gross')}`")
        lines.append(
            "- Warning thresholds: "
            f"`fee_drag_pct>={_fmt_num(_safe_float(thresholds.get('fee_drag_pct')), 3)}`, "
            f"`cascade_leq3>={_fmt_num(_safe_float(thresholds.get('cascade_leq3')), 3)}`, "
            f"`cascade_leq6>={_fmt_num(_safe_float(thresholds.get('cascade_leq6')), 3)}`"
        )

        if rows:
            lines.append("")
            lines.append(
                "| strategy_id | scenario | trades | fee_drag_pct | "
                "share_emergency_dd | reentry_median_bars | cascade_leq3 | cascade_leq6 | buy_sell_ratio |"
            )
            lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
            for row in rows:
                lines.append(
                    f"| {row.get('strategy_id', '')} | "
                    f"{row.get('scenario', '')} | "
                    f"{int(_safe_float(row.get('trades')) or 0)} | "
                    f"{_fmt_num(_safe_float(row.get('fee_drag_pct')), 3)} | "
                    f"{_fmt_num(_safe_float(row.get('share_emergency_dd')), 4)} | "
                    f"{_fmt_num(_safe_float(row.get('reentry_median_bars')), 2)} | "
                    f"{_fmt_num(_safe_float(row.get('cascade_leq3')), 2)} | "
                    f"{_fmt_num(_safe_float(row.get('cascade_leq6')), 2)} | "
                    f"{_fmt_num(_safe_float(row.get('buy_sell_ratio')), 3)} |"
                )

        if warnings:
            lines.append("")
            lines.append(f"- WARNING count: `{len(warnings)}`")
            for item in warnings[:10]:
                lines.append(f"- {item}")
        else:
            lines.append("- WARNING count: `0`")

    path = outdir / "reports" / "quality_checks.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def _as_dict(value: Any) -> dict:
    """Return *value* if it is a dict, else empty dict."""
    return value if isinstance(value, dict) else {}


def _safe_number(value: Any) -> str:
    if value is None:
        return "-"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(num - round(num)) < 1e-9:
        return str(int(round(num)))
    return f"{num:.6f}"


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        num = float(value)
        if num != num:
            return None
        return num
    except (TypeError, ValueError):
        return None


def _fmt_num(value: float | None, digits: int) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def _group_cost_sweep_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        strategy_id = str(row.get("strategy_id", "")).strip()
        if not strategy_id:
            continue
        grouped.setdefault(strategy_id, []).append(row)
    for strategy_id in grouped:
        grouped[strategy_id] = sorted(
            grouped[strategy_id],
            key=lambda item: _safe_float(item.get("bps")) or 0.0,
        )
    return grouped


def _find_breakeven_bps(rows: list[dict[str, Any]], score_threshold: float = 0.0) -> float | None:
    for row in rows:
        cagr = _safe_float(row.get("CAGR"))
        score = _safe_float(row.get("score_primary"))
        bps = _safe_float(row.get("bps"))
        if bps is None or cagr is None or score is None:
            continue
        if cagr <= 0.0 or score <= score_threshold:
            return bps
    return None


def _score_points(rows: list[dict[str, Any]]) -> dict[float, float]:
    points: dict[float, float] = {}
    for row in rows:
        bps = _safe_float(row.get("bps"))
        score = _safe_float(row.get("score_primary"))
        if bps is None or score is None:
            continue
        points[bps] = score
    return points


def _interpolate(points: dict[float, float], target_bps: float) -> float | None:
    if target_bps in points:
        return points[target_bps]
    if not points:
        return None

    xs = sorted(points.keys())
    if target_bps < xs[0] or target_bps > xs[-1]:
        return None

    left_x = xs[0]
    left_y = points[left_x]
    for right_x in xs[1:]:
        right_y = points[right_x]
        if left_x <= target_bps <= right_x:
            span = right_x - left_x
            if abs(span) < 1e-12:
                return left_y
            t = (target_bps - left_x) / span
            return left_y + (right_y - left_y) * t
        left_x, left_y = right_x, right_y
    return None


def _slope_between(points: dict[float, float], left_bps: float, right_bps: float) -> float | None:
    if abs(right_bps - left_bps) < 1e-12:
        return None
    left_score = _interpolate(points, left_bps)
    right_score = _interpolate(points, right_bps)
    if left_score is None or right_score is None:
        return None
    return (right_score - left_score) / (right_bps - left_bps)


def _append_backtest(lines: list[str], result: SuiteResult) -> None:
    rows = result.data.get("rows", [])
    if not rows:
        return
    lines.append("")
    lines.append("| Label | Scenario | Score | CAGR% | MDD% | Sharpe | Trades |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            "| "
            f"{row.get('label', '')} | {row.get('scenario', '')} | "
            f"{row.get('score', '')} | {row.get('cagr_pct', '')} | "
            f"{row.get('max_drawdown_mid_pct', '')} | {row.get('sharpe', '')} | "
            f"{row.get('trades', '')} |"
        )

    add_stats = _as_dict(result.data.get("add_throttle_stats"))
    if add_stats:
        lines.append("")
        lines.append("Add-throttle stats (`results/add_throttle_stats.json`):")
        lines.append("")
        lines.append(
            "| Label | Scenario | add_attempt_count | add_allowed_count | "
            "add_blocked_count | throttle_activation_rate | mean_dd_blocked | p90_dd_blocked |"
        )
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
        for label in ["candidate", "baseline"]:
            by_scenario = add_stats.get(label, {})
            if not isinstance(by_scenario, dict):
                continue
            for scenario, stat in sorted(by_scenario.items()):
                if not isinstance(stat, dict):
                    continue
                lines.append(
                    f"| {label} | {scenario} | "
                    f"{int(_safe_float(stat.get('add_attempt_count')) or 0)} | "
                    f"{int(_safe_float(stat.get('add_allowed_count')) or 0)} | "
                    f"{int(_safe_float(stat.get('add_blocked_count')) or 0)} | "
                    f"{_fmt_num(_safe_float(stat.get('throttle_activation_rate')), 6)} | "
                    f"{_fmt_num(_safe_float(stat.get('mean_dd_depth_when_blocked')), 6)} | "
                    f"{_fmt_num(_safe_float(stat.get('p90_dd_depth_when_blocked')), 6)} |"
                )


def _append_wfo(lines: list[str], result: SuiteResult) -> None:
    summary = result.data.get("summary", {})
    if not summary:
        return
    stats_all = _as_dict(summary.get("stats_all_valid"))
    stats_power = _as_dict(summary.get("stats_power_only"))

    def _fmt(value: Any) -> str:
        num = _safe_float(value)
        if num is None:
            return "NaN"
        return f"{num:.6f}"

    lines.append("")
    lines.append(
        f"- Windows (valid/total): {summary.get('n_windows_valid', summary.get('n_windows', 0))}"
        f"/{summary.get('n_windows_total', summary.get('n_windows', 0))}"
    )
    lines.append(f"- Invalid windows: {summary.get('invalid_windows_count', 0)}")
    lines.append(f"- Low-trade windows: {summary.get('low_trade_windows_count', summary.get('low_trade_windows', 0))}")
    lines.append(f"- Positive windows (valid only): {summary.get('positive_delta_windows', 0)}")
    lines.append(f"- Win rate (valid only): {_fmt(summary.get('win_rate'))}")
    lines.append(f"- Mean delta score (valid only): {_fmt(summary.get('mean_delta_score'))}")
    lines.append(
        "- stats_all_valid: "
        f"median={_fmt(stats_all.get('median_delta'))}, "
        f"worst={_fmt(stats_all.get('worst_delta'))}, "
        f"win_count={_fmt(stats_all.get('win_count'))}"
    )
    lines.append(
        "- stats_power_only: "
        f"median={_fmt(stats_power.get('median_delta'))}, "
        f"worst={_fmt(stats_power.get('worst_delta'))}, "
        f"win_count={_fmt(stats_power.get('win_count'))}"
    )


def _append_bootstrap(lines: list[str], result: SuiteResult) -> None:
    gate = result.data.get("gate", {})
    if not gate:
        return
    lines.append("")
    lines.append(f"- P(candidate > baseline): {gate.get('p_candidate_better')}")
    lines.append(
        f"- CI95 delta: [{gate.get('ci_lower')}, {gate.get('ci_upper')}]"
    )
    lines.append(f"- Observed delta: {gate.get('observed_delta')}")


def _append_trade_level(lines: list[str], result: SuiteResult) -> None:
    lines.append("")
    lines.append(f"- Candidate trades: {result.data.get('candidate_trades', 0)}")
    lines.append(f"- Baseline trades: {result.data.get('baseline_trades', 0)}")
    lines.append(f"- Matched trades: {result.data.get('matched_trades', 0)}")
    lines.append(f"- Candidate-only trades: {result.data.get('candidate_only_trades', 0)}")
    lines.append(f"- Baseline-only trades: {result.data.get('baseline_only_trades', 0)}")
    lines.append(f"- Mean delta pnl: {result.data.get('matched_delta_pnl_mean', 0)}")
    if result.data.get("matched_p_positive") is not None:
        lines.append(
            f"- p(delta>0): {result.data.get('matched_p_positive')}"
        )
        lines.append(
            "- Matched block-bootstrap CI95: "
            f"[{result.data.get('matched_block_bootstrap_ci_lower')}, "
            f"{result.data.get('matched_block_bootstrap_ci_upper')}]"
        )
    trade_bootstrap = _as_dict(result.data.get("trade_level_bootstrap"))
    if trade_bootstrap:
        lines.append(
            "- NAV return-diff bootstrap CI95: "
            f"[{trade_bootstrap.get('ci95_low')}, {trade_bootstrap.get('ci95_high')}]"
        )
        lines.append(
            f"- NAV return-diff mean: {trade_bootstrap.get('mean_diff')} "
            f"(p_gt_0={trade_bootstrap.get('p_gt_0')})"
        )
    if "delta_buy_fills_per_episode" in result.data:
        lines.append(
            "- DD pathology deltas: "
            f"buy_fills_per_episode={result.data.get('delta_buy_fills_per_episode')}, "
            f"fees_usd={result.data.get('delta_fees_usd')}, "
            f"emergency_dd_share_pp={result.data.get('delta_emergency_dd_share_pp')}"
        )
    entry_risk_summary = list(result.data.get("entry_risk_summary", []))
    if entry_risk_summary:
        lines.append("- Entry risk cohorts:")
        for row in entry_risk_summary:
            lines.append(
                "  "
                f"{row.get('label')}:{row.get('entry_risk_level')} "
                f"trades={row.get('n_trades')} "
                f"share={row.get('share_trades')} "
                f"avg_pnl={row.get('avg_pnl')} "
                f"win_rate={row.get('win_rate')}"
            )


def _append_churn_metrics(lines: list[str], result: SuiteResult) -> None:
    rows = list(result.data.get("rows", []))
    warnings = list(result.data.get("warnings", []))
    thresholds = _as_dict(result.data.get("warning_thresholds"))
    if not rows:
        return

    lines.append("")
    lines.append(
        f"- Fee drag definition: `{result.data.get('fee_drag_definition', 'fee_drag_pct = total_fees / abs_gross')}`"
    )
    lines.append(
        "- Warning thresholds: "
        f"`fee_drag_pct>={_fmt_num(_safe_float(thresholds.get('fee_drag_pct')), 3)}`, "
        f"`cascade_leq3>={_fmt_num(_safe_float(thresholds.get('cascade_leq3')), 3)}`, "
        f"`cascade_leq6>={_fmt_num(_safe_float(thresholds.get('cascade_leq6')), 3)}`"
    )
    lines.append(
        "- Artifact link: `results/churn_metrics.csv`"
    )
    lines.append("")
    lines.append("| Strategy | Scenario | Trades | Fee Drag % | Cascade <=3 | Cascade <=6 | Buy/Sell |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row.get('strategy_id', '')} | "
            f"{row.get('scenario', '')} | "
            f"{int(_safe_float(row.get('trades')) or 0)} | "
            f"{_fmt_num(_safe_float(row.get('fee_drag_pct')), 3)} | "
            f"{_fmt_num(_safe_float(row.get('cascade_leq3')), 2)} | "
            f"{_fmt_num(_safe_float(row.get('cascade_leq6')), 2)} | "
            f"{_fmt_num(_safe_float(row.get('buy_sell_ratio')), 3)} |"
        )
    if warnings:
        lines.append("")
        lines.append(f"- WARNING count: `{len(warnings)}`")
