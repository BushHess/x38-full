#!/usr/bin/env python3
"""P0.2 -- Trade-level attribution for the surviving stretch gate."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

OUTDIR = Path(__file__).resolve().parent
TRADE_TABLE = OUTDIR / "p0_1_trade_table.csv"

RULE_LABEL = "entry_context == chop and entry_price_to_slow_atr > 1.8"


def summarize_group(df: pd.DataFrame, strategy_id: str, cohort: str) -> dict:
    trades = int(len(df))
    wins = int(df["is_winner"].astype(bool).sum())
    losses = trades - wins
    win_rate = (wins / trades * 100.0) if trades else 0.0
    net_pnl = float(df["pnl_usd"].sum()) if trades else 0.0
    loser_loss = float(df.loc[df["pnl_usd"] < 0.0, "pnl_usd"].sum()) if trades else 0.0
    return {
        "strategy_id": strategy_id,
        "cohort": cohort,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "net_pnl_usd": round(net_pnl, 2),
        "loser_loss_usd": round(loser_loss, 2),
        "median_entry_vdo": round(float(df["entry_vdo"].median()), 6) if trades else None,
        "median_entry_er30": round(float(df["entry_er30"].median()), 6) if trades else None,
        "median_entry_price_to_slow_atr": round(float(df["entry_price_to_slow_atr"].median()), 6) if trades else None,
        "median_first6_mfe_r": round(float(df["first_6_bar_mfe_r"].median()), 6) if trades else None,
        "median_first6_mae_r": round(float(df["first_6_bar_mae_r"].median()), 6) if trades else None,
        "median_mfe_r": round(float(df["mfe_r"].median()), 6) if trades else None,
        "median_mae_r": round(float(df["mae_r"].median()), 6) if trades else None,
    }


def build_artifacts() -> tuple[list[dict], list[dict], str]:
    df = pd.read_csv(TRADE_TABLE)
    refs = df[df["strategy_id"].isin(["X0", "X0_E5EXIT"])].copy()
    blocked_mask = (
        (refs["entry_context"] == "chop")
        & (refs["entry_price_to_slow_atr"] > 1.8)
    )
    refs["cohort"] = blocked_mask.map({True: "blocked_by_stretch18", False: "kept_by_stretch18"})

    summary_rows: list[dict] = []
    failure_rows: list[dict] = []

    for strategy_id in ("X0", "X0_E5EXIT"):
        sub = refs[refs["strategy_id"] == strategy_id]
        for cohort in ("blocked_by_stretch18", "kept_by_stretch18"):
            cohort_df = sub[sub["cohort"] == cohort]
            summary_rows.append(summarize_group(cohort_df, strategy_id, cohort))

            total_loss = abs(float(cohort_df.loc[cohort_df["pnl_usd"] < 0.0, "pnl_usd"].sum()))
            for failure_mode, group in cohort_df.groupby("failure_mode"):
                loss = abs(float(group.loc[group["pnl_usd"] < 0.0, "pnl_usd"].sum()))
                failure_rows.append({
                    "strategy_id": strategy_id,
                    "cohort": cohort,
                    "failure_mode": failure_mode,
                    "trades": int(len(group)),
                    "net_pnl_usd": round(float(group["pnl_usd"].sum()), 2),
                    "loser_loss_usd": round(-loss, 2),
                    "share_of_cohort_loss_pct": round((loss / total_loss * 100.0) if total_loss > 0 else 0.0, 4),
                })

    x0_blocked = next(r for r in summary_rows if r["strategy_id"] == "X0" and r["cohort"] == "blocked_by_stretch18")
    x0_kept = next(r for r in summary_rows if r["strategy_id"] == "X0" and r["cohort"] == "kept_by_stretch18")
    x0e5_blocked = next(r for r in summary_rows if r["strategy_id"] == "X0_E5EXIT" and r["cohort"] == "blocked_by_stretch18")
    x0e5_kept = next(r for r in summary_rows if r["strategy_id"] == "X0_E5EXIT" and r["cohort"] == "kept_by_stretch18")

    report = "\n".join([
        "# P0.2 Stretch Gate Attribution",
        "",
        "## Rule",
        "",
        f"- `{RULE_LABEL}`",
        "",
        "## Key Findings",
        "",
        f"- `X0` blocked cohort: {x0_blocked['trades']} trades, net PnL {x0_blocked['net_pnl_usd']:.2f} USD, win rate {x0_blocked['win_rate_pct']:.1f}%",
        f"- `X0` kept cohort: {x0_kept['trades']} trades, net PnL {x0_kept['net_pnl_usd']:.2f} USD, win rate {x0_kept['win_rate_pct']:.1f}%",
        f"- `X0_E5EXIT` blocked cohort: {x0e5_blocked['trades']} trades, net PnL {x0e5_blocked['net_pnl_usd']:.2f} USD, win rate {x0e5_blocked['win_rate_pct']:.1f}%",
        f"- `X0_E5EXIT` kept cohort: {x0e5_kept['trades']} trades, net PnL {x0e5_kept['net_pnl_usd']:.2f} USD, win rate {x0e5_kept['win_rate_pct']:.1f}%",
        "",
        "## Interpretation",
        "",
        "- On `X0`, the stretch gate is clearly filtering a weak cohort: blocked trades are negative-PnL, lower quality, and show worse early excursion.",
        "- On `X0_E5EXIT`, the same blocked cohort is only marginally positive, which implies the robust exit already repairs part of the damage from over-stretched chop entries.",
        "- This supports a concrete next question: does the stretch gate still add value after robust exit because it removes a weak residual cohort, or because it changes later trade sequencing?",
        "",
    ]) + "\n"

    return summary_rows, failure_rows, report


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    summary_rows, failure_rows, report = build_artifacts()
    write_csv(
        OUTDIR / "p0_2_stretch_blocked_summary.csv",
        summary_rows,
        [
            "strategy_id", "cohort", "trades", "wins", "losses", "win_rate_pct",
            "net_pnl_usd", "loser_loss_usd", "median_entry_vdo", "median_entry_er30",
            "median_entry_price_to_slow_atr", "median_first6_mfe_r", "median_first6_mae_r",
            "median_mfe_r", "median_mae_r",
        ],
    )
    write_csv(
        OUTDIR / "p0_2_stretch_blocked_failure_modes.csv",
        failure_rows,
        [
            "strategy_id", "cohort", "failure_mode", "trades", "net_pnl_usd",
            "loser_loss_usd", "share_of_cohort_loss_pct",
        ],
    )
    blocked = pd.read_csv(TRADE_TABLE)
    blocked = blocked[
        blocked["strategy_id"].isin(["X0", "X0_E5EXIT"])
        & (blocked["entry_context"] == "chop")
        & (blocked["entry_price_to_slow_atr"] > 1.8)
    ].copy()
    blocked.to_csv(OUTDIR / "p0_2_stretch_blocked_trades.csv", index=False)
    (OUTDIR / "P0_2_STRETCH_ATTRIBUTION_REPORT.md").write_text(report)
    print(f"Saved stretch attribution artifacts to {OUTDIR}")


if __name__ == "__main__":
    main()
