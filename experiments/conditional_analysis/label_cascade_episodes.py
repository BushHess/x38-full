#!/usr/bin/env python3
"""Label drawdown episodes with cascade status based on baseline trades.

Definition:
  cascade_episode = episode in which baseline has ≥2 emergency_dd exits
  consecutively (in exit-time order) within [peak_ts, end_ts].

Inputs:
  - out_overlayA_conditional/episodes_baseline_full.csv
  - out_overlayA_conditional/episodes_baseline_holdout.csv
  - out_v10_apex/trades.csv  (baseline closed trades)

Outputs:
  - out_overlayA_conditional/episodes_labeled_full.csv
  - out_overlayA_conditional/episodes_labeled_holdout.csv
  - stdout summary (echoed in the report)

Usage:
  python experiments/conditional_analysis/label_cascade_episodes.py
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
TRADES_PATH = PROJECT_ROOT / "out/v10_apex" / "trades.csv"


# ── Data loading ─────────────────────────────────────────────────────────────

def load_episodes(path: Path) -> list[dict]:
    """Load episode CSV into list of dicts, coercing types."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row["episode_id"] = int(row["episode_id"])
            row["peak_ts"] = int(row["peak_ts"])
            row["trough_ts"] = int(row["trough_ts"])
            row["end_ts"] = int(row["end_ts"])
            row["peak_nav"] = float(row["peak_nav"])
            row["trough_nav"] = float(row["trough_nav"])
            row["end_nav"] = float(row["end_nav"])
            row["depth_pct"] = float(row["depth_pct"])
            row["duration_days"] = float(row["duration_days"])
            row["recovery_days"] = (
                float(row["recovery_days"]) if row["recovery_days"] else ""
            )
            row["recovered"] = row["recovered"] == "True"
            rows.append(row)
    return rows


