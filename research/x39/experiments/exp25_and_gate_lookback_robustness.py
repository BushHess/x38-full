#!/usr/bin/env python3
"""Exp 25: AND-Gate Lookback Robustness.

Exp23 showed rangepos_84 standalone exit is FRAGILE (Sharpe range 0.1525).
This experiment tests whether exp22's AND gate (rangepos + trendq) inherits
that fragility or if trendq confirmation stabilizes it.

Sweep:
  AND gate:      L in [42,63,84,105,126,168] x rp in [0.15,0.20,0.25,0.30]
                 tq_threshold FIXED at -0.10 (exp22 optimum)
  rangepos-only: same L x rp grid (exp23 reproduction + L=105 extension)
  baseline:      no supplementary exit
  -> 24 AND + 24 rangepos-only + 1 baseline = 49 runs

Key question: is AND gate Sharpe range across L < 0.05 (robust) or > 0.10 (fragile)?

Usage:
    python -m research.x39.experiments.exp25_and_gate_lookback_robustness
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

LOOKBACKS = [42, 63, 84, 105, 126, 168]
RP_THRESHOLDS = [0.15, 0.20, 0.25, 0.30]
TQ_THRESHOLD = -0.10  # fixed (exp22 optimum)


def compute_rangepos(high: np.ndarray, low: np.ndarray, close: np.ndarray, lookback: int) -> np.ndarray:
    """Compute rangepos_L = (close - rolling_low) / (rolling_high - rolling_low)."""
    roll_hi = pd.Series(high).rolling(lookback, min_periods=lookback).max().values
    roll_lo = pd.Series(low).rolling(lookback, min_periods=lookback).min().values
    denom = roll_hi - roll_lo
    return np.where(denom > 1e-10, (close - roll_lo) / denom, np.nan)


def run_backtest(
    feat: pd.DataFrame,
    rangepos: np.ndarray | None,
    rp_threshold: float | None,
    trendq: np.ndarray | None,
    tq_threshold: float | None,
    lookback: int | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional AND-gated or rangepos-only exit.

    - Both rp and tq set: AND gate (rangepos AND trendq must both trigger).
    - rp only: rangepos-only exit.
    - Neither: baseline.
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    mode_and = rangepos is not None and rp_threshold is not None and tq_threshold is not None
    mode_rp_only = rangepos is not None and rp_threshold is not None and tq_threshold is None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "and_gate": 0, "rangepos": 0}
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

            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None

            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"
            elif mode_and:
                rp_ok = np.isfinite(rangepos[i]) and rangepos[i] < rp_threshold
                tq_ok = np.isfinite(trendq[i]) and trendq[i] < tq_threshold
                if rp_ok and tq_ok:
                    exit_reason = "and_gate"
            elif mode_rp_only:
                if np.isfinite(rangepos[i]) and rangepos[i] < rp_threshold:
                    exit_reason = "rangepos"

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

                exit_counts[exit_reason] += 1
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()

    if mode_and:
        config = f"AND_L={lookback}_rp={rp_threshold}"
    elif mode_rp_only:
        config = f"RP_L={lookback}_rp={rp_threshold}"
    else:
        config = "baseline"

    mechanism = "and_gate" if mode_and else ("rp_only" if mode_rp_only else "baseline")

    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": config, "mechanism": mechanism,
            "lookback": lookback, "rp_threshold": rp_threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_and_gate": 0, "exit_rangepos": 0,
            "supp_exits": 0, "selectivity_pct": np.nan,
        }

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = rets.mean() / rets.std() * np.sqrt(bars_per_year) if rets.std() > 0 else 0.0

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

    supp_key = "and_gate" if mode_and else "rangepos"
    supp_trades = tdf[tdf["exit_reason"] == supp_key] if mode_and or mode_rp_only else pd.DataFrame()
    supp_exits = len(supp_trades)
    selectivity = np.nan
    if supp_exits > 0:
        selectivity = round((supp_trades["win"] == 0).sum() / supp_exits * 100, 1)

    return {
        "config": config,
        "mechanism": mechanism,
        "lookback": lookback,
        "rp_threshold": rp_threshold,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "exposure_pct": round(exposure * 100, 1),
        "exit_trail": exit_counts["trail"],
        "exit_trend": exit_counts["trend"],
        "exit_and_gate": exit_counts["and_gate"],
        "exit_rangepos": exit_counts["rangepos"],
        "supp_exits": supp_exits,
        "selectivity_pct": selectivity,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    total_runs = len(LOOKBACKS) * len(RP_THRESHOLDS) * 2 + 1  # AND + RP-only + baseline

    print("=" * 80)
    print("EXP 25: AND-Gate Lookback Robustness")
    print(f"  lookback sweep:    {LOOKBACKS}")
    print(f"  rp_threshold sweep: {RP_THRESHOLDS}")
    print(f"  tq_threshold:       {TQ_THRESHOLD} (FIXED)")
    print(f"  AND gate configs:   {len(LOOKBACKS) * len(RP_THRESHOLDS)}")
    print(f"  RP-only configs:    {len(LOOKBACKS) * len(RP_THRESHOLDS)}")
    print(f"  total runs:         {total_runs}")
    print(f"  trail_mult:         {TRAIL_MULT}, cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # Pre-compute rangepos for all lookbacks
    high = h4["high"].values.astype(np.float64)
    low = h4["low"].values.astype(np.float64)
    close = feat["close"].values
    rangepos_cache: dict[int, np.ndarray] = {}
    for lb in LOOKBACKS:
        rangepos_cache[lb] = compute_rangepos(high, low, close, lb)
    print(f"Pre-computed rangepos for lookbacks: {LOOKBACKS}")

    # trendq_84 from explore.py (FIXED, not varied)
    trendq = feat["trendq_84"].values

    results: list[dict] = []
    run_num = 1

    # ── 1. Baseline ───────────────────────────────────────────────────
    print(f"\n[{run_num}/{total_runs}] Baseline (no supplementary exit)...")
    r = run_backtest(feat, None, None, None, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, trades={r['trades']}")
    run_num += 1

    # ── 2. AND-gate sweep ─────────────────────────────────────────────
    print("\n--- AND GATE (rangepos_L < rp AND trendq_84 < -0.10) ---")
    for lb in LOOKBACKS:
        rp = rangepos_cache[lb]
        for thr in RP_THRESHOLDS:
            print(f"\n[{run_num}/{total_runs}] AND L={lb}, rp={thr}...")
            r = run_backtest(feat, rp, thr, trendq, TQ_THRESHOLD, lb, warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, and_exits={r['exit_and_gate']}, "
                  f"selectivity={r['selectivity_pct']}%")
            run_num += 1

    # ── 3. Rangepos-only sweep (exp23 reproduction + L=105) ───────────
    print("\n--- RANGEPOS-ONLY (rangepos_L < rp) ---")
    for lb in LOOKBACKS:
        rp = rangepos_cache[lb]
        for thr in RP_THRESHOLDS:
            print(f"\n[{run_num}/{total_runs}] RP-only L={lb}, rp={thr}...")
            r = run_backtest(feat, rp, thr, None, None, lb, warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, rp_exits={r['exit_rangepos']}")
            run_num += 1

    # ── Results ───────────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base_sharpe = df.iloc[0]["sharpe"]
    base_mdd = df.iloc[0]["mdd_pct"]
    df["d_sharpe"] = df["sharpe"] - base_sharpe
    df["d_mdd"] = df["mdd_pct"] - base_mdd  # negative = improvement

    print("\n" + "=" * 80)
    print("FULL RESULTS TABLE")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp25_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Analysis 1: AND gate lookback sensitivity at rp=0.20 ─────────
    print("\n" + "=" * 80)
    print("ANALYSIS 1: AND gate lookback sensitivity (fixed rp=0.20, tq=-0.10)")
    print("  Compare with rangepos-only at rp=0.25 (exp23 reference)")
    print("=" * 80)

    and_rows = df[df["mechanism"] == "and_gate"]
    rp_rows = df[df["mechanism"] == "rp_only"]

    and_020 = and_rows[and_rows["rp_threshold"] == 0.20].sort_values("lookback")
    rp_025 = rp_rows[rp_rows["rp_threshold"] == 0.25].sort_values("lookback")

    print(f"\n  {'L':>5s}  {'AND Sharpe':>10s}  {'AND d_Sh':>10s}  {'AND exits':>9s}  "
          f"{'RP Sharpe':>10s}  {'RP d_Sh':>10s}  {'RP exits':>9s}")
    print("  " + "-" * 75)
    for lb in LOOKBACKS:
        a = and_020[and_020["lookback"] == lb]
        r = rp_025[rp_025["lookback"] == lb]
        a_sh = a["sharpe"].values[0] if len(a) else np.nan
        a_dsh = a["d_sharpe"].values[0] if len(a) else np.nan
        a_ex = int(a["supp_exits"].values[0]) if len(a) else 0
        r_sh = r["sharpe"].values[0] if len(r) else np.nan
        r_dsh = r["d_sharpe"].values[0] if len(r) else np.nan
        r_ex = int(r["supp_exits"].values[0]) if len(r) else 0
        print(f"  {lb:5d}  {a_sh:10.4f}  {a_dsh:+10.4f}  {a_ex:9d}  "
              f"{r_sh:10.4f}  {r_dsh:+10.4f}  {r_ex:9d}")

    # ── Analysis 2: Sharpe range metric ──────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 2: Sharpe range metric (max - min across L)")
    print("  < 0.05 = ROBUST plateau, > 0.10 = FRAGILE")
    print("=" * 80)

    for rp_thr in RP_THRESHOLDS:
        and_sub = and_rows[and_rows["rp_threshold"] == rp_thr]
        rp_sub = rp_rows[rp_rows["rp_threshold"] == rp_thr]

        and_range = and_sub["sharpe"].max() - and_sub["sharpe"].min() if len(and_sub) else np.nan
        rp_range = rp_sub["sharpe"].max() - rp_sub["sharpe"].min() if len(rp_sub) else np.nan

        def label(r: float) -> str:
            if np.isnan(r):
                return "N/A"
            if r < 0.05:
                return "ROBUST"
            if r < 0.10:
                return "MODERATE"
            return "FRAGILE"

        print(f"  rp={rp_thr:.2f}:  AND range={and_range:.4f} ({label(and_range)}),  "
              f"RP-only range={rp_range:.4f} ({label(rp_range)})")

    # Key comparison at rp=0.20 (AND) vs rp=0.25 (RP-only)
    and_range_020 = and_020["sharpe"].max() - and_020["sharpe"].min() if len(and_020) else np.nan
    rp_range_025 = rp_025["sharpe"].max() - rp_025["sharpe"].min() if len(rp_025) else np.nan
    print(f"\n  KEY COMPARISON: AND(rp=0.20) range={and_range_020:.4f} vs RP-only(rp=0.25) range={rp_range_025:.4f}")
    if np.isfinite(and_range_020) and np.isfinite(rp_range_025):
        ratio = and_range_020 / rp_range_025 if rp_range_025 > 1e-10 else np.inf
        print(f"  Ratio: {ratio:.2f}x  ({'STABILIZED' if ratio < 0.50 else 'PARTIALLY STABILIZED' if ratio < 0.80 else 'NOT STABILIZED'})")

    # ── Analysis 3: Optimal L per mechanism ──────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 3: Optimal L per mechanism")
    print("=" * 80)

    for rp_thr in RP_THRESHOLDS:
        and_sub = and_rows[and_rows["rp_threshold"] == rp_thr]
        rp_sub = rp_rows[rp_rows["rp_threshold"] == rp_thr]

        if len(and_sub):
            best_and = and_sub.loc[and_sub["sharpe"].idxmax()]
            print(f"  rp={rp_thr:.2f}:  AND best L={int(best_and['lookback'])} "
                  f"(Sh={best_and['sharpe']:.4f}, d_Sh={best_and['d_sharpe']:+.4f}, "
                  f"MDD={best_and['mdd_pct']:.2f}%)")
        if len(rp_sub):
            best_rp = rp_sub.loc[rp_sub["sharpe"].idxmax()]
            print(f"          RP  best L={int(best_rp['lookback'])} "
                  f"(Sh={best_rp['sharpe']:.4f}, d_Sh={best_rp['d_sharpe']:+.4f}, "
                  f"MDD={best_rp['mdd_pct']:.2f}%)")

    # ── Analysis 4: Exit count vs L ──────────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 4: Supplementary exit count vs L (at rp=0.20)")
    print("=" * 80)

    and_020_sorted = and_020.sort_values("lookback")
    rp_020 = rp_rows[rp_rows["rp_threshold"] == 0.20].sort_values("lookback")

    print(f"  {'L':>5s}  {'AND exits':>9s}  {'RP exits':>9s}  {'AND/RP ratio':>12s}")
    print("  " + "-" * 42)
    for lb in LOOKBACKS:
        a = and_020_sorted[and_020_sorted["lookback"] == lb]
        r = rp_020[rp_020["lookback"] == lb]
        a_ex = int(a["supp_exits"].values[0]) if len(a) else 0
        r_ex = int(r["supp_exits"].values[0]) if len(r) else 0
        ratio_str = f"{a_ex / r_ex:.2f}" if r_ex > 0 else "N/A"
        print(f"  {lb:5d}  {a_ex:9d}  {r_ex:9d}  {ratio_str:>12s}")

    # ── Analysis 5: Heatmaps ─────────────────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 5: Sharpe heatmaps (L x rp_threshold)")
    print("=" * 80)

    print("\nAND gate d_sharpe:")
    and_pivot = and_rows.pivot_table(index="lookback", columns="rp_threshold", values="d_sharpe")
    print(and_pivot.to_string(float_format="{:+.4f}".format))

    print("\nRP-only d_sharpe:")
    rp_pivot = rp_rows.pivot_table(index="lookback", columns="rp_threshold", values="d_sharpe")
    print(rp_pivot.to_string(float_format="{:+.4f}".format))

    print("\nAND gate d_mdd:")
    and_mdd_pivot = and_rows.pivot_table(index="lookback", columns="rp_threshold", values="d_mdd")
    print(and_mdd_pivot.to_string(float_format="{:+.2f}".format))

    print("\nRP-only d_mdd:")
    rp_mdd_pivot = rp_rows.pivot_table(index="lookback", columns="rp_threshold", values="d_mdd")
    print(rp_mdd_pivot.to_string(float_format="{:+.2f}".format))

    print("\nAND gate exit count:")
    and_exit_pivot = and_rows.pivot_table(index="lookback", columns="rp_threshold", values="supp_exits")
    print(and_exit_pivot.to_string(float_format="{:.0f}".format))

    print("\nRP-only exit count:")
    rp_exit_pivot = rp_rows.pivot_table(index="lookback", columns="rp_threshold", values="supp_exits")
    print(rp_exit_pivot.to_string(float_format="{:.0f}".format))

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Primary metric: AND gate range at rp=0.20 vs RP-only range at rp=0.25
    print(f"\n  Baseline: Sharpe={base_sharpe}, MDD={base_mdd}%")
    print(f"\n  AND gate Sharpe range (rp=0.20, across L): {and_range_020:.4f}")
    print(f"  RP-only Sharpe range (rp=0.25, across L):  {rp_range_025:.4f}")

    if np.isfinite(and_range_020):
        if and_range_020 < 0.05:
            print("\n  -> AND gate: ROBUST PLATEAU (range < 0.05)")
            print("     trendq confirmation STABILIZES rangepos lookback sensitivity")
            verdict = "ROBUST"
        elif and_range_020 < 0.10:
            print("\n  -> AND gate: MODERATE sensitivity (0.05 <= range < 0.10)")
            print("     trendq provides PARTIAL stabilization")
            verdict = "MODERATE"
        else:
            print("\n  -> AND gate: FRAGILE (range >= 0.10)")
            print("     trendq does NOT stabilize rangepos lookback sensitivity")
            verdict = "FRAGILE"

        # Stabilization ratio
        if np.isfinite(rp_range_025) and rp_range_025 > 1e-10:
            stab = 1.0 - and_range_020 / rp_range_025
            print(f"\n  Stabilization: {stab:.1%} reduction in Sharpe range vs RP-only")
            if stab > 0.50:
                print("  -> STRONG stabilization (>50% range reduction)")
            elif stab > 0.20:
                print("  -> MODERATE stabilization (20-50% range reduction)")
            elif stab > 0:
                print("  -> WEAK stabilization (<20% range reduction)")
            else:
                print("  -> NO stabilization (AND gate is equally or more fragile)")

    # Check if ALL AND configs at rp=0.20 beat baseline
    if len(and_020):
        all_beat = (and_020["d_sharpe"] > 0).all()
        n_beat = (and_020["d_sharpe"] > 0).sum()
        print(f"\n  AND(rp=0.20) configs beating baseline: {n_beat}/{len(and_020)}")
        if all_beat:
            print("  -> ALL lookbacks beat baseline — mechanism is directionally correct")
        else:
            n_worse = len(and_020) - n_beat
            print(f"  -> {n_worse} lookback(s) WORSE than baseline — lookback choice matters")

    # Best AND config
    if len(and_rows):
        both_improve = and_rows[(and_rows["d_sharpe"] > 0) & (and_rows["d_mdd"] < 0)]
        if not both_improve.empty:
            best = both_improve.loc[both_improve["d_sharpe"].idxmax()]
            print(f"\n  Best AND config (Sharpe+MDD): L={int(best['lookback'])}, rp={best['rp_threshold']}")
            print(f"    Sharpe={best['sharpe']} ({best['d_sharpe']:+.4f}), "
                  f"MDD={best['mdd_pct']}% ({best['d_mdd']:+.2f} pp), "
                  f"trades={int(best['trades'])}, AND exits={int(best['supp_exits'])}")
        else:
            best = and_rows.loc[and_rows["d_sharpe"].idxmax()]
            print(f"\n  Best AND config (Sharpe only): L={int(best['lookback'])}, rp={best['rp_threshold']}")
            print(f"    Sharpe={best['sharpe']} ({best['d_sharpe']:+.4f}), "
                  f"MDD={best['mdd_pct']}% ({best['d_mdd']:+.2f} pp)")

    print(f"\n  VERDICT: {verdict}")


if __name__ == "__main__":
    main()
