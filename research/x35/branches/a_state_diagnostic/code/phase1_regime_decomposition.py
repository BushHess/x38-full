"""Phase 1 state-map and baseline trade decomposition for x35 a_state_diagnostic."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT))

from research.x35.shared.common import attach_state_to_events  # noqa: E402
from research.x35.shared.common import bars_to_frame  # noqa: E402
from research.x35.shared.common import ensure_dir  # noqa: E402
from research.x35.shared.common import load_feed  # noqa: E402
from research.x35.shared.common import pct  # noqa: E402
from research.x35.shared.common import safe_div  # noqa: E402
from research.x35.shared.common import ts_to_date  # noqa: E402
from research.x35.shared.common import write_json  # noqa: E402
from research.x35.shared.state_definitions import FROZEN_SPECS  # noqa: E402
from research.x35.shared.state_definitions import build_state_series  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Config  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy  # noqa: E402
from v10.core.engine import BacktestEngine  # noqa: E402
from v10.core.types import SCENARIOS  # noqa: E402

RESULTS_DIR = ensure_dir(Path(__file__).resolve().parents[1] / "results")


def trades_to_frame(trades: list) -> pd.DataFrame:
    rows = []
    for trade in trades:
        rows.append(
            {
                "trade_id": int(trade.trade_id),
                "entry_ts_ms": int(trade.entry_ts_ms),
                "exit_ts_ms": int(trade.exit_ts_ms),
                "entry_date": ts_to_date(int(trade.entry_ts_ms)),
                "exit_date": ts_to_date(int(trade.exit_ts_ms)),
                "pnl": float(trade.pnl),
                "return_pct": float(trade.return_pct),
                "days_held": float(trade.days_held),
                "entry_reason": str(trade.entry_reason),
                "exit_reason": str(trade.exit_reason),
            }
        )
    return pd.DataFrame(rows).sort_values("entry_ts_ms").reset_index(drop=True)


def _series_mean(series: pd.Series) -> float:
    return 0.0 if series.empty else float(series.mean())


def _series_median(series: pd.Series) -> float:
    return 0.0 if series.empty else float(series.median())


def _win_rate_pct(frame: pd.DataFrame) -> float:
    return 0.0 if frame.empty else float((frame["pnl"] > 0).mean() * 100.0)


def compute_spell_days(mapped_d1: pd.DataFrame) -> list[int]:
    if mapped_d1.empty:
        return []

    states = mapped_d1["state"].ffill().astype(int).to_numpy()
    dates = mapped_d1["dt_close"].dt.date.to_list()

    lengths: list[int] = []
    start_idx = 0
    for idx in range(1, len(states)):
        if states[idx] != states[idx - 1]:
            spell_days = (dates[idx - 1] - dates[start_idx]).days + 1
            lengths.append(int(spell_days))
            start_idx = idx

    final_days = (dates[-1] - dates[start_idx]).days + 1
    lengths.append(int(final_days))
    return lengths


def fold_diagnostics(mapped_trades: pd.DataFrame, n_folds: int = 8) -> tuple[int, int, list[dict[str, float | int | None]]]:
    ordered = mapped_trades.sort_values("entry_ts_ms").reset_index(drop=True)
    index_chunks = np.array_split(ordered.index.to_numpy(), n_folds)
    valid_folds = 0
    wins = 0
    details = []

    for idx, chunk in enumerate(index_chunks, start=1):
        fold = ordered.loc[chunk].copy()
        on = fold.loc[fold["state"] == 1, "return_pct"]
        off = fold.loc[fold["state"] == 0, "return_pct"]

        if len(on) >= 3 and len(off) >= 3:
            valid_folds += 1
            delta = float(on.mean() - off.mean())
            win = int(delta > 0)
            wins += win
            details.append(
                {
                    "fold": idx,
                    "risk_on_trades": int(len(on)),
                    "risk_off_trades": int(len(off)),
                    "delta_mean_return_pct": round(delta, 4),
                    "risk_on_wins": win,
                }
            )
        else:
            details.append(
                {
                    "fold": idx,
                    "risk_on_trades": int(len(on)),
                    "risk_off_trades": int(len(off)),
                    "delta_mean_return_pct": None,
                    "risk_on_wins": None,
                }
            )

    return valid_folds, wins, details


def evaluate_spec(
    spec_id: str,
    mapped_d1: pd.DataFrame,
    mapped_trades: pd.DataFrame,
    warmup_ok: bool,
) -> dict:
    state_series = mapped_d1["state"].ffill().astype(int)
    risk_on_fraction = float(state_series.mean())
    flips_total = int((state_series.diff().fillna(0) != 0).sum())
    span_years = max(
        (mapped_d1["dt_close"].iloc[-1] - mapped_d1["dt_close"].iloc[0]).days / 365.25,
        1e-9,
    )
    flips_per_year = float(flips_total / span_years)
    spell_days = compute_spell_days(mapped_d1)
    median_spell_days = float(np.median(spell_days)) if spell_days else 0.0

    on = mapped_trades[mapped_trades["state"] == 1].copy()
    off = mapped_trades[mapped_trades["state"] == 0].copy()

    pos_total = float(mapped_trades.loc[mapped_trades["pnl"] > 0, "pnl"].sum())
    neg_total = float(-mapped_trades.loc[mapped_trades["pnl"] < 0, "pnl"].sum())
    profit_share_on = safe_div(float(on.loc[on["pnl"] > 0, "pnl"].sum()), pos_total)
    loss_share_off = safe_div(float(-off.loc[off["pnl"] < 0, "pnl"].sum()), neg_total)

    valid_folds, fold_wins, fold_rows = fold_diagnostics(mapped_trades)
    fold_win_rate = safe_div(fold_wins, valid_folds)

    gates = {
        "D0_warmup": bool(warmup_ok),
        "D1_persistence": bool(flips_per_year <= 12.0 and median_spell_days >= 14.0),
        "D2_trade_split": bool(len(on) >= 20 and len(off) >= 20),
        "D3_sign_separation": bool(on["return_pct"].mean() > 0 and off["return_pct"].mean() < 0),
        "D4_concentration": bool(profit_share_on >= 0.70 and loss_share_off >= 0.55),
        "D5_stability": bool(valid_folds >= 5 and fold_win_rate >= 0.625),
    }

    return {
        "spec_id": spec_id,
        "calendar": {
            "risk_on_fraction": round(risk_on_fraction, 4),
            "risk_on_fraction_pct": pct(risk_on_fraction),
            "flips_total": flips_total,
            "flips_per_year": round(flips_per_year, 3),
            "median_spell_days": round(median_spell_days, 1),
        },
        "trade_split": {
            "risk_on_trades": int(len(on)),
            "risk_off_trades": int(len(off)),
            "risk_on_mean_return_pct": round(_series_mean(on["return_pct"]), 4),
            "risk_off_mean_return_pct": round(_series_mean(off["return_pct"]), 4),
            "risk_on_median_return_pct": round(_series_median(on["return_pct"]), 4),
            "risk_off_median_return_pct": round(_series_median(off["return_pct"]), 4),
            "risk_on_win_rate_pct": round(_win_rate_pct(on), 2),
            "risk_off_win_rate_pct": round(_win_rate_pct(off), 2),
        },
        "concentration": {
            "profit_share_on": round(profit_share_on, 4),
            "profit_share_on_pct": pct(profit_share_on),
            "loss_share_off": round(loss_share_off, 4),
            "loss_share_off_pct": pct(loss_share_off),
        },
        "stability": {
            "valid_folds": valid_folds,
            "fold_wins": fold_wins,
            "fold_win_rate": round(fold_win_rate, 4),
            "fold_win_rate_pct": pct(fold_win_rate),
            "fold_details": fold_rows,
        },
        "gates": gates,
        "advance_to_overlay": all(gates.values()),
    }


def build_markdown(payload: dict) -> str:
    lines = [
        "# X35 Phase 1 Regime Decomposition",
        "",
        "## Baseline",
        "",
        f"- Strategy: `{payload['baseline']['strategy']}`",
        f"- Trades: `{payload['baseline']['trades']}`",
        f"- Sharpe: `{payload['baseline']['sharpe']}`",
        f"- CAGR %: `{payload['baseline']['cagr_pct']}`",
        f"- MDD %: `{payload['baseline']['max_drawdown_mid_pct']}`",
        f"- Study verdict: `{payload['study_verdict']}`",
        "",
        "## Candidate Summary",
        "",
        "| Spec | Risk-on % | Flips/yr | Median spell days | On trades | Off trades | On mean % | Off mean % | Profit on % | Loss off % | Fold WR % | Advance |",
        "|------|-----------|----------|-------------------|-----------|------------|-----------|------------|-------------|------------|-----------|---------|",
    ]

    for row in payload["candidates"]:
        lines.append(
            f"| `{row['spec_id']}` | {row['calendar']['risk_on_fraction_pct']} | "
            f"{row['calendar']['flips_per_year']} | {row['calendar']['median_spell_days']} | "
            f"{row['trade_split']['risk_on_trades']} | {row['trade_split']['risk_off_trades']} | "
            f"{row['trade_split']['risk_on_mean_return_pct']} | {row['trade_split']['risk_off_mean_return_pct']} | "
            f"{row['concentration']['profit_share_on_pct']} | {row['concentration']['loss_share_off_pct']} | "
            f"{row['stability']['fold_win_rate_pct']} | {row['advance_to_overlay']} |"
        )

    lines.extend(["", "## Gate Detail", ""])
    for row in payload["candidates"]:
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

    strategy = VTrendE5Ema21D1Strategy(VTrendE5Ema21D1Config())
    engine = BacktestEngine(
        feed=feed,
        strategy=strategy,
        cost=SCENARIOS["harsh"],
        initial_cash=10_000.0,
        warmup_mode="no_trade",
    )
    result = engine.run()
    trades_df = trades_to_frame(result.trades)

    candidates = []
    warmup_lookup = {}
    for spec in FROZEN_SPECS:
        state_periods = build_state_series(d1_df, spec, report_start_ms)
        pre_report_bars = int((state_periods["close_time"] < report_start_ms).sum())
        warmup_lookup[spec.spec_id] = pre_report_bars >= spec.required_warmup_bars

        mapped_d1 = attach_state_to_events(
            d1_report[["close_time", "dt_close"]].copy(),
            state_periods[["close_time", "state", "state_label"]].copy(),
            event_time_col="close_time",
        )
        mapped_trades = attach_state_to_events(
            trades_df.copy(),
            state_periods[["close_time", "state", "state_label"]].copy(),
            event_time_col="entry_ts_ms",
        )
        mapped_trades = mapped_trades.dropna(subset=["state"]).copy()
        mapped_trades["state"] = mapped_trades["state"].astype(int)

        candidates.append(
            evaluate_spec(
                spec.spec_id,
                mapped_d1=mapped_d1.dropna(subset=["state"]).copy(),
                mapped_trades=mapped_trades,
                warmup_ok=warmup_lookup[spec.spec_id],
            )
        )

    candidates.sort(
        key=lambda row: (
            sum(bool(v) for v in row["gates"].values()),
            row["concentration"]["profit_share_on"],
            row["concentration"]["loss_share_off"],
            row["stability"]["fold_win_rate"],
        ),
        reverse=True,
    )

    baseline = {
        "strategy": "VTrendE5Ema21D1Strategy",
        "sharpe": round(float(result.summary.get("sharpe", 0.0)), 4),
        "cagr_pct": round(float(result.summary.get("cagr_pct", 0.0)), 2),
        "max_drawdown_mid_pct": round(float(result.summary.get("max_drawdown_mid_pct", 0.0)), 2),
        "trades": int(result.summary.get("trades", len(result.trades))),
    }
    any_advance = any(row["advance_to_overlay"] for row in candidates)
    payload = {
        "study_id": "x35_long_horizon_regime",
        "baseline": baseline,
        "candidate_count": len(candidates),
        "study_verdict": "GO_CURRENT_MENU" if any_advance else "NO_GO_CURRENT_MENU",
        "candidates": candidates,
    }

    json_path = RESULTS_DIR / "phase1_regime_decomposition.json"
    md_path = RESULTS_DIR / "phase1_regime_decomposition.md"
    write_json(json_path, payload)
    md_path.write_text(build_markdown(payload), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
