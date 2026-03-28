#!/usr/bin/env python3
"""Exp 17: Vote Ensemble (2/3 Agreement).

Three independent signal systems:
  - E5: EMA crossover + VDO + D1 EMA(21)
  - Gen4: trade_surprise_168 > 0 AND rangepos_168 > 0.55
  - Gen1: ret_168 > 0

Entry requires vote_threshold of 3 signals to agree.
Exit uses E5's proven mechanism (ATR trail + EMA cross-down) regardless.

Usage:
    python -m research.x39.experiments.exp17_vote_ensemble
    # or from x39/:
    python experiments/exp17_vote_ensemble.py
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

# ── Gen4 C3 entry threshold (from exp14) ──────────────────────────────────
GEN4_RANGEPOS_THRESH = 0.55

# ── Reference results (from exp14, exp15) ─────────────────────────────────
E5_REF = {"sharpe": 1.40, "cagr_pct": 61.6, "mdd_pct": 40.0, "trades": 188}
C3_REF = {"sharpe": 0.86, "cagr_pct": 30.2, "mdd_pct": 41.9, "trades": 110}
V6_REF = {"sharpe": 1.04, "cagr_pct": 45.3, "mdd_pct": 59.7, "trades": 243}


def compute_signals(feat: pd.DataFrame) -> pd.DataFrame:
    """Compute the three independent boolean signals per bar."""
    sig = pd.DataFrame(index=feat.index)

    # E5: EMA crossover + VDO > 0 + D1 regime ok
    sig["sig_e5"] = (
        (feat["ema_fast"] > feat["ema_slow"])
        & (feat["vdo"] > 0)
        & (feat["d1_regime_ok"] == 1)
    ).astype(int)

    # Gen4: trade_surprise_168 > 0 AND rangepos_168 > 0.55
    ts = feat["trade_surprise_168"]
    rp = feat["rangepos_168"]
    sig["sig_gen4"] = (
        ts.notna() & rp.notna()
        & (ts > 0)
        & (rp > GEN4_RANGEPOS_THRESH)
    ).astype(int)

    # Gen1: ret_168 > 0
    ret168 = feat["ret_168"]
    sig["sig_gen1"] = (ret168.notna() & (ret168 > 0)).astype(int)

    sig["vote"] = sig["sig_e5"] + sig["sig_gen4"] + sig["sig_gen1"]
    return sig


def run_backtest(
    feat: pd.DataFrame,
    entry_mask: np.ndarray,
    warmup_bar: int,
    label: str,
) -> dict:
    """Run backtest with given entry mask and E5 exit mechanism."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    n = len(c)

    trades: list[dict] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0
    cost = COST_BPS / 10_000

    # Equity tracking
    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash
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
            "config": label, "sharpe": np.nan, "cagr_pct": np.nan,
            "mdd_pct": np.nan, "trades": 0, "win_rate": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
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
    losses = tdf[tdf["win"] == 0]

    return {
        "config": label,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_win": round(wins["net_ret"].mean() * 100, 2) if len(wins) > 0 else np.nan,
        "avg_loss": round(losses["net_ret"].mean() * 100, 2) if len(losses) > 0 else np.nan,
        "exposure_pct": round(exposure * 100, 1),
    }


def signal_analysis(sig: pd.DataFrame, warmup_bar: int) -> None:
    """Analyze signal overlap and correlation."""
    s = sig.iloc[warmup_bar:].copy()

    print("\n" + "-" * 80)
    print("SIGNAL ANALYSIS")
    print("-" * 80)

    # Signal frequency
    print("\nSignal frequency (post-warmup):")
    for col in ["sig_e5", "sig_gen4", "sig_gen1"]:
        pct = s[col].mean() * 100
        print(f"  {col}: {pct:.1f}% of bars active")

    print(f"\n  Vote distribution:")
    for v in range(4):
        pct = (s["vote"] == v).mean() * 100
        print(f"    vote={v}: {pct:.1f}%")

    # Pairwise correlation
    print("\nPairwise signal correlation (Pearson):")
    cols = ["sig_e5", "sig_gen4", "sig_gen1"]
    corr = s[cols].corr()
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1:]:
            print(f"  {c1} vs {c2}: r={corr.loc[c1, c2]:.3f}")

    # Joint agreement
    print("\nJoint agreement rates:")
    both_e5_g4 = ((s["sig_e5"] == 1) & (s["sig_gen4"] == 1)).mean() * 100
    both_e5_g1 = ((s["sig_e5"] == 1) & (s["sig_gen1"] == 1)).mean() * 100
    both_g4_g1 = ((s["sig_gen4"] == 1) & (s["sig_gen1"] == 1)).mean() * 100
    all_three = ((s["sig_e5"] == 1) & (s["sig_gen4"] == 1) & (s["sig_gen1"] == 1)).mean() * 100
    print(f"  E5 + Gen4: {both_e5_g4:.1f}%")
    print(f"  E5 + Gen1: {both_e5_g1:.1f}%")
    print(f"  Gen4 + Gen1: {both_g4_g1:.1f}%")
    print(f"  All three: {all_three:.1f}%")


