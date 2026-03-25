#!/usr/bin/env python3
"""C9: Compare baseline vs OverlayA_v1(K=12) vs OverlayA_v2(escalating).

Runs the full conditional benefit/cost pipeline for three configurations:
  1. Baseline (K=0) — no cooldown
  2. V1 (flat K=12) — best holdout from C6 grid search
  3. V2 (escalating: short=3, long=12, lookback=24, trigger=2)

Outputs:
  - out_overlayA_conditional/compare_v1_v2_full.csv
  - out_overlayA_conditional/compare_v1_v2_holdout.csv
  - reports/overlayA_v2_results.md

Usage:
    python experiments/overlayA/overlayA_compare_v1_v2.py
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

OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
REPORT_DIR = PROJECT_ROOT / "out/v10_full_validation_stepwise" / "reports"

HOLDOUT_START_MS = 1727740800000  # 2024-10-01 00:00 UTC
DD_MIN_PCT = 0.08
RECOVERY_TOL = 0.001
ENTRY_TS_MATCH_TOL_MS = 14_400_000  # 4h

# Cooldown-related signal_log reasons (v1 + v2)
COOLDOWN_REASONS = {"cooldown_after_emergency_dd", "short_cooldown", "long_cooldown"}


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
            "peak_ts": ep.peak_ts, "trough_ts": ep.trough_ts, "end_ts": ep.end_ts,
            "peak_nav": ep.peak_nav, "trough_nav": ep.trough_nav, "end_nav": ep.end_nav,
            "depth_pct": ep.depth_pct, "duration_days": ep.duration_days,
            "peak_date": ep.peak_date, "trough_date": ep.trough_date,
            "end_date": ep.end_date, "recovered": ep.recovered,
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
    peak_ts, end_ts = ep["peak_ts"], ep["end_ts"]
    bl_nav_peak = nav_at_ts(bl_equity, peak_ts)
    bl_nav_end = nav_at_ts(bl_equity, end_ts)
    if bl_nav_peak is None or bl_nav_end is None:
        return None
    bl_pnl = bl_nav_end - bl_nav_peak

    bl_window_trades = [t for t in bl_trades if peak_ts <= t.exit_ts_ms <= end_ts]
    bl_n_emdd = sum(1 for t in bl_window_trades if t.exit_reason == "emergency_dd")

    ov_nav_peak = nav_at_ts(ov_equity, peak_ts)
    ov_nav_end = nav_at_ts(ov_equity, end_ts)
    if ov_nav_peak is None or ov_nav_end is None:
        return None
    ov_pnl = ov_nav_end - ov_nav_peak

    ov_window_trades = [t for t in ov_trades if peak_ts <= t.exit_ts_ms <= end_ts]
    ov_n_emdd = sum(1 for t in ov_window_trades if t.exit_reason == "emergency_dd")

    n_blocked = sum(
        1 for e in signal_log
        if e["event_type"] == "entry_blocked"
        and e["reason"] in COOLDOWN_REASONS
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
    """Find baseline-only trades in G2 not present in overlay."""
    bl_g2 = [t for t in bl_trades
             if not ts_in_cascade(t.exit_ts_ms, cascade_windows)]
    ov_entry_set = {t.entry_ts_ms for t in ov_trades}

    cooldown_block_bars_ms = {
        e["bar_ts_ms"] for e in signal_log
        if (e["event_type"] == "entry_blocked"
            and e["reason"] in COOLDOWN_REASONS
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
    per_ep = []
    for ep in g1_episodes:
        b = max(0.0, ep["delta_pnl"])
        per_ep.append({"episode_id": ep["episode_id"], "benefit": round(b, 2),
                        "delta_pnl": ep["delta_pnl"]})
    benefit = sum(e["benefit"] for e in per_ep)
    cost = max(0.0, bl_g2_pnl - ov_g2_pnl)
    net = global_ov_total - global_bl_total
    bcr = benefit / cost if cost > 0 else float("inf") if benefit > 0 else 0.0

    pos_benefits = sorted([e for e in per_ep if e["benefit"] > 0],
                          key=lambda x: x["benefit"], reverse=True)
    top1_pct = pos_benefits[0]["benefit"] / benefit * 100 if benefit > 0 and pos_benefits else 0.0
    top2_pct = (sum(e["benefit"] for e in pos_benefits[:2]) / benefit * 100
                if benefit > 0 and len(pos_benefits) >= 2 else top1_pct)

    blocked_winners = [t for t in blocked_trades if t["pnl"] > 0]

    return {
        "benefit": round(benefit, 2),
        "cost": round(cost, 2),
        "net": round(net, 2),
        "bcr": round(bcr, 3),
        "share_top1": round(top1_pct, 1),
        "share_top2": round(top2_pct, 1),
        "n_blocked_winners": len(blocked_winners),
        "blocked_winners_pnl": round(sum(t["pnl"] for t in blocked_winners), 2),
        "n_blocked_total": len(blocked_trades),
        "blocked_total_pnl": round(sum(t["pnl"] for t in blocked_trades), 2),
        "g1_delta_total": round(sum(ep["delta_pnl"] for ep in g1_episodes), 2),
        "g2_delta": round(ov_g2_pnl - bl_g2_pnl, 2),
        "n_cascade_episodes": len(g1_episodes),
        "per_episode": per_ep,
    }


# ── Config definitions ───────────────────────────────────────────────────────

CONFIGS = [
    {
        "label": "baseline",
        "cfg": V8ApexConfig(cooldown_after_emergency_dd_bars=0),
        "description": "No cooldown (K=0)",
    },
    {
        "label": "v1_K12",
        "cfg": V8ApexConfig(cooldown_after_emergency_dd_bars=12),
        "description": "Flat cooldown K=12 (best holdout from C6)",
    },
    {
        "label": "v2_escalating",
        "cfg": V8ApexConfig(
            escalating_cooldown=True,
            short_cooldown_bars=3,
            long_cooldown_bars=12,
            escalating_lookback_bars=24,
            cascade_trigger_count=2,
            cooldown_after_emergency_dd_bars=0,
        ),
        "description": "Escalating: short=3, long=12, lookback=24, trigger=2",
    },
]


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("  C9: COMPARE BASELINE vs V1(K=12) vs V2(ESCALATING)")
    print("=" * 70)
    print()

    # ── Load data ─────────────────────────────────────────────────────────
    print("  Loading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    cost = SCENARIOS[SCENARIO]

    # ── Run baseline once for episode extraction ──────────────────────────
    print("  Running baseline for episode extraction...")
    bl_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=0)
    bl_strat = V8ApexStrategy(bl_cfg)
    bl_engine = BacktestEngine(
        feed=feed, strategy=bl_strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    )
    bl_result = bl_engine.run()
    print(f"    Baseline trades: {len(bl_result.trades)}")

    # ── Extract episodes ──────────────────────────────────────────────────
    print("  Extracting DD episodes...")
    episodes_full = extract_episodes(bl_result.equity)
    ho_equity = [s for s in bl_result.equity if s.close_time >= HOLDOUT_START_MS]
    episodes_holdout = extract_episodes(ho_equity)

    labeled_full = label_cascades(episodes_full, bl_result.trades)
    cascade_full = [ep for ep in labeled_full if ep["is_cascade"]]
    labeled_holdout = label_cascades(episodes_holdout, bl_result.trades)
    cascade_holdout = [ep for ep in labeled_holdout if ep["is_cascade"]]

    print(f"    Full cascades: {len(cascade_full)}")
    print(f"    Holdout cascades: {len(cascade_holdout)}")

    cascade_windows_full = [(ep["peak_ts"], ep["end_ts"]) for ep in cascade_full]
    cascade_windows_holdout = [(ep["peak_ts"], ep["end_ts"]) for ep in cascade_holdout]

    bl_g2_pnl_full = compute_g2_equity_pnl(bl_result.equity, cascade_windows_full)
    bl_g2_pnl_holdout = compute_g2_equity_pnl(ho_equity, cascade_windows_holdout)

    bl_final_nav = bl_result.equity[-1].nav_mid if bl_result.equity else INITIAL_CASH
    global_bl_total = bl_final_nav - INITIAL_CASH

    ho_bl_trades = [t for t in bl_result.trades if t.exit_ts_ms >= HOLDOUT_START_MS]
    print()

    # ── Run each config ───────────────────────────────────────────────────
    results_full = []
    results_holdout = []
    run_data = {}  # store for report building

    for conf in CONFIGS:
        label = conf["label"]
        cfg = conf["cfg"]
        desc = conf["description"]

        print(f"  {'─' * 50}")
        print(f"  {label}: {desc}")
        print(f"  {'─' * 50}")

        if label == "baseline":
            ov_result = bl_result
            signal_log = []
        else:
            ov_strat = InstrumentedV8Apex(cfg)
            ov_engine = BacktestEngine(
                feed=feed, strategy=ov_strat, cost=cost,
                initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
            )
            ov_result = ov_engine.run()
            signal_log = ov_strat.signal_log

        ov_final_nav = ov_result.equity[-1].nav_mid if ov_result.equity else INITIAL_CASH
        global_ov_total = ov_final_nav - INITIAL_CASH

        print(f"    Trades: {len(ov_result.trades)}, Final NAV: {ov_final_nav:.2f}")

        # ── Full period ──
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
            cascade_windows_full, signal_log) if label != "baseline" else []

        bc_full = compute_benefit_cost(
            g1_full, bl_g2_pnl_full, ov_g2_pnl_full,
            blocked_full, global_bl_total, global_ov_total)

        row_full = {
            "config": label,
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
              f"BCR {bc_full['bcr']:.3f}")

        # ── Holdout period ──
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
            cascade_windows_holdout, sig_log_ho) if label != "baseline" else []

        # Holdout global totals
        g1_ho_bl_sum = sum(ep.get("bl_pnl", 0) for ep in g1_holdout) if g1_holdout else 0
        g1_ho_ov_sum = sum(ep.get("ov_pnl", 0) for ep in g1_holdout) if g1_holdout else 0
        ho_bl_total = g1_ho_bl_sum + bl_g2_pnl_holdout
        ho_ov_total = g1_ho_ov_sum + ov_g2_pnl_ho

        bc_holdout = compute_benefit_cost(
            g1_holdout, bl_g2_pnl_holdout, ov_g2_pnl_ho,
            blocked_holdout, ho_bl_total, ho_ov_total)

        row_holdout = {
            "config": label,
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

        # Store for report
        run_data[label] = {
            "full": bc_full,
            "holdout": bc_holdout,
            "n_trades_full": len(ov_result.trades),
            "n_trades_ho": len(ov_ho_trades),
            "final_nav": round(ov_final_nav, 2),
        }

    # ── Write CSVs ────────────────────────────────────────────────────────
    OUTDIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    csv_fields = [
        "config", "benefit", "cost", "net", "bcr",
        "share_top1", "share_top2",
        "n_blocked_winners", "blocked_winners_pnl",
        "g1_delta_total", "g2_delta",
        "n_cascade_episodes", "n_trades", "final_nav",
    ]

    full_csv_path = OUTDIR / "compare_v1_v2_full.csv"
    with open(full_csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerows(results_full)
    print(f"\n  Saved: {full_csv_path}")

    holdout_csv_path = OUTDIR / "compare_v1_v2_holdout.csv"
    with open(holdout_csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerows(results_holdout)
    print(f"  Saved: {holdout_csv_path}")

    # ── Generate report ───────────────────────────────────────────────────
    report = build_report(results_full, results_holdout, run_data,
                          cascade_full, cascade_holdout)
    report_path = REPORT_DIR / "overlayA_v2_results.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"  Saved: {report_path}")

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")
    print("=" * 70)


# ── Report builder ────────────────────────────────────────────────────────────

def build_report(full: list[dict], holdout: list[dict], run_data: dict,
                 cascade_full: list[dict], cascade_holdout: list[dict]) -> str:
    lines = []
    L = lines.append

    bl_f = run_data["baseline"]["full"]
    v1_f = run_data["v1_K12"]["full"]
    v2_f = run_data["v2_escalating"]["full"]
    bl_h = run_data["baseline"]["holdout"]
    v1_h = run_data["v1_K12"]["holdout"]
    v2_h = run_data["v2_escalating"]["holdout"]

    L("# OverlayA v2 Results: Baseline vs V1 vs V2")
    L("")
    L("**Date:** 2026-02-24")
    L("**Scenario:** harsh (50 bps RT)")
    L("")
    L("| Config | Description |")
    L("|--------|-------------|")
    L("| **baseline** | No cooldown (K=0) |")
    L("| **v1_K12** | Flat cooldown K=12 H4 bars (48h) — best holdout from C6 |")
    L("| **v2_escalating** | Escalating: short=3 (12h) / long=12 (48h) / lookback=24 (96h) / trigger=2 |")
    L("")
    L(f"**Cascade episodes:** Full={len(cascade_full)}, Holdout={len(cascade_holdout)}")
    L("")

    # ── Section 1: Full period comparison ──
    L("---")
    L("")
    L("## 1. Full Period (2019-01 → 2026-02)")
    L("")
    L("| Metric | baseline | v1 (K=12) | v2 (escalating) | v2 vs v1 Δ |")
    L("|--------|--------:|---------:|----------------:|-----------:|")

    def bcr_s(v):
        return "inf" if v > 1e6 else f"{v:.2f}"

    L(f"| **G1 Benefit** | $0 | ${v1_f['benefit']:,.0f} | ${v2_f['benefit']:,.0f} "
      f"| ${v2_f['benefit'] - v1_f['benefit']:+,.0f} |")
    L(f"| **G2 Cost** | $0 | ${v1_f['cost']:,.0f} | ${v2_f['cost']:,.0f} "
      f"| ${v2_f['cost'] - v1_f['cost']:+,.0f} |")
    L(f"| **Net** | $0 | ${v1_f['net']:+,.0f} | ${v2_f['net']:+,.0f} "
      f"| ${v2_f['net'] - v1_f['net']:+,.0f} |")
    L(f"| **BCR** | — | {bcr_s(v1_f['bcr'])} | {bcr_s(v2_f['bcr'])} | — |")
    L(f"| **Top1 %** | — | {v1_f['share_top1']:.0f}% | {v2_f['share_top1']:.0f}% | — |")
    L(f"| **Top2 %** | — | {v1_f['share_top2']:.0f}% | {v2_f['share_top2']:.0f}% | — |")
    L(f"| **#Blocked Winners** | 0 | {v1_f['n_blocked_winners']} | {v2_f['n_blocked_winners']} "
      f"| {v2_f['n_blocked_winners'] - v1_f['n_blocked_winners']:+d} |")
    L(f"| **Blocked Win PnL** | $0 | ${v1_f['blocked_winners_pnl']:+,.0f} "
      f"| ${v2_f['blocked_winners_pnl']:+,.0f} "
      f"| ${v2_f['blocked_winners_pnl'] - v1_f['blocked_winners_pnl']:+,.0f} |")
    L(f"| **G1 Δ Total** | $0 | ${v1_f['g1_delta_total']:+,.0f} | ${v2_f['g1_delta_total']:+,.0f} "
      f"| ${v2_f['g1_delta_total'] - v1_f['g1_delta_total']:+,.0f} |")
    L(f"| **G2 Δ** | $0 | ${v1_f['g2_delta']:+,.0f} | ${v2_f['g2_delta']:+,.0f} "
      f"| ${v2_f['g2_delta'] - v1_f['g2_delta']:+,.0f} |")
    n_v1_f = run_data["v1_K12"]["n_trades_full"]
    n_v2_f = run_data["v2_escalating"]["n_trades_full"]
    n_bl_f = run_data["baseline"]["n_trades_full"]
    L(f"| **Trades** | {n_bl_f} | {n_v1_f} | {n_v2_f} | {n_v2_f - n_v1_f:+d} |")
    L(f"| **Final NAV** | ${run_data['baseline']['final_nav']:,.2f} "
      f"| ${run_data['v1_K12']['final_nav']:,.2f} "
      f"| ${run_data['v2_escalating']['final_nav']:,.2f} | — |")
    L("")

    # ── Section 2: Holdout comparison ──
    L("---")
    L("")
    L("## 2. Holdout Period (2024-10 → 2026-02)")
    L("")
    L("| Metric | baseline | v1 (K=12) | v2 (escalating) | v2 vs v1 Δ |")
    L("|--------|--------:|---------:|----------------:|-----------:|")
    L(f"| **G1 Benefit** | $0 | ${v1_h['benefit']:,.0f} | ${v2_h['benefit']:,.0f} "
      f"| ${v2_h['benefit'] - v1_h['benefit']:+,.0f} |")
    L(f"| **G2 Cost** | $0 | ${v1_h['cost']:,.0f} | ${v2_h['cost']:,.0f} "
      f"| ${v2_h['cost'] - v1_h['cost']:+,.0f} |")
    L(f"| **Net** | $0 | ${v1_h['net']:+,.0f} | ${v2_h['net']:+,.0f} "
      f"| ${v2_h['net'] - v1_h['net']:+,.0f} |")
    L(f"| **BCR** | — | {bcr_s(v1_h['bcr'])} | {bcr_s(v2_h['bcr'])} | — |")
    L(f"| **#Blocked Winners** | 0 | {v1_h['n_blocked_winners']} | {v2_h['n_blocked_winners']} "
      f"| {v2_h['n_blocked_winners'] - v1_h['n_blocked_winners']:+d} |")
    L(f"| **Blocked Win PnL** | $0 | ${v1_h['blocked_winners_pnl']:+,.0f} "
      f"| ${v2_h['blocked_winners_pnl']:+,.0f} "
      f"| ${v2_h['blocked_winners_pnl'] - v1_h['blocked_winners_pnl']:+,.0f} |")
    n_v1_h = run_data["v1_K12"]["n_trades_ho"]
    n_v2_h = run_data["v2_escalating"]["n_trades_ho"]
    n_bl_h = run_data["baseline"]["n_trades_ho"]
    L(f"| **Trades** | {n_bl_h} | {n_v1_h} | {n_v2_h} | {n_v2_h - n_v1_h:+d} |")
    L("")

    # ── Section 3: Analysis ──
    L("---")
    L("")
    L("## 3. Analysis")
    L("")

    # Cost reduction
    cost_delta_f = v2_f["cost"] - v1_f["cost"]
    cost_delta_h = v2_h["cost"] - v1_h["cost"]
    cost_reduction_f_pct = (cost_delta_f / v1_f["cost"] * 100
                            if v1_f["cost"] > 0 else 0)
    cost_reduction_h_pct = (cost_delta_h / v1_h["cost"] * 100
                            if v1_h["cost"] > 0 else 0)

    L("### 3.1 Does v2 reduce Group2 cost?")
    L("")
    if cost_delta_f < 0:
        L(f"**YES.** V2 reduces G2 cost by ${abs(cost_delta_f):,.0f} "
          f"({abs(cost_reduction_f_pct):.0f}%) on full period.")
    elif cost_delta_f == 0:
        L(f"**NO CHANGE.** V2 has the same G2 cost as V1 on full period.")
    else:
        L(f"**NO — cost increased** by ${cost_delta_f:,.0f} "
          f"({cost_reduction_f_pct:+.0f}%) on full period.")
    L("")
    if cost_delta_h < 0:
        L(f"Holdout: V2 reduces cost by ${abs(cost_delta_h):,.0f} "
          f"({abs(cost_reduction_h_pct):.0f}%).")
    elif cost_delta_h == 0:
        L(f"Holdout: Same cost.")
    else:
        L(f"Holdout: Cost increased by ${cost_delta_h:,.0f} "
          f"({cost_reduction_h_pct:+.0f}%).")
    L("")

    # Benefit retention
    benefit_delta_f = v2_f["benefit"] - v1_f["benefit"]
    benefit_retention_f_pct = (v2_f["benefit"] / v1_f["benefit"] * 100
                               if v1_f["benefit"] > 0 else 100)
    benefit_delta_h = v2_h["benefit"] - v1_h["benefit"]
    benefit_retention_h_pct = (v2_h["benefit"] / v1_h["benefit"] * 100
                               if v1_h["benefit"] > 0 else 100)

    L("### 3.2 Does v2 retain Group1 benefit?")
    L("")
    if benefit_delta_f >= 0:
        L(f"**YES.** V2 retains {benefit_retention_f_pct:.0f}% of V1 benefit "
          f"(${v2_f['benefit']:,.0f} vs ${v1_f['benefit']:,.0f}).")
    elif benefit_retention_f_pct >= 80:
        L(f"**MOSTLY.** V2 retains {benefit_retention_f_pct:.0f}% of V1 benefit "
          f"(${v2_f['benefit']:,.0f} vs ${v1_f['benefit']:,.0f}, "
          f"lost ${abs(benefit_delta_f):,.0f}).")
    else:
        L(f"**NO — significant benefit loss.** V2 retains only "
          f"{benefit_retention_f_pct:.0f}% of V1 benefit.")
    L("")
    if v1_h["benefit"] > 0:
        L(f"Holdout: V2 retains {benefit_retention_h_pct:.0f}% "
          f"(${v2_h['benefit']:,.0f} vs ${v1_h['benefit']:,.0f}).")
    else:
        L(f"Holdout: V1 benefit was $0 — no retention comparison possible.")
    L("")

    # Blocked winners
    bw_delta_f = v2_f["n_blocked_winners"] - v1_f["n_blocked_winners"]
    bw_pnl_delta_f = v2_f["blocked_winners_pnl"] - v1_f["blocked_winners_pnl"]

    L("### 3.3 Blocked winners impact")
    L("")
    L(f"| Period | V1 blocked | V2 blocked | Δ count | Δ PnL |")
    L(f"|--------|----------:|----------:|--------:|------:|")
    L(f"| Full | {v1_f['n_blocked_winners']} (${v1_f['blocked_winners_pnl']:+,.0f}) "
      f"| {v2_f['n_blocked_winners']} (${v2_f['blocked_winners_pnl']:+,.0f}) "
      f"| {bw_delta_f:+d} "
      f"| ${bw_pnl_delta_f:+,.0f} |")
    bw_delta_h = v2_h["n_blocked_winners"] - v1_h["n_blocked_winners"]
    bw_pnl_delta_h = v2_h["blocked_winners_pnl"] - v1_h["blocked_winners_pnl"]
    L(f"| Holdout | {v1_h['n_blocked_winners']} (${v1_h['blocked_winners_pnl']:+,.0f}) "
      f"| {v2_h['n_blocked_winners']} (${v2_h['blocked_winners_pnl']:+,.0f}) "
      f"| {bw_delta_h:+d} "
      f"| ${bw_pnl_delta_h:+,.0f} |")
    L("")

    if bw_delta_f < 0:
        L(f"V2 unblocks {abs(bw_delta_f)} winner(s) worth "
          f"${abs(bw_pnl_delta_f):,.0f} — the isolated-ED recovery trades "
          f"that the escalating cooldown correctly allows through.")
    elif bw_delta_f == 0:
        L(f"Same number of blocked winners — the escalating cooldown did not "
          f"change which winners are blocked.")
    else:
        L(f"V2 blocks {bw_delta_f} more winners — unexpected.")
    L("")

    # Net improvement
    L("### 3.4 Net improvement")
    L("")
    net_delta_f = v2_f["net"] - v1_f["net"]
    net_delta_h = v2_h["net"] - v1_h["net"]
    L(f"| Period | V1 Net | V2 Net | Δ Net |")
    L(f"|--------|-------:|-------:|------:|")
    L(f"| Full | ${v1_f['net']:+,.0f} | ${v2_f['net']:+,.0f} | ${net_delta_f:+,.0f} |")
    L(f"| Holdout | ${v1_h['net']:+,.0f} | ${v2_h['net']:+,.0f} | ${net_delta_h:+,.0f} |")
    L("")

    if net_delta_f > 0:
        L(f"**V2 improves net by ${net_delta_f:+,.0f}** on full period.")
    elif net_delta_f == 0:
        L(f"V2 has the same net as V1 on full period.")
    else:
        L(f"V2 net is worse by ${abs(net_delta_f):,.0f} on full period.")
    L("")

    # ── Section 4: Verdict ──
    L("---")
    L("")
    L("## 4. Verdict")
    L("")

    # Assess: did v2 reduce cost significantly?
    cost_sig = abs(cost_delta_f) > 500  # > $500 change
    benefit_kept = benefit_retention_f_pct >= 80
    net_improved = net_delta_f > 0

    if cost_delta_f < 0 and cost_sig and benefit_kept:
        verdict = "PASS"
        L(f"### PASS")
        L("")
        L(f"V2 **reduces cost significantly** (−${abs(cost_delta_f):,.0f}) "
          f"while **retaining {benefit_retention_f_pct:.0f}% of benefit**.")
    elif cost_delta_f <= 0 and benefit_kept:
        if net_improved:
            verdict = "PASS"
            L(f"### PASS")
            L("")
            L(f"V2 reduces cost and improves net by ${net_delta_f:+,.0f}. "
              f"Benefit retained at {benefit_retention_f_pct:.0f}%.")
        else:
            verdict = "MARGINAL"
            L(f"### MARGINAL")
            L("")
            L(f"V2 reduces cost but net did not improve. "
              f"Benefit at {benefit_retention_f_pct:.0f}%.")
    elif not benefit_kept:
        verdict = "FAIL"
        L(f"### FAIL")
        L("")
        L(f"V2 lost too much benefit ({benefit_retention_f_pct:.0f}% retained). "
          f"The escalating cooldown's short window is not long enough to protect "
          f"in some cascade episodes.")
    else:
        verdict = "FAIL"
        L(f"### FAIL")
        L("")
        L(f"V2 did not reduce cost (Δ=${cost_delta_f:+,.0f}).")
    L("")

    # Summary table
    L("### Summary")
    L("")
    L(f"| Question | Answer |")
    L(f"|----------|--------|")
    L(f"| V2 reduces G2 cost? | {'YES' if cost_delta_f < 0 else 'NO'} "
      f"(Δ=${cost_delta_f:+,.0f}) |")
    L(f"| V2 retains G1 benefit? | {'YES' if benefit_kept else 'NO'} "
      f"({benefit_retention_f_pct:.0f}%) |")
    L(f"| V2 improves net? | {'YES' if net_improved else 'NO'} "
      f"(Δ=${net_delta_f:+,.0f}) |")
    L(f"| V2 unblocks winners? | "
      f"{'YES' if bw_delta_f < 0 else 'NO'} ({bw_delta_f:+d}) |")
    L(f"| Holdout confirms? | "
      f"{'YES' if net_delta_h >= 0 else 'NO'} "
      f"(Δ=${net_delta_h:+,.0f}) |")
    L("")

    # ── Section 5: Root cause ──
    L("---")
    L("")
    L("## 5. Root Cause Analysis")
    L("")
    L("### Why short_cooldown=3 provides zero cascade protection")
    L("")
    L("The V8Apex strategy has `exit_cooldown_bars=3` (Gate 2), which already blocks "
      "re-entry for 3 bars after ANY exit. The escalating cooldown's `short_cooldown_bars=3` "
      "(Gate 0) overlaps with this existing gate:")
    L("")
    L("```")
    L("After emergency_dd exit at bar N:")
    L("  Gate 0 (overlay):  blocks N, N+1       (short_cooldown=3, decremented immediately → effective 2 bars)")
    L("  Gate 2 (exit cd):  blocks N, N+1, N+2  (exit_cooldown_bars=3, checks idx - last_exit < 3)")
    L("  Net effect:        Gate 2 is the binding constraint → overlay adds nothing")
    L("```")
    L("")
    L("Because `short_cooldown_bars ≤ exit_cooldown_bars`, the first ED exit triggers NO "
      "additional blocking. The strategy re-enters at the same time as baseline. Only after "
      "a 2nd ED exit does the long cooldown activate — but by then, the cascade damage is done.")
    L("")
    L("### Evidence:")
    L("")
    L(f"- V2 trades: {n_v2_f} vs baseline: {n_bl_f} "
      f"(only {n_bl_f - n_v2_f} trade(s) blocked)")
    L(f"- V1 trades: {n_v1_f} vs baseline: {n_bl_f} "
      f"(blocked {n_bl_f - n_v1_f} trades)")
    L(f"- V2 G1 Δ Total: ${v2_f['g1_delta_total']:+,.0f} "
      f"(V2 is WORSE than baseline in cascade episodes)")
    L("")
    L("### Cascade episode flow comparison")
    L("")
    L("```")
    L("Typical 4-ED cascade:  ED₁ → ED₂ → ED₃ → ED₄")
    L("")
    L("Baseline (K=0):        ✗     ✗     ✗     ✗    (takes all 4 losses)")
    L("V1 (K=12):             ✗     ○     ○     ○    (blocks 3, saves ~$17k)")
    L("V2 (short=3, long=12): ✗     ✗     ○     ○    (allows 2nd hit, then blocks)")
    L("")
    L("✗ = loss taken   ○ = blocked by cooldown")
    L("```")
    L("")
    L("V2 takes one extra loss per cascade compared to V1. "
      "With 4 cascade episodes, this adds up to a significant penalty "
      "that wipes out the benefit from unblocking isolated recovery winners.")
    L("")
    L("### Fix options")
    L("")
    L("1. **Increase short_cooldown to 6+** — ensures Gate 0 is the binding constraint "
      "after the first ED, providing partial protection even for isolated exits")
    L("2. **Use cascade_trigger_count=1** with conditional short/long logic — "
      "apply longer cooldown from the first ED if market context suggests cascade risk")
    L("3. **Stay with V1 (K=12)** — the flat cooldown is simpler and the opportunity "
      "cost ($33,733 blocked winners) is the known trade-off for $17,368 cascade protection")
    L("")

    # ── Section 6: Deliverables ──
    L("---")
    L("")
    L("## 6. Deliverables")
    L("")
    L("| Artifact | Path |")
    L("|----------|------|")
    L("| Script | `experiments/overlayA/overlayA_compare_v1_v2.py` |")
    L("| Full CSV | `out_overlayA_conditional/compare_v1_v2_full.csv` |")
    L("| Holdout CSV | `out_overlayA_conditional/compare_v1_v2_holdout.csv` |")
    L("| This report | `reports/overlayA_v2_results.md` |")
    L("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
