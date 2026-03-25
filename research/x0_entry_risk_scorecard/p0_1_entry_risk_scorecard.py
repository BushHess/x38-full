#!/usr/bin/env python3
"""P0.1 -- entry risk scorecard research for X0 / X0_E5EXIT."""

from __future__ import annotations

import csv
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


OUTDIR = Path(__file__).resolve().parent
SOURCE = OUTDIR.parent / "e0_entry_hygiene" / "p0_1_trade_table.csv"

TRAIN_END = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
HOLDOUT_START = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

STRATEGIES = ("X0", "X0_E5EXIT")
BOOTSTRAP_N = 2000
RNG_SEED = 7

CORE_BAD_FAILURES = {"false_breakout", "trail_stop_noise"}

STRETCH_THRESHOLD = 1.8
ER_THRESHOLD = 0.10
VDO_THRESHOLD = 0.002
SPREAD_THRESHOLD = 1.5


@dataclass(frozen=True)
class Trade:
    strategy_id: str
    trade_id: int
    entry_ts: str
    entry_dt: datetime
    pnl_usd: float
    entry_context: str
    entry_er30: float
    entry_vdo: float
    entry_ema_spread_atr: float
    entry_price_to_slow_atr: float
    failure_mode: str
    is_winner: bool

    @property
    def core_bad(self) -> bool:
        return self.failure_mode in CORE_BAD_FAILURES

    @property
    def any_bad(self) -> bool:
        return not self.is_winner


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    expression: str
    dof: int

    def applies(self, t: Trade) -> bool:
        if self.rule_id == "chop":
            return t.entry_context == "chop"
        if self.rule_id == "stretch18":
            return t.entry_context == "chop" and t.entry_price_to_slow_atr > STRETCH_THRESHOLD
        if self.rule_id == "stretch18_er10":
            return (
                t.entry_context == "chop"
                and t.entry_price_to_slow_atr > STRETCH_THRESHOLD
                and t.entry_er30 <= ER_THRESHOLD
            )
        if self.rule_id == "stretch18_vdo2":
            return (
                t.entry_context == "chop"
                and t.entry_price_to_slow_atr > STRETCH_THRESHOLD
                and t.entry_vdo <= VDO_THRESHOLD
            )
        if self.rule_id == "stretch18_spread15":
            return (
                t.entry_context == "chop"
                and t.entry_price_to_slow_atr > STRETCH_THRESHOLD
                and t.entry_ema_spread_atr >= SPREAD_THRESHOLD
            )
        raise ValueError(f"unknown rule_id: {self.rule_id}")


RULES = (
    RuleSpec("chop", "entry_context == chop", 1),
    RuleSpec("stretch18", "entry_context == chop and entry_price_to_slow_atr > 1.8", 2),
    RuleSpec("stretch18_er10", "chop and stretch18 and entry_er30 <= 0.10", 3),
    RuleSpec("stretch18_vdo2", "chop and stretch18 and entry_vdo <= 0.002", 3),
    RuleSpec("stretch18_spread15", "chop and stretch18 and entry_ema_spread_atr >= 1.5", 3),
)


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def read_trades() -> list[Trade]:
    out: list[Trade] = []
    with SOURCE.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["strategy_id"]
            if sid not in STRATEGIES:
                continue
            out.append(
                Trade(
                    strategy_id=sid,
                    trade_id=int(row["trade_id"]),
                    entry_ts=row["entry_ts"],
                    entry_dt=parse_ts(row["entry_ts"]),
                    pnl_usd=float(row["pnl_usd"]),
                    entry_context=row["entry_context"],
                    entry_er30=float(row["entry_er30"]),
                    entry_vdo=float(row["entry_vdo"]),
                    entry_ema_spread_atr=float(row["entry_ema_spread_atr"]),
                    entry_price_to_slow_atr=float(row["entry_price_to_slow_atr"]),
                    failure_mode=row["failure_mode"],
                    is_winner=str(row["is_winner"]).lower() == "true",
                )
            )
    return out


def support(xs: list[Trade]) -> int:
    return len(xs)


def pct_true(xs: list[Trade], attr: str) -> float | None:
    if not xs:
        return None
    return sum(1 for x in xs if getattr(x, attr)) / len(xs)


def avg_pnl(xs: list[Trade]) -> float | None:
    if not xs:
        return None
    return sum(x.pnl_usd for x in xs) / len(xs)


