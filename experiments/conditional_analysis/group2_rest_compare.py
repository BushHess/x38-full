#!/usr/bin/env python3
"""Group 2: complement-time performance comparison (all bars NOT in cascade episodes).

Runs baseline (cooldown=0) and overlayA (cooldown=12) backtests, masks out
cascade episode windows, and compares performance on the remaining time.

Also identifies "blocked trades" — baseline-only trades in Group 2 that
overlayA does not take, due to residual cooldown spillover from cascade
episode boundaries.

Outputs:
  - out_overlayA_conditional/group2_rest_compare_full.csv
  - out_overlayA_conditional/group2_rest_compare_holdout.csv
  - out_overlayA_conditional/group2_blocked_trades_full.csv
  - out_overlayA_conditional/group2_blocked_trades_holdout.csv

Usage:
  python experiments/conditional_analysis/group2_rest_compare.py
"""

import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, Fill, Trade
from experiments.overlayA.step1_export import InstrumentedV8Apex
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

# ── Constants ────────────────────────────────────────────────────────────────

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
SCENARIO = "harsh"
K = 12  # OverlayA cooldown bars

OUTDIR = PROJECT_ROOT / "out/overlayA_conditional"
HOLDOUT_START_MS = 1727740800000  # 2024-10-01 00:00 UTC

ENTRY_TS_MATCH_TOL_MS = 14_400_000  # 4h tolerance for trade matching


# ── Helpers ──────────────────────────────────────────────────────────────────

