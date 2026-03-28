#!/usr/bin/env python3
"""Exp 34: Volatility Compression Entry Gate.

Adds vol_ratio_5_20 < compression_threshold to E5-ema21D1 entry.
  vol_ratio_5_20 = rolling_std(close, 5) / rolling_std(close, 20)
  Low values = compression (market coiling before breakout).

Sweeps compression_threshold ∈ [0.5, 0.6, 0.7, 0.8, 0.9, 1.0].
Threshold 1.0 should reproduce baseline (sanity check).

Usage:
    python -m research.x39.experiments.exp34_vol_compression_entry
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

# ── Sweep grid ────────────────────────────────────────────────────────────
COMPRESSION_THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]


def run_backtest(
    feat: pd.DataFrame,
    compression_threshold: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional volatility compression gate."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    vol_ratio = feat["vol_ratio_5_20"].values
    n = len(c)

    trades: list[dict] = []
    blocked_entries: list[int] = []
    in_pos = False
    peak = 0.0
    entry_bar = 0
    entry_price = 0.0

    equity = np.full(n, np.nan)
    cash = INITIAL_CASH
    position_size = 0.0

    # Track vol_ratio at actual entry bars (for distribution analysis)
    entry_vol_ratios: list[float] = []

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash

            base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if base_ok:
                compression_ok = True
                if compression_threshold is not None:
                    if np.isfinite(vol_ratio[i]):
                        compression_ok = vol_ratio[i] < compression_threshold
                    else:
                        compression_ok = False

                if compression_ok:
                    in_pos = True
                    entry_bar = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
                    if np.isfinite(vol_ratio[i]):
                        entry_vol_ratios.append(vol_ratio[i])
                else:
                    blocked_entries.append(i)
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
                cost_rt = COST_BPS / 10_000
                gross_ret = (c[i] - entry_price) / entry_price
                net_ret = gross_ret - cost_rt

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "bars_held": i - entry_bar,
                    "net_ret": net_ret,
                    "win": int(net_ret > 0),
                })

                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Metrics ───────────────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        return _empty_result(compression_threshold)

    rets = eq.pct_change().dropna()
    bars_per_year = 365.25 * 24 / 4

    sharpe = (rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0

    total_bars = len(eq)
    years = total_bars / bars_per_year
    final_ret = eq.iloc[-1] / eq.iloc[0]
    cagr = final_ret ** (1 / years) - 1 if years > 0 and final_ret > 0 else 0.0

    cummax = eq.cummax()
    dd = (eq - cummax) / cummax
    mdd = dd.min()

    total_bars_held = sum(t["bars_held"] for t in trades)
    exposure = total_bars_held / total_bars
    avg_bars_held = np.mean([t["bars_held"] for t in trades])

    tdf = pd.DataFrame(trades)
    n_wins = int(tdf["win"].sum())
    win_rate = n_wins / len(trades) * 100

    # ── Blocked entry analysis ────────────────────────────────────────
    blocked_wins = 0
    blocked_total = len(blocked_entries)

    for b_i in blocked_entries:
        b_entry = c[b_i]
        b_peak = b_entry
        b_exited = False
        for j in range(b_i + 1, n):
            if np.isnan(ratr[j]):
                continue
            b_peak = max(b_peak, c[j])
            b_trail = b_peak - TRAIL_MULT * ratr[j]
            if c[j] < b_trail or ema_f[j] < ema_s[j]:
                cost_rt = COST_BPS / 10_000
                if (c[j] - b_entry) / b_entry - cost_rt > 0:
                    blocked_wins += 1
                b_exited = True
                break
        if not b_exited:
            cost_rt = COST_BPS / 10_000
            if (c[-1] - b_entry) / b_entry - cost_rt > 0:
                blocked_wins += 1

    blocked_wr = (blocked_wins / blocked_total * 100) if blocked_total > 0 else np.nan

    # ── Entry vol_ratio distribution ──────────────────────────────────
    median_entry_vr = float(np.median(entry_vol_ratios)) if entry_vol_ratios else np.nan

    return {
        "threshold": compression_threshold if compression_threshold is not None else "baseline",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_bars_held": round(avg_bars_held, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
        "median_entry_vol_ratio": round(median_entry_vr, 4) if np.isfinite(median_entry_vr) else np.nan,
    }


def _empty_result(compression_threshold: float | None) -> dict:
    return {
        "threshold": compression_threshold if compression_threshold is not None else "baseline",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "blocked": 0, "blocked_win_rate": np.nan,
        "median_entry_vol_ratio": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 34: Volatility Compression Entry Gate")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # Baseline vol_ratio distribution at E5-ema21D1 entry bars
    print("\n--- Baseline vol_ratio_5_20 distribution at entry bars ---")
    vr = feat["vol_ratio_5_20"].dropna()
    print(f"  All bars: median={vr.median():.4f}, mean={vr.mean():.4f}, "
          f"std={vr.std():.4f}")
    print(f"  Percentiles: 10%={vr.quantile(0.1):.4f}, 25%={vr.quantile(0.25):.4f}, "
          f"50%={vr.quantile(0.5):.4f}, 75%={vr.quantile(0.75):.4f}, "
          f"90%={vr.quantile(0.9):.4f}")
    # Fraction below each threshold
    for t in COMPRESSION_THRESHOLDS:
        frac = (vr < t).mean() * 100
        print(f"  Fraction < {t}: {frac:.1f}%")

    # Build config grid: baseline + 6 configs
    configs: list[float | None] = [None]
    configs.extend(COMPRESSION_THRESHOLDS)

    results = []
    for thresh in configs:
        if thresh is None:
            label = "baseline"
        else:
            label = f"threshold={thresh}"
        print(f"\nRunning {label}...")
        r = run_backtest(feat, thresh, warmup_bar)
        results.append(r)
        print(
            f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
            f"trades={r['trades']}, blocked={r['blocked']}, "
            f"blocked_wr={r['blocked_win_rate']}, "
            f"median_entry_vr={r['median_entry_vol_ratio']}"
        )

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # positive = worse

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp34_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Sanity check ──────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SANITY CHECK")
    print("=" * 80)
    t10 = df[df["threshold"] == 1.0]
    if not t10.empty:
        t10_row = t10.iloc[0]
        sharpe_match = abs(t10_row["sharpe"] - base["sharpe"]) < 0.01
        trades_match = t10_row["trades"] == base["trades"]
        if sharpe_match and trades_match:
            print("OK: threshold=1.0 matches baseline (as expected).")
        else:
            print(f"WARNING: threshold=1.0 differs from baseline! "
                  f"Sharpe {t10_row['sharpe']} vs {base['sharpe']}, "
                  f"trades {t10_row['trades']} vs {base['trades']}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    # Exclude threshold=1.0 (sanity check) from verdict analysis
    gated = df[(df["threshold"] != "baseline") & (df["threshold"] != 1.0)]

    improvements = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(
            f"PASS: threshold={best['threshold']} "
            f"improves Sharpe ({best['d_sharpe']:+.4f}) AND MDD ({best['d_mdd']:+.2f} pp)"
        )
        print(
            f"  {best['trades']} trades, {best['blocked']} blocked "
            f"(blocked WR: {best['blocked_win_rate']:.1f}% vs baseline WR: {base['win_rate']:.1f}%)"
        )
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(
                f"MIXED: threshold={best['threshold']} "
                f"improves Sharpe ({best['d_sharpe']:+.4f}) but MDD {best['d_mdd']:+.2f} pp"
            )
        else:
            print("FAIL: No config improves Sharpe over baseline.")
            print("Volatility compression gate does NOT help E5-ema21D1.")
            print("(Consistent with negative prior from residual scan.)")

    # Blocked entry analysis summary
    print(f"\nBlocked entry analysis (baseline WR: {base['win_rate']:.1f}%):")
    for _, row in gated.iterrows():
        if row["blocked"] > 0:
            selectivity = "GOOD" if row["blocked_win_rate"] < base["win_rate"] else "BAD"
            print(
                f"  threshold={row['threshold']}: "
                f"blocked {row['blocked']:>4}, blocked WR {row['blocked_win_rate']:5.1f}% [{selectivity}]"
            )


if __name__ == "__main__":
    main()
