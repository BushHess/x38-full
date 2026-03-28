#!/usr/bin/env python3
"""Exp 09: Replace D1 EMA(21) Regime with D1 Anti-Vol.

Replaces D1 close > D1 EMA(21) regime filter with D1 rangevol84_rank365 < threshold.
- Original: "Is D1 trending up?"
- Modified: "Is D1 volatility low (orderly market)?"

Entry: ema_fast > ema_slow AND vdo > 0 AND d1_rangevol84_rank365 < threshold
Exit:  trail stop OR EMA cross-down (unchanged)

Sweeps threshold in [0.30, 0.40, 0.50, 0.60, 0.70] + baseline.

Usage:
    python -m research.x39.experiments.exp09_replace_d1regime
    # or from x39/:
    python experiments/exp09_replace_d1regime.py
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

THRESHOLDS = [0.30, 0.40, 0.50, 0.60, 0.70]


def run_baseline(
    feat: pd.DataFrame,
    warmup_bar: int,
) -> dict:
    """Original E5-ema21D1 (D1 EMA(21) regime filter)."""
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

    return _compute_metrics(equity, trades, warmup_bar, "baseline_d1ema21")


def run_antivol(
    feat: pd.DataFrame,
    threshold: float,
    warmup_bar: int,
) -> dict:
    """Modified: D1 anti-vol rank < threshold replaces D1 EMA(21) regime."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_rv_rank = feat["d1_rangevol84_rank365"].values
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
        if np.isnan(ratr[i]) or np.isnan(d1_rv_rank[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash
            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_rv_rank[i] < threshold
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

    return _compute_metrics(equity, trades, warmup_bar, f"antivol_th={threshold}")


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
    print("EXP 09: Replace D1 EMA(21) Regime with D1 Anti-Vol")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # ── Feature diagnostics ──────────────────────────────────────────
    rv_rank = feat["d1_rangevol84_rank365"].values
    valid_count = np.isfinite(rv_rank).sum()
    print(f"d1_rangevol84_rank365: {valid_count}/{len(rv_rank)} valid bars")
    valid_vals = rv_rank[np.isfinite(rv_rank)]
    if len(valid_vals) > 0:
        print(f"  Range: [{valid_vals.min():.4f}, {valid_vals.max():.4f}]")
        print(f"  Mean: {valid_vals.mean():.4f}, Std: {valid_vals.std():.4f}")
        for th in THRESHOLDS:
            pct = np.mean(valid_vals < th) * 100
            print(f"  Bars with rank < {th} (entry allowed): {pct:.1f}%")

    # ── Overlap analysis: D1 EMA(21) vs D1 anti-vol ─────────────────
    d1_ok = feat["d1_regime_ok"].values.astype(bool)
    both_valid = np.isfinite(rv_rank) & np.isfinite(d1_ok.astype(float))
    if both_valid.sum() > 0:
        print(f"\nOverlap analysis (on {both_valid.sum()} bars with both valid):")
        for th in THRESHOLDS:
            antivol_ok = rv_rank < th
            agree = (d1_ok & antivol_ok) | (~d1_ok & ~antivol_ok)
            agree_pct = agree[both_valid].mean() * 100
            both_on = (d1_ok & antivol_ok)[both_valid].mean() * 100
            ema_only = (d1_ok & ~antivol_ok)[both_valid].mean() * 100
            vol_only = (~d1_ok & antivol_ok)[both_valid].mean() * 100
            print(f"  th={th}: agree={agree_pct:.1f}%, both_on={both_on:.1f}%, "
                  f"ema_only={ema_only:.1f}%, antivol_only={vol_only:.1f}%")

    first_valid = 0
    for i in range(len(rv_rank)):
        if np.isfinite(rv_rank[i]):
            first_valid = i
            break

    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"\nWarmup bar: {warmup_bar} (d1_rangevol84_rank365 first valid at {first_valid})")

    # ── Run baseline ──────────────────────────────────────────────────
    print("\nRunning baseline (original E5-ema21D1 with D1 EMA(21))...")
    base_r = run_baseline(feat, warmup_bar)
    print(f"  Sharpe={base_r['sharpe']}, CAGR={base_r['cagr_pct']}%, "
          f"MDD={base_r['mdd_pct']}%, trades={base_r['trades']}, "
          f"exposure={base_r['exposure_pct']}%")

    results = [base_r]

    # ── Run anti-vol variants ─────────────────────────────────────────
    for th in THRESHOLDS:
        label = f"antivol_th={th}"
        print(f"\nRunning {label}...")
        r = run_antivol(feat, th, warmup_bar)
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

    out_path = RESULTS_DIR / "exp09_results.csv"
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
        print("D1 anti-vol is a better regime definition than D1 EMA(21) trend direction.")
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
            print("D1 anti-vol captures DIFFERENT information than D1 EMA(21) — "
                  "consider combining (see exp01).")
        else:
            print("FAIL: No anti-vol threshold improves Sharpe over D1 EMA(21) baseline.")
            print("D1 trend direction (EMA(21)) is a better regime filter than D1 volatility.")


if __name__ == "__main__":
    main()
