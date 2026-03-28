#!/usr/bin/env python3
"""Exp 38: Trend Maturity Trail Decay.

As a trend matures (ema_fast > ema_slow for many bars), tighten the trail
stop linearly from trail_base to trail_min.  Grace period (decay_start)
allows early trend development; full decay reached at decay_end.

Entry logic UNCHANGED.  Only exit trail multiplier changes per bar.

Sweep:
  trail_base = 3.0 (FIXED, same as baseline)
  trail_min  in [1.5, 2.0, 2.5]
  decay_start in [30, 60]   H4 bars (~5 or ~10 days)
  decay_end   in [120, 180, 240] H4 bars (~20, 30, or 40 days)
  constraint: decay_start < decay_end  → 18 configs

Usage:
    python -m research.x39.experiments.exp38_trend_maturity_decay
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
BASELINE_TRAIL_MULT = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365

# ── Experiment parameters ─────────────────────────────────────────────────
TRAIL_BASE = 3.0
TRAIL_MINS = [1.5, 2.0, 2.5]
DECAY_STARTS = [30, 60]       # H4 bars
DECAY_ENDS = [120, 180, 240]  # H4 bars


def compute_trend_age(ema_fast: np.ndarray, ema_slow: np.ndarray) -> np.ndarray:
    """Bars since most recent EMA crossover (fast > slow).

    Resets to 0 when ema_fast drops below ema_slow.
    While ema_fast > ema_slow, increments each bar.
    """
    n = len(ema_fast)
    age = np.zeros(n, dtype=np.int32)
    for i in range(1, n):
        if ema_fast[i] > ema_slow[i]:
            age[i] = age[i - 1] + 1
        # else: age[i] stays 0
    return age


def effective_trail(
    trend_age: int,
    trail_base: float,
    trail_min: float,
    decay_start: int,
    decay_end: int,
) -> float:
    """Linear decay from trail_base to trail_min between decay_start and decay_end."""
    if trend_age < decay_start:
        return trail_base
    if trend_age >= decay_end:
        return trail_min
    progress = (trend_age - decay_start) / (decay_end - decay_start)
    return trail_base - (trail_base - trail_min) * progress


def run_backtest(
    feat: pd.DataFrame,
    trend_age: np.ndarray,
    warmup_bar: int,
    *,
    trail_min: float | None = None,
    decay_start: int | None = None,
    decay_end: int | None = None,
) -> dict:
    """Replay E5-ema21D1 with optional trend-maturity trail decay."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    is_decay = trail_min is not None

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    # Tracking effective trail at exit
    trail_at_exit: list[float] = []
    age_at_exit: list[int] = []

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

            # Determine trail multiplier
            if is_decay:
                current_trail = effective_trail(
                    trend_age[i], TRAIL_BASE, trail_min, decay_start, decay_end,
                )
            else:
                current_trail = BASELINE_TRAIL_MULT

            trail_stop = peak - current_trail * ratr[i]

            exit_reason = None
            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                cost = COST_BPS / 10_000
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost

                trail_at_exit.append(current_trail)
                age_at_exit.append(int(trend_age[i]))

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
                    "trend_age_at_exit": int(trend_age[i]),
                    "effective_trail_at_exit": current_trail,
                })

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result(trail_min, decay_start, decay_end, is_decay)

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = (
        rets.mean() / rets.std() * np.sqrt(bars_per_year)
        if rets.std() > 0
        else 0.0
    )

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

    # Top 10% longest trades impact
    duration_p90 = tdf["bars_held"].quantile(0.90)
    long_trades = tdf[tdf["bars_held"] >= duration_p90]
    long_avg_net = long_trades["net_ret"].mean() if len(long_trades) > 0 else np.nan
    long_count = len(long_trades)

    config_label = (
        "baseline"
        if not is_decay
        else f"min={trail_min}/start={decay_start}/end={decay_end}"
    )

    return {
        "config": config_label,
        "trail_min": trail_min if is_decay else TRAIL_BASE,
        "decay_start": decay_start if is_decay else 0,
        "decay_end": decay_end if is_decay else 0,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "exposure_pct": round(exposure * 100, 1),
        "avg_trend_age_exit": round(np.mean(age_at_exit), 1),
        "avg_eff_trail_exit": round(np.mean(trail_at_exit), 3),
        "long_trade_count": long_count,
        "long_trade_avg_net": round(long_avg_net * 100, 2) if np.isfinite(long_avg_net) else np.nan,
    }


