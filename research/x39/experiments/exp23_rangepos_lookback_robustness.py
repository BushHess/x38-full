#!/usr/bin/env python3
"""Exp 23: Rangepos Lookback Robustness.

Exp12 found rangepos_84 + threshold=0.25 as supplementary exit (+0.046 Sharpe,
-6.37 pp MDD). But why 84 bars? This experiment sweeps lookback x threshold
to determine if 84 is a sharp peak (fragile) or part of a plateau (robust).

2D sweep: lookback L in [42, 63, 84, 126, 168] x threshold in [0.15, 0.20, 0.25, 0.30]
= 20 configs + 1 baseline = 21 runs.

Usage:
    python -m research.x39.experiments.exp23_rangepos_lookback_robustness
    # or from x39/:
    python experiments/exp23_rangepos_lookback_robustness.py
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

LOOKBACKS = [42, 63, 84, 126, 168]
THRESHOLDS = [0.15, 0.20, 0.25, 0.30]


def compute_rangepos(high: np.ndarray, low: np.ndarray, close: np.ndarray, lookback: int) -> np.ndarray:
    """Compute rangepos_L = (close - rolling_low) / (rolling_high - rolling_low)."""
    roll_hi = pd.Series(high).rolling(lookback, min_periods=lookback).max().values
    roll_lo = pd.Series(low).rolling(lookback, min_periods=lookback).min().values
    denom = roll_hi - roll_lo
    return np.where(denom > 1e-10, (close - roll_lo) / denom, np.nan)


def run_backtest(
    feat: pd.DataFrame,
    rangepos: np.ndarray | None,
    threshold: float | None,
    lookback: int | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional rangepos_L exit. Returns summary dict.

    If rangepos is None, runs baseline (no rangepos exit).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    use_rangepos = rangepos is not None and threshold is not None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "rangepos": 0}
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
            elif use_rangepos and np.isfinite(rangepos[i]) and rangepos[i] < threshold:
                exit_reason = "rangepos"

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
                })

                exit_counts[exit_reason] += 1
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        label = "baseline" if not use_rangepos else f"L={lookback}_thr={threshold}"
        return {
            "config": label,
            "lookback": lookback,
            "threshold": threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_rangepos": 0,
        }

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

    label = "baseline" if not use_rangepos else f"L={lookback}_thr={threshold}"
    return {
        "config": label,
        "lookback": lookback,
        "threshold": threshold,
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
        "exit_rangepos": exit_counts["rangepos"],
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 23: Rangepos Lookback Robustness")
    print(f"  lookback sweep:  {LOOKBACKS}")
    print(f"  threshold sweep: {THRESHOLDS}")
    print(f"  total configs:   {len(LOOKBACKS) * len(THRESHOLDS)} + 1 baseline")
    print(f"  trail_mult:      {TRAIL_MULT} (fixed)")
    print(f"  cost:            {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # Pre-compute rangepos for all lookbacks (feat has 'close' but not raw high/low)
    high = h4["high"].values.astype(np.float64)
    low = h4["low"].values.astype(np.float64)
    close = feat["close"].values
    rangepos_cache: dict[int, np.ndarray] = {}
    for lb in LOOKBACKS:
        rangepos_cache[lb] = compute_rangepos(high, low, close, lb)
    print(f"Pre-computed rangepos for lookbacks: {LOOKBACKS}")

    # ── Run baseline ──────────────────────────────────────────────────
    results = []
    print("\n[1/21] Baseline (no rangepos exit)...")
    r = run_backtest(feat, None, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, avg_held={r['avg_bars_held']}")

    # ── 2D sweep: lookback x threshold ────────────────────────────────
    run_num = 2
    for lb in LOOKBACKS:
        rp = rangepos_cache[lb]
        for thr in THRESHOLDS:
            print(f"\n[{run_num}/21] L={lb}, thr={thr}...")
            r = run_backtest(feat, rp, thr, lb, warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
            print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, rangepos={r['exit_rangepos']}")
            run_num += 1

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp23_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Analysis 1: Lookback sensitivity at fixed threshold=0.25 ─────
    print("\n" + "=" * 80)
    print("ANALYSIS 1: Lookback sensitivity at threshold=0.25")
    print("=" * 80)
    subset = df[df["threshold"] == 0.25].copy()
    if not subset.empty:
        print(f"  {'L':>5s}  {'Sharpe':>8s}  {'d_Sh':>8s}  {'CAGR%':>8s}  {'MDD%':>8s}  {'d_MDD':>8s}  {'Trades':>6s}  {'RP_exits':>8s}")
        print("  " + "-" * 72)
        for _, row in subset.iterrows():
            print(f"  {int(row['lookback']):5d}  {row['sharpe']:8.4f}  {row['d_sharpe']:+8.4f}  "
                  f"{row['cagr_pct']:8.2f}  {row['mdd_pct']:8.2f}  {row['d_mdd']:+8.2f}  "
                  f"{int(row['trades']):6d}  {int(row['exit_rangepos']):8d}")

        sharpes = subset["sharpe"].values
        sh_range = sharpes.max() - sharpes.min()
        sh_mean = sharpes.mean()
        print(f"\n  Sharpe range: {sh_range:.4f} (min {sharpes.min():.4f} -> max {sharpes.max():.4f})")
        print(f"  Sharpe mean:  {sh_mean:.4f}")
        if sh_range < 0.05:
            print("  -> PLATEAU: Sharpe spread < 0.05 across lookbacks -> ROBUST mechanism")
        elif sh_range < 0.10:
            print("  -> MODERATE: Sharpe spread 0.05-0.10 -> somewhat sensitive to lookback")
        else:
            print("  -> FRAGILE: Sharpe spread >= 0.10 -> lookback choice matters significantly")

    # ── Analysis 2: Threshold sensitivity per lookback ────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 2: Threshold sensitivity per lookback")
    print("=" * 80)
    variants = df[df["lookback"].notna()].copy()
    print(f"  {'L':>5s}  {'best_thr':>8s}  {'best_Sh':>8s}  {'worst_Sh':>9s}  {'Sh_range':>9s}")
    print("  " + "-" * 50)
    for lb in LOOKBACKS:
        lb_rows = variants[variants["lookback"] == lb]
        best_idx = lb_rows["sharpe"].idxmax()
        best_row = lb_rows.loc[best_idx]
        sh_min = lb_rows["sharpe"].min()
        sh_max = lb_rows["sharpe"].max()
        print(f"  {lb:5d}  {best_row['threshold']:8.2f}  {sh_max:8.4f}  {sh_min:9.4f}  {sh_max - sh_min:9.4f}")

    # ── Analysis 3: Best overall config ───────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 3: Best overall config")
    print("=" * 80)

    # Best by Sharpe
    best_sh_idx = variants["sharpe"].idxmax()
    best_sh = variants.loc[best_sh_idx]
    print(f"  Best Sharpe: L={int(best_sh['lookback'])}, thr={best_sh['threshold']} "
          f"-> Sh={best_sh['sharpe']}, d_Sh={best_sh['d_sharpe']:+.4f}, "
          f"MDD={best_sh['mdd_pct']}%, d_MDD={best_sh['d_mdd']:+.2f}")

    # Best by MDD (lowest)
    best_mdd_idx = variants["mdd_pct"].idxmin()
    best_mdd = variants.loc[best_mdd_idx]
    print(f"  Best MDD:    L={int(best_mdd['lookback'])}, thr={best_mdd['threshold']} "
          f"-> MDD={best_mdd['mdd_pct']}%, d_MDD={best_mdd['d_mdd']:+.2f}, "
          f"Sh={best_mdd['sharpe']}, d_Sh={best_mdd['d_sharpe']:+.4f}")

    # Both improved
    both = variants[(variants["d_sharpe"] > 0) & (variants["d_mdd"] < 0)]
    if not both.empty:
        best_both_idx = both["d_sharpe"].idxmax()
        best_both = both.loc[best_both_idx]
        print(f"  Best both:   L={int(best_both['lookback'])}, thr={best_both['threshold']} "
              f"-> Sh={best_both['sharpe']} ({best_both['d_sharpe']:+.4f}), "
              f"MDD={best_both['mdd_pct']}% ({best_both['d_mdd']:+.2f})")
        print(f"  Configs improving BOTH Sharpe AND MDD: {len(both)}/{len(variants)}")
    else:
        print("  No config improves BOTH Sharpe and MDD over baseline.")

    # ── Analysis 4: Heatmap (L x threshold) ───────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 4: Sharpe heatmap (L x threshold)")
    print("=" * 80)
    pivot_sh = variants.pivot(index="lookback", columns="threshold", values="sharpe")
    print(pivot_sh.to_string())

    print(f"\n{'MDD% heatmap (L x threshold)':}")
    pivot_mdd = variants.pivot(index="lookback", columns="threshold", values="mdd_pct")
    print(pivot_mdd.to_string())

    print(f"\n{'Rangepos exit count heatmap (L x threshold)':}")
    pivot_rp = variants.pivot(index="lookback", columns="threshold", values="exit_rangepos")
    print(pivot_rp.to_string())

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Check plateau at threshold=0.25
    subset_025 = df[df["threshold"] == 0.25].copy()
    if not subset_025.empty:
        sh_range_025 = subset_025["sharpe"].max() - subset_025["sharpe"].min()
        all_positive = (subset_025["d_sharpe"] > 0).all()

        if sh_range_025 < 0.05 and all_positive:
            verdict = "ROBUST_PLATEAU"
            print(f"  {verdict}: Sharpe varies only {sh_range_025:.4f} across L=[42..168] at thr=0.25")
            print("  -> Rangepos exit is a ROBUST mechanism, not overfit to L=84")
        elif sh_range_025 < 0.10 and all_positive:
            verdict = "MODERATE_PLATEAU"
            print(f"  {verdict}: Sharpe varies {sh_range_025:.4f} across lookbacks, all above baseline")
            print("  -> Rangepos exit is moderately robust — some lookback sensitivity")
        else:
            best_lb = subset_025.loc[subset_025["sharpe"].idxmax()]
            if sh_range_025 >= 0.10:
                verdict = "FRAGILE"
                print(f"  {verdict}: Sharpe range {sh_range_025:.4f} -> sharp peak at L={int(best_lb['lookback'])}")
                print("  -> Rangepos exit is FRAGILE — performance depends heavily on lookback choice")
            else:
                verdict = "MIXED"
                print(f"  {verdict}: Not all lookbacks beat baseline. Best: L={int(best_lb['lookback'])}")

    # Exp12 reproduction check
    exp12_match = df[(df["lookback"] == 84) & (df["threshold"] == 0.25)]
    if not exp12_match.empty:
        m = exp12_match.iloc[0]
        print(f"\n  Exp12 reproduction (L=84, thr=0.25): Sh={m['sharpe']}, d_Sh={m['d_sharpe']:+.4f}, "
              f"MDD={m['mdd_pct']}%, d_MDD={m['d_mdd']:+.2f}")

    # Exit reason breakdown
    print("\n" + "-" * 40)
    print("Exit reason breakdown:")
    for _, row in df.iterrows():
        total_exits = row["exit_trail"] + row["exit_trend"] + row["exit_rangepos"]
        if total_exits == 0:
            continue
        rp_pct = row["exit_rangepos"] / total_exits if total_exits > 0 else 0
        print(f"  {row['config']:20s}  trail={int(row['exit_trail']):3d} ({row['exit_trail']/total_exits:.0%})"
              f"  trend={int(row['exit_trend']):3d} ({row['exit_trend']/total_exits:.0%})"
              f"  rangepos={int(row['exit_rangepos']):3d} ({rp_pct:.0%})")


if __name__ == "__main__":
    main()
