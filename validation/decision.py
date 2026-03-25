"""Decision policy for validation verdicts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from typing import Any

from validation.suites.base import SuiteResult
from validation.thresholds import HARSH_SCORE_TOLERANCE
from validation.thresholds import PSR_THRESHOLD
from validation.thresholds import WFO_BOOTSTRAP_CI_ALPHA
from validation.thresholds import WFO_SMALL_SAMPLE_CUTOFF
from validation.thresholds import WFO_WILCOXON_ALPHA
from validation.thresholds import WFO_WIN_RATE_THRESHOLD


@dataclass
class GateCheck:
    gate_name: str
    passed: bool
    severity: str  # hard | soft | info
    detail: str


@dataclass
class DecisionPolicy:
    harsh_score_tolerance: float = HARSH_SCORE_TOLERANCE
    holdout_score_tolerance: float = HARSH_SCORE_TOLERANCE
    wfo_win_rate_threshold: float = WFO_WIN_RATE_THRESHOLD


@dataclass
class DecisionVerdict:
    tag: str
    exit_code: int
    gates: list[GateCheck] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    deltas: dict[str, Any] = field(default_factory=dict)
    key_links: dict[str, str] = field(default_factory=dict)
    trade_level_bootstrap: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if not math.isfinite(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _require_decisive_float(value: Any) -> float | None:
    """Return finite float or ``None`` if missing/invalid/non-finite.

    Use for authoritative decisive fields where a missing or non-finite value
    is a payload contract breach, not a benign default.
    """
    try:
        if value is None:
            return None
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _as_dict(value: Any, default: dict | None = None) -> dict:
    """Return *value* if it is a dict, else empty dict (or *default*)."""
    if isinstance(value, dict):
        return value
    return default if default is not None else {}


def _safe_int(value: Any, default: int = 0) -> int:
    """Return ``int(value)`` if possible, else *default*.

    Uses ``float()`` as intermediate to handle ``'3.0'`` strings.
    Rejects NaN/inf.
    """
    try:
        if value is None:
            return default
        f = float(value)
        if not math.isfinite(f):
            return default
        return int(f)
    except (TypeError, ValueError):
        return default


def _as_list_of_dicts(value: Any) -> list[dict]:
    """Return *value* filtered to dict elements only.

    Prevents ``list("abc")`` → ``["a","b","c"]`` then ``item.get()`` crash.
    """
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strict_bool(value: Any) -> bool:
    """Return ``True`` only for actual ``True`` or ``1``; ``False`` otherwise.

    Prevents ``bool("false")`` → ``True``.
    """
    if value is True:
        return True
    if isinstance(value, int) and not isinstance(value, bool) and value == 1:
        return True
    return False


def _compute_holdout_wfo_overlap(
    holdout_data: dict[str, Any],
    wfo_data: dict[str, Any],
) -> dict[str, Any]:
    """Compute overlap between holdout period and WFO test windows.

    Returns dict with max_overlap_days, max_overlap_pct (relative to holdout),
    and per-window overlap details.
    """
    ho_start_s = holdout_data.get("holdout_start")
    ho_end_s = holdout_data.get("holdout_end")
    if not ho_start_s or not ho_end_s:
        return {"max_overlap_days": 0, "max_overlap_pct": 0.0, "windows": []}

    try:
        ho_start = date.fromisoformat(str(ho_start_s))
        ho_end = date.fromisoformat(str(ho_end_s))
    except (ValueError, TypeError):
        return {"max_overlap_days": 0, "max_overlap_pct": 0.0, "windows": []}

    # +1 for inclusive end date (DataFeed end is inclusive, see data.py line 78)
    ho_days = max((ho_end - ho_start).days + 1, 1)
    wfo_windows = _as_list_of_dicts(_as_dict(wfo_data).get("summary", {}).get("windows") or wfo_data.get("windows"))

    if not wfo_windows:
        # Fallback: try top-level windows list.  This fires when summary.windows
        # is missing OR present but contains non-dict elements (filtered by
        # _as_list_of_dicts), while top-level windows has valid dicts.
        wfo_windows = _as_list_of_dicts(wfo_data.get("windows"))

    max_overlap_days = 0
    window_overlaps: list[dict[str, Any]] = []

    for w in wfo_windows:
        w_start_s = w.get("test_start")
        w_end_s = w.get("test_end")
        if not w_start_s or not w_end_s:
            continue
        try:
            w_start = date.fromisoformat(str(w_start_s))
            w_end = date.fromisoformat(str(w_end_s))
        except (ValueError, TypeError):
            continue

        overlap_start = max(ho_start, w_start)
        overlap_end = min(ho_end, w_end)
        # +1 for inclusive end date; if no overlap, overlap_end < overlap_start
        # so (overlap_end - overlap_start).days + 1 ≤ 0, clamped to 0.
        overlap_days = max((overlap_end - overlap_start).days + 1, 0)

        if overlap_days > 0:
            window_overlaps.append({
                "window_id": w.get("window_id"),
                "test_start": str(w_start_s),
                "test_end": str(w_end_s),
                "overlap_days": overlap_days,
                "overlap_pct_of_holdout": round(100 * overlap_days / ho_days, 1),
            })
            max_overlap_days = max(max_overlap_days, overlap_days)

    return {
        "holdout_start": str(ho_start_s),
        "holdout_end": str(ho_end_s),
        "holdout_days": ho_days,
        "max_overlap_days": max_overlap_days,
        "max_overlap_pct": round(100 * max_overlap_days / ho_days, 1),
        "windows": window_overlaps,
    }


def evaluate_decision(
    results: dict[str, SuiteResult],
    policy: DecisionPolicy | None = None,
) -> DecisionVerdict:
    if policy is None:
        policy = DecisionPolicy()

    errors = [
        f"{name}: {res.error_message or 'suite error'}"
        for name, res in results.items()
        if res.status == "error"
    ]
    if errors:
        return DecisionVerdict(
            tag="ERROR",
            exit_code=3,
            reasons=["Validation failed due to suite errors"],
            failures=errors,
            errors=errors,
            metadata={"n_errors": len(errors)},
        )

    data_integrity = results.get("data_integrity")
    if data_integrity is not None and data_integrity.status not in {"skip"}:
        _di_data = _as_dict(data_integrity.data)
        di_hard_fail = _strict_bool(_di_data.get("hard_fail"))
        if di_hard_fail:
            hard_reasons = [
                str(item)
                for item in _di_data.get("hard_fail_reasons", [])
                if str(item).strip()
            ]
            if not hard_reasons:
                hard_reasons = ["data_integrity_hard_fail"]
            _di_counts = _as_dict(_di_data.get("counts"))
            return DecisionVerdict(
                tag="ERROR",
                exit_code=3,
                reasons=["Data integrity hard-fail detected; aborting validation conclusions"],
                failures=hard_reasons,
                errors=hard_reasons,
                deltas={
                    "data_integrity_max_missing_bars_pct": _safe_float(
                        _di_counts.get("max_missing_bars_pct_estimated")
                    ),
                    "data_integrity_duplicates": _safe_float(
                        _di_counts.get("duplicate_timestamps")
                    ),
                    "data_integrity_ohlc_invalid_rows": _safe_float(
                        _di_counts.get("ohlc_invalid_rows")
                    ),
                },
                key_links={
                    "data_integrity_json": "results/data_integrity.json",
                    "data_integrity_issues": "results/data_integrity_issues.csv",
                },
                metadata={
                    "source": "data_integrity",
                    "n_hard_reasons": len(hard_reasons),
                },
            )

    invariants = results.get("invariants")
    if invariants is not None and invariants.status not in {"skip"}:
        _inv_data = _as_dict(invariants.data)
        n_violations = _safe_int(_inv_data.get("n_violations", 0))
        if n_violations > 0 or invariants.status == "fail":
            counts = _as_dict(_inv_data.get("counts_by_invariant"))
            inv_failures = [
                f"{name}:{_safe_float(value):.0f}"
                for name, value in sorted(counts.items())
            ]
            if not inv_failures:
                inv_failures = ["invariant_violation_detected"]

            return DecisionVerdict(
                tag="ERROR",
                exit_code=3,
                reasons=["Invariant violations detected; logic safety checks failed"],
                failures=inv_failures,
                errors=inv_failures,
                deltas={
                    "invariant_violation_count": n_violations,
                },
                key_links={
                    "invariant_violations": "results/invariant_violations.csv",
                },
                metadata={
                    "source": "invariants",
                    "n_violations": n_violations,
                    "limit_reached": _strict_bool(_inv_data.get("limit_reached", False)),
                },
            )

    regression_guard = results.get("regression_guard")
    if regression_guard is not None and regression_guard.status not in {"skip"}:
        _rg_data = _as_dict(regression_guard.data)
        guard_pass = _strict_bool(_rg_data.get("pass", regression_guard.status == "pass"))
        if not guard_pass or regression_guard.status in {"fail", "error"}:
            violated_rows = _as_list_of_dicts(_rg_data.get("violated_metrics", []))
            violated_meta_rows = _as_list_of_dicts(_rg_data.get("violated_metadata", []))
            rg_failures: list[str] = []
            for item in violated_rows:
                metric_name = str(item.get("metric") or item.get("field") or "unknown")
                rg_failures.append(metric_name)
            for item in violated_meta_rows:
                field_name = str(item.get("field") or "metadata")
                rg_failures.append(f"metadata:{field_name}")
            if not rg_failures:
                rg_failures = ["regression_guard_failed"]

            return DecisionVerdict(
                tag="ERROR",
                exit_code=3,
                reasons=["Regression guard failed; metrics deviated beyond golden tolerance"],
                failures=rg_failures,
                errors=rg_failures,
                deltas=_as_dict(_rg_data.get("deltas")),
                key_links={
                    "regression_guard": "results/regression_guard.json",
                },
                metadata={
                    "source": "regression_guard",
                    "n_metric_violations": len(violated_rows),
                    "n_metadata_violations": len(violated_meta_rows),
                },
            )

    gates: list[GateCheck] = []
    reasons: list[str] = []
    failures: list[str] = []
    deltas: dict[str, Any] = {}

    key_links = {
        "data_integrity": "results/data_integrity.json",
        "backtest": "results/full_backtest_summary.csv",
        "wfo": "results/wfo_per_round_metrics.csv",
        "holdout": "results/final_holdout_metrics.csv",
        "bootstrap": "results/bootstrap_paired_test.csv",
        "trade_level": "results/matched_trades.csv",
        "trade_level_bootstrap": "results/bootstrap_return_diff.json",
        "regression_guard": "results/regression_guard.json",
    }

    # Hard gate 1: lookahead must pass when enabled.
    if "lookahead" in results and results["lookahead"].status != "skip":
        passed = results["lookahead"].status == "pass"
        gates.append(
            GateCheck(
                gate_name="lookahead",
                passed=passed,
                severity="hard",
                detail=f"status={results['lookahead'].status}",
            )
        )
        if not passed:
            failures.append("lookahead_check_failed")
            reasons.append("Lookahead sanity failed")

    # Hard gate 2: harsh full-period tolerance.
    backtest = results.get("backtest")
    harsh_delta = None
    if backtest is not None:
        _raw_bt_delta = _as_dict(_as_dict(_as_dict(backtest.data).get("deltas")).get("harsh")).get("score_delta")
        harsh_delta = _require_decisive_float(_raw_bt_delta)
        if harsh_delta is None:
            return DecisionVerdict(
                tag="ERROR",
                exit_code=3,
                reasons=["Backtest ran but harsh score delta is missing or non-finite"],
                failures=["backtest_payload_contract_breach"],
                errors=["backtest_payload_contract_breach"],
                key_links=key_links,
            )
        deltas["full_harsh_score_delta"] = round(harsh_delta, 4)
        passed = harsh_delta >= -policy.harsh_score_tolerance
        gates.append(
            GateCheck(
                gate_name="full_harsh_delta",
                passed=passed,
                severity="hard",
                detail=f"delta={harsh_delta:.4f}, min={-policy.harsh_score_tolerance:.4f}",
            )
        )
        if not passed:
            failures.append("full_harsh_delta_below_tolerance")
            reasons.append(
                f"Candidate harsh score delta too low ({harsh_delta:.4f})"
            )

    # Hard gate 3: holdout tolerance when available.
    holdout = results.get("holdout")
    if holdout is not None and holdout.status not in {"skip"}:
        _raw_ho_delta = _as_dict(holdout.data).get("delta_harsh_score")
        holdout_delta = _require_decisive_float(_raw_ho_delta)
        if holdout_delta is None:
            return DecisionVerdict(
                tag="ERROR",
                exit_code=3,
                reasons=["Holdout ran but harsh score delta is missing or non-finite"],
                failures=["holdout_payload_contract_breach"],
                errors=["holdout_payload_contract_breach"],
                gates=gates,
                deltas=deltas,
                key_links=key_links,
            )
        deltas["holdout_harsh_score_delta"] = round(holdout_delta, 4)
        passed = holdout_delta >= -policy.holdout_score_tolerance
        gates.append(
            GateCheck(
                gate_name="holdout_harsh_delta",
                passed=passed,
                severity="hard",
                detail=(
                    f"delta={holdout_delta:.4f}, "
                    f"min={-policy.holdout_score_tolerance:.4f}"
                ),
            )
        )
        if not passed:
            failures.append("holdout_harsh_delta_below_tolerance")
            reasons.append(
                f"Holdout harsh score delta too low ({holdout_delta:.4f})"
            )

    # Soft gate 1: WFO robustness — Wilcoxon + Bootstrap CI (binding).
    # Binary win-rate demoted to advisory (Report 33, T03/T04 UNPROVEN).
    wfo = results.get("wfo")
    wfo_low_power = False
    if wfo is not None and wfo.status not in {"skip"}:
        summary = _as_dict(_as_dict(wfo.data).get("summary"))
        n_windows = _safe_int(summary.get("n_windows", 0))
        positive_windows = _safe_int(summary.get("positive_delta_windows", 0))
        win_rate = _safe_float(summary.get("win_rate"))
        power_windows = _safe_int(_as_dict(summary.get("stats_power_only")).get("n_windows", 0))
        valid_windows = _safe_int(summary.get("n_windows_valid", n_windows))
        low_trade_windows = _safe_int(
            summary.get("low_trade_windows_count", summary.get("low_trade_windows", 0))
        )
        low_trade_ratio = (low_trade_windows / valid_windows) if valid_windows > 0 else 1.0
        wfo_low_power = power_windows < 3 or low_trade_ratio > 0.5

        # Extract statistical test results from suite (may be absent in legacy runs)
        has_stat_tests = "wilcoxon" in summary
        wilcoxon_data = _as_dict(summary.get("wilcoxon"))
        bootstrap_data = _as_dict(summary.get("bootstrap_ci"))
        wilcoxon_p = _safe_float(wilcoxon_data.get("p_value"), 1.0)
        wilcoxon_sufficient = _strict_bool(wilcoxon_data.get("sufficient", False))
        bootstrap_excludes_zero = _strict_bool(bootstrap_data.get("excludes_zero", False))
        bootstrap_ci_lower = _safe_float(bootstrap_data.get("ci_lower"), 0.0)

        # Record in deltas for diagnostic consumption
        deltas["wfo_wilcoxon_p"] = round(wilcoxon_p, 6)
        deltas["wfo_wilcoxon_sufficient"] = wilcoxon_sufficient
        deltas["wfo_bootstrap_ci_lower"] = round(bootstrap_ci_lower, 4)
        deltas["wfo_bootstrap_excludes_zero"] = bootstrap_excludes_zero
        deltas["wfo_binary_win_rate"] = round(win_rate, 4) if math.isfinite(win_rate) else 0.0

        if wfo_low_power:
            passed = True
            detail = (
                "low_power=true; primary_evidence=trade_level_bootstrap; "
                f"power_windows={power_windows}, low_trade_ratio={low_trade_ratio:.3f}"
            )
        elif has_stat_tests:
            # Binding: pass if EITHER Wilcoxon or Bootstrap CI confirms delta > 0
            wilcoxon_pass = wilcoxon_sufficient and wilcoxon_p <= WFO_WILCOXON_ALPHA
            bootstrap_pass = bootstrap_excludes_zero
            passed = wilcoxon_pass or bootstrap_pass
            detail = (
                f"wilcoxon_p={wilcoxon_p:.4f} "
                f"({'PASS' if wilcoxon_pass else 'FAIL'}, α={WFO_WILCOXON_ALPHA}); "
                f"bootstrap_ci_lower={bootstrap_ci_lower:.4f} "
                f"({'PASS' if bootstrap_pass else 'FAIL'}, "
                f"α={WFO_BOOTSTRAP_CI_ALPHA}); "
                f"win_rate={win_rate:.3f} (advisory)"
            )
        else:
            # Fallback for legacy WFO results without statistical tests
            if n_windows <= WFO_SMALL_SAMPLE_CUTOFF and n_windows > 0:
                required = max(n_windows - 1, 0)
                passed = positive_windows >= required
                detail = f"positive={positive_windows}/{n_windows}, required>={required} (legacy)"
            else:
                passed = win_rate >= policy.wfo_win_rate_threshold
                detail = f"win_rate={win_rate:.3f}, required>={policy.wfo_win_rate_threshold:.3f} (legacy)"

        gates.append(
            GateCheck(
                gate_name="wfo_robustness",
                passed=passed,
                severity="soft",
                detail=detail,
            )
        )
        if not passed and not wfo_low_power:
            failures.append("wfo_robustness_failed")
            reasons.append("WFO robustness: neither Wilcoxon nor Bootstrap CI confirms positive OOS delta")

    # --- Holdout / WFO overlap check ---
    # When holdout period overlaps a WFO test window >30 days, these gates
    # are not statistically independent.  Log warning and, if both fail with
    # overlap >50%, mark as correlated rather than counting as 2 failures.
    holdout_wfo_correlated = False
    if holdout is not None and holdout.status not in {"skip"} and wfo is not None and wfo.status not in {"skip"}:
        _ho_data = _as_dict(holdout.data)
        _wfo_data = _as_dict(wfo.data)
        overlap_info = _compute_holdout_wfo_overlap(_ho_data, _wfo_data)
        max_overlap_days = overlap_info["max_overlap_days"]
        max_overlap_pct = overlap_info["max_overlap_pct"]
        deltas["holdout_wfo_max_overlap_days"] = max_overlap_days
        deltas["holdout_wfo_max_overlap_pct"] = max_overlap_pct

        if max_overlap_days > 30:
            overlap_warning = (
                f"Holdout/WFO overlap detected: {max_overlap_days} days "
                f"({max_overlap_pct:.1f}% of holdout period)"
            )
            warnings_list: list[str] = []  # collected for verdict
            warnings_list.append(overlap_warning)

            # Check if both gates failed
            holdout_gate = next((g for g in gates if g.gate_name == "holdout_harsh_delta"), None)
            wfo_gate = next((g for g in gates if g.gate_name == "wfo_robustness"), None)
            holdout_failed = holdout_gate is not None and not holdout_gate.passed
            wfo_failed = wfo_gate is not None and not wfo_gate.passed

            if holdout_failed and wfo_failed and max_overlap_pct > 50.0:
                holdout_wfo_correlated = True
                corr_note = (
                    f"holdout + WFO failures are NOT independent "
                    f"(overlap={max_overlap_pct:.1f}% > 50%): "
                    "same market event may cause both failures"
                )
                warnings_list.append(corr_note)
                # Downgrade WFO failure from independent soft-fail to
                # correlated advisory: remove from failures list so it is
                # not double-counted against the strategy.
                if "wfo_robustness_failed" in failures:
                    failures.remove("wfo_robustness_failed")
                if wfo_gate is not None:
                    # Mutate severity to 'info' so final tag computation
                    # does not count it as an independent soft-fail.
                    wfo_gate.severity = "info"
                    wfo_gate.detail += f" [CORRELATED with holdout, {corr_note}]"
                # Remove the WFO reason
                reasons[:] = [
                    r for r in reasons
                    if "WFO robustness" not in r
                ]

            deltas["holdout_wfo_overlap_warnings"] = warnings_list

    # Bootstrap DIAGNOSTIC — no longer a gate (Report 21, §1.1; Report 22B, Phase 3A).
    # p_a_better is a directional resampling score, NOT a calibrated p-value.
    # Values are still reported in deltas for diagnostic consumption.
    # Bootstrap has NO veto power: passed=True unconditionally, severity="info".
    bootstrap = results.get("bootstrap")
    if bootstrap is not None and bootstrap.status not in {"skip"}:
        gate = _as_dict(_as_dict(bootstrap.data).get("gate"))
        p = _safe_float(gate.get("p_candidate_better"), 0.5)
        ci_low = _safe_float(gate.get("ci_lower"), 0.0)
        deltas["bootstrap_p_candidate_better"] = round(p, 4)
        deltas["bootstrap_ci_lower"] = round(ci_low, 6)

        gates.append(
            GateCheck(
                gate_name="bootstrap",
                passed=True,
                severity="info",
                detail=(
                    f"p={p:.4f}, ci_low={ci_low:.4f} "
                    f"(diagnostic only — no veto power)"
                ),
            )
        )
        # No failures.append — bootstrap has no veto power.

    # Soft advisory: trade-level matched-trade delta.
    trade_level = results.get("trade_level")
    trade_level_bootstrap: dict[str, Any] = {}
    if trade_level is not None and trade_level.status not in {"skip"}:
        _tl_data = _as_dict(trade_level.data)
        p_pos = _tl_data.get("matched_p_positive")
        ci_low = _tl_data.get("matched_block_bootstrap_ci_lower")
        ci_up = _tl_data.get("matched_block_bootstrap_ci_upper")
        if p_pos is not None:
            deltas["matched_trade_p_positive"] = round(_safe_float(p_pos), 4)
        if ci_low is not None:
            deltas["matched_trade_ci_lower"] = round(_safe_float(ci_low), 6)
        if ci_up is not None:
            deltas["matched_trade_ci_upper"] = round(_safe_float(ci_up), 6)

        trade_level_bootstrap = _as_dict(_tl_data.get("trade_level_bootstrap"))
        if trade_level_bootstrap:
            tl_insufficient = _strict_bool(trade_level_bootstrap.get("insufficient_data", False))
            tl_ci_low = _safe_float(trade_level_bootstrap.get("ci95_low"))
            tl_ci_high = _safe_float(trade_level_bootstrap.get("ci95_high"))
            tl_mean_diff = _safe_float(trade_level_bootstrap.get("mean_diff"))
            tl_p_gt_0 = _safe_float(trade_level_bootstrap.get("p_gt_0"), 0.5)
            tl_block_len = _safe_int(trade_level_bootstrap.get("block_len", 0))
            small_threshold = _safe_float(
                trade_level_bootstrap.get("small_improvement_threshold"),
                0.0002,
            )

            deltas["trade_level_bootstrap_mean_diff"] = round(tl_mean_diff, 8)
            deltas["trade_level_bootstrap_ci95_low"] = round(tl_ci_low, 8)
            deltas["trade_level_bootstrap_ci95_high"] = round(tl_ci_high, 8)
            deltas["trade_level_bootstrap_p_gt_0"] = round(tl_p_gt_0, 4)
            deltas["trade_level_bootstrap_insufficient"] = tl_insufficient

            if tl_insufficient:
                # Too few observations for meaningful block bootstrap.
                # Treat as missing evidence — FAIL under low-power WFO.
                tl_n_obs = _safe_int(trade_level_bootstrap.get("n_obs", 0))
                if wfo_low_power:
                    gates.append(
                        GateCheck(
                            gate_name="trade_level_bootstrap",
                            passed=False,
                            severity="soft",
                            detail=(
                                f"insufficient_data=true (n_obs={tl_n_obs}); "
                                "cannot form valid CI under low-power WFO"
                            ),
                        )
                    )
                    failures.append("trade_level_bootstrap_insufficient_data")
                    reasons.append(
                        f"Trade-level bootstrap has insufficient data "
                        f"(n_obs={tl_n_obs}) under low-power WFO"
                    )
                else:
                    gates.append(
                        GateCheck(
                            gate_name="trade_level_bootstrap",
                            passed=True,
                            severity="soft",
                            detail=(
                                f"insufficient_data=true (n_obs={tl_n_obs}); "
                                "WFO not low-power, so not binding"
                            ),
                        )
                    )
            elif wfo_low_power:
                ci_crosses_zero = tl_ci_low <= 0.0 <= tl_ci_high
                is_small_improvement = abs(tl_mean_diff) <= small_threshold
                if ci_crosses_zero and is_small_improvement:
                    gates.append(
                        GateCheck(
                            gate_name="trade_level_bootstrap",
                            passed=False,
                            severity="soft",
                            detail=(
                                f"ci95=[{tl_ci_low:.8f},{tl_ci_high:.8f}] crosses 0; "
                                f"mean_diff={tl_mean_diff:.8f} <= {small_threshold:.8f} "
                                f"(block_len={tl_block_len})"
                            ),
                        )
                    )
                    failures.append("trade_level_bootstrap_inconclusive")
                    reasons.append("Trade-level bootstrap inconclusive under low-power WFO")
                else:
                    gates.append(
                        GateCheck(
                            gate_name="trade_level_bootstrap",
                            passed=True,
                            severity="soft",
                            detail=(
                                f"mean_diff={tl_mean_diff:.8f}, "
                                f"ci95=[{tl_ci_low:.8f},{tl_ci_high:.8f}], "
                                f"p_gt_0={tl_p_gt_0:.4f}, block_len={tl_block_len}"
                            ),
                        )
                    )
            else:
                gates.append(
                    GateCheck(
                        gate_name="trade_level_bootstrap",
                        passed=True,
                        severity="soft",
                        detail=(
                            f"mean_diff={tl_mean_diff:.8f}, "
                            f"ci95=[{tl_ci_low:.8f},{tl_ci_high:.8f}], "
                            f"p_gt_0={tl_p_gt_0:.4f}, block_len={tl_block_len}"
                        ),
                    )
                )
        elif ci_up is not None and _safe_float(ci_up) < 0:
            gates.append(
                GateCheck(
                    gate_name="trade_level_matched_delta",
                    passed=False,
                    severity="soft",
                    detail=f"CI upper {_safe_float(ci_up):.4f} < 0",
                )
            )
            failures.append("trade_level_delta_negative")
            reasons.append("Matched-trade CI suggests candidate underperforms")
        elif p_pos is not None:
            gates.append(
                GateCheck(
                    gate_name="trade_level_matched_delta",
                    passed=True,
                    severity="soft",
                    detail=f"p(delta>0)={_safe_float(p_pos):.4f}",
                )
            )

    if wfo_low_power and not trade_level_bootstrap:
        gates.append(
            GateCheck(
                gate_name="trade_level_bootstrap",
                passed=False,
                severity="soft",
                detail="missing trade_level_bootstrap payload while WFO is low-power",
            )
        )
        failures.append("wfo_low_power_missing_trade_level_bootstrap")
        reasons.append("WFO low-power requires trade-level bootstrap evidence")

    # Selection-bias: method-fallback (soft) + PBO overfitting (soft) +
    # PSR/DSR (diagnostic, no veto).
    #
    # PSR treats sr_benchmark as a known constant — anti-conservative for
    # 2-strategy comparison (ignores baseline estimation error and covariance).
    # Paired evidence for "candidate beats baseline" comes from WFO Wilcoxon +
    # Bootstrap CI (wfo_robustness gate), not from PSR.
    # See Bailey & López de Prado (2012), dsr.py docstring.
    sb = results.get("selection_bias")
    if sb is not None and sb.status not in {"skip"}:
        sb_data = _as_dict(sb.data)
        statement = str(sb_data.get("risk_statement", ""))
        psr_data = _as_dict(sb_data.get("psr"))
        psr_value = _safe_float(psr_data.get("psr"), 0.0)
        psr_pass = _strict_bool(sb_data.get("psr_pass"))
        has_psr = bool(psr_data)

        # Detect method fallback (e.g. requested PBO but fell back to none).
        # Contract: method_fallback is True when:
        #   (a) fallback_reason is a non-empty truthy string, OR
        #   (b) both requested_method and actual_method are non-empty truthy
        #       strings and they differ.
        # Edge cases that do NOT trigger fallback (no false positives):
        #   - Both None or both empty string → no evidence of fallback.
        #   - One None, other present → ambiguous/legacy payload, not a fallback.
        #   - requested_method == actual_method → no fallback occurred.
        requested_method = sb_data.get("requested_method")
        actual_method = sb_data.get("method")
        fallback_reason = sb_data.get("fallback_reason")
        method_fallback = bool(
            fallback_reason
            or (requested_method and actual_method and requested_method != actual_method)
        )

        # Record diagnostics
        deltas["selection_bias_psr"] = round(psr_value, 6)
        deltas["selection_bias_psr_pass"] = psr_pass
        deltas["selection_bias_sr_candidate"] = _safe_float(sb_data.get("sr_observed"))
        deltas["selection_bias_sr_baseline"] = _safe_float(sb_data.get("sr_baseline"))
        dsr_advisory = str(sb_data.get("dsr_advisory", ""))
        deltas["selection_bias_dsr_advisory"] = dsr_advisory

        if method_fallback:
            # Requested method could not run — gate must HOLD per risk_statement
            detail = (
                f"method fallback: requested={requested_method}, actual={actual_method}"
                f"{f', reason={fallback_reason}' if fallback_reason else ''}; "
                f"{statement}"
            )
            gates.append(
                GateCheck(
                    gate_name="selection_bias",
                    passed=False,
                    severity="soft",
                    detail=detail,
                )
            )
            failures.append("selection_bias_method_fallback")
            reasons.append(f"Selection-bias: {detail}")
        else:
            # ── PBO overfitting gate (binding when method=pbo) ──
            # PBO tests whether best in-sample parameters degrade OOS —
            # a genuine overfitting check independent of PSR.
            # Only binding when user explicitly requested PBO method;
            # "deflated" method computes PBO as informational side-product
            # but does not gate on it (preserves original intent).
            pbo_data = _as_dict(sb_data.get("pbo_proxy"))
            pbo_ratio_raw = pbo_data.get("negative_delta_ratio")
            pbo_failed = False
            pbo_detail = ""
            if pbo_data and pbo_ratio_raw is not None and actual_method == "pbo":
                pbo_ratio = _safe_float(pbo_ratio_raw, 1.0)
                pbo_passed = pbo_ratio <= 0.5
                pbo_detail = (
                    f"PBO negative_delta_ratio={pbo_ratio:.3f} "
                    f"({'PASS' if pbo_passed else 'FAIL'}, threshold=0.50)"
                )
                if not pbo_passed:
                    pbo_failed = True

            # ── PSR diagnostic (no veto power) ──
            # PSR treats sr_benchmark as known constant — anti-conservative
            # for 2-strategy comparison.  WFO Wilcoxon + Bootstrap CI provide
            # paired differential evidence.
            if has_psr:
                psr_level = (
                    "strong support" if psr_value >= PSR_THRESHOLD
                    else "moderate support" if psr_value >= 0.90
                    else "warning"
                )
                psr_detail = f"PSR={psr_value:.4f} ({psr_level})"
            else:
                psr_detail = (
                    f"{statement} (legacy, no PSR)" if statement
                    else f"status={sb.status}"
                )

            if pbo_failed:
                detail_parts = [pbo_detail, f"{psr_detail} (diagnostic)"]
                if dsr_advisory:
                    detail_parts.append(f"{dsr_advisory} (advisory)")
                detail = "; ".join(detail_parts)
                gates.append(
                    GateCheck(
                        gate_name="selection_bias",
                        passed=False,
                        severity="soft",
                        detail=detail,
                    )
                )
                failures.append("selection_bias_pbo_overfitting")
                reasons.append(
                    "Selection-bias PBO: negative_delta_ratio too high"
                )
            else:
                detail_parts = []
                if pbo_detail:
                    detail_parts.append(pbo_detail)
                detail_parts.append(f"{psr_detail} (diagnostic)")
                if dsr_advisory:
                    detail_parts.append(f"{dsr_advisory} (advisory)")
                detail_parts.append("no veto power")
                detail = "; ".join(detail_parts)
                gates.append(
                    GateCheck(
                        gate_name="selection_bias",
                        passed=True,
                        severity="info",
                        detail=detail,
                    )
                )
                # No failures.append — PSR/DSR have no veto power.

    hard_failures = [gate for gate in gates if gate.severity == "hard" and not gate.passed]
    soft_failures = [gate for gate in gates if gate.severity == "soft" and not gate.passed]

    if hard_failures:
        tag, exit_code = "REJECT", 2
    elif soft_failures:
        tag, exit_code = "HOLD", 1
    else:
        tag, exit_code = "PROMOTE", 0
        reasons.append("All configured decision gates passed")

    if not reasons:
        reasons.append("No decisive gate data available")

    return DecisionVerdict(
        tag=tag,
        exit_code=exit_code,
        gates=gates,
        reasons=reasons,
        failures=failures,
        deltas=deltas,
        key_links=key_links,
        trade_level_bootstrap=trade_level_bootstrap,
        metadata={
            "n_gates": len(gates),
            "n_hard_fail": len(hard_failures),
            "n_soft_fail": len(soft_failures),
            "wfo_low_power": wfo_low_power,
            "holdout_wfo_correlated": holdout_wfo_correlated,
        },
    )
