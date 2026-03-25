#!/usr/bin/env python3
"""V10 Drawdown Episode Analysis: top DD events with trade/regime/indicator context.

Identifies the top N equity drawdown episodes, then for each episode:
  - Peak/trough dates, depth, duration, regime labels
  - Trades active or opened during episode (entry/exit reasons, sizing)
  - Trailing stop state: ATR distance, activation status
  - RSI/VDO/HMA at key points (entry, peak, trough)
  - Pyramiding count (adds during the episode)

Output:
  - v10_dd_episodes.csv (top 10 episodes with detailed stats)
  - v10_dd_episodes.json (full detail for report generation)
"""

import csv
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy

DATA_PATH = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
OUTDIR = Path(__file__).resolve().parents[1]
SCENARIO = "harsh"
TOP_N = 10


def ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def ms_to_datetime(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


@dataclass
class DDEpisode:
    rank: int
    peak_idx: int          # index in equity curve
    trough_idx: int
    peak_time_ms: int
    trough_time_ms: int
    peak_nav: float
    trough_nav: float
    depth_pct: float       # (peak - trough) / peak * 100
    duration_bars: int
    duration_days: float
    recovery_idx: int | None   # first bar back to peak NAV (None if no recovery)
    recovery_days: float | None


def find_dd_episodes(equity, top_n=10):
    """Find top N non-overlapping DD episodes from equity curve."""
    if not equity:
        return []

    navs = np.array([e.nav_mid for e in equity])
    n = len(navs)

    # Running max and DD at each point
    running_max = np.maximum.accumulate(navs)
    dd = (running_max - navs) / running_max

    # Find episodes: each episode is a peak→trough segment
    # Use a greedy approach: find deepest DD, mark its range, repeat
    episodes = []
    used = np.zeros(n, dtype=bool)

    for _ in range(top_n * 3):  # overshoot, then trim
        # Mask used indices
        dd_masked = dd.copy()
        dd_masked[used] = 0.0

        if dd_masked.max() < 0.001:
            break

        trough_idx = int(np.argmax(dd_masked))
        depth = dd_masked[trough_idx]

        # Find the peak before this trough
        peak_idx = int(np.argmax(navs[:trough_idx + 1]))

        # Find recovery: first bar after trough where NAV >= peak NAV
        recovery_idx = None
        for ri in range(trough_idx + 1, n):
            if navs[ri] >= navs[peak_idx] * 0.999:  # within 0.1%
                recovery_idx = ri
                break

        # Mark this episode's bars as used
        end_mark = recovery_idx if recovery_idx else min(trough_idx + 100, n)
        used[peak_idx:end_mark] = True

        ep = DDEpisode(
            rank=0,
            peak_idx=peak_idx,
            trough_idx=trough_idx,
            peak_time_ms=equity[peak_idx].close_time,
            trough_time_ms=equity[trough_idx].close_time,
            peak_nav=navs[peak_idx],
            trough_nav=navs[trough_idx],
            depth_pct=depth * 100,
            duration_bars=trough_idx - peak_idx,
            duration_days=(equity[trough_idx].close_time - equity[peak_idx].close_time)
                          / (86_400_000),
            recovery_idx=recovery_idx,
            recovery_days=(
                (equity[recovery_idx].close_time - equity[trough_idx].close_time)
                / 86_400_000 if recovery_idx else None
            ),
        )
        episodes.append(ep)

    # Sort by depth descending, take top_n
    episodes.sort(key=lambda e: -e.depth_pct)
    for i, ep in enumerate(episodes[:top_n]):
        ep.rank = i + 1
    return episodes[:top_n]


def analyze_episode(ep, equity, trades, fills, feed, d1_regimes, v10):
    """Detailed analysis of one DD episode."""
    h4 = feed.h4_bars
    d1 = feed.d1_bars

    # Time range of episode
    t_start = equity[ep.peak_idx].close_time
    t_end = equity[ep.trough_idx].close_time

    # Regime labels during episode
    regime_counts = {}
    for i in range(ep.peak_idx, ep.trough_idx + 1):
        snap = equity[i]
        # Find matching d1 bar for this H4 time
        d1i = -1
        for j in range(len(d1)):
            if d1[j].close_time < snap.close_time:
                d1i = j
            else:
                break
        if 0 <= d1i < len(d1_regimes):
            rname = d1_regimes[d1i]
        else:
            rname = "UNKNOWN"
        regime_counts[rname] = regime_counts.get(rname, 0) + 1

    dominant_regime = max(regime_counts, key=regime_counts.get) if regime_counts else "UNKNOWN"
    regime_pcts = {k: round(v / sum(regime_counts.values()) * 100, 1)
                   for k, v in regime_counts.items()}

    # Trades that overlap with episode
    episode_trades = []
    for t in trades:
        # Trade overlaps if it was open during the episode
        if t.entry_ts_ms <= t_end and t.exit_ts_ms >= t_start:
            episode_trades.append(t)

    # Fills during episode
    episode_fills_buy = [f for f in fills
                         if t_start <= f.ts_ms <= t_end and f.side.name == "BUY"]
    episode_fills_sell = [f for f in fills
                          if t_start <= f.ts_ms <= t_end and f.side.name == "SELL"]

    # Entry reasons during episode
    entry_reasons = {}
    for f in episode_fills_buy:
        entry_reasons[f.reason] = entry_reasons.get(f.reason, 0) + 1

    exit_reasons = {}
    for f in episode_fills_sell:
        exit_reasons[f.reason] = exit_reasons.get(f.reason, 0) + 1

    # Exposure at peak and trough
    exp_peak = equity[ep.peak_idx].exposure
    exp_trough = equity[ep.trough_idx].exposure

    # Max exposure during episode
    max_exp = max(equity[i].exposure for i in range(ep.peak_idx, ep.trough_idx + 1))

    # Indicator values at peak and trough (approximate via bar_index)
    # Map equity index to bar index: equity starts at report_start,
    # bars start from the beginning. We need the offset.
    report_start_ms = feed.report_start_ms
    bar_offset = 0
    for bi, b in enumerate(h4):
        if b.close_time >= report_start_ms:
            bar_offset = bi
            break

    peak_bi = bar_offset + ep.peak_idx
    trough_bi = bar_offset + ep.trough_idx

    def _safe_idx(arr, idx):
        if 0 <= idx < len(arr):
            v = arr[idx]
            if np.isnan(v):
                return None
            return float(v)
        return None

    indicators_peak = {
        "rsi": _safe_idx(v10._h4_rsi, peak_bi),
        "vdo": _safe_idx(v10._h4_vdo, peak_bi),
        "hma": _safe_idx(v10._h4_hma, peak_bi),
        "atr_f": _safe_idx(v10._h4_atr_f, peak_bi),
        "atr_s": _safe_idx(v10._h4_atr_s, peak_bi),
        "accel": _safe_idx(v10._h4_accel, peak_bi),
        "price": h4[peak_bi].close if peak_bi < len(h4) else None,
    }
    indicators_trough = {
        "rsi": _safe_idx(v10._h4_rsi, trough_bi),
        "vdo": _safe_idx(v10._h4_vdo, trough_bi),
        "hma": _safe_idx(v10._h4_hma, trough_bi),
        "atr_f": _safe_idx(v10._h4_atr_f, trough_bi),
        "atr_s": _safe_idx(v10._h4_atr_s, trough_bi),
        "accel": _safe_idx(v10._h4_accel, trough_bi),
        "price": h4[trough_bi].close if trough_bi < len(h4) else None,
    }

    # Trailing stop analysis: how wide was the trail at the point of exit?
    trail_analysis = {}
    for t in episode_trades:
        if t.exit_reason == "trailing_stop":
            # ATR at exit time
            exit_bi = None
            for bi in range(len(h4)):
                if h4[bi].close_time >= t.exit_ts_ms:
                    exit_bi = bi
                    break
            if exit_bi and exit_bi < len(v10._h4_atr_f):
                atr_f = v10._h4_atr_f[exit_bi]
                price = h4[exit_bi].close
                trail_dist_pct = (v10.cfg.trail_atr_mult * atr_f / price * 100
                                  if price > 0 else 0)
                trail_analysis[t.trade_id] = {
                    "atr_f": round(float(atr_f), 2),
                    "trail_mult": v10.cfg.trail_atr_mult,
                    "trail_distance_pct": round(trail_dist_pct, 2),
                    "return_pct": round(t.return_pct, 2),
                    "peak_profit_at_exit_est": round(t.return_pct + trail_dist_pct, 2),
                }

    # BTC price action during episode
    btc_peak = indicators_peak.get("price", 0)
    btc_trough = indicators_trough.get("price", 0)
    btc_dd_pct = ((btc_peak - btc_trough) / btc_peak * 100) if btc_peak else 0

    return {
        "rank": ep.rank,
        "peak_date": ms_to_date(ep.peak_time_ms),
        "trough_date": ms_to_date(ep.trough_time_ms),
        "depth_pct": round(ep.depth_pct, 2),
        "duration_days": round(ep.duration_days, 1),
        "recovery_days": round(ep.recovery_days, 1) if ep.recovery_days else "no_recovery",
        "peak_nav": round(ep.peak_nav, 2),
        "trough_nav": round(ep.trough_nav, 2),
        "btc_peak_price": round(btc_peak, 0) if btc_peak else None,
        "btc_trough_price": round(btc_trough, 0) if btc_trough else None,
        "btc_dd_pct": round(btc_dd_pct, 1),
        "dominant_regime": dominant_regime,
        "regime_distribution": regime_pcts,
        "exposure_at_peak": round(exp_peak, 3),
        "exposure_at_trough": round(exp_trough, 3),
        "max_exposure_during": round(max_exp, 3),
        "n_trades_overlapping": len(episode_trades),
        "n_buy_fills": len(episode_fills_buy),
        "n_sell_fills": len(episode_fills_sell),
        "entry_reasons": entry_reasons,
        "exit_reasons": exit_reasons,
        "trade_details": [
            {
                "id": t.trade_id,
                "entry_date": ms_to_date(t.entry_ts_ms),
                "exit_date": ms_to_date(t.exit_ts_ms),
                "entry_price": round(t.entry_price, 0),
                "exit_price": round(t.exit_price, 0),
                "return_pct": round(t.return_pct, 2),
                "pnl": round(t.pnl, 2),
                "days_held": round(t.days_held, 1),
                "entry_reason": t.entry_reason,
                "exit_reason": t.exit_reason,
            }
            for t in episode_trades
        ],
        "indicators_at_peak": indicators_peak,
        "indicators_at_trough": indicators_trough,
        "trailing_stop_analysis": trail_analysis,
    }


def main():
    t0 = time.time()
    print("=" * 70)
    print("  V10 DRAWDOWN EPISODE ANALYSIS")
    print("=" * 70)

    # Run V10 backtest
    cost = SCENARIOS[SCENARIO]
    v10 = V8ApexStrategy(V8ApexConfig())
    feed = DataFeed(DATA_PATH, start=START, end=END, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=v10, cost=cost,
                            initial_cash=INITIAL_CASH, warmup_mode="no_trade")
    result = engine.run()

    print(f"  Period: {START} → {END}")
    print(f"  Scenario: {SCENARIO}")
    print(f"  Equity points: {len(result.equity)}")
    print(f"  Trades: {len(result.trades)}")
    print(f"  Fills: {len(result.fills)}")
    print(f"  Final NAV: {result.summary.get('final_nav_mid', 0):.2f}")
    print(f"  MDD: {result.summary.get('max_drawdown_mid_pct', 0):.2f}%")
    print()

    # Classify D1 regimes
    d1_regimes = classify_d1_regimes(feed.d1_bars)
    # d1_regimes is a dict or list — need to check format
    # It returns list of (AnalyticalRegime enum) values per D1 bar
    regime_names = []
    for r in d1_regimes:
        regime_names.append(r.name if hasattr(r, 'name') else str(r))

    # Find top DD episodes
    episodes = find_dd_episodes(result.equity, TOP_N)
    print(f"  Found {len(episodes)} DD episodes")
    print()

    # Analyze each episode
    all_details = []
    print(f"{'Rank':>4} {'Peak':>12} {'Trough':>12} {'Depth%':>8} {'Days':>6} "
          f"{'BTC DD%':>8} {'Regime':>12} {'Trades':>7} {'Buys':>5} {'Recovery':>10}")
    print("-" * 100)

    for ep in episodes:
        detail = analyze_episode(ep, result.equity, result.trades, result.fills,
                                 feed, regime_names, v10)
        all_details.append(detail)

        print(f"{detail['rank']:>4} {detail['peak_date']:>12} {detail['trough_date']:>12} "
              f"{detail['depth_pct']:>8.2f} {detail['duration_days']:>6.0f} "
              f"{detail['btc_dd_pct']:>8.1f} {detail['dominant_regime']:>12} "
              f"{detail['n_trades_overlapping']:>7} {detail['n_buy_fills']:>5} "
              f"{str(detail['recovery_days']):>10}")

    # ── Aggregate analysis ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  AGGREGATE ANALYSIS")
    print("=" * 70)

    # Regime distribution across all episodes
    regime_agg = {}
    for d in all_details:
        for r, pct in d["regime_distribution"].items():
            regime_agg.setdefault(r, []).append(pct)
    print("\n  Regime distribution across top 10 DD episodes:")
    for r, pcts in sorted(regime_agg.items(), key=lambda x: -np.mean(x[1])):
        print(f"    {r:12s}: mean={np.mean(pcts):5.1f}%, "
              f"max={max(pcts):5.1f}%, count={len(pcts)}")

    # Entry reasons during DDs
    entry_agg = {}
    for d in all_details:
        for reason, count in d["entry_reasons"].items():
            entry_agg[reason] = entry_agg.get(reason, 0) + count
    print(f"\n  Buy fills during DD episodes:")
    for reason, count in sorted(entry_agg.items(), key=lambda x: -x[1]):
        print(f"    {reason:25s}: {count}")

    # Exit reasons during DDs
    exit_agg = {}
    for d in all_details:
        for reason, count in d["exit_reasons"].items():
            exit_agg[reason] = exit_agg.get(reason, 0) + count
    print(f"\n  Sell fills during DD episodes:")
    for reason, count in sorted(exit_agg.items(), key=lambda x: -x[1]):
        print(f"    {reason:25s}: {count}")

    # Trailing stop analysis
    all_trails = {}
    for d in all_details:
        all_trails.update(d["trailing_stop_analysis"])
    if all_trails:
        trail_dists = [v["trail_distance_pct"] for v in all_trails.values()]
        print(f"\n  Trailing stop exits during DDs:")
        print(f"    Count: {len(all_trails)}")
        print(f"    Trail distance (ATR*{v10.cfg.trail_atr_mult}): "
              f"mean={np.mean(trail_dists):.1f}%, "
              f"max={max(trail_dists):.1f}%")

    # Exposure analysis
    max_exps = [d["max_exposure_during"] for d in all_details]
    peak_exps = [d["exposure_at_peak"] for d in all_details]
    buy_counts = [d["n_buy_fills"] for d in all_details]
    print(f"\n  Exposure during DD episodes:")
    print(f"    Exposure at peak:  mean={np.mean(peak_exps):.2f}, "
          f"max={max(peak_exps):.2f}")
    print(f"    Max during episode: mean={np.mean(max_exps):.2f}, "
          f"max={max(max_exps):.2f}")
    print(f"    Buy fills (pyramiding): mean={np.mean(buy_counts):.1f}, "
          f"max={max(buy_counts)}")

    # TOPPING-specific episodes
    topping_eps = [d for d in all_details
                   if d["regime_distribution"].get("TOPPING", 0) > 20]
    print(f"\n  Episodes with significant TOPPING regime (>20%):")
    print(f"    Count: {len(topping_eps)}")
    if topping_eps:
        for te in topping_eps:
            print(f"    Rank {te['rank']}: {te['peak_date']}→{te['trough_date']} "
                  f"depth={te['depth_pct']:.1f}% "
                  f"TOPPING={te['regime_distribution'].get('TOPPING', 0)}%")

    # ── Write CSV ────────────────────────────────────────────────────────
    csv_path = OUTDIR / "v10_dd_episodes.csv"
    fieldnames = [
        "rank", "peak_date", "trough_date", "depth_pct", "duration_days",
        "recovery_days", "peak_nav", "trough_nav",
        "btc_peak_price", "btc_trough_price", "btc_dd_pct",
        "dominant_regime", "exposure_at_peak", "exposure_at_trough",
        "max_exposure_during", "n_trades_overlapping",
        "n_buy_fills", "n_sell_fills",
        "entry_reasons", "exit_reasons",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for d in all_details:
            row = dict(d)
            row["entry_reasons"] = json.dumps(d["entry_reasons"])
            row["exit_reasons"] = json.dumps(d["exit_reasons"])
            writer.writerow(row)
    print(f"\n  CSV saved: {csv_path}")

    # ── Write JSON ───────────────────────────────────────────────────────
    def _c(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    json_path = OUTDIR / "v10_dd_episodes.json"
    json_data = {
        "scenario": SCENARIO,
        "period": f"{START} → {END}",
        "warmup_days": WARMUP_DAYS,
        "total_trades": len(result.trades),
        "final_nav": result.summary.get("final_nav_mid", 0),
        "mdd_pct": result.summary.get("max_drawdown_mid_pct", 0),
        "episodes": all_details,
        "aggregate": {
            "regime_distribution": {k: round(np.mean(v), 1)
                                    for k, v in regime_agg.items()},
            "entry_reasons_total": entry_agg,
            "exit_reasons_total": exit_agg,
            "trail_count": len(all_trails),
            "trail_mean_distance_pct": round(np.mean(trail_dists), 2) if all_trails else 0,
            "mean_max_exposure": round(np.mean(max_exps), 3),
            "mean_buy_fills_per_episode": round(np.mean(buy_counts), 1),
            "topping_episodes_count": len(topping_eps),
        },
        "v10_config": {
            "trail_atr_mult": v10.cfg.trail_atr_mult,
            "trail_activate_pct": v10.cfg.trail_activate_pct,
            "trail_tighten_mult": v10.cfg.trail_tighten_mult,
            "trail_tighten_profit_pct": v10.cfg.trail_tighten_profit_pct,
            "fixed_stop_pct": v10.cfg.fixed_stop_pct,
            "emergency_dd_pct": v10.cfg.emergency_dd_pct,
            "entry_aggression": v10.cfg.entry_aggression,
            "max_add_per_bar": v10.cfg.max_add_per_bar,
            "max_total_exposure": v10.cfg.max_total_exposure,
            "entry_cooldown_bars": v10.cfg.entry_cooldown_bars,
            "rsi_overbought": v10.cfg.rsi_overbought,
            "rsi_oversold": v10.cfg.rsi_oversold,
            "vdo_entry_threshold": v10.cfg.vdo_entry_threshold,
        },
    }
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2, default=_c)
    print(f"  JSON saved: {json_path}")

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
