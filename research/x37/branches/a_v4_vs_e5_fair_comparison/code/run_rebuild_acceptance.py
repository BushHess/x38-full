"""Phase 2: V4 rebuild acceptance test.

Runs V4MacroHystBStrategy on full data at 20 bps RT and compares
against frozen spec values (trade count, Sharpe, CAGR, MDD, thresholds).
"""

from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

# Path setup — add both repo root and branch code dir to sys.path
_THIS_DIR = Path(__file__).resolve().parent
BRANCH_DIR = _THIS_DIR.parent
ROOT = _THIS_DIR.parents[4]  # btc-spot-dev/
for p in (str(ROOT), str(_THIS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from v4_strategy import V4MacroHystBConfig, V4MacroHystBStrategy
from helpers import (
    COST_FAIR,
    RESULTS_DIR,
    load_data_feed,
    run_backtest,
    save_json,
    trade_distribution,
)


# Frozen spec targets (from PLAN §3.4, §3.7, §3.8)
SPEC_THRESHOLDS = {
    2020: (0.01733118, 0.44456083, 0.18495011, 0.03494195),
    2021: (0.11701675, 0.59767632, 0.37280954, -0.02210511),
    2022: (0.16551381, 0.53271889, 0.27334110, -0.01170659),
    2023: (0.02476320, 0.39796868, 0.12118843, -0.00430096),
    2024: (0.07826335, 0.41624702, 0.15029781, -0.01361452),
    2025: (0.07915294, 0.43110899, 0.15856132, -0.00484446),
    2026: (0.06139221, 0.39132836, 0.12691468, -0.03080399),
}

SPEC_PERF = {
    "trades": 51,
    "sharpe": 1.8395,
    "cagr_pct": 67.1,
    "mdd_pct": 22.7,
    "win_rate": 0.588,
}

TOLERANCES = {
    "trades": 3,
    "sharpe": 0.10,
    "cagr_pct": 5.0,
    "mdd_pct": 3.0,
    "win_rate": 0.05,
    "threshold": 0.01,
    "trade_net_ret": 0.001,
}


ARCHIVED_TRADES_PATH = (
    ROOT
    / "research/x37/resource/gen1/v4_macroHystB/research/trades_new_final_flow.csv"
)


def _fmt_ms(ts_ms: int) -> str:
    return dt.datetime.fromtimestamp(
        ts_ms / 1000, tz=dt.timezone.utc,
    ).strftime("%Y-%m-%d %H:%M:%S")


def _load_archived_trades() -> list[dict]:
    rows: list[dict] = []
    with ARCHIVED_TRADES_PATH.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "entry_dt": row["entry_dt"],
                    "exit_dt": row["exit_dt"],
                    "net_ret": float(row["net_ret"]),
                    "hold_days": float(row["hold_days"]),
                },
            )
    return rows


def _compare_trade_path(trades: list) -> dict:
    archived = _load_archived_trades()
    rebuilt = [
        {
            "entry_dt": _fmt_ms(t.entry_ts_ms),
            "exit_dt": _fmt_ms(t.exit_ts_ms),
            "net_ret": t.return_pct / 100.0,
            "hold_days": t.days_held,
        }
        for t in trades
    ]

    count_match = len(rebuilt) == len(archived)
    n = min(len(rebuilt), len(archived))
    timestamp_mismatches = []
    hold_day_mismatches = []
    net_ret_deltas: list[float] = []

    for i in range(n):
        rb = rebuilt[i]
        ar = archived[i]
        if rb["entry_dt"] != ar["entry_dt"] or rb["exit_dt"] != ar["exit_dt"]:
            timestamp_mismatches.append(
                {
                    "index": i,
                    "rebuilt_entry_dt": rb["entry_dt"],
                    "archived_entry_dt": ar["entry_dt"],
                    "rebuilt_exit_dt": rb["exit_dt"],
                    "archived_exit_dt": ar["exit_dt"],
                },
            )
        if abs(rb["hold_days"] - ar["hold_days"]) > 1e-12:
            hold_day_mismatches.append(
                {
                    "index": i,
                    "rebuilt_hold_days": round(rb["hold_days"], 12),
                    "archived_hold_days": round(ar["hold_days"], 12),
                },
            )
        net_ret_deltas.append(abs(rb["net_ret"] - ar["net_ret"]))

    max_net_ret_delta = max(net_ret_deltas) if net_ret_deltas else 0.0
    net_ret_status = (
        "PASS" if max_net_ret_delta <= TOLERANCES["trade_net_ret"] else "WARN"
    )
    path_status = "PASS" if count_match and not timestamp_mismatches else "FAIL"

    return {
        "status": path_status,
        "count_match": count_match,
        "rebuilt_trade_count": len(rebuilt),
        "archived_trade_count": len(archived),
        "timestamp_mismatch_count": len(timestamp_mismatches),
        "hold_day_mismatch_count": len(hold_day_mismatches),
        "max_net_ret_delta": round(max_net_ret_delta, 12),
        "net_ret_status": net_ret_status,
        "net_ret_tolerance": TOLERANCES["trade_net_ret"],
        "timestamp_mismatches_sample": timestamp_mismatches[:10],
        "hold_day_mismatches_sample": hold_day_mismatches[:10],
    }


