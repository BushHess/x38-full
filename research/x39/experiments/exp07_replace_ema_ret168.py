#!/usr/bin/env python3
"""Exp 07: Replace EMA Crossover with ret_168.

Replaces EMA fast/slow crossover entry AND EMA cross-down exit with ret_168.
Entry: ret_168 > 0  (price above 28-day-ago level)
Exit:  close < trail_stop OR ret_168 < exit_threshold

Sweeps exit_threshold in [-0.05, -0.02, 0.0, 0.02, 0.05] + baseline (original E5-ema21D1).

Usage:
    python -m research.x39.experiments.exp07_replace_ema_ret168
    # or from x39/:
    python experiments/exp07_replace_ema_ret168.py
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

EXIT_THRESHOLDS = [-0.05, -0.02, 0.0, 0.02, 0.05]


def run_baseline(
    feat: pd.DataFrame,
    warmup_bar: int,
) -> dict:
    """Original E5-ema21D1 (EMA crossover entry + EMA cross-down exit)."""
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

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
            continue

        if not in_pos:
            equity[i] = cash
            entry_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]
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

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price, "exit_price": c[i],
                    "gross_ret": gross_ret, "net_ret": net_ret,
                    "exit_reason": exit_reason, "win": int(net_ret > 0),
                })
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    return _compute_metrics(equity, trades, warmup_bar, "baseline")


def run_ret168(
    feat: pd.DataFrame,
    exit_threshold: float,
    warmup_bar: int,
) -> dict:
    """Modified: ret_168 > 0 entry, ret_168 < exit_threshold exit."""
    c = feat["close"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    ret168 = feat["ret_168"].values
    n = len(c)

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]) or np.isnan(ret168[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash
            entry_ok = ret168[i] > 0 and vdo_arr[i] > 0 and d1_ok[i]
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
            elif ret168[i] < exit_threshold:
                exit_reason = "trend_ret168"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost
                trades.append({
                    "entry_bar": entry_bar, "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price, "exit_price": c[i],
                    "gross_ret": gross_ret, "net_ret": net_ret,
                    "exit_reason": exit_reason, "win": int(net_ret > 0),
                })
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    return _compute_metrics(equity, trades, warmup_bar, f"exit_th={exit_threshold}")


def _compute_metrics(
    equity: np.ndarray,
    trades: list[dict],
    warmup_bar: int,
    label: str,
) -> dict:
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": label,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_win": np.nan,
            "avg_loss": np.nan, "exposure_pct": np.nan,
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
        "config": label,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_win": round(wins["net_ret"].mean() * 100, 2) if len(wins) > 0 else np.nan,
        "avg_loss": round(losses["net_ret"].mean() * 100, 2) if len(losses) > 0 else np.nan,
        "exposure_pct": round(exposure * 100, 1),
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 07: Replace EMA Crossover with ret_168")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    ret168 = feat["ret_168"].values
    valid_count = np.isfinite(ret168).sum()
    print(f"ret_168: {valid_count}/{len(ret168)} valid bars")
    valid_vals = ret168[np.isfinite(ret168)]
    if len(valid_vals) > 0:
        print(f"  Range: [{valid_vals.min():.4f}, {valid_vals.max():.4f}]")
        print(f"  Mean: {valid_vals.mean():.4f}, Std: {valid_vals.std():.4f}")
        pct_pos = np.mean(valid_vals > 0) * 100
        print(f"  Bars with ret_168 > 0 (entry allowed): {pct_pos:.1f}%")

    first_valid_ret168 = 0
    for i in range(len(ret168)):
        if np.isfinite(ret168[i]):
            first_valid_ret168 = i
            break

    warmup_bar = max(SLOW_PERIOD, first_valid_ret168, 168)
    print(f"Warmup bar: {warmup_bar} (ret_168 first valid at {first_valid_ret168})")

    # ── Run baseline ──────────────────────────────────────────────────
    print("\nRunning baseline (original E5-ema21D1)...")
    base_r = run_baseline(feat, warmup_bar)
    print(f"  Sharpe={base_r['sharpe']}, CAGR={base_r['cagr_pct']}%, "
          f"MDD={base_r['mdd_pct']}%, trades={base_r['trades']}, "
          f"exposure={base_r['exposure_pct']}%")

    results = [base_r]

    # ── Run ret_168 variants ──────────────────────────────────────────
    for eth in EXIT_THRESHOLDS:
        label = f"exit_th={eth}"
        print(f"\nRunning {label}...")
        r = run_ret168(feat, eth, warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, "
              f"MDD={r['mdd_pct']}%, trades={r['trades']}, "
              f"exposure={r['exposure_pct']}%")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp07_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    gated = df.iloc[1:]
    improvements = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No exit_threshold improves Sharpe over baseline.")
            print("ret_168 does NOT work as EMA crossover replacement for E5-ema21D1.")


if __name__ == "__main__":
    main()
