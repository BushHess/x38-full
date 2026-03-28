#!/usr/bin/env python3
"""Exp 35: D1 EMA Slope Confirmation.

Adds d1_slope_ok = (d1_ema_slope > min_slope) to E5-ema21D1 entry.
  d1_ema_slope = (d1_ema21[i] - d1_ema21[i-lookback]) / d1_ema21[i-lookback]
  Requires the D1 EMA(21) to be RISING, not just price > EMA.

Sweeps:
  slope_lookback (D1 bars): [3, 5, 10, 15]
  min_slope: [0.0, 0.001, 0.005, 0.01]
  (4 x 4 = 16 configs + baseline)

Usage:
    python -m research.x39.experiments.exp35_d1_ema_slope
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # btc-spot-dev/
sys.path.insert(0, str(ROOT))

from research.x39.explore import compute_features, ema, load_data, map_d1_to_h4  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

# ── Strategy constants (match E5-ema21D1) ─────────────────────────────────
SLOW_PERIOD = 120
TRAIL_MULT = 3.0
COST_BPS = 50
INITIAL_CASH = 10_000.0
WARMUP_DAYS = 365

# ── Sweep grid ────────────────────────────────────────────────────────────
SLOPE_LOOKBACKS = [3, 5, 10, 15]
MIN_SLOPES = [0.0, 0.001, 0.005, 0.01]


# ═══════════════════════════════════════════════════════════════════════════
# D1 slope computation
# ═══════════════════════════════════════════════════════════════════════════

def compute_d1_slopes(
    d1: pd.DataFrame, h4_ct: np.ndarray, n_h4: int,
) -> dict[int, np.ndarray]:
    """Pre-compute D1 EMA(21) slopes for all lookbacks, mapped to H4 grid.

    Returns dict mapping lookback -> H4-grid slope array (NaN where unavailable).
    """
    d1_c = d1["close"].values.astype(np.float64)
    d1_ct = d1["close_time"].values
    d1_ema21 = ema(d1_c, 21)
    n_d1 = len(d1_c)

    slopes: dict[int, np.ndarray] = {}
    for lb in SLOPE_LOOKBACKS:
        d1_slope = np.full(n_d1, np.nan)
        for i in range(lb, n_d1):
            prev = d1_ema21[i - lb]
            if prev > 0:
                d1_slope[i] = (d1_ema21[i] - prev) / prev
        slopes[lb] = map_d1_to_h4(d1_slope, d1_ct, h4_ct, n_h4)

    return slopes


# ═══════════════════════════════════════════════════════════════════════════
# Backtest
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest(
    feat: pd.DataFrame,
    slope_arr: np.ndarray | None,
    min_slope: float,
    warmup_bar: int,
    slope_lookback: int | None = None,
) -> dict:
    """Replay E5-ema21D1 with optional D1 EMA slope gate."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
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

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            equity[i] = cash if not in_pos else position_size * c[i]
            continue

        if not in_pos:
            equity[i] = cash
            base_ok = ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]

            if base_ok:
                slope_ok = True
                if slope_arr is not None:
                    sv = slope_arr[i]
                    if np.isfinite(sv):
                        slope_ok = sv > min_slope
                    else:
                        slope_ok = False

                if slope_ok:
                    in_pos = True
                    entry_bar = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
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
        return _empty_result(slope_lookback, min_slope)

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

    return {
        "lookback": slope_lookback if slope_lookback is not None else "baseline",
        "min_slope": min_slope if slope_arr is not None else "baseline",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_bars_held": round(avg_bars_held, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
    }


