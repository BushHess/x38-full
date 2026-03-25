"""Branch-local diagnostic for the current E5 WFO robustness fail."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.x36.shared.common import FrozenWFOConfig
from research.x36.shared.common import evaluate_wfo_window
from research.x36.shared.common import limited_windows
from research.x36.shared.common import make_baseline_factory
from research.x36.shared.common import make_candidate_factory
from research.x36.shared.common import read_json
from research.x36.shared.common import run_window_backtest
from research.x36.shared.common import summarize_trades
from research.x36.shared.common import summarize_wfo_rows
from research.x36.shared.common import top_trade_table
from research.x36.shared.common import write_json
from research.x36.shared.common import write_text

BRANCH_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = BRANCH_ROOT / "results"
CANONICAL_DIR = ROOT / "results" / "full_eval_e5_ema21d1"

FROZEN_SPLIT_MENU = (
    FrozenWFOConfig("canonical_24_6_last8", 24, 6, 6, 8),
    FrozenWFOConfig("short_horizon_24_3_last12", 24, 3, 3, 12),
    FrozenWFOConfig("long_horizon_24_9_last6", 24, 9, 9, 6),
    FrozenWFOConfig("canonical_24_6_all", 24, 6, 6, None),
)


def _fmt_float(value: Any, ndigits: int = 4) -> str:
    if value is None:
        return "NA"
    return f"{float(value):.{ndigits}f}"


def _pass_label(value: Any) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "LOW_POWER"


def _freeze_payload() -> dict[str, Any]:
    run_meta = read_json(CANONICAL_DIR / "run_meta.json")
    decision = read_json(CANONICAL_DIR / "reports" / "decision.json")
    wfo_summary = read_json(CANONICAL_DIR / "results" / "wfo_summary.json")
    summary = wfo_summary["summary"]
    valid_windows = int(summary.get("n_windows_valid", summary.get("n_windows", 0)))
    low_trade_windows = int(summary.get("low_trade_windows_count", summary.get("low_trade_windows", 0)))
    power_windows = int(summary.get("n_windows_power_only", summary.get("n_windows", 0)))
    low_trade_ratio = low_trade_windows / valid_windows if valid_windows > 0 else 1.0
    report_path = CANONICAL_DIR / "reports" / "validation_report.md"
    return {
        "source_dir": str(CANONICAL_DIR),
        "source_timestamp_utc": run_meta.get("timestamp_utc"),
        "canonical_verdict": decision.get("verdict"),
        "canonical_reasons": decision.get("reasons", []),
        "canonical_failures": decision.get("failures", []),
        "canonical_warnings": decision.get("warnings", []),
        "run_config": {
            "start": run_meta["config"]["start"],
            "end": run_meta["config"]["end"],
            "warmup_days": run_meta["config"]["warmup_days"],
            "initial_cash": run_meta["config"]["initial_cash"],
            "scenario_harsh_cost_bps": run_meta["config"]["harsh_cost_bps"],
            "wfo_train_months": run_meta["config"]["wfo_train_months"],
            "wfo_test_months": run_meta["config"]["wfo_test_months"],
            "wfo_slide_months": run_meta["config"]["wfo_slide_months"],
            "wfo_windows": run_meta["config"]["wfo_windows"],
            "seed": run_meta["config"]["seed"],
        },
        "canonical_wfo_summary": summary,
        "canonical_wfo_low_power": bool(power_windows < 3 or low_trade_ratio > 0.5),
        "source_files": {
            "run_meta": str(CANONICAL_DIR / "run_meta.json"),
            "decision": str(CANONICAL_DIR / "reports" / "decision.json"),
            "wfo_summary": str(CANONICAL_DIR / "results" / "wfo_summary.json"),
            "validation_report": str(report_path),
        },
    }


def _render_phase0(payload: dict[str, Any]) -> str:
    cfg = payload["run_config"]
    summary = payload["canonical_wfo_summary"]
    return "\n".join(
        [
            "# Phase 0 — Artifact Freeze",
            "",
            f"- Source dir: `{payload['source_dir']}`",
            f"- Source timestamp: `{payload['source_timestamp_utc']}`",
            f"- Canonical verdict: `{payload['canonical_verdict']}`",
            f"- Canonical failures: `{', '.join(payload['canonical_failures']) or 'none'}`",
            f"- Canonical warnings: `{'; '.join(payload['canonical_warnings']) or 'none'}`",
            "",
            "## Frozen Run Config",
            "",
            f"- Period: `{cfg['start']} -> {cfg['end']}`",
            f"- Warmup days: `{cfg['warmup_days']}`",
            f"- Initial cash: `{cfg['initial_cash']}`",
            f"- Harsh cost bps RT: `{cfg['scenario_harsh_cost_bps']}`",
            f"- WFO: train `{cfg['wfo_train_months']}m`, test `{cfg['wfo_test_months']}m`, slide `{cfg['wfo_slide_months']}m`, cap `{cfg['wfo_windows']}`",
            "",
            "## Canonical WFO Snapshot",
            "",
            f"- Windows valid: `{summary['n_windows_valid']}/{summary['n_windows_total']}`",
            f"- Power windows: `{summary.get('n_windows_power_only', summary['n_windows'])}`",
            f"- Invalid windows: `{summary.get('invalid_windows_count', 0)}`",
            f"- Low-trade windows: `{summary.get('low_trade_windows_count', 0)}`",
            f"- Low-power delegation active: `{payload['canonical_wfo_low_power']}`",
            f"- Positive windows: `{summary['positive_delta_windows']}`",
            f"- Win rate: `{summary['win_rate']}`",
            f"- Mean delta score: `{summary['mean_delta_score']}`",
            f"- Wilcoxon p: `{summary['wilcoxon']['p_value']}`",
            f"- Bootstrap CI: `[{summary['bootstrap_ci']['ci_lower']}, {summary['bootstrap_ci']['ci_upper']}]`",
        ]
    ) + "\n"


def _failure_tag(window_record: dict[str, Any]) -> str:
    if not bool(window_record.get("valid_window")):
        return f"invalid_window:{window_record.get('invalid_reason', 'unknown')}"
    if bool(window_record.get("low_trade_window")):
        return f"low_trade_window:{window_record.get('low_trade_reason', 'unknown')}"
    delta = window_record["delta"]
    if delta["score"] >= 0.0:
        return "positive_window"
    if delta["mdd_pct"] > 0.0 and delta["sharpe"] < 0.0:
        return "candidate_worse_return_and_worse_drawdown"
    if delta["mdd_pct"] <= 0.0 and delta["sharpe"] < 0.0:
        return "candidate_drawdown_better_but_return_weaker"
    return "mixed_underperformance"


def _run_window_suite(spec: FrozenWFOConfig, freeze_payload: dict[str, Any]) -> dict[str, Any]:
    cfg = freeze_payload["run_config"]
    min_trades_for_power = int(
        freeze_payload["canonical_wfo_summary"].get("min_trades_for_power", 5)
    )
    candidate_factory = make_candidate_factory(ROOT)
    baseline_factory = make_baseline_factory(ROOT)
    windows = limited_windows(
        start=cfg["start"],
        end=cfg["end"],
        spec=spec,
    )
    window_rows: list[dict[str, Any]] = []
    for window_idx, window in enumerate(windows):
        candidate_result = run_window_backtest(
            root=ROOT,
            factory=candidate_factory,
            start=window.test_start,
            end=window.test_end,
            warmup_days=int(cfg["warmup_days"]),
            initial_cash=float(cfg["initial_cash"]),
            scenario="harsh",
        )
        baseline_result = run_window_backtest(
            root=ROOT,
            factory=baseline_factory,
            start=window.test_start,
            end=window.test_end,
            warmup_days=int(cfg["warmup_days"]),
            initial_cash=float(cfg["initial_cash"]),
            scenario="harsh",
        )
        candidate_summary = candidate_result.summary
        baseline_summary = baseline_result.summary
        row_core = evaluate_wfo_window(
            window_id=window_idx,
            test_start=window.test_start,
            test_end=window.test_end,
            candidate_summary=candidate_summary,
            baseline_summary=baseline_summary,
            min_trades_for_power=min_trades_for_power,
        )
        record = {
            "window_id": int(window_idx),
            "train_start": window.train_start,
            "train_end": window.train_end,
            "test_start": window.test_start,
            "test_end": window.test_end,
            "valid_window": bool(row_core["valid_window"]),
            "invalid_reason": str(row_core["invalid_reason"]),
            "low_trade_window": bool(row_core["low_trade_window"]),
            "low_trade_reason": str(row_core["low_trade_reason"]),
            "delta_harsh_score": row_core["delta_harsh_score"],
            "candidate": {
                "score": row_core["candidate_score"],
                "sharpe": None if row_core["candidate_sharpe"] is None else round(float(row_core["candidate_sharpe"]), 4),
                "cagr_pct": None if row_core["candidate_cagr_pct"] is None else round(float(row_core["candidate_cagr_pct"]), 2),
                "mdd_pct": None if row_core["candidate_max_dd_pct"] is None else round(float(row_core["candidate_max_dd_pct"]), 2),
                "trades": int(row_core["candidate_trades"]),
                "trade_profile": summarize_trades(candidate_result.trades),
                "top_winners": top_trade_table(candidate_result.trades, reverse=True),
                "top_losers": top_trade_table(candidate_result.trades, reverse=False),
            },
            "baseline": {
                "score": row_core["baseline_score"],
                "sharpe": None if row_core["baseline_sharpe"] is None else round(float(row_core["baseline_sharpe"]), 4),
                "cagr_pct": None if row_core["baseline_cagr_pct"] is None else round(float(row_core["baseline_cagr_pct"]), 2),
                "mdd_pct": None if row_core["baseline_max_dd_pct"] is None else round(float(row_core["baseline_max_dd_pct"]), 2),
                "trades": int(row_core["baseline_trades"]),
                "trade_profile": summarize_trades(baseline_result.trades),
                "top_winners": top_trade_table(baseline_result.trades, reverse=True),
                "top_losers": top_trade_table(baseline_result.trades, reverse=False),
            },
            "delta": {
                "score": row_core["delta_harsh_score"],
                "sharpe": None
                if row_core["candidate_sharpe"] is None or row_core["baseline_sharpe"] is None
                else round(float(row_core["candidate_sharpe"]) - float(row_core["baseline_sharpe"]), 4),
                "cagr_pct": None
                if row_core["candidate_cagr_pct"] is None or row_core["baseline_cagr_pct"] is None
                else round(float(row_core["candidate_cagr_pct"]) - float(row_core["baseline_cagr_pct"]), 2),
                "mdd_pct": None
                if row_core["candidate_max_dd_pct"] is None or row_core["baseline_max_dd_pct"] is None
                else round(
                    float(row_core["candidate_max_dd_pct"]) - float(row_core["baseline_max_dd_pct"]),
                    2,
                ),
                "trades": int(row_core["candidate_trades"]) - int(row_core["baseline_trades"]),
            },
        }
        record["failure_tag"] = _failure_tag(record)
        window_rows.append(record)
    summary = summarize_wfo_rows(
        window_rows,
        seed=int(cfg["seed"]),
        min_trades_for_power=min_trades_for_power,
    )
    return {
        "spec": {
            "tag": spec.tag,
            "train_months": spec.train_months,
            "test_months": spec.test_months,
            "slide_months": spec.slide_months,
            "max_windows": spec.max_windows,
        },
        "windows": window_rows,
        "summary": summary,
    }


def _window_key(*, test_start: str, test_end: str) -> str:
    return f"{test_start}__{test_end}"


def _canonical_source_deltas() -> dict[str, dict[str, Any]]:
    payload = read_json(CANONICAL_DIR / "results" / "wfo_summary.json")
    return {
        _window_key(test_start=str(window["test_start"]), test_end=str(window["test_end"])): {
            "window_id": int(window["window_id"]),
            "test_start": str(window["test_start"]),
            "test_end": str(window["test_end"]),
            "delta_score": float(window["delta_harsh_score"]),
            "valid_window": bool(window.get("valid_window", True)),
            "low_trade_window": bool(window.get("low_trade_window", False)),
        }
        for window in payload["windows"]
    }


def _phase1_payload(freeze_payload: dict[str, Any]) -> dict[str, Any]:
    canonical = _run_window_suite(FROZEN_SPLIT_MENU[0], freeze_payload)
    source_deltas = _canonical_source_deltas()
    comparisons = []
    for row in canonical["windows"]:
        source = source_deltas.get(
            _window_key(test_start=str(row["test_start"]), test_end=str(row["test_end"]))
        )
        source_delta = None if source is None else float(source["delta_score"])
        branch_delta = None if row["delta"]["score"] is None else float(row["delta"]["score"])
        comparisons.append(
            {
                "window_id": int(row["window_id"]),
                "source_window_id": None if source is None else int(source["window_id"]),
                "test_start": row["test_start"],
                "test_end": row["test_end"],
                "source_delta": round(source_delta, 4) if source_delta is not None else None,
                "branch_delta": round(branch_delta, 4) if branch_delta is not None else None,
                "abs_diff": round(abs(branch_delta - source_delta), 6)
                if source_delta is not None and branch_delta is not None
                else None,
                "source_valid_window": None if source is None else bool(source["valid_window"]),
                "source_low_trade_window": None if source is None else bool(source["low_trade_window"]),
                "branch_valid_window": bool(row["valid_window"]),
                "branch_low_trade_window": bool(row["low_trade_window"]),
            }
        )
    failed_windows = [
        row
        for row in canonical["windows"]
        if row["delta"]["score"] is not None and float(row["delta"]["score"]) < 0.0
    ]
    return {
        "canonical_spec": canonical["spec"],
        "recomputed_summary": canonical["summary"],
        "reproduction_comparison": comparisons,
        "failed_window_ids": [int(row["window_id"]) for row in failed_windows],
        "failed_windows": failed_windows,
        "all_windows": canonical["windows"],
    }


def _render_phase1(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase 1 — Canonical Window Autopsy",
        "",
        "## All Windows",
        "",
        "| Window | Test Period | Valid | Low-trade | Delta Score | Delta Sharpe | Delta CAGR | Delta MDD | Tag |",
        "|---:|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in payload["all_windows"]:
        lines.append(
            "| "
            f"{row['window_id']} | {row['test_start']} -> {row['test_end']} | "
            f"{row['valid_window']} | {row['low_trade_window']} | "
            f"{_fmt_float(row['delta']['score'])} | {_fmt_float(row['delta']['sharpe'])} | "
            f"{_fmt_float(row['delta']['cagr_pct'], 2)} | {_fmt_float(row['delta']['mdd_pct'], 2)} | "
            f"{row['failure_tag']} |"
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Valid windows: `{payload['recomputed_summary']['n_windows_valid']}/{payload['recomputed_summary']['n_windows_total']}`",
            f"- Power windows: `{payload['recomputed_summary']['n_windows_power_only']}`",
            f"- Low-trade windows: `{payload['recomputed_summary']['low_trade_windows_count']}`",
            f"- Low-power delegation active: `{payload['recomputed_summary']['wfo_low_power']}`",
            f"- Wilcoxon p (power-only): `{payload['recomputed_summary']['wilcoxon']['p_value']}`",
            f"- Bootstrap CI (power-only): `[{payload['recomputed_summary']['bootstrap_ci']['ci_lower']}, {payload['recomputed_summary']['bootstrap_ci']['ci_upper']}]`",
            "",
            "## Reproduction Check",
            "",
            "| Branch window | Source window | Test period | Source delta | Branch delta | Abs diff | Branch valid | Branch low-trade |",
            "|---:|---:|---|---:|---:|---:|---|---|",
        ]
    )
    for row in payload["reproduction_comparison"]:
        source_delta = "NA" if row["source_delta"] is None else f"{row['source_delta']:.4f}"
        abs_diff = "NA" if row["abs_diff"] is None else f"{row['abs_diff']:.6f}"
        source_window = "NA" if row["source_window_id"] is None else str(row["source_window_id"])
        lines.append(
            "| "
            f"{row['window_id']} | {source_window} | {row['test_start']} -> {row['test_end']} | "
            f"{source_delta} | {_fmt_float(row['branch_delta'])} | {abs_diff} | "
            f"{row['branch_valid_window']} | {row['branch_low_trade_window']} |"
        )
    lines.extend(
        [
            "",
            "## Failed Windows",
            "",
        ]
    )
    for row in payload["failed_windows"]:
        lines.extend(
            [
                f"### Window {row['window_id']} — {row['test_start']} -> {row['test_end']}",
                "",
                f"- Failure tag: `{row['failure_tag']}`",
                f"- Delta score: `{_fmt_float(row['delta']['score'])}`",
                f"- Candidate vs baseline Sharpe: `{_fmt_float(row['candidate']['sharpe'])}` vs `{_fmt_float(row['baseline']['sharpe'])}`",
                f"- Candidate vs baseline CAGR: `{_fmt_float(row['candidate']['cagr_pct'], 2)}` vs `{_fmt_float(row['baseline']['cagr_pct'], 2)}`",
                f"- Candidate vs baseline MDD: `{_fmt_float(row['candidate']['mdd_pct'], 2)}` vs `{_fmt_float(row['baseline']['mdd_pct'], 2)}`",
                f"- Candidate trade profile: `{row['candidate']['trade_profile']}`",
                f"- Baseline trade profile: `{row['baseline']['trade_profile']}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _phase2_payload(freeze_payload: dict[str, Any], canonical_phase1: dict[str, Any]) -> dict[str, Any]:
    suites = []
    canonical_by_tag = canonical_phase1["canonical_spec"]["tag"]
    for spec in FROZEN_SPLIT_MENU:
        if spec.tag == canonical_by_tag:
            suite = {
                "spec": canonical_phase1["canonical_spec"],
                "summary": canonical_phase1["recomputed_summary"],
                "window_deltas": [
                    {
                        "window_id": int(row["window_id"]),
                        "test_start": row["test_start"],
                        "test_end": row["test_end"],
                        "delta_score": None if row["delta"]["score"] is None else float(row["delta"]["score"]),
                        "valid_window": bool(row["valid_window"]),
                        "low_trade_window": bool(row["low_trade_window"]),
                    }
                    for row in canonical_phase1["all_windows"]
                ],
            }
        else:
            run_payload = _run_window_suite(spec, freeze_payload)
            suite = {
                "spec": run_payload["spec"],
                "summary": run_payload["summary"],
                "window_deltas": [
                    {
                        "window_id": int(row["window_id"]),
                        "test_start": row["test_start"],
                        "test_end": row["test_end"],
                        "delta_score": None if row["delta"]["score"] is None else float(row["delta"]["score"]),
                        "valid_window": bool(row["valid_window"]),
                        "low_trade_window": bool(row["low_trade_window"]),
                    }
                    for row in run_payload["windows"]
                ],
            }
        suites.append(suite)
    return {"suites": suites}


def _render_phase2(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase 2 — Frozen Split Sensitivity",
        "",
        "| Spec | Valid/Total | Power | Low-trade | Positive | Win rate | Mean delta | Median delta | Worst delta | Wilcoxon p | Bootstrap lo | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for suite in payload["suites"]:
        summary = suite["summary"]
        wilcoxon = summary["wilcoxon"]
        bootstrap_ci = summary["bootstrap_ci"]
        lines.append(
            "| "
            f"{suite['spec']['tag']} | {summary['n_windows_valid']}/{summary['n_windows_total']} | "
            f"{summary['n_windows_power_only']} | {summary['low_trade_windows_count']} | "
            f"{summary['positive_delta_windows']} | {_fmt_float(summary['win_rate'])} | "
            f"{_fmt_float(summary['mean_delta_score'])} | {_fmt_float(summary['median_delta_score'])} | "
            f"{_fmt_float(summary['worst_delta_score'])} | {_fmt_float(wilcoxon['p_value'], 6)} | "
            f"{_fmt_float(bootstrap_ci['ci_lower'])} | {_pass_label(summary['pass'])} |"
        )
    return "\n".join(lines) + "\n"


def _phase3_payload(phase2: dict[str, Any]) -> dict[str, Any]:
    suites = {suite["spec"]["tag"]: suite for suite in phase2["suites"]}
    canonical_pass = suites["canonical_24_6_last8"]["summary"]["pass"]
    alternative_tags = (
        "short_horizon_24_3_last12",
        "long_horizon_24_9_last6",
        "canonical_24_6_all",
    )
    alternative_passes = sum(1 for tag in alternative_tags if suites[tag]["summary"]["pass"] is True)
    alternative_fails = sum(1 for tag in alternative_tags if suites[tag]["summary"]["pass"] is False)
    alternative_unresolved = len(alternative_tags) - alternative_passes - alternative_fails
    if canonical_pass is None:
        verdict = "CANONICAL_LOW_POWER_UNRESOLVED"
        reason = "Canonical split became low-power; branch verdict cannot be inferred without trade-level bootstrap."
    elif canonical_pass:
        verdict = "CANONICAL_PASS_LOCAL_REPRODUCTION"
        reason = "Local reproduction does not reproduce the canonical fail."
    elif alternative_fails >= 2:
        verdict = "LIKELY_TRUE_INSTABILITY"
        reason = "Canonical fail persists across most preregistered alternative split designs."
    elif alternative_passes >= 2:
        verdict = "LIKELY_DESIGN_SENSITIVE_FAIL"
        reason = "Canonical fail disappears under most preregistered alternative split designs."
    else:
        verdict = "MIXED_EVIDENCE"
        reason = (
            "Split menu produces mixed pass/fail evidence without a dominant pattern."
            if alternative_unresolved == 0
            else "Split menu contains unresolved low-power splits, so evidence is mixed."
        )
    return {
        "verdict": verdict,
        "reason": reason,
        "canonical_pass": canonical_pass,
        "alternative_passes": alternative_passes,
        "alternative_fails": alternative_fails,
        "alternative_unresolved": alternative_unresolved,
        "suite_pass_map": {
            tag: suites[tag]["summary"]["pass"]
            for tag in suites
        },
    }


def _render_phase3(payload: dict[str, Any]) -> str:
    lines = [
        "# Final Verdict",
        "",
        f"- Verdict: `{payload['verdict']}`",
        f"- Reason: {payload['reason']}",
        f"- Canonical pass: `{payload['canonical_pass']}`",
        f"- Alternative passes: `{payload['alternative_passes']}`",
        f"- Alternative fails: `{payload['alternative_fails']}`",
        f"- Alternative unresolved: `{payload['alternative_unresolved']}`",
        "",
        "## Suite Pass Map",
        "",
    ]
    for tag, passed in payload["suite_pass_map"].items():
        lines.append(f"- `{tag}`: `{_pass_label(passed)}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    phase0 = _freeze_payload()
    write_json(RESULTS_DIR / "phase0_artifact_freeze.json", phase0)
    write_text(RESULTS_DIR / "phase0_artifact_freeze.md", _render_phase0(phase0))

    phase1 = _phase1_payload(phase0)
    write_json(RESULTS_DIR / "phase1_canonical_window_autopsy.json", phase1)
    write_text(RESULTS_DIR / "phase1_canonical_window_autopsy.md", _render_phase1(phase1))

    phase2 = _phase2_payload(phase0, phase1)
    write_json(RESULTS_DIR / "phase2_split_sensitivity.json", phase2)
    write_text(RESULTS_DIR / "phase2_split_sensitivity.md", _render_phase2(phase2))

    phase3 = _phase3_payload(phase2)
    write_json(RESULTS_DIR / "final_verdict.json", phase3)
    write_text(RESULTS_DIR / "final_verdict.md", _render_phase3(phase3))


if __name__ == "__main__":
    main()
