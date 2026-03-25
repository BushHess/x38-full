#!/usr/bin/env python3
"""Final Holdout Test — ONE-SHOT, no parameter tuning allowed.

Holdout period: 2024-10-01 → 2026-02-20 (last 19.4% = 507 days)
Full evaluation period: 2019-01-01 → 2026-02-20 (2607 days)

Baseline: V10 = V8ApexConfig() defaults
Candidate: V11 WFO-opt (0.95/2.8/0.90) — params fixed BEFORE seeing holdout

This script runs EXACTLY ONCE. Do not re-run to pick better results.

Output:
  - final_holdout_metrics.csv
  - stdout → holdout_run.log (via tee)
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

np.seterr(all="ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS
from v10.research.objective import compute_objective
from v10.research.regime import classify_d1_regimes, compute_regime_returns
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
WARMUP_DAYS = 365
OUTDIR = Path("out_v11_validation_stepwise")

# ── Holdout definition ───────────────────────────────────────────────────
HOLDOUT_START = "2024-10-01"
HOLDOUT_END = "2026-02-20"
FULL_START = "2019-01-01"
FULL_END = "2026-02-20"

SCENARIO_NAMES = ["harsh", "base", "smart"]


def make_v10():
    return V8ApexStrategy(V8ApexConfig())


def make_v11():
    """V11 WFO-optimal params — fixed before holdout, NOT tuned on holdout."""
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90
    return V11HybridStrategy(cfg)


def run_backtest(factory, start, end, scenario_name):
    """Run backtest, return (result, feed)."""
    cost = SCENARIOS[scenario_name]
    strategy = factory()
    feed = DataFeed(DATA_PATH, start=start, end=end, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result, feed


def extract_full_metrics(result, feed, label):
    """Extract comprehensive metrics including regime decomposition."""
    s = result.summary
    score = compute_objective(s)

    # Regime returns
    regimes = classify_d1_regimes(feed.d1_bars)
    rr = compute_regime_returns(result.equity, feed.d1_bars, regimes)

    regime_returns = {}
    for regime_name in ["BULL", "TOPPING", "BEAR", "CHOP", "NEUTRAL", "SHOCK"]:
        r = rr.get(regime_name, {})
        regime_returns[regime_name] = {
            "total_return_pct": r.get("total_return_pct", 0.0),
            "n_days": r.get("n_days", 0),
        }

    return {
        "strategy": label,
        "score": score,
        "cagr_pct": s.get("cagr_pct", 0.0),
        "total_return_pct": s.get("total_return_pct", 0.0),
        "mdd_pct": s.get("max_drawdown_mid_pct", 0.0),
        "sharpe": s.get("sharpe") or 0.0,
        "profit_factor": s.get("profit_factor", 0.0) or 0.0,
        "trades": s.get("trades", 0),
        "turnover_per_year": s.get("turnover_per_year", 0.0),
        "fees_total": s.get("fees_total", 0),
        "final_nav": s.get("final_nav_mid", 10000.0),
        "regime_returns": regime_returns,
    }


def fmt(v, decimals=2):
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


def main():
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    print("=" * 70)
    print("  FINAL HOLDOUT TEST — ONE-SHOT")
    print("=" * 70)
    print(f"  Timestamp: {timestamp}")
    print(f"  Holdout period: {HOLDOUT_START} → {HOLDOUT_END}")
    print(f"  Full period:    {FULL_START} → {FULL_END}")
    print(f"  Warmup:         {WARMUP_DAYS} days")
    print(f"  Baseline:       V10 = V8ApexConfig() defaults")
    print(f"  Candidate:      V11 WFO-opt (aggr=0.95, trail=2.8, cap=0.90)")
    print(f"  Scenarios:      {SCENARIO_NAMES}")
    print(f"  COMMITMENT:     This script runs ONCE. No re-runs.")
    print()

    # ── Run holdout backtests ────────────────────────────────────────────
    csv_rows = []
    all_results = {}

    for scenario in SCENARIO_NAMES:
        print(f"  ── Scenario: {scenario} ──")

        res_v10, feed_v10 = run_backtest(make_v10, HOLDOUT_START, HOLDOUT_END, scenario)
        res_v11, feed_v11 = run_backtest(make_v11, HOLDOUT_START, HOLDOUT_END, scenario)

        m_v10 = extract_full_metrics(res_v10, feed_v10, "V10")
        m_v11 = extract_full_metrics(res_v11, feed_v11, "V11_WFO_opt")

        # Deltas
        m_delta = {"strategy": "DELTA"}
        metric_keys = ["score", "cagr_pct", "total_return_pct", "mdd_pct",
                       "sharpe", "profit_factor", "trades", "turnover_per_year",
                       "fees_total", "final_nav"]
        for k in metric_keys:
            v10v = m_v10[k] if isinstance(m_v10[k], (int, float, np.integer, np.floating)) else 0
            v11v = m_v11[k] if isinstance(m_v11[k], (int, float, np.integer, np.floating)) else 0
            m_delta[k] = float(v11v) - float(v10v)

        # Regime deltas
        m_delta["regime_returns"] = {}
        for regime_name in ["BULL", "TOPPING", "BEAR", "CHOP", "NEUTRAL", "SHOCK"]:
            r10 = m_v10["regime_returns"][regime_name]["total_return_pct"]
            r11 = m_v11["regime_returns"][regime_name]["total_return_pct"]
            m_delta["regime_returns"][regime_name] = {
                "total_return_pct": r11 - r10,
                "n_days": m_v10["regime_returns"][regime_name]["n_days"],
            }

        all_results[scenario] = {"v10": m_v10, "v11": m_v11, "delta": m_delta}

        # Print
        print(f"    V10: score={m_v10['score']:+.2f}  ret={m_v10['total_return_pct']:+.2f}%  "
              f"cagr={m_v10['cagr_pct']:+.2f}%  mdd={m_v10['mdd_pct']:.2f}%  "
              f"sharpe={m_v10['sharpe']:.3f}  trades={m_v10['trades']}")
        print(f"    V11: score={m_v11['score']:+.2f}  ret={m_v11['total_return_pct']:+.2f}%  "
              f"cagr={m_v11['cagr_pct']:+.2f}%  mdd={m_v11['mdd_pct']:.2f}%  "
              f"sharpe={m_v11['sharpe']:.3f}  trades={m_v11['trades']}")

        d = m_delta
        sign = "+" if d["score"] > 0.01 else ("-" if d["score"] < -0.01 else "=")
        print(f"    DELTA: score={d['score']:+.2f} [{sign}]  "
              f"ret={d['total_return_pct']:+.2f}%  "
              f"cagr={d['cagr_pct']:+.2f}%  "
              f"mdd={d['mdd_pct']:+.2f}%  "
              f"sharpe={d['sharpe']:+.3f}")

        # Regime breakdown
        print(f"    Regime deltas:", end="")
        for rn in ["BULL", "TOPPING", "BEAR", "CHOP"]:
            dr = m_delta["regime_returns"][rn]["total_return_pct"]
            nd = m_delta["regime_returns"][rn]["n_days"]
            if nd > 0:
                print(f"  {rn}={dr:+.2f}%({nd}d)", end="")
        print()
        print()

        # CSV rows
        for label, m in [("V10", m_v10), ("V11_WFO_opt", m_v11), ("DELTA", m_delta)]:
            row = {"scenario": scenario, "strategy": label}
            for k in metric_keys:
                row[k] = round(float(m[k]), 4) if isinstance(m[k], (int, float, np.integer, np.floating)) else m[k]
            for rn in ["BULL", "TOPPING", "BEAR", "CHOP"]:
                rr_val = m["regime_returns"][rn]["total_return_pct"]
                row[f"{rn.lower()}_return_pct"] = round(float(rr_val), 4)
            csv_rows.append(row)

    # ── Also run full-period for comparison ──────────────────────────────
    print("=" * 70)
    print("  FULL-PERIOD COMPARISON (for context)")
    print("=" * 70)

    for scenario in SCENARIO_NAMES:
        res_v10_full, _ = run_backtest(make_v10, FULL_START, FULL_END, scenario)
        res_v11_full, _ = run_backtest(make_v11, FULL_START, FULL_END, scenario)
        s10 = compute_objective(res_v10_full.summary)
        s11 = compute_objective(res_v11_full.summary)
        print(f"  {scenario}: V10={s10:.2f}  V11={s11:.2f}  Δ={s11-s10:+.2f}")
    print()

    # ── Write CSV ────────────────────────────────────────────────────────
    csv_path = OUTDIR / "final_holdout_metrics.csv"
    fieldnames = ["scenario", "strategy", "score", "cagr_pct", "total_return_pct",
                   "mdd_pct", "sharpe", "profit_factor", "trades",
                   "turnover_per_year", "fees_total", "final_nav",
                   "bull_return_pct", "topping_return_pct",
                   "bear_return_pct", "chop_return_pct"]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"  Saved: {csv_path}")

    # ── Verdict ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  HOLDOUT VERDICT")
    print("=" * 70)

    harsh = all_results["harsh"]
    base = all_results["base"]
    smart = all_results["smart"]

    wins_score = 0
    wins_return = 0
    wins_sharpe = 0
    for sc_name, sc_data in all_results.items():
        d = sc_data["delta"]
        if d["score"] > 0.01:
            wins_score += 1
        if d["total_return_pct"] > 0.01:
            wins_return += 1
        if d["sharpe"] > 0.001:
            wins_sharpe += 1

    print(f"  Score:  V11 wins {wins_score}/3 scenarios")
    print(f"  Return: V11 wins {wins_return}/3 scenarios")
    print(f"  Sharpe: V11 wins {wins_sharpe}/3 scenarios")

    # Primary metric: harsh score
    d_harsh = harsh["delta"]["score"]
    d_harsh_ret = harsh["delta"]["total_return_pct"]
    d_harsh_sharpe = harsh["delta"]["sharpe"]
    d_harsh_mdd = harsh["delta"]["mdd_pct"]

    # Regime safety: TOPPING/BEAR damage
    topping_dmg = harsh["delta"]["regime_returns"].get("TOPPING", {}).get("total_return_pct", 0)
    bear_dmg = harsh["delta"]["regime_returns"].get("BEAR", {}).get("total_return_pct", 0)

    print(f"\n  Harsh scenario detail:")
    print(f"    Δ score:  {d_harsh:+.2f}")
    print(f"    Δ return: {d_harsh_ret:+.2f}%")
    print(f"    Δ sharpe: {d_harsh_sharpe:+.3f}")
    print(f"    Δ MDD:    {d_harsh_mdd:+.2f}%")
    print(f"    Δ TOPPING: {topping_dmg:+.2f}%")
    print(f"    Δ BEAR:    {bear_dmg:+.2f}%")

    if d_harsh > 0.01 and wins_score >= 2:
        verdict = "PASS — V11 beats V10 on holdout"
    elif d_harsh > 0.01:
        verdict = "PASS (marginal) — V11 beats V10 on harsh but not all scenarios"
    elif abs(d_harsh) <= 0.5 and d_harsh_ret > 0:
        verdict = "HOLD — near-identical score, slight return advantage"
    elif d_harsh > -2.0:
        verdict = "HOLD — V11 slightly behind but within noise margin"
    else:
        verdict = "REJECT — V11 clearly loses to V10 on holdout"

    # Override if TOPPING/BEAR damage
    if topping_dmg < -2.0 or bear_dmg < -2.0:
        verdict += " [WARNING: regime damage detected]"

    print(f"\n  {'=' * 50}")
    print(f"  VERDICT: {verdict}")
    print(f"  {'=' * 50}")

    # ── Save full JSON ───────────────────────────────────────────────────
    def _c(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: _c(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_c(v) for v in obj]
        return obj

    json_data = {
        "holdout_start": HOLDOUT_START,
        "holdout_end": HOLDOUT_END,
        "holdout_pct": 19.4,
        "timestamp": timestamp,
        "baseline": "V10 = V8ApexConfig()",
        "candidate": "V11 WFO-opt (0.95/2.8/0.90)",
        "commitment": "One-shot. No re-runs. No parameter tuning on holdout.",
        "results": _c(all_results),
        "verdict": verdict,
    }

    json_path = OUTDIR / "final_holdout.json"
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)
    print(f"\n  Saved: {json_path}")
    print(f"  Saved: {csv_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
