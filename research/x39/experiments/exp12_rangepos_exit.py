#!/usr/bin/env python3
"""Exp 12: Range Position Exit.

E5-ema21D1 with rangepos_84 supplementary exit.
When rangepos_84 drops below threshold → exit (price falling within recent range).

Entry logic UNCHANGED. Only adds rangepos exit as additional exit condition.

Sweep:
  threshold in [0.15, 0.20, 0.25, 0.30, 0.35]
  → 5 configs + baseline (no rangepos exit)

Usage:
    python -m research.x39.experiments.exp12_rangepos_exit
    # or from x39/:
    python experiments/exp12_rangepos_exit.py
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

THRESHOLDS = [0.15, 0.20, 0.25, 0.30, 0.35]


def run_backtest(
    feat: pd.DataFrame,
    threshold: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional rangepos exit. Returns summary dict.

    If threshold is None, runs baseline (no rangepos exit).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    n = len(c)

    use_rangepos = threshold is not None

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
        return {
            "config": "baseline" if not use_rangepos else f"thr={threshold}",
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

    return {
        "config": "baseline" if not use_rangepos else f"thr={threshold}",
        "threshold": threshold if use_rangepos else None,
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
    print("EXP 12: Range Position Exit")
    print(f"  threshold sweep: {THRESHOLDS}")
    print(f"  trail_mult:      {TRAIL_MULT} (fixed)")
    print(f"  cost:            {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # Run baseline
    results = []
    print("\nRunning baseline (no rangepos exit)...")
    r = run_backtest(feat, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
    print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}")

    # Sweep thresholds
    for thr in THRESHOLDS:
        label = f"threshold={thr}"
        print(f"\nRunning {label}...")
        r = run_backtest(feat, thr, warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
        print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, rangepos={r['exit_rangepos']}")

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

    out_path = RESULTS_DIR / "exp12_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n→ Saved to {out_path}")

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
              f"rangepos={int(best['exit_rangepos'])}")
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
            print("FAIL: No rangepos exit threshold improves Sharpe or MDD over baseline.")
            print("rangepos_84 exit does NOT help E5-ema21D1.")

    # Exit reason breakdown
    print("\n" + "-" * 40)
    print("Exit reason breakdown:")
    for _, row in df.iterrows():
        total_exits = row["exit_trail"] + row["exit_trend"] + row["exit_rangepos"]
        if total_exits == 0:
            continue
        print(f"  {row['config']:15s}  trail={int(row['exit_trail']):3d} ({row['exit_trail']/total_exits:.0%})"
              f"  trend={int(row['exit_trend']):3d} ({row['exit_trend']/total_exits:.0%})"
              f"  rangepos={int(row['exit_rangepos']):3d} ({row['exit_rangepos']/total_exits:.0%})")


if __name__ == "__main__":
    main()
