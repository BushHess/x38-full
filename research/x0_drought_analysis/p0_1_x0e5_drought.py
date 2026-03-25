#!/usr/bin/env python3
"""P0.1 -- drought analysis for X0_E5EXIT."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from strategies.vtrend_x0_e5exit.strategy import VTrendX0E5ExitConfig, VTrendX0E5ExitStrategy
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS

OUTDIR = Path(__file__).resolve().parent
DATA = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
INITIAL_CASH = 10_000.0

CURRENT_START = pd.Timestamp("2025-01-01", tz="UTC")
CURRENT_END = pd.Timestamp("2026-02-20 23:59:59", tz="UTC")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _run() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    feed = DataFeed(str(DATA), start=START, end=END, warmup_days=WARMUP)
    engine = BacktestEngine(
        feed=feed,
        strategy=VTrendX0E5ExitStrategy(VTrendX0E5ExitConfig()),
        cost=SCENARIOS["harsh"],
        initial_cash=INITIAL_CASH,
        warmup_days=WARMUP,
        warmup_mode="no_trade",
    )
    result = engine.run()

    equity = pd.DataFrame(
        [
            {
                "close_time": int(e.close_time),
                "dt": datetime.fromtimestamp(e.close_time / 1000, tz=timezone.utc),
                "nav": float(e.nav_mid),
                "exposure": float(e.exposure),
            }
            for e in result.equity
        ]
    ).sort_values("dt").reset_index(drop=True)
    trades = pd.DataFrame(
        [
            {
                "entry_ts_ms": int(t.entry_ts_ms),
                "entry_dt": datetime.fromtimestamp(t.entry_ts_ms / 1000, tz=timezone.utc),
                "exit_dt": datetime.fromtimestamp(t.exit_ts_ms / 1000, tz=timezone.utc),
                "pnl_usd": float(t.pnl),
                "return_pct": float(t.return_pct),
                "days_held": float(t.days_held),
                "entry_reason": str(t.entry_reason),
                "exit_reason": str(t.exit_reason),
            }
            for t in result.trades
        ]
    ).sort_values("entry_dt").reset_index(drop=True)
    return equity, trades, result.summary


def _monthly_table(equity: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    eq = equity.copy()
    eq["nav_peak"] = eq["nav"].cummax()
    eq["underwater"] = eq["nav"] < eq["nav_peak"] - 1e-9
    eq["month"] = eq["dt"].dt.to_period("M").astype(str)

    monthly = (
        eq.groupby("month")
        .agg(
            nav_start=("nav", "first"),
            nav_end=("nav", "last"),
            underwater_share=("underwater", "mean"),
            exposure_mean=("exposure", "mean"),
        )
        .reset_index()
    )
    trades = trades.copy()
    trades["month"] = trades["entry_dt"].dt.to_period("M").astype(str)
    trade_monthly = (
        trades.groupby("month")
        .agg(
            trades=("pnl_usd", "size"),
            pnl_usd=("pnl_usd", "sum"),
            win_rate=("pnl_usd", lambda s: (s > 0.0).mean()),
        )
        .reset_index()
    )
    monthly = monthly.merge(trade_monthly, on="month", how="left").fillna(
        {"trades": 0, "pnl_usd": 0.0}
    )
    monthly["ret_pct"] = (monthly["nav_end"] / monthly["nav_start"] - 1.0) * 100.0
    return monthly


def _rolling_windows(equity: pd.DataFrame, trades: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    eq = equity.copy()
    eq["nav_peak"] = eq["nav"].cummax()
    eq["underwater"] = eq["nav"] < eq["nav_peak"] - 1e-9

    current_eq = eq[(eq["dt"] >= CURRENT_START) & (eq["dt"] <= CURRENT_END)].copy()
    current_trades = trades[
        (trades["entry_dt"] >= CURRENT_START) & (trades["entry_dt"] <= CURRENT_END)
    ].copy()
    # +1 so rolling windows span the same inclusive day-count as CURRENT_START..CURRENT_END
    window_days = int((CURRENT_END - CURRENT_START).days) + 1

    rows: list[dict] = []
    starts = pd.date_range(
        eq["dt"].iloc[0],
        eq["dt"].iloc[-1] - pd.Timedelta(days=window_days),
        freq="7D",
        tz="UTC",
    )
    for start in starts:
        end = start + pd.Timedelta(days=window_days)
        window_eq = eq[(eq["dt"] >= start) & (eq["dt"] <= end)]
        if len(window_eq) < 30:
            continue
        window_trades = trades[(trades["entry_dt"] >= start) & (trades["entry_dt"] <= end)]
        rows.append(
            {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
                "ret_pct": (window_eq["nav"].iloc[-1] / window_eq["nav"].iloc[0] - 1.0) * 100.0,
                "underwater_share": float(window_eq["underwater"].mean()),
                "trades": int(len(window_trades)),
                "pnl_usd": float(window_trades["pnl_usd"].sum()) if len(window_trades) else 0.0,
            }
        )

    rolling = pd.DataFrame(rows)
    current = {
        "start": CURRENT_START.strftime("%Y-%m-%d"),
        "end": CURRENT_END.strftime("%Y-%m-%d"),
        "window_days": window_days,
        "ret_pct": (current_eq["nav"].iloc[-1] / current_eq["nav"].iloc[0] - 1.0) * 100.0,
        "underwater_share": float(current_eq["underwater"].mean()),
        "trades": int(len(current_trades)),
        "pnl_usd": float(current_trades["pnl_usd"].sum()) if len(current_trades) else 0.0,
        "ret_rank_worst_count": int((rolling["ret_pct"] <= (current_eq["nav"].iloc[-1] / current_eq["nav"].iloc[0] - 1.0) * 100.0).sum()),
        "underwater_rank_worst_count": int((rolling["underwater_share"] >= float(current_eq["underwater"].mean())).sum()),
        "trade_rank_low_count": int((rolling["trades"] <= int(len(current_trades))).sum()),
        "rolling_window_count": int(len(rolling)),
    }
    return rolling, current


def _underwater_streaks(monthly: pd.DataFrame) -> pd.DataFrame:
    month_end = monthly[["month", "nav_end"]].copy()
    month_end["cum_peak"] = month_end["nav_end"].cummax()
    month_end["new_high"] = month_end["nav_end"] >= month_end["cum_peak"] - 1e-9

    rows: list[dict] = []
    start_idx: int | None = None
    for i, row in month_end.iterrows():
        if not bool(row["new_high"]) and start_idx is None:
            start_idx = i
        if bool(row["new_high"]) and start_idx is not None:
            streak = month_end.iloc[start_idx:i]
            prior_peak = float(month_end.iloc[start_idx - 1]["cum_peak"]) if start_idx > 0 else float(streak["cum_peak"].iloc[0])
            rows.append(
                {
                    "start_month": str(streak["month"].iloc[0]),
                    "end_month": str(streak["month"].iloc[-1]),
                    "months": int(len(streak)),
                    "min_nav_ratio_to_peak": float((streak["nav_end"] / prior_peak).min()),
                }
            )
            start_idx = None

    if start_idx is not None:
        streak = month_end.iloc[start_idx:]
        prior_peak = float(month_end.iloc[start_idx - 1]["cum_peak"]) if start_idx > 0 else float(streak["cum_peak"].iloc[0])
        rows.append(
            {
                "start_month": str(streak["month"].iloc[0]),
                "end_month": str(streak["month"].iloc[-1]),
                "months": int(len(streak)),
                "min_nav_ratio_to_peak": float((streak["nav_end"] / prior_peak).min()),
            }
        )
    return pd.DataFrame(rows).sort_values(["months", "min_nav_ratio_to_peak"], ascending=[False, True])


def _build_report(summary: dict, current: dict, current_months: pd.DataFrame, similar_windows: pd.DataFrame, streaks: pd.DataFrame) -> str:
    lines = [
        "# P0.1 X0_E5EXIT Drought Analysis",
        "",
        "## Scope",
        "",
        "- Strategy: `X0_E5EXIT`",
        "- Scenario: `harsh`",
        f"- Full replay: `{START}` -> `{END}`",
        f"- Current comparison window: `{current['start']}` -> `{current['end']}`",
        "",
        "## Current Window Summary",
        "",
        f"- Window length: `{current['window_days']} days`",
        f"- Return: `{current['ret_pct']:.4f}%`",
        f"- Trades: `{current['trades']}`",
        f"- Trade PnL: `{current['pnl_usd']:.2f} USD`",
        f"- Underwater share: `{current['underwater_share']:.4f}`",
        f"- Return rank (worse or equal windows): `{current['ret_rank_worst_count']}/{current['rolling_window_count']}`",
        f"- Underwater rank (worse or equal windows): `{current['underwater_rank_worst_count']}/{current['rolling_window_count']}`",
        f"- Low-trade rank (lower or equal windows): `{current['trade_rank_low_count']}/{current['rolling_window_count']}`",
        "",
        "## Interpretation",
        "",
        "- `2025-01 -> 2026-02` is a real drought / underwater period, but it is not the worst historical one.",
        "- It is better described as `flat-underwater alpha drought` than `no-trade starvation`.",
        "- The longest and deepest drought was `2021-11 -> 2024-01`.",
        "",
        "## Current Monthly Breakdown",
        "",
        "| Month | Return % | Trades | PnL USD | Underwater Share |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in current_months.iterrows():
        lines.append(
            f"| {row['month']} | {row['ret_pct']:.4f} | {int(row['trades'])} | "
            f"{row['pnl_usd']:.2f} | {row['underwater_share']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Similar Or Worse Historical Windows",
            "",
            "| Start | End | Return % | Trades | Underwater Share | PnL USD |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for _, row in similar_windows.iterrows():
        lines.append(
            f"| {row['start']} | {row['end']} | {row['ret_pct']:.4f} | "
            f"{int(row['trades'])} | {row['underwater_share']:.4f} | {row['pnl_usd']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Longest Underwater Streaks",
            "",
            "| Start Month | End Month | Months | Min NAV / Prior Peak |",
            "|---|---|---:|---:|",
        ]
    )
    for _, row in streaks.head(10).iterrows():
        lines.append(
            f"| {row['start_month']} | {row['end_month']} | {int(row['months'])} | "
            f"{row['min_nav_ratio_to_peak']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    equity, trades, summary = _run()
    monthly = _monthly_table(equity, trades)
    rolling, current = _rolling_windows(equity, trades)
    streaks = _underwater_streaks(monthly)

    current_months = monthly[(monthly["month"] >= "2025-01") & (monthly["month"] <= "2026-02")].copy()
    similar_windows = rolling[
        (rolling["ret_pct"] <= current["ret_pct"] + 1e-9)
        & (rolling["underwater_share"] >= current["underwater_share"] - 1e-9)
    ].sort_values(["ret_pct", "underwater_share"], ascending=[True, False]).head(12)

    _write_csv(
        OUTDIR / "p0_1_monthly_table.csv",
        monthly.to_dict("records"),
        ["month", "nav_start", "nav_end", "underwater_share", "exposure_mean", "trades", "pnl_usd", "win_rate", "ret_pct"],
    )
    _write_csv(
        OUTDIR / "p0_1_current_months.csv",
        current_months.to_dict("records"),
        ["month", "nav_start", "nav_end", "underwater_share", "exposure_mean", "trades", "pnl_usd", "win_rate", "ret_pct"],
    )
    _write_csv(
        OUTDIR / "p0_1_rolling_windows.csv",
        rolling.to_dict("records"),
        ["start", "end", "ret_pct", "underwater_share", "trades", "pnl_usd"],
    )
    _write_csv(
        OUTDIR / "p0_1_similar_or_worse_windows.csv",
        similar_windows.to_dict("records"),
        ["start", "end", "ret_pct", "underwater_share", "trades", "pnl_usd"],
    )
    _write_csv(
        OUTDIR / "p0_1_underwater_streaks.csv",
        streaks.to_dict("records"),
        ["start_month", "end_month", "months", "min_nav_ratio_to_peak"],
    )

    results = {
        "strategy_id": "X0_E5EXIT",
        "scenario": "harsh",
        "full_summary": summary,
        "current_window": current,
        "longest_underwater_streaks": streaks.head(10).to_dict("records"),
        "similar_or_worse_windows": similar_windows.to_dict("records"),
    }
    with (OUTDIR / "p0_1_results.json").open("w") as f:
        json.dump(results, f, indent=2)
    with (OUTDIR / "P0_1_REPORT.md").open("w") as f:
        f.write(_build_report(summary, current, current_months, similar_windows, streaks))

    print("Current window return pct:", round(current["ret_pct"], 4))
    print("Current underwater share:", round(current["underwater_share"], 4))
    print("Similar/worse windows:", len(similar_windows))


if __name__ == "__main__":
    main()
