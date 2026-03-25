#!/usr/bin/env python3
"""Group 1: per-episode conditional comparison for cascade episodes.

Runs baseline (cooldown=0) and overlayA (cooldown=12) backtests,
then for each cascade episode computes side-by-side metrics.

Outputs:
  - out_overlayA_conditional/group1_cascade_episode_compare_full.csv
  - out_overlayA_conditional/group1_cascade_episode_compare_holdout.csv

Usage:
  python experiments/conditional_analysis/group1_cascade_compare.py
"""

import csv
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS

# Reuse InstrumentedV8Apex from fix_loop step1 for blocked-entry counting
from experiments.overlayA.step1_export import InstrumentedV8Apex
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

# ── Constants ────────────────────────────────────────────────────────────────

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
SCENARIO = "harsh"
K = 12  # Overlay A cooldown bars

OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
HOLDOUT_START_MS = 1727740800000  # 2024-10-01 00:00 UTC


# ── Episode loading ──────────────────────────────────────────────────────────

def load_labeled_episodes(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row["episode_id"] = int(row["episode_id"])
            row["peak_ts"] = int(row["peak_ts"])
            row["trough_ts"] = int(row["trough_ts"])
            row["end_ts"] = int(row["end_ts"])
            row["depth_pct"] = float(row["depth_pct"])
            row["duration_days"] = float(row["duration_days"])
            row["is_cascade"] = row["is_cascade"] == "True"
            rows.append(row)
    return rows


# ── Backtest helpers ─────────────────────────────────────────────────────────

def run_backtest(cfg, feed):
    strat = V8ApexStrategy(cfg)
    cost = SCENARIOS[SCENARIO]
    engine = BacktestEngine(
        feed=feed, strategy=strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    )
    return engine.run()


def run_instrumented(cfg, feed):
    strat = InstrumentedV8Apex(cfg)
    cost = SCENARIOS[SCENARIO]
    engine = BacktestEngine(
        feed=feed, strategy=strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    )
    result = engine.run()
    return result, strat.signal_log


# ── Per-episode metric extraction ────────────────────────────────────────────

def nav_at_ts(equity, ts_ms):
    """Find NAV at closest equity point <= ts_ms."""
    best = None
    for snap in equity:
        if snap.close_time <= ts_ms:
            best = snap
        else:
            break
    return best.nav_mid if best else None


def episode_metrics(equity, trades, fills, peak_ts, end_ts):
    """Compute episode-level metrics for one variant within [peak_ts, end_ts]."""
    # NAV at episode boundaries
    nav_peak = nav_at_ts(equity, peak_ts)
    nav_end = nav_at_ts(equity, end_ts)

    if nav_peak is None or nav_end is None:
        return None

    # PnL
    pnl = nav_end - nav_peak
    ret_pct = (pnl / nav_peak) * 100 if nav_peak > 0 else 0.0

    # MDD within window (relative to NAV at episode peak_ts)
    window_navs = [s.nav_mid for s in equity
                   if peak_ts <= s.close_time <= end_ts]
    if window_navs:
        running_peak = nav_peak
        max_dd = 0.0
        for nav in window_navs:
            running_peak = max(running_peak, nav)
            dd = (running_peak - nav) / running_peak if running_peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        mdd_pct = max_dd * 100
    else:
        mdd_pct = 0.0

    # Recovery: first point in window where NAV >= nav_peak
    recovery_days = None
    # Find trough first (lowest NAV in window)
    trough_ts = peak_ts
    trough_nav = nav_peak
    for s in equity:
        if peak_ts <= s.close_time <= end_ts:
            if s.nav_mid < trough_nav:
                trough_nav = s.nav_mid
                trough_ts = s.close_time

    # Recovery from trough to peak level
    for s in equity:
        if s.close_time > trough_ts and s.close_time <= end_ts:
            if s.nav_mid >= nav_peak * 0.999:
                recovery_days = (s.close_time - trough_ts) / 86_400_000
                break

    # Trades exiting in window
    window_trades = [t for t in trades
                     if peak_ts <= t.exit_ts_ms <= end_ts]
    n_trades = len(window_trades)
    n_emergency_dd = sum(1 for t in window_trades
                         if t.exit_reason == "emergency_dd")

    # Fills in window
    window_fills = [f for f in fills
                    if peak_ts <= f.ts_ms <= end_ts]
    total_fees = sum(f.fee for f in window_fills)

    return {
        "nav_peak": round(nav_peak, 2),
        "nav_end": round(nav_end, 2),
        "episode_pnl": round(pnl, 2),
        "episode_return_pct": round(ret_pct, 2),
        "episode_mdd_pct": round(mdd_pct, 2),
        "recovery_days": round(recovery_days, 1) if recovery_days is not None else "",
        "n_trades": n_trades,
        "n_emergency_dd": n_emergency_dd,
        "total_fees": round(total_fees, 2),
    }


def count_blocked_entries(signal_log, peak_ts, end_ts):
    """Count overlayA-blocked entries within [peak_ts, end_ts]."""
    return sum(
        1 for e in signal_log
        if e["event_type"] == "entry_blocked"
        and e["reason"] == "cooldown_after_emergency_dd"
        and peak_ts <= e["bar_ts_ms"] <= end_ts
    )


# ── CSV output ───────────────────────────────────────────────────────────────

COMPARE_FIELDS = [
    "episode_id", "peak_date", "trough_date", "end_date",
    "depth_pct_baseline", "duration_days",
    # Baseline
    "bl_nav_peak", "bl_nav_end", "bl_pnl", "bl_return_pct",
    "bl_mdd_pct", "bl_recovery_days",
    "bl_n_trades", "bl_n_emergency_dd", "bl_total_fees",
    # OverlayA
    "ov_nav_peak", "ov_nav_end", "ov_pnl", "ov_return_pct",
    "ov_mdd_pct", "ov_recovery_days",
    "ov_n_trades", "ov_n_emergency_dd", "ov_total_fees",
    "ov_n_blocked_entries",
    # Deltas
    "delta_pnl", "delta_return_pct", "delta_mdd_pp",
    "delta_n_emergency_dd", "delta_n_trades",
]


def write_compare_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMPARE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 70)
    print("  GROUP 1: CASCADE EPISODE CONDITIONAL COMPARISON")
    print("=" * 70)
    print(f"  Scenario: {SCENARIO}")
    print(f"  Baseline: cooldown_after_emergency_dd_bars = 0")
    print(f"  OverlayA: cooldown_after_emergency_dd_bars = {K}")
    print()

    # Load data once
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)

    # Run baseline (cooldown=0)
    print("  Running baseline (cooldown=0)...")
    bl_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=0)
    bl_result = run_backtest(bl_cfg, feed)
    print(f"    Trades: {len(bl_result.trades)}, "
          f"Final NAV: {bl_result.summary.get('final_nav_mid', 0):.2f}, "
          f"MDD: {bl_result.summary.get('max_drawdown_mid_pct', 0):.2f}%")

    # Run overlayA (cooldown=K), instrumented for block counting
    print(f"  Running overlayA (cooldown={K}), instrumented...")
    ov_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=K)
    ov_result, signal_log = run_instrumented(ov_cfg, feed)
    print(f"    Trades: {len(ov_result.trades)}, "
          f"Final NAV: {ov_result.summary.get('final_nav_mid', 0):.2f}, "
          f"MDD: {ov_result.summary.get('max_drawdown_mid_pct', 0):.2f}%")
    print()

    # Load cascade episodes
    full_episodes = load_labeled_episodes(OUTDIR / "episodes_labeled_full.csv")
    holdout_episodes = load_labeled_episodes(OUTDIR / "episodes_labeled_holdout.csv")

    cascade_full = [ep for ep in full_episodes if ep["is_cascade"]]
    cascade_holdout = [ep for ep in holdout_episodes if ep["is_cascade"]]

    print(f"  Cascade episodes: {len(cascade_full)} full, {len(cascade_holdout)} holdout")
    print()

    # ── Compare each cascade episode ────────────────────────────────────

    def compare_episode(ep, bl_eq, bl_trades, bl_fills,
                        ov_eq, ov_trades, ov_fills, sig_log):
        peak_ts = ep["peak_ts"]
        end_ts = ep["end_ts"]

        bl_m = episode_metrics(bl_eq, bl_trades, bl_fills, peak_ts, end_ts)
        ov_m = episode_metrics(ov_eq, ov_trades, ov_fills, peak_ts, end_ts)

        if bl_m is None or ov_m is None:
            return None

        n_blocked = count_blocked_entries(sig_log, peak_ts, end_ts)

        return {
            "episode_id": ep["episode_id"],
            "peak_date": ep["peak_date"],
            "trough_date": ep["trough_date"],
            "end_date": ep["end_date"],
            "depth_pct_baseline": ep["depth_pct"],
            "duration_days": ep["duration_days"],
            # Baseline
            "bl_nav_peak": bl_m["nav_peak"],
            "bl_nav_end": bl_m["nav_end"],
            "bl_pnl": bl_m["episode_pnl"],
            "bl_return_pct": bl_m["episode_return_pct"],
            "bl_mdd_pct": bl_m["episode_mdd_pct"],
            "bl_recovery_days": bl_m["recovery_days"],
            "bl_n_trades": bl_m["n_trades"],
            "bl_n_emergency_dd": bl_m["n_emergency_dd"],
            "bl_total_fees": bl_m["total_fees"],
            # OverlayA
            "ov_nav_peak": ov_m["nav_peak"],
            "ov_nav_end": ov_m["nav_end"],
            "ov_pnl": ov_m["episode_pnl"],
            "ov_return_pct": ov_m["episode_return_pct"],
            "ov_mdd_pct": ov_m["episode_mdd_pct"],
            "ov_recovery_days": ov_m["recovery_days"],
            "ov_n_trades": ov_m["n_trades"],
            "ov_n_emergency_dd": ov_m["n_emergency_dd"],
            "ov_total_fees": ov_m["total_fees"],
            "ov_n_blocked_entries": n_blocked,
            # Deltas
            "delta_pnl": round(ov_m["episode_pnl"] - bl_m["episode_pnl"], 2),
            "delta_return_pct": round(
                ov_m["episode_return_pct"] - bl_m["episode_return_pct"], 2),
            "delta_mdd_pp": round(
                ov_m["episode_mdd_pct"] - bl_m["episode_mdd_pct"], 2),
            "delta_n_emergency_dd": (
                ov_m["n_emergency_dd"] - bl_m["n_emergency_dd"]),
            "delta_n_trades": ov_m["n_trades"] - bl_m["n_trades"],
        }

    # Full period
    print("  FULL PERIOD — Cascade episodes:")
    full_rows = []
    for ep in cascade_full:
        row = compare_episode(
            ep, bl_result.equity, bl_result.trades, bl_result.fills,
            ov_result.equity, ov_result.trades, ov_result.fills, signal_log,
        )
        if row:
            full_rows.append(row)

    _print_comparison_table(full_rows)

    full_csv = OUTDIR / "group1_cascade_episode_compare_full.csv"
    write_compare_csv(full_rows, full_csv)
    print(f"\n  Saved: {full_csv}")

    # Holdout period
    print(f"\n  HOLDOUT PERIOD — Cascade episodes:")
    holdout_rows = []
    for ep in cascade_holdout:
        row = compare_episode(
            ep, bl_result.equity, bl_result.trades, bl_result.fills,
            ov_result.equity, ov_result.trades, ov_result.fills, signal_log,
        )
        if row:
            holdout_rows.append(row)

    _print_comparison_table(holdout_rows)

    holdout_csv = OUTDIR / "group1_cascade_episode_compare_holdout.csv"
    write_compare_csv(holdout_rows, holdout_csv)
    print(f"\n  Saved: {holdout_csv}")

    # ── Aggregate summary ───────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  AGGREGATE SUMMARY — CASCADE EPISODES")
    print(f"{'='*70}")

    for label, rows in [("Full", full_rows), ("Holdout", holdout_rows)]:
        if not rows:
            continue
        n = len(rows)
        total_bl_pnl = sum(r["bl_pnl"] for r in rows)
        total_ov_pnl = sum(r["ov_pnl"] for r in rows)
        total_delta = sum(r["delta_pnl"] for r in rows)
        avg_bl_mdd = np.mean([r["bl_mdd_pct"] for r in rows])
        avg_ov_mdd = np.mean([r["ov_mdd_pct"] for r in rows])
        total_bl_emdd = sum(r["bl_n_emergency_dd"] for r in rows)
        total_ov_emdd = sum(r["ov_n_emergency_dd"] for r in rows)
        total_blocked = sum(r["ov_n_blocked_entries"] for r in rows)
        total_bl_fees = sum(r["bl_total_fees"] for r in rows)
        total_ov_fees = sum(r["ov_total_fees"] for r in rows)

        print(f"\n  {label} ({n} cascade episodes):")
        print(f"    PnL:            baseline ${total_bl_pnl:>+10,.2f}  "
              f"| overlayA ${total_ov_pnl:>+10,.2f}  "
              f"| delta ${total_delta:>+10,.2f}")
        print(f"    Avg MDD:        baseline {avg_bl_mdd:>8.2f}%  "
              f"| overlayA {avg_ov_mdd:>8.2f}%  "
              f"| delta {avg_ov_mdd - avg_bl_mdd:>+8.2f}pp")
        print(f"    EmDD exits:     baseline {total_bl_emdd:>8d}  "
              f"| overlayA {total_ov_emdd:>8d}  "
              f"| delta {total_ov_emdd - total_bl_emdd:>+8d}")
        print(f"    Blocked entries:                      "
              f"| overlayA {total_blocked:>8d}")
        print(f"    Fees:           baseline ${total_bl_fees:>10,.2f}  "
              f"| overlayA ${total_ov_fees:>10,.2f}  "
              f"| delta ${total_ov_fees - total_bl_fees:>+10,.2f}")

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")
    print("=" * 70)


def _print_comparison_table(rows):
    """Print a readable comparison table."""
    if not rows:
        print("    (no cascade episodes)")
        return

    hdr = (f"    {'ID':>3} {'Peak':>12} {'Trough':>12} "
           f"{'BL PnL':>10} {'OV PnL':>10} {'Δ PnL':>10} "
           f"{'BL MDD%':>8} {'OV MDD%':>8} {'ΔMDDpp':>7} "
           f"{'BL ED':>5} {'OV ED':>5} {'Block':>5}")
    print(hdr)
    print("    " + "-" * (len(hdr) - 4))
    for r in rows:
        print(f"    {r['episode_id']:>3} {r['peak_date']:>12} {r['trough_date']:>12} "
              f"{r['bl_pnl']:>+10,.0f} {r['ov_pnl']:>+10,.0f} "
              f"{r['delta_pnl']:>+10,.0f} "
              f"{r['bl_mdd_pct']:>8.2f} {r['ov_mdd_pct']:>8.2f} "
              f"{r['delta_mdd_pp']:>+7.2f} "
              f"{r['bl_n_emergency_dd']:>5} {r['ov_n_emergency_dd']:>5} "
              f"{r['ov_n_blocked_entries']:>5}")


if __name__ == "__main__":
    main()