def trade_quality_by_vote(
    feat: pd.DataFrame,
    sig: pd.DataFrame,
    warmup_bar: int,
) -> None:
    """Run E5 baseline, tag each trade with vote count at entry, compare quality."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vote = sig["vote"].values
    e5_mask = sig["sig_e5"].values
    n = len(c)

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
            if e5_mask[i]:
                in_pos = True
                entry_bar = i
                entry_price = c[i]
                peak = c[i]
        else:
            peak = max(peak, c[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            exit_reason = None
            if c[i] < trail_stop:
                exit_reason = "trail"
            elif ema_f[i] < ema_s[i]:
                exit_reason = "trend"
            if exit_reason:
                net_ret = (c[i] - entry_price) / entry_price - cost
                trades.append({
                    "entry_bar": entry_bar,
                    "vote_at_entry": vote[entry_bar],
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                })
                in_pos = False
                peak = 0.0

    if not trades:
        print("\nNo trades for quality analysis.")
        return

    tdf = pd.DataFrame(trades)

    print("\n" + "-" * 80)
    print("TRADE QUALITY BY VOTE COUNT AT ENTRY (E5 trades only)")
    print("-" * 80)
    print(f"{'Vote':>6s}  {'Trades':>7s}  {'Win Rate':>9s}  {'Avg Ret':>9s}  {'Avg Win':>9s}  {'Avg Loss':>9s}")

    for v in sorted(tdf["vote_at_entry"].unique()):
        subset = tdf[tdf["vote_at_entry"] == v]
        wins = subset[subset["win"] == 1]
        losses = subset[subset["win"] == 0]
        wr = len(wins) / len(subset) * 100 if len(subset) > 0 else 0
        avg_ret = subset["net_ret"].mean() * 100
        avg_w = wins["net_ret"].mean() * 100 if len(wins) > 0 else 0
        avg_l = losses["net_ret"].mean() * 100 if len(losses) > 0 else 0
        print(f"  {v:4d}  {len(subset):7d}  {wr:8.1f}%  {avg_ret:+8.2f}%  {avg_w:+8.2f}%  {avg_l:+8.2f}%")

    # Also show vote>=2 vs vote==1 (E5-only)
    v1 = tdf[tdf["vote_at_entry"] == 1]
    v2plus = tdf[tdf["vote_at_entry"] >= 2]
    if len(v1) > 0 and len(v2plus) > 0:
        wr1 = (v1["win"].sum() / len(v1)) * 100
        wr2 = (v2plus["win"].sum() / len(v2plus)) * 100
        print(f"\n  Vote=1 (E5 only): {len(v1)} trades, WR {wr1:.1f}%, avg ret {v1['net_ret'].mean() * 100:+.2f}%")
        print(f"  Vote>=2 (2+ agree): {len(v2plus)} trades, WR {wr2:.1f}%, avg ret {v2plus['net_ret'].mean() * 100:+.2f}%")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 17: Vote Ensemble (2/3 Agreement)")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    sig = compute_signals(feat)

    # Warmup: need all features valid + EMA warmup
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

    # ── Signal analysis (FIRST, per spec) ─────────────────────────────
    signal_analysis(sig, warmup_bar)

    # ── Trade quality by vote count ───────────────────────────────────
    trade_quality_by_vote(feat, sig, warmup_bar)

    # ── Run configs ───────────────────────────────────────────────────
    e5_mask = sig["sig_e5"].values.astype(bool)
    gen4_mask = sig["sig_gen4"].values.astype(bool)
    gen1_mask = (feat["ret_168"].notna() & (feat["ret_168"] > 0)).values

    configs: list[tuple[str, np.ndarray]] = [
        ("E5_baseline", e5_mask),
        ("Gen4_standalone", gen4_mask),
        ("Gen1_standalone", gen1_mask),
        ("vote>=2", sig["vote"].values >= 2),
        ("vote>=3", sig["vote"].values >= 3),
    ]

    results = []
    for label, mask in configs:
        print(f"\nRunning {label}...")
        r = run_backtest(feat, mask, warmup_bar, label)
        results.append(r)
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, win_rate={r['win_rate']}%, exposure={r['exposure_pct']}%")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)
    base = df.iloc[0]  # E5 baseline
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = MDD improvement

    print("\n" + "=" * 80)
    print("RESULTS (vs E5-ema21D1 baseline)")
    print("=" * 80)
    print(df.to_string(index=False))

    # ── Reference from prior experiments ──────────────────────────────
    print("\n" + "-" * 80)
    print("REFERENCE (from exp14, exp15 — different backtest engines, approximate)")
    print(f"  Gen4 C3 (exp14): Sharpe={C3_REF['sharpe']}, CAGR={C3_REF['cagr_pct']}%, "
          f"MDD={C3_REF['mdd_pct']}%, trades={C3_REF['trades']}")
    print(f"  Gen1 V6 (exp15): Sharpe={V6_REF['sharpe']}, CAGR={V6_REF['cagr_pct']}%, "
          f"MDD={V6_REF['mdd_pct']}%, trades={V6_REF['trades']}")

    # Save
    out_path = RESULTS_DIR / "exp17_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    ensembles = df[df["config"].str.startswith("vote")]

    # Check: any ensemble beats E5 on BOTH Sharpe AND MDD?
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
            print("FAIL: No ensemble config improves Sharpe over E5 baseline.")
            print("  Vote filtering reduces trade count but does not improve risk-adjusted returns.")

    # Signal independence assessment
    cols = ["sig_e5", "sig_gen4", "sig_gen1"]
    s = sig.iloc[warmup_bar:]
    corr_vals = []
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1:]:
            corr_vals.append(s[c1].corr(s[c2]))
    avg_corr = np.mean(corr_vals)
    print(f"\nSignal independence: avg pairwise r={avg_corr:.3f}")
    if avg_corr > 0.5:
        print("  HIGH correlation — signals are NOT independent. Ensemble adds little diversification.")
    elif avg_corr > 0.3:
        print("  MODERATE correlation — partial independence. Some diversification benefit possible.")
    else:
        print("  LOW correlation — signals are largely independent. Ensemble has diversification potential.")


if __name__ == "__main__":
    main()
