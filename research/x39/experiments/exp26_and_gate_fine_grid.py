#!/usr/bin/env python3
"""Exp 26: AND-Gate Fine Grid.

Fine 2D grid (7x7=49 configs) centered around (rp=0.20, tq=-0.10) from exp22.
Tests whether this operating point is a robust plateau or a fragile peak.

Sweep:
  rp_threshold in [0.10, 0.13, 0.16, 0.19, 0.22, 0.25, 0.28]
  tq_threshold in [-0.25, -0.18, -0.10, -0.03, 0.05, 0.12, 0.20]
  -> 49 grid configs + 1 baseline = 50 runs

Usage:
    python -m research.x39.experiments.exp26_and_gate_fine_grid
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

RP_THRESHOLDS = [0.10, 0.13, 0.16, 0.19, 0.22, 0.25, 0.28]
TQ_THRESHOLDS = [-0.25, -0.18, -0.10, -0.03, 0.05, 0.12, 0.20]


def run_backtest(
    feat: pd.DataFrame,
    rp_threshold: float | None,
    tq_threshold: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional AND-gated exit."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    trendq = feat["trendq_84"].values
    n = len(c)

    mode_and = rp_threshold is not None and tq_threshold is not None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "and_gate": 0}
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

    config = f"AND_rp={rp_threshold}_tq={tq_threshold}" if mode_and else "baseline"

    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": config,
            "rp_threshold": rp_threshold,
            "tq_threshold": tq_threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "and_gate_exits": 0,
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

    return {
        "config": config,
        "rp_threshold": rp_threshold,
        "tq_threshold": tq_threshold,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "and_gate_exits": exit_counts["and_gate"],
    }


def gradient_at(hm: pd.DataFrame, rp_val: float, tq_val: float) -> tuple[float, float]:
    """Compute finite-difference gradient of d_Sharpe at (rp_val, tq_val)."""
    rps = sorted(hm.index.tolist())
    tqs = sorted(hm.columns.tolist())

    ri = rps.index(rp_val)
    ti = tqs.index(tq_val)

    # ∂/∂rp
    if ri == 0:
        grad_rp = (hm.loc[rps[ri + 1], tq_val] - hm.loc[rps[ri], tq_val]) / (rps[ri + 1] - rps[ri])
    elif ri == len(rps) - 1:
        grad_rp = (hm.loc[rps[ri], tq_val] - hm.loc[rps[ri - 1], tq_val]) / (rps[ri] - rps[ri - 1])
    else:
        grad_rp = (hm.loc[rps[ri + 1], tq_val] - hm.loc[rps[ri - 1], tq_val]) / (rps[ri + 1] - rps[ri - 1])

    # ∂/∂tq
    if ti == 0:
        grad_tq = (hm.loc[rp_val, tqs[ti + 1]] - hm.loc[rp_val, tqs[ti]]) / (tqs[ti + 1] - tqs[ti])
    elif ti == len(tqs) - 1:
        grad_tq = (hm.loc[rp_val, tqs[ti]] - hm.loc[rp_val, tqs[ti - 1]]) / (tqs[ti] - tqs[ti - 1])
    else:
        grad_tq = (hm.loc[rp_val, tqs[ti + 1]] - hm.loc[rp_val, tqs[ti - 1]]) / (tqs[ti + 1] - tqs[ti - 1])

    return float(grad_rp), float(grad_tq)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 26: AND-Gate Fine Grid")
    print(f"  rp_threshold sweep: {RP_THRESHOLDS}")
    print(f"  tq_threshold sweep: {TQ_THRESHOLDS}")
    print(f"  2D grid: {len(RP_THRESHOLDS)}x{len(TQ_THRESHOLDS)} = "
          f"{len(RP_THRESHOLDS) * len(TQ_THRESHOLDS)} configs + baseline = "
          f"{len(RP_THRESHOLDS) * len(TQ_THRESHOLDS) + 1} runs")
    print(f"  trail_mult: {TRAIL_MULT}, cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    results: list[dict] = []
    total_runs = len(RP_THRESHOLDS) * len(TQ_THRESHOLDS) + 1

    # ── 1. Baseline ───────────────────────────────────────────────────
    print(f"\n[1/{total_runs}] Baseline (no supplementary exit)...")
    r = run_backtest(feat, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")

    # ── 2. AND-gate fine grid ─────────────────────────────────────────
    run_num = 2
    for rp in RP_THRESHOLDS:
        for tq in TQ_THRESHOLDS:
            print(f"\n[{run_num}/{total_runs}] AND gate rp={rp:.2f}, tq={tq:.2f}...")
            r = run_backtest(feat, rp_threshold=rp, tq_threshold=tq, warmup_bar=warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, and_exits={r['and_gate_exits']}")
            run_num += 1

    # ── Build DataFrame ───────────────────────────────────────────────
    df = pd.DataFrame(results)
    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = improvement

    out_path = RESULTS_DIR / "exp26_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    and_rows = df[df["config"].str.startswith("AND_")]

    # ── HEATMAPS (7x7 grids) ─────────────────────────────────────────
    print("\n" + "=" * 80)
    print("HEATMAP: d_sharpe (rows=rp, cols=tq)")
    print("=" * 80)
    hm_sharpe = and_rows.pivot_table(index="rp_threshold", columns="tq_threshold", values="d_sharpe")
    print(hm_sharpe.to_string(float_format="{:+.4f}".format))

    print("\n" + "=" * 80)
    print("HEATMAP: d_mdd (rows=rp, cols=tq)")
    print("=" * 80)
    hm_mdd = and_rows.pivot_table(index="rp_threshold", columns="tq_threshold", values="d_mdd")
    print(hm_mdd.to_string(float_format="{:+.2f}".format))

    print("\n" + "=" * 80)
    print("HEATMAP: AND gate exit count (rows=rp, cols=tq)")
    print("=" * 80)
    hm_exits = and_rows.pivot_table(index="rp_threshold", columns="tq_threshold", values="and_gate_exits")
    print(hm_exits.to_string(float_format="{:.0f}".format))

    # ── ANALYSIS 1: rp cross-section at tq=-0.10 ─────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 1: rp dimension cross-section at tq=-0.10")
    print("  Looking for: plateau (robust) vs sharp peak (fragile)")
    print("=" * 80)
    tq_slice = and_rows[np.isclose(and_rows["tq_threshold"], -0.10)]
    tq_slice = tq_slice.sort_values("rp_threshold")
    print(f"  {'rp':>6s}  {'d_Sharpe':>10s}  {'d_MDD':>8s}  {'trades':>6s}  {'AND_exits':>9s}")
    for _, row in tq_slice.iterrows():
        print(f"  {row['rp_threshold']:6.2f}  {row['d_sharpe']:+10.4f}  "
              f"{row['d_mdd']:+8.2f}  {int(row['trades']):6d}  {int(row['and_gate_exits']):9d}")

    # Assess shape
    ds_vals = tq_slice["d_sharpe"].values
    rp_vals = tq_slice["rp_threshold"].values
    peak_idx = int(np.argmax(ds_vals))
    peak_rp = rp_vals[peak_idx]
    peak_ds = ds_vals[peak_idx]

    # Check if plateau: count how many are within 50% of peak
    if peak_ds > 0:
        plateau_count = int(np.sum(ds_vals > peak_ds * 0.5))
        print(f"\n  Peak at rp={peak_rp:.2f} (d_Sharpe={peak_ds:+.4f})")
        print(f"  Points within 50% of peak: {plateau_count}/{len(ds_vals)}")
        if plateau_count >= 4:
            print("  -> PLATEAU shape (robust)")
        elif plateau_count >= 2:
            print("  -> RIDGE shape (partially robust)")
        else:
            print("  -> PEAK shape (fragile)")
    else:
        print(f"\n  No positive d_Sharpe in this cross-section (best: {peak_ds:+.4f})")

    # ── ANALYSIS 2: tq cross-section at rp=0.19 ──────────────────────
    # rp=0.20 is not in the grid; rp=0.19 is closest
    print("\n" + "=" * 80)
    print("ANALYSIS 2: tq dimension cross-section at rp=0.19 (closest to exp22's 0.20)")
    print("  Looking for: flat stability vs fine structure")
    print("=" * 80)
    rp_slice = and_rows[np.isclose(and_rows["rp_threshold"], 0.19)]
    rp_slice = rp_slice.sort_values("tq_threshold")
    print(f"  {'tq':>6s}  {'d_Sharpe':>10s}  {'d_MDD':>8s}  {'trades':>6s}  {'AND_exits':>9s}")
    for _, row in rp_slice.iterrows():
        print(f"  {row['tq_threshold']:6.2f}  {row['d_sharpe']:+10.4f}  "
              f"{row['d_mdd']:+8.2f}  {int(row['trades']):6d}  {int(row['and_gate_exits']):9d}")

    tq_ds_vals = rp_slice["d_sharpe"].values
    tq_range = tq_ds_vals.max() - tq_ds_vals.min()
    print(f"\n  d_Sharpe range across tq: {tq_range:.4f}")
    if tq_range < 0.02:
        print("  -> FLAT (tq dimension is stable)")
    elif tq_range < 0.05:
        print("  -> MODERATE variation")
    else:
        print("  -> HIGH variation (tq dimension matters)")

    # ── ANALYSIS 3: Contour shape classification ─────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 3: Contour shape classification")
    print("=" * 80)

    # Count how many configs improve both Sharpe and MDD
    both_improve = and_rows[(and_rows["d_sharpe"] > 0) & (and_rows["d_mdd"] < 0)]
    sharpe_only = and_rows[(and_rows["d_sharpe"] > 0) & (and_rows["d_mdd"] >= 0)]
    mdd_only = and_rows[(and_rows["d_sharpe"] <= 0) & (and_rows["d_mdd"] < 0)]
    neither = and_rows[(and_rows["d_sharpe"] <= 0) & (and_rows["d_mdd"] >= 0)]

    print(f"  Both improve (Sh+ MDD-): {len(both_improve)}/49")
    print(f"  Sharpe only (Sh+ MDD+):  {len(sharpe_only)}/49")
    print(f"  MDD only (Sh- MDD-):     {len(mdd_only)}/49")
    print(f"  Neither (Sh- MDD+):      {len(neither)}/49")

    if len(both_improve) > 0:
        best = both_improve.loc[both_improve["d_sharpe"].idxmax()]
        print(f"\n  Best (both): rp={best['rp_threshold']:.2f}, tq={best['tq_threshold']:.2f}")
        print(f"    d_Sharpe={best['d_sharpe']:+.4f}, d_MDD={best['d_mdd']:+.2f} pp, "
              f"AND exits={int(best['and_gate_exits'])}")

    # ── ANALYSIS 4: Exit count vs performance ─────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 4: d_Sharpe vs AND gate exit count")
    print("=" * 80)

    exits_sorted = and_rows.sort_values("and_gate_exits")
    print(f"  {'AND_exits':>9s}  {'d_Sharpe':>10s}  {'d_MDD':>8s}  {'config':s}")
    for _, row in exits_sorted.iterrows():
        marker = " <--" if row["d_sharpe"] == and_rows["d_sharpe"].max() else ""
        print(f"  {int(row['and_gate_exits']):9d}  {row['d_sharpe']:+10.4f}  "
              f"{row['d_mdd']:+8.2f}  rp={row['rp_threshold']:.2f},tq={row['tq_threshold']:.2f}{marker}")

    # Sweet spot analysis
    pos_rows = and_rows[and_rows["d_sharpe"] > 0]
    if len(pos_rows) > 0:
        exit_min = int(pos_rows["and_gate_exits"].min())
        exit_max = int(pos_rows["and_gate_exits"].max())
        print(f"\n  Positive d_Sharpe configs: exit count range [{exit_min}, {exit_max}]")
    else:
        print("\n  No configs with positive d_Sharpe")

    # ── ANALYSIS 5: Gradient at optimum ───────────────────────────────
    print("\n" + "=" * 80)
    print("ANALYSIS 5: Gradient magnitude at optimum")
    print("  Concern threshold: |gradient| > 0.5 Sharpe per unit threshold")
    print("=" * 80)

    best_idx = and_rows["d_sharpe"].idxmax()
    best_row = and_rows.loc[best_idx]
    best_rp = best_row["rp_threshold"]
    best_tq = best_row["tq_threshold"]

    grad_rp, grad_tq = gradient_at(hm_sharpe, best_rp, best_tq)
    print(f"  Optimum: rp={best_rp:.2f}, tq={best_tq:.2f} (d_Sharpe={best_row['d_sharpe']:+.4f})")
    print(f"  |dSharpe/drp| = {abs(grad_rp):.3f} Sharpe/unit")
    print(f"  |dSharpe/dtq| = {abs(grad_tq):.3f} Sharpe/unit")

    rp_fragile = abs(grad_rp) > 0.5
    tq_fragile = abs(grad_tq) > 0.5
    print(f"  rp dimension: {'FRAGILE' if rp_fragile else 'ROBUST'} (threshold 0.5)")
    print(f"  tq dimension: {'FRAGILE' if tq_fragile else 'ROBUST'} (threshold 0.5)")

    # Also compute at the exp22 reference point (rp=0.19, tq=-0.10)
    ref_rp, ref_tq = 0.19, -0.10
    if ref_rp in hm_sharpe.index and ref_tq in hm_sharpe.columns:
        ref_grad_rp, ref_grad_tq = gradient_at(hm_sharpe, ref_rp, ref_tq)
        ref_ds = hm_sharpe.loc[ref_rp, ref_tq]
        print(f"\n  At exp22 reference (rp=0.19, tq=-0.10): d_Sharpe={ref_ds:+.4f}")
        print(f"  |dSharpe/drp| = {abs(ref_grad_rp):.3f} Sharpe/unit")
        print(f"  |dSharpe/dtq| = {abs(ref_grad_tq):.3f} Sharpe/unit")

    # ── VERDICT ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Shape verdict
    if peak_ds > 0:
        if plateau_count >= 4 and tq_range < 0.02:
            shape = "PLATEAU"
            desc = "robust operating region"
        elif plateau_count >= 3 and tq_range < 0.05:
            shape = "BROAD_RIDGE"
            desc = "partially robust, moderate sensitivity"
        elif plateau_count >= 2:
            shape = "RIDGE"
            desc = "directionally robust but narrow"
        else:
            shape = "PEAK"
            desc = "fragile, parameter-sensitive"
    else:
        shape = "NO_IMPROVEMENT"
        desc = "AND gate does not improve baseline at fine resolution"

    print(f"  Shape: {shape} — {desc}")
    print(f"  Optimum: rp={best_rp:.2f}, tq={best_tq:.2f}")
    print(f"    d_Sharpe={best_row['d_sharpe']:+.4f}, d_MDD={best_row['d_mdd']:+.2f} pp, "
          f"AND exits={int(best_row['and_gate_exits'])}")
    print(f"  Gradient: |drp|={abs(grad_rp):.3f}, |dtq|={abs(grad_tq):.3f}")

    overall_fragile = rp_fragile or tq_fragile or shape == "PEAK"
    print(f"\n  Overall: {'FRAGILE — (rp=0.20, tq=-0.10) is NOT a robust operating point'}"
          if overall_fragile
          else f"\n  Overall: ROBUST — (rp≈{best_rp:.2f}, tq≈{best_tq:.2f}) is a safe operating region")

    print(f"\n  Configs improving both Sharpe and MDD: {len(both_improve)}/49")
    if len(both_improve) > 0:
        print(f"  rp range: [{both_improve['rp_threshold'].min():.2f}, "
              f"{both_improve['rp_threshold'].max():.2f}]")
        print(f"  tq range: [{both_improve['tq_threshold'].min():.2f}, "
              f"{both_improve['tq_threshold'].max():.2f}]")


if __name__ == "__main__":
    main()