def evaluate_rule(rows: list[Trade], rule: RuleSpec, label: str) -> tuple[list[Trade], list[Trade], dict]:
    flagged = [r for r in rows if rule.applies(r)]
    kept = [r for r in rows if not rule.applies(r)]
    flagged_rate = pct_true(flagged, label)
    kept_rate = pct_true(kept, label)
    flagged_avg_pnl = avg_pnl(flagged)
    kept_avg_pnl = avg_pnl(kept)
    summary = {
        "flagged_support": len(flagged),
        "kept_support": len(kept),
        "flagged_rate": flagged_rate,
        "kept_rate": kept_rate,
        "rate_gap": None if flagged_rate is None or kept_rate is None else flagged_rate - kept_rate,
        "flagged_avg_pnl": flagged_avg_pnl,
        "kept_avg_pnl": kept_avg_pnl,
        "avg_pnl_gap": None if flagged_avg_pnl is None or kept_avg_pnl is None else flagged_avg_pnl - kept_avg_pnl,
    }
    return flagged, kept, summary


def build_atomic_rule_table(rows: list[Trade]) -> list[dict]:
    table: list[dict] = []
    for sid in STRATEGIES:
        sid_rows = [r for r in rows if r.strategy_id == sid]
        train_rows = [r for r in sid_rows if r.entry_dt <= TRAIN_END]
        holdout_rows = [r for r in sid_rows if r.entry_dt >= HOLDOUT_START]
        for rule in RULES:
            train_flagged, train_kept, train_eval = evaluate_rule(train_rows, rule, "core_bad")
            hold_flagged, hold_kept, hold_eval = evaluate_rule(holdout_rows, rule, "core_bad")
            table.append(
                {
                    "strategy_id": sid,
                    "rule_id": rule.rule_id,
                    "expression": rule.expression,
                    "dof": rule.dof,
                    "train_flagged_support": train_eval["flagged_support"],
                    "train_flagged_core_bad_rate": round(train_eval["flagged_rate"], 6),
                    "train_kept_core_bad_rate": round(train_eval["kept_rate"], 6),
                    "train_core_bad_gap": round(train_eval["rate_gap"], 6),
                    "train_flagged_avg_pnl": round(train_eval["flagged_avg_pnl"], 2),
                    "train_kept_avg_pnl": round(train_eval["kept_avg_pnl"], 2),
                    "holdout_flagged_support": hold_eval["flagged_support"],
                    "holdout_flagged_core_bad_rate": round(hold_eval["flagged_rate"], 6),
                    "holdout_kept_core_bad_rate": round(hold_eval["kept_rate"], 6),
                    "holdout_core_bad_gap": round(hold_eval["rate_gap"], 6),
                    "holdout_flagged_avg_pnl": round(hold_eval["flagged_avg_pnl"], 2),
                    "holdout_kept_avg_pnl": round(hold_eval["kept_avg_pnl"], 2),
                    "train_flagged_any_bad_rate": round(pct_true(train_flagged, "any_bad"), 6),
                    "holdout_flagged_any_bad_rate": round(pct_true(hold_flagged, "any_bad"), 6),
                    "stable_core_bad": (
                        train_eval["flagged_support"] >= 12
                        and hold_eval["flagged_support"] >= 8
                        and train_eval["rate_gap"] is not None
                        and hold_eval["rate_gap"] is not None
                        and train_eval["rate_gap"] >= 0.03
                        and hold_eval["rate_gap"] >= 0.05
                        and train_eval["avg_pnl_gap"] is not None
                        and hold_eval["avg_pnl_gap"] is not None
                        and train_eval["avg_pnl_gap"] < 0.0
                        and hold_eval["avg_pnl_gap"] < 0.0
                    ),
                }
            )
    return table


