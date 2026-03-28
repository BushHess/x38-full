"""A01 — Temporal Decay Audit for x40 baselines.

Measures whether baseline alpha is weakening over time using:
1. Fixed era splits (3 eras)
2. Rolling window Sharpe (18-month window, 3-month step)

Both baselines use simple per-side cost model, default 20 bps RT.

Usage:
    cd /var/www/trading-bots/btc-spot-dev
    python research/x40/studies/a01_temporal_decay.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from research.x40.oh0_strategy import run_oh0_sim
from research.x40.pf0_strategy import SegmentMetrics as PF0SegmentMetrics
from research.x40.pf0_strategy import compute_segment_metrics as pf0_compute_segment
from research.x40.pf0_strategy import run_pf0_sim
from v10.core.data import DataFeed

DATA_PATH = str(ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv")
RESULTS_DIR = ROOT / "research" / "x40" / "results"
OUTPUT_DIR = ROOT / "research" / "x40" / "output"

# Default cost: 20 bps RT (synchronized with replay.py)
DEFAULT_COST_PER_SIDE = 0.001

# ---------------------------------------------------------------------------
# Era definitions
# ---------------------------------------------------------------------------

ERAS = [
    ("ERA_1_EARLY",  "2020-01-01", "2021-12-31"),
    ("ERA_2_MID",    "2022-01-01", "2023-12-31"),
    ("ERA_3_RECENT", "2024-01-01", "2026-02-20"),
]

# Rolling window config
ROLLING_WINDOW_DAYS = 18 * 30  # ~18 months
ROLLING_STEP_DAYS = 3 * 30     # ~3 months


def _date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _date_to_end_of_day_ms(date_str: str) -> int:
    return _date_to_ms(date_str) + 86_400_000 - 1


def _ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Era metrics for OH0 (D1, unchanged from original)
# ---------------------------------------------------------------------------

@dataclass
class EraMetrics:
    era: str
    start: str
    end: str
    n_bars: int
    sharpe: float           # native domain
    sharpe_common: float    # common domain: daily UTC, ddof=0, sqrt(365)
    cagr_pct: float
    max_dd_pct: float
    exposure_pct: float
    n_trades: int
    expectancy: float


def _common_sharpe(rets: np.ndarray) -> float:
    """Common-domain Sharpe: daily UTC, ddof=0, sqrt(365)."""
    if len(rets) < 2 or np.std(rets) == 0:
        return 0.0
    return float(np.mean(rets) / np.std(rets) * np.sqrt(365))


def _compute_era_metrics_d1(
    daily_returns: np.ndarray,
    open_times: np.ndarray,
    positions: np.ndarray,
    era_start_ms: int,
    era_end_ms: int,
    era_name: str,
) -> EraMetrics:
    """Compute metrics for a time window from D1 return arrays."""
    _z = EraMetrics(era_name, _ms_to_date(era_start_ms), _ms_to_date(era_end_ms),
                    0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, float("nan"))
    mask = (open_times >= era_start_ms) & (open_times <= era_end_ms)
    era_ret = daily_returns[mask]
    era_pos = positions[mask]

    if len(era_ret) < 2:
        return _z

    # Native OH0 Sharpe: ddof=1, sqrt(365) per frozen spec §9
    sharpe = float(
        np.mean(era_ret) / np.std(era_ret, ddof=1) * np.sqrt(365)
    ) if np.std(era_ret, ddof=1) > 0 else 0.0

    sharpe_c = _common_sharpe(era_ret)

    eq = np.cumprod(1.0 + era_ret)
    n_days = len(era_ret)
    cagr = (eq[-1] ** (365.0 / n_days) - 1.0) * 100.0 if n_days > 0 else 0.0

    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    max_dd = abs(float(np.min(dd))) * 100.0

    avg_expo = float(np.mean(era_pos)) * 100.0

    pos_changes = np.diff(era_pos)
    n_entries = int(np.sum(pos_changes > 0))

    return EraMetrics(
        era=era_name,
        start=_ms_to_date(era_start_ms),
        end=_ms_to_date(era_end_ms),
        n_bars=int(np.sum(mask)),
        sharpe=round(sharpe, 4),
        sharpe_common=round(sharpe_c, 4),
        cagr_pct=round(cagr, 2),
        max_dd_pct=round(max_dd, 2),
        exposure_pct=round(avg_expo, 2),
        n_trades=n_entries,
        expectancy=float("nan"),
    )


# ---------------------------------------------------------------------------
# Decay band classification (shared by both baselines)
# ---------------------------------------------------------------------------

def classify_decay(
    era_metrics: Sequence[EraMetrics | PF0SegmentMetrics],
    rolling_sharpes: list[tuple[str, float]],
) -> str:
    """Classify decay band: DURABLE / WATCH / DECAYING / BROKEN."""
    if len(era_metrics) < 2:
        return "WATCH"

    early = era_metrics[0]
    recent = era_metrics[-1]

    has_expectancy = (
        not math.isnan(recent.expectancy) and not math.isnan(early.expectancy)
    )

    def _safe_ratio(a: float, b: float) -> float:
        if abs(b) < 1e-12:
            return 0.0 if abs(a) < 1e-12 else float("inf")
        return a / b

    sharpe_ratio = _safe_ratio(recent.sharpe, early.sharpe)
    expect_ratio = (
        _safe_ratio(recent.expectancy, early.expectancy)
        if has_expectancy else float("nan")
    )

    # Rolling slope
    if len(rolling_sharpes) >= 3:
        y = np.array([s for _, s in rolling_sharpes])
        x = np.arange(len(y), dtype=np.float64)
        if np.std(x) > 0:
            slope = float(np.corrcoef(x, y)[0, 1] * np.std(y) / np.std(x))
        else:
            slope = 0.0
        n_boot = 1000
        rng = np.random.default_rng(42)
        boot_slopes = np.empty(n_boot)
        for b in range(n_boot):
            idx = rng.choice(len(y), size=len(y), replace=True)
            bx, by = x[idx], y[idx]
            if np.std(bx) > 0:
                boot_slopes[b] = np.corrcoef(bx, by)[0, 1] * np.std(by) / np.std(bx)
            else:
                boot_slopes[b] = 0.0
        ci_high = float(np.percentile(boot_slopes, 97.5))
        slope_sig_negative = ci_high < 0
    else:
        slope = 0.0
        slope_sig_negative = False

    # BROKEN: all conditions hold
    broken_conds: list[bool] = [
        recent.sharpe <= 0,
        recent.cagr_pct <= 0,
    ]
    if has_expectancy:
        broken_conds.append(recent.expectancy <= 0)
    if len(rolling_sharpes) >= 2:
        broken_conds.append(
            rolling_sharpes[-1][1] < 0 and rolling_sharpes[-2][1] < 0
        )
    if all(broken_conds):
        return "BROKEN"

    # DECAYING: >= 2 conditions
    decaying_conds: list[bool] = [
        recent.sharpe <= 0,
        sharpe_ratio < 0.40,
        slope_sig_negative,
    ]
    if has_expectancy:
        decaying_conds.append(recent.expectancy <= 0)
        if early.expectancy != 0:
            decaying_conds.append(expect_ratio < 0.40)
    if sum(decaying_conds) >= 2:
        return "DECAYING"

    # WATCH: any one triggers
    watch_conds: list[bool] = [
        0.40 <= sharpe_ratio < 0.60,
        slope < 0 and not slope_sig_negative,
    ]
    if has_expectancy and early.expectancy != 0:
        watch_conds.append(0.40 <= expect_ratio < 0.60)
    if any(watch_conds):
        return "WATCH"

    # DURABLE: all conditions hold
    durable_conds: list[bool] = [
        recent.sharpe > 0,
        not slope_sig_negative,
        sharpe_ratio >= 0.60,
    ]
    if has_expectancy:
        durable_conds.append(recent.expectancy >= 0)
    if all(durable_conds):
        return "DURABLE"

    return "WATCH"


# ---------------------------------------------------------------------------
# PF0 A01 (self-contained, using pf0_strategy.py)
# ---------------------------------------------------------------------------

def a01_pf0() -> dict[str, Any]:
    """Run A01 temporal decay for PF0_E5_EMA21D1."""
    print("=" * 60)
    print("A01 — PF0_E5_EMA21D1 Temporal Decay (20 bps RT)")
    print("=" * 60)

    feed = DataFeed(DATA_PATH, start="2019-01-01", end="2026-02-20", warmup_days=365)
    h4 = feed.h4_bars
    d1 = feed.d1_bars

    h4_close = np.array([b.close for b in h4], dtype=np.float64)
    h4_high = np.array([b.high for b in h4], dtype=np.float64)
    h4_low = np.array([b.low for b in h4], dtype=np.float64)
    h4_open = np.array([b.open for b in h4], dtype=np.float64)
    h4_volume = np.array([b.volume for b in h4], dtype=np.float64)
    h4_taker_buy = np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64)
    h4_close_time = np.array([b.close_time for b in h4], dtype=np.int64)
    h4_open_time = np.array([b.open_time for b in h4], dtype=np.int64)
    d1_close = np.array([b.close for b in d1], dtype=np.float64)
    d1_close_time = np.array([b.close_time for b in d1], dtype=np.int64)

    result = run_pf0_sim(
        h4_close, h4_high, h4_low, h4_open,
        h4_volume, h4_taker_buy,
        h4_close_time, h4_open_time,
        d1_close, d1_close_time,
        cost_per_side=DEFAULT_COST_PER_SIDE,
    )

    # Era metrics using pf0_strategy's segment computation
    era_results: list[PF0SegmentMetrics] = []
    for era_name, start, end in ERAS:
        m = pf0_compute_segment(
            result, era_name,
            _date_to_ms(start), _date_to_end_of_day_ms(end),
        )
        era_results.append(m)
        print(f"\n  {era_name} ({start} to {end}):")
        print(f"    Sharpe={m.sharpe} (common={m.sharpe_common}), "
              f"CAGR={m.cagr_pct}%, MDD={m.max_dd_pct}%")
        print(f"    Trades={m.n_trades}, Exposure={m.exposure_pct}%, "
              f"Expectancy={m.expectancy}")

    # Rolling Sharpe (H4 NAV-based, native domain)
    rolling_sharpes: list[tuple[str, float]] = []
    assert result.all_navs is not None
    assert result.all_h4_close_times is not None
    all_navs = result.all_navs
    all_ct = result.all_h4_close_times

    report_start = _date_to_ms("2020-01-01")
    report_end = _date_to_end_of_day_ms("2026-02-20")
    window_ms = ROLLING_WINDOW_DAYS * 86_400_000
    step_ms = ROLLING_STEP_DAYS * 86_400_000

    cursor = report_start
    while cursor + window_ms <= report_end:
        w_start = cursor
        w_end = cursor + window_ms
        mask = (all_ct >= w_start) & (all_ct <= w_end)
        w_navs = all_navs[mask]
        if len(w_navs) >= 10:
            rets = np.diff(w_navs) / w_navs[:-1]
            ann = math.sqrt(6.0 * 365.25)
            sh = float(np.mean(rets) / np.std(rets) * ann) if np.std(rets) > 0 else 0.0
            mid = _ms_to_date(w_start + window_ms // 2)
            rolling_sharpes.append((mid, round(sh, 4)))
        cursor += step_ms

    print(f"\n  Rolling Sharpe ({len(rolling_sharpes)} windows):")
    for mid, sh in rolling_sharpes:
        print(f"    {mid}: {sh:+.4f}")

    decay_band = classify_decay(era_results, rolling_sharpes)
    print(f"\n  Decay band: {decay_band}")

    return {
        "baseline_id": "PF0_E5_EMA21D1",
        "league_id": "PUBLIC_FLOW",
        "cost_model": "simple_per_side",
        "default_cost_rt_bps": 20,
        "a01_decay_band": decay_band,
        "eras": [
            {
                "era": m.name, "start": m.start_date, "end": m.end_date,
                "sharpe": m.sharpe, "sharpe_common": m.sharpe_common,
                "cagr_pct": m.cagr_pct, "max_dd_pct": m.max_dd_pct,
                "exposure_pct": m.exposure_pct,
                "n_trades": m.n_trades, "expectancy": m.expectancy,
            }
            for m in era_results
        ],
        "rolling_sharpe": [{"midpoint": m, "sharpe": s} for m, s in rolling_sharpes],
    }


# ---------------------------------------------------------------------------
# OH0 A01 (unchanged logic, uses default 20 bps)
# ---------------------------------------------------------------------------

def a01_oh0() -> dict[str, Any]:
    """Run A01 temporal decay for OH0_D1_TREND40."""
    print("\n" + "=" * 60)
    print("A01 — OH0_D1_TREND40 Temporal Decay (20 bps RT)")
    print("=" * 60)

    feed = DataFeed(DATA_PATH)
    d1_bars = feed.d1_bars

    d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
    d1_open = np.array([b.open for b in d1_bars], dtype=np.float64)
    d1_open_time = np.array([b.open_time for b in d1_bars], dtype=np.int64)

    result = run_oh0_sim(d1_close, d1_open, d1_open_time,
                         cost_per_side=DEFAULT_COST_PER_SIDE)

    era_results: list[EraMetrics] = []
    for era_name, start, end in ERAS:
        m = _compute_era_metrics_d1(
            result.daily_returns, result.open_times, result.positions,
            _date_to_ms(start), _date_to_end_of_day_ms(end), era_name,
        )
        era_results.append(m)
        print(f"\n  {era_name} ({start} to {end}):")
        print(f"    Sharpe={m.sharpe} native/ddof1 (common={m.sharpe_common}), "
              f"CAGR={m.cagr_pct}%, MDD={m.max_dd_pct}%")
        print(f"    Bars={m.n_bars}, Exposure={m.exposure_pct}%")

    # Rolling Sharpe (D1, native ddof=1)
    rolling_sharpes: list[tuple[str, float]] = []
    report_start = _date_to_ms("2020-01-01")
    report_end = _date_to_end_of_day_ms("2026-02-20")
    window_ms = ROLLING_WINDOW_DAYS * 86_400_000
    step_ms = ROLLING_STEP_DAYS * 86_400_000

    cursor = report_start
    while cursor + window_ms <= report_end:
        w_start = cursor
        w_end = cursor + window_ms
        mask = (result.open_times >= w_start) & (result.open_times <= w_end)
        w_ret = result.daily_returns[mask]
        if len(w_ret) >= 10:
            sh = float(
                np.mean(w_ret) / np.std(w_ret, ddof=1) * np.sqrt(365)
            ) if np.std(w_ret, ddof=1) > 0 else 0.0
            mid = _ms_to_date(w_start + window_ms // 2)
            rolling_sharpes.append((mid, round(sh, 4)))
        cursor += step_ms

    print(f"\n  Rolling Sharpe ({len(rolling_sharpes)} windows):")
    for mid, sh in rolling_sharpes:
        print(f"    {mid}: {sh:+.4f}")

    decay_band = classify_decay(era_results, rolling_sharpes)
    print(f"\n  Decay band: {decay_band}")

    return {
        "baseline_id": "OH0_D1_TREND40",
        "league_id": "OHLCV_ONLY",
        "cost_model": "simple_per_side",
        "default_cost_rt_bps": 20,
        "a01_decay_band": decay_band,
        "eras": [
            {
                "era": m.era, "start": m.start, "end": m.end,
                "sharpe": m.sharpe, "sharpe_common": m.sharpe_common,
                "cagr_pct": m.cagr_pct, "max_dd_pct": m.max_dd_pct,
                "exposure_pct": m.exposure_pct, "n_trades": m.n_trades,
            }
            for m in era_results
        ],
        "rolling_sharpe": [{"midpoint": m, "sharpe": s} for m, s in rolling_sharpes],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "OH0_D1_TREND40").mkdir(exist_ok=True)
    (RESULTS_DIR / "PF0_E5_EMA21D1").mkdir(exist_ok=True)

    pf0_data = a01_pf0()
    oh0_data = a01_oh0()

    # Write JSON results
    for data, subdir in [(pf0_data, "PF0_E5_EMA21D1"), (oh0_data, "OH0_D1_TREND40")]:
        path = RESULTS_DIR / subdir / "a01_decay_summary.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  Written: {path.relative_to(ROOT)}")

    # Write era comparison CSV
    csv_path = OUTPUT_DIR / "a01_era_comparison.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "baseline_id", "era", "start", "end",
            "sharpe_native", "sharpe_common", "cagr_pct", "max_dd_pct",
            "exposure_pct", "n_trades", "cost_rt_bps",
        ])
        for data in [pf0_data, oh0_data]:
            for era in data["eras"]:
                writer.writerow([
                    data["baseline_id"], era["era"], era["start"], era["end"],
                    era["sharpe"], era["sharpe_common"], era["cagr_pct"],
                    era["max_dd_pct"], era["exposure_pct"], era["n_trades"],
                    data["default_cost_rt_bps"],
                ])
    print(f"  Written: {csv_path.relative_to(ROOT)}")

    # Summary
    print("\n" + "=" * 60)
    print("A01 Summary (both at 20 bps RT)")
    print("=" * 60)
    print(f"  PF0_E5_EMA21D1:  {pf0_data['a01_decay_band']}")
    print(f"  OH0_D1_TREND40:  {oh0_data['a01_decay_band']}")


if __name__ == "__main__":
    main()
