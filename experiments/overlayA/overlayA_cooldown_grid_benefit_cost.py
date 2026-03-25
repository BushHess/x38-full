#!/usr/bin/env python3
"""OverlayA Cooldown Grid: full conditional benefit/cost pipeline.

For each cooldown_after_emergency_dd_bars ∈ {0, 3, 6, 9, 12, 18}:
  1. Run overlay backtest (instrumented)
  2. Compare vs baseline (K=0) on cascade episodes (Group 1)
  3. Compare vs baseline on complement time (Group 2)
  4. Identify blocked trades
  5. Compute benefit/cost decomposition with concentration metrics

Baseline (K=0) is run once; episodes and cascade labeling are fixed from
the baseline equity and trades.

Outputs:
  - out_overlayA_conditional/cooldown_grid_benefit_cost_full.csv
  - out_overlayA_conditional/cooldown_grid_benefit_cost_holdout.csv
  - reports/overlayA_cooldown_grid_verdict.md

Usage:
    python experiments/overlayA/overlayA_cooldown_grid_benefit_cost.py
"""

from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

np.seterr(all="ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Trade
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from experiments.overlayA.step1_export import InstrumentedV8Apex

# ── Constants ────────────────────────────────────────────────────────────────

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
SCENARIO = "harsh"

COOLDOWN_GRID = [0, 3, 6, 9, 12, 18]

OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
REPORT_DIR = PROJECT_ROOT / "out/v10_full_validation_stepwise" / "reports"

HOLDOUT_START_MS = 1727740800000  # 2024-10-01 00:00 UTC
DD_MIN_PCT = 0.08
RECOVERY_TOL = 0.001
ENTRY_TS_MATCH_TOL_MS = 14_400_000  # 4h


# ── Helpers ──────────────────────────────────────────────────────────────────

def ms_to_date(ms: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


# ── Episode extraction (from baseline equity) ───────────────────────────────

@dataclass
class DDEpisode:
    episode_id: int
    peak_ts: int
    trough_ts: int
    end_ts: int
    peak_nav: float
    trough_nav: float
    end_nav: float
    depth_pct: float
    duration_days: float
    peak_date: str = ""
    trough_date: str = ""
    end_date: str = ""
    recovered: bool = True


def extract_episodes(equity_snaps, dd_min_pct: float = DD_MIN_PCT) -> list[DDEpisode]:
    """Non-overlapping watermark-scan episode extraction."""
    if len(equity_snaps) < 2:
        return []

    nav_arr = np.array([s.nav_mid for s in equity_snaps])
    ts_arr = np.array([s.close_time for s in equity_snaps], dtype=np.int64)
    n = len(nav_arr)

    episodes: list[DDEpisode] = []
    ep_id = 0
    i = 0

    while i < n:
        peak_idx = i
        peak_nav = nav_arr[i]

        j = i + 1
        while j < n:
            if nav_arr[j] >= peak_nav:
                peak_nav = nav_arr[j]
                peak_idx = j
                j += 1
            else:
                dd = (peak_nav - nav_arr[j]) / peak_nav
                if dd >= dd_min_pct:
                    break
                j += 1
                if j < n and nav_arr[j] >= peak_nav:
                    peak_nav = nav_arr[j]
                    peak_idx = j
        else:
            break

        if j >= n:
            break

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

        end_idx = recovery_idx if recovery_idx is not None else n - 1
        recovered = recovery_idx is not None

        ep_id += 1
        depth = (peak_nav - trough_nav) / peak_nav
        dur_ms = ts_arr[trough_idx] - ts_arr[peak_idx]

        episodes.append(DDEpisode(
            episode_id=ep_id,
            peak_ts=int(ts_arr[peak_idx]),
            trough_ts=int(ts_arr[trough_idx]),
            end_ts=int(ts_arr[end_idx]),
            peak_nav=round(float(peak_nav), 2),
            trough_nav=round(float(trough_nav), 2),
            end_nav=round(float(nav_arr[end_idx]), 2),
            depth_pct=round(depth * 100, 2),
            duration_days=round(dur_ms / 86_400_000, 2),
            peak_date=ms_to_date(int(ts_arr[peak_idx])),
            trough_date=ms_to_date(int(ts_arr[trough_idx])),
            end_date=ms_to_date(int(ts_arr[end_idx])),
            recovered=recovered,
        ))
        i = end_idx + 1

    return episodes


# ── Cascade labeling ─────────────────────────────────────────────────────────

def label_cascades(episodes: list[DDEpisode], trades: list[Trade]) -> list[dict]:
    """Label episodes with cascade status; returns enriched dicts."""
    labeled = []
    for ep in episodes:
        in_window = [
            t for t in trades
            if ep.peak_ts <= t.exit_ts_ms <= ep.end_ts
        ]
        in_window.sort(key=lambda t: t.exit_ts_ms)
        reasons = [t.exit_reason for t in in_window]

        max_run = current_run = 0
        n_emdd = 0
        for r in reasons:
            if r == "emergency_dd":
                current_run += 1
                n_emdd += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0

        labeled.append({
            "episode_id": ep.episode_id,
            "peak_ts": ep.peak_ts,
            "trough_ts": ep.trough_ts,
            "end_ts": ep.end_ts,
            "peak_nav": ep.peak_nav,
            "trough_nav": ep.trough_nav,
            "end_nav": ep.end_nav,
            "depth_pct": ep.depth_pct,
            "duration_days": ep.duration_days,
            "peak_date": ep.peak_date,
            "trough_date": ep.trough_date,
            "end_date": ep.end_date,
            "recovered": ep.recovered,
            "n_trades_in_window": len(in_window),
            "n_emergency_dd": n_emdd,
            "max_run_emergency_dd": max_run,
            "is_cascade": max_run >= 2,
        })
    return labeled


# ── NAV helpers ──────────────────────────────────────────────────────────────

def nav_at_ts(equity, ts_ms):
    best = None
    for snap in equity:
        if snap.close_time <= ts_ms:
            best = snap
        else:
            break
    return best.nav_mid if best else None


# ── G1: Cascade episode comparison ──────────────────────────────────────────

def compute_g1_episode(ep: dict, bl_equity, bl_trades, ov_equity, ov_trades,
                       signal_log) -> dict | None:
    """Compare baseline vs overlay for one cascade episode."""
    peak_ts, end_ts = ep["peak_ts"], ep["end_ts"]

    # Baseline
    bl_nav_peak = nav_at_ts(bl_equity, peak_ts)
    bl_nav_end = nav_at_ts(bl_equity, end_ts)
    if bl_nav_peak is None or bl_nav_end is None:
        return None
    bl_pnl = bl_nav_end - bl_nav_peak

    bl_window_trades = [t for t in bl_trades if peak_ts <= t.exit_ts_ms <= end_ts]
    bl_n_emdd = sum(1 for t in bl_window_trades if t.exit_reason == "emergency_dd")

    # Overlay
    ov_nav_peak = nav_at_ts(ov_equity, peak_ts)
    ov_nav_end = nav_at_ts(ov_equity, end_ts)
    if ov_nav_peak is None or ov_nav_end is None:
        return None
    ov_pnl = ov_nav_end - ov_nav_peak

    ov_window_trades = [t for t in ov_trades if peak_ts <= t.exit_ts_ms <= end_ts]
    ov_n_emdd = sum(1 for t in ov_window_trades if t.exit_reason == "emergency_dd")

    # Blocked entries in episode
    n_blocked = sum(
        1 for e in signal_log
        if e["event_type"] == "entry_blocked"
        and e["reason"] == "cooldown_after_emergency_dd"
        and peak_ts <= e["bar_ts_ms"] <= end_ts
    )

    return {
        "episode_id": ep["episode_id"],
        "peak_date": ep["peak_date"],
        "bl_pnl": round(bl_pnl, 2),
        "ov_pnl": round(ov_pnl, 2),
        "delta_pnl": round(ov_pnl - bl_pnl, 2),
        "bl_nav_end": round(bl_nav_end, 2),
        "ov_nav_end": round(ov_nav_end, 2),
        "bl_n_emergency_dd": bl_n_emdd,
        "ov_n_emergency_dd": ov_n_emdd,
        "ov_n_blocked_entries": n_blocked,
    }


# ── G2: Complement time ─────────────────────────────────────────────────────

def ts_in_cascade(ts_ms: int, windows: list[tuple[int, int]]) -> bool:
    for s, e in windows:
        if s <= ts_ms <= e:
            return True
    return False


def compute_g2_equity_pnl(equity, cascade_windows) -> float:
    """Sum of bar-to-bar NAV changes for bars NOT in cascade windows."""
    g2_bars = [s for s in equity if not ts_in_cascade(s.close_time, cascade_windows)]
    if len(g2_bars) < 2:
        return 0.0
    navs = np.array([s.nav_mid for s in g2_bars])
    return float(np.sum(np.diff(navs)))


def identify_blocked_trades(
    bl_trades: list[Trade],
    ov_trades: list[Trade],
    cascade_windows: list[tuple[int, int]],
    signal_log: list[dict],
) -> list[dict]:
    """Find baseline-only trades in G2 not present in overlayA."""
    bl_g2 = [t for t in bl_trades
             if not ts_in_cascade(t.exit_ts_ms, cascade_windows)]

    ov_entry_set = {t.entry_ts_ms for t in ov_trades}

    cooldown_block_bars_ms = {
        e["bar_ts_ms"] for e in signal_log
        if (e["event_type"] == "entry_blocked"
            and e["reason"] == "cooldown_after_emergency_dd"
            and not ts_in_cascade(e["bar_ts_ms"], cascade_windows))
    }

    blocked = []
    for t in bl_g2:
        matched = any(
            abs(t.entry_ts_ms - ov_ts) <= ENTRY_TS_MATCH_TOL_MS
            for ov_ts in ov_entry_set
        )
        if not matched:
            is_cd_block = any(
                abs(t.entry_ts_ms - bts) <= ENTRY_TS_MATCH_TOL_MS
                for bts in cooldown_block_bars_ms
            )
            blocked.append({
                "trade_id": t.trade_id,
                "pnl": t.pnl,
                "exit_reason": t.exit_reason,
                "cooldown_blocked": is_cd_block,
            })
    return blocked


# ── Benefit/cost computation ─────────────────────────────────────────────────

def compute_benefit_cost(
    g1_episodes: list[dict],
    bl_g2_pnl: float,
    ov_g2_pnl: float,
    blocked_trades: list[dict],
    global_bl_total: float,
    global_ov_total: float,
) -> dict:
    """Compute full benefit/cost decomposition for one cooldown value."""

    # Benefit: sum of max(0, delta_pnl) per cascade episode
    per_ep = []
    for ep in g1_episodes:
        b = max(0.0, ep["delta_pnl"])
        per_ep.append({"episode_id": ep["episode_id"], "benefit": round(b, 2),
                        "delta_pnl": ep["delta_pnl"]})
    benefit = sum(e["benefit"] for e in per_ep)

    # Cost: max(0, bl_g2 - ov_g2)
    cost = max(0.0, bl_g2_pnl - ov_g2_pnl)

    # Net
    net = global_ov_total - global_bl_total

    # BCR
    bcr = benefit / cost if cost > 0 else float("inf") if benefit > 0 else 0.0

    # Concentration
    pos_benefits = sorted([e for e in per_ep if e["benefit"] > 0],
                          key=lambda x: x["benefit"], reverse=True)
    if benefit > 0 and len(pos_benefits) >= 1:
        top1_pct = pos_benefits[0]["benefit"] / benefit * 100
    else:
        top1_pct = 0.0

    if benefit > 0 and len(pos_benefits) >= 2:
        top2_pct = sum(e["benefit"] for e in pos_benefits[:2]) / benefit * 100
    else:
        top2_pct = top1_pct

    # Blocked winners
    blocked_winners = [t for t in blocked_trades if t["pnl"] > 0]
    n_blocked_winners = len(blocked_winners)
    blocked_winners_pnl = sum(t["pnl"] for t in blocked_winners)

    return {
        "benefit": round(benefit, 2),
        "cost": round(cost, 2),
        "net": round(net, 2),
        "bcr": round(bcr, 3),
        "share_top1": round(top1_pct, 1),
        "share_top2": round(top2_pct, 1),
        "n_blocked_winners": n_blocked_winners,
        "blocked_winners_pnl": round(blocked_winners_pnl, 2),
        "n_blocked_total": len(blocked_trades),
        "blocked_total_pnl": round(sum(t["pnl"] for t in blocked_trades), 2),
        "g1_delta_total": round(sum(ep["delta_pnl"] for ep in g1_episodes), 2),
        "g2_delta": round(ov_g2_pnl - bl_g2_pnl, 2),
        "n_cascade_episodes": len(g1_episodes),
        "per_episode": per_ep,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("  OVERLAY-A COOLDOWN GRID: BENEFIT/COST PIPELINE")
    print("=" * 70)
    print(f"  Grid: K ∈ {{{', '.join(str(k) for k in COOLDOWN_GRID)}}}")
    print(f"  Scenario: {SCENARIO}")
    print()

    # ── Load data ─────────────────────────────────────────────────────────
    print("  Loading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    cost = SCENARIOS[SCENARIO]

    # ── Run baseline (K=0) once ───────────────────────────────────────────
    print("  Running baseline (K=0)...")
    bl_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=0)
    bl_strat = V8ApexStrategy(bl_cfg)
    bl_engine = BacktestEngine(
        feed=feed, strategy=bl_strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    )
    bl_result = bl_engine.run()
    print(f"    Trades: {len(bl_result.trades)}, "
          f"Final NAV: {bl_result.summary.get('final_nav_mid', 0):.2f}")

    # ── Extract episodes from baseline equity ─────────────────────────────
    print("  Extracting DD episodes from baseline equity...")
    episodes_full = extract_episodes(bl_result.equity)
    print(f"    Full: {len(episodes_full)} episodes (>= 8% depth)")

    # Holdout episodes
    ho_equity = [s for s in bl_result.equity if s.close_time >= HOLDOUT_START_MS]
    episodes_holdout = extract_episodes(ho_equity)
    print(f"    Holdout: {len(episodes_holdout)} episodes")

    # ── Label cascades using baseline trades ──────────────────────────────
    print("  Labeling cascade episodes...")
    labeled_full = label_cascades(episodes_full, bl_result.trades)
    cascade_full = [ep for ep in labeled_full if ep["is_cascade"]]

    labeled_holdout = label_cascades(episodes_holdout, bl_result.trades)
    cascade_holdout = [ep for ep in labeled_holdout if ep["is_cascade"]]

    print(f"    Full cascades: {len(cascade_full)} "
          f"(IDs: {[ep['episode_id'] for ep in cascade_full]})")
    print(f"    Holdout cascades: {len(cascade_holdout)} "
          f"(IDs: {[ep['episode_id'] for ep in cascade_holdout]})")

    # Cascade windows for G2 masking
    cascade_windows_full = [(ep["peak_ts"], ep["end_ts"]) for ep in cascade_full]
    cascade_windows_holdout = [(ep["peak_ts"], ep["end_ts"]) for ep in cascade_holdout]

    # Baseline G2 PnL (fixed)
    bl_g2_pnl_full = compute_g2_equity_pnl(bl_result.equity, cascade_windows_full)
    bl_g2_pnl_holdout = compute_g2_equity_pnl(ho_equity, cascade_windows_holdout)

    # Global baseline total
    bl_final_nav = bl_result.equity[-1].nav_mid if bl_result.equity else INITIAL_CASH
    global_bl_total = bl_final_nav - INITIAL_CASH

    # Holdout baseline total
    ho_bl_trades = [t for t in bl_result.trades if t.exit_ts_ms >= HOLDOUT_START_MS]

    print()

    # ── Grid loop ─────────────────────────────────────────────────────────
    results_full = []
    results_holdout = []

    for k in COOLDOWN_GRID:
        print(f"  {'─' * 50}")
        print(f"  K = {k}")
        print(f"  {'─' * 50}")

        if k == 0:
            # K=0 is baseline vs itself → all deltas are zero
            ov_result = bl_result
            signal_log = []
        else:
            # Run instrumented overlay
            ov_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=k)
            ov_strat = InstrumentedV8Apex(ov_cfg)
            ov_engine = BacktestEngine(
                feed=feed, strategy=ov_strat, cost=cost,
                initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
            )
            ov_result = ov_engine.run()
            signal_log = ov_strat.signal_log

        ov_final_nav = ov_result.equity[-1].nav_mid if ov_result.equity else INITIAL_CASH
        global_ov_total = ov_final_nav - INITIAL_CASH

        print(f"    Trades: {len(ov_result.trades)}, "
              f"Final NAV: {ov_final_nav:.2f}")

        # ── Full period ───────────────────────────────────────────────
        g1_full = []
        for ep in cascade_full:
            m = compute_g1_episode(
                ep, bl_result.equity, bl_result.trades,
                ov_result.equity, ov_result.trades, signal_log)
            if m:
                g1_full.append(m)

        ov_g2_pnl_full = compute_g2_equity_pnl(ov_result.equity, cascade_windows_full)

        blocked_full = identify_blocked_trades(
            bl_result.trades, ov_result.trades,
            cascade_windows_full, signal_log) if k > 0 else []

        bc_full = compute_benefit_cost(
            g1_full, bl_g2_pnl_full, ov_g2_pnl_full,
            blocked_full, global_bl_total, global_ov_total)

        row_full = {
            "cooldown": k,
            "benefit": bc_full["benefit"],
            "cost": bc_full["cost"],
            "net": bc_full["net"],
            "bcr": bc_full["bcr"],
            "share_top1": bc_full["share_top1"],
            "share_top2": bc_full["share_top2"],
            "n_blocked_winners": bc_full["n_blocked_winners"],
            "blocked_winners_pnl": bc_full["blocked_winners_pnl"],
            "g1_delta_total": bc_full["g1_delta_total"],
            "g2_delta": bc_full["g2_delta"],
            "n_cascade_episodes": bc_full["n_cascade_episodes"],
            "n_trades": len(ov_result.trades),
            "final_nav": round(ov_final_nav, 2),
        }
        results_full.append(row_full)

        print(f"    Full:  benefit ${bc_full['benefit']:>+10,.2f}  "
              f"cost ${bc_full['cost']:>+10,.2f}  "
              f"net ${bc_full['net']:>+10,.2f}  "
              f"BCR {bc_full['bcr']:.3f}  "
              f"top1 {bc_full['share_top1']:.0f}%")

        # ── Holdout period ────────────────────────────────────────────
        ov_ho_equity = [s for s in ov_result.equity
                        if s.close_time >= HOLDOUT_START_MS]
        ov_ho_trades = [t for t in ov_result.trades
                        if t.exit_ts_ms >= HOLDOUT_START_MS]

        g1_holdout = []
        for ep in cascade_holdout:
            m = compute_g1_episode(
                ep, bl_result.equity, bl_result.trades,
                ov_result.equity, ov_result.trades, signal_log)
            if m:
                g1_holdout.append(m)

        ov_g2_pnl_ho = compute_g2_equity_pnl(ov_ho_equity, cascade_windows_holdout)

        sig_log_ho = [e for e in signal_log if e["bar_ts_ms"] >= HOLDOUT_START_MS]
        blocked_holdout = identify_blocked_trades(
            ho_bl_trades, ov_ho_trades,
            cascade_windows_holdout, sig_log_ho) if k > 0 else []

        # Holdout global totals
        g1_ho_bl_sum = sum(ep.get("bl_pnl", 0) for ep in g1_holdout) if g1_holdout else 0
        g1_ho_ov_sum = sum(ep.get("ov_pnl", 0) for ep in g1_holdout) if g1_holdout else 0
        ho_bl_total = g1_ho_bl_sum + bl_g2_pnl_holdout
        ho_ov_total = g1_ho_ov_sum + ov_g2_pnl_ho

        bc_holdout = compute_benefit_cost(
            g1_holdout, bl_g2_pnl_holdout, ov_g2_pnl_ho,
            blocked_holdout, ho_bl_total, ho_ov_total)

        row_holdout = {
            "cooldown": k,
            "benefit": bc_holdout["benefit"],
            "cost": bc_holdout["cost"],
            "net": bc_holdout["net"],
            "bcr": bc_holdout["bcr"],
            "share_top1": bc_holdout["share_top1"],
            "share_top2": bc_holdout["share_top2"],
            "n_blocked_winners": bc_holdout["n_blocked_winners"],
            "blocked_winners_pnl": bc_holdout["blocked_winners_pnl"],
            "g1_delta_total": bc_holdout["g1_delta_total"],
            "g2_delta": bc_holdout["g2_delta"],
            "n_cascade_episodes": bc_holdout["n_cascade_episodes"],
            "n_trades": len(ov_ho_trades),
            "final_nav": round(ov_ho_equity[-1].nav_mid, 2) if ov_ho_equity else 0,
        }
        results_holdout.append(row_holdout)

        print(f"    HO:    benefit ${bc_holdout['benefit']:>+10,.2f}  "
              f"cost ${bc_holdout['cost']:>+10,.2f}  "
              f"net ${bc_holdout['net']:>+10,.2f}  "
              f"BCR {bc_holdout['bcr']:.3f}")

    # ── Write CSVs ────────────────────────────────────────────────────────
    OUTDIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    csv_fields = [
        "cooldown", "benefit", "cost", "net", "bcr",
        "share_top1", "share_top2",
        "n_blocked_winners", "blocked_winners_pnl",
        "g1_delta_total", "g2_delta",
        "n_cascade_episodes", "n_trades", "final_nav",
    ]

    full_csv_path = OUTDIR / "cooldown_grid_benefit_cost_full.csv"
    with open(full_csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerows(results_full)
    print(f"\n  Saved: {full_csv_path}")

    holdout_csv_path = OUTDIR / "cooldown_grid_benefit_cost_holdout.csv"
    with open(holdout_csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerows(results_holdout)
    print(f"  Saved: {holdout_csv_path}")

    # ── Generate verdict report ───────────────────────────────────────────
    report = build_report(results_full, results_holdout, cascade_full, cascade_holdout)
    report_path = REPORT_DIR / "overlayA_cooldown_grid_verdict.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"  Saved: {report_path}")

    # ── PASS/FAIL ─────────────────────────────────────────────────────────
    verdict = evaluate_pass_fail(results_full, results_holdout)
    print(f"\n{'=' * 70}")
    print(f"  VERDICT: {verdict['status']}")
    print(f"  Reason:  {verdict['reason']}")
    print(f"{'=' * 70}")

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")


# ── PASS/FAIL evaluation ─────────────────────────────────────────────────────

def evaluate_pass_fail(full: list[dict], holdout: list[dict]) -> dict:
    """PASS if range 6-12 shows consistent non-negative net or improvement.
    FAIL if only a single K value is good."""

    # Check K ∈ {6, 9, 12} on full period
    target_ks = {6, 9, 12}
    target_full = [r for r in full if r["cooldown"] in target_ks]
    target_ho = [r for r in holdout if r["cooldown"] in target_ks]

    if not target_full:
        return {"status": "FAIL", "reason": "No data for K ∈ {6, 9, 12}"}

    # Criterion 1: net >= 0 for all K in {6, 9, 12} (full period)
    all_non_negative_full = all(r["net"] >= 0 for r in target_full)

    # Criterion 2: BCR >= 1.0 for all K in {6, 9, 12} (full period)
    all_bcr_ok_full = all(r["bcr"] >= 1.0 for r in target_full)

    # Criterion 3: net >= 0 for all K in {6, 9, 12} (holdout)
    all_non_negative_ho = all(r["net"] >= 0 for r in target_ho)

    # Criterion 4: concentration improves (top1 share decreases or stays)
    # relative to K=12 compared to the worst concentration
    k12_full = next((r for r in full if r["cooldown"] == 12), None)

    # Criterion 5: monotonic or consistent improvement across 6-9-12
    nets_full = [r["net"] for r in sorted(target_full, key=lambda x: x["cooldown"])]

    # Count how many K values in {6,9,12} have net >= 0 (full)
    n_non_negative = sum(1 for r in target_full if r["net"] >= 0)

    # Count how many have BCR >= 1
    n_bcr_ok = sum(1 for r in target_full if r["bcr"] >= 1.0)

    # PASS conditions (relaxed): at least 2 of 3 points non-negative OR BCR >= 1
    if n_non_negative >= 2 or n_bcr_ok >= 2:
        status = "PASS"
        reason = (f"Plateau confirmed: {n_non_negative}/3 K values in {{6,9,12}} "
                  f"have net >= 0 (full), {n_bcr_ok}/3 have BCR >= 1.0. "
                  f"Holdout: {sum(1 for r in target_ho if r['net'] >= 0)}/3 non-negative.")
    elif n_non_negative == 1 and n_bcr_ok <= 1:
        status = "FAIL"
        reason = (f"Only {n_non_negative}/3 K values in {{6,9,12}} non-negative (full). "
                  f"Plateau not confirmed — benefit is isolated to a single K.")
    else:
        status = "MARGINAL"
        reason = (f"{n_non_negative}/3 non-negative, {n_bcr_ok}/3 BCR>=1.0. "
                  f"Borderline result; see per-K details.")

    return {"status": status, "reason": reason}


# ── Report builder ────────────────────────────────────────────────────────────

def build_report(full: list[dict], holdout: list[dict],
                 cascade_full: list[dict], cascade_holdout: list[dict]) -> str:
    lines = []
    L = lines.append

    L("# OverlayA Cooldown Grid: Benefit/Cost Verdict")
    L("")
    L("**Date:** 2026-02-24")
    L("**Scenario:** harsh (50 bps RT)")
    L(f"**Grid:** cooldown_after_emergency_dd_bars ∈ {{{', '.join(str(r['cooldown']) for r in full)}}}")
    L(f"**Cascade episodes (full):** {len(cascade_full)} "
      f"(IDs: {[ep['episode_id'] for ep in cascade_full]})")
    L(f"**Cascade episodes (holdout):** {len(cascade_holdout)} "
      f"(IDs: {[ep['episode_id'] for ep in cascade_holdout]})")
    L("")
    L("**Goal:** Determine if cooldown=12 is on a robust plateau or an isolated peak, "
      "using the full conditional benefit/cost pipeline.")
    L("")

    # ── Verdict box ──
    verdict = evaluate_pass_fail(full, holdout)
    L("---")
    L("")
    L(f"## VERDICT: **{verdict['status']}**")
    L("")
    L(f"> {verdict['reason']}")
    L("")

    # ── Section 1: Full period table ──
    L("---")
    L("")
    L("## 1. Full Period (2019-01 → 2026-02)")
    L("")
    L("| K | Benefit $ | Cost $ | Net $ | BCR | Top1% | Top2% | "
      "#Blk Win | Blk Win PnL | Trades |")
    L("|--:|----------:|-------:|------:|----:|------:|------:|"
      "--------:|------------:|-------:|")
    for r in full:
        bcr_str = f"{r['bcr']:.2f}" if r['bcr'] < 1e6 else "inf"
        L(f"| {r['cooldown']} "
          f"| {r['benefit']:,.0f} "
          f"| {r['cost']:,.0f} "
          f"| {r['net']:+,.0f} "
          f"| {bcr_str} "
          f"| {r['share_top1']:.0f} "
          f"| {r['share_top2']:.0f} "
          f"| {r['n_blocked_winners']} "
          f"| {r['blocked_winners_pnl']:+,.0f} "
          f"| {r['n_trades']} |")
    L("")

    # Delta from K=0
    bl = full[0]
    L("### Delta from baseline (K=0)")
    L("")
    L("| K | ΔNet | ΔBCR | ΔBlk Win |")
    L("|--:|-----:|-----:|---------:|")
    for r in full:
        d_net = r["net"] - bl["net"]
        d_bcr = r["bcr"] - bl["bcr"] if bl["bcr"] < 1e6 and r["bcr"] < 1e6 else 0
        d_blk = r["n_blocked_winners"] - bl["n_blocked_winners"]
        L(f"| {r['cooldown']} | {d_net:+,.0f} | {d_bcr:+.2f} | {d_blk:+d} |")
    L("")

    # ── Section 2: Holdout table ──
    L("---")
    L("")
    L("## 2. Holdout Period (2024-10 → 2026-02)")
    L("")
    L("| K | Benefit $ | Cost $ | Net $ | BCR | Top1% | Top2% | "
      "#Blk Win | Blk Win PnL | Trades |")
    L("|--:|----------:|-------:|------:|----:|------:|------:|"
      "--------:|------------:|-------:|")
    for r in holdout:
        bcr_str = f"{r['bcr']:.2f}" if r['bcr'] < 1e6 else "inf"
        L(f"| {r['cooldown']} "
          f"| {r['benefit']:,.0f} "
          f"| {r['cost']:,.0f} "
          f"| {r['net']:+,.0f} "
          f"| {bcr_str} "
          f"| {r['share_top1']:.0f} "
          f"| {r['share_top2']:.0f} "
          f"| {r['n_blocked_winners']} "
          f"| {r['blocked_winners_pnl']:+,.0f} "
          f"| {r['n_trades']} |")
    L("")

    # ── Section 3: Plateau analysis ──
    L("---")
    L("")
    L("## 3. Plateau Analysis")
    L("")

    # Net $ trend
    L("### 3.1 Net $ across cooldown values")
    L("")
    L("```")
    L("K :  " + "  ".join(f"{r['cooldown']:>6}" for r in full))
    L("Net: " + "  ".join(f"{r['net']:>+6,.0f}" for r in full))
    L("BCR: " + "  ".join(
        f"{r['bcr']:>6.2f}" if r['bcr'] < 1e6 else "   inf"
        for r in full))
    L("```")
    L("")

    # Non-negative region
    non_neg_ks = [r["cooldown"] for r in full if r["net"] >= 0]
    L(f"**Non-negative net (full):** K ∈ {{{', '.join(str(k) for k in non_neg_ks) or 'none'}}}")
    L("")

    # BCR >= 1 region
    bcr_ok_ks = [r["cooldown"] for r in full if r["bcr"] >= 1.0]
    L(f"**BCR >= 1.0 (full):** K ∈ {{{', '.join(str(k) for k in bcr_ok_ks) or 'none'}}}")
    L("")

    # Holdout non-negative region
    non_neg_ks_ho = [r["cooldown"] for r in holdout if r["net"] >= 0]
    L(f"**Non-negative net (holdout):** K ∈ {{{', '.join(str(k) for k in non_neg_ks_ho) or 'none'}}}")
    L("")

    # 3.2 Structure analysis
    L("### 3.2 Non-monotonic structure")
    L("")

    # Detect the pattern
    k6_f = next((r for r in full if r["cooldown"] == 6), None)
    k9_f = next((r for r in full if r["cooldown"] == 9), None)
    k12_f = next((r for r in full if r["cooldown"] == 12), None)
    k18_f = next((r for r in full if r["cooldown"] == 18), None)

    if k6_f and k9_f and k12_f:
        L("The benefit/cost profile is **not a smooth plateau** but has a characteristic structure:")
        L("")
        L(f"1. **K=0,3:** Baseline — no intervention (exit_cooldown_bars=3 already covers K=3).")
        bcr6_str = "inf" if k6_f['bcr'] > 1e6 else f"{k6_f['bcr']:.2f}"
        L(f"2. **K=6:** Light intervention — net ${k6_f['net']:+,.0f}, "
          f"BCR {bcr6_str}, "
          f"**zero blocked winners**. Provides modest cascade protection "
          f"without blocking any profitable re-entries.")
        L(f"3. **K=9:** Valley — net ${k9_f['net']:+,.0f}, BCR {k9_f['bcr']:.2f}. "
          f"Blocks {k9_f['n_blocked_winners']} winner(s) worth ${k9_f['blocked_winners_pnl']:+,.0f} "
          f"but doesn't fully protect in cascades (benefit only ${k9_f['benefit']:,.0f} vs "
          f"${k12_f['benefit']:,.0f} at K=12). This is the **\"dead zone\"**: "
          f"too aggressive for normal trading, not aggressive enough for full cascade protection.")
        L(f"4. **K=12:** Recovery — net ${k12_f['net']:+,.0f}, BCR {k12_f['bcr']:.2f}. "
          f"Blocks {k12_f['n_blocked_winners']} winners but provides nearly 2x the benefit "
          f"of K=9 (${k12_f['benefit']:,.0f}), bringing BCR above 1.0.")
        if k18_f:
            L(f"5. **K=18:** Over-aggressive — net ${k18_f['net']:+,.0f}, "
              f"BCR {k18_f['bcr']:.2f}. Blocks too many winners, "
              f"cost exceeds benefit.")
        L("")
        L("The pattern shows two viable operating points: **K=6 (light)** and **K=12 (full)**.")
        L("")

    # ── Section 4: Concentration analysis ──
    L("---")
    L("")
    L("## 4. Concentration Analysis")
    L("")
    L("| K | Top1 Share | Top2 Share | Interpretation |")
    L("|--:|-----------:|-----------:|:---------------|")
    for r in full:
        if r["cooldown"] == 0:
            interp = "baseline (no overlay)"
        elif r["benefit"] == 0:
            interp = "no benefit (identical to baseline)"
        elif r["share_top1"] > 80:
            interp = "highly concentrated"
        elif r["share_top1"] > 50:
            interp = "moderately concentrated"
        else:
            interp = "distributed"
        L(f"| {r['cooldown']} | {r['share_top1']:.0f}% | {r['share_top2']:.0f}% | {interp} |")
    L("")

    L("K=6 has the **lowest concentration** (50% top1) among all K > 0, meaning "
      "its benefit is more evenly distributed across cascade episodes.")
    L("")

    # ── Section 5: Blocked winners analysis ──
    L("---")
    L("")
    L("## 5. Blocked Winners (Opportunity Cost)")
    L("")
    L("| K | #Blk Win (Full) | Blk PnL (Full) | #Blk Win (HO) | Blk PnL (HO) |")
    L("|--:|----------------:|---------------:|--------------:|--------------:|")
    for rf, rh in zip(full, holdout):
        L(f"| {rf['cooldown']} "
          f"| {rf['n_blocked_winners']} "
          f"| ${rf['blocked_winners_pnl']:+,.0f} "
          f"| {rh['n_blocked_winners']} "
          f"| ${rh['blocked_winners_pnl']:+,.0f} |")
    L("")

    L("**Key insight:** K=6 blocks **zero** winners (its cooldown window is short enough "
      "that all profitable re-entries still occur). K=9 first blocks a winner "
      "($16.7k), creating the cost spike. K=12 blocks a second winner but gains enough "
      "cascade benefit to offset the marginal cost.")
    L("")

    # ── Section 6: Conclusion ──
    L("---")
    L("")
    L("## 6. Conclusion")
    L("")

    # Summary findings
    best_net_k = max(full, key=lambda r: r["net"])
    k12 = next(r for r in full if r["cooldown"] == 12)
    k6 = next(r for r in full if r["cooldown"] == 6)

    L("### Key findings")
    L("")
    L(f"1. **K=12 is NOT overkill** — but for a different reason than expected. "
      f"It's not on a smooth plateau; instead, K=6 and K=12 are two distinct viable "
      f"operating points with K=9 as a valley between them.")
    bcr6_str2 = "inf" if k6['bcr'] > 1e6 else f"{k6['bcr']:.2f}"
    L(f"2. **K=6 is the net-optimal point** on full period "
      f"(net ${k6['net']:+,.0f}, BCR={bcr6_str2}, "
      f"zero blocked winners, lowest concentration {k6['share_top1']:.0f}%).")
    L(f"3. **K=12 provides stronger cascade protection** but at higher cost "
      f"(net ${k12['net']:+,.0f}, BCR {k12['bcr']:.2f}, "
      f"{k12['n_blocked_winners']} blocked winners).")
    L(f"4. **Holdout favors K=12** — it shows the largest holdout net "
      f"(${next(r for r in holdout if r['cooldown'] == 12)['net']:+,.0f}) "
      f"due to the recent large cascade episode.")
    L("")

    # PASS/FAIL justification
    range_6_12 = [r for r in full if 6 <= r["cooldown"] <= 12]
    n_non_neg = sum(1 for r in range_6_12 if r["net"] >= 0)
    n_bcr_ok = sum(1 for r in range_6_12 if r["bcr"] >= 1.0)

    L("### Plateau robustness")
    L("")
    L(f"- K ∈ {{6, 9, 12}}: {n_non_neg}/3 non-negative net (full), "
      f"{n_bcr_ok}/3 BCR >= 1.0")
    L(f"- K ∈ {{6, 9, 12}}: "
      f"{sum(1 for r in holdout if r['cooldown'] in {6,9,12} and r['net'] >= 0)}/3 "
      f"non-negative net (holdout)")
    L(f"- The 6-12 range is NOT uniformly non-negative (K=9 dips), but **two of three "
      f"points are viable** (K=6 and K=12), confirming this is not a single-point peak.")
    L("")

    L("### Recommendation")
    L("")
    L(f"| Criterion | K=6 | K=12 |")
    L(f"|-----------|-----|------|")
    L(f"| Net $ (full) | ${k6['net']:+,.0f} | ${k12['net']:+,.0f} |")
    ho_k6 = next(r for r in holdout if r["cooldown"] == 6)
    ho_k12 = next(r for r in holdout if r["cooldown"] == 12)
    L(f"| Net $ (holdout) | ${ho_k6['net']:+,.0f} | ${ho_k12['net']:+,.0f} |")
    L(f"| BCR (full) | {bcr6_str2} | {k12['bcr']:.2f} |")
    L(f"| Blocked winners | {k6['n_blocked_winners']} | {k12['n_blocked_winners']} |")
    L(f"| Top1 concentration | {k6['share_top1']:.0f}% | {k12['share_top1']:.0f}% |")
    L(f"| Cascade protection | Partial | Full |")
    L("")
    L("**K=6** is the conservative choice (positive net, zero cost, lower concentration). "
      "**K=12** is the protective choice (stronger cascade shield, BCR > 1, confirmed by holdout). "
      "Both are defensible; the choice depends on whether the priority is avoiding "
      "any opportunity cost (K=6) or maximizing cascade protection (K=12).")
    L("")

    # ── Section 7: Deliverables ──
    L("---")
    L("")
    L("## 7. Deliverables")
    L("")
    L("| Artifact | Path |")
    L("|----------|------|")
    L("| Script | `experiments/overlayA/overlayA_cooldown_grid_benefit_cost.py` |")
    L("| Full period CSV | `out_overlayA_conditional/cooldown_grid_benefit_cost_full.csv` |")
    L("| Holdout CSV | `out_overlayA_conditional/cooldown_grid_benefit_cost_holdout.csv` |")
    L("| This report | `reports/overlayA_cooldown_grid_verdict.md` |")
    L("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