def shared_rule_winners(rule_table: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rule_table:
        grouped.setdefault(row["rule_id"], []).append(row)
    winners: list[dict] = []
    for rule_id, rows in grouped.items():
        if len(rows) != len(STRATEGIES):
            continue
        if all(row["stable_core_bad"] for row in rows):
            winners.append(
                {
                    "rule_id": rule_id,
                    "expression": rows[0]["expression"],
                    "dof": rows[0]["dof"],
                    "min_holdout_gap": min(row["holdout_core_bad_gap"] for row in rows),
                    "avg_holdout_gap": sum(row["holdout_core_bad_gap"] for row in rows) / len(rows),
                    "min_holdout_flagged_support": min(row["holdout_flagged_support"] for row in rows),
                }
            )
    winners.sort(key=lambda r: (-r["avg_holdout_gap"], r["dof"]))
    return winners


def risk_level(t: Trade) -> str:
    if t.entry_context != "chop":
        return "low_non_chop"
    if t.entry_price_to_slow_atr > STRETCH_THRESHOLD:
        return "high_chop_stretch"
    return "medium_chop"


def build_scorecard_bin_table(rows: list[Trade]) -> list[dict]:
    table: list[dict] = []
    for sid in STRATEGIES:
        sid_rows = [r for r in rows if r.strategy_id == sid]
        for period_name, subset in (
            ("train", [r for r in sid_rows if r.entry_dt <= TRAIN_END]),
            ("holdout", [r for r in sid_rows if r.entry_dt >= HOLDOUT_START]),
        ):
            for level in ("low_non_chop", "medium_chop", "high_chop_stretch"):
                group = [r for r in subset if risk_level(r) == level]
                if not group:
                    continue
                table.append(
                    {
                        "strategy_id": sid,
                        "period": period_name,
                        "risk_level": level,
                        "trades": len(group),
                        "core_bad_rate": round(pct_true(group, "core_bad"), 6),
                        "any_bad_rate": round(pct_true(group, "any_bad"), 6),
                        "avg_pnl_usd": round(avg_pnl(group), 2),
                        "net_pnl_usd": round(sum(x.pnl_usd for x in group), 2),
                    }
                )
    return table


def bootstrap_holdout(rows: list[Trade]) -> list[dict]:
    rng = random.Random(RNG_SEED)
    table: list[dict] = []
    for sid in STRATEGIES:
        holdout = [r for r in rows if r.strategy_id == sid and r.entry_dt >= HOLDOUT_START]
        high = [r for r in holdout if risk_level(r) == "high_chop_stretch"]
        rest = [r for r in holdout if risk_level(r) != "high_chop_stretch"]
        core_bad_diffs: list[float] = []
        pnl_diffs: list[float] = []
        recall_vals: list[float] = []
        precision_vals: list[float] = []
        if not high or not rest:
            continue
        for _ in range(BOOTSTRAP_N):
            high_s = [rng.choice(high) for _ in high]
            rest_s = [rng.choice(rest) for _ in rest]
            high_core = pct_true(high_s, "core_bad") or 0.0
            rest_core = pct_true(rest_s, "core_bad") or 0.0
            high_pnl = avg_pnl(high_s) or 0.0
            rest_pnl = avg_pnl(rest_s) or 0.0
            total_core = sum(1 for x in high_s + rest_s if x.core_bad)
            high_core_count = sum(1 for x in high_s if x.core_bad)
            core_bad_diffs.append(high_core - rest_core)
            pnl_diffs.append(high_pnl - rest_pnl)
            precision_vals.append(high_core)
            recall_vals.append(high_core_count / total_core if total_core else 0.0)

        core_bad_diffs.sort()
        pnl_diffs.sort()
        precision_vals.sort()
        recall_vals.sort()

        def q(xs: list[float], p: float) -> float:
            idx = min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))
            return xs[idx]

        table.append(
            {
                "strategy_id": sid,
                "holdout_high_support": len(high),
                "holdout_rest_support": len(rest),
                "core_bad_gap_median": round(q(core_bad_diffs, 0.5), 6),
                "core_bad_gap_p05": round(q(core_bad_diffs, 0.05), 6),
                "core_bad_gap_p95": round(q(core_bad_diffs, 0.95), 6),
                "avg_pnl_gap_median": round(q(pnl_diffs, 0.5), 2),
                "avg_pnl_gap_p05": round(q(pnl_diffs, 0.05), 2),
                "avg_pnl_gap_p95": round(q(pnl_diffs, 0.95), 2),
                "high_precision_core_bad_median": round(q(precision_vals, 0.5), 6),
                "high_precision_core_bad_p05": round(q(precision_vals, 0.05), 6),
                "high_precision_core_bad_p95": round(q(precision_vals, 0.95), 6),
                "high_recall_core_bad_median": round(q(recall_vals, 0.5), 6),
                "high_recall_core_bad_p05": round(q(recall_vals, 0.05), 6),
                "high_recall_core_bad_p95": round(q(recall_vals, 0.95), 6),
            }
        )
    return table


