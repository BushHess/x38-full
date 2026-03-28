#!/usr/bin/env python3
"""Exp 11: Anti-Vol Dynamic Trail.

E5-ema21D1 with trail_mult adapted by D1 volatility rank.
Low vol (orderly) → tighter trail. High vol (chaotic) → wider trail.

Entry logic UNCHANGED. Only exit trail multiplier changes.

Sweep:
  low_vol_threshold = 0.40 (fixed)
  tight_mult in [2.0, 2.5]
  wide_mult  in [3.0, 3.5, 4.0]
  → 6 configs + baseline (fixed trail_mult=3.0)

Usage:
    python -m research.x39.experiments.exp11_antivol_trail
    # or from x39/:
    python experiments/exp11_antivol_trail.py
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

LOW_VOL_THRESHOLD = 0.40
TIGHT_MULTS = [2.0, 2.5]
WIDE_MULTS = [3.0, 3.5, 4.0]


def run_backtest(
    feat: pd.DataFrame,
    tight_mult: float | None,
    wide_mult: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional dynamic trail. Returns summary dict.

    If tight_mult/wide_mult are None, uses fixed BASELINE_TRAIL_MULT (baseline).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rank365 = feat["d1_rangevol84_rank365"].values
    n = len(c)

    is_dynamic = tight_mult is not None and wide_mult is not None

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

            # Dynamic trail multiplier
            if is_dynamic and np.isfinite(rank365[i]) and rank365[i] < LOW_VOL_THRESHOLD:
                current_trail = tight_mult
            elif is_dynamic:
                current_trail = wide_mult
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
            "config": "baseline" if not is_dynamic else f"t={tight_mult}/w={wide_mult}",
            "tight_mult": tight_mult, "wide_mult": wide_mult,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
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
        "config": "baseline" if not is_dynamic else f"t={tight_mult}/w={wide_mult}",
        "tight_mult": tight_mult if is_dynamic else BASELINE_TRAIL_MULT,
        "wide_mult": wide_mult if is_dynamic else BASELINE_TRAIL_MULT,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "avg_win": round(wins["net_ret"].mean() * 100, 2) if len(wins) > 0 else np.nan,
        "avg_loss": round(losses["net_ret"].mean() * 100, 2) if len(losses) > 0 else np.nan,
        "exposure_pct": round(exposure * 100, 1),
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 11: Anti-Vol Dynamic Trail")
    print(f"  low_vol_threshold = {LOW_VOL_THRESHOLD}")
    print(f"  tight_mult sweep: {TIGHT_MULTS}")
    print(f"  wide_mult sweep:  {WIDE_MULTS}")
    print(f"  baseline trail:   {BASELINE_TRAIL_MULT}")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Warmup: first bar where rank365 is valid + EMA warmup
    rank_col = feat["d1_rangevol84_rank365"].values
    first_valid = 0
    for i in range(len(rank_col)):
        if np.isfinite(rank_col[i]):
            first_valid = i
            break
    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"Warmup bar: {warmup_bar} (first valid rank365 at {first_valid})")

    # Run baseline
    results = []
    print("\nRunning baseline (fixed trail=3.0)...")
    r = run_backtest(feat, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, avg_held={r['avg_bars_held']}")

    # Sweep dynamic configs
    for tight in TIGHT_MULTS:
        for wide in WIDE_MULTS:
            label = f"tight={tight}, wide={wide}"
            print(f"\nRunning {label}...")
            r = run_backtest(feat, tight, wide, warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, avg_held={r['avg_bars_held']}")

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

    out_path = RESULTS_DIR / "exp11_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n→ Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    dynamic = df.iloc[1:]
    improvements = dynamic[(dynamic["d_sharpe"] > 0) & (dynamic["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
    else:
        sharpe_up = dynamic[dynamic["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No dynamic trail config improves Sharpe over baseline.")
            print("Anti-vol dynamic trail does NOT help E5-ema21D1.")

    # Extra: show exit reason breakdown per config
    print("\n" + "-" * 40)
    print("Note: tighter trail in low-vol → more trail exits, fewer trend exits.")
    print("      wider trail in high-vol → fewer trail exits, more trend exits.")


if __name__ == "__main__":
    main()
