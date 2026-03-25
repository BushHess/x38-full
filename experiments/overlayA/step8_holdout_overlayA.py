#!/usr/bin/env python3
"""Step 8: Out-of-sample holdout validation — Overlay A vs Baseline.

Holdout period: 2024-10-01 → 2026-02-20 (locked from V11 validation).
Runs baseline (cooldown=0) and overlay A (cooldown=12) on holdout (harsh + base).

This script runs EXACTLY ONCE. If overlay A degrades harsh score or MDD
materially on holdout, verdict is HOLD/REJECT — no "explaining away".

Outputs:
  - step8_holdout_metrics.csv
  - reports/step8_holdout_overlayA.md

Usage:
    python experiments/overlayA/step8_holdout_overlayA.py
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np

np.seterr(all="ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

# Reuse InstrumentedV8Apex from step1
from experiments.overlayA.step1_export import InstrumentedV8Apex

# ── Constants ────────────────────────────────────────────────────────────────
DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
K = 12  # Overlay A cooldown bars

# Holdout period — locked from V11 validation (DO NOT CHANGE)
HOLDOUT_START = "2024-10-01"
HOLDOUT_END = "2026-02-20"

SCENARIOS_TO_RUN = ["harsh", "base"]

OUTDIR = PROJECT_ROOT / "out/v10_fix_loop"
REPORT_DIR = PROJECT_ROOT / "out/v10_full_validation_stepwise" / "reports"

# KPIs to compare
KPI_KEYS = [
    "score", "cagr_pct", "final_nav_mid", "max_drawdown_mid_pct",
    "sharpe", "sortino", "calmar",
    "trades", "wins", "losses", "win_rate_pct", "profit_factor",
    "avg_trade_pnl",
    "fees_total", "fee_drag_pct_per_year",
    "emergency_dd_count",
    "time_in_market_pct", "avg_exposure",
]

# ── Thresholds for PASS/HOLD/REJECT ─────────────────────────────────────────
# If overlay degrades harsh score by more than this → HOLD
SCORE_DEGRADE_THRESHOLD = 5.0
# If overlay increases MDD by more than this (pp) → HOLD
MDD_DEGRADE_THRESHOLD = 5.0


# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_kpis(result) -> dict:
    """Extract KPIs including emergency_dd count and score."""
    s = dict(result.summary)
    s["score"] = compute_objective(s)
    s["emergency_dd_count"] = sum(
        1 for t in result.trades if t.exit_reason == "emergency_dd"
    )
    return s


def compute_cascade_rates(signal_log: list[dict], report_start_ms: int) -> dict:
    """Compute cascade rate at <=3 and <=6 bars from event log."""
    log = [e for e in signal_log if e["bar_ts_ms"] >= report_start_ms]

    ed_exit_bars = []
    entry_bars = []
    for e in log:
        if e["event_type"] == "exit_signal" and e["reason"] == "emergency_dd":
            ed_exit_bars.append(int(e["bar_index"]))
        elif e["event_type"] == "entry_signal":
            entry_bars.append(int(e["bar_index"]))

    ed_exit_bars.sort()
    entry_bars.sort()

    n_ed = len(ed_exit_bars)
    if n_ed == 0:
        return {"n_ed_exits": 0, "cascade_rate_3": 0.0, "cascade_rate_6": 0.0}

    latencies = []
    for exit_bar in ed_exit_bars:
        for eb in entry_bars:
            if eb > exit_bar:
                latencies.append(eb - exit_bar)
                break

    n_within_3 = sum(1 for lat in latencies if lat <= 3)
    n_within_6 = sum(1 for lat in latencies if lat <= 6)

    return {
        "n_ed_exits": n_ed,
        "cascade_rate_3": round(100.0 * n_within_3 / n_ed, 1),
        "cascade_rate_6": round(100.0 * n_within_6 / n_ed, 1),
    }


def identify_blocked_trades_from_log(
    signal_log: list[dict],
    trades: list,
    report_start_ms: int,
) -> list[dict]:
    """Identify trades in baseline that Overlay A (K=12) would block.

    Works in-memory from InstrumentedV8Apex signal_log + BacktestResult.trades.
    """
    log = [e for e in signal_log if e["bar_ts_ms"] >= report_start_ms]

    # ED exit bar indices
    ed_exit_bars = []
    for e in log:
        if e["event_type"] == "exit_signal" and e["reason"] == "emergency_dd":
            ed_exit_bars.append(int(e["bar_index"]))
    ed_exit_bars.sort()

    # Entry signal bar indices
    entry_signals = [
        e for e in log if e["event_type"] == "entry_signal"
    ]
    entry_signals.sort(key=lambda e: int(e["bar_index"]))

    # Map entry_signal ts → trade
    # Each entry_signal generates a fill on the next bar → trade
    # Match by: trade.entry_ts_ms >= entry_signal.bar_ts_ms
    trades_sorted = sorted(trades, key=lambda t: t.entry_ts_ms)

    blocked = []
    blocked_ids = set()

    for es in entry_signals:
        es_bar = int(es["bar_index"])

        # Check if this entry is within K bars of any ED exit
        is_blocked = False
        for ed_bar in ed_exit_bars:
            if 0 < es_bar - ed_bar <= K:
                is_blocked = True
                break

        if not is_blocked:
            continue

        # Find the trade this entry signal started
        es_ts = es["bar_ts_ms"]
        for t in trades_sorted:
            if t.entry_ts_ms >= es_ts and t.trade_id not in blocked_ids:
                blocked.append({
                    "trade_id": t.trade_id,
                    "entry_ts": t.entry_ts_ms,
                    "exit_ts": t.exit_ts_ms,
                    "net_pnl": t.pnl,
                    "return_pct": t.return_pct,
                    "exit_reason": t.exit_reason,
                    "fees": 0,  # Trade object has no fees field
                    "days_held": t.days_held,
                })
                blocked_ids.add(t.trade_id)
                break

    return blocked


def compute_blocked_stats(blocked: list[dict], n_total: int) -> dict:
    """Compute expectancy stats for blocked trades."""
    if not blocked:
        return {
            "n_blocked": 0, "n_total_baseline": n_total,
            "pct_blocked": 0.0,
            "mean_net_pnl": 0.0, "median_net_pnl": 0.0,
            "total_net_pnl": 0.0, "pct_exit_emergency_dd": 0.0,
        }

    pnls = np.array([b["net_pnl"] for b in blocked])
    n_ed = sum(1 for b in blocked if b["exit_reason"] == "emergency_dd")

    return {
        "n_blocked": len(blocked),
        "n_total_baseline": n_total,
        "pct_blocked": round(100.0 * len(blocked) / n_total, 1) if n_total > 0 else 0.0,
        "mean_net_pnl": round(float(np.mean(pnls)), 2),
        "median_net_pnl": round(float(np.median(pnls)), 2),
        "total_net_pnl": round(float(np.sum(pnls)), 2),
        "pct_exit_emergency_dd": round(100.0 * n_ed / len(blocked), 1),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()
    print("=" * 70)
    print("  STEP 8: HOLDOUT VALIDATION — OVERLAY A")
    print(f"  Holdout: {HOLDOUT_START} → {HOLDOUT_END}")
    print("=" * 70)

    print("\nLoading data...")
    feed = DataFeed(DATA_PATH, start=HOLDOUT_START, end=HOLDOUT_END,
                    warmup_days=WARMUP_DAYS)
    report_start_ms = getattr(feed, "report_start_ms", 0) or 0

    all_kpis = {}
    cascade_data = {}
    blocked_stats = {}
    overlay_block_count = 0

    for scenario in SCENARIOS_TO_RUN:
        print(f"\n{'='*60}")
        print(f"  Scenario: {scenario}")
        print(f"{'='*60}")

        cost = SCENARIOS[scenario]

        # ── Baseline (cooldown=0, instrumented for blocked-trade analysis) ──
        print(f"  Running baseline (cooldown=0)...")
        bl_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=0)
        bl_strat = InstrumentedV8Apex(bl_cfg)
        bl_engine = BacktestEngine(
            feed=feed, strategy=bl_strat, cost=cost,
            initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
        )
        bl_result = bl_engine.run()
        bl_kpis = extract_kpis(bl_result)
        all_kpis[f"baseline_{scenario}"] = bl_kpis

        bl_cascade = compute_cascade_rates(bl_strat.signal_log, report_start_ms)
        cascade_data[f"baseline_{scenario}"] = bl_cascade

        print(f"    Trades: {bl_kpis['trades']}, CAGR: {bl_kpis.get('cagr_pct', 0):.2f}%, "
              f"Score: {bl_kpis['score']:.2f}, ED: {bl_kpis['emergency_dd_count']}")
        print(f"    Cascade ≤3: {bl_cascade['cascade_rate_3']:.1f}%, "
              f"≤6: {bl_cascade['cascade_rate_6']:.1f}%")

        # ── Overlay A (cooldown=K, instrumented) ──
        print(f"  Running overlay A (cooldown={K})...")
        ov_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=K)
        ov_strat = InstrumentedV8Apex(ov_cfg)
        ov_engine = BacktestEngine(
            feed=feed, strategy=ov_strat, cost=cost,
            initial_cash=INITIAL_CASH, warmup_days=WARMUP_DAYS,
        )
        ov_result = ov_engine.run()
        ov_kpis = extract_kpis(ov_result)
        all_kpis[f"overlay_{scenario}"] = ov_kpis

        ov_cascade = compute_cascade_rates(ov_strat.signal_log, report_start_ms)
        cascade_data[f"overlay_{scenario}"] = ov_cascade

        # Count overlay blocks
        if scenario == "harsh":
            overlay_block_count = sum(
                1 for e in ov_strat.signal_log
                if e["event_type"] == "entry_blocked"
                and e["reason"] == "cooldown_after_emergency_dd"
                and e["bar_ts_ms"] >= report_start_ms
            )

            # Blocked trades analysis (from baseline events)
            blocked = identify_blocked_trades_from_log(
                bl_strat.signal_log, bl_result.trades, report_start_ms,
            )
            blocked_stats = compute_blocked_stats(blocked, bl_kpis["trades"])

        print(f"    Trades: {ov_kpis['trades']}, CAGR: {ov_kpis.get('cagr_pct', 0):.2f}%, "
              f"Score: {ov_kpis['score']:.2f}, ED: {ov_kpis['emergency_dd_count']}")
        print(f"    Cascade ≤3: {ov_cascade['cascade_rate_3']:.1f}%, "
              f"≤6: {ov_cascade['cascade_rate_6']:.1f}%")

        # Delta
        score_d = ov_kpis["score"] - bl_kpis["score"]
        ed_d = ov_kpis["emergency_dd_count"] - bl_kpis["emergency_dd_count"]
        print(f"    Delta: score {score_d:+.2f}, ED {ed_d:+d}")

    # ── Blocked trades summary ──
    print(f"\n{'='*60}")
    print(f"  Blocked-Trade Analysis (holdout, harsh)")
    print(f"{'='*60}")
    print(f"  Blocked: {blocked_stats.get('n_blocked', 0)} / {blocked_stats.get('n_total_baseline', 0)}")
    print(f"  Mean PnL:   ${blocked_stats.get('mean_net_pnl', 0):+,.2f}")
    print(f"  Median PnL: ${blocked_stats.get('median_net_pnl', 0):+,.2f}")
    print(f"  ED again %: {blocked_stats.get('pct_exit_emergency_dd', 0):.1f}%")
    print(f"  Total fees: ${blocked_stats.get('total_fees', 0):,.2f}")
    print(f"  Overlay actual blocks: {overlay_block_count}")

    # ── Write CSV ──
    csv_rows = []
    for key in KPI_KEYS:
        row = {"metric": key}
        for sc in SCENARIOS_TO_RUN:
            bl_v = all_kpis.get(f"baseline_{sc}", {}).get(key)
            ov_v = all_kpis.get(f"overlay_{sc}", {}).get(key)
            row[f"baseline_{sc}"] = _fmt(bl_v)
            row[f"overlay_{sc}"] = _fmt(ov_v)
            if bl_v is not None and ov_v is not None and isinstance(bl_v, (int, float)) and isinstance(ov_v, (int, float)):
                delta = ov_v - bl_v
                pct = 100.0 * delta / abs(bl_v) if abs(bl_v) > 1e-10 else 0.0
                row[f"delta_{sc}"] = _fmt(delta)
                row[f"pct_change_{sc}"] = f"{pct:+.2f}%"
            else:
                row[f"delta_{sc}"] = ""
                row[f"pct_change_{sc}"] = ""
        csv_rows.append(row)

    # Add cascade metrics
    for sc in SCENARIOS_TO_RUN:
        bl_c = cascade_data.get(f"baseline_{sc}", {})
        ov_c = cascade_data.get(f"overlay_{sc}", {})
        for ck in ["cascade_rate_3", "cascade_rate_6"]:
            row = {"metric": ck}
            bl_v = bl_c.get(ck, 0)
            ov_v = ov_c.get(ck, 0)
            row[f"baseline_{sc}"] = bl_v
            row[f"overlay_{sc}"] = ov_v
            row[f"delta_{sc}"] = round(ov_v - bl_v, 1)
            row[f"pct_change_{sc}"] = ""
            csv_rows.append(row)

    csv_path = OUTDIR / "step8_holdout_metrics.csv"
    fieldnames = ["metric"]
    for sc in SCENARIOS_TO_RUN:
        fieldnames.extend([
            f"baseline_{sc}", f"overlay_{sc}", f"delta_{sc}", f"pct_change_{sc}",
        ])
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\n  CSV saved: {csv_path.name}")

    # ── Write Report ──
    report = build_report(all_kpis, cascade_data, blocked_stats, overlay_block_count)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "step8_holdout_overlayA.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"  Report saved: {report_path.name}")

    # ── Verification ──
    print(f"\n{'='*70}")
    print("  Verification")
    print(f"{'='*70}")

    checks = []
    bl_harsh = all_kpis["baseline_harsh"]
    ov_harsh = all_kpis["overlay_harsh"]

    # Check 1: overlay has fewer or equal trades
    checks.append((
        "overlay trades <= baseline",
        ov_harsh["trades"] <= bl_harsh["trades"],
        f"{bl_harsh['trades']} → {ov_harsh['trades']}",
    ))

    # Check 2: score degradation within threshold
    score_delta = ov_harsh["score"] - bl_harsh["score"]
    checks.append((
        f"harsh score delta > -{SCORE_DEGRADE_THRESHOLD}",
        score_delta > -SCORE_DEGRADE_THRESHOLD,
        f"{score_delta:+.2f}",
    ))

    # Check 3: MDD degradation within threshold
    mdd_delta = ov_harsh["max_drawdown_mid_pct"] - bl_harsh["max_drawdown_mid_pct"]
    checks.append((
        f"harsh MDD delta < +{MDD_DEGRADE_THRESHOLD}pp",
        mdd_delta < MDD_DEGRADE_THRESHOLD,
        f"{mdd_delta:+.2f}pp",
    ))

    # Check 4: ED count does not increase
    ed_delta = ov_harsh["emergency_dd_count"] - bl_harsh["emergency_dd_count"]
    checks.append((
        "ED count non-increasing (harsh)",
        ed_delta <= 0,
        f"{bl_harsh['emergency_dd_count']} → {ov_harsh['emergency_dd_count']}",
    ))

    all_pass = True
    for label, passed, val in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {label} → {val}")

    elapsed = time.time() - t0
    overall = "PASS" if all_pass else "FAIL"
    print(f"\nDone in {elapsed:.1f}s. Overall: {overall}")


def _fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return round(v, 4)
    return v


# ── Report Builder ───────────────────────────────────────────────────────────

def build_report(
    all_kpis: dict,
    cascade_data: dict,
    blocked_stats: dict,
    overlay_block_count: int,
) -> str:
    lines = []
    lines.append("# Step 8: Holdout Validation — Overlay A\n")
    lines.append(f"**Date:** 2026-02-24")
    lines.append(f"**Holdout period:** {HOLDOUT_START} → {HOLDOUT_END} "
                 f"(locked from V11 validation)")
    lines.append(f"**Overlay A param:** cooldown_after_emergency_dd_bars = {K}")
    lines.append("**Rule:** If overlay degrades harsh score (>5 pts) or MDD (>5pp) "
                 "on holdout → HOLD/REJECT.\n")

    bl_harsh = all_kpis["baseline_harsh"]
    ov_harsh = all_kpis["overlay_harsh"]
    bl_base = all_kpis.get("baseline_base", {})
    ov_base = all_kpis.get("overlay_base", {})

    score_delta_h = ov_harsh["score"] - bl_harsh["score"]
    mdd_delta_h = ov_harsh["max_drawdown_mid_pct"] - bl_harsh["max_drawdown_mid_pct"]
    score_delta_b = (ov_base.get("score", 0) or 0) - (bl_base.get("score", 0) or 0)

    # ── Verdict (computed first, displayed in executive summary) ──
    score_fail = score_delta_h < -SCORE_DEGRADE_THRESHOLD
    mdd_fail = mdd_delta_h > MDD_DEGRADE_THRESHOLD
    if score_fail or mdd_fail:
        verdict = "HOLD"
        verdict_reason = []
        if score_fail:
            verdict_reason.append(f"harsh score delta {score_delta_h:+.2f} exceeds -{SCORE_DEGRADE_THRESHOLD}")
        if mdd_fail:
            verdict_reason.append(f"harsh MDD delta {mdd_delta_h:+.2f}pp exceeds +{MDD_DEGRADE_THRESHOLD}pp")
        verdict_detail = "; ".join(verdict_reason)
    else:
        verdict = "PASS"
        verdict_detail = (
            f"harsh score delta {score_delta_h:+.2f} within threshold, "
            f"MDD delta {mdd_delta_h:+.2f}pp within threshold"
        )

    # ── Section 1: Executive Summary ──
    lines.append("---\n")
    lines.append("## 1. Executive Summary\n")
    lines.append(f"**Verdict: {verdict}**")
    lines.append(f"- {verdict_detail}\n")

    lines.append("| | Harsh | Base |")
    lines.append("|--|-------|------|")
    lines.append(f"| Score delta | {score_delta_h:+.2f} | {score_delta_b:+.2f} |")

    cagr_d_h = (ov_harsh.get("cagr_pct", 0) or 0) - (bl_harsh.get("cagr_pct", 0) or 0)
    cagr_d_b = (ov_base.get("cagr_pct", 0) or 0) - (bl_base.get("cagr_pct", 0) or 0)
    lines.append(f"| CAGR delta | {cagr_d_h:+.2f}pp | {cagr_d_b:+.2f}pp |")

    mdd_d_b = (ov_base.get("max_drawdown_mid_pct", 0) or 0) - (bl_base.get("max_drawdown_mid_pct", 0) or 0)
    lines.append(f"| MDD delta | {mdd_delta_h:+.2f}pp | {mdd_d_b:+.2f}pp |")

    ed_d_h = ov_harsh["emergency_dd_count"] - bl_harsh["emergency_dd_count"]
    ed_d_b = (ov_base.get("emergency_dd_count", 0) or 0) - (bl_base.get("emergency_dd_count", 0) or 0)
    lines.append(f"| ED delta | {ed_d_h:+d} | {ed_d_b:+d} |")
    lines.append("")

    # ── Section 2: KPI Comparison ──
    lines.append("---\n")
    lines.append("## 2. KPI Comparison\n")

    for sc in SCENARIOS_TO_RUN:
        bl = all_kpis[f"baseline_{sc}"]
        ov = all_kpis[f"overlay_{sc}"]

        lines.append(f"### {sc.title()} scenario\n")
        lines.append("| Metric | Baseline | Overlay A | Delta | % Change |")
        lines.append("|--------|----------|-----------|-------|----------|")

        for key in KPI_KEYS:
            bl_v = bl.get(key)
            ov_v = ov.get(key)
            if bl_v is not None and ov_v is not None:
                delta = ov_v - bl_v
                pct = 100.0 * delta / abs(bl_v) if abs(bl_v) > 1e-10 else 0.0
                lines.append(
                    f"| {key} | {_fmt(bl_v)} | {_fmt(ov_v)} | "
                    f"{_fmt(delta)} | {pct:+.2f}% |"
                )
        lines.append("")

    # ── Section 3: Cascade Metrics ──
    lines.append("---\n")
    lines.append("## 3. Cascade Metrics (Holdout)\n")

    lines.append("| | Baseline | Overlay A | Delta |")
    lines.append("|--|----------|-----------|-------|")

    for sc in SCENARIOS_TO_RUN:
        bl_c = cascade_data.get(f"baseline_{sc}", {})
        ov_c = cascade_data.get(f"overlay_{sc}", {})
        bl_ed = all_kpis[f"baseline_{sc}"]["emergency_dd_count"]
        ov_ed = all_kpis[f"overlay_{sc}"]["emergency_dd_count"]

        lines.append(f"| **{sc.title()}** | | | |")
        lines.append(f"| ED exits | {bl_ed} | {ov_ed} | {ov_ed - bl_ed:+d} |")
        lines.append(f"| Cascade ≤3 bars | {bl_c.get('cascade_rate_3', 0):.1f}% | "
                     f"{ov_c.get('cascade_rate_3', 0):.1f}% | "
                     f"{ov_c.get('cascade_rate_3', 0) - bl_c.get('cascade_rate_3', 0):+.1f}pp |")
        lines.append(f"| Cascade ≤6 bars | {bl_c.get('cascade_rate_6', 0):.1f}% | "
                     f"{ov_c.get('cascade_rate_6', 0):.1f}% | "
                     f"{ov_c.get('cascade_rate_6', 0) - bl_c.get('cascade_rate_6', 0):+.1f}pp |")
    lines.append("")

    # ── Section 4: Blocked Trades (harsh) ──
    lines.append("---\n")
    lines.append("## 4. Blocked Trades (Holdout, Harsh)\n")

    n_blocked = blocked_stats.get("n_blocked", 0)
    if n_blocked > 0:
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for k, v in blocked_stats.items():
            label = k.replace("_", " ").title()
            if isinstance(v, float):
                if "pct" in k or "pnl" in k:
                    lines.append(f"| {label} | {v:+,.2f} |")
                else:
                    lines.append(f"| {label} | {v:,.2f} |")
            else:
                lines.append(f"| {label} | {v} |")
        lines.append("")

        med_pnl = blocked_stats.get("median_net_pnl", 0)
        pct_ed = blocked_stats.get("pct_exit_emergency_dd", 0)
        lines.append(f"Overlay A blocked {overlay_block_count} entry attempts on holdout. "
                     f"The {n_blocked} blocked trades have "
                     f"{'negative' if med_pnl < 0 else 'positive'} median PnL "
                     f"(${med_pnl:+,.0f}) and {pct_ed:.0f}% exit via emergency_dd.\n")
    else:
        lines.append("No trades were blocked on the holdout period.\n")

    # ── Section 5: Verdict ──
    lines.append("---\n")
    lines.append("## 5. Verdict\n")

    lines.append(f"**{verdict}.**\n")

    if verdict == "PASS":
        lines.append(
            f"Overlay A passes out-of-sample validation on the holdout period "
            f"({HOLDOUT_START} → {HOLDOUT_END}).\n"
        )
        lines.append("Evidence:")
        lines.append(f"- Harsh score delta: {score_delta_h:+.2f} "
                     f"(threshold: >{-SCORE_DEGRADE_THRESHOLD})")
        lines.append(f"- Harsh MDD delta: {mdd_delta_h:+.2f}pp "
                     f"(threshold: <+{MDD_DEGRADE_THRESHOLD}pp)")
        lines.append(f"- ED exits: {bl_harsh['emergency_dd_count']} → "
                     f"{ov_harsh['emergency_dd_count']} ({ed_d_h:+d})")
        if n_blocked > 0:
            lines.append(f"- Blocked trades median PnL: "
                         f"${blocked_stats.get('median_net_pnl', 0):+,.0f} "
                         f"({blocked_stats.get('pct_exit_emergency_dd', 0):.0f}% ED)")
        lines.append(f"- Base scenario score delta: {score_delta_b:+.2f}")
    else:
        lines.append(
            f"Overlay A **fails** out-of-sample validation. "
            f"Do not deploy.\n"
        )
        lines.append(f"Failure reason: {verdict_detail}")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
