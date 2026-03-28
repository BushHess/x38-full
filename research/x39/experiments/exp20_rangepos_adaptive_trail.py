#!/usr/bin/env python3
"""Exp 20: Rangepos-Adaptive Trail.

E5-ema21D1 with trail_mult modulated by rangepos_84 (continuous).
- rangepos_84 high (near range top) → price healthy → WIDEN trail
- rangepos_84 low (near range bottom) → price stressed → TIGHTEN trail

trail_mult = tight_mult + rangepos_84 * (wide_mult - tight_mult)

Mechanistically different from exp12 (binary exit) and exp11 (binary vol gate).
This is CONTINUOUS modulation of trail width bar-by-bar.

Sweep:
  tight_mult in [1.5, 2.0, 2.5]
  wide_mult  in [3.0, 3.5, 4.0]
  → 9 configs + baseline (fixed trail_mult=3.0)

Usage:
    python -m research.x39.experiments.exp20_rangepos_adaptive_trail
    # or from x39/:
    python experiments/exp20_rangepos_adaptive_trail.py
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

TIGHT_MULTS = [1.5, 2.0, 2.5]
WIDE_MULTS = [3.0, 3.5, 4.0]

CONFIG_LABELS = {
    (1.5, 3.0): "A", (1.5, 3.5): "B", (1.5, 4.0): "C",
    (2.0, 3.0): "D", (2.0, 3.5): "E", (2.0, 4.0): "F",
    (2.5, 3.0): "G", (2.5, 3.5): "H", (2.5, 4.0): "I",
}


def run_backtest(
    feat: pd.DataFrame,
    tight_mult: float | None,
    wide_mult: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional rangepos-adaptive trail.

    If tight_mult/wide_mult are None, uses fixed BASELINE_TRAIL_MULT (baseline).
    Returns summary dict with metrics + trail_mult distribution stats.
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    n = len(c)

    is_dynamic = tight_mult is not None and wide_mult is not None

    trades: list[dict] = []
    trail_mults_during_trades: list[float] = []  # all bar-by-bar trail_mult values
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

            # Dynamic trail multiplier via rangepos_84
            if is_dynamic and np.isfinite(rangepos[i]):
                rp = np.clip(rangepos[i], 0.0, 1.0)
                current_trail = tight_mult + rp * (wide_mult - tight_mult)
            elif is_dynamic:
                # NaN rangepos during warmup → fallback to baseline
                current_trail = BASELINE_TRAIL_MULT
            else:
                current_trail = BASELINE_TRAIL_MULT

            trail_mults_during_trades.append(current_trail)

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
    if is_dynamic:
        label = CONFIG_LABELS.get((tight_mult, wide_mult), f"t={tight_mult}/w={wide_mult}")
    else:
        label = "baseline"

    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": label,
            "tight_mult": tight_mult, "wide_mult": wide_mult,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
            "trail_median": np.nan, "trail_p10": np.nan, "trail_p90": np.nan,
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

    # Trail mult distribution during trades
    tm_arr = np.array(trail_mults_during_trades)
    trail_median = np.median(tm_arr) if len(tm_arr) > 0 else np.nan
    trail_p10 = np.percentile(tm_arr, 10) if len(tm_arr) > 0 else np.nan
    trail_p90 = np.percentile(tm_arr, 90) if len(tm_arr) > 0 else np.nan

    return {
        "config": label,
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
        "trail_median": round(trail_median, 3),
        "trail_p10": round(trail_p10, 3),
        "trail_p90": round(trail_p90, 3),
    }


def compare_trade_exits(
    feat: pd.DataFrame,
    tight_mult: float,
    wide_mult: float,
    warmup_bar: int,
    baseline_trades: list[dict],
) -> dict:
    """Compare exit timing of adaptive config vs baseline trade-by-trade.

    Match trades by entry_bar. Count how many exit EARLIER, LATER, or SAME.
    """
    # Run the adaptive config and get its trades
    result = run_backtest(feat, tight_mult, wide_mult, warmup_bar)
    # Re-run to get raw trades (run_backtest doesn't return them)
    # Instead, we'll run a lightweight version that only returns trades
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    n = len(c)

    adaptive_trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            continue

        if not in_pos:
            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )
            if entry_ok:
                in_pos = True
                entry_bar = i
                peak = c[i]
        else:
            peak = max(peak, c[i])
            if np.isfinite(rangepos[i]):
                rp = np.clip(rangepos[i], 0.0, 1.0)
                current_trail = tight_mult + rp * (wide_mult - tight_mult)
            else:
                current_trail = BASELINE_TRAIL_MULT

            trail_stop = peak - current_trail * ratr[i]
            exit_signal = c[i] < trail_stop or ema_f[i] < ema_s[i]

            if exit_signal:
                adaptive_trades.append({"entry_bar": entry_bar, "exit_bar": i})
                in_pos = False
                peak = 0.0

    # Build lookup: entry_bar → exit_bar
    base_map = {t["entry_bar"]: t["exit_bar"] for t in baseline_trades}
    adapt_map = {t["entry_bar"]: t["exit_bar"] for t in adaptive_trades}

    # Compare matched trades
    common_entries = set(base_map.keys()) & set(adapt_map.keys())
    earlier = 0
    later = 0
    same = 0
    for eb in common_entries:
        if adapt_map[eb] < base_map[eb]:
            earlier += 1
        elif adapt_map[eb] > base_map[eb]:
            later += 1
        else:
            same += 1

    return {
        "earlier": earlier,
        "later": later,
        "same": same,
        "matched": len(common_entries),
        "base_only": len(set(base_map.keys()) - set(adapt_map.keys())),
        "adapt_only": len(set(adapt_map.keys()) - set(base_map.keys())),
    }


def get_baseline_trades(feat: pd.DataFrame, warmup_bar: int) -> list[dict]:
    """Extract raw baseline trades for comparison."""
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

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            continue

        if not in_pos:
            entry_ok = (
                ema_f[i] > ema_s[i]
                and vdo_arr[i] > 0
                and d1_ok[i]
            )
            if entry_ok:
                in_pos = True
                entry_bar = i
                peak = c[i]
        else:
            peak = max(peak, c[i])
            trail_stop = peak - BASELINE_TRAIL_MULT * ratr[i]
            exit_signal = c[i] < trail_stop or ema_f[i] < ema_s[i]

            if exit_signal:
                trades.append({"entry_bar": entry_bar, "exit_bar": i})
                in_pos = False
                peak = 0.0

    return trades


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 20: Rangepos-Adaptive Trail")
    print(f"  tight_mult sweep: {TIGHT_MULTS}")
    print(f"  wide_mult sweep:  {WIDE_MULTS}")
    print(f"  baseline trail:   {BASELINE_TRAIL_MULT}")
    print(f"  modulator:        rangepos_84 (continuous, bar-by-bar)")
    print(f"  cost:             {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # ── Run baseline ──────────────────────────────────────────────────
    results = []
    print("\nRunning baseline (fixed trail=3.0)...")
    r = run_backtest(feat, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
    print(f"  trail_mult: median={r['trail_median']}, p10={r['trail_p10']}, p90={r['trail_p90']}")

    # ── Sweep 9 configs ───────────────────────────────────────────────
    for tight in TIGHT_MULTS:
        for wide in WIDE_MULTS:
            label = CONFIG_LABELS[(tight, wide)]
            print(f"\nRunning config {label} (tight={tight}, wide={wide})...")
            r = run_backtest(feat, tight, wide, warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
            print(f"  trail_mult: median={r['trail_median']}, p10={r['trail_p10']}, p90={r['trail_p90']}")

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

    out_path = RESULTS_DIR / "exp20_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n→ Saved to {out_path}")

    # ── Trade exit timing comparison ──────────────────────────────────
    print("\n" + "=" * 80)
    print("TRADE EXIT TIMING (vs baseline)")
    print("=" * 80)

    baseline_trades = get_baseline_trades(feat, warmup_bar)

    for tight in TIGHT_MULTS:
        for wide in WIDE_MULTS:
            label = CONFIG_LABELS[(tight, wide)]
            comp = compare_trade_exits(feat, tight, wide, warmup_bar, baseline_trades)
            print(f"  Config {label}: "
                  f"earlier={comp['earlier']}, later={comp['later']}, same={comp['same']} "
                  f"(matched={comp['matched']}, base_only={comp['base_only']}, adapt_only={comp['adapt_only']})")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    dynamic = df.iloc[1:]
    improvements = dynamic[(dynamic["d_sharpe"] > 0) & (dynamic["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: config {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        print(f"  trail_mult: median={best['trail_median']}, "
              f"p10={best['trail_p10']}, p90={best['trail_p90']}")
    else:
        sharpe_up = dynamic[dynamic["d_sharpe"] > 0]
        mdd_down = dynamic[dynamic["d_mdd"] < 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: config {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        elif not mdd_down.empty:
            best = mdd_down.loc[mdd_down["d_mdd"].idxmin()]
            print(f"MIXED: config {best['config']} improves MDD ({best['d_mdd']:+.2f} pp) "
                  f"but Sharpe changes {best['d_sharpe']:+.4f}")
        else:
            print("FAIL: No adaptive trail config improves Sharpe or MDD over baseline.")
            print("rangepos_84 continuous trail modulation does NOT help E5-ema21D1.")

    # ── Sanity checks ─────────────────────────────────────────────────
    print("\n" + "-" * 40)
    print("Sanity checks:")
    # Config F (tight=2.0, wide=4.0) at rp=0.5 → trail=3.0 (baseline)
    # Config H (tight=2.5, wide=3.5) at rp=0.5 → trail=3.0 (baseline)
    cfg_f = df[df["config"] == "F"].iloc[0] if len(df[df["config"] == "F"]) > 0 else None
    cfg_h = df[df["config"] == "H"].iloc[0] if len(df[df["config"] == "H"]) > 0 else None
    if cfg_f is not None:
        print(f"  Config F (rp=0.5→3.0): d_sharpe={cfg_f['d_sharpe']:+.4f}, "
              f"trail_median={cfg_f['trail_median']}")
    if cfg_h is not None:
        print(f"  Config H (rp=0.5→3.0): d_sharpe={cfg_h['d_sharpe']:+.4f}, "
              f"trail_median={cfg_h['trail_median']}")
    print("  (F and H midpoint = baseline 3.0 — divergence from baseline shows")
    print("   asymmetric rangepos distribution, not a bug)")


if __name__ == "__main__":
    main()
