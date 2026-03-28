#!/usr/bin/env python3
"""Exp 36: Regime-Split Trail Multiplier.

E5-ema21D1 with trail_mult adapted by H4 volatility percentile rank.
Low vol → tighter trail (capture more before reversal).
High vol → wider trail (prevent whipsaw exits).

Entry logic UNCHANGED. Only exit trail multiplier changes.
Trail multiplier CAN change mid-trade (adapts to current conditions).

Sweep:
  vol_split = 0.50 (fixed — symmetric median split)
  trail_low  in [2.0, 2.5, 3.0]
  trail_high in [3.0, 3.5, 4.0, 4.5]
  constraint: trail_low <= trail_high → 12 configs
  (3.0, 3.0) = baseline sanity check

Usage:
    python -m research.x39.experiments.exp36_regime_split_trail
    # or from x39/:
    python experiments/exp36_regime_split_trail.py
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

# ── Experiment parameters ─────────────────────────────────────────────────
VOL_SPLIT = 0.50  # percentile threshold (median)
RATR_PCTL_LOOKBACK = 365  # H4 bars (~60 days)

TRAIL_LOWS = [2.0, 2.5, 3.0]
TRAIL_HIGHS = [3.0, 3.5, 4.0, 4.5]


def compute_ratr_pctl(ratr_pct: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling percentile rank of ratr_pct over trailing `lookback` bars."""
    n = len(ratr_pct)
    pctl = np.full(n, np.nan)
    for i in range(lookback, n):
        window = ratr_pct[i - lookback:i]
        valid = window[np.isfinite(window)]
        if len(valid) > 0 and np.isfinite(ratr_pct[i]):
            pctl[i] = np.mean(valid < ratr_pct[i])
    return pctl


