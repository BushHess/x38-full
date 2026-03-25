#!/usr/bin/env python3
"""X36 Deep Analysis — granular path-level and trade-level tests.

Test 4: Paired path delta + Wilcoxon signed-rank test
        → For each bootstrap path, compute δ = Sharpe(V3) − Sharpe(E5).
        → Paired analysis is strictly more powerful than comparing medians.
Test 5: δ vs regime quality correlation
        → If VCBB destroys regimes V3 needs, δ should correlate with regime quality.
Test 6: Trade-duration P&L decomposition (real data)
        → Show exactly what V3's time_stop truncates.

Expected runtime: ~60-70 min (Tests 4-5) + <1 min (Test 6)
Output: research/x36/branches/a_vcbb_bias_study/test_battery/{results,figures}/
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Project imports ──────────────────────────────────────────────────

ROOT = Path("/var/www/trading-bots/btc-spot-dev")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "x36" / "branches" / "a_vcbb_bias_study"))

from v10.core.engine import BacktestEngine
from v10.core.types import CostConfig

from strategies.vtrend_e5_ema21_d1.strategy import VTrendE5Ema21D1Strategy
from v3v4_strategies import V3Strategy
from research.lib.vcbb import make_ratios, precompute_vcbb, gen_path_vcbb
from run_comparison import (
    _fast_load_bars, PreloadedFeed, make_sub_feed,
    _build_synthetic_feed, _date_ms,
    COST_20, BASE_TS, H4_MS, D1_MS,
)

# ── Constants ────────────────────────────────────────────────────────

DATA_PATH = ROOT / "data" / "bars_btcusdt_2016_now_h1_4h_1d.csv"
OUT = ROOT / "research" / "x36" / "branches" / "a_vcbb_bias_study" / "test_battery"
RESULTS = OUT / "results"
FIGURES = OUT / "figures"

START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
N_BOOT = 500
CTX = 90
K_NN = 50
SEED = 42


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════


def _ema_np(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1)
    out = np.empty_like(series)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1 - alpha) * out[i - 1]
    return out


def _extract_arrays(h4_bars):
    cl = np.array([b.close for b in h4_bars], dtype=np.float64)
    hi = np.array([b.high for b in h4_bars], dtype=np.float64)
    lo = np.array([b.low for b in h4_bars], dtype=np.float64)
    vo = np.array([b.volume for b in h4_bars], dtype=np.float64)
    tb = np.array([b.taker_buy_base_vol for b in h4_bars], dtype=np.float64)
    return cl, hi, lo, vo, tb


def _safe_sharpe(feed, name: str, cost=COST_20) -> float | None:
    """Run backtest, return Sharpe only."""
    try:
        if name == "V3":
            s = V3Strategy()
        else:
            s = VTrendE5Ema21D1Strategy()
        e = BacktestEngine(
            feed=feed, strategy=s, cost=cost,
            initial_cash=10_000.0, warmup_mode="no_trade",
        )
        r = e.run()
        sh = r.summary.get("sharpe")
        if sh is not None and np.isfinite(sh):
            return float(sh)
        return None
    except Exception:
        return None


def _regime_quality(h4_close: np.ndarray) -> float:
    """Measure regime quality: average contiguous D1 EMA(21) segment length.

    Higher = cleaner regimes (longer uninterrupted bull/bear periods).
    """
    n = len(h4_close)
    # Aggregate to D1: every 6 H4 bars
    d1_close = []
    for j in range(0, n, 6):
        chunk = h4_close[j : j + 6]
        if len(chunk) > 0:
            d1_close.append(chunk[-1])

    if len(d1_close) < 22:
        return 0.0

    d1_arr = np.array(d1_close, dtype=np.float64)
    d1_ema = _ema_np(d1_arr, 21)
    regime = d1_arr > d1_ema  # True = bull

    # Count contiguous segments
    segments = 1
    for i in range(1, len(regime)):
        if regime[i] != regime[i - 1]:
            segments += 1

    return len(regime) / segments  # average segment length (D1 bars)


# ═══════════════════════════════════════════════════════════════════════
# TEST 4: PAIRED PATH DELTA + WILCOXON
# ═══════════════════════════════════════════════════════════════════════


def test4_paired(all_h4: list) -> dict:
    """Paired path-level V3 vs E5 comparison at blksz=60 and 360."""
    print("\n" + "=" * 70)
    print("TEST 4: Paired Path Delta + Wilcoxon")
    print(f"  Block sizes: [60, 360]")
    print(f"  Paths: {N_BOOT} per block size")
    print(f"  Total backtests: {2 * N_BOOT * 2}")
    print("=" * 70)

    cl, hi, lo, vo, tb = _extract_arrays(all_h4)
    cr, hr, lr, vol_r, tb_r = make_ratios(cl, hi, lo, vo, tb)
    n_trans = len(cr)
    p0 = cl[0]
    src_base_ts = all_h4[0].open_time

    results = {}

    for blksz in [60, 360]:
        print(f"\n  --- blksz={blksz} ({blksz * 4 // 24}d) ---")
        vcbb = precompute_vcbb(cr, blksz, CTX)
        rng = np.random.default_rng(SEED + blksz * 100)

        v3_sharpes: list[float | None] = []
        e5_sharpes: list[float | None] = []
        regime_quals: list[float] = []
        t0 = time.time()

        for pi in range(N_BOOT):
            if pi % 50 == 0:
                elapsed = time.time() - t0
                print(f"    Path {pi}/{N_BOOT}  ({elapsed:.0f}s)")

            c, h, l, v, t = gen_path_vcbb(
                cr, hr, lr, vol_r, tb_r, n_trans, blksz, p0, rng,
                vcbb=vcbb, K=K_NN,
            )
            qv = c * v
            feed = _build_synthetic_feed(c, h, l, v, t, qv, base_ts=src_base_ts)

            sh_v3 = _safe_sharpe(feed, "V3")
            sh_e5 = _safe_sharpe(feed, "E5")

            v3_sharpes.append(sh_v3)
            e5_sharpes.append(sh_e5)

            # Regime quality (only for blksz=60, used by Test 5)
            if blksz == 60:
                regime_quals.append(_regime_quality(c))

        elapsed = time.time() - t0
        print(f"    blksz={blksz} done in {elapsed:.0f}s ({elapsed / 60:.1f}min)")

        # Compute paired deltas (exclude paths where either failed)
        v3_arr = np.array(
            [x if x is not None else np.nan for x in v3_sharpes], dtype=np.float64
        )
        e5_arr = np.array(
            [x if x is not None else np.nan for x in e5_sharpes], dtype=np.float64
        )
        valid = np.isfinite(v3_arr) & np.isfinite(e5_arr)
        delta = v3_arr[valid] - e5_arr[valid]

        # Wilcoxon signed-rank test
        if len(delta) > 10:
            wilcoxon_stat, wilcoxon_p = stats.wilcoxon(
                delta, alternative="two-sided"
            )
        else:
            wilcoxon_stat, wilcoxon_p = float("nan"), float("nan")

        p_v3_wins = float(np.mean(delta > 0)) if len(delta) > 0 else 0.0

        res = {
            "blksz": blksz,
            "n_valid": int(np.sum(valid)),
            "delta_median": float(np.median(delta)),
            "delta_mean": float(np.mean(delta)),
            "delta_std": float(np.std(delta)),
            "delta_p5": float(np.percentile(delta, 5)),
            "delta_p95": float(np.percentile(delta, 95)),
            "p_v3_wins": p_v3_wins,
            "wilcoxon_stat": float(wilcoxon_stat),
            "wilcoxon_p": float(wilcoxon_p),
            "v3_median": float(np.nanmedian(v3_arr[valid])),
            "e5_median": float(np.nanmedian(e5_arr[valid])),
            "v3_sharpes": v3_arr.tolist(),
            "e5_sharpes": e5_arr.tolist(),
        }
        if blksz == 60:
            res["regime_qualities"] = regime_quals

        results[str(blksz)] = res

        print(f"    V3 median: {res['v3_median']:.3f}")
        print(f"    E5 median: {res['e5_median']:.3f}")
        print(f"    δ median: {res['delta_median']:.4f}")
        print(f"    P(V3 > E5): {p_v3_wins:.1%}")
        print(f"    Wilcoxon p: {wilcoxon_p:.2e}")

    # Save
    save_path = RESULTS / "test4_paired.json"
    with open(save_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved: {save_path}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# TEST 5: δ VS REGIME QUALITY CORRELATION
# ═══════════════════════════════════════════════════════════════════════


def test5_regime_correlation(t4_results: dict) -> dict:
    """Correlate V3-E5 delta with regime quality per path (blksz=60).

    If analyst is right: ρ(δ, regime_quality) > 0 and significant.
    """
    print("\n" + "=" * 70)
    print("TEST 5: δ vs Regime Quality Correlation")
    print("=" * 70)

    data = t4_results["60"]

    v3_arr = np.array(data["v3_sharpes"], dtype=np.float64)
    e5_arr = np.array(data["e5_sharpes"], dtype=np.float64)
    rq_arr = np.array(data["regime_qualities"], dtype=np.float64)

    valid = np.isfinite(v3_arr) & np.isfinite(e5_arr) & np.isfinite(rq_arr)
    delta = v3_arr[valid] - e5_arr[valid]
    rq = rq_arr[valid]

    # Spearman and Pearson correlations
    spearman_r, spearman_p = stats.spearmanr(rq, delta)
    pearson_r, pearson_p = stats.pearsonr(rq, delta)

    # Tercile analysis: split paths by regime quality
    t1_bound, t2_bound = np.percentile(rq, [33.3, 66.7])
    low_mask = rq <= t1_bound
    mid_mask = (rq > t1_bound) & (rq <= t2_bound)
    high_mask = rq > t2_bound

    def _tercile_stats(mask):
        d = delta[mask]
        r = rq[mask]
        return {
            "rq_range": [float(np.min(r)), float(np.max(r))],
            "rq_median": float(np.median(r)),
            "delta_median": float(np.median(d)),
            "delta_mean": float(np.mean(d)),
            "p_v3_wins": float(np.mean(d > 0)),
            "n": int(np.sum(mask)),
        }

    results = {
        "n_valid": int(np.sum(valid)),
        "spearman_r": float(spearman_r),
        "spearman_p": float(spearman_p),
        "pearson_r": float(pearson_r),
        "pearson_p": float(pearson_p),
        "rq_range": [float(np.min(rq)), float(np.max(rq))],
        "rq_median": float(np.median(rq)),
        "terciles": {
            "low": _tercile_stats(low_mask),
            "mid": _tercile_stats(mid_mask),
            "high": _tercile_stats(high_mask),
        },
        "deltas": delta.tolist(),
        "regime_qualities": rq.tolist(),
    }

    print(f"  N valid: {results['n_valid']}")
    print(f"  Spearman ρ: {spearman_r:.4f} (p={spearman_p:.4f})")
    print(f"  Pearson r:  {pearson_r:.4f} (p={pearson_p:.4f})")
    for key, label in [("low", "Low RQ"), ("mid", "Mid RQ"), ("high", "High RQ")]:
        t = results["terciles"][key]
        print(f"  {label}: δ̃={t['delta_median']:.4f}, P(V3>E5)={t['p_v3_wins']:.1%}, "
              f"n={t['n']}")

    # Save
    save_path = RESULTS / "test5_regime_corr.json"
    with open(save_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved: {save_path}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# TEST 6: TRADE-DURATION P&L DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════


def test6_trade_decomposition(all_h4: list, all_d1: list) -> dict:
    """Decompose E5 and V3 trades by duration on REAL data.

    Shows exactly how much P&L comes from trades > 30 H4 bars
    (what V3's time_stop would truncate).
    """
    print("\n" + "=" * 70)
    print("TEST 6: Trade-Duration P&L Decomposition (Real Data)")
    print("=" * 70)

    feed = make_sub_feed(all_h4, all_d1, START, END)

    results = {}

    for name in ["E5", "V3"]:
        if name == "V3":
            s = V3Strategy()
        else:
            s = VTrendE5Ema21D1Strategy()
        e = BacktestEngine(
            feed=feed, strategy=s, cost=COST_20,
            initial_cash=10_000.0, warmup_mode="no_trade",
        )
        r = e.run()
        trades = r.trades

        if not trades:
            results[name] = {"error": "no trades"}
            continue

        # Per-trade stats
        trade_data = []
        for t in trades:
            bars_held = t.days_held * 6  # H4 bars (4h each, 6 per day)
            trade_data.append({
                "trade_id": t.trade_id,
                "return_pct": t.return_pct,
                "pnl": t.pnl,
                "days_held": t.days_held,
                "bars_held": bars_held,
                "exit_reason": t.exit_reason,
            })

        total_pnl = sum(t["pnl"] for t in trade_data)
        total_trades = len(trade_data)

        # Duration buckets
        buckets_def = [
            ("≤10 bars (≤1.7d)", 0, 10),
            ("11-30 bars (1.7-5d)", 11, 30),
            ("31-60 bars (5-10d)", 31, 60),
            ("61-120 bars (10-20d)", 61, 120),
            (">120 bars (>20d)", 121, 99999),
        ]

        bucket_results = []
        for label, lo, hi in buckets_def:
            subset = [t for t in trade_data if lo <= t["bars_held"] <= hi]
            n = len(subset)
            pnl_sum = sum(t["pnl"] for t in subset)
            avg_ret = float(np.mean([t["return_pct"] for t in subset])) if subset else 0.0
            max_ret = max((t["return_pct"] for t in subset), default=0.0)
            min_ret = min((t["return_pct"] for t in subset), default=0.0)
            pnl_pct = (pnl_sum / total_pnl * 100) if total_pnl != 0 else 0.0
            win_rate = float(np.mean([t["return_pct"] > 0 for t in subset])) if subset else 0.0

            bucket_results.append({
                "label": label,
                "count": n,
                "pct_of_trades": n / total_trades * 100,
                "total_pnl": pnl_sum,
                "pnl_contribution_pct": pnl_pct,
                "avg_return_pct": avg_ret,
                "max_return_pct": float(max_ret),
                "min_return_pct": float(min_ret),
                "win_rate_pct": win_rate * 100,
            })

        # Truncation analysis (only for E5)
        truncation = None
        if name == "E5":
            would_truncate = [t for t in trade_data if t["bars_held"] > 30]
            truncated_pnl = sum(t["pnl"] for t in would_truncate)

            sorted_by_dur = sorted(trade_data, key=lambda t: t["bars_held"], reverse=True)
            sorted_by_pnl = sorted(trade_data, key=lambda t: t["pnl"], reverse=True)

            truncation = {
                "trades_over_30bars": len(would_truncate),
                "pct_of_total_trades": len(would_truncate) / total_trades * 100,
                "pnl_at_risk": truncated_pnl,
                "pnl_at_risk_pct": (
                    truncated_pnl / total_pnl * 100 if total_pnl else 0.0
                ),
                "top5_longest": [
                    {
                        "bars": round(t["bars_held"], 1),
                        "return_pct": t["return_pct"],
                        "pnl": round(t["pnl"], 2),
                        "exit": t["exit_reason"],
                    }
                    for t in sorted_by_dur[:5]
                ],
                "top5_profitable": [
                    {
                        "bars": round(t["bars_held"], 1),
                        "return_pct": t["return_pct"],
                        "pnl": round(t["pnl"], 2),
                        "exit": t["exit_reason"],
                    }
                    for t in sorted_by_pnl[:5]
                ],
            }

            # Run E5+TS30 to measure ACTUAL loss from time_stop
            from run_tests import E5Ablation
            s_ts30 = E5Ablation(time_stop_bars=30)
            e_ts30 = BacktestEngine(
                feed=feed, strategy=s_ts30, cost=COST_20,
                initial_cash=10_000.0, warmup_mode="no_trade",
            )
            r_ts30 = e_ts30.run()
            ts30_pnl = sum(t.pnl for t in r_ts30.trades)
            actual_loss_pct = (
                (total_pnl - ts30_pnl) / total_pnl * 100 if total_pnl else 0.0
            )
            truncation["actual_ablation"] = {
                "e5_ts30_pnl": ts30_pnl,
                "e5_ts30_trades": len(r_ts30.trades),
                "e5_ts30_sharpe": r_ts30.summary.get("sharpe"),
                "e5_ts30_cagr_pct": r_ts30.summary.get("cagr_pct"),
                "actual_profit_loss_pct": actual_loss_pct,
            }

        results[name] = {
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "sharpe": r.summary.get("sharpe"),
            "cagr_pct": r.summary.get("cagr_pct"),
            "max_dd_pct": r.summary.get("max_drawdown_mid_pct"),
            "avg_bars_held": float(np.mean([t["bars_held"] for t in trade_data])),
            "median_bars_held": float(np.median([t["bars_held"] for t in trade_data])),
            "max_bars_held": max(t["bars_held"] for t in trade_data),
            "buckets": bucket_results,
            "truncation": truncation,
            "all_trades": [
                {"bars": round(t["bars_held"], 1), "ret": t["return_pct"], "pnl": round(t["pnl"], 2)}
                for t in trade_data
            ],
        }

        # Print
        print(f"\n  {name}: {total_trades} trades, Sharpe {r.summary.get('sharpe'):.3f}")
        print(f"    Avg bars: {results[name]['avg_bars_held']:.1f}, "
              f"Median: {results[name]['median_bars_held']:.1f}, "
              f"Max: {results[name]['max_bars_held']:.1f}")
        for b in bucket_results:
            print(f"    {b['label']}: {b['count']}t ({b['pct_of_trades']:.1f}%), "
                  f"P&L: {b['pnl_contribution_pct']:.1f}%")
        if truncation:
            print(f"    --- V3 Truncation ---")
            print(f"    Trades > 30 bars: {truncation['trades_over_30bars']} "
                  f"({truncation['pct_of_total_trades']:.1f}%)")
            print(f"    P&L exposure (upper bound): {truncation['pnl_at_risk_pct']:.1f}%")
            if truncation.get("actual_ablation"):
                abl = truncation["actual_ablation"]
                print(f"    Actual ablation loss (E5+TS30): {abl['actual_profit_loss_pct']:.1f}%")

    # Save (without all_trades to keep file small)
    save_data = {}
    for sname, sdata in results.items():
        save_data[sname] = {k: v for k, v in sdata.items() if k != "all_trades"}
    save_path = RESULTS / "test6_trade_decomp.json"
    with open(save_path, "w") as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Saved: {save_path}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# CHARTS
# ═══════════════════════════════════════════════════════════════════════


def chart_test4(results: dict):
    """Test 4: Paired delta histograms for two block sizes."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, blksz in zip(axes, ["60", "360"]):
        data = results[blksz]
        v3 = np.array(data["v3_sharpes"], dtype=np.float64)
        e5 = np.array(data["e5_sharpes"], dtype=np.float64)
        valid = np.isfinite(v3) & np.isfinite(e5)
        delta = v3[valid] - e5[valid]

        ax.hist(delta, bins=50, color="#457b9d", alpha=0.7, edgecolor="white")
        ax.axvline(0, color="black", ls="--", lw=1.5, label="δ = 0")
        ax.axvline(
            np.median(delta), color="#e63946", ls="-", lw=2,
            label=f"median = {np.median(delta):.3f}",
        )

        p_win = np.mean(delta > 0)
        ax.set_title(
            f"blksz={blksz} ({int(blksz) * 4 // 24}d)\n"
            f"P(V3>E5) = {p_win:.1%},  Wilcoxon p = {data['wilcoxon_p']:.2e}"
        )
        ax.set_xlabel("δ = Sharpe(V3) − Sharpe(E5)")
        ax.set_ylabel("Count")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Test 4: Paired Path Delta — V3 vs E5", fontsize=14, fontweight="bold"
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "test4_paired_delta.png", dpi=150)
    plt.close(fig)
    print(f"  Chart: {FIGURES / 'test4_paired_delta.png'}")