def _empty_result(lookback: int | None, min_slope: float) -> dict:
    return {
        "lookback": lookback if lookback is not None else "baseline",
        "min_slope": min_slope if lookback is not None else "baseline",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "blocked": 0, "blocked_win_rate": np.nan,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Analysis helpers
# ═══════════════════════════════════════════════════════════════════════════

def identify_baseline_entries(feat: pd.DataFrame, warmup_bar: int) -> list[int]:
    """Run baseline E5-ema21D1 and return entry bar indices."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    entries: list[int] = []
    in_pos = False
    peak = 0.0

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            continue

        if not in_pos:
            if ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]:
                in_pos = True
                peak = c[i]
                entries.append(i)
        else:
            peak = max(peak, c[i])
            trail_stop = peak - TRAIL_MULT * ratr[i]
            if c[i] < trail_stop or ema_f[i] < ema_s[i]:
                in_pos = False
                peak = 0.0

    return entries


def analyze_entry_delay(
    feat: pd.DataFrame, slopes: dict[int, np.ndarray],
) -> None:
    """Analyze lag between d1_regime_ok onset and slope_ok onset on H4 grid."""
    d1_ok = feat["d1_regime_ok"].values
    n = len(d1_ok)

    # Find regime onset bars (0->1 transition)
    onsets: list[int] = []
    for i in range(1, n):
        if d1_ok[i] == 1 and d1_ok[i - 1] == 0:
            onsets.append(i)

    print(f"\n--- Entry delay: D1 regime onsets (0->1): {len(onsets)} ---")
    print(f"  {'lookback':>8}  {'min_slope':>9}  {'median':>6}  {'mean':>6}  {'missed':>8}")

    for lb in SLOPE_LOOKBACKS:
        slope_arr = slopes[lb]
        for ms in MIN_SLOPES:
            delays: list[int] = []
            missed = 0
            for onset in onsets:
                found = False
                for j in range(onset, n):
                    if d1_ok[j] == 0:
                        break  # regime ended before slope caught up
                    sv = slope_arr[j]
                    if np.isfinite(sv) and sv > ms:
                        delays.append(j - onset)
                        found = True
                        break
                if not found:
                    missed += 1

            med = f"{np.median(delays):.0f}" if delays else "n/a"
            avg = f"{np.mean(delays):.1f}" if delays else "n/a"
            print(f"  {lb:>8}  {ms:>9}  {med:>6}  {avg:>6}  {missed:>3}/{len(onsets)}")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 35: D1 EMA Slope Confirmation")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # Warmup: 365 days from first H4 bar
    first_ot = h4["open_time"].iloc[0]
    warmup_ms = WARMUP_DAYS * 24 * 3600 * 1000
    warmup_bar = int(np.searchsorted(h4["open_time"].values, first_ot + warmup_ms))
    print(f"Warmup: {WARMUP_DAYS} days -> bar {warmup_bar}")

    # Pre-compute D1 slopes mapped to H4
    h4_ct = h4["close_time"].values
    n_h4 = len(h4)
    slopes = compute_d1_slopes(d1, h4_ct, n_h4)

    # ── D1 EMA slope distribution at baseline entry bars ─────────────
    print("\n--- D1 EMA slope distribution at baseline entry bars ---")
    base_entries = identify_baseline_entries(feat, warmup_bar)
    print(f"  Baseline entries: {len(base_entries)}")

    for lb in SLOPE_LOOKBACKS:
        s_at_entries = slopes[lb][base_entries]
        valid = s_at_entries[np.isfinite(s_at_entries)]
        if len(valid) == 0:
            continue
        print(f"\n  lookback={lb}d (n={len(valid)}):")
        print(f"    median={np.median(valid):.6f}, mean={np.mean(valid):.6f}, "
              f"std={np.std(valid):.6f}")
        print(f"    P10={np.percentile(valid, 10):.6f}, "
              f"P25={np.percentile(valid, 25):.6f}, "
              f"P75={np.percentile(valid, 75):.6f}, "
              f"P90={np.percentile(valid, 90):.6f}")
        for ms in MIN_SLOPES:
            frac = (valid <= ms).mean() * 100
            print(f"    blocked at ms={ms}: {frac:.1f}%")

    # ── Entry delay analysis ─────────────────────────────────────────
    analyze_entry_delay(feat, slopes)

    # ── Backtest sweep ────────────────────────────────────────────────
    results: list[dict] = []

    # Baseline
    print("\nRunning baseline...")
    r = run_backtest(feat, None, 0.0, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}")

    # Sweep: 4 lookbacks x 4 min_slopes
    for lb in SLOPE_LOOKBACKS:
        for ms in MIN_SLOPES:
            label = f"lb={lb}, ms={ms}"
            print(f"Running {label}...")
            r = run_backtest(feat, slopes[lb], ms, warmup_bar, slope_lookback=lb)
            results.append(r)
            print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
                  f"trades={r['trades']}, blocked={r['blocked']}")

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # positive = worse MDD

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp35_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Sanity check ──────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SANITY CHECK")
    print("=" * 80)
    # lb=3, ms=0.0 should be closest to baseline (only blocks flat/declining EMA)
    s_check = df[(df["lookback"] == 3) & (df["min_slope"] == 0.0)]
    if not s_check.empty:
        sc = s_check.iloc[0]
        print(f"lb=3, ms=0.0: Sharpe={sc['sharpe']} ({sc['d_sharpe']:+.4f}), "
              f"trades={int(sc['trades'])} (blocked {int(sc['blocked'])})")
        if sc["trades"] >= base["trades"] * 0.8:
            print("OK: minimal filtering at ms=0.0 (most entries already have rising EMA).")
        else:
            print("NOTE: >20% entries filtered at ms=0.0 — many entries with declining EMA.")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    gated = df[df["lookback"] != "baseline"]

    # Best config: improves Sharpe AND improves MDD (d_mdd < 0)
    improvements = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(
            f"PASS: lb={best['lookback']}, ms={best['min_slope']} "
            f"improves Sharpe ({best['d_sharpe']:+.4f}) AND MDD ({best['d_mdd']:+.2f} pp)"
        )
        print(
            f"  {int(best['trades'])} trades, {int(best['blocked'])} blocked "
            f"(blocked WR: {best['blocked_win_rate']:.1f}% vs baseline WR: {base['win_rate']:.1f}%)"
        )
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(
                f"MIXED: lb={best['lookback']}, ms={best['min_slope']} "
                f"improves Sharpe ({best['d_sharpe']:+.4f}) but MDD {best['d_mdd']:+.2f} pp"
            )
        else:
            print("FAIL: No config improves Sharpe over baseline.")
            print("D1 EMA slope confirmation does NOT help E5-ema21D1.")

    # Blocked entry selectivity summary
    print(f"\nBlocked entry selectivity (baseline WR: {base['win_rate']:.1f}%):")
    for _, row in gated.iterrows():
        if row["blocked"] > 0:
            sel = "GOOD" if row["blocked_win_rate"] < base["win_rate"] else "BAD"
            print(
                f"  lb={row['lookback']:>2}, ms={row['min_slope']}: "
                f"blocked {int(row['blocked']):>4}, "
                f"blocked WR {row['blocked_win_rate']:5.1f}% [{sel}]"
            )


if __name__ == "__main__":
    main()
