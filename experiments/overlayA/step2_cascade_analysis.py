#!/usr/bin/env python3
"""Step 2: Quantify the emergency_dd → re-enter → emergency_dd cascade.

Reads step1 outputs (trades + events CSVs), computes:
  1) Reentry latency distribution (bars from exit to next entry)
  2) Cascade rate at various K thresholds
  3) Expectancy of quick re-entries
  4) Fee drag from cascade trades

Outputs:
  - step2_reentry_latency.csv
  - step2_cascade_expectancy.csv
  - (reports/step2_cascade_kpis.md written separately)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTDIR = PROJECT_ROOT / "out/v10_fix_loop"
TRADES_PATH = OUTDIR / "v10_baseline_trades_harsh.csv"
EVENTS_PATH = OUTDIR / "v10_baseline_events_harsh.csv"
K_THRESHOLDS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 18, 24]


def load_data():
    with open(TRADES_PATH) as f:
        trades = list(csv.DictReader(f))
    with open(EVENTS_PATH) as f:
        events = list(csv.DictReader(f))
    return trades, events


def build_signal_index(events: list[dict]):
    """Build lookup from events: exit_signals and entry_signals with bar_index."""
    exit_signals = []
    entry_signals = []
    for e in events:
        if e["event_type"] == "exit_signal":
            exit_signals.append(e)
        elif e["event_type"] == "entry_signal":
            entry_signals.append(e)
    # Sort by bar_index
    exit_signals.sort(key=lambda e: int(e["bar_index"]))
    entry_signals.sort(key=lambda e: int(e["bar_index"]))
    return exit_signals, entry_signals


def compute_reentry_latency(trades, exit_signals, entry_signals):
    """For each emergency_dd exit, find the next entry and compute bar gap.

    Returns list of dicts with latency info for each emergency_dd exit.
    """
    # Build trade lookup by ID
    trade_by_id = {int(t["trade_id"]): t for t in trades}

    # Map exit_signal ts → bar_index for emergency_dd
    ed_exit_bars = []
    for es in exit_signals:
        if es["reason"] == "emergency_dd":
            ed_exit_bars.append({
                "bar_index": int(es["bar_index"]),
                "ts": es["ts"],
                "price": float(es["price"]),
                "regime": es["regime_d1_analytical"],
            })

    # Entry signals sorted by bar_index
    entry_bar_indices = [(int(e["bar_index"]), e) for e in entry_signals]

    rows = []
    for ed in ed_exit_bars:
        exit_bar = ed["bar_index"]

        # Find the next entry_signal AFTER this exit bar
        next_entry = None
        for bar_idx, entry_sig in entry_bar_indices:
            if bar_idx > exit_bar:
                next_entry = (bar_idx, entry_sig)
                break

        if next_entry is None:
            # Last trade, no re-entry
            rows.append({
                "exit_ts": ed["ts"],
                "exit_bar_index": exit_bar,
                "exit_price": ed["price"],
                "exit_regime": ed["regime"],
                "reentry_ts": "",
                "reentry_bar_index": "",
                "reentry_latency_bars": "",
                "reentry_reason": "",
                "reentry_regime": "",
                "next_trade_id": "",
                "next_trade_net_pnl": "",
                "next_trade_return_pct": "",
                "next_trade_exit_reason": "",
                "next_trade_fees": "",
                "next_trade_days_held": "",
                "has_reentry": False,
            })
            continue

        reentry_bar, entry_sig = next_entry
        latency = reentry_bar - exit_bar

        # Find the trade that this entry starts
        # The entry_signal ts should match a trade's entry_ts (approx)
        # Actually match by: find trade with entry_ts closest to entry_signal ts
        entry_ts = entry_sig["ts"]
        matched_trade = None
        for t in trades:
            # Entry fill happens 1 bar after signal, so entry_ts ≈ signal_ts + 4h
            # But we can match by looking at trade entry_ts being just after entry_signal ts
            if t["entry_ts"] >= entry_ts:
                matched_trade = t
                break

        rows.append({
            "exit_ts": ed["ts"],
            "exit_bar_index": exit_bar,
            "exit_price": ed["price"],
            "exit_regime": ed["regime"],
            "reentry_ts": entry_sig["ts"],
            "reentry_bar_index": reentry_bar,
            "reentry_latency_bars": latency,
            "reentry_reason": entry_sig["reason"],
            "reentry_regime": entry_sig.get("regime_d1_analytical", ""),
            "next_trade_id": matched_trade["trade_id"] if matched_trade else "",
            "next_trade_net_pnl": matched_trade["net_pnl"] if matched_trade else "",
            "next_trade_return_pct": matched_trade["return_pct"] if matched_trade else "",
            "next_trade_exit_reason": matched_trade["exit_reason"] if matched_trade else "",
            "next_trade_fees": matched_trade["fees_total"] if matched_trade else "",
            "next_trade_days_held": matched_trade["days_held"] if matched_trade else "",
            "has_reentry": True,
        })

    return rows


def compute_cascade_metrics(latency_rows, trades):
    """Compute cascade rate, expectancy, and fee drag at various K thresholds."""
    # Filter to rows with reentry
    with_reentry = [r for r in latency_rows if r["has_reentry"]]
    n_ed = len(latency_rows)
    n_with_reentry = len(with_reentry)

    latencies = [r["reentry_latency_bars"] for r in with_reentry]

    # ── Latency distribution ──
    if latencies:
        lat_arr = np.array(latencies, dtype=float)
        latency_stats = {
            "n_emergency_dd": n_ed,
            "n_with_reentry": n_with_reentry,
            "n_no_reentry": n_ed - n_with_reentry,
            "min": int(np.min(lat_arr)),
            "p25": int(np.percentile(lat_arr, 25)),
            "median": int(np.median(lat_arr)),
            "p75": int(np.percentile(lat_arr, 75)),
            "p90": int(np.percentile(lat_arr, 90)),
            "max": int(np.max(lat_arr)),
            "mean": round(float(np.mean(lat_arr)), 1),
        }
    else:
        latency_stats = {"n_emergency_dd": n_ed, "n_with_reentry": 0}

    # ── Cascade metrics per K ──
    total_fees = sum(float(t["fees_total"]) for t in trades)
    total_net_pnl = sum(float(t["net_pnl"]) for t in trades)

    cascade_rows = []
    for k in K_THRESHOLDS:
        # Trades that re-entered within K bars after emergency_dd
        quick = [r for r in with_reentry if r["reentry_latency_bars"] <= k]
        n_quick = len(quick)
        cascade_rate = round(100.0 * n_quick / n_ed, 1) if n_ed > 0 else 0.0

        if n_quick > 0:
            pnls = np.array([float(r["next_trade_net_pnl"]) for r in quick])
            returns = np.array([float(r["next_trade_return_pct"]) for r in quick])
            fees = np.array([float(r["next_trade_fees"]) for r in quick])
            exit_reasons = [r["next_trade_exit_reason"] for r in quick]
            n_ed_again = sum(1 for x in exit_reasons if x == "emergency_dd")

            cascade_rows.append({
                "K_threshold": k,
                "n_quick_reentries": n_quick,
                "cascade_rate_pct": cascade_rate,
                # Expectancy
                "mean_net_pnl": round(float(np.mean(pnls)), 2),
                "median_net_pnl": round(float(np.median(pnls)), 2),
                "p10_net_pnl": round(float(np.percentile(pnls, 10)), 2),
                "p5_net_pnl": round(float(np.percentile(pnls, 5)), 2),
                "mean_return_pct": round(float(np.mean(returns)), 4),
                "median_return_pct": round(float(np.median(returns)), 4),
                "total_net_pnl": round(float(np.sum(pnls)), 2),
                # Re-emergency rate
                "n_exit_emergency_dd_again": n_ed_again,
                "pct_emergency_dd_again": round(100.0 * n_ed_again / n_quick, 1),
                # Fee drag
                "cascade_fees_total": round(float(np.sum(fees)), 2),
                "cascade_fees_pct_of_total": round(
                    100.0 * float(np.sum(fees)) / total_fees, 1
                ) if total_fees > 0 else 0.0,
                # Context
                "mean_days_held": round(float(np.mean(
                    [float(r["next_trade_days_held"]) for r in quick]
                )), 1),
                "exit_reasons": dict(
                    zip(*np.unique(exit_reasons, return_counts=True))
                ),
            })
        else:
            cascade_rows.append({
                "K_threshold": k,
                "n_quick_reentries": 0,
                "cascade_rate_pct": 0.0,
                "mean_net_pnl": 0.0,
                "median_net_pnl": 0.0,
                "p10_net_pnl": 0.0,
                "p5_net_pnl": 0.0,
                "mean_return_pct": 0.0,
                "median_return_pct": 0.0,
                "total_net_pnl": 0.0,
                "n_exit_emergency_dd_again": 0,
                "pct_emergency_dd_again": 0.0,
                "cascade_fees_total": 0.0,
                "cascade_fees_pct_of_total": 0.0,
                "mean_days_held": 0.0,
                "exit_reasons": {},
            })

    return latency_stats, cascade_rows, total_fees, total_net_pnl


def main():
    print("Loading step1 data...")
    trades, events = load_data()
    exit_signals, entry_signals = build_signal_index(events)

    print(f"  Trades: {len(trades)}, Events: {len(events)}")
    print(f"  Exit signals: {len(exit_signals)}, Entry signals: {len(entry_signals)}")

    # ── 1. Reentry latency ──
    print("\nComputing reentry latency...")
    latency_rows = compute_reentry_latency(trades, exit_signals, entry_signals)

    latency_csv_cols = [
        "exit_ts", "exit_bar_index", "exit_price", "exit_regime",
        "reentry_ts", "reentry_bar_index", "reentry_latency_bars",
        "reentry_reason", "reentry_regime",
        "next_trade_id", "next_trade_net_pnl", "next_trade_return_pct",
        "next_trade_exit_reason", "next_trade_fees", "next_trade_days_held",
    ]
    lat_path = OUTDIR / "step2_reentry_latency.csv"
    with open(lat_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=latency_csv_cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(latency_rows)
    print(f"  Written: {lat_path.name} ({len(latency_rows)} rows)")

    # ── 2-4. Cascade metrics ──
    print("Computing cascade metrics...")
    latency_stats, cascade_rows, total_fees, total_net_pnl = compute_cascade_metrics(
        latency_rows, trades
    )

    cascade_csv_cols = [
        "K_threshold", "n_quick_reentries", "cascade_rate_pct",
        "mean_net_pnl", "median_net_pnl", "p10_net_pnl", "p5_net_pnl",
        "mean_return_pct", "median_return_pct", "total_net_pnl",
        "n_exit_emergency_dd_again", "pct_emergency_dd_again",
        "cascade_fees_total", "cascade_fees_pct_of_total",
        "mean_days_held",
    ]
    casc_path = OUTDIR / "step2_cascade_expectancy.csv"
    with open(casc_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cascade_csv_cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cascade_rows)
    print(f"  Written: {casc_path.name} ({len(cascade_rows)} rows)")

    # ── Print summary ──
    print(f"\n{'='*60}")
    print("  REENTRY LATENCY DISTRIBUTION")
    print(f"{'='*60}")
    for k, v in latency_stats.items():
        print(f"  {k}: {v}")

    print(f"\n{'='*60}")
    print("  CASCADE METRICS BY K")
    print(f"{'='*60}")
    print(f"  {'K':>3} {'N':>4} {'Rate%':>7} {'MeanPnL':>10} {'MedPnL':>10} "
          f"{'P10':>10} {'ED%':>6} {'Fees':>8} {'Fee%':>6}")
    for c in cascade_rows:
        print(f"  {c['K_threshold']:>3} {c['n_quick_reentries']:>4} "
              f"{c['cascade_rate_pct']:>6.1f}% "
              f"${c['mean_net_pnl']:>+9,.0f} "
              f"${c['median_net_pnl']:>+9,.0f} "
              f"${c['p10_net_pnl']:>+9,.0f} "
              f"{c['pct_emergency_dd_again']:>5.1f}% "
              f"${c['cascade_fees_total']:>7,.0f} "
              f"{c['cascade_fees_pct_of_total']:>5.1f}%")

    print(f"\n  Total strategy fees: ${total_fees:,.2f}")
    print(f"  Total strategy net PnL: ${total_net_pnl:,.2f}")

    # ── Non-emergency_dd comparison (baseline) ──
    print(f"\n{'='*60}")
    print("  BASELINE COMPARISON")
    print(f"{'='*60}")
    ed_trades = [t for t in trades if t["exit_reason"] == "emergency_dd"]
    non_ed = [t for t in trades if t["exit_reason"] != "emergency_dd"]
    ed_pnls = [float(t["net_pnl"]) for t in ed_trades]
    non_ed_pnls = [float(t["net_pnl"]) for t in non_ed]
    print(f"  emergency_dd trades (N={len(ed_trades)}):")
    print(f"    mean PnL: ${np.mean(ed_pnls):+,.2f}")
    print(f"    median PnL: ${np.median(ed_pnls):+,.2f}")
    print(f"    total PnL: ${np.sum(ed_pnls):+,.2f}")
    print(f"    total fees: ${sum(float(t['fees_total']) for t in ed_trades):,.2f}")
    print(f"  non-emergency_dd trades (N={len(non_ed)}):")
    print(f"    mean PnL: ${np.mean(non_ed_pnls):+,.2f}")
    print(f"    median PnL: ${np.median(non_ed_pnls):+,.2f}")
    print(f"    total PnL: ${np.sum(non_ed_pnls):+,.2f}")
    print(f"    total fees: ${sum(float(t['fees_total']) for t in non_ed):,.2f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