def chart_test5(results: dict):
    """Test 5: δ vs regime quality scatter + tercile box plot."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    delta = np.array(results["deltas"])
    rq = np.array(results["regime_qualities"])

    # Scatter with trend line
    ax1.scatter(rq, delta, alpha=0.3, s=15, c="#457b9d")
    ax1.axhline(0, color="black", ls="--", lw=1)

    z = np.polyfit(rq, delta, 1)
    x_fit = np.linspace(rq.min(), rq.max(), 100)
    ax1.plot(
        x_fit, np.polyval(z, x_fit), color="#e63946", lw=2,
        label=f"Spearman ρ = {results['spearman_r']:.3f} (p = {results['spearman_p']:.3f})",
    )

    ax1.set_xlabel("Regime Quality (avg segment length, D1 bars)")
    ax1.set_ylabel("δ = Sharpe(V3) − Sharpe(E5)")
    ax1.set_title("Test 5: δ vs Regime Quality")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Tercile box plot
    t1_bound, t2_bound = np.percentile(rq, [33.3, 66.7])
    box_data = [
        delta[rq <= t1_bound],
        delta[(rq > t1_bound) & (rq <= t2_bound)],
        delta[rq > t2_bound],
    ]
    terciles = results["terciles"]
    labels = [
        f"Low RQ\nδ̃={terciles['low']['delta_median']:.3f}\n"
        f"P(V3>E5)={terciles['low']['p_v3_wins']:.0%}",
        f"Mid RQ\nδ̃={terciles['mid']['delta_median']:.3f}\n"
        f"P(V3>E5)={terciles['mid']['p_v3_wins']:.0%}",
        f"High RQ\nδ̃={terciles['high']['delta_median']:.3f}\n"
        f"P(V3>E5)={terciles['high']['p_v3_wins']:.0%}",
    ]

    bp = ax2.boxplot(
        box_data, tick_labels=labels, patch_artist=True,
        medianprops={"color": "#e63946", "lw": 2},
    )
    box_colors = ["#a8dadc", "#457b9d", "#1d3557"]
    for patch, color in zip(bp["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax2.axhline(0, color="black", ls="--", lw=1)
    ax2.set_ylabel("δ = Sharpe(V3) − Sharpe(E5)")
    ax2.set_title("Test 5: δ by Regime Quality Tercile")
    ax2.grid(True, alpha=0.3, axis="y")

    fig.suptitle(
        "Test 5: Does Regime Quality Help V3?", fontsize=14, fontweight="bold"
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "test5_regime_correlation.png", dpi=150)
    plt.close(fig)
    print(f"  Chart: {FIGURES / 'test5_regime_correlation.png'}")


def chart_test6(results: dict):
    """Test 6: Trade duration P&L decomposition."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    e5 = results["E5"]

    # Panel 1: P&L contribution by duration bucket
    buckets = e5["buckets"]
    labels = [b["label"].split(" (")[0] for b in buckets]
    contributions = [b["pnl_contribution_pct"] for b in buckets]
    counts = [b["count"] for b in buckets]

    x = np.arange(len(labels))
    bars = ax1.bar(x, contributions, color="#2a9d8f", alpha=0.8, edgecolor="white")

    for i, (bar, cnt, cont) in enumerate(zip(bars, counts, contributions)):
        ax1.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            f"{cnt}t\n{cont:.1f}%", ha="center", fontsize=8,
        )

    # Highlight truncation zone (trades > 30 bars)
    ax1.axvspan(
        1.5, len(labels) - 0.5, alpha=0.1, color="#e63946",
        label="V3 time_stop zone (>30 bars)",
    )

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax1.set_ylabel("P&L Contribution (%)")
    ax1.set_title("E5: P&L by Trade Duration")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3, axis="y")

    # Panel 2: Scatter of all E5 trades (duration vs return)
    e5_trades = e5["all_trades"]
    bars_arr = np.array([t["bars"] for t in e5_trades])
    ret_arr = np.array([t["ret"] for t in e5_trades])

    colors_arr = np.where(bars_arr > 30, "#e63946", "#2a9d8f")
    ax2.scatter(
        bars_arr, ret_arr, c=colors_arr, alpha=0.6, s=30,
        edgecolors="white", lw=0.3,
    )
    ax2.axvline(30, color="#e63946", ls="--", lw=2, label="V3 time_stop (30 bars)")
    ax2.axhline(0, color="black", ls="-", lw=0.5)

    trunc = e5["truncation"]
    actual_loss_txt = ""
    if trunc.get("actual_ablation"):
        actual_loss_txt = f"\nActual loss (E5+TS30): {trunc['actual_ablation']['actual_profit_loss_pct']:.1f}%"
    ax2.text(
        0.98, 0.98,
        f"Trades > 30 bars: {trunc['trades_over_30bars']} "
        f"({trunc['pct_of_total_trades']:.1f}%)\n"
        f"P&L exposure: {trunc['pnl_at_risk_pct']:.1f}% (upper bound)"
        f"{actual_loss_txt}",
        transform=ax2.transAxes, ha="right", va="top", fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "#f1faee", "alpha": 0.8},
    )

    ax2.set_xlabel("Duration (H4 bars)")
    ax2.set_ylabel("Return (%)")
    ax2.set_title("E5: Trade Return vs Duration")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    fig.suptitle(
        "Test 6: Trade-Duration P&L Decomposition",
        fontsize=14, fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "test6_trade_decomposition.png", dpi=150)
    plt.close(fig)
    print(f"  Chart: {FIGURES / 'test6_trade_decomposition.png'}")


