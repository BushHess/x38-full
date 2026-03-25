"""Run multi-horizon trend state survey for x35."""

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
from research.x35.shared.common import safe_div  # noqa: E402
from research.x35.shared.common import write_json  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Config  # noqa: E402
from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy  # noqa: E402
from v10.core.engine import BacktestEngine  # noqa: E402
from v10.core.types import SCENARIOS  # noqa: E402

RESULTS_DIR = ensure_dir(Path(__file__).resolve().parents[1] / "results")

FEATURE_ORDER = (
    "wk_gap_13_26",
    "wk_gap_26_52",
    "wk_alignment_score_13_26_52",
)


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


def _build_weekly_trend_features(d1_df: pd.DataFrame) -> pd.DataFrame:
    weekly = aggregate_outer_bars(d1_df, "W1").copy()
    weekly["ema13"] = weekly["close"].ewm(span=13, adjust=False).mean()
    weekly["ema26"] = weekly["close"].ewm(span=26, adjust=False).mean()
    weekly["ema52"] = weekly["close"].ewm(span=52, adjust=False).mean()

    weekly["wk_gap_13_26"] = weekly["ema13"] / weekly["ema26"] - 1.0
    weekly["wk_gap_26_52"] = weekly["ema26"] / weekly["ema52"] - 1.0
    weekly["wk_alignment_score_13_26_52"] = (
        (weekly["close"] > weekly["ema26"]).astype(int)
        + (weekly["ema13"] > weekly["ema26"]).astype(int)
        + (weekly["ema26"] > weekly["ema52"]).astype(int)
    )
    return weekly


def _ordered_bucket_config(feature: str) -> tuple[list[str], callable]:
    if feature == "wk_alignment_score_13_26_52":
        labels = ["S0", "S1", "S2", "S3"]

        def assign(series: pd.Series) -> pd.Series:
            mapping = {0: "S0", 1: "S1", 2: "S2", 3: "S3"}
            return series.round().astype("Int64").map(mapping)

        return labels, assign

    labels = ["Q1", "Q2", "Q3", "Q4"]

    def assign(series: pd.Series) -> pd.Series:
        clean = series.dropna()
        quantiles = clean.quantile([0.25, 0.50, 0.75]).to_list()
        bins = [-np.inf, quantiles[0], quantiles[1], quantiles[2], np.inf]
        return pd.cut(series, bins=bins, labels=labels, include_lowest=True, duplicates="drop")

    return labels, assign


def _compute_spell_stats(labels: pd.Series, dates: pd.Series) -> tuple[int, float]:
    clean = pd.DataFrame({"label": labels, "dt_close": dates}).dropna().copy()
    if clean.empty:
        return 0, 0.0

    values = clean["label"].astype(str).to_list()
    day_values = clean["dt_close"].dt.date.to_list()
    flips = 0
    spell_lengths: list[int] = []
    start_idx = 0

    for idx in range(1, len(values)):
        if values[idx] != values[idx - 1]:
            flips += 1
            spell_lengths.append((day_values[idx - 1] - day_values[start_idx]).days + 1)
            start_idx = idx

    spell_lengths.append((day_values[-1] - day_values[start_idx]).days + 1)
    median_spell = float(np.median(spell_lengths)) if spell_lengths else 0.0
    return flips, median_spell


def _fold_stability(
    frame: pd.DataFrame,
    bucket_col: str,
    bottom_label: str,
    top_label: str,
) -> tuple[int, int, list[dict[str, float | int | None]]]:
    ordered = frame.sort_values("entry_ts_ms").reset_index(drop=True)
    chunks = np.array_split(ordered.index.to_numpy(), 8)
    valid_folds = 0
    wins = 0
    details: list[dict[str, float | int | None]] = []

    for fold_idx, chunk in enumerate(chunks, start=1):
        fold = ordered.loc[chunk].copy()
        top = fold.loc[fold[bucket_col] == top_label, "return_pct"]
        bottom = fold.loc[fold[bucket_col] == bottom_label, "return_pct"]

        if len(top) >= 3 and len(bottom) >= 3:
            valid_folds += 1
            delta = float(top.mean() - bottom.mean())
            win = int(delta > 0.0)
            wins += win
            details.append(
                {
                    "fold": fold_idx,
                    "top_trades": int(len(top)),
                    "bottom_trades": int(len(bottom)),
                    "delta_mean_return_pct": round(delta, 4),
                    "top_beats_bottom": win,
                }
            )
        else:
            details.append(
                {
                    "fold": fold_idx,
                    "top_trades": int(len(top)),
                    "bottom_trades": int(len(bottom)),
                    "delta_mean_return_pct": None,
                    "top_beats_bottom": None,
                }
            )

    return valid_folds, wins, details


