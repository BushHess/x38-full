#!/usr/bin/env python3
"""P0.3 -- practical validation of X0 entry-risk scorecard."""

from __future__ import annotations

import csv
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from strategies.vtrend_x0.strategy import VTrendX0Config, VTrendX0Strategy
from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import BacktestResult, SCENARIOS, Fill, Trade
from v10.research.wfo import generate_windows

OUTDIR = Path(__file__).resolve().parent
DATA = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"

FULL_START = "2019-01-01"
FULL_END = "2026-02-20"
HOLDOUT_START = "2024-01-01"
HOLDOUT_END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
COST = SCENARIOS["harsh"]

WFO_TRAIN_MONTHS = 24
WFO_TEST_MONTHS = 6
WFO_SLIDE_MONTHS = 6
WFO_WINDOWS = 8
WFO_MIN_BUCKET_TRADES = 3

BOOTSTRAP_N = 5000
BOOTSTRAP_SEED = 1337

RISK_LEVELS = ("low_non_chop", "medium_chop", "high_chop_stretch")


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    strategy_cls: type
    config_cls: type

    def build(self, *, tagged: bool):
        cfg = self.config_cls()
        setattr(cfg, "emit_entry_risk_tag", tagged)
        return self.strategy_cls(cfg)


SPECS = (
    StrategySpec("X0", VTrendX0Strategy, VTrendX0Config),
    StrategySpec("X0_E5EXIT", VTrendX0E5ExitStrategy, VTrendX0E5ExitConfig),
)