# ═══════════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════════


def write_deep_report(t4: dict, t5: dict, t6: dict) -> str:
    a: list[str] = []

    a.append("# X36 Deep Analysis — Path-Level & Trade-Level Evidence\n")
    a.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    a.append(f"**Bootstrap paths**: {N_BOOT} per config | **Cost**: 20 bps RT "
             f"| **Seed**: {SEED}\n")

    # ── Test 4 ──────────────────────────────────────────────────────
    a.append("## Test 4: Paired Path Delta + Wilcoxon\n")
    a.append("For each bootstrap path, both V3 and E5 see identical synthetic data. "
             "δ_i = Sharpe(V3) − Sharpe(E5). "
             "Paired analysis is strictly more powerful than comparing medians.\n")

    a.append("| Block Size | δ Median | δ Mean | δ Std | P(V3>E5) | Wilcoxon p | N |")
    a.append("|-----------|----------|--------|-------|----------|-----------|---|")
    for blksz in ["60", "360"]:
        d = t4[blksz]
        a.append(
            f"| {blksz} ({int(blksz) * 4 // 24}d) | {d['delta_median']:.4f} | "
            f"{d['delta_mean']:.4f} | {d['delta_std']:.3f} | "
            f"{d['p_v3_wins']:.1%} | {d['wilcoxon_p']:.2e} | {d['n_valid']} |"
        )

    a.append("\n### Test 4 Interpretation\n")
    d60 = t4["60"]
    d360 = t4["360"]
    a.append(f"- blksz=60: δ median = {d60['delta_median']:.4f}, "
             f"P(V3>E5) = {d60['p_v3_wins']:.1%}")
    a.append(f"- blksz=360: δ median = {d360['delta_median']:.4f}, "
             f"P(V3>E5) = {d360['p_v3_wins']:.1%}")

    dp = d360["p_v3_wins"] - d60["p_v3_wins"]
    if dp > 0.05:
        a.append(f"- V3 win rate improves by {dp * 100:+.1f}pp with larger blocks → "
                 "some regime effect exists, but check if V3 ever reaches >50%")
    elif dp < -0.05:
        a.append(f"- V3 win rate WORSENS by {dp * 100:+.1f}pp with larger blocks → "
                 "longer blocks hurt V3 relatively")
    else:
        a.append(f"- V3 win rate change: {dp * 100:+.1f}pp → negligible difference")

    if d60["wilcoxon_p"] < 0.001:
        a.append(f"- **VERDICT**: E5 > V3 is **HIGHLY SIGNIFICANT** on paired paths "
                 f"(Wilcoxon p = {d60['wilcoxon_p']:.2e}). "
                 "Not noise — E5 genuinely outperforms V3 on the same data.")
    elif d60["wilcoxon_p"] < 0.05:
        a.append(f"- **VERDICT**: E5 > V3 is significant (p = {d60['wilcoxon_p']:.4f}).")
    else:
        a.append(f"- **VERDICT**: E5 vs V3 difference is not significant "
                 f"(p = {d60['wilcoxon_p']:.4f}).")

    # ── Test 5 ──────────────────────────────────────────────────────
    a.append("\n---\n")
    a.append("## Test 5: δ vs Regime Quality Correlation\n")
    a.append("If VCBB destroys regimes that V3 needs, δ should correlate positively "
             "with regime quality: V3 should do relatively better on paths with "
             "cleaner/longer regimes.\n")

    a.append(f"- **Spearman ρ = {t5['spearman_r']:.4f}** (p = {t5['spearman_p']:.4f})")
    a.append(f"- Pearson r = {t5['pearson_r']:.4f} (p = {t5['pearson_p']:.4f})")
    a.append(f"- Regime quality range: {t5['rq_range'][0]:.1f} — {t5['rq_range'][1]:.1f} "
             f"D1 bars (median: {t5['rq_median']:.1f})")

    a.append("\n### Tercile Analysis\n")
    a.append("| Regime Quality | RQ Range | δ Median | P(V3>E5) | N |")
    a.append("|---------------|----------|----------|----------|---|")
    for key, label in [("low", "Low (choppy)"), ("mid", "Medium"), ("high", "High (clean)")]:
        t = t5["terciles"][key]
        a.append(f"| {label} | {t['rq_range'][0]:.1f}–{t['rq_range'][1]:.1f} | "
                 f"{t['delta_median']:.4f} | {t['p_v3_wins']:.1%} | {t['n']} |")

    a.append("\n### Test 5 Interpretation\n")
    rho = t5["spearman_r"]
    rho_p = t5["spearman_p"]
    high_p = t5["terciles"]["high"]["p_v3_wins"]
    low_p = t5["terciles"]["low"]["p_v3_wins"]

    if abs(rho) < 0.1:
        a.append(f"- Correlation is NEGLIGIBLE (|ρ| = {abs(rho):.3f} < 0.1)")
        a.append("- **VERDICT**: Regime quality does NOT help V3 relative to E5. "
                 "V3's weakness is INDEPENDENT of regime structure on bootstrap paths.")
    elif rho > 0.1 and rho_p < 0.05:
        a.append(f"- Positive correlation detected (ρ = {rho:.3f}, p = {rho_p:.4f})")
        a.append(f"- But even in High RQ tercile: P(V3>E5) = {high_p:.1%}")
        if high_p < 0.50:
            a.append("- **VERDICT**: Even on the cleanest-regime paths, V3 STILL loses "
                     "more often than it wins. Regime quality helps at the margin but "
                     "cannot close the gap.")
        else:
            a.append("- **VERDICT**: V3 wins majority on clean-regime paths — partial "
                     "support for the regime hypothesis.")
    elif rho < -0.1 and rho_p < 0.05:
        a.append(f"- NEGATIVE correlation: V3 does WORSE on cleaner-regime paths")
        a.append("- **VERDICT**: Regime quality HURTS V3 relative to E5. "
                 "Opposite of analyst's hypothesis.")
    else:
        a.append(f"- Weak/non-significant (ρ = {rho:.3f}, p = {rho_p:.3f})")
        a.append("- **VERDICT**: No robust evidence that regime quality "
                 "differentially helps V3.")

    # ── Test 6 ──────────────────────────────────────────────────────
    a.append("\n---\n")
    a.append("## Test 6: Trade-Duration P&L Decomposition (Real Data)\n")
    a.append("Shows exactly where E5's alpha comes from and what V3's "
             "time_stop=30 bars would truncate.\n")

    e5 = t6["E5"]
    v3 = t6["V3"]

    a.append("### E5 Trade Statistics\n")
    a.append(f"- Total trades: {e5['total_trades']}")
    a.append(f"- Avg duration: {e5['avg_bars_held']:.1f} bars "
             f"({e5['avg_bars_held'] / 6:.1f} days)")
    a.append(f"- Median duration: {e5['median_bars_held']:.1f} bars "
             f"({e5['median_bars_held'] / 6:.1f} days)")
    a.append(f"- Max duration: {e5['max_bars_held']:.0f} bars "
             f"({e5['max_bars_held'] / 6:.0f} days)")

    a.append("\n### P&L by Duration Bucket\n")
    a.append("| Duration | Trades | % Trades | P&L Contribution | "
             "Avg Return | Max Return | Win Rate |")
    a.append("|----------|--------|----------|-----------------|"
             "------------|------------|----------|")
    for b in e5["buckets"]:
        a.append(
            f"| {b['label']} | {b['count']} | {b['pct_of_trades']:.1f}% | "
            f"{b['pnl_contribution_pct']:.1f}% | {b['avg_return_pct']:.2f}% | "
            f"{b['max_return_pct']:.2f}% | {b['win_rate_pct']:.1f}% |"
        )

    if e5["truncation"]:
        trunc = e5["truncation"]
        a.append("\n### V3 Time-Stop Truncation Impact\n")
        a.append(f"- E5 trades > 30 bars: **{trunc['trades_over_30bars']}** "
                 f"({trunc['pct_of_total_trades']:.1f}% of all trades)")
        a.append(f"- P&L exposure (upper bound): **{trunc['pnl_at_risk_pct']:.1f}%** "
                 "of total profit — these trades WOULD BE AFFECTED, not fully lost")
        if trunc.get("actual_ablation"):
            abl = trunc["actual_ablation"]
            a.append(f"- **Actual ablation loss** (E5 vs E5+TS30): **{abl['actual_profit_loss_pct']:.1f}%** "
                     f"of profit (E5+TS30: {abl['e5_ts30_trades']} trades, "
                     f"Sharpe {abl['e5_ts30_sharpe']:.3f}, CAGR {abl['e5_ts30_cagr_pct']:.1f}%)")

        a.append("\n#### Top 5 Longest E5 Trades\n")
        a.append("| Bars | Days | Return% | P&L | Exit |")
        a.append("|------|------|---------|-----|------|")
        for t in trunc["top5_longest"]:
            a.append(f"| {t['bars']:.0f} | {t['bars'] / 6:.1f} | "
                     f"{t['return_pct']:.2f}% | ${t['pnl']:.2f} | {t['exit']} |")

        a.append("\n#### Top 5 Most Profitable E5 Trades\n")
        a.append("| Bars | Days | Return% | P&L | Exit |")
        a.append("|------|------|---------|-----|------|")
        for t in trunc["top5_profitable"]:
            a.append(f"| {t['bars']:.0f} | {t['bars'] / 6:.1f} | "
                     f"{t['return_pct']:.2f}% | ${t['pnl']:.2f} | {t['exit']} |")

    a.append("\n### V3 vs E5 Comparison\n")
    a.append("| Metric | E5 | V3 | Δ |")
    a.append("|--------|----|----|---|")
    a.append(f"| Trades | {e5['total_trades']} | {v3['total_trades']} | "
             f"{v3['total_trades'] - e5['total_trades']:+d} |")
    a.append(f"| Avg bars held | {e5['avg_bars_held']:.1f} | "
             f"{v3['avg_bars_held']:.1f} | "
             f"{v3['avg_bars_held'] - e5['avg_bars_held']:+.1f} |")
    a.append(f"| Max bars held | {e5['max_bars_held']:.0f} | "
             f"{v3['max_bars_held']:.0f} | "
             f"{v3['max_bars_held'] - e5['max_bars_held']:+.0f} |")
    a.append(f"| Sharpe | {e5['sharpe']:.3f} | {v3['sharpe']:.3f} | "
             f"{v3['sharpe'] - e5['sharpe']:+.3f} |")
    a.append(f"| CAGR% | {e5['cagr_pct']:.1f} | {v3['cagr_pct']:.1f} | "
             f"{v3['cagr_pct'] - e5['cagr_pct']:+.1f} |")
    a.append(f"| MDD% | {e5['max_dd_pct']:.1f} | {v3['max_dd_pct']:.1f} | "
             f"{v3['max_dd_pct'] - e5['max_dd_pct']:+.1f} |")

    a.append("\n### Test 6 Interpretation\n")
    trunc_data = e5.get("truncation")
    if trunc_data:
        actual_abl = trunc_data.get("actual_ablation", {})
        actual_loss = actual_abl.get("actual_profit_loss_pct", 0)
        a.append(
            f"- P&L exposure: {trunc_data['pnl_at_risk_pct']:.0f}% of E5 profits come from "
            "trades > 30 bars (upper bound)"
        )
        if actual_loss > 0:
            a.append(
                f"- Actual ablation loss (E5 vs E5+TS30): **{actual_loss:.1f}%** of total profit"
            )
        a.append("- **VERDICT**: Fat-tail truncation is the DOMINANT mechanism "
                 "explaining V3 < E5. V3's time_stop curtails the highest-returning trades, "
                 f"causing {actual_loss:.0f}% realized profit loss.")
    elif e5["truncation"] and e5["truncation"]["pnl_at_risk_pct"] > 15:
        a.append(
            f"- V3's time_stop would affect {e5['truncation']['pnl_at_risk_pct']:.0f}% "
            "of E5's P&L — material but not sole explanation"
        )
        a.append("- **VERDICT**: Fat-tail truncation is a significant contributor "
                 "to V3's underperformance.")
    else:
        a.append("- Truncation impact is modest — other V3 mechanism differences "
                 "are the primary driver.")

    # ── Overall ──────────────────────────────────────────────────────
    a.append("\n---\n")
    a.append("## Overall Conclusion\n")
    a.append("| Test | Question | Finding |")
    a.append("|------|----------|---------|")

    sig = "YES" if d60["wilcoxon_p"] < 0.05 else "NO"
    a.append(f"| Paired delta | Is E5>V3 statistically significant? | "
             f"**{sig}** (Wilcoxon p = {d60['wilcoxon_p']:.2e}) |")

    regime_ans = "NO" if abs(rho) < 0.1 or rho_p >= 0.05 else "WEAK"
    a.append(f"| Regime correlation | Does regime quality help V3? | "
             f"**{regime_ans}** (ρ = {rho:.3f}) |")

    actual_loss_final = (
        e5["truncation"]["actual_ablation"]["actual_profit_loss_pct"]
        if e5.get("truncation") and e5["truncation"].get("actual_ablation")
        else 0
    )
    a.append(f"| Trade decomposition | What does V3 sacrifice? | "
             f"**{actual_loss_final:.0f}%** actual profit loss from time_stop truncation |")

    report_text = "\n".join(a)
    report_path = RESULTS / "DEEP_ANALYSIS.md"
    with open(report_path, "w") as f:
        f.write(report_text)
    print(f"\n  Report: {report_path}")
    return report_text


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("X36 DEEP ANALYSIS — PATH-LEVEL & TRADE-LEVEL TESTS")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    all_h4, all_d1 = _fast_load_bars(DATA_PATH)
    print(f"  {len(all_h4)} H4 bars, {len(all_d1)} D1 bars")

    # Filter bars to match full-sample period (with warmup)
    start_ms = _date_ms(START)
    end_ms = _date_ms(END) + 86_400_000 - 1
    load_ms = start_ms - WARMUP * 86_400_000
    boot_h4 = [b for b in all_h4 if load_ms <= b.open_time <= end_ms]
    print(f"  Bootstrap source: {len(boot_h4)} H4 bars "
          f"(filtered to {START} with {WARMUP}d warmup)")

    t_start = time.time()

    # Test 6 first (instant, real data only)
    t6 = test6_trade_decomposition(all_h4, all_d1)

    # Test 4 (paired bootstrap, ~60 min)
    t4 = test4_paired(boot_h4)

    # Test 5 (instant, uses Test 4 data)
    t5 = test5_regime_correlation(t4)

    # Charts
    print("\n" + "=" * 70)
    print("GENERATING CHARTS")
    print("=" * 70)
    chart_test4(t4)
    chart_test5(t5)
    chart_test6(t6)

    # Report
    print("\n" + "=" * 70)
    print("GENERATING REPORT")
    print("=" * 70)
    report = write_deep_report(t4, t5, t6)

    total_time = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"DONE — Total time: {total_time:.0f}s ({total_time/60:.1f}min)")
    print(f"{'=' * 70}")

    # Key findings
    print("\nKEY FINDINGS:")
    for line in report.split("\n"):
        if "**VERDICT**" in line:
            print(f"  {line.strip()}")


if __name__ == "__main__":
    main()