def _feature_summary(
    feature: str,
    mapped_d1: pd.DataFrame,
    mapped_trades: pd.DataFrame,
    *,
    warmup_ok: bool,
) -> dict:
    labels, assign_bucket = _ordered_bucket_config(feature)
    bottom_label, top_label = labels[0], labels[-1]

    d1_frame = mapped_d1[["close_time", "dt_close", feature]].dropna().copy()
    d1_frame["bucket"] = assign_bucket(d1_frame[feature])
    d1_frame = d1_frame.dropna(subset=["bucket"]).copy()

    trade_frame = mapped_trades[["trade_id", "entry_ts_ms", "pnl", "return_pct", feature]].dropna().copy()
    trade_frame["bucket"] = assign_bucket(trade_frame[feature])
    trade_frame = trade_frame.dropna(subset=["bucket"]).copy()

    bucket_rows = []
    for label in labels:
        subset = trade_frame[trade_frame["bucket"] == label].copy()
        loss_sum = float(-subset.loc[subset["pnl"] < 0, "pnl"].sum())
        profit_sum = float(subset.loc[subset["pnl"] > 0, "pnl"].sum())
        bucket_rows.append(
            {
                "bucket": label,
                "n_trades": int(len(subset)),
                "mean_return_pct": round(float(subset["return_pct"].mean()), 4),
                "median_return_pct": round(float(subset["return_pct"].median()), 4),
                "win_rate_pct": round(float((subset["pnl"] > 0).mean() * 100.0), 2),
                "profit_sum": round(profit_sum, 2),
                "loss_sum": round(loss_sum, 2),
            }
        )

    bottom_row = next(row for row in bucket_rows if row["bucket"] == bottom_label)
    top_row = next(row for row in bucket_rows if row["bucket"] == top_label)
    total_profit = float(trade_frame.loc[trade_frame["pnl"] > 0, "pnl"].sum())
    total_loss = float(-trade_frame.loc[trade_frame["pnl"] < 0, "pnl"].sum())
    profit_share_top = safe_div(top_row["profit_sum"], total_profit)
    loss_share_bottom = safe_div(bottom_row["loss_sum"], total_loss)
    rho = float(trade_frame[feature].corr(trade_frame["return_pct"], method="spearman"))

    flips_total, median_spell_days = _compute_spell_stats(d1_frame["bucket"], d1_frame["dt_close"])
    span_years = max(
        (d1_frame["dt_close"].iloc[-1] - d1_frame["dt_close"].iloc[0]).days / 365.25,
        1e-9,
    )
    flips_per_year = float(flips_total / span_years)

    valid_folds, fold_wins, fold_rows = _fold_stability(trade_frame, "bucket", bottom_label, top_label)
    fold_win_rate = safe_div(fold_wins, valid_folds)

    delta_mean = float(top_row["mean_return_pct"] - bottom_row["mean_return_pct"])
    delta_win_rate = float(top_row["win_rate_pct"] - bottom_row["win_rate_pct"])

    promising = bool(
        warmup_ok
        and flips_per_year <= 18.0
        and median_spell_days >= 14.0
        and bottom_row["n_trades"] >= 20
        and top_row["n_trades"] >= 20
        and rho > 0.0
        and top_row["mean_return_pct"] > 0.0
        and delta_mean >= 2.0
        and delta_win_rate >= 10.0
        and (profit_share_top >= 0.35 or loss_share_bottom >= 0.40)
        and valid_folds >= 5
        and fold_win_rate >= 0.625
    )

    return {
        "feature": feature,
        "warmup_ok": warmup_ok,
        "calendar": {
            "flips_total": int(flips_total),
            "flips_per_year": round(flips_per_year, 3),
            "median_spell_days": round(median_spell_days, 1),
        },
        "trade_split": {
            "bottom_bucket": bottom_label,
            "top_bucket": top_label,
            "n_bottom": int(bottom_row["n_trades"]),
            "n_top": int(top_row["n_trades"]),
            "top_mean_return_pct": round(top_row["mean_return_pct"], 4),
            "bottom_mean_return_pct": round(bottom_row["mean_return_pct"], 4),
            "delta_mean_return_pct_top_minus_bottom": round(delta_mean, 4),
            "top_win_rate_pct": round(top_row["win_rate_pct"], 2),
            "bottom_win_rate_pct": round(bottom_row["win_rate_pct"], 2),
            "delta_win_rate_pct_top_minus_bottom": round(delta_win_rate, 2),
        },
        "concentration": {
            "profit_share_top": round(profit_share_top, 4),
            "loss_share_bottom": round(loss_share_bottom, 4),
        },
        "stability": {
            "valid_folds": valid_folds,
            "fold_wins": fold_wins,
            "fold_win_rate": round(fold_win_rate, 4),
            "fold_details": fold_rows,
        },
        "rho_spearman": round(rho, 4),
        "promising": promising,
        "buckets": bucket_rows,
    }


