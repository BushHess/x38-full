#!/usr/bin/env python3
"""Exp 04: Trade Surprise Entry Gate.

Adds trade_surprise_168 > threshold to E5-ema21D1 entry.
Positive surprise = more trades than volume predicts = unusual participation.
Sweeps threshold in [-0.05, 0.0, 0.05, 0.10, 0.15] + baseline (no gate).

Usage:
    python -m research.x39.experiments.exp04_trade_surprise_gate
    # or from x39/:
    python experiments/exp04_trade_surprise_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

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
TS_LOOKBACK = 168  # rolling mean window for de-drifting
FIT_BARS = 2000    # bars used for linear regression fit


def compute_trade_surprise(feat: pd.DataFrame) -> np.ndarray:
    """Compute trade_surprise_168: residual of num_trades vs volume, de-drifted.

    Fits log1p(num_trades) = intercept + slope * log1p(volume) on first 2000 bars,
    then de-drifts with rolling 168-bar mean.
    """
    # Already computed in explore.py — extract directly
    ts = feat["trade_surprise_168"].values.copy()
    return ts


def run_backtest(
    feat: pd.DataFrame,
    trade_surprise: np.ndarray,
    ts_threshold: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional trade surprise gate. Returns summary dict."""
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

    # Equity tracking
    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
            continue

        if not in_pos:
            equity[i] = cash

            # Entry conditions
            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )
            if ts_threshold is not None:
                entry_ok = entry_ok and np.isfinite(trade_surprise[i]) and trade_surprise[i] > ts_threshold

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
            "threshold": ts_threshold if ts_threshold is not None else "baseline",
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_win": np.nan,
            "avg_loss": np.nan, "exposure_pct": np.nan,
        }

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4  # ~2191.5

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
        "threshold": ts_threshold if ts_threshold is not None else "baseline",
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
    print("EXP 04: Trade Surprise Entry Gate (trade_surprise_168)")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Extract trade surprise (already computed by explore.py)
    print("Extracting trade_surprise_168...")
    trade_surprise = compute_trade_surprise(feat)
    valid_count = np.isfinite(trade_surprise).sum()
    print(f"  Valid bars: {valid_count}/{len(trade_surprise)}")
    valid_ts = trade_surprise[np.isfinite(trade_surprise)]
    if len(valid_ts) > 0:
        print(f"  Range: [{valid_ts.min():.4f}, {valid_ts.max():.4f}]")
        print(f"  Mean: {valid_ts.mean():.4f}, Std: {valid_ts.std():.4f}")
        for t in THRESHOLDS:
            pct_above = np.mean(valid_ts > t) * 100
            print(f"  Bars with ts > {t:+.2f}: {pct_above:.1f}%")

    first_valid = 0
    for i in range(len(trade_surprise)):
        if np.isfinite(trade_surprise[i]):
            first_valid = i
            break
    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"Warmup bar: {warmup_bar} (first valid trade_surprise at {first_valid})")

    # Run baseline + 5 threshold configs
    configs = [None] + THRESHOLDS
    results = []

    for thresh in configs:
        label = "baseline" if thresh is None else f"thresh={thresh:+.2f}"
        print(f"\nRunning {label}...")
        r = run_backtest(feat, trade_surprise, thresh, warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, exposure={r['exposure_pct']}%")

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

    # Save
    out_path = RESULTS_DIR / "exp04_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n→ Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    gated = df.iloc[1:]
    improvements = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: threshold={best['threshold']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: threshold={best['threshold']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No threshold improves Sharpe over baseline.")
            print("Trade surprise gate does NOT help E5-ema21D1.")


if __name__ == "__main__":
    main()
