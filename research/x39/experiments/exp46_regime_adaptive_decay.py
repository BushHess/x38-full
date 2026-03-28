#!/usr/bin/env python3
"""Exp 46: Regime-Adaptive Maturity Decay.

Combines exp38 (trend maturity trail decay) with exp36 (volatility regime split).
Instead of fixed decay schedule, the decay rate adapts to volatility regime:
- High-vol: shorter decay window (trends reverse faster → protect sooner)
- Low-vol: longer decay window (trends persist → give more room)

Entry logic UNCHANGED. Only exit trail decay schedule changes per regime.
Vol regime CAN change mid-trade — decay schedule switches accordingly.

Sweep:
  trail_min  = 1.5 (FIXED at exp38 optimum)
  vol_split  = 0.50 (FIXED median)
  low-vol  schedule: [(60,240), (90,240), (90,300)]
  high-vol schedule: [(30,120), (30,180), (60,120)]
  → 9 adaptive + 1 fixed-decay + 1 no-decay = 11 configs

Usage:
    python -m research.x39.experiments.exp46_regime_adaptive_decay
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
TRAIL_MIN = 1.5          # Fixed at exp38 optimum
VOL_SPLIT = 0.50         # Median split
RATR_PCTL_LOOKBACK = 365  # H4 bars for rolling percentile

# Fixed-decay baseline (exp38 best)
FIXED_DECAY_START = 60
FIXED_DECAY_END = 180

# Regime-adaptive schedules
LOW_VOL_SCHEDULES = [(60, 240), (90, 240), (90, 300)]   # slower decay
HIGH_VOL_SCHEDULES = [(30, 120), (30, 180), (60, 120)]  # faster decay


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
    return age


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
    ratr_pctl: np.ndarray,
    warmup_bar: int,
    *,
    mode: str = "no_decay",
    start_lv: int = 0,
    end_lv: int = 0,
    start_hv: int = 0,
    end_hv: int = 0,
) -> dict:
    """Replay E5-ema21D1 with optional regime-adaptive trail decay.

    mode: "no_decay" | "fixed_decay" | "adaptive"
    For fixed_decay: uses (FIXED_DECAY_START, FIXED_DECAY_END) for both regimes.
    For adaptive: uses (start_lv, end_lv) for low-vol and (start_hv, end_hv) for high-vol.
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

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    # Per-regime tracking
    trail_at_exit: list[float] = []
    age_at_exit: list[int] = []
    regime_at_exit: list[str] = []

    # Per-regime trade stats
    trades_low_vol: list[dict] = []
    trades_high_vol: list[dict] = []

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

            # Determine current volatility regime
            is_high_vol = (
                np.isfinite(ratr_pctl[i])
                and ratr_pctl[i] >= VOL_SPLIT
            )

            # Determine trail multiplier based on mode
            if mode == "no_decay":
                current_trail = BASELINE_TRAIL_MULT
            elif mode == "fixed_decay":
                current_trail = effective_trail(
                    trend_age[i], TRAIL_BASE, TRAIL_MIN,
                    FIXED_DECAY_START, FIXED_DECAY_END,
                )
            else:  # adaptive
                if is_high_vol:
                    current_trail = effective_trail(
                        trend_age[i], TRAIL_BASE, TRAIL_MIN,
                        start_hv, end_hv,
                    )
                else:
                    current_trail = effective_trail(
                        trend_age[i], TRAIL_BASE, TRAIL_MIN,
                        start_lv, end_lv,
                    )

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
                regime_label = "high" if is_high_vol else "low"
                regime_at_exit.append(regime_label)

                trade = {
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
                    "regime_at_exit": regime_label,
                }
                trades.append(trade)
                if is_high_vol:
                    trades_high_vol.append(trade)
                else:
                    trades_low_vol.append(trade)

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result(mode, start_lv, end_lv, start_hv, end_hv)

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

    # Per-regime Sharpe (using trade net returns as proxy)
    def _regime_sharpe(trade_list: list[dict]) -> float:
        if len(trade_list) < 2:
            return np.nan
        nr = [t["net_ret"] for t in trade_list]
        m, s = np.mean(nr), np.std(nr, ddof=1)
        if s <= 0:
            return np.nan
        avg_bars = np.mean([t["bars_held"] for t in trade_list])
        trades_per_year = bars_per_year / avg_bars if avg_bars > 0 else 0
        return m / s * np.sqrt(trades_per_year)

    sharpe_lv = _regime_sharpe(trades_low_vol)
    sharpe_hv = _regime_sharpe(trades_high_vol)

    config_label = _config_label(mode, start_lv, end_lv, start_hv, end_hv)

    return {
        "config": config_label,
        "mode": mode,
        "start_lv": start_lv,
        "end_lv": end_lv,
        "start_hv": start_hv,
        "end_hv": end_hv,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "exposure_pct": round(exposure * 100, 1),
        "trades_lv": len(trades_low_vol),
        "trades_hv": len(trades_high_vol),
        "sharpe_lv": round(sharpe_lv, 4) if np.isfinite(sharpe_lv) else np.nan,
        "sharpe_hv": round(sharpe_hv, 4) if np.isfinite(sharpe_hv) else np.nan,
        "avg_age_exit": round(np.mean(age_at_exit), 1),
        "avg_trail_exit": round(np.mean(trail_at_exit), 3),
        "avg_bars_lv": (
            round(np.mean([t["bars_held"] for t in trades_low_vol]), 1)
            if trades_low_vol else np.nan
        ),
        "avg_bars_hv": (
            round(np.mean([t["bars_held"] for t in trades_high_vol]), 1)
            if trades_high_vol else np.nan
        ),
    }


