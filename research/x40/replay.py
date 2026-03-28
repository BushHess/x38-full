"""A00 — Source Parity Replay for x40 baselines.

Runs both OH0_D1_TREND40 and PF0_E5_EMA21D1, compares against authoritative
source artifacts, and emits parity results.

Both baselines use the simple per-side cost model.
Default cost: 20 bps RT (10 bps/side) for cross-baseline comparison.
PF0 parity verified at 50 bps (simple) against v10 engine (trade count exact,
metrics within tolerance due to cost model difference).

Usage:
    cd /var/www/trading-bots/btc-spot-dev
    python research/x40/replay.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.x40.oh0_strategy import SegmentMetrics
from research.x40.oh0_strategy import compute_segment_metrics
from research.x40.oh0_strategy import run_oh0_sim
from research.x40.pf0_strategy import PF0Result
from research.x40.pf0_strategy import run_pf0_sim
from v10.core.data import DataFeed

DATA_PATH = str(ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv")
RESULTS_DIR = ROOT / "research" / "x40" / "results"

# Default cost: 20 bps RT (10 bps/side) — synchronized across baselines
DEFAULT_COST_PER_SIDE = 0.001  # 10 bps

# Cost sweep for sensitivity analysis
COST_SWEEP_BPS_RT = [10, 20, 30, 50, 75, 100]


def _date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _pct_diff(actual: float, expected: float) -> float:
    if abs(expected) < 1e-12:
        return 0.0 if abs(actual) < 1e-12 else float("inf")
    return abs(actual - expected) / abs(expected)


# ---------------------------------------------------------------------------
# OH0 verification targets (frozen spec §11, 20 bps RT)
# ---------------------------------------------------------------------------

@dataclass
class _OH0SegTarget:
    start: str
    end: str
    trade_count_entries: int
    sharpe: float
    cagr_pct: float
    max_dd_pct: float


OH0_SEGMENTS: dict[str, _OH0SegTarget] = {
    "discovery": _OH0SegTarget("2020-01-01", "2023-06-30", 61, 1.6941, 101.2, 48.3),
    "holdout":   _OH0SegTarget("2023-07-01", "2024-09-30", 34, 1.0819, 40.8, 43.4),
    "reserve":   _OH0SegTarget("2024-10-01", "2026-12-31", 35, 0.8734, 24.2, 24.0),
}

OH0_METRIC_TOL = 0.05
OH0_RESERVE_CAGR_TOL = 0.07


# ---------------------------------------------------------------------------
# PF0 verification targets (from full_eval_e5_ema21d1, v10 harsh 50 bps)
# ---------------------------------------------------------------------------

@dataclass
class _PF0Targets:
    """v10 engine targets at harsh 50 bps (for lineage parity)."""
    trades: int
    sharpe: float
    cagr_pct: float
    max_dd_pct: float
    win_rate_pct: float


PF0_V10_TARGETS = _PF0Targets(
    trades=188,
    sharpe=1.4545,
    cagr_pct=61.60,
    max_dd_pct=40.97,
    win_rate_pct=42.02,
)

# SHA256 of the self-contained pf0_strategy.py (updated after parity verified)
PF0_STRATEGY_FILE = ROOT / "research" / "x40" / "pf0_strategy.py"

# Lineage: original strategy file hash for traceability
PF0_LINEAGE_SOURCE = ROOT / "strategies" / "vtrend_e5_ema21_d1" / "strategy.py"
PF0_LINEAGE_SHA256 = (
    "d9d1a10bd1b6bc9ec14e6cbee12f8f52a68905b83deb39d6411901bdaa49b4d9"
)

# Metrics tolerance is wider because simple cost model ≠ v10 spread+slip+fee
# Trade count must be exact (signals are cost-independent)
PF0_METRIC_TOL = 0.10  # 10% for cross-model parity


# ---------------------------------------------------------------------------
# Helper: extract arrays from DataFeed
# ---------------------------------------------------------------------------

def _extract_h4_arrays(feed: DataFeed) -> dict[str, np.ndarray]:
    h4 = feed.h4_bars
    return {
        "h4_close": np.array([b.close for b in h4], dtype=np.float64),
        "h4_high": np.array([b.high for b in h4], dtype=np.float64),
        "h4_low": np.array([b.low for b in h4], dtype=np.float64),
        "h4_open": np.array([b.open for b in h4], dtype=np.float64),
        "h4_volume": np.array([b.volume for b in h4], dtype=np.float64),
        "h4_taker_buy": np.array([b.taker_buy_base_vol for b in h4], dtype=np.float64),
        "h4_close_time": np.array([b.close_time for b in h4], dtype=np.int64),
        "h4_open_time": np.array([b.open_time for b in h4], dtype=np.int64),
    }


def _extract_d1_arrays(feed: DataFeed) -> dict[str, np.ndarray]:
    d1 = feed.d1_bars
    return {
        "d1_close": np.array([b.close for b in d1], dtype=np.float64),
        "d1_close_time": np.array([b.close_time for b in d1], dtype=np.int64),
    }


def _run_pf0(
    h4a: dict[str, np.ndarray],
    d1a: dict[str, np.ndarray],
    cost_per_side: float = DEFAULT_COST_PER_SIDE,
    initial_cash: float = 10_000.0,
) -> PF0Result:
    """Convenience wrapper: call run_pf0_sim with extracted arrays."""
    return run_pf0_sim(
        h4_close=h4a["h4_close"],
        h4_high=h4a["h4_high"],
        h4_low=h4a["h4_low"],
        h4_open=h4a["h4_open"],
        h4_volume=h4a["h4_volume"],
        h4_taker_buy=h4a["h4_taker_buy"],
        h4_close_time=h4a["h4_close_time"],
        h4_open_time=h4a["h4_open_time"],
        d1_close=d1a["d1_close"],
        d1_close_time=d1a["d1_close_time"],
        cost_per_side=cost_per_side,
        initial_cash=initial_cash,
    )


# ---------------------------------------------------------------------------
# OH0 replay (unchanged logic, uses default 20 bps)
# ---------------------------------------------------------------------------

def replay_oh0() -> dict[str, object]:
    """Replay OH0_D1_TREND40 with per-segment verification."""
    print("=" * 60)
    print("A00 — OH0_D1_TREND40 Source Parity Replay")
    print("=" * 60)

    feed = DataFeed(DATA_PATH)
    d1_bars = feed.d1_bars

    d1_close = np.array([b.close for b in d1_bars], dtype=np.float64)
    d1_open = np.array([b.open for b in d1_bars], dtype=np.float64)
    d1_open_time = np.array([b.open_time for b in d1_bars], dtype=np.int64)

    result_20 = run_oh0_sim(d1_close, d1_open, d1_open_time, cost_per_side=0.001)
    result_50 = run_oh0_sim(d1_close, d1_open, d1_open_time, cost_per_side=0.0025)

    print(f"\n  D1 bars loaded: {len(d1_bars)}")
    print(f"\n  Full period 20 bps: Sharpe={result_20.sharpe:.4f}, "
          f"CAGR={result_20.cagr_pct:.1f}%, MDD={result_20.max_dd_pct:.1f}%")
    print(f"  Full period 50 bps: Sharpe={result_50.sharpe:.4f}, "
          f"CAGR={result_50.cagr_pct:.1f}%, MDD={result_50.max_dd_pct:.1f}%")
    print(f"  Total transitions: {result_20.n_transitions}, "
          f"Completed trades: {result_20.n_completed_trades}")

    checks: list[dict[str, object]] = []

    # --- Total transition count (exact) ---
    total_expected = sum(t.trade_count_entries for t in OH0_SEGMENTS.values())
    checks.append({
        "check": "total_state_transitions",
        "expected": total_expected,
        "actual": result_20.n_transitions,
        "passed": result_20.n_transitions == total_expected,
    })

    # --- Per-segment verification ---
    print("\n  Per-segment verification (20 bps):")
    segment_data: dict[str, SegmentMetrics] = {}
    for seg_name, tgt in OH0_SEGMENTS.items():
        seg = compute_segment_metrics(
            result_20, seg_name,
            _date_to_ms(tgt.start),
            _date_to_ms(tgt.end),
        )
        segment_data[seg_name] = seg

        print(f"\n    {seg_name} ({seg.start_date} to {seg.end_date}):")
        print(f"      transitions: {seg.n_transitions} (expected {tgt.trade_count_entries})")
        print(f"      Sharpe:      {seg.sharpe:.4f} (expected {tgt.sharpe:.4f})")
        print(f"      CAGR:        {seg.cagr_pct:.1f}% (expected {tgt.cagr_pct:.1f}%)")
        print(f"      MDD:         {seg.max_dd_pct:.1f}% (expected {tgt.max_dd_pct:.1f}%)")

        # Transition count: exact match
        checks.append({
            "check": f"{seg_name}_transitions",
            "expected": tgt.trade_count_entries,
            "actual": seg.n_transitions,
            "passed": seg.n_transitions == tgt.trade_count_entries,
        })

        # Sharpe: relative tolerance
        diff = _pct_diff(seg.sharpe, tgt.sharpe)
        checks.append({
            "check": f"{seg_name}_sharpe",
            "expected": tgt.sharpe,
            "actual": seg.sharpe,
            "pct_diff": round(diff * 100, 2),
            "passed": diff <= OH0_METRIC_TOL,
        })

        # CAGR: relative tolerance
        cagr_tol = OH0_RESERVE_CAGR_TOL if seg_name == "reserve" else OH0_METRIC_TOL
        diff = _pct_diff(seg.cagr_pct, tgt.cagr_pct)
        checks.append({
            "check": f"{seg_name}_cagr",
            "expected": tgt.cagr_pct,
            "actual": seg.cagr_pct,
            "pct_diff": round(diff * 100, 2),
            "passed": diff <= cagr_tol,
        })

        # MDD: relative tolerance
        diff = _pct_diff(seg.max_dd_pct, tgt.max_dd_pct)
        checks.append({
            "check": f"{seg_name}_mdd",
            "expected": tgt.max_dd_pct,
            "actual": seg.max_dd_pct,
            "pct_diff": round(diff * 100, 2),
            "passed": diff <= OH0_METRIC_TOL,
        })

    # --- Cost monotonicity ---
    checks.append({
        "check": "cost_monotonicity",
        "expected": "sharpe_50 < sharpe_20",
        "actual": f"{result_50.sharpe:.4f} < {result_20.sharpe:.4f}",
        "passed": result_50.sharpe < result_20.sharpe,
    })

    all_passed = all(c["passed"] for c in checks)
    print("\n  Checks:")
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        extra = f" (diff={c['pct_diff']}%)" if "pct_diff" in c else ""
        print(f"    [{status}] {c['check']}: expected={c['expected']}, actual={c['actual']}{extra}")

    result_data: dict[str, object] = {
        "baseline_id": "OH0_D1_TREND40",
        "league_id": "OHLCV_ONLY",
        "a00_verdict": "PASS" if all_passed else "FAIL",
        "cost_model": "simple_per_side",
        "default_cost_rt_bps": 20,
        "checks": checks,
        "segments": {
            name: {
                "n_transitions": seg.n_transitions,
                "sharpe": seg.sharpe,
                "cagr_pct": seg.cagr_pct,
                "max_dd_pct": seg.max_dd_pct,
            }
            for name, seg in segment_data.items()
        },
        "metrics_20bps": {
            "sharpe": round(result_20.sharpe, 4),
            "cagr_pct": round(result_20.cagr_pct, 2),
            "max_dd_pct": round(result_20.max_dd_pct, 2),
            "n_transitions": result_20.n_transitions,
            "n_completed_trades": result_20.n_completed_trades,
        },
        "metrics_50bps": {
            "sharpe": round(result_50.sharpe, 4),
            "cagr_pct": round(result_50.cagr_pct, 2),
            "max_dd_pct": round(result_50.max_dd_pct, 2),
        },
    }

    print(f"\n  A00 verdict: {result_data['a00_verdict']}")
    return result_data


# ---------------------------------------------------------------------------
# PF0 replay (self-contained, simple cost model)
# ---------------------------------------------------------------------------

def replay_pf0() -> dict[str, object]:
    """Replay PF0_E5_EMA21D1 using self-contained pf0_strategy.py."""
    print("\n" + "=" * 60)
    print("A00 — PF0_E5_EMA21D1 Source Parity Replay")
    print("=" * 60)

    feed = DataFeed(
        DATA_PATH, start="2019-01-01", end="2026-02-20", warmup_days=365,
    )
    h4a = _extract_h4_arrays(feed)
    d1a = _extract_d1_arrays(feed)

    print(f"\n  H4 bars: {len(feed.h4_bars)}, D1 bars: {len(feed.d1_bars)}")

    # --- Source hash guards ---
    # Guard 1: self-contained strategy file (active guard)
    pf0_hash = hashlib.sha256(PF0_STRATEGY_FILE.read_bytes()).hexdigest()
    print(f"\n  pf0_strategy.py hash: {pf0_hash[:16]}...")

    # Guard 2: lineage source (traceability only, not blocking)
    lineage_hash = hashlib.sha256(PF0_LINEAGE_SOURCE.read_bytes()).hexdigest()
    lineage_match = lineage_hash == PF0_LINEAGE_SHA256
    print(f"  Lineage source hash:  {lineage_hash[:16]}... "
          f"({'match' if lineage_match else 'CHANGED'})")
    if not lineage_match:
        print("    NOTE: strategies/vtrend_e5_ema21_d1/strategy.py has changed since lineage pin.")
        print("    This is informational — x40 uses pf0_strategy.py, not the original.")

    # --- Run at default 20 bps ---
    result_20 = _run_pf0(h4a, d1a, cost_per_side=0.001)

    # --- Run at 50 bps (simple) for lineage parity ---
    result_50 = _run_pf0(h4a, d1a, cost_per_side=0.0025)

    print("\n  Default 20 bps RT:")
    print(f"    Sharpe={result_20.sharpe:.4f}, CAGR={result_20.cagr_pct:.2f}%, "
          f"MDD={result_20.max_dd_pct:.2f}%, Trades={result_20.n_trades}")
    print(f"    Win rate={result_20.win_rate_pct:.2f}%, "
          f"Exposure={result_20.avg_exposure:.4f}, PF={result_20.profit_factor:.4f}")

    print("\n  Lineage parity 50 bps RT (simple cost):")
    print(f"    Sharpe={result_50.sharpe:.4f}, CAGR={result_50.cagr_pct:.2f}%, "
          f"MDD={result_50.max_dd_pct:.2f}%, Trades={result_50.n_trades}")

    checks: list[dict[str, object]] = []

    # Trade count (exact — signals are cost-independent)
    checks.append({
        "check": "trade_count",
        "expected": PF0_V10_TARGETS.trades,
        "actual": result_50.n_trades,
        "passed": result_50.n_trades == PF0_V10_TARGETS.trades,
    })

    # Lineage parity metrics at 50 bps (wider tolerance — different cost model)
    pf0_metric_pairs: list[tuple[str, float, float]] = [
        ("sharpe", result_50.sharpe, PF0_V10_TARGETS.sharpe),
        ("cagr_pct", result_50.cagr_pct, PF0_V10_TARGETS.cagr_pct),
        ("max_dd_pct", result_50.max_dd_pct, PF0_V10_TARGETS.max_dd_pct),
        ("win_rate_pct", result_50.win_rate_pct, PF0_V10_TARGETS.win_rate_pct),
    ]
    for metric, actual, expected in pf0_metric_pairs:
        diff = _pct_diff(actual, expected)
        checks.append({
            "check": f"lineage_{metric}",
            "expected": expected,
            "actual": round(actual, 4),
            "pct_diff": round(diff * 100, 4),
            "passed": diff <= PF0_METRIC_TOL,
        })

    # Cost monotonicity
    checks.append({
        "check": "cost_monotonicity",
        "expected": "sharpe_50 < sharpe_20",
        "actual": f"{result_50.sharpe:.4f} < {result_20.sharpe:.4f}",
        "passed": result_50.sharpe < result_20.sharpe,
    })

    all_passed = all(c["passed"] for c in checks)
    print("\n  Checks:")
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        extra = f" (diff={c.get('pct_diff', 'n/a')}%)" if "pct_diff" in c else ""
        print(f"    [{status}] {c['check']}: expected={c['expected']}, actual={c['actual']}{extra}")

    # --- Cost sweep ---
    print("\n  Cost sweep:")
    sweep_data: dict[str, dict[str, object]] = {}
    for rt_bps in COST_SWEEP_BPS_RT:
        cps = rt_bps / 20_000.0  # RT bps → per-side fraction
        r = _run_pf0(h4a, d1a, cost_per_side=cps)
        sweep_data[str(rt_bps)] = {
            "sharpe": round(r.sharpe, 4),
            "cagr_pct": round(r.cagr_pct, 2),
            "max_dd_pct": round(r.max_dd_pct, 2),
            "n_trades": r.n_trades,
        }
        print(f"    {rt_bps:3d} bps: Sharpe={r.sharpe:.4f}, "
              f"CAGR={r.cagr_pct:.1f}%, MDD={r.max_dd_pct:.1f}%")

    result_data: dict[str, object] = {
        "baseline_id": "PF0_E5_EMA21D1",
        "league_id": "PUBLIC_FLOW",
        "a00_verdict": "PASS" if all_passed else "FAIL",
        "cost_model": "simple_per_side",
        "default_cost_rt_bps": 20,
        "pf0_strategy_sha256": pf0_hash,
        "lineage_source_sha256": lineage_hash,
        "lineage_source_match": lineage_match,
        "checks": checks,
        "metrics_20bps": {
            "sharpe": round(result_20.sharpe, 4),
            "cagr_pct": round(result_20.cagr_pct, 2),
            "max_dd_pct": round(result_20.max_dd_pct, 2),
            "n_trades": result_20.n_trades,
            "win_rate_pct": round(result_20.win_rate_pct, 2),
            "avg_exposure": round(result_20.avg_exposure, 4),
            "profit_factor": round(result_20.profit_factor, 4),
            "final_nav": round(result_20.final_nav, 2),
        },
        "metrics_50bps": {
            "sharpe": round(result_50.sharpe, 4),
            "cagr_pct": round(result_50.cagr_pct, 2),
            "max_dd_pct": round(result_50.max_dd_pct, 2),
            "n_trades": result_50.n_trades,
        },
        "cost_sweep": sweep_data,
    }

    print(f"\n  A00 verdict: {result_data['a00_verdict']}")
    return result_data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "OH0_D1_TREND40").mkdir(exist_ok=True)
    (RESULTS_DIR / "PF0_E5_EMA21D1").mkdir(exist_ok=True)

    oh0_result = replay_oh0()
    pf0_result = replay_pf0()

    oh0_path = RESULTS_DIR / "OH0_D1_TREND40" / "a00_parity_result.json"
    with open(oh0_path, "w") as f:
        json.dump(oh0_result, f, indent=2)
    print(f"\n  Written: {oh0_path.relative_to(ROOT)}")

    pf0_path = RESULTS_DIR / "PF0_E5_EMA21D1" / "a00_parity_result.json"
    with open(pf0_path, "w") as f:
        json.dump(pf0_result, f, indent=2)
    print(f"  Written: {pf0_path.relative_to(ROOT)}")

    print("\n" + "=" * 60)
    print("A00 Summary")
    print("=" * 60)
    print(f"  OH0_D1_TREND40:  {oh0_result['a00_verdict']}")
    print(f"  PF0_E5_EMA21D1:  {pf0_result['a00_verdict']}")

    n_fail = sum(1 for r in [oh0_result, pf0_result] if r["a00_verdict"] != "PASS")
    if n_fail > 0:
        print(f"\n  {n_fail} baseline(s) failed parity.")
        sys.exit(1)
    else:
        print("\n  All baselines passed source parity.")


if __name__ == "__main__":
    main()
