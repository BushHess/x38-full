#!/usr/bin/env python3
"""Exp 28: Rangepos Velocity Exit.

E5-ema21D1 with rangepos RATE OF CHANGE (velocity) as exit signal.
Tests whether delta_rp = rangepos_84[i] - rangepos_84[i-N] provides
information beyond level-based thresholds (exp12).

Three parts:
  Part A — Velocity-only exit: delta_rp_N < velocity_threshold
  Part B — Level + Velocity AND: rangepos < level_thr AND delta_rp < vel_thr
  Part C — Velocity + trendq AND: delta_rp < vel_thr AND trendq < tq_thr

Entry logic UNCHANGED throughout.

Usage:
    python -m research.x39.experiments.exp28_rangepos_velocity_exit
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

# ── Part A sweep ──────────────────────────────────────────────────────────
VELOCITY_WINDOWS = [6, 12, 24]
VELOCITY_THRESHOLDS = [-0.40, -0.30, -0.20, -0.10, 0.00]

# ── Part B sweep ──────────────────────────────────────────────────────────
LEVEL_THRESHOLDS = [0.20, 0.25, 0.30]
PART_B_VEL_THRESHOLDS = [-0.30, -0.20, -0.10]

# ── Part C sweep ──────────────────────────────────────────────────────────
PART_C_VEL_THRESHOLDS = [-0.30, -0.20, -0.10]
TQ_THRESHOLDS = [-0.20, -0.10, 0.00]


def compute_delta_rp(rangepos: np.ndarray, window: int) -> np.ndarray:
    """Compute rangepos velocity: delta_rp[i] = rangepos[i] - rangepos[i-window]."""
    delta = np.full_like(rangepos, np.nan)
    for i in range(window, len(rangepos)):
        if np.isfinite(rangepos[i]) and np.isfinite(rangepos[i - window]):
            delta[i] = rangepos[i] - rangepos[i - window]
    return delta


def run_backtest(
    feat: pd.DataFrame,
    *,
    mode: str = "baseline",
    vel_window: int = 12,
    vel_threshold: float | None = None,
    level_threshold: float | None = None,
    tq_threshold: float | None = None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional velocity-based exit.

    Modes:
      "baseline"  — no supplementary exit
      "vel_only"  — exit when delta_rp < vel_threshold
      "level_vel" — exit when rangepos < level_threshold AND delta_rp < vel_threshold
      "vel_tq"    — exit when delta_rp < vel_threshold AND trendq < tq_threshold
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

    delta_rp = compute_delta_rp(rangepos, vel_window)

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "velocity": 0}
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
            elif mode == "vel_only" and vel_threshold is not None:
                if np.isfinite(delta_rp[i]) and delta_rp[i] < vel_threshold:
                    exit_reason = "velocity"
            elif mode == "level_vel" and vel_threshold is not None and level_threshold is not None:
                rp_low = np.isfinite(rangepos[i]) and rangepos[i] < level_threshold
                vel_neg = np.isfinite(delta_rp[i]) and delta_rp[i] < vel_threshold
                if rp_low and vel_neg:
                    exit_reason = "velocity"
            elif mode == "vel_tq" and vel_threshold is not None and tq_threshold is not None:
                vel_neg = np.isfinite(delta_rp[i]) and delta_rp[i] < vel_threshold
                tq_low = np.isfinite(trendq[i]) and trendq[i] < tq_threshold
                if vel_neg and tq_low:
                    exit_reason = "velocity"

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

    # ── Config label ──────────────────────────────────────────────────
    if mode == "baseline":
        config = "baseline"
    elif mode == "vel_only":
        config = f"A_N={vel_window}_v={vel_threshold}"
    elif mode == "level_vel":
        config = f"B_N={vel_window}_L={level_threshold}_v={vel_threshold}"
    elif mode == "vel_tq":
        config = f"C_N={vel_window}_v={vel_threshold}_tq={tq_threshold}"
    else:
        config = mode

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()

    if len(eq) < 2 or len(trades) == 0:
        return {
            "config": config, "part": mode,
            "vel_window": vel_window, "vel_threshold": vel_threshold,
            "level_threshold": level_threshold, "tq_threshold": tq_threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_velocity": 0,
            "vel_selectivity": np.nan,
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

    # Selectivity: % of velocity exits on losing trades
    vel_trades = tdf[tdf["exit_reason"] == "velocity"]
    vel_selectivity = np.nan
    if len(vel_trades) > 0:
        vel_selectivity = round((vel_trades["win"] == 0).sum() / len(vel_trades) * 100, 1)

    return {
        "config": config,
        "part": mode,
        "vel_window": vel_window,
        "vel_threshold": vel_threshold,
        "level_threshold": level_threshold,
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
        "exit_velocity": exit_counts["velocity"],
        "vel_selectivity": vel_selectivity,
    }


def print_row(r: dict) -> None:
    """Print summary for a single backtest result."""
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
    print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, "
          f"velocity={r['exit_velocity']}", end="")
    if np.isfinite(r["vel_selectivity"] or np.nan):
        print(f", selectivity={r['vel_selectivity']}%", end="")
    print()


def verdict_check(df: pd.DataFrame, base: pd.Series, label: str) -> pd.DataFrame:
    """Check for improvements and print verdict for a part."""
    variants = df[df["config"] != "baseline"]
    improvements = variants[(variants["d_sharpe"] > 0) & (variants["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(f"  {label} PASS: {best['config']} improves both Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp)")
        print(f"    Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
              f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}, "
              f"velocity_exits={int(best['exit_velocity'])}, "
              f"selectivity={best['vel_selectivity']}%")
    else:
        sharpe_up = variants[variants["d_sharpe"] > 0]
        mdd_down = variants[variants["d_mdd"] < 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(f"  {label} MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp")
        elif not mdd_down.empty:
            best = mdd_down.loc[mdd_down["d_mdd"].idxmin()]
            print(f"  {label} MIXED: {best['config']} improves MDD ({best['d_mdd']:+.2f} pp) "
                  f"but Sharpe changes {best['d_sharpe']:+.4f}")
        else:
            print(f"  {label} FAIL: No config improves Sharpe or MDD over baseline.")

    return improvements


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 28: Rangepos Velocity Exit")
    print(f"  Part A: velocity-only ({len(VELOCITY_WINDOWS)}×{len(VELOCITY_THRESHOLDS)} = "
          f"{len(VELOCITY_WINDOWS) * len(VELOCITY_THRESHOLDS)} configs)")
    print(f"  Part B: level+velocity AND ({len(LEVEL_THRESHOLDS)}×{len(PART_B_VEL_THRESHOLDS)} = "
          f"{len(LEVEL_THRESHOLDS) * len(PART_B_VEL_THRESHOLDS)} configs)")
    print(f"  Part C: velocity+trendq AND ({len(PART_C_VEL_THRESHOLDS)}×{len(TQ_THRESHOLDS)} = "
          f"{len(PART_C_VEL_THRESHOLDS) * len(TQ_THRESHOLDS)} configs)")
    print(f"  trail_mult: {TRAIL_MULT}, cost: {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    all_results: list[dict] = []

    # ═══════════════════════════════════════════════════════════════════
    # BASELINE
    # ═══════════════════════════════════════════════════════════════════
    print("\n[0] Baseline (no supplementary exit)...")
    base_r = run_backtest(feat, mode="baseline", warmup_bar=warmup_bar)
    all_results.append(base_r)
    print_row(base_r)

    # ═══════════════════════════════════════════════════════════════════
    # PART A — Velocity-only exit
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("PART A: Velocity-only exit (delta_rp_N < threshold)")
    print("=" * 80)

    part_a_results: list[dict] = [base_r]
    run_num = 1
    total_a = len(VELOCITY_WINDOWS) * len(VELOCITY_THRESHOLDS)
    for win in VELOCITY_WINDOWS:
        for vthr in VELOCITY_THRESHOLDS:
            print(f"\n  [{run_num}/{total_a}] N={win}, vel_thr={vthr}...")
            r = run_backtest(
                feat, mode="vel_only",
                vel_window=win, vel_threshold=vthr,
                warmup_bar=warmup_bar,
            )
            part_a_results.append(r)
            all_results.append(r)
            print_row(r)
            run_num += 1

    # Part A verdict
    df_a = pd.DataFrame(part_a_results)
    df_a["d_sharpe"] = df_a["sharpe"] - base_r["sharpe"]
    df_a["d_cagr"] = df_a["cagr_pct"] - base_r["cagr_pct"]
    df_a["d_mdd"] = df_a["mdd_pct"] - base_r["mdd_pct"]

    print("\n" + "-" * 60)
    print("Part A Results:")
    print(df_a[df_a["config"] != "baseline"].to_string(index=False))

    print("\nPart A Verdict:")
    a_improvements = verdict_check(df_a, df_a.iloc[0], "Part A")

    # Window sensitivity analysis
    print("\n" + "-" * 60)
    print("Window sensitivity (best Sharpe per N):")
    for win in VELOCITY_WINDOWS:
        win_rows = df_a[df_a["vel_window"] == win]
        win_rows = win_rows[win_rows["config"] != "baseline"]
        if len(win_rows) > 0:
            best = win_rows.loc[win_rows["sharpe"].idxmax()]
            print(f"  N={win:2d}: best Sharpe={best['sharpe']:.4f} "
                  f"(d={best['d_sharpe']:+.4f}) at vel_thr={best['vel_threshold']}")

    # Determine best N for Parts B and C
    a_variants = df_a[df_a["config"] != "baseline"]
    if not a_variants.empty:
        best_a = a_variants.loc[a_variants["sharpe"].idxmax()]
        best_n = int(best_a["vel_window"])
    else:
        best_n = 12  # fallback per spec

    # Check if Part A is ALL FAIL — skip B+C per spec
    any_sharpe_up = (a_variants["d_sharpe"] > 0).any()
    any_mdd_down = (a_variants["d_mdd"] < 0).any()
    part_a_total_fail = not any_sharpe_up and not any_mdd_down

    if part_a_total_fail:
        print("\n*** Part A ALL FAIL: no config improves Sharpe or MDD. ***")
        print("*** Skipping Parts B and C per spec. ***")
    else:
        print(f"\nUsing N={best_n} for Parts B and C (best from Part A).")

    # ═══════════════════════════════════════════════════════════════════
    # PART B — Level + Velocity AND gate
    # ═══════════════════════════════════════════════════════════════════
    if not part_a_total_fail:
        print("\n" + "=" * 80)
        print(f"PART B: Level + Velocity AND gate (N={best_n})")
        print("  exit when rangepos_84 < L AND delta_rp < V")
        print("=" * 80)

        part_b_results: list[dict] = [base_r]
        run_num = 1
        total_b = len(LEVEL_THRESHOLDS) * len(PART_B_VEL_THRESHOLDS)
        for lthr in LEVEL_THRESHOLDS:
            for vthr in PART_B_VEL_THRESHOLDS:
                print(f"\n  [{run_num}/{total_b}] L={lthr}, vel_thr={vthr}...")
                r = run_backtest(
                    feat, mode="level_vel",
                    vel_window=best_n, vel_threshold=vthr,
                    level_threshold=lthr,
                    warmup_bar=warmup_bar,
                )
                part_b_results.append(r)
                all_results.append(r)
                print_row(r)
                run_num += 1

        df_b = pd.DataFrame(part_b_results)
        df_b["d_sharpe"] = df_b["sharpe"] - base_r["sharpe"]
        df_b["d_cagr"] = df_b["cagr_pct"] - base_r["cagr_pct"]
        df_b["d_mdd"] = df_b["mdd_pct"] - base_r["mdd_pct"]

        print("\n" + "-" * 60)
        print("Part B Results:")
        print(df_b[df_b["config"] != "baseline"].to_string(index=False))

        print("\nPart B Verdict:")
        b_improvements = verdict_check(df_b, df_b.iloc[0], "Part B")

    # ═══════════════════════════════════════════════════════════════════
    # PART C — Velocity + trendq AND gate
    # ═══════════════════════════════════════════════════════════════════
    if not part_a_total_fail:
        print("\n" + "=" * 80)
        print(f"PART C: Velocity + trendq AND gate (N={best_n})")
        print("  exit when delta_rp < V AND trendq_84 < TQ")
        print("=" * 80)

        part_c_results: list[dict] = [base_r]
        run_num = 1
        total_c = len(PART_C_VEL_THRESHOLDS) * len(TQ_THRESHOLDS)
        for vthr in PART_C_VEL_THRESHOLDS:
            for tqthr in TQ_THRESHOLDS:
                print(f"\n  [{run_num}/{total_c}] vel_thr={vthr}, tq={tqthr}...")
                r = run_backtest(
                    feat, mode="vel_tq",
                    vel_window=best_n, vel_threshold=vthr,
                    tq_threshold=tqthr,
                    warmup_bar=warmup_bar,
                )
                part_c_results.append(r)
                all_results.append(r)
                print_row(r)
                run_num += 1

        df_c = pd.DataFrame(part_c_results)
        df_c["d_sharpe"] = df_c["sharpe"] - base_r["sharpe"]
        df_c["d_cagr"] = df_c["cagr_pct"] - base_r["cagr_pct"]
        df_c["d_mdd"] = df_c["mdd_pct"] - base_r["mdd_pct"]

        print("\n" + "-" * 60)
        print("Part C Results:")
        print(df_c[df_c["config"] != "baseline"].to_string(index=False))

        print("\nPart C Verdict:")
        c_improvements = verdict_check(df_c, df_c.iloc[0], "Part C")

    # ═══════════════════════════════════════════════════════════════════
    # COMBINED RESULTS
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("COMBINED RESULTS")
    print("=" * 80)

    # Deduplicate baseline (only keep first)
    seen_baseline = False
    unique_results: list[dict] = []
    for r in all_results:
        if r["config"] == "baseline":
            if seen_baseline:
                continue
            seen_baseline = True
        unique_results.append(r)

    df_all = pd.DataFrame(unique_results)
    df_all["d_sharpe"] = df_all["sharpe"] - base_r["sharpe"]
    df_all["d_cagr"] = df_all["cagr_pct"] - base_r["cagr_pct"]
    df_all["d_mdd"] = df_all["mdd_pct"] - base_r["mdd_pct"]

    print(df_all.to_string(index=False))

    out_path = RESULTS_DIR / "exp28_results.csv"
    df_all.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Exit timing analysis ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("EXIT TIMING: velocity exits vs trail stop timing")
    print("  Positive = velocity exited BEFORE trail would have (good for slow deterioration)")
    print("  Negative = trail would have caught it first (velocity redundant)")
    print("=" * 80)

    # For best Part A config, analyze velocity exits vs baseline trail timing
    if not part_a_total_fail:
        a_variants = df_a[df_a["config"] != "baseline"]
        best_a_row = a_variants.loc[a_variants["sharpe"].idxmax()]
        best_n_timing = int(best_a_row["vel_window"])
        best_vthr_timing = best_a_row["vel_threshold"]

        # Re-run to get detailed trade-level data
        r_base_detail = run_backtest(feat, mode="baseline", warmup_bar=warmup_bar)
        r_best_detail = run_backtest(
            feat, mode="vel_only",
            vel_window=best_n_timing, vel_threshold=best_vthr_timing,
            warmup_bar=warmup_bar,
        )

        # Compare exit bars for trades that match by entry
        base_trades = {t["entry_bar"]: t for t in [
            {"entry_bar": 0, "exit_bar": 0}  # placeholder
        ]}
        # Actually we need full trade data, use the stored results
        print(f"  Best Part A: N={best_n_timing}, vel_thr={best_vthr_timing}")
        print(f"  Baseline: {r_base_detail['trades']} trades, "
              f"Best A: {r_best_detail['trades']} trades")
        vel_exits = r_best_detail["exit_velocity"]
        total_exits = r_best_detail["exit_trail"] + r_best_detail["exit_trend"] + vel_exits
        if total_exits > 0 and vel_exits > 0:
            print(f"  Velocity exits: {vel_exits}/{total_exits} "
                  f"({vel_exits / total_exits * 100:.0f}%)")
            print(f"  Selectivity: {r_best_detail['vel_selectivity']}% on losers")
        else:
            print("  No velocity exits triggered.")

    # ── Comparison with exp12 (level-based) ───────────────────────────
    print("\n" + "=" * 80)
    print("COMPARISON: velocity (exp28) vs level (exp12 rangepos<0.25)")
    print("=" * 80)
    exp12_path = RESULTS_DIR / "exp12_results.csv"
    if exp12_path.exists():
        exp12 = pd.read_csv(exp12_path)
        exp12_best = exp12[exp12["config"] == "thr=0.25"]
        if len(exp12_best) > 0:
            e12 = exp12_best.iloc[0]
            print(f"  Exp12 (level rp<0.25): Sharpe={e12['sharpe']:.4f}, "
                  f"MDD={e12['mdd_pct']:.2f}%, trades={int(e12['trades'])}")
        all_a = df_a[df_a["config"] != "baseline"]
        if not all_a.empty:
            best_a_cmp = all_a.loc[all_a["sharpe"].idxmax()]
            print(f"  Exp28 best A:          Sharpe={best_a_cmp['sharpe']:.4f}, "
                  f"MDD={best_a_cmp['mdd_pct']:.2f}%, trades={int(best_a_cmp['trades'])}")
            if len(exp12_best) > 0:
                vel_better_sh = best_a_cmp["sharpe"] > e12["sharpe"]
                vel_better_mdd = best_a_cmp["mdd_pct"] < e12["mdd_pct"]
                print(f"  Velocity {'BETTER' if vel_better_sh else 'WORSE'} on Sharpe, "
                      f"{'BETTER' if vel_better_mdd else 'WORSE'} on MDD vs level-only")
    else:
        print("  exp12_results.csv not found — skipping comparison.")

    # ── Comparison with exp22 (level+trendq) ──────────────────────────
    if not part_a_total_fail:
        print("\n" + "-" * 60)
        print("COMPARISON: velocity+trendq (exp28C) vs level+trendq (exp22)")
        exp22_path = RESULTS_DIR / "exp22_results.csv"
        if exp22_path.exists():
            exp22 = pd.read_csv(exp22_path)
            and_rows = exp22[exp22["config"].str.startswith("AND_")]
            if not and_rows.empty:
                e22_best = and_rows.loc[and_rows["sharpe"].idxmax()]
                print(f"  Exp22 best AND:  Sharpe={e22_best['sharpe']:.4f}, "
                      f"MDD={e22_best['mdd_pct']:.2f}%")
            c_variants = df_c[df_c["config"] != "baseline"]
            if not c_variants.empty:
                best_c_cmp = c_variants.loc[c_variants["sharpe"].idxmax()]
                print(f"  Exp28 best C:    Sharpe={best_c_cmp['sharpe']:.4f}, "
                      f"MDD={best_c_cmp['mdd_pct']:.2f}%")
        else:
            print("  exp22_results.csv not found — skipping comparison.")

    # ── Overall verdict ───────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("OVERALL VERDICT")
    print("=" * 80)

    all_variants = df_all[df_all["config"] != "baseline"]
    all_improvements = all_variants[(all_variants["d_sharpe"] > 0) & (all_variants["d_mdd"] < 0)]

    if not all_improvements.empty:
        best_overall = all_improvements.loc[all_improvements["d_sharpe"].idxmax()]
        print(f"PASS: {best_overall['config']} improves both Sharpe ({best_overall['d_sharpe']:+.4f}) "
              f"and MDD ({best_overall['d_mdd']:+.2f} pp)")
        print(f"  Sharpe {best_overall['sharpe']}, CAGR {best_overall['cagr_pct']}%, "
              f"MDD {best_overall['mdd_pct']}%, trades {int(best_overall['trades'])}")
        print(f"  velocity exits: {int(best_overall['exit_velocity'])}, "
              f"selectivity: {best_overall['vel_selectivity']}%")
    elif part_a_total_fail:
        print("FAIL: Rangepos velocity provides NO useful exit information.")
        print("  All Part A configs fail — velocity is NOT a useful signal for exits.")
    else:
        any_pass = not all_improvements.empty
        any_mixed_sh = (all_variants["d_sharpe"] > 0).any()
        any_mixed_mdd = (all_variants["d_mdd"] < 0).any()
        if any_mixed_sh:
            best_sh = all_variants.loc[all_variants["d_sharpe"].idxmax()]
            print(f"MIXED: Best Sharpe improvement: {best_sh['config']} "
                  f"({best_sh['d_sharpe']:+.4f}) but MDD {best_sh['d_mdd']:+.2f} pp")
        elif any_mixed_mdd:
            best_mdd = all_variants.loc[all_variants["d_mdd"].idxmin()]
            print(f"MIXED: Best MDD improvement: {best_mdd['config']} "
                  f"({best_mdd['d_mdd']:+.2f} pp) but Sharpe {best_mdd['d_sharpe']:+.4f}")
        else:
            print("FAIL: No velocity-based exit config improves Sharpe or MDD.")

    # ── Exit reason breakdown ─────────────────────────────────────────
    print("\n" + "-" * 60)
    print("Exit reason breakdown (all configs):")
    for _, row in df_all.iterrows():
        total_exits = row["exit_trail"] + row["exit_trend"] + row["exit_velocity"]
        if total_exits == 0:
            continue
        parts = [f"trail={int(row['exit_trail'])}"]
        parts.append(f"trend={int(row['exit_trend'])}")
        if row["exit_velocity"] > 0:
            parts.append(f"vel={int(row['exit_velocity'])} "
                         f"(sel={row['vel_selectivity']}%)")
        print(f"  {row['config']:35s}  {', '.join(parts)}")


if __name__ == "__main__":
    main()
