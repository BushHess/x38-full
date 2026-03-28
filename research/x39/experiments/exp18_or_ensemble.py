#!/usr/bin/env python3
"""Exp 18: OR Ensemble (Any Signal Enters).

Opposite of exp17. Instead of requiring agreement, enter when ANY signal fires.
Exit when ALL signals say exit. This MAXIMIZES exposure — captures every
opportunity that any system identifies.

Three configs:
  A: Entry=any, Exit=all-agree + trail stop
  A-notrail: Entry=any, Exit=all-agree, NO trail stop
  B: Entry=any, Exit=E5 only (simplest)

Usage:
    python -m research.x39.experiments.exp18_or_ensemble
    # or from x39/:
    python experiments/exp18_or_ensemble.py
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

# ── Gen4 C3 thresholds (from exp14) ──────────────────────────────────────
GEN4_RANGEPOS_ENTRY = 0.55
GEN4_RANGEPOS_EXIT = 0.35


def compute_signals(feat: pd.DataFrame) -> pd.DataFrame:
    """Compute the three independent boolean entry/exit signals per bar."""
    sig = pd.DataFrame(index=feat.index)

    # ── Entry signals ─────────────────────────────────────────────────
    sig["sig_e5"] = (
        (feat["ema_fast"] > feat["ema_slow"])
        & (feat["vdo"] > 0)
        & (feat["d1_regime_ok"] == 1)
    ).astype(int)

    ts = feat["trade_surprise_168"]
    rp = feat["rangepos_168"]
    sig["sig_gen4"] = (
        ts.notna() & rp.notna()
        & (ts > 0)
        & (rp > GEN4_RANGEPOS_ENTRY)
    ).astype(int)

    ret168 = feat["ret_168"]
    sig["sig_gen1"] = (ret168.notna() & (ret168 > 0)).astype(int)

    sig["any_entry"] = ((sig["sig_e5"] | sig["sig_gen4"] | sig["sig_gen1"]) == 1).astype(int)

    # ── Exit signals (per bar, independent of position state) ─────────
    # E5 trend exit (EMA cross-down, no trail — trail is position-dependent)
    sig["exit_e5_trend"] = (feat["ema_fast"] < feat["ema_slow"]).astype(int)

    # Gen4 exit: rangepos drops below hold threshold
    sig["exit_gen4"] = (rp.isna() | (rp < GEN4_RANGEPOS_EXIT)).astype(int)

    # Gen1 exit: ret_168 turns negative
    sig["exit_gen1"] = (ret168.isna() | (ret168 < 0)).astype(int)

    return sig


def run_backtest_or(
    feat: pd.DataFrame,
    sig: pd.DataFrame,
    warmup_bar: int,
    mode: str,
    label: str,
) -> dict:
    """Run OR-ensemble backtest.

    mode:
      "A"         — entry=any, exit=(exit_e5 AND exit_gen4 AND exit_gen1), trail active
      "A-notrail" — entry=any, exit=(exit_e5_trend AND exit_gen4 AND exit_gen1), no trail
      "B"         — entry=any, exit=E5 only (trail + EMA cross)
      "E5"        — E5 baseline (entry=E5 only, exit=E5 only)
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    n = len(c)

    # Entry mask
    if mode == "E5":
        entry_mask = sig["sig_e5"].values.astype(bool)
    else:
        entry_mask = sig["any_entry"].values.astype(bool)

    # Exit signal arrays
    exit_gen4 = sig["exit_gen4"].values.astype(bool)
    exit_gen1 = sig["exit_gen1"].values.astype(bool)

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
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash

            if entry_mask[i]:
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

            # Determine exit based on mode
            do_exit = False

            if mode == "E5" or mode == "B":
                # Standard E5 exit: trail OR trend
                if c[i] < trail_stop or ema_f[i] < ema_s[i]:
                    do_exit = True

            elif mode == "A":
                # All-agree exit WITH trail: (trail OR ema_cross) AND gen4_exit AND gen1_exit
                e5_exit = c[i] < trail_stop or ema_f[i] < ema_s[i]
                if e5_exit and exit_gen4[i] and exit_gen1[i]:
                    do_exit = True

            elif mode == "A-notrail":
                # All-agree exit NO trail: ema_cross AND gen4_exit AND gen1_exit
                e5_trend_exit = ema_f[i] < ema_s[i]
                if e5_trend_exit and exit_gen4[i] and exit_gen1[i]:
                    do_exit = True

            if do_exit:
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
            "config": label, "sharpe": np.nan, "cagr_pct": np.nan,
            "mdd_pct": np.nan, "trades": 0, "win_rate": np.nan,
            "avg_bars_held": np.nan, "exposure_pct": np.nan,
        }

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4  # ~2191.5

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
    avg_held = tdf["bars_held"].mean()

    return {
        "config": label,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_bars_held": round(avg_held, 1),
        "exposure_pct": round(exposure * 100, 1),
    }


