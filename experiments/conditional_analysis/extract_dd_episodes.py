#!/usr/bin/env python3
"""Non-overlapping drawdown episode extractor from NAV equity series.

Algorithm (sequential watermark scan):
  1. Walk the NAV series left→right, tracking running peak (high watermark).
  2. When the drawdown from peak exceeds dd_min_pct, open an episode.
  3. Continue until NAV recovers to the peak level (within 0.1%) or series ends.
  4. Record the episode: peak, trough (min NAV within episode), end (recovery or sample end).
  5. Resume scanning from end+1.  Episodes are non-overlapping by construction.

Outputs:
  - out_overlayA_conditional/episodes_baseline_full.csv    (full period 2020-01 → 2026-02)
  - out_overlayA_conditional/episodes_baseline_holdout.csv (holdout 2024-10-01 →)

Usage:
  python experiments/conditional_analysis/extract_dd_episodes.py [--dd_min_pct 0.08] [--equity PATH]
"""

import argparse
import csv
import sys
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ── Defaults ─────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EQUITY = PROJECT_ROOT / "out/v10_apex" / "equity.csv"
OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
HOLDOUT_START_MS = 1727740800000  # 2024-10-01 00:00 UTC

DD_MIN_PCT = 0.08   # 8% minimum depth to record an episode
RECOVERY_TOL = 0.001  # 0.1% tolerance for recovery detection


# ── Helpers ──────────────────────────────────────────────────────────────────

def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def ms_to_days(delta_ms: int) -> float:
    return delta_ms / 86_400_000


# ── Data loading ─────────────────────────────────────────────────────────────

@dataclass
class NavPoint:
    close_time: int
    nav_mid: float


def load_equity(path: str | Path) -> list[NavPoint]:
    """Load equity CSV → list of NavPoint (sorted by close_time)."""
    points: list[NavPoint] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ct = int(row["close_time"])
            nav = float(row["nav_mid"])
            points.append(NavPoint(close_time=ct, nav_mid=nav))
    points.sort(key=lambda p: p.close_time)
    return points


# ── Episode dataclass ────────────────────────────────────────────────────────

@dataclass
class DDEpisode:
    episode_id: int
    peak_ts: int           # ms — timestamp of peak NAV
    trough_ts: int         # ms — timestamp of trough NAV
    end_ts: int            # ms — recovery timestamp or sample end
    peak_nav: float
    trough_nav: float
    end_nav: float
    depth_pct: float       # (peak − trough) / peak, as percentage (e.g. 12.5)
    duration_days: float   # peak → trough
    recovery_days: float   # trough → end (NaN if no recovery)

    # Derived human-readable fields (not in spec but useful)
    peak_date: str = ""
    trough_date: str = ""
    end_date: str = ""
    recovered: bool = True


# ── Core algorithm ───────────────────────────────────────────────────────────

def extract_episodes(
    navs: list[NavPoint],
    dd_min_pct: float = DD_MIN_PCT,
) -> list[DDEpisode]:
    """Extract non-overlapping drawdown episodes via sequential watermark scan.

    Each bar belongs to at most one episode.  Episodes are ordered chronologically.

    Parameters
    ----------
    navs : list[NavPoint]
        Time-sorted NAV series (close_time, nav_mid).
    dd_min_pct : float
        Minimum drawdown depth to qualify as an episode (fraction, e.g. 0.08 = 8%).

    Returns
    -------
    list[DDEpisode]
        Chronologically ordered, non-overlapping episodes.
    """
    if len(navs) < 2:
        return []

    n = len(navs)
    nav_arr = np.array([p.nav_mid for p in navs])
    ts_arr = np.array([p.close_time for p in navs], dtype=np.int64)

    episodes: list[DDEpisode] = []
    episode_id = 0
    i = 0  # scan pointer

    while i < n:
        # Phase 1: advance while making new highs (find the peak)
        peak_idx = i
        peak_nav = nav_arr[i]

        j = i + 1
        while j < n:
            if nav_arr[j] >= peak_nav:
                # New high — update peak
                peak_nav = nav_arr[j]
                peak_idx = j
                j += 1
            else:
                # Drawdown started — check if it's deep enough
                dd = (peak_nav - nav_arr[j]) / peak_nav
                if dd >= dd_min_pct:
                    break  # confirmed episode start
                j += 1
                # Keep checking: if we find a new high before breaching
                # dd_min_pct, update peak and continue.
                if j < n and nav_arr[j] >= peak_nav:
                    peak_nav = nav_arr[j]
                    peak_idx = j
        else:
            # Reached end of series without triggering an episode
            break

        if j >= n:
            break

        # Phase 2: we have a confirmed drawdown ≥ dd_min_pct at index j.
        # Now walk forward to find trough and recovery.
        trough_idx = j
        trough_nav = nav_arr[j]
        recovery_idx = None

        k = j + 1
        while k < n:
            if nav_arr[k] < trough_nav:
                trough_nav = nav_arr[k]
                trough_idx = k
            if nav_arr[k] >= peak_nav * (1 - RECOVERY_TOL):
                recovery_idx = k
                break
            k += 1

        # Build episode
        if recovery_idx is not None:
            end_idx = recovery_idx
            recovered = True
        else:
            end_idx = n - 1
            recovered = False

        episode_id += 1
        depth = (peak_nav - trough_nav) / peak_nav
        duration_ms = ts_arr[trough_idx] - ts_arr[peak_idx]
        recovery_ms = ts_arr[end_idx] - ts_arr[trough_idx]

        ep = DDEpisode(
            episode_id=episode_id,
            peak_ts=int(ts_arr[peak_idx]),
            trough_ts=int(ts_arr[trough_idx]),
            end_ts=int(ts_arr[end_idx]),
            peak_nav=round(float(peak_nav), 2),
            trough_nav=round(float(trough_nav), 2),
            end_nav=round(float(nav_arr[end_idx]), 2),
            depth_pct=round(depth * 100, 2),
            duration_days=round(ms_to_days(duration_ms), 2),
            recovery_days=round(ms_to_days(recovery_ms), 2) if recovered else float("nan"),
            peak_date=ms_to_date(int(ts_arr[peak_idx])),
            trough_date=ms_to_date(int(ts_arr[trough_idx])),
            end_date=ms_to_date(int(ts_arr[end_idx])),
            recovered=recovered,
        )
        episodes.append(ep)

        # Phase 3: resume scan AFTER this episode's end
        i = end_idx + 1

    return episodes


