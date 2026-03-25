"""Regression-guard suite comparing a run against a promoted golden snapshot."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import yaml

from v10.research.objective import compute_objective
from validation.output import write_json
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult
from validation.suites.common import ensure_backtest

_METRIC_ALIASES: dict[str, str] = {
    "harsh_score": "harsh_score",
    "score": "harsh_score",
    "cagr": "CAGR",
    "cagr_pct": "CAGR",
    "mdd": "MDD",
    "max_drawdown_mid_pct": "MDD",
    "trades": "trades",
    "turnover": "turnover",
    "turnover_per_year": "turnover",
    "fees": "fees",
    "fees_total": "fees",
}

_PERIOD_SEPARATOR_CANDIDATES = ("->", "to", "~", "..", ",")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_metric_name(raw: str) -> str:
    return _METRIC_ALIASES.get(raw.strip().lower(), raw.strip())


def _load_golden(path: Path) -> dict[str, Any]:
    text = path.read_text()
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(text)
    else:
        loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError("golden file must be a mapping/object")
    return loaded


def _normalize_period(raw: Any) -> dict[str, str | None]:
    if isinstance(raw, dict):
        start = str(raw.get("start") or "").strip() or None
        end = str(raw.get("end") or "").strip() or None
        return {"start": start, "end": end}

    if isinstance(raw, str):
        cleaned = raw.strip()
        for sep in _PERIOD_SEPARATOR_CANDIDATES:
            if sep in cleaned:
                left, right = cleaned.split(sep, 1)
                return {"start": left.strip() or None, "end": right.strip() or None}
        if cleaned:
            return {"start": cleaned, "end": None}

    return {"start": None, "end": None}


def _tolerance_spec(
    tolerances: dict[str, Any],
    metric_key: str,
    metric_canonical: str,
) -> dict[str, float]:
    raw = None
    for key in (metric_key, metric_key.strip().lower(), metric_canonical):
        if key in tolerances:
            raw = tolerances[key]
            break
    if raw is None:
        raw = tolerances.get("default", 0.0)

    if _is_number(raw):
        return {"abs": float(raw)}

    if isinstance(raw, dict):
        spec: dict[str, float] = {}
        if _is_number(raw.get("abs")):
            spec["abs"] = float(raw["abs"])
        if _is_number(raw.get("min_delta")):
            spec["min_delta"] = float(raw["min_delta"])
        if _is_number(raw.get("max_delta")):
            spec["max_delta"] = float(raw["max_delta"])
        return spec or {"abs": 0.0}

    return {"abs": 0.0}


def _evaluate_metric(
    metric_name: str,
    expected: float,
    observed: float,
    tolerance: dict[str, float],
) -> dict[str, Any]:
    delta = observed - expected
    passed = True

    abs_tol = tolerance.get("abs")
    if abs_tol is not None:
        passed = passed and abs(delta) <= abs_tol

    min_delta = tolerance.get("min_delta")
    if min_delta is not None:
        passed = passed and delta >= min_delta

    max_delta = tolerance.get("max_delta")
    if max_delta is not None:
        passed = passed and delta <= max_delta

    return {
        "metric": metric_name,
        "expected": expected,
        "observed": observed,
        "delta": round(delta, 10),
        "tolerance": tolerance,
        "pass": passed,
    }


def _observed_metrics(ctx: SuiteContext, scenario: str) -> dict[str, float]:
    candidate = ensure_backtest(ctx, "candidate", scenario)
    summary = dict(candidate.summary)
    return {
        "harsh_score": round(float(compute_objective(summary)), 10),
        "CAGR": round(_safe_float(summary.get("cagr_pct")), 10),
        "MDD": round(_safe_float(summary.get("max_drawdown_mid_pct")), 10),
        "trades": round(_safe_float(summary.get("trades")), 10),
        "turnover": round(_safe_float(summary.get("turnover_per_year")), 10),
        "fees": round(_safe_float(summary.get("fees_total")), 10),
    }


def _metadata_checks(ctx: SuiteContext, golden: dict[str, Any], scenario_used: str) -> list[dict[str, Any]]:
    cfg = ctx.validation_config
    checks: list[dict[str, Any]] = []

    expected_dataset_id = str(golden.get("dataset_id") or "").strip()
    observed_dataset_id = str(cfg.dataset_id or cfg.dataset.name).strip()
    if expected_dataset_id:
        checks.append(
            {
                "field": "dataset_id",
                "expected": expected_dataset_id,
                "observed": observed_dataset_id,
                "pass": expected_dataset_id == observed_dataset_id,
            }
        )

    period_expected = _normalize_period(golden.get("period"))
    if period_expected["start"] or period_expected["end"]:
        period_observed = {"start": cfg.start, "end": cfg.end}
        checks.append(
            {
                "field": "period",
                "expected": period_expected,
                "observed": period_observed,
                "pass": (
                    (period_expected["start"] in {None, cfg.start})
                    and (period_expected["end"] in {None, cfg.end})
                ),
            }
        )

    expected_scenario = str(golden.get("scenario") or "").strip()
    if expected_scenario:
        checks.append(
            {
                "field": "scenario",
                "expected": expected_scenario,
                "observed": scenario_used,
                "pass": expected_scenario == scenario_used,
            }
        )

    expected_strategy_id = str(golden.get("strategy_id") or "").strip()
    if expected_strategy_id:
        checks.append(
            {
                "field": "strategy_id",
                "expected": expected_strategy_id,
                "observed": cfg.strategy_name,
                "pass": expected_strategy_id == cfg.strategy_name,
            }
        )

    return checks


class RegressionGuardSuite(BaseSuite):
    def name(self) -> str:
        return "regression_guard"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if not ctx.validation_config.regression_guard:
            return "regression guard disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []

        payload: dict[str, Any] = {
            "status": "fail",
            "pass": False,
            "golden_path": str(cfg.golden_path) if cfg.golden_path is not None else None,
            "dataset_id": str(cfg.dataset_id or cfg.dataset.name),
            "period": {"start": cfg.start, "end": cfg.end},
            "scenario": None,
            "strategy_id": cfg.strategy_name,
            "checked_metrics": [],
            "deltas": {},
            "violated_metrics": [],
            "violated_metadata": [],
            "observed_metrics": {},
            "metadata_checks": [],
            "note": "",
        }

        if cfg.golden_path is None:
            payload["note"] = "golden_path is required when regression_guard is enabled"
            artifact = write_json(payload, ctx.results_dir / "regression_guard.json")
            artifacts.append(artifact)
            return SuiteResult(
                name=self.name(),
                status="fail",
                data=payload,
                artifacts=artifacts,
                duration_seconds=time.time() - t0,
            )

        suite_status = "fail"
        try:
            golden = _load_golden(cfg.golden_path)

            scenario = str(golden.get("scenario") or "").strip()
            if not scenario:
                scenario = "harsh" if "harsh" in cfg.scenarios else "base"
            if scenario not in cfg.scenarios:
                raise ValueError(
                    f"golden scenario '{scenario}' is not enabled in run scenarios {cfg.scenarios}"
                )

            metrics_expected_raw = golden.get("metrics_expected")
            if not isinstance(metrics_expected_raw, dict) or not metrics_expected_raw:
                raise ValueError("golden.metrics_expected must be a non-empty mapping")

            tolerances = golden.get("tolerances")
            if tolerances is None:
                tolerances = {}
            if not isinstance(tolerances, dict):
                raise ValueError("golden.tolerances must be a mapping when provided")

            observed = _observed_metrics(ctx, scenario)
            metric_rows: list[dict[str, Any]] = []

            for raw_metric, expected_value in metrics_expected_raw.items():
                metric_key = str(raw_metric)
                metric_name = _normalize_metric_name(metric_key)
                if metric_name not in observed:
                    raise ValueError(
                        f"Unsupported metric '{metric_key}'. Supported metrics: "
                        f"{', '.join(sorted(observed))}"
                    )
                if not _is_number(expected_value):
                    raise ValueError(f"metrics_expected.{metric_key} must be numeric")

                tolerance = _tolerance_spec(tolerances, metric_key, metric_name)
                metric_rows.append(
                    _evaluate_metric(
                        metric_name=metric_name,
                        expected=float(expected_value),
                        observed=float(observed[metric_name]),
                        tolerance=tolerance,
                    )
                )

            metadata_rows = _metadata_checks(ctx, golden, scenario)
            metadata_violations = [row for row in metadata_rows if not bool(row.get("pass"))]
            metric_violations = [row for row in metric_rows if not bool(row.get("pass"))]

            payload["scenario"] = scenario
            payload["checked_metrics"] = metric_rows
            payload["deltas"] = {
                row["metric"]: row["delta"]
                for row in metric_rows
            }
            payload["violated_metrics"] = metric_violations
            payload["violated_metadata"] = metadata_violations
            payload["observed_metrics"] = observed
            payload["metadata_checks"] = metadata_rows
            payload["pass"] = len(metric_violations) == 0 and len(metadata_violations) == 0
            payload["status"] = "pass" if payload["pass"] else "fail"
            payload["note"] = (
                "Regression guard matched golden within tolerance."
                if payload["pass"]
                else "Regression guard violations detected."
            )
            suite_status = payload["status"]
        except Exception as exc:  # noqa: BLE001 - keep suite robust for malformed golden files.
            payload["status"] = "fail"
            payload["pass"] = False
            payload["note"] = f"Failed to evaluate golden file: {exc}"
            suite_status = "fail"

        artifact = write_json(payload, ctx.results_dir / "regression_guard.json")
        artifacts.append(artifact)
        return SuiteResult(
            name=self.name(),
            status=suite_status,
            data=payload,
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
