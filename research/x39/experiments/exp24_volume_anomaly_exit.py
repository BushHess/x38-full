#!/usr/bin/env python3
"""Exp 24: Volume Anomaly Exit.

E5-ema21D1 with volume-based supplementary exits. Two variants:

  Variant A — Liquidity dropout (vol_per_range z-score):
    Exit when vpr_z < threshold (liquidity drops below recent average).
    threshold sweep: [-2.0, -1.5, -1.0, -0.5, 0.0]

  Variant B — Participation anomaly (trade_surprise_168):
    Exit when trade_surprise_168 < threshold (concentrated flow).
    threshold sweep: [-0.15, -0.10, -0.05, 0.00, 0.05]

Total: 10 configs + 1 baseline = 11 runs.

Additional analysis:
  - Exit attribution (trail / trend / volume counts)
  - Information overlap with rangepos_84 (exp12 independence)
  - Timing: counterfactual vs trail/trend exit
  - Per-regime exit counts (pre-2022, 2022 bear, post-2022)

Usage:
    python -m research.x39.experiments.exp24_volume_anomaly_exit
    # or from x39/:
    python experiments/exp24_volume_anomaly_exit.py
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
WARMUP_DAYS = 365

VPR_Z_THRESHOLDS = [-2.0, -1.5, -1.0, -0.5, 0.0]
TS168_THRESHOLDS = [-0.15, -0.10, -0.05, 0.00, 0.05]

# Counterfactual search horizon (bars) for timing analysis
CF_MAX_HORIZON = 500  # ~83 days at H4

# Regime boundaries (milliseconds)
REGIME_2022_START = int(pd.Timestamp("2022-01-01").timestamp() * 1000)
REGIME_2023_START = int(pd.Timestamp("2023-01-01").timestamp() * 1000)


def compute_vpr_z(feat: pd.DataFrame) -> np.ndarray:
    """Compute vol_per_range z-score with 100-bar rolling window.

    Handle doji bars (range ~ 0) by setting vpr_z = NaN.
    """
    vol = feat["volume"].values
    rng = feat["range"].values

    rng_safe = np.where(rng > 1e-10, rng, np.nan)
    vpr = vol / rng_safe

    s = pd.Series(vpr)
    rm = s.rolling(100, min_periods=100).mean()
    rs = s.rolling(100, min_periods=100).std()
    rs_safe = rs.replace(0, np.nan)
    vpr_z = ((vpr - rm) / rs_safe).values
    return vpr_z


def run_backtest(
    feat: pd.DataFrame,
    volume_feature: np.ndarray | None,
    threshold: float | None,
    warmup_bar: int,
    *,
    variant_label: str = "",
) -> tuple[dict, list[dict]]:
    """Replay E5-ema21D1 with optional volume supplementary exit.

    If volume_feature/threshold is None, runs baseline (no volume exit).
    Returns (summary_dict, trades_list).
    """
    c = feat["close"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values
    ratr = feat["ratr"].values
    vdo_arr = feat["vdo"].values
    d1_ok = feat["d1_regime_ok"].values
    rangepos = feat["rangepos_84"].values
    open_times = feat["open_time"].values
    n = len(c)

    use_vol = volume_feature is not None and threshold is not None

    trades: list[dict] = []
    exit_counts = {"trail": 0, "trend": 0, "volume": 0}
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
            elif (
                use_vol
                and np.isfinite(volume_feature[i])
                and volume_feature[i] < threshold
            ):
                exit_reason = "volume"

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
                    "peak_at_exit": peak,
                    "rangepos_at_exit": rangepos[i],
                    "open_time": open_times[i],
                })

                exit_counts[exit_reason] += 1
                equity[i] = cash
                position_size = 0.0
                in_pos = False
                peak = 0.0

    # ── Compute metrics ───────────────────────────────────────────────
    eq = pd.Series(equity[warmup_bar:]).dropna()
    if len(eq) < 2 or len(trades) == 0:
        label = "baseline" if not use_vol else f"{variant_label} thr={threshold}"
        return {
            "config": label,
            "variant": variant_label if use_vol else "baseline",
            "threshold": threshold,
            "sharpe": np.nan, "cagr_pct": np.nan, "mdd_pct": np.nan,
            "trades": 0, "win_rate": np.nan, "avg_bars_held": np.nan,
            "avg_win": np.nan, "avg_loss": np.nan, "exposure_pct": np.nan,
            "exit_trail": 0, "exit_trend": 0, "exit_volume": 0,
        }, trades

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

    label = "baseline" if not use_vol else f"{variant_label} thr={threshold}"

    return {
        "config": label,
        "variant": variant_label if use_vol else "baseline",
        "threshold": threshold,
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
        "exit_volume": exit_counts["volume"],
    }, trades


def counterfactual_exit_bar(
    c: np.ndarray,
    ratr: np.ndarray,
    ema_f: np.ndarray,
    ema_s: np.ndarray,
    vol_exit_bar: int,
    peak_at_exit: float,
) -> int | None:
    """Find when trail/trend WOULD have exited if volume signal hadn't fired.

    Returns bar index of counterfactual exit, or None if data ends first.
    """
    n = len(c)
    peak = peak_at_exit

    end = min(n, vol_exit_bar + CF_MAX_HORIZON)
    for i in range(vol_exit_bar + 1, end):
        if np.isnan(ratr[i]):
            continue
        peak = max(peak, c[i])
        trail_stop = peak - TRAIL_MULT * ratr[i]

        if c[i] < trail_stop:
            return i
        if ema_f[i] < ema_s[i]:
            return i

    return None


def timing_analysis(
    trades: list[dict],
    feat: pd.DataFrame,
) -> list[dict]:
    """For each volume-triggered exit, compute counterfactual timing delta.

    Positive bars_earlier = volume exits BEFORE trail/trend would have.
    """
    c = feat["close"].values
    ratr = feat["ratr"].values
    ema_f = feat["ema_fast"].values
    ema_s = feat["ema_slow"].values

    results = []
    for t in trades:
        if t["exit_reason"] != "volume":
            continue

        cf_bar = counterfactual_exit_bar(
            c, ratr, ema_f, ema_s,
            t["exit_bar"], t["peak_at_exit"],
        )

        if cf_bar is not None:
            bars_earlier = cf_bar - t["exit_bar"]
            cf_exit_price = c[cf_bar]
            cf_gross_ret = (cf_exit_price - t["entry_price"]) / t["entry_price"]
            cf_net_ret = cf_gross_ret - COST_BPS / 10_000
            avoided_pnl = t["net_ret"] - cf_net_ret
        else:
            bars_earlier = None
            cf_exit_price = None
            cf_net_ret = None
            avoided_pnl = None

        results.append({
            "entry_bar": t["entry_bar"],
            "vol_exit_bar": t["exit_bar"],
            "cf_exit_bar": cf_bar,
            "bars_earlier": bars_earlier,
            "vol_exit_price": t["exit_price"],
            "cf_exit_price": cf_exit_price,
            "vol_net_ret": round(t["net_ret"] * 100, 2),
            "cf_net_ret": round(cf_net_ret * 100, 2) if cf_net_ret is not None else None,
            "avoided_pnl_pct": round(avoided_pnl * 100, 2) if avoided_pnl is not None else None,
            "win": t["win"],
        })

    return results


def print_timing_report(timing: list[dict]) -> None:
    """Print timing analysis for volume exits."""
    if not timing:
        print("  (no volume exits to analyse)")
        return

    with_cf = [t for t in timing if t["bars_earlier"] is not None]
    if not with_cf:
        print("  (all volume exits near end of data — no counterfactual available)")
        return

    bars_arr = np.array([t["bars_earlier"] for t in with_cf])
    avoided_arr = np.array([t["avoided_pnl_pct"] for t in with_cf])

    n_earlier = int(np.sum(bars_arr > 0))
    n_later = int(np.sum(bars_arr < 0))
    n_same = int(np.sum(bars_arr == 0))

    print(f"  volume exits with counterfactual: {len(with_cf)}")
    print(f"  volume exits EARLIER than trail/trend: {n_earlier} ({n_earlier / len(with_cf):.0%})")
    print(f"  volume exits LATER:                    {n_later} ({n_later / len(with_cf):.0%})")
    print(f"  volume exits SAME bar:                 {n_same} ({n_same / len(with_cf):.0%})")
    print(f"  bars_earlier: median={np.median(bars_arr):.0f}, "
          f"mean={np.mean(bars_arr):.1f}, "
          f"min={np.min(bars_arr):.0f}, max={np.max(bars_arr):.0f}")
    print(f"  avoided PnL (pp): median={np.median(avoided_arr):.2f}, "
          f"mean={np.mean(avoided_arr):.2f}")

    # Per-trade detail
    print(f"\n  {'entry':>6} {'vol_ex':>7} {'cf_ex':>7} {'Δbars':>6} "
          f"{'vol%':>8} {'cf%':>8} {'avoid%':>8} {'win':>4}")
    for t in with_cf:
        print(f"  {t['entry_bar']:6d} {t['vol_exit_bar']:7d} "
              f"{t['cf_exit_bar']:7d} {t['bars_earlier']:+6d} "
              f"{t['vol_net_ret']:+8.2f} {t['cf_net_ret']:+8.2f} "
              f"{t['avoided_pnl_pct']:+8.2f} {'W' if t['win'] else 'L':>4}")


def overlap_analysis(trades: list[dict]) -> None:
    """Check information overlap with exp12 rangepos_84 exit.

    For volume-triggered exits, how many ALSO had rangepos_84 < 0.25?
    Low overlap = independent information domain → good stacking candidate.
    """
    vol_trades = [t for t in trades if t["exit_reason"] == "volume"]
    if not vol_trades:
        print("  (no volume exits)")
        return

    rp_threshold = 0.25  # exp12 best threshold
    n_total = len(vol_trades)
    n_overlap = sum(
        1 for t in vol_trades
        if np.isfinite(t["rangepos_at_exit"]) and t["rangepos_at_exit"] < rp_threshold
    )
    n_independent = n_total - n_overlap

    print(f"  volume exits: {n_total}")
    print(f"  ALSO rangepos_84 < {rp_threshold}: {n_overlap} ({n_overlap / n_total:.0%})")
    print(f"  independent (rangepos ≥ {rp_threshold}): "
          f"{n_independent} ({n_independent / n_total:.0%})")


def regime_analysis(trades: list[dict]) -> None:
    """Count volume exits per regime: pre-2022, 2022 bear, post-2022."""
    vol_trades = [t for t in trades if t["exit_reason"] == "volume"]
    if not vol_trades:
        print("  (no volume exits)")
        return

    pre_2022 = sum(1 for t in vol_trades if t["open_time"] < REGIME_2022_START)
    bear_2022 = sum(
        1 for t in vol_trades
        if REGIME_2022_START <= t["open_time"] < REGIME_2023_START
    )
    post_2022 = sum(1 for t in vol_trades if t["open_time"] >= REGIME_2023_START)
    n = len(vol_trades)

    # Total trades per regime (for rate context)
    all_pre = sum(1 for t in trades if t["open_time"] < REGIME_2022_START)
    all_bear = sum(
        1 for t in trades
        if REGIME_2022_START <= t["open_time"] < REGIME_2023_START
    )
    all_post = sum(1 for t in trades if t["open_time"] >= REGIME_2023_START)

    print(f"  volume exits by regime ({n} total):")
    print(f"    pre-2022:  {pre_2022:3d} / {all_pre:3d} trades "
          f"({pre_2022 / all_pre:.0%})" if all_pre else f"    pre-2022:  {pre_2022}")
    print(f"    2022 bear: {bear_2022:3d} / {all_bear:3d} trades "
          f"({bear_2022 / all_bear:.0%})" if all_bear else f"    2022 bear: {bear_2022}")
    print(f"    post-2022: {post_2022:3d} / {all_post:3d} trades "
          f"({post_2022 / all_post:.0%})" if all_post else f"    post-2022: {post_2022}")


def selectivity_report(trades: list[dict]) -> None:
    """Of volume exits, how many were losers vs winners?"""
    vol_trades = [t for t in trades if t["exit_reason"] == "volume"]
    if not vol_trades:
        print("  (no volume exits)")
        return

    n = len(vol_trades)
    n_win = sum(1 for t in vol_trades if t["win"])
    n_loss = n - n_win

    print(f"  volume exits: {n} total")
    print(f"    winners: {n_win} ({n_win / n:.0%})")
    print(f"    losers:  {n_loss} ({n_loss / n:.0%})")

    if n_win > 0:
        avg_win_ret = np.mean([t["net_ret"] for t in vol_trades if t["win"]]) * 100
        print(f"    avg winner return: {avg_win_ret:+.2f}%")
    if n_loss > 0:
        avg_loss_ret = np.mean([t["net_ret"] for t in vol_trades if not t["win"]]) * 100
        print(f"    avg loser return:  {avg_loss_ret:+.2f}%")

    other_trades = [t for t in trades if t["exit_reason"] != "volume"]
    if other_trades:
        other_wr = sum(1 for t in other_trades if t["win"]) / len(other_trades)
        vol_wr = n_win / n
        print(f"  win rate comparison: volume={vol_wr:.1%} vs trail/trend={other_wr:.1%}")


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("EXP 24: Volume Anomaly Exit")
    print(f"  Variant A (vpr_z) thresholds:          {VPR_Z_THRESHOLDS}")
    print(f"  Variant B (trade_surprise_168) thresholds: {TS168_THRESHOLDS}")
    print(f"  trail_mult: {TRAIL_MULT} (fixed)")
    print(f"  cost:       {COST_BPS} bps RT")
    print("=" * 80)

    h4, d1 = load_data()
    feat = compute_features(h4, d1)

    # ── Compute vpr_z (not in compute_features) ──────────────────────
    vpr_z = compute_vpr_z(feat)
    ts168 = feat["trade_surprise_168"].values

    # ── Warmup ────────────────────────────────────────────────────────
    bars_per_day = 24 / 4
    warmup_bar = max(SLOW_PERIOD, int(WARMUP_DAYS * bars_per_day))
    # Ensure both features are valid at warmup_bar
    first_valid_vpr = int(np.argmax(np.isfinite(vpr_z)))
    first_valid_ts = int(np.argmax(np.isfinite(ts168)))
    warmup_bar = max(warmup_bar, first_valid_vpr, first_valid_ts)
    print(f"Warmup bar: {warmup_bar} "
          f"(first valid vpr_z: {first_valid_vpr}, ts168: {first_valid_ts})")

    # ── Run baseline ─────────────────────────────────────────────────
    results = []
    print("\nRunning baseline (no volume exit)...")
    r, base_trades = run_backtest(feat, None, None, warmup_bar)
    results.append(r)
    print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
          f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
    print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}")

    # ── Variant A: vpr_z sweep ───────────────────────────────────────
    all_trades_a: dict[float, list[dict]] = {}
    print("\n--- Variant A: Liquidity Dropout (vpr_z) ---")
    for thr in VPR_Z_THRESHOLDS:
        label = f"vpr_z={thr}"
        print(f"\nRunning {label}...")
        r, trades = run_backtest(
            feat, vpr_z, thr, warmup_bar, variant_label="A:vpr_z",
        )
        results.append(r)
        all_trades_a[thr] = trades
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
        print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, "
              f"volume={r['exit_volume']}")

    # ── Variant B: trade_surprise_168 sweep ──────────────────────────
    all_trades_b: dict[float, list[dict]] = {}
    print("\n--- Variant B: Participation Anomaly (trade_surprise_168) ---")
    for thr in TS168_THRESHOLDS:
        label = f"ts168={thr}"
        print(f"\nRunning {label}...")
        r, trades = run_backtest(
            feat, ts168, thr, warmup_bar, variant_label="B:ts168",
        )
        results.append(r)
        all_trades_b[thr] = trades
        print(f"  Sharpe={r['sharpe']}, CAGR={r['cagr_pct']}%, MDD={r['mdd_pct']}%, "
              f"trades={r['trades']}, avg_held={r['avg_bars_held']}")
        print(f"  exits: trail={r['exit_trail']}, trend={r['exit_trend']}, "
              f"volume={r['exit_volume']}")

    # ── Results table ────────────────────────────────────────────────
    df = pd.DataFrame(results)

    base = df.iloc[0]
    df["d_sharpe"] = df["sharpe"] - base["sharpe"]
    df["d_cagr"] = df["cagr_pct"] - base["cagr_pct"]
    df["d_mdd"] = df["mdd_pct"] - base["mdd_pct"]  # negative = MDD improved

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(df.to_string(index=False))

    out_path = RESULTS_DIR / "exp24_results.csv"
    df.to_csv(out_path, index=False)
    print(f"\n-> Saved to {out_path}")

    # ── Exit attribution breakdown ───────────────────────────────────
    print("\n" + "-" * 40)
    print("Exit attribution:")
    for _, row in df.iterrows():
        total = row["exit_trail"] + row["exit_trend"] + row["exit_volume"]
        if total == 0:
            continue
        pct_t = row["exit_trail"] / total
        pct_tr = row["exit_trend"] / total
        pct_v = row["exit_volume"] / total
        print(f"  {row['config']:25s}  trail={int(row['exit_trail']):3d} ({pct_t:.0%})"
              f"  trend={int(row['exit_trend']):3d} ({pct_tr:.0%})"
              f"  volume={int(row['exit_volume']):3d} ({pct_v:.0%})")

    # ── Overlap analysis (independence from rangepos_84) ─────────────
    print("\n" + "=" * 80)
    print("INFORMATION OVERLAP with rangepos_84 < 0.25 (exp12)")
    print("(low overlap = independent information domain)")
    print("=" * 80)

    for thr in VPR_Z_THRESHOLDS:
        trades = all_trades_a[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            continue
        print(f"\nVariant A: vpr_z={thr} ({n_vol} volume exits):")
        overlap_analysis(trades)

    for thr in TS168_THRESHOLDS:
        trades = all_trades_b[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            continue
        print(f"\nVariant B: ts168={thr} ({n_vol} volume exits):")
        overlap_analysis(trades)

    # ── Timing analysis ──────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("TIMING ANALYSIS")
    print("(positive bars_earlier = volume exits BEFORE trail/trend would have)")
    print("=" * 80)

    for thr in VPR_Z_THRESHOLDS:
        trades = all_trades_a[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            print(f"\nVariant A: vpr_z={thr}: no volume exits")
            continue
        print(f"\nVariant A: vpr_z={thr}: {n_vol} volume exits")
        timing = timing_analysis(trades, feat)
        print_timing_report(timing)

    for thr in TS168_THRESHOLDS:
        trades = all_trades_b[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            print(f"\nVariant B: ts168={thr}: no volume exits")
            continue
        print(f"\nVariant B: ts168={thr}: {n_vol} volume exits")
        timing = timing_analysis(trades, feat)
        print_timing_report(timing)

    # ── Selectivity analysis ─────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SELECTIVITY ANALYSIS")
    print("(does volume signal selectively cut losers?)")
    print("=" * 80)

    for thr in VPR_Z_THRESHOLDS:
        trades = all_trades_a[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            continue
        print(f"\nVariant A: vpr_z={thr}:")
        selectivity_report(trades)

    for thr in TS168_THRESHOLDS:
        trades = all_trades_b[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            continue
        print(f"\nVariant B: ts168={thr}:")
        selectivity_report(trades)

    # ── Regime analysis ──────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("REGIME ANALYSIS")
    print("(volume exit distribution across market regimes)")
    print("=" * 80)

    for thr in VPR_Z_THRESHOLDS:
        trades = all_trades_a[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            continue
        print(f"\nVariant A: vpr_z={thr}:")
        regime_analysis(trades)

    for thr in TS168_THRESHOLDS:
        trades = all_trades_b[thr]
        n_vol = sum(1 for t in trades if t["exit_reason"] == "volume")
        if n_vol == 0:
            continue
        print(f"\nVariant B: ts168={thr}:")
        regime_analysis(trades)

    # ── Verdict ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)

    variants = df.iloc[1:]

    # Check per-variant
    for var_name, var_rows in [
        ("Variant A (vpr_z)", variants[variants["variant"] == "A:vpr_z"]),
        ("Variant B (ts168)", variants[variants["variant"] == "B:ts168"]),
    ]:
        improvements = var_rows[(var_rows["d_sharpe"] > 0) & (var_rows["d_mdd"] < 0)]

        if not improvements.empty:
            best = improvements.loc[improvements["d_sharpe"].idxmax()]
            print(f"\n{var_name}: PASS — {best['config']} improves both "
                  f"Sharpe ({best['d_sharpe']:+.4f}) and MDD ({best['d_mdd']:+.2f} pp)")
            print(f"  Sharpe {best['sharpe']}, CAGR {best['cagr_pct']}%, "
                  f"MDD {best['mdd_pct']}%, trades {int(best['trades'])}")
        else:
            sharpe_up = var_rows[var_rows["d_sharpe"] > 0]
            mdd_down = var_rows[var_rows["d_mdd"] < 0]
            if not sharpe_up.empty:
                best = sharpe_up.loc[sharpe_up["d_sharpe"].idxmax()]
                print(f"\n{var_name}: MIXED — {best['config']} improves "
                      f"Sharpe ({best['d_sharpe']:+.4f}) but MDD {best['d_mdd']:+.2f} pp")
            elif not mdd_down.empty:
                best = mdd_down.loc[mdd_down["d_mdd"].idxmin()]
                print(f"\n{var_name}: MIXED — {best['config']} improves "
                      f"MDD ({best['d_mdd']:+.2f} pp) but Sharpe {best['d_sharpe']:+.4f}")
            else:
                print(f"\n{var_name}: FAIL — no threshold improves Sharpe or MDD.")

    # Overall
    all_improvements = variants[(variants["d_sharpe"] > 0) & (variants["d_mdd"] < 0)]
    if all_improvements.empty:
        any_sharpe = variants[variants["d_sharpe"] > 0]
        if any_sharpe.empty:
            print("\nOVERALL: FAIL — volume anomaly exits do NOT help E5-ema21D1.")
        else:
            print("\nOVERALL: MIXED — some Sharpe improvement but with MDD trade-off.")
    else:
        best = all_improvements.loc[all_improvements["d_sharpe"].idxmax()]
        print(f"\nOVERALL: PASS — best: {best['config']} "
              f"(Sharpe {best['d_sharpe']:+.4f}, MDD {best['d_mdd']:+.2f} pp)")


if __name__ == "__main__":
    main()
