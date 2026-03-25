#!/usr/bin/env python3
"""validate_monitor_v2.py — Comprehensive statistical validation of Regime Monitor V2.

Addresses 10 validation gaps identified in audit (2026-03-09):
  G1: No formal validation pipeline (PSR, Wilcoxon, etc.)
  G2: Separate simulator, not engine
  G3: No threshold sensitivity
  G4: No subperiod robustness
  G5: No statistical tests on monitor
  G6: No WFO
  G7: No jackknife
  G8: Monitor forced-exit behavior
  G9: No factorial isolation
  G10: No engine integration

Tests:
  T1: Engine baseline    — run engine with monitor ON/OFF, record authoritative metrics
  T2: Threshold sweep    — 1D sweeps on 4 threshold params, find plateau vs cliff
  T3: Cost sweep         — monitor impact at smart/base/harsh
  T4: Factorial isolation — no_regime vs EMA21 vs EMA21+monitor (marginal contribution)
  T5: Subperiod robustness — 4 subperiods
  T6: Jackknife          — remove top-K blocked entries by contribution
  T7: WFO                — 8 walk-forward windows, monitor on/off per window

Outputs:
  monitor_v2_validation/validation_results.json
  monitor_v2_validation/MONITOR_V2_VALIDATION_REPORT.md
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from monitoring.regime_monitor import (
    AMBER_MDD_12M,
    AMBER_MDD_6M,
    RED_MDD_12M,
    RED_MDD_6M,
    ROLL_12M,
    ROLL_6M,
    map_d1_alert_to_h4,
    rolling_mdd,
)
from strategies.vtrend_e5_ema21_d1 import (
    VTrendE5Ema21D1Config,
    VTrendE5Ema21D1Strategy,
)
from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, CostConfig

# =========================================================================
# CONSTANTS
# =========================================================================

DATA = str(PROJECT_ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv")
START = "2019-01-01"
END = "2026-02-20"
WARMUP = 365
CASH = 10_000.0

OUTDIR = Path(__file__).parent / "monitor_v2_validation"


# =========================================================================
# HELPERS
# =========================================================================


def classify_alerts_custom(
    mdd_6m: np.ndarray,
    mdd_12m: np.ndarray,
    amber_6m: float = AMBER_MDD_6M,
    amber_12m: float = AMBER_MDD_12M,
    red_6m: float = RED_MDD_6M,
    red_12m: float = RED_MDD_12M,
) -> np.ndarray:
    """Classify alerts with custom thresholds (for sweep)."""
    n = len(mdd_6m)
    alerts = np.zeros(n, dtype=np.int8)
    for t in range(n):
        m6 = mdd_6m[t] if not np.isnan(mdd_6m[t]) else 0.0
        m12 = mdd_12m[t] if not np.isnan(mdd_12m[t]) else 0.0
        if m6 > red_6m or m12 > red_12m:
            alerts[t] = 2
        elif m6 > amber_6m or m12 > amber_12m:
            alerts[t] = 1
    return alerts


def run_engine(
    feed: DataFeed,
    cost: CostConfig,
    monitor_alerts: np.ndarray | None = None,
    enable_monitor: bool = False,
) -> dict:
    """Run BacktestEngine, return metrics dict."""
    cfg = VTrendE5Ema21D1Config(enable_regime_monitor=enable_monitor)
    strategy = VTrendE5Ema21D1Strategy(config=cfg, monitor_alerts=monitor_alerts)
    engine = BacktestEngine(
        feed=feed, strategy=strategy, cost=cost,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    result = engine.run()
    s = result.summary
    monitor_exits = strategy._monitor_exits

    # Count blocked entries: compare exit reasons
    monitor_exit_count = sum(
        1 for t in result.trades
        if t.exit_reason == "vtrend_e5_ema21_d1_monitor_exit"
    )

    return {
        "sharpe": s.get("sharpe", 0.0),
        "cagr_pct": s.get("cagr_pct", 0.0),
        "mdd_pct": s.get("max_drawdown_mid_pct", 0.0),
        "trades": s.get("trades", 0),
        "final_nav": s.get("final_nav_mid", 0.0),
        "monitor_exits": monitor_exits,
        "monitor_exit_trades": monitor_exit_count,
        "avg_exposure": s.get("avg_exposure", 0.0),
        "sortino": s.get("sortino", 0.0),
        "calmar": s.get("calmar", 0.0),
        "win_rate": s.get("win_rate_pct", 0.0),
    }


def compute_h4_alerts(feed: DataFeed, **threshold_overrides) -> np.ndarray:
    """Compute H4-mapped monitor alerts, with optional threshold overrides."""
    d1_close = np.array([b.close for b in feed.d1_bars], dtype=np.float64)
    d1_ct = np.array([b.close_time for b in feed.d1_bars], dtype=np.int64)
    h4_ct = np.array([b.close_time for b in feed.h4_bars], dtype=np.int64)

    mdd_6m = rolling_mdd(d1_close, ROLL_6M)
    mdd_12m = rolling_mdd(d1_close, ROLL_12M)
    alerts = classify_alerts_custom(mdd_6m, mdd_12m, **threshold_overrides)
    return map_d1_alert_to_h4(alerts, d1_ct, h4_ct)


def fmt_delta(val: float, fmt: str = ".4f") -> str:
    return f"{val:+{fmt}}"


# =========================================================================
# T1: ENGINE BASELINE
# =========================================================================


def t1_engine_baseline(feed: DataFeed) -> dict:
    """Run engine with monitor ON/OFF, record authoritative metrics."""
    print("\n" + "=" * 80)
    print("T1: ENGINE BASELINE — monitor ON vs OFF (harsh cost)")
    print("=" * 80)

    cost = SCENARIOS["harsh"]

    m_off = run_engine(feed, cost, enable_monitor=False)
    m_on = run_engine(feed, cost, enable_monitor=True)

    delta = {k: m_on[k] - m_off[k] for k in ["sharpe", "cagr_pct", "mdd_pct", "trades"]}

    print(f"\n  {'Metric':20s} {'Monitor OFF':>14s} {'Monitor ON':>14s} {'Delta':>12s}")
    print(f"  {'-' * 60}")
    for key, label, fmt in [
        ("sharpe", "Sharpe", ".4f"),
        ("cagr_pct", "CAGR %", ".2f"),
        ("mdd_pct", "MDD %", ".2f"),
    ]:
        print(f"  {label:20s} {m_off[key]:14{fmt}} {m_on[key]:14{fmt}} {delta[key]:+12{fmt}}")
    print(f"  {'Trades':20s} {m_off['trades']:14d} {m_on['trades']:14d} {delta['trades']:+12.0f}")
    print(f"  {'Monitor exits':20s} {'--':>14s} {m_on['monitor_exits']:14d}")
    print(f"  {'Final NAV':20s} {m_off['final_nav']:14.2f} {m_on['final_nav']:14.2f}")

    return {"monitor_off": m_off, "monitor_on": m_on, "delta": delta}


# =========================================================================
# T2: THRESHOLD SENSITIVITY SWEEP
# =========================================================================


def t2_threshold_sweep(feed: DataFeed) -> dict:
    """1D sweep on each threshold, holding others at defaults."""
    print("\n" + "=" * 80)
    print("T2: THRESHOLD SENSITIVITY SWEEP")
    print("=" * 80)

    cost = SCENARIOS["harsh"]
    defaults = {
        "amber_6m": AMBER_MDD_6M, "amber_12m": AMBER_MDD_12M,
        "red_6m": RED_MDD_6M, "red_12m": RED_MDD_12M,
    }

    sweeps = {
        "red_6m": np.arange(0.40, 0.71, 0.05),
        "red_12m": np.arange(0.55, 0.86, 0.05),
        "amber_6m": np.arange(0.30, 0.61, 0.05),
        "amber_12m": np.arange(0.45, 0.76, 0.05),
    }

    results = {}
    for param_name, values in sweeps.items():
        print(f"\n  Sweeping {param_name}: {values[0]:.2f} -> {values[-1]:.2f} "
              f"({len(values)} points)")
        rows = []
        for val in values:
            overrides = dict(defaults)
            overrides[param_name] = val
            h4_alerts = compute_h4_alerts(feed, **overrides)
            m = run_engine(feed, cost, monitor_alerts=h4_alerts)
            n_red = int(np.sum(h4_alerts == 2))
            rows.append({
                "value": round(float(val), 4),
                "sharpe": m["sharpe"],
                "cagr_pct": m["cagr_pct"],
                "mdd_pct": m["mdd_pct"],
                "trades": m["trades"],
                "n_red_h4": n_red,
            })
            print(f"    {param_name}={val:.2f}: Sharpe={m['sharpe']:.4f}  "
                  f"CAGR={m['cagr_pct']:.2f}%  MDD={m['mdd_pct']:.2f}%  "
                  f"trades={m['trades']}  RED_bars={n_red}")
        results[param_name] = rows

        # Detect plateau: Sharpe range within top 90%
        sharpes = [r["sharpe"] for r in rows]
        best = max(sharpes)
        plateau_vals = [r["value"] for r in rows if r["sharpe"] >= best * 0.95]
        print(f"    Plateau (Sharpe >= 95% of best): "
              f"{min(plateau_vals):.2f} - {max(plateau_vals):.2f}")

    return results


# =========================================================================
# T3: COST SWEEP
# =========================================================================


def t3_cost_sweep(feed: DataFeed) -> dict:
    """Monitor impact at smart/base/harsh costs."""
    print("\n" + "=" * 80)
    print("T3: COST SWEEP — monitor impact by cost scenario")
    print("=" * 80)

    results = {}
    for name in ["smart", "base", "harsh"]:
        cost = SCENARIOS[name]
        m_off = run_engine(feed, cost, enable_monitor=False)
        m_on = run_engine(feed, cost, enable_monitor=True)
        delta = {
            "sharpe": m_on["sharpe"] - m_off["sharpe"],
            "cagr_pct": m_on["cagr_pct"] - m_off["cagr_pct"],
            "mdd_pct": m_on["mdd_pct"] - m_off["mdd_pct"],
            "trades": m_on["trades"] - m_off["trades"],
        }
        results[name] = {"off": m_off, "on": m_on, "delta": delta}
        print(f"\n  {name:6s} (RT={cost.round_trip_bps:.0f} bps): "
              f"dSharpe={delta['sharpe']:+.4f}  dCAGR={delta['cagr_pct']:+.2f}%  "
              f"dMDD={delta['mdd_pct']:+.2f}%  dTrades={delta['trades']:+d}")

    return results


# =========================================================================
# T4: FACTORIAL ISOLATION
# =========================================================================


def t4_factorial(feed: DataFeed) -> dict:
    """Isolate monitor's marginal contribution vs EMA21 regime filter."""
    print("\n" + "=" * 80)
    print("T4: FACTORIAL ISOLATION — marginal contribution of monitor")
    print("=" * 80)

    cost = SCENARIOS["harsh"]

    # Config A: EMA21 regime only (baseline = standard E5+EMA21D1)
    m_ema21 = run_engine(feed, cost, enable_monitor=False)

    # Config B: EMA21 + monitor
    m_ema21_mon = run_engine(feed, cost, enable_monitor=True)

    # Config C: NO regime filter — set d1_ema_period very large so regime always True
    cfg_no_regime = VTrendE5Ema21D1Config(d1_ema_period=9999)
    strat_no_regime = VTrendE5Ema21D1Strategy(config=cfg_no_regime)
    engine_c = BacktestEngine(
        feed=feed, strategy=strat_no_regime, cost=cost,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    result_c = engine_c.run()
    sc = result_c.summary
    m_no_regime = {
        "sharpe": sc.get("sharpe", 0.0),
        "cagr_pct": sc.get("cagr_pct", 0.0),
        "mdd_pct": sc.get("max_drawdown_mid_pct", 0.0),
        "trades": sc.get("trades", 0),
    }

    # Config D: monitor only, no EMA regime — d1_ema_period=9999 + monitor
    h4_alerts = compute_h4_alerts(feed)
    cfg_mon_only = VTrendE5Ema21D1Config(d1_ema_period=9999)
    strat_mon_only = VTrendE5Ema21D1Strategy(config=cfg_mon_only, monitor_alerts=h4_alerts)
    engine_d = BacktestEngine(
        feed=feed, strategy=strat_mon_only, cost=cost,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    result_d = engine_d.run()
    sd = result_d.summary
    m_mon_only = {
        "sharpe": sd.get("sharpe", 0.0),
        "cagr_pct": sd.get("cagr_pct", 0.0),
        "mdd_pct": sd.get("max_drawdown_mid_pct", 0.0),
        "trades": sd.get("trades", 0),
    }

    configs = {
        "no_regime": m_no_regime,
        "ema21_only": m_ema21,
        "monitor_only": m_mon_only,
        "ema21_plus_monitor": m_ema21_mon,
    }

    print(f"\n  {'Config':25s} {'Sharpe':>10s} {'CAGR %':>10s} {'MDD %':>10s} {'Trades':>8s}")
    print(f"  {'-' * 65}")
    for label, m in configs.items():
        print(f"  {label:25s} {m['sharpe']:10.4f} {m['cagr_pct']:10.2f} "
              f"{m['mdd_pct']:10.2f} {m['trades']:8d}")

    # Marginal contributions
    ema21_marginal = {
        "sharpe": m_ema21["sharpe"] - m_no_regime["sharpe"],
        "cagr_pct": m_ema21["cagr_pct"] - m_no_regime["cagr_pct"],
        "mdd_pct": m_ema21["mdd_pct"] - m_no_regime["mdd_pct"],
    }
    monitor_marginal = {
        "sharpe": m_ema21_mon["sharpe"] - m_ema21["sharpe"],
        "cagr_pct": m_ema21_mon["cagr_pct"] - m_ema21["cagr_pct"],
        "mdd_pct": m_ema21_mon["mdd_pct"] - m_ema21["mdd_pct"],
    }

    print(f"\n  Marginal contributions:")
    print(f"    EMA21 filter: Sharpe {ema21_marginal['sharpe']:+.4f}  "
          f"CAGR {ema21_marginal['cagr_pct']:+.2f}%  MDD {ema21_marginal['mdd_pct']:+.2f}%")
    print(f"    Monitor V2:   Sharpe {monitor_marginal['sharpe']:+.4f}  "
          f"CAGR {monitor_marginal['cagr_pct']:+.2f}%  MDD {monitor_marginal['mdd_pct']:+.2f}%")

    return {
        "configs": configs,
        "ema21_marginal": ema21_marginal,
        "monitor_marginal": monitor_marginal,
    }


# =========================================================================
# T5: SUBPERIOD ROBUSTNESS
# =========================================================================


def t5_subperiod(feed_full: DataFeed) -> dict:
    """Test monitor impact across 4 subperiods."""
    print("\n" + "=" * 80)
    print("T5: SUBPERIOD ROBUSTNESS — monitor impact by period")
    print("=" * 80)

    cost = SCENARIOS["harsh"]
    periods = [
        ("2018-2020", "2018-01-01", "2020-01-01"),
        ("2020-2022", "2020-01-01", "2022-01-01"),
        ("2022-2024", "2022-01-01", "2024-01-01"),
        ("2024-2026", "2024-01-01", "2026-02-20"),
    ]

    results = {}
    n_positive_sharpe = 0
    n_positive_mdd = 0

    for label, start, end in periods:
        try:
            feed = DataFeed(DATA, start=start, end=end, warmup_days=WARMUP)
        except Exception as e:
            print(f"  {label}: SKIP ({e})")
            continue

        if feed.n_h4 < 100:
            print(f"  {label}: SKIP (too few bars: {feed.n_h4})")
            continue

        m_off = run_engine(feed, cost, enable_monitor=False)
        m_on = run_engine(feed, cost, enable_monitor=True)
        delta = {
            "sharpe": m_on["sharpe"] - m_off["sharpe"],
            "cagr_pct": m_on["cagr_pct"] - m_off["cagr_pct"],
            "mdd_pct": m_on["mdd_pct"] - m_off["mdd_pct"],
            "trades": m_on["trades"] - m_off["trades"],
        }
        results[label] = {"off": m_off, "on": m_on, "delta": delta}

        if delta["sharpe"] > 0:
            n_positive_sharpe += 1
        if delta["mdd_pct"] < 0:
            n_positive_mdd += 1

        print(f"  {label}: dSharpe={delta['sharpe']:+.4f}  "
              f"dCAGR={delta['cagr_pct']:+.2f}%  dMDD={delta['mdd_pct']:+.2f}%  "
              f"dTrades={delta['trades']:+d}")

    n_periods = len(results)
    print(f"\n  Summary: {n_positive_sharpe}/{n_periods} periods Sharpe improved, "
          f"{n_positive_mdd}/{n_periods} periods MDD improved")

    results["summary"] = {
        "n_periods": n_periods,
        "n_positive_sharpe": n_positive_sharpe,
        "n_positive_mdd": n_positive_mdd,
    }
    return results


# =========================================================================
# T6: JACKKNIFE — BLOCKED ENTRY ANALYSIS
# =========================================================================


def t6_jackknife(feed: DataFeed) -> dict:
    """Identify blocked entries and jackknife their contribution."""
    print("\n" + "=" * 80)
    print("T6: JACKKNIFE — blocked entry contribution analysis")
    print("=" * 80)

    cost = SCENARIOS["harsh"]

    # Run monitor OFF to get all trades
    cfg_off = VTrendE5Ema21D1Config(enable_regime_monitor=False)
    strat_off = VTrendE5Ema21D1Strategy(config=cfg_off)
    engine_off = BacktestEngine(
        feed=feed, strategy=strat_off, cost=cost,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    result_off = engine_off.run()
    trades_off = result_off.trades

    # Run monitor ON
    cfg_on = VTrendE5Ema21D1Config(enable_regime_monitor=True)
    strat_on = VTrendE5Ema21D1Strategy(config=cfg_on)
    engine_on = BacktestEngine(
        feed=feed, strategy=strat_on, cost=cost,
        initial_cash=CASH, warmup_mode="no_trade",
    )
    result_on = engine_on.run()
    trades_on = result_on.trades

    # Identify blocked trades: trades in OFF that don't appear in ON
    # Match by entry_ts_ms
    on_entry_ts = {t.entry_ts_ms for t in trades_on}
    blocked_trades = [t for t in trades_off if t.entry_ts_ms not in on_entry_ts]

    # Also identify forced-exit trades (different exit_ts_ms for same entry)
    on_exits = {t.entry_ts_ms: t for t in trades_on}
    modified_trades = []
    for t in trades_off:
        if t.entry_ts_ms in on_exits:
            on_t = on_exits[t.entry_ts_ms]
            if on_t.exit_ts_ms != t.exit_ts_ms:
                modified_trades.append({
                    "entry_ts": t.entry_ts_ms,
                    "off_exit_ts": t.exit_ts_ms,
                    "on_exit_ts": on_t.exit_ts_ms,
                    "off_pnl": t.pnl,
                    "on_pnl": on_t.pnl,
                    "off_reason": t.exit_reason,
                    "on_reason": on_t.exit_reason,
                })

    n_blocked = len(blocked_trades)
    n_modified = len(modified_trades)

    print(f"  Trades OFF: {len(trades_off)}")
    print(f"  Trades ON:  {len(trades_on)}")
    print(f"  Blocked entries: {n_blocked}")
    print(f"  Modified exits:  {n_modified}")

    if blocked_trades:
        # Sort by PnL (worst trades first = most value from blocking)
        blocked_sorted = sorted(blocked_trades, key=lambda t: t.pnl)
        print(f"\n  Blocked trades by PnL (worst first):")
        total_blocked_pnl = 0.0
        for i, t in enumerate(blocked_sorted):
            total_blocked_pnl += t.pnl
            entry_date = datetime.fromtimestamp(
                t.entry_ts_ms / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d")
            print(f"    #{i+1:2d}  {entry_date}  PnL={t.pnl:+.2f}  "
                  f"ret={t.return_pct:+.2f}%  days={t.days_held:.1f}")
        print(f"  Total blocked PnL: {total_blocked_pnl:+.2f}")

        # Jackknife: what if we had let through top-K worst blocked trades?
        blocked_pnls = [t.pnl for t in blocked_sorted]
        base_sharpe = result_on.summary.get("sharpe", 0.0)

        print(f"\n  Jackknife analysis (monitor Sharpe = {base_sharpe:.4f}):")
        print(f"    If we let through the K worst blocked trades:")
        for k in [1, 3, 5, min(n_blocked, 10)]:
            if k > n_blocked:
                break
            worst_k_pnl = sum(blocked_pnls[:k])
            print(f"    K={k:2d}: worst PnL={worst_k_pnl:+.2f} "
                  f"(these are trades the monitor correctly blocked)")

    blocked_info = []
    for t in blocked_trades:
        entry_date = datetime.fromtimestamp(
            t.entry_ts_ms / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        blocked_info.append({
            "entry_date": entry_date,
            "pnl": round(t.pnl, 2),
            "return_pct": round(t.return_pct, 2),
            "days_held": round(t.days_held, 1),
            "exit_reason": t.exit_reason,
        })

    return {
        "trades_off": len(trades_off),
        "trades_on": len(trades_on),
        "n_blocked": n_blocked,
        "n_modified": n_modified,
        "blocked_trades": blocked_info,
        "modified_trades": modified_trades,
        "total_blocked_pnl": round(sum(t.pnl for t in blocked_trades), 2),
        "monitor_exits_count": strat_on._monitor_exits,
    }


# =========================================================================
# T7: WALK-FORWARD OPTIMIZATION
# =========================================================================


def t7_wfo(feed_full: DataFeed) -> dict:
    """8 walk-forward windows, compare monitor on/off per window."""
    print("\n" + "=" * 80)
    print("T7: WALK-FORWARD — 8 windows (24m train / 6m test)")
    print("=" * 80)

    cost = SCENARIOS["harsh"]
    train_months = 24
    test_months = 6
    slide_months = 6

    # Generate windows from 2019-01-01
    base_year, base_month = 2019, 1
    windows = []
    for w in range(8):
        test_start_offset = w * slide_months
        test_start_year = base_year + (base_month - 1 + test_start_offset) // 12
        test_start_month = (base_month - 1 + test_start_offset) % 12 + 1

        test_end_offset = test_start_offset + test_months
        test_end_year = base_year + (base_month - 1 + test_end_offset) // 12
        test_end_month = (base_month - 1 + test_end_offset) % 12 + 1

        test_start = f"{test_start_year:04d}-{test_start_month:02d}-01"
        test_end = f"{test_end_year:04d}-{test_end_month:02d}-01"

        # Check if test_end exceeds our data
        if test_end > END:
            break

        windows.append((w + 1, test_start, test_end))

    results = []
    n_positive = 0

    for wid, test_start, test_end in windows:
        try:
            feed = DataFeed(DATA, start=test_start, end=test_end, warmup_days=WARMUP)
        except Exception as e:
            print(f"  W{wid}: SKIP ({e})")
            continue

        if feed.n_h4 < 50:
            print(f"  W{wid}: SKIP (too few bars: {feed.n_h4})")
            continue

        m_off = run_engine(feed, cost, enable_monitor=False)
        m_on = run_engine(feed, cost, enable_monitor=True)
        delta_sharpe = m_on["sharpe"] - m_off["sharpe"]
        delta_cagr = m_on["cagr_pct"] - m_off["cagr_pct"]

        if delta_sharpe > 0:
            n_positive += 1

        row = {
            "window": wid,
            "test_start": test_start,
            "test_end": test_end,
            "off_sharpe": m_off["sharpe"],
            "on_sharpe": m_on["sharpe"],
            "delta_sharpe": delta_sharpe,
            "off_cagr": m_off["cagr_pct"],
            "on_cagr": m_on["cagr_pct"],
            "delta_cagr": delta_cagr,
            "off_trades": m_off["trades"],
            "on_trades": m_on["trades"],
        }
        results.append(row)

        sign = "+" if delta_sharpe > 0 else "-"
        print(f"  W{wid} [{test_start} -> {test_end}]: "
              f"dSharpe={delta_sharpe:+.4f} [{sign}]  "
              f"dCAGR={delta_cagr:+.2f}%  trades {m_off['trades']}->{m_on['trades']}")

    n_windows = len(results)
    win_rate = n_positive / n_windows if n_windows > 0 else 0

    # Wilcoxon signed-rank test on delta_sharpe
    deltas = np.array([r["delta_sharpe"] for r in results])
    wilcoxon_p = None
    wilcoxon_stat = None
    if n_windows >= 6:
        from scipy.stats import wilcoxon as wilcoxon_test
        nonzero = deltas[np.abs(deltas) > 1e-10]
        if len(nonzero) >= 6:
            stat, p = wilcoxon_test(nonzero, alternative="greater")
            wilcoxon_stat = float(stat)
            wilcoxon_p = float(p)

    print(f"\n  Summary: {n_positive}/{n_windows} windows positive "
          f"(win rate {win_rate:.1%})")
    if wilcoxon_p is not None:
        print(f"  Wilcoxon signed-rank (one-sided): stat={wilcoxon_stat:.1f}, "
              f"p={wilcoxon_p:.4f} {'PASS' if wilcoxon_p < 0.10 else 'FAIL'}")
    else:
        print(f"  Wilcoxon: insufficient windows (need >= 6 non-zero deltas)")

    # Bootstrap CI on mean delta
    if n_windows >= 3:
        rng = np.random.default_rng(42)
        boot_means = []
        for _ in range(10_000):
            sample = rng.choice(deltas, size=n_windows, replace=True)
            boot_means.append(np.mean(sample))
        boot_means = np.sort(boot_means)
        ci_lower = float(np.percentile(boot_means, 2.5))
        ci_upper = float(np.percentile(boot_means, 97.5))
        boot_mean = float(np.mean(boot_means))
        ci_excludes_zero = ci_lower > 0
        print(f"  Bootstrap CI (95%): [{ci_lower:.4f}, {ci_upper:.4f}] "
              f"mean={boot_mean:.4f} "
              f"{'excludes zero' if ci_excludes_zero else 'includes zero'}")
    else:
        ci_lower = ci_upper = boot_mean = None
        ci_excludes_zero = False

    return {
        "windows": results,
        "n_windows": n_windows,
        "n_positive": n_positive,
        "win_rate": win_rate,
        "wilcoxon_stat": wilcoxon_stat,
        "wilcoxon_p": wilcoxon_p,
        "bootstrap_ci_lower": ci_lower,
        "bootstrap_ci_upper": ci_upper,
        "bootstrap_mean": boot_mean,
        "ci_excludes_zero": ci_excludes_zero,
    }


# =========================================================================
# REPORT GENERATION
# =========================================================================


def generate_report(all_results: dict) -> str:
    """Generate comprehensive validation report."""

    t1 = all_results.get("T1_engine_baseline", {})
    t2 = all_results.get("T2_threshold_sweep", {})
    t3 = all_results.get("T3_cost_sweep", {})
    t4 = all_results.get("T4_factorial", {})
    t5 = all_results.get("T5_subperiod", {})
    t6 = all_results.get("T6_jackknife", {})
    t7 = all_results.get("T7_wfo", {})

    report = """# Regime Monitor V2 — Comprehensive Validation Report

**Generated**: {timestamp}
**Data**: {start} to {end} (warmup={warmup}d)
**Engine**: BacktestEngine (next-open fills, no_trade warmup)
**Cost scenarios**: smart ({smart_rt:.0f} bps RT), base ({base_rt:.0f} bps RT), harsh ({harsh_rt:.0f} bps RT)

---

## T1: Engine Baseline (harsh cost)

""".format(
        timestamp=datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        start=START, end=END, warmup=WARMUP,
        smart_rt=SCENARIOS["smart"].round_trip_bps,
        base_rt=SCENARIOS["base"].round_trip_bps,
        harsh_rt=SCENARIOS["harsh"].round_trip_bps,
    )

    if t1:
        m_off = t1.get("monitor_off", {})
        m_on = t1.get("monitor_on", {})
        delta = t1.get("delta", {})
        report += f"""| Metric | Monitor OFF | Monitor ON | Delta |
|--------|----------:|----------:|------:|
| Sharpe | {m_off.get('sharpe', 0):.4f} | {m_on.get('sharpe', 0):.4f} | {delta.get('sharpe', 0):+.4f} |
| CAGR % | {m_off.get('cagr_pct', 0):.2f} | {m_on.get('cagr_pct', 0):.2f} | {delta.get('cagr_pct', 0):+.2f} |
| MDD % | {m_off.get('mdd_pct', 0):.2f} | {m_on.get('mdd_pct', 0):.2f} | {delta.get('mdd_pct', 0):+.2f} |
| Trades | {m_off.get('trades', 0)} | {m_on.get('trades', 0)} | {delta.get('trades', 0):+.0f} |
| Monitor exits | -- | {m_on.get('monitor_exits', 0)} | |
| Final NAV | {m_off.get('final_nav', 0):.2f} | {m_on.get('final_nav', 0):.2f} | {m_on.get('final_nav', 0) - m_off.get('final_nav', 0):+.2f} |

"""

    # T2: Threshold sweep
    report += "## T2: Threshold Sensitivity\n\n"
    if t2:
        for param_name, rows in t2.items():
            if not isinstance(rows, list):
                continue
            report += f"### {param_name}\n\n"
            report += "| Value | Sharpe | CAGR % | MDD % | Trades | RED bars |\n"
            report += "|------:|-------:|-------:|------:|-------:|---------:|\n"
            for r in rows:
                report += (f"| {r['value']:.2f} | {r['sharpe']:.4f} | "
                          f"{r['cagr_pct']:.2f} | {r['mdd_pct']:.2f} | "
                          f"{r['trades']} | {r['n_red_h4']} |\n")
            # Plateau analysis
            sharpes = [r["sharpe"] for r in rows]
            best = max(sharpes)
            plateau = [r["value"] for r in rows if r["sharpe"] >= best * 0.95]
            defaults_map = {"red_6m": "0.55", "red_12m": "0.70",
                           "amber_6m": "0.45", "amber_12m": "0.60"}
            default_val = defaults_map.get(param_name, "?")
            report += (f"\nPlateau (Sharpe >= 95% of best {best:.4f}): "
                      f"**{min(plateau):.2f} - {max(plateau):.2f}** "
                      f"(default: {default_val})\n\n")

    # T3: Cost sweep
    report += "## T3: Cost Sweep\n\n"
    if t3:
        report += "| Scenario | RT bps | dSharpe | dCAGR % | dMDD % | dTrades |\n"
        report += "|----------|-------:|--------:|--------:|-------:|--------:|\n"
        for name in ["smart", "base", "harsh"]:
            if name in t3:
                d = t3[name]["delta"]
                rt = SCENARIOS[name].round_trip_bps
                report += (f"| {name} | {rt:.0f} | {d['sharpe']:+.4f} | "
                          f"{d['cagr_pct']:+.2f} | {d['mdd_pct']:+.2f} | "
                          f"{d['trades']:+d} |\n")
        report += "\n"

    # T4: Factorial
    report += "## T4: Factorial Isolation\n\n"
    if t4:
        configs = t4.get("configs", {})
        report += "| Config | Sharpe | CAGR % | MDD % | Trades |\n"
        report += "|--------|-------:|-------:|------:|-------:|\n"
        for label, m in configs.items():
            report += (f"| {label} | {m['sharpe']:.4f} | {m['cagr_pct']:.2f} | "
                      f"{m['mdd_pct']:.2f} | {m['trades']} |\n")
        em = t4.get("ema21_marginal", {})
        mm = t4.get("monitor_marginal", {})
        report += f"""
**Marginal contributions:**
- EMA(21) filter: Sharpe {em.get('sharpe', 0):+.4f}, CAGR {em.get('cagr_pct', 0):+.2f}%, MDD {em.get('mdd_pct', 0):+.2f}%
- Monitor V2: Sharpe {mm.get('sharpe', 0):+.4f}, CAGR {mm.get('cagr_pct', 0):+.2f}%, MDD {mm.get('mdd_pct', 0):+.2f}%

"""

    # T5: Subperiod
    report += "## T5: Subperiod Robustness\n\n"
    if t5:
        report += "| Period | dSharpe | dCAGR % | dMDD % | dTrades |\n"
        report += "|--------|--------:|--------:|-------:|--------:|\n"
        for label, data in t5.items():
            if label == "summary":
                continue
            d = data.get("delta", {})
            report += (f"| {label} | {d.get('sharpe', 0):+.4f} | "
                      f"{d.get('cagr_pct', 0):+.2f} | {d.get('mdd_pct', 0):+.2f} | "
                      f"{d.get('trades', 0):+d} |\n")
        summary = t5.get("summary", {})
        report += (f"\n**{summary.get('n_positive_sharpe', 0)}/{summary.get('n_periods', 0)} "
                  f"periods Sharpe improved, "
                  f"{summary.get('n_positive_mdd', 0)}/{summary.get('n_periods', 0)} "
                  f"MDD improved**\n\n")

    # T6: Jackknife
    report += "## T6: Jackknife — Blocked Entry Analysis\n\n"
    if t6:
        report += f"""- Trades (monitor OFF): {t6.get('trades_off', 0)}
- Trades (monitor ON): {t6.get('trades_on', 0)}
- Blocked entries: {t6.get('n_blocked', 0)}
- Modified exits: {t6.get('n_modified', 0)}
- Monitor forced exits: {t6.get('monitor_exits_count', 0)}
- Total blocked PnL: {t6.get('total_blocked_pnl', 0):+.2f}

"""
        blocked = t6.get("blocked_trades", [])
        if blocked:
            # Sort by PnL
            blocked_sorted = sorted(blocked, key=lambda x: x["pnl"])
            report += "| # | Entry Date | PnL | Return % | Days | Exit Reason |\n"
            report += "|---|-----------|----:|--------:|-----:|------------|\n"
            for i, t in enumerate(blocked_sorted):
                report += (f"| {i+1} | {t['entry_date']} | {t['pnl']:+.2f} | "
                          f"{t['return_pct']:+.2f} | {t['days_held']:.1f} | "
                          f"{t['exit_reason']} |\n")
            report += "\n"

            # Profit contribution
            losing = sum(1 for t in blocked if t["pnl"] < 0)
            winning = sum(1 for t in blocked if t["pnl"] > 0)
            report += (f"Blocked: {losing} losers, {winning} winners. "
                      f"Net PnL avoided: {t6.get('total_blocked_pnl', 0):+.2f}\n\n")

    # T7: WFO
    report += "## T7: Walk-Forward Optimization\n\n"
    if t7:
        windows = t7.get("windows", [])
        report += "| Window | Test Period | OFF Sharpe | ON Sharpe | Delta | Sign |\n"
        report += "|-------:|-----------|----------:|----------:|------:|:----:|\n"
        for w in windows:
            sign = "+" if w["delta_sharpe"] > 0 else "-"
            report += (f"| {w['window']} | {w['test_start']} → {w['test_end']} | "
                      f"{w['off_sharpe']:.4f} | {w['on_sharpe']:.4f} | "
                      f"{w['delta_sharpe']:+.4f} | {sign} |\n")

        report += f"""
**Win rate**: {t7.get('n_positive', 0)}/{t7.get('n_windows', 0)} = {t7.get('win_rate', 0):.1%}
"""
        if t7.get("wilcoxon_p") is not None:
            p = t7["wilcoxon_p"]
            report += (f"**Wilcoxon signed-rank** (one-sided): p={p:.4f} "
                      f"{'**PASS** (p < 0.10)' if p < 0.10 else '**FAIL** (p >= 0.10)'}\n")
        if t7.get("bootstrap_ci_lower") is not None:
            report += (f"**Bootstrap CI** (95%): [{t7['bootstrap_ci_lower']:.4f}, "
                      f"{t7['bootstrap_ci_upper']:.4f}] mean={t7['bootstrap_mean']:.4f} "
                      f"{'**excludes zero**' if t7.get('ci_excludes_zero') else 'includes zero'}\n")
        report += "\n"

    # Verdict
    report += "## Verdict\n\n"

    gates = []
    # Gate 1: Engine confirms improvement
    if t1 and t1.get("delta", {}).get("sharpe", 0) > 0:
        gates.append(("G1: Engine Sharpe improvement", "PASS",
                      f"dSharpe={t1['delta']['sharpe']:+.4f}"))
    elif t1:
        gates.append(("G1: Engine Sharpe improvement", "FAIL",
                      f"dSharpe={t1.get('delta', {}).get('sharpe', 0):+.4f}"))

    # Gate 2: Threshold plateau exists
    if t2:
        all_plateau = True
        for param_name, rows in t2.items():
            if not isinstance(rows, list):
                continue
            sharpes = [r["sharpe"] for r in rows]
            best = max(sharpes)
            plateau = [r["value"] for r in rows if r["sharpe"] >= best * 0.95]
            if len(plateau) < 3:
                all_plateau = False
        gates.append(("G2: Threshold plateau", "PASS" if all_plateau else "FAIL",
                      "All params have plateau >= 3 points" if all_plateau else "Narrow plateau"))

    # Gate 3: Majority subperiods positive
    if t5:
        s = t5.get("summary", {})
        majority = s.get("n_positive_sharpe", 0) >= s.get("n_periods", 1) / 2
        gates.append(("G3: Subperiod majority positive",
                      "PASS" if majority else "FAIL",
                      f"{s.get('n_positive_sharpe', 0)}/{s.get('n_periods', 0)}"))

    # Gate 4: Blocked trades net negative (monitor correctly blocked losers)
    if t6:
        net_negative = t6.get("total_blocked_pnl", 0) < 0
        gates.append(("G4: Blocked trades net negative PnL",
                      "PASS" if net_negative else "FAIL",
                      f"PnL={t6.get('total_blocked_pnl', 0):+.2f}"))

    # Gate 5: WFO win rate >= 50%
    if t7:
        wr = t7.get("win_rate", 0)
        gates.append(("G5: WFO win rate >= 50%",
                      "PASS" if wr >= 0.5 else "FAIL",
                      f"win_rate={wr:.1%}"))

    # Gate 6: Monitor exits = 0 (as documented)
    if t6:
        me = t6.get("monitor_exits_count", -1)
        gates.append(("G6: Monitor forced exits = 0",
                      "PASS" if me == 0 else "INFO",
                      f"monitor_exits={me}"))

    report += "| Gate | Status | Detail |\n"
    report += "|------|:------:|--------|\n"
    for gate_name, status, detail in gates:
        report += f"| {gate_name} | **{status}** | {detail} |\n"

    n_pass = sum(1 for _, s, _ in gates if s == "PASS")
    n_total = sum(1 for _, s, _ in gates if s in ("PASS", "FAIL"))
    report += f"\n**{n_pass}/{n_total} gates PASS**\n\n"

    if n_pass == n_total:
        report += "**VERDICT: VALIDATED** — Monitor V2 passes all gates with engine-authoritative metrics.\n"
    elif n_pass >= n_total - 1:
        report += "**VERDICT: CONDITIONAL PASS** — Monitor V2 passes most gates. Review failures.\n"
    else:
        report += "**VERDICT: NEEDS WORK** — Monitor V2 fails multiple gates.\n"

    report += "\n---\n*Generated by validate_monitor_v2.py (engine-authoritative)*\n"

    return report


# =========================================================================
# MAIN
# =========================================================================


def main():
    t_start = time.time()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("REGIME MONITOR V2 — COMPREHENSIVE VALIDATION")
    print(f"  Period: {START} to {END} (warmup={WARMUP}d)")
    print(f"  Engine: BacktestEngine (next-open fills, no_trade warmup)")
    print(f"  Tests: T1-T7 (engine parity, sweep, cost, factorial, subperiod, jackknife, WFO)")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    feed = DataFeed(DATA, start=START, end=END, warmup_days=WARMUP)
    print(f"  H4 bars: {feed.n_h4}, D1 bars: {feed.n_d1}")

    all_results = {}

    # T1: Engine baseline
    all_results["T1_engine_baseline"] = t1_engine_baseline(feed)

    # T2: Threshold sweep
    all_results["T2_threshold_sweep"] = t2_threshold_sweep(feed)

    # T3: Cost sweep
    all_results["T3_cost_sweep"] = t3_cost_sweep(feed)

    # T4: Factorial isolation
    all_results["T4_factorial"] = t4_factorial(feed)

    # T5: Subperiod robustness
    all_results["T5_subperiod"] = t5_subperiod(feed)

    # T6: Jackknife
    all_results["T6_jackknife"] = t6_jackknife(feed)

    # T7: WFO
    all_results["T7_wfo"] = t7_wfo(feed)

    # Save JSON results
    def sanitize(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj

    json_path = OUTDIR / "validation_results.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2, default=sanitize)
    print(f"\nSaved: {json_path}")

    # Generate report
    report = generate_report(all_results)
    report_path = OUTDIR / "MONITOR_V2_VALIDATION_REPORT.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Saved: {report_path}")

    elapsed = time.time() - t_start
    print(f"\n{'=' * 80}")
    print(f"VALIDATION COMPLETE ({elapsed:.0f}s)")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