def load_trades(path: Path) -> list[dict]:
    """Load trades CSV → list of dicts with typed fields."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row["trade_id"] = int(row["trade_id"])
            row["exit_ts_ms"] = int(row["exit_ts_ms"])
            row["entry_ts_ms"] = int(row["entry_ts_ms"])
            rows.append(row)
    rows.sort(key=lambda r: r["exit_ts_ms"])
    return rows


# ── Core: compute max consecutive emergency_dd run ───────────────────────────

def max_consecutive_emergency_dd(
    trades: list[dict],
    window_start: int,
    window_end: int,
) -> tuple[int, int, list[int]]:
    """Find max consecutive run of emergency_dd exits within [window_start, window_end].

    Returns
    -------
    max_run : int
        Length of the longest consecutive emergency_dd streak.
    n_emergency : int
        Total count of emergency_dd exits in this window.
    trade_ids : list[int]
        Trade IDs in exit-time order within the window.
    """
    # Filter trades whose exit_ts falls inside the episode window
    in_window = [
        t for t in trades
        if window_start <= t["exit_ts_ms"] <= window_end
    ]
    # Already sorted by exit_ts_ms from load_trades()

    if not in_window:
        return 0, 0, []

    trade_ids = [t["trade_id"] for t in in_window]
    reasons = [t["exit_reason"] for t in in_window]
    n_emergency = sum(1 for r in reasons if r == "emergency_dd")

    # Compute max consecutive run
    max_run = 0
    current_run = 0
    for r in reasons:
        if r == "emergency_dd":
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0

    return max_run, n_emergency, trade_ids


# ── Label episodes ───────────────────────────────────────────────────────────

def label_episodes(
    episodes: list[dict],
    trades: list[dict],
) -> list[dict]:
    """Add cascade labeling columns to each episode."""
    for ep in episodes:
        max_run, n_emergency, trade_ids = max_consecutive_emergency_dd(
            trades, ep["peak_ts"], ep["end_ts"],
        )
        n_trades = len(trade_ids)

        ep["n_trades_in_window"] = n_trades
        ep["n_emergency_dd"] = n_emergency
        ep["max_run_emergency_dd"] = max_run
        ep["is_cascade"] = max_run >= 2
        ep["trade_ids_in_window"] = ";".join(str(t) for t in trade_ids)

    return episodes


# ── CSV output ───────────────────────────────────────────────────────────────

LABELED_FIELDS = [
    "episode_id", "peak_ts", "trough_ts", "end_ts",
    "peak_nav", "trough_nav", "end_nav",
    "depth_pct", "duration_days", "recovery_days",
    "peak_date", "trough_date", "end_date", "recovered",
    "n_trades_in_window", "n_emergency_dd", "max_run_emergency_dd",
    "is_cascade", "trade_ids_in_window",
]


def write_labeled_csv(episodes: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LABELED_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for ep in episodes:
            row = dict(ep)
            # recovery_days: keep empty string for unrecovered
            if isinstance(row.get("recovery_days"), float) and row["recovery_days"] == "":
                pass  # already empty
            writer.writerow(row)


# ── Summary ──────────────────────────────────────────────────────────────────

def print_summary(label: str, episodes: list[dict]) -> None:
    n_total = len(episodes)
    cascade_eps = [ep for ep in episodes if ep["is_cascade"]]
    n_cascade = len(cascade_eps)
    frac = n_cascade / n_total if n_total > 0 else 0.0

    print(f"\n  {label}:")
    print(f"    Total episodes:   {n_total}")
    print(f"    Cascade episodes: {n_cascade}  ({frac:.0%})")
    if cascade_eps:
        print(f"    Cascade IDs:      {[ep['episode_id'] for ep in cascade_eps]}")

    print()
    print(f"    {'ID':>3} {'Peak':>12} {'Trough':>12} {'Depth%':>8} "
          f"{'#Trades':>8} {'#EmDD':>6} {'MaxRun':>7} {'Cascade':>8}")
    print(f"    " + "-" * 75)
    for ep in episodes:
        print(f"    {ep['episode_id']:>3} {ep['peak_date']:>12} {ep['trough_date']:>12} "
              f"{ep['depth_pct']:>8.2f} "
              f"{ep['n_trades_in_window']:>8} {ep['n_emergency_dd']:>6} "
              f"{ep['max_run_emergency_dd']:>7} "
              f"{'YES' if ep['is_cascade'] else '':>8}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  CASCADE EPISODE LABELING")
    print("=" * 70)

    # Load trades
    trades = load_trades(TRADES_PATH)
    n_emdd = sum(1 for t in trades if t["exit_reason"] == "emergency_dd")
    print(f"  Trades loaded: {len(trades)}  ({n_emdd} emergency_dd exits)")

    # ── Full period ─────────────────────────────────────────────────────
    full_path = OUTDIR / "episodes_baseline_full.csv"
    episodes_full = load_episodes(full_path)
    label_episodes(episodes_full, trades)

    full_out = OUTDIR / "episodes_labeled_full.csv"
    write_labeled_csv(episodes_full, full_out)
    print_summary("FULL PERIOD", episodes_full)
    print(f"    Saved: {full_out}")

    # ── Holdout period ──────────────────────────────────────────────────
    holdout_path = OUTDIR / "episodes_baseline_holdout.csv"
    episodes_holdout = load_episodes(holdout_path)
    label_episodes(episodes_holdout, trades)

    holdout_out = OUTDIR / "episodes_labeled_holdout.csv"
    write_labeled_csv(episodes_holdout, holdout_out)
    print_summary("HOLDOUT PERIOD", episodes_holdout)
    print(f"    Saved: {holdout_out}")

    # ── Cross-check: all emergency_dd trades accounted for ─────────────
    emdd_trades = [t for t in trades if t["exit_reason"] == "emergency_dd"]
    assigned = set()
    for ep in episodes_full:
        for tid_str in ep["trade_ids_in_window"].split(";"):
            if tid_str:
                assigned.add(int(tid_str))
    emdd_in_eps = sum(1 for t in emdd_trades if t["trade_id"] in assigned)
    emdd_outside = [t["trade_id"] for t in emdd_trades if t["trade_id"] not in assigned]

    print(f"\n  Cross-check:")
    print(f"    emergency_dd trades in episodes:  {emdd_in_eps}/{len(emdd_trades)}")
    if emdd_outside:
        print(f"    emergency_dd trades NOT in any episode: {emdd_outside}")
        print(f"    (these occur during shallow DDs < dd_min_pct)")
    else:
        print(f"    All emergency_dd trades are inside an episode window.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
