#!/usr/bin/env python3
"""Exp 37: Adaptive EMA Slow Period.

E5-ema21D1 with slow_period adapted by realized volatility percentile.
Low vol → shorter EMA (more responsive to trend initiation).
High vol → longer EMA (more patient, fewer false crossovers).

Time-varying EMA: alpha changes per bar based on rv_pctl.
  slow_period[i] = slow_min + rv_pctl[i] * (slow_max - slow_min)
  fast_period[i] = max(5, slow_period[i] // 4)

Sweep:
  slow_min: [60, 84]
  slow_max: [120, 144, 168]
  rv_lookback: 365 (fixed)
  → 6 configs + baseline (fixed slow=120)

Usage:
    python -m research.x39.experiments.exp37_adaptive_ema_period
    # or from x39/:
    python experiments/exp37_adaptive_ema_period.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import load_data, robust_atr, vdo, ema  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
FIXED_SLOW = 120
TRAIL_MULT = 3.0
VDO_THRESHOLD = 0.0
D1_EMA_PERIOD = 21
COST_BPS = 50
INITIAL_CASH = 10_000.0

# ── Experiment parameters ─────────────────────────────────────────────────
RV_WINDOW = 84          # realized vol window (H4 bars)
RV_LOOKBACK = 365       # percentile lookback (H4 bars, ~60 days)

SLOW_MINS = [60, 84]
SLOW_MAXS = [120, 144, 168]


# ── Indicator helpers ─────────────────────────────────────────────────────

def compute_rv_pctl(log_ret: np.ndarray, rv_window: int, lookback: int) -> np.ndarray:
    """Rolling percentile rank of realized_vol over trailing window."""
    rv = pd.Series(log_ret).rolling(rv_window, min_periods=rv_window).std().values * np.sqrt(rv_window)
    n = len(rv)
    pctl = np.full(n, np.nan)
    for i in range(rv_window + lookback, n):
        window = rv[i - lookback:i]
        valid = window[np.isfinite(window)]
        if len(valid) > 0 and np.isfinite(rv[i]):
            pctl[i] = np.mean(valid < rv[i])
    return pctl


def adaptive_ema(close: np.ndarray, rv_pctl: np.ndarray,
                 slow_min: float, slow_max: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Time-varying EMA with period adapted by rv_pctl.

    Returns (ema_slow, ema_fast, effective_slow_period).
    """
    n = len(close)
    ema_s = np.full(n, np.nan)
    ema_f = np.full(n, np.nan)
    eff_slow = np.full(n, np.nan)

    # Initialize with first valid close
    ema_s[0] = close[0]
    ema_f[0] = close[0]

    for i in range(1, n):
        if np.isfinite(rv_pctl[i]):
            slow_p = slow_min + rv_pctl[i] * (slow_max - slow_min)
        else:
            # Fallback: use midpoint before percentile is available
            slow_p = (slow_min + slow_max) / 2.0

        eff_slow[i] = slow_p
        alpha_s = 2.0 / (slow_p + 1)
        ema_s[i] = alpha_s * close[i] + (1 - alpha_s) * ema_s[i - 1]

        fast_p = max(5.0, slow_p / 4.0)
        alpha_f = 2.0 / (fast_p + 1)
        ema_f[i] = alpha_f * close[i] + (1 - alpha_f) * ema_f[i - 1]

    return ema_s, ema_f, eff_slow


def compute_d1_regime(h4_ct: np.ndarray, d1_close: np.ndarray,
                      d1_ct: np.ndarray, period: int) -> np.ndarray:
    """D1 EMA regime mapped to H4 bar grid."""
    n_h4 = len(h4_ct)
    d1_ema_arr = ema(d1_close, period)
    d1_regime = d1_close > d1_ema_arr

    regime_ok = np.zeros(n_h4, dtype=bool)
    d1_idx = 0
    n_d1 = len(d1_close)
    for i in range(n_h4):
        while d1_idx + 1 < n_d1 and d1_ct[d1_idx + 1] < h4_ct[i]:
            d1_idx += 1
        if d1_ct[d1_idx] < h4_ct[i]:
            regime_ok[i] = d1_regime[d1_idx]
    return regime_ok


