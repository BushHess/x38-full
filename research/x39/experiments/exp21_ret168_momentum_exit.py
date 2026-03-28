#!/usr/bin/env python3
"""Exp 21: ret_168 Momentum Exit.

E5-ema21D1 with ret_168 (28-day momentum) supplementary exit.
When ret_168 < threshold during a long trade, macro momentum has reversed.
Different timescale from trail stop (local) and EMA cross-down (medium-term).

Entry logic UNCHANGED. Only adds ret_168 exit as additional OR condition.

Sweep:
  threshold in [-0.15, -0.10, -0.05, 0.00, 0.05, 0.10]
  → 6 configs + baseline (no ret_168 exit)

Additional analysis:
  - Exit attribution (trail / trend / ret168 counts)
  - Timing: for ret_168 exits, how many bars earlier/later vs counterfactual
  - Selectivity: of ret_168 exits, fraction losers vs winners

Usage:
    python -m research.x39.experiments.exp21_ret168_momentum_exit
    # or from x39/:
    python experiments/exp21_ret168_momentum_exit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, load_data  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
TRAIL_MULT = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365

THRESHOLDS = [-0.15, -0.10, -0.05, 0.00, 0.05, 0.10]

# Counterfactual search horizon (bars) for timing analysis
CF_MAX_HORIZON = 500  # ~83 days at H4


def run_backtest(
    feat: pd.DataFrame,
    ret168_threshold: float | None,
    warmup_bar: int,
) -> tuple[dict, list[dict]]:
    """Replay E5-ema21D1 with optional ret_168 supplementary exit.

    If ret168_threshold is None, runs baseline (no ret_168 exit).
    Returns (summary_dict, trades_list).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    ret168 = feat["ret_168"].values
    n = len(c)

    use_ret168 = ret168_threshold is not None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "ret168": 0}
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
            continue

        if not in_pos:
            equity[i] = cash

            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )

            if entry_ok:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / c[i]
                cash = 0.0
        else:
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])

            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"
            elif use_ret168 and np.isfinite(ret168[i]) and ret168[i] < ret168_threshold:
                exit_reason = "ret168"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price,
                    "exit_price": c[i],
                    "gross_ret": gross_ret,
                    "net_ret": net_ret,
                    "exit_reason": exit_reason,
                    "win": int(net_ret > 0),
                    "peak_at_exit": peak,
                })

                exit_counts[exit_reason] += 1
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": "baseline" if not use_ret168 else f"thr={ret168_threshold}",
            "threshold": ret168_threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_ret168": 0,
        }, trades

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    if rets.std() > 0:
        sharpe = rets.mean() / rets.std() * np.sqrt(bars_per_year)
    else:
        sharpe = 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars

    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["win"] == 1]
    losses = tdf[tdf["win"] == 0]

    label = "baseline" if not use_ret168 else f"thr={ret168_threshold}"

    return {
        "config": label,
        "threshold": ret168_threshold,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "avg_win": round(wins["net_ret"].mean() * 100, 2) if len(wins) > 0 else np.nan,
        "avg_loss": round(losses["net_ret"].mean() * 100, 2) if len(losses) > 0 else np.nan,
        "exposure_pct": round(exposure * 100, 1),
        "exit_trail": exit_counts["trail"],
        "exit_trend": exit_counts["trend"],
        "exit_ret168": exit_counts["ret168"],
    }, trades


def counterfactual_exit_bar(
    c: np.ndarray,
    ratr: np.ndarray,
    ema_f: np.ndarray,
    ema_s: np.ndarray,
    ret168_exit_bar: int,
    peak_at_exit: float,
) -> int | None:
    """Find when trail/trend WOULD have exited if ret_168 hadn't fired.

    Continues tracking peak from the ret_168 exit bar forward.
    Returns bar index of counterfactual exit, or None if data ends first.
    """
    n = len(c)
    peak = peak_at_exit

    end = min(n, ret168_exit_bar + CF_MAX_HORIZON)
    for i in range(ret168_exit_bar + 1, end):
        if np.isnan(ratr[i]):
            continue
        peak = max(peak, c[i])
        trail_stop = peak - TRAIL_MULT * ratr[i]

        if c[i] < trail_stop:
            return i
        if ema_f[i] < ema_s[i]:
            return i

    return None


