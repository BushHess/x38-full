#!/usr/bin/env python3
"""Exp 19: Stacked Supplementary Exits.

E5-ema21D1 with rangepos_84 (exp12 proven) + a second selective exit.
Tests whether a second exit captures a DIFFERENT failure mode than rangepos.

Three variants:
  A — ret_168 momentum exit (below threshold)
  B — trendq_84 trend quality exit (below threshold)
  C — d1_rangevol84_rank365 vol regime exit (ABOVE threshold — high vol = bad)

Total: 15 stacked + 1 baseline + 1 rangepos-only = 17 runs.

Usage:
    python -m research.x39.experiments.exp19_stacked_exits
    # or from x39/:
    python experiments/exp19_stacked_exits.py
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

RP_THRESHOLD = 0.25  # Fixed from exp12 optimum

# Feature B sweep definitions
VARIANTS = [
    {
        "name": "ret_168",
        "col": "ret_168",
        "direction": "below",
        "thresholds": [-0.10, -0.05, 0.00, 0.05, 0.10],
    },
    {
        "name": "trendq_84",
        "col": "trendq_84",
        "direction": "below",
        "thresholds": [-0.40, -0.20, 0.00, 0.20, 0.40],
    },
    {
        "name": "d1_rangevol84_rank365",
        "col": "d1_rangevol84_rank365",
        "direction": "above",
        "thresholds": [0.70, 0.75, 0.80, 0.85, 0.90],
    },
]


def _fb_fires(value: float, threshold: float, direction: str) -> bool:
    """Check if feature B exit condition is met."""
    if not np.isfinite(value):
        return False
    if direction == "below":
        return value < threshold
    return value > threshold


def run_backtest(
    feat: pd.DataFrame,
    warmup_bar: int,
    *,
    rp_threshold: float | None = None,
    fb_col: str | None = None,
    fb_threshold: float | None = None,
    fb_direction: str = "below",
) -> dict:
    """Replay E5-ema21D1 with optional stacked exits. Returns summary dict."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    fb_arr = feat[fb_col].values if fb_col else None
    n = len(c)

    use_rp = rp_threshold is not None
    use_fb = fb_col is not None and fb_threshold is not None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "rangepos": 0, "feature_b": 0}
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000
    half_cost = (COST_BPS / 2) / 10_000

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
            continue

        if not in_pos:
            equity[i] = cash

            if ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
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
            elif use_rp and np.isfinite(rangepos[i]) and rangepos[i] < rp_threshold:
                exit_reason = "rangepos"
            elif use_fb and _fb_fires(fb_arr[i], fb_threshold, fb_direction):
                exit_reason = "feature_b"

            if exit_reason:
                cash = position_size * c[i] * (1 - half_cost)
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost

                # Overlap: at exit bar, would BOTH supplementary exits fire?
                rp_would = (use_rp and np.isfinite(rangepos[i])
                            and rangepos[i] < rp_threshold)
                fb_would = (use_fb
                            and _fb_fires(fb_arr[i], fb_threshold, fb_direction))

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
                    "rp_would_fire": rp_would,
                    "fb_would_fire": fb_would,
                })

                exit_counts[exit_reason] += 1
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    label = _config_label(rp_threshold, fb_col, fb_threshold)
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result(label)

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = (rets.mean() / rets.std() * np.sqrt(bars_per_year)
              if rets.std() > 0 else 0.0)

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

    # Overlap stats
    overlap_count = int((tdf["rp_would_fire"] & tdf["fb_would_fire"]).sum()) if use_rp and use_fb else 0
    rp_fire_count = int(tdf["rp_would_fire"].sum()) if use_rp else 0
    fb_fire_count = int(tdf["fb_would_fire"].sum()) if use_fb else 0

    return {
        "variant": label,
        "rp_threshold": rp_threshold,
        "fb_feature": fb_col,
        "fb_threshold": fb_threshold,
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
        "exit_rangepos": exit_counts["rangepos"],
        "exit_feature_b": exit_counts["feature_b"],
        "overlap_count": overlap_count,
        "rp_fire_count": rp_fire_count,
        "fb_fire_count": fb_fire_count,
    }