def run_backtest(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    taker_buy: np.ndarray,
    h4_ct: np.ndarray,
    d1_close: np.ndarray,
    d1_ct: np.ndarray,
    rv_pctl: np.ndarray,
    slow_min: float | None,
    slow_max: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional adaptive EMA. Returns summary dict."""
    n = len(close)
    is_adaptive = slow_min is not None and slow_max is not None

    # Compute indicators
    if is_adaptive:
        ema_s, ema_f, eff_slow = adaptive_ema(close, rv_pctl, slow_min, slow_max)
    else:
        ema_s = ema(close, FIXED_SLOW)
        ema_f = ema(close, max(5, FIXED_SLOW // 4))
        eff_slow = np.full(n, float(FIXED_SLOW))

    ratr = robust_atr(high, low, close)
    vdo_arr = vdo(volume, taker_buy)
    d1_ok = compute_d1_regime(h4_ct, d1_close, d1_ct, D1_EMA_PERIOD)

    # Sim
    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]) or np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
            equity[i] = cash
            continue

        trend_up = ema_f[i] > ema_s[i]
        trend_down = ema_f[i] < ema_s[i]

        if not in_pos:
            equity[i] = cash
            if trend_up and vdo_arr[i] > VDO_THRESHOLD and d1_ok[i]:
                in_pos = True
                entry_bar = i
                entry_price = close[i]
                peak = close[i]
                half_cost = (COST_BPS / 2) / 10_000
                position_size = cash * (1 - half_cost) / close[i]
                cash = 0.0
        else:
            equity[i] = position_size * close[i]
            peak = max(peak, close[i])

            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None
            if close[i] < trail_stop:
                exit_reason = "trail"
            elif trend_down:
                exit_reason = "trend"

            if exit_reason:
                half_cost = (COST_BPS / 2) / 10_000
                cash = position_size * close[i] * (1 - half_cost)
                cost = COST_BPS / 10_000
                gross_ret = (close[i] - entry_price) / entry_price
                net_ret = gross_ret - cost

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "entry_price": entry_price,
                    "exit_price": close[i],
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
            "config": "baseline" if not is_adaptive else f"min={slow_min}/max={slow_max}",
            "slow_min": slow_min, "slow_max": slow_max,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "exposure_pct": np.nan,
            "mean_slow_period": np.nan, "std_slow_period": np.nan,
            "mean_slow_bull": np.nan, "mean_slow_bear": np.nan,
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

    # Effective slow period stats (post-warmup, where rv_pctl is valid)
    eff_valid = eff_slow[warmup_bar:]
    eff_valid = eff_valid[np.isfinite(eff_valid)]
    mean_slow = float(np.mean(eff_valid)) if len(eff_valid) > 0 else np.nan
    std_slow = float(np.std(eff_valid)) if len(eff_valid) > 0 else np.nan

    # Bull/bear regime split
    bull_mask = d1_ok[warmup_bar:warmup_bar + len(eff_slow[warmup_bar:])]
    eff_post = eff_slow[warmup_bar:]
    valid_mask = np.isfinite(eff_post)
    bull_periods = eff_post[valid_mask & bull_mask[:len(eff_post)]] if len(bull_mask) >= len(eff_post) else np.array([])
    bear_periods = eff_post[valid_mask & ~bull_mask[:len(eff_post)]] if len(bull_mask) >= len(eff_post) else np.array([])
    mean_slow_bull = float(np.mean(bull_periods)) if len(bull_periods) > 0 else np.nan
    mean_slow_bear = float(np.mean(bear_periods)) if len(bear_periods) > 0 else np.nan

    return {
        "config": "baseline" if not is_adaptive else f"min={int(slow_min)}/max={int(slow_max)}",
        "slow_min": slow_min if is_adaptive else float(FIXED_SLOW),
        "slow_max": slow_max if is_adaptive else float(FIXED_SLOW),
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "exposure_pct": round(exposure * 100, 1),
        "mean_slow_period": round(mean_slow, 1),
        "std_slow_period": round(std_slow, 1),
        "mean_slow_bull": round(mean_slow_bull, 1),
        "mean_slow_bear": round(mean_slow_bear, 1),
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    configs = [(smin, smax) for smin in SLOW_MINS for smax in SLOW_MAXS]

    print("=" * 80)
    print("EXP 37: Adaptive EMA Slow Period")
    print(f"  rv_window:       {RV_WINDOW} H4 bars")
    print(f"  rv_lookback:     {RV_LOOKBACK} H4 bars")
    print(f"  slow_min sweep:  {SLOW_MINS}")
    print(f"  slow_max sweep:  {SLOW_MAXS}")
    print(f"  configs:         {len(configs)}")
    print(f"  baseline:        fixed slow={FIXED_SLOW}")
    print(f"  cost:            {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()

    close = h4["close"].values.astype(np.float64)
    high = h4["high"].values.astype(np.float64)
    low = h4["low"].values.astype(np.float64)
    volume = h4["volume"].values.astype(np.float64)
    taker_buy = h4["taker_buy_base_vol"].values.astype(np.float64)
    h4_ct = h4["close_time"].values
    d1_close = d1["close"].values.astype(np.float64)
    d1_ct = d1["close_time"].values

    # Compute realized vol percentile
    log_ret = np.log(close / np.concatenate([[close[0]], close[:-1]]))
    print(f"\nComputing rv_pctl (rv_window={RV_WINDOW}, lookback={RV_LOOKBACK})...")
    rv_pctl = compute_rv_pctl(log_ret, RV_WINDOW, RV_LOOKBACK)

    first_valid = 0
    for i in range(len(rv_pctl)):
        if np.isfinite(rv_pctl[i]):
            first_valid = i
            break

    # Warmup: 365 days = 365 * 6 = 2190 H4 bars
    warmup_days = 365
    bars_per_day = 6  # H4 = 6 bars/day
    warmup_bar = max(warmup_days * bars_per_day, first_valid)
    print(f"First valid rv_pctl at bar {first_valid}")
    print(f"Warmup bar: {warmup_bar} ({warmup_days} days)")

    # rv_pctl stats post-warmup
    rv_valid = rv_pctl[warmup_bar:]
    rv_valid = rv_valid[np.isfinite(rv_valid)]
    print(f"rv_pctl coverage: {len(rv_valid)} bars post-warmup")
    print(f"rv_pctl range: [{rv_valid.min():.3f}, {rv_valid.max():.3f}], "
          f"mean={rv_valid.mean():.3f}, median={np.median(rv_valid):.3f}")

    # Run baseline
    results = []
    print("\nRunning baseline (fixed slow=120)...")
    r = run_backtest(close, high, low, volume, taker_buy, h4_ct, d1_close, d1_ct,
                     rv_pctl, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, exposure={r['exposure_pct']}%")

    # Sweep configs
    for slow_min, slow_max in configs:
        label = f"min={int(slow_min)}, max={int(slow_max)}"
        print(f"\nRunning {label}...")
        r = run_backtest(close, high, low, volume, taker_buy, h4_ct, d1_close, d1_ct,
                         rv_pctl, float(slow_min), float(slow_max), warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, mean_slow={r['mean_slow_period']}")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # positive = worse MDD

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp37_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Adaptation behavior analysis ──────────────────────────────────
    print("\n" + "=" * 80)
    print("ADAPTATION BEHAVIOR")
    print("=" * 80)

    adaptive_rows = df[df["config"] != "baseline"]
    if not adaptive_rows.empty:
        print("\nEffective slow_period distribution:")
        for _, row in adaptive_rows.iterrows():
            range_str = f"[{row['slow_min']:.0f}, {row['slow_max']:.0f}]"
            print(f"  {row['config']:18s}  mean={row['mean_slow_period']:5.1f}  "
                  f"std={row['std_slow_period']:4.1f}  "
                  f"bull={row['mean_slow_bull']:5.1f}  bear={row['mean_slow_bear']:5.1f}")

        # Does bull/bear split matter?
        print("\nBull vs bear mean slow_period (lower in bull = more responsive):")
        for _, row in adaptive_rows.iterrows():
            diff = row["mean_slow_bull"] - row["mean_slow_bear"]
            direction = "bull shorter (good)" if diff < 0 else "bull longer (unexpected)"
            print(f"  {row['config']:18s}  diff={diff:+.1f}  ({direction})")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    adaptive = df[df["config"] != "baseline"]

    improvements = adaptive[(adaptive["d_sharpe"] > 0) & (adaptive["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
    else:
        sharpe_up = adaptive[adaptive["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No adaptive EMA config improves Sharpe over baseline.")
            print("Fixed slow_period=120 is already within the optimal plateau.")

    # Key diagnostic: how much does the adaptation spread?
    if not adaptive_rows.empty:
        max_std = adaptive_rows["std_slow_period"].max()
        max_range = adaptive_rows["slow_max"].max() - adaptive_rows["slow_min"].min()
        print(f"\nMax std of effective slow_period: {max_std:.1f} "
              f"(range [{adaptive_rows['slow_min'].min():.0f}, {adaptive_rows['slow_max'].max():.0f}])")
        if max_std < 10:
            print("NOTE: Low std suggests adaptation has minimal effect — rv_pctl is "
                  "relatively uniform, so the period barely moves from the mean.")


if __name__ == "__main__":
    main()