def ms_to_date(ms: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def load_labeled_episodes(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row["episode_id"] = int(row["episode_id"])
            row["peak_ts"] = int(row["peak_ts"])
            row["end_ts"] = int(row["end_ts"])
            row["is_cascade"] = row["is_cascade"] == "True"
            rows.append(row)
    return rows


# ── Backtest runners ─────────────────────────────────────────────────────────

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


# ── Group 2 mask ─────────────────────────────────────────────────────────────

def build_cascade_mask(episodes: list[dict]) -> list[tuple[int, int]]:
    """Return sorted list of (start_ms, end_ms) for cascade episode windows."""
    windows = []
    for ep in episodes:
        if ep["is_cascade"]:
            windows.append((ep["peak_ts"], ep["end_ts"]))
    windows.sort()
    return windows


def ts_in_cascade(ts_ms: int, windows: list[tuple[int, int]]) -> bool:
    """Check if timestamp falls inside any cascade window."""
    for start, end in windows:
        if start <= ts_ms <= end:
            return True
    return False


# ── Per-group equity metrics ─────────────────────────────────────────────────

def group2_equity_metrics(equity, cascade_windows):
    """Compute PnL, return, MDD for bars NOT in cascade windows."""
    # Group 2 bars
    g2_bars = [s for s in equity
               if not ts_in_cascade(s.close_time, cascade_windows)]

    if len(g2_bars) < 2:
        return {}

    navs = np.array([s.nav_mid for s in g2_bars])

    # PnL: total NAV change across Group 2 segments
    # Each contiguous segment contributes NAV(end_of_seg) - NAV(start_of_seg).
    # Simpler: sum of bar-to-bar changes within Group 2 only.
    bar_changes = np.diff(navs)
    total_pnl = float(np.sum(bar_changes))

    # Return relative to NAV at first Group 2 bar
    first_nav = navs[0]
    last_nav = navs[-1]
    total_return_pct = (last_nav - first_nav) / first_nav * 100 if first_nav > 0 else 0.0

    # MDD across Group 2 bars (treating all segments as contiguous for peak tracking)
    running_peak = np.maximum.accumulate(navs)
    dd = (running_peak - navs) / np.where(running_peak > 0, running_peak, 1.0)
    mdd_pct = float(np.max(dd)) * 100

    return {
        "n_bars": len(g2_bars),
        "first_nav": round(first_nav, 2),
        "last_nav": round(last_nav, 2),
        "pnl": round(total_pnl, 2),
        "return_pct": round(total_return_pct, 2),
        "mdd_pct": round(mdd_pct, 2),
    }


def group2_trade_metrics(trades, fills, cascade_windows):
    """Compute trade-level stats for trades with exit_ts in Group 2."""
    g2_trades = [t for t in trades
                 if not ts_in_cascade(t.exit_ts_ms, cascade_windows)]
    g2_fills = [f for f in fills
                if not ts_in_cascade(f.ts_ms, cascade_windows)]

    n = len(g2_trades)
    n_emergency_dd = sum(1 for t in g2_trades if t.exit_reason == "emergency_dd")
    total_pnl = sum(t.pnl for t in g2_trades)
    wins = sum(1 for t in g2_trades if t.pnl > 0)
    total_fees = sum(f.fee for f in g2_fills)
    total_turnover = sum(f.notional for f in g2_fills)

    return {
        "n_trades": n,
        "wins": wins,
        "win_rate_pct": round(wins / n * 100, 2) if n > 0 else 0.0,
        "n_emergency_dd": n_emergency_dd,
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / n, 2) if n > 0 else 0.0,
        "total_fees": round(total_fees, 2),
        "total_turnover": round(total_turnover, 2),
    }


# ── Blocked-trade identification ─────────────────────────────────────────────

def identify_blocked_trades(
    bl_trades: list[Trade],
    ov_trades: list[Trade],
    cascade_windows: list[tuple[int, int]],
    signal_log: list[dict],
) -> list[dict]:
    """Find baseline-only trades in Group 2 not present in overlayA.

    Strategy: a baseline trade is "blocked" if:
      1. Its exit_ts falls in Group 2 (not in cascade window), AND
      2. No overlayA trade has entry_ts within ±1 bar (4h) of its entry_ts.

    We further annotate whether the block was due to cooldown using the signal log.
    """
    # Baseline trades in Group 2
    bl_g2 = [t for t in bl_trades
             if not ts_in_cascade(t.exit_ts_ms, cascade_windows)]

    # OverlayA entry timestamps for matching
    ov_entry_set = set()
    for t in ov_trades:
        ov_entry_set.add(t.entry_ts_ms)

    # Cooldown-blocked bars from signal log (in Group 2)
    cooldown_block_bars_ms = set()
    for e in signal_log:
        if (e["event_type"] == "entry_blocked"
                and e["reason"] == "cooldown_after_emergency_dd"
                and not ts_in_cascade(e["bar_ts_ms"], cascade_windows)):
            cooldown_block_bars_ms.add(e["bar_ts_ms"])

    blocked = []
    for t in bl_g2:
        # Check if overlayA has a trade entering at the same time
        matched = any(
            abs(t.entry_ts_ms - ov_ts) <= ENTRY_TS_MATCH_TOL_MS
            for ov_ts in ov_entry_set
        )
        if not matched:
            # Determine if cooldown was the reason
            is_cooldown_block = any(
                abs(t.entry_ts_ms - block_ts) <= ENTRY_TS_MATCH_TOL_MS
                for block_ts in cooldown_block_bars_ms
            )
            blocked.append({
                "trade_id": t.trade_id,
                "entry_ts_ms": t.entry_ts_ms,
                "exit_ts_ms": t.exit_ts_ms,
                "entry_date": ms_to_date(t.entry_ts_ms),
                "exit_date": ms_to_date(t.exit_ts_ms),
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "pnl": round(t.pnl, 2),
                "return_pct": round(t.return_pct, 2),
                "days_held": round(t.days_held, 2),
                "entry_reason": t.entry_reason,
                "exit_reason": t.exit_reason,
                "cooldown_blocked": is_cooldown_block,
            })

    return blocked


def blocked_trade_stats(blocked: list[dict]) -> dict:
    """Compute summary stats for blocked trades."""
    if not blocked:
        return {
            "n_blocked": 0, "n_cooldown_blocked": 0,
            "total_pnl": 0, "mean_pnl": 0, "median_pnl": 0,
            "p10_pnl": 0, "blocked_positive_pnl": 0,
            "blocked_negative_pnl": 0, "pct_exit_emergency_dd": 0,
        }

    pnls = np.array([t["pnl"] for t in blocked])
    n_cd = sum(1 for t in blocked if t["cooldown_blocked"])
    n_emdd = sum(1 for t in blocked if t["exit_reason"] == "emergency_dd")

    return {
        "n_blocked": len(blocked),
        "n_cooldown_blocked": n_cd,
        "total_pnl": round(float(np.sum(pnls)), 2),
        "mean_pnl": round(float(np.mean(pnls)), 2),
        "median_pnl": round(float(np.median(pnls)), 2),
        "p10_pnl": round(float(np.percentile(pnls, 10)), 2),
        "blocked_positive_pnl": round(float(np.sum(pnls[pnls > 0])), 2),
        "blocked_negative_pnl": round(float(np.sum(pnls[pnls < 0])), 2),
        "pct_exit_emergency_dd": round(n_emdd / len(blocked) * 100, 1),
    }


# ── CSV writers ──────────────────────────────────────────────────────────────

COMPARE_FIELDS = [
    "variant", "n_bars",
    "equity_first_nav", "equity_last_nav",
    "equity_pnl", "equity_return_pct", "equity_mdd_pct",
    "n_trades", "wins", "win_rate_pct",
    "n_emergency_dd", "trade_total_pnl", "trade_avg_pnl",
    "total_fees", "total_turnover",
]

BLOCKED_FIELDS = [
    "trade_id", "entry_date", "exit_date",
    "entry_price", "exit_price",
    "pnl", "return_pct", "days_held",
    "entry_reason", "exit_reason", "cooldown_blocked",
]


def write_compare_csv(bl_eq, bl_tr, ov_eq, ov_tr, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"variant": "baseline", **{f"equity_{k}" if k in ("first_nav", "last_nav", "pnl", "return_pct", "mdd_pct") else k: v
          for k, v in {**bl_eq, **bl_tr}.items()}},
        {"variant": "overlayA", **{f"equity_{k}" if k in ("first_nav", "last_nav", "pnl", "return_pct", "mdd_pct") else k: v
          for k, v in {**ov_eq, **ov_tr}.items()}},
    ]
    # Flatten properly
    flat_rows = []
    for r in rows:
        flat = {"variant": r["variant"]}
        merged = {**bl_eq, **bl_tr} if r["variant"] == "baseline" else {**ov_eq, **ov_tr}
        flat["n_bars"] = merged.get("n_bars", "")
        flat["equity_first_nav"] = merged.get("first_nav", "")
        flat["equity_last_nav"] = merged.get("last_nav", "")
        flat["equity_pnl"] = merged.get("pnl", "")
        flat["equity_return_pct"] = merged.get("return_pct", "")
        flat["equity_mdd_pct"] = merged.get("mdd_pct", "")
        flat["n_trades"] = merged.get("n_trades", "")
        flat["wins"] = merged.get("wins", "")
        flat["win_rate_pct"] = merged.get("win_rate_pct", "")
        flat["n_emergency_dd"] = merged.get("n_emergency_dd", "")
        flat["trade_total_pnl"] = merged.get("total_pnl", "")
        flat["trade_avg_pnl"] = merged.get("avg_pnl", "")
        flat["total_fees"] = merged.get("total_fees", "")
        flat["total_turnover"] = merged.get("total_turnover", "")
        flat_rows.append(flat)

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMPARE_FIELDS)
        writer.writeheader()
        writer.writerows(flat_rows)


