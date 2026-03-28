#!/usr/bin/env python3
"""Exp 51: Momentum Persistence Entry Gate.

Adds ret_168 persistence >= min_persistence to E5-ema21D1 entry.
  ret_168_positive[i] = 1 if ret_168[i] > 0 else 0
  persistence[i] = mean(ret_168_positive[i-M+1 : i+1])

Sweeps M ∈ [42, 84, 168] × min_persistence ∈ [0.5, 0.6, 0.7, 0.8] + baseline.
(3 × 4 = 12 configs + 1 baseline = 13 runs)

Key analyses:
  1. Selectivity: blocked WR vs baseline WR
  2. Regime behavior: persistence distribution at entry bars
  3. Complementarity with vol compression (exp34): overlap of blocked entries

Usage:
    python -m research.x39.experiments.exp51_momentum_persistence_gate
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
LOOKBACKS = [42, 84, 168]                     # M: persistence window (H4 bars)
MIN_PERSISTENCES = [0.5, 0.6, 0.7, 0.8]      # min fraction of ret_168 > 0

# ── Vol compression threshold for complementarity analysis ────────────────
VOL_COMPRESS_THRESHOLD = 0.7  # best from exp34


def compute_persistence(ret_168: np.ndarray, lookback: int) -> np.ndarray:
    """Fraction of bars with ret_168 > 0 in trailing lookback window."""
    n = len(ret_168)
    persistence = np.full(n, np.nan)
    positive = np.where(np.isfinite(ret_168), (ret_168 > 0).astype(np.float64), np.nan)

    # Cumulative sum approach for efficiency
    for i in range(lookback - 1, n):
        window = positive[i - lookback + 1 : i + 1]
        valid = window[np.isfinite(window)]
        if len(valid) == lookback:
            persistence[i] = np.mean(valid)

    return persistence


def run_backtest(
    feat: pd.DataFrame,
    lookback: int | None,
    min_persistence: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional momentum persistence gate."""
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    ret_168 = feat["ret_168"].values
    vol_ratio = feat["vol_ratio_5_20"].values
    n = len(c)

    # Pre-compute persistence array
    persistence = np.full(n, np.nan)
    if lookback is not None:
        persistence = compute_persistence(ret_168, lookback)

    trades: list[dict] = []
    blocked_entries: list[int] = []
    entry_persistence_vals: list[float] = []
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
                persistence_ok = True
                if lookback is not None:
                    if np.isfinite(persistence[i]):
                        persistence_ok = persistence[i] >= min_persistence
                    else:
                        persistence_ok = False

                if persistence_ok:
                    in_pos = True
                    entry_bar = i
                    entry_price = c[i]
                    peak = c[i]
                    half_cost = (COST_BPS / 2) / 10_000
                    position_size = cash * (1 - half_cost) / c[i]
                    cash = 0.0
                    if np.isfinite(persistence[i]):
                        entry_persistence_vals.append(persistence[i])
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
        return _empty_result(lookback, min_persistence)

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

    # ── Blocked entry analysis (simulate each as independent trade) ───
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

    # ── Complementarity with vol compression ──────────────────────────
    vol_compress_also_blocked = 0
    for b_i in blocked_entries:
        if np.isfinite(vol_ratio[b_i]) and vol_ratio[b_i] >= VOL_COMPRESS_THRESHOLD:
            vol_compress_also_blocked += 1
    overlap_pct = (vol_compress_also_blocked / blocked_total * 100) if blocked_total > 0 else np.nan

    # ── Entry persistence distribution ────────────────────────────────
    median_entry_pers = float(np.median(entry_persistence_vals)) if entry_persistence_vals else np.nan

    return {
        "lookback": lookback if lookback is not None else "baseline",
        "min_persistence": min_persistence if min_persistence is not None else "baseline",
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "avg_bars_held": round(avg_bars_held, 1),
        "exposure_pct": round(exposure * 100, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
        "vol_compress_overlap_pct": round(overlap_pct, 1) if np.isfinite(overlap_pct) else np.nan,
        "median_entry_persistence": round(median_entry_pers, 3) if np.isfinite(median_entry_pers) else np.nan,
    }


def _empty_result(
    lookback: int | None,
    min_persistence: float | None,
) -> dict:
    return {
        "lookback": lookback if lookback is not None else "baseline",
        "min_persistence": min_persistence if min_persistence is not None else "baseline",
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
        "exposure_pct": np.nan, "blocked": 0, "blocked_win_rate": np.nan,
        "vol_compress_overlap_pct": np.nan, "median_entry_persistence": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 51: Momentum Persistence Entry Gate")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    warmup_bar = SLOW_PERIOD
    print(f"Warmup bar: {warmup_bar}")

    # ── Persistence distribution at all E5-ema21D1 entry bars ─────────
    print("\n--- ret_168 persistence distribution (all bars, M=84) ---")
    ret_168 = feat["ret_168"].values
    pers_84 = compute_persistence(ret_168, 84)
    valid_pers = pers_84[np.isfinite(pers_84)]
    print(f"  All bars: median={np.median(valid_pers):.3f}, "
          f"mean={np.mean(valid_pers):.3f}, std={np.std(valid_pers):.3f}")
    for thresh in MIN_PERSISTENCES:
        frac = np.mean(valid_pers >= thresh) * 100
        print(f"  Fraction >= {thresh}: {frac:.1f}%")

    # Build config grid: baseline + 12 configs
    configs: list[tuple[int | None, float | None]] = [(None, None)]
    for lb in LOOKBACKS:
        for mp in MIN_PERSISTENCES:
            configs.append((lb, mp))

    results = []
    for lb, mp in configs:
        if lb is None:
            label = "baseline"
        else:
            label = f"M={lb}, min_pers={mp}"
        print(f"\nRunning {label}...")
        r = run_backtest(feat, lb, mp, warmup_bar)
        results.append(r)
        print(
            f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
            f"trades={r['trades']}, blocked={r['blocked']}, "
            f"blocked_wr={r['blocked_win_rate']}, "
            f"vol_overlap={r['vol_compress_overlap_pct']}%"
        )

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = improvement

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp51_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Selectivity analysis ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SELECTIVITY ANALYSIS")
    print("=" * 80)
    print(f"Baseline WR: {base['win_rate']:.1f}%")
    gated = df.iloc[1:]
    for _, row in gated.iterrows():
        if row["blocked"] > 0:
            selective = row["blocked_win_rate"] < base["win_rate"]
            tag = "SELECTIVE" if selective else "NOT selective"
            print(
                f"  M={row['lookback']:>3}, min_pers={row['min_persistence']}: "
                f"blocked {row['blocked']:>4}, blocked WR {row['blocked_win_rate']:5.1f}% "
                f"[{tag}]"
            )

    # ── Complementarity with vol compression ──────────────────────────
    print("\n" + "=" * 80)
    print(f"COMPLEMENTARITY WITH VOL COMPRESSION (threshold={VOL_COMPRESS_THRESHOLD})")
    print("=" * 80)
    print("Overlap % = fraction of persistence-blocked entries that vol compression")
    print("would ALSO block. Low overlap = potentially stackable.")
    for _, row in gated.iterrows():
        if row["blocked"] > 0:
            ovl = row["vol_compress_overlap_pct"]
            tag = "LOW" if ovl < 30 else ("MEDIUM" if ovl < 60 else "HIGH")
            print(
                f"  M={row['lookback']:>3}, min_pers={row['min_persistence']}: "
                f"overlap {ovl:5.1f}% [{tag}]"
            )

    # ── Regime behavior (persistence at entry bars per period) ────────
    print("\n" + "=" * 80)
    print("REGIME BEHAVIOR (persistence at baseline entry bars)")
    print("=" * 80)
    # Run baseline to get entry bars
    baseline_r = _get_entry_bars(feat, warmup_bar)
    if baseline_r:
        entry_bars = baseline_r["entry_bars"]
        datetimes = feat["datetime"].values

        for lb in LOOKBACKS:
            pers = compute_persistence(ret_168, lb)
            entry_pers = [pers[i] for i in entry_bars if np.isfinite(pers[i])]
            if entry_pers:
                # Split by time halves for regime approximation
                mid = len(entry_bars) // 2
                first_half = [pers[i] for i in entry_bars[:mid] if np.isfinite(pers[i])]
                second_half = [pers[i] for i in entry_bars[mid:] if np.isfinite(pers[i])]
                print(f"  M={lb}: median_entry_pers={np.median(entry_pers):.3f}, "
                      f"first_half={np.median(first_half):.3f}, "
                      f"second_half={np.median(second_half):.3f}")
                # Fraction that would be blocked at each threshold
                for mp in MIN_PERSISTENCES:
                    blocked_frac = np.mean([p < mp for p in entry_pers]) * 100
                    print(f"    Would block at >={mp}: {blocked_frac:.1f}% of entries")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    improvements = gated[(gated["d_sharpe"] > 0) & (gated["d_mdd"] < 0)]

    if not improvements.empty:
        best = improvements.loc[improvements["d_sharpe"].idxmax()]
        print(
            f"PASS: M={best['lookback']}, min_pers={best['min_persistence']} "
            f"improves Sharpe ({best['d_sharpe']:+.4f}) AND MDD ({best['d_mdd']:+.2f} pp)"
        )
        print(
            f"  {best['trades']} trades, {best['blocked']} blocked "
            f"(blocked WR: {best['blocked_win_rate']:.1f}% vs baseline WR: {base['win_rate']:.1f}%)"
        )
        if best["vol_compress_overlap_pct"] < 30:
            print(f"  Vol compression overlap: {best['vol_compress_overlap_pct']:.1f}% — stackable candidate")
    else:
        sharpe_up = gated[gated["d_sharpe"] > 0]
        if not sharpe_up.empty:
            best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
            print(
                f"MIXED: M={best['lookback']}, min_pers={best['min_persistence']} "
                f"improves Sharpe ({best['d_sharpe']:+.4f}) but MDD {best['d_mdd']:+.2f} pp"
            )
        else:
            print("FAIL: No config improves Sharpe over baseline.")
            print("Momentum persistence gate does NOT help E5-ema21D1.")


def _get_entry_bars(feat: pd.DataFrame, warmup_bar: int) -> dict | None:
    """Get baseline entry bar indices (no gate)."""
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    c = feat["close"].values
    n = len(c)

    entry_bars: list[int] = []
    in_pos = False

    for i in range(warmup_bar, n):
        if np.isnan(ratr[i]):
            continue
        if not in_pos:
            if ema_f[i] > ema_s[i] and vdo_arr[i] > 0 and d1_ok[i]:
                in_pos = True
                entry_bars.append(i)
        else:
            peak = max(c[j] for j in range(entry_bars[-1], i + 1) if not np.isnan(c[j]))
            trail_stop = peak - TRAIL_MULT * ratr[i]
            if c[i] < trail_stop or ema_f[i] < ema_s[i]:
                in_pos = False

    return {"entry_bars": entry_bars} if entry_bars else None


if __name__ == "__main__":
    main()