def _empty_result(
    trail_min: float | None,
    decay_start: int | None,
    decay_end: int | None,
    is_decay: bool,
) -> dict:
    config_label = (
        "baseline"
        if not is_decay
        else f"min={trail_min}/start={decay_start}/end={decay_end}"
    )
    return {
        "config": config_label,
        "trail_min": trail_min, "decay_start": decay_start, "decay_end": decay_end,
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "avg_trend_age_exit": np.nan,
        "avg_eff_trail_exit": np.nan, "long_trade_count": 0,
        "long_trade_avg_net": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    configs = [
        (tm, ds, de)
        for tm in TRAIL_MINS
        for ds in DECAY_STARTS
        for de in DECAY_ENDS
        if ds < de
    ]

    print("=" * 80)
    print("EXP 38: Trend Maturity Trail Decay")
    print(f"  trail_base:       {TRAIL_BASE}")
    print(f"  trail_min sweep:  {TRAIL_MINS}")
    print(f"  decay_start:      {DECAY_STARTS} H4 bars")
    print(f"  decay_end:        {DECAY_ENDS} H4 bars")
    print(f"  valid configs:    {len(configs)}")
    print(f"  baseline trail:   {BASELINE_TRAIL_MULT}")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values

    print("\nComputing trend_age...")
    trend_age = compute_trend_age(ema_f, ema_s)

    # Warmup: 365 days worth of H4 bars (6 bars/day)
    bars_per_day = 24 / 4
    warmup_bar = int(WARMUP_DAYS * bars_per_day)
    print(f"Warmup bar: {warmup_bar} ({WARMUP_DAYS} days)")

    # Trend age stats in eval window
    eval_age = trend_age[warmup_bar:]
    in_trend = eval_age > 0
    print(f"Trend age stats (eval window): "
          f"mean={eval_age[in_trend].mean():.1f}, "
          f"median={np.median(eval_age[in_trend]):.0f}, "
          f"p90={np.percentile(eval_age[in_trend], 90):.0f}, "
          f"max={eval_age.max()}")

    # Run baseline
    results = []
    print("\nRunning baseline (fixed trail=3.0)...")
    r = run_backtest(feat, trend_age, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, exposure={r['exposure_pct']}%")
    print(f"  avg_trend_age_exit={r['avg_trend_age_exit']}, "
          f"avg_eff_trail={r['avg_eff_trail_exit']}")

    # Sweep configs
    for trail_min, decay_start, decay_end in configs:
        label = f"min={trail_min}, start={decay_start}, end={decay_end}"
        print(f"\nRunning {label}...")
        r = run_backtest(
            feat, trend_age, warmup_bar,
            trail_min=trail_min, decay_start=decay_start, decay_end=decay_end,
        )
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, avg_age_exit={r['avg_trend_age_exit']}, "
              f"avg_trail={r['avg_eff_trail_exit']}")

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

    out_path = RESULTS_DIR / "exp38_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Long-trade impact ─────────────────────────────────────────────
    print("\n" + "-" * 40)
    print("Long-trade impact (top 10% by duration):")
    base_long = base["long_trade_avg_net"]
    for _, row in df.iterrows():
        if row["config"] == "baseline":
            print(f"  {'baseline':42s} avg_net={row['long_trade_avg_net']:+.2f}% "
                  f"(n={int(row['long_trade_count'])})")
        else:
            d = row["long_trade_avg_net"] - base_long if np.isfinite(row["long_trade_avg_net"]) else np.nan
            d_str = f"{d:+.2f}" if np.isfinite(d) else "NaN"
            print(f"  {row['config']:42s} avg_net={row['long_trade_avg_net']:+.2f}% "
                  f"(n={int(row['long_trade_count'])}, delta={d_str}pp)")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    dynamic = df[df["config"] != "baseline"]

    improvements = dynamic[(dynamic["d_sharpe"] > 0) & (dynamic["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        print(f"  avg_trend_age_exit={best['avg_trend_age_exit']}, "
              f"avg_eff_trail={best['avg_eff_trail_exit']}")
    else:
        sharpe_up = dynamic[dynamic["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No trend-maturity decay config improves Sharpe over baseline.")
            print("Fixed trail_mult=3.0 is already optimal across trend durations.")

    # ── Decay effectiveness ───────────────────────────────────────────
    print("\n" + "-" * 40)
    print("Effective trail at exit (how much decay actually applied):")
    for _, row in dynamic.iterrows():
        print(f"  {row['config']:42s} avg_eff_trail={row['avg_eff_trail_exit']:.3f} "
              f"(trail_min={row['trail_min']})")


if __name__ == "__main__":
    main()
