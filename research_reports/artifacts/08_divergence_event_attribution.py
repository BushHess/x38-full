#!/usr/bin/env python3
"""
08 — Divergence Event Attribution
===================================
Canonical pair: v12_emdd_ref_fix (candidate) vs v10_baseline_frozen (baseline)
  candidate: V8Apex + emdd_ref_mode=fixed, emergency_dd_pct=0.04
  baseline:  V8Apex + emergency_ref=pre_cost_legacy, emergency_dd_pct=0.28

Key mechanism difference: v12 triggers emergency exit at 4% drawdown from
true post-fill NAV. Baseline triggers at 28% from pre-cost entry NAV.

This script:
  1. Reproduces full equity curves with bar-level NAV and exposure
  2. Identifies top divergence events by absolute paired differential
  3. Classifies each event by exposure-state transition
  4. Computes forward outcomes at +1/+6/+24/+42 bars
  5. Measures concentration of excess return in top events
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from v10.core.data import DataFeed
from v10.core.engine import BacktestEngine
from v10.core.types import SCENARIOS, EquitySnap
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from strategies.v12_emdd_ref_fix.strategy import (
    V12EMDDRefFixConfig,
    V12EMDDRefFixStrategy,
)

# ── Canonical config ──────────────────────────────────────────────────
DATA_PATH = ROOT / "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
START = "2019-01-01"
END = "2026-02-20"
WARMUP_DAYS = 365
INITIAL_CASH = 10_000.0
COST = SCENARIOS["harsh"]
OUT_DIR = ROOT / "research_reports" / "artifacts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TOP_N_LEVELS = [1, 5, 10, 20, 50, 100]
FORWARD_HORIZONS = [1, 6, 24, 42]  # bars

CANONICAL_PAIR = {
    "candidate_name": "v12_emdd_ref_fix",
    "candidate_config": "configs/v12/v12_emdd_ref_fix_step5_best.yaml",
    "candidate_params": {"emdd_ref_mode": "fixed", "emergency_dd_pct": 0.04,
                         "rsi_method": "wilder", "entry_cooldown_bars": 3},
    "baseline_name": "v10_baseline_frozen",
    "baseline_config": "configs/frozen/v10_baseline.yaml",
    "baseline_strategy": "v8_apex",
    "baseline_params": {"emergency_ref": "pre_cost_legacy",
                        "rsi_method": "wilder", "entry_cooldown_bars": 3},
    "validation_label": "v12_vs_v10",
    "validation_run": "out/validate/v12_vs_v10/2026-02-24",
    "key_mechanism_difference": (
        "v12 triggers emergency exit at 4% DD from true post-fill NAV; "
        "baseline triggers at 28% DD from pre-cost entry NAV"
    ),
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: Reproduce equity curves
# ═══════════════════════════════════════════════════════════════════════

def run_backtest(strategy, label):
    feed = DataFeed(path=str(DATA_PATH), start=START, end=END,
                    warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=COST,
                            initial_cash=INITIAL_CASH,
                            warmup_days=WARMUP_DAYS)
    result = engine.run()
    s = result.summary
    print(f"  {label:20s}: Sharpe={s.get('sharpe', 0):.4f}  "
          f"CAGR={s.get('cagr_pct', 0):.2f}%  "
          f"MDD={s.get('max_drawdown_mid_pct', 0):.2f}%  "
          f"trades={s.get('trades', 0)}")
    return result.equity


def make_candidate():
    cfg = V12EMDDRefFixConfig()
    cfg.emdd_ref_mode = "fixed"
    cfg.emergency_dd_pct = 0.04
    cfg.rsi_method = "wilder"
    cfg.entry_cooldown_bars = 3
    return V12EMDDRefFixStrategy(cfg)


def make_baseline():
    cfg = V8ApexConfig()
    cfg.emergency_ref = "pre_cost_legacy"
    cfg.rsi_method = "wilder"
    cfg.entry_cooldown_bars = 3
    return V8ApexStrategy(cfg)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: Build bar-level dataset
# ═══════════════════════════════════════════════════════════════════════

def build_bar_data(eq_cand, eq_base):
    """Build arrays from equity snaps."""
    n = len(eq_cand)
    assert len(eq_base) == n

    ts = np.array([e.close_time for e in eq_cand], dtype=np.int64)
    nav_c = np.array([e.nav_mid for e in eq_cand], dtype=np.float64)
    nav_b = np.array([e.nav_mid for e in eq_base], dtype=np.float64)
    exp_c = np.array([e.exposure for e in eq_cand], dtype=np.float64)
    exp_b = np.array([e.exposure for e in eq_base], dtype=np.float64)

    # Simple pct returns (n-1 elements)
    ret_c = np.diff(nav_c) / nav_c[:-1]
    ret_b = np.diff(nav_b) / nav_b[:-1]
    simp_diff = ret_c - ret_b

    # Log returns and log differential
    log_c = np.log(nav_c[1:] / nav_c[:-1])
    log_b = np.log(nav_b[1:] / nav_b[:-1])
    log_diff = log_c - log_b

    return {
        "ts": ts[1:],  # aligned with returns (return[i] is snap[i] to snap[i+1])
        "nav_c": nav_c[1:],
        "nav_b": nav_b[1:],
        "exp_c": exp_c[1:],
        "exp_b": exp_b[1:],
        "exp_c_prev": exp_c[:-1],
        "exp_b_prev": exp_b[:-1],
        "ret_c": ret_c,
        "ret_b": ret_b,
        "simp_diff": simp_diff,
        "log_c": log_c,
        "log_b": log_b,
        "log_diff": log_diff,
        "n": len(ret_c),
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: Classify exposure transitions
# ═══════════════════════════════════════════════════════════════════════

def classify_event(exp_c_prev, exp_c_now, exp_b_prev, exp_b_now, simp_diff):
    """Classify a divergence event by exposure state transition.

    Returns (event_type, description).
    """
    c_flat_prev = exp_c_prev < 0.01
    c_flat_now = exp_c_now < 0.01
    b_flat_prev = exp_b_prev < 0.01
    b_flat_now = exp_b_now < 0.01

    c_exited = (not c_flat_prev) and c_flat_now
    c_entered = c_flat_prev and (not c_flat_now)
    b_exited = (not b_flat_prev) and b_flat_now
    b_entered = b_flat_prev and (not b_flat_now)

    # Both in same state
    if c_flat_now == b_flat_now and c_flat_prev == b_flat_prev:
        if abs(exp_c_now - exp_b_now) < 0.01:
            return "same_state_same_exp", "both same position; residual NAV diff"
        else:
            return "same_state_diff_exp", "both same direction but different exposure"

    # Candidate exited, baseline stayed
    if c_exited and not b_exited and not b_flat_now:
        return "cand_exit_base_hold", "candidate exited while baseline held"

    # Candidate stayed, baseline exited
    if b_exited and not c_exited and not c_flat_now:
        return "base_exit_cand_hold", "baseline exited while candidate held"

    # Candidate entered, baseline stayed flat
    if c_entered and not b_entered and b_flat_now:
        return "cand_enter_base_flat", "candidate entered while baseline stayed flat"

    # Baseline entered, candidate stayed flat
    if b_entered and not c_entered and c_flat_now:
        return "base_enter_cand_flat", "baseline entered while candidate stayed flat"

    # Both exited but at different bars (one still in cooldown / re-entry)
    if c_exited and b_entered:
        return "cand_exit_base_enter", "candidate exited as baseline entered"

    if c_entered and b_exited:
        return "cand_enter_base_exit", "candidate entered as baseline exited"

    # Fallback
    return "other", (f"c_prev={exp_c_prev:.2f}→{exp_c_now:.2f}, "
                     f"b_prev={exp_b_prev:.2f}→{exp_b_now:.2f}")


def classify_economic_impact(event_type, simp_diff, btc_fwd_1, btc_fwd_6):
    """Classify whether the event was beneficial, harmful, or noise.

    Candidate is 'A', baseline is 'B'. simp_diff = ret_A - ret_B.

    Beneficial: candidate avoided a loss that baseline took, OR
                candidate captured a gain that baseline missed.
    Harmful:    candidate missed a gain that baseline captured, OR
                candidate took a loss that baseline avoided.
    """
    if abs(simp_diff) < 1e-6:
        return "noise"

    if event_type == "cand_exit_base_hold":
        # Candidate exited. Was the exit good?
        # If BTC dropped in next 6 bars, it was crash-avoidance.
        if btc_fwd_6 is not None and btc_fwd_6 < -0.005:
            return "beneficial_crash_avoidance" if simp_diff > 0 else "harmful_missed_recovery"
        elif btc_fwd_6 is not None and btc_fwd_6 > 0.005:
            return "harmful_premature_exit" if simp_diff < 0 else "beneficial_exit_at_top"
        else:
            return "beneficial_crash_avoidance" if simp_diff > 0 else "harmful_premature_exit"

    elif event_type == "base_exit_cand_hold":
        if btc_fwd_6 is not None and btc_fwd_6 > 0.005:
            return "beneficial_stayed_in" if simp_diff > 0 else "harmful_stayed_in"
        else:
            return "harmful_stayed_in" if simp_diff < 0 else "beneficial_stayed_in"

    elif event_type in ("cand_enter_base_flat", "base_enter_cand_flat"):
        return "beneficial" if simp_diff > 0 else "harmful"

    else:
        return "beneficial" if simp_diff > 0 else "harmful"


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: Forward outcomes
# ═══════════════════════════════════════════════════════════════════════

def compute_forward_outcomes(data, event_idx, horizons):
    """Compute forward cumulative return for candidate, baseline, and BTC."""
    n = data["n"]
    results = {}
    for h in horizons:
        end_idx = event_idx + h
        if end_idx >= n:
            results[f"+{h}"] = None
            continue
        # Cumulative returns over the forward window
        cum_c = float(np.prod(1 + data["ret_c"][event_idx + 1:end_idx + 1]) - 1)
        cum_b = float(np.prod(1 + data["ret_b"][event_idx + 1:end_idx + 1]) - 1)
        # BTC return: use the one that was in market (baseline if both were)
        cum_btc = float(np.prod(1 + data["ret_b"][event_idx + 1:end_idx + 1]) - 1)
        # Forward differential
        cum_diff = cum_c - cum_b
        results[f"+{h}"] = {
            "cum_ret_cand": cum_c,
            "cum_ret_base": cum_b,
            "cum_diff": cum_diff,
        }
    return results


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: Concentration analysis
# ═══════════════════════════════════════════════════════════════════════

def concentration_analysis(data, top_indices, top_n_levels):
    """Fraction of total excess return explained by top-N events."""
    total_excess = float(np.sum(data["simp_diff"]))
    total_excess_abs = float(np.sum(np.abs(data["simp_diff"])))

    # Drawdown analysis for concentration
    nav_c = np.concatenate([[INITIAL_CASH], INITIAL_CASH * np.cumprod(1 + data["ret_c"])])
    nav_b = np.concatenate([[INITIAL_CASH], INITIAL_CASH * np.cumprod(1 + data["ret_b"])])
    dd_c = 1.0 - nav_c / np.maximum.accumulate(nav_c)
    dd_b = 1.0 - nav_b / np.maximum.accumulate(nav_b)
    max_dd_c = float(np.max(dd_c))
    max_dd_b = float(np.max(dd_b))
    dd_diff = max_dd_c - max_dd_b  # positive = candidate worse

    results = {
        "total_excess_return": total_excess,
        "total_absolute_differential": total_excess_abs,
        "max_dd_candidate": max_dd_c,
        "max_dd_baseline": max_dd_b,
        "max_dd_difference": dd_diff,
    }

    for n in top_n_levels:
        idx = top_indices[:n]
        excess_in_top = float(np.sum(data["simp_diff"][idx]))
        abs_in_top = float(np.sum(np.abs(data["simp_diff"][idx])))
        frac_excess = excess_in_top / total_excess if total_excess != 0 else 0.0
        frac_abs = abs_in_top / total_excess_abs if total_excess_abs != 0 else 0.0
        results[f"top_{n}"] = {
            "excess_in_top": excess_in_top,
            "frac_of_total_excess": frac_excess,
            "abs_in_top": abs_in_top,
            "frac_of_total_abs_differential": frac_abs,
        }

    return results


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("08 — DIVERGENCE EVENT ATTRIBUTION")
    print("=" * 72)
    print(f"  Candidate: {CANONICAL_PAIR['candidate_name']}")
    print(f"  Baseline:  {CANONICAL_PAIR['baseline_name']} ({CANONICAL_PAIR['baseline_strategy']})")
    print(f"  Mechanism: {CANONICAL_PAIR['key_mechanism_difference']}")
    print()

    # ── 1. Reproduce equity curves ────────────────────────────────────
    print("Reproducing equity curves...")
    eq_cand = run_backtest(make_candidate(), "v12_candidate")
    eq_base = run_backtest(make_baseline(), "v8_baseline")
    print()

    data = build_bar_data(eq_cand, eq_base)
    n = data["n"]
    print(f"Bar-level data: {n} returns")

    # ── 2. Identify top divergence events ─────────────────────────────
    abs_diff = np.abs(data["simp_diff"])
    # Sort by absolute differential, descending
    top_indices = np.argsort(abs_diff)[::-1]

    # ── 3. Build event table ──────────────────────────────────────────
    print("Building event table...")
    max_events = max(TOP_N_LEVELS)
    events = []
    for rank, idx in enumerate(top_indices[:max_events]):
        idx = int(idx)
        ts = int(data["ts"][idx])
        dt_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

        # Classify exposure transition
        event_type, event_desc = classify_event(
            data["exp_c_prev"][idx], data["exp_c"][idx],
            data["exp_b_prev"][idx], data["exp_b"][idx],
            data["simp_diff"][idx],
        )

        # Forward outcomes
        fwd = compute_forward_outcomes(data, idx, FORWARD_HORIZONS)
        btc_fwd_6 = fwd.get("+6", {})
        btc_fwd_6_val = btc_fwd_6["cum_ret_base"] if btc_fwd_6 else None

        # Economic classification
        econ = classify_economic_impact(
            event_type, data["simp_diff"][idx],
            fwd.get("+1", {}).get("cum_ret_base") if fwd.get("+1") else None,
            btc_fwd_6_val,
        )

        events.append({
            "rank": rank + 1,
            "bar_index": idx,
            "close_time_ms": ts,
            "datetime_utc": dt_str,
            "simple_differential": float(data["simp_diff"][idx]),
            "log_differential": float(data["log_diff"][idx]),
            "candidate_return": float(data["ret_c"][idx]),
            "baseline_return": float(data["ret_b"][idx]),
            "candidate_exposure": float(data["exp_c"][idx]),
            "baseline_exposure": float(data["exp_b"][idx]),
            "candidate_exposure_prev": float(data["exp_c_prev"][idx]),
            "baseline_exposure_prev": float(data["exp_b_prev"][idx]),
            "candidate_nav": float(data["nav_c"][idx]),
            "baseline_nav": float(data["nav_b"][idx]),
            "event_type": event_type,
            "event_description": event_desc,
            "economic_class": econ,
            "forward_outcomes": fwd,
        })

    # ── 4. Concentration analysis ─────────────────────────────────────
    print("Computing concentration...")
    conc = concentration_analysis(data, top_indices, TOP_N_LEVELS)

    # ── 5. Event type summary ─────────────────────────────────────────
    type_counts = {}
    econ_counts = {}
    econ_pnl = {}
    for e in events:
        t = e["event_type"]
        ec = e["economic_class"]
        type_counts[t] = type_counts.get(t, 0) + 1
        econ_counts[ec] = econ_counts.get(ec, 0) + 1
        econ_pnl[ec] = econ_pnl.get(ec, 0.0) + e["simple_differential"]

    # ── 6. Print results ──────────────────────────────────────────────
    print()
    print("=" * 72)
    print("CONCENTRATION ANALYSIS")
    print("=" * 72)
    print(f"  Total excess return (sum of simple_diff): {conc['total_excess_return']:.6f}")
    print(f"  Total abs differential:                   {conc['total_absolute_differential']:.6f}")
    print(f"  Max DD candidate: {conc['max_dd_candidate']*100:.2f}%")
    print(f"  Max DD baseline:  {conc['max_dd_baseline']*100:.2f}%")
    print(f"  DD difference:    {conc['max_dd_difference']*100:.2f}% (+ = cand worse)")
    print()
    print(f"  {'Top N':>6s}  {'Excess in top':>14s}  {'% of total':>10s}  {'Abs in top':>12s}  {'% of abs':>10s}")
    print(f"  {'-'*6}  {'-'*14}  {'-'*10}  {'-'*12}  {'-'*10}")
    for level in TOP_N_LEVELS:
        c = conc[f"top_{level}"]
        print(f"  {level:6d}  {c['excess_in_top']:14.6f}  {c['frac_of_total_excess']*100:9.1f}%  "
              f"{c['abs_in_top']:12.6f}  {c['frac_of_total_abs_differential']*100:9.1f}%")

    print()
    print("=" * 72)
    print("EVENT TYPE DISTRIBUTION (top 100)")
    print("=" * 72)
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t:30s}: {count:3d}")

    print()
    print("=" * 72)
    print("ECONOMIC CLASSIFICATION (top 100)")
    print("=" * 72)
    for ec, count in sorted(econ_counts.items(), key=lambda x: -x[1]):
        pnl = econ_pnl[ec]
        print(f"  {ec:35s}: {count:3d} events, PnL contribution: {pnl:+.6f}")

    print()
    print("=" * 72)
    print("TOP 20 EVENTS")
    print("=" * 72)
    print(f"  {'Rank':>4s}  {'Date':>16s}  {'Simp Diff':>10s}  {'Cand Ret':>10s}  {'Base Ret':>10s}  "
          f"{'Cand Exp':>8s}  {'Base Exp':>8s}  {'Type':>28s}  {'Econ':>30s}")
    print(f"  {'-'*4}  {'-'*16}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*8}  {'-'*28}  {'-'*30}")
    for e in events[:20]:
        print(f"  {e['rank']:4d}  {e['datetime_utc']:>16s}  {e['simple_differential']:+10.6f}  "
              f"{e['candidate_return']:+10.6f}  {e['baseline_return']:+10.6f}  "
              f"{e['candidate_exposure']:8.4f}  {e['baseline_exposure']:8.4f}  "
              f"{e['event_type']:>28s}  {e['economic_class']:>30s}")

    print()
    print("=" * 72)
    print("FORWARD OUTCOMES (top 20, +6 bars)")
    print("=" * 72)
    for e in events[:20]:
        fwd6 = e["forward_outcomes"].get("+6")
        if fwd6:
            print(f"  Rank {e['rank']:2d} ({e['datetime_utc']}): "
                  f"fwd_cand={fwd6['cum_ret_cand']:+.4f}  "
                  f"fwd_base={fwd6['cum_ret_base']:+.4f}  "
                  f"fwd_diff={fwd6['cum_diff']:+.4f}")

    # ── 7. Save CSV ───────────────────────────────────────────────────
    csv_path = OUT_DIR / "08_top_divergence_events.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rank", "bar_index", "close_time_ms", "datetime_utc",
            "simple_differential", "log_differential",
            "candidate_return", "baseline_return",
            "candidate_exposure", "baseline_exposure",
            "candidate_exposure_prev", "baseline_exposure_prev",
            "candidate_nav", "baseline_nav",
            "event_type", "event_description", "economic_class",
            "fwd_1_cand", "fwd_1_base", "fwd_1_diff",
            "fwd_6_cand", "fwd_6_base", "fwd_6_diff",
            "fwd_24_cand", "fwd_24_base", "fwd_24_diff",
            "fwd_42_cand", "fwd_42_base", "fwd_42_diff",
        ])
        for e in events:
            row = [
                e["rank"], e["bar_index"], e["close_time_ms"], e["datetime_utc"],
                f"{e['simple_differential']:.12f}", f"{e['log_differential']:.12f}",
                f"{e['candidate_return']:.12f}", f"{e['baseline_return']:.12f}",
                f"{e['candidate_exposure']:.6f}", f"{e['baseline_exposure']:.6f}",
                f"{e['candidate_exposure_prev']:.6f}", f"{e['baseline_exposure_prev']:.6f}",
                f"{e['candidate_nav']:.4f}", f"{e['baseline_nav']:.4f}",
                e["event_type"], e["event_description"], e["economic_class"],
            ]
            for h in FORWARD_HORIZONS:
                fwd = e["forward_outcomes"].get(f"+{h}")
                if fwd:
                    row.extend([
                        f"{fwd['cum_ret_cand']:.8f}",
                        f"{fwd['cum_ret_base']:.8f}",
                        f"{fwd['cum_diff']:.8f}",
                    ])
                else:
                    row.extend(["", "", ""])
            writer.writerow(row)
    print(f"\nCSV: {csv_path}")

    # ── 8. Save JSON ──────────────────────────────────────────────────
    result = {
        "meta": {
            "script": "08_divergence_event_attribution.py",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "start": START,
            "end": END,
            "warmup_days": WARMUP_DAYS,
            "cost_scenario": "harsh",
            "cost_rt_bps": COST.round_trip_bps,
        },
        "canonical_pair": CANONICAL_PAIR,
        "concentration": conc,
        "event_type_counts": type_counts,
        "economic_class_counts": econ_counts,
        "economic_class_pnl": econ_pnl,
        "top_20_events": events[:20],
        "n_total_events": len(events),
    }

    json_path = OUT_DIR / "08_divergence_event_summary.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"JSON: {json_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
