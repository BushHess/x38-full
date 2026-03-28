#!/usr/bin/env python3
"""Exp 50: Alternative Compression Measures — Mechanism Robustness.

Tests whether the volatility compression mechanism is robust (multiple
independent measures show selectivity) or fragile (only vol_ratio_5_20 works).

5 measures tested:
  1. vol_ratio_5_20  (original, std-based)
  2. atr_ratio_5_20  (true-range-based)
  3. range_ratio_5_20 (high-low range)
  4. bb_pctl          (Bollinger width percentile)
  5. vol_ratio_5_50   (wider window std-based)

Pass: MECHANISM ROBUST if ≥ 3/5 alternatives are selective.
Fail: MECHANISM FRAGILE if only vol_ratio_5_20 (or 1 other) is selective.

Usage:
    python -m research.x39.experiments.exp50_alt_compression_measures
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

# ── Target blocking rate ──────────────────────────────────────────────────
TARGET_BLOCK_RATE = 0.30  # ~30% of entries blocked


def compute_compression_measures(feat: pd.DataFrame) -> pd.DataFrame:
    """Compute all 5 compression measures on H4 bars."""
    c = feat["close"].values
    h = feat[["close"]].values.ravel()  # placeholder, need actual high/low
    n = len(c)

    # We need high/low from original data — extract from feat or recompute.
    # explore.py stores range = high - low. We can recover high/low indirectly
    # but simpler to re-derive true range from close prices.
    # Actually, explore.py doesn't store high/low directly.
    # We need to reload raw data for true range. Let's compute from available data.

    out = pd.DataFrame(index=feat.index)

    # 1. vol_ratio_5_20 (already in feat)
    out["vol_ratio_5_20"] = feat["vol_ratio_5_20"].values

    # 2. atr_ratio_5_20: SMA(TR, 5) / SMA(TR, 20)
    #    True range needs high, low, prev_close. We have range = high - low,
    #    and close. But we need actual high and low for |high - prev_close|
    #    and |low - prev_close|. Let's load raw data inline.
    # (loaded in main and passed via extra columns)
    tr = feat["_true_range"].values
    atr_5 = pd.Series(tr).rolling(5, min_periods=5).mean().values
    atr_20 = pd.Series(tr).rolling(20, min_periods=20).mean().values
    out["atr_ratio_5_20"] = atr_5 / np.where(atr_20 > 1e-10, atr_20, np.nan)

    # 3. range_ratio_5_20: SMA(high-low, 5) / SMA(high-low, 20)
    hl_range = feat["range"].values  # high - low from explore.py
    range_5 = pd.Series(hl_range).rolling(5, min_periods=5).mean().values
    range_20 = pd.Series(hl_range).rolling(20, min_periods=20).mean().values
    out["range_ratio_5_20"] = range_5 / np.where(range_20 > 1e-10, range_20, np.nan)

    # 4. bb_pctl: percentile rank of Bollinger width over trailing 100 bars
    bb_width = pd.Series(c).rolling(20, min_periods=20).std().values / (
        pd.Series(c).rolling(20, min_periods=20).mean().values
    )
    bb_pctl = np.full(n, np.nan)
    for i in range(100, n):
        window = bb_width[i - 100 : i + 1]
        valid = window[np.isfinite(window)]
        if len(valid) >= 20:
            bb_pctl[i] = np.searchsorted(np.sort(valid), bb_width[i]) / len(valid)
    out["bb_pctl"] = bb_pctl

    # 5. vol_ratio_5_50: rolling_std(close, 5) / rolling_std(close, 50)
    std_5 = pd.Series(c).rolling(5, min_periods=5).std().values
    std_50 = pd.Series(c).rolling(50, min_periods=50).std().values
    out["vol_ratio_5_50"] = std_5 / np.where(std_50 > 1e-10, std_50, np.nan)

    return out


def find_baseline_entries(
    feat: pd.DataFrame,
    warmup_bar: int,
) -> list[int]:
    """Find all bars where E5-ema21D1 baseline would enter."""
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


def run_backtest(
    feat: pd.DataFrame,
    gate_col: str | None,
    gate_threshold: float | None,
    warmup_bar: int,
) -> dict:
    """Replay E5-ema21D1 with optional compression gate.

    gate_col: column name in compression measures DataFrame (or None for baseline).
    gate_threshold: block entry if measure >= threshold (low = compressed).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    n = len(c)

    gate_arr = feat[gate_col].values if gate_col is not None else None

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
                gate_ok = True
                if gate_arr is not None and gate_threshold is not None:
                    if np.isfinite(gate_arr[i]):
                        gate_ok = gate_arr[i] < gate_threshold
                    else:
                        gate_ok = False

                if gate_ok:
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
        return _empty_result(gate_col, gate_threshold)

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
        "measure": gate_col if gate_col is not None else "baseline",
        "threshold": round(gate_threshold, 4) if gate_threshold is not None else None,
        "sharpe": round(sharpe, 4),
        "cagr_pct": round(cagr * 100, 2),
        "mdd_pct": round(abs(mdd) * 100, 2),
        "trades": len(trades),
        "win_rate": round(win_rate, 1),
        "blocked": blocked_total,
        "blocked_win_rate": round(blocked_wr, 1) if np.isfinite(blocked_wr) else np.nan,
    }