# ── CSV output ───────────────────────────────────────────────────────────────

CSV_FIELDS = [
    "episode_id", "peak_ts", "trough_ts", "end_ts",
    "peak_nav", "trough_nav", "end_nav",
    "depth_pct", "duration_days", "recovery_days",
    "peak_date", "trough_date", "end_date", "recovered",
]


def write_csv(episodes: list[DDEpisode], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for ep in episodes:
            row = {}
            for field in CSV_FIELDS:
                val = getattr(ep, field)
                if isinstance(val, float) and np.isnan(val):
                    row[field] = ""
                else:
                    row[field] = val
            writer.writerow(row)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract non-overlapping DD episodes")
    parser.add_argument("--equity", type=str, default=str(DEFAULT_EQUITY),
                        help="Path to equity.csv")
    parser.add_argument("--dd_min_pct", type=float, default=DD_MIN_PCT,
                        help="Minimum drawdown depth (fraction, e.g. 0.08 = 8%%)")
    parser.add_argument("--outdir", type=str, default=str(OUTDIR),
                        help="Output directory")
    args = parser.parse_args()

    equity_path = Path(args.equity)
    outdir = Path(args.outdir)

    print("=" * 70)
    print("  NON-OVERLAPPING DRAWDOWN EPISODE EXTRACTOR")
    print("=" * 70)
    print(f"  Equity file : {equity_path}")
    print(f"  dd_min_pct  : {args.dd_min_pct:.1%}")
    print(f"  Output dir  : {outdir}")
    print()

    # Load equity
    navs = load_equity(equity_path)
    print(f"  Loaded {len(navs)} equity points")
    print(f"  Period: {ms_to_iso(navs[0].close_time)} → {ms_to_iso(navs[-1].close_time)}")
    print(f"  NAV range: {min(p.nav_mid for p in navs):.2f} → {max(p.nav_mid for p in navs):.2f}")
    print()

    # ── Full period episodes ────────────────────────────────────────────
    episodes_full = extract_episodes(navs, dd_min_pct=args.dd_min_pct)
    print(f"  Full period: {len(episodes_full)} episodes (≥{args.dd_min_pct:.0%} depth)")

    if episodes_full:
        print()
        print(f"  {'ID':>3} {'Peak':>12} {'Trough':>12} {'End':>12} "
              f"{'Depth%':>8} {'Dur(d)':>8} {'Recov(d)':>9} {'Rcvd':>5}")
        print("  " + "-" * 82)
        for ep in episodes_full:
            rec_str = f"{ep.recovery_days:.1f}" if ep.recovered else "—"
            print(f"  {ep.episode_id:>3} {ep.peak_date:>12} {ep.trough_date:>12} "
                  f"{ep.end_date:>12} {ep.depth_pct:>8.2f} {ep.duration_days:>8.1f} "
                  f"{rec_str:>9} {'Y' if ep.recovered else 'N':>5}")

    full_csv = outdir / "episodes_baseline_full.csv"
    write_csv(episodes_full, full_csv)
    print(f"\n  Saved: {full_csv}")

    # ── Holdout period episodes ─────────────────────────────────────────
    navs_holdout = [p for p in navs if p.close_time >= HOLDOUT_START_MS]
    print(f"\n  Holdout period: {len(navs_holdout)} equity points "
          f"(from {ms_to_iso(HOLDOUT_START_MS)})")

    episodes_holdout = extract_episodes(navs_holdout, dd_min_pct=args.dd_min_pct)
    print(f"  Holdout: {len(episodes_holdout)} episodes (≥{args.dd_min_pct:.0%} depth)")

    if episodes_holdout:
        print()
        print(f"  {'ID':>3} {'Peak':>12} {'Trough':>12} {'End':>12} "
              f"{'Depth%':>8} {'Dur(d)':>8} {'Recov(d)':>9} {'Rcvd':>5}")
        print("  " + "-" * 82)
        for ep in episodes_holdout:
            rec_str = f"{ep.recovery_days:.1f}" if ep.recovered else "—"
            print(f"  {ep.episode_id:>3} {ep.peak_date:>12} {ep.trough_date:>12} "
                  f"{ep.end_date:>12} {ep.depth_pct:>8.2f} {ep.duration_days:>8.1f} "
                  f"{rec_str:>9} {'Y' if ep.recovered else 'N':>5}")

    holdout_csv = outdir / "episodes_baseline_holdout.csv"
    write_csv(episodes_holdout, holdout_csv)
    print(f"\n  Saved: {holdout_csv}")

    # ── Non-overlap verification ────────────────────────────────────────
    print(f"\n  Non-overlap verification (full):")
    ok = True
    for a, b in zip(episodes_full[:-1], episodes_full[1:]):
        if a.end_ts >= b.peak_ts:
            print(f"    OVERLAP: ep{a.episode_id} end={ms_to_date(a.end_ts)} "
                  f">= ep{b.episode_id} peak={ms_to_date(b.peak_ts)}")
            ok = False
    if ok:
        print("    PASS — all episodes strictly non-overlapping")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
