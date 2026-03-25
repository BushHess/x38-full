#!/usr/bin/env python3
"""P0.3 -- Event review for the best exit-floor candidate."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

OUTDIR = Path(__file__).resolve().parent
TRADE_TABLE = OUTDIR / "p0_1_trade_table.csv"


@dataclass(frozen=True)
class PairSpec:
    pair_id: str
    reference: str
    candidate: str


PAIR = PairSpec("x0e5_floor_latch", "X0_E5EXIT", "X0E5_FLOOR_LATCH")


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


def analyze_pair(df: pd.DataFrame, spec: PairSpec):
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
    improved = worsened = same = 0
    earlier = later = same_exit = 0
    floor_exit_improved = floor_exit_worsened = 0

    for entry_ts in matched_entries:
        r = ref_by_entry[entry_ts]
        c = cand_by_entry[entry_ts]
        d_pnl = float(c.pnl_usd - r.pnl_usd)
        d_ret = float(c.return_pct - r.return_pct)
        timing = exit_timing_label(r.exit_dt, c.exit_dt)
        matched_delta_pnl += d_pnl
        if d_pnl > 0:
            improved += 1
        elif d_pnl < 0:
            worsened += 1
        else:
            same += 1

        if timing == "candidate_earlier":
            earlier += 1
        elif timing == "candidate_later":
            later += 1
        else:
            same_exit += 1

        if "floor_exit" in str(c.exit_reason):
            if d_pnl > 0:
                floor_exit_improved += 1
            elif d_pnl < 0:
                floor_exit_worsened += 1

        matched_rows.append({
            "pair_id": spec.pair_id,
            "entry_ts": entry_ts,
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
            "d_bars_held": int(c.bars_held - r.bars_held),
            "exit_timing": timing,
            "ref_exit_reason": r.exit_reason,
            "cand_exit_reason": c.exit_reason,
            "ref_failure_mode": r.failure_mode,
            "cand_failure_mode": c.failure_mode,
            "ref_is_winner": bool(r.is_winner),
            "cand_is_winner": bool(c.is_winner),
        })

    ref_only_delta = 0.0
    cand_only_delta = 0.0

    for entry_ts in ref_only_entries:
        r = ref_by_entry[entry_ts]
        cand_in_pos = in_position(cand, r.entry_dt)
        ref_only_delta += -float(r.pnl_usd)
        ref_only_rows.append({
            "pair_id": spec.pair_id,
            "entry_ts": entry_ts,
            "channel": "reference_only",
            "candidate_in_position": cand_in_pos,
            "pnl_usd": round(float(r.pnl_usd), 2),
            "return_pct": round(float(r.return_pct), 4),
            "bars_held": int(r.bars_held),
            "entry_context": r.entry_context,
            "failure_mode": r.failure_mode,
            "is_winner": bool(r.is_winner),
        })

    for entry_ts in cand_only_entries:
        c = cand_by_entry[entry_ts]
        ref_in_pos = in_position(ref, c.entry_dt)
        cand_only_delta += float(c.pnl_usd)
        cand_only_rows.append({
            "pair_id": spec.pair_id,
            "entry_ts": entry_ts,
            "channel": "candidate_only",
            "reference_in_position": ref_in_pos,
            "pnl_usd": round(float(c.pnl_usd), 2),
            "return_pct": round(float(c.return_pct), 4),
            "bars_held": int(c.bars_held),
            "entry_context": c.entry_context,
            "failure_mode": c.failure_mode,
            "is_winner": bool(c.is_winner),
        })

    ref_total = float(ref["pnl_usd"].sum())
    cand_total = float(cand["pnl_usd"].sum())
    total_delta = cand_total - ref_total
    reconciliation_error = total_delta - (matched_delta_pnl + ref_only_delta + cand_only_delta)

    top_positive = sorted([r for r in matched_rows if r["d_pnl_usd"] > 0], key=lambda row: row["d_pnl_usd"], reverse=True)
    top_negative = sorted([r for r in matched_rows if r["d_pnl_usd"] < 0], key=lambda row: row["d_pnl_usd"])
    top5_positive_sum = sum(r["d_pnl_usd"] for r in top_positive[:5])
    top5_negative_sum = sum(r["d_pnl_usd"] for r in top_negative[:5])

    summary = {
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
        "reference_only_delta_pnl_usd": round(ref_only_delta, 2),
        "candidate_only_delta_pnl_usd": round(cand_only_delta, 2),
        "reconciliation_error_usd": round(reconciliation_error, 8),
        "matched_improved": improved,
        "matched_worsened": worsened,
        "matched_same": same,
        "matched_candidate_earlier": earlier,
        "matched_candidate_later": later,
        "matched_same_exit": same_exit,
        "floor_exit_improved": floor_exit_improved,
        "floor_exit_worsened": floor_exit_worsened,
        "top5_positive_matched_delta_usd": round(top5_positive_sum, 2),
        "top5_negative_matched_delta_usd": round(top5_negative_sum, 2),
        "top5_positive_share_of_total_pct": round((top5_positive_sum / total_delta * 100.0), 2) if abs(total_delta) > 1e-12 else 0.0,
    }
    return summary, matched_rows, ref_only_rows, cand_only_rows, top_positive[:15], top_negative[:15]


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_report(summary: dict) -> str:
    lines = [
        "# P0.3 Exit-Floor Event Review",
        "",
        "## Scope",
        "",
        f"- Pair: `{summary['reference']} -> {summary['candidate']}`",
        "- Source artifact: `p0_1_trade_table.csv` (harsh scenario)",
        "",
        "## Findings",
        "",
        f"- Total PnL delta: `{summary['total_delta_pnl_usd']:+.2f} USD`",
        f"- Matched-trade delta: `{summary['matched_delta_pnl_usd']:+.2f} USD`",
        f"- Reference-only sequencing delta: `{summary['reference_only_delta_pnl_usd']:+.2f} USD`",
        f"- Candidate-only sequencing delta: `{summary['candidate_only_delta_pnl_usd']:+.2f} USD`",
        f"- Matched trades improved / worsened / same: `{summary['matched_improved']}` / `{summary['matched_worsened']}` / `{summary['matched_same']}`",
        f"- Candidate earlier / later / same exit: `{summary['matched_candidate_earlier']}` / `{summary['matched_candidate_later']}` / `{summary['matched_same_exit']}`",
        f"- Floor-exit matched improvements / worsens: `{summary['floor_exit_improved']}` / `{summary['floor_exit_worsened']}`",
        f"- Top 5 positive matched contributors explain `{summary['top5_positive_share_of_total_pct']:.2f}%` of total delta",
        "",
        "## Interpretation",
        "",
    ]

    if summary["matched_delta_pnl_usd"] < 0.0 and summary["candidate_only_delta_pnl_usd"] > 0.0:
        lines.append("- The main uplift does not come from better matched exits. Matched-trade delta is negative, while candidate-only sequencing is strongly positive.")
        lines.append("- Economically, this means the candidate gives up money on many shared trades, then earns it back through altered capital path and later re-entries.")
    else:
        lines.append("- A meaningful part of the uplift comes directly from matched-trade exit changes.")

    if summary["top5_positive_share_of_total_pct"] >= 60.0:
        lines.append("- Positive attribution is fairly concentrated. A small set of events explains a large share of the observed uplift.")
    else:
        lines.append("- Positive attribution is not overly concentrated across events.")

    if summary["matched_candidate_earlier"] > summary["matched_candidate_later"]:
        lines.append("- The candidate mostly differs by exiting earlier, which is consistent with the intended floor-exit mechanism.")

    lines.append("- Read together with weak WFO breadth, this pattern supports `research-only`, not promotion.")
    return "\n".join(lines) + "\n"


def main() -> None:
    df = load_trades()
    summary, matched_rows, ref_only_rows, cand_only_rows, top_positive, top_negative = analyze_pair(df, PAIR)

    payload = {
        "settings": {
            "source_trade_table": str(TRADE_TABLE),
            "pair_id": PAIR.pair_id,
            "reference": PAIR.reference,
            "candidate": PAIR.candidate,
        },
        "summary": summary,
    }
    with (OUTDIR / "p0_3_results.json").open("w") as f:
        json.dump(payload, f, indent=2)

    write_csv(
        OUTDIR / "p0_3_channel_summary.csv",
        [summary],
        list(summary.keys()),
    )
    write_csv(
        OUTDIR / "p0_3_matched_trade_table.csv",
        matched_rows,
        [
            "pair_id", "entry_ts", "ref_exit_ts", "cand_exit_ts",
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
            "pair_id", "entry_ts", "channel", "candidate_in_position", "pnl_usd",
            "return_pct", "bars_held", "entry_context", "failure_mode", "is_winner",
        ],
    )
    write_csv(
        OUTDIR / "p0_3_candidate_only_table.csv",
        cand_only_rows,
        [
            "pair_id", "entry_ts", "channel", "reference_in_position", "pnl_usd",
            "return_pct", "bars_held", "entry_context", "failure_mode", "is_winner",
        ],
    )
    write_csv(
        OUTDIR / "p0_3_top_positive_contributors.csv",
        top_positive,
        [
            "pair_id", "entry_ts", "ref_exit_ts", "cand_exit_ts",
            "ref_pnl_usd", "cand_pnl_usd", "d_pnl_usd", "ref_return_pct", "cand_return_pct",
            "d_return_pct", "ref_bars_held", "cand_bars_held", "d_bars_held", "exit_timing",
            "ref_exit_reason", "cand_exit_reason", "ref_failure_mode", "cand_failure_mode",
            "ref_is_winner", "cand_is_winner",
        ],
    )
    write_csv(
        OUTDIR / "p0_3_top_negative_contributors.csv",
        top_negative,
        [
            "pair_id", "entry_ts", "ref_exit_ts", "cand_exit_ts",
            "ref_pnl_usd", "cand_pnl_usd", "d_pnl_usd", "ref_return_pct", "cand_return_pct",
            "d_return_pct", "ref_bars_held", "cand_bars_held", "d_bars_held", "exit_timing",
            "ref_exit_reason", "cand_exit_reason", "ref_failure_mode", "cand_failure_mode",
            "ref_is_winner", "cand_is_winner",
        ],
    )
    (OUTDIR / "P0_3_EVENT_REVIEW_REPORT.md").write_text(build_report(summary))
    print(f"Saved event review artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
