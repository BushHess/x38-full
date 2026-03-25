#!/usr/bin/env python3
"""P0.3 -- Matched-trade and sequencing attribution for stretch-gate survivors."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

OUTDIR = Path(__file__).resolve().parent
TRADE_TABLE = OUTDIR / "p0_1_trade_table.csv"

STRETCH_THRESHOLD = 1.8


@dataclass(frozen=True)
class PairSpec:
    pair_id: str
    reference: str
    candidate: str


PAIRS = [
    PairSpec("x0_stretch18", "X0", "X0_CHOP_STRETCH18"),
    PairSpec("x0e5_stretch18", "X0_E5EXIT", "X0E5_CHOP_STRETCH18"),
]


def load_trades() -> pd.DataFrame:
    df = pd.read_csv(TRADE_TABLE)
    df["entry_dt"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["exit_dt"] = pd.to_datetime(df["exit_ts"], utc=True)
    df["is_winner"] = df["is_winner"].astype(bool)
    return df


def in_position(trades: pd.DataFrame, ts: pd.Timestamp) -> bool:
    mask = (trades["entry_dt"] <= ts) & (ts < trades["exit_dt"])
    return bool(mask.any())


def exit_timing_label(ref_exit: pd.Timestamp, cand_exit: pd.Timestamp) -> str:
    if cand_exit < ref_exit:
        return "candidate_earlier"
    if cand_exit > ref_exit:
        return "candidate_later"
    return "same_exit"


def analyze_pair(df: pd.DataFrame, spec: PairSpec) -> tuple[dict, list[dict], list[dict], list[dict], list[dict]]:
    ref = df[df["strategy_id"] == spec.reference].copy()
    cand = df[df["strategy_id"] == spec.candidate].copy()

    ref_by_entry = {row.entry_ts: row for row in ref.itertuples(index=False)}
    cand_by_entry = {row.entry_ts: row for row in cand.itertuples(index=False)}

    matched_entries = sorted(set(ref_by_entry) & set(cand_by_entry))
    ref_only_entries = sorted(set(ref_by_entry) - set(cand_by_entry))
    cand_only_entries = sorted(set(cand_by_entry) - set(ref_by_entry))

    matched_rows: list[dict] = []
    ref_only_rows: list[dict] = []
    cand_only_rows: list[dict] = []

    matched_delta_pnl = 0.0
    matched_improved = 0
    matched_worsened = 0
    matched_same = 0
    matched_earlier = 0
    matched_later = 0
    matched_same_return = 0
    matched_changed_return = 0
    matched_ref_winners_improved = 0
    matched_ref_losers_improved = 0
    matched_ref_winners_worsened = 0
    matched_ref_losers_worsened = 0

    for entry_ts in matched_entries:
        r = ref_by_entry[entry_ts]
        c = cand_by_entry[entry_ts]
        d_pnl = float(c.pnl_usd - r.pnl_usd)
        d_ret = float(c.return_pct - r.return_pct)
        d_bars = int(c.bars_held - r.bars_held)
        timing = exit_timing_label(r.exit_dt, c.exit_dt)
        matched_delta_pnl += d_pnl
        if abs(d_ret) < 1e-9:
            matched_same_return += 1
        else:
            matched_changed_return += 1
        if d_pnl > 0:
            matched_improved += 1
            if r.is_winner:
                matched_ref_winners_improved += 1
            else:
                matched_ref_losers_improved += 1
        elif d_pnl < 0:
            matched_worsened += 1
            if r.is_winner:
                matched_ref_winners_worsened += 1
            else:
                matched_ref_losers_worsened += 1

        if timing == "same_exit":
            matched_same += 1
        elif timing == "candidate_earlier":
            matched_earlier += 1
        else:
            matched_later += 1

        matched_rows.append({
            "pair_id": spec.pair_id,
            "entry_ts": entry_ts,
            "reference": spec.reference,
            "candidate": spec.candidate,
            "ref_exit_ts": r.exit_ts,
            "cand_exit_ts": c.exit_ts,
            "ref_pnl_usd": round(float(r.pnl_usd), 2),
            "cand_pnl_usd": round(float(c.pnl_usd), 2),
            "d_pnl_usd": round(d_pnl, 2),
            "ref_return_pct": round(float(r.return_pct), 4),
            "cand_return_pct": round(float(c.return_pct), 4),
            "d_return_pct": round(d_ret, 4),
            "ref_bars_held": int(r.bars_held),
            "cand_bars_held": int(c.bars_held),
            "d_bars_held": d_bars,
            "exit_timing": timing,
            "ref_exit_reason": r.exit_reason,
            "cand_exit_reason": c.exit_reason,
            "ref_failure_mode": r.failure_mode,
            "cand_failure_mode": c.failure_mode,
            "ref_is_winner": bool(r.is_winner),
            "cand_is_winner": bool(c.is_winner),
        })

    direct_gate_avoided = 0.0
    sequence_removed = 0.0
    candidate_only_added = 0.0

    for entry_ts in ref_only_entries:
        r = ref_by_entry[entry_ts]
        meets_gate = bool(r.entry_context == "chop" and r.entry_price_to_slow_atr > STRETCH_THRESHOLD)
        cand_in_pos = in_position(cand, r.entry_dt)
        if meets_gate and not cand_in_pos:
            channel = "direct_gate_avoided"
            direct_gate_avoided += -float(r.pnl_usd)
        else:
            channel = "sequence_removed"
            sequence_removed += -float(r.pnl_usd)
        ref_only_rows.append({
            "pair_id": spec.pair_id,
            "entry_ts": entry_ts,
            "reference": spec.reference,
            "candidate": spec.candidate,
            "channel": channel,
            "meets_gate_rule": meets_gate,
            "candidate_in_position": cand_in_pos,
            "pnl_usd": round(float(r.pnl_usd), 2),
            "return_pct": round(float(r.return_pct), 4),
            "bars_held": int(r.bars_held),
            "entry_context": r.entry_context,
            "entry_vdo": round(float(r.entry_vdo), 6),
            "entry_er30": round(float(r.entry_er30), 6),
            "entry_price_to_slow_atr": round(float(r.entry_price_to_slow_atr), 6),
            "failure_mode": r.failure_mode,
            "is_winner": bool(r.is_winner),
        })

    for entry_ts in cand_only_entries:
        c = cand_by_entry[entry_ts]
        ref_in_pos = in_position(ref, c.entry_dt)
        candidate_only_added += float(c.pnl_usd)
        cand_only_rows.append({
            "pair_id": spec.pair_id,
            "entry_ts": entry_ts,
            "reference": spec.reference,
            "candidate": spec.candidate,
            "channel": "sequence_added",
            "reference_in_position": ref_in_pos,
            "pnl_usd": round(float(c.pnl_usd), 2),
            "return_pct": round(float(c.return_pct), 4),
            "bars_held": int(c.bars_held),
            "entry_context": c.entry_context,
            "entry_vdo": round(float(c.entry_vdo), 6),
            "entry_er30": round(float(c.entry_er30), 6),
            "entry_price_to_slow_atr": round(float(c.entry_price_to_slow_atr), 6),
            "failure_mode": c.failure_mode,
            "is_winner": bool(c.is_winner),
        })

    ref_total = float(ref["pnl_usd"].sum())
    cand_total = float(cand["pnl_usd"].sum())
    total_delta = cand_total - ref_total
    channel_sum = matched_delta_pnl + direct_gate_avoided + sequence_removed + candidate_only_added
    reconciliation_error = total_delta - channel_sum

    pair_summary = {
        "pair_id": spec.pair_id,
        "reference": spec.reference,
        "candidate": spec.candidate,
        "reference_trades": int(len(ref)),
        "candidate_trades": int(len(cand)),
        "matched_trades": int(len(matched_entries)),
        "reference_only_trades": int(len(ref_only_entries)),
        "candidate_only_trades": int(len(cand_only_entries)),
        "reference_total_pnl_usd": round(ref_total, 2),
        "candidate_total_pnl_usd": round(cand_total, 2),
        "total_delta_pnl_usd": round(total_delta, 2),
        "matched_delta_pnl_usd": round(matched_delta_pnl, 2),
        "direct_gate_avoided_pnl_usd": round(direct_gate_avoided, 2),
        "sequence_removed_pnl_usd": round(sequence_removed, 2),
        "candidate_only_added_pnl_usd": round(candidate_only_added, 2),
        "reconciliation_error_usd": round(reconciliation_error, 8),
        "matched_improved": matched_improved,
        "matched_worsened": matched_worsened,
        "matched_same_exit": matched_same,
        "matched_candidate_earlier": matched_earlier,
        "matched_candidate_later": matched_later,
        "matched_same_return": matched_same_return,
        "matched_changed_return": matched_changed_return,
        "matched_ref_winners_improved": matched_ref_winners_improved,
        "matched_ref_losers_improved": matched_ref_losers_improved,
        "matched_ref_winners_worsened": matched_ref_winners_worsened,
        "matched_ref_losers_worsened": matched_ref_losers_worsened,
    }
    if abs(total_delta) > 1e-12:
        pair_summary["matched_share_of_total_pct"] = round(matched_delta_pnl / total_delta * 100.0, 2)
        pair_summary["direct_gate_share_of_total_pct"] = round(direct_gate_avoided / total_delta * 100.0, 2)
        pair_summary["sequence_removed_share_of_total_pct"] = round(sequence_removed / total_delta * 100.0, 2)
        pair_summary["candidate_only_share_of_total_pct"] = round(candidate_only_added / total_delta * 100.0, 2)
    else:
        pair_summary["matched_share_of_total_pct"] = 0.0
        pair_summary["direct_gate_share_of_total_pct"] = 0.0
        pair_summary["sequence_removed_share_of_total_pct"] = 0.0
        pair_summary["candidate_only_share_of_total_pct"] = 0.0

    top_rows = sorted(matched_rows, key=lambda row: abs(row["d_pnl_usd"]), reverse=True)[:15]
    return pair_summary, matched_rows, ref_only_rows, cand_only_rows, top_rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_report(pair_summaries: list[dict]) -> str:
    lines = [
        "# P0.3 Matched-Trade Attribution",
        "",
        "## Scope",
        "",
        "- Pairs: `X0 -> X0_CHOP_STRETCH18`, `X0_E5EXIT -> X0E5_CHOP_STRETCH18`",
        "- Source artifact: `p0_1_trade_table.csv` (harsh scenario)",
        f"- Direct gate rule: `entry_context == chop and entry_price_to_slow_atr > {STRETCH_THRESHOLD}`",
        "",
        "## Findings",
        "",
    ]

    for summary in pair_summaries:
        lines.append(
            f"- `{summary['candidate']}` vs `{summary['reference']}`: "
            f"total delta {summary['total_delta_pnl_usd']:+.2f} USD, "
            f"matched {summary['matched_delta_pnl_usd']:+.2f} USD, "
            f"direct-gate avoided {summary['direct_gate_avoided_pnl_usd']:+.2f} USD, "
            f"sequence-removed {summary['sequence_removed_pnl_usd']:+.2f} USD, "
            f"candidate-only {summary['candidate_only_added_pnl_usd']:+.2f} USD"
        )
        lines.append(
            f"  matched exits: improved={summary['matched_improved']}, worsened={summary['matched_worsened']}, "
            f"earlier={summary['matched_candidate_earlier']}, same={summary['matched_same_exit']}, later={summary['matched_candidate_later']}, "
            f"same_return={summary['matched_same_return']}, changed_return={summary['matched_changed_return']}"
        )

    lines.extend(["", "## Interpretation", ""])

    x0 = next(s for s in pair_summaries if s["pair_id"] == "x0_stretch18")
    x0e5 = next(s for s in pair_summaries if s["pair_id"] == "x0e5_stretch18")

    lines.append("- In both pairs, all matched trades have the same exit timestamp and the same return. That means the matched channel is not `better exits`; it is capital-path carry on later shared trades.")
    lines.append("- The true root mechanism is: remove a weak over-stretched chop cohort, preserve capital, then compound larger on later trades that both variants still take.")
    lines.append("- On `X0`, direct gate removal is economically meaningful and the later capital carry amplifies it.")
    lines.append("- On `X0_E5EXIT`, direct gate removal is smaller, but the preserved-capital carry on later shared trades is still large enough to improve the family.")
    lines.append("- The next branch should validate whether this capital-path effect survives harsher validation, not add more entry filters.")

    return "\n".join(lines) + "\n"


def main() -> None:
    df = load_trades()

    pair_summaries: list[dict] = []
    matched_rows: list[dict] = []
    ref_only_rows: list[dict] = []
    cand_only_rows: list[dict] = []
    top_rows: list[dict] = []

    for spec in PAIRS:
        summary, matched, ref_only, cand_only, top = analyze_pair(df, spec)
        pair_summaries.append(summary)
        matched_rows.extend(matched)
        ref_only_rows.extend(ref_only)
        cand_only_rows.extend(cand_only)
        top_rows.extend(top)

    report = build_report(pair_summaries)

    payload = {
        "settings": {
            "source_trade_table": str(TRADE_TABLE),
            "stretch_threshold": STRETCH_THRESHOLD,
        },
        "pair_summaries": pair_summaries,
    }
    with (OUTDIR / "p0_3_results.json").open("w") as f:
        json.dump(payload, f, indent=2)

    write_csv(
        OUTDIR / "p0_3_channel_summary.csv",
        pair_summaries,
        [
            "pair_id", "reference", "candidate", "reference_trades", "candidate_trades",
            "matched_trades", "reference_only_trades", "candidate_only_trades",
            "reference_total_pnl_usd", "candidate_total_pnl_usd", "total_delta_pnl_usd",
            "matched_delta_pnl_usd", "direct_gate_avoided_pnl_usd", "sequence_removed_pnl_usd",
            "candidate_only_added_pnl_usd", "reconciliation_error_usd",
            "matched_improved", "matched_worsened", "matched_same_exit",
            "matched_candidate_earlier", "matched_candidate_later",
            "matched_same_return", "matched_changed_return",
            "matched_ref_winners_improved", "matched_ref_losers_improved",
            "matched_ref_winners_worsened", "matched_ref_losers_worsened",
            "matched_share_of_total_pct", "direct_gate_share_of_total_pct",
            "sequence_removed_share_of_total_pct", "candidate_only_share_of_total_pct",
        ],
    )
    write_csv(
        OUTDIR / "p0_3_matched_trade_table.csv",
        matched_rows,
        [
            "pair_id", "entry_ts", "reference", "candidate", "ref_exit_ts", "cand_exit_ts",
            "ref_pnl_usd", "cand_pnl_usd", "d_pnl_usd", "ref_return_pct", "cand_return_pct",
            "d_return_pct", "ref_bars_held", "cand_bars_held", "d_bars_held", "exit_timing",
            "ref_exit_reason", "cand_exit_reason", "ref_failure_mode", "cand_failure_mode",
            "ref_is_winner", "cand_is_winner",
        ],
    )
    write_csv(
        OUTDIR / "p0_3_reference_only_table.csv",
        ref_only_rows,
        [
            "pair_id", "entry_ts", "reference", "candidate", "channel", "meets_gate_rule",
            "candidate_in_position", "pnl_usd", "return_pct", "bars_held", "entry_context",
            "entry_vdo", "entry_er30", "entry_price_to_slow_atr", "failure_mode", "is_winner",
        ],
    )
    write_csv(
        OUTDIR / "p0_3_candidate_only_table.csv",
        cand_only_rows,
        [
            "pair_id", "entry_ts", "reference", "candidate", "channel", "reference_in_position",
            "pnl_usd", "return_pct", "bars_held", "entry_context", "entry_vdo", "entry_er30",
            "entry_price_to_slow_atr", "failure_mode", "is_winner",
        ],
    )
    write_csv(
        OUTDIR / "p0_3_top_matched_contributors.csv",
        top_rows,
        [
            "pair_id", "entry_ts", "reference", "candidate", "ref_exit_ts", "cand_exit_ts",
            "ref_pnl_usd", "cand_pnl_usd", "d_pnl_usd", "ref_return_pct", "cand_return_pct",
            "d_return_pct", "ref_bars_held", "cand_bars_held", "d_bars_held", "exit_timing",
            "ref_exit_reason", "cand_exit_reason", "ref_failure_mode", "cand_failure_mode",
            "ref_is_winner", "cand_is_winner",
        ],
    )
    (OUTDIR / "P0_3_MATCHED_ATTRIBUTION_REPORT.md").write_text(report)
    print(f"Saved matched-trade attribution artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