def _empty_result(gate_col: str | None, gate_threshold: float | None) -> dict:
    return {
        "measure": gate_col if gate_col is not None else "baseline",
        "threshold": gate_threshold,
        "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
        "trades": 0, "win_rate": np.nan, "blocked": 0, "blocked_win_rate": np.nan,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 50: Alternative Compression Measures — Mechanism Robustness")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)
    warmup_bar = SLOW_PERIOD

    # ── Attach true range for ATR computation ─────────────────────────
    h_arr = h4["high"].values.astype(np.float64)
    lo_arr = h4["low"].values.astype(np.float64)
    c_arr = h4["close"].values.astype(np.float64)
    prev_c = np.concatenate([[c_arr[0]], c_arr[:-1]])
    true_range = np.maximum(
        h_arr - lo_arr,
        np.maximum(np.abs(h_arr - prev_c), np.abs(lo_arr - prev_c)),
    )
    feat["_true_range"] = true_range

    # ── Compute all compression measures ──────────────────────────────
    comp = compute_compression_measures(feat)
    measures = ["vol_ratio_5_20", "atr_ratio_5_20", "range_ratio_5_20",
                "bb_pctl", "vol_ratio_5_50"]

    # Attach to feat for backtest access
    for m in measures:
        feat[m] = comp[m].values

    # ── Find baseline entries to calibrate thresholds ─────────────────
    baseline_entries = find_baseline_entries(feat, warmup_bar)
    n_entries = len(baseline_entries)
    print(f"\nBaseline entries: {n_entries}")

    # For each measure, find the threshold that blocks ~30% of entries
    print(f"\nCalibrating thresholds to block ~{TARGET_BLOCK_RATE*100:.0f}% of entries:")
    calibrated_thresholds: dict[str, float] = {}
    for m in measures:
        vals = [feat[m].values[i] for i in baseline_entries if np.isfinite(feat[m].values[i])]
        if len(vals) < 10:
            print(f"  {m}: insufficient valid entries ({len(vals)}), SKIP")
            continue
        vals_arr = np.array(vals)
        # Threshold = percentile such that (1 - TARGET_BLOCK_RATE) of entries pass
        # Entry passes when measure < threshold, so we want the (1-block_rate) percentile
        pctl = (1.0 - TARGET_BLOCK_RATE) * 100
        thresh = float(np.percentile(vals_arr, pctl))
        actual_block = (vals_arr >= thresh).mean()
        calibrated_thresholds[m] = thresh
        print(f"  {m}: P{pctl:.0f}={thresh:.4f}, actual block={actual_block*100:.1f}%")

    # ── Cross-correlation between measures ────────────────────────────
    print("\n--- Cross-correlation matrix (at baseline entry bars) ---")
    entry_vals = {}
    for m in measures:
        vals = np.array([feat[m].values[i] for i in baseline_entries])
        entry_vals[m] = vals

    corr_df = pd.DataFrame(entry_vals).corr()
    print(corr_df.round(3).to_string())

    # Pairwise correlation with vol_ratio_5_20
    print("\nCorrelation with vol_ratio_5_20:")
    for m in measures:
        if m == "vol_ratio_5_20":
            continue
        valid = np.isfinite(entry_vals["vol_ratio_5_20"]) & np.isfinite(entry_vals[m])
        if valid.sum() > 10:
            r = np.corrcoef(entry_vals["vol_ratio_5_20"][valid], entry_vals[m][valid])[0, 1]
            print(f"  {m}: r={r:.3f}")

    # ── Run baseline ──────────────────────────────────────────────────
    print("\n--- Running backtests ---")
    print("Running baseline...")
    baseline = run_backtest(feat, None, None, warmup_bar)
    baseline_wr = baseline["win_rate"]
    print(f"  Sharpe={baseline['sharpe']}, WR={baseline_wr}%, trades={baseline['trades']}")

    results = [baseline]

    # ── Run each compression measure ──────────────────────────────────
    for m in measures:
        if m not in calibrated_thresholds:
            continue
        thresh = calibrated_thresholds[m]
        print(f"\nRunning {m} (threshold={thresh:.4f})...")
        r = run_backtest(feat, m, thresh, warmup_bar)
        results.append(r)

        d_sharpe = r["sharpe"] - baseline["sharpe"]
        selective = r["blocked_win_rate"] < baseline_wr if np.isfinite(r["blocked_win_rate"]) else False
        print(
            f"  Sharpe={r['sharpe']} (d={d_sharpe:+.4f}), trades={r['trades']}, "
            f"blocked={r['blocked']}, blocked_WR={r['blocked_win_rate']}% "
            f"[{'SELECTIVE' if selective else 'NOT selective'}]"
        )

    # ── Results table ─────────────────────────────────────────────────
    df = pd.DataFrame(results)
    df["d_sharpe"] = df["sharpe"] - baseline["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - baseline["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - baseline["mdd_pct"]

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    # ── Selectivity analysis ──────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SELECTIVITY ANALYSIS")
    print(f"Baseline WR: {baseline_wr}%")
    print("=" * 80)

    selective_measures = []
    summary_rows = []
    gated = df[df["measure"] != "baseline"]

    for _, row in gated.iterrows():
        selective = False
        if np.isfinite(row["blocked_win_rate"]) and row["blocked"] > 0:
            selective = row["blocked_win_rate"] < baseline_wr
        tag = "SELECTIVE" if selective else "NOT selective"
        if selective:
            selective_measures.append(row["measure"])
        print(
            f"  {row['measure']}: blocked_WR={row['blocked_win_rate']:.1f}% "
            f"vs baseline {baseline_wr:.1f}% → {tag}"
        )
        corr_with_original = "—"
        if row["measure"] != "vol_ratio_5_20":
            valid = np.isfinite(entry_vals["vol_ratio_5_20"]) & np.isfinite(entry_vals[row["measure"]])
            if valid.sum() > 10:
                corr_with_original = f"{np.corrcoef(entry_vals['vol_ratio_5_20'][valid], entry_vals[row['measure']][valid])[0, 1]:.3f}"

        summary_rows.append({
            "measure": row["measure"],
            "sharpe": row["sharpe"],
            "d_sharpe": row["d_sharpe"],
            "blocked_wr": row["blocked_win_rate"],
            "selective": "YES" if selective else "NO",
            "corr_with_vol_ratio_5_20": corr_with_original,
        })

    # ── Summary table (spec format) ───────────────────────────────────
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    summary_df = pd.DataFrame(summary_rows)
    print(summary_df.to_string(index=False))

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    n_selective = len(selective_measures)
    n_alt_selective = len([m for m in selective_measures if m != "vol_ratio_5_20"])

    print(f"Selective measures: {n_selective}/5 total, {n_alt_selective}/4 alternatives")
    if selective_measures:
        print(f"  → {', '.join(selective_measures)}")

    if n_alt_selective >= 3:
        verdict = "MECHANISM ROBUST"
        print(f"\n{verdict}: {n_alt_selective}/4 alternative measures are selective.")
        print("Volatility compression genuinely predicts entry quality.")
        print("vol_ratio_5_20's WFO result reflects a real mechanism, not feature-specific overfit.")
    elif n_alt_selective >= 1:
        verdict = "MECHANISM PARTIAL"
        print(f"\n{verdict}: {n_alt_selective}/4 alternative measures are selective.")
        print("Some evidence for compression mechanism, but not fully robust.")
    else:
        verdict = "MECHANISM FRAGILE"
        print(f"\n{verdict}: 0/4 alternative measures are selective.")
        print("Only vol_ratio_5_20 shows selectivity — potential feature-specific overfit.")
        print("WFO result should be treated with more caution.")

    # ── Save results ──────────────────────────────────────────────────
    out_path = RESULTS_DIR / "exp50_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")


if __name__ == "__main__":
    main()
