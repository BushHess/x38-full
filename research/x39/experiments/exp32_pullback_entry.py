#!/usr/bin/env python3
"""Exp 32: Pullback-in-Trend Entry.

Adds a second entry mode (pullback re-entry) to E5-ema21D1.
MODE 1: Standard EMA crossover entry (unchanged).
MODE 2: Pullback to ema_fast within an established trend (trend_age >= N).

Sweeps N in [12, 24, 36, 48] x pullback_margin in [0.0, 0.005, 0.01] = 12 configs + baseline.

Usage:
    python -m research.x39.experiments.exp32_pullback_entry
    # or from x39/:
    python experiments/exp32_pullback_entry.py
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

# ── Sweep grid ────────────────────────────────────────────────────────────
N_VALUES = [12, 24, 36, 48]
MARGIN_VALUES = [0.0, 0.005, 0.01]


def run_backtest(
    feat: pd.DataFrame,
    n_establish: int | None,
    pullback_margin: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional pullback re-entry mode.

    If n_establish is None → baseline (MODE 1 only, standard crossover).
    Otherwise → MODE 1 + MODE 2 (pullback re-entry when trend_age >= n_establish).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    # Trend-age tracking
    trend_age = 0  # consecutive bars where ema_fast > ema_slow
    prev_trend_up = False  # for detecting crossover (MODE 1)

    # Mode counters
    mode1_entries = 0
    mode2_entries = 0
    mode2_entry_prices: list[float] = []
    mode2_ema_fast_at_entry: list[float] = []

    # Equity tracking
    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]) or np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        trend_up = ema_f[i] > ema_s[i]

        # Update trend age
        if trend_up:
            trend_age += 1
        else:
            trend_age = 0

        if not in_pos:
            equity[i] = cash

            # Base conditions (shared by both modes)
            base_ok = vdo_arr[i] > 0 and d1_ok[i]

            entry_mode = None

            if base_ok and trend_up:
                if n_establish is None:
                    # Baseline: standard crossover-style (enter whenever conditions met)
                    entry_mode = 1
                else:
                    # MODE 1: fresh crossover (first bar of new uptrend)
                    if trend_up and not prev_trend_up:
                        entry_mode = 1
                    # MODE 2: pullback re-entry within established trend
                    elif trend_age >= n_establish:
                        pullback_ok = c[i] <= ema_f[i] * (1 + pullback_margin)
                        if pullback_ok:
                            entry_mode = 2

            if entry_mode is not None:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / c[i]
                cash = 0.0

                if entry_mode == 1:
                    mode1_entries += 1
                else:
                    mode2_entries += 1
                    mode2_entry_prices.append(c[i])
                    mode2_ema_fast_at_entry.append(ema_f[i])
        else:
            # Mark to market
            equity[i] = position_size * c[i]
            peak = max(peak, c[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"

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

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

        prev_trend_up = trend_up

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return {
            "N": n_establish if n_establish is not None else "baseline",
            "margin": pullback_margin if pullback_margin is not None else "baseline",
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "exposure_pct": np.nan,
            "avg_bars_held": np.nan,
            "mode1_entries": 0, "mode2_entries": 0,
            "avg_m2_entry_vs_ema_pct": np.nan,
        }

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4  # ~2191.5

    # Sharpe
    sharpe = (rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0

    # CAGR
    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    # MDD
    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    # Exposure & holding period
    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars
    avg_bars_held = total_bars_held / len(trades)

    # Win rate
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["win"] == 1]

    # MODE 2 average entry price vs ema_fast (how far below ema_fast)
    avg_m2_entry_vs_ema = np.nan
    if mode2_entry_prices:
        diffs = [
            (p - e) / e * 100
            for p, e in zip(mode2_entry_prices, mode2_ema_fast_at_entry)
        ]
        avg_m2_entry_vs_ema = np.mean(diffs)

    return {
        "N": n_establish if n_establish is not None else "baseline",
        "margin": pullback_margin if pullback_margin is not None else "baseline",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "exposure_pct": round(exposure * 100, 1),
        "avg_bars_held": round(avg_bars_held, 1),
        "mode1_entries": mode1_entries,
        "mode2_entries": mode2_entries,
        "avg_m2_entry_vs_ema_pct": round(avg_m2_entry_vs_ema, 3) if np.isfinite(avg_m2_entry_vs_ema) else np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 32: Pullback-in-Trend Entry")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Warmup: same as baseline E5-ema21D1
    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # ── Run baseline ──────────────────────────────────────────────────
    print("\nRunning baseline (MODE 1 only, standard E5-ema21D1)...")
    base_r = run_backtest(feat, None, None, warmup_bar)
    print(f"  Sharpe={base_r['sharpe']}, CAGR={base_r['cagr_pct']}%, "
          f"MDD={base_r['mdd_pct']}%, trades={base_r['trades']}, "
          f"exposure={base_r['exposure_pct']}%")

    results = [base_r]

    # ── Run sweep ─────────────────────────────────────────────────────
    for n_val in N_VALUES:
        for margin in MARGIN_VALUES:
            label = f"N={n_val}, margin={margin:.3f}"
            print(f"\nRunning {label}...")
            r = run_backtest(feat, n_val, margin, warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, "
                  f"MDD={r['mdd_pct']}%, trades={r['trades']} "
                  f"(M1={r['mode1_entries']}, M2={r['mode2_entries']}), "
                  f"exposure={r['exposure_pct']}%")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    # Add deltas vs baseline
    base = df.iloc[0]
    df["d_sharpe"] = round(df["sharpe"] - base["sharpe"], 4)
    df["d_cagr"] = round(df["cagr_pct"] - base["cagr_pct"], 2)
    df["d_mdd"] = round(df["mdd_pct"] - base["mdd_pct"], 2)  # positive = worse

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    # Save
    out_path = RESULTS_DIR / "exp32_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    gated = df.iloc[1:]

    # Check if any config improves Sharpe AND MDD simultaneously
    improvements = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: N={best['N']}, margin={best['margin']} improves both "
              f"Sharpe ({best['d_sharpe']:+.4f}) and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Trades: {int(best['trades'])} (M1={int(best['mode1_entries'])}, "
              f"M2={int(best['mode2_entries'])})")
        if np.isfinite(best["avg_m2_entry_vs_ema_pct"]):
            print(f"  Avg MODE 2 entry vs ema_fast: {best['avg_m2_entry_vs_ema_pct']:+.3f}%")
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: N={best['N']}, margin={best['margin']} improves "
                  f"Sharpe ({best['d_sharpe']:+.4f}) but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No config improves Sharpe over baseline.")
            print("Pullback re-entry does NOT help E5-ema21D1.")

    # Mode 2 contribution analysis
    print("\n" + "-" * 40)
    print("MODE 2 (Pullback) Contribution:")
    m2_configs = gated[gated["mode2_entries"] > 0]
    if not m2_configs.empty:
        print(f"  Configs with MODE 2 entries: {len(m2_configs)}/{len(gated)}")
        print(f"  MODE 2 entries range: {int(m2_configs['mode2_entries'].min())} - "
              f"{int(m2_configs['mode2_entries'].max())}")
        valid_m2 = m2_configs[m2_configs["avg_m2_entry_vs_ema_pct"].notna()]
        if not valid_m2.empty:
            print(f"  Avg entry vs ema_fast: "
                  f"{valid_m2['avg_m2_entry_vs_ema_pct'].mean():+.3f}% "
                  f"(negative = below ema)")
    else:
        print("  No MODE 2 entries triggered in any config.")


if __name__ == "__main__":
    main()