def run_acceptance() -> dict:
    print("=" * 70)
    print("Phase 2: V4 Rebuild Acceptance Test")
    print("=" * 70)

    # ---- Run V4 full backtest at 20 bps RT ----
    print("\n[1/3] Loading data and running V4 full backtest (2020-2026)...")
    feed = load_data_feed(start="2020-01-01", end="2026-02-20",
                          warmup_days=3000)
    print(f"  DataFeed loaded: {feed.n_h4} H4 bars, {feed.n_d1} D1 bars")

    config = V4MacroHystBConfig()
    strategy = V4MacroHystBStrategy(config)
    result = run_backtest(strategy, feed, COST_FAIR)
    summary = result.summary

    print(f"  Trades: {summary['trades']}")
    print(f"  Sharpe: {summary.get('sharpe', 'N/A')}")
    print(f"  CAGR:   {summary.get('cagr_pct', 'N/A'):.2f}%")
    print(f"  MDD:    {summary.get('max_drawdown_mid_pct', 'N/A'):.2f}%")

    # ---- Check thresholds ----
    print("\n[2/3] Checking yearly thresholds...")
    threshold_checks = []
    thr_names = ["macro_q50", "entry_q60", "hold_q50", "flow_q55"]

    for year, spec_vals in sorted(SPEC_THRESHOLDS.items()):
        computed = strategy._thresholds.get(year)
        if computed is None:
            threshold_checks.append({
                "year": year, "status": "MISSING",
                "spec": list(spec_vals), "computed": None,
            })
            print(f"  {year}: MISSING (no threshold computed)")
            continue

        deltas = [abs(c - s) for c, s in zip(computed, spec_vals)]
        max_delta = max(deltas)
        status = "PASS" if max_delta < TOLERANCES["threshold"] else "WARN"

        threshold_checks.append({
            "year": year,
            "status": status,
            "spec": {n: round(v, 8) for n, v in zip(thr_names, spec_vals)},
            "computed": {n: round(v, 8) for n, v in zip(thr_names, computed)},
            "max_delta": round(max_delta, 6),
        })
        print(f"  {year}: {status} (max delta = {max_delta:.6f})")

    # ---- Check performance metrics ----
    print("\n[3/3] Checking performance metrics...")
    perf_checks = {}
    sharpe_val = summary.get("sharpe") or 0.0
    n_trades = summary.get("trades", 0)
    cagr_val = summary.get("cagr_pct", 0.0)
    mdd_val = summary.get("max_drawdown_mid_pct", 0.0)
    wr = summary.get("win_rate_pct", 0.0) / 100.0

    checks = [
        ("trades", n_trades, SPEC_PERF["trades"], TOLERANCES["trades"]),
        ("sharpe", sharpe_val, SPEC_PERF["sharpe"], TOLERANCES["sharpe"]),
        ("cagr_pct", cagr_val, SPEC_PERF["cagr_pct"], TOLERANCES["cagr_pct"]),
        ("mdd_pct", mdd_val, SPEC_PERF["mdd_pct"], TOLERANCES["mdd_pct"]),
        ("win_rate", wr, SPEC_PERF["win_rate"], TOLERANCES["win_rate"]),
    ]

    all_pass = True
    for name, actual, target, tol in checks:
        delta = abs(actual - target)
        ok = delta <= tol
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        perf_checks[name] = {
            "actual": round(actual, 4),
            "target": target,
            "delta": round(delta, 4),
            "tolerance": tol,
            "status": status,
        }
        print(f"  {name:12s}: actual={actual:.4f}  target={target}  "
              f"delta={delta:.4f}  tol={tol}  [{status}]")

    # ---- Trade distribution ----
    tdist = trade_distribution(result.trades)
    trade_path = _compare_trade_path(result.trades)
    print("\n  Trade-path comparison vs archived trades...")
    print(
        f"    count_match={trade_path['count_match']}  "
        f"timestamp_mismatches={trade_path['timestamp_mismatch_count']}  "
        f"max_net_ret_delta={trade_path['max_net_ret_delta']:.12f}  "
        f"[{trade_path['status']}]",
    )

    # ---- Also run dev and holdout periods ----
    print("\n  Running dev period (2020-2023)...")
    feed_dev = load_data_feed(start="2020-01-01", end="2023-12-31",
                              warmup_days=3000)
    strat_dev = V4MacroHystBStrategy(V4MacroHystBConfig())
    res_dev = run_backtest(strat_dev, feed_dev, COST_FAIR)
    dev_summary = res_dev.summary
    print(f"    Dev: Sh={dev_summary.get('sharpe', 'N/A')}, "
          f"CAGR={dev_summary.get('cagr_pct', 0):.1f}%, "
          f"MDD={dev_summary.get('max_drawdown_mid_pct', 0):.1f}%, "
          f"trades={dev_summary.get('trades', 0)}")

    print("  Running holdout period (2024-2026)...")
    feed_ho = load_data_feed(start="2024-01-01", end="2026-02-20",
                             warmup_days=3000)
    strat_ho = V4MacroHystBStrategy(V4MacroHystBConfig())
    res_ho = run_backtest(strat_ho, feed_ho, COST_FAIR)
    ho_summary = res_ho.summary
    print(f"    Holdout: Sh={ho_summary.get('sharpe', 'N/A')}, "
          f"CAGR={ho_summary.get('cagr_pct', 0):.1f}%, "
          f"MDD={ho_summary.get('max_drawdown_mid_pct', 0):.1f}%, "
          f"trades={ho_summary.get('trades', 0)}")

    # ---- Overall verdict ----
    thr_all_pass = all(c["status"] == "PASS" for c in threshold_checks)
    overall = "PASS" if all_pass and thr_all_pass and trade_path["status"] == "PASS" else "WARN"

    print(f"\n{'=' * 70}")
    print(f"Acceptance Test Overall: {overall}")
    if not all_pass:
        print("  Performance checks have failures — see details above.")
    if not thr_all_pass:
        print("  Threshold checks have warnings — threshold rebuild drift detected.")
    if trade_path["status"] != "PASS":
        print("  Trade path does not match archived V4 signal path exactly.")
    print(f"{'=' * 70}")

    report = {
        "overall": overall,
        "alignment_rule": (
            "allow_exact_matches"
            if config.allow_exact_matches
            else "strict_lt"
        ),
        "cost_rt_bps": round(COST_FAIR.round_trip_bps, 1),
        "performance": perf_checks,
        "thresholds": threshold_checks,
        "trade_path": trade_path,
        "trade_distribution": tdist,
        "summary_full": {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in summary.items()
        },
        "summary_dev": {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in dev_summary.items()
        },
        "summary_holdout": {
            k: round(v, 4) if isinstance(v, float) else v
            for k, v in ho_summary.items()
        },
    }

    out_path = RESULTS_DIR / "acceptance_test.json"
    save_json(out_path, report)
    print(f"\nSaved: {out_path}")

    return report


if __name__ == "__main__":
    run_acceptance()