def _build_markdown(payload: dict) -> str:
    lines = [
        "# X35 Multi-Horizon Trend State Scan",
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
        "## Feature Summary",
        "",
        "| Feature | Flips/yr | Median spell days | Bottom trades | Top trades | Spearman rho | Top-Bottom mean delta | Top-Bottom win-rate delta | Profit top % | Loss bottom % | Promising |",
        "|---------|----------|-------------------|---------------|------------|--------------|-----------------------|---------------------------|--------------|---------------|-----------|",
    ]

    for row in payload["features"]:
        lines.append(
            f"| `{row['feature']}` | {row['calendar']['flips_per_year']} | {row['calendar']['median_spell_days']} | "
            f"{row['trade_split']['n_bottom']} | {row['trade_split']['n_top']} | {row['rho_spearman']} | "
            f"{row['trade_split']['delta_mean_return_pct_top_minus_bottom']} | "
            f"{row['trade_split']['delta_win_rate_pct_top_minus_bottom']} | "
            f"{round(row['concentration']['profit_share_top'] * 100.0, 2)} | "
            f"{round(row['concentration']['loss_share_bottom'] * 100.0, 2)} | {row['promising']} |"
        )

    for row in payload["features"]:
        lines.extend(
            [
                "",
                f"### `{row['feature']}`",
                "",
                "| Bucket | Trades | Mean % | Median % | Win rate % | Profit sum | Loss sum |",
                "|--------|--------|--------|----------|------------|------------|----------|",
            ]
        )
        for bucket in row["buckets"]:
            lines.append(
                f"| {bucket['bucket']} | {bucket['n_trades']} | {bucket['mean_return_pct']} | "
                f"{bucket['median_return_pct']} | {bucket['win_rate_pct']} | "
                f"{bucket['profit_sum']} | {bucket['loss_sum']} |"
            )

    return "\n".join(lines) + "\n"


def main() -> None:
    feed = load_feed()
    report_start_ms = int(feed.report_start_ms or 0)

    d1_df = bars_to_frame(feed.d1_bars, report_start_ms)
    d1_report = d1_df[d1_df["in_report"]].copy()
    weekly = _build_weekly_trend_features(d1_df)
    pre_report_weeks = int((weekly["close_time"] < report_start_ms).sum())
    warmup_ok = pre_report_weeks >= 52

    feature_frame = weekly[["close_time", *FEATURE_ORDER]].copy()

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

    mapped_d1 = attach_state_to_events(
        d1_report[["close_time", "dt_close"]].copy(),
        feature_frame,
        event_time_col="close_time",
    )
    mapped_trades = attach_state_to_events(
        trades_df.copy(),
        feature_frame,
        event_time_col="entry_ts_ms",
    )

    feature_rows = [
        _feature_summary(
            feature,
            mapped_d1,
            mapped_trades,
            warmup_ok=warmup_ok,
        )
        for feature in FEATURE_ORDER
    ]
    branch_verdict = "GO_F2_TREND_FAMILY" if any(row["promising"] for row in feature_rows) else "NO_GO_F2_TREND_FAMILY"

    payload = {
        "study_id": "x35_long_horizon_regime",
        "branch": "d_multi_horizon_trend_diagnostic",
        "branch_verdict": branch_verdict,
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
        "features": feature_rows,
    }

    json_path = RESULTS_DIR / "multi_horizon_trend_scan.json"
    md_path = RESULTS_DIR / "multi_horizon_trend_scan.md"
    write_json(json_path, payload)
    md_path.write_text(_build_markdown(payload), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
