#!/usr/bin/env python3
"""Exp 27: Multi-Lookback Rangepos Consensus.

Instead of choosing one fragile lookback (L=84), aggregate rangepos across
three lookbacks (42, 84, 168) into a consensus signal. Three aggregation
methods: MIN, MEAN, WEIGHTED (0.25/0.50/0.25).

Part A — Standalone exit: rp_agg < threshold (3 aggs × 5 thresholds + 5 single L=84)
Part B — AND gate: rp_agg < rp_thr AND trendq_84 < -0.10 (3 aggs × 3 thresholds + 3 single L=84)
Total: 32 configs + 1 baseline = 33 runs.

Entry logic UNCHANGED (E5-ema21D1).

Usage:
    python -m research.x39.experiments.exp27_multi_lookback_rangepos
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

# Part A thresholds
STANDALONE_THRESHOLDS = [0.15, 0.20, 0.25, 0.30, 0.35]
# Part B thresholds
AND_RP_THRESHOLDS = [0.15, 0.20, 0.25]
AND_TQ_THRESHOLD = -0.10  # fixed from exp22 optimum

AGGREGATIONS = ["min", "mean", "weighted"]


def add_rangepos_42(feat: pd.DataFrame) -> None:
    """Compute rangepos_42 (not in explore.py) and add in-place."""
    c = feat["close"].values
    h = feat["high"].values
    lo = feat["low"].values
    roll_hi = pd.Series(h).rolling(42, min_periods=42).max().values
    roll_lo = pd.Series(lo).rolling(42, min_periods=42).min().values
    denom = roll_hi - roll_lo
    denom_safe = np.where(denom > 1e-10, denom, np.nan)
    feat["rangepos_42"] = (c - roll_lo) / denom_safe


def compute_aggregations(feat: pd.DataFrame) -> None:
    """Compute rp_min, rp_mean, rp_wt from three lookback rangepos. In-place."""
    rp42 = feat["rangepos_42"].values
    rp84 = feat["rangepos_84"].values
    rp168 = feat["rangepos_168"].values

    # Stack for vectorized ops
    stacked = np.stack([rp42, rp84, rp168], axis=0)  # (3, n)

    feat["rp_min"] = np.nanmin(stacked, axis=0)
    feat["rp_mean"] = np.nanmean(stacked, axis=0)
    feat["rp_wt"] = 0.25 * rp42 + 0.50 * rp84 + 0.25 * rp168

    # NaN if any lookback is NaN (skip during warmup, spec says "use skip")
    any_nan = np.any(np.isnan(stacked), axis=0)
    for col in ["rp_min", "rp_mean", "rp_wt"]:
        arr = feat[col].values.copy()
        arr[any_nan] = np.nan
        feat[col] = arr


def run_backtest(
    feat: pd.DataFrame,
    *,
    agg: str | None,
    rp_threshold: float | None,
    tq_threshold: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional multi-lookback / single-L exit.

    Modes:
    - agg=None, rp/tq=None: baseline
    - agg=None, rp set, tq=None: single L=84 standalone
    - agg=None, rp set, tq set: single L=84 AND gate
    - agg set, rp set, tq=None: multi-lookback standalone
    - agg set, rp set, tq set: multi-lookback AND gate
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    trendq = feat["trendq_84"].values
    n = len(c)

    # Select rangepos array
    if agg is not None:
        rp_col = f"rp_{agg}" if agg != "weighted" else "rp_wt"
        rangepos = feat[rp_col].values
    else:
        rangepos = feat["rangepos_84"].values

    # Also get single L=84 for overlap tracking
    rp84_single = feat["rangepos_84"].values

    use_rp = rp_threshold is not None
    use_and = use_rp and tq_threshold is not None
    use_standalone = use_rp and tq_threshold is None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "supp": 0}
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    # Overlap tracking: at each supp exit, would single L=84 also have fired?
    supp_exit_bars: list[int] = []
    single84_also_fired: list[bool] = []

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
            elif use_standalone:
                if np.isfinite(rangepos[i]) and rangepos[i] < rp_threshold:
                    exit_reason = "supp"
                    supp_exit_bars.append(i)
                    # Would single L=84 also fire at same threshold?
                    single84_also_fired.append(
                        np.isfinite(rp84_single[i])
                        and rp84_single[i] < rp_threshold
                    )
            elif use_and:
                rp_ok = np.isfinite(rangepos[i]) and rangepos[i] < rp_threshold
                tq_ok = np.isfinite(trendq[i]) and trendq[i] < tq_threshold
                if rp_ok and tq_ok:
                    exit_reason = "supp"
                    supp_exit_bars.append(i)
                    # Would single L=84 AND gate also fire?
                    single84_also_fired.append(
                        np.isfinite(rp84_single[i])
                        and rp84_single[i] < rp_threshold
                        and np.isfinite(trendq[i])
                        and trendq[i] < tq_threshold
                    )

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

    # ── Config label ─────────────────────────────────────────────────
    if not use_rp:
        config = "baseline"
    elif agg is None and not use_and:
        config = f"L84_thr={rp_threshold}"
    elif agg is None and use_and:
        config = f"L84_AND_rp={rp_threshold}"
    elif use_and:
        config = f"{agg}_AND_rp={rp_threshold}"
    else:
        config = f"{agg}_thr={rp_threshold}"

    part = "B" if use_and else ("A" if use_standalone else "-")

    # ── Compute metrics ──────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()

    if len(eq) < 2 or len(trades) == 0:
        return {
            "part": part, "config": config,
            "aggregation": agg, "rp_threshold": rp_threshold,
            "tq_threshold": tq_threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_supp": 0,
            "selectivity": np.nan,
            "_supp_exit_bars": [], "_single84_also_fired": [],
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
    losses = tdf[tdf["win"] == 0]

    # Selectivity: % of supp exits on losing trades
    supp_trades = tdf[tdf["exit_reason"] == "supp"]
    selectivity = np.nan
    if len(supp_trades) > 0:
        selectivity = round((supp_trades["win"] == 0).sum() / len(supp_trades) * 100, 1)

    return {
        "part": part,
        "config": config,
        "aggregation": agg,
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
        "exit_supp": exit_counts["supp"],
        "selectivity": selectivity,
        "_supp_exit_bars": supp_exit_bars,
        "_single84_also_fired": single84_also_fired,
    }


def robustness_analysis(df: pd.DataFrame) -> None:
    """Compare Sharpe range across thresholds for each aggregation method."""
    print("\n" + "=" * 80)
    print("ROBUSTNESS ANALYSIS")
    print("  Sharpe range across thresholds [0.15-0.35]. Lower = more robust.")
    print("  Target: range < 0.05 (plateau).")
    print("=" * 80)

    part_a = df[df["part"] == "A"]
    if part_a.empty:
        return

    # Single L=84
    l84 = part_a[part_a["aggregation"].isna()]
    if not l84.empty:
        sr = l84["sharpe"].max() - l84["sharpe"].min()
        print(f"  {'L=84 (single)':20s}  range={sr:.4f}  "
              f"[{l84['sharpe'].min():.4f} - {l84['sharpe'].max():.4f}]")

    # Each aggregation
    for agg_name in AGGREGATIONS:
        subset = part_a[part_a["aggregation"] == agg_name]
        if subset.empty:
            continue
        sr = subset["sharpe"].max() - subset["sharpe"].min()
        plateau = "PLATEAU" if sr < 0.05 else ""
        print(f"  {agg_name:20s}  range={sr:.4f}  "
              f"[{subset['sharpe'].min():.4f} - {subset['sharpe'].max():.4f}]  {plateau}")


def overlap_analysis(results: list[dict]) -> None:
    """For each multi-lookback config, check overlap with single L=84."""
    print("\n" + "=" * 80)
    print("OVERLAP ANALYSIS")
    print("  At each multi-lookback supp exit: would single L=84 also have fired?")
    print("  Low overlap = genuine value added by multi-lookback.")
    print("=" * 80)

    for r in results:
        if r["aggregation"] is None or r["exit_supp"] == 0:
            continue
        bars = r["_supp_exit_bars"]
        fired = r["_single84_also_fired"]
        n_exits = len(bars)
        n_overlap = sum(fired)
        overlap_pct = n_overlap / n_exits * 100 if n_exits > 0 else 0.0
        unique = n_exits - n_overlap
        print(f"  {r['config']:30s}  {n_exits:3d} exits | "
              f"L84_also={n_overlap} ({overlap_pct:.0f}%), unique={unique}")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    total_runs = 1 + 20 + 12  # baseline + Part A + Part B
    print("=" * 80)
    print("EXP 27: Multi-Lookback Rangepos Consensus")
    print(f"  Part A: 3 aggs × 5 thresholds + 5 single L=84 = 20 configs")
    print(f"  Part B: 3 aggs × 3 thresholds + 3 single L=84 = 12 configs")
    print(f"  Total: {total_runs} runs (32 + baseline)")
    print(f"  trail_mult: {TRAIL_MULT}, cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Compute rangepos_42 and aggregations
    print("Computing rangepos_42 and aggregations...")
    add_rangepos_42(feat)
    compute_aggregations(feat)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    results: list[dict] = []
    run_num = 1

    # ── 1. Baseline ───────────────────────────────────────────────────
    print(f"\n[{run_num}/{total_runs}] Baseline (no supplementary exit)...")
    r = run_backtest(feat, agg=None, rp_threshold=None, tq_threshold=None,
                     warmup_bar=warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")
    run_num += 1

    # ══════════════════════════════════════════════════════════════════
    # PART A: Standalone exit
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "-" * 60)
    print("PART A: Standalone exit (rp_agg < threshold)")
    print("-" * 60)

    # Single L=84 at each threshold (exp12 reproduction)
    for thr in STANDALONE_THRESHOLDS:
        print(f"\n[{run_num}/{total_runs}] L84 standalone thr={thr}...")
        r = run_backtest(feat, agg=None, rp_threshold=thr, tq_threshold=None,
                         warmup_bar=warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, supp_exits={r['exit_supp']}")
        run_num += 1

    # Multi-lookback aggregations
    for agg_name in AGGREGATIONS:
        for thr in STANDALONE_THRESHOLDS:
            print(f"\n[{run_num}/{total_runs}] {agg_name} standalone thr={thr}...")
            r = run_backtest(feat, agg=agg_name, rp_threshold=thr, tq_threshold=None,
                             warmup_bar=warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, supp_exits={r['exit_supp']}")
            run_num += 1

    # ══════════════════════════════════════════════════════════════════
    # PART B: AND gate (rp_agg < rp_thr AND trendq_84 < -0.10)
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "-" * 60)
    print(f"PART B: AND gate (rp_agg < rp_thr AND trendq_84 < {AND_TQ_THRESHOLD})")
    print("-" * 60)

    # Single L=84 AND gate
    for thr in AND_RP_THRESHOLDS:
        print(f"\n[{run_num}/{total_runs}] L84 AND rp={thr}...")
        r = run_backtest(feat, agg=None, rp_threshold=thr, tq_threshold=AND_TQ_THRESHOLD,
                         warmup_bar=warmup_bar)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, supp_exits={r['exit_supp']}, "
              f"selectivity={r['selectivity']}%")
        run_num += 1

    # Multi-lookback AND gate
    for agg_name in AGGREGATIONS:
        for thr in AND_RP_THRESHOLDS:
            print(f"\n[{run_num}/{total_runs}] {agg_name} AND rp={thr}...")
            r = run_backtest(feat, agg=agg_name, rp_threshold=thr,
                             tq_threshold=AND_TQ_THRESHOLD, warmup_bar=warmup_bar)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, supp_exits={r['exit_supp']}, "
                  f"selectivity={r['selectivity']}%")
            run_num += 1

    # ── Results table ─────────────────────────────────────────────────
    clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
    df = pd.DataFrame(clean)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS — PART A (Standalone)")
    print("=" * 80)
    part_a = df[(df["part"] == "A") | (df["part"] == "-")]
    print(part_a.to_string(index=False))

    print("\n" + "=" * 80)
    print("RESULTS — PART B (AND gate)")
    print("=" * 80)
    part_b = df[df["part"] == "B"]
    print(part_b.to_string(index=False))

    out_path = RESULTS_DIR / "exp27_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Key analyses ─────────────────────────────────────────────────

    # 1. Robustness comparison
    robustness_analysis(df)

    # 2. Overlap analysis
    overlap_analysis(results)

    # 3. Exit count profile
    print("\n" + "=" * 80)
    print("EXIT COUNT PROFILE")
    print("=" * 80)
    variants = df[df["config"] != "baseline"]
    for _, row in variants.iterrows():
        total_exits = row["exit_trail"] + row["exit_trend"] + row["exit_supp"]
        if total_exits == 0:
            continue
        print(f"  {row['config']:30s}  trail={int(row['exit_trail']):3d} "
              f"trend={int(row['exit_trend']):3d} supp={int(row['exit_supp']):3d} "
              f"(selectivity={row['selectivity']}%)")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Part A verdict
    print("\n--- Part A: Standalone ---")
    part_a_variants = df[(df["part"] == "A")]
    if not part_a_variants.empty:
        imp_a = part_a_variants[(part_a_variants["d_sharpe"] > 0) & (part_a_variants["d_mdd"] < 0)]
        if not imp_a.empty:
            best_a = imp_a.loc[imp_a["d_sharpe"].idxmax()]
            # Compare with single L=84 best
            l84_a = part_a_variants[part_a_variants["aggregation"].isna()]
            l84_best_sh = l84_a.loc[l84_a["d_sharpe"].idxmax()] if not l84_a.empty else None
            print(f"PASS: {best_a['config']} d_sharpe={best_a['d_sharpe']:+.4f}, "
                  f"d_mdd={best_a['d_mdd']:+.2f} pp")
            if l84_best_sh is not None:
                print(f"  vs L84 best: {l84_best_sh['config']} d_sharpe={l84_best_sh['d_sharpe']:+.4f}, "
                      f"d_mdd={l84_best_sh['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No Part A config improves both Sharpe and MDD.")

    # Part B verdict
    print("\n--- Part B: AND gate ---")
    part_b_only = df[df["part"] == "B"]
    if not part_b_only.empty:
        imp_b = part_b_only[(part_b_only["d_sharpe"] > 0) & (part_b_only["d_mdd"] < 0)]
        if not imp_b.empty:
            best_b = imp_b.loc[imp_b["d_sharpe"].idxmax()]
            l84_b = part_b_only[part_b_only["aggregation"].isna()]
            l84_best_b = l84_b.loc[l84_b["d_sharpe"].idxmax()] if not l84_b.empty else None
            print(f"PASS: {best_b['config']} d_sharpe={best_b['d_sharpe']:+.4f}, "
                  f"d_mdd={best_b['d_mdd']:+.2f} pp")
            if l84_best_b is not None:
                print(f"  vs L84 best: {l84_best_b['config']} d_sharpe={l84_best_b['d_sharpe']:+.4f}, "
                      f"d_mdd={l84_best_b['d_mdd']:+.2f} pp")
        else:
            print("FAIL: No Part B AND-gate config improves both Sharpe and MDD.")

    # Overall
    print("\n--- Overall ---")
    all_variants = df[df["config"] != "baseline"]
    all_imp = all_variants[(all_variants["d_sharpe"] > 0) & (all_variants["d_mdd"] < 0)]
    if not all_imp.empty:
        overall_best = all_imp.loc[all_imp["d_sharpe"].idxmax()]
        print(f"BEST OVERALL: {overall_best['config']}  "
              f"Sharpe={overall_best['sharpe']}, d_sharpe={overall_best['d_sharpe']:+.4f}, "
              f"MDD={overall_best['mdd_pct']}%, d_mdd={overall_best['d_mdd']:+.2f} pp, "
              f"trades={int(overall_best['trades'])}")

        # Does multi-lookback beat single L=84?
        multi_imp = all_imp[all_imp["aggregation"].notna()]
        l84_imp = all_imp[all_imp["aggregation"].isna()]
        if not multi_imp.empty and not l84_imp.empty:
            multi_best = multi_imp.loc[multi_imp["d_sharpe"].idxmax()]
            l84_best = l84_imp.loc[l84_imp["d_sharpe"].idxmax()]
            verdict = "BETTER" if multi_best["d_sharpe"] > l84_best["d_sharpe"] else "WORSE"
            print(f"\n  Multi-lookback {verdict} than single L=84 on Sharpe delta: "
                  f"{multi_best['d_sharpe']:+.4f} vs {l84_best['d_sharpe']:+.4f}")
        elif not multi_imp.empty:
            print("  Multi-lookback improves, single L=84 does not.")
        elif not l84_imp.empty:
            print("  Single L=84 improves, multi-lookback does not.")
    else:
        print("FAIL: No config improves both Sharpe and MDD over baseline.")


if __name__ == "__main__":
    main()
