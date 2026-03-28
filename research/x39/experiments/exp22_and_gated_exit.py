#!/usr/bin/env python3
"""Exp 22: AND-Gated Feature Interaction Exit.

E5-ema21D1 with AND-gated supplementary exit:
  exit when (rangepos_84 < rp_threshold AND trendq_84 < tq_threshold)

Both features must agree before firing — filters out single-feature false alarms.
Entry logic UNCHANGED. AND gate added as additional exit (OR with trail + trend).

Sweep (2D grid):
  rp_threshold in [0.20, 0.25, 0.30, 0.35]
  tq_threshold in [-0.30, -0.10, 0.10, 0.30]
  → 16 grid configs + baseline + 2 single-feature controls = 19 runs

Usage:
    python -m research.x39.experiments.exp22_and_gated_exit
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

RP_THRESHOLDS = [0.20, 0.25, 0.30, 0.35]
TQ_THRESHOLDS = [-0.30, -0.10, 0.10, 0.30]


def run_backtest(
    feat: pd.DataFrame,
    rp_threshold: float | None,
    tq_threshold: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional AND-gated / single-feature exit.

    - Both None: baseline (no supplementary exit).
    - rp_threshold only: rangepos-only control (exp12 reproduction).
    - tq_threshold only: trendq-only control (exp13 reproduction).
    - Both set: AND gate (rangepos AND trendq must both trigger).
    """
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
    mode_rp_only = rp_threshold is not None and tq_threshold is None
    mode_tq_only = rp_threshold is None and tq_threshold is not None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "and_gate": 0, "rangepos": 0, "trendq": 0}
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    # Track per-bar feature triggers for overlap analysis
    and_exit_bars: list[int] = []
    rp_triggered_at_and: list[bool] = []  # would rangepos-only have fired?
    tq_triggered_at_and: list[bool] = []  # would trendq-only have fired?

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
                    and_exit_bars.append(i)
                    # Would single-feature exits also have fired?
                    # rangepos-only at rp=0.25, trendq-only at tq=-0.20 (exp12/13 best)
                    rp_triggered_at_and.append(
                        np.isfinite(rangepos[i]) and rangepos[i] < 0.25
                    )
                    tq_triggered_at_and.append(
                        np.isfinite(trendq[i]) and trendq[i] < -0.20
                    )
            elif mode_rp_only:
                if np.isfinite(rangepos[i]) and rangepos[i] < rp_threshold:
                    exit_reason = "rangepos"
            elif mode_tq_only:
                if np.isfinite(trendq[i]) and trendq[i] < tq_threshold:
                    exit_reason = "trendq"

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

    # Config label
    if mode_and:
        config = f"AND_rp={rp_threshold}_tq={tq_threshold}"
    elif mode_rp_only:
        config = f"rp_only={rp_threshold}"
    elif mode_tq_only:
        config = f"tq_only={tq_threshold}"
    else:
        config = "baseline"

    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": config,
            "rp_threshold": rp_threshold,
            "tq_threshold": tq_threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_and_gate": 0,
            "exit_rangepos": 0, "exit_trendq": 0,
            "and_selectivity": np.nan,
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

    # Selectivity: % of AND/rangepos/trendq exits on losing trades
    supp_reason = "and_gate" if mode_and else ("rangepos" if mode_rp_only else ("trendq" if mode_tq_only else None))
    supp_trades = tdf[tdf["exit_reason"] == supp_reason] if supp_reason else pd.DataFrame()
    selectivity = np.nan
    if len(supp_trades) > 0:
        selectivity = round((supp_trades["win"] == 0).sum() / len(supp_trades) * 100, 1)

    return {
        "config": config,
        "rp_threshold": rp_threshold,
        "tq_threshold": tq_threshold,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(tdf["bars_held"].mean(), 1),
        "avg_win": round(wins["net_ret"].mean() * 100, 2) if len(wins) > 0 else np.nan,
        "avg_loss": round(losses["net_ret"].mean() * 100, 2) if len(losses) > 0 else np.nan,
        "exposure_pct": round(exposure * 100, 1),
        "exit_trail": exit_counts["trail"],
        "exit_trend": exit_counts["trend"],
        "exit_and_gate": exit_counts["and_gate"],
        "exit_rangepos": exit_counts["rangepos"],
        "exit_trendq": exit_counts["trendq"],
        "and_selectivity": selectivity,
        # Overlap info (only meaningful for AND mode)
        "_and_exit_bars": and_exit_bars,
        "_rp_triggered": rp_triggered_at_and,
        "_tq_triggered": tq_triggered_at_and,
    }