def write_blocked_csv(blocked: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=BLOCKED_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(blocked)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 70)
    print("  GROUP 2: COMPLEMENT-TIME PERFORMANCE COMPARISON")
    print("=" * 70)
    print(f"  Scenario: {SCENARIO}")
    print(f"  Group 2 = all bars NOT in cascade episode windows")
    print()

    # Load data and run backtests
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)

    print("  Running baseline (cooldown=0)...")
    bl_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=0)
    bl_result = run_backtest(bl_cfg, feed)
    print(f"    Trades: {len(bl_result.trades)}, Final NAV: "
          f"{bl_result.summary.get('final_nav_mid', 0):.2f}")

    print(f"  Running overlayA (cooldown={K}), instrumented...")
    ov_cfg = V8ApexConfig(cooldown_after_emergency_dd_bars=K)
    ov_result, signal_log = run_instrumented(ov_cfg, feed)
    print(f"    Trades: {len(ov_result.trades)}, Final NAV: "
          f"{ov_result.summary.get('final_nav_mid', 0):.2f}")
    print()

    # Load episodes
    full_episodes = load_labeled_episodes(OUTDIR / "episodes_labeled_full.csv")
    holdout_episodes = load_labeled_episodes(OUTDIR / "episodes_labeled_holdout.csv")

    # ── Full period ─────────────────────────────────────────────────────
    cascade_windows_full = build_cascade_mask(full_episodes)
    n_cascade_full = len(cascade_windows_full)
    print(f"  Full: {n_cascade_full} cascade windows masked out")

    bl_eq_full = group2_equity_metrics(bl_result.equity, cascade_windows_full)
    ov_eq_full = group2_equity_metrics(ov_result.equity, cascade_windows_full)
    bl_tr_full = group2_trade_metrics(
        bl_result.trades, bl_result.fills, cascade_windows_full)
    ov_tr_full = group2_trade_metrics(
        ov_result.trades, ov_result.fills, cascade_windows_full)

    blocked_full = identify_blocked_trades(
        bl_result.trades, ov_result.trades, cascade_windows_full, signal_log)
    bstats_full = blocked_trade_stats(blocked_full)

    _print_section("FULL PERIOD — Group 2 (complement of cascade)",
                   bl_eq_full, ov_eq_full, bl_tr_full, ov_tr_full, bstats_full)

    write_compare_csv(bl_eq_full, bl_tr_full, ov_eq_full, ov_tr_full,
                      OUTDIR / "group2_rest_compare_full.csv")
    write_blocked_csv(blocked_full,
                      OUTDIR / "group2_blocked_trades_full.csv")
    print(f"  Saved: group2_rest_compare_full.csv, group2_blocked_trades_full.csv")

    # ── Holdout period ──────────────────────────────────────────────────
    cascade_windows_holdout = build_cascade_mask(holdout_episodes)
    n_cascade_holdout = len(cascade_windows_holdout)

    # Filter equity to holdout
    bl_eq_ho_list = [s for s in bl_result.equity if s.close_time >= HOLDOUT_START_MS]
    ov_eq_ho_list = [s for s in ov_result.equity if s.close_time >= HOLDOUT_START_MS]

    # Holdout trades/fills
    bl_trades_ho = [t for t in bl_result.trades if t.exit_ts_ms >= HOLDOUT_START_MS]
    ov_trades_ho = [t for t in ov_result.trades if t.exit_ts_ms >= HOLDOUT_START_MS]
    bl_fills_ho = [f for f in bl_result.fills if f.ts_ms >= HOLDOUT_START_MS]
    ov_fills_ho = [f for f in ov_result.fills if f.ts_ms >= HOLDOUT_START_MS]

    # Signal log for holdout
    sig_log_ho = [e for e in signal_log if e["bar_ts_ms"] >= HOLDOUT_START_MS]

    print(f"\n  Holdout: {n_cascade_holdout} cascade windows masked out")

    # Use a stub EquitySnap-like wrapper for holdout equity
    bl_eq_holdout = group2_equity_metrics(bl_eq_ho_list, cascade_windows_holdout)
    ov_eq_holdout = group2_equity_metrics(ov_eq_ho_list, cascade_windows_holdout)
    bl_tr_holdout = group2_trade_metrics(
        bl_trades_ho, bl_fills_ho, cascade_windows_holdout)
    ov_tr_holdout = group2_trade_metrics(
        ov_trades_ho, ov_fills_ho, cascade_windows_holdout)

    blocked_holdout = identify_blocked_trades(
        bl_trades_ho, ov_trades_ho, cascade_windows_holdout, sig_log_ho)
    bstats_holdout = blocked_trade_stats(blocked_holdout)

    _print_section("HOLDOUT — Group 2 (complement of cascade)",
                   bl_eq_holdout, ov_eq_holdout,
                   bl_tr_holdout, ov_tr_holdout, bstats_holdout)

    write_compare_csv(bl_eq_holdout, bl_tr_holdout, ov_eq_holdout, ov_tr_holdout,
                      OUTDIR / "group2_rest_compare_holdout.csv")
    write_blocked_csv(blocked_holdout,
                      OUTDIR / "group2_blocked_trades_holdout.csv")
    print(f"  Saved: group2_rest_compare_holdout.csv, group2_blocked_trades_holdout.csv")

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")
    print("=" * 70)


