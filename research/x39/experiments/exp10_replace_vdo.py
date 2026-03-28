#!/usr/bin/env python3
"""Exp 10: Replace VDO with Trade Surprise.

Replaces VDO > 0 filter with trade_surprise_168 > threshold.
- Original (VDO): "Are buyers or sellers more aggressive?"
- Modified (trade surprise): "Is participation unusually high for this volume level?"

Entry: ema_fast > ema_slow AND trade_surprise_168 > threshold AND d1_regime_ok
Exit:  trail stop OR EMA cross-down (unchanged)

Sweeps threshold in [-0.05, 0.0, 0.05, 0.10, 0.15] + baseline.

Usage:
    python -m research.x39.experiments.exp10_replace_vdo
    # or from x39/:
    python experiments/exp10_replace_vdo.py
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

THRESHOLDS = [-0.05, 0.0, 0.05, 0.10, 0.15]


def run_baseline(
    feat: pd.DataFrame,
    warmup_bar: int,
) -> dict:
    """Original E5-ema21D1 (VDO > 0 filter)."""
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

    return _compute_metrics(equity, trades, warmup_bar, "baseline_vdo")


def run_trade_surprise(
    feat: pd.DataFrame,
    threshold: float,
    warmup_bar: int,
) -> dict:
    """Modified: trade_surprise_168 > threshold replaces VDO > 0."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    ts = feat["trade_surprise_168"].values
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
        if np.isnan(ratr[i]) or np.isnan(ts[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash
            entry_ok = (
                ema_f[i] > ema_s[i]
                and ts[i] > threshold
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

    return _compute_metrics(equity, trades, warmup_bar, f"tsurp_th={threshold}")


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
    print("EXP 10: Replace VDO with Trade Surprise")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # ── Feature diagnostics ──────────────────────────────────────────
    ts = feat["trade_surprise_168"].values
    valid_count = np.isfinite(ts).sum()
    print(f"trade_surprise_168: {valid_count}/{len(ts)} valid bars")
    valid_vals = ts[np.isfinite(ts)]
    if len(valid_vals) > 0:
        print(f"  Range: [{valid_vals.min():.4f}, {valid_vals.max():.4f}]")
        print(f"  Mean: {valid_vals.mean():.4f}, Std: {valid_vals.std():.4f}")
        for pct in [10, 25, 50, 75, 90]:
            print(f"  P{pct}: {np.percentile(valid_vals, pct):.4f}")
        for th in THRESHOLDS:
            pct_above = np.mean(valid_vals > th) * 100
            print(f"  Bars with ts > {th:+.2f} (entry allowed): {pct_above:.1f}%")

    # ── Overlap analysis: VDO > 0 vs trade_surprise > threshold ──────
    vdo_arr = feat["vdo"].values
    both_valid = np.isfinite(ts) & np.isfinite(vdo_arr)
    if both_valid.sum() > 0:
        vdo_pos = vdo_arr > 0
        print(f"\nOverlap analysis (on {both_valid.sum()} bars with both valid):")
        for th in THRESHOLDS:
            ts_pos = ts > th
            agree = (vdo_pos & ts_pos) | (~vdo_pos & ~ts_pos)
            agree_pct = agree[both_valid].mean() * 100
            both_on = (vdo_pos & ts_pos)[both_valid].mean() * 100
            vdo_only = (vdo_pos & ~ts_pos)[both_valid].mean() * 100
            ts_only = (~vdo_pos & ts_pos)[both_valid].mean() * 100
            print(f"  th={th:+.2f}: agree={agree_pct:.1f}%, both_on={both_on:.1f}%, "
                  f"vdo_only={vdo_only:.1f}%, ts_only={ts_only:.1f}%")

    first_valid = 0
    for i in range(len(ts)):
        if np.isfinite(ts[i]):
            first_valid = i
            break

    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"\nWarmup bar: {warmup_bar} (trade_surprise_168 first valid at {first_valid})")

    # ── Run baseline ──────────────────────────────────────────────────
    print("\nRunning baseline (original E5-ema21D1 with VDO > 0)...")
    base_r = run_baseline(feat, warmup_bar)
    print(f"  Sharpe={base_r['sharpe']}, CAGR={base_r['cagr_pct']}%, "
          f"MDD={base_r['mdd_pct']}%, trades={base_r['trades']}, "
          f"exposure={base_r['exposure_pct']}%")

    results = [base_r]

    # ── Run trade surprise variants ───────────────────────────────────
    for th in THRESHOLDS:
        label = f"tsurp_th={th}"
        print(f"\nRunning {label}...")
        r = run_trade_surprise(feat, th, warmup_bar)
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

    out_path = RESULTS_DIR / "exp10_results.csv"
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
        print("Trade surprise captures more useful information than VDO for entry filtering.")
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
            print("Trade surprise captures DIFFERENT information than VDO — "
                  "consider combining.")
        else:
            print("FAIL: No trade surprise threshold improves Sharpe over VDO baseline.")
            print("VDO (taker imbalance) is a better entry filter than trade surprise "
                  "(participation anomaly).")


if __name__ == "__main__":
    main()
