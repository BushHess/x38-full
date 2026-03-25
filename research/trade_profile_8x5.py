#!/usr/bin/env python3
"""
8-Technique × 5-Strategy Trade Profile Analysis
================================================
Computes all 8 trade-level analysis techniques for E0, E5, SM, LATCH, E0+EMA1D21.

Techniques:
  1. Win rate, avg W/L, profit factor
  2. Streaks (consecutive W/L runs)
  3. Holding time distribution
  4. MFE / MAE (per-trade, post-hoc from H4 bars)
  5. Exit reason profitability
  6. Payoff concentration (top-5/10 PnL %)
  7. Top-N jackknife (remove top-K, recompute CAGR/Sharpe)
  8. Fat-tail statistics (skew, kurtosis)

Output:
  results/trade_profile_8x5/  — per-strategy CSVs + unified summary
"""

from __future__ import annotations
import bisect
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ── paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
BAR_CSV = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
PARITY_DIR = ROOT / "results" / "parity_20260305"
OUT_DIR = ROOT / "results" / "trade_profile_8x5"

STRATEGIES = {
    "E0":             PARITY_DIR / "eval_e0_vs_e0"    / "results" / "trades_candidate.csv",
    "E5":             PARITY_DIR / "eval_e5_vs_e0"    / "results" / "trades_candidate.csv",
    "SM":             PARITY_DIR / "eval_sm_vs_e0"    / "results" / "trades_candidate.csv",
    "LATCH":          PARITY_DIR / "eval_latch_vs_e0" / "results" / "trades_candidate.csv",
    "E0_plus_EMA1D21": PARITY_DIR / "eval_ema21d1_vs_e0" / "results" / "trades_candidate.csv",
}

# backtest period for CAGR/Sharpe recalculation in jackknife
BACKTEST_YEARS = 6.5  # ~2019-01 to 2025-08 (approximate)
ANN_FACTOR = np.sqrt(6.0 * 365.25)  # H4 annualization for Sharpe


# ── load bar data for MFE/MAE ────────────────────────────────────────────