def signal_analysis(sig: pd.DataFrame, warmup_bar: int) -> None:
    """Analyze signal overlap, OR coverage, and exclusive regions."""
    s = sig.iloc[warmup_bar:].copy()

    print("\n" + "-" * 80)
    print("SIGNAL ANALYSIS")
    print("-" * 80)

    # Signal frequency
    print("\nSignal frequency (post-warmup):")
    for col in ["sig_e5", "sig_gen4", "sig_gen1"]:
        pct = s[col].mean() * 100
        print(f"  {col}: {pct:.1f}% of bars active")

    any_pct = s["any_entry"].mean() * 100
    print(f"\n  ANY signal (OR): {any_pct:.1f}% of bars")

    # Exclusive regions: bars where ONLY one signal fires
    only_e5 = ((s["sig_e5"] == 1) & (s["sig_gen4"] == 0) & (s["sig_gen1"] == 0)).mean() * 100
    only_gen4 = ((s["sig_e5"] == 0) & (s["sig_gen4"] == 1) & (s["sig_gen1"] == 0)).mean() * 100
    only_gen1 = ((s["sig_e5"] == 0) & (s["sig_gen4"] == 0) & (s["sig_gen1"] == 1)).mean() * 100
    print(f"\n  Exclusive signal bars:")
    print(f"    Only E5:   {only_e5:.1f}%")
    print(f"    Only Gen4: {only_gen4:.1f}%")
    print(f"    Only Gen1: {only_gen1:.1f}%")
    print(f"    (= new entries from OR that E5 alone misses: {only_gen4 + only_gen1:.1f}%)")

    # Exit signal frequency
    print("\nExit signal frequency (post-warmup):")
    for col in ["exit_e5_trend", "exit_gen4", "exit_gen1"]:
        pct = s[col].mean() * 100
        print(f"  {col}: {pct:.1f}% of bars")

    all_exit = ((s["exit_e5_trend"] == 1) & (s["exit_gen4"] == 1) & (s["exit_gen1"] == 1)).mean() * 100
    print(f"  ALL exit (AND): {all_exit:.1f}% of bars")

    # Pairwise entry correlation
    print("\nPairwise entry signal correlation (Pearson):")
    cols = ["sig_e5", "sig_gen4", "sig_gen1"]
    corr = s[cols].corr()
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1:]:
            print(f"  {c1} vs {c2}: r={corr.loc[c1, c2]:.3f}")


