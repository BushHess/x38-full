"""Data-integrity suite for bar-level sanity checks before backtests."""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from validation.output import write_csv
from validation.output import write_json
from validation.suites.base import BaseSuite
from validation.suites.base import SuiteContext
from validation.suites.base import SuiteResult

_DAY_MS = 86_400_000
_DAY_SECONDS = 86_400
_ISSUE_SEVERITY_ORDER = {"fail": 0, "warning": 1, "info": 2}


def _date_to_ms(date_str: str | None) -> int | None:
    if not date_str:
        return None
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _ms_to_iso(ts_ms: int | None) -> str | None:
    if ts_ms is None:
        return None
    if ts_ms <= 0:
        return None
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _timeframe_to_seconds(timeframe: str | None) -> int | None:
    if timeframe is None:
        return None
    tf = str(timeframe).strip().lower()
    m = re.fullmatch(r"(\d+)\s*([mhdw])", tf)
    if not m:
        return None
    qty = int(m.group(1))
    unit = m.group(2)
    factor = {
        "m": 60,
        "h": 3_600,
        "d": 86_400,
        "w": 7 * 86_400,
    }[unit]
    return qty * factor


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


def _load_dataset_window(ctx: SuiteContext) -> tuple[pd.DataFrame, int | None, int | None, int | None]:
    cfg = ctx.validation_config
    df = pd.read_csv(ctx.data_path)

    report_start_ms = _date_to_ms(cfg.start)
    load_start_ms = None
    if report_start_ms is not None:
        load_start_ms = report_start_ms - int(cfg.warmup_days) * _DAY_MS
        if "open_time" in df.columns:
            df = df[pd.to_numeric(df["open_time"], errors="coerce") >= load_start_ms]

    load_end_ms = None
    end_ms = _date_to_ms(cfg.end)
    if end_ms is not None:
        load_end_ms = end_ms + _DAY_MS - 1
        if "open_time" in df.columns:
            df = df[pd.to_numeric(df["open_time"], errors="coerce") <= load_end_ms]

    return df.reset_index(drop=True), report_start_ms, load_start_ms, load_end_ms


def _configured_interval_seconds(ctx: SuiteContext) -> dict[str, int]:
    out: dict[str, int] = {}
    configs = [ctx.candidate_live_config, ctx.baseline_live_config]
    for live_cfg in configs:
        for timeframe in [
            getattr(live_cfg.engine, "timeframe_h4", None),
            getattr(live_cfg.engine, "timeframe_d1", None),
        ]:
            tf = str(timeframe).strip() if timeframe else ""
            if not tf:
                continue
            seconds = _timeframe_to_seconds(tf)
            if seconds is not None and tf not in out:
                out[tf] = seconds
    return out


def _target_intervals(ctx: SuiteContext, df: pd.DataFrame, configured: dict[str, int]) -> list[str]:
    if "interval" not in df.columns:
        return ["_all_"]

    present = [str(v) for v in df["interval"].dropna().astype(str).unique().tolist()]
    desired: list[str] = []
    desired.extend(configured.keys())

    for bar in [*ctx.feed.h4_bars, *ctx.feed.d1_bars]:
        tf = str(getattr(bar, "interval", "")).strip()
        if tf and tf not in desired:
            desired.append(tf)

    if desired:
        selected = [tf for tf in desired if tf in present]
        if selected:
            return selected

    return present


def _append_issue(
    issues: list[dict[str, Any]],
    issue_type: str,
    severity: str,
    timeframe: str,
    ts_start: int | None,
    ts_end: int | None,
    details: str,
) -> None:
    issues.append(
        {
            "ts_start": _safe_int(ts_start, 0) if ts_start is not None else "",
            "ts_end": _safe_int(ts_end, 0) if ts_end is not None else "",
            "issue_type": issue_type,
            "severity": severity,
            "timeframe": timeframe,
            "details": details,
        }
    )


def _warmup_requirements_days(ctx: SuiteContext) -> int:
    cfg_days = int(getattr(ctx.validation_config, "warmup_days", 0) or 0)
    if cfg_days > 0:
        return cfg_days

    cand_days = _safe_int(getattr(ctx.candidate_live_config.engine, "warmup_days", None), 0)
    base_days = _safe_int(getattr(ctx.baseline_live_config.engine, "warmup_days", None), 0)
    return max(cand_days, base_days, 0)


