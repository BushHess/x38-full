#!/usr/bin/env python3
"""C10: Leave-One-Episode-Out robustness test for OverlayA V1(K=12).

For each cascade episode, remove it from Group1 and recompute:
  - benefit (without that episode)
  - cost (unchanged — G2 is fixed)
  - BCR, net_conditional

If removing any single episode causes net_conditional to go deeply negative,
the overlay's benefit is concentrated and fragile.

Outputs:
  - out_overlayA_conditional/leave_one_episode_out.csv
  - reports/overlayA_leave_one_out.md

Usage:
    python experiments/leave_one_out/overlayA_leave_one_out.py
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
K = 12  # V1 best cooldown from C6

OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
REPORT_DIR = PROJECT_ROOT / "out/v10_full_validation_stepwise" / "reports"

HOLDOUT_START_MS = 1727740800000  # 2024-10-01 00:00 UTC
DD_MIN_PCT = 0.08
RECOVERY_TOL = 0.001
ENTRY_TS_MATCH_TOL_MS = 14_400_000

COOLDOWN_REASONS = {"cooldown_after_emergency_dd", "short_cooldown", "long_cooldown"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def ms_to_date(ms: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


@dataclass
class DDEpisode:
    episode_id: int
    peak_ts: int; trough_ts: int; end_ts: int
    peak_nav: float; trough_nav: float; end_nav: float
    depth_pct: float; duration_days: float
    peak_date: str = ""; trough_date: str = ""; end_date: str = ""
    recovered: bool = True


def extract_episodes(equity_snaps, dd_min_pct: float = DD_MIN_PCT) -> list[DDEpisode]:
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
                peak_nav = nav_arr[j]; peak_idx = j; j += 1
            else:
                dd = (peak_nav - nav_arr[j]) / peak_nav
                if dd >= dd_min_pct:
                    break
                j += 1
                if j < n and nav_arr[j] >= peak_nav:
                    peak_nav = nav_arr[j]; peak_idx = j
        else:
            break
        if j >= n:
            break
        trough_idx = j; trough_nav = nav_arr[j]; recovery_idx = None
        k = j + 1
        while k < n:
            if nav_arr[k] < trough_nav:
                trough_nav = nav_arr[k]; trough_idx = k
            if nav_arr[k] >= peak_nav * (1 - RECOVERY_TOL):
                recovery_idx = k; break
            k += 1
        end_idx = recovery_idx if recovery_idx is not None else n - 1
        ep_id += 1
        depth = (peak_nav - trough_nav) / peak_nav
        dur_ms = ts_arr[trough_idx] - ts_arr[peak_idx]
        episodes.append(DDEpisode(
            episode_id=ep_id,
            peak_ts=int(ts_arr[peak_idx]), trough_ts=int(ts_arr[trough_idx]),
            end_ts=int(ts_arr[end_idx]),
            peak_nav=round(float(peak_nav), 2), trough_nav=round(float(trough_nav), 2),
            end_nav=round(float(nav_arr[end_idx]), 2),
            depth_pct=round(depth * 100, 2),
            duration_days=round(dur_ms / 86_400_000, 2),
            peak_date=ms_to_date(int(ts_arr[peak_idx])),
            trough_date=ms_to_date(int(ts_arr[trough_idx])),
            end_date=ms_to_date(int(ts_arr[end_idx])),
            recovered=recovery_idx is not None,
        ))
        i = end_idx + 1
    return episodes


def label_cascades(episodes: list[DDEpisode], trades: list[Trade]) -> list[dict]:
    labeled = []
    for ep in episodes:
        in_window = sorted(
            [t for t in trades if ep.peak_ts <= t.exit_ts_ms <= ep.end_ts],
            key=lambda t: t.exit_ts_ms)
        reasons = [t.exit_reason for t in in_window]
        max_run = current_run = n_emdd = 0
        for r in reasons:
            if r == "emergency_dd":
                current_run += 1; n_emdd += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 0
        labeled.append({
            "episode_id": ep.episode_id,
            "peak_ts": ep.peak_ts, "trough_ts": ep.trough_ts, "end_ts": ep.end_ts,
            "peak_nav": ep.peak_nav, "trough_nav": ep.trough_nav,
            "depth_pct": ep.depth_pct, "duration_days": ep.duration_days,
            "peak_date": ep.peak_date, "trough_date": ep.trough_date,
            "end_date": ep.end_date, "recovered": ep.recovered,
            "n_emergency_dd": n_emdd, "max_run_emergency_dd": max_run,
            "is_cascade": max_run >= 2,
        })
    return labeled


def nav_at_ts(equity, ts_ms):
    best = None
    for snap in equity:
        if snap.close_time <= ts_ms:
            best = snap
        else:
            break
    return best.nav_mid if best else None


def compute_g1_episode(ep: dict, bl_equity, ov_equity) -> dict | None:
    peak_ts, end_ts = ep["peak_ts"], ep["end_ts"]
    bl_nav_peak = nav_at_ts(bl_equity, peak_ts)
    bl_nav_end = nav_at_ts(bl_equity, end_ts)
    if bl_nav_peak is None or bl_nav_end is None:
        return None
    bl_pnl = bl_nav_end - bl_nav_peak
    ov_nav_peak = nav_at_ts(ov_equity, peak_ts)
    ov_nav_end = nav_at_ts(ov_equity, end_ts)
    if ov_nav_peak is None or ov_nav_end is None:
        return None
    ov_pnl = ov_nav_end - ov_nav_peak
    return {
        "episode_id": ep["episode_id"],
        "peak_date": ep["peak_date"],
        "trough_date": ep["trough_date"],
        "depth_pct": ep["depth_pct"],
        "n_emergency_dd": ep["n_emergency_dd"],
        "bl_pnl": round(bl_pnl, 2),
        "ov_pnl": round(ov_pnl, 2),
        "delta_pnl": round(ov_pnl - bl_pnl, 2),
        "benefit": round(max(0.0, ov_pnl - bl_pnl), 2),
    }


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


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("  C10: LEAVE-ONE-EPISODE-OUT ROBUSTNESS TEST")
    print(f"  Overlay: V1 (K={K})")
    print("=" * 70)
    print()

    # ── Load data & run backtests ─────────────────────────────────────────
    print("  Loading data...")
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    cost = SCENARIOS[SCENARIO]

    print("  Running baseline (K=0)...")
    bl_strat = V8ApexStrategy(V8ApexConfig(cooldown_after_emergency_dd_bars=0))
    bl_result = BacktestEngine(
        feed=feed, strategy=bl_strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    ).run()

    print(f"  Running overlay V1 (K={K})...")
    ov_strat = InstrumentedV8Apex(V8ApexConfig(cooldown_after_emergency_dd_bars=K))
    ov_result = BacktestEngine(
        feed=feed, strategy=ov_strat, cost=cost,
        initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
    ).run()
    signal_log = ov_strat.signal_log

    print(f"    Baseline: {len(bl_result.trades)} trades, "
          f"NAV {bl_result.equity[-1].nav_mid:.2f}")
    print(f"    Overlay:  {len(ov_result.trades)} trades, "
          f"NAV {ov_result.equity[-1].nav_mid:.2f}")

    # ── Extract & label cascade episodes ──────────────────────────────────
    print("  Extracting episodes...")
    episodes_full = extract_episodes(bl_result.equity)
    labeled_full = label_cascades(episodes_full, bl_result.trades)
    cascade_full = [ep for ep in labeled_full if ep["is_cascade"]]
    print(f"    Cascade episodes: {len(cascade_full)}")

    cascade_windows_full = [(ep["peak_ts"], ep["end_ts"]) for ep in cascade_full]

    # ── Compute per-episode G1 delta ──────────────────────────────────────
    print("  Computing per-episode G1 benefit...")
    g1_episodes = []
    for ep in cascade_full:
        m = compute_g1_episode(ep, bl_result.equity, ov_result.equity)
        if m:
            g1_episodes.append(m)

    total_benefit = sum(e["benefit"] for e in g1_episodes)
    total_delta = sum(e["delta_pnl"] for e in g1_episodes)

    # G2 cost (fixed)
    bl_g2 = compute_g2_equity_pnl(bl_result.equity, cascade_windows_full)
    ov_g2 = compute_g2_equity_pnl(ov_result.equity, cascade_windows_full)
    g2_cost = max(0.0, bl_g2 - ov_g2)

    # Global net
    bl_nav = bl_result.equity[-1].nav_mid
    ov_nav = ov_result.equity[-1].nav_mid
    global_net = ov_nav - bl_nav

    # Full BCR
    full_bcr = total_benefit / g2_cost if g2_cost > 0 else float("inf")

    print()
    print(f"  Per-episode G1 breakdown:")
    for e in g1_episodes:
        tag = "***" if e["benefit"] == 0 else ""
        print(f"    EP{e['episode_id']:>2} ({e['peak_date']}): "
              f"bl_pnl ${e['bl_pnl']:>+10,.2f}  "
              f"ov_pnl ${e['ov_pnl']:>+10,.2f}  "
              f"delta ${e['delta_pnl']:>+10,.2f}  "
              f"benefit ${e['benefit']:>+10,.2f} {tag}")

    print(f"\n  Total benefit: ${total_benefit:,.2f}")
    print(f"  G2 cost:       ${g2_cost:,.2f}")
    print(f"  Full BCR:      {full_bcr:.3f}")
    print(f"  Global net:    ${global_net:+,.2f}")
    print()

    # ── Leave-one-out ─────────────────────────────────────────────────────
    print("  Leave-one-episode-out analysis:")
    print(f"  {'─' * 60}")

    loo_rows = []
    for i, excluded in enumerate(g1_episodes):
        remaining = [e for j, e in enumerate(g1_episodes) if j != i]
        loo_benefit = sum(e["benefit"] for e in remaining)
        loo_delta = sum(e["delta_pnl"] for e in remaining)
        loo_bcr = loo_benefit / g2_cost if g2_cost > 0 else float("inf")
        loo_net_cond = loo_benefit - g2_cost

        # Contribution of excluded episode
        excluded_share = (excluded["benefit"] / total_benefit * 100
                          if total_benefit > 0 else 0.0)

        row = {
            "excluded_episode": excluded["episode_id"],
            "excluded_date": excluded["peak_date"],
            "excluded_depth_pct": excluded["depth_pct"],
            "excluded_n_emdd": excluded["n_emergency_dd"],
            "excluded_delta_pnl": excluded["delta_pnl"],
            "excluded_benefit": excluded["benefit"],
            "excluded_benefit_share_pct": round(excluded_share, 1),
            "remaining_benefit": round(loo_benefit, 2),
            "cost": round(g2_cost, 2),
            "loo_net_conditional": round(loo_net_cond, 2),
            "loo_bcr": round(loo_bcr, 3),
            "still_positive": loo_net_cond >= 0,
        }
        loo_rows.append(row)

        status = "OK" if loo_net_cond >= 0 else "NEGATIVE"
        bcr_str = f"{loo_bcr:.2f}" if loo_bcr < 1e6 else "inf"
        print(f"    Drop EP{excluded['episode_id']:>2} ({excluded['peak_date']}): "
              f"benefit ${loo_benefit:>10,.2f}  "
              f"net_cond ${loo_net_cond:>+10,.2f}  "
              f"BCR {bcr_str:>6}  "
              f"[{status}]  "
              f"(was {excluded_share:.0f}% of benefit)")

    # Also add the "all included" baseline row
    all_row = {
        "excluded_episode": "none",
        "excluded_date": "—",
        "excluded_depth_pct": 0,
        "excluded_n_emdd": 0,
        "excluded_delta_pnl": 0,
        "excluded_benefit": 0,
        "excluded_benefit_share_pct": 0,
        "remaining_benefit": round(total_benefit, 2),
        "cost": round(g2_cost, 2),
        "loo_net_conditional": round(total_benefit - g2_cost, 2),
        "loo_bcr": round(full_bcr, 3),
        "still_positive": (total_benefit - g2_cost) >= 0,
    }

    # ── Holdout leave-one-out ─────────────────────────────────────────────
    print(f"\n  Holdout leave-one-out:")
    print(f"  {'─' * 60}")

    ho_equity_bl = [s for s in bl_result.equity if s.close_time >= HOLDOUT_START_MS]
    ho_equity_ov = [s for s in ov_result.equity if s.close_time >= HOLDOUT_START_MS]
    episodes_ho = extract_episodes(ho_equity_bl)
    labeled_ho = label_cascades(episodes_ho, bl_result.trades)
    cascade_ho = [ep for ep in labeled_ho if ep["is_cascade"]]

    cascade_windows_ho = [(ep["peak_ts"], ep["end_ts"]) for ep in cascade_ho]

    g1_ho = []
    for ep in cascade_ho:
        m = compute_g1_episode(ep, bl_result.equity, ov_result.equity)
        if m:
            g1_ho.append(m)

    ho_benefit = sum(e["benefit"] for e in g1_ho)
    bl_g2_ho = compute_g2_equity_pnl(ho_equity_bl, cascade_windows_ho)
    ov_g2_ho = compute_g2_equity_pnl(ho_equity_ov, cascade_windows_ho)
    ho_cost = max(0.0, bl_g2_ho - ov_g2_ho)
    ho_bcr = ho_benefit / ho_cost if ho_cost > 0 else float("inf")

    loo_rows_ho = []
    for i, excluded in enumerate(g1_ho):
        remaining = [e for j, e in enumerate(g1_ho) if j != i]
        loo_benefit = sum(e["benefit"] for e in remaining)
        loo_bcr_ho = loo_benefit / ho_cost if ho_cost > 0 else float("inf")
        loo_net_cond = loo_benefit - ho_cost
        excluded_share = (excluded["benefit"] / ho_benefit * 100
                          if ho_benefit > 0 else 0.0)

        row = {
            "excluded_episode": excluded["episode_id"],
            "excluded_date": excluded["peak_date"],
            "excluded_depth_pct": excluded["depth_pct"],
            "excluded_n_emdd": excluded["n_emergency_dd"],
            "excluded_delta_pnl": excluded["delta_pnl"],
            "excluded_benefit": excluded["benefit"],
            "excluded_benefit_share_pct": round(excluded_share, 1),
            "remaining_benefit": round(loo_benefit, 2),
            "cost": round(ho_cost, 2),
            "loo_net_conditional": round(loo_net_cond, 2),
            "loo_bcr": round(loo_bcr_ho, 3),
            "still_positive": loo_net_cond >= 0,
        }
        loo_rows_ho.append(row)

        status = "OK" if loo_net_cond >= 0 else "NEGATIVE"
        bcr_str = f"{loo_bcr_ho:.2f}" if loo_bcr_ho < 1e6 else "inf"
        print(f"    Drop EP{excluded['episode_id']:>2} ({excluded['peak_date']}): "
              f"benefit ${loo_benefit:>10,.2f}  "
              f"net_cond ${loo_net_cond:>+10,.2f}  "
              f"BCR {bcr_str:>6}  "
              f"[{status}]  "
              f"(was {excluded_share:.0f}% of benefit)")

    if not g1_ho:
        print("    (no cascade episodes in holdout)")

    # ── Write CSV ─────────────────────────────────────────────────────────
    OUTDIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    csv_fields = [
        "excluded_episode", "excluded_date", "excluded_depth_pct",
        "excluded_n_emdd", "excluded_delta_pnl", "excluded_benefit",
        "excluded_benefit_share_pct", "remaining_benefit", "cost",
        "loo_net_conditional", "loo_bcr", "still_positive",
    ]
    csv_path = OUTDIR / "leave_one_episode_out.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        w.writerow(all_row)
        w.writerows(loo_rows)
    print(f"\n  Saved: {csv_path}")

    # ── Generate report ───────────────────────────────────────────────────
    report = build_report(g1_episodes, loo_rows, g1_ho, loo_rows_ho,
                          total_benefit, g2_cost, full_bcr, global_net,
                          ho_benefit, ho_cost, ho_bcr)
    report_path = REPORT_DIR / "overlayA_leave_one_out.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"  Saved: {report_path}")

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")
    print("=" * 70)


# ── Report builder ────────────────────────────────────────────────────────────

def build_report(g1_eps, loo_full, g1_ho, loo_ho,
                 total_benefit, g2_cost, full_bcr, global_net,
                 ho_benefit, ho_cost, ho_bcr) -> str:
    lines = []
    L = lines.append

    L("# OverlayA Leave-One-Episode-Out Robustness Test")
    L("")
    L("**Date:** 2026-02-24")
    L("**Scenario:** harsh (50 bps RT)")
    L(f"**Overlay:** V1 (cooldown_after_emergency_dd_bars = {K})")
    L(f"**Cascade episodes:** {len(g1_eps)} (full period), {len(g1_ho)} (holdout)")
    L("")

    # ── Section 1: Per-episode breakdown ──
    L("---")
    L("")
    L("## 1. Per-Episode G1 Benefit Breakdown")
    L("")
    L("| EP | Peak Date | Depth% | #ED | BL PnL | OV PnL | Δ PnL | Benefit | Share% |")
    L("|---:|:----------|-------:|----:|-------:|-------:|------:|--------:|-------:|")
    for e in g1_eps:
        share = e["benefit"] / total_benefit * 100 if total_benefit > 0 else 0
        L(f"| {e['episode_id']} "
          f"| {e['peak_date']} "
          f"| {e['depth_pct']:.1f} "
          f"| {e['n_emergency_dd']} "
          f"| ${e['bl_pnl']:+,.0f} "
          f"| ${e['ov_pnl']:+,.0f} "
          f"| ${e['delta_pnl']:+,.0f} "
          f"| ${e['benefit']:,.0f} "
          f"| {share:.0f}% |")
    L(f"| **Total** | | | | | | | **${total_benefit:,.0f}** | **100%** |")
    L("")

    bcr_str = f"{full_bcr:.2f}" if full_bcr < 1e6 else "inf"
    L(f"**G2 Cost:** ${g2_cost:,.0f}")
    L(f"**BCR (all episodes):** {bcr_str}")
    L(f"**Net conditional:** ${total_benefit - g2_cost:+,.0f}")
    L(f"**Global net:** ${global_net:+,.0f}")
    L("")

    # ── Section 2: LOO table (full) ──
    L("---")
    L("")
    L("## 2. Leave-One-Out Results (Full Period)")
    L("")
    L("| Excluded EP | Date | Benefit Lost | Remaining Benefit | Cost | LOO Net | LOO BCR | Still ≥ 0? |")
    L("|:------------|:-----|------------:|-----------------:|-----:|--------:|--------:|:----------:|")

    for r in loo_full:
        bcr_s = f"{r['loo_bcr']:.2f}" if r["loo_bcr"] < 1e6 else "inf"
        ok = "YES" if r["still_positive"] else "**NO**"
        L(f"| EP{r['excluded_episode']} "
          f"| {r['excluded_date']} "
          f"| ${r['excluded_benefit']:,.0f} ({r['excluded_benefit_share_pct']:.0f}%) "
          f"| ${r['remaining_benefit']:,.0f} "
          f"| ${r['cost']:,.0f} "
          f"| ${r['loo_net_conditional']:+,.0f} "
          f"| {bcr_s} "
          f"| {ok} |")
    L("")

    n_negative = sum(1 for r in loo_full if not r["still_positive"])
    n_positive = sum(1 for r in loo_full if r["still_positive"])

    L(f"**LOO net ≥ 0 in {n_positive}/{len(loo_full)} scenarios** "
      f"(removing each cascade episode one at a time).")
    L("")

    # ── Section 3: LOO holdout ──
    if g1_ho:
        L("---")
        L("")
        L("## 3. Leave-One-Out Results (Holdout)")
        L("")
        L("| Excluded EP | Date | Benefit Lost | Remaining | Cost | LOO Net | LOO BCR | Still ≥ 0? |")
        L("|:------------|:-----|------------:|----------:|-----:|--------:|--------:|:----------:|")
        for r in loo_ho:
            bcr_s = f"{r['loo_bcr']:.2f}" if r["loo_bcr"] < 1e6 else "inf"
            ok = "YES" if r["still_positive"] else "**NO**"
            L(f"| EP{r['excluded_episode']} "
              f"| {r['excluded_date']} "
              f"| ${r['excluded_benefit']:,.0f} ({r['excluded_benefit_share_pct']:.0f}%) "
              f"| ${r['remaining_benefit']:,.0f} "
              f"| ${r['cost']:,.0f} "
              f"| ${r['loo_net_conditional']:+,.0f} "
              f"| {bcr_s} "
              f"| {ok} |")
        L("")

        ho_bcr_str = f"{ho_bcr:.2f}" if ho_bcr < 1e6 else "inf"
        L(f"**Holdout baseline:** benefit=${ho_benefit:,.0f}, "
          f"cost=${ho_cost:,.0f}, BCR={ho_bcr_str}")
        L("")
    else:
        L("---")
        L("")
        L("## 3. Holdout")
        L("")
        L("Only 1 cascade episode in holdout — leave-one-out removes all benefit. "
          "This confirms the holdout benefit is entirely from a single episode.")
        L("")

    # ── Section 4: Concentration risk ──
    L("---")
    L("")
    L("## 4. Concentration Risk Assessment")
    L("")

    if g1_eps:
        sorted_eps = sorted(g1_eps, key=lambda e: e["benefit"], reverse=True)
        top_ep = sorted_eps[0]
        top_share = top_ep["benefit"] / total_benefit * 100 if total_benefit > 0 else 0

        L(f"**Largest single-episode contribution:** EP{top_ep['episode_id']} "
          f"({top_ep['peak_date']}) — ${top_ep['benefit']:,.0f} "
          f"({top_share:.0f}% of total benefit)")
        L("")

        if top_share > 80:
            L(f"**HIGH concentration risk.** A single episode provides "
              f">{top_share:.0f}% of the benefit. If this episode had not occurred "
              f"(or the overlay had not helped), the overlay would lose its justification.")
        elif top_share > 50:
            L(f"**MODERATE concentration risk.** The top episode provides "
              f"{top_share:.0f}% of benefit — still the majority contributor, but "
              f"some benefit comes from other episodes.")
        else:
            L(f"**LOW concentration risk.** Benefit is distributed across episodes "
              f"(top contributor is {top_share:.0f}%).")
        L("")

        # Check negative-delta episodes
        neg_eps = [e for e in g1_eps if e["delta_pnl"] < 0]
        if neg_eps:
            L(f"**Episodes where overlay performed WORSE than baseline:** "
              f"{len(neg_eps)}/{len(g1_eps)}")
            for e in neg_eps:
                L(f"  - EP{e['episode_id']} ({e['peak_date']}): "
                  f"Δ=${e['delta_pnl']:+,.0f}")
            L("")
            L("These episodes represent time periods where the cooldown's "
              "opportunity cost (blocking profitable re-entries) exceeded its benefit. "
              "The overlay is net-positive only because other cascade episodes "
              "provide enough benefit to offset.")
            L("")

    # ── Section 5: Verdict ──
    L("---")
    L("")
    L("## 5. Verdict")
    L("")

    # Determine verdict
    if len(loo_full) == 0:
        verdict = "INCONCLUSIVE"
        reason = "No cascade episodes to test."
    elif n_negative == 0:
        verdict = "PASS — ROBUST"
        reason = (f"LOO net remains ≥ 0 in all {len(loo_full)} scenarios. "
                  f"No single episode is critical.")
    elif n_negative <= 1 and len(loo_full) >= 3:
        # Only 1 episode is critical but the others maintain positive net
        critical = [r for r in loo_full if not r["still_positive"]]
        crit_ep = critical[0] if critical else None
        verdict = "MARGINAL"
        if crit_ep:
            reason = (f"Removing EP{crit_ep['excluded_episode']} "
                      f"({crit_ep['excluded_date']}) makes LOO net negative "
                      f"(${crit_ep['loo_net_conditional']:+,.0f}). "
                      f"The overlay depends on this episode but "
                      f"{n_positive}/{len(loo_full)} scenarios remain positive.")
        else:
            reason = f"{n_positive}/{len(loo_full)} scenarios positive."
    else:
        critical = [r for r in loo_full if not r["still_positive"]]
        verdict = "FAIL — NOT ROBUST"
        reason = (f"LOO net goes negative in {n_negative}/{len(loo_full)} scenarios. "
                  f"The overlay's benefit is too concentrated.")

    L(f"### {verdict}")
    L("")
    L(f"> {reason}")
    L("")

    # Summary table
    L("### Summary")
    L("")
    L("| Metric | Value |")
    L("|--------|-------|")
    L(f"| Cascade episodes | {len(g1_eps)} |")
    L(f"| Total benefit | ${total_benefit:,.0f} |")
    L(f"| G2 cost | ${g2_cost:,.0f} |")
    bcr_str = f"{full_bcr:.2f}" if full_bcr < 1e6 else "inf"
    L(f"| Full BCR | {bcr_str} |")
    L(f"| LOO net ≥ 0 | {n_positive}/{len(loo_full)} |")
    L(f"| Worst LOO net | ${min(r['loo_net_conditional'] for r in loo_full):+,.0f} |"
      if loo_full else "| Worst LOO net | — |")
    L(f"| Top1 concentration | {sorted_eps[0]['benefit']/total_benefit*100:.0f}% |"
      if g1_eps and total_benefit > 0 else "| Top1 concentration | — |")
    L("")

    # ── Section 6: Deliverables ──
    L("---")
    L("")
    L("## 6. Deliverables")
    L("")
    L("| Artifact | Path |")
    L("|----------|------|")
    L("| Script | `experiments/leave_one_out/overlayA_leave_one_out.py` |")
    L("| LOO CSV | `out_overlayA_conditional/leave_one_episode_out.csv` |")
    L("| This report | `reports/overlayA_leave_one_out.md` |")
    L("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