def overlap_analysis(results: list[dict]) -> None:
    """Print overlap matrix for AND-gated configs."""
    print("\n" + "=" * 80)
    print("OVERLAP ANALYSIS")
    print("  At each AND-gate exit: would rangepos-only (rp<0.25) or")
    print("  trendq-only (tq<-0.20) also have fired?")
    print("=" * 80)

    for r in results:
        if not r["config"].startswith("AND_"):
            continue
        bars = r["_and_exit_bars"]
        rp_trig = r["_rp_triggered"]
        tq_trig = r["_tq_triggered"]
        n_exits = len(bars)
        if n_exits == 0:
            print(f"  {r['config']:30s}  0 AND exits")
            continue

        both = sum(a and b for a, b in zip(rp_trig, tq_trig))
        rp_only = sum(a and not b for a, b in zip(rp_trig, tq_trig))
        tq_only = sum(not a and b for a, b in zip(rp_trig, tq_trig))
        neither = sum(not a and not b for a, b in zip(rp_trig, tq_trig))

        print(f"  {r['config']:30s}  {n_exits:3d} exits | "
              f"both={both} rp_only={rp_only} tq_only={tq_only} AND_unique={neither}")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 22: AND-Gated Feature Interaction Exit")
    print(f"  rp_threshold sweep: {RP_THRESHOLDS}")
    print(f"  tq_threshold sweep: {TQ_THRESHOLDS}")
    print(f"  2D grid: {len(RP_THRESHOLDS)}x{len(TQ_THRESHOLDS)} = "
          f"{len(RP_THRESHOLDS) * len(TQ_THRESHOLDS)} configs + baseline + 2 controls")
    print(f"  trail_mult: {TRAIL_MULT}, cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    results: list[dict] = []

    # ── 1. Baseline ───────────────────────────────────────────────────
    print("\n[1/19] Baseline (no supplementary exit)...")
    r = run_backtest(feat, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")

    # ── 2. Single-feature controls ────────────────────────────────────
    print("\n[2/19] Control: rangepos-only rp=0.25 (exp12 reproduction)...")
    r = run_backtest(feat, rp_threshold=0.25, tq_threshold=None, warmup_bar=warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, rangepos_exits={r['exit_rangepos']}, "
          f"selectivity={r['and_selectivity']}%")

    print("\n[3/19] Control: trendq-only tq=-0.20 (exp13 reproduction)...")
    r = run_backtest(feat, rp_threshold=None, tq_threshold=-0.20, warmup_bar=warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, trendq_exits={r['exit_trendq']}, "
          f"selectivity={r['and_selectivity']}%")

    # ── 3. AND-gate 2D grid ───────────────────────────────────────────
    run_num = 4
    for rp in RP_THRESHOLDS:
        for tq in TQ_THRESHOLDS:
            print(f"\n[{run_num}/19] AND gate rp={rp}, tq={tq}...")
            r = run_backtest(feat, rp_threshold=rp, tq_threshold=tq, warmup_bar=warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, and_exits={r['exit_and_gate']}, "
                  f"selectivity={r['and_selectivity']}%")
            run_num += 1

    # ── Results table ─────────────────────────────────────────────────
    # Strip internal fields before building DataFrame
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
    df = pd.DataFrame(clean)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp22_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Overlap analysis ──────────────────────────────────────────────
    overlap_analysis(results)

    # ── Selectivity comparison ────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SELECTIVITY COMPARISON (% of supplementary exits on losing trades)")
    print("  Higher = better (exits are correctly targeting losers)")
    print("=" * 80)
    for _, row in df.iterrows():
        if row["config"] == "baseline":
            continue
        sel = row["and_selectivity"]
        n_supp = row["exit_and_gate"] + row["exit_rangepos"] + row["exit_trendq"]
        if n_supp > 0 and np.isfinite(sel):
            print(f"  {row['config']:30s}  {n_supp:3d} supp exits, {sel:5.1f}% on losers")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Focus on AND-gate configs (skip baseline and controls)
    and_rows = df[df["config"].str.startswith("AND_")]
    controls = df[(df["config"].str.startswith("rp_only")) | (df["config"].str.startswith("tq_only"))]

    improvements = and_rows[(and_rows["d_sharpe"] > 0) & (and_rows["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        print(f"  AND exits: {int(best['exit_and_gate'])}, "
              f"selectivity: {best['and_selectivity']}%")

        # Compare with single-feature controls
        rp_ctrl = controls[controls["config"].str.startswith("rp_only")]
        tq_ctrl = controls[controls["config"].str.startswith("tq_only")]
        if not rp_ctrl.empty:
            rpc = rp_ctrl.iloc[0]
            print(f"\n  vs rangepos-only (rp=0.25):  d_sharpe={rpc['d_sharpe']:+.4f}, "
                  f"d_mdd={rpc['d_mdd']:+.2f}")
        if not tq_ctrl.empty:
            tqc = tq_ctrl.iloc[0]
            print(f"  vs trendq-only (tq=-0.20):   d_sharpe={tqc['d_sharpe']:+.4f}, "
                  f"d_mdd={tqc['d_mdd']:+.2f}")

        print(f"\n  AND gate {'BETTER' if best['d_sharpe'] > rpc['d_sharpe'] else 'WORSE'} "
              f"than rangepos-only on Sharpe, "
              f"{'BETTER' if best['d_mdd'] < rpc['d_mdd'] else 'WORSE'} on MDD")
    else:
        sharpe_up = and_rows[and_rows["d_sharpe"] > 0]
        mdd_down = and_rows[and_rows["d_mdd"] < 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        elif not mdd_down.empty:
            best = mdd_down.loc[mdd_down["d_mdd"].idxmin()]
            print(f"MIXED: {best['config']} improves MDD ({best['d_mdd']:+.2f} pp) "
                  f"but Sharpe changes {best['d_sharpe']:+.4f}")
        else:
            print("FAIL: No AND-gate config improves Sharpe or MDD over baseline.")

    # ── Exit reason breakdown ─────────────────────────────────────────
    print("\n" + "-" * 60)
    print("Exit reason breakdown:")
    for _, row in df.iterrows():
        total_exits = (row["exit_trail"] + row["exit_trend"]
                       + row["exit_and_gate"] + row["exit_rangepos"] + row["exit_trendq"])
        if total_exits == 0:
            continue
        parts = [f"trail={int(row['exit_trail'])}"]
        parts.append(f"trend={int(row['exit_trend'])}")
        if row["exit_and_gate"] > 0:
            parts.append(f"AND={int(row['exit_and_gate'])}")
        if row["exit_rangepos"] > 0:
            parts.append(f"rp={int(row['exit_rangepos'])}")
        if row["exit_trendq"] > 0:
            parts.append(f"tq={int(row['exit_trendq'])}")
        print(f"  {row['config']:30s}  {', '.join(parts)}")

    # ── Heatmap (Sharpe delta) ────────────────────────────────────────
    print("\n" + "=" * 80)
    print("HEATMAP: d_sharpe (AND gate, rows=rp, cols=tq)")
    print("=" * 80)
    hm = and_rows.pivot_table(index="rp_threshold", columns="tq_threshold", values="d_sharpe")
    print(hm.to_string(float_format="{:+.4f}".format))

    print("\nHEATMAP: d_mdd (AND gate, rows=rp, cols=tq)")
    hm2 = and_rows.pivot_table(index="rp_threshold", columns="tq_threshold", values="d_mdd")
    print(hm2.to_string(float_format="{:+.2f}".format))


if __name__ == "__main__":
    main()