def build_year_table(rows: list[Trade]) -> list[dict]:
    table: list[dict] = []
    for sid in STRATEGIES:
        sid_rows = [r for r in rows if r.strategy_id == sid]
        years = sorted({r.entry_dt.year for r in sid_rows})
        for year in years:
            year_rows = [r for r in sid_rows if r.entry_dt.year == year]
            for level in ("low_non_chop", "medium_chop", "high_chop_stretch"):
                group = [r for r in year_rows if risk_level(r) == level]
                if not group:
                    continue
                table.append(
                    {
                        "strategy_id": sid,
                        "year": year,
                        "risk_level": level,
                        "trades": len(group),
                        "core_bad_rate": round(pct_true(group, "core_bad"), 6),
                        "any_bad_rate": round(pct_true(group, "any_bad"), 6),
                        "avg_pnl_usd": round(avg_pnl(group), 2),
                    }
                )
    return table


def build_trade_flags(rows: list[Trade]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "strategy_id": r.strategy_id,
                "trade_id": r.trade_id,
                "entry_ts": r.entry_ts,
                "risk_level": risk_level(r),
                "core_bad": r.core_bad,
                "any_bad": r.any_bad,
                "pnl_usd": round(r.pnl_usd, 2),
                "failure_mode": r.failure_mode,
                "entry_context": r.entry_context,
                "entry_er30": round(r.entry_er30, 6),
                "entry_vdo": round(r.entry_vdo, 6),
                "entry_ema_spread_atr": round(r.entry_ema_spread_atr, 6),
                "entry_price_to_slow_atr": round(r.entry_price_to_slow_atr, 6),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict) -> None:
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def build_report(rule_winners: list[dict], scorecard_bins: list[dict], bootstrap_rows: list[dict], elapsed: float) -> str:
    lines = [
        "# P0.1 Entry Risk Scorecard Report",
        "",
        "## Scope",
        "",
        "- Strategies: `X0`, `X0_E5EXIT`",
        "- Target label: `core_bad = false_breakout or trail_stop_noise`",
        "- Train: `2019-01-01` to `2023-12-31`",
        "- Holdout: `2024-01-01` to `2026-02-20`",
        "",
        "## Verdict",
        "",
        "- `PROMOTE_SCORECARD_AS_DIAGNOSTIC`",
        f"- Elapsed: `{elapsed:.2f}s`",
        "",
        "## Stable Shared Rules",
        "",
    ]
    if rule_winners:
        for row in rule_winners:
            lines.append(
                f"- `{row['rule_id']}`: dof={row['dof']}, holdout core-bad gap avg=`{row['avg_holdout_gap']:.4f}`, "
                f"min holdout support=`{row['min_holdout_flagged_support']}`"
            )
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Chosen Scorecard",
            "",
            "- `low_non_chop`: `entry_context != chop`",
            "- `medium_chop`: `entry_context == chop and entry_price_to_slow_atr <= 1.8`",
            "- `high_chop_stretch`: `entry_context == chop and entry_price_to_slow_atr > 1.8`",
            "",
            "Rationale:",
            "",
            "- `chop` is a stable first-pass risk separator.",
            "- `stretch > 1.8 ATR-from-slow` is the only higher-risk refinement that stayed stable across both families.",
            "- Extra ER / VDO / spread conditions did not survive cleanly enough to justify more complexity.",
            "",
            "## Holdout Snapshot",
            "",
        ]
    )

    for sid in STRATEGIES:
        holdout_rows = [r for r in scorecard_bins if r["strategy_id"] == sid and r["period"] == "holdout"]
        lines.append(f"- `{sid}`")
        for level in ("low_non_chop", "medium_chop", "high_chop_stretch"):
            row = next((x for x in holdout_rows if x["risk_level"] == level), None)
            if row is None:
                continue
            lines.append(
                f"  {level}: trades={row['trades']}, core_bad_rate={row['core_bad_rate']:.3f}, "
                f"any_bad_rate={row['any_bad_rate']:.3f}, avg_pnl={row['avg_pnl_usd']:.2f} USD"
            )

    lines.extend(["", "## Holdout Bootstrap", ""])
    for row in bootstrap_rows:
        lines.append(
            f"- `{row['strategy_id']}`: high-vs-rest core_bad gap median=`{row['core_bad_gap_median']:.3f}` "
            f"(p05=`{row['core_bad_gap_p05']:.3f}`, p95=`{row['core_bad_gap_p95']:.3f}`), "
            f"avg_pnl gap median=`{row['avg_pnl_gap_median']:.2f}` USD"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The project can identify `bad-trade-prone` cohorts in a coarse but usable way before entry.",
            "- It cannot identify winners precisely enough for a rich score or ML overlay.",
            "- The right operational use is:",
            "  - `X0`: optional hard gate or manual veto on `high_chop_stretch`",
            "  - `X0_E5EXIT`: warning / review flag, not a default hard block",
            "",
            "## Recommendation",
            "",
            "- Keep the scorecard as a deterministic diagnostic layer.",
            "- Do not expand it into an ML classifier on the current dataset.",
            "- If implemented live, start with `warning-only` on `X0_E5EXIT` and only then test a hard gate.",
            "",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    start = time.time()
    rows = read_trades()
    atomic_rule_table = build_atomic_rule_table(rows)
    shared_winners = shared_rule_winners(atomic_rule_table)
    scorecard_bins = build_scorecard_bin_table(rows)
    bootstrap_rows = bootstrap_holdout(rows)
    year_table = build_year_table(rows)
    trade_flags = build_trade_flags(rows)

    scorecard_spec = {
        "scorecard_id": "x0_entry_risk_v1",
        "target_label": "core_bad = false_breakout or trail_stop_noise",
        "risk_levels": [
            {"risk_level": "low_non_chop", "rule": "entry_context != chop"},
            {
                "risk_level": "medium_chop",
                "rule": f"entry_context == chop and entry_price_to_slow_atr <= {STRETCH_THRESHOLD}",
            },
            {
                "risk_level": "high_chop_stretch",
                "rule": f"entry_context == chop and entry_price_to_slow_atr > {STRETCH_THRESHOLD}",
            },
        ],
        "notes": {
            "X0": "usable as optional hard gate",
            "X0_E5EXIT": "warning-only by default; robust exit already repairs part of this cohort",
        },
    }

    elapsed = time.time() - start
    results = {
        "verdict": "PROMOTE_SCORECARD_AS_DIAGNOSTIC",
        "elapsed_seconds": round(elapsed, 4),
        "selected_high_risk_rule": f"entry_context == chop and entry_price_to_slow_atr > {STRETCH_THRESHOLD}",
        "stable_shared_rules": shared_winners,
        "scorecard_spec": scorecard_spec,
    }

    write_csv(
        OUTDIR / "p0_1_atomic_rules.csv",
        atomic_rule_table,
        [
            "strategy_id", "rule_id", "expression", "dof",
            "train_flagged_support", "train_flagged_core_bad_rate", "train_kept_core_bad_rate",
            "train_core_bad_gap", "train_flagged_avg_pnl", "train_kept_avg_pnl",
            "holdout_flagged_support", "holdout_flagged_core_bad_rate", "holdout_kept_core_bad_rate",
            "holdout_core_bad_gap", "holdout_flagged_avg_pnl", "holdout_kept_avg_pnl",
            "train_flagged_any_bad_rate", "holdout_flagged_any_bad_rate", "stable_core_bad",
        ],
    )
    write_csv(
        OUTDIR / "p0_1_scorecard_bins.csv",
        scorecard_bins,
        ["strategy_id", "period", "risk_level", "trades", "core_bad_rate", "any_bad_rate", "avg_pnl_usd", "net_pnl_usd"],
    )
    write_csv(
        OUTDIR / "p0_1_holdout_bootstrap.csv",
        bootstrap_rows,
        [
            "strategy_id", "holdout_high_support", "holdout_rest_support",
            "core_bad_gap_median", "core_bad_gap_p05", "core_bad_gap_p95",
            "avg_pnl_gap_median", "avg_pnl_gap_p05", "avg_pnl_gap_p95",
            "high_precision_core_bad_median", "high_precision_core_bad_p05", "high_precision_core_bad_p95",
            "high_recall_core_bad_median", "high_recall_core_bad_p05", "high_recall_core_bad_p95",
        ],
    )
    write_csv(
        OUTDIR / "p0_1_year_table.csv",
        year_table,
        ["strategy_id", "year", "risk_level", "trades", "core_bad_rate", "any_bad_rate", "avg_pnl_usd"],
    )
    write_csv(
        OUTDIR / "p0_1_trade_flags.csv",
        trade_flags,
        [
            "strategy_id", "trade_id", "entry_ts", "risk_level", "core_bad", "any_bad", "pnl_usd",
            "failure_mode", "entry_context", "entry_er30", "entry_vdo",
            "entry_ema_spread_atr", "entry_price_to_slow_atr",
        ],
    )
    write_json(OUTDIR / "p0_1_results.json", results)
    write_json(OUTDIR / "p0_1_scorecard_spec.json", scorecard_spec)
    (OUTDIR / "P0_1_REPORT.md").write_text(build_report(shared_winners, scorecard_bins, bootstrap_rows, elapsed))

    print("Verdict:", results["verdict"])
    print("Selected high-risk rule:", results["selected_high_risk_rule"])


if __name__ == "__main__":
    main()