def _print_section(title, bl_eq, ov_eq, bl_tr, ov_tr, bstats):
    print(f"\n  {title}:")

    # Equity comparison
    print(f"\n    Equity (bar-level):")
    print(f"    {'':>20} {'Baseline':>14} {'OverlayA':>14} {'Delta':>14}")
    print(f"    {'-'*62}")
    for key, label in [
        ("n_bars", "Bars"),
        ("pnl", "PnL $"),
        ("return_pct", "Return %"),
        ("mdd_pct", "MDD %"),
    ]:
        bl_v = bl_eq.get(key, 0)
        ov_v = ov_eq.get(key, 0)
        delta = ov_v - bl_v if isinstance(bl_v, (int, float)) else ""
        if isinstance(bl_v, float):
            print(f"    {label:>20} {bl_v:>14,.2f} {ov_v:>14,.2f} {delta:>+14,.2f}")
        else:
            print(f"    {label:>20} {bl_v:>14} {ov_v:>14} {str(delta):>14}")

    # Trade comparison
    print(f"\n    Trades (exit in Group 2):")
    print(f"    {'':>20} {'Baseline':>14} {'OverlayA':>14} {'Delta':>14}")
    print(f"    {'-'*62}")
    for key, label in [
        ("n_trades", "Trades"),
        ("wins", "Wins"),
        ("win_rate_pct", "Win rate %"),
        ("n_emergency_dd", "EmDD exits"),
        ("total_pnl", "Total PnL $"),
        ("avg_pnl", "Avg PnL $"),
        ("total_fees", "Total fees $"),
        ("total_turnover", "Turnover $"),
    ]:
        bl_v = bl_tr.get(key, 0)
        ov_v = ov_tr.get(key, 0)
        delta = ov_v - bl_v if isinstance(bl_v, (int, float)) else ""
        if isinstance(bl_v, float):
            print(f"    {label:>20} {bl_v:>14,.2f} {ov_v:>14,.2f} {delta:>+14,.2f}")
        elif isinstance(bl_v, int):
            print(f"    {label:>20} {bl_v:>14} {ov_v:>14} {delta:>+14}")
        else:
            print(f"    {label:>20} {bl_v:>14} {ov_v:>14} {str(delta):>14}")

    # Blocked trades
    print(f"\n    Blocked trades (baseline-only in Group 2):")
    print(f"      N blocked:              {bstats['n_blocked']}")
    print(f"      N cooldown-blocked:     {bstats['n_cooldown_blocked']}")
    print(f"      Total PnL:             ${bstats['total_pnl']:>+10,.2f}")
    print(f"      Mean PnL:              ${bstats['mean_pnl']:>+10,.2f}")
    print(f"      Median PnL:            ${bstats['median_pnl']:>+10,.2f}")
    print(f"      P10 PnL:              ${bstats['p10_pnl']:>+10,.2f}")
    print(f"      Blocked positive PnL:  ${bstats['blocked_positive_pnl']:>+10,.2f}")
    print(f"      Blocked negative PnL:  ${bstats['blocked_negative_pnl']:>+10,.2f}")
    print(f"      % exit emergency_dd:   {bstats['pct_exit_emergency_dd']:.1f}%")


if __name__ == "__main__":
    main()