def _config_label(
    rp_thr: float | None,
    fb_col: str | None,
    fb_thr: float | None,
) -> str:
    if rp_thr is None and fb_col is None:
        return "baseline"
    if fb_col is None:
        return "rp_only"
    return f"rp+{fb_col}@{fb_thr}"


def _empty_result(label: str) -> dict:
    return {
        "variant": label,
        "rp_threshold": None, "fb_feature": None, "fb_threshold": None,
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
        "exit_trail": 0, "exit_trend": 0, "exit_rangepos": 0,
        "exit_feature_b": 0, "overlap_count": 0,
        "rp_fire_count": 0, "fb_fire_count": 0,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 19: Stacked Supplementary Exits")
    print(f"  rangepos_84 threshold: {RP_THRESHOLD} (fixed from exp12)")
    print(f"  trail_mult:            {TRAIL_MULT}")
    print(f"  cost:                  {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Warmup: first bar where d1_rangevol84_rank365 is valid (variant C needs it)
    d1_rank = feat["d1_rangevol84_rank365"].values
    valid_mask = np.isfinite(d1_rank)
    first_valid = int(np.argmax(valid_mask)) if valid_mask.any() else SLOW_PERIOD
    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"Warmup bar: {warmup_bar} (first valid d1_rangevol84_rank365)")

    results = []

    # ── 1) Baseline ───────────────────────────────────────────────────
    print("\n[1/17] Baseline (no supplementary exits)...")
    r = run_backtest(feat, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")

    # ── 2) Rangepos-only (exp12 reproduction) ─────────────────────────
    print(f"\n[2/17] Rangepos-only (threshold={RP_THRESHOLD})...")
    r = run_backtest(feat, warmup_bar, rp_threshold=RP_THRESHOLD)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")
    print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, "
          f"rp={r['exit_rangepos']}")

    # ── 3-17) Stacked variants ────────────────────────────────────────
    run_idx = 3
    for variant in VARIANTS:
        print(f"\n{'─' * 60}")
        print(f"Variant: {variant['name']} ({variant['direction']} threshold)")
        print(f"{'─' * 60}")

        for fb_thr in variant["thresholds"]:
            print(f"\n[{run_idx}/17] rp+{variant['name']}@{fb_thr}...")
            r = run_backtest(
                feat, warmup_bar,
                rp_threshold=RP_THRESHOLD,
                fb_col=variant["col"],
                fb_threshold=fb_thr,
                fb_direction=variant["direction"],
            )
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, "
                  f"MDD={r['mdd_pct']}%, trades={r['trades']}")
            print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, "
                  f"rp={r['exit_rangepos']}, fb={r['exit_feature_b']}")
            print(f"  overlap: {r['overlap_count']} trades "
                  f"(rp_fires={r['rp_fire_count']}, fb_fires={r['fb_fire_count']})")
            run_idx += 1

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base_sh = df.iloc[0]["sharpe"]
    base_cagr = df.iloc[0]["cagr_pct"]
    base_mdd = df.iloc[0]["mdd_pct"]
    rp_sh = df.iloc[1]["sharpe"]
    rp_cagr = df.iloc[1]["cagr_pct"]
    rp_mdd = df.iloc[1]["mdd_pct"]

    df["d_sharpe_vs_base"] = df["sharpe"] - base_sh
    df["d_cagr_vs_base"] = df["cagr_pct"] - base_cagr
    df["d_mdd_vs_base"] = df["mdd_pct"] - base_mdd
    df["d_sharpe_vs_rp"] = df["sharpe"] - rp_sh
    df["d_cagr_vs_rp"] = df["cagr_pct"] - rp_cagr
    df["d_mdd_vs_rp"] = df["mdd_pct"] - rp_mdd

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    show = [
        "variant", "sharpe", "cagr_pct", "mdd_pct", "trades", "win_rate",
        "exposure_pct", "d_sharpe_vs_base", "d_mdd_vs_base",
        "d_sharpe_vs_rp", "d_mdd_vs_rp",
        "exit_trail", "exit_trend", "exit_rangepos", "exit_feature_b",
        "overlap_count",
    ]
    print(df[show].to_string(index=False))

    out_path = RESULTS_DIR / "exp19_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Verdict per variant ───────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT (does stacking beat rangepos-only?)")
    print("=" * 80)

    stacked = df.iloc[2:]
    for variant in VARIANTS:
        vname = variant["name"]
        vrows = stacked[stacked["fb_feature"] == variant["col"]]
        if vrows.empty:
            continue

        improves = vrows[(vrows["d_sharpe_vs_rp"] > 0) & (vrows["d_mdd_vs_rp"] < 0)]
        if not improves.empty:
            best = improves.loc[improves["d_sharpe_vs_rp"].idxmax()]
            print(f"\n{vname}: PASS (vs rp_only)")
            print(f"  Best: fb_thr={best['fb_threshold']}")
            print(f"  dSharpe={best['d_sharpe_vs_rp']:+.4f}, "
                  f"dMDD={best['d_mdd_vs_rp']:+.2f} pp")
            print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
                  f"MDD {best['mdd_pct']}%")
            print(f"  fb_exits={int(best['exit_feature_b'])}, "
                  f"overlap={int(best['overlap_count'])}")
        else:
            sh_up = vrows[vrows["d_sharpe_vs_rp"] > 0]
            mdd_dn = vrows[vrows["d_mdd_vs_rp"] < 0]
            if not sh_up.empty:
                best = sh_up.loc[sh_up["d_sharpe_vs_rp"].idxmax()]
                print(f"\n{vname}: MIXED (Sharpe up, MDD worse vs rp_only)")
                print(f"  Best: fb_thr={best['fb_threshold']} "
                      f"dSh={best['d_sharpe_vs_rp']:+.4f}, "
                      f"dMDD={best['d_mdd_vs_rp']:+.2f}")
            elif not mdd_dn.empty:
                best = mdd_dn.loc[mdd_dn["d_mdd_vs_rp"].idxmin()]
                print(f"\n{vname}: MIXED (MDD down, Sharpe worse vs rp_only)")
                print(f"  Best: fb_thr={best['fb_threshold']} "
                      f"dSh={best['d_sharpe_vs_rp']:+.4f}, "
                      f"dMDD={best['d_mdd_vs_rp']:+.2f}")
            else:
                print(f"\n{vname}: FAIL (no improvement over rp_only)")

    # ── Overlap analysis ──────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("OVERLAP ANALYSIS (high overlap = redundant, low = complementary)")
    print("=" * 80)
    for _, row in stacked.iterrows():
        rp_f = int(row["rp_fire_count"])
        fb_f = int(row["fb_fire_count"])
        ov = int(row["overlap_count"])
        union = rp_f + fb_f - ov
        jaccard = ov / union if union > 0 else 0.0
        print(f"  {row['variant']:40s}  rp={rp_f:3d}  fb={fb_f:3d}  "
              f"overlap={ov:3d}  jaccard={jaccard:.2f}")

    # ── Exit reason breakdown ─────────────────────────────────────────
    print("\n" + "-" * 40)
    print("Exit reason breakdown:")
    for _, row in df.iterrows():
        total = (row["exit_trail"] + row["exit_trend"]
                 + row["exit_rangepos"] + row["exit_feature_b"])
        if total == 0:
            continue
        def pct(x: float) -> str:
            return f"{x / total:.0%}"
        print(f"  {row['variant']:40s}  "
              f"trail={int(row['exit_trail']):3d} ({pct(row['exit_trail'])})  "
              f"trend={int(row['exit_trend']):3d} ({pct(row['exit_trend'])})  "
              f"rp={int(row['exit_rangepos']):3d} ({pct(row['exit_rangepos'])})  "
              f"fb={int(row['exit_feature_b']):3d} ({pct(row['exit_feature_b'])})")


if __name__ == "__main__":
    main()
