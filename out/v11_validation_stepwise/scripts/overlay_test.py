#!/usr/bin/env python3
"""Nhiệm vụ F: Test 3 risk overlays — full backtest + WFO rolling OOS + regime decomposition.

Strategies:
  - V10 baseline (V8ApexConfig defaults)
  - V11 cycle_late_only (WFO-opt: 0.95/2.8/0.90)
  - V11 + Overlay 1: pyramid ban + trail tightening (3 variants)
  - V11 + Overlay 2: position peak-DD stop (6 variants)
  - V11 + Overlay 3: deceleration tightening (5 variants)

Tests:
  A) Full-period backtest: N variants × 3 scenarios
  B) WFO rolling OOS: N variants × 10 windows (harsh only)

Output:
  - overlay_results.csv (full-period results)
  - overlay_wfo.csv (WFO per-window results)
  - overlay_results.json (summary + promotion verdicts)
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
from v10.research.wfo import generate_windows
from v10.strategies.v8_apex import V8ApexConfig, V8ApexStrategy
from v10.strategies.v11_hybrid import V11HybridConfig, V11HybridStrategy

DATA_PATH = "data/bars_btcusdt_2016_now_h1_4h_1d.csv"
WARMUP_DAYS = 365
START = "2019-01-01"
END = "2026-02-20"
OUTDIR = Path("out_v11_validation_stepwise")
SCENARIO_NAMES = ["harsh", "base", "smart"]


# ── Score formula without <10 trades rejection ───────────────────────────

def compute_score_no_reject(summary: dict) -> float:
    cagr = summary.get("cagr_pct", 0.0)
    max_dd = summary.get("max_drawdown_mid_pct", 0.0)
    sharpe = summary.get("sharpe") or 0.0
    pf = summary.get("profit_factor", 0.0) or 0.0
    if isinstance(pf, str):
        pf = 3.0
    n_trades = summary.get("trades", 0)
    return (
        2.5 * cagr
        - 0.60 * max_dd
        + 8.0 * max(0.0, sharpe)
        + 5.0 * max(0.0, min(pf, 3.0) - 1.0)
        + min(n_trades / 50.0, 1.0) * 5.0
    )


# ── Strategy factories ────────────────────────────────────────────────────

def make_v10():
    return V8ApexStrategy(V8ApexConfig())


def _v11_base_cfg():
    """V11 cycle_late_only with WFO-optimal params."""
    cfg = V11HybridConfig()
    cfg.enable_cycle_phase = True
    cfg.cycle_early_aggression = 1.0
    cfg.cycle_early_trail_mult = 3.5
    cfg.cycle_late_aggression = 0.95
    cfg.cycle_late_trail_mult = 2.8
    cfg.cycle_late_max_exposure = 0.90
    return cfg


def make_v11():
    return V11HybridStrategy(_v11_base_cfg())


# Overlay 1 variants: pyramid ban + trail tightening
def make_ov1(trail_mult):
    cfg = _v11_base_cfg()
    cfg.enable_overlay_pyramid_ban = True
    cfg.ov1_late_trail_mult = trail_mult
    return V11HybridStrategy(cfg)


# Overlay 2 variants: position peak-DD stop
def make_ov2(pct=None, atr=None):
    cfg = _v11_base_cfg()
    cfg.enable_overlay_peak_dd_stop = True
    if pct is not None and atr is None:
        cfg.ov2_use_pct = True
        cfg.ov2_use_atr = False
        cfg.ov2_max_pos_dd_pct = pct
    elif atr is not None and pct is None:
        cfg.ov2_use_pct = False
        cfg.ov2_use_atr = True
        cfg.ov2_max_pos_dd_atr = atr
    else:
        cfg.ov2_use_pct = True
        cfg.ov2_use_atr = True
        cfg.ov2_max_pos_dd_pct = pct
        cfg.ov2_max_pos_dd_atr = atr
    return V11HybridStrategy(cfg)


# Overlay 3 variants: deceleration tightening
def make_ov3(accel_bars, trail_mult):
    cfg = _v11_base_cfg()
    cfg.enable_overlay_decel = True
    cfg.ov3_accel_neg_bars = accel_bars
    cfg.ov3_trail_tighten_mult = trail_mult
    return V11HybridStrategy(cfg)


# ── All variant definitions ───────────────────────────────────────────────

VARIANTS = [
    ("v10_baseline", make_v10),
    ("v11_cycle_late", make_v11),
    # Overlay 1: pyramid ban + trail
    ("ov1_trail_1.8", lambda: make_ov1(1.8)),
    ("ov1_trail_2.0", lambda: make_ov1(2.0)),
    ("ov1_trail_2.2", lambda: make_ov1(2.2)),
    # Overlay 2: position peak-DD stop (pct-only)
    ("ov2_pct_5", lambda: make_ov2(pct=0.05)),
    ("ov2_pct_8", lambda: make_ov2(pct=0.08)),
    ("ov2_pct_12", lambda: make_ov2(pct=0.12)),
    # Overlay 2: position peak-DD stop (atr-only)
    ("ov2_atr_2", lambda: make_ov2(atr=2.0)),
    ("ov2_atr_3", lambda: make_ov2(atr=3.0)),
    ("ov2_atr_4", lambda: make_ov2(atr=4.0)),
    # Overlay 3: deceleration tightening
    ("ov3_b3_t1.5", lambda: make_ov3(3, 1.5)),
    ("ov3_b3_t2.5", lambda: make_ov3(3, 2.5)),
    ("ov3_b5_t2.0", lambda: make_ov3(5, 2.0)),
    ("ov3_b8_t1.5", lambda: make_ov3(8, 1.5)),
    ("ov3_b8_t2.5", lambda: make_ov3(8, 2.5)),
]

N_VARIANTS = len(VARIANTS)


# ── Backtest runner ───────────────────────────────────────────────────────

def run_backtest(strategy, scenario, start=START, end=END):
    cost = SCENARIOS[scenario]
    feed = DataFeed(DATA_PATH, start=start, end=end, warmup_days=WARMUP_DAYS)
    engine = BacktestEngine(feed=feed, strategy=strategy, cost=cost,
                            initial_cash=10_000.0)
    result = engine.run()
    return result, feed


def extract_full(result, feed, scenario):
    """Extract full-period metrics + regime decomposition."""
    s = result.summary
    score = compute_objective(s)
    regimes = classify_d1_regimes(feed.d1_bars)
    rr = compute_regime_returns(result.equity, feed.d1_bars, regimes,
                                report_start_ms=feed.report_start_ms)
    return {
        "score": round(score, 2),
        "cagr_pct": round(s.get("cagr_pct", 0.0), 2),
        "total_return_pct": round(s.get("total_return_pct", 0.0), 2),
        "mdd_pct": round(s.get("max_drawdown_mid_pct", 0.0), 2),
        "sharpe": round(s.get("sharpe") or 0.0, 3),
        "trades": s.get("trades", 0),
        "turnover_per_year": round(s.get("turnover_per_year", 0.0), 2),
        "bull_return_pct": round(rr.get("BULL", {}).get("total_return_pct", 0.0), 2),
        "topping_return_pct": round(rr.get("TOPPING", {}).get("total_return_pct", 0.0), 2),
        "bear_return_pct": round(rr.get("BEAR", {}).get("total_return_pct", 0.0), 2),
        "shock_return_pct": round(rr.get("SHOCK", {}).get("total_return_pct", 0.0), 2),
    }


def extract_wfo(result, feed):
    """Extract WFO window metrics."""
    s = result.summary
    return {
        "score_no_reject": round(compute_score_no_reject(s), 2),
        "total_return_pct": round(s.get("total_return_pct", 0.0), 2),
        "sharpe": round(s.get("sharpe") or 0.0, 3),
        "mdd_pct": round(s.get("max_drawdown_mid_pct", 0.0), 2),
        "trades": s.get("trades", 0),
    }


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 72)
    print("Nhiệm vụ F: Risk Overlay Testing")
    print(f"Variants: {N_VARIANTS} | Scenarios: 3 | WFO windows: 10")
    print(f"Full-period backtests: {N_VARIANTS * 3}")
    print(f"WFO backtests: {N_VARIANTS * 10}")
    print(f"Total: {N_VARIANTS * 3 + N_VARIANTS * 10}")
    print("=" * 72)

    # ══ PART A: Full-period backtests ══════════════════════════════════════

    print("\n[PART A] Full-period backtests...")
    full_rows = []
    full_results = {}  # (variant, scenario) -> metrics dict

    for vi, (vname, factory) in enumerate(VARIANTS):
        for si, scenario in enumerate(SCENARIO_NAMES):
            n = vi * len(SCENARIO_NAMES) + si + 1
            total = N_VARIANTS * len(SCENARIO_NAMES)
            print(f"  [{n}/{total}] {vname} × {scenario}...", end=" ", flush=True)

            strategy = factory()
            result, feed = run_backtest(strategy, scenario)
            metrics = extract_full(result, feed, scenario)

            row = {"variant": vname, "scenario": scenario, **metrics}
            full_rows.append(row)
            full_results[(vname, scenario)] = metrics

            print(f"score={metrics['score']:.1f}  ret={metrics['total_return_pct']:.1f}%"
                  f"  bull={metrics['bull_return_pct']:.1f}%  top={metrics['topping_return_pct']:.1f}%")

    # Write full-period CSV
    csv_path = OUTDIR / "overlay_results.csv"
    fields = list(full_rows[0].keys())
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(full_rows)
    print(f"\n  → {csv_path} ({len(full_rows)} rows)")

    # ══ PART B: WFO rolling OOS ═══════════════════════════════════════════

    print("\n[PART B] WFO rolling OOS (harsh only)...")
    windows = generate_windows(START, END, train_months=24, test_months=6, slide_months=6)
    wfo_rows = []
    wfo_results = {}  # (variant, window_id) -> metrics dict

    for vi, (vname, factory) in enumerate(VARIANTS):
        for wi, w in enumerate(windows):
            n = vi * len(windows) + wi + 1
            total = N_VARIANTS * len(windows)
            print(f"  [{n}/{total}] {vname} × W{w.window_id}({w.test_start}→{w.test_end})...",
                  end=" ", flush=True)

            strategy = factory()
            result, feed = run_backtest(strategy, "harsh",
                                        start=w.test_start, end=w.test_end)
            metrics = extract_wfo(result, feed)

            row = {"variant": vname, "window_id": w.window_id,
                   "test_start": w.test_start, "test_end": w.test_end, **metrics}
            wfo_rows.append(row)
            wfo_results[(vname, w.window_id)] = metrics

            print(f"score={metrics['score_no_reject']:.1f}  ret={metrics['total_return_pct']:.1f}%")

    # Write WFO CSV
    wfo_csv = OUTDIR / "overlay_wfo.csv"
    wfo_fields = list(wfo_rows[0].keys())
    with open(wfo_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=wfo_fields)
        w.writeheader()
        w.writerows(wfo_rows)
    print(f"\n  → {wfo_csv} ({len(wfo_rows)} rows)")

    # ══ PART C: Analysis & promotion verdicts ══════════════════════════════

    print("\n[PART C] Analysis...")

    # Reference values
    v10_harsh = full_results[("v10_baseline", "harsh")]
    v11_harsh = full_results[("v11_cycle_late", "harsh")]

    # Per-variant analysis
    verdicts = {}
    print(f"\n{'Variant':<18} {'Score':>7} {'ΔvV10':>7} {'ΔvV11':>7} "
          f"{'BULL%':>7} {'TOP%':>7} {'MDD%':>7} {'Trades':>7} {'WFO%win':>8}")
    print("-" * 90)

    for vname, _ in VARIANTS:
        h = full_results[(vname, "harsh")]

        # WFO win rate vs V11
        wfo_wins = 0
        for wi in range(len(windows)):
            v11_wfo = wfo_results.get(("v11_cycle_late", wi))
            ov_wfo = wfo_results.get((vname, wi))
            if v11_wfo and ov_wfo:
                if ov_wfo["score_no_reject"] > v11_wfo["score_no_reject"]:
                    wfo_wins += 1
        wfo_win_pct = wfo_wins / len(windows) * 100

        d_v10 = h["score"] - v10_harsh["score"]
        d_v11 = h["score"] - v11_harsh["score"]

        print(f"{vname:<18} {h['score']:>7.1f} {d_v10:>+7.1f} {d_v11:>+7.1f} "
              f"{h['bull_return_pct']:>7.1f} {h['topping_return_pct']:>7.1f} "
              f"{h['mdd_pct']:>7.1f} {h['trades']:>7} {wfo_win_pct:>7.0f}%")

        # Promotion criteria
        c1 = h["score"] >= v11_harsh["score"]
        c2 = h["topping_return_pct"] >= v10_harsh["topping_return_pct"]
        c3 = h["bull_return_pct"] >= v10_harsh["bull_return_pct"] * 0.90
        c4 = h["mdd_pct"] <= v10_harsh["mdd_pct"] * 1.001  # tiny tolerance
        c5 = wfo_win_pct >= 60.0

        passed = c1 and c2 and c3 and c4 and c5
        verdicts[vname] = {
            "pass": passed,
            "c1_score_ge_v11": c1,
            "c2_topping_ge_v10": c2,
            "c3_bull_90pct_v10": c3,
            "c4_mdd_le_v10": c4,
            "c5_wfo_60pct": c5,
            "harsh_score": h["score"],
            "delta_v10": round(d_v10, 2),
            "delta_v11": round(d_v11, 2),
            "bull_return": h["bull_return_pct"],
            "topping_return": h["topping_return_pct"],
            "mdd": h["mdd_pct"],
            "wfo_win_pct": round(wfo_win_pct, 1),
        }

    # Check cliff risk per overlay group
    overlay_groups = {
        "OV1": [v for v, _ in VARIANTS if v.startswith("ov1_")],
        "OV2": [v for v, _ in VARIANTS if v.startswith("ov2_")],
        "OV3": [v for v, _ in VARIANTS if v.startswith("ov3_")],
    }
    for group_name, members in overlay_groups.items():
        passing = [v for v in members if verdicts[v]["pass"]]
        cliff_safe = len(passing) >= 2
        print(f"\n  {group_name}: {len(passing)}/{len(members)} variants pass → "
              f"cliff_safe={'YES' if cliff_safe else 'NO'}")

    # ══ PART D: Write JSON ════════════════════════════════════════════════

    def _conv(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Not serializable: {type(obj)}")

    json_path = OUTDIR / "overlay_results.json"
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "n_variants": N_VARIANTS,
        "full_period_backtests": N_VARIANTS * 3,
        "wfo_backtests": N_VARIANTS * 10,
        "reference": {
            "v10_harsh": v10_harsh,
            "v11_harsh": v11_harsh,
        },
        "verdicts": verdicts,
        "overlay_groups": {
            g: {"members": m, "passing": [v for v in m if verdicts[v]["pass"]]}
            for g, m in overlay_groups.items()
        },
        "promotion_criteria": {
            "c1": "harsh score >= V11 cycle_late_only",
            "c2": "TOPPING return >= V10 baseline",
            "c3": "BULL return >= 90% of V10 baseline",
            "c4": "MDD <= V10 baseline",
            "c5": "WFO: >= 60% of windows improve over V11",
            "c6": "cliff_safe: >= 2 variants in group pass",
        },
    }
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=_conv)
    print(f"\n  → {json_path}")

    # ══ Summary ═══════════════════════════════════════════════════════════

    any_promoted = any(v["pass"] for v in verdicts.values()
                       if v != verdicts.get("v10_baseline")
                       and v != verdicts.get("v11_cycle_late"))
    print(f"\n{'='*72}")
    print(f"RESULT: {'PROMOTED variants found' if any_promoted else 'No overlay passes all criteria'}")
    promoted = [vn for vn, vd in verdicts.items()
                if vd["pass"] and vn not in ("v10_baseline", "v11_cycle_late")]
    if promoted:
        print(f"  Promoted: {', '.join(promoted)}")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