def _ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eq(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def _parse_risk(reason: str) -> str:
    marker = "|risk="
    if marker not in reason:
        return "untagged"
    return reason.split(marker, 1)[1].strip() or "untagged"


def _run(strategy, start: str, end: str) -> BacktestResult:
    feed = DataFeed(DATA, start=start, end=end, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=COST,
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP_DAYS,
        warmup_mode="no_trade",
    )
    return engine.run()


def _compare_fills(base: list[Fill], tagged: list[Fill]) -> tuple[bool, str]:
    if len(base) != len(tagged):
        return False, f"fill_count_mismatch:{len(base)}:{len(tagged)}"
    for i, (a, b) in enumerate(zip(base, tagged, strict=False)):
        checks = (
            a.ts_ms == b.ts_ms,
            a.side == b.side,
            _eq(a.qty, b.qty),
            _eq(a.price, b.price),
            _eq(a.fee, b.fee),
            _eq(a.notional, b.notional),
        )
        if not all(checks):
            return False, f"fill_mismatch_at:{i}"
    return True, "ok"


def _compare_trades(base: list[Trade], tagged: list[Trade]) -> tuple[bool, str]:
    if len(base) != len(tagged):
        return False, f"trade_count_mismatch:{len(base)}:{len(tagged)}"
    for i, (a, b) in enumerate(zip(base, tagged, strict=False)):
        checks = (
            a.trade_id == b.trade_id,
            a.entry_ts_ms == b.entry_ts_ms,
            a.exit_ts_ms == b.exit_ts_ms,
            _eq(a.entry_price, b.entry_price),
            _eq(a.exit_price, b.exit_price),
            _eq(a.qty, b.qty),
            _eq(a.pnl, b.pnl),
            _eq(a.return_pct, b.return_pct),
            _eq(a.days_held, b.days_held),
            a.exit_reason == b.exit_reason,
        )
        if not all(checks):
            return False, f"trade_mismatch_at:{i}"
    return True, "ok"


def _compare_summary(base: dict, tagged: dict) -> tuple[bool, str]:
    keys = (
        "cagr_pct",
        "sharpe",
        "max_drawdown_mid_pct",
        "calmar",
        "trades",
        "fees_total",
        "turnover_notional",
        "fills",
        "final_nav_mid",
    )
    for key in keys:
        if key in ("trades", "fills"):
            if int(base[key]) != int(tagged[key]):
                return False, f"summary_{key}_mismatch"
            continue
        if not _eq(float(base[key]), float(tagged[key])):
            return False, f"summary_{key}_mismatch"
    return True, "ok"


def _cohort_rows(strategy_id: str, period: str, trades: list[Trade]) -> list[dict]:
    grouped: dict[str, list[Trade]] = {level: [] for level in (*RISK_LEVELS, "untagged")}
    for trade in trades:
        grouped[_parse_risk(trade.entry_reason)].append(trade)

    rows: list[dict] = []
    total = len(trades)
    for level in (*RISK_LEVELS, "untagged"):
        group = grouped[level]
        if not group:
            continue
        pnls = [float(t.pnl) for t in group]
        wins = sum(1 for pnl in pnls if pnl > 0.0)
        rows.append(
            {
                "strategy_id": strategy_id,
                "period": period,
                "risk_level": level,
                "trades": len(group),
                "share_trades": round(len(group) / max(total, 1), 6),
                "avg_pnl_usd": round(sum(pnls) / len(group), 6),
                "median_pnl_usd": round(median(pnls), 6),
                "total_pnl_usd": round(sum(pnls), 6),
                "win_rate": round(wins / len(group), 6),
            }
        )
    return rows


def _row_lookup(rows: list[dict]) -> dict[str, dict]:
    return {str(row["risk_level"]): row for row in rows}


def _bootstrap_gap(
    strategy_id: str,
    period: str,
    left_label: str,
    right_label: str,
    left: list[float],
    right: list[float],
) -> dict:
    if not left or not right:
        return {
            "strategy_id": strategy_id,
            "period": period,
            "gap_name": f"{left_label}_minus_{right_label}",
            "left_trades": len(left),
            "right_trades": len(right),
            "observed_mean_gap": None,
            "ci95_low": None,
            "ci95_high": None,
            "p_gt_0": None,
        }

    rng = random.Random(BOOTSTRAP_SEED)
    samples: list[float] = []
    for _ in range(BOOTSTRAP_N):
        left_sample = [left[rng.randrange(len(left))] for _ in range(len(left))]
        right_sample = [right[rng.randrange(len(right))] for _ in range(len(right))]
        samples.append(sum(left_sample) / len(left_sample) - sum(right_sample) / len(right_sample))
    samples.sort()
    observed = sum(left) / len(left) - sum(right) / len(right)
    return {
        "strategy_id": strategy_id,
        "period": period,
        "gap_name": f"{left_label}_minus_{right_label}",
        "left_trades": len(left),
        "right_trades": len(right),
        "observed_mean_gap": round(observed, 6),
        "ci95_low": round(samples[int(0.025 * len(samples))], 6),
        "ci95_high": round(samples[int(0.975 * len(samples))], 6),
        "p_gt_0": round(sum(1 for s in samples if s > 0.0) / len(samples), 6),
    }


def _build_bootstrap_rows(strategy_id: str, period: str, trades: list[Trade]) -> list[dict]:
    grouped: dict[str, list[float]] = {level: [] for level in (*RISK_LEVELS, "untagged")}
    for trade in trades:
        grouped[_parse_risk(trade.entry_reason)].append(float(trade.pnl))
    return [
        _bootstrap_gap(strategy_id, period, "low_non_chop", "high_chop_stretch", grouped["low_non_chop"], grouped["high_chop_stretch"]),
        _bootstrap_gap(strategy_id, period, "medium_chop", "high_chop_stretch", grouped["medium_chop"], grouped["high_chop_stretch"]),
    ]


def _wfo_windows() -> list:
    windows = generate_windows(
        FULL_START,
        FULL_END,
        train_months=WFO_TRAIN_MONTHS,
        test_months=WFO_TEST_MONTHS,
        slide_months=WFO_SLIDE_MONTHS,
    )
    return windows[-WFO_WINDOWS:]


def _wfo_rows(spec: StrategySpec) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    eligible = 0
    pnl_order_wins = 0
    win_rate_order_wins = 0
    both_order_wins = 0

    for window in _wfo_windows():
        result = _run(spec.build(tagged=True), window.test_start, window.test_end)
        cohort_rows = _cohort_rows(spec.strategy_id, f"wfo_{window.window_id}", result.trades)
        lookup = _row_lookup(cohort_rows)
        low = lookup.get("low_non_chop")
        high = lookup.get("high_chop_stretch")

        eligible_window = bool(
            low is not None
            and high is not None
            and int(low["trades"]) >= WFO_MIN_BUCKET_TRADES
            and int(high["trades"]) >= WFO_MIN_BUCKET_TRADES
        )
        pnl_order_pass = False
        win_rate_order_pass = False
        both_order_pass = False
        if eligible_window:
            eligible += 1
            pnl_order_pass = float(high["avg_pnl_usd"]) < float(low["avg_pnl_usd"])
            win_rate_order_pass = float(high["win_rate"]) < float(low["win_rate"])
            both_order_pass = pnl_order_pass and win_rate_order_pass
            pnl_order_wins += int(pnl_order_pass)
            win_rate_order_wins += int(win_rate_order_pass)
            both_order_wins += int(both_order_pass)

        rows.append(
            {
                "strategy_id": spec.strategy_id,
                "window_id": window.window_id,
                "test_start": window.test_start,
                "test_end": window.test_end,
                "low_trades": int(low["trades"]) if low else 0,
                "low_avg_pnl_usd": float(low["avg_pnl_usd"]) if low else None,
                "low_win_rate": float(low["win_rate"]) if low else None,
                "high_trades": int(high["trades"]) if high else 0,
                "high_avg_pnl_usd": float(high["avg_pnl_usd"]) if high else None,
                "high_win_rate": float(high["win_rate"]) if high else None,
                "eligible": eligible_window,
                "pnl_order_pass": pnl_order_pass,
                "win_rate_order_pass": win_rate_order_pass,
                "both_order_pass": both_order_pass,
            }
        )

    summary = {
        "strategy_id": spec.strategy_id,
        "eligible_windows": eligible,
        "total_windows": len(rows),
        "pnl_order_pass_rate": round(pnl_order_wins / eligible, 6) if eligible else None,
        "win_rate_order_pass_rate": round(win_rate_order_wins / eligible, 6) if eligible else None,
        "both_order_pass_rate": round(both_order_wins / eligible, 6) if eligible else None,
    }
    return rows, summary


def _decision(per_strategy: dict[str, dict]) -> dict:
    x0 = per_strategy["X0"]
    x0e5 = per_strategy["X0_E5EXIT"]

    x0_holdout_gap = x0["bootstrap"]["holdout"]["low_non_chop_minus_high_chop_stretch"]
    x0e5_holdout_gap = x0e5["bootstrap"]["holdout"]["low_non_chop_minus_high_chop_stretch"]

    x0_full = x0["cohorts"]["full"]
    x0_hold = x0["cohorts"]["holdout"]
    x0e5_full = x0e5["cohorts"]["full"]
    x0e5_hold = x0e5["cohorts"]["holdout"]

    x0_gate_ok = (
        x0["parity_pass"]
        and x0_full["high_avg_pnl_usd"] < 0.0
        and x0_hold["high_avg_pnl_usd"] < 0.0
        and x0_holdout_gap["ci95_low"] is not None
        and x0_holdout_gap["ci95_low"] > 0.0
        and x0["wfo"]["both_order_pass_rate"] is not None
        and x0["wfo"]["both_order_pass_rate"] >= 0.6
    )
    x0e5_warning_ok = (
        x0e5["parity_pass"]
        and x0e5_full["high_avg_pnl_usd"] < x0e5_full["low_avg_pnl_usd"]
        and x0e5_hold["high_avg_pnl_usd"] < x0e5_hold["low_avg_pnl_usd"]
    )
    x0e5_gate_ok = (
        x0e5_warning_ok
        and x0e5_hold["high_avg_pnl_usd"] < 0.0
        and x0e5_holdout_gap["ci95_low"] is not None
        and x0e5_holdout_gap["ci95_low"] > 0.0
        and x0e5["wfo"]["both_order_pass_rate"] is not None
        and x0e5["wfo"]["both_order_pass_rate"] >= 0.6
    )

    if not x0["parity_pass"] or not x0e5["parity_pass"]:
        verdict = "kill"
        rationale = "parity_failed"
    elif x0e5_gate_ok:
        verdict = "hard_gate_x0e5"
        rationale = "x0_e5exit_gate_is_stable"
    elif x0_gate_ok:
        verdict = "hard_gate_x0_only"
        rationale = "x0_gate_is_stable_but_x0_e5exit_is_not"
    elif x0e5_warning_ok:
        verdict = "warning_only"
        rationale = "risk_bucket_is_real_but_not_clean_enough_for_default_gate"
    else:
        verdict = "kill"
        rationale = "cohort_ordering_not_stable_enough"

    return {
        "verdict": verdict,
        "rationale": rationale,
        "need_full_47_stack_now": False,
        "full_47_stack_trigger": "only_if_promoting_a_new_gated_strategy",
    }


def _strategy_summary_from_rows(rows: list[dict]) -> dict[str, float | None]:
    lookup = _row_lookup(rows)
    low = lookup.get("low_non_chop")
    med = lookup.get("medium_chop")
    high = lookup.get("high_chop_stretch")
    return {
        "low_trades": int(low["trades"]) if low else 0,
        "low_avg_pnl_usd": float(low["avg_pnl_usd"]) if low else None,
        "low_win_rate": float(low["win_rate"]) if low else None,
        "medium_trades": int(med["trades"]) if med else 0,
        "medium_avg_pnl_usd": float(med["avg_pnl_usd"]) if med else None,
        "medium_win_rate": float(med["win_rate"]) if med else None,
        "high_trades": int(high["trades"]) if high else 0,
        "high_avg_pnl_usd": float(high["avg_pnl_usd"]) if high else None,
        "high_win_rate": float(high["win_rate"]) if high else None,
    }


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_report(
    elapsed: float,
    parity_rows: list[dict],
    cohort_rows: list[dict],
    bootstrap_rows: list[dict],
    wfo_summary_rows: list[dict],
    decision: dict,
) -> str:
    lines = [
        "# P0.3 Entry Risk Scorecard Validation",
        "",
        "## Verdict",
        "",
        f"- `{decision['verdict'].upper()}`",
        f"- Rationale: `{decision['rationale']}`",
        f"- Elapsed: `{elapsed:.2f}s`",
        f"- Need full 47-technique stack now: `{decision['need_full_47_stack_now']}`",
        f"- Trigger for full stack: `{decision['full_47_stack_trigger']}`",
        "",
        "## Parity",
        "",
    ]
    for row in parity_rows:
        lines.append(
            f"- `{row['strategy_id']}`: fills={row['fills_parity']}, trades={row['trades_parity']}, "
            f"summary={row['summary_parity']}"
        )

    lines.extend(["", "## Cohort Tables", ""])
    for strategy_id in ("X0", "X0_E5EXIT"):
        for period in ("full", "holdout"):
            lines.append(f"### {strategy_id} / {period}")
            lines.append("")
            lines.append("| Risk | Trades | Share | Avg pnl | Median pnl | Total pnl | Win rate |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|")
            for row in cohort_rows:
                if row["strategy_id"] != strategy_id or row["period"] != period:
                    continue
                lines.append(
                    f"| {row['risk_level']} | {row['trades']} | {row['share_trades']:.6f} | "
                    f"{row['avg_pnl_usd']:.6f} | {row['median_pnl_usd']:.6f} | "
                    f"{row['total_pnl_usd']:.6f} | {row['win_rate']:.6f} |"
                )
            lines.append("")

    lines.extend(["## Bootstrap Gaps", ""])
    lines.append("| Strategy | Period | Gap | Left N | Right N | Observed | CI95 Low | CI95 High | p(>0) |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for row in bootstrap_rows:
        lines.append(
            f"| {row['strategy_id']} | {row['period']} | {row['gap_name']} | "
            f"{row['left_trades']} | {row['right_trades']} | "
            f"{row['observed_mean_gap']} | {row['ci95_low']} | {row['ci95_high']} | {row['p_gt_0']} |"
        )

    lines.extend(["", "## WFO Summary", ""])
    lines.append("| Strategy | Eligible windows | Total windows | PnL order pass | Win-rate order pass | Both pass |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in wfo_summary_rows:
        lines.append(
            f"| {row['strategy_id']} | {row['eligible_windows']} | {row['total_windows']} | "
            f"{row['pnl_order_pass_rate']} | {row['win_rate_order_pass_rate']} | {row['both_order_pass_rate']} |"
        )

    lines.extend(
        [
            "",
            "## Final Interpretation",
            "",
            "- Running the full 47-technique stack is not necessary for the scorecard itself because this path is instrumentation plus cohort diagnostics, not a promoted trading rule.",
            "- If a gated strategy is promoted from this scorecard, that gated strategy must then go through the full validation framework.",
            "- Prior gate research still matters: `X0_CHOP_STRETCH18` improved `X0`, but `X0E5_CHOP_STRETCH18` stayed research-only after holdout/WFO review.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    start_time = time.time()

    parity_rows: list[dict] = []
    cohort_rows: list[dict] = []
    bootstrap_rows: list[dict] = []
    wfo_rows: list[dict] = []
    wfo_summary_rows: list[dict] = []
    per_strategy: dict[str, dict] = {}

    for spec in SPECS:
        baseline_res = _run(spec.build(tagged=False), FULL_START, FULL_END)
        tagged_res = _run(spec.build(tagged=True), FULL_START, FULL_END)

        fills_ok, fills_msg = _compare_fills(baseline_res.fills, tagged_res.fills)
        trades_ok, trades_msg = _compare_trades(baseline_res.trades, tagged_res.trades)
        summary_ok, summary_msg = _compare_summary(baseline_res.summary, tagged_res.summary)
        parity_rows.append(
            {
                "strategy_id": spec.strategy_id,
                "fills_parity": fills_ok,
                "fills_detail": fills_msg,
                "trades_parity": trades_ok,
                "trades_detail": trades_msg,
                "summary_parity": summary_ok,
                "summary_detail": summary_msg,
            }
        )

        full_trades = list(tagged_res.trades)
        holdout_res = _run(spec.build(tagged=True), HOLDOUT_START, HOLDOUT_END)
        holdout_trades = list(holdout_res.trades)

        full_rows = _cohort_rows(spec.strategy_id, "full", full_trades)
        holdout_rows = _cohort_rows(spec.strategy_id, "holdout", holdout_trades)
        cohort_rows.extend(full_rows)
        cohort_rows.extend(holdout_rows)

        full_boot = _build_bootstrap_rows(spec.strategy_id, "full", full_trades)
        holdout_boot = _build_bootstrap_rows(spec.strategy_id, "holdout", holdout_trades)
        bootstrap_rows.extend(full_boot)
        bootstrap_rows.extend(holdout_boot)

        window_rows, wfo_summary = _wfo_rows(spec)
        wfo_rows.extend(window_rows)
        wfo_summary_rows.append(wfo_summary)

        per_strategy[spec.strategy_id] = {
            "parity_pass": fills_ok and trades_ok and summary_ok,
            "cohorts": {
                "full": _strategy_summary_from_rows(full_rows),
                "holdout": _strategy_summary_from_rows(holdout_rows),
            },
            "bootstrap": {
                "full": {row["gap_name"]: row for row in full_boot},
                "holdout": {row["gap_name"]: row for row in holdout_boot},
            },
            "wfo": wfo_summary,
        }

    decision = _decision(per_strategy)
    elapsed = time.time() - start_time

    results = {
        "elapsed_seconds": round(elapsed, 4),
        "decision": decision,
        "per_strategy": per_strategy,
    }

    _write_csv(
        OUTDIR / "p0_3_parity_table.csv",
        parity_rows,
        [
            "strategy_id",
            "fills_parity",
            "fills_detail",
            "trades_parity",
            "trades_detail",
            "summary_parity",
            "summary_detail",
        ],
    )
    _write_csv(
        OUTDIR / "p0_3_cohort_table.csv",
        cohort_rows,
        [
            "strategy_id",
            "period",
            "risk_level",
            "trades",
            "share_trades",
            "avg_pnl_usd",
            "median_pnl_usd",
            "total_pnl_usd",
            "win_rate",
        ],
    )
    _write_csv(
        OUTDIR / "p0_3_bootstrap_table.csv",
        bootstrap_rows,
        [
            "strategy_id",
            "period",
            "gap_name",
            "left_trades",
            "right_trades",
            "observed_mean_gap",
            "ci95_low",
            "ci95_high",
            "p_gt_0",
        ],
    )
    _write_csv(
        OUTDIR / "p0_3_wfo_table.csv",
        wfo_rows,
        [
            "strategy_id",
            "window_id",
            "test_start",
            "test_end",
            "low_trades",
            "low_avg_pnl_usd",
            "low_win_rate",
            "high_trades",
            "high_avg_pnl_usd",
            "high_win_rate",
            "eligible",
            "pnl_order_pass",
            "win_rate_order_pass",
            "both_order_pass",
        ],
    )
    _write_csv(
        OUTDIR / "p0_3_wfo_summary.csv",
        wfo_summary_rows,
        [
            "strategy_id",
            "eligible_windows",
            "total_windows",
            "pnl_order_pass_rate",
            "win_rate_order_pass_rate",
            "both_order_pass_rate",
        ],
    )
    with (OUTDIR / "p0_3_results.json").open("w") as f:
        json.dump(results, f, indent=2)
    with (OUTDIR / "P0_3_VALIDATION_REPORT.md").open("w") as f:
        f.write(
            _build_report(
                elapsed=elapsed,
                parity_rows=parity_rows,
                cohort_rows=cohort_rows,
                bootstrap_rows=bootstrap_rows,
                wfo_summary_rows=wfo_summary_rows,
                decision=decision,
            )
        )

    print("Verdict:", decision["verdict"])
    for row in wfo_summary_rows:
        print(row)


if __name__ == "__main__":
    main()