def timing_analysis(
    trades: list[dict],
    feat: pd.DataFrame,
) -> list[dict]:
    """For each ret_168-triggered exit, compute counterfactual timing delta.

    Returns list of dicts with timing info for ret168 exits only.
    Positive bars_earlier = ret_168 exits BEFORE trail/trend would have.
    """
    c = feat["close"].values
    ratr = feat["ratr"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values

    results = []
    for t in trades:
        if t["exit_reason"] != "ret168":
            continue

        cf_bar = counterfactual_exit_bar(
            c, ratr, ema_f, ema_s,
            t["exit_bar"], t["peak_at_exit"],
        )

        if cf_bar is not None:
            bars_earlier = cf_bar - t["exit_bar"]  # positive = ret168 exits earlier
            # What would have happened if we waited for trail/trend?
            cf_exit_price = c[cf_bar]
            cf_gross_ret = (cf_exit_price - t["entry_price"]) / t["entry_price"]
            cf_net_ret = cf_gross_ret - COST_BPS / 10_000
            avoided_pnl = t["net_ret"] - cf_net_ret  # positive = ret168 avoided a loss
        else:
            bars_earlier = None
            cf_exit_price = None
            cf_net_ret = None
            avoided_pnl = None

        results.append({
            "entry_bar": t["entry_bar"],
            "ret168_exit_bar": t["exit_bar"],
            "cf_exit_bar": cf_bar,
            "bars_earlier": bars_earlier,
            "ret168_exit_price": t["exit_price"],
            "cf_exit_price": cf_exit_price,
            "ret168_net_ret": round(t["net_ret"] * 100, 2),
            "cf_net_ret": round(cf_net_ret * 100, 2) if cf_net_ret is not None else None,
            "avoided_pnl_pct": round(avoided_pnl * 100, 2) if avoided_pnl is not None else None,
            "win": t["win"],
        })

    return results


def print_timing_report(timing: list[dict]) -> None:
    """Print timing analysis for ret_168 exits."""
    if not timing:
        print("  (no ret_168 exits to analyse)")
        return

    with_cf = [t for t in timing if t["bars_earlier"] is not None]
    if not with_cf:
        print("  (all ret_168 exits near end of data — no counterfactual available)")
        return

    bars_arr = np.array([t["bars_earlier"] for t in with_cf])
    avoided_arr = np.array([t["avoided_pnl_pct"] for t in with_cf])

    n_earlier = int(np.sum(bars_arr > 0))
    n_later = int(np.sum(bars_arr < 0))
    n_same = int(np.sum(bars_arr == 0))

    print(f"  ret_168 exits with counterfactual: {len(with_cf)}")
    print(f"  ret_168 exits EARLIER than trail/trend: {n_earlier} ({n_earlier/len(with_cf):.0%})")
    print(f"  ret_168 exits LATER:                    {n_later} ({n_later/len(with_cf):.0%})")
    print(f"  ret_168 exits SAME bar:                 {n_same} ({n_same/len(with_cf):.0%})")
    print(f"  bars_earlier: median={np.median(bars_arr):.0f}, "
          f"mean={np.mean(bars_arr):.1f}, "
          f"min={np.min(bars_arr):.0f}, max={np.max(bars_arr):.0f}")
    print(f"  avoided PnL (pp): median={np.median(avoided_arr):.2f}, "
          f"mean={np.mean(avoided_arr):.2f}")

    # Per-trade detail
    print(f"\n  {'entry':>6} {'ret168':>7} {'cf_exit':>7} {'Δbars':>6} "
          f"{'ret168%':>8} {'cf%':>8} {'avoid%':>8} {'win':>4}")
    for t in with_cf:
        print(f"  {t['entry_bar']:6d} {t['ret168_exit_bar']:7d} "
              f"{t['cf_exit_bar']:7d} {t['bars_earlier']:+6d} "
              f"{t['ret168_net_ret']:+8.2f} {t['cf_net_ret']:+8.2f} "
              f"{t['avoided_pnl_pct']:+8.2f} {'W' if t['win'] else 'L':>4}")


def print_selectivity_report(trades: list[dict]) -> None:
    """Selectivity check: of ret_168 exits, how many were losers vs winners?"""
    ret168_trades = [t for t in trades if t["exit_reason"] == "ret168"]
    if not ret168_trades:
        print("  (no ret_168 exits)")
        return

    n = len(ret168_trades)
    n_win = sum(1 for t in ret168_trades if t["win"])
    n_loss = n - n_win

    print(f"  ret_168 exits: {n} total")
    print(f"    winners: {n_win} ({n_win/n:.0%})")
    print(f"    losers:  {n_loss} ({n_loss/n:.0%})")

    if n_win > 0:
        avg_win_ret = np.mean([t["net_ret"] for t in ret168_trades if t["win"]]) * 100
        print(f"    avg winner return: {avg_win_ret:+.2f}%")
    if n_loss > 0:
        avg_loss_ret = np.mean([t["net_ret"] for t in ret168_trades if not t["win"]]) * 100
        print(f"    avg loser return:  {avg_loss_ret:+.2f}%")

    # Compare with non-ret168 exits
    other_trades = [t for t in trades if t["exit_reason"] != "ret168"]
    if other_trades:
        other_wr = sum(1 for t in other_trades if t["win"]) / len(other_trades)
        ret168_wr = n_win / n
        print(f"  win rate comparison: ret168={ret168_wr:.1%} vs trail/trend={other_wr:.1%}")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 21: ret_168 Momentum Exit")
    print(f"  threshold sweep: {THRESHOLDS}")
    print(f"  trail_mult:      {TRAIL_MULT} (fixed)")
    print(f"  cost:            {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Warmup: 365 days = ~2191 H4 bars, but also need ret_168 valid
    bars_per_day = 24 / 4  # 6 H4 bars/day
    warmup_bar = max(SLOW_PERIOD, int(WARMUP_DAYS * bars_per_day))
    # Ensure ret_168 is valid at warmup_bar
    ret168 = feat["ret_168"].values
    first_valid = int(np.argmax(np.isfinite(ret168)))
    warmup_bar = max(warmup_bar, first_valid)
    print(f"Warmup bar: {warmup_bar} (first valid ret_168: {first_valid})")

    # ── Run baseline ──────────────────────────────────────────────────
    results = []
    print("\nRunning baseline (no ret_168 exit)...")
    r, base_trades = run_backtest(feat, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
    print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}")

    # ── Sweep thresholds ──────────────────────────────────────────────
    all_trades: dict[float, list[dict]] = {}
    for thr in THRESHOLDS:
        label = f"threshold={thr}"
        print(f"\nRunning {label}...")
        r, trades = run_backtest(feat, thr, warmup_bar)
        results.append(r)
        all_trades[thr] = trades
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
        print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, "
              f"ret168={r['exit_ret168']}")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = MDD improved

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp21_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Exit attribution breakdown ────────────────────────────────────
    print("\n" + "-" * 40)
    print("Exit attribution:")
    for _, row in df.iterrows():
        total = row["exit_trail"] + row["exit_trend"] + row["exit_ret168"]
        if total == 0:
            continue
        pct_t = row["exit_trail"] / total
        pct_tr = row["exit_trend"] / total
        pct_r = row["exit_ret168"] / total
        print(f"  {row['config']:15s}  trail={int(row['exit_trail']):3d} ({pct_t:.0%})"
              f"  trend={int(row['exit_trend']):3d} ({pct_tr:.0%})"
              f"  ret168={int(row['exit_ret168']):3d} ({pct_r:.0%})")

    # ── Timing analysis ───────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("TIMING ANALYSIS")
    print("(positive bars_earlier = ret_168 exits BEFORE trail/trend would have)")
    print("=" * 80)
    for thr in THRESHOLDS:
        trades = all_trades[thr]
        n_ret168 = sum(1 for t in trades if t["exit_reason"] == "ret168")
        if n_ret168 == 0:
            print(f"\nthr={thr}: no ret_168 exits")
            continue
        print(f"\nthr={thr}: {n_ret168} ret_168 exits")
        timing = timing_analysis(trades, feat)
        print_timing_report(timing)

    # ── Selectivity analysis ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SELECTIVITY ANALYSIS")
    print("(does ret_168 selectively cut losers?)")
    print("=" * 80)
    for thr in THRESHOLDS:
        trades = all_trades[thr]
        n_ret168 = sum(1 for t in trades if t["exit_reason"] == "ret168")
        if n_ret168 == 0:
            continue
        print(f"\nthr={thr}:")
        print_selectivity_report(trades)

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    variants = df.iloc[1:]
    improvements = variants[(variants["d_sharpe"] > 0) & (variants["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        print(f"  exits: trail={int(best['exit_trail'])}, trend={int(best['exit_trend'])}, "
              f"ret168={int(best['exit_ret168'])}")
    else:
        sharpe_up = variants[variants["d_sharpe"] > 0]
        mdd_down = variants[variants["d_mdd"] < 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        elif not mdd_down.empty:
            best = mdd_down.loc[mdd_down["d_mdd"].idxmin()]
            print(f"MIXED: {best['config']} improves MDD ({best['d_mdd']:+.2f} pp) "
                  f"but Sharpe changes {best['d_sharpe']:+.4f}")
        else:
            print("FAIL: No ret_168 exit threshold improves Sharpe or MDD over baseline.")
            print("ret_168 momentum exit does NOT help E5-ema21D1.")


if __name__ == "__main__":
    main()