def _config_label(
    mode: str,
    start_lv: int, end_lv: int,
    start_hv: int, end_hv: int,
) -> str:
    if mode == "no_decay":
        return "no_decay"
    if mode == "fixed_decay":
        return f"fixed({FIXED_DECAY_START},{FIXED_DECAY_END})"
    return f"LV({start_lv},{end_lv})/HV({start_hv},{end_hv})"


def _empty_result(
    mode: str,
    start_lv: int, end_lv: int,
    start_hv: int, end_hv: int,
) -> dict:
    config_label = _config_label(mode, start_lv, end_lv, start_hv, end_hv)
    return {
        "config": config_label, "mode": mode,
        "start_lv": start_lv, "end_lv": end_lv,
        "start_hv": start_hv, "end_hv": end_hv,
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "trades_lv": 0, "trades_hv": 0,
        "sharpe_lv": np.nan, "sharpe_hv": np.nan,
        "avg_age_exit": np.nan, "avg_trail_exit": np.nan,
        "avg_bars_lv": np.nan, "avg_bars_hv": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build adaptive configs: 3 LV × 3 HV = 9
    adaptive_configs = [
        (slv, elv, shv, ehv)
        for slv, elv in LOW_VOL_SCHEDULES
        for shv, ehv in HIGH_VOL_SCHEDULES
    ]

    print("=" * 80)
    print("EXP 46: Regime-Adaptive Maturity Decay")
    print(f"  trail_base:       {TRAIL_BASE}")
    print(f"  trail_min:        {TRAIL_MIN} (fixed at exp38 optimum)")
    print(f"  vol_split:        {VOL_SPLIT} (median)")
    print(f"  fixed baseline:   start={FIXED_DECAY_START}, end={FIXED_DECAY_END}")
    print(f"  low-vol sched:    {LOW_VOL_SCHEDULES}")
    print(f"  high-vol sched:   {HIGH_VOL_SCHEDULES}")
    print(f"  adaptive configs: {len(adaptive_configs)}")
    print(f"  total configs:    {len(adaptive_configs) + 2} (+ no_decay + fixed_decay)")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr_pct = feat["ratr_pct"].values

    print("\nComputing trend_age...")
    trend_age = compute_trend_age(ema_f, ema_s)

    print(f"Computing ratr_pctl (lookback={RATR_PCTL_LOOKBACK})...")
    ratr_pctl = compute_ratr_pctl(ratr_pct, RATR_PCTL_LOOKBACK)

    # Warmup: 365 days
    bars_per_day = 24 / 4
    warmup_bar = int(WARMUP_DAYS * bars_per_day)
    print(f"Warmup bar: {warmup_bar} ({WARMUP_DAYS} days)")

    # Regime stats in eval window
    eval_pctl = ratr_pctl[warmup_bar:]
    valid_mask = np.isfinite(eval_pctl)
    n_low = np.sum(eval_pctl[valid_mask] < VOL_SPLIT)
    n_high = np.sum(eval_pctl[valid_mask] >= VOL_SPLIT)
    print(f"Regime split: low_vol={n_low} bars ({n_low / valid_mask.sum() * 100:.1f}%), "
          f"high_vol={n_high} bars ({n_high / valid_mask.sum() * 100:.1f}%)")

    # Trend age stats
    eval_age = trend_age[warmup_bar:]
    in_trend = eval_age > 0
    print(f"Trend age stats (eval): mean={eval_age[in_trend].mean():.1f}, "
          f"median={np.median(eval_age[in_trend]):.0f}, "
          f"p90={np.percentile(eval_age[in_trend], 90):.0f}, "
          f"max={eval_age.max()}")

    results = []

    # ── 1. No-decay baseline ─────────────────────────────────────────
    print("\n[1/11] Running no-decay baseline (fixed trail=3.0)...")
    r = run_backtest(feat, trend_age, ratr_pctl, warmup_bar, mode="no_decay")
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")

    # ── 2. Fixed-decay baseline (exp38 best) ─────────────────────────
    print(f"\n[2/11] Running fixed-decay baseline "
          f"(start={FIXED_DECAY_START}, end={FIXED_DECAY_END})...")
    r = run_backtest(feat, trend_age, ratr_pctl, warmup_bar, mode="fixed_decay")
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")

    # ── 3. Adaptive configs ──────────────────────────────────────────
    for idx, (slv, elv, shv, ehv) in enumerate(adaptive_configs, start=3):
        label = f"LV({slv},{elv})/HV({shv},{ehv})"
        print(f"\n[{idx}/11] Running {label}...")
        r = run_backtest(
            feat, trend_age, ratr_pctl, warmup_bar,
            mode="adaptive", start_lv=slv, end_lv=elv, start_hv=shv, end_hv=ehv,
        )
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, lv={r['trades_lv']}, hv={r['trades_hv']}")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    no_decay = df.iloc[0]
    fixed_decay = df.iloc[1]
    df["d_sharpe_nd"] = df["sharpe"] - no_decay["sharpe"]
    df["d_cagr_nd"] = df["cagr_pct"] - no_decay["cagr_pct"]
    df["d_mdd_nd"] = df["mdd_pct"] - no_decay["mdd_pct"]
    df["d_sharpe_fd"] = df["sharpe"] - fixed_decay["sharpe"]
    df["d_cagr_fd"] = df["cagr_pct"] - fixed_decay["cagr_pct"]
    df["d_mdd_fd"] = df["mdd_pct"] - fixed_decay["mdd_pct"]

    print("\n" + "=" * 80)
    print("RESULTS (delta vs no-decay = _nd, delta vs fixed-decay = _fd)")
    print("=" * 80)
    display_cols = [
        "config", "sharpe", "cagr_pct", "mdd_pct", "trades",
        "d_sharpe_nd", "d_mdd_nd", "d_sharpe_fd", "d_mdd_fd",
    ]
    print(df[display_cols].to_string(index=False))

    out_path = RESULTS_DIR / "exp46_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Analysis 1: Best adaptive vs fixed ────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 1: Does any adaptive config beat fixed (60/180)?")
    print("=" * 80)

    adaptive = df[df["mode"] == "adaptive"]

    beats_fixed_sharpe = adaptive[adaptive["d_sharpe_fd"] > 0]
    beats_fixed_both = adaptive[(adaptive["d_sharpe_fd"] > 0) & (adaptive["d_mdd_fd"] < 0)]

    print(f"Configs that beat fixed on Sharpe:         {len(beats_fixed_sharpe)}/9")
    print(f"Configs that beat fixed on Sharpe AND MDD: {len(beats_fixed_both)}/9")

    if not beats_fixed_sharpe.empty:
        best = beats_fixed_sharpe.loc[beats_fixed_sharpe["d_sharpe_fd"].idxmax()]
        print(f"\nBest vs fixed: {best['config']}")
        print(f"  d_sharpe = {best['d_sharpe_fd']:+.4f}, d_mdd = {best['d_mdd_fd']:+.2f} pp")
    else:
        print("\nNo adaptive config beats fixed on Sharpe.")

    # ── Analysis 2: Per-regime breakdown ──────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 2: Per-regime Sharpe and trade count")
    print("=" * 80)

    print(f"{'Config':30s} {'Sh_LV':>8s} {'Sh_HV':>8s} {'Tr_LV':>6s} {'Tr_HV':>6s} "
          f"{'Bars_LV':>8s} {'Bars_HV':>8s}")
    print("-" * 80)
    for _, row in df.iterrows():
        sh_lv = f"{row['sharpe_lv']:.4f}" if np.isfinite(row['sharpe_lv']) else "NaN"
        sh_hv = f"{row['sharpe_hv']:.4f}" if np.isfinite(row['sharpe_hv']) else "NaN"
        bars_lv = f"{row['avg_bars_lv']:.1f}" if np.isfinite(row['avg_bars_lv']) else "NaN"
        bars_hv = f"{row['avg_bars_hv']:.1f}" if np.isfinite(row['avg_bars_hv']) else "NaN"
        print(f"{row['config']:30s} {sh_lv:>8s} {sh_hv:>8s} "
              f"{int(row['trades_lv']):>6d} {int(row['trades_hv']):>6d} "
              f"{bars_lv:>8s} {bars_hv:>8s}")

    # ── Analysis 3: High-vol loss prevention ──────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 3: Does faster high-vol decay prevent losses?")
    print("=" * 80)

    # Compare HV Sharpe across configs
    print(f"Fixed decay HV Sharpe: {fixed_decay['sharpe_hv']}")
    for _, row in adaptive.iterrows():
        d = row["sharpe_hv"] - fixed_decay["sharpe_hv"] if (
            np.isfinite(row["sharpe_hv"]) and np.isfinite(fixed_decay["sharpe_hv"])
        ) else np.nan
        d_str = f"{d:+.4f}" if np.isfinite(d) else "NaN"
        print(f"  {row['config']:30s} HV Sharpe={row['sharpe_hv']}, delta={d_str}")

    # ── Analysis 4: Low-vol trend capture ─────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 4: Does slower low-vol decay capture more trend alpha?")
    print("=" * 80)

    print(f"Fixed decay LV Sharpe: {fixed_decay['sharpe_lv']}")
    for _, row in adaptive.iterrows():
        d = row["sharpe_lv"] - fixed_decay["sharpe_lv"] if (
            np.isfinite(row["sharpe_lv"]) and np.isfinite(fixed_decay["sharpe_lv"])
        ) else np.nan
        d_str = f"{d:+.4f}" if np.isfinite(d) else "NaN"
        print(f"  {row['config']:30s} LV Sharpe={row['sharpe_lv']}, delta={d_str}")

    # ── Analysis 5: Effective trail at exit ───────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 5: Avg effective trail & trend age at exit")
    print("=" * 80)

    print(f"{'Config':30s} {'AvgTrail':>10s} {'AvgAge':>8s} {'Exposure':>10s}")
    print("-" * 60)
    for _, row in df.iterrows():
        print(f"{row['config']:30s} {row['avg_trail_exit']:>10.3f} "
              f"{row['avg_age_exit']:>8.1f} {row['exposure_pct']:>9.1f}%")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Check if any adaptive beats fixed on BOTH Sharpe and MDD
    if not beats_fixed_both.empty:
        best = beats_fixed_both.loc[beats_fixed_both["d_sharpe_fd"].idxmax()]
        print(f"PASS: {best['config']} beats fixed decay on both Sharpe "
              f"({best['d_sharpe_fd']:+.4f}) and MDD ({best['d_mdd_fd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        print(f"  vs no-decay:    d_sharpe={best['d_sharpe_nd']:+.4f}, "
              f"d_mdd={best['d_mdd_nd']:+.2f} pp")
    elif not beats_fixed_sharpe.empty:
        best = beats_fixed_sharpe.loc[beats_fixed_sharpe["d_sharpe_fd"].idxmax()]
        print(f"MIXED: {best['config']} beats fixed on Sharpe "
              f"({best['d_sharpe_fd']:+.4f}) but MDD worsens ({best['d_mdd_fd']:+.2f} pp)")
    else:
        # Check if fixed decay itself improves on no-decay
        fd_d_sharpe = fixed_decay["sharpe"] - no_decay["sharpe"]
        fd_d_mdd = fixed_decay["mdd_pct"] - no_decay["mdd_pct"]
        print(f"FAIL: No adaptive config beats fixed decay (60/180).")
        print(f"  Fixed decay vs no-decay: d_sharpe={fd_d_sharpe:+.4f}, "
              f"d_mdd={fd_d_mdd:+.2f} pp")
        print("  Fixed decay already captures the optimal average across regimes.")

    # Summary statistics
    print(f"\nAdaptive range: Sharpe [{adaptive['sharpe'].min():.4f}, "
          f"{adaptive['sharpe'].max():.4f}], "
          f"MDD [{adaptive['mdd_pct'].min():.2f}%, {adaptive['mdd_pct'].max():.2f}%]")
    print(f"Fixed decay:    Sharpe {fixed_decay['sharpe']:.4f}, "
          f"MDD {fixed_decay['mdd_pct']:.2f}%")
    print(f"No decay:       Sharpe {no_decay['sharpe']:.4f}, "
          f"MDD {no_decay['mdd_pct']:.2f}%")


if __name__ == "__main__":
    main()