def run_backtest(
    feat: pd.DataFrame,
    ratr_pctl: np.ndarray,
    trail_low: float | None,
    trail_high: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional regime-split trail. Returns summary dict.

    If trail_low/trail_high are None, uses fixed BASELINE_TRAIL_MULT (baseline).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    is_adaptive = trail_low is not None and trail_high is not None

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    # Per-regime tracking
    exits_low_vol = 0
    exits_high_vol = 0
    trail_widths_low: list[float] = []
    trail_widths_high: list[float] = []

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
            is_low_vol = (
                is_adaptive
                and np.isfinite(ratr_pctl[i])
                and ratr_pctl[i] < VOL_SPLIT
            )

            if is_adaptive and np.isfinite(ratr_pctl[i]):
                if is_low_vol:
                    current_trail = trail_low
                else:
                    current_trail = trail_high
            elif is_adaptive:
                current_trail = BASELINE_TRAIL_MULT  # fallback if pctl not ready
            else:
                current_trail = BASELINE_TRAIL_MULT

            trail_width = current_trail * ratr[i]
            trail_stop = peak - trail_width

            # Track trail widths per regime
            if is_adaptive and np.isfinite(ratr_pctl[i]):
                if is_low_vol:
                    trail_widths_low.append(trail_width)
                else:
                    trail_widths_high.append(trail_width)

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

                # Track per-regime exits
                if is_adaptive and np.isfinite(ratr_pctl[i]):
                    if is_low_vol:
                        exits_low_vol += 1
                    else:
                        exits_high_vol += 1

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

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": "baseline" if not is_adaptive else f"lo={trail_low}/hi={trail_high}",
            "trail_low": trail_low, "trail_high": trail_high,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "exposure_pct": np.nan,
            "exits_low_vol": 0, "exits_high_vol": 0,
            "avg_trail_width_low": np.nan, "avg_trail_width_high": np.nan,
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

    return {
        "config": "baseline" if not is_adaptive else f"lo={trail_low}/hi={trail_high}",
        "trail_low": trail_low if is_adaptive else BASELINE_TRAIL_MULT,
        "trail_high": trail_high if is_adaptive else BASELINE_TRAIL_MULT,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "exposure_pct": round(exposure * 100, 1),
        "exits_low_vol": exits_low_vol,
        "exits_high_vol": exits_high_vol,
        "avg_trail_width_low": (
            round(np.mean(trail_widths_low), 2) if trail_widths_low else np.nan
        ),
        "avg_trail_width_high": (
            round(np.mean(trail_widths_high), 2) if trail_widths_high else np.nan
        ),
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build valid configs (trail_low <= trail_high)
    configs = [
        (tl, th) for tl in TRAIL_LOWS for th in TRAIL_HIGHS if tl <= th
    ]

    print("=" * 80)
    print("EXP 36: Regime-Split Trail Multiplier")
    print(f"  vol_split (percentile):  {VOL_SPLIT}")
    print(f"  ratr_pctl lookback:      {RATR_PCTL_LOOKBACK} H4 bars")
    print(f"  trail_low sweep:         {TRAIL_LOWS}")
    print(f"  trail_high sweep:        {TRAIL_HIGHS}")
    print(f"  valid configs:           {len(configs)}")
    print(f"  baseline trail:          {BASELINE_TRAIL_MULT}")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Compute ratr_pctl (rolling percentile of ratr_pct over 365 H4 bars)
    ratr_pct = feat["ratr_pct"].values
    print(f"\nComputing ratr_pctl (lookback={RATR_PCTL_LOOKBACK})...")
    ratr_pctl = compute_ratr_pctl(ratr_pct, RATR_PCTL_LOOKBACK)

    first_valid = 0
    for i in range(len(ratr_pctl)):
        if np.isfinite(ratr_pctl[i]):
            first_valid = i
            break
    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"Warmup bar: {warmup_bar} (first valid ratr_pctl at {first_valid})")

    # Regime stats
    valid_pctl = ratr_pctl[warmup_bar:]
    valid_mask = np.isfinite(valid_pctl)
    n_low = np.sum(valid_pctl[valid_mask] < VOL_SPLIT)
    n_high = np.sum(valid_pctl[valid_mask] >= VOL_SPLIT)
    print(f"Regime split: low_vol={n_low} bars ({n_low / valid_mask.sum() * 100:.1f}%), "
          f"high_vol={n_high} bars ({n_high / valid_mask.sum() * 100:.1f}%)")

    # Run baseline
    results = []
    print("\nRunning baseline (fixed trail=3.0)...")
    r = run_backtest(feat, ratr_pctl, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, exposure={r['exposure_pct']}%")

    # Sweep configs
    for trail_low, trail_high in configs:
        label = f"lo={trail_low}, hi={trail_high}"
        sanity = " (= baseline)" if trail_low == trail_high == BASELINE_TRAIL_MULT else ""
        print(f"\nRunning {label}{sanity}...")
        r = run_backtest(feat, ratr_pctl, trail_low, trail_high, warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, exits_lo={r['exits_low_vol']}, exits_hi={r['exits_high_vol']}")

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

    out_path = RESULTS_DIR / "exp36_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n→ Saved to {out_path}")

    # ── Sanity check: (3.0, 3.0) should match baseline ───────────────
    sanity_row = df[
        (df["trail_low"] == BASELINE_TRAIL_MULT)
        & (df["trail_high"] == BASELINE_TRAIL_MULT)
        & (df["config"] != "baseline")
    ]
    if not sanity_row.empty:
        sr = sanity_row.iloc[0]
        sanity_ok = abs(sr["d_sharpe"]) < 0.001
        print(f"\nSanity (3.0/3.0): d_sharpe={sr['d_sharpe']:+.4f} "
              f"{'✓ OK' if sanity_ok else '✗ MISMATCH'}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    dynamic = df[df["config"] != "baseline"]
    # Exclude (3.0, 3.0) sanity check from verdict
    dynamic = dynamic[~(
        (dynamic["trail_low"] == BASELINE_TRAIL_MULT)
        & (dynamic["trail_high"] == BASELINE_TRAIL_MULT)
    )]

    improvements = dynamic[(dynamic["d_sharpe"] > 0) & (dynamic["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        print(f"  Exits: low_vol={int(best['exits_low_vol'])}, "
              f"high_vol={int(best['exits_high_vol'])}")
        print(f"  Avg trail width: low={best['avg_trail_width_low']}, "
              f"high={best['avg_trail_width_high']}")
    else:
        sharpe_up = dynamic[dynamic["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No regime-split trail config improves Sharpe over baseline.")
            print("Fixed trail_mult=3.0 is already optimal or near-optimal.")

    # ── Regime breakdown ──────────────────────────────────────────────
    print("\n" + "-" * 40)
    print("Regime exit breakdown:")
    for _, row in dynamic.iterrows():
        total_exits = row["exits_low_vol"] + row["exits_high_vol"]
        if total_exits > 0:
            pct_lo = row["exits_low_vol"] / total_exits * 100
            pct_hi = row["exits_high_vol"] / total_exits * 100
            print(f"  {row['config']:20s} → low_vol {int(row['exits_low_vol']):3d} "
                  f"({pct_lo:4.1f}%), high_vol {int(row['exits_high_vol']):3d} ({pct_hi:4.1f}%)")


if __name__ == "__main__":
    main()