def entry_source_analysis(
    feat: pd.DataFrame,
    sig: pd.DataFrame,
    warmup_bar: int,
) -> None:
    """For each OR-ensemble trade, identify which signal triggered entry."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    n = len(c)

    e5 = sig["sig_e5"].values.astype(bool)
    gen4 = sig["sig_gen4"].values.astype(bool)
    gen1 = sig["sig_gen1"].values.astype(bool)
    any_entry = sig["any_entry"].values.astype(bool)

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            continue
        if not in_pos:
            if any_entry[i]:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
        else:
            peak = max(peak, c[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            if c[i] < trail_stop or ema_f[i] < ema_s[i]:
                net_ret = (c[i] - entry_price) / entry_price - cost
                # Classify entry source
                sources = []
                if e5[entry_bar]:
                    sources.append("E5")
                if gen4[entry_bar]:
                    sources.append("Gen4")
                if gen1[entry_bar]:
                    sources.append("Gen1")
                trades.append({
                    "entry_bar": entry_bar,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                    "source": "+".join(sources),
                    "has_e5": int(e5[entry_bar]),
                    "has_gen4": int(gen4[entry_bar]),
                    "has_gen1": int(gen1[entry_bar]),
                })
                in_pos = False
                peak = 0.0

    if not trades:
        print("\nNo trades for source analysis.")
        return

    tdf = pd.DataFrame(trades)

    print("\n" + "-" * 80)
    print("ENTRY SOURCE ANALYSIS (OR entries, E5 exit)")
    print("-" * 80)

    # By whether E5 was active at entry
    e5_yes = tdf[tdf["has_e5"] == 1]
    e5_no = tdf[tdf["has_e5"] == 0]
    print(f"\n  E5 active at entry:  {len(e5_yes)} trades, WR {e5_yes['win'].mean() * 100:.1f}%, "
          f"avg ret {e5_yes['net_ret'].mean() * 100:+.2f}%")
    print(f"  E5 NOT active:       {len(e5_no)} trades, WR {e5_no['win'].mean() * 100:.1f}%, "
          f"avg ret {e5_no['net_ret'].mean() * 100:+.2f}%")

    # Top source combinations
    print(f"\n  {'Source':<20s}  {'Trades':>7s}  {'WR':>6s}  {'Avg Ret':>9s}")
    for src, grp in tdf.groupby("source"):
        wr = grp["win"].mean() * 100
        ar = grp["net_ret"].mean() * 100
        print(f"  {src:<20s}  {len(grp):7d}  {wr:5.1f}%  {ar:+8.2f}%")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 18: OR Ensemble (Any Signal Enters)")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    sig = compute_signals(feat)

    # Warmup: need all features valid
    ts = feat["trade_surprise_168"].values
    rp = feat["rangepos_168"].values
    ret168 = feat["ret_168"].values
    first_valid = 0
    for i in range(len(ts)):
        if np.isfinite(ts[i]) and np.isfinite(rp[i]) and np.isfinite(ret168[i]):
            first_valid = i
            break
    warmup_bar = max(SLOW_PERIOD, first_valid)
    print(f"\nWarmup bar: {warmup_bar} (first valid features at {first_valid})")

    # ── Signal analysis ───────────────────────────────────────────────
    signal_analysis(sig, warmup_bar)

    # ── Entry source analysis (OR entries, E5 exit) ───────────────────
    entry_source_analysis(feat, sig, warmup_bar)

    # ── Run configs ───────────────────────────────────────────────────
    configs = [
        ("E5_baseline", "E5"),
        ("A_all_agree_exit", "A"),
        ("A_notrail", "A-notrail"),
        ("B_e5_exit", "B"),
    ]

    results = []
    for label, mode in configs:
        print(f"\nRunning {label} (mode={mode})...")
        r = run_backtest_or(feat, sig, warmup_bar, mode, label)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, WR={r['win_rate']}%, "
              f"avg_held={r['avg_bars_held']}, exposure={r['exposure_pct']}%")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)
    base = df.iloc[0]  # E5 baseline
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # positive = worse MDD

    print("\n" + "=" * 80)
    print("RESULTS (vs E5-ema21D1 baseline)")
    print("=" * 80)
    print(df.to_string(index=False))

    # Save
    out_path = RESULTS_DIR / "exp18_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    ensembles = df[df["config"] != "E5_baseline"]

    # Check: any OR-ensemble beats E5 on BOTH Sharpe AND MDD?
    strict_wins = ensembles[(ensembles["d_sharpe"] > 0) & (ensembles["d_mdd"] < 0)]
    if not strict_wins.empty:
        best = strict_wins.loc[strict_wins["d_sharpe"].idxmax()]
        print(f"PASS: {best['config']} improves BOTH Sharpe ({best['d_sharpe']:+.4f}) "
              f"and MDD ({best['d_mdd']:+.2f} pp) vs E5 baseline.")
    else:
        sharpe_wins = ensembles[ensembles["d_sharpe"] > 0]
        if not sharpe_wins.empty:
            best = sharpe_wins.loc[sharpe_wins["d_sharpe"].idxmax()]
            print(f"MIXED: {best['config']} improves Sharpe ({best['d_sharpe']:+.4f}) "
                  f"but MDD changes {best['d_mdd']:+.2f} pp.")
        else:
            print("FAIL: No OR-ensemble config improves Sharpe over E5 baseline.")

    # Exposure comparison
    e5_exp = df.loc[df["config"] == "E5_baseline", "exposure_pct"].iloc[0]
    for _, row in ensembles.iterrows():
        d_exp = row["exposure_pct"] - e5_exp
        print(f"  {row['config']}: exposure {row['exposure_pct']:.1f}% ({d_exp:+.1f} pp vs E5)")

    # Signal independence
    cols = ["sig_e5", "sig_gen4", "sig_gen1"]
    s = sig.iloc[warmup_bar:]
    corr_vals = []
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1:]:
            corr_vals.append(s[c1].corr(s[c2]))
    avg_corr = np.mean(corr_vals)
    print(f"\nSignal independence: avg pairwise r={avg_corr:.3f}")
    if avg_corr > 0.5:
        print("  HIGH correlation — OR ensemble mostly duplicates E5 entries.")
    elif avg_corr > 0.3:
        print("  MODERATE correlation — OR adds some unique entries, but also noise.")
    else:
        print("  LOW correlation — OR captures genuinely different opportunities.")


if __name__ == "__main__":
    main()