def load_h4_bars() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load H4 bars, return (open_times_ms, highs, lows)."""
    df = pd.read_csv(BAR_CSV)
    h4 = df[df["interval"] == "4h"].copy()
    h4.sort_values("open_time", inplace=True)
    return (
        h4["open_time"].values.astype(np.int64),
        h4["high"].values.astype(np.float64),
        h4["low"].values.astype(np.float64),
    )


def compute_mfe_mae(
    entry_ts_ms: int, exit_ts_ms: int, entry_price: float,
    h4_times: np.ndarray, h4_highs: np.ndarray, h4_lows: np.ndarray,
) -> tuple[float, float]:
    """MFE/MAE from H4 bar extrema during holding period."""
    i_start = bisect.bisect_left(h4_times, entry_ts_ms)
    i_end = bisect.bisect_right(h4_times, exit_ts_ms)
    if i_start >= i_end or entry_price < 1e-12:
        return 0.0, 0.0
    max_high = h4_highs[i_start:i_end].max()
    min_low = h4_lows[i_start:i_end].min()
    mfe = max(0.0, (max_high - entry_price) / entry_price * 100.0)
    mae = max(0.0, (entry_price - min_low) / entry_price * 100.0)
    return mfe, mae


# ── technique functions ──────────────────────────────────────────────────

def t1_win_rate_pf(df: pd.DataFrame) -> dict:
    """T1: Win rate, avg win/loss, profit factor."""
    wins = df[df["return_pct"] > 0]
    losses = df[df["return_pct"] <= 0]
    n = len(df)
    n_win = len(wins)
    n_loss = len(losses)
    avg_win = wins["return_pct"].mean() if n_win > 0 else 0.0
    avg_loss = losses["return_pct"].mean() if n_loss > 0 else 0.0
    gross_profit = wins["pnl_usd"].sum() if n_win > 0 else 0.0
    gross_loss = abs(losses["pnl_usd"].sum()) if n_loss > 0 else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else np.inf
    return {
        "n_trades": n,
        "n_wins": n_win,
        "n_losses": n_loss,
        "win_rate_pct": 100.0 * n_win / n if n > 0 else 0.0,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "avg_wl_ratio": abs(avg_win / avg_loss) if avg_loss != 0 else np.inf,
        "profit_factor": pf,
        "expectancy_pct": df["return_pct"].mean(),
    }


def t2_streaks(df: pd.DataFrame) -> dict:
    """T2: Win/loss streak analysis."""
    is_win = (df["return_pct"].values > 0).astype(int)
    # compute streaks
    win_streaks, loss_streaks = [], []
    current, count = -1, 0
    for w in is_win:
        if w == current:
            count += 1
        else:
            if count > 0:
                (win_streaks if current == 1 else loss_streaks).append(count)
            current, count = w, 1
    if count > 0:
        (win_streaks if current == 1 else loss_streaks).append(count)

    return {
        "max_win_streak": max(win_streaks) if win_streaks else 0,
        "max_loss_streak": max(loss_streaks) if loss_streaks else 0,
        "avg_win_streak": np.mean(win_streaks) if win_streaks else 0.0,
        "avg_loss_streak": np.mean(loss_streaks) if loss_streaks else 0.0,
        "median_win_streak": np.median(win_streaks) if win_streaks else 0.0,
        "median_loss_streak": np.median(loss_streaks) if loss_streaks else 0.0,
        "n_win_streaks": len(win_streaks),
        "n_loss_streaks": len(loss_streaks),
    }


def t3_holding_time(df: pd.DataFrame) -> dict:
    """T3: Holding time distribution."""
    d = df["days_held"].values
    return {
        "mean_days": np.mean(d),
        "median_days": np.median(d),
        "min_days": np.min(d),
        "max_days": np.max(d),
        "std_days": np.std(d, ddof=0),
        "p10_days": np.percentile(d, 10),
        "p25_days": np.percentile(d, 25),
        "p75_days": np.percentile(d, 75),
        "p90_days": np.percentile(d, 90),
    }


def t4_mfe_mae(
    df: pd.DataFrame,
    h4_times: np.ndarray, h4_highs: np.ndarray, h4_lows: np.ndarray,
) -> tuple[dict, pd.DataFrame]:
    """T4: MFE/MAE per trade, summary stats."""
    mfes, maes = [], []
    for _, row in df.iterrows():
        mfe, mae = compute_mfe_mae(
            int(row["entry_ts_ms"]), int(row["exit_ts_ms"]),
            row["entry_price"], h4_times, h4_highs, h4_lows,
        )
        mfes.append(mfe)
        maes.append(mae)

    df_out = df[["trade_id", "return_pct", "pnl_usd", "days_held"]].copy()
    df_out["mfe_pct"] = mfes
    df_out["mae_pct"] = maes
    df_out["edge_ratio"] = [
        m / a if a > 0 else np.inf for m, a in zip(mfes, maes)
    ]

    mfe_arr = np.array(mfes)
    mae_arr = np.array(maes)
    summary = {
        "mfe_mean": mfe_arr.mean(),
        "mfe_median": np.median(mfe_arr),
        "mfe_p90": np.percentile(mfe_arr, 90),
        "mae_mean": mae_arr.mean(),
        "mae_median": np.median(mae_arr),
        "mae_p90": np.percentile(mae_arr, 90),
        "edge_ratio_mean": np.mean(df_out["edge_ratio"].replace(np.inf, np.nan).dropna()),
        "edge_ratio_median": np.median(df_out["edge_ratio"].replace(np.inf, np.nan).dropna()),
        "mfe_mae_corr": np.corrcoef(mfe_arr, mae_arr)[0, 1] if len(mfe_arr) > 1 else 0.0,
    }
    return summary, df_out


def t5_exit_reason(df: pd.DataFrame) -> dict:
    """T5: Exit reason profitability breakdown."""
    results = {}
    for reason, grp in df.groupby("exit_reason"):
        n = len(grp)
        wins = grp[grp["return_pct"] > 0]
        results[reason] = {
            "n_trades": n,
            "pct_of_total": 100.0 * n / len(df),
            "win_rate_pct": 100.0 * len(wins) / n if n > 0 else 0.0,
            "avg_return_pct": grp["return_pct"].mean(),
            "median_return_pct": grp["return_pct"].median(),
            "total_pnl_usd": grp["pnl_usd"].sum(),
            "avg_days_held": grp["days_held"].mean(),
        }
    return results


def t6_payoff_concentration(df: pd.DataFrame) -> dict:
    """T6: Payoff concentration — top-K trade contribution."""
    total_pnl = df["pnl_usd"].sum()
    sorted_pnl = df["pnl_usd"].sort_values(ascending=False).values
    n = len(df)

    # top-N absolute PnL contribution
    abs_sorted = np.sort(np.abs(df["pnl_usd"].values))[::-1]
    total_abs = abs_sorted.sum()

    results = {}
    for k in [1, 3, 5, 10]:
        if k > n:
            continue
        top_k_pnl = sorted_pnl[:k].sum()
        bot_k_pnl = sorted_pnl[-k:].sum()
        top_k_abs = abs_sorted[:k].sum()
        results[f"top_{k}_pnl_usd"] = top_k_pnl
        results[f"top_{k}_pnl_pct_of_total"] = (
            100.0 * top_k_pnl / total_pnl if total_pnl != 0 else 0.0
        )
        results[f"bottom_{k}_pnl_usd"] = bot_k_pnl
        results[f"top_{k}_abs_pct"] = (
            100.0 * top_k_abs / total_abs if total_abs > 0 else 0.0
        )

    # Herfindahl index on absolute PnL
    if total_abs > 0:
        shares = abs_sorted / total_abs
        hhi = (shares ** 2).sum()
    else:
        hhi = 0.0
    results["herfindahl_index"] = hhi
    results["effective_n_trades"] = 1.0 / hhi if hhi > 0 else n

    # Gini coefficient
    if n > 0 and total_abs > 0:
        sorted_abs = np.sort(np.abs(df["pnl_usd"].values))
        cum = np.cumsum(sorted_abs)
        gini = 1.0 - 2.0 * cum.sum() / (n * total_abs)
        results["gini_coefficient"] = gini
    else:
        results["gini_coefficient"] = 0.0

    return results


def _trade_sharpe(returns: pd.Series, trades_per_year: float) -> float:
    """Annualized Sharpe from per-trade returns using sqrt(trades/yr)."""
    if len(returns) < 2 or returns.std(ddof=0) < 1e-12:
        return 0.0
    return returns.mean() / returns.std(ddof=0) * np.sqrt(trades_per_year)


def _safe_cagr(total_pnl: float, nav0: float, years: float) -> float:
    """CAGR that handles total loss (negative final NAV)."""
    final = nav0 + total_pnl
    if final <= 0:
        return -1.0  # total wipeout
    return (final / nav0) ** (1.0 / years) - 1.0


def t7_jackknife(df: pd.DataFrame) -> dict:
    """T7: Top-N jackknife — remove top-K trades, recompute metrics."""
    sorted_idx = df["pnl_usd"].sort_values(ascending=False).index
    base_total_pnl = df["pnl_usd"].sum()
    base_return = df["return_pct"]
    nav0 = 10000.0
    tpy = len(df) / BACKTEST_YEARS  # trades per year
    base_sharpe = _trade_sharpe(base_return, tpy)
    base_cagr = _safe_cagr(base_total_pnl, nav0, BACKTEST_YEARS)

    results = {
        "base_sharpe": base_sharpe,
        "base_cagr_pct": base_cagr * 100.0,
        "base_total_pnl": base_total_pnl,
    }

    for k in [1, 3, 5, 10]:
        if k >= len(df):
            continue
        # remove top-K most profitable trades
        drop_idx = sorted_idx[:k]
        remaining = df.drop(drop_idx)
        r = remaining["return_pct"]
        pnl = remaining["pnl_usd"].sum()
        tpy_r = len(remaining) / BACKTEST_YEARS
        sharpe = _trade_sharpe(r, tpy_r)
        cagr = _safe_cagr(pnl, nav0, BACKTEST_YEARS)

        results[f"drop_top{k}_sharpe"] = sharpe
        results[f"drop_top{k}_cagr_pct"] = cagr * 100.0
        results[f"drop_top{k}_pnl"] = pnl
        results[f"drop_top{k}_sharpe_delta_pct"] = (
            100.0 * (sharpe - base_sharpe) / abs(base_sharpe)
            if base_sharpe != 0 else 0.0
        )
        results[f"drop_top{k}_cagr_delta_pct"] = (
            100.0 * (cagr - base_cagr) / abs(base_cagr)
            if base_cagr != 0 else 0.0
        )

    # also remove top-K most losing trades (bottom-K)
    sorted_idx_asc = df["pnl_usd"].sort_values(ascending=True).index
    for k in [1, 3, 5, 10]:
        if k >= len(df):
            continue
        drop_idx = sorted_idx_asc[:k]
        remaining = df.drop(drop_idx)
        r = remaining["return_pct"]
        pnl = remaining["pnl_usd"].sum()
        tpy_r = len(remaining) / BACKTEST_YEARS
        sharpe = _trade_sharpe(r, tpy_r)
        cagr = _safe_cagr(pnl, nav0, BACKTEST_YEARS)

        results[f"drop_bot{k}_sharpe"] = sharpe
        results[f"drop_bot{k}_cagr_pct"] = cagr * 100.0
        results[f"drop_bot{k}_pnl"] = pnl

    return results


def t8_fat_tail(df: pd.DataFrame) -> dict:
    """T8: Fat-tail statistics on trade return distribution."""
    r = df["return_pct"].values
    n = len(r)
    if n < 4:
        return {"skew": 0.0, "kurtosis": 0.0, "n": n}

    sk = stats.skew(r, bias=False)
    ku = stats.kurtosis(r, bias=False)  # excess kurtosis

    # Jarque-Bera test
    jb_stat, jb_p = stats.jarque_bera(r)

    # D'Agostino-Pearson omnibus test
    if n >= 20:
        dp_stat, dp_p = stats.normaltest(r)
    else:
        dp_stat, dp_p = np.nan, np.nan

    # percentile ratios for tail heaviness
    p1 = np.percentile(r, 1)
    p5 = np.percentile(r, 5)
    p95 = np.percentile(r, 95)
    p99 = np.percentile(r, 99)

    return {
        "skew": sk,
        "excess_kurtosis": ku,
        "jarque_bera_stat": jb_stat,
        "jarque_bera_p": jb_p,
        "dagostino_stat": dp_stat,
        "dagostino_p": dp_p,
        "p1": p1,
        "p5": p5,
        "p95": p95,
        "p99": p99,
        "range_p1_p99": p99 - p1,
        "tail_ratio_95_5": abs(p95 / p5) if p5 != 0 else np.inf,
        "mean_return_pct": np.mean(r),
        "std_return_pct": np.std(r, ddof=0),
    }


# ── main ─────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading H4 bar data for MFE/MAE...")
    h4_times, h4_highs, h4_lows = load_h4_bars()
    print(f"  H4 bars: {len(h4_times)}")

    all_results = {}

    for strat_name, csv_path in STRATEGIES.items():
        print(f"\n{'='*60}")
        print(f"  Strategy: {strat_name}")
        print(f"{'='*60}")

        df = pd.read_csv(csv_path)
        print(f"  Trades: {len(df)}")

        strat_dir = OUT_DIR / strat_name
        strat_dir.mkdir(parents=True, exist_ok=True)

        # T1
        print("  T1: Win rate / profit factor...")
        r1 = t1_win_rate_pf(df)

        # T2
        print("  T2: Streaks...")
        r2 = t2_streaks(df)

        # T3
        print("  T3: Holding time...")
        r3 = t3_holding_time(df)

        # T4
        print("  T4: MFE/MAE...")
        r4_summary, r4_detail = t4_mfe_mae(df, h4_times, h4_highs, h4_lows)
        r4_detail.to_csv(strat_dir / "mfe_mae_per_trade.csv", index=False)

        # T5
        print("  T5: Exit reason profitability...")
        r5 = t5_exit_reason(df)
        # flatten for summary
        r5_flat = {}
        for reason, metrics in r5.items():
            short = reason.split("_")[-2] + "_" + reason.split("_")[-1]
            for k, v in metrics.items():
                r5_flat[f"exit_{short}_{k}"] = v

        # T6
        print("  T6: Payoff concentration...")
        r6 = t6_payoff_concentration(df)

        # T7
        print("  T7: Top-N jackknife...")
        r7 = t7_jackknife(df)

        # T8
        print("  T8: Fat-tail stats...")
        r8 = t8_fat_tail(df)

        # combine
        combined = {"strategy": strat_name, "n_trades": len(df)}
        for prefix, data in [
            ("t1", r1), ("t2", r2), ("t3", r3), ("t4", r4_summary),
            ("t5", r5_flat), ("t6", r6), ("t7", r7), ("t8", r8),
        ]:
            for k, v in data.items():
                combined[f"{prefix}_{k}"] = v

        all_results[strat_name] = combined

        # per-strategy JSON
        with open(strat_dir / "profile.json", "w") as f:
            json.dump(combined, f, indent=2, default=str)

        # per-strategy exit reason detail
        with open(strat_dir / "exit_reason_detail.json", "w") as f:
            json.dump(r5, f, indent=2, default=str)

    # ── unified summary table ────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Writing unified summary...")
    print(f"{'='*60}")

    summary_df = pd.DataFrame(all_results).T
    summary_df.to_csv(OUT_DIR / "summary_8x5.csv", index=False)

    # ── formatted report ─────────────────────────────────────────────────
    report_lines = []
    report_lines.append("# 8-Technique × 5-Strategy Trade Profile Report")
    report_lines.append(f"# Generated: {pd.Timestamp.now().isoformat()}")
    report_lines.append("")

    # T1 comparison table
    report_lines.append("## T1: Win Rate / Profit Factor")
    report_lines.append(f"{'Strategy':<20} {'N':>5} {'Win%':>7} {'AvgW%':>8} {'AvgL%':>8} {'W/L':>6} {'PF':>7} {'E[r]%':>8}")
    report_lines.append("-" * 75)
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(
            f"{s:<20} {r['t1_n_trades']:>5} {r['t1_win_rate_pct']:>7.1f} "
            f"{r['t1_avg_win_pct']:>8.2f} {r['t1_avg_loss_pct']:>8.2f} "
            f"{r['t1_avg_wl_ratio']:>6.2f} {r['t1_profit_factor']:>7.2f} "
            f"{r['t1_expectancy_pct']:>8.3f}"
        )
    report_lines.append("")

    # T2 comparison
    report_lines.append("## T2: Streaks")
    report_lines.append(f"{'Strategy':<20} {'MaxW':>5} {'MaxL':>5} {'AvgW':>6} {'AvgL':>6} {'MedW':>5} {'MedL':>5}")
    report_lines.append("-" * 55)
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(
            f"{s:<20} {r['t2_max_win_streak']:>5} {r['t2_max_loss_streak']:>5} "
            f"{r['t2_avg_win_streak']:>6.1f} {r['t2_avg_loss_streak']:>6.1f} "
            f"{r['t2_median_win_streak']:>5.0f} {r['t2_median_loss_streak']:>5.0f}"
        )
    report_lines.append("")

    # T3 comparison
    report_lines.append("## T3: Holding Time (days)")
    report_lines.append(f"{'Strategy':<20} {'Mean':>7} {'Med':>7} {'Min':>6} {'Max':>7} {'P10':>7} {'P90':>7}")
    report_lines.append("-" * 65)
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(
            f"{s:<20} {r['t3_mean_days']:>7.1f} {r['t3_median_days']:>7.1f} "
            f"{r['t3_min_days']:>6.1f} {r['t3_max_days']:>7.1f} "
            f"{r['t3_p10_days']:>7.1f} {r['t3_p90_days']:>7.1f}"
        )
    report_lines.append("")

    # T4 comparison
    report_lines.append("## T4: MFE / MAE (%)")
    report_lines.append(f"{'Strategy':<20} {'MFE_μ':>7} {'MFE_md':>7} {'MAE_μ':>7} {'MAE_md':>7} {'Edge_μ':>7} {'Edge_md':>8} {'ρ':>6}")
    report_lines.append("-" * 75)
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(
            f"{s:<20} {r['t4_mfe_mean']:>7.2f} {r['t4_mfe_median']:>7.2f} "
            f"{r['t4_mae_mean']:>7.2f} {r['t4_mae_median']:>7.2f} "
            f"{r['t4_edge_ratio_mean']:>7.2f} {r['t4_edge_ratio_median']:>8.2f} "
            f"{r['t4_mfe_mae_corr']:>6.3f}"
        )
    report_lines.append("")

    # T5 comparison
    report_lines.append("## T5: Exit Reason Profitability")
    report_lines.append("  (per-strategy detail in exit_reason_detail.json)")
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(f"\n  {s}:")
        # extract exit reason keys
        exit_keys = [k for k in r if k.startswith("t5_exit_")]
        reasons = set()
        for k in exit_keys:
            parts = k.replace("t5_exit_", "").rsplit("_", 1)
            if len(parts) == 2:
                reasons.add(parts[0])
            else:
                # handle multi-word reason names
                pass
        # just print from the JSON
        strat_dir = OUT_DIR / s
        with open(strat_dir / "exit_reason_detail.json") as f:
            detail = json.load(f)
        for reason, metrics in detail.items():
            short = reason.replace("vtrend_", "").replace("ema21_d1_", "ema21d1_")
            report_lines.append(
                f"    {short:<30} n={metrics['n_trades']:>4}  "
                f"win={metrics['win_rate_pct']:>5.1f}%  "
                f"avg_r={metrics['avg_return_pct']:>7.2f}%  "
                f"total=${metrics['total_pnl_usd']:>10.0f}  "
                f"days={metrics['avg_days_held']:>5.1f}"
            )
    report_lines.append("")

    # T6 comparison
    report_lines.append("## T6: Payoff Concentration")
    report_lines.append(f"{'Strategy':<20} {'Top1%':>7} {'Top3%':>7} {'Top5%':>7} {'Top10%':>7} {'Gini':>6} {'HHI':>7} {'Eff_N':>6}")
    report_lines.append("-" * 75)
    for s in STRATEGIES:
        r = all_results[s]
        t1p = r.get("t6_top_1_pnl_pct_of_total", 0)
        t3p = r.get("t6_top_3_pnl_pct_of_total", 0)
        t5p = r.get("t6_top_5_pnl_pct_of_total", 0)
        t10p = r.get("t6_top_10_pnl_pct_of_total", 0)
        report_lines.append(
            f"{s:<20} {t1p:>7.1f} {t3p:>7.1f} {t5p:>7.1f} {t10p:>7.1f} "
            f"{r['t6_gini_coefficient']:>6.3f} {r['t6_herfindahl_index']:>7.4f} "
            f"{r['t6_effective_n_trades']:>6.1f}"
        )
    report_lines.append("")

    # T7 comparison
    report_lines.append("## T7: Top-N Jackknife")
    report_lines.append(f"{'Strategy':<20} {'Base_S':>7} {'−1_S':>7} {'−3_S':>7} {'−5_S':>7} {'−10_S':>7} {'−5Δ%':>7}")
    report_lines.append("-" * 65)
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(
            f"{s:<20} {r['t7_base_sharpe']:>7.3f} "
            f"{r.get('t7_drop_top1_sharpe', 0):>7.3f} "
            f"{r.get('t7_drop_top3_sharpe', 0):>7.3f} "
            f"{r.get('t7_drop_top5_sharpe', 0):>7.3f} "
            f"{r.get('t7_drop_top10_sharpe', 0):>7.3f} "
            f"{r.get('t7_drop_top5_sharpe_delta_pct', 0):>7.1f}"
        )
    report_lines.append("")
    report_lines.append(f"{'Strategy':<20} {'Base_C%':>8} {'−1_C%':>8} {'−3_C%':>8} {'−5_C%':>8} {'−10_C%':>8}")
    report_lines.append("-" * 60)
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(
            f"{s:<20} {r['t7_base_cagr_pct']:>8.1f} "
            f"{r.get('t7_drop_top1_cagr_pct', 0):>8.1f} "
            f"{r.get('t7_drop_top3_cagr_pct', 0):>8.1f} "
            f"{r.get('t7_drop_top5_cagr_pct', 0):>8.1f} "
            f"{r.get('t7_drop_top10_cagr_pct', 0):>8.1f}"
        )
    report_lines.append("")

    # drop bottom-K (removing worst trades)
    report_lines.append("  Removing worst trades (sensitivity to worst losers):")
    report_lines.append(f"{'Strategy':<20} {'−1bot_S':>8} {'−3bot_S':>8} {'−5bot_S':>8} {'−10bot_S':>9}")
    report_lines.append("-" * 55)
    for s in STRATEGIES:
        r = all_results[s]
        report_lines.append(
            f"{s:<20} "
            f"{r.get('t7_drop_bot1_sharpe', 0):>8.3f} "
            f"{r.get('t7_drop_bot3_sharpe', 0):>8.3f} "
            f"{r.get('t7_drop_bot5_sharpe', 0):>8.3f} "
            f"{r.get('t7_drop_bot10_sharpe', 0):>9.3f}"
        )
    report_lines.append("")

    # T8 comparison
    report_lines.append("## T8: Fat-Tail Statistics")
    report_lines.append(f"{'Strategy':<20} {'Skew':>7} {'ExKurt':>7} {'JB_p':>8} {'DA_p':>8} {'P1':>7} {'P99':>7} {'TailR':>7}")
    report_lines.append("-" * 75)
    for s in STRATEGIES:
        r = all_results[s]
        da_p = r["t8_dagostino_p"]
        da_str = f"{da_p:>8.4f}" if not (isinstance(da_p, float) and np.isnan(da_p)) else "     N/A"
        report_lines.append(
            f"{s:<20} {r['t8_skew']:>7.3f} {r['t8_excess_kurtosis']:>7.3f} "
            f"{r['t8_jarque_bera_p']:>8.4f} {da_str} "
            f"{r['t8_p1']:>7.2f} {r['t8_p99']:>7.2f} "
            f"{r['t8_tail_ratio_95_5']:>7.2f}"
        )
    report_lines.append("")

    report_text = "\n".join(report_lines)
    with open(OUT_DIR / "REPORT_8x5.txt", "w") as f:
        f.write(report_text)

    print(report_text)
    print(f"\nResults saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
