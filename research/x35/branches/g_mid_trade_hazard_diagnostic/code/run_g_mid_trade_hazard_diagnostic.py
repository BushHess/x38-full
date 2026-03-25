"""Run mid-trade hazard survey for x35."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT))

from research.x35.shared.common import attach_state_to_events  # noqa: E402
from research.x35.shared.common import bars_to_frame  # noqa: E402
from research.x35.shared.common import ensure_dir  # noqa: E402
from research.x35.shared.common import load_feed  # noqa: E402
from research.x35.shared.common import write_json  # noqa: E402
from research.x35.shared.weekly_instability_states import build_weekly_instability_states  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Config  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy  # noqa: E402
from v10.core.engine import BacktestEngine  # noqa: E402
from v10.core.types import SCENARIOS  # noqa: E402

RESULTS_DIR = ensure_dir(Path(__file__).resolve().parents[1] / "results")
H4_MS = 4 * 60 * 60 * 1000


def _trades_to_frame(trades: list) -> pd.DataFrame:
    rows = []
    for trade in trades:
        rows.append(
            {
                "trade_id": int(trade.trade_id),
                "entry_ts_ms": int(trade.entry_ts_ms),
                "exit_ts_ms": int(trade.exit_ts_ms),
                "entry_price": float(trade.entry_price),
                "exit_price": float(trade.exit_price),
                "pnl": float(trade.pnl),
                "return_pct": float(trade.return_pct),
                "days_held": float(trade.days_held),
                "entry_reason": str(trade.entry_reason),
                "exit_reason": str(trade.exit_reason),
            }
        )
    return pd.DataFrame(rows).sort_values("entry_ts_ms").reset_index(drop=True)


def _scan_spec(
    spec_id: str,
    trades_df: pd.DataFrame,
    h4_state_df: pd.DataFrame,
    entry_state_df: pd.DataFrame,
) -> dict:
    top20_ids = set(trades_df.nlargest(20, "pnl")["trade_id"].tolist())
    event_rows = []
    eligible = 0
    skipped_entry_unstable = 0

    for trade in trades_df.itertuples(index=False):
        entry_state_row = entry_state_df[entry_state_df["trade_id"] == trade.trade_id]
        if entry_state_row.empty:
            continue
        entry_state = int(entry_state_row.iloc[0]["state"])
        if entry_state != 0:
            skipped_entry_unstable += 1
            continue

        eligible += 1
        trade_h4 = h4_state_df[
            (h4_state_df["close_time"] > trade.entry_ts_ms)
            & (h4_state_df["next_open_time"].notna())
            & (h4_state_df["next_open_time"] < trade.exit_ts_ms)
        ].copy()
        hit = trade_h4[trade_h4["state"] == 1].head(1)
        if hit.empty:
            continue

        row = hit.iloc[0]
        force_flat_ts_ms = int(row["next_open_time"])
        force_flat_price = float(row["next_open"])
        bars_saved = int(max(round((trade.exit_ts_ms - force_flat_ts_ms) / H4_MS), 0))
        edge_pct = (force_flat_price / trade.exit_price - 1.0) * 100.0

        event_rows.append(
            {
                "trade_id": int(trade.trade_id),
                "final_return_pct": round(float(trade.return_pct), 4),
                "winner": bool(trade.pnl > 0),
                "force_flat_edge_pct": round(edge_pct, 4),
                "bars_saved": bars_saved,
                "hit_ts_ms": int(row["close_time"]),
                "force_flat_ts_ms": force_flat_ts_ms,
                "force_flat_price": round(force_flat_price, 4),
                "actual_exit_price": round(float(trade.exit_price), 4),
                "top20_trade": bool(trade.trade_id in top20_ids),
            }
        )

    events_df = pd.DataFrame(event_rows)
    coverage_pct = 0.0 if trades_df.empty else (len(events_df) / len(trades_df)) * 100.0
    median_bars_saved = float(events_df["bars_saved"].median()) if not events_df.empty else 0.0

    loser_hits = events_df[events_df["winner"] == False].copy()  # noqa: E712
    winner_hits = events_df[events_df["winner"] == True].copy()  # noqa: E712
    loser_mean_edge = float(loser_hits["force_flat_edge_pct"].mean()) if not loser_hits.empty else 0.0
    winner_mean_edge = float(winner_hits["force_flat_edge_pct"].mean()) if not winner_hits.empty else 0.0
    selectivity_ratio = (
        loser_mean_edge / abs(winner_mean_edge)
        if loser_mean_edge > 0.0 and winner_mean_edge < 0.0 and not math.isclose(winner_mean_edge, 0.0)
        else 0.0
    )
    top20_hit_count = int(events_df["top20_trade"].sum()) if not events_df.empty else 0

    gates = {
        "G1_coverage": bool(coverage_pct >= 10.0),
        "G2_timing": bool(median_bars_saved >= 2.0),
        "G3_loser_benefit": bool(loser_mean_edge > 0.0),
        "G4_winner_cost": bool(winner_mean_edge < 0.0),
        "G5_selectivity": bool(selectivity_ratio >= 1.5),
        "G6_top20_damage": bool(top20_hit_count <= 2),
    }

    return {
        "spec_id": spec_id,
        "eligible_trades": eligible,
        "entry_unstable_skipped": skipped_entry_unstable,
        "hazard_hit_trades": int(len(events_df)),
        "coverage_pct": round(coverage_pct, 2),
        "median_bars_saved": round(median_bars_saved, 1),
        "n_losers_with_hit": int(len(loser_hits)),
        "n_winners_with_hit": int(len(winner_hits)),
        "loser_mean_edge_pct": round(loser_mean_edge, 4),
        "winner_mean_edge_pct": round(winner_mean_edge, 4),
        "selectivity_ratio": round(selectivity_ratio, 4),
        "top20_hit_count": top20_hit_count,
        "gates": gates,
        "promising": all(gates.values()),
        "events": event_rows,
    }


def _build_markdown(payload: dict) -> str:
    lines = [
        "# X35 Mid-Trade Hazard Scan",
        "",
        "## Baseline",
        "",
        f"- Strategy: `{payload['baseline']['strategy']}`",
        f"- Trades: `{payload['baseline']['trades']}`",
        f"- Sharpe: `{payload['baseline']['sharpe']}`",
        f"- CAGR %: `{payload['baseline']['cagr_pct']}`",
        f"- MDD %: `{payload['baseline']['max_drawdown_mid_pct']}`",
        f"- Branch verdict: `{payload['branch_verdict']}`",
        "",
        "## Spec Summary",
        "",
        "| Spec | Eligible | Hits | Coverage % | Median bars saved | Loser mean edge % | Winner mean edge % | Selectivity | Top20 hits | Promising |",
        "|------|----------|------|------------|-------------------|-------------------|--------------------|-------------|------------|-----------|",
    ]

    for row in payload["specs"]:
        lines.append(
            f"| `{row['spec_id']}` | {row['eligible_trades']} | {row['hazard_hit_trades']} | {row['coverage_pct']} | "
            f"{row['median_bars_saved']} | {row['loser_mean_edge_pct']} | {row['winner_mean_edge_pct']} | "
            f"{row['selectivity_ratio']} | {row['top20_hit_count']} | {row['promising']} |"
        )

    lines.extend(["", "## Gate Detail", ""])
    for row in payload["specs"]:
        lines.append(f"### `{row['spec_id']}`")
        lines.append("")
        for gate_name, gate_value in row["gates"].items():
            lines.append(f"- {gate_name}: {'PASS' if gate_value else 'FAIL'}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    feed = load_feed()
    report_start_ms = int(feed.report_start_ms or 0)

    h4_df = bars_to_frame(feed.h4_bars, report_start_ms)
    h4_report = h4_df[h4_df["in_report"]].copy().reset_index(drop=True)
    h4_report["next_open"] = h4_report["open"].shift(-1)
    h4_report["next_open_time"] = h4_report["open_time"].shift(-1)

    d1_df = bars_to_frame(feed.d1_bars, report_start_ms)
    states = build_weekly_instability_states(d1_df)

    strategy = VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config())
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=SCENARIOS["harsh"],
        initial_cash=10_000.0,
        warmup_mode="no_trade",
    )
    result = engine.run()
    trades_df = _trades_to_frame(result.trades)

    spec_rows = []
    for spec_id, state_df in states.items():
        mapped_h4 = attach_state_to_events(
            h4_report[["open_time", "close_time", "open", "close", "next_open", "next_open_time"]].copy(),
            state_df[["close_time", "state", "state_label"]].copy(),
            event_time_col="close_time",
        ).dropna(subset=["state"]).copy()
        mapped_h4["state"] = mapped_h4["state"].astype(int)

        entry_states = attach_state_to_events(
            trades_df[["trade_id", "entry_ts_ms"]].copy(),
            state_df[["close_time", "state", "state_label"]].copy(),
            event_time_col="entry_ts_ms",
        ).dropna(subset=["state"]).copy()
        entry_states["state"] = entry_states["state"].astype(int)

        spec_rows.append(_scan_spec(spec_id, trades_df, mapped_h4, entry_states))

    spec_rows.sort(
        key=lambda row: (
            sum(bool(v) for v in row["gates"].values()),
            row["selectivity_ratio"],
            row["coverage_pct"],
        ),
        reverse=True,
    )

    payload = {
        "study_id": "x35_long_horizon_regime",
        "branch": "g_mid_trade_hazard_diagnostic",
        "branch_verdict": "GO_MID_TRADE_HAZARD_FAMILY" if any(row["promising"] for row in spec_rows) else "NO_GO_MID_TRADE_HAZARD_FAMILY",
        "baseline": {
            "strategy": "VTrendE5Ema21D1Strategy",
            "trades": int(result.summary.get("trades", len(result.trades))),
            "sharpe": round(float(result.summary.get("sharpe", 0.0)), 4),
            "cagr_pct": round(float(result.summary.get("cagr_pct", 0.0)), 2),
            "max_drawdown_mid_pct": round(float(result.summary.get("max_drawdown_mid_pct", 0.0)), 2),
        },
        "specs": spec_rows,
    }

    json_path = RESULTS_DIR / "mid_trade_hazard_scan.json"
    md_path = RESULTS_DIR / "mid_trade_hazard_scan.md"
    write_json(json_path, payload)
    md_path.write_text(_build_markdown(payload), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
