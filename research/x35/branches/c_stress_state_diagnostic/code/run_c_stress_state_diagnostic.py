"""Run stress/drawdown state survey for x35."""

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
from research.x35.shared.common import write_json  # noqa: E402
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


def _build_stress_features(d1_df: pd.DataFrame) -> pd.DataFrame:
    out = d1_df[["close_time", "dt_close", "close"]].copy()
    log_ret = np.log(out["close"] / out["close"].shift(1))

    roll_max_63 = out["close"].rolling(63, min_periods=63).max()
    roll_max_126 = out["close"].rolling(126, min_periods=126).max()
    rv_30 = log_ret.rolling(30, min_periods=30).std()
    rv_180 = log_ret.rolling(180, min_periods=180).std()

    out["dd63_depth"] = 1.0 - out["close"] / roll_max_63
    out["dd126_depth"] = 1.0 - out["close"] / roll_max_126
    out["vol_shock_30_180"] = rv_30 / rv_180
    return out


def _quantile_labels(series: pd.Series) -> pd.Series:
    ranked = series.rank(method="first")
    return pd.qcut(ranked, 4, labels=["Q1", "Q2", "Q3", "Q4"])


def _feature_summary(mapped: pd.DataFrame, feature: str) -> dict:
    frame = mapped[["trade_id", "pnl", "return_pct", feature]].dropna().copy()
    frame["quantile"] = _quantile_labels(frame[feature])

    grouped_rows = []
    for label in ["Q1", "Q2", "Q3", "Q4"]:
        subset = frame[frame["quantile"] == label].copy()
        loss_sum = float(-subset.loc[subset["pnl"] < 0, "pnl"].sum())
        profit_sum = float(subset.loc[subset["pnl"] > 0, "pnl"].sum())
        grouped_rows.append(
            {
                "quantile": label,
                "n_trades": int(len(subset)),
                "mean_return_pct": round(float(subset["return_pct"].mean()), 4),
                "median_return_pct": round(float(subset["return_pct"].median()), 4),
                "win_rate_pct": round(float((subset["pnl"] > 0).mean() * 100.0), 2),
                "profit_sum": round(profit_sum, 2),
                "loss_sum": round(loss_sum, 2),
            }
        )

    total_loss = float(-frame.loc[frame["pnl"] < 0, "pnl"].sum())
    q1 = next(row for row in grouped_rows if row["quantile"] == "Q1")
    q4 = next(row for row in grouped_rows if row["quantile"] == "Q4")
    loss_share_q4 = 0.0 if total_loss == 0 else q4["loss_sum"] / total_loss
    rho = float(frame[feature].corr(frame["return_pct"], method="spearman"))

    promising = bool(
        rho < 0.0
        and q1["mean_return_pct"] > 0.0
        and q4["mean_return_pct"] < 0.0
        and (q1["mean_return_pct"] - q4["mean_return_pct"]) >= 2.0
        and loss_share_q4 >= 0.40
    )

    return {
        "feature": feature,
        "n_mapped_trades": int(len(frame)),
        "rho_spearman": round(rho, 4),
        "delta_mean_return_pct_q1_minus_q4": round(q1["mean_return_pct"] - q4["mean_return_pct"], 4),
        "loss_share_q4": round(loss_share_q4, 4),
        "promising": promising,
        "quantiles": grouped_rows,
    }


def _build_markdown(payload: dict) -> str:
    lines = [
        "# X35 Stress State Scan",
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
        "## Feature Summary",
        "",
        "| Feature | Trades | Spearman rho | Q1-Q4 mean delta | Q4 loss share | Promising |",
        "|---------|--------|--------------|------------------|---------------|-----------|",
    ]

    for row in payload["features"]:
        lines.append(
            f"| `{row['feature']}` | {row['n_mapped_trades']} | {row['rho_spearman']} | "
            f"{row['delta_mean_return_pct_q1_minus_q4']} | {round(row['loss_share_q4'] * 100.0, 2)} | {row['promising']} |"
        )

    for row in payload["features"]:
        lines.extend(
            [
                "",
                f"### `{row['feature']}`",
                "",
                "| Quantile | Trades | Mean % | Median % | Win rate % | Profit sum | Loss sum |",
                "|----------|--------|--------|----------|------------|------------|----------|",
            ]
        )
        for q in row["quantiles"]:
            lines.append(
                f"| {q['quantile']} | {q['n_trades']} | {q['mean_return_pct']} | {q['median_return_pct']} | "
                f"{q['win_rate_pct']} | {q['profit_sum']} | {q['loss_sum']} |"
            )

    return "\n".join(lines) + "\n"


def main() -> None:
    feed = load_feed()
    report_start_ms = int(feed.report_start_ms or 0)

    d1_df = bars_to_frame(feed.d1_bars, report_start_ms)
    d1_report = d1_df[d1_df["in_report"]].copy()
    stress_df = _build_stress_features(d1_report)

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

    mapped = attach_state_to_events(
        trades_df,
        stress_df[["close_time", "dd63_depth", "dd126_depth", "vol_shock_30_180"]],
        event_time_col="entry_ts_ms",
    )

    feature_rows = [
        _feature_summary(mapped, feature)
        for feature in ("dd63_depth", "dd126_depth", "vol_shock_30_180")
    ]
    branch_verdict = "GO_STRESS_FAMILY" if any(row["promising"] for row in feature_rows) else "NO_GO_STRESS_FAMILY"

    payload = {
        "study_id": "x35_long_horizon_regime",
        "branch": "c_stress_state_diagnostic",
        "branch_verdict": branch_verdict,
        "baseline": {
            "strategy": "VTrendE5Ema21D1Strategy",
            "trades": int(result.summary.get("trades", len(result.trades))),
            "sharpe": round(float(result.summary.get("sharpe", 0.0)), 4),
            "cagr_pct": round(float(result.summary.get("cagr_pct", 0.0)), 2),
            "max_drawdown_mid_pct": round(float(result.summary.get("max_drawdown_mid_pct", 0.0)), 2),
        },
        "features": feature_rows,
    }

    json_path = RESULTS_DIR / "stress_state_scan.json"
    md_path = RESULTS_DIR / "stress_state_scan.md"
    write_json(json_path, payload)
    md_path.write_text(_build_markdown(payload), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
