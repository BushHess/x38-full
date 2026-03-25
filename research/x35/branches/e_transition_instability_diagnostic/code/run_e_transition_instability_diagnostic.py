"""Run transition / instability state survey for x35."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT))

from research.x35.shared.common import aggregate_outer_bars  # noqa: E402
from research.x35.shared.common import attach_state_to_events  # noqa: E402
from research.x35.shared.common import bars_to_frame  # noqa: E402
from research.x35.shared.common import ensure_dir  # noqa: E402
from research.x35.shared.common import load_feed  # noqa: E402
from research.x35.shared.common import pct  # noqa: E402
from research.x35.shared.common import safe_div  # noqa: E402
from research.x35.shared.common import write_json  # noqa: E402
from research.x35.shared.weekly_instability_states import build_weekly_instability_states  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Config  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy  # noqa: E402
from v10.core.engine import BacktestEngine  # noqa: E402
from v10.core.types import SCENARIOS  # noqa: E402

RESULTS_DIR = ensure_dir(Path(__file__).resolve().parents[1] / "results")


def _trades_to_frame(trades: list) -> pd.DataFrame:
    rows = []
    for trade in trades:
        rows.append(
            {
                "trade_id": int(trade.trade_id),
                "entry_ts_ms": int(trade.entry_ts_ms),
                "exit_ts_ms": int(trade.exit_ts_ms),
                "pnl": float(trade.pnl),
                "return_pct": float(trade.return_pct),
                "days_held": float(trade.days_held),
            }
        )
    return pd.DataFrame(rows).sort_values("entry_ts_ms").reset_index(drop=True)


def _compute_spell_days(mapped_d1: pd.DataFrame) -> list[int]:
    if mapped_d1.empty:
        return []

    states = mapped_d1["state"].ffill().astype(int).to_numpy()
    dates = mapped_d1["dt_close"].dt.date.to_list()
    lengths: list[int] = []
    start_idx = 0

    for idx in range(1, len(states)):
        if states[idx] != states[idx - 1]:
            lengths.append((dates[idx - 1] - dates[start_idx]).days + 1)
            start_idx = idx

    lengths.append((dates[-1] - dates[start_idx]).days + 1)
    return lengths


def _fold_diagnostics(mapped_trades: pd.DataFrame) -> tuple[int, int, list[dict[str, float | int | None]]]:
    ordered = mapped_trades.sort_values("entry_ts_ms").reset_index(drop=True)
    chunks = np.array_split(ordered.index.to_numpy(), 8)
    valid_folds = 0
    wins = 0
    details = []

    for idx, chunk in enumerate(chunks, start=1):
        fold = ordered.loc[chunk].copy()
        stable = fold.loc[fold["state"] == 0, "return_pct"]
        unstable = fold.loc[fold["state"] == 1, "return_pct"]

        if len(stable) >= 3 and len(unstable) >= 3:
            valid_folds += 1
            delta = float(stable.mean() - unstable.mean())
            win = int(delta > 0.0)
            wins += win
            details.append(
                {
                    "fold": idx,
                    "stable_trades": int(len(stable)),
                    "unstable_trades": int(len(unstable)),
                    "delta_mean_return_pct": round(delta, 4),
                    "stable_beats_unstable": win,
                }
            )
        else:
            details.append(
                {
                    "fold": idx,
                    "stable_trades": int(len(stable)),
                    "unstable_trades": int(len(unstable)),
                    "delta_mean_return_pct": None,
                    "stable_beats_unstable": None,
                }
            )

    return valid_folds, wins, details


def _evaluate_spec(
    spec_id: str,
    mapped_d1: pd.DataFrame,
    mapped_trades: pd.DataFrame,
    *,
    warmup_ok: bool,
) -> dict:
    state_series = mapped_d1["state"].ffill().astype(int)
    unstable_fraction = float(state_series.mean())
    flips_total = int((state_series.diff().fillna(0) != 0).sum())
    span_years = max(
        (mapped_d1["dt_close"].iloc[-1] - mapped_d1["dt_close"].iloc[0]).days / 365.25,
        1e-9,
    )
    flips_per_year = float(flips_total / span_years)
    spell_days = _compute_spell_days(mapped_d1)
    median_spell_days = float(np.median(spell_days)) if spell_days else 0.0

    stable = mapped_trades[mapped_trades["state"] == 0].copy()
    unstable = mapped_trades[mapped_trades["state"] == 1].copy()

    pos_total = float(mapped_trades.loc[mapped_trades["pnl"] > 0, "pnl"].sum())
    neg_total = float(-mapped_trades.loc[mapped_trades["pnl"] < 0, "pnl"].sum())
    profit_share_stable = safe_div(float(stable.loc[stable["pnl"] > 0, "pnl"].sum()), pos_total)
    loss_share_unstable = safe_div(float(-unstable.loc[unstable["pnl"] < 0, "pnl"].sum()), neg_total)

    valid_folds, fold_wins, fold_rows = _fold_diagnostics(mapped_trades)
    fold_win_rate = safe_div(fold_wins, valid_folds)

    gates = {
        "D0_warmup": bool(warmup_ok),
        "D1_persistence": bool(flips_per_year <= 20.0 and median_spell_days >= 7.0),
        "D2_trade_split": bool(len(stable) >= 20 and len(unstable) >= 20),
        "D3_sign_separation": bool(stable["return_pct"].mean() > 0 and unstable["return_pct"].mean() < 0),
        "D4_concentration": bool(profit_share_stable >= 0.70 and loss_share_unstable >= 0.55),
        "D5_stability": bool(valid_folds >= 5 and fold_win_rate >= 0.625),
    }

    return {
        "spec_id": spec_id,
        "calendar": {
            "unstable_fraction": round(unstable_fraction, 4),
            "unstable_fraction_pct": pct(unstable_fraction),
            "flips_total": flips_total,
            "flips_per_year": round(flips_per_year, 3),
            "median_spell_days": round(median_spell_days, 1),
        },
        "trade_split": {
            "stable_trades": int(len(stable)),
            "unstable_trades": int(len(unstable)),
            "stable_mean_return_pct": round(float(stable["return_pct"].mean()), 4),
            "unstable_mean_return_pct": round(float(unstable["return_pct"].mean()), 4),
            "stable_win_rate_pct": round(float((stable["pnl"] > 0).mean() * 100.0), 2),
            "unstable_win_rate_pct": round(float((unstable["pnl"] > 0).mean() * 100.0), 2),
        },
        "concentration": {
            "profit_share_stable": round(profit_share_stable, 4),
            "profit_share_stable_pct": pct(profit_share_stable),
            "loss_share_unstable": round(loss_share_unstable, 4),
            "loss_share_unstable_pct": pct(loss_share_unstable),
        },
        "stability": {
            "valid_folds": valid_folds,
            "fold_wins": fold_wins,
            "fold_win_rate": round(fold_win_rate, 4),
            "fold_win_rate_pct": pct(fold_win_rate),
            "fold_details": fold_rows,
        },
        "gates": gates,
        "promising": all(gates.values()),
    }


def _build_markdown(payload: dict) -> str:
    lines = [
        "# X35 Transition / Instability Scan",
        "",
        "## Baseline",
        "",
        f"- Strategy: `{payload['baseline']['strategy']}`",
        f"- Trades: `{payload['baseline']['trades']}`",
        f"- Sharpe: `{payload['baseline']['sharpe']}`",
        f"- CAGR %: `{payload['baseline']['cagr_pct']}`",
        f"- MDD %: `{payload['baseline']['max_drawdown_mid_pct']}`",
        f"- Warmup weeks before report: `{payload['warmup']['pre_report_weeks']}`",
        f"- Branch verdict: `{payload['branch_verdict']}`",
        "",
        "## Spec Summary",
        "",
        "| Spec | Unstable % | Flips/yr | Median spell days | Stable trades | Unstable trades | Stable mean % | Unstable mean % | Profit stable % | Loss unstable % | Fold WR % | Promising |",
        "|------|------------|----------|-------------------|---------------|-----------------|---------------|-----------------|-----------------|-----------------|-----------|-----------|",
    ]

    for row in payload["specs"]:
        lines.append(
            f"| `{row['spec_id']}` | {row['calendar']['unstable_fraction_pct']} | {row['calendar']['flips_per_year']} | "
            f"{row['calendar']['median_spell_days']} | {row['trade_split']['stable_trades']} | {row['trade_split']['unstable_trades']} | "
            f"{row['trade_split']['stable_mean_return_pct']} | {row['trade_split']['unstable_mean_return_pct']} | "
            f"{row['concentration']['profit_share_stable_pct']} | {row['concentration']['loss_share_unstable_pct']} | "
            f"{row['stability']['fold_win_rate_pct']} | {row['promising']} |"
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

    d1_df = bars_to_frame(feed.d1_bars, report_start_ms)
    d1_report = d1_df[d1_df["in_report"]].copy()
    weekly = aggregate_outer_bars(d1_df, "W1")
    pre_report_weeks = int((weekly["close_time"] < report_start_ms).sum())
    warmup_ok = pre_report_weeks >= 52

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

    states = build_weekly_instability_states(d1_df)
    spec_rows = []

    for spec_id, state_df in states.items():
        mapped_d1 = attach_state_to_events(
            d1_report[["close_time", "dt_close"]].copy(),
            state_df[["close_time", "state", "state_label"]].copy(),
            event_time_col="close_time",
        ).dropna(subset=["state"]).copy()
        mapped_d1["state"] = mapped_d1["state"].astype(int)

        mapped_trades = attach_state_to_events(
            trades_df.copy(),
            state_df[["close_time", "state", "state_label"]].copy(),
            event_time_col="entry_ts_ms",
        ).dropna(subset=["state"]).copy()
        mapped_trades["state"] = mapped_trades["state"].astype(int)

        spec_rows.append(
            _evaluate_spec(
                spec_id,
                mapped_d1=mapped_d1,
                mapped_trades=mapped_trades,
                warmup_ok=warmup_ok,
            )
        )

    spec_rows.sort(
        key=lambda row: (
            sum(bool(v) for v in row["gates"].values()),
            row["concentration"]["loss_share_unstable"],
            row["stability"]["fold_win_rate"],
        ),
        reverse=True,
    )

    payload = {
        "study_id": "x35_long_horizon_regime",
        "branch": "e_transition_instability_diagnostic",
        "branch_verdict": "GO_F4_TRANSITION_FAMILY" if any(row["promising"] for row in spec_rows) else "NO_GO_F4_TRANSITION_FAMILY",
        "warmup": {
            "pre_report_weeks": pre_report_weeks,
            "warmup_ok": warmup_ok,
        },
        "baseline": {
            "strategy": "VTrendE5Ema21D1Strategy",
            "trades": int(result.summary.get("trades", len(result.trades))),
            "sharpe": round(float(result.summary.get("sharpe", 0.0)), 4),
            "cagr_pct": round(float(result.summary.get("cagr_pct", 0.0)), 2),
            "max_drawdown_mid_pct": round(float(result.summary.get("max_drawdown_mid_pct", 0.0)), 2),
        },
        "specs": spec_rows,
    }

    json_path = RESULTS_DIR / "transition_instability_scan.json"
    md_path = RESULTS_DIR / "transition_instability_scan.md"
    write_json(json_path, payload)
    md_path.write_text(_build_markdown(payload), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