def _summarize_interval(
    frame_df: pd.DataFrame,
    timeframe: str,
    expected_seconds_cfg: int | None,
    gap_multiplier: float,
    required_warmup_days: int,
    report_start_ms: int | None,
    warmup_fail_coverage_pct: float,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "timeframe": timeframe,
        "rows": int(len(frame_df)),
        "bar_seconds": None,
        "bar_seconds_source": "unknown",
        "timestamp_not_increasing": 0,
        "duplicate_timestamps": 0,
        "gap_count": 0,
        "max_gap_seconds": 0.0,
        "missing_bars_estimated": 0,
        "missing_bars_pct_estimated": 0.0,
        "ohlc_invalid_rows": 0,
        "volume_invalid_rows": 0,
        "nan_counts": {},
        "inf_counts": {},
        "timezone_drift_events": 0,
        "warmup": {
            "required_days": int(required_warmup_days),
            "available_days": None,
            "coverage_pct": None,
            "severity": "ok",
        },
    }

    if frame_df.empty:
        return summary

    numeric_cols = ["open_time", "open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        if col in frame_df.columns:
            frame_df[col] = pd.to_numeric(frame_df[col], errors="coerce")

    ts_series = frame_df["open_time"] if "open_time" in frame_df.columns else pd.Series(dtype="float64")
    ts_valid = ts_series.dropna().astype("int64") if not ts_series.empty else pd.Series(dtype="int64")
    ts_list = ts_valid.tolist()

    prev_ts: int | None = None
    for curr_ts in ts_list:
        if prev_ts is not None and curr_ts <= prev_ts:
            if curr_ts == prev_ts:
                summary["duplicate_timestamps"] += 1
                _append_issue(
                    issues,
                    issue_type="duplicate_timestamp",
                    severity="fail",
                    timeframe=timeframe,
                    ts_start=prev_ts,
                    ts_end=curr_ts,
                    details="duplicate timestamp found in input order",
                )
            else:
                summary["timestamp_not_increasing"] += 1
                _append_issue(
                    issues,
                    issue_type="timestamp_not_increasing",
                    severity="fail",
                    timeframe=timeframe,
                    ts_start=prev_ts,
                    ts_end=curr_ts,
                    details="timestamp moved backward in input order",
                )
        prev_ts = curr_ts

    if ts_list:
        counts = Counter(ts_list)
        extra_dupes = sum(max(cnt - 1, 0) for cnt in counts.values())
        summary["duplicate_timestamps"] = max(summary["duplicate_timestamps"], int(extra_dupes))
        for ts_ms, cnt in counts.items():
            if cnt > 1:
                _append_issue(
                    issues,
                    issue_type="duplicate_timestamp",
                    severity="fail",
                    timeframe=timeframe,
                    ts_start=ts_ms,
                    ts_end=ts_ms,
                    details=f"timestamp repeats {cnt} times",
                )

    ts_sorted = sorted(set(ts_list))
    deltas_ms = [ts_sorted[idx] - ts_sorted[idx - 1] for idx in range(1, len(ts_sorted))]
    deltas_pos_ms = [x for x in deltas_ms if x > 0]
    median_delta_seconds = (
        float(pd.Series(deltas_pos_ms).median() / 1000.0) if deltas_pos_ms else None
    )

    bar_seconds = float(expected_seconds_cfg) if expected_seconds_cfg is not None else median_delta_seconds
    if bar_seconds and bar_seconds > 0:
        summary["bar_seconds"] = bar_seconds
        summary["bar_seconds_source"] = "config" if expected_seconds_cfg is not None else "median_delta"

    if bar_seconds and bar_seconds > 0 and deltas_pos_ms:
        bar_ms = bar_seconds * 1000.0
        gap_threshold_ms = gap_multiplier * bar_ms
        gap_rows = [gap for gap in deltas_pos_ms if gap > gap_threshold_ms]

        if gap_rows:
            summary["gap_count"] = int(len(gap_rows))
            summary["max_gap_seconds"] = round(max(gap_rows) / 1000.0, 6)
            missing_est = 0
            for idx, delta in enumerate(deltas_ms, start=1):
                if delta <= gap_threshold_ms:
                    continue
                ts_start = ts_sorted[idx - 1]
                ts_end = ts_sorted[idx]
                est = max(int(round(delta / bar_ms)) - 1, 1)
                missing_est += est
                _append_issue(
                    issues,
                    issue_type="gap_detected",
                    severity="warning",
                    timeframe=timeframe,
                    ts_start=ts_start,
                    ts_end=ts_end,
                    details=(
                        f"gap_seconds={delta / 1000.0:.2f}, expected_bar_seconds={bar_seconds:.2f}, "
                        f"estimated_missing_bars={est}"
                    ),
                )

            denom = len(ts_sorted) + missing_est
            missing_pct = (100.0 * missing_est / denom) if denom > 0 else 0.0
            summary["missing_bars_estimated"] = int(missing_est)
            summary["missing_bars_pct_estimated"] = round(float(missing_pct), 6)

    ohlc_cols = [col for col in ["open", "high", "low", "close"] if col in frame_df.columns]
    if len(ohlc_cols) == 4:
        open_s = frame_df["open"]
        high_s = frame_df["high"]
        low_s = frame_df["low"]
        close_s = frame_df["close"]

        finite_mask = open_s.notna() & high_s.notna() & low_s.notna() & close_s.notna()
        finite_mask &= open_s.map(math.isfinite)
        finite_mask &= high_s.map(math.isfinite)
        finite_mask &= low_s.map(math.isfinite)
        finite_mask &= close_s.map(math.isfinite)

        non_positive = (open_s <= 0) | (high_s <= 0) | (low_s <= 0) | (close_s <= 0)
        high_too_low = high_s < pd.concat([open_s, close_s], axis=1).max(axis=1)
        low_too_high = low_s > pd.concat([open_s, close_s], axis=1).min(axis=1)
        high_below_low = high_s < low_s

        invalid_mask = (~finite_mask) | non_positive | high_too_low | low_too_high | high_below_low
        invalid_rows = frame_df[invalid_mask]
        summary["ohlc_invalid_rows"] = int(len(invalid_rows))

        for _, row in invalid_rows.head(50).iterrows():
            violations: list[str] = []
            if not bool(
                pd.notna(row["open"])
                and pd.notna(row["high"])
                and pd.notna(row["low"])
                and pd.notna(row["close"])
                and all(
                    math.isfinite(_safe_float(row[x]))
                    for x in ["open", "high", "low", "close"]
                )
            ):
                violations.append("non_finite_ohlc")
            if any(
                _safe_float(row[col], 0.0) <= 0
                for col in ("open", "high", "low", "close")
            ):
                violations.append("non_positive_price")
            if _safe_float(row["high"]) < max(_safe_float(row["open"]), _safe_float(row["close"])):
                violations.append("high_lt_max(open,close)")
            if _safe_float(row["low"]) > min(_safe_float(row["open"]), _safe_float(row["close"])):
                violations.append("low_gt_min(open,close)")
            if _safe_float(row["high"]) < _safe_float(row["low"]):
                violations.append("high_lt_low")
            _append_issue(
                issues,
                issue_type="ohlc_invalid",
                severity="fail",
                timeframe=timeframe,
                ts_start=_safe_int(row.get("open_time", 0), 0),
                ts_end=_safe_int(row.get("open_time", 0), 0),
                details=(
                    f"violations={','.join(violations)}; "
                    f"open={row.get('open')}, high={row.get('high')}, "
                    f"low={row.get('low')}, close={row.get('close')}"
                ),
            )

    if "volume" in frame_df.columns:
        vol = frame_df["volume"]
        vol_invalid = vol.isna() | (~vol.map(lambda x: math.isfinite(float(x)) if pd.notna(x) else False)) | (vol < 0)
        invalid_count = int(vol_invalid.sum())
        summary["volume_invalid_rows"] = invalid_count
        if invalid_count > 0:
            for _, row in frame_df[vol_invalid].head(30).iterrows():
                _append_issue(
                    issues,
                    issue_type="volume_invalid",
                    severity="warning",
                    timeframe=timeframe,
                    ts_start=_safe_int(row.get("open_time", 0), 0),
                    ts_end=_safe_int(row.get("open_time", 0), 0),
                    details=f"volume={row.get('volume')} (must be finite and >= 0)",
                )

    nan_counts: dict[str, int] = {}
    inf_counts: dict[str, int] = {}
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in frame_df.columns:
            continue
        s = frame_df[col]
        nan_n = int(s.isna().sum())
        inf_n = int(
            s.dropna().map(
                lambda x: math.isinf(float(x)) if isinstance(x, (float, int)) else False
            ).sum()
        )
        nan_counts[col] = nan_n
        inf_counts[col] = inf_n
        if nan_n > 0 or inf_n > 0:
            _append_issue(
                issues,
                issue_type="nan_inf_detected",
                severity="warning",
                timeframe=timeframe,
                ts_start=ts_sorted[0] if ts_sorted else None,
                ts_end=ts_sorted[-1] if ts_sorted else None,
                details=f"column={col}, nan={nan_n}, inf={inf_n}",
            )
    summary["nan_counts"] = nan_counts
    summary["inf_counts"] = inf_counts

    timezone_events = 0
    if summary["bar_seconds"] and summary["bar_seconds"] > 0 and deltas_pos_ms:
        bar_seconds_float = float(summary["bar_seconds"])
        rel_err = [
            abs((delta / 1000.0) / bar_seconds_float - round((delta / 1000.0) / bar_seconds_float))
            for delta in deltas_pos_ms
        ]
        off_grid_count = int(sum(1 for x in rel_err if x > 0.05))
        if off_grid_count > 0:
            timezone_events += off_grid_count
            _append_issue(
                issues,
                issue_type="timezone_session_drift",
                severity="warning",
                timeframe=timeframe,
                ts_start=ts_sorted[0] if ts_sorted else None,
                ts_end=ts_sorted[-1] if ts_sorted else None,
                details=(
                    f"{off_grid_count} deltas not aligned to expected bar size "
                    f"{bar_seconds_float:.2f}s"
                ),
            )

        if ts_sorted:
            bar_seconds_int = max(int(round(bar_seconds_float)), 1)
            phases = [int((ts // 1000) % bar_seconds_int) for ts in ts_sorted]
            phase_counts = Counter(phases)
            if len(phase_counts) > 1:
                dominant = max(phase_counts.values())
                drifted = len(phases) - dominant
                if drifted > 0:
                    timezone_events += drifted
                    _append_issue(
                        issues,
                        issue_type="timezone_phase_drift",
                        severity="warning",
                        timeframe=timeframe,
                        ts_start=ts_sorted[0],
                        ts_end=ts_sorted[-1],
                        details=(
                            f"phase changes detected: unique_phases={len(phase_counts)}, "
                            f"non_dominant_points={drifted}"
                        ),
                    )

            if bar_seconds_int >= _DAY_SECONDS:
                hours = [int((ts // 1000 // 3600) % 24) for ts in ts_sorted]
                hour_counts = Counter(hours)
                if len(hour_counts) > 1:
                    dominant = max(hour_counts.values())
                    shifted = len(hours) - dominant
                    if shifted > 0:
                        timezone_events += shifted
                        _append_issue(
                            issues,
                            issue_type="session_hour_drift",
                            severity="warning",
                            timeframe=timeframe,
                            ts_start=ts_sorted[0],
                            ts_end=ts_sorted[-1],
                            details=f"daily/session hours drifted across {len(hour_counts)} distinct UTC hours",
                        )
    summary["timezone_drift_events"] = int(timezone_events)

    warmup = summary["warmup"]
    if report_start_ms is not None and required_warmup_days > 0:
        first_ts = ts_sorted[0] if ts_sorted else None
        available_days = 0.0
        if first_ts is not None:
            available_days = max((report_start_ms - first_ts) / _DAY_MS, 0.0)
        coverage_pct = (100.0 * available_days / required_warmup_days)
        warmup["available_days"] = round(float(available_days), 6)
        warmup["coverage_pct"] = round(float(coverage_pct), 6)
        if coverage_pct < warmup_fail_coverage_pct:
            warmup["severity"] = "fail"
            _append_issue(
                issues,
                issue_type="warmup_missing_severe",
                severity="fail",
                timeframe=timeframe,
                ts_start=first_ts,
                ts_end=report_start_ms,
                details=(
                    f"required_days={required_warmup_days}, available_days={available_days:.3f}, "
                    f"coverage_pct={coverage_pct:.2f}, fail_if_below={warmup_fail_coverage_pct:.2f}"
                ),
            )
        elif coverage_pct < 100.0:
            warmup["severity"] = "warning"
            _append_issue(
                issues,
                issue_type="warmup_missing",
                severity="warning",
                timeframe=timeframe,
                ts_start=first_ts,
                ts_end=report_start_ms,
                details=(
                    f"required_days={required_warmup_days}, available_days={available_days:.3f}, "
                    f"coverage_pct={coverage_pct:.2f}"
                ),
            )
    return summary


class DataIntegritySuite(BaseSuite):
    def name(self) -> str:
        return "data_integrity"

    def skip_reason(self, ctx: SuiteContext) -> str | None:
        if ctx.validation_config.data_integrity_check is False:
            return "data integrity check disabled"
        return None

    def run(self, ctx: SuiteContext) -> SuiteResult:
        t0 = time.time()
        cfg = ctx.validation_config
        artifacts: list[Path] = []
        issues: list[dict[str, Any]] = []

        gap_multiplier = float(getattr(cfg, "data_integrity_gap_multiplier", 1.5))
        missing_bars_fail_pct = float(getattr(cfg, "data_integrity_missing_bars_fail_pct", 0.5))
        warmup_fail_coverage_pct = float(
            getattr(cfg, "data_integrity_warmup_fail_coverage_pct", 50.0)
        )
        issue_limit = int(getattr(cfg, "data_integrity_issues_limit", 200))

        dataset_df, report_start_ms, load_start_ms, load_end_ms = _load_dataset_window(ctx)
        configured_seconds = _configured_interval_seconds(ctx)
        intervals = _target_intervals(ctx, dataset_df, configured_seconds)
        required_warmup_days = _warmup_requirements_days(ctx)

        # Detect configured timeframes missing from the dataset.
        # A missing timeframe means the strategy will silently degrade
        # (e.g., D1 regime filter returns all-False → zero entries).
        if "interval" in dataset_df.columns and configured_seconds:
            present_intervals = set(
                dataset_df["interval"].dropna().astype(str).unique()
            )
            for tf in sorted(configured_seconds):
                if tf not in present_intervals:
                    _append_issue(
                        issues,
                        issue_type="missing_configured_interval",
                        severity="fail",
                        timeframe=tf,
                        ts_start=None,
                        ts_end=None,
                        details=(
                            f"Configured timeframe '{tf}' not found in dataset. "
                            f"Present: {sorted(present_intervals)}. "
                            f"Strategy may silently degrade "
                            f"(e.g., regime filter returns all-False)."
                        ),
                    )

        if dataset_df.empty:
            _append_issue(
                issues,
                issue_type="dataset_empty",
                severity="fail",
                timeframe="_all_",
                ts_start=None,
                ts_end=None,
                details="dataset window is empty after start/end/warmup filters",
            )

        if "open_time" not in dataset_df.columns:
            _append_issue(
                issues,
                issue_type="missing_required_column",
                severity="fail",
                timeframe="_all_",
                ts_start=None,
                ts_end=None,
                details="dataset is missing required column: open_time",
            )

        if "interval" not in dataset_df.columns:
            dataset_df = dataset_df.copy()
            dataset_df["interval"] = "_all_"
            if "_all_" not in intervals:
                intervals = ["_all_"]

        interval_summaries: list[dict[str, Any]] = []
        for timeframe in intervals:
            tf_df = dataset_df[dataset_df["interval"].astype(str) == timeframe].copy()
            if timeframe == "_all_" and "interval" in dataset_df.columns:
                tf_df = dataset_df.copy()

            expected_seconds_cfg = configured_seconds.get(timeframe)
            interval_summaries.append(
                _summarize_interval(
                    frame_df=tf_df,
                    timeframe=timeframe,
                    expected_seconds_cfg=expected_seconds_cfg,
                    gap_multiplier=gap_multiplier,
                    required_warmup_days=required_warmup_days,
                    report_start_ms=report_start_ms,
                    warmup_fail_coverage_pct=warmup_fail_coverage_pct,
                    issues=issues,
                )
            )

        issue_type_counts = Counter(str(row["issue_type"]) for row in issues)
        fail_issue_count = sum(1 for row in issues if row.get("severity") == "fail")
        warning_issue_count = sum(1 for row in issues if row.get("severity") == "warning")

        total_timestamp_non_monotonic = sum(
            int(item.get("timestamp_not_increasing", 0)) for item in interval_summaries
        )
        total_duplicates = sum(int(item.get("duplicate_timestamps", 0)) for item in interval_summaries)
        total_ohlc_invalid = sum(int(item.get("ohlc_invalid_rows", 0)) for item in interval_summaries)
        total_volume_invalid = sum(int(item.get("volume_invalid_rows", 0)) for item in interval_summaries)
        max_missing_pct = max(
            [float(item.get("missing_bars_pct_estimated", 0.0)) for item in interval_summaries] or [0.0]
        )

        warmup_severe = any(
            str(item.get("warmup", {}).get("severity", "ok")) == "fail"
            for item in interval_summaries
        )

        hard_fail_reasons: list[str] = []
        if issue_type_counts.get("dataset_empty", 0) > 0:
            hard_fail_reasons.append("dataset_empty")
        if issue_type_counts.get("missing_required_column", 0) > 0:
            hard_fail_reasons.append("missing_required_column")
        if total_timestamp_non_monotonic > 0:
            hard_fail_reasons.append("timestamp_not_increasing")
        if total_duplicates > 0:
            hard_fail_reasons.append("duplicate_timestamps")
        if total_ohlc_invalid > 0:
            hard_fail_reasons.append("ohlc_invalid_rows")
        if max_missing_pct > missing_bars_fail_pct:
            hard_fail_reasons.append("missing_bars_pct_exceeds_threshold")
        if warmup_severe:
            hard_fail_reasons.append("warmup_missing_severe")
        if issue_type_counts.get("missing_configured_interval", 0) > 0:
            hard_fail_reasons.append("missing_configured_interval")

        hard_fail = bool(hard_fail_reasons)
        status = "fail" if hard_fail else "pass"

        all_nan_counts: dict[str, int] = {}
        all_inf_counts: dict[str, int] = {}
        for item in interval_summaries:
            for col, val in dict(item.get("nan_counts", {})).items():
                all_nan_counts[col] = int(all_nan_counts.get(col, 0) + int(val))
            for col, val in dict(item.get("inf_counts", {})).items():
                all_inf_counts[col] = int(all_inf_counts.get(col, 0) + int(val))

        issues_sorted = sorted(
            issues,
            key=lambda row: (
                _ISSUE_SEVERITY_ORDER.get(str(row.get("severity", "info")), 9),
                str(row.get("timeframe", "")),
                _safe_int(row.get("ts_start"), 0),
            ),
        )
        issues_limited = issues_sorted[: max(issue_limit, 1)]

        issues_csv = write_csv(
            issues_limited,
            ctx.results_dir / "data_integrity_issues.csv",
            fieldnames=["ts_start", "ts_end", "issue_type", "severity", "timeframe", "details"],
        )
        artifacts.append(issues_csv)

        summary = {
            "status": status,
            "pass": not hard_fail,
            "hard_fail": hard_fail,
            "hard_fail_reasons": hard_fail_reasons,
            "policy": {
                "missing_bars_fail_pct": missing_bars_fail_pct,
                "gap_multiplier": gap_multiplier,
                "warmup_fail_coverage_pct": warmup_fail_coverage_pct,
                "issue_rows_cap": issue_limit,
            },
            "dataset": str(ctx.data_path),
            "window": {
                "start": cfg.start,
                "end": cfg.end,
                "report_start_ms": report_start_ms,
                "report_start_utc": _ms_to_iso(report_start_ms),
                "load_start_ms": load_start_ms,
                "load_start_utc": _ms_to_iso(load_start_ms),
                "load_end_ms": load_end_ms,
                "load_end_utc": _ms_to_iso(load_end_ms),
                "required_warmup_days": required_warmup_days,
            },
            "counts": {
                "rows_checked": int(len(dataset_df)),
                "intervals_checked": int(len(interval_summaries)),
                "issues_total": int(len(issues)),
                "issues_written": int(len(issues_limited)),
                "fail_issues": int(fail_issue_count),
                "warning_issues": int(warning_issue_count),
                "timestamp_not_increasing": int(total_timestamp_non_monotonic),
                "duplicate_timestamps": int(total_duplicates),
                "ohlc_invalid_rows": int(total_ohlc_invalid),
                "volume_invalid_rows": int(total_volume_invalid),
                "max_missing_bars_pct_estimated": round(float(max_missing_pct), 6),
            },
            "nan_inf_by_column": {
                "nan": dict(sorted(all_nan_counts.items())),
                "inf": dict(sorted(all_inf_counts.items())),
            },
            "intervals": interval_summaries,
            "issue_type_counts": dict(sorted(issue_type_counts.items())),
        }

        summary_json = write_json(summary, ctx.results_dir / "data_integrity.json")
        artifacts.append(summary_json)

        return SuiteResult(
            name=self.name(),
            status=status,
            data=summary,
            artifacts=artifacts,
            duration_seconds=time.time() - t0,
        )
